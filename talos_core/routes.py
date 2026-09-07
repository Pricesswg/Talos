"""Routes: who is talking, through what, to whom.

The rest of the model answers questions one column at a time. The matrix says
which quadrant a device is in, the conduit table says a name was resolved, the
map says a device hangs off a transport. None of them reads as a sentence, and
a transport that ends in nothing looks like a bug rather than the honest answer
it is.

A route is that sentence, assembled once here so the panel, the exported report
and the CLI all say it the same way. It reads left to right: something inside
the house, the legs that carry its data, and what it reaches at the far end.

Two kinds:

  inbound   How a device reaches Home Assistant. Read from the registry: the
            transport it speaks, the system or hub that relays it, the entry
            that owns it. Always known, and it stops at Home Assistant.
  conduit   An exchange with something else, one per conduit in the scan. What
            it is worth is in the evidence: `declared` is what a config entry
            says it connects to, `observed` is a name the resolver saw asked
            for, `inherited` is a path that runs through a hub. `outward` says
            whether the far end is outside the house.

The observed ones are where the picture usually breaks, and the break is the
point.
A route that cannot be joined carries `missing`, naming the precondition that
would join it in the same vocabulary the checks use, so the panel already has
the words for it. An inbound route whose device was never seen leaving carries
it too: that is the difference between "this device talks to nobody" and "I
could not see whether it does", and it is the whole reason a transport can end
in nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import PHONE_HOME_DESTINATION_KINDS
from .model import Scan

__all__ = ["Leg", "RouteEnd", "Route", "Routes", "build_routes"]

# Transports that can carry a packet to the internet on their own. A device on
# one of these reaches the outside itself; anything else depends on a bridge,
# and saying otherwise would draw a Zigbee bulb talking to a vendor over the
# air.
ROUTABLE_TRANSPORTS = frozenset({"ip", "wifi", "ethernet"})


@dataclass(frozen=True, slots=True)
class RouteEnd:
    """One end of a route. `id` is whatever names it in the scan: a device id,
    an entry id, a destination id, or the literal address of a host nothing
    accounts for."""

    kind: str  # device | integration | ha_core | host | destination
    id: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "id": self.id}


@dataclass(frozen=True, slots=True)
class Leg:
    """One step of the path. Consumers translate `id` for the kinds that have a
    vocabulary (transport, protocol) and look the rest up by id."""

    # transport   the radio or wire the device speaks
    # origin      a system that publishes on its behalf, named by the registry
    #             as a string (zigbee2mqtt, esphome), not by an id
    # hub         a device it sits behind, named by device id
    # protocol    how the next hop is reached, with the address in `detail`
    # integration the config entry that owns it, named by entry id
    # dns         the resolver saw the name at the far end
    kind: str
    id: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        row: dict[str, str] = {"kind": self.kind, "id": self.id}
        if self.detail:
            row["detail"] = self.detail
        return row


@dataclass(frozen=True, slots=True)
class Route:
    id: str
    kind: str  # inbound | conduit
    source: RouteEnd
    legs: tuple[Leg, ...]
    target: RouteEnd
    outward: bool
    evidence: str
    port: int | None = None
    query_count: int | None = None
    filter_status: str | None = None
    # Preconditions that would complete this route, named the way the checks
    # name theirs. Empty means the route is whole.
    missing: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "source": self.source.to_dict(),
            "legs": [leg.to_dict() for leg in self.legs],
            "target": self.target.to_dict(),
            "outward": self.outward,
            "evidence": self.evidence,
        }
        if self.port is not None:
            row["port"] = self.port
        if self.query_count is not None:
            row["query_count"] = self.query_count
        if self.filter_status:
            row["filter_status"] = self.filter_status
        if self.missing:
            row["missing"] = list(self.missing)
        return row


@dataclass(frozen=True, slots=True)
class Routes:
    routes: tuple[Route, ...] = ()
    # Per transport: how many devices speak it, and how many of those were seen
    # reaching anything beyond Home Assistant. The second number is what makes
    # a branch that ends at the transport readable instead of broken.
    transports: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Hosts the resolver saw that no device accounts for, and the counts that
    # go with them. This is the join that did not happen.
    unattributed: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "routes": [route.to_dict() for route in self.routes],
            "transports": self.transports,
            "unattributed": list(self.unattributed),
        }


def build_routes(scan: Scan) -> Routes:
    """Assemble every route this scan can state, and mark the ones it cannot."""
    devices = {device.id: device for device in scan.devices}
    destinations = {destination.id: destination for destination in scan.destinations}

    # An entry's declared address, used as the leg between a bridge and its
    # broker: a Zigbee2MQTT device reaches Home Assistant through MQTT, and the
    # broker is the part worth naming.
    endpoint_of: dict[str, tuple[str, str]] = {}
    for conduit in scan.conduits:
        if conduit.evidence != "declared" or conduit.source.kind != "integration":
            continue
        if conduit.source.id in endpoint_of:
            continue
        destination = destinations.get(conduit.destination_id)
        if destination is None:
            continue
        address = destination.fqdn
        if conduit.port:
            address = f"{address}:{conduit.port}"
        endpoint_of[conduit.source.id] = (conduit.protocol or "", address)

    # Nothing was observed at all, so no device could have been seen leaving:
    # that is a different sentence from "the leases are missing", and the
    # routes have to tell them apart. A correlation that names a method proves
    # nothing on its own: this install reports mac_dhcp with zero devices
    # joined, so the count is what the routes go by.
    observed_any = any(conduit.evidence == "observed" for conduit in scan.conduits)

    routes: list[Route] = []

    # A device Talos has any conduit for is placed: its silence towards the
    # outside is an answer. A device with none could be silent or could be
    # unjoined, and Talos does not guess between the two.
    seen_any: set[str] = set()
    seen_outward: set[str] = set()

    def cut_reason(device_id: str) -> tuple[str, ...]:
        if device_id in seen_any:
            return ()
        return ("observed_evidence",) if not observed_any else ("dhcp_leases",)

    for conduit in scan.conduits:
        destination = destinations.get(conduit.destination_id)
        outward = bool(destination and destination.kind in PHONE_HOME_DESTINATION_KINDS)
        target = RouteEnd("destination", conduit.destination_id)
        legs: list[Leg] = []
        missing: tuple[str, ...] = ()

        if conduit.source.kind == "device":
            device = devices.get(conduit.source.id)
            source = RouteEnd("device", conduit.source.id)
            if device is not None:
                legs.append(Leg("transport", device.transport or "unknown"))
                # A radio device cannot reach the internet by itself: what
                # carries it out is the bridge, and the evidence says so.
                if outward and (device.transport or "unknown") not in ROUTABLE_TRANSPORTS:
                    if device.origin:
                        legs.append(Leg("origin", device.origin))
                    elif device.via_device_id:
                        legs.append(Leg("hub", device.via_device_id))
            # Any conduit at all means Talos knows something about where this
            # device goes: observed by the resolver, or inherited from the hub
            # it sits behind. Either way its branch is not cut.
            seen_any.add(conduit.source.id)
            if outward:
                seen_outward.add(conduit.source.id)
        elif conduit.source.kind == "integration":
            source = RouteEnd("integration", conduit.source.id)
        elif conduit.source.kind == "ha_core":
            source = RouteEnd("ha_core", "core")
        else:
            # A client the resolver saw and nothing in the registry claims.
            source = RouteEnd("host", conduit.source.id)
            missing = ("dhcp_leases",)

        if conduit.evidence == "observed":
            legs.append(Leg("dns", "dns"))
        elif conduit.protocol:
            legs.append(Leg("protocol", conduit.protocol))

        routes.append(
            Route(
                id=f"c:{conduit.id}",
                kind="conduit",
                source=source,
                legs=tuple(legs),
                target=target,
                outward=outward,
                evidence=conduit.evidence,
                port=conduit.port,
                query_count=conduit.query_count,
                filter_status=conduit.filter_status,
                missing=missing,
            )
        )

    # ── inbound: how each device reaches Home Assistant ──────────────────────
    for device in scan.devices:
        legs = [Leg("transport", device.transport or "unknown")]
        # The relay between the device and its entry: the system that publishes
        # it, or the hub it sits behind.
        if device.origin:
            legs.append(Leg("origin", device.origin))
        elif device.via_device_id:
            legs.append(Leg("hub", device.via_device_id))
        if device.integration_id:
            protocol, address = endpoint_of.get(device.integration_id, ("", ""))
            if address:
                legs.append(Leg("protocol", protocol, detail=address))
            legs.append(Leg("integration", device.integration_id))
        routes.append(
            Route(
                id=f"d:{device.id}",
                kind="inbound",
                source=RouteEnd("device", device.id),
                legs=tuple(legs),
                target=RouteEnd("ha_core", "core"),
                outward=False,
                evidence="declared",
                # The branch stops here, and this says whether that is an
                # answer or a hole.
                missing=cut_reason(device.id),
            )
        )

    # ── per transport: how many of its devices carry on past the core ────────
    transports: dict[str, dict[str, Any]] = {}
    for device in scan.devices:
        name = device.transport or "unknown"
        row = transports.setdefault(name, {"devices": 0, "seen": 0, "outward": 0})
        row["devices"] += 1
        if device.id in seen_any:
            row["seen"] += 1
        if device.id in seen_outward:
            row["outward"] += 1
    for row in transports.values():
        # A branch with nothing beyond it says why, in the same words a check
        # that could not run would use.
        row["missing"] = (
            []
            if row["seen"]
            else ["observed_evidence"]
            if not observed_any
            else ["dhcp_leases"]
        )

    unattributed = sorted(
        {
            conduit.source.id
            for conduit in scan.conduits
            if conduit.source.kind == "unknown_host"
        }
    )

    return Routes(routes=tuple(routes), transports=transports, unattributed=tuple(unattributed))
