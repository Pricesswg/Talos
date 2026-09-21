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
    ObservedAuthError,
    ObservedError,
    ObservedFacts,
    PiholeCollector,
    QueryRecord,
    ZeroCheck,
    adguard_records,
    settle,
    aggregate,
    collector_for,
    merge_observed,
    parse_clients,
    parse_leases,
    parse_network_table,
    pihole_records,
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
        self.search_fails = False
        # AdGuard scans at most this many entries per search request and
        # reports where it stopped in `oldest`; None models no cap.
        self.scan_cap: int | None = None
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self._page_index = 0

    def _search(self, params: dict[str, Any]) -> Any:
        """The real search, as AdGuard's internal/querylog does it: a quoted
        term is an exact match on the client, the client name and the
        question name; the scan stops at the first `limit` hits and reports
        the last scanned time in `oldest`, empty only at the end of the log;
        `older_than` continues after that time; without `offset` the scan is
        capped at `scan_cap` entries, with it the cap is lifted."""
        if self.search_fails:
            raise ObservedError("querylog: HTTP 500")
        term = str(params["search"])
        strict = term.startswith('"') and term.endswith('"')
        needle = term.strip('"')
        limit = int(params.get("limit") or 50)
        entries = [record for page in self._pages for record in page["data"]]
        start = 0
        if params.get("older_than"):
            start = next(
                (i for i, r in enumerate(entries) if r.get("time") < params["older_than"]),
                len(entries),
            )
        cap = None if ("offset" in params or self.scan_cap is None) else self.scan_cap
        stop = len(entries) if cap is None else min(len(entries), start + cap)

        def matches(r: dict[str, Any]) -> bool:
            client = str(r.get("client", ""))
            if not strict:
                return needle in client
            name = str((r.get("question") or {}).get("name", ""))
            return needle in (client, name, str((r.get("client_info") or {}).get("name", "")))

        hits: list[dict[str, Any]] = []
        last = start - 1
        for index in range(start, stop):
            last = index
            if matches(entries[index]):
                hits.append(entries[index])
                if len(hits) >= limit:
                    break
        reached_end = last >= len(entries) - 1
        oldest = "" if reached_end else entries[last]["time"]
        return {"data": hits, "oldest": oldest}

    async def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        if method != "GET":
            raise ObservedError(f"{method} {path}: HTTP 405")
        return await self.get_json(path, kwargs.get("params"))

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((path, params))
        if path == "/control/querylog/config":
            return self._data.get("querylog_config") or {"enabled": True, "anonymize_client_ip": False, "interval": 90 * 86400000}
        if path == "/control/querylog" and params and params.get("search"):
            return self._search(params)
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
        observations = aggregate(adguard_records(records))
        by_key = {(o.client, o.fqdn): o for o in observations}

        reolink = by_key[("192.168.1.42", "p2p2.reolink.com")]
        self.assertEqual(reolink.count, 3)
        self.assertEqual(reolink.blocked, 0)
        self.assertEqual(reolink.first_seen, "2026-08-30T08:38:55.001+02:00")
        self.assertEqual(reolink.last_seen, "2026-08-30T08:57:41.512+02:00")

    def test_filtered_reason_counts_as_blocked(self) -> None:
        records = [r for page in adguard()["querylog_pages"] for r in page["data"]]
        blocked = next(
            o for o in aggregate(adguard_records(records)) if o.fqdn == "analytics.home-assistant.io"
        )
        self.assertEqual(blocked.blocked, 1)
        self.assertEqual(blocked.filter_status, "blocked")

    def test_explicit_allow_is_not_a_block(self) -> None:
        # NotFilteredWhiteList must not be mistaken for a Filtered* reason.
        ntp = next(
            o
            for o in aggregate(adguard_records([r for p in adguard()["querylog_pages"] for r in p["data"]]))
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
            o for o in aggregate(adguard_records(records), previous) if o.fqdn == "p2p2.reolink.com"
        )
        self.assertEqual(merged.count, 2402)
        self.assertEqual(merged.first_seen, "2026-08-23T00:11:04+02:00")
        self.assertEqual(merged.last_seen, "2026-08-30T08:57:41.512+02:00")

    def test_malformed_records_are_skipped(self) -> None:
        # Missing client or name is dropped by the translation; an unreadable
        # time survives it and is dropped by the aggregation.
        raw = [{"client": "1.2.3.4"}, {"question": {"name": "x.com"}}, {}, "junk"]
        self.assertEqual(list(adguard_records(raw)), [])
        self.assertEqual(aggregate([QueryRecord("1.2.3.4", "x.com", "not a time")]), ())

    def test_the_aggregation_never_sees_the_appliance(self) -> None:
        # The same record from either resolver folds the same way.
        rows = [
            QueryRecord("192.168.1.9", "Api.Tuya.Com.", "2026-09-01T10:00:00+00:00", blocked=False),
            QueryRecord("192.168.1.9", "api.tuya.com", "2026-09-01T10:05:00+00:00", blocked=True),
        ]
        (only,) = aggregate(rows)
        self.assertEqual((only.fqdn, only.count, only.blocked), ("api.tuya.com", 2, 1))
        self.assertEqual(only.last_seen, "2026-09-01T10:05:00+00:00")


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
        # A candidate, not a verdict: nobody has asked the resolver about it.
        self.assertEqual(zero.silent_leases, ())
        self.assertEqual(zero.unconfirmed[0].ip, "10.0.0.9")
        self.assertEqual(settle(zero, {"10.0.0.9": False}).silent_leases[0].ip, "10.0.0.9")
        self.assertEqual(settle(zero, {"10.0.0.9": True}).outside_window[0].ip, "10.0.0.9")


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
        walked = [c for c in transport.calls if c[0].endswith("querylog") and not (c[1] or {}).get("search")]
        self.assertEqual(len(walked), 3)

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
        self.assertEqual([c for c in self.declared.conduits if c.evidence == "observed"], [])
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
        self.assertEqual(self.derived.autonomy.entities_local, 10)
        self.assertNotIn("Reolink", {loss.vendor for loss in self.derived.autonomy.losses})

    def test_transport_protocol_is_satisfied_by_the_fake(self) -> None:
        self.assertIsInstance(FakeHttp(adguard()), HttpTransport)

    def test_zero_check_survives_into_the_report(self) -> None:
        self.assertGreaterEqual(self.derived.unverified_count, 5)



