"""Persistence for the incremental collector.

A dedicated SQLite file, never the recorder's database: Talos writes on its
own schedule, prunes on its own policy, and a corrupted history here must
never be able to take somebody's energy dashboard with it.

**Why anything is stored at all.** AdGuard's query log is a rolling buffer
with limited retention. If the running totals are not kept on this side, a
device that phoned home four thousand times last week reads as a handful of
queries today. The observations table *is* the history — `first_seen` answers
"since when has this been happening", which is the question a scan snapshot
would otherwise be kept around to answer.

**Why retention is not optional.** One unique row per client-and-name pair
grows without bound: a browser on the network can invent thousands of domains
in a week. Two limits, both enforced on every save, because either one alone
fails: a time window does not bound a busy network, and a row cap alone keeps
stale rows forever while dropping fresh ones. Space is reclaimed for real —
SQLite does not return pages to the filesystem on DELETE, so the database is
opened in incremental auto-vacuum and stepped after each prune.

Every call blocks. Inside Home Assistant, run them through
`hass.async_add_executor_job` and never on the event loop.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .model import Scan
from .observed.mapping import Lease, Observation, parse_time

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """What is kept, and for how long. Enforced on every save."""

    # Drop an observation that has not been seen for this long. A device
    # replaced six months ago should stop shaping today's report.
    observation_days: int = 90

    # Hard ceiling on rows, oldest last_seen dropped first. This is the limit
    # that actually bounds the file: the time window does not, on a network
    # with a browser on it.
    max_observations: int = 20_000

    # Scan snapshots are a convenience for loading the panel without
    # recomputing, not the historical record — that is the observations
    # table. A handful is enough to diff against; more is just weight.
    scan_history: int = 5

    # Reclaiming pages costs I/O, so it is not done on every prune.
    vacuum_every: int = 20

    def __post_init__(self) -> None:
        for name in ("observation_days", "max_observations", "scan_history", "vacuum_every"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer, got {value!r}")

    def to_dict(self) -> dict[str, int]:
        return {
            "observation_days": self.observation_days,
            "max_observations": self.max_observations,
            "scan_history": self.scan_history,
            "vacuum_every": self.vacuum_every,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> RetentionPolicy:
        raw = raw or {}
        default = cls()
        return cls(
            observation_days=int(raw.get("observation_days", default.observation_days)),
            max_observations=int(raw.get("max_observations", default.max_observations)),
            scan_history=int(raw.get("scan_history", default.scan_history)),
            vacuum_every=int(raw.get("vacuum_every", default.vacuum_every)),
        )


@dataclass(frozen=True, slots=True)
class PruneReport:
    """What retention actually removed. Reported, never silent."""

    observations_expired: int = 0
    observations_over_cap: int = 0
    scans_removed: int = 0
    vacuumed: bool = False

    @property
    def total_removed(self) -> int:
        return self.observations_expired + self.observations_over_cap + self.scans_removed


@dataclass(frozen=True, slots=True)
class StoreStats:
    observations: int = 0
    leases: int = 0
    scans: int = 0
    oldest_observation: str | None = None
    bytes_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations": self.observations,
            "leases": self.leases,
            "scans": self.scans,
            "oldest_observation": self.oldest_observation,
            "bytes_used": self.bytes_used,
        }


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per client-and-name pair. The epoch columns exist because the
-- stamps are RFC 3339 with offsets: comparing those as text would order
-- "+02:00" against "Z" incorrectly, and retention would then drop the wrong
-- rows.
CREATE TABLE IF NOT EXISTS observations (
    client        TEXT NOT NULL,
    fqdn          TEXT NOT NULL,
    count         INTEGER NOT NULL DEFAULT 0,
    blocked       INTEGER NOT NULL DEFAULT 0,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    first_seen_ts REAL,
    last_seen_ts  REAL,
    PRIMARY KEY (client, fqdn)
);
CREATE INDEX IF NOT EXISTS observations_last_seen ON observations (last_seen_ts);

CREATE TABLE IF NOT EXISTS leases (
    mac       TEXT PRIMARY KEY,
    ip        TEXT NOT NULL,
    hostname  TEXT,
    static    INTEGER NOT NULL DEFAULT 0,
    seen_ts   REAL
);

CREATE TABLE IF NOT EXISTS scans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    document     TEXT NOT NULL
);
"""


