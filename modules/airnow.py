"""AirNow API integration for air quality data."""
import requests
import logging
import config
from modules import cache

log = logging.getLogger(__name__)


AQI_CATEGORIES = [
    (50,  "Good",                    "#00e400", "#000"),
    (100, "Moderate",                "#ffff00", "#000"),
    (150, "Unhealthy for Sensitive", "#ff7e00", "#000"),
    (200, "Unhealthy",               "#ff0000", "#fff"),
    (300, "Very Unhealthy",          "#8f3f97", "#fff"),
    (500, "Hazardous",               "#7e0023", "#fff"),
]


def _classify_aqi(aqi: int) -> dict:
    for threshold, label, bg, fg in AQI_CATEGORIES:
        if aqi <= threshold:
            return {"category": label, "bg_color": bg, "text_color": fg}
    return {"category": "Hazardous", "bg_color": "#7e0023", "text_color": "#fff"}


def get_aqi() -> dict:
    cached = cache.get("airnow_aqi")
    if cached:
        return cached

    if not config.AIRNOW_API_KEY:
        return {
            "error": "No AirNow API key configured",
            "configured": False,
            "aqi": None,
            "category": "Unknown",
            "bg_color": "#444",
            "text_color": "#fff",
        }

    try:
        params = {
            "latitude": config.LAT,
            "longitude": config.LON,
            "distance": 25,
            "API_KEY": config.AIRNOW_API_KEY,
            "format": "application/json",
        }
        url = "https://www.airnowapi.org/aq/observation/latLong/current/"
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        observations = r.json()

        if not observations:
            return {"error": "No AQI observations available", "aqi": None}

        # Find the worst pollutant
        worst = max(observations, key=lambda x: x.get("AQI", 0))
        aqi_val = worst.get("AQI", 0)
        classification = _classify_aqi(aqi_val)

        pollutants = []
        for obs in observations:
            p_aqi = obs.get("AQI", 0)
            p_class = _classify_aqi(p_aqi)
            pollutants.append({
                "name": obs.get("ParameterName", ""),
                "aqi": p_aqi,
                "category": p_class["category"],
                "bg_color": p_class["bg_color"],
                "reporting_area": obs.get("ReportingArea", ""),
            })

        result = {
            "configured": True,
            "aqi": aqi_val,
            "category": classification["category"],
            "bg_color": classification["bg_color"],
            "text_color": classification["text_color"],
            "primary_pollutant": worst.get("ParameterName", ""),
            "reporting_area": worst.get("ReportingArea", ""),
            "date_observed": worst.get("DateObserved", ""),
            "pollutants": pollutants,
        }
        cache.set("airnow_aqi", result, config.CACHE_TTL["aqi"])
        return result
    except Exception as e:
        log.error("AirNow fetch failed: %s", e)
        return {
            "error": str(e),
            "configured": True,
            "aqi": None,
            "category": "Unknown",
            "bg_color": "#444",
            "text_color": "#fff",
        }
