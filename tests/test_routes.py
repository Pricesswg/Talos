"""Routes read as a sentence, and say where the sentence breaks."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from talos_core import Scan
from talos_core.routes import build_routes

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "home.json"


def load() -> Scan:
    return Scan.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


class TestInboundRoutes(unittest.TestCase):
    """Every device gets one route saying how it reaches Home Assistant."""

    def setUp(self) -> None:
        self.scan = load()
        self.routes = build_routes(self.scan)
        self.inbound = {r.source.id: r for r in self.routes.routes if r.kind == "inbound"}

    def test_one_inbound_route_per_device(self) -> None:
        self.assertEqual(len(self.inbound), len(self.scan.devices))
        for route in self.inbound.values():
            self.assertEqual(route.target.kind, "ha_core")
            self.assertFalse(route.outward)

    def test_the_first_leg_is_the_transport_the_device_speaks(self) -> None:
        for device in self.scan.devices:
            with self.subTest(device=device.id):
                first = self.inbound[device.id].legs[0]
                self.assertEqual(first.kind, "transport")
                self.assertEqual(first.id, device.transport or "unknown")

    def test_a_device_behind_a_hub_names_the_hub_between_the_two(self) -> None:
        """A Zigbee bulb does not reach Home Assistant on its own, and the
        route says through what it does."""
        lamp = self.inbound["dev.hue.lamp.living"]
        kinds = [leg.kind for leg in lamp.legs]
        self.assertEqual(kinds, ["transport", "hub", "integration"])
        self.assertEqual(lamp.legs[1].id, "dev.hue.bridge")

    def test_the_entry_address_is_carried_when_the_entry_declares_one(self) -> None:
        """Zigbee2MQTT publishes over MQTT, and the broker is the part worth
        naming: the entry title says Mosquitto long after it points elsewhere."""
        motion = self.inbound["dev.z2m.motion"]
        protocol = [leg for leg in motion.legs if leg.kind == "protocol"]
        self.assertEqual(len(protocol), 1)
        self.assertIn("1883", protocol[0].detail)

    def test_a_device_no_conduit_names_says_what_is_missing(self) -> None:
        """The branch stops at the transport, and that is a hole, not a pass."""
        self.assertEqual(self.inbound["dev.zwave.lock"].missing, ("dhcp_leases",))

    def test_a_device_the_scan_placed_is_not_marked_as_a_hole(self) -> None:
        self.assertEqual(self.inbound["dev.reolink.garden"].missing, ())


class TestConduitRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.scan = load()
        self.routes = build_routes(self.scan)

    def test_every_conduit_becomes_exactly_one_route(self) -> None:
        from_conduits = [r for r in self.routes.routes if r.kind == "conduit"]
        self.assertEqual(len(from_conduits), len(self.scan.conduits))

    def test_an_observed_route_ends_at_the_name_that_was_resolved(self) -> None:
        observed = [r for r in self.routes.routes if r.evidence == "observed"]
        self.assertTrue(observed)
        for route in observed:
            with self.subTest(route=route.id):
                self.assertEqual(route.target.kind, "destination")
                self.assertEqual(route.legs[-1].kind, "dns")

    def test_a_radio_device_reaching_outside_names_the_bridge_that_carries_it(self) -> None:
        """Nothing leaves the house over Zigbee. When a radio device is seen
        outward, the route names the thing that actually carried it."""
        scan = load()
        radio = [
            route
            for route in build_routes(scan).routes
            if route.kind == "conduit"
            and route.outward
            and route.source.kind == "device"
            and (
                next((d for d in scan.devices if d.id == route.source.id), None)
                and (next(d for d in scan.devices if d.id == route.source.id).transport or "")
                not in ("ip", "wifi", "ethernet")
            )
        ]
        self.assertTrue(radio, "the fixture should hold a radio device with egress")
        for route in radio:
            with self.subTest(route=route.id):
                self.assertTrue(
                    {"origin", "hub"} & {leg.kind for leg in route.legs},
                    "a radio device reaching outside must name what carried it",
                )

    def test_a_host_nothing_accounts_for_says_so(self) -> None:
        hosts = [r for r in self.routes.routes if r.source.kind == "host"]
        self.assertTrue(hosts)
        for route in hosts:
            self.assertEqual(route.missing, ("dhcp_leases",))
        self.assertEqual(
            set(self.routes.unattributed), {r.source.id for r in hosts}
        )


class TestTransportSummary(unittest.TestCase):
    """The counts that make a branch ending at a transport readable."""

    def test_every_transport_in_the_registry_is_counted(self) -> None:
        scan = load()
        routes = build_routes(scan)
        expected = {device.transport or "unknown" for device in scan.devices}
        self.assertEqual(set(routes.transports), expected)
        self.assertEqual(
            sum(row["devices"] for row in routes.transports.values()), len(scan.devices)
        )

    def test_a_transport_with_nothing_beyond_it_names_the_precondition(self) -> None:
        routes = build_routes(load())
        zwave = routes.transports["zwave"]
        self.assertEqual(zwave["seen"], 0)
        self.assertEqual(zwave["missing"], ["dhcp_leases"])
        self.assertEqual(routes.transports["wifi"]["missing"], [])

    def test_without_observations_the_reason_is_the_missing_query_log(self) -> None:
        """No resolver at all is a different sentence from no leases, and the
        routes must not blame the leases for it."""
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw["conduits"] = [c for c in raw["conduits"] if c.get("evidence") != "observed"]
        routes = build_routes(Scan.from_dict(raw))
        for name, row in routes.transports.items():
            if row["seen"]:
                continue
            with self.subTest(transport=name):
                self.assertEqual(row["missing"], ["observed_evidence"])


class TestSerialisation(unittest.TestCase):
    def test_the_dict_round_trips_through_json(self) -> None:
        routes = build_routes(load())
        payload = json.loads(json.dumps(routes.to_dict()))
        self.assertEqual(len(payload["routes"]), len(routes.routes))
        first = payload["routes"][0]
        for key in ("id", "kind", "source", "legs", "target", "outward", "evidence"):
            self.assertIn(key, first)

    def test_an_empty_scan_produces_no_routes_and_does_not_raise(self) -> None:
        scan = Scan.from_dict(
            {
                "schema_version": "1",
                "generated_at": "2026-09-07T00:00:00+00:00",
                "collector": "test",
                "correlation": {"devices_total": 0, "devices_correlated": 0, "method": "none"},
            }
        )
        routes = build_routes(scan)
        self.assertEqual(routes.routes, ())
        self.assertEqual(routes.transports, {})


if __name__ == "__main__":
    unittest.main()
