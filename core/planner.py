"""Planning primitives for automation tasks."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

import brain

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

    The planner prefers an LLM-generated plan when a model is configured, then
    falls back to deterministic rules so the template remains runnable offline.
    """

    def draft(
        self,
        task: str,
        context: str = "",
        project: ProjectContext | None = None,
        tools: dict[str, Any] | None = None,
    ) -> Plan:
        scheduled_status = self._draft_scheduled_status(task, project=project)
        if scheduled_status is not None:
            return scheduled_status
        if self._uses_deterministic_kmu_workflow(project):
            return self._draft_with_rules(
                task, context=context, project=project, tools=tools
            )
        llm_plan = self._draft_with_llm(
            task, context=context, project=project, tools=tools
        )
        if llm_plan and llm_plan.steps:
            return llm_plan
        return self._draft_with_rules(
            task, context=context, project=project, tools=tools
        )

    @staticmethod
    def _uses_deterministic_kmu_workflow(project: ProjectContext | None) -> bool:
        manifest = (project.manifest if project else {}) or {}
        workflow = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        return isinstance(workflow, dict) and workflow.get("name") == "kmu-controlling"

    def _draft_scheduled_status(
        self, task: str, *, project: ProjectContext | None
    ) -> Plan | None:
        """Turn trusted scheduler stop signals into a deterministic no-tool plan."""
        signal: dict[str, Any] | None = None
        for line in task.splitlines():
            if not line.startswith("SCHEDULER_SIGNAL:"):
                continue
            try:
                parsed = json.loads(line.removeprefix("SCHEDULER_SIGNAL:").strip())
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict):
                signal = parsed
        if signal is None or signal.get("reason") != "missing_data":
            return None

        raw_groups = signal.get("missing_required_groups", [])
        group_ids = [
            str(group["id"])
            for group in raw_groups
            if isinstance(group, dict)
            and isinstance(group.get("id"), str)
            and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", group["id"])
        ]
        group_note = f": {', '.join(group_ids)}" if group_ids else ""
        manifest = (project.manifest if project else {}) or {}
        workflow = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        workflow_name = workflow.get("name") if isinstance(workflow, dict) else None
        metadata = {
            "source": "scheduler",
            "status": "missing_data",
            "missing_required_groups": group_ids,
        }
        return Plan(
            task=task,
            workflow_hint=str(workflow_name) if workflow_name else None,
            confidence=1.0,
            notes=["Deterministic missing-data stop; LLM planning skipped."],
            steps=[
                PlanStep(
                    id="missing_data_status",
                    action="status",
                    description=(
                        f"Scheduled status missing_data: required input groups "
                        f"are incomplete{group_note}. "
                        "KPI computation and external actions remain paused."
                    ),
                    metadata=dict(metadata),
                ),
                PlanStep(
                    id="missing_data_wait",
                    action="wait",
                    description=(
                        "Wait for the required inputs and resume only after the "
                        "scheduler validates every required group."
                    ),
                    metadata=dict(metadata),
                ),
            ],
        )

    def _draft_with_rules(
        self,
        task: str,
        context: str = "",
        project: ProjectContext | None = None,
        tools: dict[str, Any] | None = None,
    ) -> Plan:
        plan = Plan(task=task)
        normalized = task.lower()
        tools = tools or {}

        manifest = (project.manifest if project else {}) or {}
        workflow_manifest = (
            manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        )
        workflow_name = workflow_manifest.get("name")
        workflow_steps = workflow_manifest.get("steps") or []

        if workflow_name:
            plan.workflow_hint = str(workflow_name)
            plan.notes.append(f"Project workflow: {workflow_name}")

        if project and project.workflows:
            for name, text in project.workflows.items():
                if (
                    name.replace("_", " ") in normalized
                    or name.replace("-", " ") in normalized
                ):
                    plan.workflow_hint = name
                    plan.notes.append(f"Matched workflow: {name}")
                    if text:
                        plan.notes.append(text.splitlines()[0][:120])
                    break

        if workflow_steps:
            normalized_steps = [
                str(step).strip() for step in workflow_steps if str(step).strip()
            ]
            for index, step_text in enumerate(normalized_steps, start=1):
                if index == 1:
                    action = "inspect"
                elif index == len(normalized_steps):
                    action = "verify"
                else:
                    action = "execute"
                if action == "execute":
                    tool_name, tool_input = self._guess_tool(task, step_text, tools)
                else:
                    tool_name, tool_input = None, None
                plan.steps.append(
                    PlanStep(
                        id=f"step_{index}",
                        action=action,
                        description=step_text,
                        tool=tool_name,
                        input=tool_input,
                        requires_human=self._looks_risky(task, step_text),
                        metadata={
                            "workflow": plan.workflow_hint or "main",
                            "source": "manifest",
                        },
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
        plan.confidence = (
            0.74 if workflow_steps else (0.55 if plan.workflow_hint else 0.35)
        )
        return plan

    def _draft_with_llm(
        self,
        task: str,
        context: str = "",
        project: ProjectContext | None = None,
        tools: dict[str, Any] | None = None,
    ) -> Plan | None:
        tools = tools or {}
        tool_specs = [
            {
                "name": name,
                "description": getattr(tool, "description", ""),
            }
            for name, tool in sorted(tools.items())
        ]
        manifest = (project.manifest if project else {}) or {}
        system = "\n\n".join(
            part
            for part in [
                project.soul_text if project else "",
                "You are the planning layer of an automation agent. Return only valid JSON.",
            ]
            if part
        )
        skill_hints = self._build_skill_hints(task, project)
        steering = self._build_steering_hints(task, project)
        user = {
            "task": task,
            "context": context,
            "project": {
                "name": project.project_name if project else "",
                "manifest": manifest,
                "workflows": list((project.workflows if project else {}).keys()),
                "skills": list((project.skills if project else {}).keys()),
                "approval_required_for": manifest.get("approval_required_for", []),
            },
            "available_tools": tool_specs,
            "skill_hint": skill_hints,
            "steering_examples": steering,
            "required_schema": {
                "workflow_hint": "string or null",
                "skill_hint": "matching skill name or null",
                "confidence": "0.0-1.0",
                "steps": [
                    {
                        "id": "step_1",
                        "action": "inspect | execute | verify | notify | use_tool | use_skill",
                        "description": "specific instruction",
                        "tool": "one available tool name or null",
                        "input": "exact tool input or null",
                        "requires_human": False,
                    }
                ],
                "notes": ["short note"],
            },
            "rules": [
                "Use a tool when the task requires external state, files, notification, or web data.",
                "If a matching skill is available, include a 'use_skill' step before execution.",
                "Do not invent tool names.",
                "Mark requires_human=true for delete, overwrite, bulk changes, secrets, payments, or irreversible actions.",
                "Keep the plan to 2-5 concrete steps.",
                "Only write-enabled subagents (leaf writers) may produce persistent output.",
            ],
        }
        configured_model = (
            manifest.get("model", {}).get("planner")
            if isinstance(manifest.get("model"), dict)
            else None
        )
        raw = brain.complete(
            system,
            json.dumps(user, ensure_ascii=False),
            temperature=0.2,
            max_tokens=900,
            model=configured_model
            if isinstance(configured_model, str) and configured_model.strip()
            else None,
        )
        parsed = self._parse_json(raw)
        if not parsed:
            return None

        plan = Plan(
            task=task,
            workflow_hint=parsed.get("workflow_hint")
            or manifest.get("workflow", {}).get("name"),
            confidence=float(parsed.get("confidence") or 0.78),
            notes=[str(note) for note in parsed.get("notes", []) if str(note).strip()],
        )
        if parsed.get("skill_hint"):
            plan.notes.append(f"Skill: {parsed['skill_hint']}")
        available = set(tools)
        for index, item in enumerate(parsed.get("steps", []), start=1):
            tool_name = item.get("tool")
            if tool_name not in available:
                tool_name = None
            description = str(
                item.get("description") or item.get("action") or f"Step {index}"
            ).strip()
            plan.steps.append(
                PlanStep(
                    id=str(item.get("id") or f"step_{index}"),
                    action=str(item.get("action") or "execute"),
                    description=description,
                    tool=tool_name,
                    input=item.get("input") if item.get("input") is not None else None,
                    requires_human=bool(item.get("requires_human"))
                    or self._looks_risky(task, description),
                    metadata={"source": "llm"},
                )
            )
        if not plan.notes and project and project.soul_text:
            plan.notes.append("Project soul loaded.")
        self._sanitize_plan(plan, task=task, project=project)
        return plan if plan.steps else None

    def _sanitize_plan(
        self, plan: Plan, *, task: str, project: ProjectContext | None
    ) -> None:
        """Remove common LLM planning artifacts before execution."""
        wants_notification = self._mentions_any(
            task,
            [
                "benachrichtig",
                "notify",
                "slack",
                "telegram",
                "meldung",
                "send notification",
            ],
        )
        sanitized: list[PlanStep] = []

        for step in plan.steps:
            if step.tool == "notify" and not wants_notification:
                continue

            if step.tool == "file" and step.input:
                step.input = self._repair_project_file_input(step.input, project)
                ok, reason = self._file_input_is_plausible(step.input, project)
                if not ok:
                    step.tool = None
                    step.input = None
                    if step.action == "use_tool":
                        step.action = "inspect"

            sanitized.append(step)

        non_verify = [step for step in sanitized if step.action != "verify"]
        verify = [step for step in sanitized if step.action == "verify"]
        plan.steps = non_verify + verify

    def _file_input_is_plausible(
        self, tool_input: str, project: ProjectContext | None
    ) -> tuple[bool, str]:
        if ":" not in tool_input:
            return False, "file input has no operation prefix"
        op, rest = tool_input.split(":", 1)
        op = op.strip().lower()
        path_text = rest.split("|", 1)[0].strip()
        if op in {"write", "append"}:
            return True, ""
        if op not in {"read", "list"}:
            return False, f"unknown file operation '{op}'"
        if not path_text:
            return True, ""
        root = project.project_root if project else Path.cwd()
        target = (root / path_text).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            return False, "path points outside the project"
        if not target.exists():
            return False, f"path does not exist: {path_text}"
        return True, ""

    def _repair_project_file_input(
        self, tool_input: str, project: ProjectContext | None
    ) -> str:
        if project is None or ":" not in tool_input:
            return tool_input
        op, rest = tool_input.split(":", 1)
        op = op.strip().lower()
        if op not in {"read", "list"}:
            return tool_input
        path_text = rest.split("|", 1)[0].strip()
        if not path_text or "/" in path_text or "\\" in path_text:
            return tool_input
        root = project.project_root.resolve()
        if (root / path_text).exists():
            return tool_input
        project_path = root / "project" / path_text
        if project_path.exists():
            return f"{op}:project/{path_text}"
        return tool_input

    def _mentions_any(self, text: str, needles: list[str]) -> bool:
        lowered = text.lower()
        return any(needle in lowered for needle in needles)

    def _guess_tool(
        self, task: str, step_text: str, tools: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        original_text = f"{task} {step_text}"
        lowered = original_text.lower()
        if "web_search" in tools and any(
            word in lowered for word in ["such", "recherch", "web", "aktuell", "latest"]
        ):
            return "web_search", task
        if "notify" in tools and any(
            word in lowered
            for word in ["benachrichtig", "notify", "slack", "telegram", "meldung"]
        ):
            return "notify", task
        # Narrow offline route for the packaged controlling workflow.  The
        # compute capability itself fails closed unless exactly one input is
        # present, so the planner never invents a customer file name.
        if (
            "compute" in tools
            and any(word in lowered for word in ["deterministic", "deterministisch"])
            and any(
                word in lowered
                for word in ["kpi", "account", "konto", "calculate", "berechn"]
            )
        ):
            return "compute", '{"operation":"kmu_report","source":"auto"}'
        if "report" in tools and "evidence-based management update" in lowered:
            return "report", '{"source":"auto"}'
        if "file" in tools:
            match = re.search(
                r"(?P<op>lies|read|liste|list)\s+(?P<path>[\w./\\-]+)",
                original_text,
                re.I,
            )
            if match:
                op = "read" if match.group("op").lower() in {"lies", "read"} else "list"
                return "file", f"{op}:{match.group('path')}"
        return None, None

    def _looks_risky(self, task: str, step_text: str) -> bool:
        text = f"{task} {step_text}".lower()
        risky_terms = [
            "delete",
            "löschen",
            "lösch",
            "loeschen",
            "loesch",
            "overwrite",
            "überschreib",
            "ueberschreib",
            "bulk",
            "massen",
            "secret",
            "api key",
            "zahlung",
            "payment",
            "deploy production",
        ]
        return any(term in text for term in risky_terms)

    def _build_skill_hints(
        self, task: str, project: ProjectContext | None
    ) -> dict[str, str] | None:
        if not project or not project.skills:
            return None
        task_lower = task.lower()
        for skill in project.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in task_lower:
                    return {
                        "name": skill.name,
                        "description": skill.description,
                        "output": skill.output,
                    }
        return None

    def _build_steering_hints(
        self, task: str, project: ProjectContext | None
    ) -> list[dict[str, Any]]:
        if not project or not project.steering_examples:
            return []
        task_lower = task.lower()
        matches: list[dict[str, Any]] = []
        for example in project.steering_examples:
            example_input = str(example.get("input", "")).lower()
            keywords = [w for w in example_input.split() if len(w) > 3]
            if any(kw in task_lower for kw in keywords):
                matches.append(
                    {
                        "input": example.get("input"),
                        "expected_skill": example.get("expected_skill"),
                        "expected_subagent": example.get("expected_subagent"),
                        "notes": example.get("notes"),
                    }
                )
        return matches[:3]

    def _parse_json(self, text: str) -> dict[str, Any]:
        if not text:
            return {}
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1)
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, TypeError):
            return {}
