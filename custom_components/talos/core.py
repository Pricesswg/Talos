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
        DEFAULT_WINDOW,
        BlockingCall,
        Churn,
        Correlation,
        Derived,
        DiagnosticRun,
        MqttClient,
        MqttFacts,
        ZigbeeFacts,
        RetentionPolicy,
        Reach,
        Scan,
        TalosStore,
        UnverifiedCheck,
        ZoneMap,
        attribute_churn,
        clamp_window,
        declared_targets,
        derive,
        parse_blocking_calls,
        validate,
    )
    from talos_core.observed import (  # noqa: F401
        AdGuardCollector,
        DomainClassifier,
        HttpTransport,
        EMQX_CLIENTS_PATH,
        EMQX_MAX_PAGES,
        EMQX_PAGE_SIZE,
        ObservedAuthError,
        ObservedError,
        aggregate,
        emqx_has_more,
        emqx_to_clients,
        match_clients,
        merge_observed,
        parse_devices,
        parse_emqx_clients,
        parse_info,
        roles_by_ieee,
    )
    from talos_core.export_html import render_html, render_json  # noqa: F401
    from talos_core.sources.mapping import (  # noqa: F401
        RegistryPayload,
        apply_mesh_roles,
        build_scan,
    )
    from talos_core.suggest import subnets, suggestions  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - HACS release layout
    from .vendor.talos_core import (  # type: ignore[no-redef]  # noqa: F401
        CheckEngine,
        DEFAULT_WINDOW,
        BlockingCall,
        Churn,
        Correlation,
        Derived,
        DiagnosticRun,
        MqttClient,
        MqttFacts,
        ZigbeeFacts,
        RetentionPolicy,
        Reach,
        Scan,
        TalosStore,
        UnverifiedCheck,
        ZoneMap,
        attribute_churn,
        clamp_window,
        declared_targets,
        derive,
        parse_blocking_calls,
        validate,
    )
    from .vendor.talos_core.observed import (  # type: ignore[no-redef]  # noqa: F401
        AdGuardCollector,
        DomainClassifier,
        HttpTransport,
        EMQX_CLIENTS_PATH,
        EMQX_MAX_PAGES,
        EMQX_PAGE_SIZE,
        ObservedAuthError,
        ObservedError,
        aggregate,
        emqx_has_more,
        emqx_to_clients,
        match_clients,
        merge_observed,
        parse_devices,
        parse_emqx_clients,
        parse_info,
        roles_by_ieee,
    )
    from .vendor.talos_core.export_html import (  # type: ignore[no-redef]  # noqa: F401
        render_html,
        render_json,
    )
    from .vendor.talos_core.sources.mapping import (  # type: ignore[no-redef]  # noqa: F401
        RegistryPayload,
        apply_mesh_roles,
        build_scan,
    )
    from .vendor.talos_core.suggest import subnets, suggestions  # type: ignore[no-redef]  # noqa: F401

__all__ = [
    "AdGuardCollector",
    "BlockingCall",
    "Churn",
    "DEFAULT_WINDOW",
    "DiagnosticRun",
    "Reach",
    "attribute_churn",
    "clamp_window",
    "declared_targets",
    "parse_blocking_calls",
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
    "ZigbeeFacts",
    "Scan",
    "TalosStore",
    "subnets",
    "suggestions",
    "UnverifiedCheck",
    "ZoneMap",
    "aggregate",
    "apply_mesh_roles",
    "build_scan",
    "derive",
    "EMQX_CLIENTS_PATH",
    "EMQX_MAX_PAGES",
    "EMQX_PAGE_SIZE",
    "emqx_has_more",
    "emqx_to_clients",
    "match_clients",
    "merge_observed",
    "parse_devices",
    "parse_emqx_clients",
    "parse_info",
    "roles_by_ieee",
    "render_html",
    "render_json",
    "validate",
]
