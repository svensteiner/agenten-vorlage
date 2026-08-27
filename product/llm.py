"""Product model gateway — the only place tenant text may leave the process.

The rest of AI Studio never talks to a vendor SDK. Retrieval stays local (FTS5,
ACL fail-closed). This module may send only the caller-supplied excerpts, never
the knowledge base.

Default egress is ``in_boundary``: cloud vendors are refused even if an API key
is present, and answers stay extractive (or go to a local OpenAI-compatible
server). First product can opt into OpenAI with ``AISTUDIO_LLM_EGRESS=cloud``.
Later the same contract points at a decentral model via
``AISTUDIO_LLM_PROVIDER=decentral`` and ``AISTUDIO_LLM_BASE_URL``.

Prompts and excerpts are never logged — only provider, model, status, latency.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

log = logging.getLogger("product.llm")

_stats_lock = threading.Lock()
_stats = {"complete_ok": 0, "complete_fail": 0, "budget_blocked": 0, "circuit_open": 0}
_breaker = {"fails": 0, "open_until": 0.0}

CLOUD_HOSTS = ("api.openai.com", "api.anthropic.com")
DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_URL = "https://api.anthropic.com"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
MAX_EVIDENCE_DOCS = 4
MAX_QUOTE_CHARS = 900

_SCRIPT = re.compile(r"<(script|style|iframe|object|embed)\b[^>]*>.*?</\1>", re.I | re.S)
_ONATTR = re.compile(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
_JSURL = re.compile(r"javascript:", re.I)


def sanitize_html(text: str) -> str:
    """Drop script/style and inline handlers from model HTML. Keep simple markup."""
    cleaned = _SCRIPT.sub("", text or "")
    cleaned = _ONATTR.sub("", cleaned)
    cleaned = _JSURL.sub("", cleaned)
    return cleaned.strip()


def excerpts_from_hits(
    hits: list[dict[str, Any]],
    query: str,
    *,
    quote_fn: Any | None = None,
) -> list[dict[str, str]]:
    """Minimize what may cross the gateway: title, path, short quote — no body."""
    take_quote = quote_fn or (
        lambda hit, _query, n: (hit.get("snippet") or hit.get("body") or "")[:n]
    )
    out: list[dict[str, str]] = []
    for hit in (hits or [])[:MAX_EVIDENCE_DOCS]:
        out.append(
            {
                "title": str(hit.get("title") or hit.get("id") or "")[:180],
                "path": str(hit.get("path") or "")[:180],
                "quote": str(take_quote(hit, query, MAX_QUOTE_CHARS) or "")[:MAX_QUOTE_CHARS],
            }
        )
    return out


def build_user_prompt(query: str, excerpts: list[dict[str, str]]) -> str:
    blocks = []
    for item in excerpts:
        title = item.get("title") or "Dokument"
        path = item.get("path") or ""
        quote = item.get("quote") or ""
        head = f"[{title}]" + (f" ({path})" if path else "")
        blocks.append(f"{head}\n{quote}")
    return f"Frage: {query}\n\nAuszüge:\n\n" + "\n\n".join(blocks)


def settings() -> dict[str, Any]:
    """Read live env so tests and restarts do not need a process recycle."""
    provider = (os.environ.get("AISTUDIO_LLM_PROVIDER") or "auto").strip().lower()
    model = (os.environ.get("AISTUDIO_LLM_MODEL") or "").strip()
    base_url = (os.environ.get("AISTUDIO_LLM_BASE_URL") or "").strip()
    openai_key = (
        os.environ.get("AISTUDIO_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    ).strip()
    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if provider == "anthropic" and os.environ.get("AISTUDIO_LLM_API_KEY"):
        anthropic_key = os.environ.get("AISTUDIO_LLM_API_KEY", "").strip() or anthropic_key
    timeout = float(os.environ.get("AISTUDIO_LLM_TIMEOUT", "20"))
    max_tokens = int(os.environ.get("AISTUDIO_LLM_MAX_TOKENS", "700"))
    egress = (os.environ.get("AISTUDIO_LLM_EGRESS") or "in_boundary").strip().lower()
    if egress not in {"cloud", "in_boundary"}:
        egress = "in_boundary"

    if provider == "auto":
        if base_url:
            provider = "decentral"
        elif openai_key:
            provider = "openai"
        elif anthropic_key:
            provider = "anthropic"
        else:
            provider = "none"

    if provider == "openai":
        base_url = base_url or DEFAULT_OPENAI_URL
        model = model or DEFAULT_OPENAI_MODEL
        api_key = openai_key
        kind = "api"
    elif provider == "anthropic":
        base_url = base_url or DEFAULT_ANTHROPIC_URL
        model = model or DEFAULT_ANTHROPIC_MODEL
        api_key = anthropic_key
        kind = "api"
    elif provider in {"openai_compat", "decentral"}:
        kind = "decentral"
        api_key = openai_key
        model = model or "llama3.1"
        provider = "decentral" if provider == "decentral" else "openai_compat"
    else:
        provider = "none"
        kind = "none"
        api_key = ""
        model = model or ""

    cloud = _is_cloud(provider, base_url)
    blocked = bool(cloud and egress == "in_boundary")
    ready = bool(provider != "none" and not blocked and (api_key or kind == "decentral") and (kind != "decentral" or base_url))
    reason = ""
    if provider == "none":
        reason = "not_configured"
    elif blocked:
        reason = "egress_blocked"
    elif kind == "decentral" and not base_url:
        reason = "missing_base_url"
        ready = False
    elif kind == "api" and not api_key:
        reason = "missing_api_key"
        ready = False

    return {
        "provider": provider,
        "kind": kind,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout": timeout,
        "max_tokens": max_tokens,
        "egress": egress,
        "cloud": cloud,
        "ready": ready,
        "reason": reason,
    }


def public_status() -> dict[str, Any]:
    """Health payload: never keys, never prompts, never host credentials."""
    cfg = settings()
    per_user = int(os.environ.get("AISTUDIO_LLM_PER_USER", "20"))
    per_org = int(os.environ.get("AISTUDIO_LLM_PER_ORG", "60"))
    per_user_day = int(os.environ.get("AISTUDIO_LLM_PER_USER_DAY", "200"))
    per_org_day = int(os.environ.get("AISTUDIO_LLM_PER_ORG_DAY", "800"))
    brk = breaker_status()
    return {
        "provider": cfg["provider"],
        "kind": cfg["kind"],
        "model": cfg["model"] or None,
        "configured": cfg["provider"] != "none",
        "ready": cfg["ready"],
        "egress": cfg["egress"],
        "sends_excerpts": bool(cfg["ready"] and cfg["egress"] == "cloud"),
        "reason": cfg["reason"] or None,
        "per_user": per_user,
        "per_org": per_org,
        "per_user_day": per_user_day,
        "per_org_day": per_org_day,
        "circuit_open": brk["open"],
        "circuit_open_s": brk["open_for_s"],
    }


def breaker_status() -> dict[str, Any]:
    """Process-local circuit: consecutive vendor failures pause outbound calls."""
    with _stats_lock:
        open_until = float(_breaker["open_until"] or 0)
        fails = int(_breaker["fails"] or 0)
    remaining = max(0, int(open_until - time.time()))
    return {"open": remaining > 0, "open_for_s": remaining, "consecutive_fails": fails}


def circuit_open() -> bool:
    _fails, seconds = _breaker_limits()
    if seconds <= 0:
        return False
    with _stats_lock:
        return time.time() < float(_breaker["open_until"] or 0)


def _breaker_limits() -> tuple[int, int]:
    return max(1, _int_env("AISTUDIO_LLM_BREAKER_FAILS", 5)), max(
        0, _int_env("AISTUDIO_LLM_BREAKER_SECONDS", 300)
    )


def _breaker_note(ok: bool) -> None:
    threshold, seconds = _breaker_limits()
    if seconds <= 0:
        return
    with _stats_lock:
        if ok:
            _breaker["fails"] = 0
            _breaker["open_until"] = 0.0
            return
        _breaker["fails"] = int(_breaker["fails"] or 0) + 1
        if int(_breaker["fails"]) >= threshold:
            _breaker["open_until"] = time.time() + seconds
            log.info(
                "llm circuit open for=%ss after=%s fails",
                seconds,
                _breaker["fails"],
            )


def call_stats() -> dict[str, int]:
    """Process-local counters for /api/metrics. No prompts, no tenant ids."""
    with _stats_lock:
        return dict(_stats)


def allow_call(*, org_id: str | None = None, user_id: str | None = None, conn=None) -> bool:
    """Budget for paid/cloud calls. Exhausted budget → extractive fallback, not 429."""
    cfg = settings()
    if not cfg["ready"]:
        return True
    from product.security import rate_limited

    per_user = int(os.environ.get("AISTUDIO_LLM_PER_USER", "20"))
    per_org = int(os.environ.get("AISTUDIO_LLM_PER_ORG", "60"))
    if user_id and rate_limited("llm-user:" + user_id, per_user):
        return _block("user")
    if org_id and rate_limited("llm-org:" + org_id, per_org):
        return _block("org")
    if not _take_daily(org_id=org_id, user_id=user_id, conn=conn):
        return _block("day")
    return True


def _block(scope: str) -> bool:
    with _stats_lock:
        _stats["budget_blocked"] += 1
    log.info("llm budget exhausted scope=%s", scope)
    return False


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _take_daily(*, org_id: str | None, user_id: str | None, conn=None) -> bool:
    """Persist daily caps in SQLite so restarts do not reset spend. 0 = unlimited."""
    per_user = _int_env("AISTUDIO_LLM_PER_USER_DAY", 200)
    per_org = _int_env("AISTUDIO_LLM_PER_ORG_DAY", 800)
    if per_user <= 0 and per_org <= 0:
        return True
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from product import db

    own = conn is None
    c = conn or db.connect()
    try:
        db.init_db(c)
        c.execute("SAVEPOINT llm_budget")
        ok = True
        if user_id and per_user > 0 and not _bump_usage(c, day, "user", user_id, per_user):
            ok = False
        elif org_id and per_org > 0 and not _bump_usage(c, day, "org", org_id, per_org):
            ok = False
        if ok:
            c.execute("RELEASE SAVEPOINT llm_budget")
            if own:
                c.commit()
            return True
        c.execute("ROLLBACK TO SAVEPOINT llm_budget")
        c.execute("RELEASE SAVEPOINT llm_budget")
        return False
    except Exception:
        try:
            c.execute("ROLLBACK TO SAVEPOINT llm_budget")
        except Exception:
            pass
        log.exception("llm daily budget check failed")
        return False
    finally:
        if own:
            c.close()


def _bump_usage(conn, day: str, scope: str, key: str, limit: int) -> bool:
    row = conn.execute(
        "SELECT calls FROM llm_usage WHERE day = ? AND scope = ? AND key = ?",
        (day, scope, key),
    ).fetchone()
    n = int(row["calls"]) if row else 0
    if n >= limit:
        return False
    conn.execute(
        """INSERT INTO llm_usage (day, scope, key, calls) VALUES (?, ?, ?, 1)
           ON CONFLICT(day, scope, key) DO UPDATE SET calls = calls + 1""",
        (day, scope, key),
    )
    return True


def complete(*, system: str, user: str, max_tokens: int | None = None) -> dict[str, Any]:
    """Call the configured model. Never logs ``system`` or ``user``."""
    cfg = settings()
    started = time.monotonic()
    empty = {
        "ok": False,
        "text": "",
        "provider": cfg["provider"],
        "model": cfg["model"],
        "kind": cfg["kind"],
        "error": cfg["reason"] or "not_configured",
        "latency_ms": 0,
    }
    if not cfg["ready"]:
        _log_complete(cfg, ok=False, ms=0, error=empty["error"])
        return empty
    if circuit_open():
        _log_complete(cfg, ok=False, ms=0, error="circuit_open", circuit=True)
        empty["error"] = "circuit_open"
        return empty
    tokens = int(max_tokens or cfg["max_tokens"])
    try:
        if cfg["provider"] == "anthropic":
            text = _anthropic(cfg, system, user, tokens)
        else:
            text = _openai_compat(cfg, system, user, tokens)
    except httpx.TimeoutException:
        _breaker_note(False)
        return _fail(cfg, started, "timeout")
    except httpx.HTTPStatusError as exc:
        _breaker_note(False)
        return _fail(cfg, started, "http_%s" % exc.response.status_code)
    except Exception:
        _breaker_note(False)
        return _fail(cfg, started, "request_failed")
    ms = int((time.monotonic() - started) * 1000)
    text = sanitize_html(text or "")
    ok = bool(text)
    if ok:
        _breaker_note(True)
    _log_complete(cfg, ok=ok, ms=ms, error="" if ok else "empty")
    return {
        "ok": ok,
        "text": text,
        "provider": cfg["provider"],
        "model": cfg["model"],
        "kind": cfg["kind"],
        "error": "" if ok else "empty",
        "latency_ms": ms,
    }


def _is_cloud(provider: str, base_url: str) -> bool:
    if provider in {"openai", "anthropic"}:
        return True
    host = (urlparse(base_url).hostname or "").lower()
    return any(host == item or host.endswith("." + item) for item in CLOUD_HOSTS)


def _chat_url(base_url: str) -> str:
    url = (base_url or DEFAULT_OPENAI_URL).rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return url + "/chat/completions"


def _openai_compat(cfg: dict[str, Any], system: str, user: str, max_tokens: int) -> str:
    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = "Bearer " + cfg["api_key"]
    payload = {
        "model": cfg["model"],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=cfg["timeout"], follow_redirects=False) as client:
        response = client.post(_chat_url(cfg["base_url"]), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return (message.get("content") or "").strip()


def _anthropic(cfg: dict[str, Any], system: str, user: str, max_tokens: int) -> str:
    url = (cfg["base_url"] or DEFAULT_ANTHROPIC_URL).rstrip("/") + "/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    with httpx.Client(timeout=cfg["timeout"], follow_redirects=False) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    parts = []
    for block in data.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "".join(parts).strip()


def _fail(cfg: dict[str, Any], started: float, error: str) -> dict[str, Any]:
    ms = int((time.monotonic() - started) * 1000)
    _log_complete(cfg, ok=False, ms=ms, error=error)
    return {
        "ok": False,
        "text": "",
        "provider": cfg["provider"],
        "model": cfg["model"],
        "kind": cfg["kind"],
        "error": error,
        "latency_ms": ms,
    }


def _log_complete(
    cfg: dict[str, Any], *, ok: bool, ms: int, error: str, circuit: bool = False
) -> None:
    with _stats_lock:
        if circuit:
            _stats["circuit_open"] += 1
        else:
            _stats["complete_ok" if ok else "complete_fail"] += 1
    log.info(
        "llm complete provider=%s model=%s kind=%s egress=%s ok=%s ms=%s error=%s",
        cfg.get("provider"),
        cfg.get("model"),
        cfg.get("kind"),
        cfg.get("egress"),
        ok,
        ms,
        error or "-",
    )
