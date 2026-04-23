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


class SubagentManager:
    """Loads project subagents and executes the best match."""

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)

    def load(self, context: ProjectContext | None = None) -> dict[str, SubagentSpec]:
        context = context or ProjectContext(project_root=self.project_root)
        result: dict[str, SubagentSpec] = {}
        for name, body in (context.subagents or {}).items():
            spec = self._parse_spec(name, body)
            result[spec.name] = spec
        return result

    def select(self, task: str, *, context: ProjectContext | None = None, workflow_hint: str = "") -> SubagentSpec | None:
        specs = self.load(context)
        if not specs:
            return None

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
        system = "\n\n".join(
            part for part in [
                spec.system_prompt.strip(),
                context.soul_text.strip(),
            ] if part
        )
        user = f"""Task: {task}

Project: {context.project_name}

Extra context:
{extra_context or '(none)'}
"""
        text = brain.complete(system or "You are a helpful subagent.", user, temperature=0.3, max_tokens=700, use_fast=True)
        if not text:
            text = (
                f"[{spec.name}] Fallback summary for task: {task}\n"
                f"Focus: {', '.join(spec.keywords) if spec.keywords else 'general'}"
            )
        return {
            "subagent": spec.name,
            "description": spec.description,
            "output": text.strip(),
        }

    def _parse_spec(self, fallback_name: str, body: str) -> SubagentSpec:
        header, text = self._split_frontmatter(body)
        name = header.get("name", fallback_name)
        description = header.get("description", "")
        keywords = self._parse_keywords(header.get("keywords", ""))
        if not keywords:
            keywords = self._default_keywords(name)
        return SubagentSpec(name=name, description=description, keywords=keywords, system_prompt=text.strip())

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
