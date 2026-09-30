"""Offline integration contracts. No API requests, registration or publication."""

from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog
from .contracts import ContractError


def issue_to_task(issue: dict, *, company_id: str, agent_id: str) -> str:
    if not company_id or not agent_id or issue.get("companyId") != company_id:
        raise ContractError("Paperclip company binding mismatch.")
    if issue.get("assigneeAgentId") != agent_id:
        raise ContractError("Issue is not assigned to this agent.")
    if issue.get("status") not in {"todo", "backlog", "blocked", "in_progress"}:
        raise ContractError("Issue is not actionable.")
    if not isinstance(issue.get("title"), str) or not issue["title"].strip():
        raise ContractError("Issue title is required.")
    return f"Paperclip issue {issue.get('id', 'unknown')}\n{issue['title']}\n\n{issue.get('description') or ''}"


def result_to_update(state: dict) -> dict:
    if state.get("status") not in {"completed", "blocked"}:
        raise ContractError("Only a terminal local result can be mapped to Paperclip.")
    return {
        "status": "done" if state["status"] == "completed" else "blocked",
        "comment": f"AgentKit run {state['run_id']}: {state['summary']}",
    }


def native_prompt(agent_dir: Path, task: str) -> str:
    catalog = Catalog(agent_dir)
    if not task.strip():
        raise ContractError("Task must not be empty.")
    return (
        f"Use the agent pack at {catalog.root}. Read STATUS.md first, then AGENTS.md, SOUL.md and WORKFLOW.md.\n"
        f"Load {catalog.root / '.agents/skills/dynamic-workflow/SKILL.md'}.\n"
        "Use the native harness for tools, planning, sessions and bounded delegation. "
        "Choose roles and load only their relevant assigned SKILL.md files, using explicit "
        "pack paths if the native discovery root differs. Workspace: the pack's workspace/ directory. "
        "Keep pack configuration unchanged. Do not create recursive delegation trees. "
        "Follow the configured acceptance/review rules and give the artifacts, verification "
        "and limitations. Do not publish/deploy/send external messages from this task. "
        "The Python engine is not running: its locks, timeouts and schema checks do not apply. "
        "Host-enforced budgets and permissions must already be configured in the native harness.\n\n"
        "Available roles/skills:\n"
        + json.dumps(catalog.summary(), ensure_ascii=False, indent=2)
        + "\n\nTask:\n"
        + task
    )
