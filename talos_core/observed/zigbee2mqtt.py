"""Zigbee2MQTT's own view of its network, from its retained topics.

`<base>/bridge/devices` and `<base>/bridge/info` are published retained, so a
subscriber gets the current state the moment it subscribes. Nothing is asked
of the Zigbee network to read them, which matters: the topic that would give
the actual parent of every node is `bridge/request/networkmap`, and requesting
one interrogates every device on the mesh. That is a probe, so it is not done,
and the parent of a node is therefore not claimed.

What is claimed is the tier. A Coordinator, a Router and an EndDevice play
different parts: routers relay for the nodes around them and are mains
powered, end devices sleep and depend on a router being in range. Saying which
is which turns a flat list of forty lamps into the shape of the mesh, without
inventing a single edge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

# What Zigbee2MQTT calls the three parts, mapped to the vocabulary the model
# uses. Anything else it might add stays unknown rather than being guessed.
MESH_ROLES: dict[str, str] = {
    "Coordinator": "coordinator",
    "Router": "router",
    "EndDevice": "end_device",
}


@dataclass(frozen=True, slots=True)
class ZigbeeNode:
    """One node as the bridge describes it."""

    ieee: str
    role: str = "unknown"
    model: str | None = None
    vendor: str | None = None
    battery_powered: bool | None = None
    friendly_name: str | None = None


@dataclass(frozen=True, slots=True)
class BridgeInfo:
    """The coordinator's own state, as far as it reports it."""

    permit_join: bool | None = None
    channel: int | None = None
    version: str | None = None
    base_topic: str | None = None


def parse_devices(payload: Any) -> list[ZigbeeNode]:
    """The node list from `bridge/devices`.

    A payload of another shape produces no nodes rather than an exception: the
    topic is a wildcard subscription and something else may answer on it.
    """
    rows = _as_json(payload)
    if not isinstance(rows, list):
        return []
    nodes = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ieee = row.get("ieee_address") or row.get("ieeeAddr")
        if not ieee:
            continue
        definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
        power = row.get("power_source")
        nodes.append(
            ZigbeeNode(
                ieee=str(ieee).lower(),
                role=MESH_ROLES.get(str(row.get("type") or ""), "unknown"),
                model=(definition or {}).get("model") or row.get("model_id"),
                vendor=(definition or {}).get("vendor") or row.get("manufacturer"),
                battery_powered=str(power) == "Battery" if power else None,
                friendly_name=row.get("friendly_name"),
            )
        )
    return nodes


def parse_info(payload: Any) -> BridgeInfo:
    """The coordinator state from `bridge/info`."""
    data = _as_json(payload)
    if not isinstance(data, dict):
        return BridgeInfo()
    network = data.get("network") if isinstance(data.get("network"), dict) else {}
    permit = data.get("permit_join")
    return BridgeInfo(
        permit_join=bool(permit) if isinstance(permit, bool) else None,
        channel=(network or {}).get("channel"),
        version=data.get("version"),
        base_topic=((data.get("config") or {}).get("mqtt") or {}).get("base_topic")
        if isinstance(data.get("config"), dict)
        else None,
    )


def roles_by_ieee(nodes: Iterable[ZigbeeNode]) -> dict[str, str]:
    """Lowercased IEEE address to mesh role, for joining onto the registry."""
    return {node.ieee: node.role for node in nodes if node.role != "unknown"}


def _as_json(payload: Any) -> Any:
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", "replace")
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except ValueError:
            return None
    return payload
