"""Config entry diagnostics.

Diagnostics get pasted into public issue trackers, and this report is a map of
somebody's house. Addresses and MACs are redacted by default: the parts that
help debugging are the classifications, the counts and the checks, and none of
those need to name a device's address to be useful.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ADGUARD_PASSWORD, CONF_ADGUARD_URL, CONF_ADGUARD_USERNAME, DOMAIN
from .coordinator import TalosCoordinator

REDACT_CONFIG = {CONF_ADGUARD_PASSWORD, CONF_ADGUARD_USERNAME, CONF_ADGUARD_URL}
REDACT_ASSETS = {"ip", "mac"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: TalosCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None or coordinator.data is None:
        return {"error": "nessuna scansione completata"}

    data = coordinator.data
    scan = data.scan.to_dict()
    scan["devices"] = [async_redact_data(device, REDACT_ASSETS) for device in scan["devices"]]
    # An unknown_host source is a bare IP; redact it the same way.
    scan["conduits"] = [
        {**conduit, "source": async_redact_data(conduit["source"], {"id"})}
        if conduit["source"].get("kind") == "unknown_host"
        else conduit
        for conduit in scan["conduits"]
    ]
    scan["unverified"] = [
        async_redact_data(check, {"subjects"}) for check in scan["unverified"]
    ]

    return {
        "entry": {
            "options": dict(entry.options),
            "data": async_redact_data(dict(entry.data), REDACT_CONFIG),
        },
        "observed_available": data.observed_available,
        "observed_error": data.observed_error,
        "store": data.store_stats,
        "retention": data.retention,
        "derived": data.derived.to_dict(),
        "scan": scan,
    }
