"""Planning primitives for automation tasks."""

from dataclasses import dataclass, field
from typing import Any

from .context import ProjectContext


@dataclass
class PlanStep:
    id: str
    action: str
    description: str
    tool: str | None = None
    input: str | None = None
    requires_human: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    task: str
    steps: list[PlanStep] = field(default_factory=list)
    tool_hint: str | None = None
    workflow_hint: str | None = None
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


class Planner:
    """Turns a task into a small executable plan.

    The initial implementation is intentionally conservative. Real planning
    logic can be added by project packs or by plugging in an LLM-powered brain.
    """

    def draft(self, task: str, context: str = "", project: ProjectContext | None = None) -> Plan:
        plan = Plan(task=task)
        normalized = task.lower()

        manifest = (project.manifest if project else {}) or {}
        workflow_manifest = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        workflow_name = workflow_manifest.get("name")
        workflow_steps = workflow_manifest.get("steps") or []

        if workflow_name:
            plan.workflow_hint = str(workflow_name)
            plan.notes.append(f"Project workflow: {workflow_name}")

        if project and project.workflows:
            for name, text in project.workflows.items():
                if name.replace("_", " ") in normalized or name.replace("-", " ") in normalized:
                    plan.workflow_hint = name
                    plan.notes.append(f"Matched workflow: {name}")
                    if text:
                        plan.notes.append(text.splitlines()[0][:120])
                    break

        if workflow_steps:
            normalized_steps = [str(step).strip() for step in workflow_steps if str(step).strip()]
            for index, step_text in enumerate(normalized_steps, start=1):
                if index == 1:
                    action = "inspect"
                elif index == len(normalized_steps):
                    action = "verify"
                else:
                    action = "execute"
                plan.steps.append(
                    PlanStep(
                        id=f"step_{index}",
                        action=action,
                        description=step_text,
                        metadata={"workflow": plan.workflow_hint or "main", "source": "manifest"},
                    )
                )
        else:
            plan.steps.append(
                PlanStep(
                    id="step_1",
                    action="inspect",
                    description="Understand the task and identify the required workflow.",
                )
            )
            if plan.workflow_hint:
                plan.steps.append(
                    PlanStep(
                        id="step_2",
                        action="execute_workflow",
                        description=f"Follow project workflow '{plan.workflow_hint}'.",
                        metadata={"workflow": plan.workflow_hint},
                    )
                )
            else:
                plan.steps.append(
                    PlanStep(
                        id="step_2",
                        action="execute",
                        description="Execute the smallest safe action that advances the task.",
                    )
                )
            plan.steps.append(
                PlanStep(
                    id="step_3",
                    action="verify",
                    description="Verify the output and decide whether the task can be closed.",
                )
            )
        if context:
            plan.notes.append("Context provided to planner.")
        if project and project.soul_text:
            plan.notes.append("Project soul loaded.")
        if manifest.get("purpose"):
            plan.notes.append(f"Purpose: {manifest['purpose']}")
        if manifest.get("success_criteria"):
            plan.notes.append(f"Success: {manifest['success_criteria']}")
        plan.confidence = 0.7 if workflow_steps else (0.5 if plan.workflow_hint else 0.3)
        return plan
