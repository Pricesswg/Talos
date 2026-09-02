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
from typing import Any

from .core import MqttFacts, Scan, match_clients

_LOGGER = logging.getLogger(__name__)

# Mosquitto, then EMQX. Both are subscribed: whichever answers, answers.
SYS_TOPICS: tuple[str, ...] = (
    "$SYS/broker/clients/#",
    "$SYS/brokers/+/clients/#",
)

# The client id sits in the topic, not the payload, and only on the levels
# that name one. `connected` and `total` are counters and carry no id.
CLIENT_TOPIC = re.compile(r"\$SYS/broker(?:s/[^/]+)?/clients/(?P<client>[^/]+)(?:/.*)?$")
COUNTER_LEVELS = frozenset(
    {"connected", "total", "maximum", "disconnected", "expired", "active", "inactive"}
)

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
        return MqttFacts(available=False, error="no broker address configured")
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
        return MqttFacts(available=False, error=error)
    return MqttFacts(available=True, clients=match_clients(found, scan))


async def collect_via_home_assistant(
    hass: Any, scan: Scan, seconds: float = LISTEN_SECONDS
) -> MqttFacts:
    """The session the MQTT integration already holds. No new connection."""
    if "mqtt" not in hass.config.components:
        return MqttFacts(
            available=False,
            error="the MQTT integration is not loaded, so there is no broker session to use",
        )

    try:
        from homeassistant.components import mqtt
    except ImportError as err:  # pragma: no cover - only on a build without MQTT
        return MqttFacts(available=False, error=f"the MQTT component is unavailable: {err}")

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
        return MqttFacts(available=False, error=f"subscribing to $SYS failed: {err}")
    finally:
        for stop in unsubscribe:
            try:
                stop()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Talos: unsubscribing from $SYS failed", exc_info=True)

    if not found:
        return MqttFacts(available=False, error=NO_CLIENT_IDS)
    return MqttFacts(available=True, clients=match_clients(found, scan))


async def collect_mqtt(
    hass: Any,
    scan: Scan,
    credentials: dict[str, Any] | None = None,
    seconds: float = LISTEN_SECONDS,
) -> MqttFacts:
    """Talos's own account when there is one, Home Assistant's session when
    there is not. Configuring an account is the way past a broker that keeps
    $SYS to itself, which is most of them."""
    if credentials and credentials.get("host"):
        return await collect_via_credentials(hass, scan, credentials, seconds)
    return await collect_via_home_assistant(hass, scan, seconds)


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
