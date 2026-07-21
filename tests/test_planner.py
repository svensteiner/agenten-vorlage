"""Planner — LLM-preferred with a deterministic rule fallback. The LLM path is
mocked via ``brain.complete``; the rule path runs offline (WP-C1 backfill)."""

import json
from pathlib import Path

import brain

from core.context import ProjectContext
from core.planner import Planner


class _Tool:
    def __init__(self, description=""):
        self.description = description


def _ctx(tmp_path=None, **kw) -> ProjectContext:
    return ProjectContext(project_root=tmp_path or Path("."), **kw)


# ── Rule fallback (brain.complete returns nothing) ──────────────────────────

def test_rules_used_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    plan = Planner().draft("do a simple thing")
    assert len(plan.steps) == 3
    assert [s.action for s in plan.steps] == ["inspect", "execute", "verify"]
    assert plan.confidence == 0.35


def test_rules_expand_manifest_workflow_steps(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    manifest = {"workflow": {"name": "intake", "steps": ["gather", "process", "finish"]}}
    plan = Planner().draft("run the intake", project=_ctx(manifest=manifest))
    assert plan.workflow_hint == "intake"
    assert [s.action for s in plan.steps] == ["inspect", "execute", "verify"]
    assert plan.confidence == 0.74


def test_kmu_workflow_uses_rules_without_llm_and_routes_kpi_compute(monkeypatch):
    calls = []
    monkeypatch.setattr(brain, "complete", lambda *a, **k: calls.append((a, k)))
    manifest = {"workflow": {"name": "kmu-controlling", "steps": [
        "Validate input", "Calculate KPIs deterministically", "Draft report",
    ]}}
    plan = Planner().draft("scheduled review", project=_ctx(manifest=manifest), tools={"compute": _Tool()})
    compute = next(step for step in plan.steps if step.tool == "compute")
    assert calls == []
    assert compute.input == '{"operation":"kmu_report","source":"auto"}'


def test_scheduler_missing_data_short_circuits_to_toolless_status_wait(monkeypatch):
    calls = []
    monkeypatch.setattr(brain, "complete", lambda *a, **k: calls.append((a, k)))
    manifest = {
        "workflow": {
            "name": "kmu-controlling",
            "steps": [
                "Validate input",
                "Calculate KPIs deterministically",
                "Draft report",
            ],
        },
    }
    task = (
        "Profil missing_data: Stoppe KPI-Aussagen.\n"
        'SCHEDULER_SIGNAL: {"missing_required_groups": '
        '[{"count": 0, "id": "actuals", "minimum": 1}], '
        '"reason": "missing_data"}'
    )

    plan = Planner().draft(
        task,
        project=_ctx(manifest=manifest),
        tools={"compute": _Tool(), "report": _Tool(), "notify": _Tool()},
    )

    assert calls == []
    assert [step.action for step in plan.steps] == ["status", "wait"]
    assert all(step.tool is None for step in plan.steps)
    assert "actuals" in plan.steps[0].description
    assert plan.workflow_hint == "kmu-controlling"


def test_llm_planner_honors_manifest_model(monkeypatch):
    called = {}

    def complete(*args, **kwargs):
        called["model"] = kwargs.get("model")
        return '{"steps":[{"id":"s","action":"inspect","description":"x"}]}'

    monkeypatch.setattr(brain, "complete", complete)
    Planner().draft("task", project=_ctx(manifest={"model": {"planner": "cheap-model"}}))
    assert called["model"] == "cheap-model"


def test_rules_match_named_workflow_from_project(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    ctx = _ctx(workflows={"daily_report": "First line of the workflow\nmore"})
    plan = Planner().draft("please run the daily report", project=ctx)
    assert plan.workflow_hint == "daily_report"
    assert any("execute_workflow" == s.action for s in plan.steps)
    assert plan.confidence == 0.55


def test_rules_flag_risky_workflow_step_for_human(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    manifest = {"workflow": {"name": "cleanup", "steps": ["scan", "delete old files", "confirm"]}}
    plan = Planner().draft("cleanup task", project=_ctx(manifest=manifest))
    assert any(s.requires_human for s in plan.steps)


# ── LLM path (brain.complete returns JSON) ──────────────────────────────────

def test_llm_plan_is_parsed_and_sanitized(monkeypatch):
    payload = {
        "workflow_hint": "analysis",
        "confidence": 0.9,
        "steps": [
            {"id": "step_1", "action": "inspect", "description": "look", "tool": None},
            {"id": "step_2", "action": "use_tool", "description": "search web", "tool": "web_search", "input": "q"},
            {"id": "step_3", "action": "verify", "description": "check", "tool": None},
        ],
        "notes": ["a note"],
    }
    monkeypatch.setattr(brain, "complete", lambda *a, **k: json.dumps(payload))
    plan = Planner().draft("analyze the market", tools={"web_search": _Tool("search")})
    assert plan.confidence == 0.9
    assert plan.steps[-1].action == "verify"  # verify steps are moved to the end
    assert all(s.metadata.get("source") == "llm" for s in plan.steps)


def test_llm_drops_unknown_tool_names(monkeypatch):
    payload = {"steps": [{"id": "s1", "action": "use_tool", "description": "d", "tool": "ghost_tool"}]}
    monkeypatch.setattr(brain, "complete", lambda *a, **k: json.dumps(payload))
    plan = Planner().draft("task", tools={"web_search": _Tool()})
    assert plan.steps[0].tool is None


def test_llm_strips_notify_when_task_does_not_ask_for_it(monkeypatch):
    payload = {"steps": [
        {"id": "s1", "action": "execute", "description": "work", "tool": None},
        {"id": "s2", "action": "use_tool", "description": "tell", "tool": "notify", "input": "x"},
    ]}
    monkeypatch.setattr(brain, "complete", lambda *a, **k: json.dumps(payload))
    plan = Planner().draft("do work quietly", tools={"notify": _Tool()})
    assert all(s.tool != "notify" for s in plan.steps)


def test_llm_falls_back_to_rules_on_unparseable_json(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "not json at all")
    plan = Planner().draft("plain task")
    assert len(plan.steps) == 3  # rule fallback shape


# ── Private helpers ─────────────────────────────────────────────────────────

def test_parse_json_extracts_fenced_block():
    fenced = "```json\n{\"a\": 1}\n```"
    assert Planner()._parse_json(fenced) == {"a": 1}


def test_guess_tool_picks_web_search():
    tool, inp = Planner()._guess_tool("recherchiere das", "web recherche", {"web_search": _Tool()})
    assert tool == "web_search"
    assert inp == "recherchiere das"


def test_guess_tool_reads_file_path():
    tool, inp = Planner()._guess_tool("lies README.md", "read step", {"file": _Tool()})
    assert tool == "file"
    assert inp.startswith("read:")


def test_looks_risky_detects_destructive_terms():
    assert Planner()._looks_risky("delete everything", "") is True
    assert Planner()._looks_risky("read the docs", "") is False


def test_file_input_plausible_rejects_outside_project(tmp_path):
    ok, reason = Planner()._file_input_is_plausible("read:../../etc/passwd", _ctx(tmp_path=tmp_path))
    assert ok is False


def test_file_input_plausible_accepts_write():
    ok, _ = Planner()._file_input_is_plausible("write:out.txt|content", _ctx())
    assert ok is True


def test_repair_project_file_input_prefixes_project(tmp_path):
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "notes.md").write_text("hi", encoding="utf-8")
    repaired = Planner()._repair_project_file_input("read:notes.md", _ctx(tmp_path=tmp_path))
    assert repaired == "read:project/notes.md"
