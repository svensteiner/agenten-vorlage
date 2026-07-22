from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from multiprocessing import get_context
import os
from pathlib import Path
import threading
import time

import pytest

from core.controlling import artifacts as artifacts_module
from core.controlling.artifacts import persist_report_artifacts, read_acceptance_status
from core.controlling.narrative import ControllingReportTool
from core.controlling.tools import ControllingComputeTool


def _hold_acceptance_lock_in_process(root, ready, *, crash=False):
    with artifacts_module._acceptance_write_lock(root):
        ready.set()
        if crash:
            os._exit(0)
        time.sleep(0.5)


def _acceptance_mapping():
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
        "source_globs": ["inbox/actuals/*.csv"],
        "groups": {
            "revenue": {"prefixes": ["4"], "multiplier": 1},
            "material": {"prefixes": ["5"], "multiplier": -1},
            "personnel": {"prefixes": ["6"], "multiplier": -1},
            "depreciation": {"prefixes": ["7"], "multiplier": -1},
            "financial": {"prefixes": ["8"], "multiplier": -1},
        },
        "metrics": {
            "ebitda": ["revenue", "material", "personnel"],
            "depreciation": ["depreciation"],
            "egt": [
                "revenue",
                "material",
                "personnel",
                "depreciation",
                "financial",
            ],
        },
        "thresholds": {"material_deviation_abs": 1000},
    }


