from __future__ import annotations

from datetime import datetime

from app.utils.http import get_json


class NOAAService:
    BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def get_tides(self) -> dict:
        today = datetime.utcnow().strftime("%Y%m%d")
        params = {
            "product": "predictions",
            "application": "weatherdash",
            "date": "today",
            "datum": "MLLW",
            "station": "9446969",  # Olympia
            "time_zone": "lst_ldt",
            "units": "english",
            "interval": "hilo",
            "format": "json",
            "begin_date": today,
            "end_date": today,
        }
        return get_json(self.BASE, params=params)
