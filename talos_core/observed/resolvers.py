"""Which resolvers Talos can read, and how to build the reader for one.

What Talos needs from the observed side is not "a DNS server" but a query
log it can ask for: per query, the client address, the name, the time, and
whether a filter answered it. Two appliances expose that over HTTP, and they
are the two kinds here. A router's own resolver, dnsmasq on OpenWrt or the
one inside a Fritz!Box or a UniFi gateway, keeps no such log where anything
can reach it: that is not a gap in Talos, it is data that does not exist in
a readable form. The way to observe a house behind such a router is to point
the router at one of these.
"""

from __future__ import annotations

from typing import Any

from .adguard import AdGuardCollector
from .base import HttpTransport, ObservedSource
from .pihole import PiholeCollector

RESOLVER_ADGUARD = "adguard"
RESOLVER_PIHOLE = "pihole"
RESOLVER_KINDS: tuple[str, ...] = (RESOLVER_ADGUARD, RESOLVER_PIHOLE)

# What each kind is called on screen, when the panel has no table for it.
RESOLVER_NAMES = {RESOLVER_ADGUARD: "AdGuard Home", RESOLVER_PIHOLE: "Pi-hole"}


def collector_for(
    kind: str,
    transport: HttpTransport,
    *,
    password: str = "",
    page_size: int = 500,
    max_pages: int = 40,
    window_hours: int = 24,
) -> ObservedSource:
    """The reader for a resolver kind. AdGuard authenticates on the
    transport, with basic auth on every request, so the password is the
    transport's business there; Pi-hole trades it for a session itself."""
    if kind == RESOLVER_ADGUARD:
        return AdGuardCollector(
            transport, page_size=page_size, max_pages=max_pages, window_hours=window_hours
        )
    if kind == RESOLVER_PIHOLE:
        return PiholeCollector(
            transport,
            password=password,
            page_size=page_size,
            max_pages=max_pages,
            window_hours=window_hours,
        )
    raise ValueError(f"unknown resolver kind: {kind!r}")


def resolver_name(kind: Any) -> str:
    return RESOLVER_NAMES.get(str(kind or ""), str(kind or "resolver"))
