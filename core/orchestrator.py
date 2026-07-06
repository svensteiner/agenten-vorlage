"""High-level orchestration for the reusable automation template."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from .context import ContextBuilder, ProjectContext
from .dispatcher import Dispatcher, DispatchResult
from .governance import GovernanceDecision, GovernancePolicy
from .handoff import HandoffRouter, load_router
from .memory import MemoryStore
from .planner import Plan, Planner
from .subagents import SubagentManager
from .runtime import RuntimeStore
from .verifier import VerificationResult, Verifier
from .workers import WorkerRegistry, load_registry


@dataclass(frozen=True)
class RunSpec:
    """Run identity — the minimal carrier ADR-0019 §5.1 requires.

    A run is keyed ``(tenant_id, request_id)`` so it is attributable and, once
    the ``ExecutionBackend`` port is wired, resumable. When the CLI omits both,
    a local single-tenant run is synthesized so the offline path stays unbroken.
    """

    tenant_id: str
    request_id: str

    @property
    def run_id(self) -> str:
        return f"{self.tenant_id}:{self.request_id}"


@dataclass
class RunResult:
    task: str
    success: bool
    plan: Plan | None = None
    dispatch: DispatchResult | None = None
    verification: VerificationResult | None = None
    governance: GovernanceDecision | None = None
    context: ProjectContext | None = None
    run_spec: RunSpec | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """Coordinates planning, execution, verification, and persistence."""

    def __init__(
        self,
        project_root,
        *,
        planner: Planner | None = None,
        dispatcher: Dispatcher | None = None,
        verifier: Verifier | None = None,
        governance: GovernancePolicy | None = None,
        workers: WorkerRegistry | None = None,
        handoffs: HandoffRouter | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.context_builder = ContextBuilder(self.project_root)
        self.planner = planner or Planner()
        self.dispatcher = dispatcher or Dispatcher()
        self.verifier = verifier or Verifier()
        self.governance = governance or GovernancePolicy()
        self.subagents = SubagentManager(self.project_root)
        self.memory = MemoryStore(self.project_root / "state")
        self.runtime = RuntimeStore(self.project_root / "state" / "runtime")
        # Multi-agent primitives (ADR-0019): per-agent tool scope + allowlisted
        # handoffs. Defaulted from the project manifest so existing callers are
        # unaffected; the wiring below makes these two ratified gates *enforced*
        # at runtime rather than merely available (the Cycle-24 audit finding).
        manifest = self._load_manifest()
        self.workers = workers or load_registry(manifest)
        self.handoffs = handoffs or load_router(manifest)

    def _load_manifest(self) -> dict[str, Any]:
        path = self.project_root / "project" / "manifest.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def run(
        self,
        task: str,
        *,
        tools: dict[str, Any] | None = None,
        tenant: str | None = None,
        request_id: str | None = None,
    ) -> RunResult:
        run_spec = self._run_spec(task, tenant, request_id)
        context = self.context_builder.build()
        tools = tools or {}
        plan = self.planner.draft(task, context=task, project=context, tools=tools)
        governance = self.governance.allow(task, context=context, text=task)
        if not governance.allowed:
            return RunResult(
                task=task,
                success=False,
                plan=plan,
                governance=governance,
                context=context,
                run_spec=run_spec,
                metadata={"status": "blocked"},
            )

        dispatch_results: list[DispatchResult] = []
        verification_results: list[VerificationResult] = []
        outputs: list[str] = []
        evidence: list[str] = []
        subagent_runs: list[dict[str, Any]] = []
        handoffs_made: list[dict[str, Any]] = []
        success = True

        for step in plan.steps:
            step_gov = self.governance.allow(
                step.action,
                risk="high" if step.requires_human else "low",
                context=context,
                tool=step.tool,
                text=" ".join(part for part in [step.description, step.input or ""] if part),
            )
            if not step_gov.allowed:
                return RunResult(
                    task=task,
                    success=False,
                    plan=plan,
                    governance=step_gov,
                    context=context,
                    run_spec=run_spec,
                    metadata={"status": "step_blocked", "step": step.id},
                )

            selected_subagent = self.subagents.select(
                task,
                context=context,
                workflow_hint=plan.workflow_hint or "",
            )
            subagent_output = None
            if selected_subagent is not None and step.action in {"inspect", "execute_workflow", "execute"}:
                extra_context = self._execution_context(plan.notes, evidence)
                subagent_output = self.subagents.run(
                    selected_subagent,
                    task=task,
                    context=context,
                    extra_context=extra_context,
                )
                subagent_runs.append({"step": step.id, **subagent_output})
                outputs.append(subagent_output["output"])
                evidence.append(self._evidence_item("subagent", step.id, subagent_output["output"]))
                if not step.tool:
                    continue

            if step.action == "verify" and not step.tool:
                continue

            # ── Tool-scope gate (ADR-0019 O3/O5, WP-A1) ──────────────────────
            # The acting sub-agent's WorkerRegistry scope is enforced *in the
            # loop*, not merely available. When the orchestrator itself acts
            # (no sub-agent), governance covers it and no worker scope applies.
            acting_worker = self._acting_worker(selected_subagent, step)
            if acting_worker and step.tool:
                ok, reason = self.workers.check_permission(acting_worker, step.tool)
                if not ok:
                    return RunResult(
                        task=task,
                        success=False,
                        plan=plan,
                        governance=governance,
                        context=context,
                        run_spec=run_spec,
                        metadata={
                            "status": "tool_scope_blocked",
                            "step": step.id,
                            "worker": acting_worker,
                            "tool": step.tool,
                            "reason": reason,
                        },
                    )
            scoped_tools = self.workers.filter_tools(acting_worker, tools) if acting_worker else tools

            dispatch = self.dispatcher.dispatch(step, tools=scoped_tools)
            dispatch_results.append(dispatch)
            outputs.append(dispatch.output)
            evidence.append(self._evidence_item(step.tool or step.action, step.id, dispatch.output))

            # ── Handoff gate (ADR-0019 O4, WP-A2) ────────────────────────────
            # A handoff request embedded in a step's output is validated against
            # the allowlist + payload bound *before* control could transfer. An
            # invalid handoff is refused, never improvised.
            handoff = self.handoffs.extract(dispatch.output)
            if handoff is not None:
                ok, reason = self.handoffs.validate(handoff)
                if not ok:
                    return RunResult(
                        task=task,
                        success=False,
                        plan=plan,
                        governance=governance,
                        context=context,
                        run_spec=run_spec,
                        metadata={
                            "status": "handoff_refused",
                            "step": step.id,
                            "target": handoff.target,
                            "reason": reason,
                        },
                    )
                handoffs_made.append(
                    {"step": step.id, "target": handoff.target, "task": handoff.task}
                )

            if not dispatch.success:
                success = False
                break

        if outputs and success:
            final_verification = self.verifier.verify(
                "\n".join(outputs),
                task=task,
                step="final result",
                context=context,
            )
            verification_results.append(final_verification)
            success = final_verification.passed
            if not success and final_verification.improved_output:
                outputs.append(final_verification.improved_output)
                repair_verification = self.verifier.verify(
                    final_verification.improved_output,
                    task=task,
                    step="self-corrected final result",
                    context=context,
                )
                verification_results.append(repair_verification)
                success = repair_verification.passed

        self.memory.save(
            "runs",
            {
                "task": task,
                "run_id": run_spec.run_id,
                "tenant": run_spec.tenant_id,
                "success": success,
                "workflow": plan.workflow_hint or "",
                "plan_confidence": plan.confidence,
                "verification_score": verification_results[-1].score if verification_results else None,
                "steps": [
                    {
                        "id": step.id,
                        "action": step.action,
                        "tool": step.tool,
                        "requires_human": step.requires_human,
                    }
                    for step in plan.steps
                ],
                "output": "\n".join(outputs),
            },
        )
        self.runtime.write_heartbeat(context.project_name)

        return RunResult(
            task=task,
            success=success,
            plan=plan,
            dispatch=dispatch_results[-1] if dispatch_results else None,
            verification=verification_results[-1] if verification_results else None,
            governance=governance,
            context=context,
            run_spec=run_spec,
            metadata={
                "dispatch_count": len(dispatch_results),
                "verification_count": len(verification_results),
                "subagent_count": len(subagent_runs),
                "subagents": subagent_runs,
                "handoff_count": len(handoffs_made),
                "handoffs": handoffs_made,
                "evidence_count": len(evidence),
                "outputs": outputs,
            },
        )

    def _run_spec(self, task: str, tenant: str | None, request_id: str | None) -> RunSpec:
        """Synthesize run identity, keeping the offline CLI path unbroken.

        When the caller omits ``request_id`` it is derived deterministically from
        the task text (stable across retries of the same task); ``tenant``
        defaults to a local single-tenant marker.
        """
        rid = request_id or hashlib.sha256(task.encode("utf-8")).hexdigest()[:16]
        return RunSpec(tenant_id=tenant or "local", request_id=rid)

    def _acting_worker(self, selected_subagent, step) -> str | None:
        """Resolve the worker role whose tool scope governs this step.

        Priority: an explicit ``step.metadata["worker"]`` wins; otherwise the
        acting sub-agent maps to ``writer`` (leaf writer) or the least-privileged
        ``reader``. When no sub-agent is selected the orchestrator itself acts and
        no per-agent scope applies (governance is the gate there) — returns None.
        """
        explicit = step.metadata.get("worker") if getattr(step, "metadata", None) else None
        if explicit:
            return str(explicit)
        if selected_subagent is None:
            return None
        return "writer" if getattr(selected_subagent, "can_write", False) else "reader"

    def _execution_context(self, plan_notes: list[str], evidence: list[str]) -> str:
        parts: list[str] = []
        if plan_notes:
            parts.append("Plan notes:\n" + "\n".join(f"- {note}" for note in plan_notes[-5:]))
        if evidence:
            parts.append("Evidence from previous steps:\n" + "\n\n".join(evidence[-4:]))
            parts.append("Use only the evidence above for factual claims. Say what is missing instead of guessing.")
        return "\n\n".join(parts) if parts else "(none)"

    def _evidence_item(self, source: str, step_id: str, output: str) -> str:
        clipped = output.strip()
        if len(clipped) > 2500:
            clipped = clipped[:2500] + "\n[...truncated evidence]"
        return f"[{step_id} | {source}]\n{clipped}"