def _write_acceptance_mapping(root):
    path = root / "project" / "pilot" / "account-mapping.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_acceptance_mapping()), encoding="utf-8")
    (root / "project" / "config.json").write_text(
        json.dumps({"autonomy_level": "standard", "require_human_approval": True}),
        encoding="utf-8",
    )
    (root / "project" / "manifest.json").write_text(
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


def _aggregate_report(root):
    source = root / "inbox" / "actuals" / "demo.csv"
    mapping = root / "project" / "pilot" / "account-mapping.json"
    return {
        "source": "inbox/actuals/demo.csv",
        "method": "mapping-defined account groups; month/prior/ytd aggregation",
        "report_metadata": {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "currency": "EUR",
            "sign_convention": "source_value_times_group_multiplier",
            "row_identifier": ["account_id"],
        },
        "period_labels": {
            "month": "Monat",
            "prior": "Vormonat",
            "ytd": "YTD",
            "ytd_prior": "YTD Vorjahr",
        },
        "sign_convention": "source_value_times_group_multiplier",
        "sign_convention_note": (
            "Vorzeichen: Quellwert × Gruppen-Multiplikator; positive Werte erhöhen "
            "die Kennzahl, negative Werte verringern sie."
        ),
        "metrics": {
            "ebitda": {"month": "2800", "prior": "3000", "ytd": "10000", "ytd_prior": "-5000", "account_ids": ["4000", "5000", "6000"]},
            "depreciation": {"month": "-3000", "prior": "-2900", "ytd": "-9000", "ytd_prior": "-8500", "account_ids": ["7000"]},
            "egt": {"month": "-2250", "prior": "-1900", "ytd": "-5000", "ytd_prior": "-19000", "account_ids": ["4000", "5000", "6000", "7000", "8000"]},
            "material_ratio": {
                "month": "0.5",
                "prior": "0.5",
                "ytd": "0.5",
                "ytd_prior": "0.5090909090909090909090909091",
                "account_ids": ["4000", "5000"],
            },
            "personnel_ratio": {
                "month": "0.4862407862407862407862407862",
                "prior": "0.485",
                "ytd": "0.4833333333333333333333333333",
                "ytd_prior": "0.5",
                "account_ids": ["4000", "6000"],
            },
        },
        "groups": {
            "revenue": {"month": "203500", "prior": "200000", "ytd": "600000", "ytd_prior": "550000", "account_ids": ["4000"], "row_count": 1},
            "material": {"month": "-101750", "prior": "-100000", "ytd": "-300000", "ytd_prior": "-280000", "account_ids": ["5000"], "row_count": 1},
            "personnel": {"month": "-98950", "prior": "-97000", "ytd": "-290000", "ytd_prior": "-275000", "account_ids": ["6000"], "row_count": 1},
            "depreciation": {"month": "-3000", "prior": "-2900", "ytd": "-9000", "ytd_prior": "-8500", "account_ids": ["7000"], "row_count": 1},
            "financial": {"month": "-2050", "prior": "-2000", "ytd": "-6000", "ytd_prior": "-5500", "account_ids": ["8000"], "row_count": 1},
        },
        "material_deviations": [
            {"account_id": "5000", "month_vs_prior": "-22600"}
        ],
        "reconciliation": {
            "source_account_count": 5,
            "mapped_account_count": 5,
            "ignored_account_count": 0,
            "mapped_source_period_totals": {
                "month": "-2250",
                "prior": "-1900",
                "ytd": "-5000",
                "ytd_prior": "-19000",
            },
            "grouped_period_totals": {
                "month": "-2250.00",
                "prior": -1900,
                "ytd": "-5000.0",
                "ytd_prior": "-19000",
            },
        },
        "provenance": {
            "input_fingerprint": hashlib.sha256(source.read_bytes()).hexdigest(),
            "mapping_version": hashlib.sha256(mapping.read_bytes()).hexdigest(),
            "calculation_version": "kmu-report-v1",
        },
        "raw_rows": [{"account_id": "4000", "customer": "must-not-persist"}],
    }


def _report_with_reconciled_totals():
    return {
        "source": "inbox/actuals/demo.csv",
        "method": "synthetic deterministic aggregation",
        "report_metadata": {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "currency": "EUR",
            "sign_convention": "source_value_times_group_multiplier",
        },
        "period_labels": {
            "month": "Monat",
            "prior": "Vormonat",
            "ytd": "YTD",
            "ytd_prior": "YTD Vorjahr",
        },
        "sign_convention": "source_value_times_group_multiplier",
        "sign_convention_note": (
            "Vorzeichen: Quellwert × Gruppen-Multiplikator; positive Werte erhöhen "
            "die Kennzahl, negative Werte verringern sie."
        ),
        "metrics": {
            "ebitda": {
                "month": "10",
                "prior": "9",
                "ytd": "29",
                "ytd_prior": "27",
                "account_ids": ["4000", "5000"],
            },
            "depreciation": {
                "month": "-2",
                "prior": "-2",
                "ytd": "-6",
                "ytd_prior": "-6",
                "account_ids": ["7000"],
            },
            "egt": {
                "month": "8",
                "prior": "7",
                "ytd": "23",
                "ytd_prior": "21",
                "account_ids": ["4000", "5000", "7000"],
            },
            "material_ratio": {
                "month": "0.5",
                "prior": "0.5",
                "ytd": "0.5",
                "ytd_prior": "0.5",
                "account_ids": ["4000", "5000"],
            },
            "receivables": {
                "month": "20",
                "prior": "19",
                "ytd": None,
                "ytd_prior": None,
                "account_ids": ["1200"],
            },
        },
        "groups": {
            "revenue": {
                "month": "20",
                "prior": "18",
                "ytd": "58",
                "ytd_prior": "54",
                "account_ids": ["4000"],
                "row_count": 1,
            },
            "material": {
                "month": "-10",
                "prior": "-9",
                "ytd": "-29",
                "ytd_prior": "-27",
                "account_ids": ["5000"],
                "row_count": 1,
            },
            "depreciation": {
                "month": "-2",
                "prior": "-2",
                "ytd": "-6",
                "ytd_prior": "-6",
                "account_ids": ["7000"],
                "row_count": 1,
            },
            "receivables": {
                "month": "20",
                "prior": "19",
                "ytd": None,
                "ytd_prior": None,
                "account_ids": ["1200"],
                "row_count": 1,
            },
            "unused_balance": {
                "month": None,
                "prior": None,
                "ytd": None,
                "ytd_prior": None,
                "account_ids": [],
                "row_count": 0,
            },
        },
        "reconciliation": {
            "source_account_count": 5,
            "mapped_account_count": 4,
            "ignored_account_count": 1,
            "mapped_source_period_totals": {
                "month": "28.00",
                "prior": 26,
                "ytd": "23.0",
                "ytd_prior": "21",
                "detail": "synthetic-extra",
            },
            "grouped_period_totals": {
                "month": 28,
                "prior": "26.000",
                "ytd": 23.0,
                "ytd_prior": "21.00",
                "detail": "different-extra-is-allowed",
            },
        },
    }


def _reconciliation_mapping():
    return {
        "columns": {
            "month": "Monat",
            "prior": "Vormonat",
            "ytd": "YTD",
            "ytd_prior": "YTD Vorjahr",
        },
        "groups": {
            "revenue": {},
            "material": {},
            "depreciation": {},
            "receivables": {},
            "unused_balance": {},
            "ignored_example": {"ignored": True},
        },
        "metrics": {
            "ebitda": ["revenue", "material"],
            "depreciation": ["depreciation"],
            "egt": ["revenue", "material", "depreciation"],
        },
    }


def test_sourced_totals_accept_decimal_equivalence_and_ignored_accounts():
    report = _report_with_reconciled_totals()

    assert artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report: report["period_labels"].update(month="Manipuliert"),
        lambda report: report.update(sign_convention="other"),
        lambda report: report.update(sign_convention_note="Freier Text"),
    ],
    ids=("period-label", "sign-code", "sign-note"),
)
def test_sourced_totals_rejects_altered_report_semantics(mutate):
    report = _report_with_reconciled_totals()
    mutate(report)

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_management_views_use_escaped_mapping_period_labels_and_sign_note(tmp_path):
    report = {
        "period_labels": {
            "month": "<Juni & Ist>",
            "prior": "Vormonat",
            "ytd": "YTD",
            "ytd_prior": "YTD Vorjahr",
        },
        "sign_convention_note": (
            "Vorzeichen: Quellwert × Gruppen-Multiplikator; positive Werte erhöhen "
            "die Kennzahl, negative Werte verringern sie."
        ),
        "metrics": {},
        "report_metadata": {},
    }
    payload = {
        "report": report,
        "management": {"summary": "synthetisch", "alarms": [], "actions": []},
        "acceptance": {"passed": False, "repeatable_run_count": 0},
    }

    html = artifacts_module.render_html(payload)
    markdown = artifacts_module._markdown(payload)

    assert "&lt;Juni &amp; Ist&gt;" in html
    assert "<Juni & Ist>" not in html
    assert "&lt;Juni &amp; Ist&gt;" in markdown
    assert "<Juni & Ist>" not in markdown
    assert report["sign_convention_note"] in html
    assert report["sign_convention_note"] in markdown