class TestCorrelationSources(unittest.TestCase):
    """Which of the two places a MAC and an IP meet actually carried the
    join. A method nobody used has no business in the report."""

    @staticmethod
    def with_addresses(scan: Scan) -> Scan:
        """The same declared scan, as if a router tracker had named the IPs."""
        from dataclasses import replace

        known = {"ec:71:db:11:22:33": "192.168.1.42"}
        return replace(
            scan,
            devices=[
                replace(device, ip=known.get(device.mac or "")) for device in scan.devices
            ],
        )

    def test_leases_alone(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard())))
        self.assertEqual(merged.correlation.method, "mac_dhcp")
        self.assertTrue(merged.correlation.devices_correlated)

    def test_a_tracker_carries_the_join_when_the_router_does_the_dhcp(self) -> None:
        facts = collect(FakeHttp(adguard(), dhcp=False))
        merged = merge_observed(self.with_addresses(declared_scan()), facts)
        self.assertEqual(merged.correlation.method, "mac_tracker")
        self.assertEqual(merged.correlation.devices_correlated, 1)
        # And the observation stops belonging to nobody.
        owned = [
            conduit
            for conduit in merged.conduits
            if conduit.evidence == "observed" and conduit.source.kind == "device"
        ]
        self.assertTrue(owned)

    def test_with_neither_the_method_says_so_instead_of_naming_one(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard(), dhcp=False)))
        self.assertEqual(merged.correlation.method, "none")
        self.assertEqual(merged.correlation.devices_correlated, 0)

    def test_the_lease_wins_over_the_older_declared_address(self) -> None:
        merged = merge_observed(self.with_addresses(declared_scan()), collect(FakeHttp(adguard())))
        self.assertEqual(merged.correlation.method, "mac_dhcp")
        self.assertEqual(validate(merged.to_dict()), [])

if __name__ == "__main__":
    unittest.main()


def pihole() -> dict[str, Any]:
    return json.loads((FIXTURES / "pihole.json").read_text(encoding="utf-8"))


class FakePihole:
    """A Pi-hole v6 that insists on its session: every read without the SID
    header is a 401, the way the real one answers."""

    def __init__(self, data: dict[str, Any], *, password: str = "secret", dhcp: bool = True) -> None:
        self._data = data
        self._password = password
        self._dhcp = dhcp
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.open_sessions = 0

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request_json("GET", path, params=params)

    async def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        params = kwargs.get("params")
        headers = kwargs.get("headers") or {}
        self.calls.append((method, path, params))
        if path == "/api/auth":
            if method == "POST":
                if (kwargs.get("json") or {}).get("password") != self._password:
                    raise ObservedAuthError("/api/auth: HTTP 401")
                self.open_sessions += 1
                return self._data["auth"]
            if method == "DELETE":
                self.open_sessions -= 1
                return None
        if self._password and headers.get("X-FTL-SID") != "s3ss10n-1d":
            raise ObservedAuthError(f"{path}: HTTP 401")
        if path == "/api/info/version":
            return self._data["version"]
        if path == "/api/queries" and params and params.get("client_ip"):
            wanted = params["client_ip"]
            memory = [q for page in self._data["query_pages"] for q in page["queries"]]
            if str(params.get("disk", "")).lower() == "true":
                # The disk table alone, as FTL reads it: what was exported,
                # which on this fake is the memory pages plus the older rows.
                pool = memory + list(self._data.get("disk_only") or [])
                total = self._data.get("disk_total", len(pool))
                if total == 0:
                    pool = []
            else:
                pool, total = memory, len(memory)
            hits = [q for q in pool if (q.get("client") or {}).get("ip") == wanted]
            return {"queries": hits[: int(params.get("length") or 5)], "cursor": 0, "recordsTotal": total}
        if path == "/api/queries":
            start = int((params or {}).get("start") or 0)
            length = int((params or {}).get("length") or 100)
            index = start // max(length, 1)
            pages = self._data["query_pages"]
            return pages[min(index, len(pages) - 1)]
        if path == "/api/dhcp/leases":
            return self._data["leases"] if self._dhcp else {"leases": []}
        if path == "/api/config/dhcp/active":
            return self._data["dhcp_config"] if self._dhcp else {"config": {"dhcp": {"active": False}}}
        if path == "/api/network/devices":
            return self._data["network"]
        if path == "/api/clients":
            return self._data["clients"]
        if path == "/api/config/misc/privacylevel":
            if self._data.get("privacy_fails"):
                raise ObservedError("privacylevel: HTTP 500")
            return self._data.get("privacy") or {"config": {"misc": {"privacylevel": 0}}}
        if path == "/api/config/webserver/api/excludeClients":
            return self._data.get("exclude") or {"config": {"webserver": {"api": {"excludeClients": []}}}}
        if path == "/api/config/database/maxDBdays":
            return self._data.get("maxdbdays") or {"config": {"database": {"maxDBdays": 91}}}
        raise ObservedError(f"{path}: HTTP 404")


