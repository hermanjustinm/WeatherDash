#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/weatherdash}
SERVICE_NAME=${SERVICE_NAME:-weatherdash}
APP_USER=${APP_USER:-weatherdash}

sudo useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER" 2>/dev/null || true
sudo mkdir -p "$APP_DIR"
sudo rsync -a --delete ./ "$APP_DIR"/

cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi

sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
sudo cp deploy/weatherdash.service "/etc/systemd/system/${SERVICE_NAME}.service"
sudo sed -i "s#/opt/weatherdash#${APP_DIR}#g; s/weatherdash/${APP_USER}/g" "/etc/systemd/system/${SERVICE_NAME}.service"

sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.service"
sudo systemctl status "${SERVICE_NAME}.service" --no-pager
