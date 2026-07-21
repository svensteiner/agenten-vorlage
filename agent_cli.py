"""Small CLI for the reusable automation-agent template.

Commands:
  - setup: interactive onboarding that generates a new project pack, then
           runs a structural self-test so the user immediately sees that the
           generated project is internally consistent ("es funktioniert").
  - init:  same as setup, but explicit for creating a new agent
  - status: show current template/project status
  - run:   execute the existing agent loop
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any

from core.scheduling import ScheduledDecision, run_scheduled_cycle


ROOT = Path(__file__).parent
DEFAULT_OUTPUT_ROOT = ROOT / "instances"
PRESETS_ROOT = ROOT / "presets"


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
    recurring_tasks: list[str] = field(default_factory=list)
    external_sources: str = ""


@dataclass(frozen=True)
class SelfTestReport:
    """Result of the post-onboarding structural self-test.

    Immutable by design (frozen): the check functions build a fresh report,
    they never mutate an existing one.
    """

    passed: tuple[str, ...]
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


BEGINNER_QUESTIONS = [
    ("project_name", "Projektname", "Wie heißt das Projekt?"),
    ("main_problem", "Was soll er tun?", "Was soll der Agent ganz konkret erledigen?"),
    ("customer_or_team", "Für wen?", "Für wen ist der Agent gedacht?"),
    (
        "tools",
        "Welche Tools?",
        "Welche Systeme oder Dateien braucht er? (kommagetrennt, oder Enter für keine)",
    ),
    (
        "success_criteria",
        "Woran merkt man Erfolg?",
        "Woran merkst du, dass es gut gelaufen ist?",
    ),
    (
        "trigger",
        "Wann starten?",
        "Was startet den Workflow? (z.B. 'täglich um 8 Uhr' oder 'wenn ich eine E-Mail erhalte')",
    ),
    (
        "require_approval_for",
        "Was braucht Freigabe?",
        "Wofür braucht der Agent immer deine Freigabe? (z.B. 'Versenden, Löschen')",
    ),
    (
        "recurring_tasks",
        "Wiederkehrende Aufgaben",
        "Welche Aufgaben erledigt der Agent immer wieder? (kommagetrennt, z.B. 'Earnings analysieren, Meeting vorbereiten')",
    ),
    (
        "external_sources",
        "Datenquellen",
        "Welche externen Datenquellen braucht er? (z.B. 'Bloomberg, eigene Excel-Dateien', oder Enter für keine)",
    ),
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
    ("quality_threshold", "Qualität", "Was ist gut genug? (z.B. 7/10)"),
    ("keep_forever", "Merken", "Was soll er sich dauerhaft merken?"),
    ("keep_temporarily", "Kurz merken", "Was braucht er nur während des Laufs?"),
    (
        "remember_between_runs",
        "Zwischen Läufen merken",
        "Was soll er zwischen Läufen behalten?",
    ),
]

DEFAULT_ANSWERS = {
    "role": "automation agent",
    "language": "Deutsch",
    "tone": "klar und freundlich",
    "domain_expertise": "Projekt- und Prozesswissen kommt aus den Projektdateien.",
    "hard_limits": "Keine destruktiven Aktionen ohne Freigabe.",
    "inputs": "Task, Kontext, Projektdateien und ggf. Tool-Ausgaben.",
    "steps": "1. Verstehen\n2. Ausführen\n3. Prüfen",
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


# ─── Input helpers ────────────────────────────────────────────────────────────


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"  {prompt}{suffix}: ").strip()
    return value or default


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "agent"


def _split_items(text: str, fallback: list[str]) -> list[str]:
    items = [
        item.strip() for item in text.replace("\n", ",").split(",") if item.strip()
    ]
    return items or fallback


def _collect_answers(mode: str = "beginner") -> OnboardingAnswers:
    values: dict[str, Any] = {}

    sets = [BEGINNER_QUESTIONS]
    if mode == "full":
        sets.append(ADVANCED_QUESTIONS)

    for question_set in sets:
        for key, label, prompt in question_set:
            _print_question_label(label)
            if key in ("tools", "recurring_tasks"):
                raw = _ask(prompt)
                values[key] = [item.strip() for item in raw.split(",") if item.strip()]
            else:
                values[key] = _ask(prompt)

    if mode != "full":
        print()
        refine = _ask(
            "Möchtest du noch optionale Feindetails ergänzen? (j/n)", "n"
        ).lower()
        if refine in {"j", "ja", "y", "yes"}:
            for key, label, prompt in ADVANCED_QUESTIONS:
                if key in values:
                    continue
                _print_question_label(label)
                values[key] = _ask(prompt)

    for key, default in DEFAULT_ANSWERS.items():
        values.setdefault(key, default)

    values.setdefault("customer_or_team", "")
    values.setdefault("success_criteria", "")
    values.setdefault("main_problem", "")
    values.setdefault("trigger", "")
    values.setdefault("tools", [])
    values.setdefault(
        "require_approval_for", "Löschen, Überschreiben, Massenänderungen"
    )
    values.setdefault("recurring_tasks", [])
    values.setdefault("external_sources", "")

    if isinstance(values.get("tools"), str):
        values["tools"] = [
            i.strip() for i in str(values["tools"]).split(",") if i.strip()
        ]
    if isinstance(values.get("recurring_tasks"), str):
        values["recurring_tasks"] = [
            i.strip() for i in str(values["recurring_tasks"]).split(",") if i.strip()
        ]

    return OnboardingAnswers(**values)


def _print_question_label(label: str) -> None:
    print(f"\n  ── {label}")


# ─── Renderer helpers ─────────────────────────────────────────────────────────


def _render_soul(ans: OnboardingAnswers) -> str:
    workflow_steps = _split_items(ans.steps, ["Verstehen", "Ausführen", "Prüfen"])
    workflow_summary = " -> ".join(workflow_steps)
    tools_summary = ", ".join(ans.tools) if ans.tools else "[none]"
    return (
        f"# {ans.project_name} — SOUL\n\n"
        "## Identity\n"
        f"- Project: {ans.project_name}\n"
        f"- Customer / Team: {ans.customer_or_team}\n"
        f"- Role: {ans.role}\n"
        f"- Language: {ans.language}\n"
        f"- Tone: {ans.tone}\n\n"
        "## Mission\n"
        f"- Main problem: {ans.main_problem}\n"
        f"- Success criteria: {ans.success_criteria}\n"
        f"- Non-goals: {ans.non_goals}\n\n"
        "## Domain knowledge\n"
        f"- Expertise: {ans.domain_expertise}\n\n"
        "## Boundaries\n"
        f"- Hard limits: {ans.hard_limits}\n"
        f"- Approval required for: {ans.require_approval_for}\n"
        f"- Never do: {ans.never_do}\n\n"
        "## Workflow\n"
        f"- Trigger: {ans.trigger}\n"
        f"- Inputs: {ans.inputs}\n"
        f"- Steps: {workflow_summary}\n"
        f"- Validation: {ans.validation}\n"
        f"- Escalation: {ans.escalation}\n\n"
        "## Tools\n"
        f"- Tools: {tools_summary}\n\n"
        "## Quality\n"
        f"- Retry policy: {ans.retry_policy}\n"
        f"- Quality threshold: {ans.quality_threshold}\n\n"
        "## Memory\n"
        f"- Keep forever: {ans.keep_forever}\n"
        f"- Keep temporarily: {ans.keep_temporarily}\n"
        f"- Remember between runs: {ans.remember_between_runs}\n"
    )


def _render_config(
    ans: OnboardingAnswers, *, tenant_id: str | None = None, agent_id: str | None = None
) -> dict[str, Any]:
    quality = 7
    try:
        quality = int(
            "".join(
                ch for ch in ans.quality_threshold.split("/", 1)[0] if ch.isdigit()
            )
            or "7"
        )
    except ValueError:
        pass
    config = {
        "project_name": ans.project_name,
        "agent_name": _slugify(ans.project_name),
        "mode": "development",
        "quality_threshold": quality,
        "max_retries": 2,
        "max_actions_per_day": 50,
        "challenge_enabled": True,
        "proactive": True,
        "memory_scope": ["core", "project"],
        "human_approval_required": [
            i.strip() for i in ans.require_approval_for.split(",") if i.strip()
        ],
    }
    if tenant_id and agent_id:
        config["agent_name"] = agent_id
        config["instance"] = {"tenant_id": tenant_id, "agent_id": agent_id}
    return config


def _render_manifest(
    ans: OnboardingAnswers, *, tenant_id: str | None = None, agent_id: str | None = None
) -> dict[str, Any]:
    workflow_steps = _split_items(
        ans.steps,
        [
            "Understand the request",
            "Use the approved tool or subagent",
            "Verify the result",
        ],
    )
    skill_names = [_slugify(task) for task in ans.recurring_tasks if task]
    manifest = {
        "project_name": ans.project_name,
        "purpose": ans.main_problem,
        "customer_or_team": ans.customer_or_team,
        "success_criteria": ans.success_criteria,
        "trigger": ans.trigger,
        "approval_required_for": _split_items(
            ans.require_approval_for, ["delete", "overwrite", "bulk changes"]
        ),
        "model": {
            "default": "claude-sonnet-4-6",
            "planner": "claude-sonnet-4-6",
            "subagents": "claude-haiku-4-5",
        },
        "tool_permissions": {
            "default": "disabled",
            "enabled": ans.tools if ans.tools else ["read", "web_search", "notify"],
            "write_restricted_to_leaf": True,
        },
        "connectors": {
            "config_file": "connectors.yaml",
        },
        "skills": skill_names,
        "tools": ans.tools,
        "agent": {
            "role": ans.role,
            "language": ans.language,
            "tone": ans.tone,
            "domain_expertise": ans.domain_expertise,
            "hard_limits": ans.hard_limits,
        },
        "workflow": {
            "name": "main",
            "steps": workflow_steps,
            "validation": ans.validation,
            "escalation": ans.escalation,
        },
        "memory": {
            "forever": ans.keep_forever,
            "temporary": ans.keep_temporarily,
            "between_runs": ans.remember_between_runs,
        },
    }
    if tenant_id and agent_id:
        manifest["instance"] = {"tenant_id": tenant_id, "agent_id": agent_id}
    return manifest


def _render_workflow(ans: OnboardingAnswers) -> str:
    workflow_steps = _split_items(ans.steps, ["Verstehen", "Ausführen", "Prüfen"])
    steps_block = "\n".join(f"- {step}" for step in workflow_steps)
    return (
        "# Main Workflow\n\n"
        "## Trigger\n\n"
        f"{ans.trigger}\n\n"
        "## Inputs\n\n"
        f"{ans.inputs}\n\n"
        "## Steps\n\n"
        f"{steps_block}\n\n"
        "## Validation\n\n"
        f"{ans.validation}\n\n"
        "## Escalation\n\n"
        f"{ans.escalation}\n"
    )


def _render_project_brief(ans: OnboardingAnswers) -> str:
    workflow_steps = _split_items(ans.steps, ["Verstehen", "Ausführen", "Prüfen"])
    steps_summary = " -> ".join(workflow_steps)
    tools_summary = ", ".join(ans.tools) if ans.tools else "none"
    skills_summary = ", ".join(ans.recurring_tasks) if ans.recurring_tasks else "none"
    return (
        "# Project Brief\n\n"
        "## Summary\n"
        f"- Project: {ans.project_name}\n"
        f"- Customer / Team: {ans.customer_or_team}\n"
        f"- Main problem: {ans.main_problem}\n"
        f"- Success criteria: {ans.success_criteria}\n\n"
        "## Agent\n"
        f"- Role: {ans.role}\n"
        f"- Language: {ans.language}\n"
        f"- Tone: {ans.tone}\n"
        f"- Domain expertise: {ans.domain_expertise}\n\n"
        "## Workflow\n"
        f"- Trigger: {ans.trigger}\n"
        f"- Inputs: {ans.inputs}\n"
        f"- Steps: {steps_summary}\n"
        f"- Validation: {ans.validation}\n"
        f"- Escalation: {ans.escalation}\n\n"
        "## Tools\n"
        f"- Tools: {tools_summary}\n\n"
        "## Skills (recurring tasks)\n"
        f"- {skills_summary}\n\n"
        "## External sources\n"
        f"- {ans.external_sources or 'none'}\n\n"
        "## Safety\n"
        f"- Approval required for: {ans.require_approval_for}\n"
        f"- Never do: {ans.never_do}\n"
        f"- Retry policy: {ans.retry_policy}\n"
        f"- Quality threshold: {ans.quality_threshold}\n\n"
        "## Memory\n"
        f"- Keep forever: {ans.keep_forever}\n"
        f"- Keep temporarily: {ans.keep_temporarily}\n"
        f"- Remember between runs: {ans.remember_between_runs}\n"
    )


def _render_skill(task_name: str, project_name: str) -> str:
    slug = _slugify(task_name)
    return dedent(f"""\
        ---
        name: {slug}
        description: {task_name} — generiert von Setup. Beschreibe hier genauer wann dieser Skill benutzt wird.
        triggers: [{", ".join(w for w in task_name.lower().split() if len(w) > 3)}]
        output: "Ergebnis der Aufgabe '{task_name}'"
        ---

        # Skill: {task_name}

        Dieser Skill wurde automatisch aus deiner Aufgabenbeschreibung erstellt.
        Fülle die Abschnitte unten mit dem konkreten Wissen für diese Aufgabe aus.

        ## Wann benutzen

        Benutze diesen Skill wenn der Agent die Aufgabe "{task_name}" ausführen soll.

        ## Workflow

        1. **Vorbereitung** — Welche Daten oder Dokumente werden benötigt?
        2. **Durchführung** — Wie läuft die Aufgabe Schritt für Schritt ab?
        3. **Prüfung** — Woran erkennst du, dass das Ergebnis gut ist?
        4. **Ausgabe** — In welchem Format soll das Ergebnis vorliegen?

        > Ersetze diese Platzhalter mit deinem echten Prozesswissen.
        > Je konkreter, desto besser. Zahlen, Checklisten, Beispiele — alles hilft.

        ## Output-Spezifikation

        - **Format:** [z.B. Markdown, DOCX, E-Mail]
        - **Mindestinhalt:** [z.B. Executive Summary, 3 Kernpunkte, Quellen]
        - **Qualitäts-Schwelle:** [z.B. Alle Zahlen mit Quelle belegt]

        ## Qualitäts-Checkliste

        - [ ] Aufgabe vollständig erledigt
        - [ ] Ergebnis geprüft
        - [ ] Quellen angegeben (wenn nötig)
        - [ ] Output im richtigen Format

        ## Ressourcen

        - [references/workflow.md](references/workflow.md) — Detaillierter Ablauf
        - [references/best-practices.md](references/best-practices.md) — Qualitätsstandards
    """)


def _render_skill_workflow(task_name: str) -> str:
    return dedent(f"""\
        # Workflow — {task_name}

        ## Schritt-für-Schritt-Ablauf

        Beschreibe hier wie die Aufgabe konkret abläuft.

        ### Phase 1: Vorbereitung

        - Was muss vorhanden sein bevor du anfängst?
        - Welche Daten, Dokumente oder Zugänge werden gebraucht?

        ### Phase 2: Durchführung

        - Schritt 1: ...
        - Schritt 2: ...
        - Schritt 3: ...

        ### Phase 3: Prüfung

        - Woran erkennst du ob das Ergebnis gut ist?
        - Was tust du wenn es nicht gut genug ist?

        ### Phase 4: Ausgabe

        - In welchem Format lieferst du das Ergebnis?
        - An wen oder wohin geht es?

        > Ersetze diese Platzhalter mit deinem echten Ablauf.
    """)


def _render_skill_best_practices(task_name: str) -> str:
    return dedent(f"""\
        # Best Practices — {task_name}

        ## Was gute Ergebnisse ausmacht

        - [ ] Vollständig: alle erwarteten Punkte abgedeckt
        - [ ] Belegt: Zahlen haben Quellen
        - [ ] Klar: auch ohne Vorwissen verständlich
        - [ ] Pünktlich: vor dem nächsten relevanten Termin

        ## Häufige Fehler

        | Fehler | Vermeidung |
        |--------|-----------|
        | Fehlende Quelle | Immer Datum und Herkunft angeben |
        | Zu vage | Konkrete Zahlen statt Adjektive |
        | Falsche Priorität | Wichtigstes zuerst |

        > Ergänze hier die spezifischen Fehler die bei dieser Aufgabe häufig vorkommen.
    """)


def _render_connectors(ans: OnboardingAnswers) -> str:
    sources = [s.strip() for s in ans.external_sources.split(",") if s.strip()]
    lines = [
        "# Connectors — externe Datenquellen\n",
        "# Trage hier alle externen Systeme ein die dieser Agent nutzen darf.",
        "# Jeder Connector braucht eine Umgebungsvariable (URL oder API-Key).\n",
    ]
    if not sources:
        lines.append("connectors: []\n")
        lines.append("# Beispiel:")
        lines.append("# connectors:")
        lines.append("#   - name: web-search")
        lines.append("#     url_env: WEB_SEARCH_MCP_URL")
        lines.append('#     description: "Allgemeine Web-Suche"')
        lines.append("#     required: false")
    else:
        lines.append("connectors:")
        for source in sources:
            slug = _slugify(source)
            lines.append(f"  - name: {slug}")
            lines.append(f"    url_env: {slug.upper().replace('-', '_')}_MCP_URL")
            lines.append(f'    description: "{source}"')
            lines.append("    required: false")
            lines.append(
                "    # tools_enabled: []  # Optional: nur diese Tools freischalten"
            )
            lines.append("")
    return "\n".join(lines)


def _render_steering_examples(ans: OnboardingAnswers) -> list[dict[str, Any]]:
    examples = []
    for task in ans.recurring_tasks:
        if not task:
            continue
        slug = _slugify(task)
        examples.append(
            {
                "input": task,
                "description": f"Wiederkehrende Aufgabe: {task}",
                "expected_skill": slug,
                "expected_subagent": "researcher",
                "notes": f"Skill '{slug}' ausführen, dann reporter für die Ausgabe",
            }
        )
    if ans.main_problem:
        examples.append(
            {
                "input": ans.main_problem,
                "description": "Haupt-Aufgabe des Agenten",
                "expected_skill": _slugify(ans.recurring_tasks[0])
                if ans.recurring_tasks
                else None,
                "expected_subagent": "researcher",
                "notes": "Standard-Workflow ausführen",
            }
        )
    return examples


# ─── File writer ──────────────────────────────────────────────────────────────


def _write_template_project(
    target_dir: Path,
    ans: OnboardingAnswers,
    *,
    tenant_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    project_dir = target_dir / "project"
    docs_dir = target_dir / "docs"
    workflows_dir = project_dir / "workflows"
    tools_dir = project_dir / "tools"
    policies_dir = project_dir / "policies"
    knowledge_dir = project_dir / "knowledge"
    memory_dir = project_dir / "memory"
    agents_dir = project_dir / "agents"
    skills_dir = project_dir / "skills"

    for directory in [
        project_dir,
        docs_dir,
        workflows_dir,
        tools_dir,
        policies_dir,
        knowledge_dir,
        memory_dir,
        agents_dir,
        skills_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # Core project files
    (project_dir / "SOUL.md").write_text(_render_soul(ans), encoding="utf-8")
    (project_dir / "config.json").write_text(
        json.dumps(
            _render_config(ans, tenant_id=tenant_id, agent_id=agent_id),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "manifest.json").write_text(
        json.dumps(
            _render_manifest(ans, tenant_id=tenant_id, agent_id=agent_id),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "AGENTS.md").write_text(
        dedent(f"""\
            ---
            name: {_slugify(ans.project_name)}
            description: Project-specific operating instructions for {ans.project_name}.
            ---

            # Project Instructions

            - Follow the workflow in `project/workflows/main.md`.
            - Use tools only for approved actions.
            - Escalate when safety or quality rules are hit.
        """).strip()
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "onboarding.md").write_text(
        _render_project_brief(ans), encoding="utf-8"
    )
    (workflows_dir / "main.md").write_text(_render_workflow(ans), encoding="utf-8")

    # New: connectors + steering examples
    (project_dir / "connectors.yaml").write_text(
        _render_connectors(ans), encoding="utf-8"
    )
    steering = _render_steering_examples(ans)
    (project_dir / "steering-examples.json").write_text(
        json.dumps(steering, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Skills — one per recurring task
    for task in ans.recurring_tasks:
        if not task:
            continue
        skill_slug = _slugify(task)
        skill_dir = skills_dir / skill_slug
        refs_dir = skill_dir / "references"
        skill_dir.mkdir(parents=True, exist_ok=True)
        refs_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            _render_skill(task, ans.project_name), encoding="utf-8"
        )
        (refs_dir / "workflow.md").write_text(
            _render_skill_workflow(task), encoding="utf-8"
        )
        (refs_dir / "best-practices.md").write_text(
            _render_skill_best_practices(task), encoding="utf-8"
        )

    # Readme stubs
    (tools_dir / "README.md").write_text(
        "# Tools\n\nAdd project-specific tools here.\n", encoding="utf-8"
    )
    (policies_dir / "README.md").write_text(
        f"# Policies\n\n{ans.never_do}\n\nApproval required for: {ans.require_approval_for}\n",
        encoding="utf-8",
    )
    (knowledge_dir / "README.md").write_text(
        f"# Knowledge\n\n{ans.domain_expertise}\n", encoding="utf-8"
    )
    (memory_dir / "README.md").write_text(
        f"# Memory\n\n{ans.keep_forever}\n\n{ans.remember_between_runs}\n",
        encoding="utf-8",
    )
    (agents_dir / "README.md").write_text(
        "# Subagents\n\nAdd specialized subagents here when needed.\n", encoding="utf-8"
    )
    (docs_dir / "project-brief.md").write_text(
        _render_project_brief(ans), encoding="utf-8"
    )


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge preset values into a generated document without mutating either input."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _kmu_controlling_answers() -> OnboardingAnswers:
    """Generic defaults only; customer data remains a later configuration step."""
    return OnboardingAnswers(
        project_name="KMU Controlling Pilot",
        customer_or_team="KMU Management",
        main_problem="Finanzielle Abweichungen früh erkennen und verständlich einordnen",
        success_criteria="Priorisierte, belegte Controlling-Hinweise mit Freigabe vor Außenwirkung",
        non_goals="Keine Buchhaltung ersetzen und keine Entscheidungen oder Sendungen ohne Freigabe",
        role="KMU-Controlling-Agent",
        language="Deutsch",
        tone="klar, nüchtern, managementtauglich",
        domain_expertise="Controlling, Liquidität, Ergebnisrechnung und Abweichungsanalyse",
        hard_limits="Keine Zahlen erfinden; keine externe Kommunikation ohne Freigabe",
        trigger="stündlicher adaptiver Kontrolllauf",
        inputs="Saldenlisten, BWA, Budgets, offene Posten und freigegebene Quellen",
        steps="Daten prüfen\nKennzahlen deterministisch berechnen\nAbweichungen priorisieren\nEntwurf vorlegen",
        validation="Quellen, Zeitraum, Vorzeichen und Rechenwege prüfen",
        escalation="Bei fehlenden Daten, Zuordnungsfehlern oder Freigabepflicht an Menschen eskalieren",
        tools=["read", "compute", "notify"],
        require_approval_for="external communication, send, publish",
        never_do="Keine Zahlen erfinden oder extern versenden ohne Freigabe",
        retry_policy="Bei Fehlern bis zur konfigurierten Grenze wiederholen und dann eskalieren",
        quality_threshold="8/10",
        keep_forever="Freigegebene Regeln und Konten-Mappings",
        keep_temporarily="Eingabestände und Berechnungsartefakte",
        remember_between_runs="Geprüfte Mapping- und Alarmentscheidungen",
    )


def _apply_preset(target_dir: Path, preset: str) -> None:
    """Overlay a packaged preset while preserving the instance identity."""
    preset_dir = PRESETS_ROOT / preset
    if not preset_dir.is_dir():
        raise ValueError(f"Unbekanntes Preset: {preset}")
    project_dir = target_dir / "project"

    for filename in ("config.json", "manifest.json"):
        generated = json.loads((project_dir / filename).read_text(encoding="utf-8"))
        overlay = json.loads((preset_dir / filename).read_text(encoding="utf-8"))
        identity = generated.get("instance")
        merged = _deep_merge(generated, overlay)
        if identity is not None:
            merged["instance"] = identity
        (project_dir / filename).write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    for source in preset_dir.rglob("*"):
        if not source.is_file() or source.name in {"config.json", "manifest.json"}:
            continue
        relative = source.relative_to(preset_dir)
        destination = project_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    if preset == "kmu-controlling":
        for directory in ("inbox", "data", "imports", "state", "artifacts"):
            (target_dir / directory).mkdir(exist_ok=True)


# ─── Self-test ────────────────────────────────────────────────────────────────


def _self_test_project(target_dir: Path) -> SelfTestReport:
    """Structurally validate a freshly generated project instance.

    Deterministic and offline (no network / no API call), so the same
    generated tree always yields the same report. Catches a broken generation
    — a missing core file, invalid JSON, or a manifest that references a file
    that was never written (e.g. a listed skill without its SKILL.md).
    """
    project_dir = target_dir / "project"
    passed: list[str] = []
    problems: list[str] = []

    # 1. Required, non-empty core files.
    required = [
        ("SOUL.md", "Identität (SOUL.md)"),
        ("config.json", "Konfiguration (config.json)"),
        ("manifest.json", "Manifest (manifest.json)"),
        ("workflows/main.md", "Haupt-Workflow (workflows/main.md)"),
        ("connectors.yaml", "Datenquellen (connectors.yaml)"),
        ("steering-examples.json", "Planner-Beispiele (steering-examples.json)"),
    ]
    for rel, label in required:
        path = project_dir / rel
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            passed.append(label)
        else:
            problems.append(f"{label}: Datei fehlt oder ist leer ({rel})")

    # 2. JSON files parse.
    manifest: dict[str, Any] | None = None
    for rel in ("config.json", "manifest.json", "steering-examples.json"):
        path = project_dir / rel
        if not path.is_file():
            continue  # already reported as missing in step 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            passed.append(f"{rel} ist gültiges JSON")
            if rel == "manifest.json" and isinstance(data, dict):
                manifest = data
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: ungültiges JSON — {exc}")

    # 3. Manifest cross-references resolve to files that actually exist.
    if isinstance(manifest, dict):
        config_file = (manifest.get("connectors") or {}).get("config_file")
        if config_file:
            if (project_dir / config_file).is_file():
                passed.append(
                    f"Connector-Datei referenziert & vorhanden ({config_file})"
                )
            else:
                problems.append(
                    f"Manifest verweist auf fehlende Connector-Datei: {config_file}"
                )
        for slug in manifest.get("skills") or []:
            skill_file = project_dir / "skills" / slug / "SKILL.md"
            if skill_file.is_file() and skill_file.read_text(encoding="utf-8").strip():
                passed.append(f"Skill vorhanden: {slug}")
            else:
                problems.append(
                    f"Manifest listet Skill '{slug}', aber skills/{slug}/SKILL.md fehlt"
                )

    return SelfTestReport(passed=tuple(passed), problems=tuple(problems))


def _instance_identity(target_dir: Path) -> tuple[str, str]:
    """Return the tenant/agent identity encoded by an instance path."""
    target_dir = Path(target_dir)
    if len(target_dir.parts) < 2:
        raise ValueError("Instanzpfad muss <tenant>/<agent> enthalten")
    return target_dir.parent.name, target_dir.name


def _validate_instance(target_dir: Path) -> SelfTestReport:
    """Offline validation for an isolated factory instance."""
    report = _self_test_project(target_dir)
    passed = list(report.passed)
    problems = list(report.problems)
    try:
        tenant_id, agent_id = _instance_identity(target_dir)
        config = json.loads(
            (target_dir / "project" / "config.json").read_text(encoding="utf-8")
        )
        identity = config.get("instance") if isinstance(config, dict) else None
        expected = {"tenant_id": tenant_id, "agent_id": agent_id}
        if identity == expected:
            passed.append(f"Instanzidentität bestätigt: {tenant_id}/{agent_id}")
        else:
            problems.append(
                f"Instanzidentität stimmt nicht: erwartet {expected}, erhalten {identity}"
            )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        problems.append(f"Instanzidentität konnte nicht geprüft werden: {exc}")
    return SelfTestReport(passed=tuple(passed), problems=tuple(problems))


def _print_self_test(report: SelfTestReport) -> None:
    print()
    print("  ── Selbsttest ──────────────────────────")
    print("  Wir prüfen kurz, ob alles zusammenpasst …")
    print()
    for label in report.passed:
        print(f"    ✓  {label}")
    for problem in report.problems:
        print(f"    ✗  {problem}")
    print()
    if report.ok:
        print("  Alles geprüft — dein Projekt ist einsatzbereit.")
    else:
        print(
            f"  {len(report.problems)} Problem(e) gefunden — bitte die ✗-Zeilen oben ansehen."
        )


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_setup(args: argparse.Namespace) -> int:
    _print_banner()

    if args.full:
        print("  Vollständiger Modus: alle Fragen für mehr Präzision.\n")
        answers = _collect_answers(mode="full")
    else:
        print("  Kurzer Einstieg: nur die wichtigsten Fragen.")
        print("  Du kannst danach jederzeit Feindetails ergänzen.\n")
        answers = _collect_answers(mode="beginner")

    output_root = Path(args.output or DEFAULT_OUTPUT_ROOT)
    project_slug = _slugify(answers.project_name)
    target_dir = output_root / project_slug

    if target_dir.exists() and not args.force:
        confirm = _ask(
            f"\n  '{target_dir}' existiert bereits. Überschreiben? (ja/nein)", "nein"
        ).lower()
        if confirm not in {"j", "ja", "y", "yes"}:
            print("\n  Abgebrochen.")
            return 1

    _write_template_project(target_dir, answers)

    if not args.no_self_test:
        report = _self_test_project(target_dir)
        _print_self_test(report)
        if not report.ok:
            print("\n  Hinweis: Das Projekt wurde erstellt, aber der Selbsttest")
            print(
                "  hat Probleme gefunden. Bitte oben nachsehen und ggf. erneut ausführen."
            )
            _print_success(target_dir, answers)
            return 1

    _print_success(target_dir, answers)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    """Create one isolated tenant/agent instance; existing roots are immutable."""
    tenant_id = _slugify(args.tenant)
    agent_id = _slugify(args.agent)
    output_root = Path(args.output or DEFAULT_OUTPUT_ROOT)
    target_dir = output_root / tenant_id / agent_id
    if target_dir.exists():
        print(f"Instanz existiert bereits und wird nicht verändert: {target_dir}")
        return 1

    preset = getattr(args, "preset", None)
    if preset and preset != "kmu-controlling":
        print(f"Unbekanntes Preset: {preset}")
        return 1
    answers = (
        _kmu_controlling_answers()
        if preset
        else _collect_answers(mode="full" if args.full else "beginner")
    )
    _write_template_project(target_dir, answers, tenant_id=tenant_id, agent_id=agent_id)
    if preset:
        _apply_preset(target_dir, preset)
    if not args.no_self_test:
        report = _validate_instance(target_dir)
        _print_self_test(report)
        if not report.ok:
            return 1
    print(f"Instanz erstellt: {tenant_id}/{agent_id} ({target_dir})")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    report = _validate_instance(Path(args.instance))
    _print_self_test(report)
    return 0 if report.ok else 1


def cmd_status(_: argparse.Namespace) -> int:
    print("\nTemplate status")
    print("───────────────")
    print(f"  Core:         {ROOT / 'core'}")
    print(f"  Project pack: {ROOT / 'project'}")
    print(f"  Docs:         {ROOT / 'docs'}")
    print(f"  Instances:    {DEFAULT_OUTPUT_ROOT}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    instance = getattr(args, "instance", None)
    if instance:
        target_dir = Path(instance)
        report = _validate_instance(target_dir)
        if not report.ok:
            _print_self_test(report)
            return 1
        tenant_id, agent_id = _instance_identity(target_dir)
        requested_tenant = getattr(args, "tenant", None)
        if requested_tenant and _slugify(requested_tenant) != tenant_id:
            print(
                f"Tenant '{requested_tenant}' passt nicht zur Instanz "
                f"'{tenant_id}/{agent_id}'."
            )
            return 1
        config = json.loads(
            (target_dir / "project" / "config.json").read_text(encoding="utf-8")
        )
        orchestrator = _instance_orchestrator(target_dir)
        if getattr(args, "loop", False):
            _run_instance_loop(target_dir, config, tenant_id, orchestrator)
            return 0
        task = getattr(args, "task", None) or "offline smoke validation"
        result = orchestrator.run(
            task, tools=_build_instance_tools(target_dir), tenant=tenant_id
        )
        print(f"Instance: {tenant_id}/{agent_id}")
        print(f"Project root: {target_dir}")
        print(f"Success: {result.success}")
        _print_instance_result(target_dir, result)
        return 0 if result.success else 1
    from agent import main as agent_main

    if args.extra:
        import sys

        sys.argv = ["agent.py", *args.extra]
    agent_main()
    return 0


def _instance_orchestrator(project_root: Path):
    """Late import keeps factory validation usable without the legacy runner."""
    from core.orchestrator import AgentOrchestrator

    return AgentOrchestrator(project_root)


def _print_instance_result(instance_root: Path, result: Any) -> None:
    """Show the human result and durable artifact without dumping ledger data."""
    metadata = getattr(result, "metadata", {})
    outputs = metadata.get("outputs", []) if isinstance(metadata, dict) else []
    for output in reversed(outputs):
        try:
            value = json.loads(output)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("mode") not in {
            "deterministic_fallback",
            "model_draft",
        }:
            continue
        if isinstance(value.get("summary"), str):
            print(f"Summary: {value['summary']}")
        artifact = value.get("human_artifact") or value.get("artifact")
        if isinstance(artifact, str):
            print(f"Report: {(instance_root / artifact).resolve()}")
        acceptance = value.get("acceptance")
        if isinstance(acceptance, dict):
            count = acceptance.get("repeatable_run_count", 0)
            status = "passed" if acceptance.get("passed") else "open"
            print(f"Pilot acceptance: {status} ({count}/3 repeatable runs)")
        return


def _build_instance_tools(instance_root: Path) -> dict[str, Any]:
    """Build only the local capabilities explicitly allowed by a known preset."""
    try:
        manifest = json.loads(
            (instance_root / "project" / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}
    workflow = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
    if not isinstance(workflow, dict) or workflow.get("name") != "kmu-controlling":
        return {}
    permissions = manifest.get("tool_permissions", {})
    enabled = permissions.get("enabled", []) if isinstance(permissions, dict) else []
    if not isinstance(enabled, list):
        return {}

    from core.controlling import (
        ControllingComputeTool,
        ControllingReportTool,
        InstanceReadTool,
    )

    factories = {
        "read": InstanceReadTool,
        "compute": ControllingComputeTool,
        "report": ControllingReportTool,
    }
    return {
        name: factory(instance_root)
        for name, factory in factories.items()
        if name in enabled
    }


class _TenantBoundSchedulerOrchestrator:
    """Keep scheduled instance work within the same tenant boundary."""

    def __init__(self, orchestrator: Any, tenant_id: str):
        self._orchestrator = orchestrator
        self._tenant_id = tenant_id

    def run(
        self, task: str, *, tools: dict[str, Any], request_id: str | None = None
    ) -> Any:
        return self._orchestrator.run(
            task, tools=tools, tenant=self._tenant_id, request_id=request_id
        )


def _run_instance_schedule_cycle(
    instance_root: Path,
    config: dict[str, Any],
    tenant_id: str,
    orchestrator: Any,
) -> ScheduledDecision:
    """Evaluate and dispatch one adaptive schedule cycle for one instance."""
    return run_scheduled_cycle(
        root=instance_root,
        agent_config=config,
        orchestrator=_TenantBoundSchedulerOrchestrator(orchestrator, tenant_id),
        tools=_build_instance_tools(instance_root),
    )


def _run_instance_loop(
    instance_root: Path,
    config: dict[str, Any],
    tenant_id: str,
    orchestrator: Any,
) -> None:
    """Run a generated instance's adaptive scheduler at its configured interval."""
    interval = config.get("loop_interval_minutes", 60)
    interval = interval if isinstance(interval, int) and interval > 0 else 60
    print(
        f"Instanz-Loop gestartet: {tenant_id}/{config.get('agent_name', 'agent')} alle {interval} Minuten"
    )
    try:
        while True:
            try:
                decision = _run_instance_schedule_cycle(
                    instance_root, config, tenant_id, orchestrator
                )
                print(f"Schedule: {decision.reason}")
            except Exception as exc:
                print(f"Schedule-Fehler: {exc}")
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        print("Instanz-Loop gestoppt.")