@pytest.mark.parametrize(
    "hostile",
    [
        "<img src=https://invalid.test/x>",
        "<script>alert(1)</script>",
        "A&B",
        "![x](//attacker.invalid/pixel)",
        "![x](https:\\/\\/attacker.invalid/pixel)",
        "[Link](https://attacker.invalid/click)",
    ],
)
def test_markdown_period_labels_are_always_plain_text(hostile):
    payload = {
        "report": {
            "period_labels": {period: hostile for period in ("month", "prior", "ytd", "ytd_prior")},
            "report_metadata": {},
            "metrics": {},
        },
        "management": {"summary": "synthetisch", "alarms": [], "actions": []},
        "acceptance": {"passed": False, "repeatable_run_count": 0},
    }

    markdown = artifacts_module._markdown(payload)

    assert "<img" not in markdown
    assert "<script" not in markdown
    assert "![x](" not in markdown
    assert "[Link](" not in markdown
    if hostile == "A&B":
        assert "&amp;" in markdown
    elif hostile.startswith("<"):
        assert "&lt;" in markdown
    else:
        assert "\\[" in markdown and "\\]\\(" in markdown


def test_sourced_totals_reject_ignored_group_in_report():
    report = _report_with_reconciled_totals()
    report["groups"]["ignored_example"] = {
        "month": "0",
        "prior": "0",
        "ytd": "0",
        "ytd_prior": "0",
        "account_ids": [],
        "row_count": 0,
    }

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("failure", ("missing", "wrong", "nonfinite"))
def test_sourced_totals_reject_invalid_derived_ratio(failure):
    report = _report_with_reconciled_totals()
    if failure == "missing":
        del report["metrics"]["material_ratio"]
    elif failure == "wrong":
        report["metrics"]["material_ratio"]["month"] = "0.6"
    else:
        report["metrics"]["material_ratio"]["month"] = "Infinity"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("semantics", ("zero_denominator", "none_numerator"))
def test_sourced_totals_accept_ratio_zero_and_none_semantics(semantics):
    report = _report_with_reconciled_totals()
    mapping = _reconciliation_mapping()
    if semantics == "zero_denominator":
        report["groups"]["revenue"]["month"] = "0"
        report["metrics"]["ebitda"]["month"] = "-10"
        report["metrics"]["egt"]["month"] = "-12"
        report["metrics"]["material_ratio"]["month"] = None
        report["reconciliation"]["mapped_source_period_totals"]["month"] = "8"
        report["reconciliation"]["grouped_period_totals"]["month"] = "8"
    else:
        report["groups"]["material"]["ytd"] = None
        report["metrics"]["ebitda"]["ytd"] = "58"
        report["metrics"]["egt"]["ytd"] = "52"
        report["metrics"]["material_ratio"]["ytd"] = None
        report["reconciliation"]["mapped_source_period_totals"]["ytd"] = "52"
        report["reconciliation"]["grouped_period_totals"]["ytd"] = "52"
        mapping["metrics"]["ebitda"] = ["revenue"]
        mapping["metrics"]["egt"] = ["revenue", "depreciation"]
        report["metrics"]["ebitda"] = {
            "month": "20", "prior": "18", "ytd": "58", "ytd_prior": "54",
            "account_ids": ["4000"],
        }
        report["metrics"]["egt"] = {
            "month": "18", "prior": "16", "ytd": "52", "ytd_prior": "48",
            "account_ids": ["4000", "7000"],
        }

    assert artifacts_module._sourced_totals_pass(report, mapping)


def test_sourced_totals_reject_missing_ytd_for_referenced_pnl_group():
    report = _report_with_reconciled_totals()
    report["groups"]["material"]["ytd"] = None

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_sourced_totals_reject_wrong_direct_balance_metric():
    report = _report_with_reconciled_totals()
    report["metrics"]["receivables"]["month"] = "21"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_sourced_totals_reject_unknown_metric():
    report = _report_with_reconciled_totals()
    report["metrics"]["unknown"] = {
        "month": "0",
        "prior": "0",
        "ytd": "0",
        "ytd_prior": "0",
        "account_ids": [],
    }

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("failure", ("missing", "wrong"))
def test_sourced_totals_reject_invalid_metric_account_ids(failure):
    report = _report_with_reconciled_totals()
    if failure == "missing":
        del report["metrics"]["ebitda"]["account_ids"]
    else:
        report["metrics"]["ebitda"]["account_ids"] = ["5000", "4000"]

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("account_error", ("duplicate", "missing"))
def test_sourced_totals_reject_incomplete_or_duplicate_account_ids(account_error):
    report = _report_with_reconciled_totals()
    if account_error == "duplicate":
        report["groups"]["material"]["account_ids"] = ["4000"]
    else:
        report["groups"]["material"]["account_ids"] = []

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("bad_row_count", (None, 0, True))
def test_sourced_totals_reject_missing_wrong_or_bool_row_count(bad_row_count):
    report = _report_with_reconciled_totals()
    if bad_row_count is None:
        del report["groups"]["material"]["row_count"]
    else:
        report["groups"]["material"]["row_count"] = bad_row_count

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("shape_error", ("phantom_rows", "numeric_empty", "ids_without_rows"))
def test_sourced_totals_reject_non_producer_group_shape(shape_error):
    report = _report_with_reconciled_totals()
    group = report["groups"]["unused_balance"]
    if shape_error == "phantom_rows":
        group["row_count"] = 1
    elif shape_error == "numeric_empty":
        group["month"] = "0"
    else:
        group["account_ids"] = ["9999"]

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_load_acceptance_mapping_fails_closed_on_value_error(tmp_path, monkeypatch):
    mapping = tmp_path / "account-mapping.json"
    mapping.write_text("{}", encoding="utf-8")

    def fail_read(_path):
        raise ValueError("synthetic concurrent replacement")

    monkeypatch.setattr(type(mapping), "read_bytes", fail_read)

    assert (
        artifacts_module._load_acceptance_mapping(mapping, expected_hash="0" * 64)
        is None
    )


