#!/usr/bin/env bash
set -euo pipefail

APP_NAME="mas004-vj6530-zbc-bridge"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG_DIR="/etc/mas004_vj6530_zbc_bridge"
CFG_FILE="$CFG_DIR/config.json"
SERVICE_DST="/etc/systemd/system/${APP_NAME}.service"

sudo mkdir -p "$CFG_DIR"
if [ ! -f "$CFG_FILE" ]; then
  sudo cp "$ROOT_DIR/scripts/default_config.json" "$CFG_FILE"
fi

sudo cp "$ROOT_DIR/systemd/${APP_NAME}.service" "$SERVICE_DST"
sudo systemctl daemon-reload
sudo systemctl enable --now "$APP_NAME"
sudo systemctl status "$APP_NAME" --no-pager
