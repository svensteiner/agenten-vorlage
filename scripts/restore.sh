#!/usr/bin/env bash
# Restore a SQLite backup created by scripts/backup.sh onto AISTUDIO_DB.
# Optional sibling archive aistudio-…-uploads.tar.gz is restored into AISTUDIO_DATA/uploads.
# Encrypted files (*.enc) need AISTUDIO_BACKUP_PASS (openssl aes-256-cbc pbkdf2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${AISTUDIO_DATA:-$ROOT/data}"
DB="${AISTUDIO_DB:-$DATA/aistudio.db}"
SRC="${1:-}"
TMP_DB=""
TMP_UP=""

cleanup() {
  if [[ -n "${TMP_DB:-}" ]]; then
    rm -f "$TMP_DB"
  fi
  if [[ -n "${TMP_UP:-}" ]]; then
    rm -f "$TMP_UP"
  fi
}
trap cleanup EXIT

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "usage: $0 /path/to/aistudio-YYYYMMDDThhmmssZ.db[.enc]" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 fehlt — Restore abgebrochen, Live-Datenbank unangetastet." >&2
  exit 1
fi

WORK="$SRC"
if [[ "$SRC" == *.enc ]]; then
  if [[ -z "${AISTUDIO_BACKUP_PASS:-}" ]]; then
    echo "AISTUDIO_BACKUP_PASS fehlt — verschlüsselte Sicherung nicht gelesen." >&2
    exit 1
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl fehlt — verschlüsselte Sicherung nicht gelesen." >&2
    exit 1
  fi
  TMP_DB="$(mktemp)"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -pass env:AISTUDIO_BACKUP_PASS -in "$SRC" -out "$TMP_DB"
  WORK="$TMP_DB"
fi

CHECK="$(sqlite3 "$WORK" "PRAGMA integrity_check;" 2>/dev/null || true)"
if [[ "$CHECK" != "ok" ]]; then
  echo "Quelle beschädigt — nichts überschrieben." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -f "$DB" ]]; then
  cp "$DB" "$DB.before-restore-$STAMP"
fi

rm -f "$DB" "$DB-wal" "$DB-shm"
sqlite3 "$DB" ".restore '$WORK'"
AFTER="$(sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null || true)"
if [[ "$AFTER" != "ok" ]]; then
  echo "Restore beschädigt — vorherigen Stand zurücklegen." >&2
  if [[ -f "$DB.before-restore-$STAMP" ]]; then
    rm -f "$DB" "$DB-wal" "$DB-shm"
    sqlite3 "$DB" ".restore '$DB.before-restore-$STAMP'" 2>/dev/null \
      || cp "$DB.before-restore-$STAMP" "$DB"
  fi
  exit 1
fi
chmod 600 "$DB" 2>/dev/null || true

UPLOADS_SRC=""
if [[ "$SRC" == *.enc ]]; then
  UPLOADS_ENC="${SRC%.db.enc}-uploads.tar.gz.enc"
  if [[ -f "$UPLOADS_ENC" ]]; then
    TMP_UP="$(mktemp)"
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
      -pass env:AISTUDIO_BACKUP_PASS -in "$UPLOADS_ENC" -out "$TMP_UP"
    UPLOADS_SRC="$TMP_UP"
  fi
else
  CAND="${SRC%.db}-uploads.tar.gz"
  if [[ -f "$CAND" ]]; then
    UPLOADS_SRC="$CAND"
  fi
fi

if [[ -n "$UPLOADS_SRC" && -f "$UPLOADS_SRC" ]]; then
  unsafe=0
  while IFS= read -r member; do
    [[ -z "$member" ]] && continue
    case "$member" in
      /*) unsafe=1 ;;
      uploads|uploads/*) ;;
      *) unsafe=1 ;;
    esac
    if [[ "$member" == *..* ]]; then
      unsafe=1
    fi
  done < <(tar -tzf "$UPLOADS_SRC")
  if [[ "$unsafe" -ne 0 ]]; then
    echo "Upload-Archiv unsicher — Datenbank wiederhergestellt, Uploads übersprungen." >&2
  else
    if [[ -d "$DATA/uploads" ]]; then
      mv "$DATA/uploads" "$DATA/uploads.before-restore-$STAMP"
    fi
    tar -C "$DATA" -xzf "$UPLOADS_SRC"
  fi
fi

echo "wiederhergestellt: $DB"