@pytest.mark.parametrize(
    "totals_name",
    ("mapped_source_period_totals", "grouped_period_totals"),
)
def test_sourced_totals_reject_missing_reconciliation_totals(totals_name):
    report = _report_with_reconciled_totals()
    del report["reconciliation"][totals_name]

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_sourced_totals_reject_period_mismatch():
    report = _report_with_reconciled_totals()
    report["reconciliation"]["grouped_period_totals"]["prior"] = "9.01"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize(
    ("totals_name", "invalid_value"),
    (
        ("mapped_source_period_totals", float("nan")),
        ("mapped_source_period_totals", True),
        ("grouped_period_totals", "-Infinity"),
        ("grouped_period_totals", None),
    ),
)
def test_sourced_totals_reject_invalid_period_values(totals_name, invalid_value):
    report = _report_with_reconciled_totals()
    report["reconciliation"][totals_name]["month"] = invalid_value

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize(
    "totals_name",
    ("mapped_source_period_totals", "grouped_period_totals"),
)
def test_sourced_totals_reject_missing_required_period(totals_name):
    report = _report_with_reconciled_totals()
    del report["reconciliation"][totals_name]["ytd_prior"]

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_sourced_totals_reject_wrong_kpi_with_equal_global_totals():
    report = _report_with_reconciled_totals()
    report["metrics"]["ebitda"]["month"] = "11"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_sourced_totals_reject_compensating_group_errors():
    report = _report_with_reconciled_totals()
    report["groups"]["revenue"]["month"] = "21"
    report["groups"]["depreciation"]["month"] = "-3"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


@pytest.mark.parametrize("missing", ("group", "reference"))
def test_sourced_totals_reject_missing_mapping_group_or_reference(missing):
    report = _report_with_reconciled_totals()
    mapping = _reconciliation_mapping()
    if missing == "group":
        del report["groups"]["material"]
    else:
        mapping["metrics"]["ebitda"].append("missing-group")

    assert not artifacts_module._sourced_totals_pass(report, mapping)


def test_sourced_totals_reject_malformed_group_decimal():
    report = _report_with_reconciled_totals()
    report["groups"]["material"]["ytd"] = "not-a-decimal"

    assert not artifacts_module._sourced_totals_pass(report, _reconciliation_mapping())


def test_compute_to_persist_acceptance_reconciles_negative_multipliers(tmp_path):
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source.parent.mkdir(parents=True)
    source.write_text(
        "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD;YTD Vorjahr\n"
        "r1;4000;Umsatz;203500;200000;600000;550000\n"
        "r2;5000;Material;101750;100000;300000;280000\n"
        "r3;6000;Personal;98950;97000;290000;275000\n"
        "r4;7000;Abschreibung;3000;2900;9000;8500\n"
        "r5;8000;Finanzergebnis;2050;2000;6000;5500\n"
        "r6;5000;Material zweite Zeile;0;0;0;0\n",
        encoding="utf-8",
    )
    _write_acceptance_mapping(tmp_path)
    report = json.loads(
        ControllingComputeTool(tmp_path).safe_run(
            '{"operation":"kmu_report","source":"inbox/actuals/demo.csv"}'
        )
    )
    now = datetime.now(timezone.utc)

    result = persist_report_artifacts(
        tmp_path,
        report,
        {"summary": "A. B. C.", "alarms": [], "actions": ["A", "B", "C"]},
        validated_at=now,
        draft_created_at=now,
    )

    assert (
        report["reconciliation"]["mapped_source_period_totals"]
        == report["reconciliation"]["grouped_period_totals"]
    )
    assert result["acceptance"]["criteria"]["sourced_totals"] is True


def test_compute_to_persist_accepts_ratio_without_revenue_group(tmp_path):
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source.parent.mkdir(parents=True)
    source.write_text(
        "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD;YTD Vorjahr\n"
        "r1;5000;Material;10;9;29;27\n"
        "r2;7000;Abschreibung;2;2;6;6\n",
        encoding="utf-8",
    )
    mapping = _acceptance_mapping()
    mapping["groups"] = {
        name: mapping["groups"][name] for name in ("material", "depreciation")
    }
    mapping["metrics"] = {
        "ebitda": ["depreciation"],
        "depreciation": ["depreciation"],
        "egt": ["depreciation"],
    }
    _write_acceptance_mapping(tmp_path)
    mapping_path = tmp_path / "project" / "pilot" / "account-mapping.json"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    report = json.loads(
        ControllingComputeTool(tmp_path).safe_run(
            '{"operation":"kmu_report","source":"inbox/actuals/demo.csv"}'
        )
    )
    now = datetime.now(timezone.utc)
    result = persist_report_artifacts(
        tmp_path,
        report,
        {"summary": "A. B. C.", "alarms": [], "actions": ["A", "B", "C"]},
        validated_at=now,
        draft_created_at=now,
    )

    assert all(
        report["metrics"]["material_ratio"][period] is None
        for period in ("month", "prior", "ytd", "ytd_prior")
    )
    assert result["acceptance"]["criteria"]["sourced_totals"] is True


