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
from typing import Any
from urllib.parse import urlparse

import httpx

log = logging.getLogger("product.llm")

_stats_lock = threading.Lock()
_stats = {"complete_ok": 0, "complete_fail": 0, "budget_blocked": 0}

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
    }


def call_stats() -> dict[str, int]:
    """Process-local counters for /api/metrics. No prompts, no tenant ids."""
    with _stats_lock:
        return dict(_stats)


def allow_call(*, org_id: str | None = None, user_id: str | None = None) -> bool:
    """Budget for paid/cloud calls. Exhausted budget → extractive fallback, not 429."""
    cfg = settings()
    if not cfg["ready"]:
        return True
    from product.security import rate_limited

    per_user = int(os.environ.get("AISTUDIO_LLM_PER_USER", "20"))
    per_org = int(os.environ.get("AISTUDIO_LLM_PER_ORG", "60"))
    if user_id and rate_limited("llm-user:" + user_id, per_user):
        with _stats_lock:
            _stats["budget_blocked"] += 1
        log.info("llm budget exhausted scope=user")
        return False
    if org_id and rate_limited("llm-org:" + org_id, per_org):
        with _stats_lock:
            _stats["budget_blocked"] += 1
        log.info("llm budget exhausted scope=org")
        return False
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
    tokens = int(max_tokens or cfg["max_tokens"])
    try:
        if cfg["provider"] == "anthropic":
            text = _anthropic(cfg, system, user, tokens)
        else:
            text = _openai_compat(cfg, system, user, tokens)
    except httpx.TimeoutException:
        return _fail(cfg, started, "timeout")
    except httpx.HTTPStatusError as exc:
        return _fail(cfg, started, "http_%s" % exc.response.status_code)
    except Exception:
        return _fail(cfg, started, "request_failed")
    ms = int((time.monotonic() - started) * 1000)
    text = sanitize_html(text or "")
    ok = bool(text)
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
    with httpx.Client(timeout=cfg["timeout"]) as client:
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
    with httpx.Client(timeout=cfg["timeout"]) as client:
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


def _log_complete(cfg: dict[str, Any], *, ok: bool, ms: int, error: str) -> None:
    with _stats_lock:
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
