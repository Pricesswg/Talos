"""The EMQX API client, end to end against a server that answers like EMQX 5.

Skipped where aiohttp is not installed. Home Assistant is not here either, so
the one helper the transport takes from it, the shared client session, is
stood in for by a plain aiohttp session. What is being proven is the request
itself: the path, the pagination, and the Basic auth header carrying the key
and the secret, and that an EMQX-shaped answer becomes a client list with
addresses.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any

try:
    import aiohttp
    from aiohttp import web
except ImportError:  # pragma: no cover - the CLI extra is optional
    aiohttp = None  # type: ignore[assignment]
    web = None  # type: ignore[assignment]

from talos_core import MqttFacts, Scan
from talos_core.sources.mapping import RegistryPayload, build_scan

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "talos"
# The one session the fake hands out, shared by reference with the test that
# owns the current run and closed by it.
_SESSIONS: list[Any] = []


def _load(name: str) -> Any:
    package = types.ModuleType("talos_ha_api")
    package.__path__ = [str(COMPONENT)]  # type: ignore[attr-defined]
    sys.modules.setdefault("talos_ha_api", package)
    spec = importlib.util.spec_from_file_location(f"talos_ha_api.{name}", COMPONENT / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"talos_ha_api.{name}"] = module
    spec.loader.exec_module(module)
    return module


def house() -> Scan:
    payload = RegistryPayload(
        config_entries=[{"entry_id": "e_mqtt", "domain": "mqtt", "title": "EMQX", "state": "loaded",
                         "endpoint": {"host": "a0d7b954-emqx", "port": 1883, "authenticated": True}}],
        devices=[{"id": "d1", "name": "Presa cucina", "config_entries": ["e_mqtt"],
                  "primary_config_entry": "e_mqtt", "identifiers": [["mqtt", "presa-cucina"]],
                  "connections": [["mac", "aa:bb:cc:00:00:01"]]}],
        entities=[], areas=[],
        manifests=[{"domain": "mqtt", "iot_class": "local_push", "is_built_in": True}],
    )
    scan = build_scan(payload, generated_at="2026-09-01T00:00:00+00:00", collector="native")
    scan.devices[0].ip = "192.168.50.77"
    return scan


@unittest.skipUnless(aiohttp, "aiohttp is not installed")
class TestEmqxClientEndToEnd(unittest.TestCase):
    KEY = "talos-key"
    SECRET = "s3cret"

    def setUp(self) -> None:
        # The transport asks Home Assistant for its shared session. Answer
        # with a plain one, created inside the loop the test runs. The
        # transport module stays cached across tests and keeps the first
        # fake it imported, so the fake reads a holder every test resets
        # rather than a closure that would belong to the first test alone.
        _SESSIONS.clear()
        self.sessions = _SESSIONS
        helpers = types.ModuleType("homeassistant.helpers")
        client = types.ModuleType("homeassistant.helpers.aiohttp_client")

        def async_get_clientsession(hass: Any, verify_ssl: bool = True) -> Any:
            if not _SESSIONS:
                _SESSIONS.append(aiohttp.ClientSession())
            return _SESSIONS[0]

        client.async_get_clientsession = async_get_clientsession  # type: ignore[attr-defined]
        helpers.aiohttp_client = client  # type: ignore[attr-defined]
        ha = types.ModuleType("homeassistant")
        ha.helpers = helpers  # type: ignore[attr-defined]
        core = types.ModuleType("homeassistant.core")
        core.HomeAssistant = object  # type: ignore[attr-defined]
        self._installed = []
        for name, module in (("homeassistant", ha), ("homeassistant.helpers", helpers),
                             ("homeassistant.helpers.aiohttp_client", client), ("homeassistant.core", core)):
            if name not in sys.modules:
                sys.modules[name] = module
                self._installed.append(name)
        self.source = _load("mqtt_source")
        self.requests: list[dict[str, Any]] = []

    def tearDown(self) -> None:
        for name in self._installed:
            sys.modules.pop(name, None)

    def serve(self, reject: bool = False, pages: int = 2, per_page: int = 2):
        """A server that answers /api/v5/clients the way EMQX 5 does."""
        expected = "Basic " + base64.b64encode(f"{self.KEY}:{self.SECRET}".encode()).decode()

        async def clients(request: web.Request) -> web.Response:
            self.requests.append({"path": request.path, "query": dict(request.query),
                                  "auth": request.headers.get("Authorization")})
            if reject or request.headers.get("Authorization") != expected:
                return web.json_response({"code": "BAD_API_KEY_OR_SECRET"}, status=401)
            page = int(request.query.get("page", "1"))
            rows = [{"clientid": f"client-{page}-{i}", "ip_address": f"192.168.50.{70 + page * 10 + i}",
                     "username": "u", "connected": True} for i in range(per_page)]
            if page == 1:
                rows[0] = {"clientid": "presa-cucina", "ip_address": "192.168.50.77", "connected": True}
            return web.json_response({"data": rows, "meta": {"page": page, "limit": per_page,
                                                            "count": pages * per_page, "hasnext": page < pages}})

        app = web.Application()
        app.router.add_get("/api/v5/clients", clients)
        return app

    def run_against(self, app: Any, url_form: Any) -> MqttFacts:
        async def go() -> MqttFacts:
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
            try:
                return await self.source.collect_via_api(
                    object(), house(), {"url": url_form(port), "key": self.KEY, "secret": self.SECRET, "verify_ssl": True},
                )
            finally:
                for session in self.sessions:
                    await session.close()
                await runner.cleanup()

        return asyncio.run(go())

    def test_the_request_is_what_emqx_expects(self) -> None:
        facts = self.run_against(self.serve(), lambda port: f"http://127.0.0.1:{port}")
        self.assertTrue(facts.available, facts.error)
        self.assertEqual(facts.route, "api")
        # Basic auth with key:secret, the documented path, page and limit.
        first = self.requests[0]
        self.assertEqual(first["path"], "/api/v5/clients")
        self.assertTrue(first["auth"].startswith("Basic "))
        self.assertEqual(first["query"]["page"], "1")
        self.assertIn("limit", first["query"])

    def test_every_page_is_walked_and_addresses_come_through(self) -> None:
        facts = self.run_against(self.serve(pages=3, per_page=2), lambda port: f"http://127.0.0.1:{port}")
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(len(facts.clients), 6)
        by_id = {c.client_id: c for c in facts.clients}
        self.assertEqual(by_id["presa-cucina"].address, "192.168.50.77")
        # Matched by address to the device holding it, not only by name.
        self.assertEqual(by_id["presa-cucina"].matched, "Presa cucina")
        self.assertTrue(all(c.address for c in facts.clients))

    def test_a_bare_host_and_port_works(self) -> None:
        """What somebody reads off the dashboard and types has no scheme."""
        facts = self.run_against(self.serve(), lambda port: f"127.0.0.1:{port}")
        self.assertTrue(facts.available, facts.error)

    def test_a_rejected_key_is_named_as_such(self) -> None:
        facts = self.run_against(self.serve(reject=True), lambda port: f"http://127.0.0.1:{port}")
        self.assertFalse(facts.available)
        self.assertIn("rejected the key", facts.error)
        self.assertIn("401", facts.error)

    def test_nothing_listening_is_unreachable_not_a_crash(self) -> None:
        async def go() -> MqttFacts:
            probe = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
            port = probe.sockets[0].getsockname()[1]
            probe.close()
            await probe.wait_closed()
            try:
                return await self.source.collect_via_api(
                    object(), house(), {"url": f"http://127.0.0.1:{port}", "key": "k", "secret": "s"},
                )
            finally:
                for session in self.sessions:
                    await session.close()

        facts = asyncio.run(go())
        self.assertFalse(facts.available)
        self.assertIn("unreachable", facts.error)


if __name__ == "__main__":
    unittest.main()
