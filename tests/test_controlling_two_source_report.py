import hashlib
import json

import pytest

import core.controlling.narrative as narrative_module
from core.controlling.artifacts import read_acceptance_status
from core.controlling.narrative import ControllingReportTool


ACTUAL_SOURCE = "data/actuals.csv"
BUDGET_SOURCE = "imports/budget.csv"
TWO_SOURCE_REQUEST = {
    "actual_source": ACTUAL_SOURCE,
    "budget_source": BUDGET_SOURCE,
}


def _mapping():
    return {
        "schema_version": 1,
        "report_metadata": {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "currency": "EUR",
            "sign_convention": "source_value_times_group_multiplier",
            "row_identifier": "Zeilen-ID",
        },
        "columns": {
            "account_id": "Konto",
            "account_name": "Bezeichnung",
            "month": "Monat",
            "prior": "Vormonat",
            "ytd": "YTD",
            "ytd_prior": "YTD Vorjahr",
        },
        "sign_semantics": {
            "formula": "normalized_value = source_value * group.multiplier",
            "positive_contribution": "Positive increases KPI.",
            "negative_contribution": "Negative decreases KPI.",
        },
        "source_globs": ["data/*.csv", "imports/*.csv"],
        "groups": {
            "revenue": {"prefixes": ["4"], "multiplier": 1},
            "costs": {"prefixes": ["5"], "multiplier": -1},
        },
        "metrics": {
            "ebitda": ["revenue", "costs"],
            "depreciation": ["costs"],
            "egt": ["revenue", "costs"],
        },
        "thresholds": {"material_deviation_abs": 1},
    }


def _write_two_source_instance(tmp_path, *, budget_revenue="800"):
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "imports").mkdir(exist_ok=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "actuals.csv").write_text(
        "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD;YTD Vorjahr\n"
        "actual-revenue;4000;Umsatz;1000;900;6000;5000\n"
        "actual-cost;5000;Material;300;250;1800;1500\n",
        encoding="utf-8",
    )
    (tmp_path / "imports" / "budget.csv").write_text(
        "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD;YTD Vorjahr\n"
        f"budget-revenue;4000;Umsatz;{budget_revenue};750;4800;4200\n"
        "budget-cost;5000;Material;250;200;1500;1200\n",
        encoding="utf-8",
    )
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        json.dumps(_mapping()), encoding="utf-8"
    )
    (tmp_path / "project" / "config.json").write_text(
        json.dumps({"autonomy_level": "standard", "require_human_approval": True}),
        encoding="utf-8",
    )
    (tmp_path / "project" / "manifest.json").write_text(
        json.dumps(
            {
                "autonomy_level": "standard",
                "approval_required_for": ["external communication", "send", "publish"],
                "tool_permissions": {
                    "default": "disabled",
                    "enabled": ["read", "compute", "report"],
                },
            }
        ),
        encoding="utf-8",
    )


def _run(tool, request):
    return tool.safe_run(json.dumps(request, ensure_ascii=False, separators=(",", ":")))


def _ledger_runs(tmp_path):
    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]


def test_two_source_report_persists_deterministic_variance_draft_and_views(tmp_path):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)

    first = json.loads(_run(tool, TWO_SOURCE_REQUEST))
    second = json.loads(_run(tool, TWO_SOURCE_REQUEST))
    latest = json.loads(
        (tmp_path / second["artifact"]).read_text(encoding="utf-8")
    )
    markdown = (tmp_path / "artifacts" / "latest-controlling-report.md").read_text(
        encoding="utf-8"
    )
    html = (tmp_path / second["human_artifact"]).read_text(encoding="utf-8")

    assert first["mode"] == second["mode"] == "deterministic_fallback"
    assert first["summary"] == second["summary"]
    assert first["alarms"] == second["alarms"]
    assert first["actions"] == second["actions"]
    assert first["variance"] == second["variance"]
    assert first["variance"]["metrics"]["ebitda"] == {
        "actual": "700",
        "budget": "550",
        "delta": "150",
        "relative_delta_percent": "27.27272727272727272727272727",
    }
    assert not any("Budgetabweichung nicht verf" in alarm for alarm in first["alarms"])
    assert latest["management"]["variance"] == second["variance"]
    assert "variance" not in latest["report"]
    assert latest["report"]["availability"]["budget_variance"] == {
        "status": "available",
        "processing": "two_source_actual_vs_budget",
    }
    for value in ("revenue", "1000", "800", "200"):
        assert value in markdown
        assert value in html