class TestPiholeRecords(unittest.TestCase):
    def test_records_are_normalised(self) -> None:
        rows = list(pihole_records(pihole()["query_pages"][0]["queries"]))
        self.assertEqual(len(rows), 3)
        first = rows[0]
        self.assertEqual((first.client, first.fqdn), ("192.168.1.42", "p2p2.reolink.com"))
        # Unix seconds become RFC 3339 in UTC, the form the cursor compares.
        self.assertEqual(first.time, "2026-08-30T08:57:41.512000+00:00")
        self.assertFalse(first.blocked)
        self.assertTrue(rows[1].blocked, "GRAVITY is a block")

    def test_every_blocking_status_counts_and_no_other(self) -> None:
        def row(status: str) -> QueryRecord:
            return next(pihole_records([{"time": 1.0, "domain": "x.com", "status": status, "client": {"ip": "1.2.3.4"}}]))

        for status in ("GRAVITY", "REGEX", "DENYLIST", "GRAVITY_CNAME", "EXTERNAL_BLOCKED_IP", "SPECIAL_DOMAIN"):
            self.assertTrue(row(status).blocked, status)
        for status in ("FORWARDED", "CACHE", "RETRIED", "CACHE_STALE", "IN_PROGRESS", "DBBUSY"):
            self.assertFalse(row(status).blocked, status)

    def test_network_table_is_pairs_plus_names(self) -> None:
        pairs, names = parse_network_table(pihole()["network"])
        self.assertEqual({p.mac for p in pairs}, {"ec:71:db:11:22:33", "68:57:2d:99:88:77"})
        self.assertTrue(all(p.origin == "network" for p in pairs))
        self.assertEqual(names["192.168.1.61"], "smartcam")


class TestPiholeCollector(unittest.TestCase):
    def collect(self, http: FakePihole, **kwargs: Any) -> ObservedFacts:
        return asyncio.run(PiholeCollector(http, password="secret", page_size=3, **kwargs).fetch())

    def test_walks_pages_and_releases_the_session(self) -> None:
        http = FakePihole(pihole())
        facts = self.collect(http)
        by_key = {(o.client, o.fqdn): o for o in facts.observations}
        self.assertEqual(by_key[("192.168.1.42", "p2p2.reolink.com")].count, 3)
        self.assertEqual(by_key[("192.168.1.10", "analytics.home-assistant.io")].blocked, 1)
        # The cursor pins the snapshot after the first page.
        query_calls = [p for m, path, p in http.calls if path == "/api/queries"]
        self.assertNotIn("cursor", query_calls[0])
        self.assertEqual(query_calls[1]["cursor"], 9004)
        self.assertEqual(query_calls[1]["start"], 3)
        # Newest stamp becomes the cursor, and the session is closed behind us.
        self.assertEqual(facts.cursor, "2026-08-30T08:57:41.512000+00:00")
        self.assertEqual(http.open_sessions, 0)

    def test_a_wrong_password_is_an_auth_error_and_nothing_leaks(self) -> None:
        http = FakePihole(pihole(), password="other")
        with self.assertRaises(ObservedAuthError):
            self.collect(http)
        self.assertEqual(http.open_sessions, 0)

    def test_stops_at_the_previous_cursor_and_asks_only_for_newer(self) -> None:
        http = FakePihole(pihole())
        since = "2026-08-30T08:50:00+00:00"
        facts = asyncio.run(PiholeCollector(http, password="secret", page_size=3).fetch(since=since))
        # Only the two records newer than the boundary are walked; the third
        # is the smartcam's, folded in by the confirmation that found it.
        walked = sum(o.count for o in facts.observations if o.client != "192.168.1.61")
        self.assertEqual(walked, 2)
        first = next(p for m, path, p in http.calls if path == "/api/queries")
        self.assertEqual(first["from"], 1788079800)
        # One page was enough: the boundary was met inside it.
        walked = [p for m, path, p in http.calls if path == "/api/queries" and not (p or {}).get("client_ip")]
        self.assertEqual(len(walked), 1)

    def test_network_table_joins_what_dhcp_does_not_hold(self) -> None:
        facts = self.collect(FakePihole(pihole()))
        by_mac = {lease.mac: lease for lease in facts.leases}
        # The camera has a real lease, and the lease wins over the wire pair.
        self.assertEqual(by_mac["ec:71:db:11:22:33"].origin, "dhcp")
        # The smartcam was never leased by Pi-hole, yet it is joinable.
        self.assertEqual(by_mac["68:57:2d:99:88:77"].origin, "network")
        self.assertEqual(by_mac["68:57:2d:99:88:77"].ip, "192.168.1.61")
        self.assertNotIn("00:00:00:00:00:00", by_mac)
        # Names come from both the network table and the client comments.
        self.assertEqual(facts.client_names["192.168.1.61"], "smartcam")
        self.assertEqual(facts.client_names["192.168.1.42"], "Garden camera")

    def test_without_dhcp_the_wire_table_still_makes_the_zero_check_conclusive(self) -> None:
        facts = self.collect(FakePihole(pihole(), dhcp=False))
        self.assertTrue(facts.zero.is_conclusive)
        self.assertTrue(all(lease.origin == "network" for lease in facts.leases))
        # 192.168.1.10 asked the resolver but is in no table: an unleased client.
        self.assertIn("192.168.1.10", facts.zero.unleased_clients)

    def test_no_password_means_no_session(self) -> None:
        http = FakePihole(pihole(), password="")
        facts = asyncio.run(PiholeCollector(http, password="", page_size=3).fetch())
        self.assertEqual(len(facts.observations), 3)
        self.assertEqual(sum(o.count for o in facts.observations), 5)
        self.assertNotIn("POST", {m for m, path, p in http.calls})

    def test_merge_names_the_witness(self) -> None:
        facts = self.collect(FakePihole(pihole(), dhcp=False))
        merged = merge_observed(declared_scan(), facts, DomainClassifier.load())
        self.assertEqual(derive(merged).correlation.method, "mac_network")
        self.assertNotIn("unv.dhcp_leases_unavailable", {u.id for u in merged.unverified})


