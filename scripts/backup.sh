#!/usr/bin/env bash
# SQLite-Sicherung der Produkt-Datenbank (WAL-sicher, wenn sqlite3 vorhanden)
# plus Uploads unter AISTUDIO_DATA/uploads.
# AISTUDIO_BACKUP_PASS — AES-256 (openssl, pbkdf2), kein Klartext auf Platte.
# Schlägt openssl fehl, wird der Klartext mitgelöscht.
# Passwort liegt in backup.env neben .env (nicht in der Produkt-Umgebung;
# systemd: InaccessiblePaths). Docker: data/backup.env auf dem Volume.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${AISTUDIO_DATA:-$ROOT/data}"
DB="${AISTUDIO_DB:-$DATA/aistudio.db}"
DEST="${1:-$DATA/backups}"
# shellcheck source=load-backup-pass.sh
. "$(cd "$(dirname "$0")" && pwd)/load-backup-pass.sh"
aistudio_load_backup_pass
aistudio_ensure_backup_pass

if [[ ! -f "$DB" ]]; then
  echo "Keine Datenbank unter $DB" >&2
  exit 1
fi

mkdir -p "$DEST"
chmod 700 "$DEST" 2>/dev/null || true
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

chmod 600 "$OUT" 2>/dev/null || true

if [[ -d "$DATA/uploads" ]] && command -v tar >/dev/null 2>&1; then
  tar -C "$DATA" -czf "$DEST/aistudio-$STAMP-uploads.tar.gz" uploads
  chmod 600 "$DEST/aistudio-$STAMP-uploads.tar.gz" 2>/dev/null || true
fi

encrypt_file() {
  # Success: drop plaintext. Failure: drop plaintext and any partial .enc.
  local src="$1"
  local dest="$2"
  if openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt \
    -pass env:AISTUDIO_BACKUP_PASS -in "$src" -out "$dest"; then
    rm -f "$src"
    chmod 600 "$dest" 2>/dev/null || true
    return 0
  fi
  rm -f "$src" "$dest"
  echo "Verschlüsselung fehlgeschlagen — Klartext nicht behalten." >&2
  return 1
}

if [[ -n "${AISTUDIO_BACKUP_PASS:-}" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "AISTUDIO_BACKUP_PASS gesetzt, aber openssl fehlt — keine Klartext-Sicherung." >&2
    rm -f "$OUT" "$DEST/aistudio-$STAMP-uploads.tar.gz"
    exit 1
  fi
  encrypt_file "$OUT" "$OUT.enc" || exit 1
  OUT="$OUT.enc"
  if [[ -f "$DEST/aistudio-$STAMP-uploads.tar.gz" ]]; then
    encrypt_file "$DEST/aistudio-$STAMP-uploads.tar.gz" "$DEST/aistudio-$STAMP-uploads.tar.gz.enc" || exit 1
  fi
fi

# Nur die letzten 14 Sicherungen behalten (Klartext und .enc).
while IFS= read -r old; do
  [[ -z "$old" ]] && continue
  rm -f "$old" "$old.enc" "${old%.db}-uploads.tar.gz" "${old%.db}-uploads.tar.gz.enc"
done < <(
  (
    shopt -s nullglob
    files=("$DEST"/aistudio-*.db "$DEST"/aistudio-*.db.enc)
    if ((${#files[@]})); then
      ls -1t "${files[@]}"
    fi
  ) | sed 's/\.enc$//' | awk '!seen[$0]++' | tail -n +15
)

echo "$OUT"
