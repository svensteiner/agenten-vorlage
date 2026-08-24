"""Schema-locked controlling report validation."""

import json
from pathlib import Path

from core.controlling.report_schema import validate_controlling_report


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "presets" / "kmu-controlling" / "pilot" / "demo" / "expected-results.json"


def _golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_valid_golden_expected_results_pass():
    result = validate_controlling_report(_golden())
    assert result.ok is True
    assert result.errors == []


def test_valid_compute_shaped_report_pass():
    report = {
        "source": "inbox/actuals/Saldenliste_Muster_Juni2026.xlsx",
        "method": "mapping-defined account groups; month/prior/ytd aggregation",
        "report_metadata": {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "currency": "EUR",
            "sign_convention": "source_value_times_group_multiplier",
            "row_identifier": "Konto",
        },
        "metrics": {
            "ebitda": {"month": "2800", "prior": "3000", "ytd": "8400", "ytd_prior": "9000"},
            "egt": {"month": "-2250", "prior": "21780", "ytd": "66700", "ytd_prior": "105200"},
        },
        "reconciliation": {
            "source_account_count": 20,
            "mapped_account_count": 20,
            "ignored_account_count": 0,
            "mapped_source_period_totals": {"month": "0"},
            "grouped_period_totals": {"month": "0"},
        },
        "availability": {
            "budget_variance": {"status": "unavailable", "processing": "not_processed_by_this_pilot"}
        },
        "provenance": {
            "input_fingerprint": "a" * 64,
            "mapping_version": "b" * 64,
            "calculation_version": "kmu-report-v3",
        },
    }
    result = validate_controlling_report(report)
    assert result.ok is True, result.errors


def test_missing_key_fails():
    data = _golden()
    del data["reconciliation"]
    result = validate_controlling_report(data)
    assert result.ok is False
    assert any("missing key" in err and "reconciliation" in err for err in result.errors)


def test_extra_key_fails():
    data = _golden()
    data["invented_kpi"] = "999"
    result = validate_controlling_report(data)
    assert result.ok is False
    assert any("unknown field" in err and "invented_kpi" in err for err in result.errors)


def test_extra_nested_metadata_key_fails():
    data = _golden()
    data["report_metadata"] = {**data["report_metadata"], "extra_meta": "nope"}
    result = validate_controlling_report(data)
    assert result.ok is False
    assert any("unknown field" in err for err in result.errors)


def test_number_as_string_where_number_required_fails():
    data = _golden()
    data["reconciliation"]["source_account_count"] = "20"
    result = validate_controlling_report(data)
    assert result.ok is False
    joined = " ".join(result.errors).lower()
    assert "source_account_count" in joined
    assert "int" in joined


def test_verifier_rejects_schema_invalid_controlling_report(monkeypatch):
    from core.context import ProjectContext
    from core.controlling.tools import pilot_availability
    from core.verifier import Verifier
    import brain
    import json

    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("schema lock must short-circuit")),
    )

    computation = {
        "source": "inbox/actuals/demo.xlsx",
        "method": "mapping-defined account groups; month/prior/ytd aggregation",
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
        "mystery_field": "nope",
    }
    management = {
        "mode": "deterministic_fallback",
        "summary": "A. B. C.",
        "alarms": [],
        "actions": ["a", "b", "c"],
        "citations": {"source": computation["source"], "method": computation["method"]},
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
    assert result.passed is False
    assert result.metadata.get("mode") == "report_schema"
