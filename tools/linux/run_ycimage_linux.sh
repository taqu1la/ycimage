#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${YCIMAGE_ENV_FILE:-/etc/ycimage/ycimage.env}"
PYTHON_BIN="${YCIMAGE_PYTHON_BIN:-python3}"
LOG_DIR="${YCIMAGE_LOG_DIR:-/var/log/ycimage}"

mkdir -p "$LOG_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-4178}"
YCIMAGE_DB_PATH="${YCIMAGE_DB_PATH:-$ROOT_DIR/backend/data/app.db}"

if [[ "${YCIMAGE_ENV:-}" == "production" ]]; then
  required_vars=(
    YCIMAGE_SECRET_KEY
    YCIMAGE_ADMIN_PASSWORD
    YCIMAGE_ALLOWED_ORIGINS
  )
  for var_name in "${required_vars[@]}"; do
    if [[ -z "${!var_name:-}" ]]; then
      echo "Missing required production setting: $var_name" >&2
      exit 1
    fi
  done
  if [[ "${YCIMAGE_ALLOWED_ORIGINS}" == *"http://"* || "${YCIMAGE_ALLOWED_ORIGINS}" == *"localhost"* || "${YCIMAGE_ALLOWED_ORIGINS}" == *"127.0.0.1"* ]]; then
    echo "YCIMAGE_ALLOWED_ORIGINS must contain only production HTTPS origins" >&2
    exit 1
  fi
  if [[ "${YCIMAGE_PAYMENT_PROVIDER:-manual}" == "mpay" ]]; then
    for var_name in MPAY_PID MPAY_KEY MPAY_NOTIFY_URL MPAY_RETURN_URL; do
      if [[ -z "${!var_name:-}" ]]; then
        echo "Missing required MPAY production setting: $var_name" >&2
        exit 1
      fi
    done
    if [[ "${MPAY_NOTIFY_URL}" != https://* || "${MPAY_RETURN_URL}" != https://* ]]; then
      echo "MPAY_NOTIFY_URL and MPAY_RETURN_URL must use HTTPS in production" >&2
      exit 1
    fi
  fi
fi

cd "$ROOT_DIR"
export PYTHONUNBUFFERED=1
exec "$PYTHON_BIN" -u backend/server.py --host "$APP_HOST" --port "$APP_PORT" --db "$YCIMAGE_DB_PATH" >>"$LOG_DIR/server.log" 2>&1
