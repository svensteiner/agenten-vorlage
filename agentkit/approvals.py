"""Durable, single-use approvals for side-effecting backend tools."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from .contracts import ContractError


WRITE_TOOLS = {"write_file", "edit_file", "run_pytest"}


class ApprovalRequired(Exception):
    """Raised before a tool is executed when an operator decision is needed."""

    def __init__(self, request: dict):
        super().__init__("Tool approval required")
        self.request = request


def workspace_fingerprint(workspace: Path) -> str:
    """Hash supported workspace contents; unsupported inputs fail closed."""
    digest = hashlib.sha256()
    root = workspace.resolve()
    total_bytes = 0
    items = []
    def unreadable(error):
        raise ContractError("Workspace could not be fingerprinted safely.") from error

    for current, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
        dirs[:] = sorted(d for d in dirs if d not in {".runs", ".git"})
        files[:] = sorted(files)
        for name in [*dirs, *files]:
            item = Path(current) / name
            if item.name in {".agentkit.lock", ".lock"}:
                continue
            if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
                raise ContractError("Linked paths are not supported in approval workspaces.")
            items.append(item)
            if len(items) > 512:
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


def binding(*, run_id: str, agent: str, company: str, workspace: str, backend: str, model: str | None, fingerprint: str) -> dict:
    return {"run_id": run_id, "agent": agent, "company": company, "workspace": workspace,
            "backend": backend, "model": model or "", "workspace_fingerprint": fingerprint}


def validate_binding(request: dict, current: dict) -> None:
    if request.get("binding") != current:
        raise ContractError("Approval is stale or bound to a different run, workspace, company or backend.")
