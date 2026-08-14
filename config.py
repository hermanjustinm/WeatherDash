from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "5000"))
    latitude: float = float(os.getenv("LATITUDE", "47.0379"))
    longitude: float = float(os.getenv("LONGITUDE", "-122.9007"))
    timezone: str = os.getenv("TIMEZONE", "America/Los_Angeles")
    county_zone: str = os.getenv("COUNTY_ZONE", "WAC067")
    airnow_api_key: str | None = os.getenv("AIRNOW_API_KEY")
    lightning_embed_url: str = os.getenv("LIGHTNING_EMBED_URL", "https://www.lightningmaps.org")
    power_outage_embed_url: str = os.getenv(
        "POWER_OUTAGE_EMBED_URL", "https://poweroutage.us/area/state/washington"
    )
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")


settings = Settings()