# ─── Output helpers ───────────────────────────────────────────────────────────


def _print_banner() -> None:
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║       Agent Setup — Willkommen       ║")
    print("  ╚══════════════════════════════════════╝")
    print()
    print("  Wir erstellen jetzt dein Agent-Projekt.")
    print("  So läuft es ab:")
    print("    1. Du beantwortest ein paar kurze Fragen")
    print("    2. Alle Dateien werden automatisch ausgefüllt")
    print("    3. Wir testen kurz, ob alles zusammenpasst")
    print()


def _print_success(target_dir: Path, ans: OnboardingAnswers) -> None:
    skill_count = len(ans.recurring_tasks)
    connector_count = len([s for s in ans.external_sources.split(",") if s.strip()])

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║         Agent erfolgreich erstellt!  ║")
    print("  ╚══════════════════════════════════════╝")
    print()
    print(f"  Projektordner:  {target_dir}")
    print()
    print("  Erstellt:")
    print("    ✓  SOUL.md               — Identität und Regeln")
    print("    ✓  manifest.json         — Konfiguration")
    print("    ✓  workflows/main.md     — Haupt-Workflow")
    print(
        f"    ✓  connectors.yaml       — {connector_count} Datenquelle(n) vorkonfiguriert"
    )
    print(
        f"    ✓  steering-examples.json— {len(ans.recurring_tasks) + (1 if ans.main_problem else 0)} Beispiele für den Planner"
    )
    if skill_count:
        print(
            f"    ✓  skills/               — {skill_count} Skill(s) als Vorlage erstellt:"
        )
        for task in ans.recurring_tasks:
            print(f"         • {task}")
    print()
    print("  ── Nächste Schritte ────────────────────")
    print()
    print("  1. Skills befüllen (das Wichtigste)")
    if ans.recurring_tasks:
        first_skill = _slugify(ans.recurring_tasks[0])
        print(f"     Öffne: {target_dir}/project/skills/{first_skill}/SKILL.md")
        print(
            f"     → Beschreibe dort Schritt für Schritt wie '{ans.recurring_tasks[0]}' abläuft."
        )
    print()
    if connector_count:
        print("  2. Datenquellen konfigurieren")
        print(f"     Öffne: {target_dir}/project/connectors.yaml")
        print("     → Trage die URL oder den API-Key für deine Quelle ein.")
        print()
    print("  3. Agenten testen")
    print("     python agent_cli.py run")
    if ans.recurring_tasks:
        print(f'     → Probiere: "{ans.recurring_tasks[0]}"')
    print()
    print("  4. Feindetails ergänzen (optional)")
    print("     python agent_cli.py setup --full")
    print()
    print("  Dokumentation: docs/architecture.md")
    print()


