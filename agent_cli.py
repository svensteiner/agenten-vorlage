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
import base64
import contextlib
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core.controlling.artifacts import read_acceptance_status, render_html
from core.scheduling import ScheduledDecision, run_scheduled_cycle


ROOT = Path(__file__).parent
DEFAULT_OUTPUT_ROOT = ROOT / "instances"
PRESETS_ROOT = ROOT / "presets"
LOOP_HEALTH_GRACE = timedelta(minutes=5)
LOOP_HEALTH_STATUSES = frozenset({"running", "error", "stopped"})
LOOP_POLL_RESULTS = frozenset({"success", "idle", "already_enqueued", "error", "stopped"})
LOOP_WORK_REASONS = frozenset(
    {
        "missing_data",
        "new_input",
        "changed_input",
        "input_changed",
        "pending_approval",
        "recovery",
        "periodic_review",
    }
)
MAX_LOOP_INTERVAL_MINUTES = 1440
MAX_STATUS_JSON_BYTES = 1024 * 1024
MAX_MANAGEMENT_REPORT_HTML_BYTES = 5 * 1024 * 1024
SUPERVISOR_HEALTH_RELATIVE = "state/supervisor-health.json"
SUPERVISOR_LOCK_RELATIVE = "state/.supervisor.lock"
SUPERVISOR_STATUSES = frozenset({"running", "backoff", "frozen", "stopped"})
MAX_SUPERVISOR_CRASHES = 20
MAX_SUPERVISOR_BACKOFF_SECONDS = 3600
MAX_SUPERVISOR_HEALTH_AGE = timedelta(minutes=15)
SUPERVISOR_HEARTBEAT_SECONDS = 60
PRODUCTION_EVIDENCE_REFERENCE = "state/production-attestation-reference.json"
PRODUCTION_TRUST_ROOT_ENV = "AGENT_PRODUCTION_TRUST_ROOT"
PRODUCTION_KEY_FILES = ("platform.pub", "security.pub", "control-plane.pub")
# Provisioning replaces this package trust anchor with the authorized release root.
# The placeholder deliberately verifies no production trust configuration.
CONTROL_PLANE_ROOT_PUBLIC_KEY_B64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
MAX_ATTESTATION_TTL = timedelta(days=30)
MAX_CURRENT_FACTS_TTL = timedelta(minutes=15)
PRODUCTION_MATRIX_OUTCOMES = frozenset(
    {
        "own_input",
        "own_control_areas",
        "foreign_scope",
        "link_junction_e2e",
        "own_service",
        "restart",
    }
)
PRODUCTION_FINGERPRINTS = frozenset(
    {"deployment", "image", "acl_parent_chain", "namespace_volume"}
)


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


def cmd_status(args: argparse.Namespace) -> int:
    instance = getattr(args, "instance", None)
    if instance:
        if getattr(args, "production", False):
            return _print_production_status(Path(instance))
        return _print_pilot_status(Path(instance))
    if getattr(args, "production", False):
        print("Produktionsstatus braucht --instance.")
        return 1
    print("\nTemplate status")
    print("───────────────")
    print(f"  Core:         {ROOT / 'core'}")
    print(f"  Project pack: {ROOT / 'project'}")
    print(f"  Docs:         {ROOT / 'docs'}")
    print(f"  Instances:    {DEFAULT_OUTPUT_ROOT}")
    return 0


def _is_link_or_junction(path: Path) -> bool:
    """Treat Windows junctions/reparse redirects like symbolic links."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction is not None and is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        return bool(attributes & reparse_flag)
    except FileNotFoundError:
        return False
    except OSError:
        return True


def _safe_status_path(root: Path, relative: str) -> Path | None:
    """Resolve a fixed instance-relative status path without following symlinks."""
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    candidate = root
    for part in relative_path.parts:
        candidate /= part
        if _is_link_or_junction(candidate):
            return None
    try:
        candidate.resolve(strict=False).relative_to(root)
    except (OSError, ValueError):
        return None
    return candidate


def _tree_contains_symlink(root: Path) -> bool:
    """Reject project trees that could make structural validation leave the root."""
    if root.is_symlink():
        return True
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = list(directory.iterdir())
        except OSError:
            return True
        for child in children:
            if child.is_symlink():
                return True
            if child.is_dir():
                pending.append(child)
    return False


def _read_status_json(root: Path, relative: str) -> tuple[dict[str, Any], bool]:
    """Read one fixed status file; the boolean reports malformed/unsafe data."""
    path = _safe_status_path(root, relative)
    if path is None:
        return {}, True
    if not path.exists():
        return {}, False
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_STATUS_JSON_BYTES + 1)
        if len(raw) > MAX_STATUS_JSON_BYTES:
            return {}, True
        value = json.loads(raw.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ):
        return {}, True
    return (value, False) if isinstance(value, dict) else ({}, True)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare a path lstat with an opened descriptor without trusting a name."""
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
    )


