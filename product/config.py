"""Runtime configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import ipaddress
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

VERSION = "1.4.21"
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


def proxy_ip_networks():
    """Peers allowed to set X-Forwarded-For. Default loopback. '*' = any (opt-in)."""
    raw = (os.environ.get("AISTUDIO_PROXY_IPS") or "127.0.0.1,::1").strip()
    if raw.lower() in {"*", "any"}:
        return None
    nets: list = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        if text.lower() == "localhost":
            nets.append(ipaddress.ip_network("127.0.0.1/32"))
            nets.append(ipaddress.ip_network("::1/128"))
            continue
        try:
            if "/" in text:
                nets.append(ipaddress.ip_network(text, strict=False))
            else:
                addr = ipaddress.ip_address(text)
                nets.append(ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}"))
        except ValueError:
            continue
    return nets or [
        ipaddress.ip_network("127.0.0.1/32"),
        ipaddress.ip_network("::1/128"),
    ]


def peer_is_trusted_proxy(peer: str) -> bool:
    """True if this TCP peer may supply X-Forwarded-For."""
    if not trust_proxy():
        return False
    nets = proxy_ip_networks()
    if nets is None:
        return True
    text = (peer or "").strip()
    if not text:
        return False
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return False
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped
    return any(addr in net for net in nets)


def uvicorn_forwarded_allow_ips() -> str | None:
    """Uvicorn compares exact IPs, not CIDR. Never '*' unless operators set it."""
    if not trust_proxy():
        return None
    raw = (os.environ.get("AISTUDIO_PROXY_IPS") or "127.0.0.1,::1").strip()
    if raw.lower() in {"*", "any"}:
        return "*"
    exact: list[str] = []
    for part in raw.split(","):
        text = part.strip()
        if not text or "/" in text:
            continue
        if text.lower() == "localhost":
            exact.extend(["127.0.0.1", "::1"])
            continue
        exact.append(text)
    return ",".join(dict.fromkeys(exact)) if exact else "127.0.0.1"


def bootstrap_file() -> Path:
    """Ephemeral first-tenant secrets. Lives under data/ so systemd can delete it."""
    return Path(DATA_DIR) / "bootstrap.env"


def _parse_bootstrap_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key in BOOTSTRAP_KEYS:
            out[key] = value
    return out


def bootstrap_spec() -> dict | None:
    """First-tenant bootstrap. Env vars win; otherwise data/bootstrap.env."""
    file_vals: dict[str, str] = {}
    path = bootstrap_file()
    if path.is_file():
        file_vals = _parse_bootstrap_file(path)
    org = (os.environ.get("AISTUDIO_BOOTSTRAP_ORG") or file_vals.get("AISTUDIO_BOOTSTRAP_ORG") or "").strip()
    email = (os.environ.get("AISTUDIO_BOOTSTRAP_EMAIL") or file_vals.get("AISTUDIO_BOOTSTRAP_EMAIL") or "").strip()
    password = os.environ.get("AISTUDIO_BOOTSTRAP_PASSWORD") or file_vals.get("AISTUDIO_BOOTSTRAP_PASSWORD") or ""
    name = (os.environ.get("AISTUDIO_BOOTSTRAP_NAME") or file_vals.get("AISTUDIO_BOOTSTRAP_NAME") or "").strip()
    if not org or not email or not password:
        return None
    return {"org_name": org, "email": email, "password": password, "name": name or email}


def has_bootstrap_residue() -> bool:
    if any((os.environ.get(key) or "").strip() for key in BOOTSTRAP_KEYS):
        return True
    return bootstrap_file().is_file()


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
    """Drop first-tenant secrets from the process, data/bootstrap.env, and .env."""
    for key in BOOTSTRAP_KEYS:
        os.environ.pop(key, None)
    removed = False
    boot = bootstrap_file()
    if boot.is_file():
        try:
            boot.resolve().relative_to(Path(DATA_DIR).resolve())
            boot.unlink()
            removed = True
        except (OSError, ValueError):
            pass
    explicit = env_path is not None or bool((os.environ.get("AISTUDIO_ENV_FILE") or "").strip())
    if not explicit and not is_production():
        return removed
    path = env_path or env_file()
    if not path.is_file():
        return removed
    try:
        resolved = path.resolve()
        text = path.read_text(encoding="utf-8")
    except OSError:
        return removed
    # Never rewrite an unrelated path unless the caller named it.
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        if not explicit:
            return removed
    lines: list[str] = []
    changed = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if any(stripped.startswith(key + "=") for key in BOOTSTRAP_KEYS):
            changed = True
            continue
        lines.append(line)
    if not changed:
        return removed
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
        return removed
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
    prod = is_production()
    for item in (
        os.environ.get("AISTUDIO_SECRET"),
        SECRET,
        os.environ.get("AISTUDIO_SECRET_PREV"),
    ):
        text = (item or "").strip()
        if not text or text in keys:
            continue
        if prod and (text == DEFAULT_SECRET or len(text) < 24):
            continue
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


def pid_file() -> Path:
    return Path(DATA_DIR) / "aistudio.pid"


def write_pid_file() -> None:
    """Record this process so restore.sh can refuse a live overwrite."""
    path = pid_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("%s\n" % os.getpid(), encoding="utf-8")
        os.chmod(path, 0o600)
    except OSError:
        pass


def clear_pid_file() -> None:
    path = pid_file()
    try:
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8").strip()
        if text == str(os.getpid()):
            path.unlink()
    except OSError:
        pass


def harden_data_dir() -> None:
    """Restrict data directory and SQLite file if the filesystem allows it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DATA_DIR, 0o700)
    except OSError:
        pass
    backups = DATA_DIR / "backups"
    if backups.is_dir():
        try:
            os.chmod(backups, 0o700)
        except OSError:
            pass
    bakenv = DATA_DIR / "backup.env"
    if bakenv.is_file():
        try:
            os.chmod(bakenv, 0o600)
        except OSError:
            pass
    pidf = pid_file()
    if pidf.is_file():
        try:
            os.chmod(pidf, 0o600)
        except OSError:
            pass
    for extra in (DB_PATH, Path(str(DB_PATH) + "-wal"), Path(str(DB_PATH) + "-shm")):
        if extra.exists() and extra.is_file():
            try:
                os.chmod(extra, 0o600)
            except OSError:
                pass
