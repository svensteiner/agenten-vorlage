"""Authenticated, tenant-scoped public HTTP adapter for the local cockpit API.

The public adapter trusts identity only from an explicitly configured private
proxy network.  It maps every authenticated user to a private runtime tree and
never accepts host filesystem paths.  Executable workspace tools remain
disabled; the public DeepSeek policy, when configured, exposes only bounded
read/write/edit tools.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import signal
import socket
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agentkit.storage import lock
from agentkit.contracts import ContractError
from cockpit.conversations import Conversations
from cockpit.public_security import (
    AuthContext,
    PublicSecurityConfig,
    PublicSecurityError,
    RateLimiter,
    csrf_token,
    security_headers,
    validate_request,
    verify_csrf,
)
from cockpit.server import JobManager, TEMPLATE_ROOT, make_handler
from cockpit.tenancy import RuntimeLimitError, RuntimePaths, TenantRuntimeProvisioner


_SAFE_PUBLIC_BACKENDS = frozenset({"demo", "deepseek"})
_COOKIE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$", re.ASCII)
_STABLE_ERRORS = frozenset({
    "authentication_required", "csrf_rejected", "forbidden", "rate_limited",
    "service_not_ready", "service_busy", "job_not_found", "not_found", "invalid_request", "quota_exceeded",
})

_DEFAULT_DRAIN_TIMEOUT_SECONDS = 30
_MAX_DRAIN_TIMEOUT_SECONDS = 30
_OVERLOAD_RESPONSE = (
    b"HTTP/1.1 503 Service Unavailable\r\n"
    b"Content-Type: application/json; charset=utf-8\r\n"
    b"Content-Length: 24\r\n"
    b"Connection: close\r\n"
    b"Retry-After: 1\r\n"
    b"Cache-Control: no-store\r\n"
    b"\r\n"
    b'{"error":"service_busy"}'
)
# The edge proxy rejects bodies above 3 MiB. Allow additional room for headers
# so every request admitted by that boundary can be drained without buffering it.
_OVERLOAD_DRAIN_BYTES = (3 * 1024 * 1024) + (64 * 1024)


class _UserStorageQuotaExceeded(ContractError):
    """Raised when persisted user data already exceeds its configured quota."""


def _single_header(headers, name: str) -> str:
    values = [value.strip() for key, value in headers.items() if key.lower() == name.lower()]
    if len(values) != 1:
        return ""
    return values[0]


class AuditLog:
    """Append a payload-free HMAC hash chain for security-relevant requests."""

    def __init__(self, path: Path, secret: bytes, *, max_bytes: int = 8 * 1024 * 1024):
        if max_bytes < 64 * 1024:
            raise ValueError("Audit log limit must be at least 64 KiB.")
        self.path = path
        audit_directory_existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret
        self.max_bytes = max_bytes
        self.marker = self.path.with_suffix(".initialized")
        self.bootstrap_marker = self.path.parent.parent / ".audit-initialized"
        marker_digest = hmac.new(self.secret, b"agentkit-public-audit-initialized", hashlib.sha256).hexdigest()
        bootstrap_digest = hmac.new(self.secret, b"agentkit-public-audit-bootstrap", hashlib.sha256).hexdigest()
        self._marker_digest = marker_digest
        self._bootstrap_digest = bootstrap_digest
        evidence = (self.path.exists(), self.marker.exists(), self.bootstrap_marker.exists())
        fresh = not any(evidence)
        if fresh and audit_directory_existed:
            raise RuntimeError("Public audit initialization evidence is missing.")
        if not fresh and not all(evidence):
            raise RuntimeError("Public audit log or initialization marker is missing.")

        def validate_marker(marker: Path, expected: str) -> None:
            try:
                if marker.is_symlink() or not marker.is_file() or marker.read_text(encoding="ascii") != expected:
                    raise RuntimeError("Public audit marker integrity cannot be established.")
            except OSError as exc:
                raise RuntimeError("Public audit marker integrity cannot be established.") from exc

        def create_marker(marker: Path, encoded: str) -> None:
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(descriptor, encoded.encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        if fresh:
            create_marker(self.bootstrap_marker, bootstrap_digest)
            create_marker(self.marker, marker_digest)
        else:
            validate_marker(self.marker, marker_digest)
            validate_marker(self.bootstrap_marker, bootstrap_digest)
            if not self.path.is_file() or self.path.is_symlink():
                raise RuntimeError("Public audit log is missing after initialization.")
        self._lock = threading.Lock()
        self._previous = self._read_previous()
        if fresh:
            self.append(
                request_id="startup",
                context=None,
                method="SYSTEM",
                path="audit_initialized",
                status=200,
            )

    def _read_previous(self) -> str:
        if not self.path.is_file():
            return "0" * 64
        try:
            previous = "0" * 64
            seen = False
            with self.path.open("rb") as handle:
                for raw_line in handle:
                    if not raw_line.endswith(b"\n") or len(raw_line) > 8_192:
                        raise ValueError("invalid audit record framing")
                    value = json.loads(raw_line.decode("utf-8"))
                    if not isinstance(value, dict):
                        raise ValueError("invalid audit record")
                    digest = value.pop("event_hmac", "")
                    if (
                        not isinstance(digest, str)
                        or len(digest) != 64
                        or value.get("previous_hmac") != previous
                    ):
                        raise ValueError("invalid audit chain")
                    canonical = json.dumps(
                        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                    expected = hmac.new(self.secret, canonical, hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(digest, expected):
                        raise ValueError("invalid audit signature")
                    previous = digest
                    seen = True
            if seen:
                return previous
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
            pass
        # A malformed or truncated audit chain is not silently continued.
        raise RuntimeError("Public audit log integrity cannot be established.")

    def append(self, *, request_id: str, context: AuthContext | None, method: str, path: str, status: int) -> None:
        def opaque(value: str) -> str:
            return hmac.new(self.secret, b"audit\0" + value.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

        event = {
            "at": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "tenant": opaque(context.tenant_id) if context else "",
            "user": opaque(context.user_id) if context else "",
            "method": method,
            "path": path[:300],
            "status": int(status),
        }
        with self._lock:
            try:
                current_size = self.path.stat().st_size if self.path.exists() else 0
            except OSError as exc:
                raise RuntimeError("Public audit log cannot be inspected.") from exc
            if current_size + 8_192 > self.max_bytes:
                reset = {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "request_id": "rotation",
                    "tenant": "",
                    "user": "",
                    "method": "SYSTEM",
                    "path": "audit_rotation",
                    "status": 200,
                    "prior_hmac": self._previous,
                    "previous_hmac": "0" * 64,
                }
                canonical = json.dumps(
                    reset, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
                digest = hmac.new(self.secret, canonical, hashlib.sha256).hexdigest()
                reset["event_hmac"] = digest
                encoded_reset = (
                    json.dumps(reset, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                ).encode("utf-8")
                descriptor, temporary = tempfile.mkstemp(
                    prefix=".audit-", suffix=".tmp", dir=self.path.parent
                )
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(encoded_reset)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, self.path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
                self._previous = digest
            event["previous_hmac"] = self._previous
            canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            digest = hmac.new(self.secret, canonical, hashlib.sha256).hexdigest()
            event["event_hmac"] = digest
            encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._previous = digest

    def healthy(self, *, minimum_free_bytes: int = 64 * 1024 * 1024) -> bool:
        try:
            return (
                self.path.is_file()
                and self.marker.is_file()
                and self.bootstrap_marker.is_file()
                and self.marker.read_text(encoding="ascii") == self._marker_digest
                and self.bootstrap_marker.read_text(encoding="ascii") == self._bootstrap_digest
                and self.path.stat().st_size <= self.max_bytes + 8_192
                and shutil.disk_usage(self.path.parent).free >= minimum_free_bytes
            )
        except OSError:
            return False


class WorkspaceQuota:
    """Serialize every durable user write against one prospective quota."""

    def __init__(
        self,
        root: Path,
        *,
        max_bytes: int,
        max_files: int,
        allowed_root: Path | None = None,
        max_directories: int | None = None,
    ):
        raw_root = Path(root).absolute()
        if raw_root.is_symlink() or bool(getattr(raw_root, "is_junction", lambda: False)()):
            raise ValueError("Workspace quota root must not be a symlink or junction.")
        raw_allowed = Path(allowed_root or root).absolute()
        if raw_allowed.is_symlink() or bool(getattr(raw_allowed, "is_junction", lambda: False)()):
            raise ValueError("Workspace quota root must not be a symlink or junction.")
        self.root = raw_root.resolve()
        self.allowed_root = raw_allowed.resolve()
        if not self.allowed_root.is_relative_to(self.root):
            raise ValueError("Workspace quota root must stay inside the user storage root.")
        self.max_bytes = max_bytes
        self.max_files = max_files
        self.max_directories = max_files if max_directories is None else max_directories
        if self.max_directories < 0:
            raise ValueError("Storage directory quota must not be negative.")
        self._lock = threading.RLock()

    @staticmethod
    def _is_link(path: Path) -> bool:
        return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())

    def _validate_path(self, value: Path, *, directory: bool = False) -> Path:
        """Validate a prospective path and every existing ancestor."""

        raw = Path(value).absolute()
        if self._is_link(raw):
            raise ContractError("Workspace quota cannot traverse links or junctions.")
        candidate = raw.resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise ContractError("Storage mutation escaped its quota root.")
        current = self.root
        if self._is_link(current):
            raise ContractError("Workspace quota cannot traverse links or junctions.")
        for part in candidate.relative_to(self.root).parts:
            current = current / part
            if current.exists() and self._is_link(current):
                raise ContractError("Workspace quota cannot traverse links or junctions.")
        if candidate.exists() and directory and not candidate.is_dir():
            raise ContractError("Storage coordination path must be a directory.")
        return candidate

    class _Reservation:
        def __init__(
            self,
            quota: "WorkspaceQuota",
            files: tuple[tuple[Path, int, int], ...],
            directories: tuple[tuple[Path, int, int], ...],
        ):
            self._quota = quota
            self._files = files
            self._directories = directories
            self._committed = False

        def commit(self) -> None:
            with self._quota._lock:
                self._committed = True

        def rollback(self) -> None:
            with self._quota._lock:
                if self._committed:
                    return
                for path, device, inode in self._files:
                    try:
                        current = path.stat(follow_symlinks=False)
                        if (current.st_dev, current.st_ino) == (device, inode) and path.is_file() and not self._quota._is_link(path):
                            path.unlink()
                    except OSError:
                        pass
                for path, device, inode in reversed(self._directories):
                    try:
                        current = path.stat(follow_symlinks=False)
                        if (current.st_dev, current.st_ino) == (device, inode) and path.is_dir() and not self._quota._is_link(path):
                            path.rmdir()
                    except OSError:
                        pass

    def reserve_coordination(self, run_directory: Path, workspace: Path) -> "WorkspaceQuota._Reservation":
        """Admit a run directory and both lock files as one quota mutation."""

        with self._lock:
            run_directory = self._validate_path(run_directory, directory=True)
            workspace = self._validate_path(workspace, directory=True)
            if not workspace.is_dir():
                raise ContractError("Storage coordination workspace must be a directory.")
            run_lock = run_directory / ".lock"
            workspace_lock = workspace / ".agentkit.lock"
            for path in (run_lock, workspace_lock):
                self._validate_path(path)
                if path.exists() and not path.is_file():
                    raise ContractError("Storage coordination lock must be a regular file.")

            missing_dirs: list[Path] = []
            ancestor = run_directory
            while not ancestor.exists():
                if ancestor == self.root or not ancestor.is_relative_to(self.root):
                    raise ContractError("Storage coordination escaped its quota root.")
                missing_dirs.append(ancestor)
                ancestor = ancestor.parent
            if self._is_link(ancestor) or not ancestor.is_dir():
                raise ContractError("Storage coordination parent must be a directory.")
            new_files = tuple(path for path in (run_lock, workspace_lock) if not path.exists())
            total, files, directories = self._measure()
            if total + len(new_files) > self.max_bytes:
                raise ContractError("Storage byte quota exceeded.")
            if files + len(new_files) > self.max_files:
                raise ContractError("Storage file quota exceeded.")
            if directories + len(missing_dirs) > self.max_directories:
                raise ContractError("Storage directory quota exceeded.")

            created_dirs: list[Path] = []
            created_files: list[Path] = []
            try:
                for path in reversed(missing_dirs):
                    try:
                        path.mkdir()
                        created_dirs.append(path)
                    except FileExistsError:
                        if self._is_link(path) or not path.is_dir():
                            raise ContractError("Storage coordination parent must be a directory.")
                for path in new_files:
                    try:
                        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        try:
                            os.write(descriptor, b"0")
                            os.fsync(descriptor)
                        finally:
                            os.close(descriptor)
                        created_files.append(path)
                    except FileExistsError:
                        if self._is_link(path) or not path.is_file():
                            raise ContractError("Storage coordination lock must be a regular file.")
            except Exception:
                # Both lock files are permanent infrastructure.  Once either
                # pathname is published, another process may have opened it;
                # unlinking it could strand that process on an unlinked inode
                # and allow a replacement lock to be acquired.  Empty
                # directories can still be cleaned up below, while a
                # directory containing a permanent lock is retained.
                for path in reversed(created_dirs):
                    try:
                        path.rmdir()
                    except OSError:
                        pass
                raise
            # Keep both the shared workspace lock and the per-run lock as
            # bounded, permanent infrastructure.  Rollback never unlinks a
            # lock pathname, so an already-open descriptor cannot be detached
            # from the lock that later processes acquire.
            directory_records = tuple(
                (path, path.stat(follow_symlinks=False).st_dev, path.stat(follow_symlinks=False).st_ino)
                for path in created_dirs
            )
            return self._Reservation(self, (), directory_records)

    def _measure(self) -> tuple[int, int, int]:
        total = 0
        files = 0
        directory_count = 0
        for current, directories, names in os.walk(self.root, followlinks=False):
            current_path = Path(current)
            safe_directories = []
            for name in directories:
                candidate = current_path / name
                if candidate.is_symlink() or bool(getattr(candidate, "is_junction", lambda: False)()):
                    raise ContractError("Workspace quota cannot traverse links or junctions.")
                safe_directories.append(name)
            directories[:] = safe_directories
            directory_count += len(safe_directories)
            for name in names:
                candidate = current_path / name
                if candidate.is_symlink() or bool(getattr(candidate, "is_junction", lambda: False)()):
                    raise ContractError("Workspace quota cannot traverse links or junctions.")
                try:
                    total += candidate.stat().st_size
                except OSError as exc:
                    raise ContractError("Workspace quota cannot inspect storage.") from exc
                files += 1
        return total, files, directory_count

    def usage(self) -> tuple[int, int]:
        with self._lock:
            total, files, _directories = self._measure()
            return total, files

    def within_limits(self) -> bool:
        try:
            with self._lock:
                total, files, directories = self._measure()
        except ContractError:
            return False
        return (
            total <= self.max_bytes
            and files <= self.max_files
            and directories <= self.max_directories
        )

    def _write(self, target: Path, data: bytes, *, allowed_root: Path) -> None:
        if not isinstance(data, bytes):
            raise ContractError("Storage mutation must contain bytes.")
        with self._lock:
            try:
                raw_target = Path(target).absolute()
                if raw_target.is_symlink() or bool(getattr(raw_target, "is_junction", lambda: False)()):
                    raise ContractError("Storage mutation cannot replace a link or junction.")
                target = raw_target.resolve(strict=False)
                if not target.is_relative_to(allowed_root) or target == allowed_root:
                    raise ContractError("Storage mutation escaped its quota root.")
                missing_parents: list[Path] = []
                ancestor = target.parent
                while not ancestor.exists():
                    if ancestor == allowed_root or not ancestor.is_relative_to(allowed_root):
                        raise ContractError("Storage mutation escaped its quota root.")
                    missing_parents.append(ancestor)
                    ancestor = ancestor.parent
                parent_ancestor = ancestor.resolve(strict=True)
                if not parent_ancestor.is_relative_to(allowed_root):
                    raise ContractError("Storage mutation escaped its quota root.")
                total, files, directories = self._measure()
                existed = target.exists()
                if existed and not target.is_file():
                    raise ContractError("Storage mutation target must be a regular file.")
                previous_size = target.stat().st_size if existed else 0
                if total - previous_size + len(data) > self.max_bytes:
                    raise ContractError("Storage byte quota exceeded.")
                if files + (0 if existed else 1) > self.max_files:
                    raise ContractError("Storage file quota exceeded.")
                if directories + len(missing_parents) > self.max_directories:
                    raise ContractError("Storage directory quota exceeded.")
                target.parent.mkdir(parents=True, exist_ok=True)
                parent = target.parent.resolve(strict=True)
                if not parent.is_relative_to(allowed_root):
                    raise ContractError("Storage mutation escaped its quota root.")
            except ContractError:
                raise
            except OSError as exc:
                raise ContractError("Storage mutation cannot be validated safely.") from exc
            descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                if raw_target.is_symlink() or bool(getattr(raw_target, "is_junction", lambda: False)()):
                    raise ContractError("Storage mutation cannot replace a link or junction.")
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def write(self, target: Path, data: bytes) -> None:
        """Write model output only inside the server-controlled workspace tree."""

        self._write(target, data, allowed_root=self.allowed_root)

    def write_user(self, target: Path, data: bytes) -> None:
        """Write trusted application state anywhere inside this user's tree."""

        self._write(target, data, allowed_root=self.root)


