"""Context assembly for reusable automation agents.

The core idea is that the orchestrator should not know project details.
Project packs provide the rules, knowledge, and workflows that are loaded
into a structured context object here.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import re


@dataclass
class SkillSpec:
    name: str
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    output: str = ""
    body: str = ""
    references: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None


@dataclass
class ConnectorSpec:
    name: str
    url_env: str = ""
    description: str = ""
    tools_enabled: list[str] = field(default_factory=list)
    required: bool = False


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
    skills: dict[str, SkillSpec] = field(default_factory=dict)
    steering_examples: list[dict[str, Any]] = field(default_factory=list)
    connectors: list[ConnectorSpec] = field(default_factory=list)


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
        context.skills = self._load_skills(project_dir / "skills")
        context.steering_examples = self._load_steering_examples(project_dir / "steering-examples.json")
        context.connectors = self._load_connectors(project_dir / "connectors.yaml")
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

    def _load_skills(self, directory: Path) -> dict[str, SkillSpec]:
        result: dict[str, SkillSpec] = {}
        if not directory.exists():
            return result
        for skill_path in sorted(directory.glob("*/SKILL.md")):
            skill_dir = skill_path.parent
            body = skill_path.read_text(encoding="utf-8")
            header, text = self._split_frontmatter(body)
            name = header.get("name", skill_dir.name)
            references = self._load_skill_references(skill_dir / "references")
            triggers_raw = header.get("triggers", "")
            triggers = self._parse_list(triggers_raw)
            spec = SkillSpec(
                name=name,
                description=header.get("description", ""),
                triggers=triggers,
                output=header.get("output", ""),
                body=text.strip(),
                references=references,
                source_path=skill_path,
            )
            result[name] = spec
        return result

    def _load_skill_references(self, references_dir: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        if not references_dir.exists():
            return result
        for path in sorted(references_dir.glob("*.md")):
            result[path.stem] = path.read_text(encoding="utf-8")
        return result

    def _load_steering_examples(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _load_connectors(self, path: Path) -> list[ConnectorSpec]:
        if not path.exists():
            return []
        try:
            import yaml  # type: ignore[import-untyped]
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except ImportError:
            data = self._parse_connectors_without_yaml(path)
        except Exception:
            return []

        raw_list = data.get("connectors") or []
        result: list[ConnectorSpec] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            result.append(ConnectorSpec(
                name=str(item.get("name", "")),
                url_env=str(item.get("url_env", "")),
                description=str(item.get("description", "")),
                tools_enabled=list(item.get("tools_enabled") or []),
                required=bool(item.get("required", False)),
            ))
        return result

    def _parse_connectors_without_yaml(self, path: Path) -> dict[str, Any]:
        """Minimal YAML parser for connectors.yaml when PyYAML is not installed."""
        text = path.read_text(encoding="utf-8")
        if "connectors: []" in text or not re.search(r"- name:", text):
            return {"connectors": []}
        return {"connectors": []}

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

    def _parse_list(self, raw: str) -> list[str]:
        if not raw:
            return []
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        return [item.strip(" '\"") for item in raw.split(",") if item.strip()]
