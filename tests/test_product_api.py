"""Product API: login, retrieval, fleet, billing, jobs."""

from __future__ import annotations

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as c:
        yield c


def _login(client, email="katharina.vogel@meridian.example", password="Meridian2026!"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_index(client):
    h = client.get("/api/health")
    assert h.status_code == 200
    body = h.json()
    assert body["ok"] is True
    assert body["documents"] >= 20
    page = client.get("/")
    assert page.status_code == 200
    assert "AI Studio" in page.text
    js = client.get("/app.js")
    assert js.status_code == 200
    pc = client.get("/product-client.js")
    assert pc.status_code == 200


def test_login_rejects_bad_password(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "katharina.vogel@meridian.example", "password": "wrong"},
    )
    assert r.status_code == 401


def test_ask_requires_auth(client):
    r = client.post("/api/ask", json={"q": "Reiserichtlinie"})
    assert r.status_code == 401


def test_cfo_ask_finds_travel_policy(client):
    headers = _login(client)
    r = client.post("/api/ask", json={"q": "Wo finde ich die aktuelle Reiserichtlinie?"}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sources"]
    ids = [s["docId"] for s in data["sources"]]
    assert "reiserichtlinie-2026" in ids
    assert data["confidence"] >= 70


def test_cfo_cannot_read_board_docs(client):
    headers = _login(client)
    r = client.post("/api/ask", json={"q": "Nordstern"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    source_ids = [s["docId"] for s in data.get("sources") or []]
    assert "akquisition-nordstern" not in source_ids
    withheld = data.get("withheld") or {}
    assert withheld.get("count", 0) >= 1
    assert "akquisition-nordstern" in (withheld.get("docs") or [])


def test_board_can_read_locked_docs(client):
    headers = _login(client, "markus.brandt@meridian.example")
    r = client.post("/api/ask", json={"q": "Nordstern Akquisition"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    ids = [s["docId"] for s in data.get("sources") or []]
    assert "akquisition-nordstern" in ids


def test_fleet_rent_pause_billing_cancel(client):
    headers = _login(client)
    fleet = client.get("/api/fleet", headers=headers).json()
    assert "auskunft" in fleet["leases"]
    assert fleet["leases"]["auskunft"]["included"] is True

    rented = client.post(
        "/api/fleet", json={"agent_id": "reporting", "action": "rent"}, headers=headers
    )
    assert rented.status_code == 200, rented.text
    leases = rented.json()["leases"]
    assert leases["reporting"]["status"] == "active"

    bill = client.get("/api/billing", headers=headers).json()
    assert bill["amount_cents"] == 40000

    paused = client.post(
        "/api/fleet", json={"agent_id": "reporting", "action": "pause"}, headers=headers
    )
    assert paused.status_code == 200
    bill2 = client.get("/api/billing", headers=headers).json()
    assert bill2["amount_cents"] == 0

    client.post("/api/fleet", json={"agent_id": "reporting", "action": "resume"}, headers=headers)
    cancelled = client.post(
        "/api/fleet", json={"agent_id": "reporting", "action": "cancel"}, headers=headers
    )
    assert cancelled.status_code == 200
    assert "reporting" not in cancelled.json()["leases"]

    blocked = client.post(
        "/api/fleet", json={"agent_id": "auskunft", "action": "cancel"}, headers=headers
    )
    assert blocked.status_code == 400


def test_cannot_run_unleased_agent(client):
    headers = _login(client)
    r = client.post(
        "/api/agents/run",
        json={"agent_id": "reporting", "task": "Erstelle die Vorstandsvorlage Q1"},
        headers=headers,
    )
    assert r.status_code == 403


def test_run_included_agent(client):
    headers = _login(client)
    r = client.post(
        "/api/agents/run",
        json={"agent_id": "auskunft", "task": "Fasse die Reiserichtlinie zusammen"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("job_id")
    assert "Reiserichtlinie" in data.get("text", "") or data.get("sources")


def test_upload_and_ask(client):
    headers = _login(client)
    files = {"file": ("notiz.txt", "Der Sonderpreis für Titanlegierung beträgt 12,50 Euro pro kg.", "text/plain")}
    up = client.post("/api/docs/upload", headers=headers, files=files)
    assert up.status_code == 200, up.text
    r = client.post("/api/ask", json={"q": "Titanlegierung Sonderpreis"}, headers=headers)
    assert r.status_code == 200
    text = r.json().get("text") or ""
    ids = [s["docId"] for s in r.json().get("sources") or []]
    assert "12,50" in text or any(i.startswith("upload-") for i in ids)


def test_audit_for_cfo(client):
    headers = _login(client)
    client.post("/api/ask", json={"q": "Reiserichtlinie"}, headers=headers)
    r = client.get("/api/audit", headers=headers)
    assert r.status_code == 200
    actions = [e["action"] for e in r.json()["events"]]
    assert "ask" in actions
    assert "login" in actions
