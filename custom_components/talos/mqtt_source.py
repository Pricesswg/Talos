"""Reading the broker's own client list.

Two ways in, and the difference matters. Home Assistant already holds an
authorised session, so by default this subscribes on that one: no second
connection, no credentials of ours. The catch is that most brokers restrict
the `$SYS` tree, and the account the MQTT integration uses has no reason to
hold that right, so on a locked-down broker the default path returns nothing.

Giving Talos its own read-only account is the way around that. It is used only
when one is configured, it publishes nothing, and it subscribes to `$SYS` and
to nothing else. Either way the rule is the same: if no client id arrives, the
facts come back unavailable with the reason, and the check that depends on
them is declared unverified rather than passed on an empty list.
"""

from __future__ import annotations

import asyncio
import logging
import re
import ssl
from dataclasses import replace
from typing import Any

from .core import MqttFacts, Scan, ZigbeeFacts, match_clients

_LOGGER = logging.getLogger(__name__)

# Mosquitto, then EMQX. Both are subscribed: whichever answers, answers.
SYS_TOPICS: tuple[str, ...] = (
    "$SYS/broker/clients/#",
    "$SYS/brokers/+/clients/#",
)

# The client id sits in the topic, not the payload, and only on the levels
# that name one. Everything below is a counter published at the same depth:
# EMQX writes $SYS/brokers/<node>/clients/count, and reading that as a client
# called "count" would invent a finding out of a gauge.
CLIENT_TOPIC = re.compile(r"\$SYS/broker(?:s/[^/]+)?/clients/(?P<client>[^/]+)(?:/.*)?$")
COUNTER_LEVELS = frozenset(
    {
        "connected",
        "disconnected",
        "total",
        "count",
        "max",
        "maximum",
        "expired",
        "active",
        "inactive",
    }
)

# Zigbee2MQTT publishes these retained, so they arrive the moment we
# subscribe. The base topic is configurable, hence the wildcard: whoever
# answers on `<anything>/bridge/devices` is a Zigbee2MQTT bridge.
#
# `bridge/request/networkmap` would give the actual parent of every node, and
# is deliberately not used: requesting one interrogates every device on the
# mesh, which is a probe.
ZIGBEE_TOPICS: tuple[str, ...] = ("+/bridge/devices", "+/bridge/info")

# How long to stay subscribed. Retained $SYS messages arrive at once, so this
# is a ceiling for a slow broker, not a fixed cost per scan.
LISTEN_SECONDS = 4.0

# The client id Talos connects under. Fixed and recognisable on purpose: it
# has to be obvious in the broker's own client list which connection is ours.
CLIENT_ID = "talos-scanner"

NO_CLIENT_IDS = (
    "the broker published no client id under $SYS. Mosquitto only exposes"
    " counters there unless it was built otherwise, and most brokers restrict"
    " the tree to an account that holds the right to read it, so this is a"
    " normal answer rather than a fault"
)


def client_id_from_topic(topic: str) -> str | None:
    """The client id a $SYS topic names, if it names one rather than a count."""
    match = CLIENT_TOPIC.match(topic)
    if not match:
        return None
    client = match.group("client")
    return None if client in COUNTER_LEVELS else client


def read_sys_blocking(
    host: str,
    port: int,
    username: str = "",
    password: str = "",
    tls: bool = False,
    seconds: float = LISTEN_SECONDS,
) -> tuple[set[str], str | None]:
    """Connect, listen to $SYS, disconnect. Blocking, so it runs off the loop.

    Returns the client ids heard and the reason there were none, never an
    exception: a broker that refuses $SYS is an ordinary outcome here.
    """
    try:
        import paho.mqtt.client as paho
    except ImportError as err:  # pragma: no cover - only without the requirement
        return set(), f"the MQTT client library is unavailable: {err}"

    found: set[str] = set()
    failure: list[str] = []

    def on_connect(client: Any, _userdata: Any, _flags: Any, reason: Any, *_rest: Any) -> None:
        # paho 1.x hands an int, 2.x a ReasonCode. Both compare to 0 wrong, so
        # the string is the only thing both agree on.
        code = getattr(reason, "value", reason)
        if code not in (0, "Success"):
            failure.append(f"the broker refused the connection: {reason}")
            return
        for topic in SYS_TOPICS:
            client.subscribe(topic, qos=0)

    def on_message(_client: Any, _userdata: Any, message: Any) -> None:
        client_id = client_id_from_topic(message.topic)
        if client_id:
            found.add(client_id)

    try:
        version = getattr(paho, "CallbackAPIVersion", None)
        client = (
            paho.Client(version.VERSION1, client_id=CLIENT_ID)
            if version is not None
            else paho.Client(client_id=CLIENT_ID)
        )
        if username:
            client.username_pw_set(username, password or None)
        if tls:
            client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(host, port, keepalive=max(10, int(seconds) + 5))
        client.loop_start()
        deadline = seconds
        step = 0.25
        while deadline > 0 and not failure:
            _sleep(step)
            deadline -= step
    except Exception as err:  # noqa: BLE001 - every failure is a reported reason
        return set(), f"connecting to {host}:{port} failed: {err}"
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Talos: disconnecting from the broker failed", exc_info=True)

    if failure:
        return set(), failure[0]
    return found, None if found else NO_CLIENT_IDS


