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

nologin_shell() {
  local s
  for s in /usr/sbin/nologin /sbin/nologin /bin/false; do
    if [[ -x "$s" ]]; then
      printf '%s\n' "$s"
      return 0
    fi
  done
  printf '%s\n' /bin/false
}

ensure_aistudio_user() {
  # Product and backup units use User=aistudio — never uid 0.
  if ! getent group aistudio >/dev/null 2>&1; then
    if command -v groupadd >/dev/null 2>&1; then
      groupadd --system aistudio
    else
      echo "Kein groupadd — Gruppe aistudio fehlt." >&2
      return 1
    fi
  fi
  if ! getent passwd aistudio >/dev/null 2>&1; then
    local shell
    shell="$(nologin_shell)"
    if command -v useradd >/dev/null 2>&1; then
      useradd --system --gid aistudio --home-dir "$ROOT" --no-create-home --shell "$shell" --comment "AI Studio" aistudio
    elif command -v adduser >/dev/null 2>&1; then
      adduser --system --ingroup aistudio --home "$ROOT" --no-create-home --shell "$shell" aistudio
    else
      echo "Kein useradd — Dienstbenutzer aistudio fehlt." >&2
      return 1
    fi
  fi
}

fix_runtime_ownership() {
  chown -R aistudio:aistudio "$ROOT/data" 2>/dev/null || true
  chmod 700 "$ROOT/data" 2>/dev/null || true
  if [[ -f "$ENV_FILE" ]]; then
    chown root:aistudio "$ENV_FILE"
    chmod 640 "$ENV_FILE"
  fi
  if [[ -f "$ROOT/backup.env" ]]; then
    chown aistudio:aistudio "$ROOT/backup.env"
    chmod 600 "$ROOT/backup.env"
  fi
  if [[ -f "$ROOT/data/backup.env" ]]; then
    chown aistudio:aistudio "$ROOT/data/backup.env"
    chmod 600 "$ROOT/data/backup.env"
  fi
  if [[ -f "$ROOT/data/bootstrap.env" ]]; then
    chown aistudio:aistudio "$ROOT/data/bootstrap.env"
    chmod 600 "$ROOT/data/bootstrap.env"
  fi
}

render_systemd() {
  local dest="$ROOT/data/systemd"
  local unit_user="aistudio"
  local unit_group="aistudio"
  mkdir -p "$dest"
  chmod 700 "$ROOT/data"
  if [[ "$(id -u)" -eq 0 ]]; then
    if ensure_aistudio_user; then
      fix_runtime_ownership
      echo "Dienstbenutzer: aistudio (nicht root)"
    else
      echo "Hinweis: Benutzer aistudio anlegen, sonst startet die Einheit nicht." >&2
    fi
  else
    unit_user="$(id -un)"
    unit_group="$(id -gn)"
    echo "Kein root — Einheiten mit User=$unit_user (nicht aistudio)."
  fi
  local unit
  for unit in aistudio.service aistudio-backup.service aistudio-backup.timer; do
    sed \
      -e "s|/opt/aistudio|$ROOT|g" \
      -e "s|^User=aistudio\$|User=$unit_user|" \
      -e "s|^Group=aistudio\$|Group=$unit_group|" \
      "$ROOT/scripts/$unit" > "$dest/$unit"
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

env_has_key() {
  local envf="$1" key="$2"
  grep -qE "^[[:space:]]*${key}=" "$envf" 2>/dev/null
}

env_value_too_short() {
  # Exit 0 (true) when missing, empty, or shorter than $3 characters.
  local envf="$1" key="$2" min="$3"
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
key = sys.argv[2]
try:
    min_n = int(sys.argv[3])
except ValueError:
    min_n = 16
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(0)
val = ""
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() == key:
        val = v.strip()
        break
raise SystemExit(0 if len(val) < min_n else 1)
' "$envf" "$key" "$min"
}

env_secret_unusable() {
  # Exit 0 (true) when AISTUDIO_SECRET is missing, the published demo value, or <24 chars.
  # Last assignment wins (systemd EnvironmentFile). Never prints the value.
  local envf="$1"
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
demo = "dev-secret-change-me"
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(0)
val = ""
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() == "AISTUDIO_SECRET":
        val = v.strip()
raise SystemExit(0 if (not val or val == demo or len(val) < 24) else 1)
' "$envf"
}

env_flag_on() {
  # Exit 0 when the key is 1/true/yes/on. Missing or other values → 1 (off).
  local envf="$1" key="$2"
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
key = sys.argv[2]
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(1)
val = ""
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() == key:
        val = v.strip()
raise SystemExit(0 if val.lower() in {"1", "true", "yes", "on"} else 1)
' "$envf" "$key"
}

env_runs_as_production() {
  # .env last assignment. Missing key → production (unit + pin file).
  # systemd EnvironmentFile overrides Environment=; the pin file after
  # .env restores production even when this helper sees development.
  local envf="$1"
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(0)
val = None
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() == "AISTUDIO_ENV":
        val = v.strip().lower()
if val is None:
    raise SystemExit(0)
raise SystemExit(0 if val in {"production", "prod"} else 1)
' "$envf"
}

replace_env_value() {
  local envf="$1" key="$2" val="$3" mode
  mode="$(stat -c '%a' "$envf" 2>/dev/null || echo 600)"
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1])
key = sys.argv[2]
val = sys.argv[3]
try:
    text = p.read_text(encoding="utf-8")
