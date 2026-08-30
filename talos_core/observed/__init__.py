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
    "merge_observed",
    "parse_clients",
    "parse_leases",
    "run_zero_check",
]
