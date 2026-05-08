"""WeatherDash — Flask application entry point."""
import logging
import time
import requests
from datetime import datetime

from flask import Flask, jsonify, render_template, Response, abort
import pytz

import config
from modules import cache
from modules import nws, usgs, noaa_tides, airnow, wadot, sun_times

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ── Helper ──────────────────────────────────────────────────────────────────

def _api_response(data: dict, cache_key: str = None):
    resp = jsonify(data)
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Last-Updated"] = datetime.utcnow().isoformat() + "Z"
    if cache_key:
        remaining = cache.ttl_remaining(cache_key)
        if remaining is not None:
            resp.headers["X-Cache-TTL-Remaining"] = str(int(remaining))
    return resp


# ── Frontend ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    return render_template(
        "index.html",
        location_name=config.LOCATION_NAME,
        lat=config.LAT,
        lon=config.LON,
        now=now,
        airnow_configured=bool(config.AIRNOW_API_KEY),
    )


# ── API: Current conditions ──────────────────────────────────────────────────

@app.route("/api/current")
def api_current():
    data = nws.get_current_conditions()
    return _api_response(data, "nws_current")


@app.route("/api/wind")
def api_wind():
    data = nws.get_current_conditions()
    if "error" in data:
        return _api_response(data)
    wind = {
        "speed_mph": data.get("wind_speed_mph"),
        "gust_mph": data.get("wind_gust_mph"),
        "direction_deg": data.get("wind_direction_deg"),
        "direction_cardinal": data.get("wind_direction_cardinal"),
    }
    return _api_response(wind, "nws_current")


# ── API: Forecast ────────────────────────────────────────────────────────────

@app.route("/api/forecast/hourly")
def api_forecast_hourly():
    data = nws.get_hourly_forecast()
    return _api_response(data, "nws_hourly")


@app.route("/api/forecast/daily")
def api_forecast_daily():
    data = nws.get_daily_forecast()
    return _api_response(data, "nws_daily")


# ── API: Alerts ──────────────────────────────────────────────────────────────

@app.route("/api/alerts")
def api_alerts():
    data = nws.get_alerts()
    return _api_response(data, "nws_alerts")


# ── API: Precipitation & Snow ────────────────────────────────────────────────

@app.route("/api/precipitation")
def api_precipitation():
    data = nws.get_precipitation()
    return _api_response(data, "nws_precip")


@app.route("/api/snow")
def api_snow():
    data = nws.get_snow_depth()
    return _api_response(data, "nws_snow")


# ── API: Sun times ───────────────────────────────────────────────────────────

@app.route("/api/sun")
def api_sun():
    data = sun_times.get_sun_times()
    return _api_response(data, "sun_times")


# ── API: AQI ─────────────────────────────────────────────────────────────────

@app.route("/api/aqi")
def api_aqi():
    data = airnow.get_aqi()
    return _api_response(data, "airnow_aqi")


# ── API: Rivers ──────────────────────────────────────────────────────────────

@app.route("/api/rivers")
def api_rivers():
    data = usgs.get_river_levels()
    return _api_response(data, "usgs_rivers")


# ── API: Tides ───────────────────────────────────────────────────────────────

@app.route("/api/tides")
def api_tides():
    data = noaa_tides.get_tides()
    return _api_response(data, "noaa_tides")


# ── API: Traffic Cameras ─────────────────────────────────────────────────────

@app.route("/api/cameras")
def api_cameras():
    data = wadot.get_cameras()
    return _api_response(data, "wadot_cameras")


@app.route("/api/cameras/<int:camera_id>/image")
def api_camera_image(camera_id: int):
    """Proxy camera image to avoid CORS/mixed-content issues."""
    valid_ids = {c["id"] for c in config.WSDOT_CAMERA_IDS}
    if camera_id not in valid_ids:
        abort(404)
    try:
        image_data = wadot.fetch_camera_image(camera_id)
        return Response(image_data, mimetype="image/jpeg",
                        headers={"Cache-Control": "max-age=60"})
    except Exception as e:
        log.warning("Camera proxy failed for %s: %s", camera_id, e)
        abort(502)


# ── API: Radar times (RainViewer) ────────────────────────────────────────────

@app.route("/api/radar/times")
def api_radar_times():
    cached = cache.get("rainviewer_times")
    if cached:
        return _api_response(cached, "rainviewer_times")

    try:
        r = requests.get(
            "https://api.rainviewer.com/public/weather-maps.json",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        cache.set("rainviewer_times", data, config.CACHE_TTL["radar"])
        return _api_response(data, "rainviewer_times")
    except Exception as e:
        log.error("RainViewer times fetch failed: %s", e)
        return _api_response({"error": str(e)})


# ── API: Health ──────────────────────────────────────────────────────────────

@app.route("/api/health")
def api_health():
    tz = pytz.timezone(config.TIMEZONE)
    now_ts = datetime.now(tz).isoformat()

    def check(name: str, cache_key: str, fetch_fn) -> dict:
        remaining = cache.ttl_remaining(cache_key)
        if remaining is not None and remaining > 0:
            return {
                "name": name,
                "status": "ok",
                "cached": True,
                "ttl_remaining": int(remaining),
                "last_check": now_ts,
            }
        # Do a fresh check
        t0 = time.time()
        try:
            result = fetch_fn()
            elapsed = round((time.time() - t0) * 1000)
            has_error = isinstance(result, dict) and "error" in result
            return {
                "name": name,
                "status": "error" if has_error else "ok",
                "latency_ms": elapsed,
                "cached": False,
                "last_check": now_ts,
                "detail": result.get("error") if has_error else None,
            }
        except Exception as e:
            return {
                "name": name,
                "status": "error",
                "latency_ms": round((time.time() - t0) * 1000),
                "cached": False,
                "last_check": now_ts,
                "detail": str(e),
            }

    services = [
        check("NWS Current",   "nws_current",    nws.get_current_conditions),
        check("NWS Forecast",  "nws_daily",       nws.get_daily_forecast),
        check("NWS Alerts",    "nws_alerts",      nws.get_alerts),
        check("USGS Rivers",   "usgs_rivers",     usgs.get_river_levels),
        check("NOAA Tides",    "noaa_tides",      noaa_tides.get_tides),
        check("AirNow AQI",    "airnow_aqi",      airnow.get_aqi),
        check("WA DOT Cams",   "wadot_cameras",   wadot.get_cameras),
        check("Sun Times",     "sun_times",       sun_times.get_sun_times),
    ]

    overall = "ok" if all(s["status"] == "ok" for s in services) else "degraded"
    return _api_response({"status": overall, "services": services, "timestamp": now_ts})


# ── API: Config (safe subset) ────────────────────────────────────────────────

@app.route("/api/config")
def api_config():
    return _api_response({
        "location_name": config.LOCATION_NAME,
        "lat": config.LAT,
        "lon": config.LON,
        "timezone": config.TIMEZONE,
        "airnow_configured": bool(config.AIRNOW_API_KEY),
        "refresh_intervals": {
            "radar_ms":        config.CACHE_TTL["radar"] * 1000,
            "current_ms":      config.CACHE_TTL["current"] * 1000,
            "forecast_ms":     config.CACHE_TTL["forecast"] * 1000,
            "alerts_ms":       config.CACHE_TTL["alerts"] * 1000,
            "aqi_ms":          config.CACHE_TTL["aqi"] * 1000,
            "river_ms":        config.CACHE_TTL["river"] * 1000,
            "tides_ms":        config.CACHE_TTL["tides"] * 1000,
            "cameras_ms":      config.CACHE_TTL["cameras"] * 1000,
        },
    })


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
