"""Talos core: data model, schema and validator.

Deliberately free of any `homeassistant.*` import. The logic has to be
testable against JSON fixtures without a running Home Assistant, or it stops
being testable in CI and every HA release turns into a regression risk.
"""

from __future__ import annotations

from .checks import CheckEngine, CheckReport, CheckResult, default_engine
from .const import SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS
from .zones import ZoneMap
from .diagnostics import (
    DEFAULT_WINDOW,
    BlockingCall,
    Churn,
    DiagnosticRun,
    Reach,
    attribute_churn,
    clamp_window,
    declared_targets,
    parse_blocking_calls,
)
from .derive import (
    Autonomy,
    Derived,
    Exposure,
    InheritedExposure,
    Matrix,
    VendorExposure,
    VendorLoss,
    build_autonomy,
    build_exposure,
    build_matrix,
    derive,
)
from .errors import CODES, Finding, TalosSchemaError
from .storage import PruneReport, RetentionPolicy, StoreStats, TalosStore
from .model import (
    Conduit,
    Correlation,
    Destination,
    Device,
    Integration,
    MqttClient,
    MqttFacts,
    Scan,
    ZigbeeFacts,
    SourceRef,
    UnverifiedCheck,
)
from .validate import is_valid, validate

__all__ = [
    "Autonomy",
    "BlockingCall",
    "Churn",
    "DEFAULT_WINDOW",
    "DiagnosticRun",
    "Reach",
    "attribute_churn",
    "clamp_window",
    "declared_targets",
    "parse_blocking_calls",
    "CODES",
    "CheckEngine",
    "CheckReport",
    "CheckResult",
    "Conduit",
    "Correlation",
    "Derived",
    "Destination",
    "Device",
    "Exposure",
    "Finding",
    "InheritedExposure",
    "Integration",
    "Matrix",
    "MqttClient",
    "MqttFacts",
    "ZigbeeFacts",
    "PruneReport",
    "RetentionPolicy",
    "SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "Scan",
    "SourceRef",
    "StoreStats",
    "TalosSchemaError",
    "TalosStore",
    "UnverifiedCheck",
    "ZoneMap",
    "VendorExposure",
    "VendorLoss",
    "build_autonomy",
    "build_exposure",
    "build_matrix",
    "default_engine",
    "derive",
    "is_valid",
    "validate",
]

__version__ = "1.16.0"
