"""Production-shaped product paths: register, sessions, roles, export."""

from __future__ import annotations

import os

import pytest

from product import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret-not-for-production-use")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_ready(client, tmp_path):
    r = client.get("/api/ready")
    assert r.status_code == 200
    assert r.json()["db"] is True
    assert "disk_free_mb" in r.json()
    assert "backup_age_hours" in r.json()
    assert "backup_ok" in r.json()
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "script-src 'self'" in (r.headers.get("content-security-policy") or "")
    page = client.get("/")
    assert page.headers.get("cross-origin-opener-policy") == "same-origin"
    pidf = tmp_path / "aistudio.pid"
    assert pidf.is_file()
    assert pidf.read_text(encoding="utf-8").strip().isdigit()


def test_register_empty_tenant_and_upload(client):
    r = client.post(
        "/api/auth/register",
        json={
            "org_name": "Nordstahl GmbH",
            "name": "Ines Hartung",
            "email": "ines@nordstahl.example",
            "password": "Stahlwerk2026!",
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    headers = {"Authorization": "Bearer " + token}
    assert r.json()["user"]["role"] == "admin"
    me = client.get("/api/me", headers=headers).json()
    assert me["org"]["name"] == "Nordstahl GmbH"
    assert me["demo"] is False

    ask = client.post("/api/ask", json={"q": "Reiserichtlinie"}, headers=headers)
    assert ask.status_code == 200
    assert not ask.json().get("sources")

    up = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("notiz.txt", "Der Sonderpreis für Titanlegierung beträgt 12,50 Euro.", "text/plain")},
    )
    assert up.status_code == 200, up.text
    found = client.post("/api/ask", json={"q": "Titanlegierung"}, headers=headers).json()
    assert found.get("sources") or "12,50" in (found.get("text") or "")

    fleet = client.get("/api/fleet", headers=headers).json()
    assert "auskunft" in fleet["leases"]


def test_logout_revokes_session(client):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    assert client.post("/api/auth/logout", headers=headers, json={}).status_code == 200
    r = client.get("/api/me", headers=headers)
    assert r.status_code == 401


def test_member_cannot_rent(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "org_name": "Member Test AG",
            "name": "Admin Person",
            "email": "admin@membertest.example",
            "password": "Passwort2026x",
        },
    )
    assert reg.status_code == 200, reg.text
    admin_h = {"Authorization": "Bearer " + reg.json()["token"]}
    added = client.post(
        "/api/users",
        headers=admin_h,
        json={
            "email": "member@membertest.example",
            "name": "Max Member",
            "role": "member",
            "password": "Passwort2026x",
        },
    )
    assert added.status_code == 200, added.text
    member_h = _login(client, "member@membertest.example", "Passwort2026x")
    denied = client.post(
        "/api/fleet", json={"agent_id": "reporting", "action": "rent"}, headers=member_h
    )
    assert denied.status_code == 403
    users = client.get("/api/users", headers=member_h)
    assert users.status_code == 403


def test_export_and_invoice_snapshot(client):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    client.post("/api/fleet", json={"agent_id": "reporting", "action": "rent"}, headers=headers)
    bill = client.get("/api/billing", headers=headers).json()
    assert bill["amount_cents"] == 40000
    assert bill.get("invoices")
    exp = client.get("/api/export", headers=headers)
    assert exp.status_code == 200
    payload = exp.json()
    assert payload["org"]["slug"] == "meridian"
    assert "users" in payload and "documents" in payload


def test_jobs_and_audit_reject_negative_limit(client):
    from product.api import _page_limit

    assert _page_limit(-1, cap=100, default=20) == 20
    assert _page_limit(0, cap=100, default=20) == 20
    assert _page_limit(500, cap=100, default=20) == 100
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    jobs = client.get("/api/jobs?limit=-1", headers=headers)
    assert jobs.status_code == 422
    audit = client.get("/api/audit?limit=-1", headers=headers)
    assert audit.status_code == 422
    ok = client.get("/api/jobs?limit=5", headers=headers)
    assert ok.status_code == 200


