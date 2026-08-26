"""Mandanten, Nutzer, Sitzungen, DSGVO-Export — additiv zur Demo-Schicht."""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from product import auth, catalog, config, db, retrieval

ROLES = ("admin", "cfo", "board", "member")


def _uid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex[:12]


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return (slug[:40] or "mandant")


def can_manage_users(role: str) -> bool:
    return role == "admin"


def can_mutate_fleet(role: str) -> bool:
    return role in {"admin", "cfo"}


def can_see_audit(role: str) -> bool:
    return role in {"admin", "cfo", "board"}


def can_export(role: str) -> bool:
    return role in {"admin", "cfo"}


def can_delete_docs(role: str) -> bool:
    return role in {"admin", "cfo"}


def public_user(row) -> dict[str, Any]:
    item = db.row_dict(row) if not isinstance(row, dict) else dict(row)
    assert item is not None
    return {
        "id": item["id"],
        "email": item["email"],
        "name": item["name"],
        "role": item["role"],
        "active": bool(item.get("active", 1)),
        "last_login_at": item.get("last_login_at"),
    }


def unique_slug(conn, base: str) -> str:
    slug = slugify(base)
    n = 0
    candidate = slug
    while conn.execute("SELECT 1 FROM orgs WHERE slug = ?", (candidate,)).fetchone():
        n += 1
        candidate = f"{slug}-{n}"
    return candidate


def grant_included(conn, org_id: str) -> None:
    now = db.now_iso()
    for agent in catalog.catalog():
        if not agent.get("included"):
            continue
        exists = conn.execute(
            "SELECT 1 FROM leases WHERE org_id = ? AND agent_id = ?",
            (org_id, agent["id"]),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO leases (id, org_id, agent_id, status, since, included) VALUES (?, ?, ?, 'active', 'inklusive', 1)",
            (_uid("lease"), org_id, agent["id"]),
        )


def register_org(conn, *, org_name: str, email: str, name: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    org_name = (org_name or "").strip()
    name = (name or "").strip()
    if len(org_name) < 2:
        raise ValueError("Firmenname fehlt.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("E-Mail ungültig.")
    problem = auth.validate_password(password, email)
    if problem:
        raise ValueError(problem)
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise ValueError("Diese E-Mail ist bereits registriert.")
    now = db.now_iso()
    org_id = _uid("org")
    user_id = _uid("user")
    slug = unique_slug(conn, org_name)
    conn.execute(
        "INSERT INTO orgs (id, name, slug, tagline, billing_email, country, created_at) VALUES (?, ?, ?, '', ?, 'DE', ?)",
        (org_id, org_name, slug, email, now),
    )
    conn.execute(
        """INSERT INTO users (id, org_id, email, name, password_hash, role, created_at, active)
           VALUES (?, ?, ?, ?, ?, 'admin', ?, 1)""",
        (user_id, org_id, email, name or email, auth.hash_password(password), now),
    )
    grant_included(conn, org_id)
    db.audit(org_id, email, "register", org_name, conn=conn)
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    org = conn.execute("SELECT * FROM orgs WHERE id = ?", (org_id,)).fetchone()
    return {"user": user, "org": org}


def is_locked(user: dict[str, Any]) -> bool:
    until = user.get("locked_until")
    if not until:
        return False
    try:
        ts = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts > datetime.now(timezone.utc)


def record_login_failure(conn, user) -> None:
    fails = int(user["failed_logins"] or 0) + 1
    locked = None
    if fails >= config.LOCKOUT_AFTER:
        locked = (datetime.now(timezone.utc) + timedelta(minutes=config.LOCKOUT_MINUTES)).replace(microsecond=0).isoformat()
        fails = 0
    conn.execute(
        "UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
        (fails, locked, user["id"]),
    )


def record_login_success(conn, user) -> None:
    conn.execute(
        "UPDATE users SET failed_logins = 0, locked_until = NULL, last_login_at = ? WHERE id = ?",
        (db.now_iso(), user["id"]),
    )


def prune_sessions(conn) -> None:
    """Drop expired rows so the session table does not grow without bound."""
    now = db.now_iso()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0).isoformat()
    conn.execute(
        "DELETE FROM sessions WHERE revoked_at IS NOT NULL AND revoked_at < ?",
        (cutoff,),
    )


def list_user_sessions(conn, user_id: str, current_jti: str) -> list[dict[str, Any]]:
    prune_sessions(conn)
    rows = conn.execute(
        """SELECT id, jti, created_at, expires_at, ip, user_agent
           FROM sessions WHERE user_id = ? AND revoked_at IS NULL
           ORDER BY created_at DESC LIMIT 30""",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
            "ip": r["ip"] or "",
            "user_agent": (r["user_agent"] or "")[:120],
            "current": r["jti"] == current_jti,
        }
        for r in rows
    ]


