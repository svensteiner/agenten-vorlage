"""Durable, single-use approvals for side-effecting backend tools."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from .contracts import ContractError, inside


WRITE_TOOLS = {"write_file", "edit_file", "run_pytest"}
INTERNAL_WORKSPACE_SEGMENTS = frozenset({
    ".agentkit.lock", ".git", ".lock", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".runs", "__pycache__",
})


class ApprovalRequired(Exception):
    """Raised before a tool is executed when an operator decision is needed."""

    def __init__(self, request: dict):
        super().__init__("Tool approval required")
        self.request = request


def _canonical_windows_path(path: Path) -> Path:
    """Expand 8.3 aliases for the deepest existing ancestor, failing closed."""
    resolved = path.resolve()
    if os.name != "nt":
        return resolved
    import ctypes

    probe = resolved
    suffix: list[str] = []
    while True:
        try:
            if probe.exists():
                break
        except OSError as exc:
            raise ContractError("Workspace path cannot be inspected safely.") from exc
        parent = probe.parent
        if parent == probe:
            raise ContractError("Workspace path has no existing canonical ancestor.")
        suffix.append(probe.name)
        probe = parent
    buffer = ctypes.create_unicode_buffer(32_768)
    length = ctypes.windll.kernel32.GetLongPathNameW(str(probe), buffer, len(buffer))
    if not length or length >= len(buffer):
        raise ContractError("Workspace path cannot be canonicalized safely.")
    canonical = Path(buffer.value)
    for name in reversed(suffix):
        canonical /= name
    return canonical.resolve()


def safe_workspace_path(workspace: Path, relative: str) -> Path:
    """Resolve a workspace path and reject canonical internal/runtime segments."""
    if (not isinstance(relative, str) or not relative or len(relative) > 500
            or "\x00" in relative or any(ord(char) < 32 for char in relative)):
        raise ContractError("Workspace path must be bounded text without control characters.")
    if os.name == "nt":
        reserved = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        for part in Path(relative).parts:
            if (":" in part or part.endswith((" ", "."))
                    or part.split(".", 1)[0].upper() in reserved):
                raise ContractError("Workspace path uses unsafe Windows device or stream syntax.")
    target = inside(workspace, relative)
    canonical_root = _canonical_windows_path(workspace)
    canonical_target = _canonical_windows_path(target)
    try:
        canonical_relative = canonical_target.relative_to(canonical_root)
    except ValueError as exc:
        raise ContractError("Path escapes its workspace after canonicalization.") from exc
    if any(
        part.casefold() in INTERNAL_WORKSPACE_SEGMENTS
        for part in canonical_relative.parts
    ):
        raise ContractError("Path targets internal coordination/cache state.")
    return canonical_target


def workspace_fingerprint(workspace: Path) -> str:
    """Hash supported workspace contents; unsupported inputs fail closed."""
    digest = hashlib.sha256()
    root = workspace.resolve()
    total_bytes = 0
    items = []
    def unreadable(error):
        raise ContractError("Workspace could not be fingerprinted safely.") from error

    for current, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
        dirs[:] = sorted(
            d for d in dirs if d.casefold() not in INTERNAL_WORKSPACE_SEGMENTS
        )
        files[:] = sorted(files)
        for name in [*dirs, *files]:
            item = Path(current) / name
            if item.name.casefold() in INTERNAL_WORKSPACE_SEGMENTS:
                continue
            if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
                raise ContractError("Linked paths are not supported in approval workspaces.")
            items.append(item)
            if len(items) > 4096:
                raise ContractError("Workspace is too large to safely fingerprint for approval.")
    for item in sorted(items, key=lambda p: str(p).lower()):
        try:
            rel = item.relative_to(root).as_posix()
            if item.is_symlink():
                raise ContractError("Symlinks are not supported in approval workspaces.")
            stat = item.stat()
            digest.update(json.dumps([rel, stat.st_size, stat.st_mtime_ns]).encode())
            if item.is_file():
                total_bytes += stat.st_size
                if total_bytes > 8 * 1024 * 1024:
                    raise ContractError("Workspace is too large to safely fingerprint for approval.")
                with item.open("rb") as handle:
                    content = handle.read(stat.st_size + 1)
                if len(content) != stat.st_size:
                    raise ContractError("Workspace changed during approval fingerprinting.")
                digest.update(content)
        except OSError as exc:
            raise ContractError("Workspace could not be fingerprinted safely.") from exc
    return digest.hexdigest()


def new_id() -> str:
    return uuid.uuid4().hex


def _json_digest(value: object, label: str) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError(f"Approval {label} is not canonical JSON.") from exc
    return hashlib.sha256(encoded).hexdigest()


def action_digest(tool: str, arguments: dict) -> str:
    """Bind the operator-visible canonical manifest to the resumed executor."""
    return _json_digest({"tool": tool, "arguments": arguments}, "action")


def replay_action_digest(tool: str, arguments: dict, workspace: Path) -> str:
    """Hash a filesystem-canonical identity without changing the visible manifest."""
    if not isinstance(arguments, dict) or not isinstance(arguments.get("path"), str):
        raise ContractError("Approval replay action has no valid workspace path.")
    canonical_root = _canonical_windows_path(workspace)
    canonical_target = safe_workspace_path(workspace, arguments["path"])
    try:
        relative = canonical_target.relative_to(canonical_root).as_posix()
    except ValueError as exc:
        raise ContractError("Approval replay path escapes its canonical workspace.") from exc
    canonical_arguments = dict(arguments)
    canonical_arguments["path"] = relative.casefold() if os.name == "nt" else relative
    return _json_digest(
        {"tool": tool, "arguments": canonical_arguments}, "replay action"
    )


def continuation_digest(continuation: dict) -> str:
    """Bind hidden resume state so a persisted approval cannot change meaning."""
    return _json_digest(continuation, "continuation")


def binding(*, run_id: str, agent: str, company: str, workspace: str, backend: str,
            model: str | None, fingerprint: str, write_policy_sha256: str = "") -> dict:
    result = {"run_id": run_id, "agent": agent, "company": company, "workspace": workspace,
              "backend": backend, "model": model or "", "workspace_fingerprint": fingerprint}
    if write_policy_sha256:
        result["write_policy_sha256"] = write_policy_sha256
    return result


def validate_binding(request: dict, current: dict) -> None:
    if request.get("binding") != current:
        raise ContractError("Approval is stale or bound to a different run, workspace, company or backend.")
    if request.get("action_sha256") != action_digest(request.get("tool"), request.get("arguments")):
        raise ContractError("Approval action integrity check failed.")
    if request.get("continuation_sha256") != continuation_digest(request.get("continuation")):
        raise ContractError("Approval continuation integrity check failed.")
