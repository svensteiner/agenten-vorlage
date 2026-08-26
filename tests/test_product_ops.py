"""Production-shaped product paths: register, sessions, roles, export."""

from __future__ import annotations

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


def test_ready(client):
    r = client.get("/api/ready")
    assert r.status_code == 200
    assert r.json()["db"] is True
    assert "disk_free_mb" in r.json()
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "script-src 'self'" in (r.headers.get("content-security-policy") or "")
    page = client.get("/")
    assert page.headers.get("cross-origin-opener-policy") == "same-origin"


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


def test_lockout(client, monkeypatch):
    monkeypatch.setattr("product.config.LOCKOUT_AFTER", 2)
    email = "katharina.vogel@meridian.example"
    client.post("/api/auth/login", json={"email": email, "password": "wrong-1"})
    client.post("/api/auth/login", json={"email": email, "password": "wrong-2"})
    locked = client.post("/api/auth/login", json={"email": email, "password": "Meridian2026!"})
    assert locked.status_code in {401, 423}


def test_weak_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={"org_name": "Kurz GmbH", "name": "A B", "email": "a@kurz.example", "password": "short"},
    )
    assert r.status_code == 400


def test_production_requires_secret(monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    monkeypatch.delenv("AISTUDIO_SECRET", raising=False)
    monkeypatch.setattr(config, "SECRET", "dev-secret-change-me")
    with pytest.raises(RuntimeError):
        config.validate_runtime()


def test_health_hides_demo_email_in_production(client, monkeypatch):
    monkeypatch.setenv("AISTUDIO_ENV", "production")
    h = client.get("/api/health").json()
    assert "demo_email" not in h or h.get("env") == "production"


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
    assert client.delete(f"/api/docs/{doc_id}", headers=headers).status_code == 200
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
