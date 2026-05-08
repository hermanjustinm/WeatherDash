from __future__ import annotations

from app.utils.http import get_json


class USGSService:
    BASE = "https://waterservices.usgs.gov/nwis/iv/"

    def get_river_levels(self) -> dict:
        params = {
            "format": "json",
            "sites": "12079000,12080010",  # Deschutes + nearby gauge
            "parameterCd": "00065,00060",
            "siteStatus": "all",
        }
        return get_json(self.BASE, params=params)
