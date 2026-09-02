"""Values a user cannot be expected to know, derived from the scan itself.

Nothing here is applied on its own. A suggestion carries the value and the
evidence behind it, and the user decides: a subnet Talos saw traffic on is a
good guess for the trusted LAN and a bad one for the guest network, and only
the person who built the network can tell the two apart.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any, Iterable

from .model import Scan

# The networks Home Assistant builds for itself. Supervisor puts add-ons on
# 172.30.32.0/23 and Docker hands out the rest of 172.16/12: those are
# container plumbing, not a VLAN somebody decided to build.
CONTAINER_NETWORKS = (
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("127.0.0.0/8"),
)

# One host proves nothing. A subnet worth proposing has to look inhabited.
MIN_HOSTS = 3


@dataclass(frozen=True, slots=True)
class Suggestion:
    """One proposed value, with the count of hosts that produced it."""

    option: str
    value: str
    hosts: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "option": self.option,
            "value": self.value,
            "hosts": self.hosts,
            "detail": self.detail,
        }


def _addresses(scan: Scan) -> list[str]:
    """Every address this scan actually saw, from either side of the join."""
    found = [device.ip for device in scan.devices if device.ip]
    found.extend(
        conduit.source.id
        for conduit in scan.conduits
        if conduit.source.kind == "unknown_host"
    )
    return found


def subnets(scan: Scan) -> list[tuple[str, int]]:
    """The private /24s the scan holds, busiest first."""
    counted: dict[str, set[str]] = {}
    for raw in _addresses(scan):
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if not address.is_private or address.version != 4:
            continue
        if any(address in network for network in CONTAINER_NETWORKS):
            continue
        network = ipaddress.ip_network(f"{address}/24", strict=False)
        counted.setdefault(str(network), set()).add(raw)
    return sorted(
        ((network, len(hosts)) for network, hosts in counted.items()),
        key=lambda pair: (-pair[1], pair[0]),
    )


def suggestions(scan: Scan, options: dict[str, Any] | None = None) -> list[Suggestion]:
    """What Talos can propose for the options that are still empty.

    Only empty options are proposed for: a value the user chose is theirs, and
    overwriting it with a guess would be worse than saying nothing.
    """
    options = options or {}
    found = [pair for pair in subnets(scan) if pair[1] >= MIN_HOSTS]
    if not found:
        return []

    proposed: list[Suggestion] = []
    if not str(options.get("zone_trusted_lan") or "").strip():
        network, hosts = found[0]
        proposed.append(
            Suggestion(
                option="zone_trusted_lan",
                value=network,
                hosts=hosts,
                detail=(
                    "The busiest subnet in this scan. Set it only if this is the"
                    " network your computers and phones are on, because that is"
                    " what the trusted LAN check means by trusted."
                ),
            )
        )

    # A second populated subnet is usually the separated one. Which of the two
    # it is remains the user's call, so both are named and neither is assumed.
    if (
        len(found) > 1
        and found[1][1] >= MIN_HOSTS
        and not str(options.get("zone_iot_vlan") or "").strip()
    ):
        network, hosts = found[1]
        proposed.append(
            Suggestion(
                option="zone_iot_vlan",
                value=network,
                hosts=hosts,
                detail=(
                    "A second subnet carrying traffic in this scan. If your IoT"
                    " devices are the ones on it, this is the IoT VLAN; if they"
                    " are not, leave it empty rather than filling it in."
                ),
            )
        )
    return proposed


def all_subnets_detail(scan: Scan) -> str:
    """Every subnet seen, for the case where none of them can be named."""
    return ", ".join(f"{network} ({hosts})" for network, hosts in subnets(scan))
