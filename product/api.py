"""HTTP API for the tenant product. Does not modify core/ or platform/."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from product import auth, catalog, config, db, retrieval
from product.runtime import run_agent_job
from product.seed import ensure_seeded, insert_document

router = APIRouter()


def _conn():
    conn = db.connect()
    ensure_seeded(conn)
    return conn


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
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
        return db.row_dict(row)  # type: ignore[return-value]
    finally:
        conn.close()


class LoginBody(BaseModel):
    email: str
    password: str


class AskBody(BaseModel):
    q: str = Field(min_length=1)
    module: str | None = None


class FleetBody(BaseModel):
    agent_id: str = ""
    action: str
    reason: str | None = None


class RunBody(BaseModel):
    agent_id: str
    task: str = Field(min_length=3)


@router.get("/health")
def health() -> dict[str, Any]:
    conn = _conn()
    try:
        org = conn.execute("SELECT * FROM orgs LIMIT 1").fetchone()
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        return {
            "ok": True,
            "product": "aistudio",
            "host": config.HOST,
            "port": config.PORT,
            "org": org["name"] if org else None,
            "documents": docs,
            "demo_email": config.DEMO_EMAIL,
        }
    finally:
        conn.close()


@router.post("/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    conn = _conn()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (body.email.strip().lower(),),
        ).fetchone()
        if not user or not auth.verify_password(body.password, user["password_hash"]):
            db.audit("anon", body.email, "login_failed", body.email, conn=conn)
            conn.commit()
            raise HTTPException(401, "E-Mail oder Passwort falsch.")
        token = auth.issue_token(
            {
                "sub": user["id"],
                "org": user["org_id"],
                "role": user["role"],
                "email": user["email"],
            }
        )
        db.audit(user["org_id"], user["email"], "login", user["email"], conn=conn)
        conn.commit()
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            },
        }
    finally:
        conn.close()


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            },
            "org": db.row_dict(org) if org else None,
        }
    finally:
        conn.close()


@router.get("/docs")
def docs(user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        items = retrieval.list_documents(conn=conn, org_id=user["org_id"], role=user["role"])
        return {"docs": [retrieval.to_frontend_doc(d) for d in items]}
    finally:
        conn.close()


@router.get("/search")
def search(q: str, user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        hits, withheld = retrieval.retrieve(
            user["org_id"], q, role=user["role"], conn=conn
        )
        return {
            "hits": [retrieval.to_frontend_doc(h) for h in hits],
            "withheld": retrieval.withheld_payload(withheld),
        }
    finally:
        conn.close()


@router.post("/ask")
def ask(body: AskBody, user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        db.audit(user["org_id"], user["email"], "ask", body.q[:400], conn=conn)
        conn.commit()
        return retrieval.ask(user["org_id"], body.q, role=user["role"], conn=conn)
    finally:
        conn.close()


@router.get("/agents")
def agents(user: dict = Depends(current_user)) -> dict[str, Any]:
    return {"agents": catalog.catalog()}


@router.get("/fleet")
def get_fleet(user: dict = Depends(current_user)) -> dict[str, Any]:
    conn = _conn()
    try:
        return catalog.fleet_state(user["org_id"], conn=conn)
    finally:
        conn.close()


@router.post("/fleet")
def mutate_fleet(body: FleetBody, user: dict = Depends(current_user)) -> dict[str, Any]:
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
    conn = _conn()
    try:
        return catalog.billing_payload(user["org_id"], conn=conn)
    finally:
        conn.close()


@router.post("/agents/run")
def run_agent(body: RunBody, user: dict = Depends(current_user)) -> dict[str, Any]:
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
            f"{body.agent_id}: {body.task[:200]}",
            conn=conn,
        )
        conn.commit()
        result["job_id"] = job_id
        return result
    finally:
        conn.close()


@router.get("/jobs")
def jobs(user: dict = Depends(current_user), limit: int = 20) -> dict[str, Any]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, agent_id, task, status, created_at FROM jobs "
            "WHERE org_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["org_id"], limit),
        ).fetchall()
        return {"jobs": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/audit")
def audit(user: dict = Depends(current_user), limit: int = 50) -> dict[str, Any]:
    if user["role"] not in {"board", "admin", "cfo"}:
        raise HTTPException(403, "Kein Zugriff auf das Audit-Log.")
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE org_id IN (?, 'anon') ORDER BY created_at DESC LIMIT ?",
            (user["org_id"], limit),
        ).fetchall()
        return {"events": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/docs/upload")
async def upload_doc(
    user: dict = Depends(current_user),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(400, "Datei zu groß (max. 2 MB in dieser Instanz).")
    text = raw.decode("utf-8", errors="replace")
    stamp = db.now_iso()
    doc_id = "upload-" + stamp.replace(":", "").replace("-", "")
    dest = config.DATA_DIR / "uploads" / f"{doc_id}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    conn = _conn()
    try:
        insert_document(
            conn,
            user["org_id"],
            {
                "id": doc_id,
                "title": file.filename or "Upload",
                "type": "Upload",
                "module": "wissen",
                "path": f"Uploads › {file.filename or doc_id}",
                "author": user["name"],
                "date": stamp[:10],
                "snippet": text[:180].replace("\n", " "),
                "body": text[:50_000],
                "body_parts": [{"t": text[:50_000], "highlight": False}],
                "locked": False,
            },
        )
        db.audit(user["org_id"], user["email"], "upload", file.filename or doc_id, conn=conn)
        conn.commit()
        return {"ok": True, "id": doc_id}
    finally:
        conn.close()
