"""EMQX 5 client list, parsed from what its API actually returns.

No broker and no network: the request belongs to the integration, the shape
of the answer is what has to be got right, and the interesting part is that
this route returns addresses, which the $SYS route never did.
"""

from __future__ import annotations

import unittest
from typing import Any

from talos_core import Scan
from talos_core.observed import emqx_has_more, emqx_to_clients, parse_emqx_clients
from talos_core.sources.mapping import RegistryPayload, build_scan


def house() -> Scan:
    payload = RegistryPayload(
        config_entries=[
            {"entry_id": "e_mqtt", "domain": "mqtt", "title": "EMQX", "state": "loaded",
             "endpoint": {"host": "a0d7b954-emqx", "port": 1883, "authenticated": True}},
        ],
        devices=[
            {"id": "d1", "name": "Presa cucina", "config_entries": ["e_mqtt"],
             "primary_config_entry": "e_mqtt", "identifiers": [["mqtt", "plug-1"]],
             "connections": [["mac", "aa:bb:cc:00:11:22"]]},
        ],
        entities=[],
        areas=[],
        manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
        addresses=[{"mac": "aa:bb:cc:00:11:22", "ip": "192.168.50.7"}],
    )
    return build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")


class TestParsing(unittest.TestCase):
    def test_the_rows_of_a_normal_answer(self) -> None:
        found = parse_emqx_clients(
            {"data": [{"clientid": "a"}, {"clientid": "b"}], "meta": {"hasnext": False}}
        )
        self.assertEqual([row["clientid"] for row in found], ["a", "b"])

    def test_a_row_with_no_client_id_is_not_a_client(self) -> None:
        self.assertEqual(parse_emqx_clients({"data": [{"username": "x"}, "nonsense"]}), [])

    def test_an_answer_of_another_shape_yields_nothing(self) -> None:
        for payload in ({}, [], None, {"data": "no"}, "error"):
            with self.subTest(payload=payload):
                self.assertEqual(parse_emqx_clients(payload), [])

    def test_pagination_follows_hasnext_when_it_is_there(self) -> None:
        self.assertTrue(emqx_has_more({"meta": {"hasnext": True}}, 100))
        self.assertFalse(emqx_has_more({"meta": {"hasnext": False}}, 0))

    def test_pagination_falls_back_to_the_count(self) -> None:
        self.assertTrue(emqx_has_more({"meta": {"count": 50}}, 10))
        self.assertFalse(emqx_has_more({"meta": {"count": 50}}, 50))

    def test_no_meta_is_no_further_page(self) -> None:
        self.assertFalse(emqx_has_more({"data": []}, 0))


class TestAttribution(unittest.TestCase):
    """A client id is a name the client chose. An address is where it really
    connected from, which is the half the subscription never gave us."""

    def setUp(self) -> None:
        self.scan = house()

    def clients(self, *rows: dict[str, Any]) -> dict[str, str | None]:
        return {c.client_id: c.matched for c in emqx_to_clients(rows, self.scan)}

    def test_the_address_attributes_a_client_whose_name_says_nothing(self) -> None:
        found = self.clients({"clientid": "auto-9F2A11", "ip_address": "192.168.50.7"})
        self.assertEqual(found["auto-9F2A11"], "Presa cucina")

    def test_the_name_still_wins_when_it_says_something(self) -> None:
        found = self.clients({"clientid": "home-assistant-1", "ip_address": "192.168.50.99"})
        self.assertEqual(found["home-assistant-1"], "Home Assistant")

    def test_neither_name_nor_address_leaves_it_unmatched(self) -> None:
        found = self.clients({"clientid": "mosq-Xy99", "ip_address": "192.168.50.240"})
        self.assertIsNone(found["mosq-Xy99"])

    def test_the_port_is_stripped_from_the_address(self) -> None:
        clients = emqx_to_clients([{"clientid": "x", "peername": "192.168.50.7:51234"}], self.scan)
        self.assertEqual(clients[0].address, "192.168.50.7")
        self.assertEqual(clients[0].matched, "Presa cucina")

    def test_an_ipv6_address_is_not_cut_at_a_colon(self) -> None:
        clients = emqx_to_clients([{"clientid": "x", "ip_address": "fd00::1"}], self.scan)
        self.assertEqual(clients[0].address, "fd00::1")

    def test_a_row_with_no_address_is_still_a_client(self) -> None:
        clients = emqx_to_clients([{"clientid": "x"}], self.scan)
        self.assertIsNone(clients[0].address)
        self.assertEqual(clients[0].client_id, "x")


if __name__ == "__main__":
    unittest.main()
