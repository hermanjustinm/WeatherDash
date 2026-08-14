$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) {
  py -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}
python run.py
