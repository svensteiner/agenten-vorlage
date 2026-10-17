"""Host-owned policy and bounded Docker runner for an immutable test suite.

The container is a defense-in-depth boundary, not a proof against Docker or
kernel vulnerabilities. Agent actions never control its command line.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable

from .approvals import safe_workspace_path, workspace_fingerprint
from .contracts import ContractError


_HEX = re.compile(r"^[0-9a-f]{64}$")
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_DENIED_SEGMENTS = frozenset({
    ".aws", ".azure", ".codex", ".config", ".credentials", ".ssh",
    ".venv", "credentials", "secrets", "secret", "tokens", "token",
    "private", "private_keys", "certificates", "certs", "__pycache__",
    "node_modules", "vendor", "dist", "build",
})
_LOCK_LABEL = "org.agentkit.test-lock-sha256"
_PYTEST_COUNT_RE = re.compile(r"(?<![\w])(?P<count>\d+)\s+(?P<kind>passed|failed|error|errors|skipped|xfailed|xpassed|deselected)(?![\w])")
_LIMITS = MappingProxyType({
    "timeout_seconds": 180,
    "output_bytes": 2_000_000,
    "memory_bytes": 128 * 1024 * 1024,
    "memory_swap_bytes": 128 * 1024 * 1024,
    "nano_cpus": 1_000_000_000,
    "pids": 32,
    "nofile": 64,
    "tmpfs_bytes": 16 * 1024 * 1024,
    "max_file_bytes": 2 * 1024 * 1024,
    "max_snapshot_bytes": 64 * 1024 * 1024,
    "max_runs_per_run": 4,
})


def _canonical_path(value: object) -> str:
    if (not isinstance(value, str) or not value or len(value) > 500
            or "\\" in value or ":" in value or "\x00" in value
            or unicodedata.normalize("NFC", value) != value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ContractError("Test manifest paths must be canonical relative POSIX paths.")
    parts = value.split("/")
    if (len(parts) > 20 or any(part in {"", ".", ".."} for part in parts)
            or Path(value).is_absolute()):
        raise ContractError("Test manifest path escapes its workspace.")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10))}
    if any(part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in reserved for part in parts):
        raise ContractError("Test manifest path is not a canonical portable filename.")
    folded = [part.casefold() for part in parts]
    if any(part in _DENIED_SEGMENTS or part in {".git", ".runs", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
           for part in folded):
        raise ContractError("Test manifest includes a protected/internal path.")
    filename = folded[-1]
    if filename.startswith(".env") or filename.endswith((".pem", ".key", ".p12", ".pfx")):
        raise ContractError("Test manifest includes a credential-like path.")
    # Python source is code, not a credential store. Names such as
    # provider_credentials.py and test_token_budget.py are ordinary modules;
    # the manifest operator still owns content curation and hash pinning.
    if not filename.endswith(".py") and any(term in filename for term in ("credential", "secret", "token")):
        raise ContractError("Test manifest includes a credential-like path.")
    return value


def _parse_image_ref(value: object) -> str:
    if not isinstance(value, str) or len(value) > 500 or any(ord(ch) < 33 for ch in value):
        raise ContractError("Test image must be an immutable digest reference.")
    if _IMAGE_ID.fullmatch(value):
        return value
    if "@sha256:" not in value:
        raise ContractError("Test image must be pinned by an image digest, never a tag.")
    name, digest = value.rsplit("@sha256:", 1)
    if not name or not _HEX.fullmatch(digest) or "://" in name:
        raise ContractError("Test image digest reference is invalid.")
    return value


@dataclass(frozen=True, slots=True, init=False)
class TestExecutionPolicy:
    """Immutable operator-loaded policy; agent requests contain no policy data."""

    image_ref: str
    image_id: str
    dependency_lock_sha256: str
    docker_transport: str
    test_paths: tuple[str, ...]
    test_hashes: tuple[tuple[str, str], ...]
    support_paths: tuple[str, ...]
    support_hashes: tuple[tuple[str, str], ...]
    expected_test_count: int
    snapshot_paths: tuple[str, ...]
    sha256: str
    source_path: Path
    limits_sha256: str

    def __init__(self, *args, **kwargs):  # pragma: no cover - construction guard
        raise ContractError("TestExecutionPolicy must be loaded from an operator manifest.")

    @classmethod
    def from_file(cls, path: Path) -> "TestExecutionPolicy":
        original_path = Path(path).expanduser().absolute()
        try:
            if original_path.is_symlink() or bool(getattr(original_path, "is_junction", lambda: False)()):
                raise ContractError("Test manifest must not be a link or junction.")
        except OSError as exc:
            raise ContractError("Test manifest path cannot be inspected safely.") from exc
        path = original_path.resolve(strict=True)
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ContractError("Test manifest must not be a link or junction.")
        if not path.is_file() or path.stat().st_size > 200_000:
            raise ContractError("Test manifest must be a bounded regular file.")
        def reject_duplicate_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result

        try:
            data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
        except (OSError, UnicodeError, ValueError) as exc:
            raise ContractError("Test manifest is unreadable or invalid JSON.") from exc
        required = {"version", "image_ref", "image_id", "dependency_lock_sha256", "docker_transport",
                    "test_files", "support_files", "expected_test_count", "snapshot_paths"}
        if (type(data) is not dict or set(data) != required or type(data.get("version")) is not int
                or data.get("version") != 1):
            raise ContractError("Test manifest fields do not match the versioned host schema.")
        image_ref = _parse_image_ref(data["image_ref"])
        image_id = data["image_id"]
        lock_sha = data["dependency_lock_sha256"]
        transport = data["docker_transport"]
        if transport not in {"native", "wsl-ubuntu"}:
            raise ContractError("Docker transport must be the host-selected native or fixed Ubuntu WSL adapter.")
        if not isinstance(image_id, str) or not _IMAGE_ID.fullmatch(image_id):
            raise ContractError("Test manifest image ID is invalid.")
        if _IMAGE_ID.fullmatch(image_ref) and image_ref != image_id:
            raise ContractError("Local immutable image reference must equal its pinned image ID.")
        if not isinstance(lock_sha, str) or not _HEX.fullmatch(lock_sha):
            raise ContractError("Dependency lock digest is invalid.")
        tests = data["test_files"]
        if not isinstance(tests, list) or not tests or len(tests) > 512:
            raise ContractError("Test manifest must name the complete bounded test suite.")
        test_hashes: dict[str, str] = {}
        for entry in tests:
            if type(entry) is not dict or set(entry) != {"path", "sha256"}:
                raise ContractError("Test manifest entries require exactly path and sha256.")
            relative = _canonical_path(entry["path"])
            content_sha = entry["sha256"]
            if not isinstance(content_sha, str) or not _HEX.fullmatch(content_sha):
                raise ContractError("A pinned test-file digest is invalid.")
            if relative in test_hashes:
                raise ContractError("Test manifest paths must be unique.")
            test_hashes[relative] = content_sha
        support_files = data["support_files"]
        if not isinstance(support_files, list) or len(support_files) > 512:
            raise ContractError("Test manifest support-file list is invalid or too large.")
        support_hashes: dict[str, str] = {}
        for entry in support_files:
            if type(entry) is not dict or set(entry) != {"path", "sha256"}:
                raise ContractError("Test support files require exactly path and sha256.")
            relative = _canonical_path(entry["path"])
            content_sha = entry["sha256"]
            if not isinstance(content_sha, str) or not _HEX.fullmatch(content_sha):
                raise ContractError("A pinned support-file digest is invalid.")
            if relative in test_hashes or relative in support_hashes:
                raise ContractError("Test and support-file paths must be unique.")
            support_hashes[relative] = content_sha
        expected_test_count = data["expected_test_count"]
        if type(expected_test_count) is not int or not 1 <= expected_test_count <= 10_000:
            raise ContractError("Expected pytest collection count must be an integer from 1 to 10000.")
        snapshot_paths = data["snapshot_paths"]
        if not isinstance(snapshot_paths, list) or not snapshot_paths or len(snapshot_paths) > 4096:
            raise ContractError("Test manifest requires a bounded explicit source snapshot allowlist.")
        canonical_snapshot = tuple(sorted(_canonical_path(item) for item in snapshot_paths))
        if len(set(item.casefold() for item in canonical_snapshot)) != len(canonical_snapshot):
            raise ContractError("Snapshot paths must be unique without case aliases.")
        if not (set(test_hashes) | set(support_hashes)).issubset(canonical_snapshot):
            raise ContractError("Every pinned test and support file must also be in the snapshot allowlist.")
        canonical_tests = tuple(sorted(test_hashes))
        canonical_support = tuple(sorted(support_hashes))
        digest_payload = {
            "version": 1,
            "image_ref": image_ref,
            "image_id": image_id,
            "dependency_lock_sha256": lock_sha,
            "docker_transport": transport,
            "test_files": [[name, test_hashes[name]] for name in canonical_tests],
            "support_files": [[name, support_hashes[name]] for name in canonical_support],
            "expected_test_count": expected_test_count,
            "snapshot_paths": canonical_snapshot,
            "limits": dict(_LIMITS),
        }
        limits_sha = hashlib.sha256(json.dumps(dict(_LIMITS), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        sha = hashlib.sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        instance = object.__new__(cls)
        for name, value in {
            "image_ref": image_ref,
            "image_id": image_id,
            "dependency_lock_sha256": lock_sha,
            "docker_transport": transport,
            "test_paths": canonical_tests,
            "test_hashes": tuple((name, test_hashes[name]) for name in canonical_tests),
            "support_paths": canonical_support,
            "support_hashes": tuple((name, support_hashes[name]) for name in canonical_support),
            "expected_test_count": expected_test_count,
            "snapshot_paths": canonical_snapshot,
            "sha256": sha,
            "source_path": path,
            "limits_sha256": limits_sha,
        }.items():
            object.__setattr__(instance, name, value)
        return instance

    @property
    def limits(self) -> dict[str, int]:
        return dict(_LIMITS)

    def authorize_action(self, tool: str, arguments: dict) -> None:
        if tool != "run_isolated_tests" or arguments != {}:
            raise ContractError("Test policy authorizes only its fixed full suite with empty arguments.")

    def summary(self) -> dict[str, object]:
        return {"sha256": self.sha256, "suite_files": len(self.test_paths),
                "support_files": len(self.support_paths), "expected_test_count": self.expected_test_count,
                "image_id": self.image_id, "dependency_lock_sha256": self.dependency_lock_sha256}


def _open_source_handle(workspace: Path, target: Path, relative: str) -> int:
    """Open an approved file without following raced links in any path component."""
    if os.name == "nt":
        import ctypes
        import msvcrt

        class FileTime(ctypes.Structure):
            _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

        class ByHandleInfo(ctypes.Structure):
            _fields_ = [
                ("attributes", ctypes.c_uint32), ("creation", FileTime),
                ("access", FileTime), ("write", FileTime), ("volume", ctypes.c_uint32),
                ("size_high", ctypes.c_uint32), ("size_low", ctypes.c_uint32),
                ("links", ctypes.c_uint32), ("index_high", ctypes.c_uint32),
                ("index_low", ctypes.c_uint32),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create_file.restype = ctypes.c_void_p
        get_info = kernel32.GetFileInformationByHandle
        get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(ByHandleInfo)]
        get_info.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = create_file(str(target), 0x80000000, 0x00000001, None, 3,
                             0x00200000 | 0x08000000, None)  # read-only sharing; open final reparse point
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(), "CreateFileW failed")
        try:
            info = ByHandleInfo()
            if not get_info(handle, ctypes.byref(info)):
                raise OSError(ctypes.get_last_error(), "GetFileInformationByHandle failed")
            if info.attributes & (0x10 | 0x400) or info.links != 1:
                raise ContractError("Test snapshot accepts regular files without links only.")

            get_final_path = kernel32.GetFinalPathNameByHandleW
            get_final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
            get_final_path.restype = ctypes.c_uint32
            buffer = ctypes.create_unicode_buffer(32768)
            length = get_final_path(handle, buffer, len(buffer), 0)
            if not length or length >= len(buffer):
                raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
            actual = buffer.value
            if actual.startswith("\\\\?\\UNC\\"):
                actual = "\\\\" + actual[8:]
            elif actual.startswith("\\\\?\\"):
                actual = actual[4:]
            if os.path.normcase(os.path.normpath(actual)) != os.path.normcase(os.path.normpath(str(target))):
                raise ContractError("Snapshot file resolved outside its approved canonical path.")

            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            handle = None  # ownership transferred to fd
            return fd
        finally:
            if handle is not None:
                close_handle(handle)

    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None or os.open not in getattr(os, "supports_dir_fd", set()):
        raise ContractError("This host cannot safely open the curated snapshot path.")
    flags = os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0)
    parent_fd = os.open(str(workspace), flags)
    try:
        for part in relative.split("/")[:-1]:
            next_fd = os.open(part, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        file_flags = (os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0)
                      | getattr(os, "O_NONBLOCK", 0))
        return os.open(relative.split("/")[-1], file_flags, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)


def _safe_source_bytes(workspace: Path, relative: str, max_bytes: int) -> bytes:
    safe_workspace_path(workspace, relative)
    try:
        canonical_workspace = workspace.resolve(strict=True)
        # Validate containment without erasing a pre-existing reparse point.
        # Windows must open the lexical path so its handle checks can reject it.
        target = canonical_workspace / relative
        fd = _open_source_handle(canonical_workspace, target, relative)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ContractError("Test snapshot accepts regular files without hard-link aliases only.")
            if before.st_size > max_bytes:
                raise ContractError("A manifest-listed snapshot file exceeds the per-file size cap.")
            chunks = []
            remaining = max_bytes + 1
            while remaining:
                chunk = os.read(fd, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = os.fstat(fd)
        finally:
            os.close(fd)
    except ContractError:
        raise
    except OSError as exc:
        raise ContractError("A manifest-listed snapshot file is unavailable or changed unsafely.") from exc
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                       before.st_ctime_ns, before.st_nlink)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                      after.st_ctime_ns, after.st_nlink)
    if len(data) != before.st_size or before_identity != after_identity:
        raise ContractError("Workspace changed while an isolated test snapshot was read.")
    return data


def prepare_snapshot(policy: TestExecutionPolicy, workspace: Path, temp_root: Path | None = None) -> tuple[Path, str]:
    if type(policy) is not TestExecutionPolicy:
        raise ContractError("A host-loaded TestExecutionPolicy is required.")
    workspace = Path(workspace).resolve(strict=True)
    staging_root = Path(temp_root or tempfile.gettempdir()).resolve(strict=True)
    if not workspace.is_dir() or not staging_root.is_dir():
        raise ContractError("Workspace and staging root must be existing directories.")
    if staging_root == workspace or workspace in staging_root.parents:
        raise ContractError("Snapshot staging must be outside the live workspace.")
    snapshot = Path(tempfile.mkdtemp(prefix="agentkit-tests-", dir=staging_root))
    snapshot_hashes: list[tuple[str, str]] = []
    total_bytes = 0
    expected_tests = {**dict(policy.test_hashes), **dict(policy.support_hashes)}
    try:
        for relative in policy.snapshot_paths:
            data = _safe_source_bytes(workspace, relative, _LIMITS["max_file_bytes"])
            total_bytes += len(data)
            if total_bytes > _LIMITS["max_snapshot_bytes"]:
                raise ContractError("Curated test snapshot exceeds the total byte cap.")
            content_sha = hashlib.sha256(data).hexdigest()
            if relative in expected_tests and content_sha != expected_tests[relative]:
                raise ContractError("Pinned test/support content changed; isolated tests refused.")
            destination = snapshot.joinpath(*relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if hashlib.sha256(destination.read_bytes()).hexdigest() != content_sha:
                raise ContractError("Staged snapshot bytes failed their content check.")
            snapshot_hashes.append((relative, content_sha))
        digest_bytes = json.dumps(snapshot_hashes, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return snapshot, hashlib.sha256(digest_bytes).hexdigest()
    except BaseException:
        shutil.rmtree(snapshot, ignore_errors=True)
        raise


def _valid_image_inspect(output: str, policy: TestExecutionPolicy) -> bool:
    try:
        image = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(image, dict):
        return False
    config = image.get("Config") if isinstance(image, dict) else None
    labels = config.get("Labels") if isinstance(config, dict) else None
    return (image.get("Id") == policy.image_id and isinstance(labels, dict)
            and labels.get(_LOCK_LABEL) == policy.dependency_lock_sha256)


def _valid_container_inspect(output: str, policy: TestExecutionPolicy, snapshot: Path,
                             expected_source: str | None = None,
                             timeout_seconds: int = _LIMITS["timeout_seconds"]) -> bool:
    try:
        value = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(value, dict):
        return False
    config = value.get("Config") or {}
    host = value.get("HostConfig") or {}
    mounts = value.get("Mounts") or []
    expected_tmpfs = "rw,noexec,nosuid,nodev,size=16m,mode=1777"
    expected_mount = (expected_source or str(snapshot.resolve())).replace("\\", "/")
    ulimits = host.get("Ulimits") or []
    nofile_ok = any(item.get("Name") == "nofile" and item.get("Soft") == 64 and item.get("Hard") == 64
                    for item in ulimits if isinstance(item, dict))
    mount_ok = (len(mounts) == 1 and isinstance(mounts[0], dict)
                and mounts[0].get("Destination") == "/workspace"
                and mounts[0].get("RW") is False and mounts[0].get("Type") == "bind"
                and str(mounts[0].get("Source", "")).replace("\\", "/").casefold() == expected_mount.casefold())
    expected_command = ["--signal=TERM", "--kill-after=2", str(timeout_seconds), "/usr/local/bin/python",
                        "-I", "-B", "-c",
                        "import sys; sys.path[:0] = ['/workspace', '/workspace/src']; import pytest; raise SystemExit(pytest.main(['-q', '-c', '/dev/null', '-p', 'no:cacheprovider', '--', *sys.argv[1:]]))",
                        *policy.test_paths]
    environment = config.get("Env") or []
    expected_environment = {
        "PYTEST_ADDOPTS": "", "PYTEST_PLUGINS": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    env_ok = isinstance(environment, list) and all(
        sum(1 for item in environment if isinstance(item, str) and item.partition("=")[0] == key) == 1
        and f"{key}={expected}" in environment
        for key, expected in expected_environment.items()
    )
    return (
        value.get("Image") == policy.image_id
        and config.get("Image") == policy.image_ref
        and config.get("User") == "65534:65534"
        and config.get("Entrypoint") == ["/usr/bin/timeout"]
        and config.get("Cmd") == expected_command
        and config.get("WorkingDir") == "/workspace"
        and env_ok
        and host.get("NetworkMode") == "none"
        and host.get("ReadonlyRootfs") is True
        and host.get("Privileged") is False
        and host.get("CapDrop") == ["ALL"]
        and host.get("CapAdd") in (None, [])
        and host.get("SecurityOpt") in (["no-new-privileges"], ["no-new-privileges:true"])
        and host.get("Memory") == _LIMITS["memory_bytes"]
        and host.get("MemorySwap") == _LIMITS["memory_swap_bytes"]
        and host.get("NanoCpus") == _LIMITS["nano_cpus"]
        and host.get("PidsLimit") == _LIMITS["pids"]
        # This is the pinned container tmpfs mount, not a host /tmp write.
        and host.get("Tmpfs") == {"/tmp": expected_tmpfs}  # nosec B108
        and host.get("Binds") in (None, []) and nofile_ok and mount_ok
    )


def _docker_args(policy: TestExecutionPolicy, snapshot: Path, container_name: str,
                 timeout_seconds: int) -> list[str]:
    snapshot_path = str(snapshot.resolve()).replace("\\", "/")
    args = [
        "docker", "create", "--pull=never", "--name", container_name,
        "--label", "org.agentkit.run-tests=true",
        "--network=none", "--read-only", "--user=65534:65534", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--memory=128m", "--memory-swap=128m",
        "--cpus=1", "--pids-limit=32", "--ulimit=nofile=64:64",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
        "--mount", f"type=bind,source={snapshot_path},target=/workspace,readonly",
        "--env=PYTEST_ADDOPTS=", "--env=PYTEST_PLUGINS=", "--env=PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "--workdir=/workspace", "--entrypoint=/usr/bin/timeout", policy.image_ref,
        "--signal=TERM", "--kill-after=2", str(timeout_seconds), "/usr/local/bin/python",
        "-I", "-B", "-c",
        "import sys; sys.path[:0] = ['/workspace', '/workspace/src']; import pytest; raise SystemExit(pytest.main(['-q', '-c', '/dev/null', '-p', 'no:cacheprovider', '--', *sys.argv[1:]]))",
        *policy.test_paths,
    ]
    return args


def _pytest_outcomes(output: str) -> dict[str, int]:
    outcomes = {key: 0 for key in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed", "deselected")}
    for match in _PYTEST_COUNT_RE.finditer(output):
        key = match.group("kind")
        if key == "error":
            key = "errors"
        outcomes[key] += int(match.group("count"))
    return outcomes


def _host_docker_runner(policy: TestExecutionPolicy, config_dir: Path, base_runner: Callable) -> Callable:
    """Wrap fixed Docker argv with a credential-clean host transport."""
    clean_env = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR"}
    }
    clean_env["DOCKER_CONFIG"] = str(config_dir)
    if policy.docker_transport == "native":
        executable = shutil.which("docker", path=clean_env.get("PATH"))
        if not executable:
            raise ContractError("Docker CLI is unavailable; host pytest fallback is disabled.")

        def native(args, prompt, cwd, timeout):
            return base_runner([executable, *args[1:]], prompt, cwd, timeout, env=clean_env)
        return native

    wsl = shutil.which("wsl.exe", path=clean_env.get("PATH")) or shutil.which("wsl", path=clean_env.get("PATH"))
    if not wsl:
        raise ContractError("Fixed Ubuntu WSL Docker transport is unavailable; host pytest fallback is disabled.")
    linux_env = ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/tmp/agentkit-test-home"]
    wsl_env = dict(clean_env)

    def map_host_path(host_path: str, cwd: Path, timeout: float) -> str:
        path_args = [wsl, "--distribution", "Ubuntu", "--exec", "/usr/bin/env", "-i",
                     *linux_env, "wslpath", "-a", host_path]
        code, linux_path, _ = base_runner(path_args, "", cwd, timeout, env=wsl_env)
        linux_path = linux_path.strip()
        if code or not linux_path.startswith("/mnt/") or any(ch in linux_path for ch in ("\n", ",")):
            raise ContractError("Host staging path could not be mapped to the fixed WSL Docker host.")
        return linux_path

    def invoke_linux(tool_args: list[str], cwd: Path, timeout: float):
        command = [wsl, "--distribution", "Ubuntu", "--exec", "/usr/bin/env", "-i",
                   *linux_env, tool_args[0], *tool_args[1:]]
        return base_runner(command, "", cwd, timeout, env=wsl_env)

    mapped_snapshot_source: str | None = None
    mapped_config_dir: str | None = None

    def wsl_runner(args, prompt, cwd, timeout):
        nonlocal mapped_snapshot_source, mapped_config_dir
        if mapped_config_dir is None:
            mapped_config_dir = map_host_path(str(config_dir.resolve()), cwd, timeout)
        mapped_args = list(args[1:])
        if args[1] == "create" and "--mount" in mapped_args:
            index = mapped_args.index("--mount") + 1
            mount = mapped_args[index]
            marker = "source="
            source_start = mount.index(marker) + len(marker)
            source_end = mount.index(",target=", source_start)
            host_path = mount[source_start:source_end]
            if "," in host_path:
                raise ContractError("Staging path cannot be represented safely in a Docker mount.")
            linux_path = map_host_path(host_path, cwd, timeout)
            mapped_args[index] = mount[:source_start] + linux_path + mount[source_end:]
            mapped_snapshot_source = linux_path
            wsl_runner.snapshot_mount_path = linux_path
        docker_args = ["/usr/bin/docker", "--config", mapped_config_dir, *mapped_args]
        return invoke_linux(docker_args, cwd, timeout)
    return wsl_runner


def run_isolated_tests(
    policy: TestExecutionPolicy,
    workspace: Path,
    *,
    run_id: str,
    timeout: float,
    runner: Callable | None = None,
    temp_root: Path | None = None,
) -> dict:
    """Run the entire operator-pinned suite; result is host-generated evidence."""
    if type(policy) is not TestExecutionPolicy or not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ContractError("Isolated test policy or run identity is invalid.")
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
        raise ContractError("Isolated test deadline is invalid.")
    timeout = min(float(timeout), float(_LIMITS["timeout_seconds"]))
    injected_runner = runner is not None
    base_runner = runner
    if base_runner is None:
        from .backends import _process_result
        base_runner = _process_result
    workspace = Path(workspace).resolve(strict=True)
    start = time.monotonic()
    name = f"agentkit-tests-{run_id}-{uuid.uuid4().hex}"
    container_created = False
    cleanup_ok = False
    snapshot_sha = ""
    output = ""
    test_outcomes = {key: 0 for key in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed", "deselected")}
    error_code = "runner_error"
    exit_code: int | None = None
    snapshot: Path | None = None
    before_fingerprint = workspace_fingerprint(workspace)

    def remaining() -> float:
        return max(0.01, timeout - (time.monotonic() - start))

    try:
        with tempfile.TemporaryDirectory(prefix="agentkit-test-stage-", dir=temp_root) as stage_parent:
            config_dir = Path(stage_parent) / "docker-config"
            config_dir.mkdir()
            (config_dir / "config.json").write_text('{"auths":{}}', encoding="utf-8")
            snapshot, snapshot_sha = prepare_snapshot(policy, workspace, Path(stage_parent))
            runner = (base_runner if injected_runner
                      else _host_docker_runner(policy, config_dir, base_runner))

            code, image_json, _ = runner(["docker", "image", "inspect", "--format", "{{json .}}", policy.image_ref],
                                         "", workspace, remaining())
            if code or not _valid_image_inspect(image_json, policy):
                error_code = "pinned_image_unavailable_or_mismatch"
            else:
                test_timeout_seconds = max(1, min(_LIMITS["timeout_seconds"], int(remaining())))
                command = _docker_args(policy, snapshot, name, test_timeout_seconds)
                # Mark before the call: timeout/transport loss may happen after
                # Docker created the named container but before its ID arrived.
                container_created = True
                code, container_id, _ = runner(command, "", workspace, remaining())
                container_id = container_id.strip()
                if code or not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
                    error_code = "container_create_failed_or_unknown"
                else:
                    inspect_args = ["docker", "inspect", "--format", "{{json .}}", container_id]
                    code, container_json, _ = runner(inspect_args, "", workspace, remaining())
                    expected_source = getattr(runner, "snapshot_mount_path", None)
                    if code or not _valid_container_inspect(
                            container_json, policy, snapshot, expected_source, test_timeout_seconds):
                        error_code = "container_configuration_mismatch"
                    else:
                        try:
                            exit_code, stdout, stderr = runner(["docker", "start", "--attach", container_id],
                                                              "", workspace, remaining())
                            full_output = stdout + "\n" + stderr
                            test_outcomes = _pytest_outcomes(full_output)
                            output = full_output[-12_000:]
                            error_code = "tests_failed" if exit_code else ""
                            outcome_total = sum(test_outcomes.values())
                            if not error_code and outcome_total != policy.expected_test_count:
                                error_code = "pytest_outcome_count_mismatch"
                            if not error_code and (test_outcomes["passed"] < 1
                                    or test_outcomes["failed"] or test_outcomes["errors"]
                                    or test_outcomes["xpassed"] or test_outcomes["deselected"]):
                                error_code = "pytest_outcome_summary_rejected"
                        except subprocess.TimeoutExpired:
                            error_code = "timeout"
                        except ContractError as exc:
                            if "output" in str(exc).casefold():
                                error_code = "output_limit_exceeded"
                            else:
                                error_code = "runner_error"
            # The live workspace must not change while its snapshot is being verified.
            if workspace_fingerprint(workspace) != before_fingerprint:
                error_code = "workspace_changed_during_test"
                exit_code = None
            if container_created:
                try:
                    cleanup_code, _, _ = runner(["docker", "rm", "--force", name], "", workspace, 5.0)
                    cleanup_ok = cleanup_code == 0
                except Exception:
                    cleanup_ok = False
                if not cleanup_ok:
                    error_code = "container_cleanup_failed"
                    exit_code = None
            if not error_code and exit_code == 0 and cleanup_ok:
                status = "passed"
            elif error_code == "timeout":
                status = "timeout"
            else:
                status = "failed"
            return {
                "status": status,
                "run_id": run_id,
                "reason": error_code or "ok",
                "exit_code": exit_code,
                "policy_sha256": policy.sha256,
                "test_manifest_sha256": policy.sha256,
                "test_paths": list(policy.test_paths),
                "expected_test_count": policy.expected_test_count,
                "test_outcomes": test_outcomes,
                "image_ref": policy.image_ref,
                "image_id": policy.image_id,
                "dependency_lock_sha256": policy.dependency_lock_sha256,
                "snapshot_sha256": snapshot_sha,
                "workspace_fingerprint": before_fingerprint,
                "duration_seconds": round(time.monotonic() - start, 3),
                "output": output[:12_000],
                "cleanup_confirmed": cleanup_ok,
            }
    except subprocess.TimeoutExpired:
        error_code = "timeout"
    except Exception as exc:
        # Do not persist raw subprocess/environment diagnostics into run history.
        error_code = "test_snapshot_or_runner_error"
        output = type(exc).__name__
    finally:
        if container_created and not cleanup_ok:
            try:
                cleanup_code, _, _ = runner(["docker", "rm", "--force", name], "", workspace, 5.0)
                cleanup_ok = cleanup_code == 0
            except Exception:
                cleanup_ok = False
    return {
        "status": "timeout" if error_code == "timeout" else "failed",
        "run_id": run_id,
        "reason": error_code,
        "exit_code": exit_code,
        "policy_sha256": policy.sha256,
        "test_manifest_sha256": policy.sha256,
        "test_paths": list(policy.test_paths),
        "expected_test_count": policy.expected_test_count,
        "test_outcomes": test_outcomes,
        "image_ref": policy.image_ref,
        "image_id": policy.image_id,
        "dependency_lock_sha256": policy.dependency_lock_sha256,
        "snapshot_sha256": snapshot_sha,
        "workspace_fingerprint": before_fingerprint,
        "duration_seconds": round(time.monotonic() - start, 3),
        "output": output[:12_000],
        "cleanup_confirmed": cleanup_ok,
    }


def validate_test_receipt(value: object, policy: TestExecutionPolicy, run_id: str) -> dict:
    """Validate the exact host-runner receipt before the engine checkpoints it."""
    required = {
        "status", "run_id", "reason", "exit_code", "policy_sha256", "test_manifest_sha256",
        "test_paths", "image_ref", "image_id", "dependency_lock_sha256", "snapshot_sha256",
        "expected_test_count", "test_outcomes",
        "workspace_fingerprint", "duration_seconds", "output", "cleanup_confirmed",
    }
    if type(value) is not dict or set(value) != required:
        raise ContractError("Host test receipt has an invalid schema.")
    if (value["run_id"] != run_id or value["status"] not in {"passed", "failed", "timeout"}
            or value["policy_sha256"] != policy.sha256
            or value["test_manifest_sha256"] != policy.sha256
            or value["test_paths"] != list(policy.test_paths)
            or value["expected_test_count"] != policy.expected_test_count
            or value["image_ref"] != policy.image_ref or value["image_id"] != policy.image_id
            or value["dependency_lock_sha256"] != policy.dependency_lock_sha256):
        raise ContractError("Host test receipt does not match this run's pinned test policy.")
    for name in ("workspace_fingerprint",):
        if not isinstance(value[name], str) or not _HEX.fullmatch(value[name]):
            raise ContractError("Host test receipt has an invalid workspace binding.")
    snapshot_sha = value["snapshot_sha256"]
    if snapshot_sha and (not isinstance(snapshot_sha, str) or not _HEX.fullmatch(snapshot_sha)):
        raise ContractError("Host test receipt has an invalid source snapshot digest.")
    if value["status"] == "passed" and (not snapshot_sha or value["exit_code"] != 0 or value["cleanup_confirmed"] is not True):
        raise ContractError("Passing host test receipt is incomplete.")
    outcomes = value["test_outcomes"]
    outcome_keys = {"passed", "failed", "errors", "skipped", "xfailed", "xpassed", "deselected"}
    if (type(outcomes) is not dict or set(outcomes) != outcome_keys
            or any(type(count) is not int or not 0 <= count <= 10_000 for count in outcomes.values())):
        raise ContractError("Host test receipt has invalid pytest summary counts.")
    if value["status"] == "passed" and (
            sum(outcomes.values()) != policy.expected_test_count or outcomes["passed"] < 1
            or outcomes["failed"] or outcomes["errors"] or outcomes["xpassed"] or outcomes["deselected"]):
        raise ContractError("Passing host test receipt lacks the required complete pytest summary.")
    if value["exit_code"] is not None and (type(value["exit_code"]) is not int or abs(value["exit_code"]) > 255):
        raise ContractError("Host test receipt exit code is invalid.")
    if (not isinstance(value["reason"], str) or len(value["reason"]) > 100
            or not re.fullmatch(r"[a-z0-9_]+", value["reason"])):
        raise ContractError("Host test receipt reason is invalid.")
    duration = value["duration_seconds"]
    if type(duration) not in {int, float} or not math.isfinite(duration) or duration < 0 or duration > 240:
        raise ContractError("Host test receipt duration is invalid.")
    if not isinstance(value["output"], str) or len(value["output"]) > 12_000:
        raise ContractError("Host test receipt output is not bounded text.")
    if type(value["cleanup_confirmed"]) is not bool:
        raise ContractError("Host test receipt cleanup state is invalid.")
    return dict(value)
