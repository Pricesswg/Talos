"""The observed side: what the resolver actually saw, and the tool's blind spots."""

from __future__ import annotations

from .adguard import AdGuardCollector, AiohttpJsonTransport, adguard_records
from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
from .pihole import PiholeCollector, parse_network_table, parse_pihole_leases, pihole_records
from .resolvers import (
    RESOLVER_ADGUARD,
    RESOLVER_KINDS,
    RESOLVER_NAMES,
    RESOLVER_PIHOLE,
    collector_for,
    resolver_name,
)
from .classify import Classification, DomainClassifier, DomainRule
from .mapping import (
    Lease,
    Observation,
    ObservedFacts,
    QueryRecord,
    ZeroCheck,
    aggregate,
    parse_clients,
    parse_leases,
    run_zero_check,
)
from .merge import merge_observed
from .emqx import (
    EMQX_CLIENTS_PATH,
    EMQX_MAX_PAGES,
    EMQX_PAGE_SIZE,
    emqx_has_more,
    emqx_to_clients,
    parse_emqx_clients,
)
from .mqtt import known_tokens, match_clients
from .zigbee2mqtt import (
    BridgeInfo,
    ZigbeeNode,
    parse_devices,
    parse_info,
    roles_by_ieee,
)

__all__ = [
    "AdGuardCollector",
    "AiohttpJsonTransport",
    "PiholeCollector",
    "QueryRecord",
    "RESOLVER_ADGUARD",
    "RESOLVER_KINDS",
    "RESOLVER_NAMES",
    "RESOLVER_PIHOLE",
    "adguard_records",
    "collector_for",
    "parse_network_table",
    "parse_pihole_leases",
    "pihole_records",
    "resolver_name",
    "Classification",
    "DomainClassifier",
    "DomainRule",
    "HttpTransport",
    "Lease",
    "Observation",
    "ObservedAuthError",
    "ObservedError",
    "ObservedFacts",
    "ObservedSource",
    "ZeroCheck",
    "aggregate",
    "EMQX_CLIENTS_PATH",
    "EMQX_MAX_PAGES",
    "EMQX_PAGE_SIZE",
    "emqx_has_more",
    "emqx_to_clients",
    "BridgeInfo",
    "ZigbeeNode",
    "match_clients",
    "parse_devices",
    "parse_info",
    "roles_by_ieee",
    "parse_emqx_clients",
    "merge_observed",
    "parse_clients",
    "parse_leases",
    "run_zero_check",
]
