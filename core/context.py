"""Context assembly for reusable automation agents.

The core idea is that the orchestrator should not know project details.
Project packs provide the rules, knowledge, and workflows that are loaded
into a structured context object here.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class ProjectContext:
    project_root: Path
    project_name: str = "default-project"
    manifest: dict[str, Any] = field(default_factory=dict)
    soul_text: str = ""
    agents_text: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    knowledge: dict[str, str] = field(default_factory=dict)
    policies: dict[str, str] = field(default_factory=dict)
    workflows: dict[str, str] = field(default_factory=dict)
    subagents: dict[str, str] = field(default_factory=dict)
    memory: dict[str, str] = field(default_factory=dict)


class ContextBuilder:
    """Loads project-specific files into a structured context."""

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)

    def build(self) -> ProjectContext:
        project_dir = self.project_root / "project"
        context = ProjectContext(project_root=self.project_root)
        context.project_name = self._load_project_name(project_dir)
        context.manifest = self._read_json(project_dir / "manifest.json")
        context.soul_text = self._read_text(project_dir / "SOUL.md")
        context.agents_text = self._read_text(project_dir / "AGENTS.md")
        context.config = self._read_json(project_dir / "config.json")
        context.knowledge = self._load_knowledge(project_dir / "knowledge")
        context.policies = self._load_markdown_tree(project_dir / "policies")
        context.workflows = self._load_markdown_tree(project_dir / "workflows")
        context.subagents = self._load_agent_tree(project_dir / "agents")
        context.memory = self._load_markdown_tree(project_dir / "memory")
        return context

    def _load_project_name(self, project_dir: Path) -> str:
        config = self._read_json(project_dir / "config.json")
        manifest = self._read_json(project_dir / "manifest.json")
        if manifest.get("project_name"):
            return str(manifest["project_name"])
        return str(config.get("project_name", self.project_root.name))

    def _read_text(self, path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _read_json(self, path: Path) -> dict[str, Any]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _load_markdown_tree(self, directory: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        if not directory.exists():
            return result
        for path in sorted(directory.glob("*.md")):
            if path.stem.lower() == "readme":
                continue
            result[path.stem] = path.read_text(encoding="utf-8")
        return result

    def _load_agent_tree(self, directory: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        if not directory.exists():
            return result
        for path in sorted(directory.glob("**/AGENT.md")):
            if path.stem.lower() == "agent" and path.parent.name.lower() == "readme":
                continue
            result[path.parent.name] = path.read_text(encoding="utf-8")
        for path in sorted(directory.glob("**/AGENTS.md")):
            if path.stem.lower() == "agents" and path.parent.name.lower() == "readme":
                continue
            if path.parent.name not in result:
                result[path.parent.name] = path.read_text(encoding="utf-8")
        return result

    def _load_knowledge(self, directory: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        if not directory.exists():
            return result
        for path in sorted(directory.glob("*.md")):
            if path.stem.lower() == "readme":
                continue
            result[path.stem] = path.read_text(encoding="utf-8")
        return result
