from __future__ import annotations

import requests

DEFAULT_HEADERS = {
    "User-Agent": "WeatherDash/1.0 (local-home-server; contact: admin@localhost)",
    "Accept": "application/geo+json, application/json",
}


def get_json(url: str, params: dict | None = None, timeout: int = 15) -> dict | list:
    response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()
