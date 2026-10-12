"""Small explicit CLI: create, inspect, validate, run, resume, and export prompts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .backends import CodexBackend, DeepSeekBackend, DemoBackend, codex_readiness
from .catalog import Catalog
from .contracts import ContractError, LIBRARY, read_json
from .engine import Engine
from .integrations import native_prompt
from .scaffold import add_skill, create


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="agentkit", description="Skill-based company agents with dynamic workflows"
    )
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("profiles", help="List available specializations")
    commands.add_parser(
        "doctor", help="Check local runtime and Codex availability; no model calls"
    )
    init = commands.add_parser("init", help="Create a self-contained agent pack")
    init.add_argument("target", type=Path)
    init.add_argument("--profile")
    init.add_argument("--role", action="append", dest="roles")
    init.add_argument("--skill", action="append", default=[], metavar="ROLE:SKILL")
    init.add_argument("--name", default="developer")
    init.add_argument("--company", default="AI_Studioxyz")
    for name in ("inspect", "validate"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--agent", type=Path, required=True)
    skill = commands.add_parser(
        "add-skill", help="Copy a reviewed local skill bundle and assign it to a role"
    )
    skill.add_argument("--agent", type=Path, required=True)
    skill.add_argument("--source", type=Path, required=True)
    skill.add_argument("--role", required=True)
    prompt = commands.add_parser(
        "native-prompt", help="Print a task prompt for DeepSeek Harness/native hosts"
    )
    prompt.add_argument("--agent", type=Path, required=True)
    prompt.add_argument("--task", required=True)
    for name in ("run", "resume"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--agent", type=Path, required=True)
        cmd.add_argument(
            "--workspace", type=Path, help="Defaults to the pack's workspace directory"
        )
        cmd.add_argument("--backend", choices=("demo", "codex", "deepseek"), default="demo")
        cmd.add_argument("--require-approvals", action="store_true", help="Pause before supported backend write/test actions; always enabled for Codex and DeepSeek")
        cmd.add_argument(
            "--model",
            help="Optional model override; Codex defaults to gpt-5.6-luna with low reasoning; DeepSeek uses its provider default",
        )
        if name == "run":
            cmd.add_argument("--task", required=True)
        else:
            cmd.add_argument("--run-dir", type=Path, required=True)
            cmd.add_argument("--feedback", default="")
            cmd.add_argument("--approval-id", default="")
            cmd.add_argument("--approval-decision", choices=("approve", "reject"), default="")
            cmd.add_argument("--acknowledge-interruption", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    # Windows can inherit a legacy console code page even when the CLI is
    # launched with redirected pipes.  JSON results may contain Unicode from
    # workflow instructions (for example, the ``→`` arrow), so make the
    # process streams explicitly UTF-8 before argparse or any output runs.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parser().parse_args(argv)
    try:
        if args.command == "profiles":
            result = read_json(LIBRARY / "profiles.json")
        elif args.command == "doctor":
            result = {
                "python": sys.version.split()[0],
                "codex": codex_readiness(),
                "deepseek": {
                    "api_key_configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
                    "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                    "native_harness": "see docs/DEEPSEEK.md",
                },
            }
        elif args.command == "init":
            if args.roles and args.profile is not None:
                raise ContractError("--profile cannot be combined with --role.")
            assignments = []
            for item in args.skill:
                role, separator, skill_name = item.partition(":")
                if not separator or not role or not skill_name:
                    raise ContractError("--skill must use ROLE:SKILL.")
                assignments.append((role, skill_name))
            result = {
                "created": str(
                    create(
                        args.target,
                        args.profile if args.profile is not None else "developer",
                        args.name,
                        args.company,
                        roles=args.roles,
                        extra_skills=assignments,
                    )
                )
            }
        elif args.command in {"validate", "inspect"}:
            catalog = Catalog(args.agent)
            result = {"valid": True, "agent": catalog.config["id"]}
            if args.command == "inspect":
                result.update(catalog.summary())
        elif args.command == "add-skill":
            result = {"installed": add_skill(args.agent, args.source, args.role)}
        elif args.command == "native-prompt":
            print(native_prompt(args.agent, args.task))
            return 0
        else:
            catalog = Catalog(args.agent)
            has_worker = any(
                role["sandbox"] == "workspace-write" and not role["can_review"]
                for role in catalog.roles.values()
            )
            has_reviewer = any(role["can_review"] for role in catalog.roles.values())
            if args.backend == "demo" and not (has_worker and has_reviewer):
                raise ContractError(
                    "The demo fixture requires one workspace-writing worker and one read-only reviewer."
                )
            if args.backend == "demo":
                backend = DemoBackend()
            else:
                backend = {"codex": CodexBackend, "deepseek": DeepSeekBackend}[args.backend](args.model)
            workspace = args.workspace or args.agent / "workspace"
            require_approvals = args.backend in {"codex", "deepseek"} or args.require_approvals
            engine = Engine(args.agent, workspace, backend, require_approvals=require_approvals)
            if args.command == "run":
                result = engine.run(args.task)
            else:
                result = engine.run(
                    "",
                    run_dir=args.run_dir,
                    feedback=args.feedback,
                    acknowledge_interruption=args.acknowledge_interruption,
                    approval_id=args.approval_id,
                    approval_decision=args.approval_decision,
                )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "completed" else 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(
            json.dumps({"status": "error", "summary": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