def test_report_writes_human_and_machine_artifacts_with_acceptance_evidence(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )

    responses = [json.loads(tool.safe_run('{"source":"auto"}')) for _ in range(3)]

    latest = tmp_path / responses[-1]["artifact"]
    markdown = tmp_path / "artifacts" / "latest-controlling-report.md"
    html = tmp_path / responses[-1]["human_artifact"]
    evidence_path = tmp_path / "artifacts" / "acceptance-evidence.json"
    artifact = json.loads(latest.read_text(encoding="utf-8"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert latest.name == "latest-controlling-report.json"
    assert markdown.is_file()
    assert html.is_file()
    assert "KMU-Controlling-Report" in html.read_text(encoding="utf-8")
    assert "must-not-persist" not in html.read_text(encoding="utf-8")
    assert "must-not-persist" not in latest.read_text(encoding="utf-8")
    assert artifact["report"]["metrics"]["ebitda"]["month"] == "2800"
    assert artifact["acceptance"]["repeatable_run_count"] == 3
    assert artifact["acceptance"]["criteria"]["repeatable_runs"] is True
    assert artifact["acceptance"]["criteria"]["sourced_totals"] is True
    assert artifact["acceptance"]["criteria"]["draft_latency"] is True
    assert artifact["acceptance"]["criteria"]["approval_safety"] is True
    assert len(evidence["runs"]) == 3
    assert len({run["kpi_result_hash"] for run in evidence["runs"]}) == 1
    assert evidence["runs"][-1]["source_file"] == "inbox/actuals/demo.csv"
    assert evidence["runs"][-1]["mapped_accounts"] == 5
    assert evidence["runs"][-1]["approval_log"] == []
    assert evidence["runs"][-1]["external_action_log"] == []
    assert [run["sequence"] for run in evidence["runs"]] == [1, 2, 3]
    assert responses[-1]["acceptance"]["passed"] is True
    signed_status = read_acceptance_status(tmp_path)
    assert signed_status["valid"] is True
    assert signed_status["passed"] is True
    assert signed_status["repeatable_run_count"] == 3
    assert signed_status["sequence"] == 3


def test_acceptance_status_is_read_only_before_first_run(tmp_path):
    before = list(tmp_path.rglob("*"))

    status = read_acceptance_status(tmp_path)

    assert status == {
        "valid": True,
        "passed": False,
        "repeatable_run_count": 0,
        "sequence": 0,
        "run_signature": None,
    }
    assert list(tmp_path.rglob("*")) == before


@pytest.mark.parametrize(
    ("config", "manifest"),
    [
        ({"require_human_approval": False}, None),
        (None, {"autonomy_level": "max", "approval_required_for": ["external communication", "send", "publish"], "tool_permissions": {"default": "disabled", "enabled": ["read"]}}),
        (None, {"approval_required_for": ["send", "publish"], "tool_permissions": {"default": "disabled", "enabled": ["read"]}}),
        (None, {"approval_required_for": ["external communication", "send", "publish"], "tool_permissions": {"default": "disabled", "enabled": ["read", "send"]}}),
    ],
)
def test_approval_policy_snapshot_fails_closed_for_unsafe_governance(
    tmp_path, config, manifest
):
    _write_acceptance_mapping(tmp_path)
    if config is not None:
        (tmp_path / "project" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    if manifest is not None:
        (tmp_path / "project" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    snapshot = artifacts_module._approval_policy_snapshot(tmp_path)

    assert snapshot["gate_active"] is False


def test_config_autonomy_level_cannot_disable_manifest_approval_gate(tmp_path):
    _write_acceptance_mapping(tmp_path)
    (tmp_path / "project" / "config.json").write_text(
        json.dumps({"autonomy_level": "max", "require_human_approval": True}),
        encoding="utf-8",
    )

    snapshot = artifacts_module._approval_policy_snapshot(tmp_path)

    assert snapshot["autonomy_level"] == "standard"
    assert snapshot["gate_active"] is True


def test_nested_relative_instance_policy_snapshot_passes(tmp_path, monkeypatch):
    instance = tmp_path / "instances" / "nested" / "pilot"
    _write_acceptance_mapping(instance)
    monkeypatch.chdir(tmp_path)

    snapshot = artifacts_module._approval_policy_snapshot(
        Path("instances/nested/pilot")
    )

    assert snapshot["policy_valid"] is True
    assert snapshot["gate_active"] is True
    assert artifacts_module._approval_safety_pass(
        {
            "approval_log": [],
            "external_action_log": [],
            "external_actions_without_explicit_approval": 0,
        },
        snapshot,
    )


def test_link_in_first_relative_instance_component_fails_closed(
    tmp_path, monkeypatch
):
    target = tmp_path / "actual" / "nested" / "pilot"
    _write_acceptance_mapping(target)
    link = tmp_path / "linked"
    try:
        link.symlink_to(tmp_path / "actual", target_is_directory=True)
    except OSError:
        pytest.skip("Directory links unavailable for this test account")
    monkeypatch.chdir(tmp_path)

    snapshot = artifacts_module._approval_policy_snapshot(Path("linked/nested/pilot"))

    assert snapshot["policy_valid"] is False
    assert snapshot["gate_active"] is False


def test_approval_policy_snapshot_rejects_missing_malformed_and_symlink_files(tmp_path):
    _write_acceptance_mapping(tmp_path)
    config = tmp_path / "project" / "config.json"
    config.unlink()
    assert artifacts_module._approval_policy_snapshot(tmp_path)["policy_valid"] is False


def test_approval_policy_snapshot_rejects_oversize_and_replaced_policy_file(tmp_path, monkeypatch):
    _write_acceptance_mapping(tmp_path)
    config = tmp_path / "project" / "config.json"
    config.write_bytes(b"{" + b" " * artifacts_module._MAX_POLICY_BYTES)
    assert artifacts_module._approval_policy_snapshot(tmp_path)["policy_valid"] is False

    _write_acceptance_mapping(tmp_path)
    replacement = tmp_path / "replacement.json"
    replacement.write_text('{"require_human_approval": false}', encoding="utf-8")
    swapped = False
    if os.name == "nt":
        original_read = artifacts_module._windows_read_policy_handle

        def replace_after_descriptor_read(read_file, set_pointer, handle):
            nonlocal swapped
            raw = original_read(read_file, set_pointer, handle)
            if not swapped:
                swapped = True
                os.replace(replacement, config)
            return raw

        monkeypatch.setattr(
            artifacts_module,
            "_windows_read_policy_handle",
            replace_after_descriptor_read,
        )
    else:
        original_read = artifacts_module.os.read

        def replace_after_descriptor_read(descriptor, count):
            nonlocal swapped
            raw = original_read(descriptor, count)
            if not swapped:
                swapped = True
                os.replace(replacement, config)
            return raw

        monkeypatch.setattr(artifacts_module.os, "read", replace_after_descriptor_read)
    assert artifacts_module._approval_policy_snapshot(tmp_path)["policy_valid"] is False

    config.write_text("{", encoding="utf-8")
    assert artifacts_module._approval_policy_snapshot(tmp_path)["policy_valid"] is False

    config.unlink()
    target = tmp_path / "config-target.json"
    target.write_text("{}", encoding="utf-8")
    try:
        config.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks unavailable for this test account")
    assert artifacts_module._approval_policy_snapshot(tmp_path)["policy_valid"] is False


def test_policy_drift_invalidates_signed_acceptance_status(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text("Konto;Monat\n4000;1\n", encoding="utf-8")
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(tool._compute, "safe_run", lambda *_: json.dumps(_aggregate_report(tmp_path)))
    for _ in range(3):
        json.loads(tool.safe_run('{"source":"auto"}'))
    assert read_acceptance_status(tmp_path)["passed"] is True

    config_path = tmp_path / "project" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["require_human_approval"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")

    status = read_acceptance_status(tmp_path)
    assert status["valid"] is False
    assert status["passed"] is False


def test_unsafe_run_breaks_repeatability_even_after_safe_policy_is_restored(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path)),
    )
    manifest_path = tmp_path / "project" / "manifest.json"
    safe_manifest = manifest_path.read_text(encoding="utf-8")
    first = json.loads(tool.safe_run('{"source":"auto"}'))
    manifest = json.loads(safe_manifest)
    manifest["autonomy_level"] = "max"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    unsafe = json.loads(tool.safe_run('{"source":"auto"}'))
    manifest_path.write_text(safe_manifest, encoding="utf-8")
    restored = json.loads(tool.safe_run('{"source":"auto"}'))

    assert first["acceptance"]["repeatable_run_count"] == 1
    assert unsafe["acceptance"]["repeatable_run_count"] == 0
    assert restored["acceptance"]["repeatable_run_count"] == 1
    assert restored["acceptance"]["passed"] is False
    for _ in range(2):
        restored = json.loads(tool.safe_run('{"source":"auto"}'))
    assert restored["acceptance"]["repeatable_run_count"] == 3
    assert restored["acceptance"]["passed"] is True


def test_policy_change_between_bundle_read_and_signing_fails_closed(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path)),
    )
    original_key = artifacts_module._acceptance_key

    def change_policy_after_initial_bundle(root):
        key = original_key(root)
        config_path = root / "project" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["require_human_approval"] = False
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return key

    monkeypatch.setattr(artifacts_module, "_acceptance_key", change_policy_after_initial_bundle)
    response = json.loads(tool.safe_run('{"source":"auto"}'))
    evidence = json.loads(
        (tmp_path / "artifacts" / "acceptance-evidence.json").read_text(
            encoding="utf-8"
        )
    )

    snapshot = evidence["runs"][-1]["approval_policy_snapshot"]
    assert response["acceptance"]["criteria"]["approval_safety"] is False
    assert response["acceptance"]["passed"] is False
    assert snapshot["policy_valid"] is False
    assert "policy_changed_during_acceptance" in snapshot["validation_errors"]


def test_acceptance_rejects_tampered_policy_snapshot_or_hash(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text("Konto;Monat\n4000;1\n", encoding="utf-8")
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(tool._compute, "safe_run", lambda *_: json.dumps(_aggregate_report(tmp_path)))
    json.loads(tool.safe_run('{"source":"auto"}'))
    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    run = json.loads(ledger.read_text(encoding="utf-8"))
    run["approval_policy_hash"] = "0" * 64
    ledger.write_text(json.dumps(run) + "\n", encoding="utf-8")

    status = read_acceptance_status(tmp_path)
    assert status["valid"] is False
    assert status["passed"] is False


def test_interrupted_human_view_write_does_not_publish_new_latest_json(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    report = _aggregate_report(tmp_path)
    management = {"summary": "A. B. C.", "alarms": [], "actions": ["A", "B", "C"]}
    now = datetime.now(timezone.utc)
    persist_report_artifacts(
        tmp_path, report, management, validated_at=now, draft_created_at=now
    )
    latest_path = tmp_path / "artifacts" / "latest-controlling-report.json"
    published = latest_path.read_bytes()
    original_atomic_text = artifacts_module._atomic_text

    def interrupt_html(path, text):
        if path.name == "latest-controlling-report.html":
            raise OSError("synthetic interrupted HTML publication")
        original_atomic_text(path, text)

    monkeypatch.setattr(artifacts_module, "_atomic_text", interrupt_html)

    with pytest.raises(OSError, match="interrupted HTML"):
        persist_report_artifacts(
            tmp_path, report, management, validated_at=now, draft_created_at=now
        )

    assert latest_path.read_bytes() == published
    status = read_acceptance_status(tmp_path)
    assert status["valid"] is True
    assert status["sequence"] == 2


def test_acceptance_history_rejects_duplicated_replayed_runs(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )

    first = json.loads(tool.safe_run('{"source":"auto"}'))
    evidence_path = tmp_path / "artifacts" / "acceptance-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["runs"] = [evidence["runs"][0]] * 3
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    second = json.loads(tool.safe_run('{"source":"auto"}'))
    third = json.loads(tool.safe_run('{"source":"auto"}'))

    assert first["acceptance"]["repeatable_run_count"] == 1
    assert second["acceptance"]["repeatable_run_count"] == 2
    assert second["acceptance"]["passed"] is False
    assert third["acceptance"]["repeatable_run_count"] == 3
    assert third["acceptance"]["passed"] is True
    assert (tmp_path / "state" / ".acceptance-hmac-key").stat().st_size == 32


def test_acceptance_uses_authoritative_ledger_after_evidence_rollback(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source_a = "Konto;Monat\n4000;1\n"
    source.write_text(source_a, encoding="utf-8")
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )

    for _ in range(2):
        json.loads(tool.safe_run('{"source":"auto"}'))
    evidence_path = tmp_path / "artifacts" / "acceptance-evidence.json"
    old_evidence = evidence_path.read_text(encoding="utf-8")

    source.write_text("Konto;Monat\n4000;2\n", encoding="utf-8")
    changed = json.loads(tool.safe_run('{"source":"auto"}'))
    assert changed["acceptance"]["repeatable_run_count"] == 1

    source.write_text(source_a, encoding="utf-8")
    evidence_path.write_text(old_evidence, encoding="utf-8")
    restored = json.loads(tool.safe_run('{"source":"auto"}'))

    assert restored["acceptance"]["repeatable_run_count"] == 1
    assert restored["acceptance"]["passed"] is False
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert [run["sequence"] for run in evidence["runs"]] == [1, 2, 3, 4]


def test_acceptance_rejects_authoritative_ledger_truncation(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )
    for _ in range(2):
        json.loads(tool.safe_run('{"source":"auto"}'))

    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    first_line = ledger.read_text(encoding="utf-8").splitlines()[0]
    ledger.write_text(first_line + "\n", encoding="utf-8")

    response = tool.safe_run('{"source":"auto"}')

    assert response.startswith("FEHLER:")
    assert "Rollback" in response


def test_acceptance_rejects_tampered_middle_ledger_record(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )
    for _ in range(3):
        json.loads(tool.safe_run('{"source":"auto"}'))

    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    middle = json.loads(lines[1])
    middle["kpi_result_hash"] = "0" * 64
    lines[1] = json.dumps(middle, ensure_ascii=False, sort_keys=True)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    response = tool.safe_run('{"source":"auto"}')

    assert response.startswith("FEHLER:")
    assert "besch\u00e4digt" in response


def test_acceptance_serializes_parallel_writers(tmp_path, monkeypatch):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )
    original_append = artifacts_module._append_acceptance_ledger

    def slow_append(path, run):
        time.sleep(0.05)
        original_append(path, run)

    monkeypatch.setattr(artifacts_module, "_append_acceptance_ledger", slow_append)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(lambda _: tool.safe_run('{"source":"auto"}'), range(2))
        )

    parsed = [json.loads(response) for response in responses]
    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

    assert sorted(item["acceptance"]["repeatable_run_count"] for item in parsed) == [1, 2]
    assert [record["sequence"] for record in records] == [1, 2]
    third = json.loads(tool.safe_run('{"source":"auto"}'))
    assert third["acceptance"]["repeatable_run_count"] == 3
    assert third["acceptance"]["passed"] is True


def test_acceptance_os_lock_serializes_processes(tmp_path):
    context = get_context("spawn")
    ready = context.Event()
    process = context.Process(
        target=_hold_acceptance_lock_in_process,
        args=(tmp_path, ready),
    )
    process.start()
    assert ready.wait(timeout=5)
    started = time.monotonic()

    with artifacts_module._acceptance_write_lock(tmp_path):
        pass

    elapsed = time.monotonic() - started
    process.join(timeout=5)
    assert process.exitcode == 0
    assert elapsed >= 0.25


def test_acceptance_os_lock_releases_after_process_crash(tmp_path):
    context = get_context("spawn")
    ready = context.Event()
    process = context.Process(
        target=_hold_acceptance_lock_in_process,
        args=(tmp_path, ready),
        kwargs={"crash": True},
    )
    process.start()
    assert ready.wait(timeout=5)
    process.join(timeout=5)
    assert process.exitcode == 0

    with artifacts_module._acceptance_write_lock(tmp_path):
        pass


def test_parallel_older_run_cannot_overwrite_newer_shared_reports(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    source_a = tmp_path / "inbox" / "actuals" / "a.csv"
    source_b = tmp_path / "inbox" / "actuals" / "b.csv"
    source_a.write_text("Konto;Monat\n4000;1\n", encoding="utf-8")
    source_b.write_text("Konto;Monat\n4000;2\n", encoding="utf-8")
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        source_a.read_text(encoding="utf-8"), encoding="utf-8"
    )
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    b_computed = threading.Event()

    def compute(input_str):
        source = json.loads(input_str)["source"]
        report = _aggregate_report(tmp_path)
        report["source"] = source
        selected = tmp_path / source
        report["provenance"]["input_fingerprint"] = hashlib.sha256(
            selected.read_bytes()
        ).hexdigest()
        if source.endswith("b.csv"):
            b_computed.set()
        return json.dumps(report, ensure_ascii=False)

    monkeypatch.setattr(tool._compute, "safe_run", compute)
    request_a = '{"source":"inbox/actuals/a.csv"}'
    request_b = '{"source":"inbox/actuals/b.csv"}'
    for _ in range(2):
        json.loads(tool.safe_run(request_a))

    original_atomic_json = artifacts_module._atomic_json
    a_paused = threading.Event()
    release_a = threading.Event()

    def pause_sequence_three(path, value):
        provenance = value.get("provenance") if isinstance(value, dict) else None
        if (
            path.name.startswith("controlling-report-")
            and isinstance(provenance, dict)
            and provenance.get("sequence") == 3
        ):
            a_paused.set()
            assert release_a.wait(timeout=5)
        original_atomic_json(path, value)

    monkeypatch.setattr(artifacts_module, "_atomic_json", pause_sequence_three)
    with ThreadPoolExecutor(max_workers=2) as executor:
        older = executor.submit(tool.safe_run, request_a)
        assert a_paused.wait(timeout=5)
        newer = executor.submit(tool.safe_run, request_b)
        assert b_computed.wait(timeout=5)
        time.sleep(0.1)
        release_a.set()
        json.loads(older.result(timeout=10))
        json.loads(newer.result(timeout=10))

    latest = json.loads(
        (tmp_path / "artifacts" / "latest-controlling-report.json").read_text(
            encoding="utf-8"
        )
    )
    evidence = json.loads(
        (tmp_path / "artifacts" / "acceptance-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    head = json.loads(
        (tmp_path / "state" / "acceptance-head.json").read_text(encoding="utf-8")
    )

    assert head["sequence"] == 4
    assert latest["provenance"]["sequence"] == 4
    assert latest["provenance"]["run_signature"] == head["last_run_signature"]
    assert latest["acceptance"]["passed"] is False
    assert evidence["runs"][-1]["sequence"] == 4


def test_artifact_persistence_rejects_source_replacement_after_computation(tmp_path):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source.write_text("Konto;Monat\n4000;1\n", encoding="utf-8")
    _write_acceptance_mapping(tmp_path)
    report = _aggregate_report(tmp_path)
    source.write_text("Konto;Monat\n4000;999\n", encoding="utf-8")
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="verändert"):
        persist_report_artifacts(
            tmp_path,
            report,
            {"summary": "A. B. C.", "alarms": [], "actions": ["A", "B", "C"]},
            validated_at=now,
            draft_created_at=now,
        )


def test_instance_result_prints_summary_artifact_and_acceptance(
    tmp_path, capsys
):
    import agent_cli

    result = type(
        "Result",
        (),
        {
            "success": True,
            "metadata": {
                "outputs": [
                    json.dumps(
                        {
                            "mode": "deterministic_fallback",
                            "summary": "A. B. C.",
                            "artifact": "artifacts/latest-controlling-report.json",
                            "human_artifact": "artifacts/latest-controlling-report.html",
                            "acceptance": {"passed": False, "repeatable_run_count": 1},
                        }
                    )
                ]
            },
        },
    )()

    agent_cli._print_instance_result(tmp_path, result)

    output = capsys.readouterr().out
    assert "A. B. C." in output
    assert "artifacts" in output
    assert "1/3" in output
