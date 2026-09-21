"""AdGuard Home collector.

The query log is not a queryable history: it is a rolling buffer read newest
first, paginated with an `older_than` cursor. Retention is limited and the
file grows, so the running totals live on our side and each poll only walks
back as far as the previous cursor.

Endpoint and credentials are asked for, never assumed: AdGuard often runs on
the same machine as Home Assistant, and just as often does not.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator

from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
from datetime import datetime, timezone

from .mapping import (
    HIDDEN_CLIENTS,
    Confirmation,
    Lease,
    Observation,
    ObservedFacts,
    QueryRecord,
    WalkWindow,
    aggregate,
    order_candidates,
    parse_clients,
    parse_leases,
    parse_time,
    parse_unlogged,
    run_zero_check,
    settle,
)

QUERYLOG_PATH = "/control/querylog"
QUERYLOG_CONFIG_PATH = "/control/querylog/config"
CLIENTS_PATH = "/control/clients"
DHCP_PATH = "/control/dhcp/status"
STATUS_PATH = "/control/status"

# AdGuard's reason field: Filtered* means the query was answered by a
# filter, NotFilteredWhiteList is an explicit allow and must not match.
_BLOCKED_PREFIX = "Filtered"

# A silent lease is asked about one by one, over the whole retained log,
# before it is called anything. Each question costs the resolver a scan of
# its log file, so the questions are bounded per poll and the hosts left
# over are asked first next time, and an answer is remembered for a day.
MAX_CONFIRMATIONS = 40
# AdGuard scans at most 50 000 log entries per search request, unless an
# `offset` is given, which lifts the cap: with offset=0 and limit=1 one
# request scans to the first hit or to the end of the log, and an empty
# `oldest` in the answer means the end was reached. A term in double quotes
# is an exact match on the host, the client id, the address and the client
# name: 192.168.1.4 no longer finds 192.168.1.40, but a query for the bare
# name "192.168.1.4" from another host does match, so a hit is read back
# for the client, and a foreign hit is stepped past with older_than.
CONFIRM_STEPS = 4


def parse_querylog_config(payload: Any) -> tuple[str | None, float | None]:
    """`/control/querylog/config`: whether the log can answer at all, and
    how far back it keeps entries.

    Returns a reason the log is hidden, or None, and the retention in
    seconds. A log that is switched off holds nothing, and one that
    anonymises client addresses on output matches the real address in the
    file but hands back x.y.0.0, so no host can ever be read back from it."""
    if not isinstance(payload, dict):
        return None, None
    hidden: str | None = None
    if payload.get("enabled") is False:
        hidden = "the query log is switched off"
    elif payload.get("anonymize_client_ip"):
        hidden = "client addresses are anonymised in the query log"
    interval = payload.get("interval")
    retention: float | None = None
    if isinstance(interval, (int, float)) and not isinstance(interval, bool) and interval > 0:
        # Milliseconds in the API, since v0.107.
        retention = float(interval) / 1000.0
    return hidden, retention


def _clients_look_hidden(observations: Iterable[Observation]) -> bool:
    """The data-side guard for a config read that failed: a walk whose every
    client is a placeholder or an anonymised x.y.0.0 says the same thing."""
    clients = {o.client for o in observations}
    if not clients:
        return False
    return all(c in HIDDEN_CLIENTS or c.endswith(".0.0") for c in clients)


def adguard_records(records: Iterable[dict[str, Any]]) -> Iterator[QueryRecord]:
    """AdGuard's query log entries as normalised records. A record without a
    client or a name is dropped here; one with an unreadable time is kept
    and dropped by the aggregation, which owns that rule."""
    for record in records:
        if not isinstance(record, dict):
            continue
        client = record.get("client")
        question = record.get("question") or {}
        fqdn = question.get("name") if isinstance(question, dict) else None
        if not client or not fqdn:
            continue
        yield QueryRecord(
            client=str(client),
            fqdn=str(fqdn),
            time=str(record.get("time") or ""),
            blocked=str(record.get("reason") or "").startswith(_BLOCKED_PREFIX),
        )


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
        remembered: dict[str, Confirmation] | None = None,
        now: datetime | None = None,
    ) -> ObservedFacts:
        now = now or datetime.now(timezone.utc)
        log_hidden, retention = parse_querylog_config(await self._read_optional(QUERYLOG_CONFIG_PATH))
        records, cursor, window = await self._read_querylog(since)
        observations = aggregate(adguard_records(records), previous)

        clients = await self._read_optional(CLIENTS_PATH)
        dhcp_available, leases = parse_leases(await self._read_optional(DHCP_PATH))
        unlogged = parse_unlogged(clients)

        zero = run_zero_check(
            observations, leases, dhcp_available, unlogged, window, retention, now
        )
        asked: dict[str, bool | None] = {}
        if log_hidden or _clients_look_hidden(observations):
            # A log that is off, or anonymised on output, cannot answer the
            # question: nothing is asked, the candidates stay unconfirmed,
            # and the check withholds itself with the setting named.
            zero = settle(zero, {})
        else:
            to_ask, answers = order_candidates(zero.unconfirmed, remembered or {}, now, window)
            asked, hits = await self._confirm(to_ask[:MAX_CONFIRMATIONS])
            answers.update(asked)
            zero = settle(zero, answers, not_asked=to_ask[MAX_CONFIRMATIONS:])
            if hits:
                # The entries the confirmation returned are real log entries:
                # fold them in, so the host is seen from now on and its
                # earlier query is in the totals at least once.
                observations = aggregate(adguard_records(hits), observations)

        stamp = now.isoformat(timespec="seconds")
        return ObservedFacts(
            observations=observations,
            leases=leases,
            client_names=parse_clients(clients),
            zero=zero,
            cursor=cursor or since,
            window_hours=self._window_hours,
            unlogged=unlogged,
            log_hidden=log_hidden,
            confirmations=tuple(
                Confirmation(ip=ip, answer=answer, asked_at=stamp) for ip, answer in asked.items()
            ),
        )

    async def _confirm(
        self, candidates: Iterable[Lease]
    ) -> tuple[dict[str, bool | None], list[dict[str, Any]]]:
        """Ask the resolver about each silent host over its whole log.

        Returns the answer per address and the entries that answered yes.
        The search is exact, one hit is enough, and an empty page counts as
        a no only once the server says it reached the end of the log."""
        answers: dict[str, bool | None] = {}
        hits: list[dict[str, Any]] = []
        for lease in candidates:
            answers[lease.ip] = None
            older_than: str | None = None
            for _ in range(CONFIRM_STEPS):
                params: dict[str, Any] = {"search": f'"{lease.ip}"', "limit": 1, "offset": 0}
                if older_than:
                    params["older_than"] = older_than
                try:
                    payload = await self._get(QUERYLOG_PATH, params)
                except ObservedAuthError:
                    raise
                except ObservedError:
                    break
                page = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(page, list):
                    break
                exact = [r for r in page if isinstance(r, dict) and r.get("client") == lease.ip]
                if exact:
                    answers[lease.ip] = True
                    hits.extend(exact)
                    break
                oldest = payload.get("oldest") if isinstance(payload, dict) else None
                if not oldest:
                    # End of the log reached with nothing from this host.
                    answers[lease.ip] = False
                    break
                if not page:
                    # Nothing matched and the end was not reached: the server
                    # stopped for a reason of its own. Not an answer.
                    break
                if oldest == older_than:
                    break  # the server stopped advancing; do not spin on it
                # A foreign hit, a query for the bare name from another host:
                # step past it and look further.
                older_than = str(oldest)
        return answers, hits

    async def probe(self) -> None:
        # /control/status answers on every AdGuard, before and after login;
        # a 401 there is the credentials, anything else is the address.
        await self._get(STATUS_PATH)

    async def _read_querylog(
        self, since: str | None
    ) -> tuple[list[dict[str, Any]], str | None, WalkWindow]:
        boundary = parse_time(since)
        collected: list[dict[str, Any]] = []
        newest: str | None = None
        oldest_walked: str | None = None
        older_than: str | None = None
        # Truncated until proven otherwise: the loop below clears it when it
        # reaches the previous cursor or the end of the log.
        truncated = True

        for _ in range(self._max_pages):
            params: dict[str, Any] = {"limit": self._page_size}
            if older_than:
                params["older_than"] = older_than

            payload = await self._get(QUERYLOG_PATH, params)
            page = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(page, list) or not page:
                truncated = False
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
                if isinstance(record, dict) and record.get("time"):
                    oldest_walked = str(record["time"])
            if reached_boundary:
                truncated = False
                break

            oldest = payload.get("oldest") if isinstance(payload, dict) else None
            if not oldest or oldest == older_than:
                truncated = False
                break  # the server stopped advancing; do not spin on it
            older_than = oldest

        window = WalkWindow(
            entries=len(collected), newest=newest, oldest=oldest_walked, truncated=truncated
        )
        return collected, newest, window

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return await self._transport.get_json(path, params)
        except ObservedError:
            raise
        except Exception as err:  # pragma: no cover - transport specific
            raise ObservedError(f"{path}: {err}") from err

    async def _read_optional(self, path: str) -> Any:
        """DHCP served by the router, or an appliance with clients hidden, is
        a normal setup, not an error. The caller degrades from an empty
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
        return await self.request_json("GET", path, params=params)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if self._session is None:
            await self.connect()
        assert self._session is not None

        async with self._session.request(
            method, f"{self._base_url}{path}", params=params, json=json, headers=headers
        ) as response:
            if response.status in (401, 403):
                raise ObservedAuthError(f"{path}: credentials rejected ({response.status})")
            if response.status >= 400:
                raise ObservedError(f"{path}: HTTP {response.status}")
            if response.status == 204:
                return None
            return await response.json(content_type=None)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
