"""Query log records -> aggregated observations, plus the zero check.

Pure functions over plain dicts, so the aggregation and the zero check can be
tested against recorded AdGuard payloads with no appliance in the loop.

The query log says **with whom** a host spoke. It does not say what was said,
nor how much: nothing derived here may be phrased as data leaving the house.
"""

from __future__ import annotations

import ipaddress

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence

# AdGuard reports why a query was answered the way it was. Every reason that
# starts with "Filtered" means a filter intervened; "NotFilteredWhiteList" is
# an explicit allow and deliberately does not match.


@dataclass(frozen=True, slots=True)
class QueryRecord:
    """One query as every resolver reports it, once its own shape is gone.

    Each collector translates its appliance's records into these, and the
    aggregation below never sees the appliance. `time` is RFC 3339 text, the
    form AdGuard already uses; Pi-hole's Unix seconds are converted on the way
    in, so the cursor and the totals compare the same way for both."""

    client: str
    fqdn: str
    time: str
    blocked: bool = False


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
    # "dhcp" is a lease the resolver handed out itself. "network" is a pair
    # Pi-hole saw on the wire, from ARP and neighbour tables, which it keeps
    # even when the router does the DHCP: the same join, a different witness,
    # and the report names which one carried it.
    origin: str = "dhcp"
    # When the witness last saw this pair, RFC 3339, where it says. A pair
    # last seen months ago belongs to something gone, not to something silent.
    seen_at: str | None = None
    # Whether the witness counts queries from this device: Pi-hole's network
    # table carries a per device total over its whole history, which answers
    # the silence question without a scan of the log. None means unknown.
    queried: bool | None = None


@dataclass(frozen=True, slots=True)
class WalkWindow:
    """How much of the log one poll actually read.

    A poll walks newest first under a page budget, so on a busy resolver it
    covers hours where the log holds days. An absence inside that window is
    not an absence from the log, and the report must be able to say which."""

    entries: int = 0
    newest: str | None = None
    oldest: str | None = None
    # True when the page budget ran out before the previous cursor or the end
    # of the log was reached: the window is shorter than what is retained.
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class Confirmation:
    """What the resolver answered about one silent host, and when.

    Kept in the store between polls: a targeted search costs the resolver a
    scan of its log file, so a host confirmed absent is not asked again for a
    day, and the hosts never asked go first when the per-poll budget runs
    out. A host that starts querying shows up in the walk and stops being a
    candidate regardless of what is remembered here."""

    ip: str
    # True: the log holds a query from it. False: it holds none. None: the
    # question could not be answered last time.
    answer: bool | None
    asked_at: str


@dataclass(frozen=True, slots=True)
class ZeroCheck:
    """The tool's own blind spots, measured rather than assumed.

    Runs continuously, not once: a device that arrives tomorrow with a
    hardcoded resolver has to surface on its own.

    A lease with no observation is a candidate, never a verdict, until the
    resolver has been asked about that one host over its whole retained log.
    `silent_leases` holds only the confirmed ones: absent from the walked
    window and absent from the full log. The other outcomes are kept apart
    because each means something different, and none of them is a finding:
    `outside_window` hosts did query, only earlier than this poll read;
    `unlogged_leases` are hosts the resolver is configured never to log;
    `unconfirmed` are candidates the confirmation could not settle.
    """

    dhcp_available: bool
    silent_leases: tuple[Lease, ...] = ()
    unleased_clients: tuple[str, ...] = ()
    outside_window: tuple[Lease, ...] = ()
    unlogged_leases: tuple[Lease, ...] = ()
    unconfirmed: tuple[Lease, ...] = ()
    window: WalkWindow | None = None
    # Whether the targeted confirmation ran at all. False on a source that
    # cannot search its log, or when every request for it failed.
    confirmed: bool = False
    # Candidates that were not asked this poll because the budget ran out.
    # Kept apart from the ones that were asked and got no answer.
    not_asked: tuple[Lease, ...] = ()
    # Pairs the witness last saw before the log's retention began: gone, as
    # far as the log can tell, and never a candidate.
    stale_pairs: tuple[Lease, ...] = ()
    # How far back the resolver keeps its log, in seconds, when it says.
    retention_seconds: float | None = None

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
    # Identifiers (addresses, MACs, CIDRs) the resolver is configured to keep
    # out of its log. Nothing from them can be observed, by the operator's
    # own choice, and the report has to say so rather than call them silent.
    unlogged: tuple[str, ...] = ()
    # A resolver-wide limit on what the log shows, when one is set: Pi-hole's
    # privacy level hides names, or names and clients, from everyone.
    log_hidden: str | None = None
    # The answers gathered this poll, for the store to remember.
    confirmations: tuple[Confirmation, ...] = ()


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
    records: Iterable[QueryRecord],
    previous: Iterable[Observation] = (),
) -> tuple[Observation, ...]:
    """Fold query records into per client-and-name totals.

    `previous` carries what earlier polls already counted: a resolver's
    retention is limited and the log rolls over, so the running total has to
    live here rather than being re-read from the appliance.
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
        client = record.client
        fqdn = record.fqdn.rstrip(".").lower()
        if not client or not fqdn:
            continue

        stamp = record.time
        if parse_time(stamp) is None:
            continue

        blocked = record.blocked
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
    """Read AdGuard's `/control/dhcp/status`.

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


