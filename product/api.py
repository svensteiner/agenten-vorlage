"""HTTP API for the tenant product. Does not modify core/ or platform/."""

from __future__ import annotations

import json
import secrets
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from product import auth, catalog, config, db, retrieval, tenancy
from product.runtime import run_agent_job
from product.security import client_ip, metrics_authorized, rate_limit_error, rate_limited
from product.seed import delete_document, ensure_seeded, insert_document

router = APIRouter()


def _conn():
    conn = db.connect()
    ensure_seeded(conn)
    return conn


def _demo_present(conn) -> bool:
    row = conn.execute("SELECT 1 FROM orgs WHERE slug = 'meridian'").fetchone()
    return bool(row)


def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Anmeldung erforderlich.")
    token = authorization.split(" ", 1)[1].strip()
    claims = auth.read_token(token)
    if not claims:
        raise HTTPException(401, "Sitzung ungültig oder abgelaufen.")
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND org_id = ?",
            (claims.get("sub"), claims.get("org")),
        ).fetchone()
        if not row:
            raise HTTPException(401, "Benutzer unbekannt.")
        user = db.row_dict(row)
        assert user is not None
        if not user.get("active", 1):
            raise HTTPException(401, "Konto deaktiviert.")
        jti = claims.get("jti") or ""
        if not tenancy.session_ok(conn, jti, user["id"]):
            raise HTTPException(401, "Sitzung ungültig oder abgelaufen.")
        conn.commit()
        user["_jti"] = jti
        user["_ip"] = client_ip(request)
        return user
    finally:
        conn.close()


def _require(role_ok: bool, message: str = "Keine Berechtigung.") -> None:
    if not role_ok:
        raise HTTPException(403, message)


