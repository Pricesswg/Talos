"""Sizing the store from one number: the days to keep."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from talos_core.retention import (
    DEFAULT_RATE_PER_DAY,
    HEADROOM,
    MAX_SCAN_DOCUMENTS,
    measured_rate,
    size_for,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
BOUNDS = {"observation_days": (1, 3650), "max_observations": (500, 500_000), "scan_history": (1, 200)}


class TestMeasuredRate(unittest.TestCase):
    def test_the_rate_is_rows_over_the_days_they_span(self) -> None:
        oldest = (NOW - timedelta(days=10)).isoformat()
        self.assertAlmostEqual(measured_rate(4000, oldest, NOW), 400.0)

    def test_too_little_history_gives_no_rate(self) -> None:
        self.assertIsNone(measured_rate(50, (NOW - timedelta(days=10)).isoformat(), NOW))
        self.assertIsNone(measured_rate(4000, None, NOW))
        # Less than a day of history would give a number that means nothing.
        self.assertIsNone(measured_rate(4000, (NOW - timedelta(hours=6)).isoformat(), NOW))

    def test_a_z_suffix_and_a_naive_stamp_both_parse(self) -> None:
        z = (NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        naive = (NOW - timedelta(days=2)).replace(tzinfo=None).isoformat()
        self.assertIsNotNone(measured_rate(1000, z, NOW))
        self.assertIsNotNone(measured_rate(1000, naive, NOW))


class TestSizing(unittest.TestCase):
    def test_everything_follows_from_the_days_and_the_rate(self) -> None:
        oldest = (NOW - timedelta(days=10)).isoformat()
        sizing = size_for(30, 15, observations=4000, oldest=oldest, bytes_used=1_000_000, bounds=BOUNDS, now=NOW)
        self.assertEqual(sizing.observation_days, 30)
        self.assertTrue(sizing.rate_measured)
        # 400 a day, 30 days, a quarter of headroom.
        self.assertEqual(sizing.max_observations, int(400 * 30 * HEADROOM))
        # A scan every 15 minutes is 96 a day; the documents are capped.
        self.assertEqual(sizing.scan_history, MAX_SCAN_DOCUMENTS)
        # 250 bytes each today, projected onto the ceiling.
        self.assertEqual(sizing.estimate_bytes, int(1_000_000 / 4000 * sizing.max_observations))

    def test_without_history_the_default_rate_is_used_and_said_so(self) -> None:
        sizing = size_for(7, 60, observations=0, oldest=None, bounds=BOUNDS, now=NOW)
        self.assertFalse(sizing.rate_measured)
        self.assertEqual(sizing.rate_per_day, DEFAULT_RATE_PER_DAY)
        self.assertEqual(sizing.max_observations, int(DEFAULT_RATE_PER_DAY * 7 * HEADROOM))
        self.assertIsNone(sizing.estimate_bytes)
        # Hourly scans for a week: 168 documents, under the cap.
        self.assertEqual(sizing.scan_history, MAX_SCAN_DOCUMENTS)

    def test_the_store_bounds_are_respected(self) -> None:
        tiny = size_for(1, 1440, observations=0, oldest=None, bounds=BOUNDS, now=NOW)
        self.assertEqual(tiny.max_observations, 500)
        self.assertEqual(tiny.scan_history, 1)
        huge = size_for(100_000, 5, observations=0, oldest=None, bounds=BOUNDS, now=NOW)
        self.assertEqual(huge.observation_days, 3650)
        self.assertEqual(huge.max_observations, 500_000)
        self.assertEqual(huge.scan_history, MAX_SCAN_DOCUMENTS)


if __name__ == "__main__":
    unittest.main()


class TestSnapshotRow(unittest.TestCase):
    def test_the_row_carries_the_numbers_the_charts_draw(self) -> None:
        import json
        from pathlib import Path

        from talos_core import Scan, derive, snapshot_of

        raw = json.loads((Path(__file__).parent / "fixtures" / "home.json").read_text(encoding="utf-8"))
        scan = Scan.from_dict(raw)
        row = snapshot_of(scan, derive(scan))
        for key in ("generated_at", "failed_high", "failed_medium", "failed_low", "passed", "partial",
                    "unverified", "entities_total", "entities_local", "entities_cloud",
                    "devices_total", "devices_exposed", "local_egress", "unclassified",
                    "devices_correlated", "devices_scanned"):
            with self.subTest(key=key):
                self.assertIn(key, row)
        self.assertEqual(row["generated_at"], scan.generated_at)
        # Only declared checks count as could-not-run here, never the notes.
        self.assertLessEqual(row["unverified"], len(derive(scan).checks.unverified))
