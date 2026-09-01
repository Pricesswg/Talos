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
        self.assertEqual(self.scan.conduits, [])
        self.assertEqual(self.scan.destinations, [])
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
