# SolidGPS for Home Assistant

A Home Assistant custom integration that tracks your vehicle's location using [SolidGPS](https://www.solidgps.com/) trackers.

## Features

- Device tracker entity with GPS coordinates
- Automatic zone detection (home/away)
- Extra attributes: speed, course, GPS quality, location source
- Polls the SolidGPS API once per hour
- Falls back to cell tower location when GPS is unavailable
- Config flow UI for easy setup
- Reauth support if credentials expire

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "SolidGPS" in HACS
3. Install the integration
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/solidgps` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **SolidGPS**
3. Enter your credentials:
   - **Device IMEI**: The IMEI number of your SolidGPS tracker
   - **Auth Code**: Found in your SolidGPS dashboard URL (`auth_code` parameter)
   - **Tracking Code**: Found in your SolidGPS dashboard URL (`tracking_code` parameter)
   - **Device Name** (optional): Custom name for the tracker

### Finding Your Credentials

Open your SolidGPS dashboard in a web browser and look at the URL. It will contain the `IMEI`, `auth_code`, and `tracking_code` parameters you need.

## Entity Attributes

| Attribute | Description |
|-----------|-------------|
| `speed` | Speed over ground in KM/H |
| `course` | Heading/bearing (null when stationary) |
| `gps_quality` | GPS signal quality (e.g., "Okay", "Great") |
| `location_source` | "gps" or "cell" (cell tower fallback) |
| `last_gps_update` | Timestamp of the last GPS update |

## Update Interval

The integration polls the SolidGPS API once per hour to respect API limits. The device tracker state (home/away/zone) is automatically updated based on the GPS coordinates and your configured Home Assistant zones.