@dataclass(slots=True)
class PublicRuntime:
    manager: JobManager
    conversations: Conversations
    context: AuthContext
    csrf: str
    response_headers: dict[str, str]
    response_callback: Any


class _RequestAdmission:
    """One authenticated request admitted before or during a drain."""

    def __init__(self, application: "PublicApplication"):
        self._application = application
        self._lock = threading.Lock()
        self._released = False

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._application._release_request()


@dataclass(slots=True)
class _CachedRuntime:
    manager: JobManager
    conversations: Conversations
    paths: RuntimePaths
    quota: WorkspaceQuota


class PublicApplication:
    """Resolve authenticated requests to isolated per-user runtime instances."""

    def __init__(
        self,
        *,
        security: PublicSecurityConfig,
        data_root: Path,
        base_agents_root: Path,
        identity_secret: bytes,
        identity_issuer: str,
        identity_client_id: str,
        allowed_backends: set[str] | frozenset[str] = frozenset({"demo"}),
        deepseek_api_key: str | None = None,
        per_user_requests_per_minute: int = 120,
        per_tenant_requests_per_minute: int = 1_000,
        max_cached_runtimes: int = 128,
        max_users_per_tenant: int = 100,
        storage_quota_bytes: int = 256 * 1024 * 1024,
        storage_quota_files: int = 10_000,
        session_cookie_name: str = "_oauth2_proxy",
        jobs_per_user_per_hour: int = 20,
        jobs_per_tenant_per_hour: int = 200,
        max_concurrent_jobs: int = 4,
        max_active_jobs_per_user: int = 2,
        max_http_workers: int = 32,
        audit_max_bytes: int = 8 * 1024 * 1024,
    ):
        self.security = security
        self.data_root = Path(data_root).resolve()
        try:
            parsed_issuer = urlparse(identity_issuer)
            parsed_issuer.port
        except (TypeError, ValueError) as exc:
            raise ValueError("identity_issuer must be an exact HTTPS OIDC issuer") from exc
        if (
            not isinstance(identity_issuer, str)
            or identity_issuer != identity_issuer.strip()
            or parsed_issuer.scheme != "https"
            or not parsed_issuer.netloc
            or not parsed_issuer.hostname
            or parsed_issuer.username is not None
            or parsed_issuer.password is not None
            or parsed_issuer.params
            or parsed_issuer.query
            or parsed_issuer.fragment
            or any(ord(character) < 33 or ord(character) == 127 for character in identity_issuer)
        ):
            raise ValueError("identity_issuer must be an exact HTTPS OIDC issuer")
        if (
            not isinstance(identity_client_id, str)
            or identity_client_id != identity_client_id.strip()
            or not identity_client_id
            or len(identity_client_id) > 512
            or any(ord(character) < 33 or ord(character) == 127 for character in identity_client_id)
        ):
            raise ValueError("identity_client_id must be bounded non-empty text")
        identity_namespace = json.dumps(
            {
                "client_id": identity_client_id,
                "issuer": identity_issuer,
                "scheme": "oidc-sub-v1",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        self.allowed_backends = frozenset(allowed_backends)
        if not self.allowed_backends or not self.allowed_backends <= {"demo", "deepseek", "codex"}:
            raise ValueError("Public backend policy is invalid.")
        if deepseek_api_key is not None and (
            not isinstance(deepseek_api_key, str)
            or not deepseek_api_key.strip()
            or len(deepseek_api_key) > 500
        ):
            raise ValueError("deepseek_api_key must be bounded non-empty text.")
        self._deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key is not None else None
        if (per_user_requests_per_minute < 1 or per_tenant_requests_per_minute < 1
                or jobs_per_user_per_hour < 1 or jobs_per_tenant_per_hour < 1):
            raise ValueError("Public request limits must be positive.")
        if storage_quota_bytes < 1 or storage_quota_files < 1:
            raise ValueError("Public storage quotas must be positive.")
        if max_concurrent_jobs < 1 or max_concurrent_jobs > 128:
            raise ValueError("max_concurrent_jobs must be between 1 and 128.")
        if max_active_jobs_per_user < 1 or max_active_jobs_per_user > 128:
            raise ValueError("max_active_jobs_per_user must be between 1 and 128.")
        if max_http_workers < 1 or max_http_workers > 256:
            raise ValueError("max_http_workers must be between 1 and 256.")
        if max_cached_runtimes < max_users_per_tenant:
            raise ValueError("Runtime cache must cover the configured single-tenant user limit.")
        if not _COOKIE_NAME.fullmatch(session_cookie_name):
            raise ValueError("Public session cookie name is invalid.")
        self.per_user_requests_per_minute = per_user_requests_per_minute
        self.per_tenant_requests_per_minute = per_tenant_requests_per_minute
        self.storage_quota_bytes = storage_quota_bytes
        self.storage_quota_files = storage_quota_files
        self.session_cookie_name = session_cookie_name
        self.jobs_per_user_per_hour = jobs_per_user_per_hour
        self.jobs_per_tenant_per_hour = jobs_per_tenant_per_hour
        self.max_active_jobs_per_user = max_active_jobs_per_user
        self.max_http_workers = max_http_workers
        self.worker_semaphore = threading.BoundedSemaphore(max_concurrent_jobs)
        self._drain_lock = threading.Lock()
        self._drain_condition = threading.Condition(self._drain_lock)
        self._draining = False
        self._active_requests = 0
        self.provisioner = TenantRuntimeProvisioner(
            self.data_root,
            base_agents_root,
            identity_secret=identity_secret,
            identity_namespace=identity_namespace,
            max_cached_runtimes=max_cached_runtimes,
            max_users_per_tenant=max_users_per_tenant,
        )
        self.rate_limiter = RateLimiter(window_seconds=60, max_entries=max_cached_runtimes * 8 + 256)
        self.job_rate_limiter = RateLimiter(window_seconds=3_600, max_entries=max_cached_runtimes * 4 + 128)
        self.audit = AuditLog(
            self.data_root / "audit" / "events.jsonl",
            identity_secret,
            max_bytes=audit_max_bytes,
        )

    def ready(self) -> bool:
        """Public readiness is false when an unsafe host executor is enabled."""
        with self._drain_lock:
            draining = self._draining
        return (
            not draining and bool(self.allowed_backends)
            and self.allowed_backends <= _SAFE_PUBLIC_BACKENDS
            and ("deepseek" not in self.allowed_backends or bool(self._deepseek_api_key))
            and self.audit.healthy()
        )

    def is_draining(self) -> bool:
        """Return whether the process is draining and closed to new work."""

        with self._drain_lock:
            return self._draining

    def begin_drain(self) -> bool:
        """Atomically stop admission of new authenticated requests.

        Existing jobs are intentionally left untouched.  Their workers remain
        observable and can finish through :meth:`wait_for_jobs`, preserving the
        unknown-outcome semantics used by the runtime on abrupt termination.
        """

        with self._drain_lock:
            already_draining = self._draining
            self._draining = True
            self._drain_condition.notify_all()
            return not already_draining

    def _admit_authenticated_request(self) -> _RequestAdmission | None:
        """Atomically admit an authenticated request unless draining."""

        with self._drain_lock:
            if self._draining:
                return None
            # This check is part of the admission transaction.  Once admitted,
            # a request is allowed to finish dispatching even if drain starts.
            if not (
                bool(self.allowed_backends)
                and self.allowed_backends <= _SAFE_PUBLIC_BACKENDS
                and ("deepseek" not in self.allowed_backends or bool(self._deepseek_api_key))
                and self.audit.healthy()
            ):
                return None
            self._active_requests += 1
            return _RequestAdmission(self)

    def _release_request(self) -> None:
        with self._drain_condition:
            if self._active_requests > 0:
                self._active_requests -= 1
            if self._active_requests == 0:
                self._drain_condition.notify_all()

    def _wait_for_requests(self, timeout: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        with self._drain_condition:
            while self._active_requests:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._drain_condition.wait(remaining)
            return True

    def wait_for_jobs(self, timeout: float = 30.0) -> bool:
        """Drain active per-user workers before closing persistent storage."""

        timeout = min(max(0.0, timeout), _MAX_DRAIN_TIMEOUT_SECONDS)
        deadline = time.monotonic() + timeout
        if not self._wait_for_requests(timeout):
            return False
        complete = True
        for runtime in self.provisioner.cached_runtimes():
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not runtime.manager.wait_for_workers(remaining):
                complete = False
        return complete

    def response_headers(self, request_id: str) -> dict[str, str]:
        headers = security_headers(self.security)
        headers["X-Request-ID"] = request_id
        headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        return headers

    def _factory(self, paths: RuntimePaths) -> _CachedRuntime:
        quota = WorkspaceQuota(
            paths.user_root,
            max_bytes=self.storage_quota_bytes,
            max_files=self.storage_quota_files,
            allowed_root=paths.workspaces_root,
        )
        if not quota.within_limits():
            raise _UserStorageQuotaExceeded("User storage quota is already exceeded.")
        manager = JobManager(
            template_root=TEMPLATE_ROOT,
            state_dir=paths.state_root,
            max_active=self.max_active_jobs_per_user,
            agent_roots=(paths.agents_root,),
            generated_root=paths.agents_root,
            workspace_root=paths.workspaces_root,
            public_mode=True,
            allowed_backends=set(self.allowed_backends),
            provider_api_key=self._deepseek_api_key,
            worker_semaphore=self.worker_semaphore,
            mutation_writer=quota.write,
            storage_writer=quota.write_user,
            coordination_reserver=quota.reserve_coordination,
        )
        return _CachedRuntime(manager, Conversations(manager), paths, quota)

    @staticmethod
    def _authorize(context: AuthContext, method: str, path: str) -> bool:
        roles = set(context.roles)
        if not roles & {"viewer", "member", "reviewer", "tenant_admin"}:
            return False
        if path.startswith("/api/providers/"):
            return method.upper() == "GET"
        if method.upper() == "POST":
            if path.endswith("/approval"):
                return bool(roles & {"reviewer", "tenant_admin"})
            return bool(roles & {"member", "tenant_admin"})
        return True

    def resolve(self, handler) -> PublicRuntime | None:
        request_id = uuid.uuid4().hex
        handler._extra_response_headers = self.response_headers(request_id)
        method = handler.command.upper()
        path = urlparse(handler.path).path
        context: AuthContext | None = None

        def reject(status: int, code: str) -> None:
            self.audit.append(request_id=request_id, context=context, method=method, path=path, status=status)
            handler._response_recorded = True
            handler._send(status, {"error": code})

        try:
            context = validate_request(handler.client_address[0], handler.headers, self.security)
        except PublicSecurityError:
            reject(HTTPStatus.UNAUTHORIZED, "authentication_required")
            return None

        cookie = _single_header(handler.headers, "Cookie")
        session_values = []
        if cookie and len(cookie) <= 8_192 and "\r" not in cookie and "\n" not in cookie:
            for item in cookie.split(";"):
                name, separator, value = item.strip().partition("=")
                if separator and name == self.session_cookie_name and value:
                    session_values.append(value)
        if len(session_values) != 1 or len(session_values[0]) > 4_096:
            reject(HTTPStatus.UNAUTHORIZED, "authentication_required")
            return None
        session_id = hashlib.sha256(session_values[0].encode("utf-8")).hexdigest()
        admission = self._admit_authenticated_request()
        if admission is None:
            reject(HTTPStatus.SERVICE_UNAVAILABLE, "service_not_ready")
            return None
        handler._request_admission = admission
        try:
            verify_csrf(method, handler.headers, context, session_id, self.security)
        except PublicSecurityError:
            reject(HTTPStatus.FORBIDDEN, "csrf_rejected")
            return None
        if not self._authorize(context, method, path):
            reject(HTTPStatus.FORBIDDEN, "forbidden")
            return None

        for key, limit in (
            (f"user:{context.tenant_id}:{context.user_id}", self.per_user_requests_per_minute),
            (f"tenant:{context.tenant_id}", self.per_tenant_requests_per_minute),
        ):
            decision = self.rate_limiter.allow(key, limit=limit)
            if not decision.allowed:
                handler._extra_response_headers["Retry-After"] = str(decision.retry_after)
                reject(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited")
                return None
        starts_job = method == "POST" and (
            path == "/api/jobs" or bool(re.fullmatch(r"/api/conversations/[0-9a-f]{32}/messages", path))
        )
        if starts_job:
            for key, limit in (
                (f"user:{context.tenant_id}:{context.user_id}", self.jobs_per_user_per_hour),
                (f"tenant:{context.tenant_id}", self.jobs_per_tenant_per_hour),
            ):
                decision = self.job_rate_limiter.allow(key, limit=limit)
                if not decision.allowed:
                    handler._extra_response_headers["Retry-After"] = str(decision.retry_after)
                    reject(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited")
                    return None
        try:
            cached = self.provisioner.runtime(context.tenant_id, context.user_id, self._factory)
        except _UserStorageQuotaExceeded:
            reject(HTTPStatus.INSUFFICIENT_STORAGE, "quota_exceeded")
            return None
        except (RuntimeLimitError, OSError, ValueError):
            reject(HTTPStatus.SERVICE_UNAVAILABLE, "service_not_ready")
            return None
        if method == "POST" and not cached.quota.within_limits():
            reject(HTTPStatus.INSUFFICIENT_STORAGE, "quota_exceeded")
            return None

        def record(status: int) -> None:
            self.audit.append(request_id=request_id, context=context, method=method, path=path, status=status)

        return PublicRuntime(
            manager=cached.manager,
            conversations=cached.conversations,
            context=context,
            csrf=csrf_token(self.security.csrf_secret, context, session_id),
            response_headers=self.response_headers(request_id),
            response_callback=record,
        )


def make_public_handler(application: PublicApplication):
    base = make_handler(None, runtime_resolver=application.resolve)

    class PublicHandler(base):
        server_version = "AgentKitPublic/1"

        def _release_request_admission(self) -> None:
            admission = getattr(self, "_request_admission", None)
            if admission is not None:
                self._request_admission = None
                admission.release()

        def _send(self, status: int, value: Any, content_type: str = "application/json", *, download: bool = False, filename: str = ""):
            try:
                self._extra_response_headers = {
                    **application.response_headers(getattr(self, "_request_id", uuid.uuid4().hex)),
                    **getattr(self, "_extra_response_headers", {}),
                }
                if int(status) == HTTPStatus.BAD_REQUEST and isinstance(value, dict):
                    raw_error = value.get("error")
                    if isinstance(raw_error, str) and "not found" in raw_error.lower():
                        status = HTTPStatus.NOT_FOUND
                        value = {"error": "not_found"}
                    elif isinstance(raw_error, str) and "worker slots are busy" in raw_error.lower():
                        status = HTTPStatus.SERVICE_UNAVAILABLE
                        value = {"error": "service_busy"}
                        self._extra_response_headers["Retry-After"] = "1"
                    elif isinstance(raw_error, str) and "quota" in raw_error.lower():
                        status = HTTPStatus.INSUFFICIENT_STORAGE
                        value = {"error": "quota_exceeded"}
                if int(status) >= 400 and isinstance(value, dict) and "error" in value:
                    code = value.get("error")
                    if code not in _STABLE_ERRORS:
                        value = {"error": "invalid_request" if int(status) < 500 else "service_not_ready"}
                return super()._send(status, value, content_type, download=download, filename=filename)
            finally:
                # A broken pipe, audit exception, or normal response must all
                # release the same admission exactly once.
                self._release_request_admission()

        def finish(self):
            try:
                super().finish()
            finally:
                # Covers exceptions raised before a response can be emitted.
                self._release_request_admission()

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/health":
                self._response_recorded = True
                self._response_callback = None
                self._extra_response_headers = application.response_headers(uuid.uuid4().hex)
                self._send(HTTPStatus.OK, {"status": "ok"})
                return
            if path == "/api/readiness":
                self._response_recorded = True
                self._response_callback = None
                self._extra_response_headers = application.response_headers(uuid.uuid4().hex)
                ready = application.ready()
                status = HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE
                self._send(status, {"status": "ready" if ready else "not_ready"})
                return
            if path == "/api/session":
                if not self._prepare_request():
                    return
                runtime = self._active_runtime
                self._send(HTTPStatus.OK, {
                    "authenticated": True,
                    "tenant_id": runtime.context.tenant_id,
                    "user_id": runtime.context.user_id,
                    "roles": list(runtime.context.roles),
                    "csrf_token": runtime.csrf,
                })
                return
            super().do_GET()

        def log_message(self, format: str, *args):
            return

    return PublicHandler


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Bound concurrent public connections and slow header/body readers."""

    daemon_threads = True
    request_queue_size = 128

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        *,
        max_workers: int = 32,
        overload_send_timeout: float = 1.0,
    ):
        if max_workers < 1 or max_workers > 256:
            raise ValueError("max_workers must be between 1 and 256")
        if not 0.1 <= overload_send_timeout <= 10:
            raise ValueError("overload_send_timeout must be between 0.1 and 10 seconds")
        self.overload_send_timeout = overload_send_timeout
        self._worker_slots = threading.BoundedSemaphore(max_workers)
        super().__init__(server_address, RequestHandlerClass)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(15)
        return request, address

    def process_request(self, request, client_address):
        if not self._worker_slots.acquire(blocking=False):
            deadline = time.monotonic() + self.overload_send_timeout
            try:
                request.settimeout(self.overload_send_timeout)
                request.sendall(_OVERLOAD_RESPONSE)
                # Windows can reset a just-closed TCP connection when inbound
                # request bytes remain unread, discarding the 503 we sent. End
                # the response first, then drain any request admitted by the
                # edge-size boundary within the same timeout.
                request.shutdown(socket.SHUT_WR)
                drained = 0
                while drained < _OVERLOAD_DRAIN_BYTES:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    request.settimeout(remaining)
                    chunk = request.recv(min(4096, _OVERLOAD_DRAIN_BYTES - drained))
                    if not chunk:
                        break
                    drained += len(chunk)
            except OSError:
                # The client may have disconnected while waiting in the
                # accept queue.  Closing it is still the safe overload action.
                pass
            finally:
                self.close_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()


def _secret_file(name: str, *, minimum: int = 32) -> bytes:
    path = os.environ.get(name, "").strip()
    if not path:
        raise RuntimeError(f"{name} must name a deployment secret file.")
    # These files contain raw key material.  Whitespace bytes are valid key
    # bytes and must not be removed or transformed on load.
    value = Path(path).read_bytes()
    if len(value) < minimum:
        raise RuntimeError(f"{name} is too short.")
    return value


def _identity_user_header() -> str:
    """Return the one header backed by the vetted OIDC `sub` mapping."""

    value = os.environ.get("AGENTKIT_IDENTITY_USER_HEADER", "X-Forwarded-User").strip()
    if value.lower() != "x-forwarded-user":
        raise RuntimeError(
            "AGENTKIT_IDENTITY_USER_HEADER must be X-Forwarded-User for stable OIDC subject identity."
        )
    return "X-Forwarded-User"


def _identity_roles_header() -> str:
    """Return the one header populated from verified OIDC group claims."""

    value = os.environ.get("AGENTKIT_IDENTITY_ROLES_HEADER", "X-Forwarded-Groups").strip()
    if value.lower() != "x-forwarded-groups":
        raise RuntimeError(
            "AGENTKIT_IDENTITY_ROLES_HEADER must be X-Forwarded-Groups for verified OIDC roles."
        )
    return "X-Forwarded-Groups"


def _identity_tenant_header() -> str:
    """Return the only tenant header stripped by the vetted edge contract."""

    value = os.environ.get("AGENTKIT_IDENTITY_TENANT_HEADER", "X-Agent-Tenant").strip()
    if value.lower() != "x-agent-tenant":
        raise RuntimeError(
            "AGENTKIT_IDENTITY_TENANT_HEADER must be X-Agent-Tenant for the public proxy contract."
        )
    return "X-Agent-Tenant"


def _install_shutdown_handlers(application: PublicApplication, server: BoundedThreadingHTTPServer):
    """Install signal handlers without calling ``server.shutdown`` inline.

    ``BaseServer.shutdown`` waits for ``serve_forever`` to leave its loop, so
    invoking it from that same signal-handler thread can deadlock.  The handler
    only marks the application draining and wakes a coordinator thread.
    """

    stop_requested = threading.Event()
    previous_handlers = {}

    def request_shutdown(_signum, _frame):
        application.begin_drain()
        stop_requested.set()

    for signal_number in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[signal_number] = signal.getsignal(signal_number)
        signal.signal(signal_number, request_shutdown)

    def shutdown_coordinator():
        stop_requested.wait()
        server.shutdown()

    coordinator = threading.Thread(target=shutdown_coordinator, name="public-server-shutdown", daemon=True)
    coordinator.start()

    def restore():
        for signal_number, previous in previous_handlers.items():
            signal.signal(signal_number, previous)
        stop_requested.set()
        coordinator.join(timeout=2)

    return request_shutdown, restore


def _provider_secret_file() -> str | None:
    path = os.environ.get("AGENTKIT_PROVIDER_CREDENTIALS_FILE", "").strip()
    if not path:
        return None
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        key = value.get("deepseek_api_key") if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Provider credentials file is invalid.") from exc
    if not isinstance(key, str) or not key.strip() or len(key) > 500:
        raise RuntimeError("Provider credentials file has no valid DeepSeek key.")
    return key.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the authenticated AgentKit public gateway")
    # The public entrypoint is explicitly gated by AGENTKIT_PUBLIC=1 and is
    # exposed only on the private Compose frontend behind OIDC/TLS.
    parser.add_argument("--host", default=os.environ.get("AGENTKIT_BIND", "0.0.0.0"))  # nosec B104
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENTKIT_PORT", "8766")))
    args = parser.parse_args()
    if os.environ.get("AGENTKIT_PUBLIC") != "1":
        parser.error("Public gateway requires AGENTKIT_PUBLIC=1.")
    origin = os.environ.get("AGENTKIT_PUBLIC_ORIGIN", "").strip()
    cidrs = tuple(value.strip() for value in os.environ.get("AGENTKIT_TRUSTED_PROXY_CIDRS", "").split(",") if value.strip())
    csrf_secret = _secret_file("AGENTKIT_CSRF_SECRET_FILE")
    identity_secret = _secret_file("AGENTKIT_IDENTITY_SECRET_FILE")
    identity_tenant_header = _identity_tenant_header()
    identity_user_header = _identity_user_header()
    identity_roles_header = _identity_roles_header()
    def env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
        raw = os.environ.get(name, str(default)).strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise RuntimeError(f"{name} must be an integer.") from exc
        if value < minimum or value > maximum:
            raise RuntimeError(f"{name} must be between {minimum} and {maximum}.")
        return value

    drain_timeout = env_int(
        "AGENTKIT_DRAIN_TIMEOUT_SECONDS",
        _DEFAULT_DRAIN_TIMEOUT_SECONDS,
        minimum=1,
        maximum=_MAX_DRAIN_TIMEOUT_SECONDS,
    )
    application = PublicApplication(
        security=PublicSecurityConfig(
            public_origin=origin,
            trusted_proxy_cidrs=cidrs,
            csrf_secret=csrf_secret,
            identity_tenant_header=identity_tenant_header,
            identity_user_header=identity_user_header,
            identity_roles_header=identity_roles_header,
            fixed_tenant_id=os.environ.get("AGENTKIT_TENANT_ID", "").strip(),
        ),
        data_root=Path(os.environ.get("AGENTKIT_DATA_DIR", "/var/lib/agentkit")),
        base_agents_root=TEMPLATE_ROOT / "agents",
        identity_secret=identity_secret,
        identity_issuer=os.environ.get("AGENTKIT_AUTH_ISSUER", ""),
        identity_client_id=os.environ.get("AGENTKIT_AUTH_CLIENT_ID", ""),
        allowed_backends={value.strip() for value in os.environ.get("AGENTKIT_PUBLIC_BACKENDS", "demo").split(",") if value.strip()},
        deepseek_api_key=_provider_secret_file(),
        session_cookie_name=os.environ.get("AGENTKIT_SESSION_COOKIE_NAME", "_oauth2_proxy"),
        per_user_requests_per_minute=env_int("AGENTKIT_MAX_REQUESTS_PER_USER_PER_MINUTE", 120, minimum=1, maximum=100_000),
        per_tenant_requests_per_minute=env_int("AGENTKIT_MAX_REQUESTS_PER_TENANT_PER_MINUTE", 1_000, minimum=1, maximum=1_000_000),
        max_cached_runtimes=env_int("AGENTKIT_MAX_CACHED_RUNTIMES", 128, minimum=1, maximum=10_000),
        max_users_per_tenant=env_int("AGENTKIT_MAX_USERS_PER_TENANT", 100, minimum=1, maximum=10_000),
        storage_quota_bytes=env_int("AGENTKIT_STORAGE_QUOTA_BYTES", 256 * 1024 * 1024, minimum=1, maximum=100 * 1024 * 1024 * 1024),
        storage_quota_files=env_int("AGENTKIT_STORAGE_QUOTA_FILES", 10_000, minimum=1, maximum=1_000_000),
        jobs_per_user_per_hour=env_int("AGENTKIT_MAX_JOBS_PER_USER_PER_HOUR", 20, minimum=1, maximum=100_000),
        jobs_per_tenant_per_hour=env_int("AGENTKIT_MAX_JOBS_PER_TENANT_PER_HOUR", 200, minimum=1, maximum=1_000_000),
        max_concurrent_jobs=env_int("AGENTKIT_MAX_CONCURRENT_JOBS", 4, minimum=1, maximum=128),
        max_active_jobs_per_user=env_int("AGENTKIT_MAX_ACTIVE_JOBS_PER_USER", 2, minimum=1, maximum=128),
        max_http_workers=env_int("AGENTKIT_MAX_HTTP_WORKERS", 32, minimum=1, maximum=256),
        audit_max_bytes=env_int("AGENTKIT_AUDIT_MAX_BYTES", 8 * 1024 * 1024, minimum=64 * 1024, maximum=1024 * 1024 * 1024),
    )
    application.data_root.mkdir(parents=True, exist_ok=True)
    with lock(application.data_root / ".public-server.lock"):
        server = BoundedThreadingHTTPServer(
            (args.host, args.port), make_public_handler(application), max_workers=application.max_http_workers
        )
        print(f"AgentKit public gateway listening on {args.host}:{args.port}", flush=True)
        _request_shutdown, restore_handlers = _install_shutdown_handlers(application, server)
        try:
            server.serve_forever()
        finally:
            application.begin_drain()
            restore_handlers()
            application.wait_for_jobs(drain_timeout)
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
