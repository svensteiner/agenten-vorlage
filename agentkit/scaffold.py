"""Generate independent agent packs without forking the shared runtime."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from .catalog import Catalog, skill_metadata
from .contracts import ContractError, LIBRARY, read_json, slug
from .storage import save


def create(
    target: Path,
    profile: str,
    agent_id: str,
    company: str,
    *,
    storage_writer: Callable[[Path, bytes], None] | None = None,
) -> Path:
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
    def write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if storage_writer is None:
            path.write_bytes(data)
        else:
            storage_writer(path, data)

    target.mkdir(parents=True)
    try:
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
            write_bytes(target / path.name, text.encode("utf-8"))
        for role in roles:
            source = LIBRARY / "roles" / f"{role}.md"
            write_bytes(target / "roles" / source.name, source.read_bytes())
        skills = {"dynamic-workflow"} | {
            name for role in roles.values() for name in role["skills"]
        }
        for name in sorted(skills):
            source_root = LIBRARY / "skills" / name
            for source in source_root.rglob("*"):
                relative = source.relative_to(source_root)
                destination = target / ".agents" / "skills" / name / relative
                if source.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    write_bytes(destination, source.read_bytes())
        write_bytes(
            target / ".gitignore",
            b".runs/\n.agentkit.lock\nworkspace/.agentkit.lock\n.env\n.env.*\n",
        )
        save(target / "agent.json", config, writer=storage_writer)
        Catalog(target)
        return target
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise


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
