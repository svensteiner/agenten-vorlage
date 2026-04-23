"""Small CLI for the reusable automation-agent template.

Commands:
  - setup: interactive onboarding that generates a new project pack
  - init: same as setup, but explicit for creating a new agent
  - status: show current template/project status
  - run: execute the existing agent loop

The goal is to provide a Hermes/ADK-style entry point: setup first, then run.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any


ROOT = Path(__file__).parent
DEFAULT_OUTPUT_ROOT = ROOT / "instances"


@dataclass
class OnboardingAnswers:
    project_name: str
    customer_or_team: str
    main_problem: str
    success_criteria: str
    non_goals: str
    role: str
    language: str
    tone: str
    domain_expertise: str
    hard_limits: str
    trigger: str
    inputs: str
    steps: str
    validation: str
    escalation: str
    tools: list[str]
    require_approval_for: str
    never_do: str
    retry_policy: str
    quality_threshold: str
    keep_forever: str
    keep_temporarily: str
    remember_between_runs: str


BEGINNER_QUESTIONS = [
    ("project_name", "Projektname", "Wie heißt das Projekt?"),
    ("main_problem", "Was soll er tun?", "Was soll der Agent ganz konkret erledigen?"),
    ("customer_or_team", "Für wen?", "Für wen ist der Agent gedacht?"),
    ("tools", "Welche Tools?", "Welche Systeme oder Dateien braucht er? Schreibe sie mit Kommas getrennt."),
    ("success_criteria", "Woran merkt man Erfolg?", "Woran merkst du, dass es gut gelaufen ist?"),
    ("trigger", "Wann starten?", "Was startet den Workflow?"),
    ("require_approval_for", "Was braucht Freigabe?", "Wofür braucht der Agent immer Freigabe?"),
]

ADVANCED_QUESTIONS = [
    ("role", "Rolle", "Welche Rolle soll der Agent haben?"),
    ("language", "Sprache", "Welche Sprache soll er verwenden?"),
    ("tone", "Ton", "Wie soll er klingen?"),
    ("domain_expertise", "Wissen", "Was sollte der Agent immer wissen?"),
    ("hard_limits", "Grenzen", "Was darf er niemals alleine entscheiden?"),
    ("inputs", "Eingaben", "Welche Eingaben bekommt er typischerweise?"),
    ("steps", "Schritte", "Wie läuft der Standard-Workflow ab?"),
    ("validation", "Prüfen", "Wie soll das Ergebnis geprüft werden?"),
    ("escalation", "Hilfe holen", "Wann soll er einen Menschen fragen?"),
    ("non_goals", "Nicht-Ziele", "Was soll er nicht versuchen?"),
    ("never_do", "Nie tun", "Welche Aktionen sind tabu?"),
    ("retry_policy", "Fehler", "Wie soll er mit Fehlern umgehen?"),
    ("quality_threshold", "Qualität", "Was ist gut genug?"),
    ("keep_forever", "Merken", "Was soll er sich dauerhaft merken?"),
    ("keep_temporarily", "Kurz merken", "Was braucht er nur während des Laufs?"),
    ("remember_between_runs", "Zwischen Läufen merken", "Was soll er zwischen Läufen behalten?"),
]

DEFAULT_ANSWERS = {
    "role": "automation agent",
    "language": "Deutsch",
    "tone": "klar und freundlich",
    "domain_expertise": "Projekt- und Prozesswissen kommt aus den Projektdateien.",
    "hard_limits": "Keine destruktiven Aktionen ohne Freigabe.",
    "inputs": "Task, Kontext, Projektdateien und ggf. Tool-Ausgaben.",
    "steps": "Verstehen, planen, prüfen, ausführen, verifizieren.",
    "validation": "Erst prüfen, dann als erledigt markieren.",
    "escalation": "Wenn etwas unklar, riskant oder destruktiv ist.",
    "non_goals": "Keine unnötige Komplexität oder Experimente im Produktivpfad.",
    "never_do": "Nie ohne Freigabe löschen, überschreiben oder massenhaft ändern.",
    "retry_policy": "Einmal sauber retryen, dann eskalieren.",
    "quality_threshold": "7/10",
    "keep_forever": "Rollenregeln, Prozesse und wichtige Projektkonventionen.",
    "keep_temporarily": "Zwischenzustände, offene Aufgaben und aktuelle Ergebnisse.",
    "remember_between_runs": "Letzte Aktionen, Learnings und wiederkehrende Muster.",
}


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "agent"


def _collect_answers(mode: str = "beginner") -> OnboardingAnswers:
    values: dict[str, Any] = {}

    sets = [BEGINNER_QUESTIONS]
    if mode == "full":
        sets.append(ADVANCED_QUESTIONS)

    for question_set in sets:
        for key, label, prompt in question_set:
            if key == "tools":
                raw = _ask(f"{label} - {prompt}")
                values[key] = [item.strip() for item in raw.split(",") if item.strip()]
            else:
                values[key] = _ask(f"{label} - {prompt}")

    if mode != "full":
        refine = _ask("Möchtest du noch optionale Feindetails ergänzen? (j/n)", "n").lower()
        if refine in {"j", "ja", "y", "yes"}:
            for key, label, prompt in ADVANCED_QUESTIONS:
                if key in values:
                    continue
                values[key] = _ask(f"{label} - {prompt}")

    for key, default in DEFAULT_ANSWERS.items():
        values.setdefault(key, default)

    values.setdefault("customer_or_team", "")
    values.setdefault("success_criteria", "")
    values.setdefault("main_problem", "")
    values.setdefault("trigger", "")
    values.setdefault("tools", [])
    values.setdefault("require_approval_for", "Löschen, Überschreiben, Massenänderungen")

    if isinstance(values.get("tools"), str):
        values["tools"] = [item.strip() for item in str(values["tools"]).split(",") if item.strip()]

    return OnboardingAnswers(**values)


def _render_soul(ans: OnboardingAnswers) -> str:
    tools_lines = "\n".join(f"- {tool}" for tool in ans.tools) if ans.tools else "- [add tools]"
    return dedent(
        f"""\
        # {ans.project_name} - SOUL

        ## Identity

        - Project: {ans.project_name}
        - Customer / Team: {ans.customer_or_team}
        - Role: {ans.role}
        - Language: {ans.language}
        - Tone: {ans.tone}

        ## Mission

        - Main problem: {ans.main_problem}
        - Success criteria: {ans.success_criteria}
        - Non-goals: {ans.non_goals}

        ## Domain knowledge

        - Expertise: {ans.domain_expertise}

        ## Boundaries

        - Hard limits: {ans.hard_limits}
        - Approval required for: {ans.require_approval_for}
        - Never do: {ans.never_do}

        ## Workflow

        - Trigger: {ans.trigger}
        - Inputs: {ans.inputs}
        - Steps: {ans.steps}
        - Validation: {ans.validation}
        - Escalation: {ans.escalation}

        ## Tools

        {tools_lines}

        ## Quality

        - Retry policy: {ans.retry_policy}
        - Quality threshold: {ans.quality_threshold}

        ## Memory

        - Keep forever: {ans.keep_forever}
        - Keep temporarily: {ans.keep_temporarily}
        - Remember between runs: {ans.remember_between_runs}
        """
    ).strip() + "\n"


def _render_config(ans: OnboardingAnswers) -> dict[str, Any]:
    quality = 7
    try:
        quality = int("".join(ch for ch in ans.quality_threshold if ch.isdigit()) or "7")
    except ValueError:
        pass
    return {
        "project_name": ans.project_name,
        "agent_name": _slugify(ans.project_name),
        "mode": "development",
        "quality_threshold": quality,
        "max_retries": 2,
        "max_actions_per_day": 50,
        "challenge_enabled": True,
        "proactive": True,
        "memory_scope": ["core", "project"],
        "human_approval_required": [item.strip() for item in ans.require_approval_for.split(",") if item.strip()],
    }


def _render_workflow(ans: OnboardingAnswers) -> str:
    return dedent(
        f"""\
        # Main Workflow

        ## Trigger

        {ans.trigger}

        ## Inputs

        {ans.inputs}

        ## Steps

        {ans.steps}

        ## Validation

        {ans.validation}

        ## Escalation

        {ans.escalation}
        """
    ).strip() + "\n"


def _render_project_brief(ans: OnboardingAnswers) -> str:
    tools = "\n".join(f"- {tool}" for tool in ans.tools) if ans.tools else "- none"
    return dedent(
        f"""\
        # Project Brief

        ## Summary
        - Project: {ans.project_name}
        - Customer / Team: {ans.customer_or_team}
        - Main problem: {ans.main_problem}
        - Success criteria: {ans.success_criteria}

        ## Agent
        - Role: {ans.role}
        - Language: {ans.language}
        - Tone: {ans.tone}
        - Domain expertise: {ans.domain_expertise}

        ## Workflow
        - Trigger: {ans.trigger}
        - Inputs: {ans.inputs}
        - Steps: {ans.steps}
        - Validation: {ans.validation}
        - Escalation: {ans.escalation}

        ## Tools
        {tools}

        ## Safety
        - Approval required for: {ans.require_approval_for}
        - Never do: {ans.never_do}
        - Retry policy: {ans.retry_policy}
        - Quality threshold: {ans.quality_threshold}

        ## Memory
        - Keep forever: {ans.keep_forever}
        - Keep temporarily: {ans.keep_temporarily}
        - Remember between runs: {ans.remember_between_runs}
        """
    ).strip() + "\n"


def _write_template_project(target_dir: Path, ans: OnboardingAnswers) -> None:
    project_dir = target_dir / "project"
    docs_dir = target_dir / "docs"
    workflows_dir = project_dir / "workflows"
    tools_dir = project_dir / "tools"
    policies_dir = project_dir / "policies"
    knowledge_dir = project_dir / "knowledge"
    memory_dir = project_dir / "memory"
    agents_dir = project_dir / "agents"

    for directory in [
        project_dir,
        docs_dir,
        workflows_dir,
        tools_dir,
        policies_dir,
        knowledge_dir,
        memory_dir,
        agents_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    (project_dir / "SOUL.md").write_text(_render_soul(ans), encoding="utf-8")
    (project_dir / "config.json").write_text(json.dumps(_render_config(ans), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (project_dir / "AGENTS.md").write_text(
        dedent(
            f"""\
            ---
            name: { _slugify(ans.project_name) }
            description: Project-specific operating instructions for {ans.project_name}.
            ---

            # Project Instructions

            - Follow the workflow in `project/workflows/main.md`.
            - Use tools only for approved actions.
            - Escalate when safety or quality rules are hit.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "onboarding.md").write_text(_render_project_brief(ans), encoding="utf-8")
    (workflows_dir / "main.md").write_text(_render_workflow(ans), encoding="utf-8")
    (tools_dir / "README.md").write_text(
        "# Tools\n\nAdd project-specific tools here.\n", encoding="utf-8"
    )
    (policies_dir / "README.md").write_text(
        f"# Policies\n\n{ans.never_do}\n\nApproval required for: {ans.require_approval_for}\n", encoding="utf-8"
    )
    (knowledge_dir / "README.md").write_text(
        f"# Knowledge\n\n{ans.domain_expertise}\n", encoding="utf-8"
    )
    (memory_dir / "README.md").write_text(
        f"# Memory\n\n{ans.keep_forever}\n\n{ans.remember_between_runs}\n", encoding="utf-8"
    )
    (agents_dir / "README.md").write_text(
        "# Subagents\n\nAdd specialized subagents here when needed.\n", encoding="utf-8"
    )
    (docs_dir / "project-brief.md").write_text(_render_project_brief(ans), encoding="utf-8")