except OSError:
    raise SystemExit(0)
out = []
found = False
for ln in text.splitlines(keepends=True):
    s = ln.lstrip()
    if s.startswith("#") or "=" not in ln:
        out.append(ln)
        continue
    k, _, _rest = ln.partition("=")
    if k.strip() == key:
        if not found:
            out.append("%s=%s\n" % (key, val))
            found = True
        continue
    out.append(ln)
if not found:
    if out and not out[-1].endswith("\n"):
        out.append("\n")
    out.append("%s=%s\n" % (key, val))
p.write_text("".join(out), encoding="utf-8")
' "$envf" "$key" "$val"
  chmod "$mode" "$envf" 2>/dev/null || true
}

append_env_line() {
  local envf="$1" line="$2" mode
  mode="$(stat -c '%a' "$envf" 2>/dev/null || echo 600)"
  printf '%s\n' "$line" >> "$envf"
  chmod "$mode" "$envf" 2>/dev/null || true
}

backfill_runtime_env() {
  # Existing .env from older installs: append missing keys, never overwrite
  # a non-empty value. Empty/short AISTUDIO_METRICS_TOKEN is replaced (1.4.49 boot).
  local envf="$1"
  [[ -f "$envf" ]] || return 0
  if ! env_has_key "$envf" AISTUDIO_HOST; then
    append_env_line "$envf" "AISTUDIO_HOST=127.0.0.1"
    echo "nachgetragen: AISTUDIO_HOST=127.0.0.1 (nicht alle Interfaces; Docker setzt 0.0.0.0 im Container)."
  fi
  if ! env_has_key "$envf" AISTUDIO_ALLOWED_HOSTS; then
    append_env_line "$envf" "AISTUDIO_ALLOWED_HOSTS=127.0.0.1,localhost"
    echo "nachgetragen: AISTUDIO_ALLOWED_HOSTS=127.0.0.1,localhost (Produktion prüft den Host; hinter nginx den öffentlichen Namen ergänzen)."
  fi
  if ! env_has_key "$envf" AISTUDIO_METRICS_TOKEN || env_value_too_short "$envf" AISTUDIO_METRICS_TOKEN 16; then
    local tok
    tok="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
    if env_has_key "$envf" AISTUDIO_METRICS_TOKEN; then
      replace_env_value "$envf" AISTUDIO_METRICS_TOKEN "$tok"
      echo "nachgetragen: AISTUDIO_METRICS_TOKEN (war leer oder zu kurz; Header X-Metrics-Token)."
    else
      append_env_line "$envf" "AISTUDIO_METRICS_TOKEN=$tok"
      echo "nachgetragen: AISTUDIO_METRICS_TOKEN (Header X-Metrics-Token)."
    fi
  fi
  if ! env_has_key "$envf" AISTUDIO_PROXY_IPS; then
    append_env_line "$envf" "AISTUDIO_PROXY_IPS=127.0.0.1,::1"
    echo "nachgetragen: AISTUDIO_PROXY_IPS=127.0.0.1,::1"
  fi
  if ! env_has_key "$envf" AISTUDIO_TRUST_PROXY; then
    append_env_line "$envf" "AISTUDIO_TRUST_PROXY=true"
    echo "nachgetragen: AISTUDIO_TRUST_PROXY=true"
  fi
  if ! env_has_key "$envf" AISTUDIO_SESSION_IDLE; then
    append_env_line "$envf" "AISTUDIO_SESSION_IDLE=14400"
    echo "nachgetragen: AISTUDIO_SESSION_IDLE=14400"
  fi
  if ! env_has_key "$envf" AISTUDIO_LLM_EGRESS; then
    append_env_line "$envf" "AISTUDIO_LLM_EGRESS=in_boundary"
    echo "nachgetragen: AISTUDIO_LLM_EGRESS=in_boundary"
  fi
}

