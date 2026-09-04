"""Diagnostics: a measurement taken on demand, kept apart from the scan.

The pure parts run with no Home Assistant. The runner is exercised with
fakes for the bus and the registry, a real file for the log, and a real
listening socket on the loopback for the one connection it makes: the point
of that section is the connect, so the connect is what gets tested.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any

from talos_core import Scan
from talos_core.diagnostics import (
    DEFAULT_WINDOW,
    MAX_WINDOW,
    MIN_WINDOW,
    attribute_churn,
    clamp_window,
    declared_targets,
    parse_blocking_calls,
)
from talos_core.sources.mapping import RegistryPayload, build_scan

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "talos"


def _load_runner() -> Any:
    package = types.ModuleType("talos_ha_diag")
    package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
    sys.modules.setdefault("talos_ha_diag", package)
    spec = importlib.util.spec_from_file_location(
        "talos_ha_diag.diagnostics_run", COMPONENT / "diagnostics_run.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["talos_ha_diag.diagnostics_run"] = module
    spec.loader.exec_module(module)
    return module


BLOCKING_LOG = """2026-09-01 10:22:33.123 WARNING (MainThread) [homeassistant.util.loop] Detected blocking call to open with args ('/x',) inside the event loop by custom integration 'device_pulse' at custom_components/device_pulse/sensor.py, line 12: f = open(p)
2026-09-01 10:23:01.000 WARNING (MainThread) [homeassistant.util.loop] Detected blocking call to sleep inside the event loop by integration 'shelly' at homeassistant/components/shelly/coordinator.py, line 88
2026-09-01 10:24:01.000 WARNING (MainThread) [homeassistant.util.loop] Detected blocking call to open with args inside the event loop by custom integration 'device_pulse' at custom_components/device_pulse/sensor.py, line 12
2026-09-01 10:24:30.000 WARNING (MainThread) [homeassistant.util.loop] Detected blocking call to putrequest inside the event loop at homeassistant/components/hue/bridge.py, line 40
2026-09-01 10:25:00.000 INFO (MainThread) [homeassistant.core] nothing to see here
"""


def scan_with_endpoints(*ports: int) -> Scan:
    entries = [
        {"entry_id": f"e{index}", "domain": "mqtt", "title": f"Broker {index}",
         "state": "loaded", "endpoint": {"host": "127.0.0.1", "port": port, "authenticated": True}}
        for index, port in enumerate(ports)
    ]
    entries.append(
        {"entry_id": "e_none", "domain": "matter", "title": "Matter", "state": "loaded",
         "endpoint": None}
    )
    payload = RegistryPayload(
        config_entries=entries,
        devices=[], entities=[], areas=[],
        manifests=[
            {"domain": "mqtt", "iot_class": "local_push", "is_built_in": True},
            {"domain": "matter", "iot_class": "local_push", "is_built_in": True},
        ],
    )
    return build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")


class TestChurn(unittest.TestCase):
    def test_changes_are_attributed_to_their_entry_and_ranked(self) -> None:
        rows, total, unattributed = attribute_churn(
            ["sensor.a", "sensor.a", "sensor.b", "light.x", "sensor.yaml"],
            {"sensor.a": "e1", "sensor.b": "e1", "light.x": "e2", "sensor.yaml": None},
            window_seconds=60,
        )
        self.assertEqual([(r.entry_id, r.changes, r.entities) for r in rows], [("e1", 3, 2), ("e2", 1, 1)])
        self.assertEqual(rows[0].per_minute, 3.0)
        self.assertEqual(rows[0].top_entities, (("sensor.a", 2), ("sensor.b", 1)))
        self.assertEqual(total, 5)
        # Counted, not dropped: the total has to add up.
        self.assertEqual(unattributed, 1)

    def test_the_rate_is_per_minute_whatever_the_window(self) -> None:
        rows, _total, _un = attribute_churn(["s.a"] * 30, {"s.a": "e1"}, window_seconds=30)
        self.assertEqual(rows[0].per_minute, 60.0)

    def test_an_empty_window_is_an_empty_answer(self) -> None:
        self.assertEqual(attribute_churn([], {}, 60), ([], 0, 0))


class TestBlockingCalls(unittest.TestCase):
    def test_warnings_are_counted_by_the_integration_named(self) -> None:
        rows = parse_blocking_calls(BLOCKING_LOG)
        by_domain = {row.domain: row for row in rows}
        self.assertEqual(by_domain["device_pulse"].count, 2)
        self.assertEqual(by_domain["device_pulse"].last_seen, "2026-09-01 10:24:01")
        self.assertEqual(by_domain["shelly"].count, 1)
        # Busiest first.
        self.assertEqual(rows[0].domain, "device_pulse")

    def test_a_line_naming_no_integration_falls_back_to_the_path(self) -> None:
        by_domain = {row.domain: row for row in parse_blocking_calls(BLOCKING_LOG)}
        self.assertIn("hue", by_domain)

    def test_the_sample_starts_at_the_message_and_is_bounded(self) -> None:
        row = parse_blocking_calls(BLOCKING_LOG)[0]
        self.assertTrue(row.sample.startswith("Detected blocking call"))
        self.assertLessEqual(len(row.sample), 240)

    def test_ordinary_lines_count_for_nothing(self) -> None:
        self.assertEqual(parse_blocking_calls("2026-09-01 10:25:00 INFO all fine\n"), [])
        self.assertEqual(parse_blocking_calls(""), [])


class TestWindow(unittest.TestCase):
    def test_bounded_so_a_run_cannot_become_monitoring(self) -> None:
        self.assertEqual(clamp_window(1), MIN_WINDOW)
        self.assertEqual(clamp_window(10_000), MAX_WINDOW)
        self.assertEqual(clamp_window("60"), 60)
        self.assertEqual(clamp_window(None), DEFAULT_WINDOW)
        self.assertEqual(clamp_window("nope"), DEFAULT_WINDOW)


class TestDeclaredTargets(unittest.TestCase):
    def test_only_entries_that_name_host_and_port(self) -> None:
        targets = declared_targets(scan_with_endpoints(1883, 8883))
        self.assertEqual(sorted(t[2] for t in targets), [1883, 8883])
        self.assertNotIn("e_none", [t[0] for t in targets])

    def test_the_same_host_and_port_is_one_target(self) -> None:
        targets = declared_targets(scan_with_endpoints(1883, 1883))
        self.assertEqual(len(targets), 1)


class TestRunner(unittest.TestCase):
    """The Home Assistant side, with the bus and registry faked and the
    connect real. The listening window is skipped: the fake bus fires
    everything on listen, so waiting would only make the suite slow."""

    def setUp(self) -> None:
        self.runner = _load_runner()
        self._real_wait = self.runner._wait

        async def _instant(_seconds: float) -> None:
            return None

        self.runner._wait = _instant
        self._installed = _install_fake_home_assistant()

    def tearDown(self) -> None:
        self.runner._wait = self._real_wait
        for name in self._installed:
            sys.modules.pop(name, None)

    def test_a_full_run_measures_all_three_and_says_what_it_could_not(self) -> None:
        async def go() -> Any:
            # A real listener on a free port: the reachable target.
            server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
            open_port = server.sockets[0].getsockname()[1]
            # And a port nothing listens on: the unreachable one.
            probe = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
            closed_port = probe.sockets[0].getsockname()[1]
            probe.close()
            await probe.wait_closed()

            with tempfile.TemporaryDirectory() as folder:
                Path(folder, "home-assistant.log").write_text(BLOCKING_LOG, encoding="utf-8")
                hass = FakeHass(folder, changes=["sensor.a", "sensor.a", "light.b", "sensor.yaml"])
                scan = scan_with_endpoints(open_port, closed_port)
                try:
                    return await self.runner.run_diagnostics(hass, scan, window=MIN_WINDOW)
                finally:
                    server.close()
                    await server.wait_closed()
                    hass.assert_released()

        run = asyncio.run(go())
        self.assertEqual(run.window_seconds, MIN_WINDOW)
        self.assertIsNotNone(run.finished_at)

        self.assertEqual(run.total_changes, 4)
        self.assertEqual(run.unattributed_changes, 1)
        self.assertEqual([(r.entry_id, r.changes) for r in run.churn], [("e_a", 2), ("e_b", 1)])

        self.assertEqual(run.blocking[0].domain, "device_pulse")

        by_port = {r.port: r for r in run.reachability}
        reachable = [r for r in by_port.values() if r.reachable]
        unreachable = [r for r in by_port.values() if not r.reachable]
        self.assertEqual(len(reachable), 1)
        self.assertIsNotNone(reachable[0].latency_ms)
        self.assertEqual(len(unreachable), 1)
        self.assertTrue(unreachable[0].error)
        # This machine has no Supervisor, and the run says so. That is the
        # only thing it could not measure, so it is the only note.
        self.assertEqual(len(run.notes), 1)
        self.assertIn("Supervisor", run.notes[0])
        self.assertEqual(run.addons, [])

    def test_a_missing_log_is_a_note_not_a_crash(self) -> None:
        async def go() -> Any:
            with tempfile.TemporaryDirectory() as folder:
                hass = FakeHass(folder, changes=[])
                scan = scan_with_endpoints()
                return await self.runner.run_diagnostics(hass, scan, window=MIN_WINDOW)

        run = asyncio.run(go())
        self.assertEqual(run.blocking, [])
        self.assertEqual(run.reachability, [])
        self.assertTrue(any("log" in note for note in run.notes))
        self.assertTrue(any("nothing to connect to" in note for note in run.notes))


class FakeHass:
    """Just enough of hass for the runner: a bus that fires the given
    entity ids as soon as it is listened to, a config path, a registry that
    attributes by the entity's prefix, and an executor that runs inline."""

    def __init__(self, folder: str, changes: list[str]) -> None:
        self._folder = folder
        self._changes = changes
        self._released = False
        self.bus = self
        self.config = types.SimpleNamespace(path=lambda name: str(Path(folder, name)))

    def async_listen(self, event_type: str, callback: Any) -> Any:
        assert event_type == "state_changed"
        for entity_id in self._changes:
            callback(types.SimpleNamespace(data={"entity_id": entity_id}))

        def _release() -> None:
            self._released = True

        return _release

    async def async_add_executor_job(self, func: Any, *args: Any) -> Any:
        return func(*args)

    def assert_released(self) -> None:
        assert self._released, "the state listener was never released"


