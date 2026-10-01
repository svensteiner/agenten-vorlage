"""Small, dependency-free security boundary for the public cockpit adapter.

The local cockpit server deliberately remains a separate compatibility mode.  Public
adapters can use this module to authenticate a request at the proxy boundary before
calling any tenant-scoped runtime code.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit


class PublicSecurityError(ValueError):
    """Raised when a request cannot be trusted as a public request."""


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,127}$", re.ASCII)
_OIDC_SUBJECT = re.compile(r"^[\x21-\x7e]{1,255}$", re.ASCII)
_ROLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,63}$", re.ASCII)
_HEADER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$", re.ASCII)
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _header(headers: Mapping[str, str], name: str) -> str:
    wanted = name.lower()
    values = [value for key, value in headers.items() if key.lower() == wanted]
    if len(values) != 1:
        return "" if not values else "\x00"
    return values[0].strip()


@dataclass(frozen=True, slots=True)
class AuthContext:
    tenant_id: str
    user_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublicSecurityConfig:
    public_origin: str
    trusted_proxy_cidrs: tuple[str, ...]
    csrf_secret: bytes
    identity_tenant_header: str = "X-Agent-Tenant"
    identity_user_header: str = "X-Agent-User"
    identity_roles_header: str = "X-Agent-Roles"
    fixed_tenant_id: str = ""

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.public_origin)
            parsed.port
        except ValueError as exc:
            raise ValueError("public_origin must be an exact HTTPS origin") from exc
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("public_origin must be an exact HTTPS origin")
        if (parsed.username or parsed.password or not parsed.hostname
                or any(ord(character) < 33 or ord(character) == 127 for character in self.public_origin)):
            raise ValueError("public_origin must not contain credentials")
        if not isinstance(self.csrf_secret, bytes) or len(self.csrf_secret) < 32:
            raise ValueError("csrf_secret must contain at least 32 bytes")
        networks = tuple(ipaddress.ip_network(value, strict=False) for value in self.trusted_proxy_cidrs)
        if not networks:
            raise ValueError("at least one trusted proxy CIDR is required")
        if self.fixed_tenant_id and not _IDENTIFIER.fullmatch(self.fixed_tenant_id):
            raise ValueError("fixed_tenant_id is invalid")
        identity_headers = (
            self.identity_tenant_header,
            self.identity_user_header,
            self.identity_roles_header,
        )
        if any(not _HEADER_NAME.fullmatch(name) for name in identity_headers):
            raise ValueError("identity header name is invalid")
        if len({name.lower() for name in identity_headers}) != 3:
            raise ValueError("identity header names must be distinct")
        object.__setattr__(self, "public_origin", f"https://{parsed.netloc.lower()}")
        object.__setattr__(self, "trusted_proxy_cidrs", tuple(str(network) for network in networks))

    @property
    def public_host(self) -> str:
        return urlsplit(self.public_origin).netloc

    def is_trusted_proxy(self, address: str) -> bool:
        try:
            candidate = ipaddress.ip_address(address.strip())
        except ValueError as exc:
            raise PublicSecurityError("invalid proxy address") from exc
        return any(candidate in ipaddress.ip_network(network) for network in self.trusted_proxy_cidrs)


def _validated_identity(value: str, label: str, pattern: re.Pattern[str]) -> str:
    if not value or not pattern.fullmatch(value):
        raise PublicSecurityError(f"invalid {label}")
    return value


def _context_from_headers(headers: Mapping[str, str], config: PublicSecurityConfig) -> AuthContext:
    tenant = config.fixed_tenant_id or _validated_identity(
        _header(headers, config.identity_tenant_header), "tenant identity", _IDENTIFIER
    )
    # OIDC Core permits a case-sensitive `sub` of up to 255 ASCII characters.
    # It is hashed before filesystem use, so visible punctuation is safe here;
    # controls, whitespace and non-ASCII data remain fail-closed.
    user = _validated_identity(
        _header(headers, config.identity_user_header), "user identity", _OIDC_SUBJECT
    )
    raw_roles = _header(headers, config.identity_roles_header)
    if not raw_roles or raw_roles.startswith(",") or raw_roles.endswith(","):
        raise PublicSecurityError("invalid role identity")
    roles = tuple(role.strip() for role in raw_roles.split(","))
    if (
        not roles
        or len(roles) > 16
        or len(set(roles)) != len(roles)
        or any(not _ROLE.fullmatch(role) for role in roles)
    ):
        raise PublicSecurityError("invalid role identity")
    return AuthContext(tenant, user, roles)


def validate_request(client_address: str, headers: Mapping[str, str], config: PublicSecurityConfig) -> AuthContext:
    """Validate proxy provenance, exact public forwarding and identity headers."""
    if not config.is_trusted_proxy(client_address):
        raise PublicSecurityError("request did not come from a trusted proxy")
    if _header(headers, "X-Forwarded-Proto") != "https":
        raise PublicSecurityError("request must be forwarded as HTTPS")
    if _header(headers, "X-Forwarded-Host") != config.public_host:
        raise PublicSecurityError("request host is not the configured public host")
    return _context_from_headers(headers, config)


def csrf_token(secret: bytes, context: AuthContext, session_id: str) -> str:
    """Create a session- and tenant-bound token suitable for a request header."""
    if not session_id or "\n" in session_id or "\r" in session_id:
        raise PublicSecurityError("invalid session")
    message = f"{context.tenant_id}\0{context.user_id}\0{session_id}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_csrf(method: str, headers: Mapping[str, str], context: AuthContext, session_id: str, config: PublicSecurityConfig) -> None:
    """Enforce exact-origin and CSRF checks for every state-changing request."""
    method = method.upper()
    origin = _header(headers, "Origin")
    referer = _header(headers, "Referer")
    if method in _SAFE_METHODS:
        return
    if origin != config.public_origin:
        raise PublicSecurityError("origin is not allowed")
    if referer and not referer.startswith(config.public_origin + "/"):
        raise PublicSecurityError("referer is not allowed")
    supplied = _header(headers, "X-CSRF-Token")
    expected = csrf_token(config.csrf_secret, context, session_id)
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise PublicSecurityError("CSRF validation failed")


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter:
    """Thread-safe fixed-window limiter with bounded key storage."""

    def __init__(self, *, window_seconds: float = 60.0, max_entries: int = 10_000) -> None:
        if window_seconds <= 0 or max_entries <= 0:
            raise ValueError("invalid rate limiter bounds")
        self.window_seconds = float(window_seconds)
        self.max_entries = int(max_entries)
        self._entries: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)

    def allow(self, key: str, *, limit: int, cost: int = 1, now: float | None = None) -> RateLimitDecision:
        if not key or limit <= 0 or cost <= 0:
            raise ValueError("invalid rate limit request")
        current = time.monotonic() if now is None else now
        with self._lock:
            started, count = self._entries.get(key, (current, 0))
            if current - started >= self.window_seconds:
                started, count = current, 0
            allowed = count + cost <= limit
            if allowed:
                count += cost
            self._entries[key] = (started, count)
            self._entries.move_to_end(key)
            self._evict(current)
            remaining = max(0, limit - count)
            retry = max(1, int(started + self.window_seconds - current)) if not allowed else 0
            return RateLimitDecision(allowed, remaining, retry)

    def _evict(self, now: float) -> None:
        expired = [key for key, (started, _) in self._entries.items() if now - started >= self.window_seconds]
        for key in expired:
            self._entries.pop(key, None)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)


def security_headers(config: PublicSecurityConfig) -> dict[str, str]:
    """Return response headers safe for the public browser surface."""
    return {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    }
