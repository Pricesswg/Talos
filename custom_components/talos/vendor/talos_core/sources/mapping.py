"""Home Assistant registry payloads -> a declared-only `Scan`.

Pure functions over plain dicts. No network, no clock, no `homeassistant.*`:
give it recorded payloads and it gives back a scan, which is the only way this
layer stays testable across HA releases.

Two rules govern everything below.

**Never invent.** A device registry has no IP field, so `ip` stays None here
and the join with the observed side happens later, on the MAC. A manifest that
could not be read leaves `iot_class` at `unknown` and adds an entry to the
unverified list, rather than defaulting to something that reads reassuring.

**Skip what is switched off.** Disabled devices and disabled entities are
excluded: they already do not work, so counting them among the things that
would stop working offline would inflate the number in the wrong direction.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..const import SCHEMA_VERSION
from ..model import Correlation, Device, Integration, Scan, UnverifiedCheck

# A device registry does not say how a device is attached. The domain is the
# best hint available; anything not listed stays `unknown`, which is honest and
# stays visible rather than being folded into a plausible default.
DOMAIN_TRANSPORT_HINTS: dict[str, str] = {
    "zha": "zigbee",
    "deconz": "zigbee",
    "zwave_js": "zwave",
    "matter": "matter",
    "thread": "thread",
    "esphome": "wifi",
    "shelly": "wifi",
    "tasmota": "wifi",
    "tplink": "wifi",
    "hue": "ethernet",
    "reolink": "wifi",
    "onvif": "wifi",
    "bluetooth": "ble",
    "bthome": "ble",
    "sonos": "wifi",
    "cast": "wifi",
}

# Connection types in a device registry entry that pin the transport down
# better than the domain does.
CONNECTION_TRANSPORT: dict[str, str] = {
    "zigbee": "zigbee",
    "zwave": "zwave",
    "bluetooth": "ble",
    "matter": "matter",
}


class RegistryPayload:
    """Everything a collector managed to read, plus what it could not."""

    __slots__ = ("config_entries", "devices", "entities", "areas", "manifests", "notes")

    def __init__(
        self,
        *,
        config_entries: Iterable[dict[str, Any]] = (),
        devices: Iterable[dict[str, Any]] = (),
        entities: Iterable[dict[str, Any]] = (),
        areas: Iterable[dict[str, Any]] = (),
        manifests: Iterable[dict[str, Any]] = (),
        notes: Iterable[UnverifiedCheck] = (),
    ) -> None:
        self.config_entries = list(config_entries)
        self.devices = list(devices)
        self.entities = list(entities)
        self.areas = list(areas)
        self.manifests = list(manifests)
        self.notes = list(notes)


def build_scan(
    payload: RegistryPayload,
    *,
    generated_at: str,
    collector: str = "websocket",
    ha_version: str | None = None,
) -> Scan:
    """Normalise registry payloads into a scan. Declared evidence only."""
    areas = {a["area_id"]: a.get("name") for a in payload.areas if a.get("area_id")}
    manifests = {m["domain"]: m for m in payload.manifests if m.get("domain")}

    integrations, missing_manifests = _build_integrations(payload.config_entries, manifests)
    known_entries = {i.id for i in integrations}

    entry_domains = {i.id: i.domain for i in integrations}
    devices = _build_devices(payload.devices, known_entries, entry_domains, areas)
    _count_entities(payload.entities, integrations, devices)

    unverified = list(payload.notes)
    if missing_manifests:
        unverified.append(
            UnverifiedCheck(
                id="unv.manifests_unavailable",
                title="iot_class of some integrations",
                reason="missing_data",
                detail=(
                    "Manifest unreadable for: "
                    + ", ".join(sorted(missing_manifests))
                    + ". These integrations stay 'unknown' and are counted neither"
                    " as local nor as cloud."
                ),
            )
        )

    orphan_entities = sum(
        1
        for entity in payload.entities
        if not entity.get("disabled_by")
        and not entity.get("config_entry_id")
        and not entity.get("device_id")
    )
    if orphan_entities:
        unverified.append(
            UnverifiedCheck(
                id="unv.entities_outside_registry",
                title="Entities that map to no config entry",
                reason="missing_data",
                detail=(
                    f"{orphan_entities} entities with neither a config entry nor a"
                    " device, typically defined in YAML. They are left out of the"
                    " autonomy count."
                ),
            )
        )

    return Scan(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at,
        collector=collector,
        ha_version=ha_version,
        integrations=integrations,
        devices=devices,
        destinations=[],
        # A declared-only scan names no destinations: the manifest says an
        # integration is cloud-bound, never which host it reaches. Those edges
        # arrive with the observed side and the domain classification.
        conduits=[],
        correlation=_correlation(devices),
        unverified=unverified,
    )


def _build_integrations(
    config_entries: Iterable[dict[str, Any]],
    manifests: dict[str, dict[str, Any]],
) -> tuple[list[Integration], set[str]]:
    integrations: list[Integration] = []
    missing: set[str] = set()

    for entry in config_entries:
        entry_id, domain = entry.get("entry_id"), entry.get("domain")
        if not entry_id or not domain:
            continue
        if entry.get("disabled_by"):
            continue

        manifest = manifests.get(domain)
        if manifest is None:
            missing.add(domain)

        integrations.append(
            Integration(
                id=entry_id,
                domain=domain,
                title=entry.get("title") or domain,
                iot_class=(manifest or {}).get("iot_class") or "unknown",
                # Absent a manifest we cannot claim it is built in, and
                # claiming it is would understate the finding.
                is_built_in=bool((manifest or {}).get("is_built_in", False)),
                state=entry.get("state") or "loaded",
                dependencies=list((manifest or {}).get("dependencies") or []),
            )
        )

    return integrations, missing


def _build_devices(
    raw_devices: Iterable[dict[str, Any]],
    known_entries: set[str],
    entry_domains: dict[str, str],
    areas: dict[str, Any],
) -> list[Device]:
    kept: list[Device] = []
    attributed: dict[str, str] = {}

    for raw in raw_devices:
        device_id = raw.get("id")
        if not device_id or raw.get("disabled_by"):
            continue
        entry_id = _primary_entry(raw, known_entries)
        if entry_id is None:
            # No config entry we kept: nothing to attribute it to.
            continue
        attributed[device_id] = entry_id

    for raw in raw_devices:
        device_id = raw.get("id")
        if device_id not in attributed:
            continue

        via = raw.get("via_device_id")
        kept.append(
            Device(
                id=device_id,
                integration_id=attributed[device_id],
                name=raw.get("name_by_user") or raw.get("name") or device_id,
                transport=_transport(raw, entry_domains.get(attributed[device_id])),
                manufacturer=raw.get("manufacturer"),
                model=raw.get("model"),
                area=areas.get(raw.get("area_id")),
                mac=_mac(raw),
                # The device registry carries no address. The IP arrives from
                # the DHCP leases on the observed side, joined on the MAC.
                ip=None,
                zone="unknown",
                # Drop a parent we did not keep, rather than emit a dangling
                # reference the validator would rightly reject.
                via_device_id=via if via in attributed else None,
                entity_count=0,
            )
        )

    return kept


def _primary_entry(raw: dict[str, Any], known_entries: set[str]) -> str | None:
    """A device can belong to several config entries; pick the one HA calls
    primary, else the first we recognise."""
    primary = raw.get("primary_config_entry")
    if primary in known_entries:
        return primary
    for entry_id in raw.get("config_entries") or ():
        if entry_id in known_entries:
            return entry_id
    return None


def _transport(raw: dict[str, Any], domain: str | None) -> str:
    for connection in raw.get("connections") or ():
        if not isinstance(connection, (list, tuple)) or not connection:
            continue
        hinted = CONNECTION_TRANSPORT.get(str(connection[0]))
        if hinted:
            return hinted
    # The domain hint describes how the integration reaches its own hub, not
    # how the hub reaches its children: a Hue bridge is on ethernet, the lamps
    # behind it are not. Anything sitting under a via_device stays unknown
    # rather than inheriting a transport it demonstrably does not use.
    if raw.get("via_device_id"):
        return "unknown"
    if domain:
        return DOMAIN_TRANSPORT_HINTS.get(domain, "unknown")
    return "unknown"


def _mac(raw: dict[str, Any]) -> str | None:
    for connection in raw.get("connections") or ():
        if (
            isinstance(connection, (list, tuple))
            and len(connection) >= 2
            and str(connection[0]) == "mac"
        ):
            return str(connection[1]).lower()
    return None


def _count_entities(
    raw_entities: Iterable[dict[str, Any]],
    integrations: list[Integration],
    devices: list[Device],
) -> None:
    """Count active entities per device and per config entry.

    An integration is credited with every entity that names it *or* that
    belongs to one of its devices. The union keeps the per-integration total
    at or above the sum of its devices, which is the invariant `TALOS-C010`
    enforces on the way out.
    """
    device_entry = {d.id: d.integration_id for d in devices}
    per_device: dict[str, int] = {}
    per_integration: dict[str, int] = {}

    for entity in raw_entities:
        if entity.get("disabled_by"):
            continue
        device_id = entity.get("device_id")
        entry_id = entity.get("config_entry_id")

        if device_id in device_entry:
            per_device[device_id] = per_device.get(device_id, 0) + 1
            entry_id = entry_id or device_entry[device_id]
        elif device_id:
            # Its device was skipped (disabled, or attributed to nothing).
            continue

        if entry_id:
            per_integration[entry_id] = per_integration.get(entry_id, 0) + 1

    for device in devices:
        device.entity_count = per_device.get(device.id, 0)
    for integration in integrations:
        integration.entity_count = per_integration.get(integration.id, 0)


def _correlation(devices: list[Device]) -> Correlation:
    joinable = sum(1 for d in devices if d.mac or d.ip)
    return Correlation(
        devices_total=len(devices),
        devices_correlated=joinable,
        method="mac",
    )
