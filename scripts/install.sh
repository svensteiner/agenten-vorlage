#!/usr/bin/env bash
# First-run production files: .env with a fresh secret, data directory.
# Optional first tenant:
#   ./scripts/install.sh --org "Muster GmbH" --email admin@muster.example --password 'Mindestens10x'
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
ORG=""
EMAIL=""
PASSWORD=""
NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org) ORG="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    -h|--help)
      echo "usage: $0 [--org NAME --email EMAIL --password PASS --name NAME]"
      exit 0
      ;;
    *) echo "unbekanntes Argument: $1" >&2; exit 1 ;;
  esac
done

mkdir -p "$ROOT/data"
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

echo "Start: set -a && source $ENV_FILE && set +a && ./scripts/run_product.sh"
echo "Sicherung: ./scripts/backup.sh"
echo "Qualität (lokal, ohne GitHub Actions): ./scripts/check.sh"
