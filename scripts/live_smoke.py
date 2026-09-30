"""Explicitly opt in to a bounded real-model workflow in an isolated test workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentkit.backends import CodexBackend, DeepSeekBackend  # noqa: E402
from agentkit.codex_artifacts import MAX_ARTIFACT_BYTES, read_codex_artifact  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from agentkit.storage import save  # noqa: E402


def _read_bounded(path: Path, max_bytes: int) -> bytes:
    if path.stat().st_size > max_bytes:
        raise ValueError("file exceeds qualification limit")
    with path.open("rb") as handle:
        value = handle.read(max_bytes + 1)
    if len(value) > max_bytes:
        raise ValueError("file exceeds qualification limit")
    return value


def _artifact_was_reported(workspace: Path, artifact: Path, reported: set[str]) -> bool:
    expected = artifact.resolve()
    for value in reported:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = workspace / candidate
        try:
            if candidate.resolve() == expected:
                return True
        except (OSError, RuntimeError):
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True, help="Acknowledge use of real model quota")
    parser.add_argument("--backend", choices=("codex", "deepseek"), required=True)
    parser.add_argument("--model", required=True, help="Explicit model; never silently use an expensive default")
    parser.add_argument("--scenario", choices=("read", "write"), default="read")
    parser.add_argument("--output", type=Path, required=True, help="Sanitized JSON evidence file")
    parser.add_argument("--call-timeout", type=int, default=45, choices=range(15, 121), metavar="15..120")
    parser.add_argument("--max-seconds", type=int, default=180, choices=range(60, 601), metavar="60..600")
    args = parser.parse_args()
    started = time.monotonic()
    marker = "STUDIO-FACT-4729"
    result = {"kind": "real-model-workflow", "backend": args.backend, "model": args.model,
              "scenario": args.scenario, "started_at": datetime.now(timezone.utc).isoformat(),
              "call_timeout": args.call_timeout, "max_seconds": args.max_seconds,
              "isolated_user_config": args.backend == "codex",
              "passed": False, "status": "not_started"}
    # A fixture inside this repository inherits its AGENTS.md and its full test
    # requirements. Keep qualification separate from the template being tested.
    scratch_root = Path(tempfile.gettempdir()) / "agentkit-qualification"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="studio-live-qualification-",
        dir=scratch_root,
        ignore_cleanup_errors=True,
    ) as folder:
        pack = create(Path(folder) / "agent", "research" if args.scenario == "read" else "developer",
                      "qualification", "ReleaseQualification")
        config_file = pack / "agent.json"
        config = json.loads(config_file.read_text(encoding="utf-8"))
        config["limits"].update(max_steps=5 if args.scenario == "read" else 9,
                                max_seconds=args.max_seconds, call_timeout=args.call_timeout)
        save(config_file, config)
        workspace = pack / "workspace"
        fact_bytes = (marker + "\n").encode("utf-8")
        (workspace / "FACT.txt").write_bytes(fact_bytes)
        (workspace / "STATUS.md").write_text("# Isolated model qualification\nOnly test files in this directory may be used.\n", encoding="utf-8")
        if args.scenario == "read":
            task = (
                "Read FACT.txt in the workspace and report its exact marker in the final summary, "
                "with evidence that you actually read it. Do not modify any file. "
                "A single research worker report is sufficient; do not perform external research."
            )
        else:
            task = (
                "Read FACT.txt. Create RESULT.txt containing exactly the same bytes. "
                "Use local Python to print the stripped FACT.txt value, verify byte equality, "
                "and report both command results. The literal file value itself (not a label or "
                "description) is a mandatory acceptance item in every worker report and in the "
                "planner's final summary; completion without that literal is invalid. "
                "Have a separate reviewer independently read both files and confirm the equality. "
                "Do not install dependencies, "
                "access network resources, or change files outside this isolated workspace."
            )
        try:
            backend = (CodexBackend if args.backend == "codex" else DeepSeekBackend)(args.model)
            if args.backend == "codex":
                result["windows_sandbox"] = backend.windows_sandbox
            state = Engine(pack, workspace, backend).run(task)
            reports = [item for item in state["history"] if "report" in item]
            reported_artifacts = {
                str(path).replace("\\", "/")
                for item in reports
                for path in item["report"].get("artifacts", [])
                if isinstance(path, str)
            }
            summary = str(state.get("summary", ""))
            result.update(status=state["status"], steps=state["steps"],
                          reviewed=state["reviewed"], dirty=state["dirty"],
                          report_count=len(reports),
                          report_statuses=[item["report"].get("status") in {"success", "needs_revision", "blocked"} for item in reports])
            result["summary_sha256"] = hashlib.sha256(summary.encode("utf-8")).hexdigest()
            source_bytes = _read_bounded(workspace / "FACT.txt", len(fact_bytes))
            result["source_unchanged"] = source_bytes == fact_bytes
            result["marker_in_final_summary"] = marker in summary
            if args.scenario == "write":
                target = workspace / "RESULT.txt"
                result["artifact_reported"] = _artifact_was_reported(
                    workspace, target, reported_artifacts
                )
                if not result["artifact_reported"]:
                    raise ValueError("RESULT.txt was not reported as an approved artifact")
                try:
                    artifact = _read_bounded(target, MAX_ARTIFACT_BYTES)
                    result["artifact_read_method"] = "host"
                except PermissionError:
                    if args.backend != "codex":
                        raise
                    artifact = read_codex_artifact(workspace, "RESULT.txt")
                    result["artifact_read_method"] = "codex_readonly_sandbox_export"
                result["artifact_verified"] = artifact == (marker + "\n").encode()
                if result["artifact_verified"]:
                    result["artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
            else:
                result["artifact_verified"] = result["source_unchanged"] and not state["dirty"]
            result["passed"] = bool(
                state["status"] == "completed" and reports and result["source_unchanged"]
                and result["marker_in_final_summary"] and result["artifact_verified"]
                and (args.scenario == "read" or (state["reviewed"] and result["artifact_reported"]))
            )
        except Exception as exc:
            result.update(status="failed", error_type=type(exc).__name__)
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