def _sleep(seconds: float) -> None:
    """Blocking sleep, isolated so the executor path stays obvious."""
    import time

    time.sleep(seconds)


async def collect_via_credentials(
    hass: Any, scan: Scan, credentials: dict[str, Any], seconds: float = LISTEN_SECONDS
) -> MqttFacts:
    """Talos's own read-only session, used only when one is configured."""
    host = str(credentials.get("host") or "").strip()
    if not host:
        return MqttFacts(available=False, route="account", error="no broker address configured")
    found, error = await hass.async_add_executor_job(
        read_sys_blocking,
        host,
        int(credentials.get("port") or 1883),
        str(credentials.get("username") or ""),
        str(credentials.get("password") or ""),
        bool(credentials.get("tls")),
        seconds,
    )
    if error:
        return MqttFacts(available=False, route="account", error=error)
    return MqttFacts(available=True, route="account", clients=match_clients(found, scan))


async def collect_zigbee(hass: Any, seconds: float = 2.0) -> tuple[ZigbeeFacts, dict[str, str]]:
    """The coordinator's own view, from Zigbee2MQTT's retained topics.

    Returns the network facts and the mesh role of every node it named, keyed
    by IEEE address so the caller can join it onto the device registry.
    """
    from .core import ZigbeeFacts, parse_devices, parse_info, roles_by_ieee

    if "mqtt" not in hass.config.components:
        return ZigbeeFacts(available=False, error="the MQTT integration is not loaded"), {}
    try:
        from homeassistant.components import mqtt
    except ImportError as err:  # pragma: no cover - only on a build without MQTT
        return ZigbeeFacts(available=False, error=f"the MQTT component is unavailable: {err}"), {}

    nodes: list[Any] = []
    info: Any = None

    @callback_safe
    def _on_message(message: Any) -> None:
        nonlocal nodes, info
        topic = getattr(message, "topic", "") or ""
        payload = getattr(message, "payload", None)
        if topic.endswith("/bridge/devices"):
            found = parse_devices(payload)
            if found:
                nodes = found
        elif topic.endswith("/bridge/info"):
            parsed = parse_info(payload)
            if parsed.version or parsed.permit_join is not None:
                info = parsed

    unsubscribe = []
    try:
        for topic in ZIGBEE_TOPICS:
            unsubscribe.append(await mqtt.async_subscribe(hass, topic, _on_message, qos=0))
        await asyncio.sleep(seconds)
    except Exception as err:  # noqa: BLE001
        return ZigbeeFacts(available=False, error=f"subscribing to the bridge failed: {err}"), {}
    finally:
        for stop in unsubscribe:
            try:
                stop()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Talos: unsubscribing from the bridge failed", exc_info=True)

    if not nodes and info is None:
        return (
            ZigbeeFacts(
                available=False,
                error=(
                    "no Zigbee2MQTT bridge answered on <base>/bridge/devices."
                    " A coordinator behind ZHA or another add-on does not publish"
                    " these topics, so this is a normal answer rather than a fault"
                ),
            ),
            {},
        )

    roles = roles_by_ieee(nodes)
    return (
        ZigbeeFacts(
            available=True,
            permit_join=info.permit_join if info else None,
            channel=info.channel if info else None,
            version=info.version if info else None,
            nodes=len(nodes),
            routers=sum(1 for node in nodes if node.role == "router"),
            end_devices=sum(1 for node in nodes if node.role == "end_device"),
        ),
        roles,
    )


async def collect_via_home_assistant(
    hass: Any, scan: Scan, seconds: float = LISTEN_SECONDS
) -> MqttFacts:
    """The session the MQTT integration already holds. No new connection."""
    if "mqtt" not in hass.config.components:
        return MqttFacts(
            available=False,
            route="session",
            error="the MQTT integration is not loaded, so there is no broker session to use",
        )

    try:
        from homeassistant.components import mqtt
    except ImportError as err:  # pragma: no cover - only on a build without MQTT
        return MqttFacts(available=False, route="session", error=f"the MQTT component is unavailable: {err}")

    found: set[str] = set()

    @callback_safe
    def _on_message(message: Any) -> None:
        client = client_id_from_topic(getattr(message, "topic", "") or "")
        if client:
            found.add(client)

    unsubscribe = []
    try:
        for topic in SYS_TOPICS:
            unsubscribe.append(await mqtt.async_subscribe(hass, topic, _on_message, qos=0))
        await asyncio.sleep(seconds)
    except Exception as err:  # noqa: BLE001 - a broker refusing $SYS is normal
        return MqttFacts(available=False, route="session", error=f"subscribing to $SYS failed: {err}")
    finally:
        for stop in unsubscribe:
            try:
                stop()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Talos: unsubscribing from $SYS failed", exc_info=True)

    if not found:
        return MqttFacts(available=False, route="session", error=NO_CLIENT_IDS)
    return MqttFacts(available=True, route="session", clients=match_clients(found, scan))