class TestResolverFactory(unittest.TestCase):
    def test_each_kind_builds_its_reader_and_probes(self) -> None:
        adguard_reader = collector_for("adguard", FakeHttp(adguard()))
        self.assertIsInstance(adguard_reader, AdGuardCollector)
        with self.assertRaises(ObservedError):
            # The AdGuard fake has no /control/status: the probe says so.
            asyncio.run(adguard_reader.probe())

        pihole_http = FakePihole(pihole())
        pihole_reader = collector_for("pihole", pihole_http, password="secret")
        self.assertIsInstance(pihole_reader, PiholeCollector)
        asyncio.run(pihole_reader.probe())
        self.assertEqual(pihole_http.open_sessions, 0)

        with self.assertRaises(ObservedAuthError):
            asyncio.run(collector_for("pihole", FakePihole(pihole()), password="nope").probe())

    def test_an_unknown_kind_is_refused_loudly(self) -> None:
        with self.assertRaises(ValueError):
            collector_for("dnsmasq", FakeHttp(adguard()))


class TestSilenceOutcomes(unittest.TestCase):
    """Issue 1: an absence from the walked window was read as a bypass. Now a
    silent lease is a candidate until the resolver has been asked about it
    over its whole log, and each outcome is its own note."""

    def test_full_walk_confirms_the_one_real_silence(self) -> None:
        facts = collect(FakeHttp(adguard()))
        zero = facts.zero
        self.assertTrue(zero.confirmed)
        self.assertEqual([l.ip for l in zero.silent_leases], ["192.168.1.203"])
        # The boiler gateway is flagged ignore_querylog: absent by configuration.
        self.assertEqual([l.ip for l in zero.unlogged_leases], ["192.168.1.150"])
        self.assertEqual(facts.unlogged, ("192.168.1.150",))
        self.assertEqual(zero.outside_window, ())
        self.assertEqual(zero.unconfirmed, ())
        self.assertFalse(zero.window.truncated)

    def test_a_short_walk_does_not_turn_an_old_query_into_a_bypass(self) -> None:
        # Two pages of budget: the HVAC unit's only query sits on page four.
        transport = FakeHttp(adguard())
        facts = collect(transport, max_pages=2)
        zero = facts.zero
        self.assertTrue(zero.window.truncated)
        self.assertEqual(zero.window.entries, 12)
        self.assertEqual([l.ip for l in zero.outside_window], ["192.168.1.177"])
        self.assertEqual([l.ip for l in zero.silent_leases], ["192.168.1.203"])
        # One targeted search per candidate, and none for the unlogged host.
        searched = [p["search"] for path, p in transport.calls if p and p.get("search")]
        # Exact terms, in AdGuard's double quotes, one per candidate.
        self.assertEqual(sorted(searched), ['"192.168.1.177"', '"192.168.1.203"'])

    def test_a_prefix_neighbour_is_not_a_match(self) -> None:
        data = adguard()
        data["dhcp"]["leases"].append({"mac": "AA:BB:CC:00:00:04", "ip": "192.168.1.4"})
        facts = collect(FakeHttp(data))
        # `search=192.168.1.4` returns the camera at .42; read back exactly,
        # that is not this host, and the page was short, so: silent.
        self.assertIn("192.168.1.4", [l.ip for l in facts.zero.silent_leases])

    def test_when_the_confirmation_fails_nothing_is_a_finding(self) -> None:
        transport = FakeHttp(adguard())
        transport.search_fails = True
        facts = collect(transport, max_pages=2)
        zero = facts.zero
        self.assertFalse(zero.confirmed)
        self.assertEqual(zero.silent_leases, ())
        self.assertEqual(sorted(l.ip for l in zero.unconfirmed), ["192.168.1.177", "192.168.1.203"])
        merged = merge_observed(declared_scan(), facts)
        ids = {u.id for u in merged.unverified}
        self.assertIn("unv.resolver_silence_unconfirmed", ids)
        self.assertNotIn("unv.resolver_bypassed", ids)
        # And the check is partial, naming the hosts it could not inspect,
        # rather than passed or failed.
        checks = derive(merged).checks
        partial = {c.id: c for c in checks.partial}
        self.assertIn("chk.resolver_bypass", partial)
        # The unlogged boiler gateway is uninspected too: never asked, by design.
        self.assertEqual(
            sorted(partial["chk.resolver_bypass"].uninspected),
            ["192.168.1.150", "192.168.1.177", "192.168.1.203"],
        )
        self.assertNotIn("chk.resolver_bypass", {c.id for c in checks.failed})

    def test_each_outcome_is_its_own_note(self) -> None:
        merged = merge_observed(declared_scan(), collect(FakeHttp(adguard()), max_pages=2))
        notes = {u.id: u for u in merged.unverified}
        self.assertEqual(notes["unv.resolver_bypassed"].subjects, ["192.168.1.203"])
        self.assertIn("whole retention", notes["unv.resolver_bypassed"].detail)
        self.assertIn("12 entries", notes["unv.resolver_bypassed"].detail)
        self.assertEqual(notes["unv.observation_window"].subjects, ["192.168.1.177"])
        self.assertIn("hvac-attic", notes["unv.observation_window"].detail)
        self.assertEqual(notes["unv.resolver_unlogged_clients"].subjects, ["192.168.1.150"])
        self.assertIn("ignore_querylog", notes["unv.resolver_unlogged_clients"].detail)
        # The check fires on the confirmed host only.
        failed = {c.id: c for c in derive(merged).checks.failed}
        self.assertEqual(list(failed["chk.resolver_bypass"].subjects), ["192.168.1.203"])

    def test_unlogged_matches_mac_and_cidr_too(self) -> None:
        from talos_core.observed import is_unlogged

        lease = Lease(mac="aa:bb:cc:dd:ee:ff", ip="10.1.2.3")
        self.assertTrue(is_unlogged(lease, ("aa:bb:cc:dd:ee:ff",)))
        self.assertTrue(is_unlogged(lease, ("10.1.2.0/24",)))
        self.assertFalse(is_unlogged(lease, ("10.1.3.0/24", "10.1.2.4")))
        self.assertFalse(is_unlogged(lease, ("not an id",)))


