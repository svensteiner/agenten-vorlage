"""Private, run-bound storage for original production bytes used by phase recovery."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

from .approvals import _canonical_windows_path
from .contracts import ContractError
from .phase_test_execution import LocalPhaseTestPolicy
from .test_execution import _safe_source_bytes


_SCHEMA = "agentkit/production-baseline-cache-v1"
_MANIFEST_MAX_BYTES = 2_000_000


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("Private production baseline cache is not canonical JSON.") from exc


def _reject_link(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ContractError("Private production baseline cache path is unavailable.") from exc
    if (stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & 0x400
            or bool(getattr(path, "is_junction", lambda: False)())):
        raise ContractError("Private production baseline cache must not contain links or junctions.")


def _write_exclusive(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ContractError("Private production baseline cache file is unsafe.")
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ContractError("Private production baseline cache already exists.") from exc
    except OSError as exc:
        raise ContractError("Private production baseline cache could not be persisted.") from exc


def _read_regular(cache: Path, relative: str, maximum: int) -> bytes:
    """Use the shared handle-based bounded reader for cache blobs and manifest."""
    _reject_link(cache)
    try:
        if not cache.is_dir():
            raise ContractError("Private production baseline cache path is not a directory.")
        return _safe_source_bytes(cache, relative, maximum)
    except ContractError:
        raise


def _cache_directory(run_dir: Path, workspace: Path) -> Path:
    lexical_run_dir = Path(run_dir).expanduser().absolute()
    if lexical_run_dir.parent.name != ".runs":
        raise ContractError("Private production baseline cache requires a direct agent run directory.")
    safe_run_dir = validate_run_cache_parent(
        lexical_run_dir, lexical_run_dir.parent.parent
    )
    root = safe_run_dir.resolve(strict=True)
    canonical_workspace = _canonical_windows_path(Path(workspace).resolve(strict=True))
    cache = root / "private-production-baseline"
    if cache == canonical_workspace or cache.is_relative_to(canonical_workspace):
        raise ContractError("Private production baseline cache must be outside the mutable workspace.")
    try:
        if os.path.lexists(cache):
            _reject_link(cache)
            if not cache.is_dir():
                raise ContractError("Private production baseline cache path is not a directory.")
    except OSError as exc:
        raise ContractError("Private production baseline cache path cannot be inspected.") from exc
    return cache


def validate_run_cache_parent(run_dir: Path, agent_root: Path) -> Path:
    """Reject links in the lexical run path before resolving any component."""
    candidate = Path(run_dir).expanduser().absolute()
    root = Path(agent_root).resolve(strict=True)
    for current in reversed((candidate, *candidate.parents)):
        if os.path.lexists(current):
            _reject_link(current)
    canonical_candidate = _canonical_windows_path(candidate)
    try:
        relative = canonical_candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError("Private production baseline cache must remain under its agent run root.") from exc
    current = root
    for part in relative.parts:
        current /= part
        if os.path.lexists(current):
            _reject_link(current)
    return canonical_candidate


def capture_production_baseline(
    policy: LocalPhaseTestPolicy, workspace: Path, run_id: str, run_dir: Path
) -> tuple[dict[str, bytes], str]:
    """Persist pristine pinned production bytes before the first worker invocation."""
    root = Path(workspace).resolve(strict=True)
    cache = _cache_directory(run_dir, root)
    cache.mkdir(mode=0o700)
    entries = []
    blobs: dict[str, bytes] = {}
    total = 0
    try:
        for relative, expected_sha256 in policy.production_hashes:
            raw = _safe_source_bytes(root, relative, policy.limits["max_file_bytes"])
            digest = hashlib.sha256(raw).hexdigest()
            if digest != expected_sha256:
                raise ContractError("Production source differs from the pinned baseline before run start.")
            total += len(raw)
            if total > policy.limits["max_snapshot_bytes"]:
                raise ContractError("Private production baseline exceeds the bounded snapshot size.")
            blob_name = hashlib.sha256(relative.encode("utf-8")).hexdigest() + ".blob"
            _write_exclusive(cache / blob_name, raw)
            blobs[relative] = raw
            entries.append({"path": relative, "blob": blob_name, "size": len(raw), "sha256": digest})
        manifest = {
            "schema": _SCHEMA,
            "run_id": run_id,
            "policy_sha256": policy.sha256,
            "workspace": str(policy.workspace_path),
            "files": entries,
        }
        encoded = _canonical_json(manifest)
        if len(encoded) > _MANIFEST_MAX_BYTES:
            raise ContractError("Private production baseline manifest exceeds its byte limit.")
        _write_exclusive(cache / "manifest.json", encoded)
        return blobs, hashlib.sha256(encoded).hexdigest()
    except BaseException:
        # A partial cache is deliberately left in place after errors. A retry
        # cannot silently recapture potentially changed source under this run ID.
        raise


def load_production_baseline(
    policy: LocalPhaseTestPolicy,
    workspace: Path,
    run_id: str,
    run_dir: Path,
    expected_manifest_sha256: str,
) -> dict[str, bytes]:
    """Load and verify the original run baseline; never recapture at resume."""
    if (type(expected_manifest_sha256) is not str or len(expected_manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in expected_manifest_sha256)):
        raise ContractError("Persisted private production baseline identity is missing or invalid.")
    cache = _cache_directory(run_dir, workspace)
    try:
        metadata = cache.stat()
    except OSError as exc:
        raise ContractError("Persisted private production baseline cache is missing.") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise ContractError("Persisted private production baseline cache is not a directory.")
    raw_manifest = _read_regular(cache, "manifest.json", _MANIFEST_MAX_BYTES)
    if hashlib.sha256(raw_manifest).hexdigest() != expected_manifest_sha256:
        raise ContractError("Persisted private production baseline manifest hash does not match the checkpoint.")
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError("Persisted private production baseline manifest is invalid JSON.") from exc
    if (type(manifest) is not dict
            or set(manifest) != {"schema", "run_id", "policy_sha256", "workspace", "files"}
            or manifest["schema"] != _SCHEMA
            or manifest["run_id"] != run_id
            or manifest["policy_sha256"] != policy.sha256
            or manifest["workspace"] != str(policy.workspace_path)
            or type(manifest["files"]) is not list):
        raise ContractError("Persisted private production baseline belongs to another run or policy.")
    if len(manifest["files"]) != len(policy.production_hashes):
        raise ContractError("Persisted private production baseline file list is incomplete.")
    expected_names = {"manifest.json"}
    expected_names.update(
        hashlib.sha256(relative.encode("utf-8")).hexdigest() + ".blob"
        for relative, _digest in policy.production_hashes
    )
    try:
        actual_names = {item.name for item in cache.iterdir()}
    except OSError as exc:
        raise ContractError("Persisted private production baseline inventory is unavailable.") from exc
    if actual_names != expected_names:
        raise ContractError("Persisted private production baseline cache has unexpected files.")
    result = {}
    total = 0
    for entry, (relative, expected_sha256) in zip(
        manifest["files"], policy.production_hashes, strict=True
    ):
        expected_blob = hashlib.sha256(relative.encode("utf-8")).hexdigest() + ".blob"
        if (type(entry) is not dict or set(entry) != {"path", "blob", "size", "sha256"}
                or entry["path"] != relative or entry["blob"] != expected_blob
                or type(entry["size"]) is not int or entry["size"] < 0
                or entry["sha256"] != expected_sha256):
            raise ContractError("Persisted private production baseline entry is invalid.")
        if entry["size"] > policy.limits["max_file_bytes"]:
            raise ContractError("Persisted private production baseline file exceeds its size limit.")
        blob = _read_regular(cache, expected_blob, policy.limits["max_file_bytes"])
        if len(blob) != entry["size"] or hashlib.sha256(blob).hexdigest() != expected_sha256:
            raise ContractError("Persisted private production baseline bytes do not match the operator pin.")
        total += len(blob)
        if total > policy.limits["max_snapshot_bytes"]:
            raise ContractError("Persisted private production baseline exceeds its total size limit.")
        result[relative] = blob
    return result


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result
