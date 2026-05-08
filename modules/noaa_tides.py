"""NOAA Tides & Currents API integration."""
import requests
import logging
from datetime import datetime, date, timedelta
import pytz
import config
from modules import cache

log = logging.getLogger(__name__)


def _fetch_tide_predictions(begin_date: str, end_date: str) -> list:
    params = {
        "begin_date": begin_date,
        "end_date": end_date,
        "station": config.NOAA_TIDE_STATION,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "interval": "hilo",  # only highs and lows
        "units": "english",
        "application": "WeatherDash",
        "format": "json",
    }
    r = requests.get(config.NOAA_TIDES_BASE, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("predictions", [])


def _fetch_water_level() -> dict:
    """Fetch current observed water level."""
    params = {
        "station": config.NOAA_TIDE_STATION,
        "product": "water_level",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "application": "WeatherDash",
        "format": "json",
        "date": "latest",
    }
    r = requests.get(config.NOAA_TIDES_BASE, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    obs = data.get("data", [])
    if obs:
        latest = obs[-1]
        return {"level_ft": float(latest["v"]), "timestamp": latest["t"], "quality": latest.get("q", "")}
    return {}


def get_tides() -> dict:
    cached = cache.get("noaa_tides")
    if cached:
        return cached

    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)

    try:
        predictions = _fetch_tide_predictions(
            today.strftime("%Y%m%d"),
            tomorrow.strftime("%Y%m%d"),
        )

        tides = []
        for p in predictions:
            tides.append({
                "time": p["t"],
                "height_ft": float(p["v"]),
                "type": "High" if p["type"] == "H" else "Low",
            })

        current_level = {}
        try:
            current_level = _fetch_water_level()
        except Exception as e:
            log.warning("Current water level fetch failed: %s", e)

        # Find next high and low
        now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        next_high = next((t for t in tides if t["type"] == "High" and t["time"] > now_str), None)
        next_low = next((t for t in tides if t["type"] == "Low" and t["time"] > now_str), None)

        result = {
            "station": config.NOAA_TIDE_STATION,
            "station_name": "Olympia, WA",
            "tides_today": [t for t in tides if t["time"].startswith(str(today))],
            "tides_tomorrow": [t for t in tides if t["time"].startswith(str(tomorrow))],
            "current_level_ft": current_level.get("level_ft"),
            "current_level_timestamp": current_level.get("timestamp"),
            "next_high": next_high,
            "next_low": next_low,
        }
        cache.set("noaa_tides", result, config.CACHE_TTL["tides"])
        return result
    except Exception as e:
        log.error("NOAA tides fetch failed: %s", e)
        return {"error": str(e)}
