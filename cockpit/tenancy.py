"""Filesystem tenancy primitives for public, multi-user deployments.

This module deliberately does not know about ``JobManager``.  It provisions a
small, private filesystem namespace and lets the caller construct its runtime
from the resulting paths.  Keeping that boundary explicit prevents identity
and path handling from leaking into the execution engine.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import shutil
import stat
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, TypeVar


class IdentityError(ValueError):
    """An identity or canonical resource identifier is invalid."""


class RuntimeLimitError(RuntimeError):
    """The process-local runtime cache has reached its configured limit."""


T = TypeVar("T")


@dataclass(frozen=True)
class RuntimePaths:
    """Canonical paths assigned to one user in one tenant."""

    data_root: Path
    tenant_id: str
    user_id: str
    tenant_root: Path
    user_root: Path
    agents_root: Path
    workspaces_root: Path
    state_root: Path
    default_workspace: Path


def _is_reparse_point(path: Path) -> bool:
    """Return whether *path* is a symlink or Windows reparse point."""

    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    except (FileNotFoundError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _assert_directory(path: Path, label: str) -> None:
    if _is_reparse_point(path):
        raise ValueError(f"{label} must not be a symlink or reparse point")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{label} must be a directory")


def _safe_component(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise IdentityError(f"{label} must be a non-empty string")
    if len(value) > 256 or "\x00" in value:
        raise IdentityError(f"{label} is too long or contains NUL")
    return value


def _canonical_id(value: str, label: str) -> str:
    """Validate an ID supplied by an API caller, never a filesystem path."""

    if not isinstance(value, str) or not value or len(value) > 66:
        raise IdentityError(f"{label} must be a canonical ID")
    if value in {".", ".."} or value[0] == ".":
        raise IdentityError(f"{label} must be a canonical ID")
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in value):
        raise IdentityError(f"{label} must be a canonical ID")
    return value


def _inside(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError:
        return False


class TenantRuntimeProvisioner(Generic[T]):
    """Provision isolated tenant/user roots and cache their runtimes.

    ``identity_secret`` should be supplied from a deployment secret.  When it
    is omitted, a random key is persisted below ``data_root`` so opaque names
    remain stable across process restarts without exposing the identity in a
    path.  The callback passed to :meth:`runtime` receives only ``RuntimePaths``.
    """

    _EXCLUDED_NAMES = frozenset(
        {
            ".git",
            ".runs",
            "secret-state",
            "secrets",
            "secret",
            "credentials",
            ".env",
            ".instructions.lock",
            "workspace",
        }
    )

    def __init__(
        self,
        data_root: os.PathLike[str] | str,
        base_agents_root: os.PathLike[str] | str,
        *,
        identity_secret: bytes | str | None = None,
        max_cached_runtimes: int = 64,
        max_users_per_tenant: int = 100,
    ) -> None:
        if max_cached_runtimes < 1 or max_users_per_tenant < 1:
            raise ValueError("runtime limits must be positive")
        self.data_root = Path(data_root).expanduser().absolute()
        self.base_agents_root = Path(base_agents_root).expanduser().absolute()
        _assert_directory(self.base_agents_root, "base agent root")
        if self.base_agents_root.exists() is False:
            raise FileNotFoundError(self.base_agents_root)
        self.data_root.parent.mkdir(parents=True, exist_ok=True)
        _assert_directory(self.data_root, "data root")
        self.data_root.mkdir(parents=True, exist_ok=True)
        if identity_secret is None:
            identity_secret = self._load_or_create_secret()
        elif isinstance(identity_secret, str):
            identity_secret = identity_secret.encode("utf-8")
        if not isinstance(identity_secret, bytes) or len(identity_secret) < 16:
            raise ValueError("identity_secret must contain at least 16 bytes")
        self._identity_secret = identity_secret
        self.max_cached_runtimes = max_cached_runtimes
        self.max_users_per_tenant = max_users_per_tenant
        self._provision_lock = threading.RLock()
        self._runtime_lock = threading.RLock()
        self._runtime_admission_lock = threading.Lock()
        self._runtime_cache: OrderedDict[tuple[str, str], T] = OrderedDict()
        self._tenant_users: dict[str, set[str]] = {}

    def _load_or_create_secret(self) -> bytes:
        secret_path = self.data_root / ".identity-key"
        if _is_reparse_point(secret_path):
            raise ValueError("identity key must not be a symlink or reparse point")
        try:
            return secret_path.read_bytes()
        except FileNotFoundError:
            secret = secrets.token_bytes(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                descriptor = os.open(secret_path, flags, 0o600)
                try:
                    os.write(descriptor, secret)
                finally:
                    os.close(descriptor)
                return secret
            except FileExistsError:
                return secret_path.read_bytes()

    def identity_ids(self, tenant_identity: str, user_identity: str) -> tuple[str, str]:
        tenant_identity = _safe_component(tenant_identity, "tenant identity")
        user_identity = _safe_component(user_identity, "user identity")
        # 128 opaque bits avoid Windows MAX_PATH failures once nested agent
        # resources are copied, while retaining a negligible collision risk.
        tenant = hmac.new(self._identity_secret, b"tenant\0" + tenant_identity.encode(), hashlib.sha256).hexdigest()[:32]
        user = hmac.new(self._identity_secret, b"user\0" + user_identity.encode(), hashlib.sha256).hexdigest()[:32]
        return f"t_{tenant}", f"u_{user}"

    def _validate_base_tree(self) -> None:
        for path in (self.base_agents_root, *self.base_agents_root.rglob("*")):
            if _is_reparse_point(path):
                raise ValueError(f"base agent tree contains a symlink or reparse point: {path.name}")

    def _copy_snapshot(self, destination: Path) -> None:
        self._validate_base_tree()
        destination.mkdir(parents=True, exist_ok=True)
        for source in sorted(self.base_agents_root.iterdir(), key=lambda item: item.name):
            if source.name.casefold() in self._EXCLUDED_NAMES:
                continue
            if source.name.startswith("."):
                continue
            if not source.is_dir():
                continue
            _canonical_id(source.name, "agent pack")
            target = destination / source.name
            if target.exists():
                continue
            self._copy_tree(source, target)

    def _copy_tree(self, source: Path, target: Path) -> None:
        if _is_reparse_point(source):
            raise ValueError(f"snapshot source contains a symlink or reparse point: {source.name}")
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=False)
            for child in sorted(source.iterdir(), key=lambda item: item.name):
                if child.name.casefold() in self._EXCLUDED_NAMES or (
                    child.name.startswith(".") and child.name != ".agents"
                ):
                    continue
                self._copy_tree(child, target / child.name)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        else:
            raise ValueError(f"unsupported snapshot entry: {source.name}")

    def provision(self, tenant_identity: str, user_identity: str) -> RuntimePaths:
        tenant_id, user_id = self.identity_ids(tenant_identity, user_identity)
        with self._provision_lock:
            # Validate the immutable source before creating any tenant state.
            self._validate_base_tree()
            tenant_root = self.data_root / "tenants" / tenant_id
            user_root = tenant_root / "users" / user_id
            _assert_directory(tenant_root.parent, "tenant root parent")
            tenant_root.mkdir(parents=True, exist_ok=True)
            _assert_directory(tenant_root, "tenant root")
            user_root.mkdir(parents=True, exist_ok=True)
            _assert_directory(user_root, "user root")
            agents_root = user_root / "agents"
            workspaces_root = user_root / "workspaces"
            state_root = user_root / "state"
            default_workspace = workspaces_root / "default"
            for path in (workspaces_root, state_root, default_workspace):
                _assert_directory(path, "runtime path")
                path.mkdir(parents=True, exist_ok=True)
            marker = agents_root / ".base-snapshot-complete"
            if agents_root.exists():
                _assert_directory(agents_root, "agent root")
                if _is_reparse_point(marker) or not marker.is_file():
                    raise ValueError("agent snapshot is incomplete")
            else:
                # Keep the staging prefix shallow: a deep temporary segment can
                # exceed the legacy Windows MAX_PATH limit before the atomic
                # rename into the final (shorter) ``agents`` directory.
                staging_parent = self.data_root / ".staging"
                staging_parent.mkdir(parents=True, exist_ok=True)
                staging = staging_parent / uuid.uuid4().hex[:12]
                try:
                    self._copy_snapshot(staging)
                    marker_in_staging = staging / marker.name
                    marker_in_staging.write_text("v1\n", encoding="ascii")
                    os.replace(staging, agents_root)
                finally:
                    if staging.exists():
                        shutil.rmtree(staging, ignore_errors=True)
            with self._runtime_lock:
                self._tenant_users.setdefault(tenant_id, set()).add(user_id)
            return RuntimePaths(
                data_root=self.data_root,
                tenant_id=tenant_id,
                user_id=user_id,
                tenant_root=tenant_root,
                user_root=user_root,
                agents_root=agents_root,
                workspaces_root=workspaces_root,
                state_root=state_root,
                default_workspace=default_workspace,
            )

    def paths_for(self, tenant_id: str, user_id: str) -> RuntimePaths:
        """Resolve only IDs previously returned by :meth:`identity_ids`."""

        tenant_id = _canonical_id(tenant_id, "tenant ID")
        user_id = _canonical_id(user_id, "user ID")
        tenant_root = self.data_root / "tenants" / tenant_id
        user_root = tenant_root / "users" / user_id
        if not user_root.is_dir() or _is_reparse_point(user_root):
            raise KeyError("unknown runtime")
        return RuntimePaths(
            data_root=self.data_root,
            tenant_id=tenant_id,
            user_id=user_id,
            tenant_root=tenant_root,
            user_root=user_root,
            agents_root=user_root / "agents",
            workspaces_root=user_root / "workspaces",
            state_root=user_root / "state",
            default_workspace=user_root / "workspaces" / "default",
        )

    def resolve_workspace(self, paths: RuntimePaths, workspace_id: str) -> Path:
        self._validate_runtime_paths(paths)
        workspace_id = _canonical_id(workspace_id, "workspace ID")
        candidate = paths.workspaces_root / workspace_id
        if not _inside(paths.workspaces_root, candidate) or _is_reparse_point(candidate) or not candidate.is_dir():
            raise KeyError("unknown workspace")
        return candidate

    def ensure_workspace(self, paths: RuntimePaths, workspace_id: str) -> Path:
        self._validate_runtime_paths(paths)
        workspace_id = _canonical_id(workspace_id, "workspace ID")
        candidate = paths.workspaces_root / workspace_id
        with self._provision_lock:
            _assert_directory(paths.workspaces_root, "workspace root")
            candidate.mkdir(parents=False, exist_ok=True)
            if _is_reparse_point(candidate) or not _inside(paths.workspaces_root, candidate):
                raise ValueError("workspace must remain inside the user root")
        return candidate

    def resolve_agent(self, paths: RuntimePaths, agent_id: str) -> Path:
        self._validate_runtime_paths(paths)
        agent_id = _canonical_id(agent_id, "agent ID")
        candidate = paths.agents_root / agent_id
        if not _inside(paths.agents_root, candidate) or _is_reparse_point(candidate) or not candidate.is_dir():
            raise KeyError("unknown agent")
        return candidate

    def _validate_runtime_paths(self, paths: RuntimePaths) -> None:
        """Reject forged or symlink-replaced path bundles before resolution."""

        if not isinstance(paths, RuntimePaths) or paths.data_root != self.data_root:
            raise IdentityError("runtime paths belong to another provisioner")
        expected_tenant = self.data_root / "tenants" / _canonical_id(paths.tenant_id, "tenant ID")
        expected_user = expected_tenant / "users" / _canonical_id(paths.user_id, "user ID")
        if paths.tenant_root != expected_tenant or paths.user_root != expected_user:
            raise IdentityError("runtime paths are not canonical")
        for path in (expected_tenant, expected_user, paths.agents_root, paths.workspaces_root, paths.state_root):
            if _is_reparse_point(path):
                raise ValueError("runtime path must not be a symlink or reparse point")
        if paths.agents_root != expected_user / "agents" or paths.workspaces_root != expected_user / "workspaces":
            raise IdentityError("runtime paths are not canonical")

    def runtime(self, tenant_identity: str, user_identity: str, factory: Callable[[RuntimePaths], T]) -> T:
        tenant_id, user_id = self.identity_ids(tenant_identity, user_identity)
        key = (tenant_id, user_id)
        with self._runtime_admission_lock:
            with self._runtime_lock:
                cached = self._runtime_cache.get(key)
                if cached is not None:
                    self._runtime_cache.move_to_end(key)
                    return cached
                active_users = sum(1 for cached_tenant, _ in self._runtime_cache if cached_tenant == tenant_id)
                if active_users >= self.max_users_per_tenant:
                    raise RuntimeLimitError("tenant user limit exceeded")
                if len(self._runtime_cache) >= self.max_cached_runtimes:
                    raise RuntimeLimitError("runtime cache limit exceeded")
            # Admission happens before provisioning, so rejected identities do
            # not create persistent user directories or copy assistant packs.
            paths = self.provision(tenant_identity, user_identity)
            with self._runtime_lock:
                cached = self._runtime_cache.get(key)
                if cached is not None:
                    self._runtime_cache.move_to_end(key)
                    return cached
                value = factory(paths)
                self._runtime_cache[key] = value
                return value

    def evict_runtime(self, tenant_identity: str, user_identity: str) -> bool:
        tenant_id, user_id = self.identity_ids(tenant_identity, user_identity)
        with self._runtime_lock:
            return self._runtime_cache.pop((tenant_id, user_id), None) is not None

    def cache_size(self) -> int:
        with self._runtime_lock:
            return len(self._runtime_cache)

    def cached_runtimes(self) -> tuple[T, ...]:
        """Return a stable snapshot for bounded graceful shutdown work."""

        with self._runtime_lock:
            return tuple(self._runtime_cache.values())
