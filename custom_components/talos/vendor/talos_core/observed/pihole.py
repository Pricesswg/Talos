"""Pi-hole v6 collector.

Pi-hole keeps its queries in a database and hands them out newest first,
pinned to a cursor so paging stays stable while new queries arrive. Access is
a session: the web password is traded for a SID at /api/auth, sent back as a
header on every call, and released at the end so the appliance's session
table does not fill up with what Talos left behind. With no password set the
API is open and no session is made.

What it has that AdGuard lacks is a network table. Pi-hole records every MAC
and IP it sees on the wire, from ARP and neighbour discovery, whether or not
it serves DHCP. So the join between the registry and the query log works on a
Pi-hole even when the router hands out the addresses. Those pairs are kept
apart from real leases by their origin, and the report says which one it
used.

Only v6 is spoken here. The v5 API was a PHP page with a token in the query
string and no session; it is out of support upstream, and its query listing
lacks the cursor that makes incremental reading safe.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator

from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
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
    parse_time,
    run_zero_check,
    settle,
)

AUTH_PATH = "/api/auth"
QUERIES_PATH = "/api/queries"
LEASES_PATH = "/api/dhcp/leases"
DHCP_CONFIG_PATH = "/api/config/dhcp/active"
NETWORK_PATH = "/api/network/devices"
CLIENTS_PATH = "/api/clients"
VERSION_PATH = "/api/info/version"
PRIVACY_PATH = "/api/config/misc/privacylevel"
EXCLUDE_PATH = "/api/config/webserver/api/excludeClients"
MAXDBDAYS_PATH = "/api/config/database/maxDBdays"
SID_HEADER = "X-FTL-SID"

# Same bound as AdGuard's: one request per silent host, per poll. Each one
# reads the long-term database on disk, which the API warns is heavy on a
# Pi, so the bound is real and the answers are remembered for a day.
MAX_CONFIRMATIONS = 40
CONFIRM_BUDGET_SECONDS = 45.0

# Pi-hole's privacy levels. Above zero the log stops naming things, and
# what it stops naming is exactly what the join needs. From level 2 the
# client is written as 0.0.0.0, so no lease can ever be seen and the
# silence question has no answer: it is not asked.
PRIVACY_LEVELS = {
    1: "domains are hidden in the query log",
    2: "domains and clients are hidden in the query log",
    3: "the query log is anonymised: no domain and no client",
}
CLIENTS_HIDDEN_FROM = 2

# Pi-hole's status names. Anything answered by a list, a regex or an
# upstream that blocked it counts as blocked; CACHE, FORWARDED, RETRIED and
# the rest are answers.
BLOCKED_PREFIXES = ("GRAVITY", "REGEX", "DENYLIST", "EXTERNAL_BLOCKED", "SPECIAL_DOMAIN")

# The network table is asked for whole, within reason: a home has tens of
# devices, and a table that large is a sign of something else going on.
MAX_NETWORK_DEVICES = 2000
MAX_ADDRESSES_PER_DEVICE = 8


def pihole_records(queries: Iterable[dict[str, Any]]) -> Iterator[QueryRecord]:
    """Pi-hole's query entries as normalised records.

    The client is an object carrying the address and the name Pi-hole
    resolved for it; the address is the key, the name is noise here because
    the registry names things itself. Time arrives as Unix seconds and leaves
    as RFC 3339 in UTC, the form the aggregation and the cursor expect."""
    for query in queries:
        if not isinstance(query, dict):
            continue
        client = query.get("client")
        address = client.get("ip") if isinstance(client, dict) else client
        fqdn = query.get("domain")
        if not address or not fqdn:
            continue
        yield QueryRecord(
            client=str(address),
            fqdn=str(fqdn),
            time=_iso(query.get("time")),
            blocked=str(query.get("status") or "").upper().startswith(BLOCKED_PREFIXES),
        )


def parse_pihole_leases(payload: Any) -> tuple[Lease, ...]:
    """`/api/dhcp/leases`: what Pi-hole's own DHCP server handed out."""
    if not isinstance(payload, dict):
        return ()
    leases: list[Lease] = []
    for raw in payload.get("leases") or ():
        if not isinstance(raw, dict):
            continue
        mac, ip = raw.get("hwaddr"), raw.get("ip")
        if not mac or not ip:
            continue
        leases.append(
            Lease(mac=str(mac).lower(), ip=str(ip), hostname=raw.get("name") or None, origin="dhcp")
        )
    return tuple(leases)


