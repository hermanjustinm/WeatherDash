"""USGS Water Services API integration for river gauge data."""
import requests
import logging
from datetime import datetime, timezone
import config
from modules import cache

log = logging.getLogger(__name__)

USGS_BASE = "https://waterservices.usgs.gov/nwis/iv/"


def _fetch_gauge(site_no: str) -> dict:
    """Fetch instantaneous values for a single USGS gauge site."""
    params = {
        "format": "json",
        "sites": site_no,
        "parameterCd": "00060,00065",  # discharge (cfs) + gage height (ft)
        "siteStatus": "active",
    }
    try:
        r = requests.get(USGS_BASE, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        ts_list = data.get("value", {}).get("timeSeries", [])

        result = {"site": site_no, "gage_height_ft": None, "discharge_cfs": None, "timestamp": None}

        for ts in ts_list:
            var_code = ts["variable"]["variableCode"][0]["value"]
            values = ts.get("values", [{}])[0].get("value", [])
            if not values:
                continue
            latest = values[-1]
            val = latest.get("value")
            dt = latest.get("dateTime")
            if result["timestamp"] is None:
                result["timestamp"] = dt

            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue

            if var_code == "00065":
                result["gage_height_ft"] = round(fval, 2)
            elif var_code == "00060":
                result["discharge_cfs"] = round(fval, 1)

        return result
    except Exception as e:
        log.error("USGS gauge %s fetch failed: %s", site_no, e)
        return {"site": site_no, "error": str(e)}


def _get_flood_status(site_no: str, gage_height_ft: float) -> dict:
    stages = config.FLOOD_STAGES.get(site_no, {})
    if not stages or gage_height_ft is None:
        return {"status": "unknown", "color": "gray"}

    if gage_height_ft >= stages.get("major", 9999):
        return {"status": "Major Flood", "color": "#ff0000"}
    elif gage_height_ft >= stages.get("moderate", 9999):
        return {"status": "Moderate Flood", "color": "#ff6600"}
    elif gage_height_ft >= stages.get("flood", 9999):
        return {"status": "Flood Stage", "color": "#ff9900"}
    elif gage_height_ft >= stages.get("action", 9999):
        return {"status": "Action Stage", "color": "#ffcc00"}
    else:
        return {"status": "Normal", "color": "#00cc44"}


def get_river_levels() -> dict:
    cached = cache.get("usgs_rivers")
    if cached:
        return cached

    gauges = []
    for name, site_no in config.USGS_GAUGES.items():
        data = _fetch_gauge(site_no)
        flood_info = _get_flood_status(site_no, data.get("gage_height_ft"))
        stages = config.FLOOD_STAGES.get(site_no, {})
        gauges.append({
            "name": name,
            "site_no": site_no,
            "gage_height_ft": data.get("gage_height_ft"),
            "discharge_cfs": data.get("discharge_cfs"),
            "timestamp": data.get("timestamp"),
            "flood_status": flood_info["status"],
            "flood_color": flood_info["color"],
            "flood_stage_ft": stages.get("flood"),
            "action_stage_ft": stages.get("action"),
            "error": data.get("error"),
        })

    result = {"gauges": gauges}
    cache.set("usgs_rivers", result, config.CACHE_TTL["river"])
    return result
