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
        plan = self.planner.draft(task, context=task, project=context)
        governance = self.governance.allow(task)
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
        subagent_runs: list[dict[str, Any]] = []
        success = True

        for step in plan.steps:
            step_gov = self.governance.allow(step.action, risk="high" if step.requires_human else "low")
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
            if selected_subagent is not None and step.action in {"inspect", "execute_workflow", "execute"}:
                subagent_output = self.subagents.run(
                    selected_subagent,
                    task=task,
                    context=context,
                    extra_context="\n".join(plan.notes),
                )
                subagent_runs.append({"step": step.id, **subagent_output})
                outputs.append(subagent_output["output"])

            dispatch = self.dispatcher.dispatch(step, tools=tools)
            dispatch_results.append(dispatch)
            outputs.append(dispatch.output)
            verification = self.verifier.verify(dispatch.output)
            verification_results.append(verification)

            if not (dispatch.success and verification.passed):
                success = False
                break

        self.memory.save(
            "runs",
            {
                "task": task,
                "success": success,
                "workflow": plan.workflow_hint or "",
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
                "outputs": outputs,
            },
        )
