from __future__ import annotations

from app.utils.http import get_json


class WADOTService:
    BASE = "https://data.wsdot.wa.gov/mobile/HighwayCameras.js"

    def get_cameras(self) -> list:
        data = get_json(self.BASE)
        # Olympia-ish fallback filtering by route labels / vicinity names.
        cams = [
            c
            for c in data
            if any(k in (c.get("Title", "") + c.get("Region", "")) for k in ["Olympia", "Lacey", "Tumwater", "I-5"])
        ]
        return cams[:6]
