#!/usr/bin/env bash
# First-run production files: .env with a fresh secret, data directory.
# Optional first tenant (written to data/bootstrap.env, deleted after first start):
#   ./scripts/install.sh --org "Muster GmbH" --email admin@muster.example --password-file ./pass.txt
#   AISTUDIO_BOOTSTRAP_PASSWORD='…' ./scripts/install.sh --org "Muster GmbH" --email admin@muster.example
# --password steht in der Prozessliste — nur für lokale Versuche.
# --password-file muss chmod 600 oder 400 sein.
# Optional systemd units rewritten for this checkout:
#   ./scripts/install.sh --systemd
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
ORG=""
EMAIL=""
PASSWORD=""
PASSWORD_FILE=""
PASSWORD_FROM_CLI=0
NAME=""
SYSTEMD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org) ORG="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --password) PASSWORD="$2"; PASSWORD_FROM_CLI=1; shift 2 ;;
    --password-file) PASSWORD_FILE="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --systemd) SYSTEMD=1; shift ;;
    -h|--help)
      echo "usage: $0 [--org NAME --email EMAIL --password-file FILE|--password PASS --name NAME] [--systemd]"
      exit 0
      ;;
    *) echo "unbekanntes Argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -n "$PASSWORD_FILE" ]]; then
  if [[ ! -f "$PASSWORD_FILE" ]]; then
    echo "Passwort-Datei nicht gefunden: $PASSWORD_FILE" >&2
    exit 1
  fi
  MODE="$(stat -c '%a' "$PASSWORD_FILE" 2>/dev/null || true)"
  if [[ -n "$MODE" && "$MODE" != "600" && "$MODE" != "400" ]]; then
    echo "Passwort-Datei muss chmod 600 oder 400 sein (ist $MODE)." >&2
    exit 1
  fi
  PASSWORD="$(python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); print(p.rstrip("\n"))' "$PASSWORD_FILE")"
  PASSWORD_FROM_CLI=0
fi
if [[ -z "$PASSWORD" && -n "${AISTUDIO_BOOTSTRAP_PASSWORD:-}" ]]; then
  PASSWORD="$AISTUDIO_BOOTSTRAP_PASSWORD"
  PASSWORD_FROM_CLI=0
fi
if [[ "$PASSWORD_FROM_CLI" -eq 1 ]]; then
  echo "Hinweis: --password ist in der Prozessliste sichtbar. Lieber --password-file oder AISTUDIO_BOOTSTRAP_PASSWORD." >&2
fi

mkdir -p "$ROOT/data/backups"
chmod 700 "$ROOT/data"

render_systemd() {
  local dest="$ROOT/data/systemd"
  mkdir -p "$dest"
  chmod 700 "$ROOT/data"
  for unit in aistudio.service aistudio-backup.service aistudio-backup.timer; do
    sed "s|/opt/aistudio|$ROOT|g" "$ROOT/scripts/$unit" > "$dest/$unit"
  done
  echo "systemd-Einheiten: $dest"
  if [[ -w /etc/systemd/system ]]; then
    cp "$dest/"*.service "$dest/"*.timer /etc/systemd/system/
    if command -v systemctl >/dev/null 2>&1; then
      systemctl daemon-reload
      systemctl enable --now aistudio.service
      systemctl enable --now aistudio-backup.timer
      echo "systemd: aistudio.service und Backup-Timer aktiv"
    fi
  else
    echo "Als root: cp $dest/* /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now aistudio.service aistudio-backup.timer"
  fi
}

strip_backup_pass_from_env() {
  local envf="$1"
  [[ -f "$envf" ]] || return 0
  if ! grep -q '^[[:space:]]*AISTUDIO_BACKUP_PASS=' "$envf" 2>/dev/null; then
    return 0
  fi
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
lines = [ln for ln in text.splitlines(keepends=True) if not ln.lstrip().startswith("AISTUDIO_BACKUP_PASS=")]
p.write_text("".join(lines), encoding="utf-8")
' "$envf"
  chmod 600 "$envf"
}