def _verified_management_report_view(root: Path, payload: dict[str, Any]) -> bool:
    """Require the displayed HTML view to be the exact deterministic payload view."""
    relative = "artifacts/latest-controlling-report.html"
    path = _safe_status_path(root, relative)
    if path is None:
        return False
    try:
        expected = render_html(payload).encode("utf-8")
        if len(expected) > MAX_MANAGEMENT_REPORT_HTML_BYTES:
            return False
        before = path.lstat()
        if (
            _is_link_or_junction(root)
            or _is_link_or_junction(path)
            or not stat.S_ISREG(before.st_mode)
            or before.st_size > MAX_MANAGEMENT_REPORT_HTML_BYTES
        ):
            return False
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not _same_file_identity(before, opened):
                return False
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(MAX_MANAGEMENT_REPORT_HTML_BYTES + 1)
            after = path.lstat()
            if (
                len(raw) > MAX_MANAGEMENT_REPORT_HTML_BYTES
                or not _same_file_identity(before, after)
                or _is_link_or_junction(root)
                or _safe_status_path(root, relative) != path
            ):
                return False
        finally:
            os.close(descriptor)
    except (OSError, KeyError, TypeError, ValueError, AttributeError, UnicodeError):
        return False
    return hmac.compare_digest(raw, expected)


def _bounded_json_file(path: Path) -> dict[str, Any] | None:
    """Read one small regular JSON object without accepting a link/reparse path."""
    try:
        if _is_link_or_junction(path) or not path.is_file():
            return None
        with path.open("rb") as stream:
            raw = stream.read(MAX_STATUS_JSON_BYTES + 1)
        if len(raw) > MAX_STATUS_JSON_BYTES:
            return None
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _valid_production_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 64 or any(ord(c) < 32 for c in value):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _nonempty_evidence_text(value: Any, *, limit: int = 512) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value.strip()) <= limit
        and all(ord(character) >= 32 for character in value)
    )


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _safe_trust_root() -> Path | None:
    raw_root = os.environ.get(PRODUCTION_TRUST_ROOT_ENV)
    if not raw_root or raw_root.startswith(("\\\\", "//")) or len(raw_root) > 1024:
        return None
    root = Path(raw_root)
    if not root.is_absolute():
        return None
    try:
        current = Path(root.anchor)
        for part in root.parts[1:]:
            current /= part
            if _is_link_or_junction(current):
                return None
        resolved = root.resolve(strict=True)
        if str(resolved).startswith(("\\\\", "//")):
            return None
        if os.name == "nt":
            import ctypes

            if ctypes.windll.kernel32.GetDriveTypeW(root.anchor) == 4:  # DRIVE_REMOTE
                return None
        return resolved if resolved.is_dir() and not _is_link_or_junction(resolved) else None
    except OSError:
        return None


def _safe_trust_file(root: Path, *parts: str) -> Path | None:
    path = root
    for part in parts:
        if not part or Path(part).name != part:
            return None
        path /= part
        if _is_link_or_junction(path):
            return None
    try:
        return path if path.is_file() and not _is_link_or_junction(path) else None
    except OSError:
        return None


def _bounded_bytes(path: Path, limit: int = 4096) -> bytes | None:
    try:
        with path.open("rb") as stream:
            value = stream.read(limit + 1)
        return value if len(value) <= limit else None
    except OSError:
        return None


def _opaque_evidence_id(value: Any) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return None
    return value if value[0].isalnum() and all(c.islower() or c.isdigit() or c in "_-" for c in value) else None


def _load_public_key(path: Path, expected_pin: str) -> Ed25519PublicKey | None:
    try:
        encoded = _bounded_bytes(path)
        raw = base64.b64decode(encoded, validate=True) if encoded is not None else b""
        if (
            len(raw) != 32
            or len(expected_pin) != 64
            or expected_pin.lower() != expected_pin
            or any(character not in "0123456789abcdef" for character in expected_pin)
            or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_pin)
        ):
            return None
        return Ed25519PublicKey.from_public_bytes(raw)
    except (OSError, ValueError, TypeError):
        return None


def _verify_signed_payload(root: Path, payload_path: Path, signature_path: Path, key_name: str, key_pins: dict[str, str]) -> dict[str, Any] | None:
    payload = _bounded_json_file(payload_path)
    key_path = _safe_trust_file(root, "keys", key_name)
    key = _load_public_key(key_path, key_pins.get(key_name, "")) if key_path else None
    try:
        encoded = _bounded_bytes(signature_path)
        signature = base64.b64decode(encoded, validate=True) if encoded is not None else b""
        if payload is None or key is None or len(signature) != 64:
            return None
        key.verify(signature, _canonical_json(payload))
        return payload
    except (OSError, ValueError, TypeError, InvalidSignature):
        return None


