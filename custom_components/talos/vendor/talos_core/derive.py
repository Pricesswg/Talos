"""Derivations: the matrix, offline autonomy and external exposure.

Three separate answers, deliberately not merged into one score.

Autonomy and exposure are **orthogonal**. A device can send telemetry every
minute and still work perfectly with the router unplugged; another can be
silent on the wire and stop dead the moment its vendor's API blinks. Folding
them into a single "how safe are you" number flattens four different
situations into one, and none of the four gets the fix it needs.

Everything here is a pure function of a `Scan`. No I/O, no clock, no network:
the same document always derives the same numbers, which is what makes any of
it falsifiable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .checks import CheckEngine, CheckReport, default_engine
from .const import (
    CLOUD_IOT_CLASSES,
    INFRA_DESTINATION_KINDS,
    LOCAL_IOT_CLASSES,
    PHONE_HOME_DESTINATION_KINDS,
    VENDOR_DESTINATION_KINDS,
)
from .model import Correlation, Destination, Device, Integration, Scan


@dataclass(frozen=True, slots=True)
class InheritedExposure:
    """A device exposed only through the hub above it.

    Kept out of the matrix quadrants on purpose. Nine Hue lamps behind one
    talkative bridge are one thing to fix, not ten, and putting them in the
    red quadrant would triple a number whose whole value is that it is small
    and actionable.
    """

    device_id: str
    hub_id: str
    destination_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "device_id": self.device_id,
            "hub_id": self.hub_id,
            "destination_id": self.destination_id,
        }


@dataclass(frozen=True, slots=True)
class Matrix:
    """How HA talks to a device, crossed with what the resolver saw it do.

    Rows come from `iot_class`, columns from first-hand observation. The two
    axes are independent: `local_egress` is the quadrant the tool exists for.
    """

    local_silent: tuple[str, ...] = ()
    local_egress: tuple[str, ...] = ()
    cloud_silent: tuple[str, ...] = ()
    cloud_egress: tuple[str, ...] = ()
    # iot_class is assumed_state, calculated or unknown: neither row applies.
    unclassified: tuple[str, ...] = ()
    # Sits in a silent column but is not strictly silent: its only egress went
    # to NTP or an update server. Reported so the simplification stays visible.
    infra_only: tuple[str, ...] = ()
    inherited: tuple[InheritedExposure, ...] = ()

    @property
    def key_quadrant(self) -> tuple[str, ...]:
        """Local to Home Assistant, yet phoning home on its own."""
        return self.local_egress

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_silent": list(self.local_silent),
            "local_egress": list(self.local_egress),
            "cloud_silent": list(self.cloud_silent),
            "cloud_egress": list(self.cloud_egress),
            "unclassified": list(self.unclassified),
            "infra_only": list(self.infra_only),
            "inherited": [i.to_dict() for i in self.inherited],
        }


@dataclass(frozen=True, slots=True)
class VendorLoss:
    """What one vendor's outage takes with it."""

    vendor: str
    integration_ids: tuple[str, ...]
    entities: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "integration_ids": list(self.integration_ids),
            "entities": self.entities,
        }


@dataclass(frozen=True, slots=True)
class Autonomy:
    """What still works with the uplink down.

    Derived from `iot_class`, which is a declaration, not a measurement: a
    cloud integration may hold a local fallback and a local one may need the
    cloud to re-authenticate after a restart. The numbers are an estimate and
    the UI has to say so.
    """

    entities_total: int = 0
    entities_local: int = 0
    entities_cloud: int = 0
    entities_unclassified: int = 0
    integrations_cloud: tuple[str, ...] = ()
    # Per vendor, worst first. Vendors can overlap if one integration talks to
    # several, so these do not sum to entities_cloud — that total is the one
    # to quote, these are for deciding what to replace first.
    losses: tuple[VendorLoss, ...] = ()

    @property
    def local_ratio(self) -> float:
        return self.entities_local / self.entities_total if self.entities_total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities_total": self.entities_total,
            "entities_local": self.entities_local,
            "entities_cloud": self.entities_cloud,
            "entities_unclassified": self.entities_unclassified,
            "integrations_cloud": list(self.integrations_cloud),
            "losses": [loss.to_dict() for loss in self.losses],
        }


@dataclass(frozen=True, slots=True)
class VendorExposure:
    """Who a set of devices talks to, and how insistently."""

    vendor: str
    destination_ids: tuple[str, ...]
    devices_direct: tuple[str, ...]
    devices_inherited: tuple[str, ...]
    queries: int
    blocked_queries: int
    # Which kinds of evidence back this entry. A vendor reached only through
    # a declared dependency and one caught in the query log are different
    # claims, and the list must not present them as the same one.
    evidence: tuple[str, ...] = ()

    @property
    def is_observed(self) -> bool:
        return "observed" in self.evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "evidence": list(self.evidence),
            "destination_ids": list(self.destination_ids),
            "devices_direct": list(self.devices_direct),
            "devices_inherited": list(self.devices_inherited),
            "queries": self.queries,
            "blocked_queries": self.blocked_queries,
        }


