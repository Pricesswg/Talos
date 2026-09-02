"""MQTT facts: reading the broker's client list and matching it back.

No broker and no Home Assistant here. The topic parsing and the matching are
pure, which is the only reason they can be tested at all: the subscription
itself is a thin wrapper the coordinator owns.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any

from talos_core import MqttClient, MqttFacts, Scan, derive
from talos_core.observed.mqtt import known_tokens, match_clients
from talos_core.sources.mapping import RegistryPayload, build_scan

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "talos"


def _load_mqtt_source() -> Any:
    package = types.ModuleType("talos_ha_mqtt")
    package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
    sys.modules.setdefault("talos_ha_mqtt", package)
    spec = importlib.util.spec_from_file_location(
        "talos_ha_mqtt.mqtt_source", COMPONENT / "mqtt_source.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["talos_ha_mqtt.mqtt_source"] = module
    spec.loader.exec_module(module)
    return module


def house() -> Scan:
    payload = RegistryPayload(
        config_entries=[
            {"entry_id": "e_mqtt", "domain": "mqtt", "title": "Mosquitto", "state": "loaded",
             "endpoint": {"host": "core-mosquitto", "port": 1883, "authenticated": True}},
            {"entry_id": "e_esp", "domain": "esphome", "title": "ESPHome", "state": "loaded"},
        ],
        devices=[
            {"id": "brg", "name": "Zigbee2MQTT Bridge", "config_entries": ["e_mqtt"],
             "primary_config_entry": "e_mqtt",
             "identifiers": [["mqtt", "zigbee2mqtt_bridge_0x0017"]], "connections": []},
        ],
        entities=[],
        areas=[],
        manifests=[
            {"domain": "mqtt", "iot_class": "local_push", "is_built_in": True},
            {"domain": "esphome", "iot_class": "local_push", "is_built_in": True},
        ],
    )
    return build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")


class TestTopicParsing(unittest.TestCase):
    """A client id lives in the topic. A counter also lives in the topic, and
    reporting `connected` as a client would be worse than reporting nothing."""

    def setUp(self) -> None:
        self.source = _load_mqtt_source()

    def test_mosquitto_style_client_topic(self) -> None:
        self.assertEqual(
            self.source.client_id_from_topic("$SYS/broker/clients/tasmota-kitchen"),
            "tasmota-kitchen",
        )

    def test_emqx_style_client_topic(self) -> None:
        self.assertEqual(
            self.source.client_id_from_topic("$SYS/brokers/emqx@127.0.0.1/clients/esp-porch/connected"),
            "esp-porch",
        )

    def test_a_counter_is_not_a_client(self) -> None:
        for topic in (
            "$SYS/broker/clients/connected",
            "$SYS/broker/clients/total",
            "$SYS/broker/clients/maximum",
        ):
            with self.subTest(topic=topic):
                self.assertIsNone(self.source.client_id_from_topic(topic))

    def test_an_unrelated_topic_yields_nothing(self) -> None:
        self.assertIsNone(self.source.client_id_from_topic("$SYS/broker/uptime"))
        self.assertIsNone(self.source.client_id_from_topic("zigbee2mqtt/bridge/state"))


class TestClientMatching(unittest.TestCase):
    def setUp(self) -> None:
        self.scan = house()

    def matched(self, *ids: str) -> dict[str, str | None]:
        return {client.client_id: client.matched for client in match_clients(ids, self.scan)}

    def test_home_assistant_names_itself(self) -> None:
        self.assertEqual(self.matched("home-assistant-9f2b")["home-assistant-9f2b"], "Home Assistant")

    def test_a_system_in_the_scan_claims_its_client(self) -> None:
        found = self.matched("zigbee2mqtt", "esphome-porch")
        # The bridge device carries the name, so it is the one that answers.
        self.assertEqual(found["zigbee2mqtt"], "Zigbee2MQTT Bridge")
        # The ESPHome config entry claims it by its own title.
        self.assertEqual(found["esphome-porch"], "ESPHome")

    def test_a_client_nothing_accounts_for_stays_unmatched(self) -> None:
        self.assertIsNone(self.matched("mosq-Xy99Zq")["mosq-Xy99Zq"])

    def test_a_short_token_is_not_a_match(self) -> None:
        """Three letters match half the world and prove nothing."""
        self.assertNotIn("mqt", known_tokens(self.scan))


class TestClientCheck(unittest.TestCase):
    def report_for(self, facts: MqttFacts | None):
        scan = house()
        scan.mqtt = facts
        return derive(scan).checks

    def test_an_unmatched_client_is_the_finding(self) -> None:
        facts = MqttFacts(
            available=True,
            clients=(
                MqttClient("home-assistant-1", matched="Home Assistant"),
                MqttClient("mosq-Xy99Zq"),
            ),
        )
        result = next(r for r in self.report_for(facts).failed if r.id == "chk.mqtt_unknown_client")
        self.assertEqual(result.subjects, ("mosq-Xy99Zq",))

    def test_every_client_accounted_for_passes(self) -> None:
        facts = MqttFacts(available=True, clients=(MqttClient("zigbee2mqtt", matched="zigbee2mqtt"),))
        self.assertIn("chk.mqtt_unknown_client", {r.id for r in self.report_for(facts).passed})

    def test_a_broker_that_named_nobody_is_unverified(self) -> None:
        """Mosquitto's default answer. An empty list is not a clean result."""
        facts = MqttFacts(available=False, error="the broker published no client id under $SYS")
        report = self.report_for(facts)
        self.assertIn("chk.mqtt_unknown_client", {r.id for r in report.unverified})
        self.assertNotIn("chk.mqtt_unknown_client", {r.id for r in report.passed})

    def test_no_broker_read_at_all_is_also_unverified(self) -> None:
        report = self.report_for(None)
        self.assertIn("chk.mqtt_unknown_client", {r.id for r in report.unverified})


if __name__ == "__main__":
    unittest.main()