def _time_window(payload: dict[str, Any], maximum_ttl: timedelta, now: datetime) -> bool:
    issued = _valid_production_timestamp(payload.get("issued_at"))
    signed = _valid_production_timestamp(payload.get("signed_at"))
    expires = _valid_production_timestamp(payload.get("expires_at"))
    return bool(issued and signed and expires and issued <= signed <= now < expires and expires - issued <= maximum_ttl)


def _valid_fingerprints(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == PRODUCTION_FINGERPRINTS and all(_nonempty_evidence_text(value[name]) for name in PRODUCTION_FINGERPRINTS)


def _trusted_key_pins(root: Path, now: datetime) -> dict[str, str] | None:
    config_path = _safe_trust_file(root, "trust-config.json")
    signature_path = _safe_trust_file(root, "trust-config.sig")
    try:
        root_raw = base64.b64decode(CONTROL_PLANE_ROOT_PUBLIC_KEY_B64, validate=True)
        root_key = Ed25519PublicKey.from_public_bytes(root_raw)
        config = _bounded_json_file(config_path) if config_path else None
        encoded = _bounded_bytes(signature_path) if signature_path else None
        signature = base64.b64decode(encoded, validate=True) if encoded is not None else b""
        if config is None or len(signature) != 64:
            return None
        root_key.verify(signature, _canonical_json(config))
    except (ValueError, TypeError, InvalidSignature):
        return None
    if set(config) != {"schema_version", "trust_config_id", "issued_at", "signed_at", "expires_at", "key_pins"} or config.get("schema_version") != 1 or _opaque_evidence_id(config.get("trust_config_id")) is None or not _time_window(config, MAX_ATTESTATION_TTL, now):
        return None
    pins = config.get("key_pins")
    if not isinstance(pins, dict) or set(pins) != set(PRODUCTION_KEY_FILES) or len(set(pins.values())) != 3:
        return None
    return pins


def _production_evidence_valid(instance: Path) -> bool:
    """Verify pinned signatures and fresh runtime facts from a controlled trust root."""
    reference, invalid = _read_status_json(instance, PRODUCTION_EVIDENCE_REFERENCE)
    if invalid or set(reference) != {"schema_version", "attestation_id"} or reference.get("schema_version") != 1:
        return False
    attestation_id = _opaque_evidence_id(reference.get("attestation_id"))
    root = _safe_trust_root()
    if attestation_id is None or root is None:
        return False
    now = datetime.now(timezone.utc)
    key_pins = _trusted_key_pins(root, now)
    if key_pins is None:
        return False
    try:
        root.relative_to(instance)
        return False
    except ValueError:
        pass
    try:
        instance.relative_to(root)
        return False
    except ValueError:
        pass
    tenant_id, agent_id = _instance_identity(instance)
    attestation = _safe_trust_file(root, "attestations", attestation_id, "attestation.json")
    platform_sig = _safe_trust_file(root, "attestations", attestation_id, "platform.sig")
    security_sig = _safe_trust_file(root, "attestations", attestation_id, "security.sig")
    facts = _safe_trust_file(root, "runtime", tenant_id, agent_id, "current-facts.json")
    facts_sig = _safe_trust_file(root, "runtime", tenant_id, agent_id, "current-facts.sig")
    if not all((attestation, platform_sig, security_sig, facts, facts_sig)):
        return False
    payload = _verify_signed_payload(root, attestation, platform_sig, "platform.pub", key_pins)
    security_payload = _verify_signed_payload(root, attestation, security_sig, "security.pub", key_pins)
    runtime = _verify_signed_payload(root, facts, facts_sig, "control-plane.pub", key_pins)
    if payload is None or security_payload != payload or runtime is None:
        return False
    if set(payload) != {"schema_version", "attestation_id", "tenant_id", "agent_id", "deployment_generation", "service_identity", "tenant_identity", "fingerprints", "matrix", "issued_at", "signed_at", "expires_at"}:
        return False
    if payload.get("schema_version") != 1 or payload.get("attestation_id") != attestation_id or payload.get("tenant_id") != tenant_id or payload.get("agent_id") != agent_id:
        return False
    if not _time_window(payload, MAX_ATTESTATION_TTL, now) or not _nonempty_evidence_text(payload.get("deployment_generation")) or not _nonempty_evidence_text(payload.get("service_identity")) or not _nonempty_evidence_text(payload.get("tenant_identity")) or not _valid_fingerprints(payload.get("fingerprints")):
        return False
    matrix = payload.get("matrix")
    if not isinstance(matrix, dict) or set(matrix) != PRODUCTION_MATRIX_OUTCOMES or any(matrix[name] != "passed" for name in PRODUCTION_MATRIX_OUTCOMES):
        return False
    if set(runtime) != {"schema_version", "attestation_id", "tenant_id", "agent_id", "deployment_generation", "service_identity", "tenant_identity", "fingerprints", "issued_at", "signed_at", "expires_at"}:
        return False
    required = ("attestation_id", "tenant_id", "agent_id", "deployment_generation", "service_identity", "tenant_identity", "fingerprints")
    return bool(runtime.get("schema_version") == 1 and _time_window(runtime, MAX_CURRENT_FACTS_TTL, now) and all(runtime.get(name) == payload.get(name) for name in required))


def _print_production_status(instance: Path) -> int:
    """Show the separate production gate; local status is never evidence."""
    local_result = _print_pilot_status(instance)
    try:
        resolved = instance.resolve(strict=True)
    except OSError:
        resolved = instance
    evidence_valid = _production_evidence_valid(resolved) if local_result == 0 else False
    if evidence_valid:
        print("  Produktionsfreigabe: GRÜN – externe Evidenz gültig")
        return 0
    print("  Produktionsfreigabe: ROT – externe Evidenz fehlt oder ist ungültig")
    return 1


def _status_timestamp(value: Any) -> tuple[str, bool]:
    if value is None:
        return "–", False
    if (
        not isinstance(value, str)
        or len(value) > 64
        or any(ord(character) < 32 for character in value)
    ):
        return "–", True
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return "–", True
    return value, False


def _loop_interval_minutes(config: dict[str, Any]) -> int:
    """Return the shared validated status/runtime loop interval."""
    interval = config.get("loop_interval_minutes", 60)
    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
        or not 1 <= interval <= MAX_LOOP_INTERVAL_MINUTES
    ):
        raise ValueError("loop interval must be an integer from 1 to 1440 minutes")
    return interval