class _Registry:
    def async_get(self, entity_id: str) -> Any:
        if entity_id.endswith("yaml"):
            return None
        return types.SimpleNamespace(config_entry_id="e_a" if entity_id.startswith("sensor") else "e_b")


def _install_fake_home_assistant() -> list[str]:
    """Answer the runner's registry import while it runs, and only then.

    Home Assistant is not installed here. A stand-in left in sys.modules for
    the whole suite would change what every other test sees when it asks
    whether Home Assistant is importable, so it is put in for this class and
    taken out again. Nothing is done if the real one is present.
    """
    if "homeassistant" in sys.modules and not isinstance(
        sys.modules["homeassistant"], types.ModuleType
    ):
        return []
    if "homeassistant.helpers.entity_registry" in sys.modules:
        return []
    ha = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    registry = types.ModuleType("homeassistant.helpers.entity_registry")
    registry.async_get = lambda hass: _Registry()  # type: ignore[attr-defined]
    helpers.entity_registry = registry  # type: ignore[attr-defined]
    ha.helpers = helpers  # type: ignore[attr-defined]
    installed = []
    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.entity_registry", registry),
    ):
        if name not in sys.modules:
            sys.modules[name] = module
            installed.append(name)
    return installed


if __name__ == "__main__":
    unittest.main()