ensure_backup_pass() {
  # Encryption key lives in checkout/backup.env (outside data/) so systemd
  # InaccessiblePaths can hide it from the product process. Existing .env or
  # data/backup.env values are moved, not regenerated.
  local envf="$1"
  local bakenv="$ROOT/backup.env"
  local legacy="$ROOT/data/backup.env"
  mkdir -p "$ROOT/data"
  chmod 700 "$ROOT/data" 2>/dev/null || true
  if grep -q '^[[:space:]]*AISTUDIO_BACKUP_PASS=.' "$bakenv" 2>/dev/null; then
    strip_backup_pass_from_env "$envf"
    if [[ -f "$legacy" ]]; then
      rm -f "$legacy"
      echo "entfernt: $legacy (Passwort liegt in $bakenv)."
    fi
    return 0
  fi
  if grep -q '^[[:space:]]*AISTUDIO_BACKUP_PASS=.' "$legacy" 2>/dev/null; then
    mv "$legacy" "$bakenv"
    chmod 600 "$bakenv"
    strip_backup_pass_from_env "$envf"
    echo "verschoben: $legacy nach $bakenv (außerhalb von data/)."
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
  backfill_runtime_env "$ENV_FILE"
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
    echo "AISTUDIO_ORG_MAX_DOCS=500"
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

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 fehlt — ./scripts/backup.sh bricht ab. Paket sqlite3 installieren." >&2
  if [[ "$SYSTEMD" -eq 1 ]]; then
    exit 1
  fi
fi
if ! command -v flock >/dev/null 2>&1; then
  echo "flock fehlt — überlappende Sicherungen sind unsicher. Paket util-linux installieren." >&2
  if [[ "$SYSTEMD" -eq 1 ]]; then
    exit 1
  fi
fi

if [[ "$SYSTEMD" -eq 1 ]]; then
  if env_secret_unusable "$ENV_FILE"; then
    echo "AISTUDIO_SECRET ist der Demo-Wert, fehlt oder kürzer als 24 Zeichen — systemd nicht installiert (sonst Crash-Loop). Eigenes Secret in $ENV_FILE setzen (mindestens 24 Zeichen) oder .env entfernen und install.sh erneut ausführen." >&2
    exit 1
  fi
  # Unit always pins production; leftover development .env must not skip this.
  if env_flag_on "$ENV_FILE" AISTUDIO_ALLOW_DEMO_SEED; then
    echo "AISTUDIO_ALLOW_DEMO_SEED ist an — systemd nicht installiert (Produktion würde mit bekanntem Demo-Passwort starten). In $ENV_FILE auf false setzen." >&2
    exit 1
  fi
  if [[ ! -f "$ROOT/scripts/aistudio.systemd.env" ]]; then
    echo "scripts/aistudio.systemd.env fehlt — systemd nicht installiert (Pin für production/Loopback/kein Demo-Seed)." >&2
    exit 1
  fi
  if ! env_runs_as_production "$ENV_FILE"; then
    echo "Hinweis: AISTUDIO_ENV in $ENV_FILE ist nicht production — die Unit setzt production nach der .env (scripts/aistudio.systemd.env)." >&2
  fi
  render_systemd
fi

echo "Start: set -a && source $ENV_FILE && set +a && ./scripts/run_product.sh"
echo "systemd (--systemd): User=aistudio, nicht root. data/ gehört aistudio, .env ist 640 root:aistudio."
echo "Nach dem ersten Start löscht der Prozess data/bootstrap.env (systemd kann data/ schreiben)."
echo "Ältere Installs: AISTUDIO_BOOTSTRAP_* aus .env entfernen, falls noch vorhanden."
echo "Metriken: Header X-Metrics-Token (Wert in .env)."
echo "Sicherung: ./scripts/backup.sh  (AISTUDIO_BACKUP_PASS in backup.env neben .env, AES-256; Restore braucht denselben Wert)"
echo "Restore: Produkt zuerst stoppen — restore.sh bricht ab, solange data/aistudio.lock gehalten wird (FORCE umgeht nur die PID-Datei)."
echo "Ältere Installs: Passwort wird aus .env oder data/backup.env nach backup.env verschoben — der Produktprozess sieht die Datei nicht (InaccessiblePaths)."
echo "Aufräumen: ./scripts/housekeeping.sh"
echo "Proxy HTTP: scripts/nginx-aistudio.conf — TLS: scripts/nginx-aistudio.tls.conf"
echo "Ohne AISTUDIO_HOST bindet die Instanz 127.0.0.1. Docker setzt 0.0.0.0 im Container und braucht dann ein eigenes Secret."
echo "Hinter nginx AISTUDIO_ALLOWED_HOSTS um den öffentlichen Hostnamen ergänzen."
echo "X-Forwarded-For nur von AISTUDIO_PROXY_IPS (Standard 127.0.0.1,::1), nicht von jedem Client."
echo "Qualität (lokal, ohne GitHub Actions): ./scripts/check.sh"