def test_search_rejects_huge_query(client):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    huge = client.get("/api/search", params={"q": "x" * 5000}, headers=headers)
    assert huge.status_code == 422
    ok = client.get("/api/search", params={"q": "Reiserichtlinie"}, headers=headers)
    assert ok.status_code == 200
    assert "hits" in ok.json()


def test_lockout(client, monkeypatch):
    monkeypatch.setattr("product.config.LOCKOUT_AFTER", 2)
    email = "katharina.vogel@meridian.example"
    client.post("/api/auth/login", json={"email": email, "password": "wrong-1"})
    client.post("/api/auth/login", json={"email": email, "password": "wrong-2"})
    locked = client.post("/api/auth/login", json={"email": email, "password": "Meridian2026!"})
    assert locked.status_code in {401, 423}


def test_login_unknown_email_still_hashes(client, monkeypatch):
    from product import auth

    monkeypatch.setattr(auth, "_PBKDF_ROUNDS", 2)
    auth._DUMMY_HASH = None
    assert auth.verify_password("wrong-password-1", None) is False
    assert auth._DUMMY_HASH
    unknown = client.post(
        "/api/auth/login",
        json={"email": "nobody@not-a-tenant.example", "password": "Meridian2026!"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "E-Mail oder Passwort falsch."
    wrong = client.post(
        "/api/auth/login",
        json={"email": "katharina.vogel@meridian.example", "password": "definitely-wrong-1"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "E-Mail oder Passwort falsch."
    reg = client.post(
        "/api/auth/register",
        json={
            "org_name": "Inaktiv GmbH",
            "name": "Ada Admin",
            "email": "ada@inaktiv.example",
            "password": "InaktivWerk26",
        },
    )
    assert reg.status_code == 200, reg.text
    admin_h = {"Authorization": "Bearer " + reg.json()["token"]}
    added = client.post(
        "/api/users",
        headers=admin_h,
        json={
            "email": "member@inaktiv.example",
            "name": "Max Member",
            "role": "member",
            "password": "InaktivWerk26",
        },
    )
    assert added.status_code == 200, added.text
    uid = added.json()["user"]["id"]
    patch = client.patch(
        f"/api/users/{uid}",
        headers=admin_h,
        json={"active": False},
    )
    assert patch.status_code == 200, patch.text
    inactive = client.post(
        "/api/auth/login",
        json={"email": "member@inaktiv.example", "password": "InaktivWerk26"},
    )
    assert inactive.status_code == 401
    assert inactive.json()["detail"] == "E-Mail oder Passwort falsch."


def test_weak_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={"org_name": "Kurz GmbH", "name": "A B", "email": "a@kurz.example", "password": "short"},
    )
    assert r.status_code == 400


def test_oversize_password_rejected(client):
    """PBKDF2 must not run on a megabyte-scale password (unauthenticated login)."""
    from product import auth

    huge = "Aa1" + ("x" * 400)
    assert auth.validate_password(huge) is not None
    login = client.post(
        "/api/auth/login",
        json={"email": "katharina.vogel@meridian.example", "password": huge},
    )
    assert login.status_code == 422
    reg = client.post(
        "/api/auth/register",
        json={
            "org_name": "Lang GmbH",
            "name": "Lang Name",
            "email": "lang@lang.example",
            "password": huge,
        },
    )
    assert reg.status_code == 422
    ok = auth.validate_password("GutesPasswort12")
    assert ok is None


def test_production_requires_secret(monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.delenv("AISTUDIO_SECRET", raising=False)
    monkeypatch.setattr(config, "SECRET", "dev-secret-change-me")
    with pytest.raises(RuntimeError):
        config.validate_runtime()


def test_secret_prev_accepts_old_tokens(monkeypatch):
    from product import auth

    old = "old-secret-not-for-production-xx"
    new = "new-secret-not-for-production-xx"
    monkeypatch.delenv("AISTUDIO_SECRET", raising=False)
    monkeypatch.delenv("AISTUDIO_SECRET_PREV", raising=False)
    monkeypatch.setattr(config, "SECRET", old)
    token = auth.issue_token({"sub": "user-rotate", "org": "org-x", "jti": "j1"})
    monkeypatch.setattr(config, "SECRET", new)
    monkeypatch.setenv("AISTUDIO_SECRET", new)
    assert auth.read_token(token) is None
    monkeypatch.setenv("AISTUDIO_SECRET_PREV", old)
    body = auth.read_token(token)
    assert body is not None
    assert body["sub"] == "user-rotate"


def test_health_hides_demo_email_in_production(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    h = client.get("/api/health").json()
    assert h.get("env") == "production"
    assert "demo_email" not in h
    assert "orgs" not in h
    assert "documents" not in h
    assert "llm" in h


def test_sessions_list_and_revoke_others(client):
    first = client.post(
        "/api/auth/login",
        json={"email": "katharina.vogel@meridian.example", "password": "Meridian2026!"},
    )
    assert first.status_code == 200
    h1 = {"Authorization": "Bearer " + first.json()["token"]}
    second = client.post(
        "/api/auth/login",
        json={"email": "katharina.vogel@meridian.example", "password": "Meridian2026!"},
    )
    h2 = {"Authorization": "Bearer " + second.json()["token"]}
    listed = client.get("/api/sessions", headers=h2).json()
    assert len(listed["sessions"]) >= 2
    assert sum(1 for s in listed["sessions"] if s["current"]) == 1
    assert client.post("/api/sessions/revoke-others", headers=h2, json={}).status_code == 200
    assert client.get("/api/me", headers=h1).status_code == 401
    assert client.get("/api/me", headers=h2).status_code == 200


def test_empty_kb_message_and_delete_doc(client):
    r = client.post(
        "/api/auth/register",
        json={
            "org_name": "Leerwerk GmbH",
            "name": "Lea Werk",
            "email": "lea@leerwerk.example",
            "password": "Leerwerk2026!",
        },
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": "Bearer " + r.json()["token"]}
    ask = client.post("/api/ask", json={"q": "Was steht im Vertrag?"}, headers=headers)
    assert ask.status_code == 200
    assert "leer" in ask.json()["text"].lower()
    up = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("vertrag.txt", "Der Wartungsvertrag endet am 31.12.2026.", "text/plain")},
    )
    assert up.status_code == 200
    doc_id = up.json()["id"]
    found = client.post("/api/ask", json={"q": "Wartungsvertrag"}, headers=headers).json()
    assert found.get("sources") or "31.12.2026" in (found.get("text") or "")
    me = client.get("/api/me", headers=headers).json()
    dest = config.upload_path(me["org"]["id"], doc_id)
    assert dest.is_file()
    assert client.delete(f"/api/docs/{doc_id}", headers=headers).status_code == 200
    assert not dest.exists()
    gone = client.post("/api/ask", json={"q": "Wartungsvertrag"}, headers=headers).json()
    assert "leer" in gone["text"].lower() or not gone.get("sources")


def test_security_headers_on_api(client):
    r = client.get("/api/ready")
    assert r.headers.get("permissions-policy")
    assert r.headers.get("x-frame-options") == "DENY"
    body = r.json()
    assert body["writable"] is True
    assert body.get("version")


def test_production_register_off_by_default(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.delenv("AISTUDIO_ALLOW_REGISTER", raising=False)
    r = client.post(
        "/api/auth/register",
        json={
            "org_name": "Closed GmbH",
            "name": "C Admin",
            "email": "c@closed.example",
            "password": "Closedwerk2026!",
        },
    )
    assert r.status_code == 403


def test_oversize_request_rejected(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "a@b.example", "password": "x"},
        headers={"content-length": "9000000"},
    )
    assert r.status_code == 413


def test_oversize_chunked_body_rejected(monkeypatch):
    """Chunked POST has no Content-Length — the cap must still hold."""
    monkeypatch.setattr(config, "MAX_REQUEST_BYTES", 32)
    from product.security import LimitRequestMiddleware

    captured = {}

    async def inner(scope, receive, send):
        msg = await receive()
        captured["n"] = len(msg.get("body") or b"")
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    app = LimitRequestMiddleware(inner)

    async def _call(chunks):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [(b"host", b"test")],
            "client": ("127.0.0.1", 1),
            "server": ("test", 80),
        }
        state = {"i": 0}
        sent = []

        async def receive():
            i = state["i"]
            if i >= len(chunks):
                return {"type": "http.disconnect"}
            body = chunks[i]
            state["i"] += 1
            return {
                "type": "http.request",
                "body": body,
                "more_body": i + 1 < len(chunks),
            }

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        start = next(m for m in sent if m["type"] == "http.response.start")
        return start["status"]

    import asyncio

    assert asyncio.run(_call([b"a" * 20, b"b" * 20])) == 413
    assert "n" not in captured
    assert asyncio.run(_call([b"ok"])) == 200
    assert captured["n"] == 2


def test_admin_sets_member_password(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "org_name": "Passwerk GmbH",
            "name": "Admin Person",
            "email": "admin@passwerk.example",
            "password": "Passwerk2026x",
        },
    )
    assert reg.status_code == 200, reg.text
    admin_h = {"Authorization": "Bearer " + reg.json()["token"]}
    added = client.post(
        "/api/users",
        headers=admin_h,
        json={
            "email": "member@passwerk.example",
            "name": "Max Member",
            "role": "member",
            "password": "Passwerk2026x",
        },
    )
    assert added.status_code == 200, added.text
    uid = added.json()["user"]["id"]
    reset = client.post(
        f"/api/users/{uid}/password",
        headers=admin_h,
        json={"password": "NeuesWerk2026!"},
    )
    assert reset.status_code == 200, reset.text
    old = client.post(
        "/api/auth/login",
        json={"email": "member@passwerk.example", "password": "Passwerk2026x"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/auth/login",
        json={"email": "member@passwerk.example", "password": "NeuesWerk2026!"},
    )
    assert new.status_code == 200


def test_bootstrap_creates_first_tenant(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "boot.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret-not-for-production-use")
    monkeypatch.setenv("AISTUDIO_ALLOW_DEMO_SEED", "false")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_ORG", "Start GmbH")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_EMAIL", "ada@start.example")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_PASSWORD", "Startwerk2026!")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_NAME", "Ada Admin")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/auth/login",
            json={"email": "ada@start.example", "password": "Startwerk2026!"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["user"]["role"] == "admin"
        assert r.json()["org"]["name"] == "Start GmbH"


def test_static_rejects_hidden_and_serves_app_js(client):
    assert client.get("/app.js").status_code == 200
    assert client.get("/.env").status_code == 404
    assert client.get("/../product/config.py").status_code == 404
    assert client.get("/data/aistudio.db").status_code == 404


def test_upload_strips_path_and_rejects_binary(client):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    up = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("../../etc/passwd.txt", "Nur Text aus der Richtlinie.", "text/plain")},
    )
    assert up.status_code == 200, up.text
    listed = client.get("/api/docs", headers=headers).json()
    titles = [d.get("title") for d in listed.get("docs") or []]
    assert "passwd.txt" in titles
    binary = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("note.txt", b"abc\x00def", "text/plain")},
    )
    assert binary.status_code == 400


def test_live_and_error_includes_request_id(client):
    live = client.get("/api/live")
    assert live.status_code == 200
    assert live.json()["ok"] is True
    assert live.json()["product"] == "aistudio"
    r = client.post("/api/ask", json={"q": "Reiserichtlinie"})
    assert r.status_code == 401
    body = r.json()
    assert body.get("request_id")
    assert r.headers.get("x-request-id")


def test_housekeeping_prunes_old_audit(client):
    from product import db, housekeeping

    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO audit_log (org_id, actor, action, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("org-old", "system", "ask", "alt", "2020-01-01T00:00:00"),
        )
        conn.commit()
        assert conn.execute(
            "SELECT COUNT(*) AS n FROM audit_log WHERE created_at < '2021-01-01'"
        ).fetchone()["n"] >= 1
        housekeeping.prune(conn)
        assert conn.execute(
            "SELECT COUNT(*) AS n FROM audit_log WHERE created_at < '2021-01-01'"
        ).fetchone()["n"] == 0
    finally:
        conn.close()


def test_rate_limiter_drops_idle_keys():
    import time
    from collections import deque

    from product import security

    security._hits.clear()
    security._sweep = 31
    security._hits["old"] = deque([time.time() - 200])
    assert security.rate_limited("fresh", 10) is False
    assert "old" not in security._hits
    assert "fresh" in security._hits
    security._hits.clear()
    security._sweep = 0


