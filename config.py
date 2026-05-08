import os
from dotenv import load_dotenv

load_dotenv()

# Location
LAT = float(os.getenv("LAT", "47.0379"))
LON = float(os.getenv("LON", "-122.9007"))
LOCATION_NAME = os.getenv("LOCATION_NAME", "Olympia, WA")
TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")

# API Keys
AIRNOW_API_KEY = os.getenv("AIRNOW_API_KEY", "")
WSDOT_API_KEY = os.getenv("WSDOT_API_KEY", "")

# Flask
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", "5000"))

# NWS API
NWS_BASE = "https://api.weather.gov"
NWS_HEADERS = {
    "User-Agent": f"WeatherDash/1.0 (home-weather-dashboard; contact@localhost)",
    "Accept": "application/geo+json",
}

# USGS Water Services — gauges near Olympia, WA
USGS_GAUGES = {
    "Deschutes River (Tumwater)": "12080010",
    "Nisqually River (McKenna)": "12082500",
    "Black River": "12077500",
}

# NOAA Tides — Olympia, WA station
NOAA_TIDE_STATION = "9446484"  # Olympia, WA
NOAA_TIDES_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# AirNow
AIRNOW_BASE = "https://www.airnowapi.org/aq/observation/latLong/current/"
AIRNOW_ZIP = "98501"

# WA DOT cameras — hardcoded public camera IDs near Olympia
# These are camera IDs from the WSDOT public feed
WSDOT_CAMERAS_BASE = "https://www.wsdot.wa.gov/traffic/api/HighwayCameras/HighwayCameraRest.svc"
WSDOT_CAMERA_IDS = [
    {"id": 1099, "label": "I-5 at Capitol Blvd", "location": "Olympia"},
    {"id": 1098, "label": "I-5 at 2nd Ave", "location": "Olympia"},
    {"id": 1100, "label": "I-5 at Airdustrial Way", "location": "Olympia"},
    {"id": 9223, "label": "US-101 at Black Lake", "location": "Olympia"},
    {"id": 1097, "label": "I-5 SB at Tumwater", "location": "Tumwater"},
    {"id": 1101, "label": "I-5 at Marvin Rd", "location": "Lacey"},
]

# Cache TTLs (seconds)
CACHE_TTL = {
    "radar": int(os.getenv("CACHE_RADAR_TTL", "300")),
    "current": int(os.getenv("CACHE_CURRENT_TTL", "600")),
    "forecast": int(os.getenv("CACHE_FORECAST_TTL", "1800")),
    "alerts": int(os.getenv("CACHE_ALERTS_TTL", "120")),
    "aqi": int(os.getenv("CACHE_AQI_TTL", "1800")),
    "river": int(os.getenv("CACHE_RIVER_TTL", "900")),
    "tides": int(os.getenv("CACHE_TIDES_TTL", "1800")),
    "cameras": int(os.getenv("CACHE_CAMERAS_TTL", "60")),
    "sun": int(os.getenv("CACHE_SUN_TTL", "43200")),
}

# NWS Thurston County alert zone
NWS_ALERT_ZONE = "WAC067"   # Thurston County
NWS_FORECAST_ZONE = "WAZ516"  # Olympia area

# Flood stage reference for gauges (in feet)
FLOOD_STAGES = {
    "12080010": {"action": 10.0, "flood": 12.0, "moderate": 14.0, "major": 17.0},
    "12082500": {"action": 18.0, "flood": 20.0, "moderate": 23.0, "major": 28.0},
    "12077500": {"action": 8.0,  "flood": 10.0, "moderate": 12.0, "major": 14.0},
}