class TestPiholeSilence(unittest.TestCase):
    def test_candidates_are_confirmed_by_client_ip(self) -> None:
        data = pihole()
        data["leases"]["leases"].append({"hwaddr": "AA:BB:CC:00:00:99", "ip": "192.168.1.99", "name": "mute"})
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret", page_size=3, max_pages=1).fetch())
        zero = facts.zero
        # Page budget of one: the smartcam's query is on page two, confirmed
        # present by the targeted filter; the mute host is confirmed absent.
        self.assertEqual([l.ip for l in zero.outside_window], ["192.168.1.61"])
        self.assertEqual([l.ip for l in zero.silent_leases], ["192.168.1.99"])
        confirmations = [p for m, path, p in http.calls if path == "/api/queries" and (p or {}).get("client_ip")]
        self.assertEqual(sorted(p["client_ip"] for p in confirmations), ["192.168.1.61", "192.168.1.99"])

    def test_privacy_level_is_reported_as_a_limit(self) -> None:
        data = pihole()
        data["privacy"] = {"config": {"misc": {"privacylevel": 2}}}
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertIn("clients are hidden", facts.log_hidden)
        merged = merge_observed(declared_scan(), facts)
        self.assertIn("unv.resolver_log_hidden", {u.id for u in merged.unverified})