def is_unlogged(lease: Lease, unlogged: Sequence[str]) -> bool:
    """Whether the resolver keeps this host out of its log. An identifier can
    be an address, a MAC or a CIDR; AdGuard accepts all three on a client."""
    if not unlogged:
        return False
    mac = normalise_identifier(lease.mac)
    for identifier in unlogged:
        if identifier == lease.ip or identifier == mac:
            return True
        if "/" in identifier:
            try:
                if ipaddress.ip_address(lease.ip) in ipaddress.ip_network(identifier, strict=False):
                    return True
            except ValueError:
                continue
    return False


# Placeholder addresses a resolver writes when it hides who asked.
HIDDEN_CLIENTS = frozenset({"0.0.0.0", "::", "hidden"})


def is_anonymised(client: str) -> bool:
    """AdGuard's anonymised client: the last two IPv4 octets zeroed, or an
    IPv6 cut to its prefix. A real host at x.y.0.0 is a network address and
    no client, so nothing true is lost."""
    return client.endswith(".0.0") or client.endswith("::")


def run_zero_check(
    observations: Sequence[Observation],
    leases: Sequence[Lease],
    dhcp_available: bool,
    unlogged: Sequence[str] = (),
    window: WalkWindow | None = None,
    retention_seconds: float | None = None,
    now: datetime | None = None,
) -> ZeroCheck:
    """Compare who asked the resolver against who holds a lease.

    The delta on one side is a device with a hardcoded resolver: the blind
    spot of the tool itself. On the other, a host the registry cannot explain.

    What comes out here is candidates: every lease with no observation lands
    in `unconfirmed`, minus the hosts the resolver never logs. The collector
    then asks the resolver about each candidate over its whole log and calls
    `settle` with the answers. A candidate is a finding only after that.
    """
    # `dhcp_available` reads as "an address table exists to compare against":
    # DHCP leases, or the network table a Pi-hole keeps from what it sees on
    # the wire. Without either there is nothing to hold the clients up to.
    if not dhcp_available:
        return ZeroCheck(dhcp_available=False, window=window, retention_seconds=retention_seconds)

    seen = {
        observation.client
        for observation in observations
        if observation.client not in HIDDEN_CLIENTS and not is_anonymised(observation.client)
    }
    leased = {lease.ip for lease in leases}

    # The device is the MAC, not the address. A MAC seen on any of its
    # addresses is using the resolver: its other addresses, an old IPv4 or
    # the IPv6 ones a network table lists, are not silent hosts.
    seen_macs = {lease.mac for lease in leases if lease.ip in seen}
    # A zero retention is a log that keeps nothing on disk, not a horizon at
    # this very moment: it cannot make every pair stale.
    horizon = None
    if retention_seconds and now is not None:
        horizon = now.timestamp() - retention_seconds
    # A witness that counts queries per device answers for its MAC outright.
    queried_macs = {lease.mac for lease in leases if lease.queried}
    candidates: list[Lease] = []
    stale: list[Lease] = []
    known_outside: list[Lease] = []
    for lease in sorted(leases, key=lambda l: l.ip):
        if lease.ip in seen or lease.mac in seen_macs:
            continue
        last = parse_time(lease.seen_at) if lease.seen_at else None
        if horizon is not None and last is not None and last.timestamp() < horizon:
            stale.append(lease)
            continue
        if lease.mac in queried_macs:
            known_outside.append(lease)
            continue
        candidates.append(lease)

    return ZeroCheck(
        dhcp_available=True,
        unleased_clients=tuple(sorted(seen - leased)),
        unlogged_leases=tuple(l for l in candidates if is_unlogged(l, unlogged)),
        unconfirmed=tuple(l for l in candidates if not is_unlogged(l, unlogged)),
        outside_window=tuple(known_outside),
        window=window,
        stale_pairs=tuple(stale),
        retention_seconds=retention_seconds,
    )


# A log kept for less than this cannot vouch for a device that phones home
# weekly: a "no" from it is pending, not a finding.
SILENCE_MIN_RETENTION_SECONDS = 7 * 86400

# A confirmed absence is trusted for this long before the host is asked
# about again. The walk still sees the host the moment it queries, so the
# only thing the interval buys is fewer log scans on the resolver. A
# question that got no answer is retried sooner, but not every poll: each
# retry costs the resolver a scan of its log.
CONFIRM_TTL_SECONDS = 24 * 3600
RETRY_TTL_SECONDS = 3600