def _loop_health_is_fresh(
    health: dict[str, Any], interval_minutes: int
) -> bool:
    """Validate the bounded heartbeat contract and reject stale/future values."""
    status = health.get("status")
    poll_result = health.get("poll_result")
    updated_at = health.get("updated_at")
    schema_version = health.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
        or status not in LOOP_HEALTH_STATUSES
        or poll_result not in LOOP_POLL_RESULTS
        or not isinstance(updated_at, str)
        or len(updated_at) > 64
        or any(ord(character) < 32 for character in updated_at)
    ):
        return False
    try:
        timestamp = datetime.fromisoformat(updated_at)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return False
        age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
        maximum_age = (
            timedelta(minutes=2 * interval_minutes) + LOOP_HEALTH_GRACE
        )
    except (ValueError, OverflowError):
        return False
    return (
        status == "running"
        and poll_result not in {"error", "stopped"}
        and -LOOP_HEALTH_GRACE <= age <= maximum_age
    )


def _supervisor_config(config: dict[str, Any]) -> tuple[bool, int, int, int]:
    """Return the bounded opt-in supervisor settings without accepting junk."""
    raw = config.get("supervisor", {})
    if not isinstance(raw, dict):
        raise ValueError("supervisor configuration must be an object")
    required = raw.get("supervisor_required", config.get("supervisor_required", False))
    threshold = raw.get("crash_threshold", 3)
    base_backoff = raw.get("base_backoff_seconds", 5)
    max_backoff = raw.get("max_backoff_seconds", 300)
    if not isinstance(required, bool):
        raise ValueError("supervisor_required must be a boolean")
    for value, label, upper in (
        (threshold, "crash_threshold", MAX_SUPERVISOR_CRASHES),
        (base_backoff, "base_backoff_seconds", MAX_SUPERVISOR_BACKOFF_SECONDS),
        (max_backoff, "max_backoff_seconds", MAX_SUPERVISOR_BACKOFF_SECONDS),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= upper:
            raise ValueError(f"supervisor {label} must be an integer from 1 to {upper}")
    if base_backoff > max_backoff:
        raise ValueError("supervisor base_backoff_seconds must not exceed max_backoff_seconds")
    return required, threshold, base_backoff, max_backoff


def _supervisor_health_is_fresh(health: dict[str, Any], now: datetime | None = None) -> bool:
    """Strict, content-free supervisor heartbeat validation for status."""
    if set(health) != {
        "schema_version", "status", "restart_count", "consecutive_crashes",
        "exit_code", "updated_at", "next_restart_at",
    }:
        return False
    if health.get("schema_version") != 1 or health.get("status") not in SUPERVISOR_STATUSES:
        return False
    for key in ("restart_count", "consecutive_crashes"):
        value = health.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_SUPERVISOR_CRASHES:
            return False
    exit_code = health.get("exit_code")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        return False
    next_restart_at = health.get("next_restart_at")
    if next_restart_at is not None and not isinstance(next_restart_at, str):
        return False
    try:
        updated = datetime.fromisoformat(health["updated_at"])
        if updated.tzinfo is None or updated.utcoffset() is None:
            return False
        updated = updated.astimezone(timezone.utc)
        current = now or datetime.now(timezone.utc)
        age = current - updated
        if health["status"] == "backoff":
            if next_restart_at is None:
                return False
            restart_at = datetime.fromisoformat(next_restart_at)
            if restart_at.tzinfo is None or restart_at.utcoffset() is None:
                return False
            until_restart = restart_at.astimezone(timezone.utc) - updated
            if until_restart < timedelta(0) or until_restart > timedelta(seconds=MAX_SUPERVISOR_BACKOFF_SECONDS) + LOOP_HEALTH_GRACE:
                return False
        elif next_restart_at is not None:
            return False
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return -LOOP_HEALTH_GRACE <= age <= MAX_SUPERVISOR_HEALTH_AGE


def _write_supervisor_health(
    instance_root: Path, status: str, restart_count: int, consecutive_crashes: int,
    exit_code: int | None, next_restart_at: datetime | None = None,
    *, now: datetime | None = None,
) -> None:
    """Atomically write bounded health only; never persist tenant paths or errors."""
    if status not in SUPERVISOR_STATUSES:
        raise ValueError("unsupported supervisor status")
    if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= MAX_SUPERVISOR_CRASHES
           for value in (restart_count, consecutive_crashes)):
        raise ValueError("invalid supervisor counters")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        raise ValueError("invalid supervisor exit code")
    instance_root = Path(instance_root)
    if _is_link_or_junction(instance_root):
        raise OSError("unsafe supervisor health path")
    root = instance_root.resolve(strict=True)
    state = _safe_status_path(root, "state")
    target = _safe_status_path(root, SUPERVISOR_HEALTH_RELATIVE)
    if state is None or target is None or _is_link_or_junction(root):
        raise OSError("unsafe supervisor health path")
    state.mkdir(parents=True, exist_ok=True)
    if not state.is_dir() or _is_link_or_junction(state) or state.resolve(strict=True) != state:
        raise OSError("unsafe supervisor health path")
    temporary = _safe_status_path(root, f"state/.supervisor-health.{os.getpid()}.{time.time_ns()}.tmp")
    if temporary is None:
        raise OSError("unsafe supervisor health path")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload = {
        "schema_version": 1, "status": status, "restart_count": restart_count,
        "consecutive_crashes": consecutive_crashes, "exit_code": exit_code,
        "updated_at": timestamp.isoformat(),
        "next_restart_at": next_restart_at.astimezone(timezone.utc).isoformat() if next_restart_at else None,
    }
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
            stream.flush()
            os.fsync(stream.fileno())
        if (
            _is_link_or_junction(root)
            or _safe_status_path(root, "state") != state
            or _safe_status_path(root, SUPERVISOR_HEALTH_RELATIVE) != target
            or _safe_status_path(root, temporary.relative_to(root).as_posix()) != temporary
        ):
            raise OSError("unsafe supervisor health path changed")
        os.replace(temporary, target)
    finally:
        with contextlib.suppress(OSError):
            if temporary.exists() and not _is_link_or_junction(temporary):
                temporary.unlink()


