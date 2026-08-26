#!/usr/bin/env bash
# Restore a SQLite backup created by scripts/backup.sh onto AISTUDIO_DB.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${AISTUDIO_DATA:-$ROOT/data}"
DB="${AISTUDIO_DB:-$DATA/aistudio.db}"
SRC="${1:-}"

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "usage: $0 /path/to/aistudio-YYYYMMDDThhmmssZ.db" >&2
  exit 1
fi

mkdir -p "$(dirname "$DB")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -f "$DB" ]]; then
  cp "$DB" "$DB.before-restore-$STAMP"
fi

if command -v sqlite3 >/dev/null 2>&1; then
  rm -f "$DB" "$DB-wal" "$DB-shm"
  sqlite3 "$DB" ".restore '$SRC'"
else
  cp "$SRC" "$DB"
fi
echo "wiederhergestellt: $DB"
