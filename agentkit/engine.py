"""An observation-driven loop. The planner chooses the next action, not a task DAG."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Protocol

from .catalog import Catalog
from .contracts import ContractError, read_json, validate
from .storage import lock, save
from .write_policy import WritePolicy
from .approvals import (
    ApprovalRequired,
    action_digest,
    binding,
    continuation_digest,
    new_id,
    replay_action_digest,
    safe_workspace_path,
    validate_binding,
    workspace_fingerprint,
)


class Backend(Protocol):
    name: str

    def decide(self, context: dict, timeout: float) -> dict: ...

    def execute(self, decision: dict, context: dict, timeout: float) -> dict: ...


def _valid_completed_actions(value: object) -> bool:
    if not isinstance(value, list) or len(value) > 48:
        return False
    try:
        if len(json.dumps(value, ensure_ascii=False)) > 40_000:
            return False
    except (TypeError, ValueError):
        return False
    hexadecimal = frozenset("0123456789abcdef")
    return all(
        isinstance(entry, dict)
        and entry.get("kind") == "completed_action"
        and isinstance(entry.get("action_sha256"), str)
        and len(entry["action_sha256"]) == 64
        and set(entry["action_sha256"]) <= hexadecimal
        and isinstance(entry.get("replay_sha256"), str)
        and len(entry["replay_sha256"]) == 64
        and set(entry["replay_sha256"]) <= hexadecimal
        and isinstance(entry.get("post_workspace_fingerprint"), str)
        and len(entry["post_workspace_fingerprint"]) == 64
        and set(entry["post_workspace_fingerprint"]) <= hexadecimal
        for entry in value
    )


class Engine:
    def _verify_artifact(self, artifact: str, timeout: float) -> None:
        try:
            if not safe_workspace_path(self.workspace, artifact).is_file():
                raise ContractError(f"Reported artifact does not exist: {artifact}")
        except (PermissionError, ContractError) as exc:
            denied = isinstance(exc, PermissionError) or isinstance(exc.__cause__, PermissionError)
            if self.backend.name != "codex" or not denied:
                raise
            # Canonical path/internal-state checks run unchanged in the read-only
            # sandbox account. Never alter ACLs or repeat the worker's write.
            from .codex_artifacts import verify_codex_artifact
            verify_codex_artifact(self.workspace, artifact, timeout=timeout)

    def __init__(
        self,
        agent_dir: Path,
        workspace: Path,
        backend: Backend,
        *,
        require_approvals: bool = False,
        write_policy: WritePolicy | None = None,
        core_snapshot: str | None = None,
        mutation_writer: Callable[[Path, bytes], None] | None = None,
        state_writer: Callable[[Path, bytes], None] | None = None,
        coordination_reserver: Callable[[Path, Path], Any] | None = None,
    ):
        self.catalog = Catalog(agent_dir)
        self.workspace = workspace.resolve()
        self.backend = backend
        self.limits = self.catalog.config["limits"]
        self.require_approvals = require_approvals
        if write_policy is not None and type(write_policy) is not WritePolicy:
            raise ContractError("write_policy must be a host-created WritePolicy.")
        if write_policy is not None and getattr(backend, "supports_write_policy", False) is not True:
            raise ContractError("The selected backend cannot enforce a strict write policy.")
        self.write_policy = write_policy
        self.mutation_writer = mutation_writer
        self.state_writer = state_writer
        self.coordination_reserver = coordination_reserver
        if core_snapshot is not None and not isinstance(core_snapshot, str):
            raise ContractError("core_snapshot must be text.")
        if isinstance(core_snapshot, str) and len(core_snapshot) > self.limits["max_context_chars"]:
            raise ContractError("core_snapshot exceeds the context budget.")
        self.core_snapshot = core_snapshot
        if require_approvals and not getattr(backend, "supports_action_approvals", False):
            raise ContractError("This backend cannot enforce individual tool approvals.")

    def run(
        self,
        task: str,
        *,
        run_dir: Path | None = None,
        feedback: str = "",
        acknowledge_interruption: bool = False,
        new_run_id: str | None = None,
        approval_id: str = "",
        approval_decision: str = "",
    ) -> dict:
        if new_run_id is not None:
            if run_dir is not None or not isinstance(new_run_id, str) or len(new_run_id) != 32:
                raise ContractError("new_run_id must be a fresh 32-character UUID hex value.")
            try:
                if uuid.UUID(hex=new_run_id).hex != new_run_id:
                    raise ValueError("Noncanonical UUID")
            except ValueError as exc:
                raise ContractError("new_run_id must be a fresh 32-character UUID hex value.") from exc
        if not task.strip() and run_dir is None:
            raise ContractError("A task must not be empty.")
        if not self.workspace.is_dir():
            raise ContractError(f"Workspace does not exist: {self.workspace}")
        if run_dir is not None and not (run_dir / "state.json").is_file():
            raise ContractError("Resume checkpoint does not exist; no new run was started.")
        directory = run_dir or self.catalog.root / ".runs" / (new_run_id or uuid.uuid4().hex)
        directory = directory.resolve()
        if directory.parent != (self.catalog.root / ".runs").resolve():
            raise ContractError("Run checkpoints must remain inside this agent's .runs directory.")
        reservation = None
        try:
            if self.coordination_reserver is not None:
                reservation = self.coordination_reserver(directory, self.workspace)
            directory.mkdir(parents=True, exist_ok=True)
            with lock(directory / ".lock"), lock(self.workspace / ".agentkit.lock"):
                if new_run_id is not None and (directory / "state.json").exists():
                    raise ContractError("Run ID already has a checkpoint; use resume explicitly.")
                result = self._locked(
                    task,
                    directory,
                    feedback,
                    acknowledge_interruption,
                    approval_id,
                    approval_decision,
                    reservation=reservation,
                )
                # A completed checkpoint resumed without writing anything
                # leaves a newly-created coordination reservation unused.
                # Rollback is idempotent after commit and removes only files
                # owned by this reservation.
                if reservation is not None:
                    reservation.rollback()
                return result
        except Exception:
            if reservation is not None:
                try:
                    reservation.rollback()
                except Exception:
                    pass
            raise

    def _locked(
        self,
        task: str,
        directory: Path,
        feedback: str,
        acknowledge: bool,
        approval_id: str,
        approval_decision: str,
        *,
        reservation: Any = None,
    ) -> dict:
        path = directory / "state.json"
        config = self.catalog.config
        failure_baseline = 0
        if path.exists():
            state = read_json(path)
            if state.get("run_id") != directory.name:
                raise ContractError("Checkpoint identity does not match its directory.")
            if (
                state["agent"] != config["id"]
                or state["company"] != config["company"]
                or state["workspace"] != str(self.workspace)
                or state["backend"] != self.backend.name
            ):
                raise ContractError(
                    "Cannot resume across agent, company, backend or workspace boundaries."
                )
            expected_policy = self.write_policy.sha256 if self.write_policy else ""
            if state.get("write_policy_sha256", "") != expected_policy:
                raise ContractError("Cannot resume with a changed or missing host write policy.")
            if state["status"] == "completed":
                return state
            snapshot = state.get("core_snapshot")
            if "core_snapshot" in state and (not isinstance(snapshot, str) or len(snapshot) > self.limits["max_context_chars"]):
                raise ContractError("Persisted core_snapshot is invalid.")
            if snapshot is not None and self.core_snapshot is not None and snapshot != self.core_snapshot:
                raise ContractError("core_snapshot does not match the persisted run snapshot.")
            if "core_snapshot" not in state:
                state["core_snapshot"] = self.core_snapshot if self.core_snapshot is not None else self.catalog.core()
                if len(state["core_snapshot"]) > self.limits["max_context_chars"]:
                    raise ContractError("core_snapshot exceeds the context budget.")
            completed_actions = state.setdefault("completed_actions", [])
            if not _valid_completed_actions(completed_actions):
                raise ContractError("Persisted completed action history is invalid.")
            if state.get("status") != "awaiting_approval" and (approval_id or approval_decision):
                raise ContractError("No pending action matches this approval response.")
            if state.get("status") == "awaiting_approval":
                pending = state.get("pending_approval") or {}
                if not approval_id or approval_id != pending.get("id"):
                    raise ContractError("A matching approval_id is required to resume this tool approval.")
                if approval_decision not in {"approve", "reject"}:
                    raise ContractError("approval_decision must be approve or reject.")
                current_binding = binding(run_id=state["run_id"], agent=config["id"], company=config["company"],
                                          workspace=str(self.workspace), backend=self.backend.name,
                                          model=getattr(self.backend, "approval_identity", getattr(self.backend, "model", None)),
                                          fingerprint=workspace_fingerprint(self.workspace) if approval_decision == "approve"
                                          else pending.get("binding", {}).get("workspace_fingerprint", ""),
                                          write_policy_sha256=self.write_policy.sha256 if self.write_policy else "")
                validate_binding(pending, current_binding)
                replay_sha256 = pending.get("replay_sha256")
                if (not isinstance(replay_sha256, str)
                        or len(replay_sha256) != 64
                        or any(char not in "0123456789abcdef" for char in replay_sha256)):
                    raise ContractError("Approval canonical replay identity is missing or invalid.")
                if (approval_decision == "approve"
                        and replay_sha256 != replay_action_digest(
                            pending.get("tool"), pending.get("arguments"), self.workspace
                        )):
                    raise ContractError("Approval canonical replay identity changed before execution.")
                if approval_decision == "approve" and self.write_policy is not None:
                    self.write_policy.authorize_action(
                        self.workspace, pending.get("tool"), pending.get("arguments")
                    )
                state.setdefault("approvals", []).append({"id": approval_id, "tool": pending.get("tool"),
                    "arguments": pending.get("arguments"), "action_sha256": pending.get("action_sha256"),
                    "replay_sha256": replay_sha256,
                    "continuation_sha256": pending.get("continuation_sha256"),
                    "decision": approval_decision, "at": time.time()})
                state["pending_approval"] = None
                if approval_decision == "reject":
                    state["status"] = "blocked"
                    state["summary"] = f"Tool approval rejected: {pending.get('tool')}"
                    state["in_flight"] = None
                    save(path, state, writer=self.state_writer)
                    return state
                state["approval_resume"] = pending.get("continuation")
                state["approved_action"] = {
                    "tool": pending.get("tool"),
                    "arguments": pending.get("arguments"),
                    "action_sha256": pending.get("action_sha256"),
                    "replay_sha256": replay_sha256,
                }
                state["status"] = "running"
                state["in_flight"] = {"kind": "worker-resume"}
                # Continue below without requiring unrelated feedback.
            elif state["in_flight"] and not acknowledge:
                raise ContractError(
                    "Interrupted call may have changed files. Inspect the workspace; resume with --acknowledge-interruption and --feedback."
                )
            if state.get("status") != "awaiting_approval" and not approval_decision:
                # An acknowledged unknown outcome is replanned from evidence, never replayed.
                state.pop("approval_resume", None)
            if not feedback.strip() and not approval_decision:
                raise ContractError(
                    "Resuming requires --feedback with the new evidence or resolved blocker."
                )
            if feedback.strip():
                state["feedback"].append(feedback)
                # A manual recovery is a new bounded attempt. Preserve the
                # cumulative failure audit, but do not make an exhausted prior
                # attempt impossible to recover after its blocker is resolved.
                failure_baseline = state["failures"]
            state["in_flight"] = None
            # The operator may have changed files while the run was paused.
            # Recheck written work instead of trusting a review from before the pause.
            if state["dirty"]:
                state["reviewed"] = False
        else:
            if approval_id or approval_decision:
                raise ContractError("A new run cannot consume an approval response.")
            state = {
                "version": 1,
                "run_id": directory.name,
                "agent": config["id"],
                "company": config["company"],
                "backend": self.backend.name,
                "workspace": str(self.workspace),
                "task": task,
                "status": "running",
                "summary": "",
                "history": [],
                "feedback": [],
                "in_flight": None,
                "steps": 0,
                "failures": 0,
                "elapsed_seconds": 0.0,
                "dirty": False,
                "reviewed": False,
                "require_approvals": self.require_approvals,
                "write_policy_sha256": self.write_policy.sha256 if self.write_policy else "",
                "pending_approval": None,
                "approvals": [],
                "completed_actions": [],
                "core_snapshot": self.core_snapshot if self.core_snapshot is not None else self.catalog.core(),
            }
        if path.exists() and state.get("require_approvals"):
            # A persisted approval policy is sticky across process restarts;
            # callers cannot resume a gated run with approvals disabled.
            self.require_approvals = True
        elif path.exists() and self.require_approvals:
            state["require_approvals"] = True
        if self.require_approvals and not getattr(self.backend, "supports_action_approvals", False):
            raise ContractError("This backend cannot enforce the persisted approval policy.")
        started = time.monotonic()
        elapsed_before = state["elapsed_seconds"]

        def checkpoint() -> None:
            nonlocal reservation
            state["elapsed_seconds"] = round(
                elapsed_before + time.monotonic() - started, 3
            )
            save(path, state, writer=self.state_writer)
            # Coordination files remain rollbackable until this first durable
            # checkpoint succeeds.  After that point the run has an identity
            # that must survive later execution failures and resume attempts.
            if reservation is not None:
                reservation.commit()
                reservation = None

        def timeout() -> float:
            remaining = self.limits["max_seconds"] - (
                elapsed_before + time.monotonic() - started
            )
            if remaining <= 0:
                raise ContractError(
                    "Wall-time budget exhausted. Raise the limit deliberately before resuming."
                )
            return min(self.limits["call_timeout"], remaining)

        def context() -> dict:
            result = {
                "task": state["task"],
                "feedback": state["feedback"],
                "history": state["history"],
                "catalog": self.catalog.summary(),
                "core": state["core_snapshot"],
                "workspace": str(self.workspace),
                "require_review": config["require_review"],
                "review_pending": state["dirty"] and not state["reviewed"],
                "steps_remaining": self.limits["max_steps"] - state["steps"],
                "require_approvals": bool(state.get("require_approvals", False)),
                "completed_actions": state.get("completed_actions", []),
            }
            if self.write_policy is not None:
                # Trusted, JSON-safe guidance for planning. Enforcement still uses
                # the host-created WritePolicy instance attached only to worker context.
                result["write_policy_summary"] = {
                    "sha256": self.write_policy.sha256,
                    "allowed_files": list(self.write_policy.paths),
                }
            if state.get("approval_resume"):
                result["approval_resume"] = state["approval_resume"]
                result["approved_action"] = state.get("approved_action")
            if (
                len(json.dumps(result, ensure_ascii=False))
                > self.limits["max_context_chars"]
            ):
                raise ContractError(
                    "Context budget exhausted; split the task rather than silently discard evidence."
                )
            return result

        state["status"] = "running"
        checkpoint()
        try:
            resumed_worker = bool(state.get("approval_resume"))
            while True:
                if not resumed_worker and state["steps"] >= self.limits["max_steps"]:
                    raise ContractError("Step budget exhausted.")
                if state["failures"] - failure_baseline >= self.limits["max_failures"]:
                    raise ContractError(
                        "Failure budget exhausted; investigate the blocker."
                    )
                if resumed_worker:
                    resumed_worker = False
                    record = state["history"][-1]
                    decision = record["decision"]
                else:
                    state["steps"] += 1
                    state["in_flight"] = {"kind": "planner", "step": state["steps"]}
                    checkpoint()
                    decision = self.backend.decide(context(), timeout())
                    validate(decision, "decision")
                    state["in_flight"] = None
                    record = {"step": state["steps"], "decision": decision}
                    state["history"].append(record)
                if decision["action"] == "blocked":
                    state.update(status="blocked", summary=decision["task"])
                    break
                if decision["action"] == "finish":
                    reports = [h["report"] for h in state["history"] if "report" in h]
                    completion_error = None
                    if (
                        not reports
                        or reports[-1]["status"] != "success"
                        or not reports[-1]["evidence"]
                    ):
                        completion_error = "Completion requires a successful, evidence-bearing final report."
                    elif (
                        config["require_review"]
                        and state["dirty"]
                        and not state["reviewed"]
                    ):
                        completion_error = "Completion refused: changes require a successful subsequent review."
                    if completion_error is not None:
                        # A rejected finish has no external effects. Let the planner
                        # repair the evidence gap, within the existing failure budget.
                        record["completion_rejected"] = completion_error
                        state["failures"] += 1
                        checkpoint()
                        continue
                    state.update(status="completed", summary=decision["task"])
                    break
                instructions = self.catalog.selected(
                    decision["role"], decision["skills"]
                )
                role = self.catalog.roles[decision["role"]]
                if role["sandbox"] == "workspace-write":
                    state.update(dirty=True, reviewed=False)
                state["in_flight"] = {"kind": "worker", "decision": decision}
                checkpoint()
                ctx = context()
                ctx["instructions"] = instructions
                ctx["sandbox"] = role["sandbox"]
                if (
                    len(json.dumps(ctx, ensure_ascii=False))
                    > self.limits["max_context_chars"]
                ):
                    raise ContractError("Selected skills exceed context budget.")
                if self.mutation_writer is not None:
                    ctx["mutation_writer"] = self.mutation_writer
                if self.write_policy is not None:
                    ctx["write_policy"] = self.write_policy
                def request_approval(tool: str, arguments: dict, continuation: dict) -> None:
                    if self.write_policy is not None:
                        self.write_policy.authorize_action(self.workspace, tool, arguments)
                    approval = {
                        "id": new_id(), "tool": tool, "arguments": arguments,
                        "action_sha256": action_digest(tool, arguments),
                        "replay_sha256": replay_action_digest(
                            tool, arguments, self.workspace
                        ),
                        "continuation_sha256": continuation_digest(continuation),
                        "binding": binding(run_id=state["run_id"], agent=config["id"], company=config["company"],
                            workspace=str(self.workspace), backend=self.backend.name,
                            model=getattr(self.backend, "approval_identity", getattr(self.backend, "model", None)),
                            fingerprint=workspace_fingerprint(self.workspace),
                            write_policy_sha256=self.write_policy.sha256 if self.write_policy else ""),
                        "continuation": continuation,
                    }
                    state["pending_approval"] = approval
                    # The proposal is durable in pending_approval; no tool is in flight.
                    state["in_flight"] = None
                    state["status"] = "awaiting_approval"
                    checkpoint()
                    raise ApprovalRequired(approval)
                def record_completed_action(entry: dict) -> None:
                    completed = state.setdefault("completed_actions", [])
                    candidate = [*completed, entry]
                    if not _valid_completed_actions(candidate):
                        raise ContractError("Backend returned an invalid or exhausted completed action history.")
                    completed.append(entry)
                    checkpoint()
                ctx["request_approval"] = request_approval
                ctx["record_completed_action"] = record_completed_action
                state.pop("approval_resume", None)
                state.pop("approved_action", None)
                checkpoint()
                execution_route = getattr(self.backend, "execution_route", None)
                if execution_route is not None:
                    record["model_route"] = execution_route(decision, ctx)
                    checkpoint()
                report = self.backend.execute(decision, ctx, timeout())
                validate(report, "report")
                for artifact in report["artifacts"]:
                    self._verify_artifact(artifact, timeout())
                record["report"] = report
                state.pop("approval_resume", None)
                state["in_flight"] = None
                if report["status"] != "success":
                    state["failures"] += 1
                    if role["can_review"]:
                        state["reviewed"] = False
                elif role["can_review"] and report["evidence"]:
                    state["reviewed"] = True
                checkpoint()
        except ApprovalRequired:
            # request_approval checkpointed the exact continuation already.
            return state
        except (Exception, KeyboardInterrupt) as exc:
            state.update(status="blocked", summary=f"{type(exc).__name__}: {exc}")
            # Keep an uncertain in-flight call; never auto-replay an operation with unknown effects.
        finally:
            checkpoint()
        return state
