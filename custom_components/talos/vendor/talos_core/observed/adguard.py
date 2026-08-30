"""AdGuard Home collector.

The query log is not a queryable history: it is a rolling buffer read newest
first, paginated with an `older_than` cursor. Retention is limited and the
file grows, so the running totals live on our side and each poll only walks
back as far as the previous cursor.

Endpoint and credentials are asked for, never assumed: AdGuard often runs on
the same machine as Home Assistant, and just as often does not.
"""

from __future__ import annotations

from typing import Any, Iterable

from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
from .mapping import (
    Observation,
    ObservedFacts,
    aggregate,
    parse_clients,
    parse_leases,
    parse_time,
    run_zero_check,
)

QUERYLOG_PATH = "/control/querylog"
CLIENTS_PATH = "/control/clients"
DHCP_PATH = "/control/dhcp/status"


class AdGuardCollector(ObservedSource):
    """Incremental poller over the AdGuard Home control API."""

    def __init__(
        self,
        transport: HttpTransport,
        *,
        page_size: int = 500,
        max_pages: int = 40,
        window_hours: int = 24,
    ) -> None:
        self._transport = transport
        self._page_size = page_size
        # A budget, not a guess: an unbounded walk over a busy log would block
        # the poll for minutes and grow without limit.
        self._max_pages = max_pages
        self._window_hours = window_hours

    async def fetch(
        self,
        since: str | None = None,
        previous: Iterable[Observation] = (),
    ) -> ObservedFacts:
        records, cursor = await self._read_querylog(since)
        observations = aggregate(records, previous)

        clients = await self._read_optional(CLIENTS_PATH)
        dhcp_available, leases = parse_leases(await self._read_optional(DHCP_PATH))

        return ObservedFacts(
            observations=observations,
            leases=leases,
            client_names=parse_clients(clients),
            zero=run_zero_check(observations, leases, dhcp_available),
            cursor=cursor or since,
            window_hours=self._window_hours,
        )

    async def _read_querylog(self, since: str | None) -> tuple[list[dict[str, Any]], str | None]:
        boundary = parse_time(since)
        collected: list[dict[str, Any]] = []
        newest: str | None = None
        older_than: str | None = None

        for _ in range(self._max_pages):
            params: dict[str, Any] = {"limit": self._page_size}
            if older_than:
                params["older_than"] = older_than

            payload = await self._get(QUERYLOG_PATH, params)
            page = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(page, list) or not page:
                break

            if newest is None:
                newest = page[0].get("time")

            reached_boundary = False
            for record in page:
                stamp = parse_time(record.get("time"))
                if boundary is not None and stamp is not None and stamp <= boundary:
                    # Everything from here on was already counted by an
                    # earlier poll.
                    reached_boundary = True
                    break
                collected.append(record)
            if reached_boundary:
                break

            oldest = payload.get("oldest") if isinstance(payload, dict) else None
            if not oldest or oldest == older_than:
                break  # the server stopped advancing; do not spin on it
            older_than = oldest

        return collected, newest

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return await self._transport.get_json(path, params)
        except ObservedError:
            raise
        except Exception as err:  # pragma: no cover - transport specific
            raise ObservedError(f"{path}: {err}") from err

    async def _read_optional(self, path: str) -> Any:
        """DHCP served by the router, or an appliance with clients hidden, is
        a normal setup — not an error. The caller degrades from an empty
        answer and says so."""
        try:
            return await self._get(path)
        except ObservedAuthError:
            raise
        except ObservedError:
            return None


class AiohttpJsonTransport:
    """`HttpTransport` over aiohttp with basic auth.

    aiohttp is imported on first use: the core declares no dependencies and
    only the standalone collector needs one.
    """

    def __init__(self, base_url: str, username: str = "", password: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._session: Any = None

    async def __aenter__(self) -> AiohttpJsonTransport:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def connect(self) -> None:
        try:
            import aiohttp
        except ImportError as err:  # pragma: no cover - depends on the install
            raise ObservedError(
                "aiohttp is required for the standalone collector:"
                " install talos-core[cli]"
            ) from err
        auth = (
            aiohttp.BasicAuth(self._username, self._password)
            if self._username or self._password
            else None
        )
        self._session = aiohttp.ClientSession(auth=auth)

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._session is None:
            await self.connect()
        assert self._session is not None

        async with self._session.get(f"{self._base_url}{path}", params=params) as response:
            if response.status in (401, 403):
                raise ObservedAuthError(f"{path}: credenziali rifiutate ({response.status})")
            if response.status >= 400:
                raise ObservedError(f"{path}: HTTP {response.status}")
            return await response.json()

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