class TestAddonUsage(unittest.TestCase):
    """The Supervisor's numbers, and the one piece of arithmetic that turns
    two byte counters into a rate."""

    def test_the_supervisor_envelope_is_unwrapped(self) -> None:
        from talos_core.diagnostics import parse_addon_stats

        parsed = parse_addon_stats(
            {"result": "ok", "data": {"cpu_percent": 1.5, "memory_usage": 100, "network_rx": 7, "blk_read": 9}}
        )
        self.assertEqual(parsed, {"cpu_percent": 1.5, "memory_usage": 100, "network_rx": 7})

    def test_anything_else_yields_no_numbers(self) -> None:
        from talos_core.diagnostics import parse_addon_stats

        for payload in ("no", None, [], {"data": "x"}, {"data": {"cpu_percent": True}}):
            with self.subTest(payload=payload):
                self.assertEqual(parse_addon_stats(payload), {})

    def test_network_is_a_rate_over_the_window(self) -> None:
        from talos_core.diagnostics import addon_usage

        row = addon_usage("a", "A", "started", {"network_rx": 1000, "network_tx": 0}, {"network_rx": 7000, "network_tx": 600}, 60)
        self.assertEqual(row.rx_bytes_per_s, 100.0)
        self.assertEqual(row.tx_bytes_per_s, 10.0)

    def test_a_counter_that_went_backwards_yields_no_rate(self) -> None:
        """A restart resets the counter; a negative rate would be a lie."""
        from talos_core.diagnostics import addon_usage

        row = addon_usage("a", "A", "started", {"network_rx": 9000}, {"network_rx": 100}, 60)
        self.assertIsNone(row.rx_bytes_per_s)

    def test_cpu_and_memory_come_from_the_second_sample(self) -> None:
        from talos_core.diagnostics import addon_usage

        row = addon_usage("a", "A", "started", {"cpu_percent": 1, "memory_usage": 10}, {"cpu_percent": 9, "memory_usage": 90}, 60)
        self.assertEqual((row.cpu_percent, row.memory_bytes), (9, 90))


