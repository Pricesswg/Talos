"""Talos: data provenance and offline autonomy for Home Assistant.

Registers a sidebar panel rather than a Lovelace card, and an admin-only one.
A card can be dropped onto a dashboard that ends up on the kitchen tablet or
a guest account; this report lists addresses, MACs and the topology of the
house. Not being embeddable is a feature here.
"""

from __future__ import annotations

import logging

from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from . import services, websocket_api
from .const import (
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_SCRIPT,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_URL,
)
from .coordinator import TalosCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = TalosCoordinator(hass, entry)
    await coordinator.async_prepare()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    websocket_api.async_register(hass)
    services.async_register(hass)
    await _async_register_panel(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: TalosCoordinator | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator is not None:
        await coordinator.async_shutdown_store()
    if not hass.data.get(DOMAIN):
        frontend.async_remove_panel(hass, PANEL_URL)
        services.async_unregister(hass)
    return unloaded


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload only for the changes that actually need one.

    A reload tears down the store, the coordinator and every entity, and on a
    large install that is seconds of everything going unavailable. The scan
    interval, the retention policy and the zone ranges are read at setup, so
    they need it. The broker account is read fresh on every scan, so it does
    not, and reloading for it would throw away the state of the panel the user
    is looking at while they configure it.
    """
    coordinator: TalosCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        await hass.config_entries.async_reload(entry.entry_id)
        return

    if coordinator.needs_reload(entry):
        await hass.config_entries.async_reload(entry.entry_id)
        return

    # Nothing structural moved. Pick up the new value on the next scan, and
    # run one now so the change is visible immediately.
    coordinator.remember_setup(entry)
    await coordinator.async_refresh()


async def _async_register_panel(hass: HomeAssistant) -> None:
    if PANEL_URL in hass.data.get("frontend_panels", {}):
        return

    integration = await async_get_integration(hass, DOMAIN)
    static_dir = str(integration.file_path / "www")
    await _async_register_static(hass, static_dir)

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_COMPONENT,
        module_url=f"{STATIC_URL}/{PANEL_SCRIPT}?v={integration.version}",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        # The report is a map of the house. Admins only.
        require_admin=True,
        config={},
    )


async def _async_register_static(hass: HomeAssistant, directory: str) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, directory, True)]
        )
    except ImportError:  # pragma: no cover - Home Assistant < 2024.7
        hass.http.register_static_path(STATIC_URL, directory, True)
