"""Declarative-source tests, driven by recorded WebSocket payloads.

No network and no Home Assistant: a fake transport replays the fixture and
refuses anything it was not given, which is also how the command fallbacks
get exercised.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import Scan, derive, validate
from talos_core.const import INTERNAL_DESTINATION_KINDS
from talos_core.sources import (
    CommandError,
    CommandTransport,
    RegistryPayload,
    SourceError,
    WebSocketSource,
    build_scan,
)

FIXTURES = Path(__file__).parent / "fixtures"
FROZEN_CLOCK = "2026-08-30T07:14:02+00:00"


def registry() -> dict[str, Any]:
    return json.loads((FIXTURES / "ha_registry.json").read_text(encoding="utf-8"))


class FakeTransport:
    """Replays recorded results and refuses every other command."""

    def __init__(self, responses: dict[str, Any], ha_version: str | None = None) -> None:
        self._responses = responses
        self._ha_version = ha_version
        self.sent: list[str] = []

    @property
    def ha_version(self) -> str | None:
        return self._ha_version

    async def send(self, command: dict[str, Any]) -> Any:
        name = command["type"]
        self.sent.append(name)
        if name not in self._responses:
            raise CommandError(name, "unknown command", "unknown_command")
        return self._responses[name]


def collect(transport: CommandTransport) -> Scan:
    source = WebSocketSource(transport, clock=lambda: FROZEN_CLOCK)
    return asyncio.run(source.fetch())


class TestTransportContract(unittest.TestCase):
    def test_fake_satisfies_the_protocol(self) -> None:
        self.assertIsInstance(FakeTransport({}), CommandTransport)


class TestWebSocketCollection(unittest.TestCase):
    def setUp(self) -> None:
        data = registry()
        self.transport = FakeTransport(data["responses"], data["ha_version"])
        self.scan = collect(self.transport)

    def test_scan_validates(self) -> None:
        self.assertEqual(validate(self.scan.to_dict()), [])

    def test_declared_only(self) -> None:
        # Nothing has been observed yet, and a manifest never names a host.
        # The local radio links are declared, so they are here: what must not
        # be is anything claiming to have been seen on the wire.
        self.assertEqual([c for c in self.scan.conduits if c.evidence != "declared"], [])
        self.assertEqual(
            [d for d in self.scan.destinations if d.kind not in INTERNAL_DESTINATION_KINDS], []
        )
        self.assertEqual(self.scan.collector, "websocket")
        self.assertEqual(self.scan.ha_version, "2026.8.1")
        self.assertEqual(self.scan.generated_at, FROZEN_CLOCK)

    def test_disabled_config_entry_is_dropped(self) -> None:
        ids = {i.id for i in self.scan.integrations}
        self.assertEqual(len(ids), 6)
        self.assertNotIn("e_off", ids)

    def test_integration_without_a_manifest_stays_unknown(self) -> None:
        custom = self.scan.integration("e_custom")
        assert custom is not None
        self.assertEqual(custom.iot_class, "unknown")
        # Absent a manifest we cannot claim it ships with Home Assistant.
        self.assertFalse(custom.is_built_in)
        self.assertIn(
            "unv.manifests_unavailable", {check.id for check in self.scan.unverified}
        )

    def test_devices_kept_and_dropped(self) -> None:
        ids = {d.id for d in self.scan.devices}
        self.assertEqual(
            ids,
            {
                "d_cam1", "d_bridge", "d_lamp", "d_tuya",
                "d_z2m", "d_z2m_bridge", "d_child_of_disabled",
            },
        )
        self.assertNotIn("d_disabled", ids)  # switched off
        self.assertNotIn("d_orphan", ids)  # its config entry is gone

    def test_dangling_via_device_is_cleared(self) -> None:
        # Its hub was dropped, so the reference has to go with it rather than
        # become a broken pointer the validator would reject.
        child = self.scan.device("d_child_of_disabled")
        assert child is not None
        self.assertIsNone(child.via_device_id)

        lamp = self.scan.device("d_lamp")
        assert lamp is not None
        self.assertEqual(lamp.via_device_id, "d_bridge")

    def test_user_given_name_wins(self) -> None:
        camera = self.scan.device("d_cam1")
        assert camera is not None
        self.assertEqual(camera.name, "Garden camera")
        self.assertEqual(camera.area, "Garden")

    def test_mac_is_normalised_and_ip_is_never_invented(self) -> None:
        camera = self.scan.device("d_cam1")
        assert camera is not None
        self.assertEqual(camera.mac, "ec:71:db:11:22:33")
        # A device registry carries no address; the IP arrives with the leases.
        self.assertTrue(all(d.ip is None for d in self.scan.devices))

    def test_transport_hints(self) -> None:
        by_id = {d.id: d.transport for d in self.scan.devices}
        self.assertEqual(by_id["d_cam1"], "wifi")  # from the domain
        # Arrives through MQTT, which says nothing: only the identifier does.
        self.assertEqual(by_id["d_z2m"], "zigbee")
        self.assertEqual(by_id["d_z2m_bridge"], "zigbee")
        self.assertEqual(by_id["d_bridge"], "ethernet")
        # Behind the bridge: the transport is the hub's radio, not the hub's
        # own uplink. A Hue bridge is on ethernet and speaks Zigbee.
        self.assertEqual(by_id["d_lamp"], "zigbee")
        # Its hub was dropped and nothing else says what it is.
        self.assertEqual(by_id["d_child_of_disabled"], "unknown")

    def test_entity_counts_per_device(self) -> None:
        by_id = {d.id: d.entity_count for d in self.scan.devices}
        self.assertEqual(by_id["d_cam1"], 3)  # the fourth is disabled
        self.assertEqual(by_id["d_lamp"], 1)

    def test_device_less_entities_are_credited_to_their_integration(self) -> None:
        mobile = self.scan.integration("e_mobileapp")
        assert mobile is not None
        self.assertEqual(mobile.entity_count, 3)
        self.assertEqual([d for d in self.scan.devices if d.integration_id == "e_mobileapp"], [])

    def test_entities_of_dropped_devices_are_not_counted(self) -> None:
        reolink = self.scan.integration("e_reolink")
        assert reolink is not None
        self.assertEqual(reolink.entity_count, 3)  # the disabled camera's entity is gone

    def test_entities_outside_the_registry_are_declared_unverified(self) -> None:
        checks = {check.id: check for check in self.scan.unverified}
        self.assertIn("unv.entities_outside_registry", checks)
        self.assertEqual(checks["unv.entities_outside_registry"].reason, "missing_data")

    def test_correlation_counts_joinable_devices(self) -> None:
        # Only three devices carry a MAC the observed side could join on.
        self.assertEqual(self.scan.correlation.devices_total, 7)
        self.assertEqual(self.scan.correlation.devices_correlated, 3)


class TestCommandFallbacks(unittest.TestCase):
    def test_falls_back_to_the_older_command_name(self) -> None:
        data = registry()
        responses = dict(data["responses"])
        responses["config_entries/list"] = responses.pop("config_entries/get")
        transport = FakeTransport(responses, data["ha_version"])
        scan = collect(transport)
        self.assertEqual(len(scan.integrations), 6)
        self.assertIn("config_entries/get", transport.sent)  # tried first
        self.assertIn("config_entries/list", transport.sent)

    def test_missing_manifests_degrade_instead_of_failing(self) -> None:
        data = registry()
        responses = {k: v for k, v in data["responses"].items() if k != "manifest/list"}
        scan = collect(FakeTransport(responses, data["ha_version"]))
        self.assertTrue(all(i.iot_class == "unknown" for i in scan.integrations))
        self.assertIn("unv.manifest_list_unreadable", {c.id for c in scan.unverified})
        self.assertEqual(validate(scan.to_dict()), [])

    def test_missing_entity_registry_degrades_loudly(self) -> None:
        data = registry()
        responses = {
            k: v
            for k, v in data["responses"].items()
            if not k.startswith("config/entity_registry")
        }
        scan = collect(FakeTransport(responses, data["ha_version"]))
        self.assertTrue(all(i.entity_count == 0 for i in scan.integrations))
        check = next(c for c in scan.unverified if c.id == "unv.entity_registry_unreadable")
        # The point of the note: zero must not read as "nothing at risk".
        self.assertIn("nothing at risk", check.detail)

    def test_missing_device_registry_is_fatal(self) -> None:
        data = registry()
        responses = {
            k: v for k, v in data["responses"].items() if k != "config/device_registry/list"
        }
        with self.assertRaises(SourceError):
            collect(FakeTransport(responses, data["ha_version"]))

    def test_result_wrapped_in_an_object_is_unwrapped(self) -> None:
        data = registry()
        responses = dict(data["responses"])
        responses["config/area_registry/list"] = {
            "entries": responses["config/area_registry/list"]
        }
        scan = collect(FakeTransport(responses, data["ha_version"]))
        self.assertEqual(scan.device("d_cam1").area, "Garden")  # type: ignore[union-attr]


class TestDeclaredOnlyDerivations(unittest.TestCase):
    """A declared-only scan must still derive something honest."""

    def setUp(self) -> None:
        data = registry()
        self.derived = derive(collect(FakeTransport(data["responses"], data["ha_version"])))

    def test_matrix_has_no_egress_column(self) -> None:
        self.assertEqual(self.derived.matrix.local_egress, ())
        self.assertEqual(self.derived.matrix.cloud_egress, ())
        self.assertEqual(self.derived.matrix.inherited, ())

    def test_unknown_iot_class_lands_in_its_own_bucket(self) -> None:
        # The integration with no manifest must not be counted as local.
        self.assertEqual(self.derived.autonomy.entities_unclassified, 0)
        self.assertEqual(self.derived.autonomy.entities_cloud, 5)  # tuya 2 + mobile_app 3
        # reolink 3 + hue 3 + mqtt 4
        self.assertEqual(self.derived.autonomy.entities_local, 10)
        self.assertEqual(self.derived.autonomy.entities_total, 15)

    def test_losses_fall_back_to_the_integration_title(self) -> None:
        # Nothing declares a destination yet, so the vendor label is the name
        # the user would recognise rather than an invented hostname.
        vendors = {loss.vendor for loss in self.derived.autonomy.losses}
        self.assertEqual(vendors, {"Tuya", "Alessandro's iPhone"})

    def test_exposure_is_empty_not_reassuring(self) -> None:
        self.assertEqual(self.derived.exposure.vendors, ())
        self.assertEqual(self.derived.exposure.devices_direct, ())
        self.assertGreaterEqual(self.derived.unverified_count, 2)


class TestBuildScanDirectly(unittest.TestCase):
    def test_empty_payload_produces_a_valid_empty_scan(self) -> None:
        scan = build_scan(RegistryPayload(), generated_at=FROZEN_CLOCK)
        self.assertEqual(validate(scan.to_dict()), [])
        self.assertEqual(scan.correlation.devices_total, 0)

    def test_mapping_does_not_mutate_its_input(self) -> None:
        data = registry()["responses"]
        payload = RegistryPayload(
            config_entries=data["config_entries/get"],
            devices=data["config/device_registry/list"],
            entities=data["config/entity_registry/list"],
            areas=data["config/area_registry/list"],
            manifests=data["manifest/list"],
        )
        before = json.dumps(data, sort_keys=True)
        build_scan(payload, generated_at=FROZEN_CLOCK)
        self.assertEqual(json.dumps(data, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()


class TestTransportDetection(unittest.TestCase):
    """The bus a device arrives on is not the radio it speaks.

    Zigbee2MQTT is the case that matters: its devices reach Home Assistant
    through the MQTT integration, so the config entry says `mqtt` and only the
    device identifier says Zigbee.
    """

    def scan_with(self, device: dict[str, Any]) -> Any:
        data = registry()
        responses = {key: list(value) for key, value in data["responses"].items()}
        responses["config/device_registry/list"] = [
            *responses["config/device_registry/list"],
            {
                "name": "probe", "name_by_user": None, "manufacturer": None,
                "model": None, "area_id": None, "config_entries": ["e_mqtt"],
                "primary_config_entry": "e_mqtt", "connections": [],
                "identifiers": [], "via_device_id": None, "disabled_by": None,
                **device,
            },
        ]

        class Replay:
            ha_version = data["ha_version"]

            async def send(self, command: dict[str, Any]) -> Any:
                name = command["type"]
                if name not in responses:
                    raise CommandError(name, "unknown command", "unknown_command")
                return responses[name]

        return collect(Replay())

    def transport_of(self, device: dict[str, Any]) -> str:
        scan = self.scan_with(device)
        found = scan.device(device["id"])
        assert found is not None
        return found.transport

    def test_mqtt_alone_says_nothing(self) -> None:
        # A bus carries anything; guessing here would be inventing.
        self.assertEqual(self.transport_of({"id": "p1"}), "unknown")

    def test_zigbee2mqtt_identifier_is_evidence(self) -> None:
        self.assertEqual(
            self.transport_of(
                {"id": "p2", "identifiers": [["mqtt", "zigbee2mqtt_0x00158d00012345"]]}
            ),
            "zigbee",
        )

    def test_identifier_matches_on_the_prefix_not_anywhere(self) -> None:
        # A device merely named after a protocol is not one.
        self.assertEqual(
            self.transport_of({"id": "p3", "identifiers": [["mqtt", "my_zigbee2mqtt_clone"]]}),
            "unknown",
        )

    def test_a_connection_type_outranks_an_identifier(self) -> None:
        self.assertEqual(
            self.transport_of(
                {
                    "id": "p4",
                    "connections": [["zwave", "12"]],
                    "identifiers": [["mqtt", "zigbee2mqtt_0x1"]],
                }
            ),
            "zwave",
        )

    def test_a_child_takes_the_hubs_radio(self) -> None:
        # The Hue bridge is on ethernet and speaks Zigbee to its bulbs.
        self.assertEqual(
            self.transport_of(
                {"id": "p5", "config_entries": ["e_hue"], "primary_config_entry": "e_hue",
                 "via_device_id": "d_bridge"}
            ),
            "zigbee",
        )

    def test_a_child_inherits_a_radio_the_hub_was_found_to_speak(self) -> None:
        # The bridge resolved to Zigbee from its own identifier; whatever hangs
        # off it is on Zigbee too, whatever bus carried the discovery message.
        self.assertEqual(
            self.transport_of({"id": "p6", "via_device_id": "d_z2m_bridge"}), "zigbee"
        )

    def test_a_child_of_a_hub_with_no_known_radio_stays_unknown(self) -> None:
        # d_child_of_disabled has no transport of its own, so it passes none on.
        self.assertEqual(
            self.transport_of({"id": "p7", "via_device_id": "d_child_of_disabled"}), "unknown"
        )


class TestOriginDetection(unittest.TestCase):
    """An integration can be fed by more than one system.

    An MQTT entry carries Zigbee2MQTT and a SwitchBot bridge at the same time.
    The integration is the bus; the origin is what produced the device, and it
    is only recorded when the two differ.
    """

    def origin_of(self, device: dict[str, Any]) -> str | None:
        data = registry()
        responses = {key: list(value) for key, value in data["responses"].items()}
        responses["config/device_registry/list"] = [
            *responses["config/device_registry/list"],
            {
                "name": "probe", "name_by_user": None, "manufacturer": None,
                "model": None, "area_id": None, "config_entries": ["e_mqtt"],
                "primary_config_entry": "e_mqtt", "connections": [],
                "identifiers": [], "via_device_id": None, "disabled_by": None,
                **device,
            },
        ]

        class Replay:
            ha_version = data["ha_version"]

            async def send(self, command: dict[str, Any]) -> Any:
                name = command["type"]
                if name not in responses:
                    raise CommandError(name, "unknown command", "unknown_command")
                return responses[name]

        scan = collect(Replay())
        found = scan.device(device["id"])
        assert found is not None
        return found.origin

    def test_zigbee2mqtt_is_recorded_as_the_origin(self) -> None:
        self.assertEqual(
            self.origin_of({"id": "o1", "identifiers": [["mqtt", "zigbee2mqtt_0x1"]]}),
            "zigbee2mqtt",
        )

    def test_two_systems_on_one_entry_are_told_apart(self) -> None:
        self.assertEqual(
            self.origin_of({"id": "o2", "identifiers": [["mqtt", "switchbot_ab12"]]}),
            "switchbot",
        )

    def test_nothing_recorded_when_the_integration_is_the_source(self) -> None:
        # An ESPHome device under the ESPHome entry adds nothing to say.
        self.assertIsNone(
            self.origin_of(
                {
                    "id": "o3",
                    "config_entries": ["e_mqtt"],
                    "identifiers": [["mqtt", "nothing_we_know"]],
                }
            )
        )

    def test_the_field_stays_absent_for_ordinary_devices(self) -> None:
        self.assertIsNone(self.origin_of({"id": "o4"}))


class TestDeclaredEndpoints(unittest.TestCase):
    """A config entry that names its broker is the only way to tell two
    brokers apart. Nothing here is probed: it is what the entry states."""

    @staticmethod
    def scan_for(*entries: dict[str, Any]) -> Scan:
        payload = RegistryPayload(
            config_entries=list(entries),
            devices=[],
            entities=[],
            areas=[],
            manifests=[
                {"domain": entry["domain"], "iot_class": "local_push", "is_built_in": True}
                for entry in entries
            ],
        )
        return build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")

    def test_the_named_broker_becomes_a_declared_conduit(self) -> None:
        scan = self.scan_for(
            {
                "entry_id": "e_mqtt",
                "domain": "mqtt",
                "title": "EMQX",
                "state": "loaded",
                "endpoint": {"host": "a0d7b954-emqx", "port": 1883},
            }
        )
        self.assertEqual(len(scan.conduits), 1)
        conduit = scan.conduits[0]
        self.assertEqual(conduit.evidence, "declared")
        self.assertEqual(conduit.source.kind, "integration")
        self.assertEqual(conduit.source.id, "e_mqtt")
        self.assertEqual(conduit.port, 1883)
        self.assertEqual(scan.destination(conduit.destination_id).fqdn, "a0d7b954-emqx")
        self.assertEqual(validate(scan.to_dict()), [])

    def test_two_brokers_stay_two_destinations(self) -> None:
        scan = self.scan_for(
            {
                "entry_id": "e_emqx",
                "domain": "mqtt",
                "state": "loaded",
                "endpoint": {"host": "a0d7b954-emqx", "port": 1883},
            },
            {
                "entry_id": "e_mosq",
                "domain": "mqtt",
                "state": "setup_retry",
                "endpoint": {"host": "core-mosquitto", "port": 1883},
            },
        )
        by_source = {c.source.id: scan.destination(c.destination_id).fqdn for c in scan.conduits}
        self.assertEqual(by_source, {"e_emqx": "a0d7b954-emqx", "e_mosq": "core-mosquitto"})

    def test_a_host_off_the_network_is_not_called_local(self) -> None:
        scan = self.scan_for(
            {
                "entry_id": "e_cloud",
                "domain": "tuya",
                "state": "loaded",
                "endpoint": {"host": "openapi.tuyaeu.com", "port": 443},
            }
        )
        self.assertNotIn(scan.destinations[0].kind, INTERNAL_DESTINATION_KINDS)

    def test_an_entry_that_names_nothing_produces_nothing(self) -> None:
        scan = self.scan_for(
            {"entry_id": "e_matter", "domain": "matter", "state": "loaded", "endpoint": None}
        )
        self.assertEqual(list(scan.conduits), [])
        self.assertEqual(list(scan.destinations), [])

    def test_the_websocket_source_says_it_cannot_read_them(self) -> None:
        data = registry()
        scan = collect(FakeTransport(data["responses"], data["ha_version"]))
        self.assertIn(
            "unv.entry_endpoints_unavailable", {note.id for note in scan.unverified}
        )


class TestTransportEvidence(unittest.TestCase):
    """How a device is attached, from what the registry actually holds. The
    case that matters is Zigbee2MQTT: it arrives through MQTT, and MQTT is a
    bus, so the domain says nothing about the radio."""

    @staticmethod
    def transports(*devices: dict[str, Any]) -> dict[str, str]:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_mqtt", "domain": "mqtt", "state": "loaded", "endpoint": None}
            ],
            devices=[{"config_entries": ["e_mqtt"], "primary_config_entry": "e_mqtt", **d}
                     for d in devices],
            entities=[],
            areas=[],
            manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
        )
        scan = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")
        return {device.id: device.transport for device in scan.devices}

    def test_a_bare_ieee_address_names_the_radio(self) -> None:
        found = self.transports({"id": "d", "identifiers": [["mqtt", "0x00158d0001234567"]]})
        self.assertEqual(found["d"], "zigbee")

    def test_something_merely_hexadecimal_is_not_an_ieee_address(self) -> None:
        found = self.transports({"id": "d", "identifiers": [["mqtt", "0xdeadbeef"]]})
        self.assertEqual(found["d"], "unknown")

    def test_a_mac_says_the_device_is_on_ip_and_no_more(self) -> None:
        found = self.transports(
            {"id": "d", "identifiers": [["mqtt", "gw"]], "connections": [["mac", "AA:BB:CC:00:11:22"]]}
        )
        self.assertEqual(found["d"], "ip")

    def test_an_address_to_open_counts_the_same(self) -> None:
        found = self.transports(
            {"id": "d", "identifiers": [["mqtt", "nas"]],
             "configuration_url": "http://192.168.50.10:5000"}
        )
        self.assertEqual(found["d"], "ip")

    def test_no_evidence_stays_unknown(self) -> None:
        found = self.transports({"id": "d", "identifiers": [["mqtt", "x1"]]})
        self.assertEqual(found["d"], "unknown")

    def test_a_leaf_takes_the_radio_and_the_system_of_its_bridge(self) -> None:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_mqtt", "domain": "mqtt", "state": "loaded", "endpoint": None}
            ],
            devices=[
                {"id": "brg", "name": "Zigbee2MQTT Bridge", "config_entries": ["e_mqtt"],
                 "primary_config_entry": "e_mqtt",
                 "identifiers": [["mqtt", "zigbee2mqtt_bridge_0x001788"]], "via_device_id": None},
                {"id": "leaf", "name": "Door sensor", "config_entries": ["e_mqtt"],
                 "primary_config_entry": "e_mqtt", "identifiers": [["mqtt", "sensor-7"]],
                 "via_device_id": "brg"},
            ],
            entities=[],
            areas=[],
            manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
        )
        scan = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")
        leaf = next(device for device in scan.devices if device.id == "leaf")
        self.assertEqual(leaf.transport, "zigbee")
        # The bus underneath is MQTT; the system that produced it is not.
        self.assertEqual(leaf.origin, "zigbee2mqtt")


class TestKnownAddresses(unittest.TestCase):
    """An address Home Assistant already holds lands on the device, so the
    observed side has something to join against without DHCP leases."""

    @staticmethod
    def build(addresses: list[dict[str, Any]]) -> Scan:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e1", "domain": "asuswrt", "state": "loaded", "endpoint": None}
            ],
            devices=[
                {"id": "d1", "name": "Laptop", "config_entries": ["e1"],
                 "primary_config_entry": "e1", "identifiers": [],
                 "connections": [["mac", "AA:BB:CC:11:22:33"]]},
                {"id": "d2", "name": "Nothing known", "config_entries": ["e1"],
                 "primary_config_entry": "e1", "identifiers": [["asuswrt", "x"]],
                 "connections": []},
            ],
            entities=[],
            areas=[],
            manifests=[{"domain": "asuswrt", "iot_class": "local_polling", "is_built_in": True}],
            addresses=addresses,
        )
        return build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")

    def test_the_address_reaches_the_device_with_that_mac(self) -> None:
        scan = self.build([{"mac": "aa:bb:cc:11:22:33", "ip": "192.168.50.42"}])
        self.assertEqual({d.id: d.ip for d in scan.devices}, {"d1": "192.168.50.42", "d2": None})

    def test_nothing_is_invented_for_a_device_nobody_tracks(self) -> None:
        scan = self.build([])
        self.assertEqual([d.ip for d in scan.devices], [None, None])
        self.assertEqual(validate(scan.to_dict()), [])


class TestServiceEntriesAreVirtual(unittest.TestCase):
    def test_home_assistant_saying_service_settles_the_transport(self) -> None:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e1", "domain": "hassio", "state": "loaded", "endpoint": None}
            ],
            devices=[
                {"id": "d1", "name": "File editor", "config_entries": ["e1"],
                 "primary_config_entry": "e1", "entry_type": "service",
                 "identifiers": [["hassio", "core_configurator"]], "connections": []},
            ],
            entities=[],
            areas=[],
            manifests=[{"domain": "hassio", "iot_class": None, "is_built_in": True}],
        )
        scan = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")
        self.assertEqual(scan.devices[0].transport, "virtual")


class TestEntityCountInvariant(unittest.TestCase):
    """An integration's total has to be at least the sum of its devices.
    The validator enforces it as TALOS-C010, so the mapping has to hold it."""

    def test_an_entity_owned_elsewhere_still_counts_for_both(self) -> None:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_mqtt", "domain": "mqtt", "state": "loaded", "endpoint": None},
                {"entry_id": "e_helper", "domain": "template", "state": "loaded"},
            ],
            devices=[
                {"id": "d1", "name": "Sensor", "config_entries": ["e_mqtt"],
                 "primary_config_entry": "e_mqtt", "identifiers": [["mqtt", "s1"]],
                 "connections": []},
            ],
            entities=[
                # Sits on the MQTT device, but names the helper entry.
                {"entity_id": "sensor.a", "device_id": "d1", "config_entry_id": "e_helper"},
                {"entity_id": "sensor.b", "device_id": "d1", "config_entry_id": "e_mqtt"},
            ],
            areas=[],
            manifests=[
                {"domain": "mqtt", "iot_class": "local_push", "is_built_in": True},
                {"domain": "template", "iot_class": "local_push", "is_built_in": True},
            ],
        )
        scan = build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")
        counts = {i.id: i.entity_count for i in scan.integrations}
        self.assertEqual(scan.devices[0].entity_count, 2)
        self.assertEqual(counts["e_mqtt"], 2)
        self.assertEqual(counts["e_helper"], 1)
        self.assertEqual(validate(scan.to_dict()), [])


class TestDeclaredStreams(unittest.TestCase):
    """A camera entry names its stream, and the scheme is the finding. The
    URL itself is the one field in a config entry that reliably carries a
    password, so it must never reach the document."""

    @staticmethod
    def scan_for(*streams: dict[str, Any]) -> Scan:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_cam", "domain": "generic", "title": "Ingresso",
                 "state": "loaded", "endpoint": None, "streams": list(streams)}
            ],
            devices=[],
            entities=[],
            areas=[],
            manifests=[{"domain": "generic", "iot_class": "local_polling", "is_built_in": True}],
        )
        return build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")

    def test_a_cleartext_stream_becomes_a_declared_conduit(self) -> None:
        scan = self.scan_for(
            {"protocol": "rtsp", "host": "192.168.50.42", "port": 554, "encrypted": False}
        )
        conduit = next(c for c in scan.conduits if c.protocol == "rtsp")
        self.assertEqual(conduit.evidence, "declared")
        self.assertIs(conduit.encrypted, False)
        self.assertEqual(conduit.port, 554)
        self.assertEqual(scan.destination(conduit.destination_id).fqdn, "192.168.50.42")
        self.assertEqual(validate(scan.to_dict()), [])

    def test_an_encrypted_stream_is_recorded_and_not_reported(self) -> None:
        scan = self.scan_for(
            {"protocol": "rtsps", "host": "192.168.50.42", "port": 322, "encrypted": True}
        )
        conduit = next(c for c in scan.conduits if c.protocol == "rtsps")
        self.assertIs(conduit.encrypted, True)
        self.assertNotIn("chk.rtsp_cleartext", {r.id for r in derive(scan).checks.failed})

    def test_the_cleartext_one_is_reported(self) -> None:
        scan = self.scan_for(
            {"protocol": "rtsp", "host": "192.168.50.42", "port": 554, "encrypted": False}
        )
        result = next(r for r in derive(scan).checks.failed if r.id == "chk.rtsp_cleartext")
        self.assertEqual(result.severity, "medium")
        self.assertEqual(result.subjects, ("e_cam",))

    def test_an_entry_naming_no_stream_produces_none(self) -> None:
        scan = self.scan_for()
        self.assertEqual([c for c in scan.conduits if c.protocol], [])

    def test_the_document_never_carries_the_stream_url(self) -> None:
        scan = self.scan_for(
            {"protocol": "rtsp", "host": "192.168.50.42", "port": 554, "encrypted": False}
        )
        document = json.dumps(scan.to_dict())
        for secret in ("admin", "password", "h264Preview", "@"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, document)


class TestLocalLinks(unittest.TestCase):
    """A radio is a conduit. A Zigbee lamp exchanges data with its
    coordinator constantly and never touches IP, so before this it appeared
    in no view built on conduits, which said the branch was not there."""

    @staticmethod
    def scan_for(*devices: dict[str, Any]) -> Scan:
        payload = RegistryPayload(
            config_entries=[
                {"entry_id": "e_mqtt", "domain": "mqtt", "state": "loaded", "endpoint": None}
            ],
            devices=[{"config_entries": ["e_mqtt"], "primary_config_entry": "e_mqtt", **d}
                     for d in devices],
            entities=[],
            areas=[],
            manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
        )
        return build_scan(payload, generated_at=FROZEN_CLOCK, collector="native")

    def hub_scan(self) -> Scan:
        return self.scan_for(
            {"id": "brg", "name": "Zigbee2MQTT Bridge",
             "identifiers": [["mqtt", "zigbee2mqtt_bridge_0x0017"]]},
            {"id": "lamp", "name": "Lampada", "via_device_id": "brg",
             "identifiers": [["mqtt", "0x00158d0001234567"]]},
        )

    def test_the_link_to_the_hub_is_a_declared_conduit(self) -> None:
        scan = self.hub_scan()
        conduit = next(c for c in scan.conduits if c.source.id == "lamp")
        self.assertEqual(conduit.evidence, "declared")
        self.assertEqual(conduit.protocol, "zigbee")
        destination = scan.destination(conduit.destination_id)
        self.assertEqual(destination.kind, "local_hub")
        self.assertEqual(destination.fqdn, "Zigbee2MQTT Bridge")
        self.assertEqual(validate(scan.to_dict()), [])

    def test_a_hub_is_one_destination_however_many_hang_off_it(self) -> None:
        scan = self.scan_for(
            {"id": "brg", "name": "Bridge", "identifiers": [["mqtt", "zigbee2mqtt_bridge_0x1"]]},
            {"id": "a", "name": "A", "via_device_id": "brg",
             "identifiers": [["mqtt", "0x00158d0001234567"]]},
            {"id": "b", "name": "B", "via_device_id": "brg",
             "identifiers": [["mqtt", "0x00158d0089abcdef"]]},
        )
        hubs = [d for d in scan.destinations if d.kind == "local_hub"]
        self.assertEqual(len(hubs), 1)
        self.assertEqual(len([c for c in scan.conduits if c.protocol == "zigbee"]), 2)

    def test_a_device_with_no_hub_gets_no_link(self) -> None:
        scan = self.scan_for(
            {"id": "solo", "name": "Solo", "identifiers": [["mqtt", "0x00158d0001234567"]]}
        )
        self.assertEqual([c for c in scan.conduits if c.source.id == "solo"], [])

    def test_a_transport_nobody_could_name_is_not_a_link(self) -> None:
        """Claiming a conduit whose protocol is `unknown` would add a line to
        the picture and no information to it."""
        # Neither names a radio, and neither inherits one, so the transport
        # stays unknown all the way down.
        scan = self.scan_for(
            {"id": "hub", "name": "Hub", "identifiers": [["mqtt", "hub-1"]]},
            {"id": "x", "name": "X", "via_device_id": "hub", "identifiers": [["mqtt", "x"]]},
        )
        self.assertEqual([d.transport for d in scan.devices], ["unknown", "unknown"])
        self.assertEqual([c for c in scan.conduits if c.source.id == "x"], [])

    def test_the_hub_stays_internal_so_the_matrix_is_not_moved(self) -> None:
        """A link to a hub is not egress, and must not read as any."""
        scan = self.hub_scan()
        hub = next(d for d in scan.destinations if d.kind == "local_hub")
        self.assertIn(hub.kind, INTERNAL_DESTINATION_KINDS)
        self.assertEqual(list(derive(scan).matrix.local_egress), [])
