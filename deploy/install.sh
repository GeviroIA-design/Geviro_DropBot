#!/usr/bin/env bash
#
# Installation / mise en service du GEVIRO Dropbot sur un VPS Ubuntu/Debian.
# Idempotent : peut être relancé sans risque.
#
# Pré-requis : le repo est DÉJÀ cloné dans $APP_DIR (voir deploy/DEPLOY.md),
# OU vous fournissez REPO_URL pour que le script le clone.
#
# Usage (en root) :
#   sudo bash /opt/geviro-dropbot/deploy/install.sh
# Variables surchargeables :
#   APP_USER=dropbot APP_DIR=/opt/geviro-dropbot REPO_URL=git@github.com:user/repo.git
#
set -euo pipefail

APP_USER="${APP_USER:-dropbot}"
APP_DIR="${APP_DIR:-/opt/geviro-dropbot}"
REPO_URL="${REPO_URL:-https://github.com/GeviroIA-design/Geviro_DropBot.git}"
SERVICE_NAME="${SERVICE_NAME:-geviro-dropbot}"

if [[ $EUID -ne 0 ]]; then
  echo "ERREUR: lancez ce script avec sudo (root)." >&2
  exit 1
fi

echo "[1/7] Paquets systeme (python3, venv, git)..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "[2/7] Utilisateur de service '$APP_USER'..."
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

echo "[3/7] Code source dans $APP_DIR..."
if [[ -d "$APP_DIR/.git" ]]; then
  echo "  repo present -> git pull"
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
elif [[ -n "$REPO_URL" ]]; then
  echo "  clone depuis $REPO_URL"
  mkdir -p "$APP_DIR"
  chown "$APP_USER:$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
else
  echo "ERREUR: $APP_DIR n'est pas un repo git et REPO_URL est vide." >&2
  echo "Clonez d'abord le repo (voir deploy/DEPLOY.md) ou exportez REPO_URL." >&2
  exit 1
fi

echo "[4/7] Environnement Python (venv + dependances)..."
if [[ ! -d "$APP_DIR/.venv" ]]; then
  sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
fi
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[5/7] Repertoires runtime + fichier .env..."
sudo -u "$APP_USER" mkdir -p "$APP_DIR/data" "$APP_DIR/logs" "$APP_DIR/outputs"
if [[ ! -f "$APP_DIR/.env" ]]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "  >> .env cree depuis le modele."
fi

echo "[6/7] Service systemd ($SERVICE_NAME)..."
sed -e "s#/opt/geviro-dropbot#${APP_DIR}#g" \
    -e "s/^User=.*/User=${APP_USER}/" \
    -e "s/^Group=.*/Group=${APP_USER}/" \
    "$APP_DIR/deploy/geviro-dropbot.service" > "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true

echo "[7/7] Demarrage..."
if grep -Eq '^TELEGRAM_BOT_TOKEN=.+' "$APP_DIR/.env"; then
  systemctl restart "$SERVICE_NAME"
  sleep 2
  systemctl --no-pager --full status "$SERVICE_NAME" | head -n 12 || true
  echo ""
  echo "OK. Service demarre. Logs en direct : journalctl -u ${SERVICE_NAME} -f"
else
  echo ""
  echo ">> ATTENTION : TELEGRAM_BOT_TOKEN est vide dans $APP_DIR/.env"
  echo ">> 1) Editez le fichier :   sudo -u ${APP_USER} nano ${APP_DIR}/.env"
  echo ">>    (renseignez TELEGRAM_BOT_TOKEN et TELEGRAM_ADMIN_IDS)"
  echo ">> 2) Demarrez :            sudo systemctl start ${SERVICE_NAME}"
  echo ">> 3) Logs :                journalctl -u ${SERVICE_NAME} -f"
fi
