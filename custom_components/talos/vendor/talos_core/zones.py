"""Network zones from IP ranges.

Home Assistant does not know that 192.168.30.0/24 is the IoT VLAN — only the
person who set the network up knows that. So the ranges are configuration,
and a device whose address matches none of them stays `unknown` rather than
being assumed to sit on the trusted LAN.

That distinction carries weight downstream: a posture check about devices on
the trusted LAN cannot run at all until at least one range is configured, and
reporting it as passed would be a lie by omission.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any, Iterable

from .const import ZONES


@dataclass(frozen=True, slots=True)
class ZoneRule:
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    zone: str

    @property
    def prefixlen(self) -> int:
        return self.network.prefixlen


class ZoneMap:
    """Longest prefix wins, so a /28 carve-out beats the /24 around it."""

    def __init__(self, rules: Iterable[ZoneRule] = ()) -> None:
        self._rules = sorted(rules, key=lambda rule: rule.prefixlen, reverse=True)

    def __bool__(self) -> bool:
        return bool(self._rules)

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[str, str]]) -> ZoneMap:
        rules: list[ZoneRule] = []
        for cidr, zone in pairs:
            if not cidr or zone not in ZONES:
                continue
            try:
                network = ipaddress.ip_network(cidr, strict=False)
            except ValueError:
                # A malformed range is dropped rather than guessed at; the
                # check that needs it will report itself unverifiable.
                continue
            rules.append(ZoneRule(network, zone))
        return cls(rules)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> ZoneMap:
        """Accepts `{"iot_vlan": "192.168.30.0/24", ...}` or lists of ranges."""
        if not raw:
            return cls()
        pairs: list[tuple[str, str]] = []
        for zone, value in raw.items():
            if isinstance(value, str):
                pairs.extend((cidr.strip(), zone) for cidr in value.split(",") if cidr.strip())
            elif isinstance(value, (list, tuple)):
                pairs.extend((str(cidr).strip(), zone) for cidr in value)
        return cls.from_pairs(pairs)

    def zone_for(self, ip: str | None) -> str:
        if not ip:
            return "unknown"
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return "unknown"
        for rule in self._rules:
            if address in rule.network:
                return rule.zone
        return "unknown"
