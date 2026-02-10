"""The SolidGPS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolidGPSApiClient
from .const import CONF_ACCOUNT_ID, CONF_AUTH_CODE, CONF_IMEI, DOMAIN
from .coordinator import SolidGPSCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    if config_entry.version < 2:
        _LOGGER.debug(
            "Migrating SolidGPS config entry from version %s to 2",
            config_entry.version,
        )
        hass.config_entries.async_update_entry(config_entry, version=2)
        _LOGGER.info(
            "SolidGPS config entry migrated to version 2. "
            "Re-authentication will be required when auth_code expires."
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolidGPS from a config entry."""
    session = async_get_clientsession(hass)
    api_client = SolidGPSApiClient(
        session=session,
        imei=entry.data[CONF_IMEI],
        account_id=entry.data[CONF_ACCOUNT_ID],
        auth_code=entry.data[CONF_AUTH_CODE],
    )

    coordinator = SolidGPSCoordinator(hass, entry, api_client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
