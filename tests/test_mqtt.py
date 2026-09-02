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


class TestRouteCascade(unittest.TestCase):
    """Configuring a route must never leave Talos with less than it had.

    The EMQX API is preferred where it exists, but a key that stops working
    used to take the subscription down with it, which is the opposite of what
    configuring something is for.
    """

    def setUp(self) -> None:
        self.source = _load_mqtt_source()

    def collect(self, hass: Any, credentials=None, api=None) -> MqttFacts:
        import asyncio

        return asyncio.run(self.source.collect_mqtt(hass, house(), credentials, 0.01, api=api))

    @staticmethod
    def hass_with(sys_clients: set[str]) -> Any:
        class Hass:
            config = types.SimpleNamespace(components={"mqtt"})

            async def async_add_executor_job(self, func, *args):
                return set(sys_clients), None if sys_clients else "nothing"

        return Hass()

    def test_a_failing_api_hands_over_to_the_account(self) -> None:
        async def failing(hass, scan, api):
            return MqttFacts(available=False, route="api", error="the EMQX API rejected the key")

        original = self.source.collect_via_api
        self.source.collect_via_api = failing
        try:
            facts = self.collect(
                self.hass_with({"zigbee2mqtt"}),
                credentials={"host": "10.0.0.4"},
                api={"url": "https://emqx:18083"},
            )
        finally:
            self.source.collect_via_api = original
        self.assertTrue(facts.available)
        self.assertEqual(facts.route, "account")
        # And the panel is told which route was meant to answer, and why not.
        self.assertEqual(facts.fallback_from, "api")
        self.assertIn("rejected the key", facts.error)

    def test_a_working_api_is_not_second_guessed(self) -> None:
        async def working(hass, scan, api):
            return MqttFacts(available=True, route="api", clients=(MqttClient("esp-1"),))

        original = self.source.collect_via_api
        self.source.collect_via_api = working
        try:
            facts = self.collect(
                self.hass_with(set()),
                credentials={"host": "10.0.0.4"},
                api={"url": "https://emqx:18083"},
            )
        finally:
            self.source.collect_via_api = original
        self.assertEqual(facts.route, "api")
        self.assertIsNone(facts.fallback_from)
        self.assertIsNone(facts.error)

    def test_when_nothing_answers_the_configured_route_is_the_one_reported(self) -> None:
        async def failing(hass, scan, api):
            return MqttFacts(available=False, route="api", error="the EMQX API is unreachable")

        original = self.source.collect_via_api
        self.source.collect_via_api = failing
        try:
            facts = self.collect(self.hass_with(set()), api={"url": "https://emqx:18083"})
        finally:
            self.source.collect_via_api = original
        self.assertFalse(facts.available)
        self.assertEqual(facts.route, "api")
        self.assertIn("unreachable", facts.error)

    def test_the_session_still_names_itself(self) -> None:
        facts = self.collect(self.hass_with({"zigbee2mqtt"}))
        self.assertEqual(facts.route, "session")

if __name__ == "__main__":
    unittest.main()


class TestZigbeeBridge(unittest.TestCase):
    """The coordinator's own account of its network, from retained topics.
    Nothing is asked of the mesh, so nothing about the mesh is invented."""

    def test_the_three_parts_are_read_from_the_device_list(self) -> None:
        from talos_core.observed.zigbee2mqtt import parse_devices, roles_by_ieee

        nodes = parse_devices(
            '[{"ieee_address":"0x00124B0001A2B3C4","type":"Coordinator"},'
            ' {"ieee_address":"0x00158D0002A2B3C4","type":"Router","power_source":"Mains (single phase)"},'
            ' {"ieee_address":"0x00158D0003A2B3C4","type":"EndDevice","power_source":"Battery"}]'
        )
        self.assertEqual(
            roles_by_ieee(nodes),
            {
                "0x00124b0001a2b3c4": "coordinator",
                "0x00158d0002a2b3c4": "router",
                "0x00158d0003a2b3c4": "end_device",
            },
        )
        self.assertIs(nodes[2].battery_powered, True)

    def test_a_type_we_do_not_know_stays_unknown(self) -> None:
        from talos_core.observed.zigbee2mqtt import parse_devices

        nodes = parse_devices('[{"ieee_address":"0x1","type":"GreenPower"}]')
        self.assertEqual(nodes[0].role, "unknown")

    def test_a_payload_of_another_shape_names_no_node(self) -> None:
        from talos_core.observed.zigbee2mqtt import parse_devices, parse_info

        for payload in ("not json", "", b"{}", '{"a":1}', None):
            with self.subTest(payload=payload):
                self.assertEqual(parse_devices(payload), [])
        self.assertIsNone(parse_info("not json").permit_join)

    def test_permit_join_is_read_but_never_assumed(self) -> None:
        from talos_core.observed.zigbee2mqtt import parse_info

        self.assertIs(parse_info('{"permit_join":true,"version":"2.5.1"}').permit_join, True)
        self.assertIs(parse_info('{"permit_join":false,"version":"2.5.1"}').permit_join, False)
        # Absent is not closed, and the check has a precondition for exactly this.
        self.assertIsNone(parse_info('{"version":"2.5.1"}').permit_join)

    def test_the_role_joins_onto_the_registry_by_ieee(self) -> None:
        from talos_core.sources.mapping import apply_mesh_roles

        scan = house()
        roles = {"0x00158d0002a2b3c4": "router", "0x00158d0003a2b3c4": "end_device"}
        identifiers = {
            device.id: ["zigbee2mqtt_0x00158d0002a2b3c4"] for device in scan.devices
        }
        applied = apply_mesh_roles(scan.devices, roles, identifiers)
        self.assertEqual(applied, 1)
        self.assertEqual(scan.devices[0].mesh_role, "router")

    def test_a_node_the_coordinator_did_not_name_stays_unknown(self) -> None:
        from talos_core.sources.mapping import apply_mesh_roles

        scan = house()
        identifiers = {device.id: ["zigbee2mqtt_0x00158d00ffa2b3c4"] for device in scan.devices}
        self.assertEqual(apply_mesh_roles(scan.devices, {"0x00158d0002a2b3c4": "router"}, identifiers), 0)
        self.assertEqual(scan.devices[0].mesh_role, "unknown")


class TestClientSubjects(unittest.TestCase):
    """A client id is a name the client gave itself, so a finding that lists
    only ids gives the reader nothing to act on."""

    def report_for(self, facts: MqttFacts):
        scan = house()
        scan.mqtt = facts
        return derive(scan).checks

    def test_the_subjects_are_named_as_clients_not_as_nothing(self) -> None:
        facts = MqttFacts(
            available=True,
            clients=(
                MqttClient("home-assistant-1", address="10.0.0.2", matched="Home Assistant"),
                MqttClient("mosq-Xy99Zq", address="10.0.0.77"),
            ),
        )
        result = next(
            r for r in self.report_for(facts).failed if r.id == "chk.mqtt_unknown_client"
        )
        self.assertEqual(result.subject_kind, "mqtt_client")
        self.assertEqual(result.subjects, ("mosq-Xy99Zq",))

    def test_the_address_travels_with_the_client(self) -> None:
        """It is the only handle on a client nothing else names."""
        facts = MqttFacts(available=True, clients=(MqttClient("x", address="10.0.0.77"),))
        scan = house()
        scan.mqtt = facts
        document = scan.to_dict()
        self.assertEqual(document["mqtt"]["clients"][0]["address"], "10.0.0.77")

    def test_the_export_names_the_address_beside_the_id(self) -> None:
        from talos_core.export_html import render_html

        scan = house()
        scan.mqtt = MqttFacts(available=True, clients=(MqttClient("mosq-Xy", address="10.0.0.77"),))
        page = render_html(scan, derive(scan))
        self.assertIn("mosq-Xy (10.0.0.77)", page)

    def test_a_broker_that_named_nobody_keeps_its_reason(self) -> None:
        """The panel prints this instead of an empty list, which is the whole
        difference between "nothing connected" and "I could not look"."""
        facts = MqttFacts(available=False, error="the broker published no client id under $SYS")
        scan = house()
        scan.mqtt = facts
        self.assertIn("$SYS", scan.to_dict()["mqtt"]["error"])
        self.assertIn(
            "chk.mqtt_unknown_client", {r.id for r in derive(scan).checks.unverified}
        )


class TestApiAddress(unittest.TestCase):
    """An address is typed by a person reading it off a dashboard, and what
    they read has no scheme on it."""

    def setUp(self) -> None:
        self.source = _load_mqtt_source()

    def test_a_bare_host_and_port_becomes_usable(self) -> None:
        """Without this the request goes to a URL with no host at all and
        fails in a way that says nothing about what went wrong."""
        self.assertEqual(
            self.source.normalise_api_url("192.168.50.92:18083"),
            "http://192.168.50.92:18083",
        )

    def test_a_scheme_that_is_there_is_kept(self) -> None:
        self.assertEqual(
            self.source.normalise_api_url("https://emqx.local:18083"),
            "https://emqx.local:18083",
        )

    def test_a_trailing_slash_goes(self) -> None:
        self.assertEqual(
            self.source.normalise_api_url("http://10.0.0.4:18083/"), "http://10.0.0.4:18083"
        )

    def test_a_pasted_api_path_is_dropped(self) -> None:
        """The path is added back on every request, so leaving it would ask
        for /api/v5/api/v5/clients."""
        for pasted in (
            "http://10.0.0.4:18083/api/v5",
            "http://10.0.0.4:18083/api/v5/clients",
            "10.0.0.4:18083/api",
        ):
            with self.subTest(pasted=pasted):
                self.assertEqual(
                    self.source.normalise_api_url(pasted), "http://10.0.0.4:18083"
                )

    def test_nothing_stays_nothing(self) -> None:
        self.assertEqual(self.source.normalise_api_url(""), "")
        self.assertEqual(self.source.normalise_api_url("   "), "")
