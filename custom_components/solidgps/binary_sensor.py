"""Binary sensor platform for SolidGPS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SolidGPSCoordinator
from .entity import SolidGPSEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolidGPS binary sensors from a config entry."""
    coordinator: SolidGPSCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SolidGPSMovingSensor(coordinator)])


class SolidGPSMovingSensor(SolidGPSEntity, BinarySensorEntity):
    """Binary sensor indicating whether the device is moving."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "moving"

    def __init__(self, coordinator: SolidGPSCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"solidgps_{coordinator.imei}_moving"

    @property
    def is_on(self) -> bool | None:
        """Return true if the device is moving."""
        if self.coordinator.data is None:
            return None
        speed = self.coordinator.data.speed
        if speed is None:
            return False
        return speed > 0