@contextlib.contextmanager
def _supervisor_lock(instance_root: Path):
    """One supervisor per instance; OS locks release automatically after a crash."""
    instance_root = Path(instance_root)
    if _is_link_or_junction(instance_root):
        raise OSError("unsafe supervisor lock path")
    root = instance_root.resolve(strict=True)
    if os.name == "nt":
        # A named kernel mutex has no tenant path on disk and releases on process death.
        import ctypes
        from ctypes import wintypes

        identity = hashlib.sha256(str(root).casefold().encode("utf-8")).hexdigest()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, f"Global\\AIStudioXYZ.Supervisor.{identity}")
        if not handle:
            raise OSError("unable to create supervisor mutex")
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS, including same process
            kernel32.CloseHandle(handle)
            raise RuntimeError("supervisor already running for this instance")
        result = kernel32.WaitForSingleObject(handle, 0)
        if result not in {0, 0x80}:  # WAIT_OBJECT_0 / WAIT_ABANDONED
            kernel32.CloseHandle(handle)
            if result == 0x102:  # WAIT_TIMEOUT
                raise RuntimeError("supervisor already running for this instance")
            raise OSError("unable to acquire supervisor mutex")
        try:
            yield
        finally:
            kernel32.ReleaseMutex(handle)
            kernel32.CloseHandle(handle)
        return

    lock_path = _safe_status_path(root, SUPERVISOR_LOCK_RELATIVE)
    if lock_path is None:
        raise OSError("unsafe supervisor lock path")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if _is_link_or_junction(lock_path.parent) or lock_path.parent.resolve(strict=True) != lock_path.parent:
        raise OSError("unsafe supervisor lock path")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        if _is_link_or_junction(lock_path) or os.fstat(descriptor).st_ino != lock_path.lstat().st_ino:
            raise OSError("unsafe supervisor lock path")
        stream = os.fdopen(descriptor, "a+", encoding="utf-8")
    except Exception:
        os.close(descriptor)
        raise
    try:
        try:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("supervisor already running for this instance") from exc
        yield
    finally:
        with contextlib.suppress(OSError):
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            stream.close()


