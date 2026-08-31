"""Posture engine and zone tests.

The property under test throughout: a check that could not run is never
reported as a pass. Everything else in this file is detail.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import CheckEngine, Scan, ZoneMap, derive, validate
from talos_core.checks import default_engine
from talos_core.observed import merge_observed
from talos_core.zones import ZoneMap as Zones

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str = "home") -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def scan(name: str = "home") -> Scan:
    raw = load(name)
    assert validate(raw) == []
    return Scan.from_dict(raw)


class TestZoneMap(unittest.TestCase):
    def test_longest_prefix_wins(self) -> None:
        zones = Zones.from_pairs(
            [("192.168.1.0/24", "trusted_lan"), ("192.168.1.240/28", "iot_vlan")]
        )
        self.assertEqual(zones.zone_for("192.168.1.42"), "trusted_lan")
        self.assertEqual(zones.zone_for("192.168.1.243"), "iot_vlan")

    def test_unmatched_address_is_unknown_not_trusted(self) -> None:
        zones = Zones.from_pairs([("10.0.0.0/8", "iot_vlan")])
        self.assertEqual(zones.zone_for("192.168.1.1"), "unknown")

    def test_missing_or_malformed_input_is_dropped(self) -> None:
        self.assertEqual(Zones().zone_for("192.168.1.1"), "unknown")
        self.assertFalse(Zones.from_pairs([("not-a-cidr", "iot_vlan")]))
        self.assertFalse(Zones.from_pairs([("10.0.0.0/8", "not-a-zone")]))
        self.assertEqual(Zones.from_pairs([("10.0.0.0/8", "iot_vlan")]).zone_for(None), "unknown")
        self.assertEqual(Zones.from_pairs([("10.0.0.0/8", "iot_vlan")]).zone_for("nonsense"), "unknown")

    def test_from_dict_accepts_strings_and_lists(self) -> None:
        zones = ZoneMap.from_dict(
            {"iot_vlan": "192.168.30.0/24, 192.168.31.0/24", "trusted_lan": ["192.168.1.0/24"]}
        )
        self.assertEqual(zones.zone_for("192.168.31.5"), "iot_vlan")
        self.assertEqual(zones.zone_for("192.168.1.5"), "trusted_lan")


class TestEngineOnTheReferenceHouse(unittest.TestCase):
    def setUp(self) -> None:
        self.report = derive(scan()).checks

    def test_the_high_severity_finding_is_the_key_quadrant(self) -> None:
        failure = next(r for r in self.report.failed if r.id == "chk.local_with_egress")
        self.assertEqual(failure.severity, "high")
        self.assertEqual(len(failure.subjects), 4)
        self.assertEqual(failure.subject_kind, "device")
        self.assertTrue(failure.remediation)

    def test_failures_are_ordered_by_severity(self) -> None:
        severities = [result.severity for result in self.report.failed]
        self.assertEqual(severities, sorted(severities, key=["high", "medium", "low"].index))

    def test_unimplemented_checks_are_declared_not_omitted(self) -> None:
        declared = {check.id for check in self.report.unverified}
        for check_id in (
            "chk.mqtt_anonymous",
            "chk.mqtt_unknown_client",
            "chk.zwave_s2",
            "chk.rtsp_cleartext",
            "chk.arp_unknown",
        ):
            with self.subTest(check=check_id):
                self.assertIn(check_id, declared)

    def test_counts_add_up_and_stay_separate(self) -> None:
        counts = self.report.counts
        self.assertEqual(
            counts["failed_high"] + counts["failed_medium"] + counts["failed_low"],
            len(self.report.failed),
        )
        self.assertEqual(counts["passed"], len(self.report.passed))
        # The unverified are counted on their own, never inside the passes.
        self.assertNotIn("chk.mqtt_anonymous", {r.id for r in self.report.passed})


class TestPreconditions(unittest.TestCase):
    """The reason the engine exists in this shape."""

    def test_declared_only_scan_does_not_pass_the_egress_check(self) -> None:
        raw = load()
        raw["conduits"] = []
        raw["destinations"] = []
        report = derive(Scan.from_dict(raw)).checks

        passed = {result.id for result in report.passed}
        self.assertNotIn("chk.local_with_egress", passed)

        note = next(c for c in report.unverified if c.id == "chk.local_with_egress")
        self.assertIn("does not mean an absence of traffic", note.detail)
        self.assertIn("This is not a pass", note.detail)

    def test_without_zones_the_vlan_check_cannot_run(self) -> None:
        raw = load()
        for device in raw["devices"]:
            device["zone"] = "unknown"
        report = derive(Scan.from_dict(raw)).checks
        self.assertNotIn("chk.device_on_trusted_lan", {r.id for r in report.passed})
        note = next(c for c in report.unverified if c.id == "chk.device_on_trusted_lan")
        self.assertIn("no network ranges configured", note.detail)

    def test_without_leases_the_zero_check_cannot_run(self) -> None:
        raw = load()
        raw["unverified"].append(
            {
                "id": "unv.dhcp_leases_unavailable",
                "title": "Lease DHCP non disponibili",
                "reason": "missing_data",
                "detail": "…",
            }
        )
        report = derive(Scan.from_dict(raw)).checks
        self.assertNotIn("chk.resolver_bypass", {r.id for r in report.passed})

    def test_without_manifests_the_custom_integration_check_cannot_run(self) -> None:
        raw = load()
        raw["unverified"].append(
            {
                "id": "unv.manifests_unavailable",
                "title": "Manifest non leggibili",
                "reason": "missing_data",
                "detail": "…",
            }
        )
        report = derive(Scan.from_dict(raw)).checks
        self.assertNotIn("chk.custom_integration_cloud", {r.id for r in report.passed})

    def test_an_unknown_precondition_blocks_the_check(self) -> None:
        engine = CheckEngine(
            [
                {
                    "id": "chk.bogus",
                    "title": "Regola con precondizione inventata",
                    "severity": "high",
                    "requires": ["something_nobody_implemented"],
                    "selector": {"type": "matrix_quadrant", "quadrant": "local_egress"},
                }
            ]
        )
        derived = derive(scan(), engine)
        self.assertEqual(derived.checks.results, ())
        self.assertEqual(derived.checks.unverified[-1].id, "chk.bogus")


class TestSelectors(unittest.TestCase):
    def run_selector(self, selector: dict[str, Any], **rule: Any) -> Any:
        engine = CheckEngine(
            [{"id": "chk.t", "title": "t", "severity": "low", "selector": selector, **rule}]
        )
        return derive(scan(), engine).checks.results[0]

    def test_integration_where(self) -> None:
        result = self.run_selector(
            {"type": "integration_where", "iot_class_in": ["cloud_push"]}
        )
        self.assertEqual(set(result.subjects), {"int.tuya", "int.mobile_app"})
        self.assertEqual(result.subject_kind, "integration")

    def test_integration_where_built_in_flag(self) -> None:
        result = self.run_selector({"type": "integration_where", "is_built_in": False})
        self.assertEqual(result.subjects, ())
        self.assertTrue(result.passed)

    def test_device_where_combines_conditions(self) -> None:
        result = self.run_selector(
            {"type": "device_where", "zone_in": ["trusted_lan"], "has_phone_home_egress": True}
        )
        self.assertIn("dev.reolink.garden", result.subjects)
        self.assertNotIn("dev.esphome.garage", result.subjects)  # iot_vlan

    def test_unverified_present_uses_structured_subjects(self) -> None:
        raw = load()
        raw["unverified"].append(
            {
                "id": "unv.resolver_bypassed",
                "title": "Dispositivi che non passano dal resolver",
                "reason": "method_limit",
                "detail": "…",
                "subjects": ["192.168.1.203"],
            }
        )
        engine = CheckEngine(
            [
                {
                    "id": "chk.t",
                    "title": "t",
                    "severity": "high",
                    "selector": {"type": "unverified_present", "check_id": "unv.resolver_bypassed"},
                }
            ]
        )
        result = derive(Scan.from_dict(raw), engine).checks.results[0]
        self.assertEqual(result.subjects, ("192.168.1.203",))
        self.assertEqual(result.subject_kind, "host")
        self.assertFalse(result.passed)

    def test_unsupported_selector_raises_instead_of_passing(self) -> None:
        engine = CheckEngine(
            [{"id": "chk.t", "title": "t", "severity": "low", "selector": {"type": "wat"}}]
        )
        with self.assertRaises(ValueError):
            derive(scan(), engine)


class TestEngineLoading(unittest.TestCase):
    def test_default_rules_file_parses(self) -> None:
        engine = default_engine()
        self.assertGreaterEqual(len(engine._rules), 10)  # noqa: SLF001

    def test_report_is_json_serialisable(self) -> None:
        payload = json.loads(json.dumps(derive(scan()).checks.to_dict()))
        self.assertIn("counts", payload)
        self.assertIn("failed", payload)


class TestZonesThroughTheMerge(unittest.TestCase):
    def test_merge_assigns_zones_from_the_leases(self) -> None:
        from tests.test_observed import FakeHttp, adguard, collect, declared_scan

        facts = collect(FakeHttp(adguard()))
        zones = ZoneMap.from_dict({"trusted_lan": "192.168.1.0/24"})
        merged = merge_observed(declared_scan(), facts, None, zones)

        camera = merged.device("d_cam1")
        assert camera is not None
        self.assertEqual(camera.zone, "trusted_lan")
        # No address, no zone: nothing is assumed.
        lamp = merged.device("d_lamp")
        assert lamp is not None
        self.assertEqual(lamp.zone, "unknown")
        self.assertEqual(validate(merged.to_dict()), [])

    def test_without_a_zone_map_nothing_is_assumed(self) -> None:
        from tests.test_observed import FakeHttp, adguard, collect, declared_scan

        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        self.assertTrue(all(device.zone == "unknown" for device in merged.devices))


if __name__ == "__main__":
    unittest.main()
