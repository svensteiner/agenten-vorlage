"""In-process rate limiting, client IP, security headers, access log."""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from product import config

log = logging.getLogger("aistudio.access")

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
_sweep = 0
_MAX_KEYS = 8000
_REQ_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def normalize_request_id(raw: str | None) -> str:
    """Accept a short correlator; ignore oversized or odd client values."""
    text = (raw or "").strip()
    if _REQ_ID.fullmatch(text):
        return text
    return uuid.uuid4().hex[:16]


def client_ip(request: Request) -> str:
    """Client address for rate limits. X-Forwarded-For only from a trusted proxy."""
    peer = "unknown"
    if request.client:
        peer = (request.client.host or "unknown")[:80]
    if config.peer_is_trusted_proxy(peer):
        forwarded = request.headers.get("x-forwarded-for") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()[:80] or peer
    return peer


def rate_limited(key: str, limit: int, window_s: int = 60) -> bool:
    """Return True if the caller should be rejected."""
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            _sweep_idle(now)
            return True
        q.append(now)
        _sweep_idle(now)
        return False


def _sweep_idle(now: float) -> None:
    """Drop idle keys so unique IPs cannot grow the map without bound."""
    global _sweep
    _sweep += 1
    if _sweep < 32 and len(_hits) < _MAX_KEYS:
        return
    _sweep = 0
    stale = [
        k
        for k, q in _hits.items()
        if not q or now - q[-1] > 120
    ]
    for k in stale:
        del _hits[k]
    if len(_hits) <= _MAX_KEYS:
        return
    extra = sorted(
        _hits.items(),
        key=lambda kv: kv[1][-1] if kv[1] else 0,
    )
    for k, _q in extra[: len(_hits) - _MAX_KEYS]:
        del _hits[k]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = normalize_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        path = request.url.path
        if path.startswith("/api/") or path in {"/", "/index.html", "/app.js", "/product-client.js", "/data.js"}:
            response.headers["Cache-Control"] = "no-store"
        if config.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        return response


class AccessLogMiddleware:
    """ASGI access log — does not buffer the body (BaseHTTPMiddleware would)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        request = Request(scope)
        status_holder = {"code": 0}
        rid = "-"

        async def send_wrap(message):
            nonlocal rid
            if message["type"] == "http.response.start":
                status_holder["code"] = int(message.get("status") or 0)
                for key, value in message.get("headers") or ():
                    if key.lower() == b"x-request-id":
                        rid = value.decode("latin-1", errors="replace")
            await send(message)

        await self.app(scope, receive, send_wrap)
        path = request.url.path
        if not path.startswith("/api/"):
            return
        ms = int((time.perf_counter() - start) * 1000)
        ip = client_ip(request)
        if config.is_production():
            log.info(
                json.dumps(
                    {
                        "method": request.method,
                        "path": path,
                        "status": status_holder["code"],
                        "ms": ms,
                        "rid": rid,
                        "ip": ip,
                    },
                    ensure_ascii=False,
                )
            )
            return
        log.info(
            "method=%s path=%s status=%s ms=%s rid=%s ip=%s",
            request.method,
            path,
            status_holder["code"],
            ms,
            rid,
            ip,
        )


def too_large() -> JSONResponse:
    response = JSONResponse({"detail": "Anfrage zu groß."}, status_code=413)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


class LimitRequestMiddleware:
    """Cap the real body, not only Content-Length (chunked POST would otherwise skip the limit).

    Must sit outside SecurityHeadersMiddleware (BaseHTTPMiddleware buffers the body).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        max_bytes = int(config.MAX_REQUEST_BYTES)
        declared = None
        for key, value in scope.get("headers") or ():
            if key == b"content-length":
                try:
                    declared = int(value)
                except (TypeError, ValueError):
                    declared = None
                break
        if declared is not None and (declared < 0 or declared > max_bytes):
            await too_large()(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            mtype = message.get("type")
            if mtype == "http.disconnect":
                return
            if mtype != "http.request":
                continue
            chunk = message.get("body") or b""
            if len(body) + len(chunk) > max_bytes:
                await too_large()(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body"):
                break

        replayed = False

        async def replay():
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


def key_count() -> int:
    with _lock:
        return len(_hits)


def too_many() -> JSONResponse:
    return JSONResponse(
        {"detail": "Zu viele Anfragen. Bitte kurz warten.", "request_id": "-"},
        status_code=429,
        headers={"Retry-After": "60"},
    )


def rate_limit_error():
    from fastapi import HTTPException

    return HTTPException(
        429,
        "Zu viele Anfragen. Bitte kurz warten.",
        headers={"Retry-After": "60"},
    )


def metrics_authorized(request: Request) -> bool:
    """Token required in production. Optional in development if unset."""
    expected = (os.environ.get("AISTUDIO_METRICS_TOKEN") or "").strip()
    if not expected:
        return not config.is_production()
    supplied = (request.headers.get("x-metrics-token") or "").strip()
    authz = request.headers.get("authorization") or ""
    if not supplied and authz.lower().startswith("bearer "):
        supplied = authz.split(" ", 1)[1].strip()
    try:
        return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))
    except (TypeError, ValueError):
        return False