def normalise_api_url(raw: str) -> str:
    """Make an address typed by a person into one a client can use.

    `192.168.50.92:18083` is what somebody reads off the EMQX dashboard and
    types in, and without a scheme it parses to nothing at all: the request
    then goes to a URL with no host and fails in a way that says nothing about
    what went wrong. A pasted `/api/v5` tail is dropped for the same reason,
    since the path is added back on every request.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"http://{text}"
    text = text.rstrip("/")
    for tail in ("/api/v5/clients", "/api/v5", "/api"):
        if text.endswith(tail):
            text = text[: -len(tail)]
            break
    return text.rstrip("/")


async def collect_via_api(
    hass: Any, scan: Scan, api: dict[str, Any]
) -> MqttFacts:
    """EMQX 5's own client list, over HTTP with an API key.

    Read-only and stateless: one GET per page, no subscription, no session on
    the broker at all. It is also the only route that returns addresses, so a
    client whose id matches nothing can still be attributed to the device it
    connected from.
    """
    from .core import (
        EMQX_CLIENTS_PATH,
        EMQX_MAX_PAGES,
        EMQX_PAGE_SIZE,
        emqx_has_more,
        emqx_to_clients,
        parse_emqx_clients,
    )
    from .core import ObservedAuthError, ObservedError
    from .http_transport import HassHttpTransport

    url = normalise_api_url(api.get("url") or "")
    if not url:
        return MqttFacts(available=False, route="api", error="no EMQX API address configured")

    transport = HassHttpTransport(
        hass,
        url,
        str(api.get("key") or ""),
        str(api.get("secret") or ""),
        bool(api.get("verify_ssl", True)),
        timeout=15,
    )

    rows: list[dict[str, Any]] = []
    try:
        for page in range(1, EMQX_MAX_PAGES + 1):
            payload = await transport.get_json(
                EMQX_CLIENTS_PATH, {"page": page, "limit": EMQX_PAGE_SIZE}
            )
            found = parse_emqx_clients(payload)
            rows.extend(found)
            if not found or not emqx_has_more(payload, len(rows)):
                break
    except ObservedAuthError as err:
        return MqttFacts(available=False, route="api", error=f"the EMQX API rejected the key: {err}")
    except ObservedError as err:
        return MqttFacts(available=False, route="api", error=f"the EMQX API is unreachable: {err}")
    except Exception as err:  # noqa: BLE001
        return MqttFacts(available=False, route="api", error=f"reading the EMQX client list failed: {err}")

    if not rows:
        return MqttFacts(
            available=False,
            route="api",
            error=(
                "the EMQX API answered with no client at all, which a broker"
                " running Home Assistant cannot be: check that the key belongs"
                " to the same node the devices connect to"
            ),
        )
    return MqttFacts(available=True, route="api", clients=emqx_to_clients(rows, scan))


async def collect_mqtt(
    hass: Any,
    scan: Scan,
    credentials: dict[str, Any] | None = None,
    seconds: float = LISTEN_SECONDS,
    api: dict[str, Any] | None = None,
) -> MqttFacts:
    """Best route first, and the next one when the best fails.

    The EMQX API is preferred where a key is configured: on EMQX 5 it is the
    only route that can answer at all, and it is the only one anywhere that
    returns the address each client connected from. Then Talos's own account,
    which gets past a broker that reserves $SYS. Then the session Home
    Assistant already holds, which needs nothing.

    A configured route that fails hands over to the next rather than ending
    the search. Configuring something must never leave Talos with less than it
    had before, and the failure is carried on the result so the panel can say
    which route answered and which one was meant to.
    """
    attempts: list[tuple[str, Any]] = []
    if api and api.get("url"):
        attempts.append(("api", lambda: collect_via_api(hass, scan, api)))
    if credentials and credentials.get("host"):
        attempts.append(
            ("account", lambda: collect_via_credentials(hass, scan, credentials, seconds))
        )
    attempts.append(("session", lambda: collect_via_home_assistant(hass, scan, seconds)))

    first_failure: MqttFacts | None = None
    for _name, run in attempts:
        facts = await run()
        if facts.available:
            if first_failure is not None:
                return replace(
                    facts,
                    fallback_from=first_failure.route,
                    error=first_failure.error,
                )
            return facts
        if first_failure is None:
            first_failure = facts
    # Nothing answered. The first failure is the one worth reporting: it is
    # the route the user configured and expected to work.
    return first_failure or MqttFacts(available=False, error="no MQTT source available")


def callback_safe(func: Any) -> Any:
    """Mark the handler as a callback when Home Assistant is importable.

    Kept behind a function so this module still imports in a plain test
    environment, which is the same reason every other HA import here is lazy.
    """
    try:
        from homeassistant.core import callback

        return callback(func)
    except ImportError:  # pragma: no cover - outside Home Assistant
        return func
