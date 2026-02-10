"""Config flow for SolidGPS integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import (
    SolidGPSAuthenticator,
    SolidGPSAuthError,
    SolidGPSLoginError,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_AUTH_CODE,
    CONF_DEVICE_NAME,
    CONF_EMAIL,
    CONF_IMEI,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SolidGPSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolidGPS."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._login_data: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle step 1: email and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                authenticator = SolidGPSAuthenticator(email, password)
                login_data = await authenticator.async_login()
            except SolidGPSAuthError:
                errors["base"] = "invalid_auth"
            except SolidGPSLoginError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during login")
                errors["base"] = "unknown"
            else:
                self._login_data = {
                    **login_data,
                    CONF_EMAIL: email,
                    CONF_PASSWORD: password,
                }

                devices = login_data.get("devices", {})
                if len(devices) == 1:
                    imei = next(iter(devices))
                    return await self._create_device_entry(imei)

                return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle step 2: device selection."""
        assert self._login_data is not None

        if user_input is not None:
            return await self._create_device_entry(user_input[CONF_IMEI])

        devices = self._login_data.get("devices", {})
        device_options = {}
        for imei, info in devices.items():
            nickname = info.get("Nickname", "").strip() if isinstance(info, dict) else ""
            label = f"{nickname} ({imei})" if nickname else imei
            device_options[imei] = label

        schema = vol.Schema(
            {
                vol.Required(CONF_IMEI): vol.In(device_options),
            }
        )

        return self.async_show_form(
            step_id="select_device",
            data_schema=schema,
        )

    async def _create_device_entry(self, imei: str) -> ConfigFlowResult:
        """Create a config entry for a selected device."""
        assert self._login_data is not None

        await self.async_set_unique_id(imei)
        self._abort_if_unique_id_configured()

        devices = self._login_data.get("devices", {})
        device_info = devices.get(imei, {})
        nickname = ""
        if isinstance(device_info, dict):
            nickname = device_info.get("Nickname", "").strip()
        name = nickname if nickname else f"SolidGPS {imei[-4:]}"

        return self.async_create_entry(
            title=name,
            data={
                CONF_EMAIL: self._login_data[CONF_EMAIL],
                CONF_PASSWORD: self._login_data[CONF_PASSWORD],
                CONF_IMEI: imei,
                CONF_ACCOUNT_ID: self._login_data["account_id"],
                CONF_AUTH_CODE: self._login_data["auth_code"],
                CONF_DEVICE_NAME: name,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation with email and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                authenticator = SolidGPSAuthenticator(email, password)
                login_data = await authenticator.async_login()
            except SolidGPSAuthError:
                errors["base"] = "invalid_auth"
            except SolidGPSLoginError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Validate that the IMEI from this entry exists in the account
                imei = reauth_entry.data[CONF_IMEI]
                devices = login_data.get("devices", {})
                if imei not in devices:
                    errors["base"] = "device_not_found"
                else:
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data_updates={
                            CONF_EMAIL: email,
                            CONF_PASSWORD: password,
                            CONF_ACCOUNT_ID: login_data["account_id"],
                            CONF_AUTH_CODE: login_data["auth_code"],
                        },
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )
