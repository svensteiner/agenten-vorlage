"""Bounded hashes for distinguishing host-recorded writes from workspace baseline."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .contracts import ContractError
from .test_execution import _safe_source_bytes
from .workspace_observation import _sensitive_path
from .write_policy import WritePolicy


_HEX = re.compile(r"^[0-9a-f]{64}$")
_MAX_PATHS = 64
_MAX_TOTAL_BYTES = 4 * 1024 * 1024
_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_RECEIPTS = 48


def _snapshot_path(workspace: Path, policy: WritePolicy, relative: str) -> dict:
    if _sensitive_path(relative):
        return {"path": relative, "state": "unknown", "sha256": None}
    try:
        policy.authorize(workspace, relative)
        raw = _safe_source_bytes(workspace, relative, _MAX_FILE_BYTES)
    except ContractError as exc:
        # A securely observed absent target can be a legitimate write_file
        # destination. Other read failures cannot support attribution.
        if isinstance(exc.__cause__, FileNotFoundError):
            return {"path": relative, "state": "missing", "sha256": None}
        return {"path": relative, "state": "unknown", "sha256": None}
    except (OSError, ValueError, TypeError):
        return {"path": relative, "state": "unknown", "sha256": None}
    return {"path": relative, "state": "present",
            "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def _capture_files(workspace: Path, policy: WritePolicy) -> tuple[str, list[dict]]:
    if len(policy.paths) > _MAX_PATHS:
        return "unknown", []
    files = []
    total = 0
    for relative in policy.paths:
        item = _snapshot_path(workspace, policy, relative)
        if item["state"] == "present":
            total += item["size"]
            if total > _MAX_TOTAL_BYTES:
                return "unknown", [
                    {"path": path, "state": "unknown", "sha256": None}
                    for path in policy.paths
                ]
            item.pop("size")
        files.append(item)
    status = "partial" if any(item["state"] == "unknown" for item in files) else "captured"
    return status, files


def capture_baseline(workspace: Path, policy: WritePolicy) -> dict:
    status, files = _capture_files(Path(workspace), policy)
    return {"version": 1, "policy_sha256": policy.sha256, "status": status, "files": files}


def unknown_baseline(policy: WritePolicy) -> dict:
    files = ([{"path": path, "state": "unknown", "sha256": None} for path in policy.paths]
             if len(policy.paths) <= _MAX_PATHS else [])
    return {"version": 1, "policy_sha256": policy.sha256, "status": "unknown", "files": files}


def validate_baseline(value: object, policy: WritePolicy) -> dict:
    if (type(value) is not dict or set(value) != {"version", "policy_sha256", "status", "files"}
            or type(value["version"]) is not int or value["version"] != 1
            or value["policy_sha256"] != policy.sha256
            or value["status"] not in {"captured", "partial", "unknown"}
            or type(value["files"]) is not list):
        raise ValueError("Persisted run-write provenance baseline is invalid.")
    files = value["files"]
    if len(policy.paths) > _MAX_PATHS:
        if value["status"] != "unknown" or files:
            raise ValueError("Oversized write policy provenance must remain unknown.")
        return value
    if len(files) != len(policy.paths):
        raise ValueError("Run-write baseline paths do not match the active policy.")
    seen_unknown = False
    for relative, item in zip(policy.paths, files, strict=True):
        if (type(item) is not dict or set(item) != {"path", "state", "sha256"}
                or item["path"] != relative):
            raise ValueError("Run-write baseline contains an invalid or noncanonical path.")
        state, digest = item["state"], item["sha256"]
        if state == "present":
            if not isinstance(digest, str) or not _HEX.fullmatch(digest):
                raise ValueError("Run-write baseline digest is invalid.")
        elif state in {"missing", "unknown"}:
            if digest is not None:
                raise ValueError("Non-present baseline state must not contain a digest.")
            seen_unknown |= state == "unknown"
        else:
            raise ValueError("Run-write baseline state is invalid.")
    if value["status"] == "captured" and seen_unknown or value["status"] == "partial" and not seen_unknown:
        raise ValueError("Run-write baseline status does not match its per-file states.")
    if value["status"] == "unknown" and any(item["state"] != "unknown" for item in files):
        raise ValueError("Unknown baseline must not imply known per-file states.")
    return value


def validate_receipts(value: object, policy: WritePolicy) -> list[dict]:
    if not isinstance(value, list) or len(value) > _MAX_RECEIPTS:
        raise ValueError("Persisted run-write receipts are invalid or exhausted.")
    result = []
    for item in value:
        if (type(item) is not dict or set(item) != {"path", "action_sha256", "state", "sha256"}
                or item["path"] not in policy.paths or _sensitive_path(item["path"])
                or not isinstance(item["action_sha256"], str)
                or not _HEX.fullmatch(item["action_sha256"])
                or item["state"] not in {"present", "missing", "unknown"}):
            raise ValueError("Persisted run-write receipt is invalid.")
        if item["state"] == "present":
            if not isinstance(item["sha256"], str) or not _HEX.fullmatch(item["sha256"]):
                raise ValueError("Persisted run-write digest is invalid.")
        elif item["sha256"] is not None:
            raise ValueError("Non-present write receipt must not contain a digest.")
        result.append(item)
    return result


def make_write_receipt(workspace: Path, policy: WritePolicy, action: dict) -> dict | None:
    if (type(action) is not dict or action.get("tool") not in {"write_file", "edit_file"}
            or not isinstance(action.get("arguments"), dict)):
        return None
    relative = action["arguments"].get("path")
    if not isinstance(relative, str) or relative not in policy.paths or _sensitive_path(relative):
        return None
    digest = action.get("action_sha256")
    if not isinstance(digest, str) or not _HEX.fullmatch(digest):
        return None
    item = _snapshot_path(workspace, policy, relative)
    return {"path": relative, "action_sha256": digest,
            "state": item["state"], "sha256": item["sha256"]}


def summarize_run_writes(workspace: Path, policy: WritePolicy,
                         baseline: dict, receipts: list[dict]) -> dict:
    baseline = validate_baseline(baseline, policy)
    receipts = validate_receipts(receipts, policy)
    if baseline["status"] == "unknown":
        return {"status": "unknown", "baseline_status": "unknown",
                "changed_by_run": [], "changed_without_matching_receipt": [],
                "unknown_paths": [item["path"] for item in baseline["files"]],
                "unknown_path_count": len(policy.paths),
                "write_receipt_count": len(receipts)}
    current_status, current_files = _capture_files(Path(workspace), policy)
    if current_status == "unknown":
        return {"status": "unknown", "baseline_status": baseline["status"],
                "changed_by_run": [], "changed_without_matching_receipt": [],
                "unknown_paths": [item["path"] for item in current_files],
                "unknown_path_count": len(policy.paths),
                "write_receipt_count": len(receipts)}
    before = {item["path"]: item for item in baseline["files"]}
    now = {item["path"]: item for item in current_files}
    latest = {item["path"]: item for item in receipts}
    changed_by_run, unattributed, unknown = [], [], []
    for relative in policy.paths:
        initial, current = before[relative], now[relative]
        if initial["state"] == "unknown" or current["state"] == "unknown":
            unknown.append(relative)
            continue
        if (initial["state"], initial["sha256"]) == (current["state"], current["sha256"]):
            continue
        receipt = latest.get(relative)
        if receipt is not None and (receipt["state"], receipt["sha256"]) == (
                current["state"], current["sha256"]):
            changed_by_run.append(relative)
        else:
            unattributed.append(relative)
    def display(path: str) -> str:
        return "[sensitive path]" if _sensitive_path(path) else path

    return {"status": "partial" if unknown else "complete",
            "baseline_status": baseline["status"],
            "changed_by_run": [display(path) for path in changed_by_run],
            "changed_without_matching_receipt": [display(path) for path in unattributed],
            "unknown_paths": [display(path) for path in unknown],
            "unknown_path_count": len(unknown),
            "write_receipt_count": len(receipts)}
