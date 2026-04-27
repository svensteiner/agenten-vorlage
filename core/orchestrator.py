"""High-level orchestration for the reusable automation template."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .context import ContextBuilder, ProjectContext
from .dispatcher import Dispatcher, DispatchResult
from .governance import GovernanceDecision, GovernancePolicy
from .memory import MemoryStore
from .planner import Plan, Planner
from .subagents import SubagentManager
from .runtime import RuntimeStore
from .verifier import VerificationResult, Verifier


@dataclass
class RunResult:
    task: str
    success: bool
    plan: Plan | None = None
    dispatch: DispatchResult | None = None
    verification: VerificationResult | None = None
    governance: GovernanceDecision | None = None
    context: ProjectContext | None = None
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

    def run(self, task: str, *, tools: dict[str, Any] | None = None) -> RunResult:
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
                metadata={"status": "blocked"},
            )

        dispatch_results: list[DispatchResult] = []
        verification_results: list[VerificationResult] = []
        outputs: list[str] = []
        evidence: list[str] = []
        subagent_runs: list[dict[str, Any]] = []
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

            dispatch = self.dispatcher.dispatch(step, tools=tools)
            dispatch_results.append(dispatch)
            outputs.append(dispatch.output)
            evidence.append(self._evidence_item(step.tool or step.action, step.id, dispatch.output))

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
            metadata={
                "dispatch_count": len(dispatch_results),
                "verification_count": len(verification_results),
                "subagent_count": len(subagent_runs),
                "subagents": subagent_runs,
                "evidence_count": len(evidence),
                "outputs": outputs,
            },
        )

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
