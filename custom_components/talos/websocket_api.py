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
    CONF_MQTT_API_KEY,
    CONF_MQTT_API_SECRET,
    CONF_MQTT_API_URL,
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
from .core import DiagnosticRun
from .diagnostics_run import run_diagnostics
from .mqtt_source import (
    NO_CLIENT_IDS,
    collect_mqtt,
    collect_via_api,
    normalise_api_url,
    read_sys_blocking,
)
from .core import subnets, suggestions
from .core import DEFAULT_WINDOW

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
    websocket_api.async_register_command(hass, ws_set_mqtt)
    websocket_api.async_register_command(hass, ws_mqtt_test)
    websocket_api.async_register_command(hass, ws_diagnostics_run)
    websocket_api.async_register_command(hass, ws_diagnostics_last)
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
                CONF_MQTT_API_URL: coordinator.entry.data.get(CONF_MQTT_API_URL, ""),
                CONF_MQTT_API_KEY: coordinator.entry.data.get(CONF_MQTT_API_KEY, ""),
                "has_api_secret": bool(coordinator.entry.data.get(CONF_MQTT_API_SECRET)),
                # The route that answered, which is not always the one that
                # was configured: a preferred route that fails hands over.
                "route": (
                    data.scan.mqtt.route
                    if data and data.scan.mqtt and data.scan.mqtt.route
                    else "api"
                    if coordinator.entry.data.get(CONF_MQTT_API_URL)
                    else "account"
                    if coordinator.entry.data.get(CONF_MQTT_USERNAME)
                    or coordinator.entry.data.get(CONF_MQTT_HOST)
                    else "session"
                ),
                "fallback_from": (
                    data.scan.mqtt.fallback_from if data and data.scan.mqtt else None
                ),
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
                        # Coordinator, router or end device, when the mesh
                        # coordinator said so. Never a parent.
                        "mesh_role": device.mesh_role,
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
            "zigbee": data.scan.zigbee.to_dict() if data.scan.zigbee else None,
            # The client list itself, so the panel can say which ones it could
            # not account for instead of only how many.
            "mqtt": data.scan.mqtt.to_dict() if data.scan.mqtt else None,
            "observed_available": data.observed_available,
            "observed_error": data.observed_error,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/mqtt/set",
        vol.Optional(CONF_MQTT_HOST, default=""): str,
        vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): vol.Coerce(int),
        vol.Optional(CONF_MQTT_USERNAME, default=""): str,
        # Empty means "leave the stored one alone". Without that rule, saving
        # any other field on this form would silently wipe the password.
        vol.Optional(CONF_MQTT_PASSWORD, default=""): str,
        vol.Optional(CONF_MQTT_TLS, default=False): bool,
        vol.Optional(CONF_MQTT_API_URL, default=""): str,
        vol.Optional(CONF_MQTT_API_KEY, default=""): str,
        vol.Optional(CONF_MQTT_API_SECRET, default=""): str,
        vol.Optional("clear", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_set_mqtt(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Write the read-only broker account from the panel.

    Admin only, over the same authenticated socket the config flow itself
    uses. The password goes one way: it is written here and never sent back,
    and the panel is told only whether one is stored.
    """
    coordinator = _coordinator(hass)
    if coordinator is None:
        _not_ready(connection, msg["id"])
        return

    entry = coordinator.entry
    if msg["clear"]:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_MQTT_HOST: "",
                CONF_MQTT_USERNAME: "",
                CONF_MQTT_PASSWORD: "",
                CONF_MQTT_TLS: False,
                CONF_MQTT_API_URL: "",
                CONF_MQTT_API_KEY: "",
                CONF_MQTT_API_SECRET: "",
            },
        )
        connection.send_result(msg["id"], {"ok": True, "cleared": True})
        return

    password = msg[CONF_MQTT_PASSWORD] or entry.data.get(CONF_MQTT_PASSWORD, "")
    secret = msg[CONF_MQTT_API_SECRET] or entry.data.get(CONF_MQTT_API_SECRET, "")
    api_url = normalise_api_url(msg[CONF_MQTT_API_URL])
    updated = {
        CONF_MQTT_HOST: msg[CONF_MQTT_HOST].strip(),
        CONF_MQTT_PORT: int(msg[CONF_MQTT_PORT] or DEFAULT_MQTT_PORT),
        CONF_MQTT_USERNAME: msg[CONF_MQTT_USERNAME].strip(),
        CONF_MQTT_PASSWORD: password,
        CONF_MQTT_TLS: bool(msg[CONF_MQTT_TLS]),
        CONF_MQTT_API_URL: api_url,
        CONF_MQTT_API_KEY: msg[CONF_MQTT_API_KEY].strip(),
        CONF_MQTT_API_SECRET: secret,
    }

    # Every route that was filled in is tried, and the form is stored either
    # way. Refusing to save on a failed test threw away what the user had just
    # typed, so a key that needed a permission fixed on the broker could not
    # be kept while they went and fixed it. A route that does not work is a
    # configuration with a problem, not an invalid form, and it is reported as
    # one: both results come back, so filling in both says something about
    # both instead of only about the preferred one.
    tried: list[dict[str, Any]] = []

    if api_url:
        facts = await collect_via_api(
            hass,
            coordinator.data.scan,
            {
                "url": api_url,
                "key": updated[CONF_MQTT_API_KEY],
                "secret": secret,
                "verify_ssl": bool(entry.data.get(CONF_VERIFY_SSL, True)),
            },
        )
        tried.append(
            {
                "route": "api",
                "ok": facts.available,
                "error": facts.error,
                "clients": len(facts.clients),
                "unmatched": len(facts.unmatched),
            }
        )

    host = updated[CONF_MQTT_HOST] or _entry_broker(coordinator)
    if host and (updated[CONF_MQTT_USERNAME] or updated[CONF_MQTT_HOST]):
        found, error = await hass.async_add_executor_job(
            read_sys_blocking,
            host,
            updated[CONF_MQTT_PORT],
            updated[CONF_MQTT_USERNAME],
            password,
            updated[CONF_MQTT_TLS],
            1.5,
        )
        # Reached but keeping $SYS to itself is a working account with a
        # limit, and stays distinct from a broker that refused the connection.
        reachable = not error or error == NO_CLIENT_IDS
        tried.append(
            {
                "route": "account",
                "ok": reachable,
                "error": None if reachable else error,
                "clients": len(found),
                "unmatched": 0,
                "sys_readable": bool(found),
            }
        )

    hass.config_entries.async_update_entry(entry, data={**entry.data, **updated})
    working = next((item for item in tried if item["ok"]), None)
    connection.send_result(
        msg["id"],
        {
            # Saved either way; `working` says whether anything answered.
            "ok": True,
            "saved": True,
            "url": api_url,
            "tried": tried,
            "route": (working or {}).get("route", "session"),
            "clients": (working or {}).get("clients", 0),
            "unmatched": (working or {}).get("unmatched", 0),
            "sys_readable": bool(working) and (working.get("clients", 0) > 0),
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/diagnostics/run",
        vol.Optional("window", default=DEFAULT_WINDOW): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_diagnostics_run(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Start one diagnostic run and answer when it is done.

    User-started and one-shot by design. Two runs at once would measure each
    other, so a second request while one is in flight is refused rather than
    queued: the caller gets the one already running when it finishes.
    """
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        _not_ready(connection, msg["id"])
        return
    if coordinator.diagnostics_running:
        connection.send_error(msg["id"], "busy", "a diagnostic run is already in progress")
        return

    coordinator.diagnostics_running = True
    try:
        run = await run_diagnostics(hass, coordinator.data.scan, msg["window"])
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Talos: diagnostic run failed")
        connection.send_error(msg["id"], "failed", f"the diagnostic run failed: {err}")
        return
    finally:
        coordinator.diagnostics_running = False

    coordinator.last_diagnostics = run
    connection.send_result(msg["id"], _diagnostics_payload(coordinator, run))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/diagnostics/last"})
@callback
def ws_diagnostics_last(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = _coordinator(hass)
    if coordinator is None:
        _not_ready(connection, msg["id"])
        return
    run = coordinator.last_diagnostics
    connection.send_result(
        msg["id"],
        {
            "running": coordinator.diagnostics_running,
            "run": _diagnostics_payload(coordinator, run) if run else None,
        },
    )


def _diagnostics_payload(coordinator: TalosCoordinator, run: DiagnosticRun) -> dict[str, Any]:
    """The run plus the names the panel needs, since ids mean nothing on
    screen and re-deriving titles client side would duplicate the mapping."""
    scan = coordinator.data.scan if coordinator.data else None
    titles = (
        {integration.id: integration.title for integration in scan.integrations} if scan else {}
    )
    domains = (
        {integration.id: integration.domain for integration in scan.integrations} if scan else {}
    )
    return {
        **run.to_dict(),
        "labels": {"titles": titles, "domains": domains},
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/mqtt/test"})
@websocket_api.async_response
async def ws_mqtt_test(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Run every configured MQTT route now and hand back each outcome, verbatim.

    For the case where the panel says a route did not answer and the reason
    has to be read rather than guessed: the same code the scan runs, on
    demand, with nothing hidden.
    """
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        _not_ready(connection, msg["id"])
        return
    scan = coordinator.data.scan
    api = coordinator._mqtt_api()  # noqa: SLF001
    credentials = coordinator._mqtt_credentials(scan)  # noqa: SLF001
    facts = await collect_mqtt(hass, scan, credentials, api=api)
    connection.send_result(
        msg["id"],
        {
            **facts.to_dict(),
            "api_url": (api or {}).get("url"),
            "broker": (credentials or {}).get("host"),
        },
    )


def _entry_broker(coordinator: TalosCoordinator) -> str:
    """The broker the MQTT config entry names, when the form gives no address."""
    data = coordinator.data
    if data is None:
        return ""
    for conduit in data.scan.conduits:
        integration = data.scan.integration(conduit.source.id)
        if conduit.evidence != "declared" or integration is None or integration.domain != "mqtt":
            continue
        destination = data.scan.destination(conduit.destination_id)
        if destination is not None:
            return destination.fqdn
    return ""


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

    Options only. Credentials live in the config entry and have their own
    command, so a mistake here can never touch them.
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
