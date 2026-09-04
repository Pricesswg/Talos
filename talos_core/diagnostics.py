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