def revoke_session_id(conn, user_id: str, session_id: str, current_jti: str) -> None:
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not row:
        raise KeyError(session_id)
    if row["jti"] == current_jti:
        raise ValueError("Die aktuelle Sitzung beenden Sie über Abmelden.")
    revoke_session(conn, row["jti"])


def open_session(conn, user, *, ip: str = "", user_agent: str = "") -> str:
    prune_sessions(conn)
    jti = uuid.uuid4().hex
    now = int(datetime.now(timezone.utc).timestamp())
    exp = now + config.TOKEN_TTL_SECONDS
    conn.execute(
        """INSERT INTO sessions (id, jti, user_id, org_id, created_at, expires_at, ip, user_agent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            _uid("sess"),
            jti,
            user["id"],
            user["org_id"],
            db.now_iso(),
            datetime.fromtimestamp(exp, timezone.utc).replace(microsecond=0).isoformat(),
            (ip or "")[:80],
            (user_agent or "")[:240],
        ),
    )
    return auth.issue_token(
        {
            "sub": user["id"],
            "org": user["org_id"],
            "role": user["role"],
            "email": user["email"],
            "jti": jti,
        }
    )


def session_ok(conn, jti: str, user_id: str) -> bool:
    if not jti:
        return not config.is_production()
    row = conn.execute(
        "SELECT * FROM sessions WHERE jti = ? AND user_id = ?",
        (jti, user_id),
    ).fetchone()
    if not row or row["revoked_at"]:
        return False
    try:
        exp = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return False
    except ValueError:
        return False
    return True


def revoke_session(conn, jti: str) -> None:
    if not jti:
        return
    conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL",
        (db.now_iso(), jti),
    )


def revoke_user_sessions(conn, user_id: str, *, keep_jti: str | None = None) -> None:
    if keep_jti:
        conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND jti != ? AND revoked_at IS NULL",
            (db.now_iso(), user_id, keep_jti),
        )
    else:
        conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (db.now_iso(), user_id),
        )


def bootstrap_if_empty(conn) -> dict[str, Any] | None:
    """Create the first tenant from env when the database has no orgs yet."""
    if conn.execute("SELECT 1 FROM orgs LIMIT 1").fetchone():
        return None
    spec = config.bootstrap_spec()
    if not spec:
        return None
    created = register_org(
        conn,
        org_name=spec["org_name"],
        email=spec["email"],
        name=spec["name"],
        password=spec["password"],
    )
    db.audit(created["org"]["id"], "system", "bootstrap", spec["org_name"], conn=conn)
    return created


def admin_set_password(conn, org_id: str, user_id: str, *, password: str, actor: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM users WHERE id = ? AND org_id = ?", (user_id, org_id)
    ).fetchone()
    if not row:
        raise KeyError(user_id)
    problem = auth.validate_password(password, row["email"])
    if problem:
        raise ValueError(problem)
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (auth.hash_password(password), user_id),
    )
    revoke_user_sessions(conn, user_id)
    db.audit(org_id, actor, "password_reset", row["email"], conn=conn)
    return public_user(row)


def add_user(conn, org_id: str, *, email: str, name: str, role: str, password: str, actor: str) -> dict[str, Any]:
    email = email.strip().lower()
    role = (role or "member").strip()
    if role not in ROLES:
        raise ValueError("Unbekannte Rolle.")
    problem = auth.validate_password(password, email)
    if problem:
        raise ValueError(problem)
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise ValueError("Diese E-Mail ist bereits vergeben.")
    user_id = _uid("user")
    conn.execute(
        """INSERT INTO users (id, org_id, email, name, password_hash, role, created_at, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
        (user_id, org_id, email, name.strip() or email, auth.hash_password(password), role, db.now_iso()),
    )
    db.audit(org_id, actor, "user_add", f"{email} ({role})", conn=conn)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row)