class TestResourceShares(unittest.TestCase):
    def rows(self) -> list[Any]:
        from talos_core.diagnostics import AddonUsage

        return [
            AddonUsage("emqx", "EMQX", "started", cpu_percent=120, memory_bytes=600 * 2**20, rx_bytes_per_s=1000, tx_bytes_per_s=200),
            AddonUsage("z2m", "Zigbee2MQTT", "started", cpu_percent=30, memory_bytes=200 * 2**20, rx_bytes_per_s=50),
            AddonUsage("off", "Stopped one", "stopped"),
        ]

    def test_cpu_is_a_share_of_the_machine_and_closes_to_a_hundred(self) -> None:
        """The Supervisor's figure is per core, so on four cores 120 is 30%."""
        from talos_core.diagnostics import resource_shares

        cpu = resource_shares(self.rows(), cpu_count=4, memory_total=4 * 2**30)["cpu"]
        self.assertEqual([(s.name, s.percent) for s in cpu], [("EMQX", 30.0), ("Zigbee2MQTT", 7.5), ("other", 62.5)])
        self.assertAlmostEqual(sum(s.percent for s in cpu), 100.0)

    def test_memory_is_a_share_of_the_host_with_the_rest_as_free(self) -> None:
        from talos_core.diagnostics import resource_shares

        memory = resource_shares(self.rows(), cpu_count=4, memory_total=4 * 2**30)["memory"]
        self.assertEqual(memory[-1].slug, "other")
        self.assertAlmostEqual(sum(s.percent for s in memory), 100.0)

    def test_network_has_no_whole_so_no_remainder(self) -> None:
        from talos_core.diagnostics import resource_shares

        network = resource_shares(self.rows(), cpu_count=4, memory_total=4 * 2**30)["network"]
        self.assertEqual([s.slug for s in network], ["emqx", "z2m"])
        self.assertAlmostEqual(sum(s.percent for s in network), 100.0)

    def test_a_stopped_addon_is_in_no_pie(self) -> None:
        from talos_core.diagnostics import resource_shares

        shares = resource_shares(self.rows(), cpu_count=4, memory_total=4 * 2**30)
        for key, slices in shares.items():
            with self.subTest(pie=key):
                self.assertNotIn("off", [s.slug for s in slices])

    def test_without_a_whole_there_is_no_cpu_or_memory_pie(self) -> None:
        from talos_core.diagnostics import resource_shares

        shares = resource_shares(self.rows(), cpu_count=None, memory_total=None)
        self.assertEqual((shares["cpu"], shares["memory"]), ([], []))
        self.assertTrue(shares["network"])


