"""Data models for the SolidGPS integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SolidGPSData:
    """Consolidated data from SolidGPS API."""

    latitude: float | None = None
    longitude: float | None = None
    speed: float | None = None
    course: float | None = None
    utc: int | None = None
    quality: str | None = None
    source: str | None = None  # "gps" | "cell"
