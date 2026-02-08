"""DataUpdateCoordinator for SolidGPS."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SolidGPSApiClient, SolidGPSApiError, SolidGPSAuthError, extract_location_data
from .const import CONF_IMEI, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SolidGPSCoordinator(DataUpdateCoordinator[dict[str, Any] | None]):
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

    async def _async_update_data(self) -> dict[str, Any] | None:
        """Fetch the latest data from the SolidGPS API."""
        try:
            response = await self.api_client.async_get_data()
        except SolidGPSAuthError as err:
            raise ConfigEntryAuthFailed(
                "SolidGPS authentication failed"
            ) from err
        except SolidGPSApiError as err:
            raise UpdateFailed(
                f"Error communicating with SolidGPS: {err}"
            ) from err

        return extract_location_data(response, self.imei)