def test_legacy_single_source_draft_remains_byte_compatible(tmp_path, monkeypatch):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(narrative_module, "persist_report_artifacts", lambda *_args, **_kwargs: None)

    result = _run(tool, {"source": ACTUAL_SOURCE})

    expected = {
        "mode": "deterministic_fallback",
        "summary": (
            "Der Bericht basiert auf der geprüften Quelle. "
            "EBITDA im Monat: 700. EGT im Monat: 700."
        ),
        "alarms": [
            "Materielle Abweichungen: 2.",
            "Budgetabweichung nicht verfügbar: in diesem Piloten nicht verarbeitet.",
            "Forderungsalterung nicht verfügbar: in diesem Piloten nicht verarbeitet.",
        ],
        "actions": [
            "Kontenzuordnung prüfen.",
            "Abweichungen priorisieren.",
            "Management-Entwurf intern freigeben.",
        ],
        "citations": {
            "source": ACTUAL_SOURCE,
            "method": "mapping-defined account groups; month/prior/ytd aggregation",
        },
    }
    assert result == json.dumps(expected, ensure_ascii=False, separators=(",", ":"))


@pytest.mark.parametrize(
    "report_request",
    [
        {"actual_source": ACTUAL_SOURCE},
        {"budget_source": BUDGET_SOURCE},
        {"actual_source": ACTUAL_SOURCE, "budget_source": "auto"},
        {"actual_source": "auto", "budget_source": BUDGET_SOURCE},
        {"source": ACTUAL_SOURCE, **TWO_SOURCE_REQUEST},
        {"source": ACTUAL_SOURCE, "budget_source": BUDGET_SOURCE},
    ],
    ids=("actual-only", "budget-only", "budget-auto", "actual-auto", "mixed", "mixed-partial"),
)
def test_two_source_report_rejects_partial_auto_and_mixed_requests_before_compute(
    tmp_path, monkeypatch, report_request
):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_args: pytest.fail("UngÃ¼ltige Zwei-Quellen-Anfrage darf nicht rechnen."),
    )

    assert _run(tool, report_request).startswith("FEHLER")


def test_three_identical_two_source_runs_are_accepted_and_ledger_binds_both_inputs(
    tmp_path,
):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)

    drafts = [json.loads(_run(tool, TWO_SOURCE_REQUEST)) for _ in range(3)]
    actual = tmp_path / ACTUAL_SOURCE
    budget = tmp_path / BUDGET_SOURCE
    latest_run = _ledger_runs(tmp_path)[-1]
    status = read_acceptance_status(tmp_path)

    assert drafts[-1]["acceptance"]["passed"] is True
    assert drafts[-1]["acceptance"]["repeatable_run_count"] == 3
    assert status["valid"] is True
    assert status["passed"] is True
    assert latest_run["source_file"] == ACTUAL_SOURCE
    assert latest_run["input_fingerprint"] == hashlib.sha256(actual.read_bytes()).hexdigest()
    assert latest_run["budget_source_file"] == BUDGET_SOURCE
    assert latest_run["budget_input_fingerprint"] == hashlib.sha256(budget.read_bytes()).hexdigest()


def test_budget_change_invalidates_signed_two_source_status_and_resets_runs(tmp_path):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)

    for _ in range(3):
        _run(tool, TWO_SOURCE_REQUEST)
    assert read_acceptance_status(tmp_path)["passed"] is True
    _write_two_source_instance(tmp_path, budget_revenue="801")

    invalidated = read_acceptance_status(tmp_path)
    next_draft = json.loads(_run(tool, TWO_SOURCE_REQUEST))

    assert invalidated["valid"] is False
    assert invalidated["passed"] is False
    assert next_draft["acceptance"]["passed"] is False
    assert next_draft["acceptance"]["repeatable_run_count"] == 1


def test_operation_id_rejects_budget_change_instead_of_replaying_old_two_source_run(
    tmp_path,
):
    _write_two_source_instance(tmp_path)
    tool = ControllingReportTool(tmp_path)
    request = {**TWO_SOURCE_REQUEST, "operation_id": "two-source-budget-binding"}

    first = _run(tool, request)
    _write_two_source_instance(tmp_path, budget_revenue="801")
    changed = _run(tool, request)

    assert not first.startswith("FEHLER")
    assert changed.startswith("FEHLER")
    assert "Operation-ID" in changed