class TestConfirmationAgainstTheRealServer(unittest.TestCase):
    """The reviewers' reproductions: AdGuard scans 50 000 entries per search
    unless told to continue, Pi-hole answers from a day of memory unless
    told to read the disk, a budget that never rotates asks the same hosts
    forever, and a privacy level that hides clients makes every lease look
    silent. None of those may become a finding."""

    def test_offset_lifts_the_scan_cap_so_one_request_reaches_the_end(self) -> None:
        transport = FakeHttp(adguard())
        transport.scan_cap = 5  # the HVAC entry sits 13 entries deep
        facts = collect(transport, max_pages=2)
        self.assertEqual([l.ip for l in facts.zero.outside_window], ["192.168.1.177"])
        self.assertEqual([l.ip for l in facts.zero.silent_leases], ["192.168.1.203"])
        searches = [p for path, p in transport.calls if p and p.get("search")]
        self.assertTrue(all(p.get("offset") == 0 and p.get("limit") == 1 for p in searches))
        # One request per host was enough: no continuation was needed.
        self.assertEqual(len([p for p in searches if p["search"] == '"192.168.1.203"']), 1)

    def test_a_foreign_hit_is_stepped_past(self) -> None:
        # A query for the bare name "192.168.1.4", from the camera: the
        # strict search returns it first, and it is not this host.
        data = adguard()
        data["dhcp"]["leases"].append({"mac": "AA:BB:CC:00:00:04", "ip": "192.168.1.4"})
        data["querylog_pages"][0]["data"].insert(0, {
            "time": "2026-08-30T08:58:00.000+02:00", "client": "192.168.1.42",
            "question": {"name": "192.168.1.4", "type": "A"}, "reason": "NotFilteredNotFound",
        })
        transport = FakeHttp(data)
        facts = collect(transport)
        self.assertIn("192.168.1.4", [l.ip for l in facts.zero.silent_leases])
        steps = [p for path, p in transport.calls if p and p.get("search") == '"192.168.1.4"']
        self.assertEqual(len(steps), 2)
        self.assertTrue(steps[1].get("older_than"))
        # And when the host itself has an older entry, it is found past it.
        data["querylog_pages"][-2]["data"].append({
            "time": "2026-08-28T03:00:00.000+02:00", "client": "192.168.1.4",
            "question": {"name": "printer.vendor.example", "type": "A"}, "reason": "NotFilteredNotFound",
        })
        # Two pages of walk keep that entry out of the walk, so the search
        # is what finds it, past the foreign hit.
        facts = collect(FakeHttp(data), max_pages=2)
        self.assertIn("192.168.1.4", [l.ip for l in facts.zero.outside_window])

    def test_a_truncated_walk_does_not_trust_the_memory(self) -> None:
        from datetime import datetime, timezone

        from talos_core.observed import Confirmation

        remembered = {"192.168.1.177": Confirmation("192.168.1.177", False, "2026-09-01T11:00:00+00:00")}
        now = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
        # Two pages: truncated, so the answer is not reused and the search
        # finds the HVAC entry the walk did not reach.
        facts = asyncio.run(AdGuardCollector(FakeHttp(adguard()), max_pages=2).fetch(remembered=remembered, now=now))
        self.assertIn("192.168.1.177", [l.ip for l in facts.zero.outside_window])

    def test_the_found_entry_is_folded_into_the_totals(self) -> None:
        facts = collect(FakeHttp(adguard()), max_pages=2)
        hvac = [o for o in facts.observations if o.client == "192.168.1.177"]
        self.assertEqual([(o.fqdn, o.count) for o in hvac], [("iot.hvac-vendor.com", 1)])

    def test_answers_are_remembered_and_the_budget_rotates(self) -> None:
        from datetime import datetime, timedelta, timezone

        from talos_core.observed import Confirmation
        from talos_core.observed import adguard as module

        data = adguard()
        for n in range(3):
            data["dhcp"]["leases"].append({"mac": f"AA:BB:CC:00:09:{n:02x}", "ip": f"10.9.0.{n}"})
        original = module.MAX_CONFIRMATIONS
        module.MAX_CONFIRMATIONS = 2
        try:
            now = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
            # First poll, a full walk: four candidates (the HVAC unit was
            # walked), two asked, the rest wait.
            transport = FakeHttp(data)
            facts = asyncio.run(AdGuardCollector(transport).fetch(now=now))
            asked = {c.ip for c in facts.confirmations}
            self.assertEqual(len(asked), 2)
            self.assertEqual(len(facts.zero.not_asked), 2)
            # Second poll, remembering the answers: the two already answered
            # False are skipped for a day, two new hosts are asked.
            remembered = {c.ip: c for c in facts.confirmations}
            transport = FakeHttp(data)
            again = asyncio.run(
                AdGuardCollector(transport).fetch(
                    remembered=remembered, now=now + timedelta(hours=1)
                )
            )
            asked_again = {c.ip for c in again.confirmations}
            self.assertEqual(len(asked_again), 2)
            self.assertFalse(asked & asked_again, "a host answered an hour ago is not re-asked")
            # Reused answers still count as confirmed silence.
            self.assertTrue(asked <= {l.ip for l in again.zero.silent_leases})
            # Once everyone has been asked, the ones asked longest ago go
            # first: the two with a stale answer outrank three asked an hour
            # ago without an answer.
            stale = {ip: Confirmation(ip, False, "2026-08-01T00:00:00+00:00") for ip in asked}
            recent = {
                l.ip: Confirmation(l.ip, None, (now - timedelta(hours=1)).isoformat())
                for l in facts.zero.not_asked
            }
            later = asyncio.run(
                AdGuardCollector(FakeHttp(data)).fetch(remembered={**stale, **recent}, now=now)
            )
            self.assertEqual({c.ip for c in later.confirmations}, asked)
        finally:
            module.MAX_CONFIRMATIONS = original

    def test_pihole_reads_the_disk_not_the_day_in_memory(self) -> None:
        data = pihole()
        data["leases"]["leases"].append({"hwaddr": "AA:BB:CC:00:00:77", "ip": "192.168.1.77", "name": "hvac"})
        # Its only query is 40 hours old: on disk, gone from memory.
        data["disk_only"] = [{"id": 8000, "time": 1787936000.0, "domain": "iot.hvac-vendor.com",
                              "status": "FORWARDED", "client": {"ip": "192.168.1.77", "name": "hvac"}}]
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertIn("192.168.1.77", [l.ip for l in facts.zero.outside_window])
        self.assertNotIn("192.168.1.77", [l.ip for l in facts.zero.silent_leases])
        disk_reads = [p for m, path, p in http.calls if path == "/api/queries" and (p or {}).get("client_ip")]
        self.assertTrue(all(str(p.get("disk")).lower() == "true" for p in disk_reads))

    def test_hidden_clients_never_become_silent_hosts(self) -> None:
        data = pihole()
        data["privacy"] = {"config": {"misc": {"privacylevel": 2}}}
        for page in data["query_pages"]:
            for q in page["queries"]:
                q["client"] = {"ip": "0.0.0.0", "name": None}
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertEqual(facts.zero.silent_leases, ())
        self.assertNotIn("0.0.0.0", facts.zero.unleased_clients)
        self.assertFalse(any((p or {}).get("client_ip") for m, path, p in http.calls if path == "/api/queries"))
        merged = merge_observed(declared_scan(), facts)
        notes = {u.id: u for u in merged.unverified}
        self.assertIn("unv.resolver_log_hidden", notes)
        self.assertIn("hides who asked", notes["unv.resolver_silence_unconfirmed"].detail)
        self.assertNotIn("chk.resolver_bypass", {c.id for c in derive(merged).checks.failed})


