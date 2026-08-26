"""In-process rate limiting, client IP, security headers, access log."""

from __future__ import annotations

import json
import logging
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


def client_ip(request: Request) -> str:
    if config.trust_proxy():
        forwarded = request.headers.get("x-forwarded-for") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()[:80]
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def rate_limited(key: str, limit: int, window_s: int = 60) -> bool:
    """Return True if the caller should be rejected."""
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
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


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            ms = int((time.perf_counter() - start) * 1000)
            rid = getattr(request.state, "request_id", "-")
            ip = client_ip(request)
            if config.is_production():
                log.info(
                    json.dumps(
                        {
                            "method": request.method,
                            "path": request.url.path,
                            "status": response.status_code,
                            "ms": ms,
                            "rid": rid,
                            "ip": ip,
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                log.info(
                    "method=%s path=%s status=%s ms=%s rid=%s ip=%s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    ms,
                    rid,
                    ip,
                )
        return response


class LimitRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        raw = request.headers.get("content-length")
        if raw:
            try:
                size = int(raw)
            except ValueError:
                size = 0
            if size > config.MAX_REQUEST_BYTES:
                return JSONResponse({"detail": "Anfrage zu groß."}, status_code=413)
        return await call_next(request)


def too_many() -> JSONResponse:
    return JSONResponse({"detail": "Zu viele Anfragen. Bitte kurz warten."}, status_code=429)
