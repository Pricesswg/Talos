"""Declarative collection from inside Home Assistant.

Same normalised output as the WebSocket source, and for the same reason: the
CLI and the panel must never start disagreeing about the same house. Only the
first step differs: the registries are read in process, so there is no token,
no socket, and the data is always fresh.

The conversion below is a pure function over duck-typed registry objects, so
it is unit-testable with fakes and does not need Home Assistant to import.
Every `homeassistant.*` import is deferred into the method that needs it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .core import RegistryPayload, Scan, build_scan


def _enum_value(value: Any) -> str | None:
    """Registry enums stringify as `ConfigEntryState.LOADED`; keep the value."""
    if value is None:
        return None
    return str(getattr(value, "value", value))


def device_to_dict(device: Any) -> dict[str, Any]:
    return {
        "id": device.id,
        "name": getattr(device, "name", None),
        "name_by_user": getattr(device, "name_by_user", None),
        "manufacturer": getattr(device, "manufacturer", None),
        "model": getattr(device, "model", None),
        "area_id": getattr(device, "area_id", None),
        "config_entries": sorted(getattr(device, "config_entries", ()) or ()),
        "primary_config_entry": getattr(device, "primary_config_entry", None),
        "connections": [list(pair) for pair in (getattr(device, "connections", ()) or ())],
        # The only evidence that a device behind MQTT is actually Zigbee.
        "identifiers": [list(pair) for pair in (getattr(device, "identifiers", ()) or ())],
        "via_device_id": getattr(device, "via_device_id", None),
        "disabled_by": _enum_value(getattr(device, "disabled_by", None)),
    }


def entity_to_dict(entity: Any) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "device_id": getattr(entity, "device_id", None),
        "config_entry_id": getattr(entity, "config_entry_id", None),
        "platform": getattr(entity, "platform", None),
        "disabled_by": _enum_value(getattr(entity, "disabled_by", None)),
    }


def area_to_dict(area: Any) -> dict[str, Any]:
    # An AreaEntry exposes `id`; the normalised payload speaks `area_id`.
    return {"area_id": getattr(area, "id", None), "name": getattr(area, "name", None)}


# Keys that name where a config entry connects. Nothing else is read: a
# config entry also holds passwords and tokens, and none of them belong in a
# document meant to be exported and shared.
ENDPOINT_HOST_KEYS = ("broker", "host", "server", "hostname", "address", "url")
ENDPOINT_PORT_KEYS = ("port",)


def entry_endpoint(entry: Any) -> dict[str, Any] | None:
    """The address a config entry connects to, if it names one.

    This is the difference between saying "the MQTT integration" and saying
    which broker it actually talks to, which matters when there are two of
    them and one is stopped.
    """
    data = dict(getattr(entry, "data", {}) or {})
    host = next((str(data[key]) for key in ENDPOINT_HOST_KEYS if data.get(key)), None)
    if not host:
        return None
    port = next((data[key] for key in ENDPOINT_PORT_KEYS if data.get(key)), None)
    return {"host": host, "port": int(port) if isinstance(port, (int, str)) and str(port).isdigit() else None}


def config_entry_to_dict(entry: Any) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "domain": entry.domain,
        "title": getattr(entry, "title", None),
        "state": _enum_value(getattr(entry, "state", None)) or "loaded",
        "source": getattr(entry, "source", None),
        "disabled_by": _enum_value(getattr(entry, "disabled_by", None)),
        "endpoint": entry_endpoint(entry),
    }


def integration_to_dict(integration: Any) -> dict[str, Any] | None:
    """Read a loader Integration. Anything unreadable becomes None so that the
    domain lands in the unverified list instead of getting a default."""
    if integration is None or isinstance(integration, BaseException):
        return None
    manifest = getattr(integration, "manifest", None) or {}
    domain = getattr(integration, "domain", None) or manifest.get("domain")
    if not domain:
        return None
    return {
        "domain": domain,
        "name": manifest.get("name") or domain,
        "iot_class": manifest.get("iot_class"),
        "is_built_in": bool(getattr(integration, "is_built_in", manifest.get("is_built_in", False))),
        "dependencies": list(manifest.get("dependencies") or ()),
    }


def payload_from_registries(
    *,
    config_entries: Iterable[Any],
    devices: Iterable[Any],
    entities: Iterable[Any],
    areas: Iterable[Any],
    integrations: Iterable[Any],
) -> RegistryPayload:
    """Normalise in-process registry objects into the shared payload shape."""
    manifests = [
        manifest
        for manifest in (integration_to_dict(item) for item in integrations)
        if manifest is not None
    ]
    return RegistryPayload(
        config_entries=[config_entry_to_dict(entry) for entry in config_entries],
        devices=[device_to_dict(device) for device in devices],
        entities=[entity_to_dict(entity) for entity in entities],
        areas=[area_to_dict(area) for area in areas],
        manifests=manifests,
    )


class NativeSource:
    """Reads the declarative side through the in-process registries.

    Fulfils the same contract as `WebSocketSource`: a scan carrying
    `evidence: declared` and nothing else.
    """

    def __init__(self, hass: Any) -> None:
        self._hass = hass

    async def fetch(self) -> Scan:
        from homeassistant.const import __version__ as ha_version
        from homeassistant.helpers import area_registry, device_registry, entity_registry
        from homeassistant.loader import async_get_integrations

        devices = device_registry.async_get(self._hass).devices.values()
        entities = entity_registry.async_get(self._hass).entities.values()
        areas = area_registry.async_get(self._hass).areas.values()
        config_entries = self._hass.config_entries.async_entries()

        domains = {entry.domain for entry in config_entries}
        resolved = await async_get_integrations(self._hass, domains)

        payload = payload_from_registries(
            config_entries=config_entries,
            devices=list(devices),
            entities=list(entities),
            areas=list(areas),
            integrations=list(resolved.values()),
        )

        # Normalisation walks every device and entity; on a large install that
        # is real work and does not belong on the event loop.
        return await self._hass.async_add_executor_job(
            lambda: build_scan(
                payload,
                generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                collector="native",
                ha_version=ha_version,
            )
        )