class TestSilenceIsPerDevice(unittest.TestCase):
    """The device is the MAC. A device seen on one address is not silent on
    its others, and a pair last seen before the log began is gone, not
    silent."""

    def test_other_addresses_of_a_seen_mac_are_not_candidates(self) -> None:
        data = pihole()
        cam = next(d for d in data["network"]["devices"] if d["hwaddr"] == "68:57:2d:99:88:77")
        cam["ips"].append({"ip": "fe80::6a57:2dff:fe99:8877", "name": None, "lastSeen": 1788080000, "nameUpdated": 0})
        cam["ips"].append({"ip": "192.168.1.60", "name": "smartcam", "lastSeen": 1788080000, "nameUpdated": 0})
        http = FakePihole(data, dhcp=False)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        addresses = [l.ip for l in facts.zero.silent_leases] + [l.ip for l in facts.zero.unconfirmed]
        self.assertNotIn("fe80::6a57:2dff:fe99:8877", addresses)
        self.assertNotIn("192.168.1.60", addresses)

    def test_a_device_is_silent_only_when_every_address_answers_no(self) -> None:
        from talos_core.observed import Lease, ZeroCheck, settle

        a = Lease(mac="aa:aa:aa:aa:aa:aa", ip="10.0.0.1")
        a6 = Lease(mac="aa:aa:aa:aa:aa:aa", ip="fe80::1")
        b = Lease(mac="bb:bb:bb:bb:bb:bb", ip="10.0.0.2")
        zero = ZeroCheck(dhcp_available=True, unconfirmed=(a, a6, b))
        settled = settle(zero, {"10.0.0.1": False, "fe80::1": True, "10.0.0.2": False})
        self.assertEqual([l.ip for l in settled.silent_leases], ["10.0.0.2"])
        self.assertEqual(sorted(l.ip for l in settled.outside_window), ["10.0.0.1", "fe80::1"])
        # One address unanswered leaves the whole device pending.
        settled = settle(zero, {"10.0.0.1": False, "10.0.0.2": False})
        self.assertEqual([l.ip for l in settled.silent_leases], ["10.0.0.2"])
        self.assertEqual(sorted(l.ip for l in settled.unconfirmed), ["10.0.0.1", "fe80::1"])

    def test_a_pair_last_seen_before_the_log_began_is_stale_not_silent(self) -> None:
        from datetime import datetime, timezone

        data = pihole()
        data["network"]["devices"].append({
            "id": 9, "hwaddr": "de:ad:be:ef:00:01", "interface": "eth0", "firstSeen": 1745000000,
            "lastQuery": 1745000000, "numQueries": 3, "macVendor": "",
            "ips": [{"ip": "192.168.1.250", "name": "old-laptop", "lastSeen": 1745000000, "nameUpdated": 0}],
        })
        data["maxdbdays"] = {"config": {"database": {"maxDBdays": 30}}}
        http = FakePihole(data, dhcp=False)
        now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch(now=now))
        self.assertEqual([l.ip for l in facts.zero.stale_pairs], ["192.168.1.250"])
        self.assertNotIn("192.168.1.250", [l.ip for l in facts.zero.silent_leases])
        self.assertFalse(any((p or {}).get("client_ip") == "192.168.1.250" for m, path, p in http.calls))
        merged = merge_observed(declared_scan(), facts)
        note = next(u for u in merged.unverified if u.id == "unv.resolver_stale_pairs")
        self.assertIn("old-laptop", note.detail)
        self.assertIn("30 days", note.detail)


