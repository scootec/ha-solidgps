"""Base entity for the SolidGPS integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolidGPSCoordinator


class SolidGPSEntity(CoordinatorEntity[SolidGPSCoordinator]):
    """Base class for SolidGPS entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SolidGPSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.imei)},
        )
