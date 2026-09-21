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
    SETUP_RETRY = "setup_retry"


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
        self.assertEqual([c for c in self.scan.conduits if c.evidence != "declared"], [])
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



class TestEntryEndpoint(unittest.TestCase):
    """Reading config entry data is what tells one broker from another. It is
    also where the passwords live, so the extraction has to stay narrow."""

    @staticmethod
    def endpoint(data: dict[str, Any]) -> dict[str, Any] | None:
        return native.entry_endpoint(types.SimpleNamespace(data=data))

    def test_it_reads_the_broker_an_entry_points_at(self) -> None:
        self.assertEqual(
            self.endpoint({"broker": "a0d7b954-emqx", "port": 1883}),
            {"host": "a0d7b954-emqx", "port": 1883, "authenticated": False},
        )

    def test_a_string_port_still_resolves(self) -> None:
        self.assertEqual(self.endpoint({"host": "10.0.0.4", "port": "8123"})["port"], 8123)

    def test_an_entry_with_no_address_yields_nothing(self) -> None:
        self.assertIsNone(self.endpoint({"username": "simon", "password": "hunter2"}))

    def test_credentials_never_come_out_with_the_address(self) -> None:
        endpoint = self.endpoint(
            {
                "broker": "core-mosquitto",
                "port": 1883,
                "username": "simon",
                "password": "hunter2",
                "api_key": "sk-live-0001",
                "access_token": "eyJhbGci",
            }
        )
        self.assertEqual(set(endpoint), {"host", "port", "authenticated"})
        # The fact that there are credentials, never one of them.
        self.assertIs(endpoint["authenticated"], True)
        self.assertNotIn("hunter2", str(endpoint))
        self.assertNotIn("simon", str(endpoint))
        self.assertNotIn("sk-live-0001", str(endpoint))


class TestAddressesFromStates(unittest.TestCase):
    """The MAC to IP pairs Home Assistant already holds. Without them, an
    install whose router does the DHCP correlates nothing at all."""

    @staticmethod
    def state(**attributes: Any) -> Any:
        return types.SimpleNamespace(attributes=attributes)

    def test_a_router_tracker_supplies_both_halves_of_the_join(self) -> None:
        found = native.state_address(self.state(mac="AA:BB:CC:11:22:33", ip="192.168.50.42"))
        self.assertEqual(found, {"mac": "aa:bb:cc:11:22:33", "ip": "192.168.50.42"})

    def test_the_dashed_form_is_the_same_mac(self) -> None:
        found = native.state_address(self.state(mac_address="AA-BB-CC-11-22-33", ip_address="10.0.0.9"))
        self.assertEqual(found["mac"], "aa:bb:cc:11:22:33")

    def test_half_a_pair_is_worth_nothing(self) -> None:
        self.assertIsNone(native.state_address(self.state(mac="aa:bb:cc:11:22:33")))
        self.assertIsNone(native.state_address(self.state(ip="192.168.50.42")))

    def test_a_hostname_is_not_an_address(self) -> None:
        """It would join with nothing and look like a correlation that worked."""
        self.assertIsNone(
            native.state_address(self.state(mac="aa:bb:cc:11:22:33", ip="nas.local"))
        )

    def test_one_row_per_mac(self) -> None:
        found = native.addresses_from_states(
            [
                self.state(mac="aa:bb:cc:11:22:33", ip="192.168.50.10"),
                self.state(mac="AA:BB:CC:11:22:33", ip="192.168.50.11"),
                self.state(friendly_name="no address here"),
            ]
        )
        self.assertEqual(found, [{"mac": "aa:bb:cc:11:22:33", "ip": "192.168.50.11"}])


class TestServiceEntries(unittest.TestCase):
    """A HACS repository and a Supervisor add-on are registry entries, not
    things attached to a network. Home Assistant says so itself."""

    def test_a_service_entry_is_virtual_not_undetermined(self) -> None:
        raw = native.device_to_dict(
            types.SimpleNamespace(
                id="d1",
                name="File editor",
                entry_type="service",
                connections=set(),
                identifiers={("hassio", "core_configurator")},
                config_entries={"e1"},
                primary_config_entry="e1",
                via_device_id=None,
                disabled_by=None,
                configuration_url=None,
            )
        )
        self.assertEqual(raw["entry_type"], "service")

    def test_the_configuration_url_is_carried_through(self) -> None:
        raw = native.device_to_dict(
            types.SimpleNamespace(
                id="d2",
                name="NAS",
                entry_type=None,
                connections=set(),
                identifiers=set(),
                config_entries={"e1"},
                primary_config_entry="e1",
                via_device_id=None,
                disabled_by=None,
                configuration_url="http://192.168.50.10:5000",
            )
        )
        self.assertEqual(raw["configuration_url"], "http://192.168.50.10:5000")

