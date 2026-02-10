"""SolidGPS API client."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from .const import (
    API_TIMEOUT,
    API_URL,
    DASHBOARD_URL,
    LOGIN_AJAX_URL,
    LOGIN_PAGE_URL,
    LOGIN_TIMEOUT,
)

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


class SolidGPSLoginError(SolidGPSApiError):
    """Login flow error (transient/network)."""


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

    def update_credentials(self, account_id: str, auth_code: str) -> None:
        """Update stored credentials after re-login."""
        self._account_id = account_id
        self._auth_code = auth_code

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


class SolidGPSAuthenticator:
    """Handle WordPress login flow to obtain fresh auth credentials."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the authenticator."""
        self._email = email
        self._password = password

    async def async_login(self) -> dict[str, Any]:
        """Perform login and return credentials and device info.

        Returns dict with keys: account_id, auth_code, devices.
        devices is a dict of {imei: {Nickname, DeviceType, ...}}.

        Raises SolidGPSAuthError for bad credentials.
        Raises SolidGPSLoginError for transient/network errors.
        """
        jar = aiohttp.CookieJar()
        try:
            async with aiohttp.ClientSession(cookie_jar=jar) as session:
                nonce = await self._get_login_nonce(session)
                await self._submit_login(session, nonce)
                return await self._extract_dashboard_data(session)
        except (SolidGPSAuthError, SolidGPSLoginError):
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SolidGPSLoginError(
                f"Network error during login: {err}"
            ) from err

    async def _get_login_nonce(self, session: aiohttp.ClientSession) -> str:
        """Fetch the login page and extract the nonce."""
        async with asyncio.timeout(LOGIN_TIMEOUT):
            resp = await session.get(LOGIN_PAGE_URL)
            html = await resp.text()

        match = re.search(
            r'"ur_login_form_save_nonce"\s*:\s*"([a-f0-9]+)"', html
        )
        if not match:
            raise SolidGPSLoginError("Could not find login nonce in page")
        return match.group(1)

    async def _submit_login(
        self, session: aiohttp.ClientSession, nonce: str
    ) -> None:
        """Submit AJAX login with credentials."""
        url = f"{LOGIN_AJAX_URL}?action=user_registration_ajax_login_submit&security={nonce}"
        form_data = aiohttp.FormData()
        form_data.add_field("username", self._email)
        form_data.add_field("password", self._password)
        form_data.add_field("redirect", "/dashboard/")

        async with asyncio.timeout(LOGIN_TIMEOUT):
            resp = await session.post(url, data=form_data)
            result = await resp.json(content_type=None)

        if not result.get("success"):
            msg = "Login failed"
            data = result.get("data", {})
            if isinstance(data, dict):
                msg = data.get("message", msg)
            elif isinstance(data, str):
                # Strip HTML tags from error message
                msg = re.sub(r"<[^>]+>", "", data)
            raise SolidGPSAuthError(msg)

    async def _extract_dashboard_data(
        self, session: aiohttp.ClientSession
    ) -> dict[str, Any]:
        """Fetch dashboard and extract account_info and device_info."""
        async with asyncio.timeout(LOGIN_TIMEOUT):
            resp = await session.get(DASHBOARD_URL)
            html = await resp.text()

        account_info = self._parse_js_object(html, "account_info")
        if not account_info:
            raise SolidGPSLoginError(
                "Could not extract account_info from dashboard"
            )

        device_info = self._parse_js_object(html, "device_info")
        if not device_info:
            raise SolidGPSLoginError(
                "Could not extract device_info from dashboard"
            )

        account_id = account_info.get("AccountID")
        auth_code = account_info.get("AuthCode")
        if not account_id or not auth_code:
            raise SolidGPSLoginError(
                "Missing AccountID or AuthCode in account_info"
            )

        return {
            "account_id": str(account_id),
            "auth_code": str(auth_code),
            "devices": device_info,
        }

    @staticmethod
    def _parse_js_object(html: str, var_name: str) -> dict[str, Any] | None:
        """Extract a JavaScript object assignment from HTML.

        Matches patterns like: var account_info = {...};
        Uses brace counting to handle nested objects.
        """
        pattern = rf"var\s+{re.escape(var_name)}\s*=\s*\{{"
        match = re.search(pattern, html)
        if not match:
            return None

        start = match.end() - 1  # include the opening brace
        depth = 0
        for i in range(start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    json_str = html[start : i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        _LOGGER.debug(
                            "Failed to parse %s JSON from dashboard",
                            var_name,
                        )
                        return None
        return None