@dataclass(frozen=True, slots=True)
class Exposure:
    """Who talks outside the house. Says with whom, never what about."""

    devices_total: int = 0
    devices_direct: tuple[str, ...] = ()
    devices_inherited: tuple[str, ...] = ()
    vendors: tuple[VendorExposure, ...] = ()
    # Hosts the resolver saw that match nothing in the registry. Not exposure
    # in itself: a hole in the map, which is worse, because it is unmeasured.
    unknown_hosts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "devices_total": self.devices_total,
            "devices_direct": list(self.devices_direct),
            "devices_inherited": list(self.devices_inherited),
            "vendors": [v.to_dict() for v in self.vendors],
            "unknown_hosts": list(self.unknown_hosts),
        }


@dataclass(frozen=True, slots=True)
class Derived:
    """Everything the panel needs, both views, from one scan."""

    matrix: Matrix
    autonomy: Autonomy
    exposure: Exposure
    correlation: Correlation
    checks: CheckReport = field(default_factory=CheckReport)
    unverified_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix": self.matrix.to_dict(),
            "autonomy": self.autonomy.to_dict(),
            "exposure": self.exposure.to_dict(),
            "correlation": self.correlation.to_dict(),
            "checks": self.checks.to_dict(),
            "unverified_count": self.unverified_count,
        }


def derive(scan: Scan, engine: CheckEngine | None = None) -> Derived:
    """Compute every derivation from a validated scan."""
    context = _Context(scan)
    matrix = build_matrix(scan, context)
    # The checks run on the matrix, so they see the same quadrants the panel
    # shows: one classification, not two that can drift apart.
    report = (engine or default_engine()).run(scan, matrix)
    return Derived(
        matrix=matrix,
        autonomy=build_autonomy(scan, context),
        exposure=build_exposure(scan, context),
        correlation=scan.correlation,
        checks=report,
        # Everything the scan could not verify, plus every check that could
        # not run. Never folded into the passes.
        unverified_count=len(report.unverified),
    )


class _Context:
    """Indexes built once and shared by the three derivations."""

    def __init__(self, scan: Scan) -> None:
        self.devices: dict[str, Device] = {d.id: d for d in scan.devices}
        self.integrations: dict[str, Integration] = {i.id: i for i in scan.integrations}
        self.destinations: dict[str, Destination] = {d.id: d for d in scan.destinations}

    def iot_class_of(self, device: Device) -> str:
        integration = self.integrations.get(device.integration_id)
        return integration.iot_class if integration else "unknown"

    def destination_of(self, destination_id: str) -> Destination | None:
        return self.destinations.get(destination_id)

    def vendor_label(self, destination: Destination) -> str:
        """A name a person recognises. Falls back to the hostname rather than
        inventing a vendor we were never told."""
        return destination.vendor or destination.fqdn


def build_matrix(scan: Scan, context: _Context | None = None) -> Matrix:
    context = context or _Context(scan)

    phone_home: dict[str, bool] = {}
    infra: dict[str, bool] = {}
    inherited: list[InheritedExposure] = []

    for conduit in scan.conduits:
        if conduit.source.kind != "device" or not conduit.source.id:
            continue
        destination = context.destination_of(conduit.destination_id)
        if destination is None:
            continue

        if conduit.evidence == "observed":
            if destination.kind in PHONE_HOME_DESTINATION_KINDS:
                phone_home[conduit.source.id] = True
            elif destination.kind in INFRA_DESTINATION_KINDS:
                infra[conduit.source.id] = True
        elif conduit.evidence == "inherited" and conduit.inherited_from:
            if destination.kind in PHONE_HOME_DESTINATION_KINDS:
                inherited.append(
                    InheritedExposure(
                        device_id=conduit.source.id,
                        hub_id=conduit.inherited_from,
                        destination_id=conduit.destination_id,
                    )
                )

    buckets: dict[str, list[str]] = {
        "local_silent": [],
        "local_egress": [],
        "cloud_silent": [],
        "cloud_egress": [],
        "unclassified": [],
    }

    for device in scan.devices:
        iot_class = context.iot_class_of(device)
        has_egress = phone_home.get(device.id, False)
        if iot_class in LOCAL_IOT_CLASSES:
            row = "local"
        elif iot_class in CLOUD_IOT_CLASSES:
            row = "cloud"
        else:
            buckets["unclassified"].append(device.id)
            continue
        buckets[f"{row}_{'egress' if has_egress else 'silent'}"].append(device.id)

    infra_only = sorted(d for d in infra if not phone_home.get(d, False))

    return Matrix(
        local_silent=_sorted(buckets["local_silent"]),
        local_egress=_sorted(buckets["local_egress"]),
        cloud_silent=_sorted(buckets["cloud_silent"]),
        cloud_egress=_sorted(buckets["cloud_egress"]),
        unclassified=_sorted(buckets["unclassified"]),
        infra_only=tuple(infra_only),
        inherited=tuple(
            sorted(inherited, key=lambda i: (i.device_id, i.destination_id))
        ),
    )


