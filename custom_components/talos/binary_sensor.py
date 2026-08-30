"""Blind-spot indicator.

On when the zero check found a host that bypasses the resolver, and also on
when the check could not run at all. Those are different situations with the
same consequence: there is part of the network Talos cannot see, and a report
that reads clean would be lying about it.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TalosCoordinator
from .entity import TalosEntity

BLIND_SPOT_CHECKS = {
    "unv.resolver_bypassed",
    "unv.dhcp_leases_unavailable",
    "unv.observed_source_unavailable",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TalosCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TalosBlindSpot(coordinator)])


class TalosBlindSpot(TalosEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: TalosCoordinator) -> None:
        super().__init__(coordinator, "blind_spot")

    @property
    def is_on(self) -> bool | None:
        data = self.talos
        if data is None:
            return None
        return bool(self._active_checks(data))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.talos
        if data is None:
            return None
        return {
            "reasons": [check.title for check in self._active_checks(data)],
            "observed_available": data.observed_available,
        }

    @staticmethod
    def _active_checks(data: Any) -> list[Any]:
        return [check for check in data.scan.unverified if check.id in BLIND_SPOT_CHECKS]
