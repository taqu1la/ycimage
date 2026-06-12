#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

APP_USER="${YCIMAGE_APP_USER:-ycimage}"
APP_GROUP="${YCIMAGE_APP_GROUP:-$APP_USER}"
APP_ROOT="${YCIMAGE_APP_ROOT:-$ROOT_DIR}"
CONF_DIR="${YCIMAGE_CONF_DIR:-/etc/ycimage}"
ENV_FILE="${YCIMAGE_ENV_FILE:-$CONF_DIR/ycimage.env}"
STATE_ROOT="${YCIMAGE_STATE_ROOT:-/var/lib/ycimage}"
LOG_DIR="${YCIMAGE_LOG_DIR:-/var/log/ycimage}"
SERVICE_FILE="/etc/systemd/system/ycimage.service"
NGINX_CONF_D="/etc/nginx/conf.d"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"

if [[ ! -f "$ENV_FILE" ]]; then
  install -d -o root -g root "$CONF_DIR"
  cp "$APP_ROOT/tools/linux/ycimage.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE. Fill in the real values, then rerun apply_release.sh." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-4178}"
YCIMAGE_PYTHON_BIN="${YCIMAGE_PYTHON_BIN:-python3}"
YCIMAGE_DB_PATH="${YCIMAGE_DB_PATH:-$STATE_ROOT/app.db}"
YCIMAGE_SEED_DB_PATH="${YCIMAGE_SEED_DB_PATH:-}"
YCIMAGE_SERVER_NAME="${YCIMAGE_SERVER_NAME:-_}"

render_template() {
  local template_path="$1"
  local output_path="$2"
  YCIMAGE_RENDER_ROOT_DIR="$APP_ROOT" \
  YCIMAGE_RENDER_RUN_USER="$APP_USER" \
  YCIMAGE_RENDER_RUN_GROUP="$APP_GROUP" \
  YCIMAGE_RENDER_SERVER_NAME="$YCIMAGE_SERVER_NAME" \
  python3 - "$template_path" "$output_path" <<'PY'
from pathlib import Path
import os
import sys

template = Path(sys.argv[1])
output = Path(sys.argv[2])
text = template.read_text(encoding="utf-8")
mapping = {
    "__ROOT_DIR__": os.environ["YCIMAGE_RENDER_ROOT_DIR"],
    "__RUN_USER__": os.environ["YCIMAGE_RENDER_RUN_USER"],
    "__RUN_GROUP__": os.environ["YCIMAGE_RENDER_RUN_GROUP"],
    "__SERVER_NAME__": os.environ["YCIMAGE_RENDER_SERVER_NAME"],
}
for old, new in mapping.items():
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
}

install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_ROOT"
install -d -o "$APP_USER" -g "$APP_GROUP" "$STATE_ROOT"
install -d -o "$APP_USER" -g "$APP_GROUP" "$LOG_DIR"
chown -R "$APP_USER:$APP_GROUP" "$APP_ROOT"
chown -R "$APP_USER:$APP_GROUP" "$STATE_ROOT"
chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"

if [[ ! -f "$YCIMAGE_DB_PATH" ]]; then
  if [[ -n "$YCIMAGE_SEED_DB_PATH" ]]; then
    if [[ ! -f "$YCIMAGE_SEED_DB_PATH" ]]; then
      echo "YCIMAGE_SEED_DB_PATH is set but not found: $YCIMAGE_SEED_DB_PATH" >&2
      exit 1
    fi
    install -D -m 640 "$YCIMAGE_SEED_DB_PATH" "$YCIMAGE_DB_PATH"
  else
    "$YCIMAGE_PYTHON_BIN" "$APP_ROOT/backend/scripts/init_db.py" --db "$YCIMAGE_DB_PATH"
  fi
  chown "$APP_USER:$APP_GROUP" "$YCIMAGE_DB_PATH"
fi

render_template "$APP_ROOT/tools/linux/ycimage.service.example" "$SERVICE_FILE"

if [[ -d "$NGINX_CONF_D" ]]; then
  render_template "$APP_ROOT/tools/linux/ycimage.nginx.conf.example" "$NGINX_CONF_D/ycimage.conf"
else
  install -d -o root -g root "$NGINX_SITES_AVAILABLE"
  install -d -o root -g root "$NGINX_SITES_ENABLED"
  render_template "$APP_ROOT/tools/linux/ycimage.nginx.conf.example" "$NGINX_SITES_AVAILABLE/ycimage.conf"
  ln -sfn "$NGINX_SITES_AVAILABLE/ycimage.conf" "$NGINX_SITES_ENABLED/ycimage.conf"
fi

systemctl daemon-reload
systemctl enable ycimage
systemctl restart ycimage

nginx -t
systemctl enable nginx
systemctl restart nginx

curl -fsS "http://${APP_HOST}:${APP_PORT}/api/health" >/dev/null
echo "YCImage is healthy at http://${APP_HOST}:${APP_PORT}/api/health"
