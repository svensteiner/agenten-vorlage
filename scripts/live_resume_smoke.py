"""Bounded, explicit real-model interruption/resume qualification.

This script is opt-in because it consumes model quota. It never records prompts,
credentials, or raw backend output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentkit.backends import CodexBackend  # noqa: E402
from agentkit.contracts import ContractError, read_json  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from agentkit.storage import save  # noqa: E402


MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_ENTRIES = 512
INTERNAL_WORKSPACE_FILES = {".agentkit.lock"}


def _kill(proc: subprocess.Popen) -> bool:
    """Terminate a live process tree and report whether a signal was delivered."""
    if proc.poll() is not None:
        proc.wait(timeout=10)
        return False
    delivered = False
    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        delivered = result.returncode == 0
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            delivered = True
        except ProcessLookupError:
            pass
    proc.wait(timeout=10)
    return delivered and proc.poll() is not None


def _process_options() -> dict:
    if os.name == "nt":
        return {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        }
    return {"start_new_session": True}


def _child(pack: Path, model: str, task: str) -> int:
    try:
        state = Engine(pack, pack / "workspace", CodexBackend(model)).run(task)
        return 0 if state.get("status") == "completed" else 2
    except Exception:
        return 3


def _resume(pack: Path, checkpoint: Path, backend: CodexBackend) -> tuple[bool, dict]:
    refused_without_ack = False
    try:
        Engine(pack, pack / "workspace", backend).run(
            "", run_dir=checkpoint.parent, feedback="Inspect checkpoint"
        )
    except ContractError as exc:
        refused_without_ack = "acknowledge-interruption" in str(exc)
    resumed = Engine(pack, pack / "workspace", backend).run(
        "",
        run_dir=checkpoint.parent,
        feedback="Workspace inspected; safely continue from durable evidence.",
        acknowledge_interruption=True,
    )
    return refused_without_ack, resumed


def _resume_child(pack: Path, checkpoint: Path, model: str) -> int:
    try:
        refused, resumed = _resume(pack, checkpoint, CodexBackend(model))
    except Exception:
        return 3
    return 0 if refused and resumed.get("status") == "completed" else 2


def _wait_bounded(proc: subprocess.Popen, deadline: float) -> int:
    """Wait only until the parent-wide deadline and kill the whole tree on timeout."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        if proc.poll() is None:
            _kill(proc)
        raise TimeoutError("qualification deadline expired")
    try:
        return proc.wait(timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        if proc.poll() is None:
            _kill(proc)
        raise TimeoutError("qualification deadline expired") from exc


def _workspace_manifest(root: Path) -> list[dict]:
    """Create a bounded final-state manifest without storing workspace contents."""
    manifest: list[dict] = []
    hashed = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as scanner:
            entries = []
            for entry in scanner:
                entries.append(entry)
                if len(entries) + len(manifest) > MAX_MANIFEST_ENTRIES:
                    raise ValueError("workspace manifest exceeds entry limit")
        for item in sorted(entries, key=lambda entry: entry.name.casefold()):
            path = Path(item.path)
            relative = path.relative_to(root).as_posix()
            if relative in INTERNAL_WORKSPACE_FILES:
                continue
            if item.is_symlink():
                manifest.append({"path": relative, "kind": "symlink"})
            elif item.is_dir(follow_symlinks=False):
                manifest.append({"path": relative, "kind": "directory"})
                pending.append(path)
            elif item.is_file(follow_symlinks=False):
                size = item.stat(follow_symlinks=False).st_size
                entry = {"path": relative, "kind": "file", "size": size}
                if hashed + size > MAX_MANIFEST_BYTES:
                    raise ValueError("workspace manifest exceeds byte limit")
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(64 * 1024), b""):
                        digest.update(chunk)
                entry["sha256"] = digest.hexdigest()
                hashed += size
                manifest.append(entry)
            else:
                manifest.append({"path": relative, "kind": "other"})
    manifest.sort(key=lambda entry: str(entry.get("path", "")))
    return manifest


def _report_contains(state: dict, marker: str) -> bool:
    for item in state.get("history", []):
        report = item.get("report") if isinstance(item, dict) else None
        if not isinstance(report, dict):
            continue
        if marker in str(report.get("summary", "")):
            return True
        evidence = report.get("evidence", [])
        if isinstance(evidence, list) and any(marker in str(value) for value in evidence):
            return True
    return False


