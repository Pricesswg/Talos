"""Reading the broker's own client list, through Home Assistant's connection.

No second MQTT client and no credentials of our own: if the MQTT integration
is loaded then Home Assistant already holds an authorised session, and this
subscribes to `$SYS` on it. Read-only, and it publishes nothing.

Not every broker answers. Mosquitto exposes counters under `$SYS/broker` and
names no client at all unless it was built with the option; EMQX names them
per node. Either way the rule is the same: if no client id arrives, the facts
come back unavailable with the reason, and the check that depends on them is
declared unverified rather than passed on an empty list.
"""

from __future__ import annotations

import asyncio
import logging
import re
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
# is a ceiling for a slow broker and not a fixed cost per scan.
LISTEN_SECONDS = 4.0


def client_id_from_topic(topic: str) -> str | None:
    """The client id a $SYS topic names, if it names one rather than a count."""
    match = CLIENT_TOPIC.match(topic)
    if not match:
        return None
    client = match.group("client")
    return None if client in COUNTER_LEVELS else client


async def collect_mqtt(hass: Any, scan: Scan, seconds: float = LISTEN_SECONDS) -> MqttFacts:
    """Subscribe to $SYS long enough to hear who is connected.

    Every failure mode ends the same way: facts that say what went wrong,
    never an empty list presented as an answer.
    """
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
        return MqttFacts(
            available=False,
            error=(
                "the broker published no client id under $SYS. Mosquitto only"
                " exposes counters there unless it was built otherwise, so this"
                " is the normal answer on a default install rather than a fault"
            ),
        )
    return MqttFacts(available=True, clients=match_clients(found, scan))


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
