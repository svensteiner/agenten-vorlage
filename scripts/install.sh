#!/usr/bin/env bash
# First-run production files: .env with a fresh secret, data directory.
# Optional first tenant:
#   ./scripts/install.sh --org "Muster GmbH" --email admin@muster.example --password 'Mindestens10x'
# Optional systemd units rewritten for this checkout:
#   ./scripts/install.sh --systemd
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
ORG=""
EMAIL=""
PASSWORD=""
NAME=""
SYSTEMD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org) ORG="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --systemd) SYSTEMD=1; shift ;;
    -h|--help)
      echo "usage: $0 [--org NAME --email EMAIL --password PASS --name NAME] [--systemd]"
      exit 0
      ;;
    *) echo "unbekanntes Argument: $1" >&2; exit 1 ;;
  esac
done

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

if [[ -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE existiert bereits — nichts überschrieben." >&2
else
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  {
    echo "AISTUDIO_ENV=production"
    echo "AISTUDIO_HOST=127.0.0.1"
    echo "AISTUDIO_PORT=8123"
    echo "AISTUDIO_DATA=$ROOT/data"
    echo "AISTUDIO_SECRET=$SECRET"
    echo "AISTUDIO_ALLOW_DEMO_SEED=false"
    echo "AISTUDIO_ALLOW_REGISTER=false"
    echo "AISTUDIO_TRUST_PROXY=true"
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
    if [[ -n "$ORG" && -n "$EMAIL" && -n "$PASSWORD" ]]; then
      echo "AISTUDIO_BOOTSTRAP_ORG=$ORG"
      echo "AISTUDIO_BOOTSTRAP_EMAIL=$EMAIL"
      echo "AISTUDIO_BOOTSTRAP_PASSWORD=$PASSWORD"
      echo "AISTUDIO_BOOTSTRAP_NAME=${NAME:-$EMAIL}"
    fi
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "geschrieben: $ENV_FILE"
fi

if [[ "$SYSTEMD" -eq 1 ]]; then
  render_systemd
fi

echo "Start: set -a && source $ENV_FILE && set +a && ./scripts/run_product.sh"
echo "Sicherung: ./scripts/backup.sh  (AISTUDIO_BACKUP_PASS für AES-256)"
echo "Aufräumen: ./scripts/housekeeping.sh"
echo "Proxy HTTP: scripts/nginx-aistudio.conf — TLS: scripts/nginx-aistudio.tls.conf"
echo "Hinter nginx AISTUDIO_ALLOWED_HOSTS um den öffentlichen Hostnamen ergänzen."
echo "Qualität (lokal, ohne GitHub Actions): ./scripts/check.sh"
