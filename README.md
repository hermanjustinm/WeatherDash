# WeatherDash (Olympia, WA)

Self-hosted Flask weather/infrastructure dashboard for Olympia, Washington.

## Features
- Live radar (RainViewer embed) with 5-minute refresh.
- NWS current conditions, hourly, and 7-day forecast.
- NWS severe alerts for Thurston County.
- Wind, AQI (AirNow), river levels (USGS), tides (NOAA), traffic cams (WADOT), source health checks.
- Dark, responsive dashboard layout for desktop/mobile.
- Cached backend responses to reduce rate limits.
- Persistent fallback snapshot saved at `data/last_dashboard.json` for API outage/reboot resilience.

## Quick start (manual)
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and optionally add `AIRNOW_API_KEY`.
4. `python run.py`
5. Open `http://<server-ip>:5000`

## Auto-run after reboot (systemd)
Use the provided install script to set up a dedicated service user and enable startup on boot:

```bash
./scripts/install_systemd.sh
```

This will:
- install app into `/opt/weatherdash` (override with `APP_DIR=/path`)
- create service account `weatherdash` (override with `APP_USER=user`)
- create/enable `weatherdash.service`
- automatically restart on failure and reboot

Useful commands:
- `sudo systemctl status weatherdash`
- `sudo journalctl -u weatherdash -f`
- `sudo systemctl restart weatherdash`

## Cloudflare Tunnel (optional)
- Install `cloudflared` on your server.
- Run: `cloudflared tunnel --url http://localhost:5000`
- For persistent tunnel, create a named tunnel and DNS route per Cloudflare docs.

## Project layout
- `app/services/`: integrations by provider.
- `app/static/`: CSS/JS frontend assets.
- `app/templates/`: Jinja templates.
- `config.py`: env-driven settings.
- `deploy/weatherdash.service`: systemd unit template.
- `scripts/install_systemd.sh`: one-command installation + autostart setup.

## Notes
- Some modules (lightning, snow depth, precipitation accumulation, flood-only filters) can be extended further depending on preferred data provider and local gauge mapping.
