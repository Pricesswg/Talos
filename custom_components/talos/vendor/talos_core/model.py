"""The Talos data model.

The canonical unit is the **config entry**, not the device. A config entry
always has an integration, an iot_class and a built-in flag; devices are zero,
one or a hundred underneath it. Keying on the device would lose every cloud
dependency that has no device at all (mobile_app push, TTS, weather, the
version check Home Assistant makes about itself) which is exactly the
category most likely to be cloud-bound.

Loading assumes the document already passed `validate()`. The model does not
re-report schema problems: it raises on the first one it cannot survive, so
that a caller who skipped validation fails loudly instead of silently
building a half-populated scan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import LOCAL_IOT_CLASSES, NON_IP_TRANSPORTS, SCHEMA_VERSION
from .errors import Finding, TalosSchemaError


def _req(obj: dict[str, Any], key: str, path: str) -> Any:
    if key not in obj:
        raise TalosSchemaError([Finding("TALOS-S002", f"{path}.{key}", "required field is missing")])
    return obj[key]


@dataclass(slots=True)
class Integration:
    """A Home Assistant config entry. The unit everything else hangs from."""

    id: str
    domain: str
    title: str
    iot_class: str
    is_built_in: bool
    state: str = "loaded"
    dependencies: list[str] = field(default_factory=list)
    # Every entity of the config entry, including the ones that belong to no
    # device: notify targets, weather, TTS. Counting entities device by device
    # would miss exactly the most cloud-bound category there is.
    entity_count: int = 0

    @property
    def is_local(self) -> bool:
        """How HA talks to it. Says nothing about the device's own egress."""
        return self.iot_class in LOCAL_IOT_CLASSES

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> Integration:
        return cls(
            id=_req(raw, "id", path),
            domain=_req(raw, "domain", path),
            title=_req(raw, "title", path),
            iot_class=_req(raw, "iot_class", path),
            is_built_in=bool(_req(raw, "is_built_in", path)),
            state=raw.get("state") or "loaded",
            dependencies=list(raw.get("dependencies") or []),
            entity_count=int(raw.get("entity_count") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "title": self.title,
            "iot_class": self.iot_class,
            "is_built_in": self.is_built_in,
            "state": self.state,
            "dependencies": list(self.dependencies),
            "entity_count": self.entity_count,
        }


@dataclass(slots=True)
class Device:
    """A physical or logical device under a config entry. Optional by design."""

    id: str
    integration_id: str
    name: str
    transport: str = "unknown"
    manufacturer: str | None = None
    model: str | None = None
    area: str | None = None
    mac: str | None = None
    ip: str | None = None
    zone: str = "unknown"
    # The system that produced the device, when it is not the integration that
    # registered it. An MQTT entry can be fed by Zigbee2MQTT and a SwitchBot
    # bridge at once; the integration is the bus, this is the source on it.
    origin: str | None = None
    via_device_id: str | None = None
    entity_count: int = 0

    @property
    def can_have_direct_egress(self) -> bool:
        """Zigbee and Z-Wave carry no IP: whatever they reach, they reach
        through their hub. Their exposure is inherited, never direct."""
        return self.transport not in NON_IP_TRANSPORTS

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> Device:
        return cls(
            id=_req(raw, "id", path),
            integration_id=_req(raw, "integration_id", path),
            name=_req(raw, "name", path),
            transport=raw.get("transport") or "unknown",
            manufacturer=raw.get("manufacturer"),
            model=raw.get("model"),
            area=raw.get("area"),
            mac=raw.get("mac"),
            ip=raw.get("ip"),
            zone=raw.get("zone") or "unknown",
            origin=raw.get("origin"),
            via_device_id=raw.get("via_device_id"),
            entity_count=int(raw.get("entity_count") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "name": self.name,
            "transport": self.transport,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "area": self.area,
            "mac": self.mac,
            "ip": self.ip,
            "zone": self.zone,
            "origin": self.origin,
            "via_device_id": self.via_device_id,
            "entity_count": self.entity_count,
        }


@dataclass(slots=True)
class Destination:
    """Something outside the asset: a hostname, a broker, a service."""

    id: str
    fqdn: str
    kind: str = "unknown"
    vendor: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> Destination:
        return cls(
            id=_req(raw, "id", path),
            fqdn=_req(raw, "fqdn", path),
            kind=raw.get("kind") or "unknown",
            vendor=raw.get("vendor"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "fqdn": self.fqdn, "kind": self.kind, "vendor": self.vendor}


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Where a conduit starts. `unknown_host` holds a bare IP seen by the
    resolver that matches nothing in the registry, the zero check's output."""

    kind: str
    id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> SourceRef:
        if not isinstance(raw, dict):
            raise TalosSchemaError([Finding("TALOS-S001", path, "source must be an object")])
        return cls(kind=_req(raw, "kind", path), id=raw.get("id"))

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id}


@dataclass(slots=True)
class Conduit:
    """One edge: an asset reaching a destination, with the evidence for it.

    Observation fields are only populated when `evidence == "observed"`. An
    inherited conduit deliberately carries none of them: its counts live on
    the hub's own conduit, and copying them down here would present a
    second-hand fact with the weight of a first-hand one.
    """

    id: str
    source: SourceRef
    destination_id: str
    evidence: str
    protocol: str | None = None
    port: int | None = None
    encrypted: bool | str = "unknown"
    first_seen: str | None = None
    last_seen: str | None = None
    query_count: int | None = None
    filter_status: str | None = None
    inherited_from: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> Conduit:
        return cls(
            id=_req(raw, "id", path),
            source=SourceRef.from_dict(_req(raw, "source", path), f"{path}.source"),
            destination_id=_req(raw, "destination_id", path),
            evidence=_req(raw, "evidence", path),
            protocol=raw.get("protocol"),
            port=raw.get("port"),
            encrypted=raw.get("encrypted", "unknown"),
            first_seen=raw.get("first_seen"),
            last_seen=raw.get("last_seen"),
            query_count=raw.get("query_count"),
            filter_status=raw.get("filter_status"),
            inherited_from=raw.get("inherited_from"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "source": self.source.to_dict(),
            "destination_id": self.destination_id,
            "evidence": self.evidence,
            "protocol": self.protocol,
            "port": self.port,
            "encrypted": self.encrypted,
        }
        if self.evidence == "observed":
            out |= {
                "first_seen": self.first_seen,
                "last_seen": self.last_seen,
                "query_count": self.query_count,
                "filter_status": self.filter_status,
            }
        if self.inherited_from is not None:
            out["inherited_from"] = self.inherited_from
        return out


@dataclass(slots=True)
class Correlation:
    """How much of the declarative side could be joined to the observed side.

    Always reported, never hidden in diagnostics. A quadrant that looks empty
    because the join failed reads exactly like a quadrant that is empty
    because nothing is wrong, and only this number tells them apart.
    """

    devices_total: int = 0
    devices_correlated: int = 0
    method: str = "mac_ip"

    @property
    def ratio(self) -> float:
        return self.devices_correlated / self.devices_total if self.devices_total else 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> Correlation:
        return cls(
            devices_total=int(_req(raw, "devices_total", path)),
            devices_correlated=int(_req(raw, "devices_correlated", path)),
            method=raw.get("method") or "mac_ip",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "devices_total": self.devices_total,
            "devices_correlated": self.devices_correlated,
            "method": self.method,
        }


@dataclass(slots=True)
class UnverifiedCheck:
    """A check that could not run. Not a pass, not a failure, and never
    folded into either count."""

    id: str
    title: str
    reason: str
    detail: str = ""
    # What the check could not speak about: IPs, device ids, domains. Kept
    # structured so a posture check can act on them instead of parsing prose.
    subjects: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], path: str) -> UnverifiedCheck:
        return cls(
            id=_req(raw, "id", path),
            title=_req(raw, "title", path),
            reason=_req(raw, "reason", path),
            detail=raw.get("detail") or "",
            subjects=list(raw.get("subjects") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "reason": self.reason,
            "detail": self.detail,
            "subjects": list(self.subjects),
        }


@dataclass(slots=True)
class Scan:
    """A complete run: the declarative side, the observed side, and the gap."""

    generated_at: str
    collector: str
    schema_version: str = SCHEMA_VERSION
    ha_version: str | None = None
    integrations: list[Integration] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    destinations: list[Destination] = field(default_factory=list)
    conduits: list[Conduit] = field(default_factory=list)
    correlation: Correlation = field(default_factory=Correlation)
    unverified: list[UnverifiedCheck] = field(default_factory=list)

    # ── lookups ───────────────────────────────────────────────────────────

    def integration(self, integration_id: str) -> Integration | None:
        return next((i for i in self.integrations if i.id == integration_id), None)

    def device(self, device_id: str) -> Device | None:
        return next((d for d in self.devices if d.id == device_id), None)

    def destination(self, destination_id: str) -> Destination | None:
        return next((d for d in self.destinations if d.id == destination_id), None)

    def hub_chain(self, device_id: str) -> list[str]:
        """Ancestors of a device along via_device, nearest hub first.

        Stops on a cycle rather than looping: a malformed chain is the
        validator's problem to report, not this helper's to crash on.
        """
        chain: list[str] = []
        seen = {device_id}
        current = self.device(device_id)
        while current is not None and current.via_device_id:
            parent_id = current.via_device_id
            if parent_id in seen:
                break
            seen.add(parent_id)
            chain.append(parent_id)
            current = self.device(parent_id)
        return chain

    # ── serialisation ─────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Scan:
        if not isinstance(raw, dict):
            raise TalosSchemaError([Finding("TALOS-S001", "$", "document root must be an object")])
        return cls(
            schema_version=raw.get("schema_version") or SCHEMA_VERSION,
            generated_at=_req(raw, "generated_at", "$"),
            collector=_req(raw, "collector", "$"),
            ha_version=raw.get("ha_version"),
            integrations=[
                Integration.from_dict(r, f"$.integrations[{i}]")
                for i, r in enumerate(raw.get("integrations") or [])
            ],
            devices=[
                Device.from_dict(r, f"$.devices[{i}]")
                for i, r in enumerate(raw.get("devices") or [])
            ],
            destinations=[
                Destination.from_dict(r, f"$.destinations[{i}]")
                for i, r in enumerate(raw.get("destinations") or [])
            ],
            conduits=[
                Conduit.from_dict(r, f"$.conduits[{i}]")
                for i, r in enumerate(raw.get("conduits") or [])
            ],
            correlation=Correlation.from_dict(raw.get("correlation") or {}, "$.correlation"),
            unverified=[
                UnverifiedCheck.from_dict(r, f"$.unverified[{i}]")
                for i, r in enumerate(raw.get("unverified") or [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "collector": self.collector,
            "ha_version": self.ha_version,
            "integrations": [i.to_dict() for i in self.integrations],
            "devices": [d.to_dict() for d in self.devices],
            "destinations": [d.to_dict() for d in self.destinations],
            "conduits": [c.to_dict() for c in self.conduits],
            "correlation": self.correlation.to_dict(),
            "unverified": [u.to_dict() for u in self.unverified],
        }