class TalosStore:
    """Blocking SQLite store for cursors, observations, leases and snapshots."""

    def __init__(
        self,
        path: str | Path,
        policy: RetentionPolicy | None = None,
    ) -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)

        # Home Assistant runs executor jobs on a thread pool, so the same
        # store is legitimately touched from several threads. The connection
        # allows it and the lock keeps the writes serialised.
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

        # A failure past this point must not leave the file handle open: the
        # caller gets an exception and has nothing left to call close() on.
        try:
            self._configure()
            self._prune_counter = 0
            self.policy = self._install_policy(policy)
        except Exception:
            self._connection.close()
            raise

    # ── lifecycle ─────────────────────────────────────────────────────────

    def __enter__(self) -> TalosStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _configure(self) -> None:
        with self._lock:
            # Readers (the panel) must not block on the writer (the poll).
            self._connection.execute("PRAGMA journal_mode=WAL")
            # DELETE alone never shrinks the file; incremental auto-vacuum is
            # what makes the retention policy show up on disk.
            self._connection.execute("PRAGMA auto_vacuum=INCREMENTAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.executescript(_SCHEMA)
            self._migrate()
            self._connection.commit()

    def _migrate(self) -> None:
        current = self._get_meta("schema_version")
        if current is None:
            self._set_meta("schema_version", str(SCHEMA_VERSION))
            return
        version = int(current)
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"{self.path.name} was written by a newer Talos"
                f" (schema {version} > {SCHEMA_VERSION})"
            )
        # Future migrations step from `version` to SCHEMA_VERSION here.
        self._set_meta("schema_version", str(SCHEMA_VERSION))

    def _install_policy(self, policy: RetentionPolicy | None) -> RetentionPolicy:
        """The file carries its own policy, so a store opened by the CLI
        prunes the same way the integration does."""
        if policy is not None:
            self.set_policy(policy)
            return policy
        stored = self._get_meta("retention_policy")
        return RetentionPolicy.from_dict(json.loads(stored)) if stored else RetentionPolicy()

    def set_policy(self, policy: RetentionPolicy) -> None:
        with self._lock:
            self.policy = policy
            self._set_meta("retention_policy", json.dumps(policy.to_dict()))
            self._connection.commit()

    # ── cursor ────────────────────────────────────────────────────────────

    def get_cursor(self) -> str | None:
        return self._get_meta("querylog_cursor")

    def set_cursor(self, value: str | None) -> None:
        with self._lock:
            if value is None:
                self._connection.execute("DELETE FROM meta WHERE key = 'querylog_cursor'")
            else:
                self._set_meta("querylog_cursor", value)
            self._connection.commit()

    # ── observations ──────────────────────────────────────────────────────

    def load_observations(self) -> tuple[Observation, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT client, fqdn, count, blocked, first_seen, last_seen"
                " FROM observations ORDER BY count DESC, client, fqdn"
            ).fetchall()
        return tuple(
            Observation(
                client=row["client"],
                fqdn=row["fqdn"],
                count=row["count"],
                blocked=row["blocked"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
            )
            for row in rows
        )

    def save_observations(self, observations: Iterable[Observation]) -> None:
        payload = [
            (
                o.client,
                o.fqdn,
                o.count,
                o.blocked,
                o.first_seen,
                o.last_seen,
                _epoch(o.first_seen),
                _epoch(o.last_seen),
            )
            for o in observations
        ]
        if not payload:
            return
        with self._lock:
            self._connection.executemany(
                "INSERT INTO observations"
                " (client, fqdn, count, blocked, first_seen, last_seen,"
                "  first_seen_ts, last_seen_ts)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(client, fqdn) DO UPDATE SET"
                "  count = excluded.count,"
                "  blocked = excluded.blocked,"
                "  first_seen = excluded.first_seen,"
                "  last_seen = excluded.last_seen,"
                "  first_seen_ts = excluded.first_seen_ts,"
                "  last_seen_ts = excluded.last_seen_ts",
                payload,
            )
            self._connection.commit()

    # ── leases ────────────────────────────────────────────────────────────

    def save_leases(self, leases: Iterable[Lease], seen_at: datetime | None = None) -> None:
        stamp = (seen_at or datetime.now(timezone.utc)).timestamp()
        payload = [(l.mac, l.ip, l.hostname, int(l.static), stamp) for l in leases]
        if not payload:
            return
        with self._lock:
            self._connection.executemany(
                "INSERT INTO leases (mac, ip, hostname, static, seen_ts)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(mac) DO UPDATE SET"
                "  ip = excluded.ip, hostname = excluded.hostname,"
                "  static = excluded.static, seen_ts = excluded.seen_ts",
                payload,
            )
            self._connection.commit()

    def load_leases(self) -> tuple[Lease, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT mac, ip, hostname, static FROM leases ORDER BY ip"
            ).fetchall()
        return tuple(
            Lease(
                mac=row["mac"],
                ip=row["ip"],
                hostname=row["hostname"],
                static=bool(row["static"]),
            )
            for row in rows
        )

    # ── scan snapshots ────────────────────────────────────────────────────

    def save_scan(self, scan: Scan) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO scans (generated_at, document) VALUES (?, ?)",
                (scan.generated_at, json.dumps(scan.to_dict(), separators=(",", ":"))),
            )
            self._connection.commit()

    def latest_scan(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM scans ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return json.loads(row["document"]) if row else None

    # ── retention ─────────────────────────────────────────────────────────

    def prune(self, now: datetime | None = None) -> PruneReport:
        """Apply the policy. Called on every save, not on a separate schedule.

        A retention job that has to be scheduled is a retention job that can
        fail to be scheduled, and nobody notices until the disk fills.
        """
        moment = now or datetime.now(timezone.utc)
        horizon = (moment - timedelta(days=self.policy.observation_days)).timestamp()

        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM observations"
                " WHERE last_seen_ts IS NOT NULL AND last_seen_ts < ?",
                (horizon,),
            )
            expired = cursor.rowcount or 0

            # A row with an unparseable stamp has no age; it is bounded by the
            # cap below rather than deleted on a guess.
            cursor = self._connection.execute(
                "DELETE FROM observations WHERE rowid IN ("
                "  SELECT rowid FROM observations"
                "  ORDER BY last_seen_ts IS NULL DESC, last_seen_ts ASC"
                "  LIMIT MAX(0, (SELECT COUNT(*) FROM observations) - ?)"
                ")",
                (self.policy.max_observations,),
            )
            over_cap = cursor.rowcount or 0

            cursor = self._connection.execute(
                "DELETE FROM scans WHERE id NOT IN ("
                "  SELECT id FROM scans ORDER BY id DESC LIMIT ?"
                ")",
                (self.policy.scan_history,),
            )
            scans_removed = cursor.rowcount or 0

            self._connection.commit()

            self._prune_counter += 1
            vacuumed = self._prune_counter % self.policy.vacuum_every == 0
            if vacuumed:
                self._connection.execute("PRAGMA incremental_vacuum")
                self._connection.commit()

        return PruneReport(
            observations_expired=expired,
            observations_over_cap=over_cap,
            scans_removed=scans_removed,
            vacuumed=vacuumed,
        )

    def stats(self) -> StoreStats:
        with self._lock:
            observations = self._scalar("SELECT COUNT(*) FROM observations")
            leases = self._scalar("SELECT COUNT(*) FROM leases")
            scans = self._scalar("SELECT COUNT(*) FROM scans")
            oldest = self._connection.execute(
                "SELECT first_seen FROM observations"
                " WHERE first_seen_ts IS NOT NULL"
                " ORDER BY first_seen_ts ASC LIMIT 1"
            ).fetchone()
            page_count = self._scalar("PRAGMA page_count")
            page_size = self._scalar("PRAGMA page_size")

        return StoreStats(
            observations=observations,
            leases=leases,
            scans=scans,
            oldest_observation=oldest["first_seen"] if oldest else None,
            bytes_used=page_count * page_size,
        )

    # ── internals ─────────────────────────────────────────────────────────

    def _scalar(self, sql: str) -> int:
        row = self._connection.execute(sql).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def _get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self._connection.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def _epoch(stamp: str) -> float | None:
    parsed = parse_time(stamp)
    return parsed.timestamp() if parsed else None


def merge_policy(base: RetentionPolicy, **overrides: int) -> RetentionPolicy:
    """Apply a partial override, validating the result."""
    return replace(base, **{k: v for k, v in overrides.items() if v is not None})
