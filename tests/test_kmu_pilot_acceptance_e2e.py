"""Offline acceptance journey for the packaged KMU controlling pilot."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import time

import agent_cli
from core.controlling.artifacts import read_acceptance_status
from core.controlling.narrative import ControllingReportTool


ROOT = Path(__file__).parents[1]
DEMO = ROOT / "presets" / "kmu-controlling" / "pilot" / "demo"


def _is_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def test_packaged_kmu_pilot_passes_all_acceptance_gates_offline(tmp_path):
    """A KMU owner can prove a repeatable, sourced, approval-safe pilot."""
    create = argparse.Namespace(
        tenant="Muster KMU",
        agent="Controlling Pilot",
        output=str(tmp_path),
        full=False,
        no_self_test=True,
        preset="kmu-controlling",
    )
    assert agent_cli.cmd_create(create) == 0

    instance = tmp_path / "muster-kmu" / "controlling-pilot"
    actuals = instance / "inbox" / "actuals"
    actuals.mkdir(parents=True)
    shutil.copyfile(
        DEMO / "Saldenliste_Muster_Juni2026.xlsx",
        actuals / "Saldenliste_Muster_Juni2026.xlsx",
    )
    shutil.copyfile(
        DEMO / "account-mapping.json",
        instance / "project" / "pilot" / "account-mapping.json",
    )

    tool = ControllingReportTool(instance)
    responses = []
    wall_times = []
    for _ in range(3):
        started = time.perf_counter()
        responses.append(json.loads(tool.safe_run('{"source":"auto"}')))
        wall_times.append(time.perf_counter() - started)

    latest = json.loads(
        (instance / "artifacts" / "latest-controlling-report.json").read_text(
            encoding="utf-8"
        )
    )
    evidence = json.loads(
        (instance / "artifacts" / "acceptance-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    expected = json.loads(
        (DEMO / "expected-results.json").read_text(encoding="utf-8")
    )
    criteria = json.loads(
        (instance / "project" / "pilot" / "acceptance-criteria.json").read_text(
            encoding="utf-8"
        )
    )

    criteria_by_id = {item["id"]: item for item in criteria["criteria"]}
    assert set(criteria_by_id) == {
        "sourced_totals",
        "draft_latency",
        "repeatable_runs",
        "approval_safety",
    }
    assert latest["report"]["source"] == expected["source"]
    assert latest["report"]["report_metadata"] == expected["report_metadata"]
    actual_metrics = {
        "revenue_month": latest["report"]["groups"]["revenue"]["month"],
        "material_month": latest["report"]["groups"]["material"]["month"],
        "personnel_month": latest["report"]["groups"]["personnel"]["month"],
        "ebitda_month": latest["report"]["metrics"]["ebitda"]["month"],
        "egt_month": latest["report"]["metrics"]["egt"]["month"],
        "egt_prior": latest["report"]["metrics"]["egt"]["prior"],
        "egt_ytd": latest["report"]["metrics"]["egt"]["ytd"],
        "egt_ytd_prior": latest["report"]["metrics"]["egt"]["ytd_prior"],
        "receivables_month": latest["report"]["metrics"]["receivables"]["month"],
        "liquidity_month": latest["report"]["metrics"]["liquidity"]["month"],
        "payables_month": latest["report"]["metrics"]["payables"]["month"],
    }
    assert actual_metrics == expected["metrics"]
    assert latest["report"]["reconciliation"]["source_account_count"] == 20
    assert latest["report"]["reconciliation"]["mapped_account_count"] == 20
    assert latest["report"]["reconciliation"]["ignored_account_count"] == 0
    assert (
        latest["report"]["reconciliation"]["mapped_source_period_totals"]
        == latest["report"]["reconciliation"]["grouped_period_totals"]
    )
    assert latest["acceptance"]["criteria"]["sourced_totals"] is True

    runs = evidence["runs"]
    assert len(runs) == 3
    for criterion in criteria_by_id.values():
        required = set(criterion["evidence_required"])
        assert all(required <= set(run) for run in runs)

    for run in runs:
        assert run["source_file"] == expected["source"]
        assert run["period"] == expected["report_metadata"]
        assert run["mapped_accounts"] == expected["reconciliation"][
            "mapped_account_count"
        ]
        assert run["formula"] == latest["report"]["method"]
        assert run["reconciliation_result"] == latest["report"]["reconciliation"]

    assert all(elapsed < 300 for elapsed in wall_times)
    for run in runs:
        validated_at = datetime.fromisoformat(run["validation_completed_at"])
        drafted_at = datetime.fromisoformat(run["draft_created_at"])
        assert validated_at.tzinfo is not None
        assert drafted_at.tzinfo is not None
        assert validated_at <= drafted_at
        assert (drafted_at - validated_at).total_seconds() < 300
        assert run["draft_latency_seconds"] == (
            drafted_at - validated_at
        ).total_seconds()
    assert latest["acceptance"]["criteria"]["draft_latency"] is True
    run_ids = [run["run_id"] for run in runs]
    assert all(isinstance(run_id, str) and run_id for run_id in run_ids)
    assert len(set(run_ids)) == 3
    for field in ("input_fingerprint", "mapping_version", "kpi_result_hash"):
        assert all(_is_sha256(run[field]) for run in runs)
    assert all(
        isinstance(run["calculation_version"], str)
        and run["calculation_version"]
        for run in runs
    )
    assert len({run["input_fingerprint"] for run in runs}) == 1
    assert len({run["mapping_version"] for run in runs}) == 1
    assert len({run["calculation_version"] for run in runs}) == 1
    assert len({run["kpi_result_hash"] for run in runs}) == 1
    repeatable_counts = [
        response["acceptance"]["repeatable_run_count"] for response in responses
    ]
    assert all(response["mode"] == "deterministic_fallback" for response in responses)
    assert repeatable_counts == [
        1,
        2,
        3,
    ]
    assert latest["acceptance"]["criteria"]["repeatable_runs"] is True

    assert all(run["approval_log"] == [] for run in runs)
    assert all(run["external_action_log"] == [] for run in runs)
    assert all(run["external_action_capabilities_enabled"] == [] for run in runs)
    assert all(run["external_actions_without_explicit_approval"] == 0 for run in runs)
    assert all(_is_sha256(run["approval_policy_hash"]) for run in runs)
    assert len({run["approval_policy_hash"] for run in runs}) == 1
    assert all(run["approval_policy_snapshot"]["gate_active"] is True for run in runs)
    assert all(run["approval_policy_snapshot"]["policy_valid"] is True for run in runs)
    assert all(
        run["approval_policy_snapshot"]["enabled_external_capabilities"] == []
        for run in runs
    )
    assert latest["acceptance"]["criteria"]["approval_safety"] is True

    signed_status = read_acceptance_status(instance)
    assert signed_status["valid"] is True
    assert signed_status["passed"] is True
    assert signed_status["repeatable_run_count"] == 3
    assert signed_status["sequence"] == 3
    assert _is_sha256(signed_status["run_signature"])
    assert [run["sequence"] for run in runs] == [1, 2, 3]
    assert all(_is_sha256(run["run_signature"]) for run in runs)
    assert runs[0]["previous_run_signature"] is None
    assert runs[1]["previous_run_signature"] == runs[0]["run_signature"]
    assert runs[2]["previous_run_signature"] == runs[1]["run_signature"]
    assert latest["acceptance"]["passed"] is True
