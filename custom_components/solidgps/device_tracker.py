"""Device tracker platform for SolidGPS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COURSE,
    ATTR_GPS_QUALITY,
    ATTR_LAST_GPS_UPDATE,
    ATTR_LOCATION_SOURCE,
    ATTR_SPEED,
    CONF_DEVICE_NAME,
    CONF_IMEI,
    DOMAIN,
)
from .coordinator import SolidGPSCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolidGPS device tracker from a config entry."""
    coordinator: SolidGPSCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SolidGPSTracker(coordinator, config_entry)])


class SolidGPSTracker(CoordinatorEntity[SolidGPSCoordinator], TrackerEntity):
    """Represent a SolidGPS tracked device."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: SolidGPSCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the tracker entity."""
        super().__init__(coordinator)

        imei = config_entry.data[CONF_IMEI]
        device_name = config_entry.data.get(CONF_DEVICE_NAME) or f"SolidGPS {imei[-4:]}"

        self._attr_unique_id = f"solidgps_{imei}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, imei)},
            name=device_name,
            manufacturer="SolidGPS",
            model="GPS Tracker",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("latitude")

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("longitude")

    @property
    def location_accuracy(self) -> float:
        """Return the location accuracy of the device."""
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data
        attrs: dict[str, Any] = {}

        if (speed := data.get("speed")) is not None:
            attrs[ATTR_SPEED] = speed
        if (course := data.get("course")) is not None:
            attrs[ATTR_COURSE] = course
        if (quality := data.get("quality")) is not None:
            attrs[ATTR_GPS_QUALITY] = quality
        if (source := data.get("source")) is not None:
            attrs[ATTR_LOCATION_SOURCE] = source
        if (utc := data.get("utc")) is not None:
            attrs[ATTR_LAST_GPS_UPDATE] = dt_util.utc_from_timestamp(utc).isoformat()

        return attrs
