"""Specialized subagent loading and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import brain

from .context import ProjectContext


@dataclass
class SubagentSpec:
    name: str
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    system_prompt: str = ""
    source_path: Path | None = None
    can_write: bool = False
    model: str | None = None


class SubagentManager:
    """Loads project subagents and executes the best match.

    Leaf-write pattern: subagents are read-only by default.
    Only subagents with 'can_write: true' in their AGENT.md frontmatter
    may produce persistent output. In a multi-subagent chain, exactly one
    leaf subagent should be write-enabled — typically the last one.
    """

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)

    def load(self, context: ProjectContext | None = None) -> dict[str, SubagentSpec]:
        context = context or ProjectContext(project_root=self.project_root)
        result: dict[str, SubagentSpec] = {}
        for name, body in (context.subagents or {}).items():
            spec = self._parse_spec(name, body)
            result[spec.name] = spec
        return result

    def leaf_writer(self, context: ProjectContext | None = None) -> SubagentSpec | None:
        """Return the designated leaf writer, or None if none is declared."""
        specs = self.load(context)
        writers = [s for s in specs.values() if s.can_write]
        if not writers:
            return None
        if len(writers) > 1:
            writers_by_name = sorted(writers, key=lambda s: s.name)
            return writers_by_name[-1]
        return writers[0]

    def select(self, task: str, *, context: ProjectContext | None = None, workflow_hint: str = "") -> SubagentSpec | None:
        specs = self.load(context)
        if not specs:
            return None

        skill_match = self._select_by_skill(task, context)
        if skill_match and skill_match in specs:
            return specs[skill_match]

        haystack = f"{task} {workflow_hint}".lower()
        scored: list[tuple[int, SubagentSpec]] = []
        for spec in specs.values():
            score = 0
            if spec.name.lower() in haystack:
                score += 5
            for keyword in spec.keywords:
                if keyword and keyword.lower() in haystack:
                    score += 2
            if score > 0:
                scored.append((score, spec))
        if not scored:
            return specs.get("researcher") or next(iter(specs.values()))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def run(
        self,
        spec: SubagentSpec,
        *,
        task: str,
        context: ProjectContext | None = None,
        extra_context: str = "",
    ) -> dict[str, Any]:
        context = context or ProjectContext(project_root=self.project_root)

        skill_context = self._build_skill_context(task, context)

        system = "\n\n".join(
            part for part in [
                spec.system_prompt.strip(),
                context.soul_text.strip(),
                skill_context,
            ] if part
        )
        user = f"""Task: {task}

Project: {context.project_name}

Extra context:
{extra_context or '(none)'}
"""
        model_override = spec.model or self._default_subagent_model(context)
        text = brain.complete(
            system or "You are a helpful subagent.",
            user,
            temperature=0.3,
            max_tokens=700,
            use_fast=True,
        )
        if not text:
            text = (
                f"[{spec.name}] Fallback summary for task: {task}\n"
                f"Focus: {', '.join(spec.keywords) if spec.keywords else 'general'}"
            )
        return {
            "subagent": spec.name,
            "description": spec.description,
            "output": text.strip(),
            "can_write": spec.can_write,
            "model": model_override,
        }

    def _select_by_skill(self, task: str, context: ProjectContext | None) -> str | None:
        if not context or not context.skills:
            return None
        task_lower = task.lower()
        for skill in context.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in task_lower:
                    if skill.body and "subagent" in skill.body.lower():
                        match = re.search(r"expected_subagent[:\s]+(\w+)", skill.body)
                        if match:
                            return match.group(1)
        return None

    def _build_skill_context(self, task: str, context: ProjectContext) -> str:
        if not context.skills:
            return ""
        task_lower = task.lower()
        for skill in context.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in task_lower:
                    parts = [f"## Active Skill: {skill.name}", skill.body]
                    for ref_name, ref_body in skill.references.items():
                        parts.append(f"### Reference: {ref_name}\n{ref_body}")
                    return "\n\n".join(parts)
        return ""

    def _default_subagent_model(self, context: ProjectContext | None) -> str:
        if not context:
            return "claude-haiku-4-5"
        manifest = context.manifest or {}
        model_config = manifest.get("model", {})
        if isinstance(model_config, dict):
            return str(model_config.get("subagents", "claude-haiku-4-5"))
        return "claude-haiku-4-5"

    def _parse_spec(self, fallback_name: str, body: str) -> SubagentSpec:
        header, text = self._split_frontmatter(body)
        name = header.get("name", fallback_name)
        description = header.get("description", "")
        keywords = self._parse_keywords(header.get("keywords", ""))
        if not keywords:
            keywords = self._default_keywords(name)
        can_write = header.get("can_write", "").lower() in {"true", "yes", "1"}
        model = header.get("model") or None
        return SubagentSpec(
            name=name,
            description=description,
            keywords=keywords,
            system_prompt=text.strip(),
            can_write=can_write,
            model=model,
        )

    def _split_frontmatter(self, body: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", body, re.S)
        if not match:
            return {}, body
        header_text, markdown = match.groups()
        header: dict[str, str] = {}
        for line in header_text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip().strip('"')
        return header, markdown

    def _parse_keywords(self, raw: str) -> list[str]:
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        return [item.strip(" '\"") for item in raw.split(",") if item.strip()]

    def _default_keywords(self, name: str) -> list[str]:
        lower = name.lower()
        defaults = {
            "researcher": ["research", "analyse", "investigate", "compare", "study"],
            "verifier": ["verify", "check", "audit", "validate", "review"],
            "reporter": ["report", "summarize", "document", "brief", "write"],
            "planner": ["plan", "workflow", "outline", "structure"],
        }
        return defaults.get(lower, [lower])
