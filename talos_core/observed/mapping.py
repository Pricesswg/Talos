"""Query log records -> aggregated observations, plus the zero check.

Pure functions over plain dicts, so the aggregation and the zero check can be
tested against recorded AdGuard payloads with no appliance in the loop.

The query log says **with whom** a host spoke. It does not say what was said,
nor how much: nothing derived here may be phrased as data leaving the house.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence

# AdGuard reports why a query was answered the way it was. Every reason that
# starts with "Filtered" means a filter intervened; "NotFilteredWhiteList" is
# an explicit allow and deliberately does not match.
_BLOCKED_PREFIX = "Filtered"


@dataclass(frozen=True, slots=True)
class Observation:
    """One client talking to one name, aggregated over the retention window."""

    client: str
    fqdn: str
    count: int
    blocked: int
    first_seen: str
    last_seen: str

    @property
    def filter_status(self) -> str:
        """`blocked` means at least one query was filtered, not all of them."""
        return "blocked" if self.blocked else "allowed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "client": self.client,
            "fqdn": self.fqdn,
            "count": self.count,
            "blocked": self.blocked,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Observation:
        return cls(
            client=raw["client"],
            fqdn=raw["fqdn"],
            count=int(raw.get("count") or 0),
            blocked=int(raw.get("blocked") or 0),
            first_seen=raw["first_seen"],
            last_seen=raw["last_seen"],
        )


@dataclass(frozen=True, slots=True)
class Lease:
    """A DHCP lease: the only place a MAC and an IP appear together."""

    mac: str
    ip: str
    hostname: str | None = None
    static: bool = False


@dataclass(frozen=True, slots=True)
class ZeroCheck:
    """The tool's own blind spots, measured rather than assumed.

    Runs continuously, not once: a device that arrives tomorrow with a
    hardcoded resolver has to surface on its own.
    """

    dhcp_available: bool
    silent_leases: tuple[Lease, ...] = ()
    unleased_clients: tuple[str, ...] = ()

    @property
    def is_conclusive(self) -> bool:
        """Without leases there is nothing to compare the clients against."""
        return self.dhcp_available


@dataclass(frozen=True, slots=True)
class ObservedFacts:
    observations: tuple[Observation, ...] = ()
    leases: tuple[Lease, ...] = ()
    client_names: dict[str, str] = field(default_factory=dict)
    zero: ZeroCheck = ZeroCheck(dhcp_available=False)
    cursor: str | None = None
    window_hours: int = 24


def parse_time(value: Any) -> datetime | None:
    """AdGuard stamps RFC 3339; tolerate a trailing Z and stray whitespace."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def aggregate(
    records: Iterable[dict[str, Any]],
    previous: Iterable[Observation] = (),
) -> tuple[Observation, ...]:
    """Fold query log records into per client-and-name totals.

    `previous` carries what earlier polls already counted: AdGuard's retention
    is limited and the log rolls over, so the running total has to live here
    rather than being re-read from the appliance.
    """
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for observation in previous:
        merged[(observation.client, observation.fqdn)] = {
            "count": observation.count,
            "blocked": observation.blocked,
            "first": observation.first_seen,
            "last": observation.last_seen,
        }

    for record in records:
        client = record.get("client")
        question = record.get("question") or {}
        fqdn = (question.get("name") or "").rstrip(".").lower()
        if not client or not fqdn:
            continue

        stamp = record.get("time")
        if parse_time(stamp) is None:
            continue

        blocked = str(record.get("reason") or "").startswith(_BLOCKED_PREFIX)
        bucket = merged.setdefault(
            (client, fqdn), {"count": 0, "blocked": 0, "first": stamp, "last": stamp}
        )
        bucket["count"] += 1
        bucket["blocked"] += 1 if blocked else 0
        bucket["first"] = _earlier(bucket["first"], stamp)
        bucket["last"] = _later(bucket["last"], stamp)

    return tuple(
        sorted(
            (
                Observation(
                    client=client,
                    fqdn=fqdn,
                    count=data["count"],
                    blocked=data["blocked"],
                    first_seen=data["first"],
                    last_seen=data["last"],
                )
                for (client, fqdn), data in merged.items()
            ),
            key=lambda o: (-o.count, o.client, o.fqdn),
        )
    )


def parse_leases(status: Any) -> tuple[bool, tuple[Lease, ...]]:
    """Read `/control/dhcp/status`.

    Returns whether AdGuard is actually serving DHCP, and the leases. A
    disabled DHCP server is not an error: it means the zero check cannot run
    here, which is a different statement from "the zero check passed".
    """
    if not isinstance(status, dict):
        return False, ()

    enabled = bool(status.get("enabled"))
    leases: list[Lease] = []
    for key, static in (("leases", False), ("static_leases", True)):
        for raw in status.get(key) or ():
            if not isinstance(raw, dict):
                continue
            mac, ip = raw.get("mac"), raw.get("ip")
            if not mac or not ip:
                continue
            leases.append(
                Lease(
                    mac=str(mac).lower(),
                    ip=str(ip),
                    hostname=raw.get("hostname") or None,
                    static=static,
                )
            )

    return (enabled or bool(leases)), tuple(leases)


def run_zero_check(
    observations: Sequence[Observation],
    leases: Sequence[Lease],
    dhcp_available: bool,
) -> ZeroCheck:
    """Compare who asked the resolver against who holds a lease.

    The delta on one side is a device with a hardcoded resolver: the blind
    spot of the tool itself. On the other, a host the registry cannot explain.
    """
    if not dhcp_available:
        return ZeroCheck(dhcp_available=False)

    seen = {observation.client for observation in observations}
    leased = {lease.ip for lease in leases}

    return ZeroCheck(
        dhcp_available=True,
        silent_leases=tuple(sorted((l for l in leases if l.ip not in seen), key=lambda l: l.ip)),
        unleased_clients=tuple(sorted(seen - leased)),
    )


def parse_clients(payload: Any) -> dict[str, str]:
    """Names AdGuard has been given for its clients, by identifier."""
    names: dict[str, str] = {}
    if not isinstance(payload, dict):
        return names
    for group in ("clients", "auto_clients"):
        for raw in payload.get(group) or ():
            if not isinstance(raw, dict):
                continue
            name = raw.get("name")
            if not name:
                continue
            for identifier in raw.get("ids") or ():
                names[str(identifier)] = str(name)
            if raw.get("ip"):
                names[str(raw["ip"])] = str(name)
    return names


def _earlier(a: str, b: str) -> str:
    pa, pb = parse_time(a), parse_time(b)
    if pa is None:
        return b
    if pb is None:
        return a
    return a if pa <= pb else b


def _later(a: str, b: str) -> str:
    pa, pb = parse_time(a), parse_time(b)
    if pa is None:
        return b
    if pb is None:
        return a
    return a if pa >= pb else b
