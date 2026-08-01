import hashlib
import json
from copy import deepcopy

import pytest

from core.controlling.tools import ControllingComputeTool
from core.controlling.variance import monthly_variance_brief


REQUEST = {
    "operation": "monthly_variance_brief",
    "actual_source": "data/actuals.csv",
    "budget_source": "imports/budget.csv",
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


def _ratio_mapping():
    mapping = _mapping()
    mapping["groups"] = {
        "revenue": {"prefixes": ["4"], "multiplier": 1},
        "material": {"prefixes": ["5"], "multiplier": -1},
        "costs": {"prefixes": ["6"], "multiplier": -1},
    }
    mapping["metrics"] = {
        "ebitda": ["revenue", "material", "costs"],
        "depreciation": ["costs"],
        "egt": ["revenue", "material", "costs"],
    }
    return mapping


def _write_instance(tmp_path, *, actual_rows=None, budget_rows=None, budget_mapping=None):
    actual_rows = actual_rows or [
        "actual-revenue;4000;Umsatz;1000;900;6000;5000",
        "actual-cost;5000;Material;300;250;1800;1500",
    ]
    budget_rows = budget_rows or [
        "budget-revenue;4000;Umsatz;800;750;4800;4200",
        "budget-cost;5000;Material;0;0;0;0",
    ]
    for folder, filename, rows in (
        ("data", "actuals.csv", actual_rows),
        ("imports", "budget.csv", budget_rows),
    ):
        directory = tmp_path / folder
        directory.mkdir(exist_ok=True)
        (directory / filename).write_text(
            "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD;YTD Vorjahr\n"
            + "\n".join(rows)
            + "\n",
            encoding="utf-8",
        )
    pilot = tmp_path / "project" / "pilot"
    pilot.mkdir(parents=True)
    (pilot / "account-mapping.json").write_text(
        json.dumps(budget_mapping or _mapping()), encoding="utf-8"
    )


def _run(tmp_path, request=REQUEST):
    return ControllingComputeTool(tmp_path).safe_run(json.dumps(request))


def _aggregate_reports(tmp_path):
    tool = ControllingComputeTool(tmp_path)
    mapping = tool._mapping()
    return (
        json.loads(tool._kmu_report(tmp_path / "data" / "actuals.csv", mapping)),
        json.loads(tool._kmu_report(tmp_path / "imports" / "budget.csv", mapping)),
    )


def test_monthly_variance_brief_is_deterministic_and_source_backed(tmp_path):
    _write_instance(tmp_path)

    first = _run(tmp_path)
    second = _run(tmp_path)
    brief = json.loads(first)

    assert first == second
    assert brief["kind"] == "monthly_actual_vs_budget_brief"
    assert brief["status"] == "computed_unapproved"
    assert brief["report_metadata"] == _mapping()["report_metadata"]
    assert brief["metrics"]["ebitda"] == {
        "actual": "700",
        "budget": "800",
        "delta": "-100",
        "relative_delta_percent": "-12.5",
    }
    assert brief["top_group_drivers"] == [
        {
            "group": "costs",
            "actual": "-300",
            "budget": "0",
            "delta": "-300",
            "relative_delta_percent": None,
        },
        {
            "group": "revenue",
            "actual": "1000",
            "budget": "800",
            "delta": "200",
            "relative_delta_percent": "25",
        },
    ]
    actual = tmp_path / "data" / "actuals.csv"
    budget = tmp_path / "imports" / "budget.csv"
    mapping = tmp_path / "project" / "pilot" / "account-mapping.json"
    assert brief["sources"] == {
        "actual": {
            "source": "data/actuals.csv",
            "fingerprint": hashlib.sha256(actual.read_bytes()).hexdigest(),
        },
        "budget": {
            "source": "imports/budget.csv",
            "fingerprint": hashlib.sha256(budget.read_bytes()).hexdigest(),
        },
        "mapping_version": hashlib.sha256(mapping.read_bytes()).hexdigest(),
    }
    assert brief["reconciliation"] == {
        "actual": {
            "source_account_count": 2,
            "mapped_account_count": 2,
            "ignored_account_count": 0,
        },
        "budget": {
            "source_account_count": 2,
            "mapped_account_count": 2,
            "ignored_account_count": 0,
        },
    }
    assert brief["limitations"] == [
        "computed_from_provided_actual_and_budget_sources",
        "not_approved",
    ]


@pytest.mark.parametrize(
    "variance_request",
    [
        {**REQUEST, "actual_source": "auto"},
        {**REQUEST, "budget_source": "auto"},
        {**REQUEST, "actual_source": "data/actuals.csv", "budget_source": "data/./actuals.csv"},
    ],
    ids=("actual-auto", "budget-auto", "same-resolved-source"),
)
def test_monthly_variance_brief_requires_two_distinct_explicit_sources(
    tmp_path, variance_request
):
    _write_instance(tmp_path)

    result = _run(tmp_path, variance_request)

    assert result.startswith("FEHLER")


@pytest.mark.parametrize(
    "raw_request",
    [
        "not json",
        "[]",
        json.dumps({"operation": "monthly_variance_brief"}),
        json.dumps({**REQUEST, "actual_source": None}),
        json.dumps({**REQUEST, "budget_source": 4}),
    ],
    ids=("malformed-json", "not-object", "missing-sources", "null-source", "invalid-source-type"),
)
def test_monthly_variance_brief_rejects_malformed_requests(tmp_path, raw_request):
    _write_instance(tmp_path)

    result = ControllingComputeTool(tmp_path).safe_run(raw_request)

    assert result.startswith("FEHLER")


def test_monthly_variance_brief_rejects_mismatched_account_sets(tmp_path):
    budget_rows = [
        "budget-revenue;4000;Umsatz;800;750;4800;4200",
        "budget-other;6000;Lohn;100;100;600;600",
    ]
    _write_instance(tmp_path, budget_rows=budget_rows)

    result = _run(tmp_path)

    assert result.startswith("FEHLER")


def test_monthly_variance_brief_rejects_missing_source_contract_header(tmp_path):
    _write_instance(
        tmp_path,
        budget_rows=["budget-revenue;4000;Umsatz;800;750;4800;4200"],
    )
    budget = tmp_path / "imports" / "budget.csv"
    budget.write_text(
        "Zeilen-ID;Konto;Bezeichnung;Monat;Vormonat;YTD\n"
        "budget-revenue;4000;Umsatz;800;750;4800\n",
        encoding="utf-8",
    )

    result = _run(tmp_path)

    assert result.startswith("FEHLER")


def test_monthly_variance_brief_does_not_claim_zero_percent_for_zero_budget(tmp_path):
    _write_instance(tmp_path)

    brief = json.loads(_run(tmp_path))

    assert brief["top_group_drivers"][0]["relative_delta_percent"] is None
    assert brief["metrics"]["depreciation"]["relative_delta_percent"] is None


def test_monthly_variance_brief_omits_an_unavailable_optional_group(tmp_path):
    mapping = _mapping()
    mapping["groups"]["financial"] = {"prefixes": ["8"], "multiplier": -1}
    _write_instance(tmp_path, budget_mapping=mapping)

    brief = json.loads(_run(tmp_path))

    assert all(driver["group"] != "financial" for driver in brief["top_group_drivers"])


def test_monthly_variance_brief_preserves_a_valid_null_ratio_on_both_sides(tmp_path):
    mapping = _ratio_mapping()
    actual_rows = [
        "actual-revenue;4000;Umsatz;0;0;0;0",
        "actual-material;5000;Material;300;250;1800;1500",
        "actual-cost;6000;Sonstige Kosten;50;40;300;250",
    ]
    budget_rows = [
        "budget-revenue;4000;Umsatz;0;0;0;0",
        "budget-material;5000;Material;200;175;1200;1050",
        "budget-cost;6000;Sonstige Kosten;60;50;360;300",
    ]
    _write_instance(
        tmp_path,
        actual_rows=actual_rows,
        budget_rows=budget_rows,
        budget_mapping=mapping,
    )

    first = _run(tmp_path)
    second = _run(tmp_path)
    brief = json.loads(first)

    assert first == second
    assert brief["metrics"]["material_ratio"] == {
        "actual": None,
        "budget": None,
        "delta": None,
        "relative_delta_percent": None,
    }


def test_monthly_variance_brief_rejects_ratio_missing_on_only_one_side(tmp_path):
    mapping = _ratio_mapping()
    actual_rows = [
        "actual-revenue;4000;Umsatz;0;0;0;0",
        "actual-material;5000;Material;300;250;1800;1500",
        "actual-cost;6000;Sonstige Kosten;50;40;300;250",
    ]
    budget_rows = [
        "budget-revenue;4000;Umsatz;1000;900;6000;5000",
        "budget-material;5000;Material;200;175;1200;1050",
        "budget-cost;6000;Sonstige Kosten;60;50;360;300",
    ]
    _write_instance(
        tmp_path,
        actual_rows=actual_rows,
        budget_rows=budget_rows,
        budget_mapping=mapping,
    )

    assert _run(tmp_path).startswith("FEHLER")


def test_monthly_variance_brief_rejects_different_reconciliation_account_counts(tmp_path):
    mapping = _mapping()
    mapping["groups"]["ignored"] = {
        "prefixes": ["9"],
        "multiplier": 1,
        "ignored": True,
    }
    budget_rows = [
        "budget-revenue;4000;Umsatz;800;750;4800;4200",
        "budget-cost;5000;Material;0;0;0;0",
        "budget-ignored;9000;Abgrenzung;10;10;10;10",
    ]
    _write_instance(tmp_path, budget_rows=budget_rows, budget_mapping=mapping)

    assert _run(tmp_path).startswith("FEHLER")


@pytest.mark.parametrize(
    ("mutation", "label"),
    [
        (
            lambda report: report["groups"]["revenue"].pop("account_ids"),
            "missing-account-ids",
        ),
        (
            lambda report: report["groups"]["revenue"].__setitem__(
                "account_ids", ["4000", "4000"]
            ),
            "duplicate-account-ids",
        ),
        (
            lambda report: report["metrics"]["ebitda"].__setitem__("month", "NaN"),
            "non-finite-metric",
        ),
    ],
)
def test_monthly_variance_brief_pure_function_rejects_invalid_aggregate_values(
    tmp_path, mutation, label
):
    _write_instance(tmp_path)
    actual, budget = _aggregate_reports(tmp_path)
    mutation(actual)

    with pytest.raises(ValueError):
        monthly_variance_brief(deepcopy(actual), deepcopy(budget))


@pytest.mark.parametrize("field", ("actual_source", "budget_source"))
def test_monthly_variance_brief_rejects_whitespace_auto_without_report_run(
    tmp_path, monkeypatch, field
):
    _write_instance(tmp_path)
    tool = ControllingComputeTool(tmp_path)
    report_runs = 0

    def report_must_not_run(*_args, **_kwargs):
        nonlocal report_runs
        report_runs += 1
        raise AssertionError("Eine automatische Quelle darf keinen Bericht ausloesen.")

    monkeypatch.setattr(tool, "_kmu_report", report_must_not_run)

    result = tool.safe_run(json.dumps({**REQUEST, field: " auto "}))

    assert result.startswith("FEHLER")
    assert "explizite" in result
    assert report_runs == 0


def test_monthly_variance_brief_does_not_change_kmu_report(tmp_path):
    _write_instance(tmp_path)

    report = json.loads(
        ControllingComputeTool(tmp_path).safe_run(
            json.dumps({"operation": "kmu_report", "source": "data/actuals.csv"})
        )
    )

    assert report["source"] == "data/actuals.csv"
    assert report["metrics"]["ebitda"]["month"] == "700"
    assert "kind" not in report
