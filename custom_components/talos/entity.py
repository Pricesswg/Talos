"""Shared entity base.

Only a handful of summary entities exist, all under one service device. No
entity per asset: a house with three hundred devices would otherwise get
three hundred new entities in the registry, which is a poor trade for numbers
the panel already shows.
"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TalosCoordinator, TalosData


class TalosEntity(CoordinatorEntity[TalosCoordinator]):
    """Base for the summary entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TalosCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Talos",
            manufacturer="Talos",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def talos(self) -> TalosData | None:
        return self.coordinator.data
