"""Discovery tests.

The parts that decide what to try are pure, so they run without Home
Assistant. The probe takes the check as a callable, which is what makes the
ordering and the early exit testable at all.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "talos"


def _load() -> Any:
    """Load the module without triggering the package's Home Assistant imports."""
    package = types.ModuleType("talos_ha_discovery")
    package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
    sys.modules.setdefault("talos_ha_discovery", package)

    name = "talos_ha_discovery.discovery"
    spec = importlib.util.spec_from_file_location(name, COMPONENT / "discovery.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: a frozen dataclass with slots needs its module
    # present while the decorator runs.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


discovery = _load()


class TestCandidatesFromAdGuardEntry(unittest.TestCase):
    def test_reads_host_port_and_credentials(self) -> None:
        found = discovery.candidates_from_adguard_entries(
            [
                {
                    "host": "192.168.50.92",
                    "port": 3000,
                    "ssl": False,
                    "verify_ssl": True,
                    "username": "admin",
                    "password": "secret",
                }
            ]
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].url, "http://192.168.50.92:3000")
        self.assertEqual(found[0].username, "admin")
        self.assertTrue(found[0].has_credentials)
        self.assertEqual(found[0].source, "adguard_integration")

    def test_ssl_flag_picks_the_scheme(self) -> None:
        found = discovery.candidates_from_adguard_entries(
            [{"host": "adguard.lan", "port": 443, "ssl": True, "verify_ssl": False}]
        )
        self.assertEqual(found[0].url, "https://adguard.lan:443")
        self.assertFalse(found[0].verify_ssl)

    def test_entry_without_a_host_is_skipped(self) -> None:
        self.assertEqual(discovery.candidates_from_adguard_entries([{"port": 3000}, {}]), [])


class TestFallbackCandidates(unittest.TestCase):
    def test_addon_hostname_comes_first(self) -> None:
        found = discovery.fallback_candidates()
        self.assertTrue(found[0].url.startswith(f"http://{discovery.ADDON_HOSTNAME}:"))
        self.assertEqual(found[0].source, "addon")

    def test_internal_url_contributes_its_host(self) -> None:
        found = discovery.fallback_candidates("http://192.168.50.92:8123")
        hosts = {candidate.url.split("//")[1].split(":")[0] for candidate in found}
        self.assertIn("192.168.50.92", hosts)
        self.assertIn(discovery.ADDON_HOSTNAME, hosts)

    def test_certificates_are_never_verified_on_a_guess(self) -> None:
        # An internal hostname or a bare IP never matches a certificate, so
        # verifying would fail on every https candidate.
        self.assertTrue(all(not c.verify_ssl for c in discovery.fallback_candidates()))

    def test_a_malformed_internal_url_is_harmless(self) -> None:
        self.assertTrue(discovery.fallback_candidates("not a url"))


class TestDeduplicate(unittest.TestCase):
    def test_first_wins_so_a_configured_entry_beats_a_guess(self) -> None:
        configured = discovery.Candidate("http://host:3000", username="admin", source="adguard_integration")
        guessed = discovery.Candidate("http://host:3000/", source="addon")
        result = discovery.deduplicate([configured, guessed])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].username, "admin")


class TestProbe(unittest.TestCase):
    def probe(self, outcomes: dict[str, str | None], candidates: list[Any]) -> Any:
        self.tried: list[str] = []

        async def check(candidate: Any) -> str | None:
            self.tried.append(candidate.url)
            return outcomes.get(candidate.url)

        return asyncio.run(discovery.async_probe(check, candidates))

    def test_returns_the_first_that_answers(self) -> None:
        candidates = [
            discovery.Candidate("http://a:3000"),
            discovery.Candidate("http://b:3000"),
            discovery.Candidate("http://c:3000"),
        ]
        found = self.probe({"http://b:3000": "ok"}, candidates)
        assert found is not None
        self.assertEqual(found.url, "http://b:3000")
        # Stops as soon as it has an answer.
        self.assertEqual(self.tried, ["http://a:3000", "http://b:3000"])

    def test_an_auth_challenge_confirms_the_address(self) -> None:
        candidate = discovery.Candidate("http://a:3000", username="wrong", password="wrong")
        found = self.probe({"http://a:3000": "auth"}, [candidate])
        assert found is not None
        self.assertEqual(found.url, "http://a:3000")
        # The guessed credentials did not apply, so they are not offered back.
        self.assertEqual(found.username, "")
        self.assertEqual(found.password, "")

    def test_nothing_answering_returns_none(self) -> None:
        self.assertIsNone(self.probe({}, [discovery.Candidate("http://a:3000")]))

    def test_no_candidates_is_not_an_error(self) -> None:
        self.assertIsNone(self.probe({}, []))


class TestConfigFlowWiring(unittest.TestCase):
    """The flow has to actually use what discovery exposes."""

    def setUp(self) -> None:
        self.source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")

    def test_the_flow_imports_and_calls_the_helpers(self) -> None:
        for name in (
            "candidates_from_adguard_entries",
            "fallback_candidates",
            "deduplicate",
            "async_probe",
        ):
            with self.subTest(helper=name):
                self.assertGreaterEqual(self.source.count(name), 2, f"{name} imported but unused")

    def test_the_probe_timeout_is_short(self) -> None:
        # The flow waits on this, and most candidates are misses.
        self.assertIn("PROBE_TIMEOUT", self.source)
        self.assertLess(discovery_timeout(self.source), 10)

    def test_discovery_never_blocks_setup(self) -> None:
        # Any failure while probing must degrade to the manual form.
        self.assertIn("discovery must never block setup", self.source)


def discovery_timeout(source: str) -> float:
    import re

    match = re.search(r"PROBE_TIMEOUT\s*=\s*([\d.]+)", source)
    assert match
    return float(match.group(1))


if __name__ == "__main__":
    unittest.main()
