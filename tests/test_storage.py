"""Storage tests, with retention treated as a correctness property.

The point of most of these is not that the store works, but that the file
stops growing. A collector that keeps running totals forever is a disk that
fills up quietly some months after everyone stopped thinking about it.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from talos_core import RetentionPolicy, Scan, TalosStore
from talos_core.observed import Lease, Observation

NOW = datetime(2026, 8, 30, 9, 0, tzinfo=timezone.utc)


def observation(client: str, fqdn: str, *, days_ago: float = 0, count: int = 1) -> Observation:
    stamp = (NOW - timedelta(days=days_ago)).isoformat()
    return Observation(
        client=client, fqdn=fqdn, count=count, blocked=0, first_seen=stamp, last_seen=stamp
    )


class StoreCase(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "nested" / "talos.db"
        self.addCleanup(self._dir.cleanup)

    def store(self, **policy: int) -> TalosStore:
        store = TalosStore(self.path, RetentionPolicy(**policy) if policy else None)
        self.addCleanup(store.close)
        return store


class TestLifecycle(StoreCase):
    def test_creates_its_directory(self) -> None:
        self.store()
        self.assertTrue(self.path.exists())

    def test_reopening_keeps_the_data(self) -> None:
        first = self.store()
        first.save_observations([observation("10.0.0.1", "a.com")])
        first.set_cursor("2026-08-30T09:00:00+00:00")
        first.close()

        second = TalosStore(self.path)
        self.addCleanup(second.close)
        self.assertEqual(len(second.load_observations()), 1)
        self.assertEqual(second.get_cursor(), "2026-08-30T09:00:00+00:00")

    def test_policy_travels_with_the_file(self) -> None:
        # The CLI and the integration must prune the same way.
        first = self.store(max_observations=7, observation_days=3)
        first.close()
        reopened = TalosStore(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.policy.max_observations, 7)
        self.assertEqual(reopened.policy.observation_days, 3)

    def test_refuses_a_newer_schema(self) -> None:
        store = self.store()
        store._set_meta("schema_version", "99")  # noqa: SLF001 - simulating the future
        store._connection.commit()  # noqa: SLF001
        store.close()
        with self.assertRaises(RuntimeError):
            TalosStore(self.path)


class TestPolicyValidation(unittest.TestCase):
    def test_rejects_nonsense(self) -> None:
        for field in ("observation_days", "max_observations", "scan_history", "vacuum_every"):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        RetentionPolicy(**{field: value})

    def test_round_trips(self) -> None:
        policy = RetentionPolicy(observation_days=7, max_observations=100)
        self.assertEqual(RetentionPolicy.from_dict(policy.to_dict()), policy)

    def test_partial_dict_keeps_defaults(self) -> None:
        policy = RetentionPolicy.from_dict({"observation_days": 7})
        self.assertEqual(policy.observation_days, 7)
        self.assertEqual(policy.max_observations, RetentionPolicy().max_observations)


class TestObservations(StoreCase):
    def test_upsert_replaces_the_running_total(self) -> None:
        store = self.store()
        store.save_observations([observation("10.0.0.1", "a.com", count=5)])
        store.save_observations([observation("10.0.0.1", "a.com", count=9)])
        loaded = store.load_observations()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].count, 9)

    def test_round_trip_preserves_stamps(self) -> None:
        store = self.store()
        original = observation("10.0.0.1", "a.com", days_ago=3, count=42)
        store.save_observations([original])
        self.assertEqual(store.load_observations()[0], original)

    def test_saving_nothing_is_not_an_error(self) -> None:
        store = self.store()
        store.save_observations([])
        self.assertEqual(store.load_observations(), ())


class TestRetention(StoreCase):
    def test_the_file_stops_growing(self) -> None:
        # The property that matters: a collector left running for a year must
        # not end up with a row per domain the network ever resolved.
        store = self.store(max_observations=500, vacuum_every=1)
        store.save_observations(
            [observation("10.0.0.1", f"host{i}.example.com", days_ago=i % 30) for i in range(5000)]
        )
        report = store.prune(now=NOW)

        self.assertEqual(store.stats().observations, 500)
        self.assertGreater(report.observations_over_cap, 0)
        self.assertTrue(report.vacuumed)

    def test_the_cap_keeps_the_freshest_rows(self) -> None:
        store = self.store(max_observations=2)
        store.save_observations(
            [
                observation("10.0.0.1", "old.com", days_ago=10),
                observation("10.0.0.1", "mid.com", days_ago=5),
                observation("10.0.0.1", "new.com", days_ago=1),
            ]
        )
        store.prune(now=NOW)
        self.assertEqual({o.fqdn for o in store.load_observations()}, {"mid.com", "new.com"})

    def test_stale_rows_expire_by_age(self) -> None:
        store = self.store(observation_days=30)
        store.save_observations(
            [
                observation("10.0.0.1", "recent.com", days_ago=2),
                observation("10.0.0.1", "ancient.com", days_ago=200),
            ]
        )
        report = store.prune(now=NOW)
        self.assertEqual(report.observations_expired, 1)
        self.assertEqual({o.fqdn for o in store.load_observations()}, {"recent.com"})

    def test_unparseable_stamps_are_not_aged_out_on_a_guess(self) -> None:
        store = self.store(observation_days=1, max_observations=10)
        store.save_observations(
            [Observation("10.0.0.1", "odd.com", 1, 0, "not a date", "not a date")]
        )
        store.prune(now=NOW)
        self.assertEqual(len(store.load_observations()), 1)

    def test_but_they_go_first_when_over_the_cap(self) -> None:
        store = self.store(max_observations=1)
        store.save_observations(
            [
                Observation("10.0.0.1", "odd.com", 1, 0, "not a date", "not a date"),
                observation("10.0.0.1", "good.com", days_ago=1),
            ]
        )
        store.prune(now=NOW)
        self.assertEqual([o.fqdn for o in store.load_observations()], ["good.com"])

    def test_scan_history_is_bounded(self) -> None:
        store = self.store(scan_history=2)
        for index in range(6):
            store.save_scan(Scan(generated_at=f"2026-08-30T09:0{index}:00+00:00", collector="native"))
        report = store.prune(now=NOW)
        self.assertEqual(report.scans_removed, 4)
        self.assertEqual(store.stats().scans, 2)
        latest = store.latest_scan()
        assert latest is not None
        self.assertEqual(latest["generated_at"], "2026-08-30T09:05:00+00:00")

    def test_vacuum_runs_on_a_schedule_not_every_time(self) -> None:
        store = self.store(vacuum_every=3)
        self.assertFalse(store.prune(now=NOW).vacuumed)
        self.assertFalse(store.prune(now=NOW).vacuumed)
        self.assertTrue(store.prune(now=NOW).vacuumed)

    def test_pruning_an_empty_store_is_harmless(self) -> None:
        report = self.store().prune(now=NOW)
        self.assertEqual(report.total_removed, 0)

    def test_nothing_is_removed_when_within_policy(self) -> None:
        store = self.store(max_observations=100, observation_days=90)
        store.save_observations([observation("10.0.0.1", "a.com", days_ago=1)])
        self.assertEqual(store.prune(now=NOW).total_removed, 0)


class TestLeases(StoreCase):
    def test_round_trip_and_upsert(self) -> None:
        store = self.store()
        store.save_leases([Lease("aa:bb:cc:dd:ee:ff", "10.0.0.5", "nas", static=True)])
        store.save_leases([Lease("aa:bb:cc:dd:ee:ff", "10.0.0.9", "nas", static=True)])
        leases = store.load_leases()
        self.assertEqual(len(leases), 1)
        self.assertEqual(leases[0].ip, "10.0.0.9")
        self.assertTrue(leases[0].static)


class TestStats(StoreCase):
    def test_reports_what_the_panel_needs(self) -> None:
        store = self.store()
        store.save_observations(
            [
                observation("10.0.0.1", "a.com", days_ago=40),
                observation("10.0.0.2", "b.com", days_ago=1),
            ]
        )
        store.save_leases([Lease("aa:bb:cc:dd:ee:ff", "10.0.0.5")])
        store.save_scan(Scan(generated_at="2026-08-30T09:00:00+00:00", collector="native"))

        stats = store.stats()
        self.assertEqual(stats.observations, 2)
        self.assertEqual(stats.leases, 1)
        self.assertEqual(stats.scans, 1)
        self.assertEqual(stats.oldest_observation, (NOW - timedelta(days=40)).isoformat())
        self.assertGreater(stats.bytes_used, 0)
        self.assertIn("bytes_used", json.dumps(stats.to_dict()))


class TestIncrementalPolling(StoreCase):
    """The reason the store exists: the query log rolls over, totals must not."""

    def test_totals_survive_across_polls(self) -> None:
        from talos_core.observed import aggregate

        store = self.store()

        first_poll = [
            {
                "time": "2026-08-30T08:00:00+00:00",
                "client": "192.168.1.42",
                "question": {"name": "p2p2.reolink.com"},
                "reason": "NotFilteredNotFound",
            }
        ] * 3
        store.save_observations(aggregate(first_poll, store.load_observations()))
        store.set_cursor("2026-08-30T08:00:00+00:00")

        # AdGuard has since rolled the log: the second poll sees two records.
        second_poll = [
            {
                "time": "2026-08-30T08:30:00+00:00",
                "client": "192.168.1.42",
                "question": {"name": "p2p2.reolink.com"},
                "reason": "NotFilteredNotFound",
            }
        ] * 2
        store.save_observations(aggregate(second_poll, store.load_observations()))

        total = store.load_observations()[0]
        self.assertEqual(total.count, 5)
        self.assertEqual(total.first_seen, "2026-08-30T08:00:00+00:00")
        self.assertEqual(total.last_seen, "2026-08-30T08:30:00+00:00")
        self.assertEqual(store.get_cursor(), "2026-08-30T08:00:00+00:00")

    def test_cursor_can_be_cleared_for_a_full_resync(self) -> None:
        store = self.store()
        store.set_cursor("2026-08-30T08:00:00+00:00")
        store.set_cursor(None)
        self.assertIsNone(store.get_cursor())


if __name__ == "__main__":
    unittest.main()


class TestSnapshots(unittest.TestCase):
    """One compact row per scan, kept for the window, oldest first."""

    def test_rows_come_back_oldest_first_and_bounded(self) -> None:
        import tempfile
        from pathlib import Path

        from talos_core import RetentionPolicy, TalosStore

        with tempfile.TemporaryDirectory() as folder:
            with TalosStore(Path(folder, "t.sqlite"), RetentionPolicy(observation_days=30)) as store:
                for day in (1, 2, 3):
                    store.save_snapshot({"generated_at": f"2026-09-0{day}T00:00:00+00:00", "failed_high": day})
                rows = store.history(limit=10)
                self.assertEqual([r["failed_high"] for r in rows], [1, 2, 3])
                self.assertEqual([r["failed_high"] for r in store.history(limit=2)], [2, 3])
                self.assertEqual(store.stats().snapshots, 3)

    def test_rows_older_than_the_window_are_pruned_with_it(self) -> None:
        import tempfile
        from datetime import datetime, timezone
        from pathlib import Path

        from talos_core import RetentionPolicy, TalosStore

        with tempfile.TemporaryDirectory() as folder:
            with TalosStore(Path(folder, "t.sqlite"), RetentionPolicy(observation_days=7)) as store:
                store.save_snapshot({"generated_at": "2026-08-01T00:00:00+00:00", "failed_high": 9})
                store.save_snapshot({"generated_at": "2026-09-03T00:00:00+00:00", "failed_high": 1})
                store.prune(now=datetime(2026, 9, 4, tzinfo=timezone.utc))
                self.assertEqual([r["failed_high"] for r in store.history()], [1])
