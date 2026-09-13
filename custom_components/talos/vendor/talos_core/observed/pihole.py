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

from datetime import datetime, timezone
from typing import Any, Iterable, Iterator

from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
from .mapping import (
    Lease,
    Observation,
    ObservedFacts,
    QueryRecord,
    aggregate,
    parse_time,
    run_zero_check,
)

AUTH_PATH = "/api/auth"
QUERIES_PATH = "/api/queries"
LEASES_PATH = "/api/dhcp/leases"
DHCP_CONFIG_PATH = "/api/config/dhcp/active"
NETWORK_PATH = "/api/network/devices"
CLIENTS_PATH = "/api/clients"
VERSION_PATH = "/api/info/version"
SID_HEADER = "X-FTL-SID"

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
        if not mac or str(mac).lower() in ("00:00:00:00:00:00", "ip-"):
            continue
        for entry in device.get("ips") or ():
            if not isinstance(entry, dict) or not entry.get("ip"):
                continue
            ip = str(entry["ip"])
            name = entry.get("name") or None
            pairs.append(Lease(mac=str(mac).lower(), ip=ip, hostname=name, origin="network"))
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
    ) -> ObservedFacts:
        await self._login()
        try:
            queries, cursor = await self._read_queries(since)
            observations = aggregate(pihole_records(queries), previous)

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

            return ObservedFacts(
                observations=observations,
                leases=tuple(pairs),
                client_names=names,
                zero=run_zero_check(observations, pairs, table_available),
                cursor=cursor or since,
                window_hours=self._window_hours,
            )
        finally:
            await self._logout()

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

    async def _read_queries(self, since: str | None) -> tuple[list[dict[str, Any]], str | None]:
        boundary = parse_time(since)
        collected: list[dict[str, Any]] = []
        newest: str | None = None
        cursor: Any = None
        start = 0

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
            if reached_boundary or len(page) < self._page_size:
                break
            start += len(page)

        return collected, newest

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
