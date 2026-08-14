from __future__ import annotations

from config import settings
from app.utils.http import get_json


class AirQualityService:
    BASE = "https://www.airnowapi.org/aq/observation/latLong/current/"

    def get_current(self, lat: float, lon: float) -> list:
        if not settings.airnow_api_key:
            return []
        return get_json(
            self.BASE,
            params={
                "format": "application/json",
                "latitude": lat,
                "longitude": lon,
                "distance": 25,
                "API_KEY": settings.airnow_api_key,
            },
        )