def parse_network_table(payload: Any) -> tuple[tuple[Lease, ...], dict[str, str]]:
    """`/api/network/devices`: every MAC with the addresses seen behind it.

    Returns the pairs as leases of origin "network", and the names Pi-hole
    attached to the addresses, which double as client names. A MAC with
    several addresses yields one pair per address: a device that moved
    between two IPs is two rows, and the newer one wins the join later."""
    if not isinstance(payload, dict):
        return (), {}
    pairs: list[Lease] = []
    names: dict[str, str] = {}
    for device in payload.get("devices") or ():
        if not isinstance(device, dict):
            continue
        mac = device.get("hwaddr")
        # FTL files an address it saw without a MAC under a pseudo MAC of
        # the form ip-<address>: no device to join, nothing to keep.
        if not mac or str(mac).lower() == "00:00:00:00:00:00" or str(mac).lower().startswith("ip-"):
            continue
        count = device.get("numQueries")
        queried = (int(count) > 0) if isinstance(count, (int, float)) and not isinstance(count, bool) else None
        for entry in device.get("ips") or ():
            if not isinstance(entry, dict) or not entry.get("ip"):
                continue
            ip = str(entry["ip"])
            name = entry.get("name") or None
            pairs.append(
                Lease(
                    mac=str(mac).lower(),
                    ip=ip,
                    hostname=name,
                    origin="network",
                    seen_at=_iso(entry.get("lastSeen")) or None,
                    queried=queried,
                )
            )
            if name:
                names[ip] = str(name)
    return tuple(pairs), names


def parse_pihole_clients(payload: Any) -> dict[str, str]:
    """`/api/clients`: the clients someone named in the Pi-hole UI. The
    key is whatever they typed, an address or a MAC, and the comment is the
    name."""
    names: dict[str, str] = {}
    if not isinstance(payload, dict):
        return names
    for raw in payload.get("clients") or ():
        if not isinstance(raw, dict):
            continue
        key, comment = raw.get("client"), raw.get("comment")
        if key and comment:
            names[str(key).lower()] = str(comment)
    return names


