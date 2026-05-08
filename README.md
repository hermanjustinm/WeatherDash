# WeatherDash

A self-hosted weather and infrastructure dashboard for **Olympia, WA** (or any location you configure). Dark-themed, real-time, built on Flask + vanilla JS.

![Modules: Radar, Forecast, Alerts, Wind, AQI, Tides, Rivers, Traffic Cams, Power Outages]

---

## Features

| Module | Data Source | Refresh |
|--------|-------------|---------|
| Live Radar (animated) | RainViewer API | 5 min |
| Current Conditions | NWS Observations | 10 min |
| Hourly + 7-Day Forecast | NWS API | 30 min |
| Severe Weather Alerts | NWS Alerts (Thurston Co.) | 2 min |
| Wind Speed/Direction/Gusts | NWS | 10 min |
| Air Quality Index | AirNow API | 30 min |
| Sunrise / Sunset | Calculated (NOAA algorithm) | 12 hr |
| Precipitation Accumulation | NWS | 10 min |
| Snow Depth | NWS (shown when > 0") | 30 min |
| River Levels + Flood Stage | USGS Water Services | 15 min |
| Flood Warnings | NWS Alerts | 2 min |
| Tide Chart | NOAA Tides & Currents | 30 min |
| Power Outage Map | PowerOutage.us (iframe) | N/A |
| Traffic Cameras (6 cams) | WA DOT | 60 sec |
| Clock / Date | Browser | 1 sec |
| Data Source Health | All APIs | 60 sec |

---

## Quick Start

### 1. Clone & set up virtualenv

```bash
git clone <repo-url> WeatherDash
cd WeatherDash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env  # or your editor of choice
```

Minimum required: nothing (all public APIs work without keys).

**Optional but recommended:**
- `AIRNOW_API_KEY` — [free key from AirNow](https://docs.airnowapi.org/account/request/), enables AQI module

### 3. Run

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## Configuration

Edit `.env` (copy from `.env.example`):

```env
# Location
LAT=47.0379
LON=-122.9007
LOCATION_NAME=Olympia, WA
TIMEZONE=America/Los_Angeles

# Optional: AirNow API key
AIRNOW_API_KEY=your_key_here

# Flask settings
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
```

### Changing location

Update `LAT`, `LON`, `LOCATION_NAME`, and `TIMEZONE` in `.env`. Also update:
- `USGS_GAUGES` in `config.py` with USGS site numbers near you
- `FLOOD_STAGES` in `config.py` with NWS flood stage data for your gauges
- `NOAA_TIDE_STATION` in `config.py` — find yours at [tidesandcurrents.noaa.gov](https://tidesandcurrents.noaa.gov)
- `NWS_ALERT_ZONE` and `NWS_FORECAST_ZONE` in `config.py` — look up at [alerts.weather.gov](https://alerts.weather.gov)
- `WSDOT_CAMERA_IDS` in `config.py` if you are not in Washington State (or remove/disable the cameras module)

---

## Running in Production (Home Server)

### Using Gunicorn

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### systemd service

Create `/etc/systemd/system/weatherdash.service`:

```ini
[Unit]
Description=WeatherDash
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/WeatherDash
EnvironmentFile=/path/to/WeatherDash/.env
ExecStart=/path/to/WeatherDash/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable weatherdash
sudo systemctl start weatherdash
```

### Cloudflare Tunnel (optional, remote access)

1. Install `cloudflared`: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
2. Log in: `cloudflared tunnel login`
3. Create tunnel: `cloudflared tunnel create weatherdash`
4. Configure `~/.cloudflared/config.yml`:

```yaml
tunnel: <tunnel-id>
credentials-file: /home/user/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: weather.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
```

5. Run: `cloudflared tunnel run weatherdash`

Or add it as a systemd service alongside WeatherDash.

---

## API Keys

| Service | Key Required | Where to Get |
|---------|-------------|--------------|
| National Weather Service | No | — |
| USGS Water Services | No | — |
| NOAA Tides & Currents | No | — |
| RainViewer | No | — |
| WA DOT (cameras) | No (public feed) | — |
| AirNow (AQI) | Yes (free) | [docs.airnowapi.org/account/request](https://docs.airnowapi.org/account/request/) |

---

## Project Structure

```
WeatherDash/
├── app.py              # Flask app, all API endpoints
├── config.py           # All configuration (reads .env)
├── requirements.txt
├── .env.example        # Copy to .env
├── modules/
│   ├── cache.py        # Thread-safe TTL in-memory cache
│   ├── nws.py          # National Weather Service API
│   ├── usgs.py         # USGS river gauge data
│   ├── noaa_tides.py   # NOAA tides & currents
│   ├── airnow.py       # AirNow AQI
│   ├── wadot.py        # WA DOT traffic cameras
│   └── sun_times.py    # Sunrise/sunset calculator
├── templates/
│   └── index.html      # Single-page dashboard
└── static/
    ├── css/style.css   # Dark theme dashboard styles
    └── js/dashboard.js # Frontend polling & rendering
```

---

## Customizing Traffic Cameras

The `WSDOT_CAMERA_IDS` list in `config.py` contains hardcoded camera IDs. WSDOT camera images are available at:

```
https://images.wsdot.wa.gov/nw/005vc{camera_id:05d}.jpg
```

Browse available cameras at [wsdot.wa.gov/travel/real-time-traffic](https://wsdot.wa.gov/travel/real-time-traffic/cameras) to find IDs near you.

---

## Troubleshooting

**NWS data not loading:**
- NWS API can be slow (~2-3s). Check `/api/health` for status.
- NWS has maintenance windows; check https://www.weather.gov for outages.

**AQI shows "configure API key":**
- Add `AIRNOW_API_KEY` to your `.env` file.

**Camera images are broken:**
- Camera IDs in `config.py` may have changed. Check the WSDOT camera portal for current IDs.
- Some cameras go offline seasonally.

**Tides show no data:**
- Verify `NOAA_TIDE_STATION` in `config.py`. Olympia's station is `9446484`.
- Station `9446484` is Olympia; nearest salt water is Budd Inlet.

**Power outage iframe not loading:**
- PowerOutage.us may block iframes occasionally. The module will display a blank frame in that case.

---

## License

MIT
