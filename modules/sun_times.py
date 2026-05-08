"""Sunrise/sunset calculation using NWS or formula-based approach."""
import math
import logging
from datetime import date, datetime, timedelta
import pytz
import config
from modules import cache

log = logging.getLogger(__name__)


def _solar_noon_and_day_length(lat: float, lon: float, dt: date) -> tuple[float, float]:
    """Returns (solar_noon_utc_hours, daylight_hours) using simplified NOAA algorithm."""
    day_of_year = dt.timetuple().tm_yday

    # Fractional year (radians)
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + 0.5)

    # Equation of time (minutes)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.04089 * math.sin(2 * gamma)
    )

    # Solar declination (radians)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    lat_rad = math.radians(lat)

    # Hour angle at sunrise/sunset
    cos_ha = (
        math.cos(math.radians(90.833)) / (math.cos(lat_rad) * math.cos(decl))
        - math.tan(lat_rad) * math.tan(decl)
    )
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha = math.degrees(math.acos(cos_ha))

    # Solar noon (UTC minutes)
    solar_noon_utc_min = 720 - 4 * lon - eqtime
    sunrise_utc_min = solar_noon_utc_min - ha * 4
    sunset_utc_min = solar_noon_utc_min + ha * 4

    return sunrise_utc_min / 60.0, sunset_utc_min / 60.0


def _utc_hour_to_local(utc_hour: float, dt: date, tz: pytz.BaseTzInfo) -> datetime:
    h = int(utc_hour)
    m = int((utc_hour - h) * 60)
    s = int(((utc_hour - h) * 60 - m) * 60)
    utc_dt = datetime(dt.year, dt.month, dt.day, h % 24, m, s, tzinfo=pytz.utc)
    return utc_dt.astimezone(tz)


def get_sun_times() -> dict:
    cached = cache.get("sun_times")
    if cached:
        return cached

    tz = pytz.timezone(config.TIMEZONE)
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)

    sunrise_utc, sunset_utc = _solar_noon_and_day_length(config.LAT, config.LON, today)
    sunrise_local = _utc_hour_to_local(sunrise_utc, today, tz)
    sunset_local = _utc_hour_to_local(sunset_utc, today, tz)

    # Tomorrow's for "next sunrise"
    sunrise_utc_tmr, _ = _solar_noon_and_day_length(config.LAT, config.LON, tomorrow)
    next_sunrise_local = _utc_hour_to_local(sunrise_utc_tmr, tomorrow, tz)

    now = datetime.now(tz)
    daylight_seconds = (sunset_local - sunrise_local).total_seconds()

    if now < sunrise_local:
        phase = "night_before"
        next_event = sunrise_local
        next_event_label = "Sunrise"
    elif now < sunset_local:
        phase = "day"
        next_event = sunset_local
        next_event_label = "Sunset"
    else:
        phase = "night_after"
        next_event = next_sunrise_local
        next_event_label = "Sunrise"

    # Day progress percentage (0-100)
    if phase == "day":
        elapsed = (now - sunrise_local).total_seconds()
        day_progress = min(100.0, elapsed / daylight_seconds * 100)
    elif phase == "night_before":
        day_progress = 0.0
    else:
        day_progress = 100.0

    result = {
        "sunrise": sunrise_local.strftime("%I:%M %p"),
        "sunset": sunset_local.strftime("%I:%M %p"),
        "sunrise_iso": sunrise_local.isoformat(),
        "sunset_iso": sunset_local.isoformat(),
        "daylight_hours": round(daylight_seconds / 3600, 2),
        "phase": phase,
        "day_progress": round(day_progress, 1),
        "next_event": next_event.strftime("%I:%M %p"),
        "next_event_label": next_event_label,
        "date": str(today),
    }
    cache.set("sun_times", result, config.CACHE_TTL["sun"])
    return result
