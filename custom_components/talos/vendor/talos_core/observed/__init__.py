"""The observed side: what the resolver actually saw, and the tool's blind spots."""

from __future__ import annotations

from .adguard import AdGuardCollector, AiohttpJsonTransport
from .base import HttpTransport, ObservedAuthError, ObservedError, ObservedSource
from .classify import Classification, DomainClassifier, DomainRule
from .mapping import (
    Lease,
    Observation,
    ObservedFacts,
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
