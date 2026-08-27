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
