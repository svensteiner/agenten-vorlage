"""Runtime configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
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

VERSION = "1.4.4"
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
