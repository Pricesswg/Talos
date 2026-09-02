"""Import shim for the standalone core.

During development `talos_core` sits at the repository root and is importable
directly. A HACS release bundles a copy under `vendor/`, because an
integration installed from HACS cannot rely on a package outside
`custom_components`. One place knows about both layouts so nothing else has
to.
"""

from __future__ import annotations

try:  # repository checkout, or an installed talos-core
    from talos_core import (  # noqa: F401
        Correlation,
        Derived,
        MqttClient,
        MqttFacts,
        RetentionPolicy,
        Scan,
        TalosStore,
        UnverifiedCheck,
        ZoneMap,
        derive,
        validate,
    )
    from talos_core.observed import (  # noqa: F401
        AdGuardCollector,
        DomainClassifier,
        HttpTransport,
        ObservedAuthError,
        ObservedError,
        aggregate,
        match_clients,
        merge_observed,
    )
    from talos_core.export_html import render_html, render_json  # noqa: F401
    from talos_core.sources.mapping import RegistryPayload, build_scan  # noqa: F401
    from talos_core.suggest import subnets, suggestions  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - HACS release layout
    from .vendor.talos_core import (  # type: ignore[no-redef]  # noqa: F401
        CheckEngine,
        Correlation,
        Derived,
        MqttClient,
        MqttFacts,
        RetentionPolicy,
        Scan,
        TalosStore,
        UnverifiedCheck,
        ZoneMap,
        derive,
        validate,
    )
    from .vendor.talos_core.observed import (  # type: ignore[no-redef]  # noqa: F401
        AdGuardCollector,
        DomainClassifier,
        HttpTransport,
        ObservedAuthError,
        ObservedError,
        aggregate,
        match_clients,
        merge_observed,
    )
    from .vendor.talos_core.export_html import (  # type: ignore[no-redef]  # noqa: F401
        render_html,
        render_json,
    )
    from .vendor.talos_core.sources.mapping import (  # type: ignore[no-redef]  # noqa: F401
        RegistryPayload,
        build_scan,
    )
    from .vendor.talos_core.suggest import subnets, suggestions  # type: ignore[no-redef]  # noqa: F401

__all__ = [
    "AdGuardCollector",
    "CheckEngine",
    "Correlation",
    "Derived",
    "DomainClassifier",
    "HttpTransport",
    "ObservedAuthError",
    "ObservedError",
    "RegistryPayload",
    "RetentionPolicy",
    "MqttClient",
    "MqttFacts",
    "Scan",
    "TalosStore",
    "subnets",
    "suggestions",
    "UnverifiedCheck",
    "ZoneMap",
    "aggregate",
    "build_scan",
    "derive",
    "match_clients",
    "merge_observed",
    "render_html",
    "render_json",
    "validate",
]
