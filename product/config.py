"""Runtime configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Tests set AISTUDIO_LOAD_DOTENV=0 so a local .env cannot leak keys into pytest.
if os.environ.get("AISTUDIO_LOAD_DOTENV", "1").strip().lower() not in {"0", "false", "no", "off"}:
    load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.environ.get("AISTUDIO_DATA", ROOT / "data"))
DB_PATH = Path(os.environ.get("AISTUDIO_DB", DATA_DIR / "aistudio.db"))
SECRET = os.environ.get("AISTUDIO_SECRET", "dev-secret-change-me")
SEED_PATH = Path(__file__).resolve().parent / "seed.json"
TOKEN_TTL_SECONDS = int(os.environ.get("AISTUDIO_TOKEN_TTL", str(7 * 24 * 3600)))

DEMO_EMAIL = os.environ.get("AISTUDIO_DEMO_EMAIL", "katharina.vogel@meridian.example")
DEMO_PASSWORD = os.environ.get("AISTUDIO_DEMO_PASSWORD", "Meridian2026!")
DEMO_NAME = os.environ.get("AISTUDIO_DEMO_NAME", "Dr. Katharina Vogel")
DEMO_ROLE = os.environ.get("AISTUDIO_DEMO_ROLE", "cfo")

HOST = os.environ.get("AISTUDIO_HOST", "0.0.0.0")
PORT = int(os.environ.get("AISTUDIO_PORT", "8123"))

VERSION = "1.4.12"
STARTED_AT = time.time()
DEFAULT_SECRET = "dev-secret-change-me"
LOCKOUT_AFTER = int(os.environ.get("AISTUDIO_LOCKOUT_AFTER", "8"))
LOCKOUT_MINUTES = int(os.environ.get("AISTUDIO_LOCKOUT_MINUTES", "15"))
MAX_UPLOAD_BYTES = int(os.environ.get("AISTUDIO_MAX_UPLOAD_BYTES", str(2_000_000)))
MAX_REQUEST_BYTES = int(os.environ.get("AISTUDIO_MAX_REQUEST_BYTES", str(MAX_UPLOAD_BYTES + 200_000)))


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_name() -> str:
    return os.environ.get("AISTUDIO_ENV", "development").strip().lower()


def is_production() -> bool:
    return env_name() in {"production", "prod"}


def allow_demo_seed() -> bool:
    return _flag("AISTUDIO_ALLOW_DEMO_SEED", default=not is_production())


def allow_register() -> bool:
    return _flag("AISTUDIO_ALLOW_REGISTER", default=not is_production())


def trust_proxy() -> bool:
    return _flag("AISTUDIO_TRUST_PROXY", default=False)


def bootstrap_spec() -> dict | None:
    """First-tenant env bootstrap. None unless org, email and password are set."""
    org = (os.environ.get("AISTUDIO_BOOTSTRAP_ORG") or "").strip()
    email = (os.environ.get("AISTUDIO_BOOTSTRAP_EMAIL") or "").strip()
    password = os.environ.get("AISTUDIO_BOOTSTRAP_PASSWORD") or ""
    name = (os.environ.get("AISTUDIO_BOOTSTRAP_NAME") or "").strip()
    if not org or not email or not password:
        return None
    return {"org_name": org, "email": email, "password": password, "name": name or email}


def cors_origins() -> list[str]:
    raw = os.environ.get("AISTUDIO_CORS_ORIGINS")
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    if is_production():
        return []
    return ["*"]


def allowed_hosts() -> list[str] | None:
    """Host-Header allowlist. None = do not enforce (development / unset)."""
    raw = os.environ.get("AISTUDIO_ALLOWED_HOSTS")
    if raw is None:
        return None
    text = raw.strip()
    if not text or text == "*":
        return None
    hosts = [p.strip() for p in text.split(",") if p.strip()]
    return hosts or None


def docs_kwargs() -> dict:
    """Hide OpenAPI in production — /docs was already off, /openapi.json was not."""
    if is_production():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


def session_idle_seconds() -> int:
    """0 = only the signed token TTL applies. Production install sets 4 hours."""
    try:
        n = int(os.environ.get("AISTUDIO_SESSION_IDLE", "0"))
    except ValueError:
        n = 0
    return max(0, min(n, 7 * 24 * 3600))


def org_upload_limit_bytes() -> int:
    """Per-tenant upload cap. 0 = unlimited. Default 200 MB."""
    try:
        mb = int(os.environ.get("AISTUDIO_ORG_UPLOAD_MB", "200"))
    except ValueError:
        mb = 200
    if mb <= 0:
        return 0
    return max(1, min(mb, 10_240)) * 1024 * 1024


def org_upload_bytes(org_id: str) -> int:
    root = DATA_DIR / "uploads" / org_dir(org_id)
    if not root.is_dir():
        return 0
    try:
        root.resolve().relative_to(Path(DATA_DIR).resolve())
    except ValueError:
        return 0
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            total += path.stat().st_size
        except OSError:
            continue
    return total


BOOTSTRAP_KEYS = (
    "AISTUDIO_BOOTSTRAP_ORG",
    "AISTUDIO_BOOTSTRAP_EMAIL",
    "AISTUDIO_BOOTSTRAP_PASSWORD",
    "AISTUDIO_BOOTSTRAP_NAME",
)


def env_file() -> Path:
    raw = (os.environ.get("AISTUDIO_ENV_FILE") or "").strip()
    return Path(raw) if raw else ROOT / ".env"


def consume_bootstrap_env(*, env_path: Path | None = None) -> bool:
    """Drop first-tenant secrets from the process and from .env after success."""
    for key in BOOTSTRAP_KEYS:
        os.environ.pop(key, None)
    explicit = env_path is not None or bool((os.environ.get("AISTUDIO_ENV_FILE") or "").strip())
    if not explicit and not is_production():
        return False
    path = env_path or env_file()
    if not path.is_file():
        return False
    try:
        resolved = path.resolve()
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Never rewrite an unrelated path unless the caller named it.
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        if not explicit:
            return False
    lines: list[str] = []
    changed = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if any(stripped.startswith(key + "=") for key in BOOTSTRAP_KEYS):
            changed = True
            continue
        lines.append(line)
    if not changed:
        return False
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text("".join(lines), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
        os.chmod(path, 0o600)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


def backup_dir() -> Path:
    raw = (os.environ.get("AISTUDIO_BACKUP_DIR") or "").strip()
    return Path(raw) if raw else DATA_DIR / "backups"


def latest_backup_age_hours() -> float | None:
    """Hours since the newest SQLite backup. None if none found. No file contents."""
    dest = backup_dir()
    if not dest.is_dir():
        return None
    newest: float | None = None
    try:
        for path in dest.iterdir():
            name = path.name
            if not (name.endswith(".db") or name.endswith(".db.enc")):
                continue
            if not name.startswith("aistudio-"):
                continue
            if "-uploads." in name:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if newest is None or mtime > newest:
                newest = mtime
    except OSError:
        return None
    if newest is None:
        return None
    return round(max(0.0, (time.time() - newest) / 3600.0), 2)


def backup_max_age_hours() -> float:
    try:
        n = float(os.environ.get("AISTUDIO_BACKUP_MAX_AGE_HOURS", "36"))
    except ValueError:
        n = 36.0
    return max(1.0, min(n, 24 * 14))


def signing_secrets() -> list[str]:
    """Current HMAC secret, then optional previous secret for rotation."""
    keys: list[str] = []
    for item in (
        os.environ.get("AISTUDIO_SECRET"),
        SECRET,
        os.environ.get("AISTUDIO_SECRET_PREV"),
    ):
        text = (item or "").strip()
        if text and text not in keys:
            keys.append(text)
    return keys


def require_backup_for_ready() -> bool:
    return _flag("AISTUDIO_READY_REQUIRE_BACKUP", default=False)


def validate_runtime() -> None:
    """Refuse to boot a production process with the bundled demo secret."""
    if not is_production():
        return
    secret = os.environ.get("AISTUDIO_SECRET") or SECRET
    if not secret or secret == DEFAULT_SECRET or len(secret) < 24:
        raise RuntimeError(
            "Produktion verweigert den Start: AISTUDIO_SECRET muss gesetzt sein "
            "(mindestens 24 Zeichen, nicht der Demo-Wert)."
        )


def org_dir(org_id: str) -> str:
    return "".join(ch for ch in (org_id or "") if ch.isalnum() or ch in "-_")[:80] or "org"


def upload_path(org_id: str, doc_id: str) -> Path:
    safe_id = "".join(ch for ch in (doc_id or "") if ch.isalnum() or ch in "-_.")[:120]
    return DATA_DIR / "uploads" / org_dir(org_id) / f"{safe_id}.txt"


def harden_data_dir() -> None:
    """Restrict data directory and SQLite file if the filesystem allows it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DATA_DIR, 0o700)
    except OSError:
        pass
    if DB_PATH.exists():
        try:
            os.chmod(DB_PATH, 0o600)
        except OSError:
            pass
