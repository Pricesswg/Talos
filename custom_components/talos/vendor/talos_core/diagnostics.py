"""One-shot diagnostics: what is loading the system, measured on demand.

This is a different kind of evidence from the scan and is kept apart from it.
The scan is passive and periodic, and every row carries a proof that is
declared or observed. A diagnostic run is something the user starts, it lasts
about a minute, and what it produces was measured at that moment: a rate, a
count in a log, a connection time. It contributes to no posture check.

Three measures, all attributable to a config entry:

* churn: state changes per integration over the window. What writes four
  hundred states a minute is what fills the recorder and keeps the loop busy.
* blocking calls: Home Assistant logs every call that blocked the event
  loop, with the integration that made it. Counting those is the most direct
  signal of "this thing makes everything slow".
* reachability: a TCP connect to each endpoint the config entries declare,
  timed. Only to hosts the user configured, only on the port they wrote,
  never ICMP and never a sweep. That is the line between checking the broker
  answers and scanning the network, and this stays on the right side of it.

The pure parts live here so they can be tested; the parts that need Home
Assistant live in the integration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

# The window is bounded so a run cannot become monitoring by accident.
MIN_WINDOW = 10
MAX_WINDOW = 180
DEFAULT_WINDOW = 60

# How Home Assistant names the culprit in a blocking-call warning. The named
# form is the reliable one; the path form catches older builds and the cases
# where the name is missing.
_BLOCKING_LINE = re.compile(r"Detected blocking call", re.IGNORECASE)
_BY_INTEGRATION = re.compile(r"by (?:custom )?integration '(?P<domain>[\w.]+)'")
_BY_PATH = re.compile(
    r"(?:custom_components|homeassistant/components)/(?P<domain>[\w]+)/"
)
_TIMESTAMP = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


@dataclass(frozen=True, slots=True)
class Churn:
    """State changes attributed to one config entry over the window."""

    entry_id: str
    changes: int
    entities: int
    per_minute: float
    top_entities: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "changes": self.changes,
            "entities": self.entities,
            "per_minute": round(self.per_minute, 1),
            "top_entities": [list(item) for item in self.top_entities],
        }


@dataclass(frozen=True, slots=True)
class BlockingCall:
    """Blocking-call warnings the log attributes to one integration domain."""

    domain: str
    count: int
    last_seen: str | None
    sample: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "count": self.count,
            "last_seen": self.last_seen,
            "sample": self.sample,
        }


@dataclass(frozen=True, slots=True)
class Reach:
    """One timed connection to a declared endpoint."""

    entry_id: str
    host: str
    port: int
    reachable: bool
    latency_ms: float | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "host": self.host,
            "port": self.port,
            "reachable": self.reachable,
            "latency_ms": None if self.latency_ms is None else round(self.latency_ms, 1),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AddonUsage:
    """One add-on's share of the machine, over the window.

    CPU and memory are what the Supervisor reports at the moment of the
    second sample. Network is a rate: the Supervisor hands out byte counters
    that grow since the container started, and a counter says nothing about
    now, so the two samples at either end of the window are subtracted and
    divided by the seconds between them. That is the only way "who is using
    the bandwidth" can be answered honestly from what the Supervisor gives.
    """

    slug: str
    name: str
    state: str
    cpu_percent: float | None = None
    memory_bytes: int | None = None
    memory_limit: int | None = None
    memory_percent: float | None = None
    rx_bytes_per_s: float | None = None
    tx_bytes_per_s: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "state": self.state,
            "cpu_percent": _round(self.cpu_percent),
            "memory_bytes": self.memory_bytes,
            "memory_limit": self.memory_limit,
            "memory_percent": _round(self.memory_percent),
            "rx_bytes_per_s": _round(self.rx_bytes_per_s),
            "tx_bytes_per_s": _round(self.tx_bytes_per_s),
        }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def parse_addon_stats(payload: Any) -> dict[str, Any]:
    """The numbers from one `/addons/<slug>/stats` answer, or nothing.

    The Supervisor wraps its answer in `{"result": "ok", "data": {...}}` and
    the numbers are in `data`; a bare dict is accepted too. Anything else is
    an answer to a question that was not asked, and yields no numbers rather
    than a guess.
    """
    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(data, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("cpu_percent", "memory_usage", "memory_limit", "memory_percent", "network_rx", "network_tx"):
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key] = value
    return out


def addon_usage(
    slug: str,
    name: str,
    state: str,
    first: dict[str, Any],
    second: dict[str, Any],
    seconds: float,
) -> AddonUsage:
    """Combine the two samples into one row. Rates come from the difference;
    a counter that went down, which a restart does, yields no rate rather
    than a negative one."""
    seconds = max(float(seconds), 1.0)

    def rate(key: str) -> float | None:
        before, after = first.get(key), second.get(key)
        if before is None or after is None or after < before:
            return None
        return (after - before) / seconds

    return AddonUsage(
        slug=slug,
        name=name,
        state=state,
        cpu_percent=second.get("cpu_percent"),
        memory_bytes=second.get("memory_usage"),
        memory_limit=second.get("memory_limit"),
        memory_percent=second.get("memory_percent"),
        rx_bytes_per_s=rate("network_rx"),
        tx_bytes_per_s=rate("network_tx"),
    )


def rank_addons(rows: Iterable[AddonUsage]) -> list[AddonUsage]:
    """Busiest first: by network, then CPU, then memory. A stopped add-on
    has no numbers and goes last, still listed so the picture is complete."""

    def key(row: AddonUsage) -> tuple[float, float, float, str]:
        network = (row.rx_bytes_per_s or 0) + (row.tx_bytes_per_s or 0)
        return (-network, -(row.cpu_percent or 0), -(row.memory_bytes or 0), row.name)

    return sorted(rows, key=key)


@dataclass(frozen=True, slots=True)
class Slice:
    """One wedge of a pie: who, how much, and the share of the whole."""

    slug: str
    name: str
    value: float
    percent: float

    def to_dict(self) -> dict[str, Any]:
        return {"slug": self.slug, "name": self.name, "value": round(self.value, 1), "percent": round(self.percent, 1)}


def resource_shares(
    rows: Iterable[AddonUsage],
    cpu_count: int | None,
    memory_total: int | None,
) -> dict[str, list[Slice]]:
    """The three pies.

    CPU and memory have a whole to be a share of, so each gets a remainder
    wedge, `other`, for what nothing measured is using: idle CPU, and memory
    held by the host and by whatever is not a container. The Supervisor's
    CPU figure is relative to one core, so on four cores an add-on can report
    250 and the wedges would not close; dividing by the core count makes it
    a share of the machine. Network has no whole. Nobody knows what the link
    could carry, so that pie is the split among what was measured, and the
    label says so.
    """
    rows = [row for row in rows if row.state == "started"]

    cpu: list[Slice] = []
    if cpu_count and cpu_count > 0:
        capacity = 100.0 * cpu_count
        used = 0.0
        for row in rows:
            if row.cpu_percent is None:
                continue
            share = min(row.cpu_percent, capacity) / capacity * 100
            cpu.append(Slice(row.slug, row.name, row.cpu_percent, share))
            used += share
        cpu.sort(key=lambda s: -s.percent)
        if used < 100:
            cpu.append(Slice("other", "other", 0.0, 100 - used))

    memory: list[Slice] = []
    if memory_total and memory_total > 0:
        used_bytes = 0
        for row in rows:
            if row.memory_bytes is None:
                continue
            memory.append(Slice(row.slug, row.name, float(row.memory_bytes), row.memory_bytes / memory_total * 100))
            used_bytes += row.memory_bytes
        memory.sort(key=lambda s: -s.percent)
        if used_bytes < memory_total:
            memory.append(Slice("other", "other", float(memory_total - used_bytes), (memory_total - used_bytes) / memory_total * 100))

    network: list[Slice] = []
    total_rate = sum((row.rx_bytes_per_s or 0) + (row.tx_bytes_per_s or 0) for row in rows)
    if total_rate > 0:
        for row in rows:
            rate = (row.rx_bytes_per_s or 0) + (row.tx_bytes_per_s or 0)
            if rate > 0:
                network.append(Slice(row.slug, row.name, rate, rate / total_rate * 100))
        network.sort(key=lambda s: -s.percent)

    return {"cpu": cpu, "memory": memory, "network": network}


@dataclass(slots=True)
class DiagnosticRun:
    started_at: str
    finished_at: str | None = None
    window_seconds: int = DEFAULT_WINDOW
    total_changes: int = 0
    unattributed_changes: int = 0
    churn: list[Churn] = field(default_factory=list)
    blocking: list[BlockingCall] = field(default_factory=list)
    reachability: list[Reach] = field(default_factory=list)
    # Per add-on, where the Supervisor is there to ask. Home Assistant Core
    # itself is included as a row so the add-ons have something to be
    # compared against.
    addons: list[AddonUsage] = field(default_factory=list)
    # The wholes the shares are of. None when there was no way to know.
    cpu_count: int | None = None
    memory_total: int | None = None
    # What could not be measured and why, in the same spirit as the scan's
    # unverified list: an empty section and a section that was not looked at
    # are different things.
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "window_seconds": self.window_seconds,
            "total_changes": self.total_changes,
            "unattributed_changes": self.unattributed_changes,
            "churn": [item.to_dict() for item in self.churn],
            "blocking": [item.to_dict() for item in self.blocking],
            "reachability": [item.to_dict() for item in self.reachability],
            "addons": [item.to_dict() for item in self.addons],
            "cpu_count": self.cpu_count,
            "memory_total": self.memory_total,
            "shares": {
                key: [item.to_dict() for item in slices]
                for key, slices in resource_shares(self.addons, self.cpu_count, self.memory_total).items()
            },
            "notes": list(self.notes),
        }


def clamp_window(value: Any) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return DEFAULT_WINDOW
    return max(MIN_WINDOW, min(MAX_WINDOW, seconds))


def attribute_churn(
    changes: Iterable[str],
    entry_of: dict[str, str | None],
    window_seconds: int,
    top: int = 5,
) -> tuple[list[Churn], int, int]:
    """Turn a stream of changed entity ids into per-entry rates.

    Returns the rows, busiest first, the total, and the number of changes
    that belong to no config entry, which are YAML entities, helpers and the
    like. Those are counted rather than dropped so the total adds up.
    """
    per_entity: dict[str, int] = {}
    for entity_id in changes:
        per_entity[entity_id] = per_entity.get(entity_id, 0) + 1

    per_entry: dict[str, dict[str, int]] = {}
    unattributed = 0
    for entity_id, count in per_entity.items():
        entry_id = entry_of.get(entity_id)
        if not entry_id:
            unattributed += count
            continue
        per_entry.setdefault(entry_id, {})[entity_id] = count

    minutes = max(window_seconds, 1) / 60
    rows = [
        Churn(
            entry_id=entry_id,
            changes=sum(entities.values()),
            entities=len(entities),
            per_minute=sum(entities.values()) / minutes,
            top_entities=tuple(
                sorted(entities.items(), key=lambda item: (-item[1], item[0]))[:top]
            ),
        )
        for entry_id, entities in per_entry.items()
    ]
    rows.sort(key=lambda row: (-row.changes, row.entry_id))
    return rows, sum(per_entity.values()), unattributed


def parse_blocking_calls(log_text: str) -> list[BlockingCall]:
    """Count the loop-blocking warnings in a log, by the integration named.

    A line that names no integration at all is counted under `unknown`
    rather than dropped: the loop was blocked either way, and hiding the
    line because the culprit is unclear would understate the total.
    """
    found: dict[str, dict[str, Any]] = {}
    for line in log_text.splitlines():
        if not _BLOCKING_LINE.search(line):
            continue
        named = _BY_INTEGRATION.search(line) or _BY_PATH.search(line)
        domain = named.group("domain") if named else "unknown"
        stamp = _TIMESTAMP.match(line)
        record = found.setdefault(domain, {"count": 0, "last_seen": None, "sample": ""})
        record["count"] += 1
        if stamp:
            record["last_seen"] = stamp.group("ts")
        record["sample"] = _trim(line)
    rows = [
        BlockingCall(domain=domain, count=r["count"], last_seen=r["last_seen"], sample=r["sample"])
        for domain, r in found.items()
    ]
    rows.sort(key=lambda row: (-row.count, row.domain))
    return rows


def _trim(line: str, limit: int = 240) -> str:
    """The message without the timestamp and logger prefix, cut to a size a
    panel row can hold. Enough to recognise the call, not a stack trace."""
    text = line.strip()
    marker = text.find("Detected blocking call")
    if marker > 0:
        text = text[marker:]
    return text if len(text) <= limit else text[: limit - 1] + "…"


def declared_targets(scan: Any) -> list[tuple[str, str, int]]:
    """The (entry, host, port) triples the config entries declare.

    Only these are connected to. An endpoint without a port is skipped rather
    than guessed at: the point is to check what the user wrote, not to probe
    for what might answer.
    """
    seen: set[tuple[str, int]] = set()
    targets: list[tuple[str, str, int]] = []
    for conduit in scan.conduits:
        if conduit.evidence != "declared" or conduit.source.kind != "integration":
            continue
        if not conduit.port:
            continue
        destination = scan.destination(conduit.destination_id)
        if destination is None:
            continue
        key = (destination.fqdn, int(conduit.port))
        if key in seen:
            continue
        seen.add(key)
        targets.append((conduit.source.id, destination.fqdn, int(conduit.port)))
    return targets
