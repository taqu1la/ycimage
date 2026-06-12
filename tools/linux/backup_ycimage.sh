#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${YCIMAGE_ENV_FILE:-/etc/ycimage/ycimage.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

BACKUP_DIR="${YCIMAGE_BACKUP_DIR:-/opt/ycimage/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB_PATH="${YCIMAGE_DB_PATH:-/var/lib/ycimage/app.db}"
ASSET_ROOT="${YCIMAGE_ASSET_ROOT:-$ROOT_DIR/webapp/assets}"
SQLITE_BIN="${SQLITE_BIN:-sqlite3}"
RETENTION_DAYS="${YCIMAGE_BACKUP_RETENTION_DAYS:-7}"
ACTION="${1:-backup}"
RESTORE_ARCHIVE="${2:-}"

usage() {
  cat <<'EOF'
Usage:
  backup_ycimage.sh backup
  backup_ycimage.sh restore /opt/ycimage/backups/db-YYYYmmdd-HHMMSS.tar.gz

The backup command uses SQLite's online backup API, so WAL-mode databases are
captured consistently without copying a stale main .db file by itself.
EOF
}

require_sqlite() {
  if ! command -v "$SQLITE_BIN" >/dev/null 2>&1; then
    echo "sqlite3 is required. Set SQLITE_BIN or install sqlite3." >&2
    exit 1
  fi
}

backup() {
  mkdir -p "$BACKUP_DIR"

  if [[ -f "$DB_PATH" ]]; then
    require_sqlite
    local work_dir="$BACKUP_DIR/db-$STAMP"
    local db_backup="$work_dir/app.db"
    if [[ "$db_backup" == *"'"* ]]; then
      echo "Backup path must not contain single quotes: $db_backup" >&2
      exit 1
    fi
    install -d -m 700 "$work_dir"
    "$SQLITE_BIN" "$DB_PATH" ".backup '$db_backup'"
    "$SQLITE_BIN" "$db_backup" "PRAGMA integrity_check;" | grep -qx "ok"
    tar -czf "$BACKUP_DIR/db-$STAMP.tar.gz" -C "$work_dir" app.db
    rm -rf "$work_dir"
  fi

  if [[ -d "$ASSET_ROOT" ]]; then
    tar -czf "$BACKUP_DIR/assets-$STAMP.tar.gz" -C "$ROOT_DIR/webapp" assets
  fi

  find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete
  echo "Backup completed: $BACKUP_DIR"
}

restore() {
  if [[ -z "$RESTORE_ARCHIVE" ]]; then
    usage >&2
    exit 1
  fi
  if [[ ! -f "$RESTORE_ARCHIVE" ]]; then
    echo "Restore archive not found: $RESTORE_ARCHIVE" >&2
    exit 1
  fi
  require_sqlite
  local restore_dir
  restore_dir="$(mktemp -d)"
  trap 'rm -rf "$restore_dir"' EXIT
  tar -xzf "$RESTORE_ARCHIVE" -C "$restore_dir"
  if [[ ! -f "$restore_dir/app.db" ]]; then
    echo "Archive does not contain app.db: $RESTORE_ARCHIVE" >&2
    exit 1
  fi
  "$SQLITE_BIN" "$restore_dir/app.db" "PRAGMA integrity_check;" | grep -qx "ok"
  install -D -m 640 "$restore_dir/app.db" "$DB_PATH"
  rm -f "$DB_PATH-wal" "$DB_PATH-shm"
  echo "Database restored to $DB_PATH"
}

case "$ACTION" in
  backup)
    backup
    ;;
  restore)
    restore
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
