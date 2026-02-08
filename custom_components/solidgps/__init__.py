"""The SolidGPS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolidGPSApiClient
from .const import CONF_AUTH_CODE, CONF_IMEI, CONF_TRACKING_CODE, DOMAIN
from .coordinator import SolidGPSCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolidGPS from a config entry."""
    session = async_get_clientsession(hass)
    api_client = SolidGPSApiClient(
        session=session,
        imei=entry.data[CONF_IMEI],
        auth_code=entry.data[CONF_AUTH_CODE],
        tracking_code=entry.data[CONF_TRACKING_CODE],
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
