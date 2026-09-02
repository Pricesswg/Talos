"""Reading EMQX 5's client list over its own API.

EMQX 4 published a topic per client under `$SYS`. EMQX 5 removed those and
left only gauges there, so a subscription answers with numbers and never a
name. What EMQX 5 does expose is `/api/v5/clients`, which lists every client
connected right now, with its address.

That address is worth more than the subscription ever was: a client id is a
name the client chose for itself, an address can be joined against the devices
in the scan the same way a DNS observation is. So a client that matches
nothing by name can still be attributed by where it connected from.

Parsing only. The request belongs to the integration, which owns the session.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..model import MqttClient, Scan
from .mqtt import match_clients

# The page size EMQX accepts. Its maximum is 10000; this is well inside it and
# keeps a single response small enough to parse without care.
EMQX_PAGE_SIZE = 1000

# How many pages to walk before giving up. A broker with more clients than
# this has a bigger problem than an unmatched client id.
EMQX_MAX_PAGES = 20

EMQX_CLIENTS_PATH = "/api/v5/clients"


def parse_emqx_clients(payload: Any) -> list[dict[str, Any]]:
    """The rows of one `/api/v5/clients` response.

    EMQX returns `{"data": [...], "meta": {...}}`. Anything else is a broker
    answering something we did not ask for, and produces no rows rather than
    an exception.
    """
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("clientid")]


def emqx_has_more(payload: Any, seen: int) -> bool:
    """Whether another page is worth asking for.

    EMQX reports `meta.hasnext` on recent builds and only a count on older
    ones, so both are read and neither is required.
    """
    meta = payload.get("meta") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        return False
    if "hasnext" in meta:
        return bool(meta["hasnext"])
    count = meta.get("count")
    return isinstance(count, int) and seen < count


def emqx_to_clients(rows: Iterable[dict[str, Any]], scan: Scan) -> tuple[MqttClient, ...]:
    """Attribute each row, by name first and by address second.

    The name is the client's own claim. The address is where it actually
    connected from, and if a device in the scan holds that address then the
    client is that device, whatever it decided to call itself.
    """
    rows = list(rows)
    device_by_ip = {device.ip: device.name for device in scan.devices if device.ip}
    by_name = {client.client_id: client for client in match_clients(
        (str(row["clientid"]) for row in rows), scan
    )}

    attributed: list[MqttClient] = []
    for row in rows:
        client_id = str(row["clientid"])
        address = _address(row)
        matched = by_name[client_id].matched if client_id in by_name else None
        if not matched and address:
            matched = device_by_ip.get(address)
        attributed.append(MqttClient(client_id=client_id, address=address, matched=matched))
    return tuple(sorted(attributed, key=lambda client: client.client_id))


def _address(row: dict[str, Any]) -> str | None:
    """The client's address, without the port EMQX sometimes appends."""
    raw = row.get("ip_address") or row.get("peerhost") or row.get("peername")
    if not raw:
        return None
    text = str(raw)
    # `1.2.3.4:51234`, but never an IPv6 address, which is full of colons.
    if text.count(":") == 1:
        text = text.split(":", 1)[0]
    return text or None
