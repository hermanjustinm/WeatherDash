from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, jsonify, render_template

from config import settings
from app.services.air_quality import AirQualityService
from app.services.hydrology import USGSService
from app.services.tides import NOAAService
from app.services.wadot import WADOTService
from app.services.weather import NWSService
from app.utils.cache import TTLCacheStore


cache = TTLCacheStore()


def create_app() -> Flask:
    app = Flask(__name__)

    nws = NWSService(settings.latitude, settings.longitude)
    aqi = AirQualityService()
    usgs = USGSService()
    noaa = NOAAService()
    wadot = WADOTService()

    @app.route("/")
    def index():
        return render_template("index.html", settings=settings)

    @app.route("/api/dashboard")
    def dashboard_data():
        health = {}

        def wrap(name: str, ttl: int, fn):
            try:
                res = cache.get_or_set(name, ttl, fn)
                health[name] = {"status": "ok", "last_success": datetime.fromtimestamp(res.fetched_at, tz=timezone.utc).isoformat()}
                return res.data
            except Exception as exc:  # graceful degradation
                health[name] = {"status": "down", "error": str(exc)}
                return None

        data = {
            "forecast": wrap("forecast", 1800, nws.get_forecast),
            "hourly": wrap("hourly", 1800, nws.get_hourly),
            "observations": wrap("obs", 600, nws.get_observations_latest),
            "alerts": wrap("alerts", 120, lambda: nws.get_alerts(settings.county_zone)),
            "air_quality": wrap("aqi", 1800, lambda: aqi.get_current(settings.latitude, settings.longitude)),
            "river_levels": wrap("river", 900, usgs.get_river_levels),
            "tides": wrap("tides", 900, noaa.get_tides),
            "traffic_cams": wrap("cams", 60, wadot.get_cameras),
            "meta": {
                "radar_refresh_seconds": 300,
                "power_refresh_seconds": 300,
                "health_refresh_seconds": 60,
            },
            "health": health,
        }
        return jsonify(data)

    return app
