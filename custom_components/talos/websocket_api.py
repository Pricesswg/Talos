"""WebSocket commands for the panel.

Every command is admin only. The report is a reconnaissance map of the house
(addresses, MACs, topology, blind spots) and it must not be reachable by a
non-admin session any more than the panel itself is.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_ADGUARD_PASSWORD,
    CONF_ADGUARD_URL,
    CONF_ADGUARD_USERNAME,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_TLS,
    CONF_MQTT_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_MQTT_PORT,
    DOMAIN,
    OPTION_BOUNDS,
    TEXT_OPTIONS,
)
from .coordinator import TalosCoordinator
from .core import subnets, suggestions

_REGISTERED = f"{DOMAIN}_ws_registered"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register once per instance, however many entries come and go."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True
    websocket_api.async_register_command(hass, ws_status)
    websocket_api.async_register_command(hass, ws_scan)
    websocket_api.async_register_command(hass, ws_derived)
    websocket_api.async_register_command(hass, ws_suggest)
    websocket_api.async_register_command(hass, ws_refresh)
    websocket_api.async_register_command(hass, ws_set_options)


def _coordinator(hass: HomeAssistant) -> TalosCoordinator | None:
    entries = hass.data.get(DOMAIN) or {}
    for value in entries.values():
        if isinstance(value, TalosCoordinator):
            return value
    return None


def _not_ready(connection: websocket_api.ActiveConnection, msg_id: int) -> None:
    connection.send_error(msg_id, "not_ready", "Talos has not completed a scan yet")


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/status"})
@callback
def ws_status(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = _coordinator(hass)
    if coordinator is None:
        _not_ready(connection, msg["id"])
        return
    data = coordinator.data
    connection.send_result(
        msg["id"],
        {
            "last_update_success": coordinator.last_update_success,
            # The timestamp is the last scan that worked. Without this, a
            # coordinator that has been failing for a day reads as idle.
            "last_error": (
                None
                if coordinator.last_update_success
                else str(coordinator.last_exception or "the scan failed")
            ),
            "generated_at": data.scan.generated_at if data else None,
            "ha_version": data.scan.ha_version if data else None,
            "observed_available": data.observed_available if data else False,
            "observed_error": data.observed_error if data else None,
            "store": data.store_stats if data else {},
            "retention": data.retention if data else {},
            "interval_minutes": int(
                coordinator.update_interval.total_seconds() // 60
            )
            if coordinator.update_interval
            else None,
            "options": dict(coordinator.entry.options),
            "bounds": {key: list(value) for key, value in OPTION_BOUNDS.items()},
            "text_options": list(TEXT_OPTIONS),
            # The endpoint is shown so the settings screen can state what it is
            # talking to. The password never leaves the config entry: only
            # whether one is set.
            "connection": {
                CONF_ADGUARD_URL: coordinator.entry.data.get(CONF_ADGUARD_URL, ""),
                CONF_ADGUARD_USERNAME: coordinator.entry.data.get(CONF_ADGUARD_USERNAME, ""),
                CONF_VERIFY_SSL: bool(coordinator.entry.data.get(CONF_VERIFY_SSL, True)),
                "has_password": bool(coordinator.entry.data.get(CONF_ADGUARD_PASSWORD)),
            },
            # The broker account, same rule: what it is, never the password.
            "mqtt": {
                CONF_MQTT_HOST: coordinator.entry.data.get(CONF_MQTT_HOST, ""),
                CONF_MQTT_PORT: coordinator.entry.data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
                CONF_MQTT_USERNAME: coordinator.entry.data.get(CONF_MQTT_USERNAME, ""),
                CONF_MQTT_TLS: bool(coordinator.entry.data.get(CONF_MQTT_TLS)),
                "has_password": bool(coordinator.entry.data.get(CONF_MQTT_PASSWORD)),
                # What the last scan actually got out of the broker.
                "available": bool(data.scan.mqtt.available) if data and data.scan.mqtt else False,
                "error": data.scan.mqtt.error if data and data.scan.mqtt else None,
                "clients": len(data.scan.mqtt.clients) if data and data.scan.mqtt else 0,
                "unmatched": (
                    len(data.scan.mqtt.unmatched) if data and data.scan.mqtt else 0
                ),
            },
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/scan"})
@callback
def ws_scan(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        _not_ready(connection, msg["id"])
        return
    connection.send_result(msg["id"], coordinator.data.scan.to_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/derived"})
@callback
def ws_derived(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        _not_ready(connection, msg["id"])
        return
    data = coordinator.data
    # Where each integration says it connects. Read from the config entry, so
    # it answers "which broker" without probing anything.
    endpoints: dict[str, str] = {}
    for conduit in data.scan.conduits:
        if conduit.evidence != "declared" or conduit.source.kind != "integration":
            continue
        destination = data.scan.destination(conduit.destination_id)
        if destination is None or conduit.source.id in endpoints:
            continue
        endpoints[conduit.source.id] = (
            f"{destination.fqdn}:{conduit.port}" if conduit.port else destination.fqdn
        )

    connection.send_result(
        msg["id"],
        {
            **data.derived.to_dict(),
            # The panel needs names, not identifiers, and re-deriving them
            # client side would duplicate the mapping rules.
            "labels": {
                "devices": {
                    device.id: {
                        "name": device.name,
                        "area": device.area,
                        "transport": device.transport,
                        "manufacturer": device.manufacturer,
                        "model": device.model,
                        "ip": device.ip,
                        "integration_id": device.integration_id,
                        # The system that produced it, when that is not the
                        # integration that registered it.
                        "origin": device.origin,
                        # The map draws the hub hierarchy and the weight of
                        # each branch from these two.
                        "via_device_id": device.via_device_id,
                        "entity_count": device.entity_count,
                    }
                    for device in data.scan.devices
                },
                "integrations": {
                    integration.id: {
                        "title": integration.title,
                        "domain": integration.domain,
                        "iot_class": integration.iot_class,
                        # Bus or media service, which is not a transport.
                        "role": integration.role,
                        # Not loaded means its entities are unavailable now.
                        "state": integration.state,
                        "endpoint": endpoints.get(integration.id),
                        "is_built_in": integration.is_built_in,
                        "entity_count": integration.entity_count,
                    }
                    for integration in data.scan.integrations
                },
                "destinations": {
                    destination.id: {
                        "fqdn": destination.fqdn,
                        "kind": destination.kind,
                        "vendor": destination.vendor,
                    }
                    for destination in data.scan.destinations
                },
            },
            "conduits": [conduit.to_dict() for conduit in data.scan.conduits],
            "observed_available": data.observed_available,
            "observed_error": data.observed_error,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/suggest"})
@callback
def ws_suggest(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Values for the options the user left empty, derived from the scan.

    Proposed, never applied: a subnet Talos saw traffic on is a good guess for
    the trusted LAN and a bad one for the guest network, and only the person
    who built the network can tell them apart.
    """
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        _not_ready(connection, msg["id"])
        return
    scan = coordinator.data.scan
    connection.send_result(
        msg["id"],
        {
            "suggestions": [
                item.to_dict() for item in suggestions(scan, dict(coordinator.entry.options))
            ],
            "subnets": [
                {"network": network, "hosts": hosts} for network, hosts in subnets(scan)
            ],
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/options/set",
        vol.Required("options"): dict,
    }
)
@websocket_api.async_response
async def ws_set_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Update the editable options from the panel.

    Only the options are writable here. The AdGuard endpoint and its
    credentials stay in the config entry and are changed through the
    reconfigure flow, so no password ever travels over this socket.
    """
    coordinator = _coordinator(hass)
    if coordinator is None:
        _not_ready(connection, msg["id"])
        return

    merged = dict(coordinator.entry.options)
    for key, value in msg["options"].items():
        if key in OPTION_BOUNDS:
            try:
                number = int(value)
            except (TypeError, ValueError):
                connection.send_error(msg["id"], "invalid_format", f"{key} must be a whole number")
                return
            minimum, maximum = OPTION_BOUNDS[key]
            if not minimum <= number <= maximum:
                connection.send_error(
                    msg["id"], "invalid_format", f"{key} must be between {minimum} and {maximum}"
                )
                return
            merged[key] = number
        elif key in TEXT_OPTIONS:
            merged[key] = str(value or "").strip()
        else:
            connection.send_error(msg["id"], "invalid_format", f"unknown option: {key}")
            return

    # Updating the entry fires the update listener, which reloads Talos with
    # the new interval, retention policy and zone ranges.
    hass.config_entries.async_update_entry(coordinator.entry, options=merged)
    connection.send_result(msg["id"], {"options": merged})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/refresh"})
@websocket_api.async_response
async def ws_refresh(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = _coordinator(hass)
    if coordinator is None:
        _not_ready(connection, msg["id"])
        return
    # Not async_request_refresh: that one is debounced, so a user pressing
    # the button twice would be told nothing happened. This runs now and
    # answers with the outcome, which is what the button needs to show.
    await coordinator.async_refresh()
    data = coordinator.data
    connection.send_result(
        msg["id"],
        {
            "ok": coordinator.last_update_success,
            "generated_at": data.scan.generated_at if data else None,
            "error": (
                None
                if coordinator.last_update_success
                else str(coordinator.last_exception or "the scan failed")
            ),
            "observed_available": data.observed_available if data else False,
            "observed_error": data.observed_error if data else None,
        },
    )
