"""The router that carries the resolver's log.

The report users send most often reads: the resolver is configured, the
log is full, and Talos attributes nothing. The log, looked at, is one host
asking for everything. That is what a router's DHCP does when it hands out
the router itself as the DNS server and forwards cache misses to the
resolver: Fritz!Box, Google and Nest Wifi, eero, Deco and Orbi in router
mode, most ISP boxes, over IPv6 as well when the box announces itself as
DNSv6. A second router doing NAT in front of the resolver looks the same,
and so does a resolver that is only the router's upstream. Nothing behind
that host can be attributed to a device, every silent lease may simply be
behind it, and the checks that read the query log must not pass.

The rule here decides whether the log has that shape. It was tuned on
seventeen synthetic homes and is deliberately conservative: a busy NAS in a
house where everyone else is heard is not a forwarder, nor is Home
Assistant as the busiest client, nor a three device home, nor a stale
network table with one loud host.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from ..model import Device
from .classify import DomainClassifier
from .mapping import HIDDEN_CLIENTS, Lease, Observation, ObservedFacts, parse_time

# Only queries this recent count: the store's totals are cumulative for
# ninety days, and liveness is what lets the note clear the day after the
# router is fixed.
LIVE_HOURS = 24
# A resolver installed minutes ago says nothing.
MIN_QUERIES = 200
# 2.5 times the largest router-only footprint (AVM about 8 names, UniFi
# about 25), far below one relayed phone.
MIN_NAMES = 40
# Admits Home Assistant plus a laptop pointed by hand (65/25/10) and rejects
# a router as an ordinary client (under 0.35).
MIN_SHARE = 0.6
# The relay ceiling: router, Home Assistant, one admin host. Above it the
# registry clause below would fire on stale address tables.
MAX_LIVE = 3
# Where a tracker or a Pi-hole table stops being the resolver's own
# neighbours: five known addresses with at most a fifth of them heard.
MIN_KNOWN = 5
MAX_KNOWN_HEARD = 0.2
# With this many names the host also looks like a single machine pointed at
# the resolver by hand while the rest of the network resolves elsewhere.
HOUSE_NAMES = 300
# A lone daemon resolves fewer names than this; on a container bridge other
# containers compete for the share.
CONTAINER_MIN_SHARE = 0.5
CONTAINER_MIN_NAMES = 20

SUPERVISOR_NETWORKS = (
    ipaddress.ip_network("172.30.32.0/23"),
    ipaddress.ip_network("fd0c:ac1e:2100::/48"),
)
CONTAINER_NETWORKS = (
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("127.0.0.0/8"),
)
ROUTER_MODELS = re.compile(
    r"fritz!?box|udm|dream machine|ucg|usg|edgerouter|orbi|deco|eero|nest wifi|google wifi"
    r"|amplifi|velop|archer|nighthawk|speedport|opnsense|pfsense",
    re.IGNORECASE,
)
ROUTER_NAMES = (
    "fritz", "router", "gateway", "gw", "openwrt", "udm", "unifi", "usg", "ucg", "opnsense",
    "pfsense", "speedport", "orbi", "deco", "eero", "amplifi", "velop", "mikrotik", "keenetic",
    "livebox", "nest wifi", "google wifi", "vodafone", "technicolor", "sagemcom",
)


@dataclass(frozen=True, slots=True)
class Forwarder:
    address: str
    tier: str  # house | single | loopback | container | container_unreferenced
    share: float
    names: int
    live_clients: int
    known: int
    known_heard: int
    identity: str | None  # gateway_address | registry_model | name | None
    label: str | None


def _address(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _is_container(address: Any) -> bool:
    return any(address in network for network in CONTAINER_NETWORKS)


def _is_supervisor(address: Any) -> bool:
    return any(address in network for network in SUPERVISOR_NETWORKS)


def _is_lan(address: Any) -> bool:
    return (
        address is not None
        and not _is_container(address)
        and not address.is_loopback
        and not address.is_link_local
    )


def find_forwarder(
    facts: ObservedFacts,
    devices: Sequence[Device],
    device_by_ip: dict[str, str],
    classifier: DomainClassifier,
    now: datetime | None = None,
) -> Forwarder | None:
    """Whether one host carries the log, and which."""
    if facts.log_hidden and "client" in facts.log_hidden:
        return None
    reference = parse_time(facts.cursor) if facts.cursor else None
    reference = reference or now or datetime.now(timezone.utc)
    horizon = reference - timedelta(hours=facts.window_hours or LIVE_HOURS)

    count: dict[str, int] = {}
    names: dict[str, set[str]] = {}
    last: dict[str, datetime] = {}
    for observation in facts.observations:
        client = observation.client
        if client in HIDDEN_CLIENTS:
            continue
        stamp = parse_time(observation.last_seen)
        if stamp is None:
            continue
        count[client] = count.get(client, 0) + observation.count
        if not classifier.is_ignored(observation.fqdn):
            names.setdefault(client, set()).add(observation.fqdn)
        if client not in last or stamp > last[client]:
            last[client] = stamp

    live = {client for client, stamp in last.items() if stamp >= horizon}
    if not live or sum(count[c] for c in live) < MIN_QUERIES:
        return None

    lan = {c for c in live if _is_lan(_address(c))}
    if lan:
        total = sum(count[c] for c in lan)
        dominant = max(lan, key=lambda c: (count[c], c))
        share = count[dominant] / total if total else 0.0
        distinct = len(names.get(dominant, ()))
        if distinct < MIN_NAMES or share < MIN_SHARE or len(lan) > MAX_LIVE:
            return None
        known = _known_addresses(facts.leases, devices, reference) - {dominant}
        heard = known & live
        identity, label = _identity(dominant, facts, devices, device_by_ip)
        registry_clause = len(known) >= MIN_KNOWN and len(heard) <= max(1, int(MAX_KNOWN_HEARD * len(known)))
        if identity is None and not registry_clause:
            return None
        return Forwarder(
            address=dominant,
            tier="house" if distinct >= HOUSE_NAMES else "single",
            share=share,
            names=distinct,
            live_clients=len(live),
            known=len(known),
            known_heard=len(heard),
            identity=identity,
            label=label,
        )

    # No LAN client at all: the whole log comes from the machine itself, or
    # from a container network's gateway.
    total = sum(count[c] for c in live)
    dominant = max(live, key=lambda c: (count[c], c))
    share = count[dominant] / total if total else 0.0
    distinct = len(names.get(dominant, ()))
    if share < CONTAINER_MIN_SHARE or distinct < CONTAINER_MIN_NAMES:
        return None
    address = _address(dominant)
    if address is None:
        return None
    if address.is_loopback:
        return Forwarder(dominant, "loopback", share, distinct, len(live), 0, 0, None, None)
    if (
        address.version == 4
        and _is_container(address)
        and not _is_supervisor(address)
        and int(str(address).rsplit(".", 1)[-1]) == 1
        and all(lease.mac.lower().startswith("02:42:") for lease in facts.leases if lease.ip == dominant)
    ):
        referenced = any(
            _is_lan(_address(ip)) and (_address(ip) or address).version == 4 and (_address(ip) or address).is_private
            for ip in [l.ip for l in facts.leases] + [d.ip for d in devices if d.ip]
        )
        return Forwarder(
            dominant, "container" if referenced else "container_unreferenced",
            share, distinct, len(live), 0, 0, None, None,
        )
    return None


def _known_addresses(leases: Iterable[Lease], devices: Sequence[Device], reference: datetime) -> set[str]:
    """Addresses the table and the registry hold for real devices: IPv4,
    not in a container range, and for wire pairs seen within a week."""
    known: set[str] = set()
    week = reference - timedelta(days=7)
    for lease in leases:
        address = _address(lease.ip)
        if address is None or address.version != 4 or _is_container(address):
            continue
        seen = parse_time(lease.seen_at) if lease.seen_at else None
        if seen is not None and seen < week:
            continue
        known.add(lease.ip)
    for device in devices:
        address = _address(device.ip) if device.ip else None
        if address is None or address.version != 4 or not address.is_private or _is_container(address):
            continue
        known.add(device.ip)
    return known


def _identity(
    dominant: str,
    facts: ObservedFacts,
    devices: Sequence[Device],
    device_by_ip: dict[str, str],
) -> tuple[str | None, str | None]:
    """What names the dominant host as a router, if anything does. A
    manufacturer alone never does: a Fritz tracker stamps AVM on every
    laptop it tracks."""
    address = _address(dominant)
    if address is not None and address.version == 4:
        last_octet = int(str(address).rsplit(".", 1)[-1])
        if last_octet in (1, 254):
            return "gateway_address", None
    device_id = device_by_ip.get(dominant)
    if device_id:
        device = next((d for d in devices if d.id == device_id), None)
        model = (device.model or "") if device else ""
        if model and ROUTER_MODELS.search(model) and "tracked" not in model.lower():
            return "registry_model", model
    label = facts.client_names.get(dominant) or next(
        (lease.hostname for lease in facts.leases if lease.ip == dominant and lease.hostname), None
    )
    if label and any(token in label.lower() for token in ROUTER_NAMES):
        return "name", label
    return None, None


def is_supervisor_client(client: str) -> bool:
    address = _address(client)
    return address is not None and _is_supervisor(address)
