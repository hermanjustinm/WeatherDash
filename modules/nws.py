"""National Weather Service API integration."""
import requests
import logging
from datetime import datetime, timezone
from typing import Optional
import config
from modules import cache

log = logging.getLogger(__name__)

_nws_meta: Optional[dict] = None  # cached points/gridpoint metadata


def _get_nws_meta() -> Optional[dict]:
    global _nws_meta
    if _nws_meta:
        return _nws_meta

    cached = cache.get("nws_meta")
    if cached:
        _nws_meta = cached
        return _nws_meta

    try:
        url = f"{config.NWS_BASE}/points/{config.LAT},{config.LON}"
        r = requests.get(url, headers=config.NWS_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        props = data["properties"]
        meta = {
            "forecast_url": props["forecast"],
            "forecast_hourly_url": props["forecastHourly"],
            "observation_stations_url": props["observationStations"],
            "gridId": props["gridId"],
            "gridX": props["gridX"],
            "gridY": props["gridY"],
            "cwa": props["cwa"],
            "timezone": props["timeZone"],
            "city": props.get("relativeLocation", {}).get("properties", {}).get("city", ""),
            "state": props.get("relativeLocation", {}).get("properties", {}).get("state", ""),
        }
        cache.set("nws_meta", meta, 86400)  # cache for 24 hours
        _nws_meta = meta
        return meta
    except Exception as e:
        log.error("NWS points lookup failed: %s", e)
        return None


def _get_observation_station() -> Optional[str]:
    cached = cache.get("nws_obs_station")
    if cached:
        return cached

    meta = _get_nws_meta()
    if not meta:
        return None

    try:
        r = requests.get(
            meta["observation_stations_url"],
            headers=config.NWS_HEADERS,
            timeout=10
        )
        r.raise_for_status()
        stations = r.json()
        station_id = stations["features"][0]["properties"]["stationIdentifier"]
        cache.set("nws_obs_station", station_id, 86400)
        return station_id
    except Exception as e:
        log.error("NWS station lookup failed: %s", e)
        return None


def get_current_conditions() -> dict:
    cached = cache.get("nws_current")
    if cached:
        return cached

    station = _get_observation_station()
    if not station:
        return {"error": "Unable to resolve NWS observation station"}

    try:
        url = f"{config.NWS_BASE}/stations/{station}/observations/latest"
        r = requests.get(url, headers=config.NWS_HEADERS, timeout=10)
        r.raise_for_status()
        obs = r.json()["properties"]

        def c_to_f(c):
            if c is None:
                return None
            return round(c * 9 / 5 + 32, 1)

        def ms_to_mph(ms):
            if ms is None:
                return None
            return round(ms * 2.237, 1)

        def pa_to_inhg(pa):
            if pa is None:
                return None
            return round(pa * 0.0002953, 2)

        temp_c = obs.get("temperature", {}).get("value")
        dewpoint_c = obs.get("dewpoint", {}).get("value")
        wind_speed_ms = obs.get("windSpeed", {}).get("value")
        wind_gust_ms = obs.get("windGust", {}).get("value")
        wind_dir = obs.get("windDirection", {}).get("value")
        humidity = obs.get("relativeHumidity", {}).get("value")
        pressure_pa = obs.get("barometricPressure", {}).get("value")
        visibility_m = obs.get("visibility", {}).get("value")
        precip_1h_mm = obs.get("precipitationLastHour", {}).get("value")
        precip_6h_mm = obs.get("precipitationLast6Hours", {}).get("value")
        precip_24h_mm = obs.get("precipitationLast24Hours", {}).get("value")

        # NWS observations sometimes report null wind speed even when gust is valid.
        # Parse wind speed from the hourly forecast description as a last resort.
        wind_speed_mph = ms_to_mph(wind_speed_ms)
        if wind_speed_mph is None and wind_gust_ms is not None:
            # Treat gust as a floor estimate for display
            wind_speed_mph = ms_to_mph(wind_gust_ms)

        result = {
            "station": station,
            "timestamp": obs.get("timestamp"),
            "description": obs.get("textDescription", ""),
            "icon": obs.get("icon", ""),
            "temperature_f": c_to_f(temp_c),
            "temperature_c": round(temp_c, 1) if temp_c is not None else None,
            "dewpoint_f": c_to_f(dewpoint_c),
            "humidity": round(humidity, 1) if humidity is not None else None,
            "wind_speed_mph": wind_speed_mph,
            "wind_speed_estimated": wind_speed_ms is None and wind_gust_ms is not None,
            "wind_gust_mph": ms_to_mph(wind_gust_ms),
            "wind_direction_deg": wind_dir,
            "wind_direction_cardinal": _deg_to_cardinal(wind_dir),
            "pressure_inhg": pa_to_inhg(pressure_pa),
            "visibility_miles": round(visibility_m * 0.000621371, 1) if visibility_m is not None else None,
            "precip_1h_in": round(precip_1h_mm * 0.0393701, 2) if precip_1h_mm is not None else None,
            "precip_6h_in": round(precip_6h_mm * 0.0393701, 2) if precip_6h_mm is not None else None,
            "precip_24h_in": round(precip_24h_mm * 0.0393701, 2) if precip_24h_mm is not None else None,
        }
        cache.set("nws_current", result, config.CACHE_TTL["current"])
        return result
    except Exception as e:
        log.error("NWS current conditions failed: %s", e)
        return {"error": str(e)}


def get_hourly_forecast() -> dict:
    cached = cache.get("nws_hourly")
    if cached:
        return cached

    meta = _get_nws_meta()
    if not meta:
        return {"error": "NWS metadata unavailable"}

    try:
        r = requests.get(meta["forecast_hourly_url"], headers=config.NWS_HEADERS, timeout=15)
        r.raise_for_status()
        periods = r.json()["properties"]["periods"][:24]

        result = {"periods": []}
        for p in periods:
            result["periods"].append({
                "time": p["startTime"],
                "temp_f": p["temperature"],
                "temp_unit": p["temperatureUnit"],
                "wind_speed": p["windSpeed"],
                "wind_direction": p["windDirection"],
                "description": p["shortForecast"],
                "icon": p["icon"],
                "precip_chance": p.get("probabilityOfPrecipitation", {}).get("value"),
                "humidity": p.get("relativeHumidity", {}).get("value"),
                "is_daytime": p["isDaytime"],
            })

        cache.set("nws_hourly", result, config.CACHE_TTL["forecast"])
        return result
    except Exception as e:
        log.error("NWS hourly forecast failed: %s", e)
        return {"error": str(e)}


def get_daily_forecast() -> dict:
    cached = cache.get("nws_daily")
    if cached:
        return cached

    meta = _get_nws_meta()
    if not meta:
        return {"error": "NWS metadata unavailable"}

    try:
        r = requests.get(meta["forecast_url"], headers=config.NWS_HEADERS, timeout=15)
        r.raise_for_status()
        periods = r.json()["properties"]["periods"]

        # Pair day/night periods
        days = []
        i = 0
        while i < len(periods) and len(days) < 7:
            p = periods[i]
            day_entry = {
                "name": p["name"],
                "date": p["startTime"][:10],
                "is_daytime": p["isDaytime"],
                "temp_f": p["temperature"],
                "temp_unit": p["temperatureUnit"],
                "wind_speed": p["windSpeed"],
                "wind_direction": p["windDirection"],
                "description": p["shortForecast"],
                "detailed": p["detailedForecast"],
                "icon": p["icon"],
                "precip_chance": p.get("probabilityOfPrecipitation", {}).get("value"),
                "low_f": None,
            }
            # Try to grab paired night period
            if p["isDaytime"] and i + 1 < len(periods) and not periods[i+1]["isDaytime"]:
                night = periods[i + 1]
                day_entry["low_f"] = night["temperature"]
                day_entry["night_description"] = night["shortForecast"]
                i += 2
            else:
                i += 1
            days.append(day_entry)

        result = {"periods": days}
        cache.set("nws_daily", result, config.CACHE_TTL["forecast"])
        return result
    except Exception as e:
        log.error("NWS daily forecast failed: %s", e)
        return {"error": str(e)}


def get_alerts() -> dict:
    cached = cache.get("nws_alerts")
    if cached:
        return cached

    try:
        url = f"{config.NWS_BASE}/alerts/active?zone={config.NWS_ALERT_ZONE}"
        r = requests.get(url, headers=config.NWS_HEADERS, timeout=10)
        r.raise_for_status()
        features = r.json().get("features", [])

        alerts = []
        for f in features:
            p = f["properties"]
            alerts.append({
                "id": f["id"],
                "event": p.get("event", ""),
                "severity": p.get("severity", "Unknown"),
                "urgency": p.get("urgency", "Unknown"),
                "certainty": p.get("certainty", "Unknown"),
                "headline": p.get("headline", ""),
                "description": p.get("description", ""),
                "instruction": p.get("instruction", ""),
                "onset": p.get("onset", ""),
                "expires": p.get("expires", ""),
                "sent": p.get("sent", ""),
                "status": p.get("status", ""),
                "area": p.get("areaDesc", ""),
            })

        result = {"alerts": alerts, "count": len(alerts)}
        cache.set("nws_alerts", result, config.CACHE_TTL["alerts"])
        return result
    except Exception as e:
        log.error("NWS alerts failed: %s", e)
        return {"error": str(e), "alerts": [], "count": 0}


def get_precipitation() -> dict:
    """Return precipitation accumulation from recent observations."""
    cached = cache.get("nws_precip")
    if cached:
        return cached

    current = get_current_conditions()
    if "error" in current:
        return {"error": current["error"]}

    result = {
        "precip_1h_in": current.get("precip_1h_in"),
        "precip_6h_in": current.get("precip_6h_in"),
        "precip_24h_in": current.get("precip_24h_in"),
    }

    # Try to get 7-day precip from gridpoint data
    meta = _get_nws_meta()
    if meta:
        try:
            url = f"{config.NWS_BASE}/gridpoints/{meta['gridId']}/{meta['gridX']},{meta['gridY']}"
            r = requests.get(url, headers=config.NWS_HEADERS, timeout=10)
            r.raise_for_status()
            gdata = r.json()["properties"]
            qpf = gdata.get("quantitativePrecipitation", {}).get("values", [])
            if qpf:
                # Sum last 7 days worth (168 hours)
                total_mm = sum(v["value"] for v in qpf[-168:] if v["value"] is not None)
                result["precip_7day_in"] = round(total_mm * 0.0393701, 2)
        except Exception as e:
            log.warning("QPF gridpoint fetch failed: %s", e)

    cache.set("nws_precip", result, config.CACHE_TTL["current"])
    return result


def get_snow_depth() -> dict:
    cached = cache.get("nws_snow")
    if cached:
        return cached

    station = _get_observation_station()
    if not station:
        return {"error": "No station"}

    try:
        url = f"{config.NWS_BASE}/stations/{station}/observations/latest"
        r = requests.get(url, headers=config.NWS_HEADERS, timeout=10)
        r.raise_for_status()
        obs = r.json()["properties"]
        snow_mm = obs.get("snowDepth", {}).get("value")
        result = {
            "snow_depth_in": round(snow_mm * 0.0393701, 1) if snow_mm is not None else None,
            "snow_depth_cm": round(snow_mm / 10, 1) if snow_mm is not None else None,
            "has_snow": snow_mm is not None and snow_mm > 0,
        }
        cache.set("nws_snow", result, config.CACHE_TTL["current"])
        return result
    except Exception as e:
        log.error("NWS snow depth failed: %s", e)
        return {"error": str(e)}


def _deg_to_cardinal(deg) -> str:
    if deg is None:
        return ""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(deg / 22.5) % 16
    return directions[idx]