def set_user_state(conn, org_id: str, user_id: str, *, role: str | None, active: bool | None, actor: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM users WHERE id = ? AND org_id = ?", (user_id, org_id)
    ).fetchone()
    if not row:
        raise KeyError(user_id)
    if role is not None:
        if role not in ROLES:
            raise ValueError("Unbekannte Rolle.")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        db.audit(org_id, actor, "user_role", f"{row['email']} → {role}", conn=conn)
    if active is not None:
        conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
        if not active:
            revoke_user_sessions(conn, user_id)
        db.audit(org_id, actor, "user_active" if active else "user_disable", row["email"], conn=conn)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row)


def change_password(conn, user, *, old: str, new: str) -> None:
    if not auth.verify_password(old, user["password_hash"]):
        raise ValueError("Aktuelles Passwort ist falsch.")
    problem = auth.validate_password(new, user["email"])
    if problem:
        raise ValueError(problem)
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (auth.hash_password(new), user["id"]),
    )
    db.audit(user["org_id"], user["email"], "password_change", user["email"], conn=conn)


def persist_invoice(conn, org_id: str) -> None:
    preview = catalog.invoice_preview(org_id, conn=conn)
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    lines = json.dumps(preview["lines"], ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM invoices WHERE org_id = ? AND period = ?",
        (org_id, period),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE invoices SET amount_cents = ?, lines_json = ?, status = 'draft' WHERE id = ?",
            (preview["amount_cents"], lines, existing["id"]),
        )
        return
    conn.execute(
        """INSERT INTO invoices (id, org_id, period, amount_cents, currency, status, lines_json, created_at)
           VALUES (?, ?, ?, ?, 'EUR', 'draft', ?, ?)""",
        (_uid("inv"), org_id, period, preview["amount_cents"], lines, db.now_iso()),
    )


def export_tenant(conn, org_id: str, role: str) -> dict[str, Any]:
    org = db.row_dict(conn.execute("SELECT * FROM orgs WHERE id = ?", (org_id,)).fetchone())
    users = [
        public_user(r)
        for r in conn.execute(
            "SELECT * FROM users WHERE org_id = ? ORDER BY email", (org_id,)
        ).fetchall()
    ]
    docs = [retrieval.to_frontend_doc(d) for d in retrieval.list_documents(org_id, role, conn=conn)]
    bodies = {
        r["id"]: r["body"]
        for r in conn.execute("SELECT id, body FROM documents WHERE org_id = ?", (org_id,)).fetchall()
    }
    visible_ids = {d["id"] for d in docs if not d.get("denied")}
    for d in docs:
        d["body"] = bodies.get(d["id"], "") if d["id"] in visible_ids else ""
    jobs = [dict(r) for r in conn.execute(
        "SELECT id, agent_id, task, status, created_at FROM jobs WHERE org_id = ? ORDER BY created_at",
        (org_id,),
    ).fetchall()]
    audit = [dict(r) for r in conn.execute(
        "SELECT actor, action, detail, created_at FROM audit_log WHERE org_id = ? ORDER BY created_at",
        (org_id,),
    ).fetchall()]
    invoices = [dict(r) for r in conn.execute(
        "SELECT id, period, amount_cents, currency, status, lines_json, created_at FROM invoices WHERE org_id = ?",
        (org_id,),
    ).fetchall()]
    return {
        "exported_at": db.now_iso(),
        "product": "aistudio",
        "version": config.VERSION,
        "org": org,
        "users": users,
        "fleet": catalog.fleet_state(org_id, conn=conn),
        "documents": docs,
        "jobs": jobs,
        "invoices": invoices,
        "audit": audit,
    }


def purge_org(conn, org_id: str) -> None:
    doc_rows = conn.execute("SELECT rowid FROM documents WHERE org_id = ?", (org_id,)).fetchall()
    for row in doc_rows:
        conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (row["rowid"],))
    for table in ("documents", "leases", "jobs", "invoices", "audit_log", "sessions"):
        conn.execute(f"DELETE FROM {table} WHERE org_id = ?", (org_id,))
    conn.execute("DELETE FROM users WHERE org_id = ?", (org_id,))
    conn.execute("DELETE FROM orgs WHERE id = ?", (org_id,))
    uploads = config.DATA_DIR / "uploads" / config.org_dir(org_id)
    if uploads.is_dir():
        import shutil

        shutil.rmtree(uploads, ignore_errors=True)