def _page_limit(limit: int, *, cap: int, default: int) -> int:
    """SQLite treats LIMIT < 0 as unlimited — never pass a negative through."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = default
    if n < 1:
        return default
    return min(n, cap)


JOB_LIST_PREVIEW_CHARS = 180


def _plain_preview(text: str, n: int = JOB_LIST_PREVIEW_CHARS) -> str:
    """Strip tags and collapse whitespace so list rows never carry HTML or bodies."""
    cleaned: list[str] = []
    skip = False
    for ch in text or "":
        if ch == "<":
            skip = True
            continue
        if skip:
            if ch == ">":
                skip = False
                cleaned.append(" ")
            continue
        cleaned.append(ch)
    return " ".join("".join(cleaned).split())[:n]


class LoginBody(BaseModel):
    email: str = Field(max_length=auth.MAX_EMAIL_CHARS)
    password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


class RegisterBody(BaseModel):
    org_name: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=auth.MAX_EMAIL_CHARS)
    password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


class AskBody(BaseModel):
    q: str = Field(min_length=1, max_length=4000)
    module: str | None = Field(default=None, max_length=40)


class FleetBody(BaseModel):
    agent_id: str = Field(default="", max_length=80)
    action: str = Field(max_length=40)
    reason: str | None = Field(default=None, max_length=500)


class RunBody(BaseModel):
    agent_id: str = Field(max_length=80)
    task: str = Field(min_length=3, max_length=4000)


class PasswordBody(BaseModel):
    old_password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)
    new_password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


class UserAddBody(BaseModel):
    email: str = Field(max_length=auth.MAX_EMAIL_CHARS)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="member", max_length=32)
    password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


class UserPasswordBody(BaseModel):
    password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


class UserPatchBody(BaseModel):
    role: str | None = Field(default=None, max_length=32)
    active: bool | None = None


class OrgPatchBody(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=240)
    billing_email: str | None = Field(default=None, max_length=auth.MAX_EMAIL_CHARS)


class PurgeBody(BaseModel):
    password: str = Field(max_length=auth.MAX_PASSWORD_CHARS)


def _ops_status() -> dict[str, Any]:
    """LLM/backup snapshot for authenticated callers and development health."""
    from product import llm

    age = config.latest_backup_age_hours()
    return {
        "llm": llm.public_status(),
        "backup_age_hours": age,
        "backup_ok": age is not None and age <= config.backup_max_age_hours(),
    }


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    # 180/min ≈ 3/s — Docker HEALTHCHECK is 30s; a 1/s LB probe stays green.
    if rate_limited("health:" + client_ip(request), 180):
        raise rate_limit_error()
    conn = _conn()
    try:
        conn.execute("SELECT 1").fetchone()
        payload = {
            "ok": True,
            "product": "aistudio",
            "version": config.VERSION,
            "env": config.env_name(),
            "allow_register": config.allow_register(),
        }
        if config.is_production():
            return payload
        demo = _demo_present(conn)
        orgs = conn.execute("SELECT COUNT(*) AS n FROM orgs").fetchone()["n"]
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        payload.update(_ops_status())
        payload["demo"] = demo
        payload["orgs"] = orgs
        payload["documents"] = docs
        if demo:
            payload["demo_email"] = config.DEMO_EMAIL
        return payload
    finally:
        conn.close()


@router.get("/ready")
def ready(request: Request) -> dict[str, Any]:
    if rate_limited("ready:" + client_ip(request), 180):
        raise rate_limit_error()
    conn = db.connect()
    try:
        db.init_db(conn)
        conn.execute("SELECT 1").fetchone()
        data = config.DATA_DIR
        data.mkdir(parents=True, exist_ok=True)
        probe = data / ".write-ok"
        writable = False
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            writable = True
        except OSError:
            writable = False
        free_mb = 0
        try:
            free_mb = shutil.disk_usage(data).free // (1024 * 1024)
        except OSError:
            free_mb = 0
        age = config.latest_backup_age_hours()
        max_age = config.backup_max_age_hours()
        backup_ok = age is not None and age <= max_age
        payload = {
            "ok": bool(writable),
            "db": True,
            "writable": writable,
            "disk_free_mb": free_mb,
            "version": config.VERSION,
        }
        if not config.is_production():
            from product import llm

            payload["llm"] = llm.public_status()
            payload["backup_age_hours"] = age
            payload["backup_ok"] = backup_ok
        if not writable:
            return JSONResponse(payload, status_code=503)
        require_backup = config.require_backup_for_ready()
        if require_backup and not backup_ok:
            payload["ok"] = False
            return JSONResponse(payload, status_code=503)
        return payload
    finally:
        conn.close()


@router.get("/live")
def live(request: Request) -> dict[str, Any]:
    """Process liveness — no database. Use /api/ready for traffic."""
    if rate_limited("live:" + client_ip(request), 300):
        raise rate_limit_error()
    return {"ok": True, "product": "aistudio", "version": config.VERSION}


@router.get("/metrics")
def metrics(request: Request):
    """Ops snapshot: sizes and counters only — no tenant text, no keys.

    Optional ``AISTUDIO_METRICS_TOKEN`` (Header ``X-Metrics-Token`` or Bearer).
    In Produktion ist das Token Pflicht.
    ``?format=prom`` yields Prometheus text.
    """
    if rate_limited("metrics:" + client_ip(request), 60):
        raise rate_limit_error()
    if not metrics_authorized(request):
        raise HTTPException(401, "Metriken erfordern ein Token.")
    payload = _metrics_payload()
    if (request.query_params.get("format") or "").strip().lower() in {"prom", "prometheus"}:
        return PlainTextResponse(_metrics_prom(payload), media_type="text/plain; version=0.0.4")
    return payload


def _metrics_payload() -> dict[str, Any]:
    import time

    from product import housekeeping, llm, security

    data = config.DATA_DIR
    free_mb = 0
    try:
        free_mb = shutil.disk_usage(data).free // (1024 * 1024)
    except OSError:
        free_mb = 0
    db_bytes = config.DB_PATH.stat().st_size if config.DB_PATH.is_file() else 0
    wal_path = Path(str(config.DB_PATH) + "-wal")
    wal_bytes = wal_path.stat().st_size if wal_path.is_file() else 0
    age = config.latest_backup_age_hours()
    return {
        "ok": True,
        "product": "aistudio",
        "version": config.VERSION,
        "uptime_s": int(time.time() - config.STARTED_AT),
        "disk_free_mb": free_mb,
        "db_bytes": db_bytes,
        "wal_bytes": wal_bytes,
        "backup_age_hours": age,
        "backup_ok": age is not None and age <= config.backup_max_age_hours(),
        "rate_limiter_keys": security.key_count(),
        "housekeeping": housekeeping.snapshot(),
        "llm": llm.public_status(),
        "llm_calls": llm.call_stats(),
    }


def _metrics_prom(payload: dict[str, Any]) -> str:
    calls = payload.get("llm_calls") or {}
    lines = [
        "# HELP aistudio_up 1 if the process answers metrics.",
        "# TYPE aistudio_up gauge",
        "aistudio_up 1",
        "# TYPE aistudio_uptime_seconds gauge",
        "aistudio_uptime_seconds %s" % payload.get("uptime_s", 0),
        "# TYPE aistudio_disk_free_megabytes gauge",
        "aistudio_disk_free_megabytes %s" % payload.get("disk_free_mb", 0),
        "# TYPE aistudio_db_bytes gauge",
        "aistudio_db_bytes %s" % payload.get("db_bytes", 0),
        "# TYPE aistudio_wal_bytes gauge",
        "aistudio_wal_bytes %s" % payload.get("wal_bytes", 0),
        "# TYPE aistudio_rate_limiter_keys gauge",
        "aistudio_rate_limiter_keys %s" % payload.get("rate_limiter_keys", 0),
        "# TYPE aistudio_llm_complete_ok_total counter",
        "aistudio_llm_complete_ok_total %s" % calls.get("complete_ok", 0),
        "# TYPE aistudio_llm_complete_fail_total counter",
        "aistudio_llm_complete_fail_total %s" % calls.get("complete_fail", 0),
        "# TYPE aistudio_llm_budget_blocked_total counter",
        "aistudio_llm_budget_blocked_total %s" % calls.get("budget_blocked", 0),
        "# TYPE aistudio_llm_circuit_open_total counter",
        "aistudio_llm_circuit_open_total %s" % calls.get("circuit_open", 0),
        "# TYPE aistudio_backup_ok gauge",
        "aistudio_backup_ok %s" % (1 if payload.get("backup_ok") else 0),
        "# TYPE aistudio_backup_age_hours gauge",
        "aistudio_backup_age_hours %s" % (
            payload["backup_age_hours"] if payload.get("backup_age_hours") is not None else -1
        ),
    ]
    return "\n".join(lines) + "\n"


@router.post("/auth/register")
def register(body: RegisterBody, request: Request) -> dict[str, Any]:
    if not config.allow_register():
        raise HTTPException(403, "Registrierung ist auf dieser Instanz deaktiviert.")
    if rate_limited("reg:" + client_ip(request), 8):
        raise rate_limit_error()
    conn = _conn()
    try:
        try:
            created = tenancy.register_org(
                conn,
                org_name=body.org_name,
                email=body.email,
                name=body.name,
                password=body.password,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        user = created["user"]
        token = tenancy.open_session(
            conn, user, ip=client_ip(request), user_agent=request.headers.get("user-agent", "")
        )
        conn.commit()
        return {
            "token": token,
            "user": tenancy.public_user(user),
            "org": db.row_dict(created["org"]),
        }
    finally:
        conn.close()


@router.post("/auth/login")
def login(body: LoginBody, request: Request) -> dict[str, Any]:
    if rate_limited("login:" + client_ip(request), 30):
        raise rate_limit_error()
    conn = _conn()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (body.email.strip().lower(),),
        ).fetchone()
        stored = user["password_hash"] if user else None
        password_ok = auth.verify_password(body.password, stored)
        if not user or not password_ok:
            if user:
                user_d = db.row_dict(user)
                assert user_d is not None
                tenancy.record_login_failure(conn, user_d)
                db.audit(user["org_id"], body.email, "login_failed", body.email, conn=conn)
            else:
                db.audit("anon", body.email, "login_failed", body.email, conn=conn)
            conn.commit()
            raise HTTPException(401, "E-Mail oder Passwort falsch.")
        user_d = db.row_dict(user)
        assert user_d is not None
        if not user_d.get("active", 1):
            raise HTTPException(401, "E-Mail oder Passwort falsch.")
        if tenancy.is_locked(user_d):
            raise HTTPException(423, "Konto vorübergehend gesperrt. Bitte später erneut versuchen.")
        tenancy.record_login_success(conn, user_d)
        token = tenancy.open_session(
            conn, user_d, ip=client_ip(request), user_agent=request.headers.get("user-agent", "")
        )
        db.audit(user["org_id"], user["email"], "login", user["email"], conn=conn)
        conn.commit()
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        return {
            "token": token,
            "user": tenancy.public_user(user_d),
            "org": db.row_dict(org),
        }
    finally:
        conn.close()


@router.post("/auth/logout")
def logout(user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        tenancy.revoke_session(conn, user.get("_jti") or "")
        db.audit(user["org_id"], user["email"], "logout", user["email"], conn=conn)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/auth/password")
def password(body: PasswordBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("pwd:" + user["id"], 10):
        raise rate_limit_error()
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        try:
            tenancy.change_password(conn, dict(row), old=body.old_password, new=body.new_password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        tenancy.revoke_user_sessions(conn, user["id"], keep_jti=user.get("_jti"))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/sessions")
def sessions(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("sessions:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        items = tenancy.list_user_sessions(conn, user["id"], user.get("_jti") or "")
        return {"sessions": items}
    finally:
        conn.close()


@router.post("/sessions/revoke-others")
def revoke_other_sessions(user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        tenancy.revoke_user_sessions(conn, user["id"], keep_jti=user.get("_jti"))
        db.audit(user["org_id"], user["email"], "sessions_revoke_others", user["email"], conn=conn)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        try:
            tenancy.revoke_session_id(conn, user["id"], session_id, user.get("_jti") or "")
        except KeyError:
            raise HTTPException(404, "Sitzung nicht gefunden.")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        db.audit(user["org_id"], user["email"], "session_revoke", session_id, conn=conn)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("me:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        used = config.org_upload_bytes(user["org_id"])
        limit = config.org_upload_limit_bytes()
        docs_n = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE org_id = ?", (user["org_id"],)
        ).fetchone()["n"]
        ops = _ops_status()
        return {
            "user": tenancy.public_user(user),
            "org": db.row_dict(org) if org else None,
            "demo": _demo_present(conn) and user["org_id"] == "org-meridian",
            "storage": {
                "used_bytes": used,
                "limit_bytes": limit,
                "docs": int(docs_n),
                "docs_limit": config.org_max_docs(),
            },
            "llm": ops["llm"],
            "backup_age_hours": ops["backup_age_hours"],
            "backup_ok": ops["backup_ok"],
        }
    finally:
        conn.close()


@router.patch("/org")
def patch_org(body: OrgPatchBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    conn = _conn()
    try:
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        if not org:
            raise HTTPException(404, "Mandant nicht gefunden.")
        name = body.name.strip() if body.name else org["name"]
        tagline = body.tagline if body.tagline is not None else org["tagline"]
        billing = body.billing_email.strip() if body.billing_email is not None else org["billing_email"]
        conn.execute(
            "UPDATE orgs SET name = ?, tagline = ?, billing_email = ? WHERE id = ?",
            (name, tagline, billing, user["org_id"]),
        )
        db.audit(user["org_id"], user["email"], "org_update", name, conn=conn)
        conn.commit()
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        return {"org": db.row_dict(org)}
    finally:
        conn.close()


@router.get("/users")
def list_users(user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    if rate_limited("users:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, email, name, role, active, last_login_at FROM users "
            "WHERE org_id = ? ORDER BY email",
            (user["org_id"],),
        ).fetchall()
        return {"users": [tenancy.public_user(r) for r in rows]}
    finally:
        conn.close()


@router.post("/users")
def add_user(body: UserAddBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    if rate_limited("useradd:" + user["id"], 8):
        raise rate_limit_error()
    conn = _conn()
    try:
        try:
            created = tenancy.add_user(
                conn,
                user["org_id"],
                email=body.email,
                name=body.name,
                role=body.role,
                password=body.password,
                actor=user["email"],
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        conn.commit()
        return {"user": created}
    finally:
        conn.close()


@router.patch("/users/{user_id}")
def patch_user(user_id: str, body: UserPatchBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    if user_id == user["id"] and body.active is False:
        raise HTTPException(400, "Sie können sich nicht selbst deaktivieren.")
    conn = _conn()
    try:
        try:
            updated = tenancy.set_user_state(
                conn,
                user["org_id"],
                user_id,
                role=body.role,
                active=body.active,
                actor=user["email"],
            )
        except KeyError:
            raise HTTPException(404, "Benutzer nicht gefunden.")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        conn.commit()
        return {"user": updated}
    finally:
        conn.close()


@router.post("/users/{user_id}/password")
def admin_password(user_id: str, body: UserPasswordBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    if rate_limited("adminpwd:" + user["id"], 10):
        raise rate_limit_error()
    conn = _conn()
    try:
        try:
            tenancy.admin_set_password(
                conn, user["org_id"], user_id, password=body.password, actor=user["email"]
            )
        except KeyError:
            raise HTTPException(404, "Benutzer nicht gefunden.")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/docs")
def docs(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("docs:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        cap = config.org_max_docs()
        items = retrieval.list_documents(
            conn=conn,
            org_id=user["org_id"],
            role=user["role"],
            limit=cap,
            summaries=True,
        )
        return {
            "docs": [retrieval.to_frontend_doc(d, summary=True) for d in items],
            "limit": cap,
        }
    finally:
        conn.close()


@router.get("/docs/{doc_id}")
def doc_one(doc_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("docs:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        item = retrieval.get_document(user["org_id"], doc_id, user["role"], conn=conn)
        if not item:
            raise HTTPException(404, "Dokument nicht gefunden.")
        return retrieval.to_frontend_doc(item)
    finally:
        conn.close()


@router.delete("/docs/{doc_id}")
def remove_doc(doc_id: str, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_delete_docs(user["role"]))
    conn = _conn()
    try:
        ok = delete_document(conn, user["org_id"], doc_id)
        if not ok:
            raise HTTPException(404, "Dokument nicht gefunden.")
        db.audit(user["org_id"], user["email"], "doc_delete", doc_id, conn=conn)
        conn.commit()
        dest = config.upload_path(user["org_id"], doc_id)
        dest.unlink(missing_ok=True)
        config.invalidate_org_upload_bytes(user["org_id"])
        return {"ok": True}
    finally:
        conn.close()


@router.get("/search")
def search(
    user: dict = Depends(current_user),
    q: str = Query(..., min_length=1, max_length=4000),
) -> dict[str, Any]:
    if rate_limited("search:" + user["id"], 120):
        raise rate_limit_error()
    conn = _conn()
    try:
        hits, withheld = retrieval.retrieve(
            user["org_id"], q, role=user["role"], conn=conn
        )
        return {
            "hits": [retrieval.to_frontend_doc(h, summary=True) for h in hits],
            "withheld": retrieval.withheld_payload(withheld),
        }
    finally:
        conn.close()


@router.post("/ask")
def ask(body: AskBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("ask:" + user["id"], 120):
        raise rate_limit_error()
    conn = _conn()
    try:
        db.audit(
            user["org_id"],
            user["email"],
            "ask",
            "chars=%s" % len(body.q or ""),
            conn=conn,
        )
        answer = retrieval.ask(
            user["org_id"], body.q, role=user["role"], conn=conn, user_id=user["id"]
        )
        if answer.get("via") == "llm":
            db.audit(
                user["org_id"],
                user["email"],
                "llm",
                "%s %s" % (answer.get("llm_provider") or "-", answer.get("llm_model") or "-"),
                conn=conn,
            )
        conn.commit()
        return answer
    finally:
        conn.close()


@router.get("/agents")
def agents(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("agents:" + user["id"], 60):
        raise rate_limit_error()
    return {"agents": catalog.catalog()}


@router.get("/fleet")
def get_fleet(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("fleet:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        return catalog.fleet_state(user["org_id"], conn=conn)
    finally:
        conn.close()


@router.post("/fleet")
def mutate_fleet(body: FleetBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_mutate_fleet(user["role"]), "Nur Admin oder CFO dürfen die Flotte ändern.")
    conn = _conn()
    try:
        try:
            state = catalog.apply_fleet_action(
                user["org_id"], body.agent_id, body.action, conn=conn
            )
        except KeyError:
            raise HTTPException(404, "Agent nicht gefunden.")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        tenancy.persist_invoice(conn, user["org_id"])
        db.audit(
            user["org_id"],
            user["email"],
            f"fleet_{body.action}",
            body.agent_id or "all",
            conn=conn,
        )
        conn.commit()
        return {"ok": True, **state}
    finally:
        conn.close()


@router.get("/billing")
def billing(user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("billing:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        payload = catalog.billing_payload(user["org_id"], conn=conn)
        invoices = conn.execute(
            "SELECT id, period, amount_cents, currency, status, created_at FROM invoices "
            "WHERE org_id = ? ORDER BY period DESC LIMIT 12",
            (user["org_id"],),
        ).fetchall()
        payload["invoices"] = [dict(r) for r in invoices]
        return payload
    finally:
        conn.close()


@router.post("/agents/run")
def run_agent(body: RunBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    if rate_limited("job:" + user["id"], 20):
        raise rate_limit_error()
    conn = _conn()
    try:
        spec = catalog.by_id(body.agent_id)
        if not spec:
            raise HTTPException(404, "Agent nicht gefunden.")
        lease = conn.execute(
            "SELECT * FROM leases WHERE org_id = ? AND agent_id = ? AND status IN ('active','paused','cancelling')",
            (user["org_id"], body.agent_id),
        ).fetchone()
        if not lease and not spec.get("included"):
            raise HTTPException(403, "Agent ist nicht gemietet.")
        if lease and lease["status"] == "paused":
            raise HTTPException(400, "Agent ist pausiert. Setzen Sie ihn fort, um Aufträge zu starten.")
        job_id = "job-" + db.now_iso().replace(":", "").replace("-", "") + "-" + body.agent_id
        conn.execute(
            "INSERT INTO jobs (id, org_id, agent_id, task, status, output_json, run_meta_json, created_at) "
            "VALUES (?, ?, ?, ?, 'running', '{}', ?, ?)",
            (
                job_id,
                user["org_id"],
                body.agent_id,
                body.task,
                json.dumps({"user_id": user["id"]}, ensure_ascii=False),
                db.now_iso(),
            ),
        )
        conn.commit()
        result = run_agent_job(
            conn,
            org_id=user["org_id"],
            role=user["role"],
            agent_id=body.agent_id,
            task=body.task,
            user_id=user["id"],
        )
        conn.execute(
            "UPDATE jobs SET status = ?, output_json = ?, run_meta_json = ? WHERE id = ?",
            (
                "done" if result.get("ok") else "error",
                json.dumps(result, ensure_ascii=False),
                json.dumps(
                    {
                        "user_id": user["id"],
                        "run_id": result.get("run_id"),
                        "finished_at": result.get("finished_at"),
                    },
                    ensure_ascii=False,
                ),
                job_id,
            ),
        )
        db.audit(
            user["org_id"],
            user["email"],
            "agent_run",
            "%s chars=%s" % (body.agent_id, len(body.task or "")),
            conn=conn,
        )
        conn.commit()
        result["job_id"] = job_id
        return result
    finally:
        conn.close()


@router.get("/jobs")
def jobs(
    user: dict = Depends(current_user),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    if rate_limited("jobs:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        preview_n = JOB_LIST_PREVIEW_CHARS
        text_n = preview_n * 8
        rows = conn.execute(
            "SELECT id, agent_id, substr(task, 1, ?) AS task, status, created_at, "
            "json_extract(output_json, '$.ok') AS ok, "
            "substr(COALESCE(json_extract(output_json, '$.text'), ''), 1, ?) AS text "
            "FROM jobs WHERE org_id = ? ORDER BY created_at DESC LIMIT ?",
            (
                preview_n,
                text_n,
                user["org_id"],
                _page_limit(limit, cap=100, default=20),
            ),
        ).fetchall()
        items = []
        for r in rows:
            ok_raw = r["ok"]
            items.append(
                {
                    "id": r["id"],
                    "agent_id": r["agent_id"],
                    "task": (r["task"] or "")[:preview_n],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "ok": None if ok_raw is None else bool(ok_raw),
                    "preview": _plain_preview(r["text"] or "", preview_n),
                }
            )
        return {"jobs": items}
    finally:
        conn.close()


@router.get("/audit")
def audit(
    user: dict = Depends(current_user),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    _require(tenancy.can_see_audit(user["role"]), "Kein Zugriff auf das Audit-Log.")
    if rate_limited("audit:" + user["id"], 60):
        raise rate_limit_error()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE org_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["org_id"], _page_limit(limit, cap=200, default=50)),
        ).fetchall()
        return {"events": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/export")
def export(user: dict = Depends(current_user)) -> JSONResponse:
    _require(tenancy.can_export(user["role"]), "Kein Export-Recht.")
    if rate_limited("export:" + user["id"], 6):
        raise rate_limit_error()
    conn = _conn()
    try:
        payload = tenancy.export_tenant(conn, user["org_id"], user["role"])
        db.audit(user["org_id"], user["email"], "export", "tenant-json", conn=conn)
        conn.commit()
        return JSONResponse(
            payload,
            headers={"Content-Disposition": 'attachment; filename="aistudio-export.json"'},
        )
    finally:
        conn.close()


@router.post("/org/purge")
def purge(body: PurgeBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    _require(tenancy.can_manage_users(user["role"]))
    if rate_limited("purge:" + user["id"], 8):
        raise rate_limit_error()
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not row or not auth.verify_password(body.password, row["password_hash"]):
            raise HTTPException(401, "Passwort falsch.")
        tenancy.purge_org(conn, user["org_id"])
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/docs/upload")
async def upload_doc(
    user: dict = Depends(current_user),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if rate_limited("up:" + user["id"], 40):
        raise rate_limit_error()
    raw = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(400, "Datei zu groß (max. 2 MB in dieser Instanz).")
    if b"\x00" in raw:
        raise HTTPException(400, "Binärdateien werden nicht angenommen.")
    given = (file.filename or "upload.txt").replace("\\", "/")
    name = given.rsplit("/", 1)[-1].lower()
    if not name or name.startswith(".") or ".." in name:
        name = "upload.txt"
    if not name.endswith((".txt", ".md", ".csv", ".json", ".log")):
        raise HTTPException(400, "Nur Textformate (.txt, .md, .csv, .json).")
    conn = _conn()
    try:
        n_docs = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE org_id = ?", (user["org_id"],)
        ).fetchone()["n"]
        cap = config.org_max_docs()
        if n_docs >= cap:
            raise HTTPException(
                413,
                "Dokumentenlimit des Mandanten erreicht (%s Dateien)." % cap,
            )
        limit = config.org_upload_limit_bytes()
        if limit:
            used = config.org_upload_bytes(user["org_id"], fresh=True)
            if used + len(raw) > limit:
                mb = max(1, limit // (1024 * 1024))
                raise HTTPException(
                    413,
                    "Speicherlimit des Mandanten erreicht (%s MB)." % mb,
                )
        title = (file.filename or "Upload").replace("\\", "/").rsplit("/", 1)[-1][:180]
        text = raw.decode("utf-8", errors="replace")
        stamp = db.now_iso()
        doc_id = "upload-" + stamp.replace(":", "").replace("-", "") + "-" + secrets.token_hex(4)
        dest = config.upload_path(user["org_id"], doc_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        insert_document(
            conn,
            user["org_id"],
            {
                "id": doc_id,
                "title": title or "Upload",
                "type": "Upload",
                "module": "wissen",
                "path": f"Uploads › {title or doc_id}",
                "author": user["name"],
                "date": stamp[:10],
                "snippet": text[:180].replace("\n", " "),
                "body": text[:50_000],
                "body_parts": [{"t": text[:50_000], "highlight": False}],
                "locked": False,
            },
        )
        db.audit(user["org_id"], user["email"], "upload", title or doc_id, conn=conn)
        conn.commit()
        config.invalidate_org_upload_bytes(user["org_id"])
        return {"ok": True, "id": doc_id}
    finally:
        conn.close()