def _supervise_instance(
    instance_root: Path, config: dict[str, Any], *, child_factory: Any = subprocess.Popen,
    sleep: Any = time.sleep, now: Any = lambda: datetime.now(timezone.utc),
) -> int:
    """Restart unexpected loop exits with bounded backoff, then freeze fail-closed."""
    _required, threshold, base_backoff, max_backoff = _supervisor_config(config)
    restarts = crashes = 0
    exit_code: int | None = None
    with _supervisor_lock(instance_root):
        try:
            while True:
                _write_supervisor_health(instance_root, "running", restarts, crashes, exit_code, now=now())
                try:
                    child = child_factory([sys.executable, str(ROOT / "agent_cli.py"), "run", "--instance", str(instance_root), "--loop"])
                    # Poll rather than a blocking wait so a healthy long-lived child refreshes health.
                    while (polled := child.poll()) is None:
                        sleep(SUPERVISOR_HEARTBEAT_SECONDS)
                        _write_supervisor_health(instance_root, "running", restarts, crashes, None, now=now())
                    exit_code = polled
                except OSError:
                    exit_code = 1
                # A child has no trusted "clean stop" protocol. Any exit is unexpected;
                # only an explicit operator interrupt of this supervisor writes stopped.
                crashes += 1
                if crashes >= threshold:
                    _write_supervisor_health(instance_root, "frozen", restarts, crashes, exit_code, now=now())
                    print("Supervisor eingefroren: Crash-Grenze erreicht. Betreiber-Eingriff erforderlich.")
                    return 1
                delay = min(base_backoff * (2 ** (crashes - 1)), max_backoff)
                restart_at = now() + timedelta(seconds=delay)
                remaining = delay
                while remaining:
                    _write_supervisor_health(
                        instance_root, "backoff", restarts, crashes, exit_code,
                        restart_at, now=now(),
                    )
                    chunk = min(remaining, SUPERVISOR_HEARTBEAT_SECONDS)
                    sleep(chunk)
                    remaining -= chunk
                restarts += 1
        except KeyboardInterrupt:
            # Do not leave a child loop behind when the operator stops the supervisor.
            child_running = False
            if "child" in locals():
                try:
                    child_running = child.poll() is None
                except KeyboardInterrupt:
                    child_running = False
            if child_running:
                with contextlib.suppress(OSError):
                    child.terminate()
                try:
                    child.wait(timeout=10)
                except (OSError, subprocess.TimeoutExpired):
                    with contextlib.suppress(OSError):
                        child.kill()
                    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                        child.wait(timeout=5)
            _write_supervisor_health(instance_root, "stopped", restarts, crashes, exit_code, now=now())
            print("Supervisor gestoppt.")
            return 0


