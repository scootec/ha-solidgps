"""Constants for the SolidGPS integration."""

from datetime import timedelta

DOMAIN = "solidgps"

API_URL = "https://www.solidgps.com/custom/dashboardConfig/dashboard.9/request.php"
API_TIMEOUT = 30

CONF_IMEI = "imei"
CONF_ACCOUNT_ID = "account_id"
CONF_AUTH_CODE = "auth_code"
CONF_DEVICE_NAME = "device_name"

UPDATE_INTERVAL = timedelta(minutes=5)

ATTR_SPEED = "speed"
ATTR_COURSE = "course"
ATTR_GPS_QUALITY = "gps_quality"
ATTR_LOCATION_SOURCE = "location_source"
ATTR_LAST_GPS_UPDATE = "last_gps_update"

EVENT_MOTION_STARTED = "solidgps_motion_started"
EVENT_MOTION_STOPPED = "solidgps_motion_stopped"
