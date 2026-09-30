"""Generate independent agent packs without forking the shared runtime."""

from __future__ import annotations

import shutil
from pathlib import Path

from .catalog import Catalog, skill_metadata
from .contracts import ContractError, LIBRARY, read_json, slug
from .storage import save


def create(target: Path, profile: str, agent_id: str, company: str) -> Path:
    slug(agent_id)
    profiles = read_json(LIBRARY / "profiles.json")
    if profile not in profiles:
        raise ContractError(f"Unknown profile: {profile}")
    if not company.strip() or len(company) > 100 or any(ch in company for ch in "\r\n"):
        raise ContractError(
            "Company must be a single nonempty line of at most 100 characters."
        )
    target = target.absolute()
    if target.exists():
        raise ContractError(f"Target already exists; choose a new directory: {target}")
    template = profiles[profile]
    all_roles = read_json(LIBRARY / "roles.json")
    roles = {name: all_roles[name] for name in template["roles"]}
    config = {
        "version": 1,
        "id": agent_id,
        "company": company,
        "profile": profile,
        "require_review": template["require_review"],
        "limits": {
            "max_steps": 12,
            "max_failures": 3,
            "max_seconds": 1800,
            "call_timeout": 300,
            "max_context_chars": 100000,
        },
        "roles": roles,
    }
    target.mkdir(parents=True)
    (target / "roles").mkdir()
    (target / "workspace").mkdir()
    for path in (LIBRARY / "base").iterdir():
        text = path.read_text(encoding="utf-8")
        for key, value in {
            "AGENT_ID": agent_id,
            "COMPANY": company,
            "PROFILE": profile,
        }.items():
            text = text.replace("{{" + key + "}}", value)
        (target / path.name).write_text(text, encoding="utf-8")
    for role in roles:
        shutil.copy2(LIBRARY / "roles" / f"{role}.md", target / "roles" / f"{role}.md")
    skills = {"dynamic-workflow"} | {
        name for role in roles.values() for name in role["skills"]
    }
    for name in sorted(skills):
        shutil.copytree(LIBRARY / "skills" / name, target / ".agents" / "skills" / name)
    (target / ".gitignore").write_text(
        ".runs/\n.agentkit.lock\nworkspace/.agentkit.lock\n.env\n.env.*\n",
        encoding="utf-8",
    )
    save(target / "agent.json", config)
    Catalog(target)
    return target


def add_skill(agent_dir: Path, source: Path, role: str) -> str:
    catalog = Catalog(agent_dir)
    if role not in catalog.roles:
        raise ContractError(f"Unknown role: {role}")
    metadata = skill_metadata(source / "SKILL.md")
    # A local reviewed bundle only. Never run installers or follow symlinks from downloads.
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
        raise ContractError("Skill bundles may not contain symlinks.")
    target = catalog.root / ".agents" / "skills" / metadata["name"]
    if target.exists():
        raise ContractError(
            "Skill already installed. Edit its role assignment in agent.json."
        )
    shutil.copytree(source, target)
    catalog.config["roles"][role]["skills"].append(metadata["name"])
    save(catalog.root / "agent.json", catalog.config)
    Catalog(catalog.root)
    return metadata["name"]