def test_metrics_has_no_tenant_secrets(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    blob = str(body)
    assert "sk-" not in blob.lower()
    assert "@meridian.example" not in blob
    assert body["ok"] is True
    assert "uptime_s" in body
    assert "disk_free_mb" in body
    assert "llm_calls" in body
    assert "budget_blocked" in body["llm_calls"]
    assert body["llm"]["per_user"] >= 1
    assert body["llm"]["per_user_day"] >= 1
    assert "password" not in blob.lower()
    prom = client.get("/api/metrics?format=prom")
    assert prom.status_code == 200
    text = prom.text
    assert "aistudio_up 1" in text
    assert "aistudio_llm_budget_blocked_total" in text
    assert "aistudio_backup_ok" in text
    assert "@meridian.example" not in text


def test_metrics_token_required(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_METRICS_TOKEN", "metrics-test-token")
    assert client.get("/api/metrics").status_code == 401
    bad = client.get("/api/metrics", headers={"X-Metrics-Token": "wrong"})
    assert bad.status_code == 401
    ok = client.get("/api/metrics", headers={"X-Metrics-Token": "metrics-test-token"})
    assert ok.status_code == 200
    bearer = client.get(
        "/api/metrics",
        headers={"Authorization": "Bearer metrics-test-token"},
    )
    assert bearer.status_code == 200


def test_login_rate_limit_sets_retry_after(client, monkeypatch):
    monkeypatch.setattr("product.api.rate_limited", lambda *a, **k: True)
    r = client.post(
        "/api/auth/login",
        json={"email": "a@b.example", "password": "x"},
    )
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"


def test_job_and_export_rate_limited(client, monkeypatch):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    monkeypatch.setattr("product.api.rate_limited", lambda *a, **k: True)
    job = client.post(
        "/api/agents/run",
        headers=headers,
        json={"agent_id": "reporting", "task": "Bitte die Lage kurz zusammenfassen."},
    )
    assert job.status_code == 429
    assert job.headers.get("retry-after") == "60"
    exp = client.get("/api/export", headers=headers)
    assert exp.status_code == 429


def test_password_change_rate_limited(client, monkeypatch):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    monkeypatch.setattr("product.api.rate_limited", lambda *a, **k: True)
    r = client.post(
        "/api/auth/password",
        headers=headers,
        json={"old_password": "Meridian2026!", "new_password": "NeuesWerk2026!"},
    )
    assert r.status_code == 429


def test_org_and_fleet_reject_huge_fields(client):
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    org = client.patch("/api/org", headers=headers, json={"name": "N" * 200})
    assert org.status_code == 422
    fleet = client.post(
        "/api/fleet",
        headers=headers,
        json={"agent_id": "a" * 120, "action": "rent"},
    )
    assert fleet.status_code == 422


def test_systemd_unit_rewrites_install_root():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    src = (root / "scripts" / "aistudio.service").read_text(encoding="utf-8")
    rendered = src.replace("/opt/aistudio", "/srv/studio")
    assert "WorkingDirectory=/srv/studio" in rendered
    assert "EnvironmentFile=-/srv/studio/.env" in rendered
    assert "/opt/aistudio" not in rendered
    assert "MemoryMax=512M" in src
    assert "User=aistudio" in src.splitlines()
    assert "Group=aistudio" in src.splitlines()
    rewritten = src
    rewritten = "\n".join(
        "User=deploy" if line == "User=aistudio" else
        "Group=deploy" if line == "Group=aistudio" else line
        for line in rewritten.splitlines()
    )
    assert "User=deploy" in rewritten.splitlines()
    assert "User=aistudio" not in rewritten.splitlines()
    assert "ReadWritePaths=/opt/aistudio/data" in src
    assert "ReadWritePaths=/opt/aistudio\n" not in src
    assert "CapabilityBoundingSet=" in src
    assert "StartLimitBurst=5" in src
    backup = (root / "scripts" / "aistudio-backup.service").read_text(encoding="utf-8")
    assert "User=aistudio" in backup
    assert "Group=aistudio" in backup
    assert "ReadWritePaths=/opt/aistudio/data" in backup
    assert "PrivateNetwork=true" in backup
    assert "RestrictAddressFamilies=none" in backup
    assert "MemoryMax=256M" in backup
    install = (root / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "--systemd" in install
    assert "Dienstbenutzer: aistudio" in install
    assert "useradd --system" in install
    assert "640" in install
    assert "AISTUDIO_ALLOWED_HOSTS" in install
    assert "AISTUDIO_METRICS_TOKEN" in install
    assert "AISTUDIO_BACKUP_PASS" in install
    assert "nachgetragen: AISTUDIO_BACKUP_PASS" in install
    assert "data/backup.env" in install
    assert "EnvironmentFile=-/opt/aistudio/data/backup.env" in backup
    assert "EnvironmentFile=-/opt/aistudio/data/backup.env" not in src
    assert "AISTUDIO_PROXY_IPS" in install
    assert "--password-file" in install
    assert "data/aistudio.pid" in install
    assert "data/bootstrap.env" in install
    assert "AISTUDIO_RESTORE_FORCE" in (root / "scripts" / "restore.sh").read_text(encoding="utf-8")
    assert "chmod 600 oder 400" in install
    nginx = (root / "scripts" / "nginx-aistudio.conf").read_text(encoding="utf-8")
    assert "ssl_certificate" not in nginx
    assert "limit_req" in nginx
    assert "/api/auth/(login|register)" in nginx
    tls = (root / "scripts" / "nginx-aistudio.tls.conf").read_text(encoding="utf-8")
    assert "ssl_certificate" in tls
    assert "/api/auth/(login|register)" in tls


def test_client_ip_ignores_spoofed_forwarded_for(monkeypatch):
    from types import SimpleNamespace

    from product.security import client_ip

    monkeypatch.setenv("AISTUDIO_TRUST_PROXY", "true")
    monkeypatch.delenv("AISTUDIO_PROXY_IPS", raising=False)

    def req(peer: str, xff: str | None = "203.0.113.9"):
        headers = {"x-forwarded-for": xff} if xff else {}
        return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)

    assert client_ip(req("203.0.113.10")) == "203.0.113.10"
    assert client_ip(req("testclient")) == "testclient"
    assert client_ip(req("127.0.0.1")) == "203.0.113.9"
    assert client_ip(req("::1")) == "203.0.113.9"
    assert client_ip(req("::ffff:127.0.0.1")) == "203.0.113.9"
    monkeypatch.setenv("AISTUDIO_PROXY_IPS", "10.0.0.0/8")
    assert client_ip(req("10.8.0.4")) == "203.0.113.9"
    assert client_ip(req("11.0.0.1")) == "11.0.0.1"
    monkeypatch.setenv("AISTUDIO_PROXY_IPS", "*")
    assert client_ip(req("198.51.100.2")) == "203.0.113.9"
    monkeypatch.setenv("AISTUDIO_TRUST_PROXY", "false")
    monkeypatch.setenv("AISTUDIO_PROXY_IPS", "*")
    assert client_ip(req("127.0.0.1")) == "127.0.0.1"
    assert config.uvicorn_forwarded_allow_ips() is None
    monkeypatch.setenv("AISTUDIO_TRUST_PROXY", "true")
    monkeypatch.setenv("AISTUDIO_PROXY_IPS", "127.0.0.1,::1")
    assert config.uvicorn_forwarded_allow_ips() == "127.0.0.1,::1"
    monkeypatch.setenv("AISTUDIO_PROXY_IPS", "*")
    assert config.uvicorn_forwarded_allow_ips() == "*"


def test_orphan_upload_pruned(client, tmp_path):
    from product import db, housekeeping

    orphan = tmp_path / "uploads" / "orgx" / "upload-gone.txt"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("rest", encoding="utf-8")
    conn = db.connect()
    try:
        removed = housekeeping.prune_orphan_uploads(conn)
        assert removed >= 1
        assert not orphan.exists()
    finally:
        conn.close()


def test_org_upload_quota(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_ORG_UPLOAD_MB", "1")
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    blob = "x" * 600_000
    first = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("a.txt", blob, "text/plain")},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/docs/upload",
        headers=headers,
        files={"file": ("b.txt", blob, "text/plain")},
    )
    assert second.status_code == 413
    me = client.get("/api/me", headers=headers).json()
    assert me["storage"]["limit_bytes"] == 1024 * 1024
    assert me["storage"]["used_bytes"] >= 600_000


def test_idle_session_revoked(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_SESSION_IDLE", "60")
    headers = _login(client, "katharina.vogel@meridian.example", "Meridian2026!")
    assert client.get("/api/me", headers=headers).status_code == 200
    from product import db

    conn = db.connect()
    try:
        conn.execute(
            "UPDATE sessions SET last_seen_at = ?",
            ("2020-01-01T00:00:00+00:00",),
        )
        conn.commit()
    finally:
        conn.close()
    assert client.get("/api/me", headers=headers).status_code == 401


def test_production_hides_openapi_and_checks_hosts(monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.setenv("AISTUDIO_ALLOWED_HOSTS", "studio.example.com")
    assert config.docs_kwargs()["openapi_url"] is None
    assert config.docs_kwargs()["docs_url"] is None
    assert config.allowed_hosts() == ["studio.example.com"]
    from fastapi import FastAPI
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.testclient import TestClient

    app = FastAPI(**config.docs_kwargs())
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts())

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app, base_url="http://studio.example.com") as c:
        assert c.get("/ping").status_code == 200
        assert c.get("/openapi.json").status_code == 404
        assert c.get("/docs").status_code == 404
    with TestClient(app, base_url="http://evil.example") as c:
        assert c.get("/ping").status_code == 400


def test_production_metrics_require_token(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.delenv("AISTUDIO_METRICS_TOKEN", raising=False)
    assert client.get("/api/metrics").status_code == 401


def test_bootstrap_strips_password_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AISTUDIO_SECRET=test-secret-not-for-production-use\n"
        "AISTUDIO_BOOTSTRAP_ORG=Start GmbH\n"
        "AISTUDIO_BOOTSTRAP_EMAIL=ada@start.example\n"
        "AISTUDIO_BOOTSTRAP_PASSWORD=Startwerk2026!\n"
        "AISTUDIO_BOOTSTRAP_NAME=Ada Admin\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "boot.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret-not-for-production-use")
    monkeypatch.setenv("AISTUDIO_ENV_FILE", str(env_file))
    monkeypatch.setenv("AISTUDIO_ALLOW_DEMO_SEED", "false")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_ORG", "Start GmbH")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_EMAIL", "ada@start.example")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_PASSWORD", "Startwerk2026!")
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_NAME", "Ada Admin")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/auth/login",
            json={"email": "ada@start.example", "password": "Startwerk2026!"},
        )
        assert r.status_code == 200, r.text
    text = env_file.read_text(encoding="utf-8")
    assert "AISTUDIO_BOOTSTRAP_PASSWORD" not in text
    assert "Startwerk2026!" not in text
    assert "AISTUDIO_SECRET=test-secret-not-for-production-use" in text
    import os

    assert os.environ.get("AISTUDIO_BOOTSTRAP_PASSWORD") is None


