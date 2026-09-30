"""Skills are Markdown instructions, never implicitly imported Python plugins."""

from __future__ import annotations

from pathlib import Path

import yaml

from .contracts import ContractError, inside, read_json, slug, validate


def skill_metadata(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ContractError(f"Missing skill frontmatter: {path}")
    try:
        end = lines.index("---", 1)
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except (ValueError, yaml.YAMLError) as exc:
        raise ContractError(f"Invalid skill frontmatter: {path}") from exc
    if not isinstance(metadata, dict):
        raise ContractError(f"Expected skill metadata object: {path}")
    name = slug(metadata.get("name"))
    description = metadata.get("description")
    if (
        name != path.parent.name
        or not isinstance(description, str)
        or not 1 <= len(description.strip()) <= 1024
    ):
        raise ContractError(f"Invalid skill name/description: {path}")
    if not "\n".join(lines[end + 1 :]).strip():
        raise ContractError(f"Empty skill instructions: {path}")
    return {"name": name, "description": description}


class Catalog:
    def __init__(self, agent_dir: Path):
        self.root = agent_dir.resolve()
        self.config = read_json(self.root / "agent.json")
        validate(self.config, "agent")
        self.roles = self.config["roles"]
        self.skills = {}
        for role, data in self.roles.items():
            slug(role)
            path = inside(self.root, data["instructions"])
            if not path.is_file():
                raise ContractError(f"Missing role instructions: {path}")
            for name in data["skills"]:
                slug(name)
                path = inside(self.root, f".agents/skills/{name}/SKILL.md")
                if not path.is_file():
                    raise ContractError(f"Missing skill: {name}")
                self.skills[name] = skill_metadata(path)
        for name in ("STATUS.md", "AGENTS.md", "SOUL.md", "WORKFLOW.md"):
            if not inside(self.root, name).is_file():
                raise ContractError(f"Missing core instructions: {name}")
        if self.config["require_review"] and not any(
            r["can_review"] for r in self.roles.values()
        ):
            raise ContractError("A review-gated agent requires a reviewing role.")
        if any(
            r["can_review"] and r["sandbox"] != "read-only" for r in self.roles.values()
        ):
            raise ContractError("Review roles must use the read-only sandbox.")

    def summary(self) -> dict:
        return {"roles": self.roles, "skills": list(self.skills.values())}

    def selected(self, role: str, skills: list[str]) -> str:
        if role not in self.roles:
            raise ContractError(f"Unknown role: {role}")
        if not set(skills).issubset(self.roles[role]["skills"]):
            raise ContractError(f"Skill not assigned to role {role}.")
        parts = [
            inside(self.root, self.roles[role]["instructions"]).read_text(
                encoding="utf-8"
            )
        ]
        for name in skills:
            path = inside(self.root, f".agents/skills/{name}/SKILL.md")
            parts.append(
                f"Skill: {name}; relative references resolve from {path.parent}\n"
                + path.read_text(encoding="utf-8")
            )
        return "\n\n".join(parts)

    def core(self) -> str:
        return "\n\n".join(
            inside(self.root, p).read_text(encoding="utf-8")
            for p in ("STATUS.md", "AGENTS.md", "SOUL.md", "WORKFLOW.md")
        )