def _print_pilot_status(instance: Path) -> int:
    """Show a compact, read-only traffic light for a generated pilot instance."""
    try:
        instance = instance.resolve(strict=True)
    except OSError:
        print("\nKMU-Pilotstatus\n───────────────\n  Ampel: ROT – Instanz fehlt")
        return 1
    if _tree_contains_symlink(instance / "project"):
        print(
            "\nKMU-Pilotstatus\n───────────────\n"
            "  Ampel: ROT – unsicherer Projektpfad"
        )
        return 1
    validation = _validate_instance(instance)
    if not validation.ok:
        _print_self_test(validation)
        return 1
    tenant_id, agent_id = _instance_identity(instance)
    config, config_invalid = _read_status_json(instance, "project/config.json")
    latest_relative = "artifacts/latest-controlling-report.json"
    latest_path = _safe_status_path(instance, latest_relative)
    latest, latest_invalid = _read_status_json(instance, latest_relative)
    state_relative = "state/adaptive-schedule.json"
    state_path = _safe_status_path(instance, state_relative)
    state, state_invalid = _read_status_json(instance, state_relative)
    health_relative = "state/loop-health.json"
    health_path = _safe_status_path(instance, health_relative)
    health, health_invalid = _read_status_json(instance, health_relative)
    supervisor_health, supervisor_health_invalid = _read_status_json(
        instance, SUPERVISOR_HEALTH_RELATIVE
    )

    acceptance = read_acceptance_status(instance)
    repeatable = acceptance.get("repeatable_run_count", 0)
    repeatable = (
        repeatable
        if isinstance(repeatable, int) and not isinstance(repeatable, bool)
        else 0
    )
    displayed_repeatable = min(max(repeatable, 0), 3)
    accepted = acceptance.get("passed") is True
    schedule = config.get("adaptive_schedule", {}) if isinstance(config, dict) else {}
    schedule = schedule if isinstance(schedule, dict) else {}
    max_failures = schedule.get("max_consecutive_failures", 3)
    max_failures = (
        max_failures
        if isinstance(max_failures, int)
        and not isinstance(max_failures, bool)
        and max_failures > 0
        else 3
    )
    failures = state.get("consecutive_failures", 0)
    failures = (
        failures
        if isinstance(failures, int) and not isinstance(failures, bool) and failures >= 0
        else max_failures
    )
    last_result = state.get("last_result")
    try:
        interval = _loop_interval_minutes(config)
        supervisor_required, _threshold, _base_backoff, _max_backoff = _supervisor_config(config)
        interval_invalid = False
    except ValueError:
        interval = 60
        supervisor_required = True
        interval_invalid = True
    health_fresh = (
        health_path is not None
        and health_path.exists()
        and not health_invalid
        and _loop_health_is_fresh(health, interval)
    )
    supervisor_fresh = (
        not supervisor_required
        or (
            not supervisor_health_invalid
            and _supervisor_health_is_fresh(supervisor_health)
            and supervisor_health.get("status") in {"running", "backoff"}
        )
    )
    provenance = latest.get("provenance") if isinstance(latest, dict) else None
    signed_sequence = acceptance.get("sequence", 0)
    human_relative = "artifacts/latest-controlling-report.html"
    human_path = _safe_status_path(instance, human_relative)
    view_consistent = (
        isinstance(provenance, dict)
        and provenance.get("sequence") == signed_sequence
        and provenance.get("run_signature") == acceptance.get("run_signature")
        if isinstance(signed_sequence, int) and signed_sequence > 0
        else (
            latest_path is not None
            and human_path is not None
            and not latest_path.exists()
            and not human_path.exists()
        )
    )
    human_view_verified = (
        _verified_management_report_view(instance, latest)
        if isinstance(signed_sequence, int) and signed_sequence > 0 and view_consistent
        else False
    )
    last_result_at, timestamp_invalid = _status_timestamp(
        state.get("last_result_at")
    )
    status_invalid = (
        config_invalid
        or latest_invalid
        or state_invalid
        or acceptance.get("valid") is not True
        or not view_consistent
        or (isinstance(signed_sequence, int) and signed_sequence > 0 and not human_view_verified)
        or timestamp_invalid
        or last_result not in {None, "success", "failed"}
        or interval_invalid
        or not health_fresh
        or not supervisor_fresh
    )
    loop_failed = last_result == "failed" or failures >= max_failures
    loop_healthy = (
        state_path is not None
        and state_path.exists()
        and last_result == "success"
        and failures == 0
        and health_fresh
    )

    if status_invalid or loop_failed:
        light = "ROT – Eingriff erforderlich"
        next_step = "Fehler beheben und den Stundenloop kontrolliert erneut starten."
        return_code = 1
    elif accepted and loop_healthy:
        light = "GRÜN – pilotbereit"
        next_step = "Den 30-Tage-Pilot überwacht fortführen."
        return_code = 0
    else:
        light = "GELB – Pilot noch nicht vollständig abgenommen"
        if latest_path is None or not latest_path.exists():
            next_step = "Den ersten belegten Managementbericht erzeugen."
        elif repeatable < 3:
            next_step = "Den identischen validierten Lauf bis 3/3 wiederholen."
        else:
            next_step = "Den Stundenloop einmal ausführen und erneut prüfen."
        return_code = 1

    loop_result = str(last_result) if last_result else "noch nicht gelaufen"
    acceptance_label = "bestanden" if accepted else "offen"
    print("\nKMU-Pilotstatus")
    print("───────────────")
    print(f"  Instanz:          {tenant_id}/{agent_id}")
    print(f"  Ampel:            {light}")
    print(f"  Abnahme:          {acceptance_label} ({displayed_repeatable}/3)")
    print(
        f"  Stundenloop:      {loop_result}; Fehler {failures}/{max_failures}; "
        f"zuletzt {last_result_at}"
    )
    if supervisor_required:
        print(f"  Supervisor:       {supervisor_health.get('status', 'fehlt')}")
    if human_view_verified:
        print(f"  Managementreport: {human_path}")
    else:
        print("  Managementreport: nicht verfügbar bzw. nicht verifiziert")
    print(f"  Nächster Schritt: {next_step}")
    return return_code


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


