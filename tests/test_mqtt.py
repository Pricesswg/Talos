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
        """EMQX publishes its gauges at the same depth as a client id would
        sit, so reading one as a client invents a finding out of a number."""
        for topic in (
            "$SYS/broker/clients/connected",
            "$SYS/broker/clients/total",
            "$SYS/broker/clients/maximum",
            "$SYS/brokers/emqx@127.0.0.1/clients/count",
            "$SYS/brokers/emqx@127.0.0.1/clients/max",
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



class TestCredentialledCollection(unittest.TestCase):
    """The read-only account path. No broker here: what is testable is the
    decision of which way in to take, and that a failure is a reason rather
    than an exception."""

    def setUp(self) -> None:
        self.source = _load_mqtt_source()

    def run_collect(self, hass: Any, credentials: dict[str, Any] | None) -> MqttFacts:
        import asyncio

        return asyncio.run(self.source.collect_mqtt(hass, house(), credentials, 0.01))

    def test_an_account_is_used_in_preference_to_the_shared_session(self) -> None:
        calls: list[tuple[Any, ...]] = []

        class Hass:
            config = types.SimpleNamespace(components={"mqtt"})

            async def async_add_executor_job(self, func, *args):
                calls.append(args)
                return {"zigbee2mqtt", "mosq-Xy99Zq"}, None

        facts = self.run_collect(
            Hass(), {"host": "10.0.0.4", "port": 8883, "username": "talos", "password": "x", "tls": True}
        )
        self.assertTrue(facts.available)
        self.assertEqual([c.client_id for c in facts.clients], ["mosq-Xy99Zq", "zigbee2mqtt"])
        self.assertEqual(facts.unmatched[0].client_id, "mosq-Xy99Zq")
        # Host, port, user, password and TLS all reach the client, in order.
        self.assertEqual(calls[0][:3], ("10.0.0.4", 8883, "talos"))
        self.assertIs(calls[0][4], True)

    def test_a_refused_connection_comes_back_as_a_reason(self) -> None:
        class Hass:
            config = types.SimpleNamespace(components=set())

            async def async_add_executor_job(self, func, *args):
                return set(), "the broker refused the connection: Not authorised"

        facts = self.run_collect(Hass(), {"host": "10.0.0.4", "username": "talos"})
        self.assertFalse(facts.available)
        self.assertIn("refused", facts.error)
        self.assertEqual(facts.clients, ())

    def test_no_account_and_no_mqtt_integration_says_which(self) -> None:
        class Hass:
            config = types.SimpleNamespace(components=set())

        facts = self.run_collect(Hass(), None)
        self.assertFalse(facts.available)
        self.assertIn("not loaded", facts.error)

    def test_an_account_with_no_address_is_not_an_account(self) -> None:
        class Hass:
            config = types.SimpleNamespace(components=set())

        facts = self.run_collect(Hass(), {"username": "talos"})
        self.assertFalse(facts.available)

if __name__ == "__main__":
    unittest.main()
