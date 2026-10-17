"""Immutable host-owned allowlist for exact workspace files a worker may write."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .approvals import (
    INTERNAL_WORKSPACE_SEGMENTS,
    _canonical_windows_path,
    safe_workspace_path,
)
from .contracts import ContractError


def _canonical_rule(value: object) -> str:
    if (not isinstance(value, str) or not value or len(value) > 500
            or "\\" in value or ":" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or unicodedata.normalize("NFC", value) != value):
        raise ContractError("Write-policy paths must be canonical relative POSIX paths.")
    parts = value.split("/")
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
    if any(
        not part or part in {".", ".."} or part.endswith((" ", "."))
        or part.split(".", 1)[0].rstrip(" .").upper() in reserved
        or part.casefold() in INTERNAL_WORKSPACE_SEGMENTS
        for part in parts
    ):
        raise ContractError("Write-policy path contains a noncanonical or protected segment.")
    if Path(value).is_absolute() or value.startswith("/"):
        raise ContractError("Write-policy paths must stay relative to the workspace.")
    return value


@dataclass(frozen=True, slots=True, init=False)
class WritePolicy:
    """A canonical, immutable set of exact relative filenames.

    The policy is a logical AgentKit boundary, not an OS sandbox. Codex strict
    mode therefore uses read-only proposals and the host executor; arbitrary
    project execution is disabled while a policy is active. It assumes no
    untrusted process concurrently changes workspace paths; it cannot close
    filesystem races against another host-level actor.
    """

    paths: tuple[str, ...]
    sha256: str

    def __init__(self, paths: Iterable[str]):
        if isinstance(paths, (str, bytes)):
            raise ContractError("WritePolicy expects an iterable of file paths.")
        try:
            canonical = tuple(sorted(_canonical_rule(path) for path in paths))
        except TypeError as exc:
            raise ContractError("WritePolicy expects an iterable of file paths.") from exc
        folded = [path.casefold() for path in canonical]
        if len(set(folded)) != len(canonical):
            raise ContractError("Write-policy paths must be unique without case aliases.")
        digest = hashlib.sha256(
            json.dumps(
                {"version": 1, "paths": canonical},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "paths", canonical)
        object.__setattr__(self, "sha256", digest)

    def authorize(self, workspace: Path, relative: str) -> Path:
        """Return the canonical target only when it is an exact allowed file."""
        if not isinstance(relative, str) or "\\" in relative:
            raise ContractError("Write action path is not canonical relative POSIX text.")
        root = workspace.resolve()
        candidate = root
        for part in relative.split("/"):
            if part in {"", ".", ".."}:
                raise ContractError("Write action path is not canonical.")
            candidate /= part
            try:
                linked = candidate.is_symlink() or bool(
                    getattr(candidate, "is_junction", lambda: False)()
                )
            except OSError as exc:
                raise ContractError("Write action path cannot be inspected safely.") from exc
            if linked:
                raise ContractError("Write action path traverses a link or junction.")
        target = safe_workspace_path(root, relative)
        try:
            actual = target.relative_to(_canonical_windows_path(root))
        except (ValueError, ContractError) as exc:
            raise ContractError("Write action escapes its workspace.") from exc
        identity = actual.as_posix()
        if identity != relative:
            raise ContractError("Write action path uses a filesystem alias or noncanonical case.")
        if identity not in self.paths:
            raise ContractError("Write action path is outside the host write policy.")
        if target.exists():
            try:
                stat = target.stat()
            except OSError as exc:
                raise ContractError("Write target cannot be inspected safely.") from exc
            if stat.st_nlink > 1:
                raise ContractError("Write target has hard-link aliases and is not permitted.")
            if not target.is_file():
                raise ContractError("Write policy permits files only, not directories or special paths.")
        return target

    def authorize_action(self, workspace: Path, tool: str, arguments: dict) -> Path:
        """Check a proposed mutation before approval, dispatch or file creation."""
        if tool == "run_pytest":
            raise ContractError("Project execution is disabled while a strict write policy is active.")
        if tool not in {"write_file", "edit_file"} or not isinstance(arguments, dict):
            raise ContractError("Unsupported action under the strict write policy.")
        return self.authorize(workspace, arguments.get("path"))

    def authorize_target(self, workspace: Path, target: Path) -> Path:
        """Recheck an already resolved path at the final host mutation boundary."""
        root = _canonical_windows_path(workspace)
        canonical_target = _canonical_windows_path(target)
        try:
            relative = canonical_target.relative_to(root).as_posix()
        except ValueError as exc:
            raise ContractError("Mutation target escapes its workspace.") from exc
        return self.authorize(root, relative)
