"""Model tests: loading, serialisation and the helpers the derivations rely on."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import Conduit, Correlation, Device, Scan, SourceRef, TalosSchemaError, validate

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class TestRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = load("home")
        self.scan = Scan.from_dict(self.raw)

    def test_loads_every_collection(self) -> None:
        self.assertEqual(len(self.scan.integrations), 9)
        self.assertEqual(len(self.scan.devices), 10)
        self.assertEqual(len(self.scan.destinations), 10)
        self.assertEqual(len(self.scan.conduits), 14)
        self.assertEqual(len(self.scan.unverified), 4)

    def test_export_still_validates(self) -> None:
        self.assertEqual(validate(self.scan.to_dict()), [])

    def test_export_is_stable_across_two_passes(self) -> None:
        once = self.scan.to_dict()
        twice = Scan.from_dict(once).to_dict()
        self.assertEqual(once, twice)

    def test_lookups_resolve(self) -> None:
        self.assertIsNotNone(self.scan.integration("int.hue"))
        self.assertIsNotNone(self.scan.device("dev.hue.bridge"))
        self.assertIsNotNone(self.scan.destination("dst.reolink.p2p"))
        self.assertIsNone(self.scan.device("dev.nope"))


class TestConduitSerialisation(unittest.TestCase):
    def test_inherited_conduit_never_exports_observation_fields(self) -> None:
        # Even if a caller sets them in memory, they must not reach the export:
        # a second-hand fact would otherwise be published with the weight of a
        # first-hand one.
        conduit = Conduit(
            id="c1",
            source=SourceRef("device", "dev.lamp"),
            destination_id="dst.cloud",
            evidence="inherited",
            inherited_from="dev.hub",
            query_count=999,
            last_seen="2026-08-30T09:00:00+02:00",
        )
        exported = conduit.to_dict()
        for field in ("first_seen", "last_seen", "query_count", "filter_status"):
            self.assertNotIn(field, exported)
        self.assertEqual(exported["inherited_from"], "dev.hub")

    def test_observed_conduit_exports_them(self) -> None:
        conduit = Conduit(
            id="c2",
            source=SourceRef("device", "dev.cam"),
            destination_id="dst.cloud",
            evidence="observed",
            last_seen="2026-08-30T09:00:00+02:00",
            query_count=12,
            filter_status="allowed",
        )
        exported = conduit.to_dict()
        self.assertEqual(exported["query_count"], 12)
        self.assertNotIn("inherited_from", exported)


class TestHubChain(unittest.TestCase):
    def setUp(self) -> None:
        self.scan = Scan.from_dict(load("home"))

    def test_child_reports_its_hub(self) -> None:
        self.assertEqual(self.scan.hub_chain("dev.hue.lamp.living"), ["dev.hue.bridge"])

    def test_root_device_has_no_chain(self) -> None:
        self.assertEqual(self.scan.hub_chain("dev.hue.bridge"), [])

    def test_chain_survives_a_cycle(self) -> None:
        # A malformed chain is the validator's problem to report; the helper
        # must not spin on it.
        scan = Scan(
            generated_at="2026-08-30T09:00:00+02:00",
            collector="native",
            devices=[
                Device(id="a", integration_id="i", name="A", via_device_id="b"),
                Device(id="b", integration_id="i", name="B", via_device_id="a"),
            ],
        )
        self.assertEqual(scan.hub_chain("a"), ["b"])


class TestDeviceProperties(unittest.TestCase):
    def test_non_ip_transports_have_no_direct_egress(self) -> None:
        for transport in ("zigbee", "zwave", "ble", "thread"):
            with self.subTest(transport=transport):
                device = Device(id="d", integration_id="i", name="D", transport=transport)
                self.assertFalse(device.can_have_direct_egress)

    def test_ip_transports_can(self) -> None:
        for transport in ("wifi", "ethernet", "matter"):
            with self.subTest(transport=transport):
                device = Device(id="d", integration_id="i", name="D", transport=transport)
                self.assertTrue(device.can_have_direct_egress)


class TestCorrelation(unittest.TestCase):
    def test_ratio(self) -> None:
        self.assertAlmostEqual(Correlation(devices_total=10, devices_correlated=6).ratio, 0.6)

    def test_ratio_with_no_devices_does_not_divide_by_zero(self) -> None:
        self.assertEqual(Correlation().ratio, 0.0)


class TestLoadingUnvalidatedDocuments(unittest.TestCase):
    def test_missing_required_field_raises(self) -> None:
        raw = load("home")
        del raw["devices"][0]["name"]
        with self.assertRaises(TalosSchemaError) as caught:
            Scan.from_dict(raw)
        self.assertTrue(caught.exception.findings)

    def test_error_message_names_the_path(self) -> None:
        with self.assertRaises(TalosSchemaError) as caught:
            Scan.from_dict({"collector": "native"})
        self.assertIn("$.generated_at", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
