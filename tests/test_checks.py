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
        # Both are implemented; on this fixture neither has what it needs, and
        # a check that cannot run must say so rather than pass.
        for check_id in ("chk.mqtt_unknown_client", "chk.rtsp_cleartext"):
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
        self.assertNotIn("chk.mqtt_unknown_client", {r.id for r in self.report.passed})


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


class TestAnonymousBroker(unittest.TestCase):
    """Proved by Home Assistant's own connection, not by a probe: an entry
    that reaches a broker with no credential is the broker's answer."""

    @staticmethod
    def report_for(**endpoint: object):
        from talos_core.sources.mapping import RegistryPayload, build_scan

        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_mqtt", "domain": "mqtt", "title": "Mosquitto",
                 "state": "loaded", "endpoint": endpoint or None}
            ],
            devices=[],
            entities=[],
            areas=[],
            manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
        )
        scan = build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")
        return derive(scan).checks

    def test_no_credential_on_the_entry_is_the_finding(self) -> None:
        report = self.report_for(host="core-mosquitto", port=1883, authenticated=False)
        result = next(r for r in report.failed if r.id == "chk.mqtt_anonymous")
        self.assertEqual(result.severity, "high")
        self.assertEqual(result.subjects, ("e_mqtt",))

    def test_an_authenticated_entry_passes(self) -> None:
        report = self.report_for(host="core-mosquitto", port=1883, authenticated=True)
        self.assertIn("chk.mqtt_anonymous", {r.id for r in report.passed})

    def test_an_unreadable_entry_is_unverified_not_passed(self) -> None:
        """The WebSocket collector cannot read entry data. Not knowing is not
        the same as knowing there is nothing."""
        report = self.report_for()
        self.assertIn("chk.mqtt_anonymous", {r.id for r in report.unverified})
        self.assertNotIn("chk.mqtt_anonymous", {r.id for r in report.passed})


class TestMissingPreconditionsAreNamed(unittest.TestCase):
    """A reason of "missing data" that does not say which data is no reason.
    The names travel as data, so the panel can say what to supply and where."""

    def test_a_skipped_check_names_what_it_lacked(self) -> None:
        raw = load()
        raw["conduits"] = []
        raw["destinations"] = []
        report = derive(Scan.from_dict(raw)).checks
        skipped = {check.id: check for check in report.unverified}
        self.assertEqual(skipped["chk.local_with_egress"].missing, ["observed_evidence"])
        # The reference house has zones configured, so only the observations
        # are missing here. The two-precondition case is built below, where
        # nothing about the fixture is assumed.
        self.assertEqual(skipped["chk.device_on_trusted_lan"].missing, ["observed_evidence"])

    def test_every_unmet_precondition_is_named_in_rule_order(self) -> None:
        """A fresh registry has no zones and no observations, so the trusted
        LAN check lacks both, and both must be named, in the order the rule
        lists them, not only the first one found."""
        from talos_core.sources.mapping import RegistryPayload, build_scan

        payload = RegistryPayload(
            config_entries=[{"entry_id": "e1", "domain": "hue", "state": "loaded", "endpoint": None}],
            devices=[{"id": "d1", "name": "Lamp", "config_entries": ["e1"],
                      "primary_config_entry": "e1", "identifiers": [["hue", "1"]],
                      "connections": [["mac", "aa:bb:cc:dd:ee:01"]]}],
            entities=[],
            areas=[],
            manifests=[{"domain": "hue", "iot_class": "local_push", "is_built_in": True}],
        )
        scan = build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")
        skipped = {check.id: check for check in derive(scan).checks.unverified}
        self.assertEqual(
            skipped["chk.device_on_trusted_lan"].missing,
            ["zones_configured", "observed_evidence"],
        )

    def test_the_names_survive_the_document(self) -> None:
        from talos_core import UnverifiedCheck

        check = UnverifiedCheck(id="chk.x", title="x", reason="missing_data", missing=["dhcp_leases"])
        self.assertEqual(UnverifiedCheck.from_dict(check.to_dict(), "$").missing, ["dhcp_leases"])
        # A note from a collector carries none, and that reads as an empty list.
        self.assertEqual(UnverifiedCheck.from_dict({"id": "unv.x", "title": "x", "reason": "method_limit"}, "$").missing, [])

    def test_every_precondition_the_engine_knows_can_be_named(self) -> None:
        """The panel translates by name, so a precondition added to the engine
        without a string would render a key to the user."""
        from talos_core.checks import PRECONDITION_REASONS

        source = (
            Path(__file__).resolve().parent.parent / "custom_components" / "talos" / "www" / "talos-panel.js"
        ).read_text(encoding="utf-8")
        for name in PRECONDITION_REASONS:
            with self.subTest(precondition=name):
                self.assertEqual(source.count(f'"precondition.{name}"'), 2, "one per language")


class TestCleartextStreamCoverage(unittest.TestCase):
    """Green where nothing carries video, named where something does and
    declares no URL, and audio is not video."""

    @staticmethod
    def report_for(*domains: str):
        from talos_core.sources.mapping import RegistryPayload, build_scan

        payload = RegistryPayload(
            config_entries=[
                {"entry_id": f"e_{d}", "domain": d, "title": d.title(), "state": "loaded", "endpoint": None}
                for d in domains
            ],
            devices=[], entities=[], areas=[],
            manifests=[{"domain": d, "iot_class": "local_polling", "is_built_in": True} for d in domains],
        )
        scan = build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")
        return derive(scan).checks

    def test_nothing_carrying_video_is_a_pass(self) -> None:
        report = self.report_for("mqtt", "hue")
        self.assertIn("chk.rtsp_cleartext", {r.id for r in report.passed})

    def test_a_camera_that_declares_no_url_is_named_not_passed(self) -> None:
        report = self.report_for("mqtt", "reolink")
        skipped = {c.id: c for c in report.unverified}
        self.assertIn("chk.rtsp_cleartext", skipped)
        self.assertEqual(skipped["chk.rtsp_cleartext"].subjects, ["e_reolink"])
        self.assertEqual(skipped["chk.rtsp_cleartext"].missing, ["entry_streams"])

    def test_audio_is_not_video(self) -> None:
        """Sonos and Spotify stream, and have no RTSP stream to be in the
        clear. Naming them as uninspectable for one would be wrong."""
        report = self.report_for("spotify", "sonos", "dlna_dmr")
        self.assertIn("chk.rtsp_cleartext", {r.id for r in report.passed})
