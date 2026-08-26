"""SQLite persistence: orgs, users, documents (FTS5), leases, jobs, invoices, audit."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    tagline TEXT DEFAULT '',
    billing_email TEXT DEFAULT '',
    country TEXT DEFAULT 'DE',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_login_at TEXT,
    FOREIGN KEY (org_id) REFERENCES orgs(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    jti TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    last_seen_at TEXT,
    ip TEXT DEFAULT '',
    user_agent TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS documents (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    org_id TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT DEFAULT '',
    module TEXT DEFAULT 'wissen',
    path TEXT DEFAULT '',
    author TEXT DEFAULT '',
    date TEXT DEFAULT '',
    snippet TEXT DEFAULT '',
    body TEXT DEFAULT '',
    body_json TEXT DEFAULT '[]',
    locked INTEGER NOT NULL DEFAULT 0,
    locked_role TEXT,
    classification TEXT,
    extra_json TEXT DEFAULT '{}',
    FOREIGN KEY (org_id) REFERENCES orgs(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, snippet, body, author, type,
    content='documents',
    content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS leases (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    since TEXT NOT NULL,
    included INTEGER NOT NULL DEFAULT 0,
    UNIQUE (org_id, agent_id),
    FOREIGN KEY (org_id) REFERENCES orgs(id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    output_json TEXT DEFAULT '{}',
    run_meta_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (org_id) REFERENCES orgs(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    period TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    status TEXT NOT NULL,
    lines_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (org_id) REFERENCES orgs(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_usage (
    day TEXT NOT NULL,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    calls INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, scope, key)
);

CREATE INDEX IF NOT EXISTS idx_documents_org ON documents(org_id);
CREATE INDEX IF NOT EXISTS idx_jobs_org ON jobs(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_log(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_jti ON sessions(jti);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path or config.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    config.harden_data_dir()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = connect()
        _local.conn = conn
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    c = conn or get_conn()
    c.executescript(SCHEMA)
    migrate(c)
    c.commit()


def _add_column(conn: sqlite3.Connection, table: str, column: str, spec: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column in cols:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {spec}")


def migrate(conn: sqlite3.Connection) -> None:
    """Additive columns for databases created before the production schema."""
    try:
        _add_column(conn, "orgs", "billing_email", "TEXT DEFAULT ''")
        _add_column(conn, "orgs", "country", "TEXT DEFAULT 'DE'")
        _add_column(conn, "users", "active", "INTEGER NOT NULL DEFAULT 1")
        _add_column(conn, "users", "failed_logins", "INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "users", "locked_until", "TEXT")
        _add_column(conn, "users", "last_login_at", "TEXT")
        _add_column(conn, "sessions", "last_seen_at", "TEXT")
    except sqlite3.OperationalError:
        # Table may not exist yet on a brand-new file before SCHEMA ran.
        return


@contextmanager
def tx(conn: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
    c = conn or get_conn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def audit(org_id: str, actor: str, action: str, detail: str = "", conn: sqlite3.Connection | None = None) -> None:
    c = conn or get_conn()
    c.execute(
        "INSERT INTO audit_log (org_id, actor, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (org_id, actor, action, detail[:2000], now_iso()),
    )


def parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
