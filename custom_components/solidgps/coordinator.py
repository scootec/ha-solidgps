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

from .api import (
    SolidGPSApiClient,
    SolidGPSApiError,
    SolidGPSAuthenticator,
    SolidGPSAuthError,
    SolidGPSLoginError,
    extract_location_data,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_AUTH_CODE,
    CONF_EMAIL,
    CONF_IMEI,
    CONF_PASSWORD,
    DOMAIN,
    EVENT_MOTION_STARTED,
    EVENT_MOTION_STOPPED,
    UPDATE_INTERVAL,
)
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
            response = await self._handle_auth_refresh(err)
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

    async def _handle_auth_refresh(self, original_error: SolidGPSAuthError) -> dict:
        """Attempt to re-login and retry the API call.

        Returns the API response on success.
        Raises ConfigEntryAuthFailed if credentials are bad or missing.
        Raises UpdateFailed if login has a transient failure.
        """
        email = self.config_entry.data.get(CONF_EMAIL)
        password = self.config_entry.data.get(CONF_PASSWORD)

        if not email or not password:
            raise ConfigEntryAuthFailed(
                "SolidGPS authentication expired. Please re-authenticate with email and password."
            ) from original_error

        _LOGGER.debug("Auth expired, attempting re-login for %s", email)

        try:
            authenticator = SolidGPSAuthenticator(email, password)
            login_data = await authenticator.async_login()
        except SolidGPSAuthError as err:
            raise ConfigEntryAuthFailed(f"SolidGPS re-login failed: {err}") from err
        except SolidGPSLoginError as err:
            raise UpdateFailed(f"SolidGPS login error (will retry): {err}") from err

        new_account_id = login_data["account_id"]
        new_auth_code = login_data["auth_code"]

        self.api_client.update_credentials(new_account_id, new_auth_code)

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_ACCOUNT_ID: new_account_id,
                CONF_AUTH_CODE: new_auth_code,
            },
        )

        _LOGGER.info("SolidGPS credentials refreshed successfully")

        try:
            return await self.api_client.async_get_data()
        except SolidGPSAuthError as err:
            raise ConfigEntryAuthFailed("SolidGPS authentication failed after re-login") from err
        except SolidGPSApiError as err:
            raise UpdateFailed(f"Error communicating with SolidGPS after re-login: {err}") from err

    def _fire_motion_events(self, current_speed: float | None) -> None:
        """Fire motion started/stopped events on speed transitions."""
        was_moving = self._previous_speed is not None and self._previous_speed > 0
        is_moving = current_speed is not None and current_speed > 0

        if is_moving and not was_moving:
            self.hass.bus.async_fire(EVENT_MOTION_STARTED, {"imei": self.imei})
        elif was_moving and not is_moving:
            self.hass.bus.async_fire(EVENT_MOTION_STOPPED, {"imei": self.imei})
