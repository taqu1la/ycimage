#!/usr/bin/env bash

set -euo pipefail

APP_USER="${YCIMAGE_APP_USER:-ycimage}"
APP_GROUP="${YCIMAGE_APP_GROUP:-$APP_USER}"
APP_HOME="${YCIMAGE_APP_HOME:-/opt/ycimage}"
APP_ROOT="${YCIMAGE_APP_ROOT:-$APP_HOME/current}"
STATE_ROOT="${YCIMAGE_STATE_ROOT:-/var/lib/ycimage}"
LOG_DIR="${YCIMAGE_LOG_DIR:-/var/log/ycimage}"
CONF_DIR="${YCIMAGE_CONF_DIR:-/etc/ycimage}"
BACKUP_DIR="${YCIMAGE_BACKUP_DIR:-$APP_HOME/backups}"

install_packages() {
  local missing=0
  local required_commands=(git rsync nginx curl python3 sqlite3)
  local cmd
  for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing=1
      break
    fi
  done
  if [[ "$missing" -eq 0 ]]; then
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    dnf install -y git rsync nginx curl python3 sqlite
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    yum install -y git rsync nginx curl python3 sqlite
    return
  fi
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y git rsync nginx curl python3 sqlite3
    return
  fi
  echo "Unsupported Linux distribution: cannot find dnf, yum, or apt-get." >&2
  exit 1
}

ensure_group() {
  if getent group "$APP_GROUP" >/dev/null 2>&1; then
    return
  fi
  groupadd --system "$APP_GROUP"
}

ensure_user() {
  if id "$APP_USER" >/dev/null 2>&1; then
    return
  fi
  useradd \
    --system \
    --gid "$APP_GROUP" \
    --home-dir "$APP_HOME" \
    --create-home \
    --shell /sbin/nologin \
    "$APP_USER"
}

install_packages
ensure_group
ensure_user

install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_HOME"
install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_ROOT"
install -d -o "$APP_USER" -g "$APP_GROUP" "$STATE_ROOT"
install -d -o "$APP_USER" -g "$APP_GROUP" "$LOG_DIR"
install -d -o "$APP_USER" -g "$APP_GROUP" "$BACKUP_DIR"
install -d -o root -g root "$CONF_DIR"
chmod 755 "$CONF_DIR"

echo "Bootstrap complete."
echo "APP_USER=$APP_USER"
echo "APP_ROOT=$APP_ROOT"
echo "STATE_ROOT=$STATE_ROOT"
