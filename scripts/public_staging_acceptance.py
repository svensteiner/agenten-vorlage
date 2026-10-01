"""Bounded acceptance checks for a public AgentKit staging origin.

The command deliberately accepts authentication only through files containing a
Cookie header.  It never prints a cookie, CSRF token, user identity, response
body, or request payload.  It creates one deterministic demo conversation for
the first session so that cross-user isolation is tested against real state.  It
is an operator check for a concrete HTTPS edge;
it is not a provider, capacity, backup, or penetration test.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import re
import ssl
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


DEFAULT_TIMEOUT = 10.0
DEFAULT_RESPONSE_LIMIT = 1_048_576
MAX_RESPONSE_LIMIT = 8 * 1_048_576
MAX_TIMEOUT = 60.0
MAX_SOAK_DURATION = 15 * 60.0
MAX_SOAK_CONCURRENCY = 16
MAX_SOAK_REQUESTS = 10_000
MAX_READINESS_INTERVAL = 300.0
COOKIE_LIMIT = 8_192
COOKIE_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
SAFE_ID = re.compile(r"^[0-9a-f]{32}$")
GITHUB_ACCEPTANCE_TARGET = {
    "owner": "Anil-matcha",
    "repo": "Open-Dots",
    "path": "README.md",
    "ref": "5abe1b3d65d5176af936ed92de1b731634d2bcb5",
}
GITHUB_ACCEPTANCE_BLOB_SHA = "23f69cc9dcab5c7922f5eb6b8b7a83cfa06f69c6"


class AcceptanceError(Exception):
    """An expected, sanitized operator-check failure."""

    def __init__(self, category: str, check: str | None = None):
        super().__init__(category)
        self.category = category
        self.check = check


class _ArgumentParser(argparse.ArgumentParser):
    """Prevent argparse from printing values or a noisy usage on bad input."""

    def error(self, message: str):  # noqa: D401
        raise AcceptanceError("invalid_arguments")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str]
    elapsed_ms: float


@dataclass(frozen=True)
class Session:
    cookie: str
    csrf_token: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class SoakLimits:
    duration: float
    concurrency: int
    requests: int
    readiness_interval: float


def validate_origin(value: str) -> SplitResult:
    """Return an exact HTTPS origin, rejecting credentials and URL components."""

    if not isinstance(value, str) or value != value.strip() or not value:
        raise AcceptanceError("origin_invalid")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise AcceptanceError("origin_invalid")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise AcceptanceError("origin_invalid") from exc
    if parsed.scheme != "https" or not parsed.hostname or not parsed.netloc:
        raise AcceptanceError("origin_invalid")
    if parsed.username is not None or parsed.password is not None:
        raise AcceptanceError("origin_invalid")
    # A strict origin has no path, query, or fragment.  This also rejects a
    # trailing slash, which could otherwise hide a reverse-proxy path prefix.
    if parsed.path or parsed.query or parsed.fragment:
        raise AcceptanceError("origin_invalid")
    if port is not None and not 1 <= port <= 65535:
        raise AcceptanceError("origin_invalid")
    if any(char.isspace() for char in parsed.netloc):
        raise AcceptanceError("origin_invalid")
    return parsed


def read_cookie_file(path: str | Path) -> str:
    """Read and validate a Cookie header without ever returning it to output."""

    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            raw = stream.read(COOKIE_LIMIT + 1)
    except (OSError, UnicodeError) as exc:
        raise AcceptanceError("cookie_file") from exc
    if len(raw) > COOKIE_LIMIT or len(raw.encode("utf-8")) > COOKIE_LIMIT or "\x00" in raw:
        raise AcceptanceError("cookie_file")
    raw = raw.strip()
    if raw.lower().startswith("cookie:"):
        raw = raw[7:].strip()
    if not raw or "\r" in raw or "\n" in raw:
        raise AcceptanceError("cookie_file")
    # A file is intentionally a raw Cookie header, with a permissive parser for
    # values that contain '='.  No other header format is accepted.
    pairs = [part.strip() for part in raw.split(";") if part.strip()]
    if not pairs:
        raise AcceptanceError("cookie_file")
    for pair in pairs:
        name, separator, value = pair.partition("=")
        if not separator or not COOKIE_NAME.fullmatch(name.strip()) or not value:
            raise AcceptanceError("cookie_file")
        if any(ord(char) < 0x21 or ord(char) > 0x7E for char in value):
            raise AcceptanceError("cookie_file")
    return "; ".join(pairs)


def _json_object(response: HttpResponse) -> dict[str, Any]:
    try:
        value = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcceptanceError("protocol") from exc
    if not isinstance(value, dict):
        raise AcceptanceError("protocol")
    return value


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 3)


class StagingClient:
    """Small HTTP client with redirect, timeout, and response-size guards."""

    def __init__(
        self,
        origin: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        response_limit: int = DEFAULT_RESPONSE_LIMIT,
        ca_file: str | None = None,
    ):
        self.origin = origin
        validate_origin(origin)
        if not 0 < timeout <= MAX_TIMEOUT:
            raise AcceptanceError("bounds")
        if not 1 <= response_limit <= MAX_RESPONSE_LIMIT:
            raise AcceptanceError("bounds")
        self.timeout = timeout
        self.response_limit = response_limit
        try:
            if ca_file:
                context = ssl.create_default_context(cafile=ca_file)
            else:
                context = ssl.create_default_context()
        except (OSError, ssl.SSLError) as exc:
            raise AcceptanceError("tls") from exc
        self._opener = build_opener(_NoRedirect, HTTPSHandler(context=context))
        self._context = context
        self._request_ids: set[str] = set()
        self._request_ids_lock = threading.Lock()

    def request(
        self,
        path: str,
        *,
        cookie: str | None = None,
        method: str = "GET",
        body: Mapping[str, Any] | None = None,
        origin: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        if not path.startswith("/") or "?" in path or "#" in path:
            raise AcceptanceError("protocol")
        request_id = uuid.uuid4().hex
        with self._request_ids_lock:
            if request_id in self._request_ids:
                raise AcceptanceError("request_id")
            self._request_ids.add(request_id)
        request_headers = {"Accept": "application/json", "X-Request-ID": request_id}
        if cookie is not None:
            request_headers["Cookie"] = cookie
        if origin is not None:
            request_headers["Origin"] = origin
        if headers:
            request_headers.update(headers)
        # Callers cannot replace the correlation ID or cookie selected from a
        # protected file.  Origin remains caller-controlled because the check
        # intentionally sends one wrong origin during acceptance.
        request_headers["X-Request-ID"] = request_id
        if cookie is not None:
            request_headers["Cookie"] = cookie
        encoded = None
        if body is not None:
            encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = Request(self.origin + path, data=encoded, headers=request_headers, method=method)
        request_timeout = self.timeout if timeout is None else min(self.timeout, timeout)
        if request_timeout <= 0:
            raise AcceptanceError("bounds")
        started = time.perf_counter()
        try:
            with self._opener.open(request, timeout=request_timeout) as response:
                status = int(response.status)
                response_headers = {str(key): str(value) for key, value in response.headers.items()}
                self._check_content_length(response_headers)
                body_bytes = response.read(self.response_limit + 1)
                if len(body_bytes) > self.response_limit:
                    raise AcceptanceError("response_too_large")
        except HTTPError as exc:
            try:
                # No-redirect makes redirects visible as HTTPError without ever
                # following an attacker-controlled Location value.
                if 300 <= int(exc.code) < 400:
                    raise AcceptanceError("redirect_refused") from exc
                response_headers = {str(key): str(value) for key, value in exc.headers.items()}
                self._check_content_length(response_headers)
                body_bytes = exc.read(self.response_limit + 1)
            finally:
                exc.close()
            if len(body_bytes) > self.response_limit:
                raise AcceptanceError("response_too_large") from exc
            status = int(exc.code)
        except AcceptanceError:
            raise
        except (TimeoutError, OSError, URLError, ssl.SSLError) as exc:
            raise AcceptanceError("network") from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        return HttpResponse(status, body_bytes, response_headers, elapsed_ms)

    def _check_content_length(self, headers: Mapping[str, str]) -> None:
        for key, value in headers.items():
            if key.lower() == "content-length":
                try:
                    length = int(value)
                except ValueError as exc:
                    raise AcceptanceError("protocol") from exc
                if length < 0 or length > self.response_limit:
                    raise AcceptanceError("response_too_large")


class StagingAcceptance:
    def __init__(
        self,
        client: StagingClient,
        alice_cookie: str,
        bob_cookie: str,
        *,
        required_roles: Sequence[str] = ("member",),
        soak: SoakLimits | None = None,
    ):
        self.client = client
        self.alice_cookie = alice_cookie
        self.bob_cookie = bob_cookie
        self.required_roles = tuple(required_roles)
        self.soak = soak
        self.checks: dict[str, bool] = {}

    def run(self) -> dict[str, Any]:
        try:
            # The production OAuth2 proxy protects every edge route.  Its
            # internal app healthcheck bypasses the edge, but an external
            # staging probe must carry a real authenticated session.
            self._check_service_status(
                "health",
                self.client.request("/api/health", cookie=self.alice_cookie),
                "ok",
            )
            self._check_service_status(
                "readiness",
                self.client.request("/api/readiness", cookie=self.alice_cookie),
                "ready",
            )
            alice = self._session("alice_session", self.alice_cookie)
            bob = self._session("bob_session", self.bob_cookie)
            if alice.user_id == bob.user_id:
                self._fail("distinct_users", "identity_not_distinct")
            self.checks["distinct_users"] = True
            if alice.tenant_id != bob.tenant_id:
                self._fail("single_tenant", "tenant_mismatch")
            self.checks["single_tenant"] = True
            for session in (alice, bob):
                if not set(self.required_roles).issubset(session.roles):
                    self._fail("required_roles", "role_missing")
            self.checks["required_roles"] = True
            injected = {
                "X-Forwarded-Email": "injected@example.invalid",
                "X-Forwarded-Groups": "tenant_admin",
                "X-Forwarded-User": "injected-user",
                "X-Forwarded-Preferred-Username": "injected-user",
                "X-Forwarded-Access-Token": "injected-token",
                "X-Agent-Tenant": "injected-tenant",
                "X-Agent-User": "injected-user",
                "X-Agent-Roles": "tenant_admin",
            }
            injected_session = self._session(
                "forwarded_identity_stripping", self.alice_cookie, headers=injected
            )
            if (
                injected_session.user_id != alice.user_id
                or injected_session.tenant_id != alice.tenant_id
                or injected_session.roles != alice.roles
            ):
                self._fail("forwarded_identity_stripping", "identity_header_injection")
            self.checks["forwarded_identity_stripping"] = True
            config = self._json_checked("config", self.client.request("/api/config", cookie=self.alice_cookie))
            agent = self._discover_agent(config)
            workspace = self._discover_workspace(config)
            self._discover_demo_backend(config)
            self.checks["public_config"] = True
            self._check_github_preview(alice)
            payload = {
                "request_id": uuid.uuid4().hex,
                "agent": agent,
                "workspace": workspace,
                "backend": "demo",
                "model": "",
                "title": "staging acceptance",
            }
            wrong_origin = self.client.request(
                "/api/conversations",
                cookie=self.alice_cookie,
                method="POST",
                body=payload,
                origin=self.client.origin + ".invalid",
                headers={"X-CSRF-Token": alice.csrf_token},
            )
            if wrong_origin.status != 403:
                self._fail("wrong_origin_csrf", "csrf_origin")
            self.checks["wrong_origin_csrf"] = True
            created = self.client.request(
                "/api/conversations",
                cookie=self.alice_cookie,
                method="POST",
                body=payload,
                origin=self.client.origin,
                headers={"X-CSRF-Token": alice.csrf_token},
            )
            if created.status not in (200, 201):
                self._fail("conversation_created", "conversation_create")
            created_data = self._json_checked("conversation_created", created)
            conversation_id = created_data.get("id")
            if not isinstance(conversation_id, str) or not SAFE_ID.fullmatch(conversation_id):
                self._fail("conversation_created", "protocol")
            self.checks["conversation_created"] = True
            alice_view = self.client.request(
                "/api/conversations/" + conversation_id,
                cookie=self.alice_cookie,
            )
            alice_data = self._json_checked("alice_resource_access", alice_view)
            if alice_view.status != 200 or alice_data.get("id") != conversation_id:
                self._fail("alice_resource_access", "conversation_not_persisted")
            self.checks["alice_resource_access"] = True
            bob_view = self.client.request(
                "/api/conversations/" + conversation_id,
                cookie=self.bob_cookie,
            )
            if bob_view.status != 404:
                self._fail("bob_isolation", "cross_user_resource")
            self.checks["bob_isolation"] = True
            result: dict[str, Any] = {
                "ok": True,
                "status": "passed",
                "category": "success",
                "checks": {key: bool(value) for key, value in self.checks.items()},
            }
            if self.soak is not None:
                result["soak"] = self._soak()
                if not result["soak"]["ok"]:
                    result["ok"] = False
                    result["status"] = "failed"
                    result["category"] = "soak_failed"
            return result
        except AcceptanceError as exc:
            if exc.check:
                self.checks[exc.check] = False
            return {
                "ok": False,
                "status": "failed",
                "category": exc.category,
                "checks": {key: bool(value) for key, value in self.checks.items()},
            }

    def _session(self, check: str, cookie: str, *, headers=None) -> Session:
        response = self.client.request("/api/session", cookie=cookie, headers=headers)
        value = self._json_checked(check, response)
        if response.status != 200 or value.get("authenticated") is not True:
            self._fail(check, "authentication")
        user_id = value.get("user_id")
        tenant_id = value.get("tenant_id")
        roles = value.get("roles")
        csrf = value.get("csrf_token")
        if not all(isinstance(item, str) and item for item in (user_id, tenant_id, csrf)):
            self._fail(check, "authentication")
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            self._fail(check, "authentication")
        self.checks[check] = True
        return Session(cookie, csrf, user_id, tenant_id, frozenset(roles))

    def _json_checked(self, check: str, response: HttpResponse) -> dict[str, Any]:
        if response.status >= 400:
            self._fail(check, "http_error")
        return _json_object(response)

    def _check_service_status(self, check: str, response: HttpResponse, expected: str) -> None:
        if response.status != 200:
            self._fail(check, "preflight")
        value = _json_object(response)
        if value != {"status": expected}:
            self._fail(check, "preflight")
        self.checks[check] = True

    def _discover_demo_backend(self, config: Mapping[str, Any]) -> None:
        backends = config.get("backends")
        if not isinstance(backends, list):
            self._fail("public_config", "protocol")
        demo = next((item for item in backends if isinstance(item, dict) and item.get("id") == "demo"), None)
        if not isinstance(demo, dict) or demo.get("available") is not True:
            self._fail("public_config", "demo_unavailable")

    def _check_github_preview(self, session: Session) -> None:
        """Exercise the deployed read-only connector through the real edge."""

        response = self.client.request(
            "/api/connectors/github/preview",
            cookie=session.cookie,
            method="POST",
            body=GITHUB_ACCEPTANCE_TARGET,
            origin=self.client.origin,
            headers={"X-CSRF-Token": session.csrf_token},
        )
        value = self._json_checked("github_preview", response)
        source = value.get("source")
        encoded = value.get("content_base64")
        size = value.get("size")
        expected_url = (
            "https://github.com/Anil-matcha/Open-Dots/blob/"
            + GITHUB_ACCEPTANCE_TARGET["ref"]
            + "/README.md"
        )
        if (
            response.status != 200
            or not isinstance(source, dict)
            or any(source.get(key) != expected for key, expected in GITHUB_ACCEPTANCE_TARGET.items())
            or source.get("blob_sha") != GITHUB_ACCEPTANCE_BLOB_SHA
            or source.get("url") != expected_url
            or not isinstance(encoded, str)
            or type(size) is not int
            or not 1 <= size <= 32_768
        ):
            self._fail("github_preview", "github_connector")
        try:
            snapshot = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise AcceptanceError("github_connector", "github_preview") from exc
        expected_header = (
            "GitHub source: Anil-matcha/Open-Dots@"
            + GITHUB_ACCEPTANCE_TARGET["ref"]
            + " README.md (blob "
            + GITHUB_ACCEPTANCE_BLOB_SHA
            + ")\nSource URL: "
            + expected_url
            + "\n\n"
        ).encode("ascii")
        payload = snapshot[len(expected_header):]
        computed_blob_sha = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload,
            usedforsecurity=False,
        ).hexdigest()
        try:
            decoded_text = snapshot.decode("utf-8")
        except UnicodeDecodeError:
            self._fail("github_preview", "github_connector")
        if (
            len(snapshot) != size
            or not snapshot.startswith(expected_header)
            or not payload
            or computed_blob_sha != GITHUB_ACCEPTANCE_BLOB_SHA
            or value.get("text") != decoded_text
        ):
            self._fail("github_preview", "github_connector")
        self.checks["github_preview"] = True

    def _discover_workspace(self, config: Mapping[str, Any]) -> str:
        workspace = config.get("default_workspace", config.get("workspace"))
        if not isinstance(workspace, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", workspace):
            self._fail("public_config", "workspace_missing")
        return workspace

    def _discover_agent(self, config: Mapping[str, Any]) -> str:
        configured = config.get("agent", config.get("default_agent"))
        if isinstance(configured, str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", configured):
            return configured
        configured_agents = config.get("agents")
        if isinstance(configured_agents, list):
            configured_agents = configured_agents
        elif isinstance(configured_agents, dict):
            configured_agents = list(configured_agents.values())
        else:
            configured_agents = []
        for item in configured_agents:
            candidate = item if isinstance(item, str) else item.get("id") if isinstance(item, dict) else None
            if isinstance(candidate, str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", candidate):
                return candidate
        response = self.client.request("/api/agents", cookie=self.alice_cookie)
        value = self._json_checked("public_config", response)
        agents = value.get("agents")
        if not isinstance(agents, list):
            self._fail("public_config", "agent_missing")
        for item in agents:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                agent_id = item["id"]
                if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", agent_id):
                    return agent_id
        self._fail("public_config", "agent_missing")
        raise AssertionError("unreachable")

    def _fail(self, check: str, category: str) -> None:
        self.checks[check] = False
        raise AcceptanceError(category, check)

    def _soak(self) -> dict[str, Any]:
        assert self.soak is not None
        limits = self.soak
        # Every soak has a real wall-clock ceiling.  Request-count-only mode is
        # still capped at the global fifteen-minute maximum.
        deadline = time.monotonic() + (limits.duration or MAX_SOAK_DURATION)
        max_requests = limits.requests or MAX_SOAK_REQUESTS
        count_lock = threading.Lock()
        claimed_count = 0
        completed_count = 0
        statuses: dict[str, int] = {}
        latencies: list[float] = []
        failures = 0
        last_readiness = 0.0

        def worker() -> None:
            nonlocal claimed_count, completed_count, failures, last_readiness
            while True:
                with count_lock:
                    if claimed_count >= max_requests:
                        return
                    if time.monotonic() >= deadline:
                        return
                    claimed_count += 1
                    now = time.monotonic()
                    if now - last_readiness >= limits.readiness_interval:
                        endpoint = "/api/readiness"
                        last_readiness = now
                    else:
                        endpoint = "/api/health"
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return
                    response = self.client.request(
                        endpoint,
                        cookie=self.alice_cookie,
                        timeout=remaining,
                    )
                    status = str(response.status)
                    with count_lock:
                        statuses[status] = statuses.get(status, 0) + 1
                        latencies.append(response.elapsed_ms)
                        completed_count += 1
                        if response.status != 200:
                            failures += 1
                except AcceptanceError:
                    with count_lock:
                        statuses["error"] = statuses.get("error", 0) + 1
                        completed_count += 1
                        failures += 1

        with ThreadPoolExecutor(max_workers=limits.concurrency) as pool:
            futures = [pool.submit(worker) for _ in range(limits.concurrency)]
            for future in futures:
                future.result()
        return {
            "ok": failures == 0 and completed_count > 0,
            "requests": completed_count,
            "status_counts": statuses,
            "latency_ms": {
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "p99": _percentile(latencies, 0.99),
                "max": round(max(latencies), 3) if latencies else 0.0,
            },
        }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Run bounded checks against a public HTTPS staging origin.")
    parser.add_argument("--live-staging", action="store_true", help="Acknowledge that this contacts a live staging origin.")
    parser.add_argument("--origin")
    parser.add_argument("--alice-cookie-file")
    parser.add_argument("--bob-cookie-file")
    parser.add_argument("--required-role", action="append", default=["member"])
    parser.add_argument("--ca-file")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-response-bytes", type=int, default=DEFAULT_RESPONSE_LIMIT)
    parser.add_argument("--soak-duration", type=float, default=0.0)
    parser.add_argument("--soak-concurrency", type=int, default=1)
    parser.add_argument("--soak-requests", type=int, default=0)
    parser.add_argument("--soak-readiness-interval", type=float, default=15.0)
    return parser


def _args(argv: Sequence[str] | None) -> argparse.Namespace:
    args = _parser().parse_args(argv)
    if not args.live_staging or not args.origin or not args.alice_cookie_file or not args.bob_cookie_file:
        raise AcceptanceError("live_staging_acknowledgement")
    validate_origin(args.origin)
    if not 0 < args.timeout <= MAX_TIMEOUT or not 1 <= args.max_response_bytes <= MAX_RESPONSE_LIMIT:
        raise AcceptanceError("bounds")
    if not 0 <= args.soak_duration <= MAX_SOAK_DURATION:
        raise AcceptanceError("bounds")
    if not 1 <= args.soak_concurrency <= MAX_SOAK_CONCURRENCY:
        raise AcceptanceError("bounds")
    if not 0 <= args.soak_requests <= MAX_SOAK_REQUESTS:
        raise AcceptanceError("bounds")
    if not 1 <= args.soak_readiness_interval <= MAX_READINESS_INTERVAL:
        raise AcceptanceError("bounds")
    if args.soak_duration == 0 and args.soak_requests:
        pass
    if args.soak_duration > 0 and args.soak_requests == 0:
        # The client still has a hard request ceiling; a long duration cannot
        # turn into an unbounded load test.
        args.soak_requests = MAX_SOAK_REQUESTS
    roles = [role for role in args.required_role if isinstance(role, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", role)]
    if len(roles) != len(args.required_role) or not roles:
        raise AcceptanceError("bounds")
    return args


def run(argv: Sequence[str] | None = None) -> dict[str, Any]:
    try:
        args = _args(argv)
        alice = read_cookie_file(args.alice_cookie_file)
        bob = read_cookie_file(args.bob_cookie_file)
        soak = None
        if args.soak_duration or args.soak_requests:
            soak = SoakLimits(
                args.soak_duration,
                args.soak_concurrency,
                args.soak_requests,
                args.soak_readiness_interval,
            )
        client = StagingClient(
            args.origin,
            timeout=args.timeout,
            response_limit=args.max_response_bytes,
            ca_file=args.ca_file,
        )
        return StagingAcceptance(client, alice, bob, required_roles=args.required_role, soak=soak).run()
    except AcceptanceError as exc:
        return {"ok": False, "status": "failed", "category": exc.category, "checks": {}}
    except Exception:
        # Operational tools must never turn a traceback into a secret sink.
        return {"ok": False, "status": "failed", "category": "unexpected", "checks": {}}


def main(argv: Sequence[str] | None = None) -> int:
    result = run(argv)
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
