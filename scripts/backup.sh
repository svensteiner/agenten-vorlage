#!/usr/bin/env bash
# SQLite-Sicherung der Produkt-Datenbank (WAL-sicher, wenn sqlite3 vorhanden)
# plus Uploads unter AISTUDIO_DATA/uploads.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${AISTUDIO_DATA:-$ROOT/data}"
DB="${AISTUDIO_DB:-$DATA/aistudio.db}"
DEST="${1:-$DATA/backups}"

if [[ ! -f "$DB" ]]; then
  echo "Keine Datenbank unter $DB" >&2
  exit 1
fi

mkdir -p "$DEST"
if command -v df >/dev/null 2>&1; then
  FREE_KB="$(df -Pk "$DEST" | awk 'NR==2 {print $4}')"
  if [[ -n "$FREE_KB" && "$FREE_KB" -lt 102400 ]]; then
    echo "Zu wenig Speicher für Sicherung (<100 MB frei)." >&2
    exit 1
  fi
fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$DEST/aistudio-$STAMP.db"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" ".backup '$OUT'"
  CHECK="$(sqlite3 "$OUT" "PRAGMA integrity_check;" 2>/dev/null || true)"
  if [[ "$CHECK" != "ok" ]]; then
    echo "Sicherung beschädigt ($CHECK) — $OUT verworfen." >&2
    rm -f "$OUT"
    exit 1
  fi
else
  echo "Hinweis: sqlite3 fehlt — Dateikopie, nicht WAL-sicher." >&2
  cp "$DB" "$OUT"
  if [[ -f "$DB-wal" ]]; then
    cp "$DB-wal" "$OUT-wal"
  fi
fi

if [[ -d "$DATA/uploads" ]] && command -v tar >/dev/null 2>&1; then
  tar -C "$DATA" -czf "$DEST/aistudio-$STAMP-uploads.tar.gz" uploads
fi

# Nur die letzten 14 Sicherungen behalten (Datenbank + zugehörige Uploads).
while IFS= read -r old; do
  [[ -z "$old" ]] && continue
  rm -f "$old" "${old%.db}-uploads.tar.gz"
done < <(ls -1t "$DEST"/aistudio-*.db 2>/dev/null | tail -n +15)

echo "$OUT"