def _qualification_passed(*, child_terminated: bool, refused: bool, completed: bool,
                          marker_in_summary: bool, marker_in_report: bool,
                          workspace_unchanged: bool) -> bool:
    return all((child_terminated, refused, completed, marker_in_summary,
                marker_in_report, workspace_unchanged))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live", action="store_true", required=True)
    p.add_argument("--model", required=True, help="Use gpt-5.6-luna explicitly")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--call-timeout", type=int, required=True)
    p.add_argument("--max-seconds", type=int, required=True)
    p.add_argument("--_child", nargs=3, metavar=("PACK", "MODEL", "TASK"), help=argparse.SUPPRESS)
    p.add_argument("--_resume-child", nargs=3, metavar=("PACK", "CHECKPOINT", "MODEL"),
                   help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if a._child:
        return _child(Path(a._child[0]), a._child[1], a._child[2])
    if a._resume_child:
        return _resume_child(Path(a._resume_child[0]), Path(a._resume_child[1]), a._resume_child[2])
    if a.model != "gpt-5.6-luna":
        p.error("live qualification is restricted to gpt-5.6-luna")
    if not (15 <= a.call_timeout <= 120 and 60 <= a.max_seconds <= 600):
        p.error("call-timeout must be 15..120 and max-seconds 60..600")
    started = time.monotonic()
    evidence = {"kind": "live-resume-smoke", "model": a.model, "passed": False,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "call_timeout": a.call_timeout, "max_seconds": a.max_seconds}
    task = "Read STATUS.md and report its first heading; do not modify files or access the network."
    with tempfile.TemporaryDirectory(prefix="agentkit-live-resume-") as d:
        pack = create(Path(d) / "agent", "research", "live-resume", "ReleaseQualification")
        cfg = json.loads((pack / "agent.json").read_text(encoding="utf-8"))
        cfg["limits"].update(max_seconds=a.max_seconds, call_timeout=a.call_timeout, max_steps=3)
        save(pack / "agent.json", cfg)
        (pack / "workspace" / "STATUS.md").write_text("# Isolated resume probe\n", encoding="utf-8")
        workspace_before = _workspace_manifest(pack / "workspace")
        proc = subprocess.Popen([sys.executable, __file__, "--live", "--model", a.model,
                                 "--output", str(a.output), "--call-timeout", str(a.call_timeout),
                                 "--max-seconds", str(a.max_seconds), "--_child", str(pack), a.model, task],
                                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                **_process_options())
        state_path = pack / ".runs"
        deadline = started + a.max_seconds
        checkpoint = None
        evidence["workspace_internal_exclusions"] = sorted(INTERNAL_WORKSPACE_FILES)
        while time.monotonic() < deadline and proc.poll() is None:
            files = list(state_path.glob("*/state.json")) if state_path.exists() else []
            if files:
                candidate = read_json(files[0])
                if candidate.get("in_flight"):
                    checkpoint = files[0]
                    break
            time.sleep(0.1)
        if checkpoint is None:
            _kill(proc) if proc.poll() is None else None
            evidence["status"] = "no_durable_in_flight_checkpoint"
        else:
            continue_resume = False
            child_terminated = _kill(proc)
            evidence["child_was_terminated"] = child_terminated
            if not child_terminated:
                evidence["status"] = "child_exited_before_interruption"
            else:
                try:
                    state = read_json(checkpoint)
                except Exception:
                    evidence["status"] = "checkpoint_unreadable_after_interruption"
                    state = {}
                in_flight = state.get("in_flight")
                if not isinstance(in_flight, dict):
                    evidence["status"] = "checkpoint_no_longer_in_flight"
                    continue_resume = False
                else:
                    evidence["checkpoint_kind"] = in_flight.get("kind")
                    continue_resume = True
            if child_terminated and continue_resume:
                resume_proc = subprocess.Popen(
                    [sys.executable, __file__, "--live", "--model", a.model,
                     "--output", str(a.output), "--call-timeout", str(a.call_timeout),
                     "--max-seconds", str(a.max_seconds), "--_resume-child", str(pack),
                     str(checkpoint), a.model],
                    cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    **_process_options(),
                )
                try:
                    resume_exit = _wait_bounded(resume_proc, deadline)
                except TimeoutError:
                    evidence["status"] = "resume_deadline_exceeded"
                else:
                    refused_without_ack = resume_exit == 0
                    resumed = read_json(checkpoint)
                    completed = resumed.get("status") == "completed"
                    summary = str(resumed.get("summary", ""))
                    marker_in_summary = "Isolated resume probe" in summary
                    marker_in_report = _report_contains(resumed, "Isolated resume probe")
                    try:
                        invariant = _workspace_manifest(pack / "workspace") == workspace_before
                    except (OSError, ValueError):
                        invariant = False
                    evidence.update(
                        status=resumed.get("status"),
                        steps=resumed.get("steps"),
                        refusal="ContractError" if refused_without_ack else "missing",
                        refused_without_acknowledgment=refused_without_ack,
                        resumed_after_acknowledgment=completed,
                        marker_in_summary=marker_in_summary,
                        marker_in_report=marker_in_report,
                        workspace_unchanged=invariant,
                        passed=_qualification_passed(
                            child_terminated=child_terminated,
                            refused=refused_without_ack,
                            completed=completed,
                            marker_in_summary=marker_in_summary,
                            marker_in_report=marker_in_report,
                            workspace_unchanged=invariant,
                        ),
                    )
    evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
