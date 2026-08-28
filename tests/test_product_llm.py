"""Product model gateway: excerpts only, default in-boundary, no prompt logs."""

from __future__ import annotations

import logging

from product import llm, retrieval

def test_quote_from_prefers_longer_query_tokens():
    doc = {
        "body": (
            "Alle Reisen sind über das Portal zu buchen. "
            "§5 Verpflegungspauschale: 28 € pro vollem Reisetag. "
            "Reiserichtlinie 2026 gilt ab Februar."
        ),
        "snippet": "Kurz",
    }
    q = retrieval.quote_from(
        doc, "Wie hoch sind Tagegeld und Sätze in der Reiserichtlinie?", 80
    )
    assert "Reiserichtlinie" in q
    assert "sind über" not in q


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
    assert blob.count("SECRET_FULL_BODY") <= 8
    assert "body" not in excerpts[0]
    assert all(len(e["quote"]) <= llm.MAX_QUOTE_CHARS for e in excerpts)


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
            captured["client_kwargs"] = k

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
    assert captured["client_kwargs"].get("follow_redirects") is False
    assert captured["client_kwargs"].get("trust_env") is True
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


def test_in_boundary_blocks_public_decentral_url(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    monkeypatch.delenv("AISTUDIO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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
            raise AssertionError("public decentral must not happen")

    monkeypatch.setattr(llm.httpx, "Client", Boom)
    result = llm.complete(system="sys", user="Frage: intern")
    assert result["ok"] is False
    assert result["error"] == "egress_blocked"
    assert called == []
    status = llm.public_status()
    assert status["ready"] is False
    assert status["reason"] == "egress_blocked"
    assert status["sends_excerpts"] is False
    assert "groq" not in str(status)


def test_in_boundary_allows_rfc1918_and_docker_name(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    monkeypatch.delenv("AISTUDIO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "http://10.1.2.3:11434/v1")
    assert llm.public_status()["ready"] is True
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "http://ollama:11434/v1")
    assert llm.public_status()["ready"] is True
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "https://llm.corp.internal/v1")
    assert llm.public_status()["ready"] is True
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "http://8.8.8.8:11434/v1")
    assert llm.public_status()["ready"] is False
    assert llm.public_status()["reason"] == "egress_blocked"


def test_in_boundary_hosts_allowlist(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "https://llm.firma.example/v1")
    monkeypatch.delenv("AISTUDIO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AISTUDIO_LLM_IN_BOUNDARY_HOSTS", raising=False)
    assert llm.public_status()["ready"] is False
    monkeypatch.setenv("AISTUDIO_LLM_IN_BOUNDARY_HOSTS", "llm.firma.example")
    assert llm.public_status()["ready"] is True


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


def test_llm_budget_falls_back_without_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret")
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "cloud")
    monkeypatch.setenv("AISTUDIO_LLM_PER_USER", "1")
    calls: list[int] = []

    def fake_complete(*, system, user, max_tokens=None):
        calls.append(1)
        return {
            "ok": True,
            "text": "<p>Nur Modell.</p>",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "kind": "api",
            "error": "",
            "latency_ms": 1,
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
        first = client.post("/api/ask", json={"q": "Reiserichtlinie"}, headers=headers)
        second = client.post("/api/ask", json={"q": "Reiserichtlinie Hotel"}, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["via"] == "llm"
        assert second.json()["via"] == "extractive"
        assert len(calls) == 1
        assert "Kontingent" in " ".join(second.json().get("reasoning") or [])
        assert llm.call_stats()["budget_blocked"] >= 1


def test_llm_daily_budget_persists(tmp_path, monkeypatch):
    monkeypatch.setattr("product.auth._PBKDF_ROUNDS", 2)
    monkeypatch.setattr("product.config.DB_PATH", tmp_path / "aistudio.db")
    monkeypatch.setattr("product.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("product.config.SECRET", "test-secret")
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "cloud")
    monkeypatch.setenv("AISTUDIO_LLM_PER_USER", "50")
    monkeypatch.setenv("AISTUDIO_LLM_PER_ORG", "50")
    monkeypatch.setenv("AISTUDIO_LLM_PER_USER_DAY", "1")
    calls: list[int] = []

    def fake_complete(*, system, user, max_tokens=None):
        calls.append(1)
        return {
            "ok": True,
            "text": "<p>Nur Modell.</p>",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "kind": "api",
            "error": "",
            "latency_ms": 1,
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
        first = client.post("/api/ask", json={"q": "Reiserichtlinie"}, headers=headers)
        second = client.post("/api/ask", json={"q": "Reiserichtlinie Hotel"}, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["via"] == "llm"
        assert second.json()["via"] == "extractive"
        assert len(calls) == 1
        health = client.get("/api/health").json()
        assert health["llm"]["per_user_day"] == 1
        assert "sk-" not in str(health)


def test_llm_circuit_opens_without_further_calls(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AISTUDIO_LLM_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "cloud")
    monkeypatch.setenv("AISTUDIO_LLM_BREAKER_FAILS", "2")
    monkeypatch.setenv("AISTUDIO_LLM_BREAKER_SECONDS", "60")
    with llm._stats_lock:
        llm._breaker["fails"] = 0
        llm._breaker["open_until"] = 0.0
        llm._stats["circuit_open"] = 0
    posts = []

    class Boom:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            posts.append(1)
            raise llm.httpx.TimeoutException("offline")

    monkeypatch.setattr(llm.httpx, "Client", Boom)
    first = llm.complete(system="sys", user="Frage: intern")
    second = llm.complete(system="sys", user="Frage: intern")
    third = llm.complete(system="sys", user="Frage: intern")
    assert first["error"] == "timeout"
    assert second["error"] == "timeout"
    assert third["error"] == "circuit_open"
    assert third["ok"] is False
    assert len(posts) == 2
    status = llm.public_status()
    assert status["circuit_open"] is True
    assert llm.call_stats()["circuit_open"] >= 1
    with llm._stats_lock:
        llm._breaker["fails"] = 0
        llm._breaker["open_until"] = 0.0


def test_in_boundary_does_not_use_env_proxy(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    monkeypatch.setenv("AISTUDIO_LLM_MODEL", "llama3.1")
    monkeypatch.delenv("AISTUDIO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "<p>ok</p>"}}]}

    class FakeClient:
        def __init__(self, *a, **k):
            captured["client_kwargs"] = k

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(llm.httpx, "Client", FakeClient)
    result = llm.complete(system="sys", user="Frage: intern")
    assert result["ok"] is True
    assert captured["client_kwargs"].get("follow_redirects") is False
    assert captured["client_kwargs"].get("trust_env") is False


def test_garbage_llm_env_does_not_crash_status(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_TIMEOUT", "nope")
    monkeypatch.setenv("AISTUDIO_LLM_MAX_TOKENS", "abc")
    monkeypatch.setenv("AISTUDIO_LLM_PER_USER", "x")
    monkeypatch.setenv("AISTUDIO_LLM_PER_ORG_DAY", "")
    status = llm.public_status()
    assert status["per_user"] == 20
    assert status["per_org_day"] == 800
    cfg = llm.settings()
    assert cfg["timeout"] == 20.0
    assert cfg["max_tokens"] == 700


def test_llm_timeout_and_tokens_clamped(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_TIMEOUT", "3600")
    monkeypatch.setenv("AISTUDIO_LLM_MAX_TOKENS", "99999")
    cfg = llm.settings()
    assert cfg["timeout"] == 60.0
    assert cfg["max_tokens"] == 4096


def test_file_base_url_is_not_ready(monkeypatch):
    monkeypatch.setenv("AISTUDIO_LLM_PROVIDER", "decentral")
    monkeypatch.setenv("AISTUDIO_LLM_BASE_URL", "file:///etc/passwd")
    monkeypatch.setenv("AISTUDIO_LLM_EGRESS", "in_boundary")
    status = llm.public_status()
    assert status["ready"] is False
    assert status["reason"] == "bad_base_url"
    assert "passwd" not in str(status)
