"""Summary sensors.

Two orthogonal numbers, never merged into one score, plus the count of checks
that could not run — which is the figure most products hide and the one an
"everything is fine" reading would otherwise conceal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import TalosCoordinator, TalosData
from .entity import TalosEntity


@dataclass(frozen=True, kw_only=True)
class TalosSensorDescription(SensorEntityDescription):
    value_fn: Callable[[TalosData], Any]
    attributes_fn: Callable[[TalosData], dict[str, Any]] | None = None


def _percent(part: int, whole: int) -> float | None:
    return round(part / whole * 100, 1) if whole else None


SENSORS: tuple[TalosSensorDescription, ...] = (
    TalosSensorDescription(
        key="local_with_egress",
        state_class=SensorStateClass.MEASUREMENT,
        # Local to Home Assistant, yet phoning home on their own. The one
        # number the whole tool exists to produce.
        value_fn=lambda data: len(data.derived.matrix.local_egress),
        attributes_fn=lambda data: {
            "devices": [
                data.scan.device(device_id).name if data.scan.device(device_id) else device_id
                for device_id in data.derived.matrix.local_egress
            ],
            "inherited_through_hub": len(data.derived.matrix.inherited),
        },
    ),
    TalosSensorDescription(
        key="findings_high",
        state_class=SensorStateClass.MEASUREMENT,
        # Severity counters, kept apart from the unverified count on purpose.
        value_fn=lambda data: data.derived.checks.counts["failed_high"],
        attributes_fn=lambda data: {
            **data.derived.checks.counts,
            "findings": [
                {
                    "id": result.id,
                    "title": result.title,
                    "severity": result.severity,
                    "subjects": len(result.subjects),
                }
                for result in data.derived.checks.failed
            ],
        },
    ),
    TalosSensorDescription(
        key="entities_offline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.derived.autonomy.entities_cloud,
        attributes_fn=lambda data: {
            "entities_total": data.derived.autonomy.entities_total,
            "entities_local": data.derived.autonomy.entities_local,
            "entities_unclassified": data.derived.autonomy.entities_unclassified,
            "by_vendor": {
                loss.vendor: loss.entities for loss in data.derived.autonomy.losses
            },
        },
    ),
    TalosSensorDescription(
        key="autonomy",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _percent(
            data.derived.autonomy.entities_local, data.derived.autonomy.entities_total
        ),
    ),
    TalosSensorDescription(
        key="devices_talking_out",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.derived.exposure.devices_direct),
        attributes_fn=lambda data: {
            "devices_total": data.derived.exposure.devices_total,
            "through_hub": len(data.derived.exposure.devices_inherited),
            "unknown_hosts": list(data.derived.exposure.unknown_hosts),
            "vendors": {
                vendor.vendor: vendor.queries for vendor in data.derived.exposure.vendors
            },
        },
    ),
    TalosSensorDescription(
        key="unverified_checks",
        state_class=SensorStateClass.MEASUREMENT,
        # Not passes, not failures. Counted separately on purpose.
        value_fn=lambda data: data.derived.unverified_count,
        attributes_fn=lambda data: {
            # The scan's own notes plus every check that could not run: the
            # count and the list must describe the same set.
            "checks": [
                {"id": check.id, "title": check.title, "reason": check.reason}
                for check in data.derived.checks.unverified
            ]
        },
    ),
    TalosSensorDescription(
        key="correlation",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        # How much of the house the join could actually reach. An empty
        # quadrant means nothing without this number beside it.
        value_fn=lambda data: _percent(
            data.derived.correlation.devices_correlated,
            data.derived.correlation.devices_total,
        ),
        attributes_fn=lambda data: {
            "devices_total": data.derived.correlation.devices_total,
            "devices_correlated": data.derived.correlation.devices_correlated,
            "method": data.derived.correlation.method,
        },
    ),
    TalosSensorDescription(
        key="database_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.store_stats.get("bytes_used"),
        attributes_fn=lambda data: {
            "observations": data.store_stats.get("observations"),
            "oldest_observation": data.store_stats.get("oldest_observation"),
            **(data.retention or {}),
        },
    ),
    TalosSensorDescription(
        key="last_scan",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: dt_util.parse_datetime(data.scan.generated_at),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TalosCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(TalosSensor(coordinator, description) for description in SENSORS)


class TalosSensor(TalosEntity, SensorEntity):
    entity_description: TalosSensorDescription

    def __init__(
        self, coordinator: TalosCoordinator, description: TalosSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        data = self.talos
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.talos
        if data is None or self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(data)
