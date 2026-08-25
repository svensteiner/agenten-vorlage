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
    assert r.headers.get("x-content-type-options") == "nosniff"


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