def test_bootstrap_from_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "boot.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret-not-for-production-use")
    monkeypatch.setenv("AISTUDIO_ALLOW_DEMO_SEED", "false")
    for key in (
        "AISTUDIO_BOOTSTRAP_ORG",
        "AISTUDIO_BOOTSTRAP_EMAIL",
        "AISTUDIO_BOOTSTRAP_PASSWORD",
        "AISTUDIO_BOOTSTRAP_NAME",
    ):
        monkeypatch.delenv(key, raising=False)
    boot = tmp_path / "bootstrap.env"
    boot.write_text(
        "AISTUDIO_BOOTSTRAP_ORG=Datei GmbH\n"
        "AISTUDIO_BOOTSTRAP_EMAIL=ada@datei.example\n"
        "AISTUDIO_BOOTSTRAP_PASSWORD=Datewerk2026!\n"
        "AISTUDIO_BOOTSTRAP_NAME=Ada Datei\n",
        encoding="utf-8",
    )
    os.chmod(boot, 0o600)
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/auth/login",
            json={"email": "ada@datei.example", "password": "Datewerk2026!"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["org"]["name"] == "Datei GmbH"
    assert not boot.exists()


def test_leftover_bootstrap_stripped_when_orgs_exist(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "boot.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret-not-for-production-use")
    monkeypatch.setenv("AISTUDIO_ALLOW_DEMO_SEED", "false")
    from product import db, tenancy

    conn = db.connect()
    try:
        db.init_db(conn)
        tenancy.register_org(
            conn,
            org_name="Schon da GmbH",
            email="ada@schon.example",
            name="Ada",
            password="SchonDa2026!",
        )
        conn.commit()
    finally:
        conn.close()
    boot = tmp_path / "bootstrap.env"
    boot.write_text(
        "AISTUDIO_BOOTSTRAP_ORG=Zu spaet GmbH\n"
        "AISTUDIO_BOOTSTRAP_EMAIL=spaet@example.com\n"
        "AISTUDIO_BOOTSTRAP_PASSWORD=ZuSpaet2026!\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AISTUDIO_BOOTSTRAP_PASSWORD", "ZuSpaet2026!")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/auth/login",
            json={"email": "ada@schon.example", "password": "SchonDa2026!"},
        )
        assert r.status_code == 200, r.text
        late = c.post(
            "/api/auth/login",
            json={"email": "spaet@example.com", "password": "ZuSpaet2026!"},
        )
        assert late.status_code == 401
    assert not boot.exists()
    assert os.environ.get("AISTUDIO_BOOTSTRAP_PASSWORD") is None


