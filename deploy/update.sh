#!/usr/bin/env bash
#
# Mise à jour du GEVIRO Dropbot déjà installé : git pull + deps + restart.
# Usage (en root) : sudo bash /opt/geviro-dropbot/deploy/update.sh
#
set -euo pipefail

APP_USER="${APP_USER:-dropbot}"
APP_DIR="${APP_DIR:-/opt/geviro-dropbot}"
SERVICE_NAME="${SERVICE_NAME:-geviro-dropbot}"

if [[ $EUID -ne 0 ]]; then
  echo "ERREUR: lancez avec sudo (root)." >&2
  exit 1
fi

echo "[1/3] git pull..."
sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only

echo "[2/3] dependances..."
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[3/3] redemarrage..."
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" | head -n 8 || true
echo "OK. Logs : journalctl -u ${SERVICE_NAME} -f"