def build_autonomy(scan: Scan, context: _Context | None = None) -> Autonomy:
    context = context or _Context(scan)

    total = local = cloud = unclassified = 0
    cloud_integrations: list[str] = []

    for integration in scan.integrations:
        total += integration.entity_count
        if integration.iot_class in LOCAL_IOT_CLASSES:
            local += integration.entity_count
        elif integration.iot_class in CLOUD_IOT_CLASSES:
            cloud += integration.entity_count
            cloud_integrations.append(integration.id)
        else:
            unclassified += integration.entity_count

    # Attribute each cloud integration to the vendors it declares a
    # dependency on. A declared conduit is what makes it a functional
    # dependency; a merely observed one is exposure, which is the other axis.
    cloud_lookup = set(cloud_integrations)
    by_vendor: dict[str, set[str]] = {}
    for conduit in scan.conduits:
        if conduit.evidence != "declared" or conduit.source.kind != "integration":
            continue
        integration_id = conduit.source.id
        if integration_id not in cloud_lookup:
            continue
        destination = context.destination_of(conduit.destination_id)
        if destination is None or destination.kind not in VENDOR_DESTINATION_KINDS:
            continue
        by_vendor.setdefault(context.vendor_label(destination), set()).add(integration_id)

    attributed = {i for ids in by_vendor.values() for i in ids}
    for integration_id in cloud_integrations:
        if integration_id in attributed:
            continue
        # Cloud-bound but with nothing declared to attribute it to. Name it
        # after the integration rather than dropping it from the list.
        integration = context.integrations[integration_id]
        by_vendor.setdefault(integration.title, set()).add(integration_id)

    losses = [
        VendorLoss(
            vendor=vendor,
            integration_ids=_sorted(ids),
            entities=sum(context.integrations[i].entity_count for i in ids),
        )
        for vendor, ids in by_vendor.items()
    ]
    losses.sort(key=lambda loss: (-loss.entities, loss.vendor))

    return Autonomy(
        entities_total=total,
        entities_local=local,
        entities_cloud=cloud,
        entities_unclassified=unclassified,
        integrations_cloud=_sorted(cloud_integrations),
        losses=tuple(losses),
    )


def build_exposure(scan: Scan, context: _Context | None = None) -> Exposure:
    context = context or _Context(scan)

    vendors: dict[str, dict[str, Any]] = {}
    direct: set[str] = set()
    through_hub: set[str] = set()
    unknown_hosts: set[str] = set()

    for conduit in scan.conduits:
        destination = context.destination_of(conduit.destination_id)
        if destination is None or destination.kind not in PHONE_HOME_DESTINATION_KINDS:
            continue

        if conduit.source.kind == "unknown_host" and conduit.source.id:
            unknown_hosts.add(conduit.source.id)

        label = context.vendor_label(destination)
        bucket = vendors.setdefault(
            label,
            {
                "destinations": set(),
                "direct": set(),
                "inherited": set(),
                "queries": 0,
                "blocked": 0,
                "evidence": set(),
            },
        )
        bucket["destinations"].add(destination.id)
        bucket["evidence"].add(conduit.evidence)

        if conduit.evidence == "observed":
            count = conduit.query_count or 0
            bucket["queries"] += count
            if conduit.filter_status == "blocked":
                bucket["blocked"] += count
            if conduit.source.kind == "device" and conduit.source.id:
                bucket["direct"].add(conduit.source.id)
                direct.add(conduit.source.id)
        elif conduit.evidence == "inherited":
            if conduit.source.kind == "device" and conduit.source.id:
                bucket["inherited"].add(conduit.source.id)
                through_hub.add(conduit.source.id)

    exposures = [
        VendorExposure(
            vendor=label,
            destination_ids=_sorted(data["destinations"]),
            devices_direct=_sorted(data["direct"]),
            devices_inherited=_sorted(data["inherited"]),
            queries=data["queries"],
            blocked_queries=data["blocked"],
            evidence=_sorted(data["evidence"]),
        )
        for label, data in vendors.items()
    ]
    exposures.sort(key=lambda e: (not e.is_observed, -e.queries, e.vendor))

    return Exposure(
        devices_total=len(scan.devices),
        devices_direct=_sorted(direct),
        # A device already exposed first-hand is not also reported second-hand.
        devices_inherited=_sorted(through_hub - direct),
        vendors=tuple(exposures),
        unknown_hosts=_sorted(unknown_hosts),
    )


def _sorted(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(values))
