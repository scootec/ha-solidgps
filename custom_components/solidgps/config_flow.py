"""Config flow for SolidGPS integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolidGPSApiClient, SolidGPSApiError, SolidGPSAuthError
from .const import (
    CONF_AUTH_CODE,
    CONF_DEVICE_NAME,
    CONF_IMEI,
    CONF_TRACKING_CODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IMEI): str,
        vol.Required(CONF_AUTH_CODE): str,
        vol.Required(CONF_TRACKING_CODE): str,
        vol.Optional(CONF_DEVICE_NAME, default=""): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTH_CODE): str,
        vol.Required(CONF_TRACKING_CODE): str,
    }
)


class SolidGPSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolidGPS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_IMEI])
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = SolidGPSApiClient(
                session=session,
                imei=user_input[CONF_IMEI],
                auth_code=user_input[CONF_AUTH_CODE],
                tracking_code=user_input[CONF_TRACKING_CODE],
            )

            try:
                await client.async_validate_credentials()
            except SolidGPSAuthError:
                errors["base"] = "invalid_auth"
            except SolidGPSApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"
            else:
                name = (user_input.get(CONF_DEVICE_NAME) or "").strip()
                if not name:
                    name = f"SolidGPS {user_input[CONF_IMEI][-4:]}"

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_IMEI: user_input[CONF_IMEI],
                        CONF_AUTH_CODE: user_input[CONF_AUTH_CODE],
                        CONF_TRACKING_CODE: user_input[CONF_TRACKING_CODE],
                        CONF_DEVICE_NAME: name,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            session = async_get_clientsession(self.hass)
            client = SolidGPSApiClient(
                session=session,
                imei=reauth_entry.data[CONF_IMEI],
                auth_code=user_input[CONF_AUTH_CODE],
                tracking_code=user_input[CONF_TRACKING_CODE],
            )

            try:
                await client.async_validate_credentials()
            except SolidGPSAuthError:
                errors["base"] = "invalid_auth"
            except SolidGPSApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_AUTH_CODE: user_input[CONF_AUTH_CODE],
                        CONF_TRACKING_CODE: user_input[CONF_TRACKING_CODE],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )
