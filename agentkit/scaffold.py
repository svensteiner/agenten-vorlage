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
    roles: list[str] | None = None,
    extra_skills: list[tuple[str, str]] | None = None,
    require_review: bool | None = None,
    storage_writer: Callable[[Path, bytes], None] | None = None,
) -> Path:
    if require_review is not None and not isinstance(require_review, bool):
        raise ContractError("require_review must be a boolean.")
    if not isinstance(profile, str):
        raise ContractError("profile must be a profile name.")
    slug(agent_id)
    profiles = read_json(LIBRARY / "profiles.json")
    all_roles = read_json(LIBRARY / "roles.json")
    if roles is not None:
        if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
            raise ContractError("roles must be a list of role names.")
        if not roles:
            raise ContractError("A composition must include at least one role.")
        for role in roles:
            slug(role)
        if len(roles) != len(set(roles)):
            raise ContractError("Duplicate role names are not allowed.")
        for role in roles:
            if role not in all_roles:
                raise ContractError(f"Unknown role: {role}")
        template_roles = roles
        template_review = (
            any(all_roles[r]["can_review"] for r in roles)
            if require_review is None
            else require_review
        )
        profile = "custom"
    else:
        if profile not in profiles:
            raise ContractError(f"Unknown profile: {profile}")
        template = profiles[profile]
        template_roles = template["roles"]
        template_review = (
            template["require_review"] if require_review is None else require_review
        )
    has_write_role = any(
        all_roles[role]["sandbox"] == "workspace-write" for role in template_roles
    )
    has_reviewer = any(all_roles[role]["can_review"] for role in template_roles)
    if has_write_role and not has_reviewer:
        raise ContractError("A writable composition requires a reviewing role.")
    if has_write_role and not template_review:
        raise ContractError("A writable composition cannot disable review.")
    if extra_skills is not None and not isinstance(extra_skills, list):
        raise ContractError("extra_skills must be a list of role/skill pairs.")
    extras = extra_skills or []
    seen_extras: set[tuple[str, str]] = set()
    for assignment in extras:
        if (
            not isinstance(assignment, (tuple, list))
            or len(assignment) != 2
            or any(not isinstance(value, str) for value in assignment)
        ):
            raise ContractError("Each extra skill must be a ROLE, SKILL pair.")
        role, skill = assignment
        slug(role)
        slug(skill)
        if role not in template_roles:
            raise ContractError(f"Skill assigned to missing role: {role}")
        if role not in all_roles:
            raise ContractError(f"Unknown role: {role}")
        if (role, skill) in seen_extras:
            raise ContractError(f"Duplicate skill assignment: {role}:{skill}")
        seen_extras.add((role, skill))
        skill_source = LIBRARY / "skills" / skill
        if not skill_source.is_dir():
            raise ContractError(f"Unknown built-in skill: {skill}")
        skill_metadata(skill_source / "SKILL.md")
    for role in template_roles:
        role_path = LIBRARY / "roles" / f"{role}.md"
        if not role_path.is_file():
            raise ContractError(f"Missing built-in role instructions: {role}")
    all_selected_skills = {"dynamic-workflow"}
    all_selected_skills.update(
        skill for role in template_roles for skill in all_roles[role]["skills"]
    )
    all_selected_skills.update(skill for _, skill in extras)
    for skill in all_selected_skills:
        skill_source = LIBRARY / "skills" / skill
        if not skill_source.is_dir():
            raise ContractError(f"Unknown built-in skill: {skill}")
        skill_metadata(skill_source / "SKILL.md")
    if template_review and not any(
        all_roles[r]["can_review"] and all_roles[r]["sandbox"] == "read-only"
        for r in template_roles
    ):
        raise ContractError(
            "A review-gated composition requires a read-only reviewing role."
        )
    if not company.strip() or len(company) > 100 or any(ch in company for ch in "\r\n"):
        raise ContractError(
            "Company must be a single nonempty line of at most 100 characters."
        )
    target = target.absolute()
    if target.exists():
        raise ContractError(f"Target already exists; choose a new directory: {target}")
    selected_roles = {name: dict(all_roles[name]) for name in template_roles}
    for name, data in selected_roles.items():
        data["skills"] = list(data["skills"])
    for role, skill in extras:
        if skill not in selected_roles[role]["skills"]:
            selected_roles[role]["skills"].append(skill)
    config = {
        "version": 1,
        "id": agent_id,
        "company": company,
        "profile": profile,
        "require_review": template_review,
        "limits": {
            "max_steps": 12,
            "max_failures": 3,
            "max_seconds": 1800,
            "call_timeout": 300,
            "max_context_chars": 100000,
        },
        "roles": selected_roles,
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
        for role in selected_roles:
            source = LIBRARY / "roles" / f"{role}.md"
            write_bytes(target / "roles" / source.name, source.read_bytes())
        skills = {"dynamic-workflow"} | {
            name for role in selected_roles.values() for name in role["skills"]
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