class TestAddonRunner(unittest.TestCase):
    """The Supervisor side, answered by a fake in place of the HTTP seam."""

    def setUp(self) -> None:
        self.runner = _load_runner()
        self._real_wait = self.runner._wait
        self._real_get = self.runner._supervisor_get
        self._real_has = self.runner._has_supervisor

        async def _instant(_seconds: float) -> None:
            return None

        self.runner._wait = _instant
        self.calls: list[str] = []
        self.sample = 0

        async def _fake_get(hass: Any, path: str) -> Any:
            self.calls.append(path)
            if path == "/addons":
                return {"result": "ok", "data": {"addons": [
                    {"slug": "a0d7b954_emqx", "name": "EMQX", "state": "started"},
                    {"slug": "core_mosquitto", "name": "Mosquitto broker", "state": "stopped"},
                ]}}
            # Second sample after the wait: counters have grown.
            grown = 6000 if self.calls.count(path) > 1 else 0
            if path == "/core/stats":
                return {"data": {"cpu_percent": 12.0, "memory_usage": 300 * 2**20, "memory_limit": 4 * 2**30, "memory_percent": 7.3, "network_rx": 1000 + grown, "network_tx": 500}}
            if path == "/addons/a0d7b954_emqx/stats":
                return {"data": {"cpu_percent": 40.0, "memory_usage": 600 * 2**20, "memory_limit": 4 * 2**30, "memory_percent": 14.6, "network_rx": 100 + grown * 10, "network_tx": 100 + grown}}
            raise RuntimeError(f"unexpected {path}")

        self.runner._supervisor_get = _fake_get
        self.runner._has_supervisor = lambda: True
        self._installed = _install_fake_home_assistant()

    def tearDown(self) -> None:
        self.runner._wait = self._real_wait
        self.runner._supervisor_get = self._real_get
        self.runner._has_supervisor = self._real_has
        for name in self._installed:
            sys.modules.pop(name, None)

    def test_two_samples_become_rates_and_stopped_addons_stay_listed(self) -> None:
        async def go() -> Any:
            with tempfile.TemporaryDirectory() as folder:
                Path(folder, "home-assistant.log").write_text("", encoding="utf-8")
                hass = FakeHass(folder, changes=[])
                return await self.runner.run_diagnostics(hass, scan_with_endpoints(), window=60)

        run = asyncio.run(go())
        by_slug = {row.slug: row for row in run.addons}
        # Every started container was sampled twice, the stopped one never.
        self.assertEqual(self.calls.count("/addons/a0d7b954_emqx/stats"), 2)
        self.assertEqual(self.calls.count("/core/stats"), 2)
        self.assertNotIn("/addons/core_mosquitto/stats", self.calls)

        emqx = by_slug["a0d7b954_emqx"]
        self.assertEqual(emqx.rx_bytes_per_s, 1000.0)
        self.assertEqual(emqx.tx_bytes_per_s, 100.0)
        self.assertEqual(emqx.cpu_percent, 40.0)
        self.assertEqual(by_slug["core_mosquitto"].state, "stopped")
        self.assertIsNone(by_slug["core_mosquitto"].cpu_percent)
        # Core is the yardstick, and always there.
        self.assertIn("core", by_slug)
        # Busiest by network first.
        self.assertEqual(run.addons[0].slug, "a0d7b954_emqx")
        self.assertEqual(run.memory_total, 4 * 2**30)
        self.assertIsNotNone(run.cpu_count)
        self.assertTrue(run.to_dict()["shares"]["network"])

    def test_no_supervisor_is_a_note_not_a_crash(self) -> None:
        self.runner._has_supervisor = lambda: False

        async def go() -> Any:
            with tempfile.TemporaryDirectory() as folder:
                Path(folder, "home-assistant.log").write_text("", encoding="utf-8")
                return await self.runner.run_diagnostics(FakeHass(folder, changes=[]), scan_with_endpoints(), window=60)

        run = asyncio.run(go())
        self.assertEqual(run.addons, [])
        self.assertTrue(any("Supervisor" in note for note in run.notes))
        self.assertEqual(self.calls, [])

    def test_a_supervisor_that_will_not_list_is_a_note(self) -> None:
        async def _refuse(hass: Any, path: str) -> Any:
            raise RuntimeError("/addons: HTTP 401")

        self.runner._supervisor_get = _refuse

        async def go() -> Any:
            with tempfile.TemporaryDirectory() as folder:
                Path(folder, "home-assistant.log").write_text("", encoding="utf-8")
                return await self.runner.run_diagnostics(FakeHass(folder, changes=[]), scan_with_endpoints(), window=60)

        run = asyncio.run(go())
        self.assertEqual(run.addons, [])
        self.assertTrue(any("401" in note for note in run.notes))
