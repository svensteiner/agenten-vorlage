"""Strict host-owned policy for separately authorized local test phases.

This module defines policy and freshness checks only. It does not execute tests
or change the existing Docker-backed ``TestExecutionPolicy`` contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .approvals import _canonical_windows_path
from .contracts import ContractError
from .test_execution import _canonical_path, _safe_source_bytes, _parse_image_ref


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_MANIFEST_BYTES = 200_000
_MAX_PATHS = 4096
_MAX_PHASE_NODEIDS = 10_000
_MAX_TOTAL_NODEIDS = 20_000
# Source-text parametrization can include the complete 8,192-character input.
# Selection remains operator-owned and bounded by the total manifest size.
_MAX_NODEID_CHARS = 16_384
_HARD_LIMITS = MappingProxyType({
    "timeout_seconds": 720,
    "memory_bytes": 2 * 1024**3,
    "memory_swap_bytes": 2 * 1024**3,
    "nano_cpus": 2_000_000_000,
    "pids": 256,
    "output_bytes": 2_000_000,
    "nofile": 1024,
    "tmpfs_bytes": 256 * 1024**2,
    "max_file_bytes": 8 * 1024**2,
    "max_snapshot_bytes": 512 * 1024**2,
})
_LIMIT_FIELDS = frozenset(_HARD_LIMITS)
_PHASES = ("red", "targeted", "full")
_MANIFEST_FIELDS = frozenset({
    "version", "image_ref", "image_id", "dependency_lock_sha256",
    "host_runner_sha256", "production_files", "snapshot_paths",
    "allowed_write_paths", "phases", "full_test_roots",
    "full_minimum_test_count", "limits",
})


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def _manifest_path(path: Path, workspace: Path) -> Path:
    original = Path(path).expanduser().absolute()
    root = Path(workspace).expanduser().absolute()
    try:
        for candidate in (original, *reversed(original.parents)):
            if candidate.exists() and _is_link(candidate):
                raise ContractError("Phase policy manifest path must not traverse links or junctions.")
        resolved_root = root.resolve(strict=True)
        resolved = original.resolve(strict=True)
        if resolved.is_relative_to(resolved_root):
            raise ContractError("Phase policy manifest must be outside the workspace.")
        metadata = resolved.stat()
    except ContractError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ContractError("Phase policy manifest or workspace cannot be inspected safely.") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_MANIFEST_BYTES:
        raise ContractError("Phase policy manifest must be a bounded regular file.")
    if metadata.st_nlink != 1:
        raise ContractError("Phase policy manifest must not have hard-link aliases.")
    return resolved


def _is_link(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        checker = getattr(path, "is_junction", None)
        return bool(checker()) if checker is not None else False
    except OSError as exc:
        raise ContractError("Phase policy path cannot be inspected safely.") from exc


def _canonical_workspace(path: Path) -> Path:
    original = Path(path).expanduser().absolute()
    try:
        for candidate in (original, *reversed(original.parents)):
            if candidate.exists() and _is_link(candidate):
                raise ContractError("Phase policy workspace must not traverse links or junctions.")
        resolved = original.resolve(strict=True)
        if not resolved.is_dir():
            raise ContractError("Phase policy workspace must be an existing directory.")
        canonical = _canonical_windows_path(resolved)
    except ContractError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ContractError("Phase policy workspace cannot be inspected safely.") from exc
    return canonical


def _digest(value: object, label: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ContractError(f"{label} must be a lowercase SHA-256 digest.")
    return value


def _path_list(value: object, label: str, *, required: bool) -> tuple[str, ...]:
    if type(value) is not list or (required and not value) or len(value) > _MAX_PATHS:
        raise ContractError(f"{label} must be a bounded explicit path list.")
    paths = tuple(_canonical_path(item) for item in value)
    folded = [item.casefold() for item in paths]
    if len(set(folded)) != len(paths):
        raise ContractError(f"{label} must not contain duplicate or case-alias paths.")
    return tuple(sorted(paths))


def _nodeids(value: object, snapshot_paths: set[str], phase: str) -> tuple[str, ...]:
    if type(value) is not list or not value or len(value) > _MAX_PHASE_NODEIDS:
        raise ContractError(f"The {phase} phase requires a bounded nonempty nodeid list.")
    result: list[str] = []
    for nodeid in value:
        if (type(nodeid) is not str or not nodeid or len(nodeid) > _MAX_NODEID_CHARS
                or any(ord(char) < 32 or ord(char) == 127 for char in nodeid)):
            raise ContractError(f"The {phase} phase contains an invalid test nodeid.")
        parts = nodeid.split("::")
        if len(parts) < 2 or any(not part for part in parts):
            raise ContractError(f"The {phase} phase nodeid must bind a test file and test name.")
        test_path = _canonical_path(parts[0])
        if test_path not in snapshot_paths:
            raise ContractError(f"The {phase} phase nodeid is outside the snapshot manifest.")
        if not test_path.startswith("tests/"):
            raise ContractError("Phase nodeids must select tests under tests/.")
        result.append(nodeid)
    if len(set(result)) != len(result):
        raise ContractError(f"The {phase} phase nodeid list contains duplicates.")
    return tuple(sorted(result))


def _is_test_file(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _under_root(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _validate_test_roots(value: object) -> tuple[str, ...]:
    roots = _path_list(value, "Full test roots", required=True)
    if any(root != "tests" and not root.startswith("tests/") for root in roots):
        raise ContractError("Full test roots must be under tests/.")
    folded_roots = tuple(root.casefold() for root in roots)
    for index, root in enumerate(folded_roots):
        if any(
            _under_root(other, root) or _under_root(root, other)
            for other_index, other in enumerate(folded_roots)
            if other_index != index
        ):
            raise ContractError("Full test roots must not overlap.")
    return roots


def _full_scope_files(paths: tuple[str, ...], roots: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(
        path for path in paths
        if _is_test_file(path) and any(_under_root(path, root) for root in roots)
    ))


def _workspace_test_inventory(workspace: Path, roots: tuple[str, ...]) -> tuple[str, ...]:
    found: set[str] = set()
    for relative_root in roots:
        current = workspace
        for part in relative_root.split("/"):
            current = current / part
            if _is_link(current):
                raise ContractError("Full test roots cannot traverse links or junctions.")
        if not current.is_dir():
            raise ContractError("A declared full test root is missing or not a directory.")

        def fail_walk(error: OSError) -> None:
            raise ContractError("Full test-file inventory cannot be inspected safely.") from error

        for directory, names, files in os.walk(current, topdown=True, followlinks=False, onerror=fail_walk):
            directory_path = Path(directory)
            kept_names: list[str] = []
            for name in names:
                child = directory_path / name
                if _is_link(child):
                    raise ContractError("Full test roots cannot contain linked directories.")
                kept_names.append(name)
            names[:] = sorted(kept_names)
            for name in files:
                child = directory_path / name
                if _is_link(child):
                    raise ContractError("Full test roots cannot contain linked files.")
                try:
                    mode = child.stat(follow_symlinks=False).st_mode
                except OSError as exc:
                    raise ContractError("Full test-file inventory cannot be inspected safely.") from exc
                if not stat.S_ISREG(mode):
                    raise ContractError("Full test roots may contain regular files only.")
                if _is_test_file((child.relative_to(workspace)).as_posix()):
                    found.add((child.relative_to(workspace)).as_posix())
                    if len(found) > _MAX_PATHS:
                        raise ContractError("Full test-file inventory exceeds its host limit.")
    return tuple(sorted(found))


@dataclass(frozen=True, slots=True)
class PhasePlan:
    """An immutable selection resolved solely from the host policy."""

    phase: str
    nodeids: tuple[str, ...]
    test_files: tuple[str, ...]
    expected_failure_nodeids: tuple[str, ...]
    minimum_test_count: int | None
    policy_sha256: str


@dataclass(frozen=True, slots=True, init=False)
class LocalPhaseTestPolicy:
    """Immutable operator-loaded manifest for bounded red/targeted/full phases."""

    image_ref: str
    image_id: str
    dependency_lock_sha256: str
    host_runner_sha256: str
    production_hashes: tuple[tuple[str, str], ...]
    snapshot_paths: tuple[str, ...]
    allowed_write_paths: tuple[str, ...]
    phase_nodeids: tuple[tuple[str, tuple[str, ...]], ...]
    expected_red_nodeids: tuple[str, ...]
    full_minimum_test_count: int
    full_test_roots: tuple[str, ...]
    full_test_files: tuple[str, ...]
    sha256: str
    source_path: Path
    workspace_path: Path
    _limits: tuple[tuple[str, int], ...]

    def __init__(self, *args, **kwargs):  # pragma: no cover - construction guard
        raise ContractError("LocalPhaseTestPolicy must be loaded from an operator manifest.")

    @classmethod
    def from_file(cls, path: Path, workspace: Path) -> "LocalPhaseTestPolicy":
        source_path = _manifest_path(path, workspace)
        workspace_path = _canonical_workspace(workspace)
        try:
            raw = source_path.read_bytes()
            if len(raw) > _MAX_MANIFEST_BYTES:
                raise ContractError("Phase policy manifest exceeds its byte limit.")
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        except ContractError:
            raise
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            raise ContractError("Phase policy manifest is unreadable or invalid JSON.") from exc
        if (type(data) is not dict or set(data) != _MANIFEST_FIELDS
                or type(data.get("version")) is not int or data["version"] != 1):
            raise ContractError("Phase policy fields do not match the versioned host schema.")

        image_ref = _parse_image_ref(data["image_ref"])
        image_id = data["image_id"]
        if type(image_id) is not str or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ContractError("Phase policy image ID must be an immutable sha256 ID.")
        if image_ref.startswith("sha256:") and image_ref != image_id:
            raise ContractError("Local phase image reference must match the pinned image ID.")
        dependency_lock_sha256 = _digest(data["dependency_lock_sha256"], "Dependency lock digest")
        host_runner_sha256 = _digest(data["host_runner_sha256"], "Host runner digest")

        snapshot_paths = _path_list(data["snapshot_paths"], "Snapshot paths", required=True)
        allowed_write_paths = _path_list(data["allowed_write_paths"], "Allowed write paths", required=True)
        if not set(allowed_write_paths).issubset(snapshot_paths):
            raise ContractError("Every allowed write path must be in the snapshot manifest.")
        production_files = data["production_files"]
        if type(production_files) is not list or not production_files or len(production_files) > _MAX_PATHS:
            raise ContractError("Production baseline files must be a bounded nonempty list.")
        production: dict[str, str] = {}
        for entry in production_files:
            if type(entry) is not dict or set(entry) != {"path", "sha256"}:
                raise ContractError("Production baseline entries require exactly path and sha256.")
            relative = _canonical_path(entry["path"])
            digest = _digest(entry["sha256"], "Production baseline hash")
            if relative not in snapshot_paths or relative in production:
                raise ContractError("Production baseline files must be unique snapshot paths.")
            production[relative] = digest

        if any(not path.startswith("tests/") and path not in production for path in allowed_write_paths):
            raise ContractError("Every permitted production write requires a pinned RED baseline hash.")

        phases = data["phases"]
        if type(phases) is not dict or set(phases) != set(_PHASES):
            raise ContractError("Phase map must contain exactly red, targeted and full.")
        parsed_phases: dict[str, tuple[str, ...]] = {}
        full_test_files: tuple[str, ...] = ()
        expected_red: tuple[str, ...] = ()
        total_nodeids = 0
        for phase in _PHASES:
            phase_value = phases[phase]
            required = (
                {"nodeids", "expected_failure_nodeids"} if phase == "red" else
                {"test_files"} if phase == "full" else {"nodeids"}
            )
            if type(phase_value) is not dict or set(phase_value) != required:
                raise ContractError(f"The {phase} phase has invalid fields.")
            if phase == "full":
                full_test_files = _path_list(
                    phase_value["test_files"], "Full-phase test files", required=True
                )
                if not set(full_test_files).issubset(snapshot_paths):
                    raise ContractError("Full-phase files must be test paths in the snapshot manifest.")
                continue
            nodeids = _nodeids(phase_value["nodeids"], set(snapshot_paths), phase)
            total_nodeids += len(nodeids)
            parsed_phases[phase] = nodeids
            if phase == "red":
                expected_red = _nodeids(
                    phase_value["expected_failure_nodeids"], set(snapshot_paths), phase
                )
                if not set(expected_red).issubset(nodeids):
                    raise ContractError("Expected RED assertion nodeids must be selected by the RED phase.")
        if total_nodeids > _MAX_TOTAL_NODEIDS:
            raise ContractError("Phase nodeid lists exceed the total policy limit.")
        minimum_count = data["full_minimum_test_count"]
        if type(minimum_count) is not int or not 1 <= minimum_count <= 100_000:
            raise ContractError("Full-phase minimum test count is outside the permitted range.")

        full_test_roots = _validate_test_roots(data["full_test_roots"])
        expected_full_files = _full_scope_files(snapshot_paths, full_test_roots)
        if not expected_full_files or full_test_files != expected_full_files:
            raise ContractError("Full-phase files must exactly inventory test files beneath the declared roots.")

        limits = _validate_limits(data["limits"])
        digest_payload = {
            "version": 1,
            "workspace": str(workspace_path),
            "image_ref": image_ref,
            "image_id": image_id,
            "dependency_lock_sha256": dependency_lock_sha256,
            "host_runner_sha256": host_runner_sha256,
            "production_files": [[key, production[key]] for key in sorted(production)],
            "snapshot_paths": snapshot_paths,
            "allowed_write_paths": allowed_write_paths,
            "phases": {phase: {
                **({"test_files": full_test_files} if phase == "full" else {
                    "nodeids": parsed_phases[phase],
                    **({"expected_failure_nodeids": expected_red} if phase == "red" else {}),
                }),
            } for phase in _PHASES},
            "full_minimum_test_count": minimum_count,
            "full_test_roots": full_test_roots,
            "limits": limits,
        }
        sha = hashlib.sha256(_canonical_json(digest_payload)).hexdigest()
        instance = object.__new__(cls)
        values = {
            "image_ref": image_ref,
            "image_id": image_id,
            "dependency_lock_sha256": dependency_lock_sha256,
            "host_runner_sha256": host_runner_sha256,
            "production_hashes": tuple((key, production[key]) for key in sorted(production)),
            "snapshot_paths": snapshot_paths,
            "allowed_write_paths": allowed_write_paths,
            "phase_nodeids": tuple((phase, parsed_phases.get(phase, ())) for phase in _PHASES),
            "full_test_files": full_test_files,
            "expected_red_nodeids": expected_red,
            "full_minimum_test_count": minimum_count,
            "full_test_roots": full_test_roots,
            "sha256": sha,
            "source_path": source_path,
            "workspace_path": workspace_path,
            "_limits": tuple(sorted(limits.items())),
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance

    @property
    def limits(self) -> dict[str, int]:
        return dict(self._limits)

    def authorize_write(self, relative: object) -> str:
        canonical = _canonical_path(relative)
        if canonical not in self.allowed_write_paths:
            raise ContractError("Write path is outside the phase policy's exact host allowlist.")
        return canonical


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("Phase policy is not canonical JSON.") from exc


def _validate_limits(value: object) -> dict[str, int]:
    if type(value) is not dict or set(value) != _LIMIT_FIELDS:
        raise ContractError("Phase policy must declare every separate bounded resource limit.")
    limits: dict[str, int] = {}
    for name, maximum in _HARD_LIMITS.items():
        number = value[name]
        if type(number) is not int or not 1 <= number <= maximum:
            raise ContractError(f"Phase policy {name} exceeds its host hard bound.")
        limits[name] = number
    if limits["memory_swap_bytes"] < limits["memory_bytes"]:
        raise ContractError("Memory-swap limit cannot be lower than the memory limit.")
    if limits["max_snapshot_bytes"] < limits["max_file_bytes"]:
        raise ContractError("Total snapshot limit cannot be lower than the per-file limit.")
    return limits


def authorize_phase(policy: LocalPhaseTestPolicy, phase: object, **kwargs: object) -> PhasePlan:
    """Resolve only a fixed host phase; never accept caller-selected test argv."""
    if type(policy) is not LocalPhaseTestPolicy:
        raise ContractError("A loaded LocalPhaseTestPolicy is required.")
    if type(phase) is not str or phase not in _PHASES or kwargs:
        raise ContractError("Only the fixed red, targeted and full phases are authorized.")
    nodeids = dict(policy.phase_nodeids)[phase]
    return PhasePlan(
        phase=phase,
        nodeids=nodeids,
        test_files=policy.full_test_files if phase == "full" else (),
        expected_failure_nodeids=policy.expected_red_nodeids if phase == "red" else (),
        minimum_test_count=policy.full_minimum_test_count if phase == "full" else None,
        policy_sha256=policy.sha256,
    )


def verify_phase_freshness(
    policy: LocalPhaseTestPolicy, workspace: Path, phase: object
) -> dict[str, object]:
    """Check workspace identity and snapshot inputs; RED also enforces source baseline hashes.

    Regression tests are intentionally mutable so a RED test can be introduced.
    The production-file baseline is an operator-owned precondition for RED only.
    """
    plan = authorize_phase(policy, phase)
    canonical = _canonical_workspace(workspace)
    if canonical != policy.workspace_path:
        raise ContractError("Phase policy is bound to a different workspace.")
    limits = policy.limits
    hashes: dict[str, str] = {}
    total = 0
    for relative in policy.snapshot_paths:
        content = _safe_source_bytes(canonical, relative, limits["max_file_bytes"])
        total += len(content)
        if total > limits["max_snapshot_bytes"]:
            raise ContractError("Phase snapshot exceeds its configured total byte limit.")
        hashes[relative] = hashlib.sha256(content).hexdigest()
    if plan.phase == "red":
        for relative, expected in policy.production_hashes:
            if hashes.get(relative) != expected:
                raise ContractError("Production baseline changed before the RED precondition.")
    if plan.phase == "full":
        actual_test_files = _workspace_test_inventory(canonical, policy.full_test_roots)
        if actual_test_files != policy.full_test_files:
            raise ContractError("Live full test-file inventory differs from the operator-pinned scope.")
    snapshot_sha256 = hashlib.sha256(_canonical_json([
        [relative, hashes[relative]] for relative in sorted(hashes)
    ])).hexdigest()
    return {
        "phase": plan.phase,
        "policy_sha256": policy.sha256,
        "snapshot_paths": policy.snapshot_paths,
        "full_test_roots": policy.full_test_roots if plan.phase == "full" else (),
        "full_test_files": policy.full_test_files if plan.phase == "full" else (),
        "snapshot_sha256": snapshot_sha256,
        "input_hashes": hashes,
        "production_hashes": {
            path: digest for path, digest in policy.production_hashes
        },
    }