def test_signing_secrets_skip_demo_prev(monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.setenv("AISTUDIO_SECRET", "production-secret-not-demo-xx")
    monkeypatch.setenv("AISTUDIO_SECRET_PREV", "dev-secret-change-me")
    keys = config.signing_secrets()
    assert "dev-secret-change-me" not in keys
    assert "production-secret-not-demo-xx" in keys


def test_harden_data_dir_chmod_wal(tmp_path, monkeypatch):
    db_path = tmp_path / "aistudio.db"
    wal = tmp_path / "aistudio.db-wal"
    shm = tmp_path / "aistudio.db-shm"
    db_path.write_bytes(b"x")
    wal.write_bytes(b"y")
    shm.write_bytes(b"z")
    os.chmod(db_path, 0o644)
    os.chmod(wal, 0o644)
    os.chmod(shm, 0o644)
    bakenv = tmp_path / "backup.env"
    bakenv.write_text("AISTUDIO_BACKUP_PASS=not-read-by-product\n", encoding="utf-8")
    os.chmod(bakenv, 0o644)
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.DB_PATH", db_path)
    config.harden_data_dir()
    assert (db_path.stat().st_mode & 0o777) == 0o600
    assert (wal.stat().st_mode & 0o777) == 0o600
    assert (shm.stat().st_mode & 0o777) == 0o600
    assert (bakenv.stat().st_mode & 0o777) == 0o600
    assert (tmp_path.stat().st_mode & 0o777) == 0o700


def test_backup_age_from_dir(tmp_path, monkeypatch):
    backups = tmp_path / "backups"
    backups.mkdir()
    stamp = backups / "aistudio-20200101T000000Z.db"
    stamp.write_bytes(b"sqlite")
    os.utime(stamp, (1_577_836_800, 1_577_836_800))
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    age = config.latest_backup_age_hours()
    assert age is not None
    assert age > 24
    assert config.backup_max_age_hours() >= 1
    monkeypatch.setenv("AISTUDIO_READY_REQUIRE_BACKUP", "true")
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        r = c.get("/api/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["backup_ok"] is False
        assert body["ok"] is False
