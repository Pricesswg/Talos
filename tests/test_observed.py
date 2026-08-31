"""Observed-side tests: classification, aggregation, the zero check, the join.

A fake HTTP transport replays recorded AdGuard payloads. Nothing here touches
an appliance, and the two fixtures are built to be merged with each other: the
MACs in the device registry match the MACs in the DHCP leases, which is the
only reason the join has anything to work with.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any

from talos_core import Scan, derive, validate
from talos_core.observed import (
    AdGuardCollector,
    DomainClassifier,
    HttpTransport,
    Lease,
    Observation,
    ObservedError,
    ObservedFacts,
    ZeroCheck,
    aggregate,
    merge_observed,
    parse_clients,
    parse_leases,
    run_zero_check,
)
from talos_core.sources import CommandError, WebSocketSource

FIXTURES = Path(__file__).parent / "fixtures"
FROZEN_CLOCK = "2026-08-30T07:14:02+00:00"


def adguard() -> dict[str, Any]:
    return json.loads((FIXTURES / "adguard.json").read_text(encoding="utf-8"))


def registry() -> dict[str, Any]:
    return json.loads((FIXTURES / "ha_registry.json").read_text(encoding="utf-8"))


class FakeHttp:
    """Serves the recorded query log pages in order; 404s what it lacks."""

    def __init__(self, data: dict[str, Any], *, dhcp: bool = True, clients: bool = True) -> None:
        self._pages = data["querylog_pages"]
        self._data = data
        self._dhcp = dhcp
        self._clients = clients
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self._page_index = 0

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((path, params))
        if path == "/control/querylog":
            page = self._pages[min(self._page_index, len(self._pages) - 1)]
            self._page_index += 1
            return page
        if path == "/control/clients":
            if not self._clients:
                raise ObservedError("clients: HTTP 404")
            return self._data["clients"]
        if path == "/control/dhcp/status":
            if not self._dhcp:
                raise ObservedError("dhcp: HTTP 501")
            return self._data["dhcp"]
        raise ObservedError(f"{path}: HTTP 404")


def declared_scan() -> Scan:
    data = registry()

    class Replay:
        ha_version = data["ha_version"]

        async def send(self, command: dict[str, Any]) -> Any:
            name = command["type"]
            if name not in data["responses"]:
                raise CommandError(name, "unknown command", "unknown_command")
            return data["responses"][name]

    return asyncio.run(WebSocketSource(Replay(), clock=lambda: FROZEN_CLOCK).fetch())


def collect(transport: FakeHttp, **kwargs: Any) -> ObservedFacts:
    return asyncio.run(AdGuardCollector(transport, **kwargs).fetch())


class TestClassifier(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = DomainClassifier.load()

    def test_longest_suffix_wins(self) -> None:
        # tuyaeu.com must beat tuya.com, and both must beat nothing.
        self.assertEqual(self.classifier.classify("a3.tuyaeu.com").matched, "tuyaeu.com")

    def test_known_vendors(self) -> None:
        self.assertEqual(self.classifier.classify("p2p2.reolink.com").vendor, "Reolink")
        self.assertEqual(self.classifier.classify("pool.ntp.org").kind, "ntp")
        self.assertEqual(
            self.classifier.classify("analytics.home-assistant.io").kind, "telemetry"
        )

    def test_unknown_is_recorded_not_swallowed(self) -> None:
        verdict = self.classifier.classify("weird.example.net")
        self.assertEqual(verdict.kind, "unknown")
        self.assertFalse(verdict.is_known)
        self.assertIn("weird.example.net", self.classifier.unknown)

    def test_local_names_are_ignored_entirely(self) -> None:
        for name in ("hub.local", "nas.lan", "1.1.168.192.in-addr.arpa"):
            with self.subTest(name=name):
                self.assertTrue(self.classifier.is_ignored(name))
        self.assertFalse(self.classifier.is_ignored("p2p2.reolink.com"))

    def test_user_rules_layer_on_top(self) -> None:
        extended = self.classifier.extend(
            {"rules": [{"suffix": "example.net", "kind": "telemetry", "vendor": "Acme"}]}
        )
        self.assertEqual(extended.classify("weird.example.net").vendor, "Acme")


class TestAggregation(unittest.TestCase):
    def test_folds_records_into_totals(self) -> None:
        records = [r for page in adguard()["querylog_pages"] for r in page["data"]]
        observations = aggregate(records)
        by_key = {(o.client, o.fqdn): o for o in observations}

        reolink = by_key[("192.168.1.42", "p2p2.reolink.com")]
        self.assertEqual(reolink.count, 3)
        self.assertEqual(reolink.blocked, 0)
        self.assertEqual(reolink.first_seen, "2026-08-30T08:38:55.001+02:00")
        self.assertEqual(reolink.last_seen, "2026-08-30T08:57:41.512+02:00")

    def test_filtered_reason_counts_as_blocked(self) -> None:
        records = [r for page in adguard()["querylog_pages"] for r in page["data"]]
        blocked = next(o for o in aggregate(records) if o.fqdn == "analytics.home-assistant.io")
        self.assertEqual(blocked.blocked, 1)
        self.assertEqual(blocked.filter_status, "blocked")

    def test_explicit_allow_is_not_a_block(self) -> None:
        # NotFilteredWhiteList must not be mistaken for a Filtered* reason.
        ntp = next(
            o
            for o in aggregate([r for p in adguard()["querylog_pages"] for r in p["data"]])
            if o.fqdn == "pool.ntp.org"
        )
        self.assertEqual(ntp.blocked, 0)

    def test_previous_totals_survive_the_log_rolling_over(self) -> None:
        previous = [
            Observation(
                client="192.168.1.42",
                fqdn="p2p2.reolink.com",
                count=2400,
                blocked=0,
                first_seen="2026-08-23T00:11:04+02:00",
                last_seen="2026-08-29T23:00:00+02:00",
            )
        ]
        records = adguard()["querylog_pages"][0]["data"]
        merged = next(
            o for o in aggregate(records, previous) if o.fqdn == "p2p2.reolink.com"
        )
        self.assertEqual(merged.count, 2402)
        self.assertEqual(merged.first_seen, "2026-08-23T00:11:04+02:00")
        self.assertEqual(merged.last_seen, "2026-08-30T08:57:41.512+02:00")

    def test_malformed_records_are_skipped(self) -> None:
        self.assertEqual(
            aggregate([{"client": "1.2.3.4"}, {"question": {"name": "x.com"}}, {}]), ()
        )


class TestZeroCheck(unittest.TestCase):
    def test_leases_and_clients_are_compared(self) -> None:
        facts = collect(FakeHttp(adguard()))
        zero = facts.zero
        self.assertTrue(zero.is_conclusive)
        self.assertEqual([lease.ip for lease in zero.silent_leases], ["192.168.1.203"])
        self.assertEqual(zero.unleased_clients, ("192.168.1.87",))

    def test_without_dhcp_the_check_is_inconclusive_not_clean(self) -> None:
        facts = collect(FakeHttp(adguard(), dhcp=False))
        self.assertFalse(facts.zero.is_conclusive)
        self.assertEqual(facts.zero.silent_leases, ())
        self.assertEqual(facts.zero.unleased_clients, ())

    def test_disabled_dhcp_server_reports_no_leases(self) -> None:
        available, leases = parse_leases({"enabled": False, "leases": []})
        self.assertFalse(available)
        self.assertEqual(leases, ())

    def test_static_leases_count_too(self) -> None:
        available, leases = parse_leases(
            {"enabled": False, "static_leases": [{"mac": "AA:BB:CC:DD:EE:FF", "ip": "10.0.0.5"}]}
        )
        self.assertTrue(available)
        self.assertEqual(leases[0].mac, "aa:bb:cc:dd:ee:ff")
        self.assertTrue(leases[0].static)

    def test_zero_check_needs_no_appliance(self) -> None:
        zero = run_zero_check(
            [Observation("10.0.0.1", "x.com", 1, 0, "t", "t")],
            [Lease("aa:bb:cc:dd:ee:ff", "10.0.0.9")],
            dhcp_available=True,
        )
        self.assertEqual(zero.unleased_clients, ("10.0.0.1",))
        self.assertEqual(zero.silent_leases[0].ip, "10.0.0.9")


class TestCollectorPagination(unittest.TestCase):
    def test_walks_pages_with_the_older_than_cursor(self) -> None:
        transport = FakeHttp(adguard())
        facts = collect(transport)
        querylog_calls = [params for path, params in transport.calls if path.endswith("querylog")]
        self.assertGreaterEqual(len(querylog_calls), 2)
        self.assertIsNone(querylog_calls[0].get("older_than"))
        self.assertEqual(querylog_calls[1]["older_than"], "2026-08-30T08:40:00.000+02:00")
        self.assertEqual(facts.cursor, "2026-08-30T08:57:41.512+02:00")

    def test_stops_at_the_previous_cursor(self) -> None:
        transport = FakeHttp(adguard())
        facts = asyncio.run(
            AdGuardCollector(transport).fetch(since="2026-08-30T08:50:00.000+02:00")
        )
        names = {o.fqdn for o in facts.observations}
        self.assertIn("p2p2.reolink.com", names)
        self.assertNotIn("tbc.mt.hicloud.com", names)  # older than the cursor

    def test_page_budget_is_respected(self) -> None:
        data = adguard()
        # A log that never stops advancing must not spin the poll forever.
        data["querylog_pages"] = [
            {"oldest": f"2026-08-30T0{i}:00:00.000+02:00", "data": data["querylog_pages"][0]["data"]}
            for i in range(9)
        ]
        transport = FakeHttp(data)
        collect(transport, max_pages=3)
        self.assertEqual(len([c for c in transport.calls if c[0].endswith("querylog")]), 3)

    def test_missing_optional_endpoints_degrade(self) -> None:
        facts = collect(FakeHttp(adguard(), dhcp=False, clients=False))
        self.assertEqual(facts.client_names, {})
        self.assertEqual(facts.leases, ())
        self.assertTrue(facts.observations)  # the query log still worked

    def test_client_names_are_read(self) -> None:
        names = parse_clients(adguard()["clients"])
        self.assertEqual(names["192.168.1.42"], "Garden camera")
        self.assertEqual(names["192.168.1.87"], "unknown-87")


class TestMerge(unittest.TestCase):
    def setUp(self) -> None:
        self.declared = declared_scan()
        self.facts = collect(FakeHttp(adguard()))
        self.merged = merge_observed(self.declared, self.facts)

    def test_merged_scan_validates(self) -> None:
        self.assertEqual(validate(self.merged.to_dict()), [])

    def test_input_scan_is_untouched(self) -> None:
        self.assertEqual(self.declared.conduits, [])
        self.assertTrue(all(d.ip is None for d in self.declared.devices))

    def test_leases_supply_the_addresses_the_registry_lacks(self) -> None:
        camera = self.merged.device("d_cam1")
        assert camera is not None
        self.assertEqual(camera.ip, "192.168.1.42")
        self.assertEqual(self.merged.correlation.devices_correlated, 3)
        self.assertEqual(self.merged.correlation.method, "mac_dhcp")

    def test_observations_become_conduits_attributed_to_devices(self) -> None:
        observed = [c for c in self.merged.conduits if c.evidence == "observed"]
        by_source = {(c.source.kind, c.source.id, c.destination_id) for c in observed}
        self.assertIn(("device", "d_cam1", "dst.p2p2.reolink.com"), by_source)
        self.assertIn(("device", "d_tuya", "dst.a3.tuyaeu.com"), by_source)

    def test_uncorrelated_client_becomes_an_unknown_host(self) -> None:
        conduit = next(c for c in self.merged.conduits if c.destination_id == "dst.tbc.mt.hicloud.com")
        self.assertEqual(conduit.source.kind, "unknown_host")
        self.assertEqual(conduit.source.id, "192.168.1.87")

    def test_local_names_never_become_conduits(self) -> None:
        self.assertNotIn("dst.hub.local", {d.id for d in self.merged.destinations})

    def test_hub_egress_is_inherited_by_its_children(self) -> None:
        inherited = [c for c in self.merged.conduits if c.evidence == "inherited"]
        self.assertEqual(len(inherited), 1)
        conduit = inherited[0]
        self.assertEqual(conduit.source.id, "d_lamp")
        self.assertEqual(conduit.inherited_from, "d_bridge")
        self.assertEqual(conduit.destination_id, "dst.ws.meethue.com")
        # Second-hand facts carry no first-hand counters.
        self.assertIsNone(conduit.query_count)
        self.assertIsNone(conduit.last_seen)

    def test_infrastructure_is_not_inherited(self) -> None:
        inherited_destinations = {
            c.destination_id for c in self.merged.conduits if c.evidence == "inherited"
        }
        self.assertNotIn("dst.pool.ntp.org", inherited_destinations)

    def test_blocked_queries_are_preserved(self) -> None:
        conduit = next(
            c for c in self.merged.conduits if c.destination_id == "dst.analytics.home-assistant.io"
        )
        self.assertEqual(conduit.filter_status, "blocked")
        self.assertEqual(conduit.query_count, 1)


class TestMergeNotes(unittest.TestCase):
    def note_ids(self, scan: Scan) -> set[str]:
        return {check.id for check in scan.unverified}

    def test_resolver_bypass_is_reported_as_a_blind_spot(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        checks = {c.id: c for c in merged.unverified}
        self.assertIn("unv.resolver_bypassed", checks)
        self.assertEqual(checks["unv.resolver_bypassed"].reason, "method_limit")
        self.assertIn("192.168.1.203", checks["unv.resolver_bypassed"].detail)

    def test_without_leases_the_whole_join_degrades_loudly(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard(), dhcp=False)))
        checks = {c.id: c for c in merged.unverified}
        self.assertIn("unv.dhcp_leases_unavailable", checks)
        detail = checks["unv.dhcp_leases_unavailable"].detail
        self.assertIn("it did not run", detail)
        self.assertIn("DHCP", detail)

        # Every observation is now attributed to nobody.
        observed = [c for c in merged.conduits if c.evidence == "observed"]
        self.assertTrue(all(c.source.kind == "unknown_host" for c in observed))
        self.assertEqual(merged.correlation.devices_correlated, 0)
        self.assertEqual(validate(merged.to_dict()), [])

    def test_unclassified_domains_are_counted(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        check = next(c for c in merged.unverified if c.id == "unv.unclassified_domains")
        self.assertIn("weird.example.net", check.detail)

    def test_devices_without_a_mac_are_declared_uncorrelatable(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        check = next(c for c in merged.unverified if c.id == "unv.devices_without_identifier")
        self.assertIn("a minimum, not a total", check.detail)

    def test_doh_limit_is_always_declared(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        self.assertIn("unv.doh", self.note_ids(merged))


class TestFullPipeline(unittest.TestCase):
    """Declared + observed, all the way to the numbers the panel shows."""

    def setUp(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        self.scan = merged
        self.derived = derive(merged)

    def test_the_quadrant_that_counts(self) -> None:
        # Local to HA, caught phoning home on their own.
        self.assertEqual(self.derived.matrix.local_egress, ("d_bridge", "d_cam1"))

    def test_cloud_device_confirms_its_declared_dependency(self) -> None:
        self.assertEqual(self.derived.matrix.cloud_egress, ("d_tuya",))

    def test_lamp_is_exposed_but_not_in_the_red_quadrant(self) -> None:
        self.assertIn("d_lamp", self.derived.matrix.local_silent)
        self.assertEqual([i.device_id for i in self.derived.matrix.inherited], ["d_lamp"])

    def test_exposure_names_vendors_with_their_evidence(self) -> None:
        by_vendor = {v.vendor: v for v in self.derived.exposure.vendors}
        self.assertEqual(by_vendor["Reolink"].queries, 3)
        self.assertEqual(by_vendor["Signify"].evidence, ("inherited", "observed"))
        # A classified domain is named after whoever is behind it, even when
        # the host asking is one we could not identify.
        self.assertEqual(by_vendor["Huawei"].devices_direct, ())
        # An unclassified one falls back to the domain rather than inventing
        # a vendor nobody told us about.
        self.assertIn("weird.example.net", by_vendor)

    def test_autonomy_is_unaffected_by_observation(self) -> None:
        # Observed egress is exposure, not a functional dependency: the
        # offline picture must not move because a camera chattered.
        self.assertEqual(self.derived.autonomy.entities_local, 9)
        self.assertNotIn("Reolink", {loss.vendor for loss in self.derived.autonomy.losses})

    def test_transport_protocol_is_satisfied_by_the_fake(self) -> None:
        self.assertIsInstance(FakeHttp(adguard()), HttpTransport)

    def test_zero_check_survives_into_the_report(self) -> None:
        self.assertGreaterEqual(self.derived.unverified_count, 5)


if __name__ == "__main__":
    unittest.main()
