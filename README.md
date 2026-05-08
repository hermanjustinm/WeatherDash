# WeatherDash (Olympia, WA)

WeatherDash is a Flask backend + dashboard frontend for weather/infrastructure monitoring.

## Important: GitHub Pages vs Flask
GitHub Pages can only host **static files**. It cannot run Flask/Python.

Use one of these patterns:
1. **Recommended:** Host Flask on your server (Linux/Windows) and access `/` directly.
2. **Optional split mode:** Host `static_site/` on GitHub Pages and point it to your running backend API by setting `window.WEATHERDASH_API_URL` in `static_site/index.html`.

## Features
- Live radar (RainViewer embed), severe alerts, hourly + 7-day forecast.
- Infrastructure modules: AQI, river levels, tides, traffic cams, health indicators.
- Graceful degradation with in-memory TTL caching + persisted snapshot fallback (`data/last_dashboard.json`).
- CORS-configurable API for remote/browser-hosted clients.

## Linux quick start
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env`
4. `python run.py`

## Windows quick start
### PowerShell
```powershell
./scripts/run_windows.ps1
```

### CMD
```bat
scripts\run_windows.bat
```

## Auto-run after reboot (Linux systemd)
```bash
./scripts/install_systemd.sh
```

## GitHub Pages static viewer mode
- Publish contents of `static_site/` to your Pages branch.
- Edit this line in `static_site/index.html` to your backend URL:
  - `window.WEATHERDASH_API_URL = "https://your-host-or-tunnel/api/dashboard";`
- In backend `.env`, set `CORS_ALLOWED_ORIGINS` to your Pages domain(s), e.g.:
  - `CORS_ALLOWED_ORIGINS=https://<user>.github.io,https://<org>.github.io`

## Environment
Copy `.env.example` to `.env` and set:
- `AIRNOW_API_KEY` (optional but needed for AQI values)
- `CORS_ALLOWED_ORIGINS` (for remote/static clients)
- location/zone values if you want a different city