def cmd_setup(args: argparse.Namespace) -> int:
    print("\nAgent setup")
    print("-----------")
    if args.full:
        print("Vollständiger Modus: alle Fragen für mehr Präzision.\n")
        answers = _collect_answers(mode="full")
    else:
        print("Kurzer Einstieg: nur die wichtigsten Fragen. Du kannst danach Feindetails ergänzen.\n")
        answers = _collect_answers(mode="beginner")
    output_root = Path(args.output or DEFAULT_OUTPUT_ROOT)
    project_slug = _slugify(answers.project_name)
    target_dir = output_root / project_slug

    if target_dir.exists() and not args.force:
        confirm = _ask(f"{target_dir} exists. Overwrite? (yes/no)", "no").lower()
        if confirm not in {"y", "yes"}:
            print("Aborted.")
            return 1

    _write_template_project(target_dir, answers)
    print(f"\nCreated project pack at: {target_dir}")
    print("Next:")
    print(f"  cd {target_dir}")
    print("  read project/onboarding.md")
    print("  adapt project/tools/ as needed")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    print("Template status")
    print("---------------")
    print(f"Core: {ROOT / 'core'}")
    print(f"Project pack: {ROOT / 'project'}")
    print(f"Docs: {ROOT / 'docs'}")
    print(f"Current template branch: repository root")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from agent import main as agent_main

    if args.extra:
        import sys

        sys.argv = ["agent.py", *args.extra]
    agent_main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent", description="Reusable automation agent template CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Interactive onboarding that generates a new project pack")
    setup.add_argument("--output", help="Output root for generated agent packs")
    setup.add_argument("--force", action="store_true", help="Overwrite existing output without asking")
    setup.add_argument("--full", action="store_true", help="Ask the full advanced question set")
    setup.set_defaults(func=cmd_setup)

    init_cmd = sub.add_parser("init", help="Alias for setup")
    init_cmd.add_argument("--output", help="Output root for generated agent packs")
    init_cmd.add_argument("--force", action="store_true", help="Overwrite existing output without asking")
    init_cmd.add_argument("--full", action="store_true", help="Ask the full advanced question set")
    init_cmd.set_defaults(func=cmd_setup)

    run = sub.add_parser("run", help="Run the current agent implementation")
    run.add_argument("extra", nargs=argparse.REMAINDER, help="Extra arguments passed through to agent.py")
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", help="Show template status")
    status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