ensure_backup_pass() {
  # Encryption key lives in data/backup.env so the product process (EnvironmentFile=.env)
  # never sees it. Existing .env values are moved, not regenerated.
  local envf="$1"
  local bakenv="$ROOT/data/backup.env"
  mkdir -p "$ROOT/data"
  chmod 700 "$ROOT/data" 2>/dev/null || true
  if grep -q '^[[:space:]]*AISTUDIO_BACKUP_PASS=.' "$bakenv" 2>/dev/null; then
    strip_backup_pass_from_env "$envf"
    return 0
  fi
  local pass=""
  if [[ -f "$envf" ]]; then
    pass="$(python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(0)
found = ""
for line in text.splitlines():
    s = line.strip()
    if s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() != "AISTUDIO_BACKUP_PASS":
        continue
    found = v.strip()
if found:
    print(found, end="")
' "$envf")"
  fi
  local moved=0
  if [[ -n "$pass" ]]; then
    moved=1
  else
    pass="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  fi
  printf 'AISTUDIO_BACKUP_PASS=%s\n' "$pass" > "$bakenv"
  chmod 600 "$bakenv"
  strip_backup_pass_from_env "$envf"
  if [[ "$moved" -eq 1 ]]; then
    echo "verschoben: AISTUDIO_BACKUP_PASS nach $bakenv (nicht mehr in der Produkt-Umgebung)."
  else
    echo "nachgetragen: AISTUDIO_BACKUP_PASS in $bakenv (AES-256 für Sicherungen)."
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    echo "Hinweis: openssl fehlt — Sicherungen bleiben unverschlüsselt, bis openssl da ist." >&2
  fi
}

if [[ -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE existiert bereits — nichts überschrieben." >&2
  ensure_backup_pass "$ENV_FILE"
else
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  METRICS="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  {
    echo "AISTUDIO_ENV=production"
    echo "AISTUDIO_HOST=127.0.0.1"
    echo "AISTUDIO_PORT=8123"
    echo "AISTUDIO_DATA=$ROOT/data"
    echo "AISTUDIO_SECRET=$SECRET"
    echo "AISTUDIO_METRICS_TOKEN=$METRICS"
    echo "AISTUDIO_ALLOW_DEMO_SEED=false"
    echo "AISTUDIO_ALLOW_REGISTER=false"
    echo "AISTUDIO_TRUST_PROXY=true"
    echo "AISTUDIO_PROXY_IPS=127.0.0.1,::1"
    echo "AISTUDIO_LLM_PROVIDER=none"
    echo "AISTUDIO_LLM_EGRESS=in_boundary"
    echo "AISTUDIO_TOKEN_TTL=43200"
    echo "AISTUDIO_SESSION_IDLE=14400"
    echo "AISTUDIO_ALLOWED_HOSTS=127.0.0.1,localhost"
    echo "AISTUDIO_ORG_UPLOAD_MB=200"
    echo "AISTUDIO_AUDIT_RETENTION_DAYS=365"
    echo "AISTUDIO_HOUSEKEEPING_HOURS=24"
    echo "AISTUDIO_LLM_PER_USER_DAY=200"
    echo "AISTUDIO_LLM_PER_ORG_DAY=800"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "geschrieben: $ENV_FILE"
  ensure_backup_pass "$ENV_FILE"
fi

if [[ -n "$ORG" && -n "$EMAIL" && -n "$PASSWORD" ]]; then
  BOOT="$ROOT/data/bootstrap.env"
  if [[ -f "$BOOT" ]]; then
    echo "$BOOT existiert bereits — nichts überschrieben." >&2
  else
    {
      echo "AISTUDIO_BOOTSTRAP_ORG=$ORG"
      echo "AISTUDIO_BOOTSTRAP_EMAIL=$EMAIL"
      echo "AISTUDIO_BOOTSTRAP_PASSWORD=$PASSWORD"
      echo "AISTUDIO_BOOTSTRAP_NAME=${NAME:-$EMAIL}"
    } > "$BOOT"
    chmod 600 "$BOOT"
    echo "geschrieben: $BOOT (wird nach dem ersten Start gelöscht)"
  fi
fi

if [[ "$SYSTEMD" -eq 1 ]]; then
  render_systemd
fi

echo "Start: set -a && source $ENV_FILE && set +a && ./scripts/run_product.sh"
echo "Nach dem ersten Start löscht der Prozess data/bootstrap.env (systemd kann data/ schreiben)."
echo "Ältere Installs: AISTUDIO_BOOTSTRAP_* aus .env entfernen, falls noch vorhanden."
echo "Metriken: Header X-Metrics-Token (Wert in .env)."
echo "Sicherung: ./scripts/backup.sh  (AISTUDIO_BACKUP_PASS in data/backup.env, AES-256; Restore braucht denselben Wert)"
echo "Ältere Installs: Passwort wird aus .env nach data/backup.env verschoben — der Produktprozess sieht es nicht."
echo "Aufräumen: ./scripts/housekeeping.sh"
echo "Proxy HTTP: scripts/nginx-aistudio.conf — TLS: scripts/nginx-aistudio.tls.conf"
echo "Hinter nginx AISTUDIO_ALLOWED_HOSTS um den öffentlichen Hostnamen ergänzen."
echo "X-Forwarded-For nur von AISTUDIO_PROXY_IPS (Standard 127.0.0.1,::1), nicht von jedem Client."
echo "Qualität (lokal, ohne GitHub Actions): ./scripts/check.sh"