def order_candidates(
    candidates: Sequence[Lease],
    remembered: dict[str, Confirmation],
    now: datetime,
    window: WalkWindow | None = None,
) -> tuple[list[Lease], dict[str, bool | None]]:
    """Which candidates to ask this poll, and which answers still hold.

    A host confirmed absent within the TTL is not asked again and its answer
    is reused, unless this poll's walk was cut short: then the log may hold
    a query the walk did not reach, and the memory is not trusted over it.
    The rest are ordered never-asked first, then by the time they were last
    asked, so a budget that cannot cover everyone rotates through the set
    across polls instead of asking the same hosts every time."""
    reuse: dict[str, bool | None] = {}
    to_ask: list[tuple[float, str, Lease]] = []
    truncated = bool(window and window.truncated)
    for lease in candidates:
        past = remembered.get(lease.ip)
        asked = parse_time(past.asked_at) if past else None
        if past is not None and asked is not None and not truncated:
            age = (now - asked).total_seconds()
            if past.answer is False and age < CONFIRM_TTL_SECONDS:
                reuse[lease.ip] = False
                continue
            if past.answer is None and age < RETRY_TTL_SECONDS:
                reuse[lease.ip] = None
                continue
        to_ask.append((asked.timestamp() if asked else float("-inf"), lease.ip, lease))
    to_ask.sort(key=lambda item: (item[0], item[1]))
    return [lease for _, _, lease in to_ask], reuse


def settle(
    zero: ZeroCheck,
    answers: dict[str, bool | None],
    not_asked: Sequence[Lease] = (),
) -> ZeroCheck:
    """Apply the targeted confirmation to the candidates.

    `answers` maps a candidate address to True when the resolver's full log
    holds at least one query from it, False when it holds none, None when the
    question could not be answered. Only False becomes a finding. Candidates
    in `not_asked` were left for a later poll and are reported as such.
    """
    skipped = {(lease.mac, lease.ip) for lease in not_asked}
    # A log too short to vouch for a weekly caller turns every no into pending.
    short_log = (
        zero.retention_seconds is not None and zero.retention_seconds < SILENCE_MIN_RETENTION_SECONDS
    )
    # Answers are per address; the verdict is per device. Any address that
    # answered yes makes the whole device seen; any that is unanswered or
    # unasked leaves it pending; only a device whose every address answered
    # no is silent.
    by_mac: dict[str, list[Lease]] = {}
    for lease in zero.unconfirmed:
        by_mac.setdefault(lease.mac, []).append(lease)
    silent = list(zero.silent_leases)
    outside = list(zero.outside_window)
    pending: list[Lease] = []
    waiting: list[Lease] = []
    for group in by_mac.values():
        verdicts = []
        for lease in group:
            if (lease.mac, lease.ip) in skipped:
                verdicts.append("waiting")
            else:
                answer = answers.get(lease.ip)
                verdicts.append("yes" if answer is True else "no" if answer is False else "pending")
        if "yes" in verdicts:
            outside.extend(group)
        elif all(v == "no" for v in verdicts):
            if short_log:
                pending.extend(group)
            else:
                silent.extend(group)
        elif "pending" in verdicts:
            pending.extend(group)
        else:
            waiting.extend(group)
    return ZeroCheck(
        dhcp_available=zero.dhcp_available,
        silent_leases=tuple(sorted(silent, key=lambda l: l.ip)),
        unleased_clients=zero.unleased_clients,
        outside_window=tuple(sorted(outside, key=lambda l: l.ip)),
        unlogged_leases=zero.unlogged_leases,
        unconfirmed=tuple(pending),
        window=zero.window,
        confirmed=any(answer is not None for answer in answers.values()),
        not_asked=tuple(waiting),
        stale_pairs=zero.stale_pairs,
        retention_seconds=zero.retention_seconds,
    )


def parse_unlogged(payload: Any) -> tuple[str, ...]:
    """Identifiers of AdGuard clients flagged `ignore_querylog`.

    Such a client is counted in statistics and never written to the query
    log: an operator sets it on the chattiest devices to keep the log
    readable. Absence from the log is then a configuration, not a behaviour,
    and it must never be read as bypassing the resolver."""
    found: list[str] = []
    if not isinstance(payload, dict):
        return ()
    for raw in payload.get("clients") or ():
        if not isinstance(raw, dict) or not raw.get("ignore_querylog"):
            continue
        for identifier in raw.get("ids") or ():
            if identifier:
                found.append(normalise_identifier(str(identifier)))
    return tuple(sorted(set(found)))


def normalise_identifier(value: str) -> str:
    """Lowercase, and a MAC in any of AdGuard's accepted spellings, with
    hyphens or dots, in the colon form the leases carry."""
    text = value.strip().lower()
    compact = text.replace("-", "").replace(".", "").replace(":", "")
    if len(compact) == 12 and all(c in "0123456789abcdef" for c in compact):
        return ":".join(compact[i : i + 2] for i in range(0, 12, 2))
    return text


def parse_clients(payload: Any) -> dict[str, str]:
    """Names AdGuard has been given for its clients, by identifier, from
    `/control/clients`."""
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
