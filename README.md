# WeatherDash (Olympia, WA)

WeatherDash is a Flask backend + dashboard frontend for weather/infrastructure monitoring.

## Important: GitHub Pages vs Flask
GitHub Pages can only host **static files**. It cannot run Flask/Python.

Use one of these patterns:
1. **Recommended:** Host Flask on your server (Linux/Windows) and access `http://<server>:5000/` directly.
2. **Split mode:** Host static UI on GitHub Pages and point it to your Flask API URL.

---

## Windows setup (fix for `source is not recognized`)
`source` is a Linux/macOS command. On Windows use one of these:

### PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

### Command Prompt (cmd.exe)
```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Or run the helper scripts:
- PowerShell: `./scripts/run_windows.ps1`
- CMD: `scripts\run_windows.bat`

---

## GitHub Pages setup (fix for README showing instead of app)
If Pages is showing README, your site is publishing Markdown instead of dashboard HTML.

This repo now includes:
- root `index.html` that redirects to `static_site/index.html`
- `.nojekyll` to prevent Jekyll processing

### Recommended Pages settings
1. GitHub → **Settings** → **Pages**
2. Source: **Deploy from branch**
3. Branch: `main` (or your branch), folder: **/(root)**
4. Save and wait 1-2 minutes

Then your site should open the dashboard instead of README.

### Point static UI to your backend
Edit `static_site/index.html`:
```html
window.WEATHERDASH_API_URL = "https://your-host-or-cloudflare-tunnel/api/dashboard";
```

Set backend CORS in `.env`:
```env
CORS_ALLOWED_ORIGINS=https://<your-user>.github.io
```
(Use comma-separated values for multiple origins.)

---

## Linux quick start
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env`
4. `python run.py`

## Auto-run after reboot (Linux systemd)
```bash
./scripts/install_systemd.sh
```

## Features
- Live radar (RainViewer embed), severe alerts, hourly + 7-day forecast.
- Infrastructure modules: AQI, river levels, tides, traffic cams, health indicators.
- Graceful degradation with in-memory TTL caching + persisted snapshot fallback (`data/last_dashboard.json`).
- CORS-configurable API for remote/static clients.
