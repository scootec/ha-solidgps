"""DataUpdateCoordinator for SolidGPS."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SolidGPSApiClient, SolidGPSApiError, SolidGPSAuthError, extract_location_data
from .const import CONF_IMEI, DOMAIN, EVENT_MOTION_STARTED, EVENT_MOTION_STOPPED, UPDATE_INTERVAL
from .models import SolidGPSData

_LOGGER = logging.getLogger(__name__)


class SolidGPSCoordinator(DataUpdateCoordinator[SolidGPSData]):
    """Coordinator to manage fetching SolidGPS data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: SolidGPSApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
        )
        self.api_client = api_client
        self.imei = config_entry.data[CONF_IMEI]
        self._previous_speed: float | None = None

    async def _async_update_data(self) -> SolidGPSData:
        """Fetch the latest data from the SolidGPS API."""
        try:
            response = await self.api_client.async_get_data()
        except SolidGPSAuthError as err:
            raise ConfigEntryAuthFailed("SolidGPS authentication failed") from err
        except SolidGPSApiError as err:
            raise UpdateFailed(f"Error communicating with SolidGPS: {err}") from err

        raw = extract_location_data(response, self.imei)
        if raw is None:
            return SolidGPSData()

        data = SolidGPSData(
            latitude=raw["latitude"],
            longitude=raw["longitude"],
            speed=raw.get("speed"),
            course=raw.get("course"),
            utc=raw.get("utc"),
            quality=raw.get("quality"),
            source=raw.get("source"),
        )

        self._fire_motion_events(data.speed)
        self._previous_speed = data.speed

        return data

    def _fire_motion_events(self, current_speed: float | None) -> None:
        """Fire motion started/stopped events on speed transitions."""
        was_moving = self._previous_speed is not None and self._previous_speed > 0
        is_moving = current_speed is not None and current_speed > 0

        if is_moving and not was_moving:
            self.hass.bus.async_fire(EVENT_MOTION_STARTED, {"imei": self.imei})
        elif was_moving and not is_moving:
            self.hass.bus.async_fire(EVENT_MOTION_STOPPED, {"imei": self.imei})