class PiholeCollector(ObservedSource):
    """Incremental reader over the Pi-hole v6 REST API."""

    def __init__(
        self,
        transport: HttpTransport,
        *,
        password: str = "",
        page_size: int = 500,
        max_pages: int = 40,
        window_hours: int = 24,
    ) -> None:
        self._transport = transport
        self._password = password
        self._page_size = page_size
        # A budget, not a guess: the same reasoning as for AdGuard.
        self._max_pages = max_pages
        self._window_hours = window_hours
        self._headers: dict[str, str] = {}

    async def probe(self) -> None:
        # Logging in is the credential check; the version call is the
        # address check on an open appliance, where login is skipped.
        await self._login()
        try:
            await self._get(VERSION_PATH)
        finally:
            await self._logout()

    async def fetch(
        self,
        since: str | None = None,
        previous: Iterable[Observation] = (),
        remembered: dict[str, Confirmation] | None = None,
        now: datetime | None = None,
    ) -> ObservedFacts:
        now = now or datetime.now(timezone.utc)
        await self._login()
        try:
            privacy = _privacy_level(await self._read_optional(PRIVACY_PATH))
            excluded = parse_exclude_clients(await self._read_optional(EXCLUDE_PATH))
            retention = _max_db_seconds(await self._read_optional(MAXDBDAYS_PATH))
            queries, cursor, window = await self._read_queries(since)
            observations = aggregate(pihole_records(queries), previous)
            # A config read that failed is not level 0: a walk whose every
            # client is the placeholder says the clients are hidden.
            if privacy is None:
                privacy = CLIENTS_HIDDEN_FROM if _walk_is_hidden(observations) else None

            leases = list(parse_pihole_leases(await self._read_optional(LEASES_PATH)))
            dhcp_active = _dhcp_active(await self._read_optional(DHCP_CONFIG_PATH))
            network, network_names = parse_network_table(
                await self._read_optional(
                    NETWORK_PATH,
                    {"max_devices": MAX_NETWORK_DEVICES, "max_addresses": MAX_ADDRESSES_PER_DEVICE},
                )
            )
            names = dict(network_names)
            names.update(parse_pihole_clients(await self._read_optional(CLIENTS_PATH)))

            # Real leases are authoritative for their MAC; the network table
            # fills in every other MAC it has seen.
            leased_macs = {lease.mac for lease in leases}
            pairs = leases + [pair for pair in network if pair.mac not in leased_macs]
            table_available = dhcp_active or bool(pairs)

            # The exclusion list is regular expressions over the client's
            # address or name. A pair that matches is kept out of the API's
            # answers, walk and confirmation alike: unlogged, like AdGuard's
            # flag, and never a candidate.
            unlogged = tuple(
                sorted(
                    {
                        pair.ip
                        for pair in pairs
                        if _excluded(pair, names.get(pair.ip), excluded)
                    }
                )
            )
            zero = run_zero_check(
                observations, pairs, table_available, unlogged, window, retention, now
            )
            asked: dict[str, bool | None] = {}
            hits: list[dict[str, Any]] = []
            hidden = privacy is not None and privacy >= CLIENTS_HIDDEN_FROM
            if hidden or privacy is None or retention == 0:
                # No filter can answer: clients are hidden, or the level could
                # not be read and the walk did not settle it, or nothing is
                # ever written to the long-term database. Leave the
                # candidates unconfirmed and the check withholds itself.
                zero = settle(zero, {})
            else:
                to_ask, answers = order_candidates(zero.unconfirmed, remembered or {}, now, window)
                asked, hits = await self._confirm(to_ask[:MAX_CONFIRMATIONS])
                answers.update(asked)
                skipped = [lease for lease in to_ask if lease.ip not in asked]
                zero = settle(zero, answers, not_asked=skipped)
                if hits:
                    observations = aggregate(pihole_records(hits), observations)

            if hidden or (privacy is not None and privacy > 0):
                log_hidden = PRIVACY_LEVELS.get(privacy or 0)
            elif privacy is None:
                log_hidden = "the privacy level could not be read, so whether clients are shown is unknown"
            elif retention == 0:
                log_hidden = "the long-term query database is disabled (maxDBdays is 0), so the log holds only what is in memory"
            else:
                log_hidden = None

            stamp = now.isoformat(timespec="seconds")
            return ObservedFacts(
                observations=observations,
                leases=tuple(pairs),
                client_names=names,
                zero=zero,
                cursor=cursor or since,
                window_hours=self._window_hours,
                unlogged=unlogged,
                log_hidden=log_hidden,
                confirmations=tuple(
                    Confirmation(ip=ip, answer=answer, asked_at=stamp)
                    for ip, answer in asked.items()
                ),
            )
        finally:
            await self._logout()

    async def _confirm(
        self, candidates: Iterable[Lease]
    ) -> tuple[dict[str, bool | None], list[dict[str, Any]]]:
        """Ask about each silent host over the long-term database.

        Without `disk` the API answers from memory, which holds a day at
        most; `disk=true` reads the database on disk, the whole retention.
        `client_ip` is an exact filter, so one entry back is a yes and an
        empty page is a no."""
        answers: dict[str, bool | None] = {}
        hits: list[dict[str, Any]] = []
        started = time.monotonic()
        for lease in candidates:
            if time.monotonic() - started > CONFIRM_BUDGET_SECONDS:
                break
            try:
                payload = await self._get(
                    QUERIES_PATH, {"client_ip": lease.ip, "length": 1, "disk": "true"}
                )
            except ObservedAuthError:
                raise
            except ObservedError:
                answers[lease.ip] = None
                continue
            page = payload.get("queries") if isinstance(payload, dict) else None
            if not isinstance(page, list):
                answers[lease.ip] = None
                continue
            exact = [q for q in page if isinstance(q, dict) and _client_ip(q) == lease.ip]
            if exact:
                answers[lease.ip] = True
                hits.extend(exact)
                continue
            # An empty page from an empty database is not an absence: the
            # response says how many rows the disk table holds at all.
            total = payload.get("recordsTotal") if isinstance(payload, dict) else None
            answers[lease.ip] = False if (total is None or int(total or 0) > 0) else None
        return answers, hits

    # ── session ──────────────────────────────────────────────────────────

    async def _login(self) -> None:
        if not self._password:
            self._headers = {}
            return
        try:
            payload = await self._transport.request_json(
                "POST", AUTH_PATH, json={"password": self._password}
            )
        except ObservedAuthError:
            raise
        except ObservedError:
            raise
        except Exception as err:  # pragma: no cover - transport specific
            raise ObservedError(f"{AUTH_PATH}: {err}") from err
        session = payload.get("session") if isinstance(payload, dict) else None
        sid = session.get("sid") if isinstance(session, dict) and session.get("valid") else None
        if not sid:
            raise ObservedAuthError(f"{AUTH_PATH}: password rejected")
        self._headers = {SID_HEADER: str(sid)}

    async def _logout(self) -> None:
        if not self._headers:
            return
        headers, self._headers = self._headers, {}
        try:
            await self._transport.request_json("DELETE", AUTH_PATH, headers=headers)
        except Exception:  # noqa: BLE001 - a session left behind expires on its own
            pass

    # ── queries ──────────────────────────────────────────────────────────

    async def _read_queries(
        self, since: str | None
    ) -> tuple[list[dict[str, Any]], str | None, WalkWindow]:
        boundary = parse_time(since)
        collected: list[dict[str, Any]] = []
        newest: str | None = None
        oldest_walked: str | None = None
        cursor: Any = None
        start = 0
        truncated = True

        for _ in range(self._max_pages):
            params: dict[str, Any] = {"length": self._page_size, "start": start}
            if boundary is not None:
                # Ask only for what is newer; the boundary check below still
                # runs, because `from` is inclusive and the clock is theirs.
                params["from"] = int(boundary.timestamp())
            if cursor is not None:
                params["cursor"] = cursor

            payload = await self._get(QUERIES_PATH, params)
            page = payload.get("queries") if isinstance(payload, dict) else None
            if not isinstance(page, list) or not page:
                truncated = False
                break
            if cursor is None:
                cursor = payload.get("cursor")
            if newest is None:
                newest = _iso(page[0].get("time"))

            reached_boundary = False
            for query in page:
                stamp = parse_time(_iso(query.get("time")))
                if boundary is not None and stamp is not None and stamp <= boundary:
                    reached_boundary = True
                    break
                collected.append(query)
                if isinstance(query, dict) and query.get("time") is not None:
                    oldest_walked = _iso(query.get("time"))
            if reached_boundary or len(page) < self._page_size:
                truncated = False
                break
            start += len(page)

        window = WalkWindow(
            entries=len(collected), newest=newest, oldest=oldest_walked, truncated=truncated
        )
        return collected, newest, window

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return await self._transport.request_json(
                "GET", path, params=params, headers=self._headers or None
            )
        except ObservedError:
            raise
        except Exception as err:  # pragma: no cover - transport specific
            raise ObservedError(f"{path}: {err}") from err

    async def _read_optional(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """A Pi-hole with DHCP off, or an API build without an endpoint, is a
        normal setup. The caller degrades from an empty answer and says so."""
        try:
            return await self._get(path, params)
        except ObservedAuthError:
            raise
        except ObservedError:
            return None


def _privacy_level(payload: Any) -> int | None:
    """`/api/config/misc/privacylevel`: what the log is allowed to show.
    Unreadable is None, not 0: it is not known that everything is shown."""
    config = payload.get("config") if isinstance(payload, dict) else None
    misc = config.get("misc") if isinstance(config, dict) else None
    level = misc.get("privacylevel") if isinstance(misc, dict) else None
    try:
        return max(0, int(level))
    except (TypeError, ValueError):
        return None


def _walk_is_hidden(observations: Iterable[Observation]) -> bool:
    clients = {o.client for o in observations}
    return bool(clients) and clients <= HIDDEN_CLIENTS


def _max_db_seconds(payload: Any) -> float | None:
    """`/api/config/database/maxDBdays`: how long queries stay on disk. 0
    means they are never written there. Unreadable is unknown."""
    config = payload.get("config") if isinstance(payload, dict) else None
    database = config.get("database") if isinstance(config, dict) else None
    days = database.get("maxDBdays") if isinstance(database, dict) else None
    try:
        days = float(days)
    except (TypeError, ValueError):
        return None
    return max(0.0, days) * 86400.0


def parse_exclude_clients(payload: Any) -> tuple[Any, ...]:
    """`/api/config/webserver/api/excludeClients`: regular expressions the
    API applies to a client's address or name before answering. Compiled
    here; a pattern that does not compile is skipped."""
    import re

    config = payload.get("config") if isinstance(payload, dict) else None
    webserver = config.get("webserver") if isinstance(config, dict) else None
    api = webserver.get("api") if isinstance(webserver, dict) else None
    raw = api.get("excludeClients") if isinstance(api, dict) else None
    patterns = []
    for item in raw or ():
        try:
            patterns.append(re.compile(str(item)))
        except re.error:
            continue
    return tuple(patterns)


def _excluded(pair: Lease, name: str | None, patterns: tuple[Any, ...]) -> bool:
    for pattern in patterns:
        for text in (pair.ip, pair.hostname, name):
            if text and pattern.search(str(text)):
                return True
    return False


def _client_ip(query: dict[str, Any]) -> str | None:
    client = query.get("client")
    if isinstance(client, dict):
        return client.get("ip")
    return client if isinstance(client, str) else None


def _dhcp_active(payload: Any) -> bool:
    config = payload.get("config") if isinstance(payload, dict) else None
    dhcp = config.get("dhcp") if isinstance(config, dict) else None
    return bool(dhcp.get("active")) if isinstance(dhcp, dict) else False


def _iso(value: Any) -> str:
    """Unix seconds, possibly fractional, as RFC 3339 in UTC. Anything else
    is returned as text, so an unreadable stamp fails the aggregation's
    parse and is dropped there rather than here."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    return "" if value is None else str(value)