# ─── CLI wiring ───────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent",
        description="Reusable automation agent template CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for cmd_name, cmd_help in [
        ("setup", "Interaktives Onboarding — erstellt ein neues Agent-Projekt"),
        ("init", "Alias für setup"),
    ]:
        p = sub.add_parser(cmd_name, help=cmd_help)
        p.add_argument("--output", help="Zielordner für das generierte Projekt")
        p.add_argument(
            "--force",
            action="store_true",
            help="Vorhandenes Projekt ohne Rückfrage überschreiben",
        )
        p.add_argument(
            "--full", action="store_true", help="Alle erweiterten Fragen stellen"
        )
        p.add_argument(
            "--no-self-test",
            action="store_true",
            help="Selbsttest nach dem Erstellen überspringen",
        )
        p.set_defaults(func=cmd_setup)

    create = sub.add_parser("create", help="Create an isolated tenant/agent instance")
    create.add_argument("--tenant", required=True, help="Tenant identifier")
    create.add_argument("--agent", required=True, help="Agent identifier")
    create.add_argument("--output", help="Instances root (default: instances)")
    create.add_argument(
        "--full", action="store_true", help="Ask all advanced questions"
    )
    create.add_argument(
        "--preset", choices=["kmu-controlling"], help="Create a packaged agent preset"
    )
    create.add_argument("--no-self-test", action="store_true", help="Skip self-test")
    create.set_defaults(func=cmd_create)

    validate = sub.add_parser("validate", help="Validate an instance offline")
    validate.add_argument(
        "--instance", required=True, help="Instance path <tenant>/<agent>"
    )
    validate.set_defaults(func=cmd_validate)

    run = sub.add_parser("run", help="Agenten starten")
    run.add_argument("--instance", help="Run instance <tenant>/<agent>")
    run.add_argument("--tenant", help="Run tenant (default: instance tenant)")
    run.add_argument("--task", help="Single task for an instance")
    run.add_argument(
        "--loop",
        action="store_true",
        help="Run the instance adaptive scheduler continuously",
    )
    run.add_argument("extra", nargs=argparse.REMAINDER, help="Argumente für agent.py")
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", help="Template-Status anzeigen")
    status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
