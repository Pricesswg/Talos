"""Matching broker clients back to things Home Assistant knows about.

A broker identifies a client by the name the client gave itself and nothing
else. There is no MAC, no registry id, often not even a stable address, so
this is a name-matching problem and it is treated as one: a client is matched
when its id contains a token that belongs to something in the scan, and the
token that matched is recorded so the reader can judge it.

What cannot be matched is not called an intruder. It is called unmatched.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..model import MqttClient, Scan

# Clients Home Assistant itself opens. Their ids are generated per connection,
# so they are matched by prefix rather than by equality.
HOME_ASSISTANT_PREFIXES: tuple[str, ...] = (
    "home-assistant",
    "homeassistant",
    "ha-",
    "hass",
    "mqtt-explorer",
)

# A token shorter than this matches everything and proves nothing.
MIN_TOKEN = 4

_SPLIT = re.compile(r"[^a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return {part for part in _SPLIT.split(value.lower()) if len(part) >= MIN_TOKEN}


def known_tokens(scan: Scan) -> dict[str, str]:
    """Every name in the scan worth recognising, mapped to what it names."""
    known: dict[str, str] = {}

    def add(value: str | None, owner: str) -> None:
        if not value:
            return
        for token in _tokens(str(value)):
            known.setdefault(token, owner)

    for integration in scan.integrations:
        add(integration.domain, integration.title or integration.domain)
        add(integration.title, integration.title or integration.domain)
    for device in scan.devices:
        add(device.name, device.name)
        # The system that produced it names itself: "esphome" matching a
        # client called esphome-porch should read as ESPHome, not as whichever
        # device happened to be first in the list.
        add(device.origin, device.origin)
        if device.mac:
            known.setdefault(device.mac.replace(":", "").lower(), device.name)
    return known


def match_clients(clients: Iterable[str], scan: Scan) -> tuple[MqttClient, ...]:
    """Attribute each client id, leaving the ones nothing accounts for."""
    known = known_tokens(scan)
    matched: list[MqttClient] = []
    for client_id in clients:
        lowered = client_id.lower()
        owner: str | None = None
        if any(lowered.startswith(prefix) for prefix in HOME_ASSISTANT_PREFIXES):
            owner = "Home Assistant"
        else:
            for token in _tokens(client_id):
                if token in known:
                    owner = known[token]
                    break
        matched.append(MqttClient(client_id=client_id, matched=owner))
    return tuple(sorted(matched, key=lambda client: client.client_id))
