"""Verifier — the single answer gate. Heuristic paths need no model; the LLM
path is exercised with a mocked ``brain.evaluate`` so the test is deterministic
regardless of environment/API keys (WP-C1 mocked-model backfill)."""

import json
from pathlib import Path

import brain
from core.controlling.tools import pilot_availability

from core.context import ProjectContext
from core.verifier import Verifier


def _ctx(**config) -> ProjectContext:
    return ProjectContext(project_root=Path("."), config=config)


def test_empty_output_fails():
    result = Verifier().verify("   ")
    assert result.passed is False
    assert result.score == 0
    assert "Empty output" in result.feedback


def test_error_looking_output_fails_heuristically():
    result = Verifier().verify("Traceback: something raised an Exception")
    assert result.passed is False
    assert result.score == 2
    assert result.metadata["mode"] == "heuristic"


def test_placeholder_output_fails_and_offers_repair():
    result = Verifier().verify("Here is the plan.\n[fill in] the details later.")
    assert result.passed is False
    assert result.score == 4
    assert result.improved_output is not None
    assert "[fill in]" not in result.improved_output
    assert result.metadata["reason"] == "placeholder"


def test_heuristic_pass_on_substantial_relevant_output(monkeypatch):
    # No LLM available → heuristic scoring; long output containing a task term.
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    output = "The migration strategy analysis is complete. " * 3
    result = Verifier().verify(output, task="migration strategy analysis", step="final")
    assert result.metadata["mode"] == "heuristic"
    assert result.score >= 7
    assert result.passed is True


def test_heuristic_fail_on_thin_output(monkeypatch):
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    result = Verifier().verify("done", task="quarterly financial reconciliation report")
    assert result.metadata["mode"] == "heuristic"
    assert result.passed is False


def test_context_quality_threshold_overrides_default(monkeypatch):
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    # A permissive threshold of 3 lets the base heuristic score (6) pass.
    result = Verifier().verify("a short but acceptable answer", context=_ctx(quality_threshold="3"))
    assert result.metadata["threshold"] == 3
    assert result.passed is True


def test_invalid_context_threshold_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    result = Verifier().verify("x" * 90, task="anything", context=_ctx(quality_threshold="not-a-number"))
    assert result.metadata["threshold"] == 7


def test_llm_path_is_used_when_evaluation_present(monkeypatch):
    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: {
            "score": 9,
            "passes": True,
            "feedback": ["clear and grounded"],
            "improved_version": "an even better answer",
        },
    )
    result = Verifier().verify("a plausible answer", task="t", step="s")
    assert result.metadata["mode"] == "llm"
    assert result.score == 9
    assert result.passed is True
    assert result.improved_output == "an even better answer"


def test_llm_unavailable_marker_falls_back_to_heuristic(monkeypatch):
    # brain returns a fallback dict carrying the "LLM nicht verfügbar" marker →
    # the verifier must NOT treat it as a real evaluation.
    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: {"score": 5, "feedback": ["LLM nicht verfügbar — heuristik"]},
    )
    result = Verifier().verify("x" * 90, task="topic")
    assert result.metadata["mode"] == "heuristic"


def test_sourced_kmu_report_passes_deterministically_without_verifier_llm(monkeypatch):
    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("deterministic controlling evidence needs no verifier LLM")
        ),
    )
    source = "inbox/actuals/demo.xlsx"
    method = "mapping-defined account groups; month/prior/ytd aggregation"
    computation = {
        "source": source,
        "method": method,
        "metrics": {
            "ebitda": {"month": "2800", "prior": "3000", "ytd": "8400", "ytd_prior": "9000"},
            "depreciation": {"month": "-3000", "prior": "-2900", "ytd": "-9000", "ytd_prior": "-8500"},
            "egt": {"month": "-2250", "prior": "21780", "ytd": "66700", "ytd_prior": "105200"},
        },
        "reconciliation": {
            "source_account_count": 20,
            "mapped_account_count": 20,
            "ignored_account_count": 0,
        },
        "availability": pilot_availability(),
        "provenance": {
            "input_fingerprint": "a" * 64,
            "mapping_version": "b" * 64,
            "calculation_version": "kmu-report-v3",
        },
    }
    management = {
        "mode": "deterministic_fallback",
        "summary": "A. B. C.",
        "alarms": [],
        "actions": ["a", "b", "c"],
        "citations": {"source": source, "method": method},
    }
    context = ProjectContext(
        project_root=Path("."),
        config={"quality_threshold": 8},
        manifest={"workflow": {"name": "kmu-controlling"}},
    )

    result = Verifier().verify(
        "\n".join((json.dumps(computation), json.dumps(management))),
        task="Erstelle den belegten Monatsreport",
        context=context,
    )

    assert result.passed is True
    assert result.score >= 8
    assert result.metadata["mode"] == "deterministic_controlling"


def test_scheduler_missing_data_status_passes_without_verifier_llm(monkeypatch):
    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("scheduler status needs no verifier LLM")
        ),
    )
    signal = {
        "event_id": "schedule-1234567890abcdef1234",
        "input_count": 0,
        "missing_required_groups": [
            {"id": "actuals", "count": 0, "minimum": 1},
            {"id": "account_mapping", "count": 0, "minimum": 1},
        ],
        "reason": "missing_data",
        "reasons": ["missing_data"],
        "required_input_counts": [0, 0],
    }
    task = "Profil missing_data.\nSCHEDULER_SIGNAL: " + json.dumps(signal)
    output = (
        "Planned step recorded: Scheduled status missing_data: required input "
        "groups are incomplete: actuals, account_mapping. KPI computation and "
        "external actions remain paused.\n"
        "Planned step recorded: Wait for the required inputs and resume only "
        "after the scheduler validates every required group."
    )
    context = ProjectContext(
        project_root=Path("."),
        config={"quality_threshold": 8},
        manifest={"workflow": {"name": "kmu-controlling"}},
    )

    result = Verifier().verify(output, task=task, context=context)

    assert result.passed is True
    assert result.metadata["mode"] == "deterministic_missing_data"