class TestResolverSettingsThatHideTheLog(unittest.TestCase):
    def test_pihole_exclude_clients_are_unlogged(self) -> None:
        data = pihole()
        data["leases"]["leases"].append({"hwaddr": "AA:BB:CC:00:00:50", "ip": "192.168.1.50", "name": "tv"})
        data["exclude"] = {"config": {"webserver": {"api": {"excludeClients": ["^192\\.168\\.1\\.50$", "not[a(valid"]}}}}
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertEqual([l.ip for l in facts.zero.unlogged_leases], ["192.168.1.50"])
        self.assertNotIn("192.168.1.50", [l.ip for l in facts.zero.silent_leases])
        merged = merge_observed(declared_scan(), facts)
        note = next(u for u in merged.unverified if u.id == "unv.resolver_unlogged_clients")
        self.assertIn("excludeClients", note.detail)

    def test_pihole_without_a_disk_database_cannot_confirm(self) -> None:
        data = pihole()
        data["leases"]["leases"].append({"hwaddr": "AA:BB:CC:00:00:99", "ip": "192.168.1.99", "name": "mute"})
        data["maxdbdays"] = {"config": {"database": {"maxDBdays": 0}}}
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertEqual(facts.zero.silent_leases, ())
        self.assertIn("192.168.1.99", [l.ip for l in facts.zero.unconfirmed])
        self.assertIn("maxDBdays", facts.log_hidden)

    def test_pihole_empty_disk_table_is_not_an_absence(self) -> None:
        data = pihole()
        data["leases"]["leases"].append({"hwaddr": "AA:BB:CC:00:00:99", "ip": "192.168.1.99", "name": "mute"})
        data["disk_total"] = 0
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertEqual(facts.zero.silent_leases, ())
        self.assertIn("192.168.1.99", [l.ip for l in facts.zero.unconfirmed])

    def test_pihole_unreadable_privacy_level_is_not_level_zero(self) -> None:
        data = pihole()
        data["privacy_fails"] = True
        for page in data["query_pages"]:
            for q in page["queries"]:
                q["client"] = {"ip": "0.0.0.0", "name": "0.0.0.0"}
        http = FakePihole(data)
        facts = asyncio.run(PiholeCollector(http, password="secret").fetch())
        self.assertEqual(facts.zero.silent_leases, ())
        self.assertFalse(any((p or {}).get("client_ip") for m, path, p in http.calls if path == "/api/queries"))

    def test_adguard_log_off_or_anonymised_asks_nothing(self) -> None:
        for config, phrase in (
            ({"enabled": False, "interval": 86400000}, "switched off"),
            ({"enabled": True, "anonymize_client_ip": True, "interval": 86400000}, "anonymised"),
        ):
            with self.subTest(config=config):
                data = adguard()
                data["querylog_config"] = config
                transport = FakeHttp(data)
                facts = collect(transport)
                self.assertIn(phrase, facts.log_hidden)
                self.assertEqual(facts.zero.silent_leases, ())
                self.assertFalse(any(p and p.get("search") for path, p in transport.calls))
                merged = merge_observed(declared_scan(), facts)
                self.assertIn("unv.resolver_log_hidden", {u.id for u in merged.unverified})
                self.assertNotIn("chk.resolver_bypass", {c.id for c in derive(merged).checks.failed})

    def test_adguard_retention_is_read_and_stated(self) -> None:
        data = adguard()
        data["querylog_config"] = {"enabled": True, "anonymize_client_ip": False, "interval": 7 * 86400000}
        facts = collect(FakeHttp(data))
        self.assertEqual(facts.zero.retention_seconds, 7 * 86400)
        merged = merge_observed(declared_scan(), facts)
        note = next(u for u in merged.unverified if u.id == "unv.resolver_bypassed")
        self.assertIn("7 days", note.detail)

    def test_unlogged_matches_every_mac_spelling(self) -> None:
        from talos_core.observed import Lease, is_unlogged, parse_unlogged

        payload = {"clients": [{"name": "x", "ids": ["AA-BB-CC-DD-EE-FF"], "ignore_querylog": True},
                               {"name": "y", "ids": ["aabb.ccdd.ee00"], "ignore_querylog": True}]}
        unlogged = parse_unlogged(payload)
        self.assertEqual(unlogged, ("aa:bb:cc:dd:ee:00", "aa:bb:cc:dd:ee:ff"))
        self.assertTrue(is_unlogged(Lease(mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.1"), unlogged))

    def test_unleased_clients_are_named_and_the_supervisor_network_explained(self) -> None:
        data = adguard()
        data["querylog_pages"][0]["data"].insert(0, {
            "time": "2026-08-30T08:59:00.000+02:00", "client": "172.30.32.3",
            "question": {"name": "version.home-assistant.io", "type": "A"}, "reason": "NotFilteredNotFound",
        })
        merged = merge_observed(declared_scan(), collect(FakeHttp(data)))
        note = next(u for u in merged.unverified if u.id == "unv.resolver_unleased_clients")
        self.assertIn("172.30.32.3", note.subjects)
        self.assertIn("supervisor network", note.detail)


class TestUptimeSurvivesTheMerge(unittest.TestCase):
    def test_a_young_scan_stays_young_after_merging(self) -> None:
        from dataclasses import replace

        young = replace(declared_scan(), ha_uptime_seconds=60.0)
        merged = merge_observed(young, collect(FakeHttp(adguard())))
        self.assertEqual(merged.ha_uptime_seconds, 60.0)
        self.assertEqual(merged.ha_version, young.ha_version)
