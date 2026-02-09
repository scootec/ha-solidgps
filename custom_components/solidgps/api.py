"""SolidGPS API client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_TIMEOUT, API_URL

_LOGGER = logging.getLogger(__name__)

REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.solidgps.com/",
    "Accept": "*/*",
}


class SolidGPSApiError(Exception):
    """General SolidGPS API error."""


class SolidGPSAuthError(SolidGPSApiError):
    """Authentication error."""


class SolidGPSApiClient:
    """Client for the SolidGPS API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        imei: str,
        account_id: str,
        auth_code: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._imei = imei
        self._account_id = account_id
        self._auth_code = auth_code

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch data from the SolidGPS API."""
        params = {
            "IMEI": self._imei,
            "account_id": self._account_id,
            "auth_code": self._auth_code,
            "tracking_code": "",
            "startEpoch": "",
            "endEpoch": "",
        }

        try:
            async with asyncio.timeout(API_TIMEOUT):
                resp = await self._session.get(API_URL, params=params, headers=REQUIRED_HEADERS)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SolidGPSApiError(f"Error communicating with SolidGPS API: {err}") from err

        if resp.status != 200:
            raise SolidGPSApiError(f"SolidGPS API returned HTTP {resp.status}")

        try:
            data = await resp.json(content_type=None)
        except (ValueError, aiohttp.ContentTypeError) as err:
            raise SolidGPSApiError(f"Invalid JSON from SolidGPS API: {err}") from err

        if not data:
            raise SolidGPSApiError("SolidGPS API returned empty response")

        api_status = data.get("status")
        if api_status == 401:
            raise SolidGPSAuthError("Authentication failed (status 401)")

        if api_status != 200:
            raise SolidGPSApiError(f"SolidGPS API returned status {api_status}")

        return data

    async def async_validate_credentials(self) -> bool:
        """Validate credentials by making a test API call."""
        await self.async_get_data()
        return True


def extract_location_data(api_response: dict[str, Any], imei: str) -> dict[str, Any] | None:
    """Extract the latest location from an API response.

    Returns a flat dict with location data, or None if no data is available.
    Prefers GPS data over cell tower data.
    """
    results = api_response.get("Results", {})
    device = results.get(imei)
    if device is None:
        _LOGGER.warning("IMEI %s not found in API response", imei)
        return None

    entry = None
    source = None

    gps_data = device.get("gps_data")
    if gps_data and len(gps_data) > 0:
        entry = gps_data[0]
        source = "gps"
    else:
        cell_data = device.get("cell_data")
        if cell_data and len(cell_data) > 0:
            entry = cell_data[0]
            source = "cell"

    if entry is None:
        _LOGGER.debug("No GPS or cell data available for IMEI %s", imei)
        return None

    try:
        latitude = float(entry["latitude"])
        longitude = float(entry["longitude"])
    except (KeyError, ValueError, TypeError) as err:
        _LOGGER.warning("Failed to parse coordinates for IMEI %s: %s", imei, err)
        return None

    speed: float | None = None
    raw_speed = entry.get("sog")
    if raw_speed is not None:
        try:
            speed = float(raw_speed)
        except (ValueError, TypeError):
            _LOGGER.debug("Failed to parse speed for IMEI %s: %s", imei, raw_speed)

    course: float | None = None
    cog = entry.get("cog")
    if cog not in ("-", None, ""):
        try:
            course = float(cog)
        except (ValueError, TypeError):
            _LOGGER.debug("Failed to parse course for IMEI %s: %s", imei, cog)

    utc: int | None = None
    raw_utc = entry.get("UTC")
    if raw_utc is not None:
        try:
            utc = int(raw_utc)
        except (ValueError, TypeError):
            _LOGGER.debug("Failed to parse UTC for IMEI %s: %s", imei, raw_utc)

    quality = entry.get("quality")

    return {
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "course": course,
        "utc": utc,
        "quality": quality,
        "source": source,
    }
