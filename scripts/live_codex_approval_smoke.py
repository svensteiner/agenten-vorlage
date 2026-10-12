"""Opt-in, sanitized real-Codex qualification for approval mode.

This smoke test deliberately has a tiny policy surface: the operator may approve
only the exact app.py change and the exact test_app.py pytest invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentkit.backends import CodexBackend, codex_command  # noqa: E402
from agentkit.approvals import action_digest, workspace_fingerprint  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from agentkit.storage import save  # noqa: E402


ORIGINAL_APP = b"def value():\n    return 'before'\n"
EXPECTED_APP = b"def value():\n    return 'after'\n"
TEST_APP = b"from app import value\n\ndef test_value():\n    assert value() == 'after'\n"
MODEL = "gpt-5.6-luna"
BASELINE_FILES = (".gitignore", "STATUS.md", "app.py", "test_app.py")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def allowed_action(pending: dict, *, original: bytes, expected: bytes) -> bool:
    """Return whether a pending action is safe for this qualification fixture."""
    tool = pending.get("tool")
    args = pending.get("arguments")
    if not isinstance(args, dict):
        return False
    if tool == "write_file":
        return args == {"path": "app.py", "content": expected.decode("utf-8")}
    if tool == "edit_file":
        if set(args) != {"path", "old_text", "new_text"} or args["path"] != "app.py":
            return False
        old_text, new_text = args["old_text"], args["new_text"]
        if not isinstance(old_text, str) or not old_text or not isinstance(new_text, str):
            return False
        source = original.decode("utf-8")
        return source.count(old_text) == 1 and source.replace(old_text, new_text).encode("utf-8") == expected
    if tool == "run_pytest":
        return args == {"path": "test_app.py"}
    return False


def policy_decision(pending: dict, *, original: bytes, expected: bytes, reject: bool = False) -> str:
    """Strict local operator policy used by both live scenarios and unit tests."""
    if reject:
        return "reject"
    return "approve" if allowed_action(pending, original=original, expected=expected) else "reject"


def sequence_decision(pending: dict, approved_tools: list[str], *, reject: bool = False) -> str:
    """Approve only one exact mutation followed by one exact verification."""
    if reject:
        return "reject"
    tool = pending.get("tool")
    allowed = allowed_action(pending, original=ORIGINAL_APP, expected=EXPECTED_APP)
    if not allowed:
        return "reject"
    if not approved_tools and tool in {"write_file", "edit_file"}:
        return "approve"
    if len(approved_tools) == 1 and tool == "run_pytest":
        return "approve"
    return "reject"


def _history_trace(history: object) -> list[dict]:
    """Keep bounded diagnostic evidence without raw prompts or model transcripts."""
    if not isinstance(history, list):
        return []
    trace = []
    for item in history[:12]:
        if not isinstance(item, dict):
            continue
        decision = item.get("decision") if isinstance(item.get("decision"), dict) else {}
        report = item.get("report") if isinstance(item.get("report"), dict) else {}
        trace.append({
            "step": item.get("step"),
            "action": decision.get("action"),
            "role": decision.get("role"),
            "report_status": report.get("status"),
            "report_summary": str(report.get("summary", ""))[:300],
            "evidence_count": len(report.get("evidence", []))
            if isinstance(report.get("evidence", []), list) else 0,
        })
    return trace


def _cli_version() -> str:
    try:
        completed = subprocess.run([*codex_command(), "--version"], capture_output=True, text=True,
                                   timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    match = re.search(r"\d+\.\d+\.\d+", completed.stdout or "")
    return match.group(0) if match else "unknown"


def _write_fixture(workspace: Path) -> None:
    (workspace / "app.py").write_bytes(ORIGINAL_APP)
    (workspace / "test_app.py").write_bytes(TEST_APP)
    (workspace / "STATUS.md").write_text("# Isolated approval qualification\n", encoding="utf-8")
    (workspace / ".gitignore").write_text(
        ".agentkit.lock\n__pycache__/\n.pytest_cache/\n", encoding="utf-8"
    )
    for command in (
        ("init", "--quiet"),
        ("config", "user.name", "AgentKit approval smoke"),
        ("config", "user.email", "approval-smoke@example.invalid"),
        ("config", "core.autocrlf", "false"),
        ("add", "--", *BASELINE_FILES),
        ("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "approval smoke baseline"),
    ):
        completed = subprocess.run(
            ["git", *command], cwd=workspace, capture_output=True, text=True,
            timeout=15, check=False,
        )
        if completed.returncode:
            raise RuntimeError("Could not create the isolated Git baseline for live qualification.")


def _git_changes(workspace: Path) -> tuple[list[str], list[str]]:
    """Return machine-measured status entries and tracked paths changed from HEAD."""
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=workspace,
        capture_output=True, text=True, timeout=15, check=False,
    )
    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"], cwd=workspace,
        capture_output=True, text=True, timeout=15, check=False,
    )
    if status.returncode or diff.returncode:
        raise RuntimeError("Could not measure the isolated Git workspace after qualification.")
    return status.stdout.splitlines(), diff.stdout.splitlines()


def _scenario(pack: Path, model: str, call_timeout: int, max_seconds: int, *, reject: bool) -> dict:
    workspace = pack / "workspace"
    _write_fixture(workspace)
    workspace_before = workspace_fingerprint(workspace)
    config_path = pack / "agent.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["limits"].update(max_steps=8, call_timeout=call_timeout, max_seconds=max_seconds)
    save(config_path, config)
    task = (
        "Delegate this bounded task to the developer role; its host actions are available. "
        "In this isolated workspace, read app.py and test_app.py. Change app.py so it is "
        "byte-for-byte exactly this UTF-8 byte sequence (including the final newline): "
        "def value():\\n    return 'after'\\n. Then run "
        "pytest on exactly test_app.py. Use only the bounded write/edit and run_pytest "
        "actions; propose each action for approval. After the test passes, report evidence "
        "and request a separate reviewer before finishing. Do not change any other file. "
        "Then delegate one independent reviewer before finishing. The workspace is a Git "
        "repository with a committed baseline; the reviewer must inspect git status and "
        "git diff HEAD as well as the recorded test evidence."
    )
    started = time.monotonic()
    state = Engine(pack, workspace, CodexBackend(model), require_approvals=True).run(task)
    initial_status = state.get("status")
    preapproval_clean = workspace_fingerprint(workspace) == workspace_before
    approval_count = 0
    approved_tools: list[str] = []
    rejected = False
    rejected_tool = ""
    run_dir = pack / ".runs" / state["run_id"]
    while state.get("status") == "awaiting_approval":
        pending = state.get("pending_approval") or {}
        decision = sequence_decision(pending, approved_tools, reject=reject)
        if decision == "reject":
            rejected = True
            rejected_tool = str(pending.get("tool", ""))
        else:
            approved_tools.append(str(pending.get("tool", "")))
        approval_count += 1
        # A fresh backend and Engine prove that an approval is restart-safe.
        state = Engine(pack, workspace, CodexBackend(model), require_approvals=True).run(
            "", run_dir=run_dir, approval_id=str(pending.get("id", "")), approval_decision=decision
        )
        if rejected:
            break
    app_bytes = workspace.joinpath("app.py").read_bytes()
    git_status, git_diff_paths = _git_changes(workspace)
    expected_git_status = [" M app.py"] if not reject else []
    expected_git_diff_paths = ["app.py"] if not reject else []
    exact_workspace_change = (
        git_status == expected_git_status and git_diff_paths == expected_git_diff_paths
    )
    audit = state.get("approvals", [])
    reviewer_step_completed = any(
        item.get("decision", {}).get("role") == "reviewer"
        and item.get("report", {}).get("status") == "success"
        and bool(item.get("report", {}).get("evidence"))
        for item in state.get("history", [])
    )
    audit_integrity = all(
        entry.get("action_sha256") == action_digest(entry.get("tool"), entry.get("arguments"))
        for entry in audit
    )
    continuation_binding_recorded = all(
        isinstance(entry.get("continuation_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", entry["continuation_sha256"]) is not None
        for entry in audit
    )
    independent_pytest_exit_code = None
    if not reject and app_bytes == EXPECTED_APP:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            verified = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--", "test_app.py"],
                cwd=workspace, env=environment, capture_output=True, text=True, timeout=30, check=False,
            )
            independent_pytest_exit_code = verified.returncode
        except (OSError, subprocess.SubprocessError):
            independent_pytest_exit_code = -1
    return {
        "status": state.get("status"),
        "failure_summary": str(state.get("summary", ""))[:500]
        if state.get("status") == "blocked" and not rejected else "",
        "history_trace": _history_trace(state.get("history")),
        "initial_status": initial_status,
        "completed": state.get("status") == "completed",
        "reviewer_step_completed": reviewer_step_completed,
        "preapproval_clean": preapproval_clean,
        "zero_mutation_on_reject": rejected and workspace_fingerprint(workspace) == workspace_before,
        "app_expected": app_bytes == EXPECTED_APP,
        "git_status": git_status,
        "git_diff_paths": git_diff_paths,
        "exact_workspace_change": exact_workspace_change,
        "app_sha256": sha256(app_bytes),
        "expected_app_sha256": sha256(EXPECTED_APP),
        "approved_tools": approved_tools,
        "approval_count": approval_count,
        "rejected": rejected,
        "rejected_tool": rejected_tool,
        "audit_count": len(audit),
        "audit_decisions": [entry.get("decision") for entry in audit],
        "audit_integrity": audit_integrity,
        "continuation_binding_recorded": continuation_binding_recorded,
        "no_replay": len({entry.get("id") for entry in audit}) == len(audit),
        "independent_pytest_exit_code": independent_pytest_exit_code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run_live(model: str, output: Path, call_timeout: int, max_seconds: int) -> dict:
    started = time.monotonic()
    deadline = started + max_seconds
    result: dict[str, object] = {
        "kind": "codex-approval-smoke", "model": model,
        "call_timeout": call_timeout, "max_seconds": max_seconds,
        "codex_cli_version": _cli_version(), "passed": False,
    }
    with tempfile.TemporaryDirectory(prefix="codex-approval-smoke-") as folder:
        root = Path(folder)
        accept_pack = create(root / "accept-agent", "developer", "approval-accept", "Qualification")
        reject_pack = create(root / "reject-agent", "developer", "approval-reject", "Qualification")
        accept_budget = max(1, int(deadline - time.monotonic()))
        accepted = _scenario(accept_pack, model, min(call_timeout, accept_budget), accept_budget, reject=False)
        reject_budget = int(deadline - time.monotonic())
        if reject_budget > 0:
            rejected = _scenario(reject_pack, model, min(call_timeout, reject_budget), reject_budget, reject=True)
        else:
            rejected = {"status": "budget_exhausted"}
    result["accepted"] = accepted
    result["rejected"] = rejected
    result["passed"] = bool(
        accepted["initial_status"] == "awaiting_approval"
        and accepted["completed"] and accepted["reviewer_step_completed"] and accepted["preapproval_clean"]
        and accepted["app_expected"] and accepted["exact_workspace_change"]
        and accepted["approved_tools"].count("run_pytest") == 1
        and sum(tool in {"write_file", "edit_file"} for tool in accepted["approved_tools"]) == 1
        and accepted["approval_count"] == 2 and accepted["audit_count"] == 2
        and accepted["audit_decisions"] == ["approve", "approve"]
        and accepted["audit_integrity"] and accepted["continuation_binding_recorded"]
        and accepted["independent_pytest_exit_code"] == 0
        and accepted["no_replay"] and rejected.get("initial_status") == "awaiting_approval"
        and rejected.get("rejected") and rejected.get("status") == "blocked"
        and rejected.get("rejected_tool") in {"write_file", "edit_file"}
        and rejected.get("preapproval_clean") and rejected.get("zero_mutation_on_reject") and not rejected.get("app_expected")
        and rejected.get("exact_workspace_change")
        and rejected.get("approval_count") == 1 and rejected.get("audit_count") == 1
        and rejected.get("audit_decisions") == ["reject"] and rejected.get("audit_integrity")
        and rejected.get("continuation_binding_recorded") and rejected.get("no_replay")
    )
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["budget_respected"] = result["elapsed_seconds"] <= max_seconds
    result["passed"] = bool(result["passed"] and result["budget_respected"])
    output.parent.mkdir(parents=True, exist_ok=True)
    save(output, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True, help="Required acknowledgement of real model quota")
    parser.add_argument("--model", choices=(MODEL,), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--call-timeout", type=int, choices=range(15, 121), default=45, metavar="15..120")
    parser.add_argument("--max-seconds", type=int, choices=range(60, 601), default=240, metavar="60..600")
    args = parser.parse_args(argv)
    result = run_live(args.model, args.output, args.call_timeout, args.max_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
