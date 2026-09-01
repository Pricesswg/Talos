"""NativeSource tests.

The integration package cannot be imported without Home Assistant, but the
part that matters, turning registry objects into the shared payload shape,
is pure and duck-typed. It is loaded here under a synthetic package name so it
can be exercised with fakes, which is the only way this conversion stays
tested at all.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from talos_core import derive, validate
from talos_core.sources.mapping import build_scan

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "talos"
FROZEN_CLOCK = "2026-08-30T07:14:02+00:00"


def _load_native_source() -> Any:
    """Load the module without triggering the package's Home Assistant imports."""
    package = types.ModuleType("talos_ha")
    package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
    sys.modules.setdefault("talos_ha", package)

    spec = importlib.util.spec_from_file_location(
        "talos_ha.native_source", COMPONENT / "native_source.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["talos_ha.native_source"] = module
    spec.loader.exec_module(module)
    return module


native = _load_native_source()


class ConfigEntryState(Enum):
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"


class DisabledBy(Enum):
    USER = "user"


@dataclass
class FakeDevice:
    id: str
    config_entries: set[str]
    name: str | None = None
    name_by_user: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    area_id: str | None = None
    primary_config_entry: str | None = None
    connections: set[tuple[str, str]] = field(default_factory=set)
    via_device_id: str | None = None
    disabled_by: Any = None


@dataclass
class FakeEntity:
    entity_id: str
    device_id: str | None = None
    config_entry_id: str | None = None
    platform: str | None = None
    disabled_by: Any = None


@dataclass
class FakeArea:
    id: str
    name: str


@dataclass
class FakeConfigEntry:
    entry_id: str
    domain: str
    title: str
    state: Any = ConfigEntryState.LOADED
    source: str = "user"
    disabled_by: Any = None


@dataclass
class FakeIntegration:
    domain: str
    manifest: dict[str, Any]
    is_built_in: bool = True


def house() -> dict[str, list[Any]]:
    return {
        "config_entries": [
            FakeConfigEntry("e_hue", "hue", "Philips Hue"),
            FakeConfigEntry("e_tuya", "tuya", "Tuya"),
            FakeConfigEntry("e_mobile", "mobile_app", "iPhone"),
            FakeConfigEntry("e_off", "demo", "Demo", ConfigEntryState.NOT_LOADED, disabled_by=DisabledBy.USER),
        ],
        "devices": [
            FakeDevice(
                id="d_bridge",
                config_entries={"e_hue"},
                primary_config_entry="e_hue",
                name="Hue Bridge",
                area_id="a_studio",
                connections={("mac", "00:17:88:AA:BB:CC")},
            ),
            FakeDevice(
                id="d_lamp",
                config_entries={"e_hue"},
                primary_config_entry="e_hue",
                name="Hue lamp",
                name_by_user="Living room light",
                via_device_id="d_bridge",
            ),
            FakeDevice(
                id="d_cam",
                config_entries={"e_tuya"},
                primary_config_entry="e_tuya",
                name="SmartCam",
                connections={("mac", "68:57:2D:99:88:77")},
            ),
            FakeDevice(
                id="d_off",
                config_entries={"e_hue"},
                primary_config_entry="e_hue",
                name="Retired lamp",
                disabled_by=DisabledBy.USER,
            ),
        ],
        "entities": [
            FakeEntity("sensor.bridge_ip", "d_bridge", "e_hue", "hue"),
            FakeEntity("light.salotto", "d_lamp", "e_hue", "hue"),
            FakeEntity("camera.cucina", "d_cam", "e_tuya", "tuya"),
            FakeEntity("switch.cucina", "d_cam", "e_tuya", "tuya", disabled_by=DisabledBy.USER),
            FakeEntity("notify.iphone", None, "e_mobile", "mobile_app"),
            FakeEntity("sensor.iphone_batteria", None, "e_mobile", "mobile_app"),
            FakeEntity("sensor.template", None, None, "template"),
        ],
        "areas": [FakeArea("a_studio", "Studio")],
        "integrations": [
            FakeIntegration("hue", {"name": "Hue", "iot_class": "local_push", "dependencies": []}),
            FakeIntegration("tuya", {"name": "Tuya", "iot_class": "cloud_push"}),
            FakeIntegration("mobile_app", {"name": "Mobile App", "iot_class": "cloud_push"}),
            FakeIntegration("demo", {"name": "Demo", "iot_class": "calculated"}),
        ],
    }


def scan_from_house(**overrides: Any):
    data = {**house(), **overrides}
    payload = native.payload_from_registries(**data)
    return build_scan(payload, generated_at=FROZEN_CLOCK, collector="native", ha_version="2026.8.1")


class TestConversion(unittest.TestCase):
    def test_enums_keep_their_value(self) -> None:
        entry = native.config_entry_to_dict(FakeConfigEntry("e", "d", "t"))
        self.assertEqual(entry["state"], "loaded")
        device = native.device_to_dict(FakeDevice("d", set(), disabled_by=DisabledBy.USER))
        self.assertEqual(device["disabled_by"], "user")

    def test_area_id_is_renamed_for_the_shared_payload(self) -> None:
        # An AreaEntry exposes `id`; the payload speaks `area_id`.
        self.assertEqual(native.area_to_dict(FakeArea("a1", "Studio")), {"area_id": "a1", "name": "Studio"})

    def test_connections_become_plain_pairs(self) -> None:
        device = native.device_to_dict(FakeDevice("d", set(), connections={("mac", "AA:BB")}))
        self.assertEqual(device["connections"], [["mac", "AA:BB"]])

    def test_unreadable_integration_is_dropped_not_defaulted(self) -> None:
        # async_get_integrations returns exceptions for what it could not load.
        self.assertIsNone(native.integration_to_dict(ImportError("boom")))
        self.assertIsNone(native.integration_to_dict(None))

    def test_config_entries_set_is_ordered_for_stability(self) -> None:
        device = native.device_to_dict(FakeDevice("d", {"z", "a", "m"}))
        self.assertEqual(device["config_entries"], ["a", "m", "z"])


class TestScanFromRegistries(unittest.TestCase):
    def setUp(self) -> None:
        self.scan = scan_from_house()

    def test_it_validates(self) -> None:
        self.assertEqual(validate(self.scan.to_dict()), [])

    def test_declared_only(self) -> None:
        self.assertEqual(self.scan.conduits, [])
        self.assertEqual(self.scan.collector, "native")
        self.assertEqual(self.scan.ha_version, "2026.8.1")

    def test_disabled_entry_and_device_are_dropped(self) -> None:
        self.assertEqual({i.id for i in self.scan.integrations}, {"e_hue", "e_tuya", "e_mobile"})
        self.assertEqual({d.id for d in self.scan.devices}, {"d_bridge", "d_lamp", "d_cam"})

    def test_manifest_supplies_the_iot_class(self) -> None:
        hue = self.scan.integration("e_hue")
        assert hue is not None
        self.assertEqual(hue.iot_class, "local_push")
        self.assertTrue(hue.is_built_in)

    def test_area_and_user_name_are_resolved(self) -> None:
        bridge = self.scan.device("d_bridge")
        lamp = self.scan.device("d_lamp")
        assert bridge is not None and lamp is not None
        self.assertEqual(bridge.area, "Studio")
        self.assertEqual(lamp.name, "Living room light")
        self.assertEqual(lamp.via_device_id, "d_bridge")

    def test_transport_hints_match_the_websocket_source(self) -> None:
        bridge = self.scan.device("d_bridge")
        lamp = self.scan.device("d_lamp")
        assert bridge is not None and lamp is not None
        self.assertEqual(bridge.transport, "ethernet")
        # Behind the bridge: the hub's radio, not the hub's uplink.
        self.assertEqual(lamp.transport, "zigbee")

    def test_device_less_entities_reach_their_integration(self) -> None:
        mobile = self.scan.integration("e_mobile")
        assert mobile is not None
        self.assertEqual(mobile.entity_count, 2)

    def test_disabled_entity_is_not_counted(self) -> None:
        camera = self.scan.device("d_cam")
        assert camera is not None
        self.assertEqual(camera.entity_count, 1)

    def test_ip_is_never_invented(self) -> None:
        self.assertTrue(all(device.ip is None for device in self.scan.devices))
        self.assertEqual(self.scan.correlation.devices_correlated, 2)  # only the two MACs

    def test_orphan_entities_are_declared_unverified(self) -> None:
        self.assertIn("unv.entities_outside_registry", {c.id for c in self.scan.unverified})

    def test_missing_manifest_lands_in_unverified(self) -> None:
        scan = scan_from_house(integrations=[])
        self.assertTrue(all(i.iot_class == "unknown" for i in scan.integrations))
        self.assertIn("unv.manifests_unavailable", {c.id for c in scan.unverified})

    def test_derivations_run_on_it(self) -> None:
        derived = derive(self.scan)
        self.assertEqual(derived.autonomy.entities_local, 2)  # hue: bridge 1 + lamp 1
        self.assertEqual(derived.autonomy.entities_cloud, 3)  # tuya 1 + mobile_app 2
        self.assertEqual(derived.matrix.local_egress, ())  # nothing observed yet

    def test_empty_house_is_valid(self) -> None:
        scan = scan_from_house(
            config_entries=[], devices=[], entities=[], areas=[], integrations=[]
        )
        self.assertEqual(validate(scan.to_dict()), [])
        self.assertEqual(scan.correlation.devices_total, 0)


if __name__ == "__main__":
    unittest.main()
