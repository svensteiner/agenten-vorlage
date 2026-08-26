"""Product model gateway: excerpts only, default in-boundary, no prompt logs."""

from __future__ import annotations

import logging

from product import llm


def test_sanitize_strips_script_and_handlers():
    raw = '<p>Tagegeld 28 €</p><script>alert(1)</script><b onclick="x()">Hotel</b>'
    cleaned = llm.sanitize_html(raw)
    assert "script" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "Tagegeld" in cleaned
    assert "Hotel" in cleaned


def test_excerpts_drop_full_body():
    hits = [
        {
            "id": "d1",
            "title": "Reiserichtlinie",
            "path": "/intern/reise.md",
            "body": ("SECRET_FULL_BODY " * 400) + "Tagegeld 28 Euro",
            "snippet": "Tagegeld 28 Euro",
        }
    ]
    excerpts = llm.excerpts_from_hits(hits, "Tagegeld")
    blob = " ".join(e["quote"] for e in excerpts)
    assert "Tagegeld" in blob or "28" in blob
    assert blob.count("SECRET_FULL_BODY") <= 2
    assert "body" not in excerpts[0]


def test_default_egress_blocks_openai_even_with_key(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    called = []

    class Boom:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            called.append(True)
            raise AssertionError("cloud call must not happen")

    monkeypatch.setattr(llm.httpx, "Client", Boom)
    result = llm.complete(system="sys", user="Frage: intern")
    assert result["ok"] is False
    assert result["error"] == "egress_blocked"
    assert called == []
    status = llm.public_status()
    assert status["ready"] is False
    assert status["sends_excerpts"] is False
    assert "sk-test" not in str(status)


def test_openai_compat_sends_excerpts_only(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "cloud")
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "<p>Hotel <b>140 €</b></p><script>x()</script>"
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr(llm.httpx, "Client", FakeClient)
    result = llm.complete(
        system="Antworte knapp.",
        user="Frage: Hotel\n\nAuszüge:\n\n[Reise]\nHotel 140 Euro",
    )
    assert result["ok"] is True
    assert "140" in result["text"]
    assert "script" not in result["text"].lower()
    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["model"] == "gpt-4o-mini"
    user = captured["json"]["messages"][1]["content"]
    assert "Auszüge" in user
    assert "SECRET" not in user
    auth = captured["headers"]["Authorization"]
    assert auth.startswith("Bearer ")
    assert "sk-test-not-real" not in str(llm.public_status())


def test_decentral_uses_local_base_url(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("AISTUDIO_LLM_MODEL", "llama3.1")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    monkeypatch.delenv("AISTUDIO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = llm.public_status()
    assert status["kind"] == "decentral"
    assert status["ready"] is True
    assert status["sends_excerpts"] is False
    assert status["egress"] == "in_boundary"


def test_public_status_never_contains_secrets(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-proj-LEAKME")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-LEAKME")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "cloud")
    blob = str(llm.public_status())
    assert "sk-proj" not in blob
    assert "LEAKME" not in blob


def test_complete_does_not_log_prompt(monkeypatch, caplog):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    secret = "MANDANTENGEHEIMNIS-42"
    with caplog.at_level(logging.INFO, logger="product.llm"):
        llm.complete(system="sys", user="Frage: " + secret)
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert secret not in joined
    assert "sk-test-not-real" not in joined


def test_ask_uses_gateway_and_sets_via(monkeypatch, tmp_path):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret")

    def fake_complete(*, system, user, max_tokens=None):
        assert "Auszüge" in user
        assert "SECRET_FULL_BODY" not in user
        return {
            "ok": True,
            "text": "<p>Nur aus Auszügen: Tagegeld <b>28 €</b>.</p>",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "kind": "api",
            "error": "",
            "latency_ms": 3,
        }

    monkeypatch.setattr("product.llm.complete", fake_complete)
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": "katharina.vogel@meridian.example", "password": "Meridian2026!"},
        )
        headers = {"Authorization": "Bearer " + login.json()["token"]}
        r = client.post("/api/ask", json={"q": "Tagegeld Reiserichtlinie"}, headers=headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["via"] == "llm"
        assert "28" in data["text"]
        health = client.get("/api/health").json()
        assert "llm" in health
        assert "sk-" not in str(health)


def test_ask_falls_back_extractive_when_gateway_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret")
    from fastapi.testclient import TestClient
    from product.main import app

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": "katharina.vogel@meridian.example", "password": "Meridian2026!"},
        )
        headers = {"Authorization": "Bearer " + login.json()["token"]}
        r = client.post("/api/ask", json={"q": "Reiserichtlinie"}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["via"] == "extractive"
        assert data["sources"]
