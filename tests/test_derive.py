"""Derivation tests, all against the reference house.

The fixture is small enough to reason about by hand, which is the point: if a
number here is wrong it is wrong in a way a person can see, not only in a way
an assertion can.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import (
    Correlation,
    Scan,
    build_autonomy,
    build_exposure,
    build_matrix,
    derive,
    validate,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str = "home") -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def scan_from(raw: dict[str, Any]) -> Scan:
    assert validate(raw) == [], "fixture mutation made the document invalid"
    return Scan.from_dict(raw)


class TestMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = build_matrix(scan_from(load()))

    def test_key_quadrant(self) -> None:
        # Local to HA, yet caught talking to their vendor on their own.
        self.assertEqual(
            self.matrix.local_egress,
            ("dev.hue.bridge", "dev.reolink.door", "dev.reolink.garden", "dev.shelly.plug"),
        )
        self.assertEqual(self.matrix.key_quadrant, self.matrix.local_egress)

    def test_other_quadrants(self) -> None:
        self.assertEqual(self.matrix.cloud_egress, ("dev.tuya.cam",))
        self.assertEqual(self.matrix.cloud_silent, ())
        self.assertEqual(len(self.matrix.local_silent), 5)
        self.assertEqual(self.matrix.unclassified, ())

    def test_every_device_lands_in_exactly_one_bucket(self) -> None:
        placed = (
            self.matrix.local_silent
            + self.matrix.local_egress
            + self.matrix.cloud_silent
            + self.matrix.cloud_egress
            + self.matrix.unclassified
        )
        self.assertEqual(len(placed), 10)
        self.assertEqual(len(set(placed)), 10)

    def test_inherited_exposure_stays_out_of_the_quadrants(self) -> None:
        # Nine lamps behind one talkative bridge are one thing to fix, not ten.
        self.assertEqual(len(self.matrix.inherited), 2)
        for exposure in self.matrix.inherited:
            self.assertEqual(exposure.hub_id, "dev.hue.bridge")
            self.assertIn(exposure.device_id, self.matrix.local_silent)
            self.assertNotIn(exposure.device_id, self.matrix.local_egress)

    def test_infra_egress_is_not_phoning_home(self) -> None:
        raw = load()
        raw["conduits"].append(
            {
                "id": "cnd.esphome.ntp",
                "source": {"kind": "device", "id": "dev.esphome.garage"},
                "destination_id": "dst.ntp",
                "evidence": "observed",
                "last_seen": "2026-08-30T09:00:00+02:00",
                "query_count": 48,
                "filter_status": "allowed",
            }
        )
        matrix = build_matrix(scan_from(raw))
        self.assertNotIn("dev.esphome.garage", matrix.local_egress)
        self.assertIn("dev.esphome.garage", matrix.infra_only)

    def test_unclassified_iot_class_gets_its_own_bucket(self) -> None:
        raw = load()
        next(i for i in raw["integrations"] if i["id"] == "int.esphome")["iot_class"] = (
            "assumed_state"
        )
        matrix = build_matrix(scan_from(raw))
        self.assertIn("dev.esphome.garage", matrix.unclassified)
        self.assertNotIn("dev.esphome.garage", matrix.local_silent)


class TestAutonomy(unittest.TestCase):
    def setUp(self) -> None:
        self.autonomy = build_autonomy(scan_from(load()))

    def test_entity_totals(self) -> None:
        self.assertEqual(self.autonomy.entities_total, 53)
        self.assertEqual(self.autonomy.entities_local, 41)
        self.assertEqual(self.autonomy.entities_cloud, 12)
        self.assertEqual(self.autonomy.entities_unclassified, 0)
        self.assertAlmostEqual(self.autonomy.local_ratio, 41 / 53)

    def test_device_less_integrations_are_counted(self) -> None:
        # mobile_app has no device at all. Counting entities device by device
        # would drop it, and it is the most cloud-bound thing in the house.
        self.assertIn("int.mobile_app", self.autonomy.integrations_cloud)
        google = next(loss for loss in self.autonomy.losses if loss.vendor == "Google")
        self.assertEqual(google.entities, 4)

    def test_losses_are_ordered_worst_first(self) -> None:
        self.assertEqual(
            [(loss.vendor, loss.entities) for loss in self.autonomy.losses],
            [("Tuya", 6), ("Google", 4), ("MET Norway", 2)],
        )

    def test_observed_only_egress_is_not_a_functional_dependency(self) -> None:
        # Reolink is watched talking to its cloud, but HA drives the cameras
        # locally: unplugging the uplink does not stop them.
        vendors = [loss.vendor for loss in self.autonomy.losses]
        self.assertNotIn("Reolink", vendors)
        self.assertNotIn("Allterco", vendors)

    def test_cloud_integration_without_a_declared_destination_is_still_named(self) -> None:
        raw = load()
        raw["conduits"] = [c for c in raw["conduits"] if c["id"] != "cnd.met.api"]
        autonomy = build_autonomy(scan_from(raw))
        self.assertIn("Meteorologisk institutt", [loss.vendor for loss in autonomy.losses])
        self.assertEqual(autonomy.entities_cloud, 12)


class TestExposure(unittest.TestCase):
    def setUp(self) -> None:
        self.exposure = build_exposure(scan_from(load()))

    def test_direct_and_inherited_are_disjoint(self) -> None:
        self.assertEqual(len(self.exposure.devices_direct), 5)
        self.assertEqual(
            self.exposure.devices_inherited, ("dev.hue.lamp.hall", "dev.hue.lamp.living")
        )
        self.assertEqual(
            set(self.exposure.devices_direct) & set(self.exposure.devices_inherited), set()
        )

    def test_evidence_is_labelled_per_vendor(self) -> None:
        by_vendor = {v.vendor: v for v in self.exposure.vendors}
        self.assertEqual(by_vendor["Reolink"].evidence, ("observed",))
        self.assertEqual(by_vendor["Google"].evidence, ("declared",))
        self.assertEqual(by_vendor["Tuya"].evidence, ("declared", "observed"))
        self.assertEqual(by_vendor["Signify"].evidence, ("inherited", "observed"))

    def test_observed_vendors_come_before_declared_only_ones(self) -> None:
        observed = [v.is_observed for v in self.exposure.vendors]
        self.assertEqual(observed, sorted(observed, reverse=True))

    def test_query_volumes_add_up_per_vendor(self) -> None:
        by_vendor = {v.vendor: v for v in self.exposure.vendors}
        self.assertEqual(by_vendor["Reolink"].queries, 2412 + 2388)
        self.assertEqual(by_vendor["Allterco"].blocked_queries, 96)
        self.assertEqual(by_vendor["Google"].queries, 0)

    def test_unknown_hosts_are_surfaced(self) -> None:
        self.assertEqual(self.exposure.unknown_hosts, ("192.168.1.87",))

    def test_internal_destinations_are_not_exposure(self) -> None:
        vendors = [v.vendor for v in self.exposure.vendors]
        self.assertNotIn("192.168.1.10", vendors)  # the local MQTT broker
        self.assertNotIn("Home Assistant", vendors)  # the version check is infra


class TestDerived(unittest.TestCase):
    def test_derive_bundles_everything(self) -> None:
        derived = derive(scan_from(load()))
        self.assertEqual(derived.correlation, Correlation(10, 6, "mac_ip"))
        self.assertEqual(len(derived.matrix.local_egress), 4)
        # The count carries the scan's own notes plus every check that could
        # not run, which is the whole point of keeping it visible.
        self.assertEqual(derived.unverified_count, len(derived.checks.unverified))
        self.assertGreater(derived.unverified_count, len(scan_from(load()).unverified))

    def test_export_is_json_serialisable(self) -> None:
        derived = derive(scan_from(load()))
        restored = json.loads(json.dumps(derived.to_dict()))
        self.assertEqual(restored["matrix"]["local_egress"], list(derived.matrix.local_egress))
        self.assertEqual(restored["autonomy"]["entities_total"], 53)
        self.assertEqual(restored["unverified_count"], derived.unverified_count)
        self.assertIn("counts", restored["checks"])

    def test_derivations_are_pure(self) -> None:
        raw = load()
        before = copy.deepcopy(raw)
        derive(scan_from(raw))
        self.assertEqual(raw, before)

    def test_empty_scan_does_not_crash(self) -> None:
        scan = Scan(generated_at="2026-08-30T09:00:00+02:00", collector="native")
        derived = derive(scan)
        self.assertEqual(derived.matrix.local_egress, ())
        self.assertEqual(derived.autonomy.entities_total, 0)
        self.assertEqual(derived.autonomy.local_ratio, 0.0)
        self.assertEqual(derived.exposure.vendors, ())


if __name__ == "__main__":
    unittest.main()
