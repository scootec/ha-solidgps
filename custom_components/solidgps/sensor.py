"""Sensor platform for SolidGPS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SolidGPSCoordinator
from .entity import SolidGPSEntity
from .models import SolidGPSData


@dataclass(frozen=True, kw_only=True)
class SolidGPSSensorEntityDescription(SensorEntityDescription):
    """Describe a SolidGPS sensor entity."""

    value_fn: Callable[[SolidGPSData], float | str | None]


SENSOR_DESCRIPTIONS: tuple[SolidGPSSensorEntityDescription, ...] = (
    SolidGPSSensorEntityDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.speed,
    ),
    SolidGPSSensorEntityDescription(
        key="gps_quality",
        translation_key="gps_quality",
        value_fn=lambda data: data.quality,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolidGPS sensors from a config entry."""
    coordinator: SolidGPSCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        SolidGPSSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class SolidGPSSensor(SolidGPSEntity, SensorEntity):
    """Represent a SolidGPS sensor."""

    entity_description: SolidGPSSensorEntityDescription

    def __init__(
        self,
        coordinator: SolidGPSCoordinator,
        description: SolidGPSSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"solidgps_{coordinator.imei}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
