from __future__ import annotations

from app.utils.http import get_json


class NWSService:
    BASE = "https://api.weather.gov"

    def __init__(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon

    def get_points(self) -> dict:
        return get_json(f"{self.BASE}/points/{self.lat},{self.lon}")

    def get_forecast(self) -> dict:
        points = self.get_points()
        forecast_url = points["properties"]["forecast"]
        return get_json(forecast_url)

    def get_hourly(self) -> dict:
        points = self.get_points()
        hourly_url = points["properties"]["forecastHourly"]
        return get_json(hourly_url)

    def get_observations_latest(self) -> dict:
        points = self.get_points()
        station_url = points["properties"]["observationStations"]
        stations = get_json(station_url)
        station = stations["features"][0]["id"]
        return get_json(f"{station}/observations/latest")

    def get_alerts(self, county_zone: str) -> dict:
        return get_json(f"{self.BASE}/alerts/active", params={"zone": county_zone})
