"""Sizing the store from one answer: how long to keep the data.

The three knobs the store enforces, the age of an observation, the ceiling
on rows and the number of scan snapshots, are not what a person thinks in.
They think in days. Everything else follows from the days and from the rate
the install actually produces, which the store already knows: how many
observations it holds and how old the oldest one is. A ceiling that is not
derived from the rate is either so high it never bounds anything or so low it
silently cuts the window short, and the second failure is invisible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Room above the measured rate, so a week that is busier than the last does
# not start trimming the window before its time.
HEADROOM = 1.25
# The rate assumed before there is any history to measure: a modest home
# network. Replaced by the measured figure as soon as there is one.
DEFAULT_RATE_PER_DAY = 400.0
# Fewer observations than this cannot give a rate worth trusting.
MIN_SAMPLE = 200
# Snapshots are heavy documents kept for the panel; the long history lives
# in the compact snapshot rows. This caps the documents whatever the window.
MAX_SCAN_DOCUMENTS = 48


def snapshot_of(scan: Any, derived: Any) -> dict[str, Any]:
    """One compact row per scan: the numbers the charts draw.

    The scan document is kept for the panel and pruned early because it is
    heavy. This row is what the long history is made of: a few counters,
    small enough to keep for the whole retention window, and enough to say
    whether things are getting better.
    """
    checks = derived.checks
    autonomy = derived.autonomy
    exposure = derived.exposure
    correlation = scan.correlation
    unclassified = sum(1 for d in scan.destinations if d.kind == "unknown")
    return {
        "generated_at": scan.generated_at,
        "failed_high": len(checks.failed_by_severity("high")),
        "failed_medium": len(checks.failed_by_severity("medium")),
        "failed_low": len(checks.failed_by_severity("low")),
        "passed": len(checks.passed),
        "partial": len(checks.partial),
        "unverified": sum(1 for c in checks.unverified if str(c.id).startswith("chk.")),
        "entities_total": autonomy.entities_total,
        "entities_local": autonomy.entities_local,
        "entities_cloud": autonomy.entities_cloud,
        "entities_unavailable": autonomy.entities_unavailable,
        "devices_total": exposure.devices_total,
        "devices_exposed": len(exposure.devices_direct),
        "local_egress": len(derived.matrix.local_egress),
        "unclassified": unclassified,
        "devices_correlated": correlation.devices_correlated,
        "devices_scanned": correlation.devices_total,
    }


@dataclass(frozen=True, slots=True)
class Sizing:
    retention_days: int
    observation_days: int
    max_observations: int
    scan_history: int
    rate_per_day: float
    rate_measured: bool
    estimate_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "retention_days": self.retention_days,
            "observation_days": self.observation_days,
            "max_observations": self.max_observations,
            "scan_history": self.scan_history,
            "rate_per_day": round(self.rate_per_day, 1),
            "rate_measured": self.rate_measured,
            "estimate_bytes": self.estimate_bytes,
        }


def measured_rate(observations: int, oldest: str | None, now: datetime | None = None) -> float | None:
    """Observations per day, from what the store holds and how old it is.

    None when there is not enough to measure: a fresh install, or a window
    shorter than a day, would give a number that means nothing.
    """
    if observations < MIN_SAMPLE or not oldest:
        return None
    try:
        start = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
    except ValueError:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    days = (now - start).total_seconds() / 86400
    if days < 1:
        return None
    return observations / days


def size_for(
    retention_days: int,
    interval_minutes: int,
    observations: int,
    oldest: str | None,
    bytes_used: int = 0,
    bounds: dict[str, tuple[int, int]] | None = None,
    now: datetime | None = None,
) -> Sizing:
    """The three knobs, from the days and the measured rate.

    Bounded to what the store accepts, and an estimate of the file size from
    the bytes each observation costs today. The estimate is labelled as one:
    it is a projection of the current ratio, not a promise.
    """
    bounds = bounds or {}
    lo_days, hi_days = bounds.get("observation_days", (1, 3650))
    lo_rows, hi_rows = bounds.get("max_observations", (500, 500_000))
    lo_scans, hi_scans = bounds.get("scan_history", (1, 200))

    days = max(lo_days, min(hi_days, int(retention_days)))
    rate = measured_rate(observations, oldest, now)
    measured = rate is not None
    rate = rate if measured else DEFAULT_RATE_PER_DAY

    rows = int(math.ceil(rate * days * HEADROOM))
    rows = max(lo_rows, min(hi_rows, rows))

    per_day = 1440 / max(int(interval_minutes), 1)
    scans = int(math.ceil(per_day * days))
    scans = max(lo_scans, min(hi_scans, min(scans, MAX_SCAN_DOCUMENTS)))

    estimate = None
    if observations > 0 and bytes_used > 0:
        estimate = int(bytes_used / observations * rows)

    return Sizing(
        retention_days=days,
        observation_days=days,
        max_observations=rows,
        scan_history=scans,
        rate_per_day=rate,
        rate_measured=measured,
        estimate_bytes=estimate,
    )