if __name__ == "__main__":
    unittest.main()


class TestEntryStreams(unittest.TestCase):
    """A camera's stream URL is the one config entry field that reliably
    carries a password. The scheme is the finding; the URL never comes out."""

    @staticmethod
    def streams(data: dict[str, Any], options: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return native.entry_streams(
            types.SimpleNamespace(data=data, options=options or {})
        )

    def test_rtsp_is_read_as_cleartext_with_its_default_port(self) -> None:
        found = self.streams({"stream_source": "rtsp://192.168.50.42/h264Preview_01_main"})
        self.assertEqual(
            found, [{"protocol": "rtsp", "host": "192.168.50.42", "port": 554, "encrypted": False}]
        )

    def test_rtsps_is_read_as_encrypted(self) -> None:
        found = self.streams({"stream_source": "rtsps://cam.example/stream"})
        self.assertIs(found[0]["encrypted"], True)
        self.assertEqual(found[0]["protocol"], "rtsps")

    def test_credentials_and_path_never_come_out(self) -> None:
        found = self.streams(
            {"stream_source": "rtsp://admin:hunter2@192.168.50.42:8554/h264Preview_01_main"}
        )
        self.assertEqual(
            found, [{"protocol": "rtsp", "host": "192.168.50.42", "port": 8554, "encrypted": False}]
        )
        for secret in ("admin", "hunter2", "h264Preview", "@"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, str(found))

    def test_the_options_are_read_too(self) -> None:
        """The generic camera integration keeps its stream in options."""
        found = self.streams({}, {"stream_source": "rtsp://10.0.0.9/live"})
        self.assertEqual(found[0]["host"], "10.0.0.9")

    def test_the_same_stream_named_twice_is_one_row(self) -> None:
        found = self.streams(
            {
                "stream_source": "rtsp://10.0.0.9:554/live",
                "rtsp_url": "rtsp://10.0.0.9:554/other",
            }
        )
        self.assertEqual(len(found), 1)

    def test_a_scheme_that_is_not_a_stream_is_ignored(self) -> None:
        self.assertEqual(self.streams({"stream_source": "file:///tmp/x.mp4"}), [])
        self.assertEqual(self.streams({"stream_source": "not a url"}), [])
        self.assertEqual(self.streams({"stream_source": ""}), [])

    def test_a_malformed_authority_yields_nothing_rather_than_raising(self) -> None:
        self.assertEqual(self.streams({"stream_source": "rtsp://host:notaport/live"}), [])

    def test_an_entry_with_no_stream_yields_nothing(self) -> None:
        self.assertEqual(self.streams({"host": "10.0.0.9", "password": "x"}), [])


class TestRegistryEntries(unittest.TestCase):
    """Issue 1, minor: Home Assistant 2026.9 deprecates reading the device
    registry as a mapping. The adapter never touches it as one on cores
    where iteration yields entries, and falls back only where it yields
    keys, which was never deprecated."""

    def test_a_new_core_yields_entries_on_iteration(self) -> None:
        class NewStyle:
            def __init__(self, entries: list[Any]) -> None:
                self._entries = entries

            def __iter__(self):
                return iter(self._entries)

            def values(self):  # pragma: no cover - must not be called
                raise AssertionError("mapping access on a new core")

        entries = [FakeDevice(id="d1", config_entries=set()), FakeDevice(id="d2", config_entries=set())]
        self.assertEqual([d.id for d in native.registry_entries(NewStyle(entries))], ["d1", "d2"])

    def test_an_old_core_yields_keys_and_is_read_by_values(self) -> None:
        old = {"d1": FakeDevice(id="d1", config_entries=set()), "d2": FakeDevice(id="d2", config_entries=set())}
        self.assertEqual([d.id for d in native.registry_entries(old)], ["d1", "d2"])

    def test_empty_either_way(self) -> None:
        self.assertEqual(native.registry_entries({}), [])
        self.assertEqual(native.registry_entries([]), [])


class TestProcessUptime(unittest.TestCase):
    """The one piece of parsing in the change, pinned with a crafted /proc so
    a wrong field index or a broken split fails on every platform."""

    def _run(self, stat: bytes, booted: float, hertz: int = 100) -> Any:
        import builtins
        from unittest import mock

        real_open = builtins.open

        def fake_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            if str(path) == "/proc/self/stat":
                import io

                return io.BytesIO(stat)
            return real_open(path, *args, **kwargs)

        # A stand-in for the time module: macOS has no CLOCK_BOOTTIME, and
        # the function must read the clock through the module attribute.
        clock = types.SimpleNamespace(CLOCK_BOOTTIME=7, clock_gettime=lambda which: booted)
        with mock.patch("builtins.open", fake_open), mock.patch.object(
            native.os, "sysconf", lambda name: hertz
        ), mock.patch.object(native, "time", clock):
            return native.process_uptime_seconds()

    def test_start_time_is_field_22_after_a_comm_with_brackets(self) -> None:
        # comm is "py (weird) thon 3": the split has to happen at the LAST
        # closing bracket. Field 22 (starttime) is 500000 ticks at 100 Hz.
        fields = ["S", "1", "1", "1", "0", "-1", "4194560", "0", "0", "0", "0", "1", "1", "0", "0",
                  "20", "0", "1", "0", "500000", "1000", "100", "0"]
        stat = b"4242 (py (weird) thon 3) " + " ".join(fields).encode()
        self.assertAlmostEqual(self._run(stat, booted=6000.25), 1000.25)

    def test_disagreeing_clocks_are_unknown_not_zero(self) -> None:
        # lxcfs rewrites the boot clock to the container's age while the
        # start time stays host relative: negative age, so unknown.
        fields = ["S"] + ["0"] * 18 + ["500000", "0", "0", "0"]
        stat = b"1 (hass) " + " ".join(fields).encode()
        self.assertIsNone(self._run(stat, booted=400.0))

    def test_is_a_non_negative_float_or_none_for_real(self) -> None:
        uptime = native.process_uptime_seconds()
        self.assertTrue(uptime is None or uptime >= 0.0)


class TestDeviceConfigEntry(unittest.TestCase):
    """2026.8 gave a device one config_entry_id and deprecated the two older
    properties. The new one is read where it exists, the old ones only
    where it does not, and the payload keys stay the same."""

    def test_new_core_uses_config_entry_id_and_never_the_shims(self) -> None:
        class NewDevice:
            id = "d1"
            config_entry_id = "entry_a"

            @property
            def config_entries(self):  # pragma: no cover - must not be called
                raise AssertionError("deprecated shim touched")

            @property
            def primary_config_entry(self):  # pragma: no cover - must not be called
                raise AssertionError("deprecated shim touched")

        payload = native.device_to_dict(NewDevice())
        self.assertEqual(payload["config_entries"], ["entry_a"])
        self.assertEqual(payload["primary_config_entry"], "entry_a")

    def test_old_core_falls_back_to_the_set(self) -> None:
        device = FakeDevice(id="d2", config_entries={"entry_b", "entry_a"})
        payload = native.device_to_dict(device)
        self.assertEqual(payload["config_entries"], ["entry_a", "entry_b"])


class TestIgnoredEntries(unittest.TestCase):
    """Issue 1, cause 3: a dismissed discovery has source "ignore" and never
    loads by design. It is a user decision, not a fault."""

    def test_source_reaches_the_model(self) -> None:
        scan = scan_from_house()
        self.assertTrue(all(i.source for i in scan.integrations))

    def test_an_ignored_entry_is_not_a_not_loaded_finding(self) -> None:
        from talos_core import derive

        data = house()
        data["config_entries"] = data["config_entries"] + [
            FakeConfigEntry(entry_id="zha_dismissed", domain="zha", title="ZHA",
                            state=ConfigEntryState.NOT_LOADED, source="ignore"),
            FakeConfigEntry(entry_id="printer", domain="ipp", title="Printer",
                            state=ConfigEntryState.SETUP_RETRY, source="user"),
        ]
        payload = native.payload_from_registries(**data)
        scan = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native",
                          ha_version="2026.9.3", ha_uptime_seconds=3600.0)
        failed = {c.id: c for c in derive(scan).checks.failed}
        subjects = list(failed["chk.integration_not_loaded"].subjects)
        self.assertIn("printer", subjects)
        self.assertNotIn("zha_dismissed", subjects)

    def test_a_young_system_withholds_the_check(self) -> None:
        from talos_core import derive

        data = house()
        data["config_entries"] = data["config_entries"] + [
            FakeConfigEntry(entry_id="printer", domain="ipp", title="Printer",
                            state=ConfigEntryState.SETUP_RETRY, source="user"),
        ]
        payload = native.payload_from_registries(**data)
        young = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native", ha_uptime_seconds=60.0)
        report = derive(young).checks
        self.assertIn("chk.integration_not_loaded", {c.id for c in report.unverified})
        self.assertNotIn("chk.integration_not_loaded", {c.id for c in report.failed})
        # Unknown uptime, as in a CLI document, does not withhold it.
        unknown = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")
        self.assertIn("chk.integration_not_loaded", {c.id for c in derive(unknown).checks.failed})