def cmd_supervise(args: argparse.Namespace) -> int:
    """Run the optional external-process supervisor; task registration is operator-owned."""
    target_dir = Path(args.instance)
    report = _validate_instance(target_dir)
    if not report.ok:
        _print_self_test(report)
        return 1
    try:
        config = json.loads(
            (target_dir / "project" / "config.json").read_text(encoding="utf-8")
        )
        if not isinstance(config, dict):
            raise ValueError("invalid instance config")
        _supervisor_config(config)
        return _supervise_instance(target_dir, config)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Supervisor nicht gestartet: {exc}")
        return 1


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


def _write_loop_health(
    instance_root: Path, status: str, poll_result: str
) -> None:
    """Persist a heartbeat with ADR-0001 defense-in-depth path preflights.

    These portable checks complement, but do not replace, the ADR-mandated
    service identity and deployment/volume isolation boundary.
    """
    if status not in LOOP_HEALTH_STATUSES or poll_result not in LOOP_POLL_RESULTS:
        raise ValueError("unsupported loop health value")
    instance_root = Path(instance_root)
    if _is_link_or_junction(instance_root):
        raise OSError("unsafe instance root")
    try:
        root = instance_root.resolve(strict=True)
    except OSError as exc:
        raise OSError("unsafe instance root") from exc
    if not root.is_dir():
        raise OSError("unsafe instance root")
    state_dir = _safe_status_path(root, "state")
    if state_dir is None:
        raise OSError("unsafe loop health state path")
    state_dir.mkdir(parents=True, exist_ok=True)
    if (
        not state_dir.is_dir()
        or _is_link_or_junction(state_dir)
        or state_dir.resolve(strict=True) != state_dir
    ):
        raise OSError("unsafe loop health state path")
    target = _safe_status_path(root, "state/loop-health.json")
    temporary = _safe_status_path(
        root,
        f"state/.loop-health.{os.getpid()}.{time.time_ns()}.tmp",
    )
    if target is None or temporary is None:
        raise OSError("unsafe loop health file path")
    payload = {
        "schema_version": 1,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "poll_result": poll_result,
    }
    try:
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(
                json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            )
            stream.flush()
            os.fsync(stream.fileno())
        if (
            _safe_status_path(root, "state") != state_dir
            or _safe_status_path(root, "state/loop-health.json") != target
            or _safe_status_path(root, temporary.relative_to(root).as_posix())
            != temporary
        ):
            raise OSError("unsafe loop health path changed")
        os.replace(temporary, target)
    finally:
        try:
            if temporary.exists() and not _is_link_or_junction(temporary):
                temporary.unlink()
        except OSError:
            pass


def _decision_loop_health(decision: ScheduledDecision) -> tuple[str, str]:
    """Map only exhaustive, structurally consistent scheduler outcomes healthy."""
    if decision.should_enqueue and decision.reason in LOOP_WORK_REASONS:
        return "running", "success"
    if not decision.should_enqueue and decision.reason in {"idle", "already_enqueued"}:
        return "running", decision.reason
    return "error", "error"


def _run_instance_loop(
    instance_root: Path,
    config: dict[str, Any],
    tenant_id: str,
    orchestrator: Any,
) -> None:
    """Run a generated instance's adaptive scheduler at its configured interval."""
    interval = _loop_interval_minutes(config)
    print(
        f"Instanz-Loop gestartet: {tenant_id}/{config.get('agent_name', 'agent')} alle {interval} Minuten"
    )
    try:
        while True:
            try:
                decision = _run_instance_schedule_cycle(
                    instance_root, config, tenant_id, orchestrator
                )
                status, poll_result = _decision_loop_health(decision)
                _write_loop_health(instance_root, status, poll_result)
                if status == "running":
                    print(f"Schedule: {decision.reason}")
                else:
                    print("Schedule-Fehler: ungültige Scheduler-Entscheidung.")
            except Exception:
                _write_loop_health(instance_root, "error", "error")
                print("Schedule-Fehler: Poll fehlgeschlagen.")
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        _write_loop_health(instance_root, "stopped", "stopped")
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

    supervise = sub.add_parser(
        "supervise", help="Optionalen Loop-Supervisor für eine Instanz ausführen"
    )
    supervise.add_argument("--instance", required=True, help="Instance path <tenant>/<agent>")
    supervise.set_defaults(func=cmd_supervise)

    status = sub.add_parser("status", help="Template- oder Pilotstatus anzeigen")
    status.add_argument(
        "--instance",
        help="Pilot-Ampel für eine Instanz <tenant>/<agent> anzeigen",
    )
    status.add_argument(
        "--production",
        action="store_true",
        help="separate fail-closed Produktionsfreigabe mit externer Evidenz prüfen",
    )
    status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
