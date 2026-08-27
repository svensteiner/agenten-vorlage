# Shared by backup.sh and restore.sh. Do not execute directly.
# Loads AISTUDIO_BACKUP_PASS from data/backup.env (preferred), then from the
# checkout .env only when AISTUDIO_DATA is this checkout's data/ — so a test
# tmpdir never reads the workspace .env. Never prints the value.

aistudio_extract_backup_pass() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  local line val
  line="$(grep -E '^[[:space:]]*AISTUDIO_BACKUP_PASS=.' "$file" 2>/dev/null | tail -n 1 || true)"
  [[ -n "${line:-}" ]] || return 1
  val="${line#*=}"
  val="${val%$'\r'}"
  case "$val" in
    \"*\") val="${val:1:${#val}-2}" ;;
    \'*\') val="${val:1:${#val}-2}" ;;
  esac
  [[ -n "$val" ]] || return 1
  export AISTUDIO_BACKUP_PASS="$val"
  return 0
}

aistudio_load_backup_pass() {
  if [[ -n "${AISTUDIO_BACKUP_PASS:-}" ]]; then
    return 0
  fi
  local root data parent
  root="${AISTUDIO_ROOT:-${ROOT:-}}"
  data="${AISTUDIO_DATA:-}"
  if [[ -z "$data" && -n "$root" ]]; then
    data="$root/data"
  fi
  if [[ -n "$data" ]]; then
    aistudio_extract_backup_pass "$data/backup.env" && return 0
    parent="$(cd "$data/.." && pwd 2>/dev/null || true)"
    if [[ -n "$root" && -n "$parent" && "$parent" == "$root" ]]; then
      aistudio_extract_backup_pass "$root/.env" && return 0
    fi
  elif [[ -n "$root" ]]; then
    aistudio_extract_backup_pass "$root/data/backup.env" && return 0
    aistudio_extract_backup_pass "$root/.env" && return 0
  fi
  return 0
}

aistudio_ensure_backup_pass() {
  # Production only: create data/backup.env once so Docker backups encrypt
  # without install.sh. Never prints the value. No-op in development.
  if [[ -n "${AISTUDIO_BACKUP_PASS:-}" ]]; then
    return 0
  fi
  local envn data pass
  envn="$(printf '%s' "${AISTUDIO_ENV:-}" | tr '[:upper:]' '[:lower:]')"
  if [[ "$envn" != "production" && "$envn" != "prod" ]]; then
    return 0
  fi
  data="${AISTUDIO_DATA:-${DATA:-}}"
  if [[ -z "$data" ]]; then
    return 0
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    echo "Hinweis: AISTUDIO_BACKUP_PASS fehlt — Sicherung unverschlüsselt. openssl fehlt; ./scripts/install.sh schreibt data/backup.env." >&2
    return 0
  fi
  mkdir -p "$data"
  chmod 700 "$data" 2>/dev/null || true
  if command -v python3 >/dev/null 2>&1; then
    pass="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  elif command -v python >/dev/null 2>&1; then
    pass="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  else
    pass="$(openssl rand -base64 32 | tr -d '\n')"
  fi
  if [[ -z "$pass" ]]; then
    echo "Hinweis: AISTUDIO_BACKUP_PASS fehlt — Sicherung unverschlüsselt." >&2
    return 0
  fi
  printf 'AISTUDIO_BACKUP_PASS=%s\n' "$pass" > "$data/backup.env"
  chmod 600 "$data/backup.env" 2>/dev/null || true
  export AISTUDIO_BACKUP_PASS="$pass"
  echo "geschrieben: $data/backup.env (AES-256). Wert bleibt außerhalb der Produkt-Umgebung." >&2
}
