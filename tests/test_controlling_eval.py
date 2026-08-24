"""Offline ADK-inspired eval harness for the KMU controlling preset."""

import argparse
import json
import shutil

import pytest

import agent_cli
from core.controlling.narrative import ControllingReportTool
from core.controlling.tools import ControllingComputeTool
from test_kmu_pilot_acceptance_e2e import DEMO, ROOT, _is_sha256


EVAL_SET_PATH = ROOT / "eval" / "controlling_eval_set.json"
GOLDEN_PATH = DEMO / "expected-results.json"


def _load_eval_set():
    payload = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["preset"] == "kmu-controlling"
    cases = payload["cases"]
    assert 4 <= len(cases) <= 8
    return payload


def _golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _report_metrics(report):
    return {
        "revenue_month": report["groups"]["revenue"]["month"],
        "material_month": report["groups"]["material"]["month"],
        "personnel_month": report["groups"]["personnel"]["month"],
        "ebitda_month": report["metrics"]["ebitda"]["month"],
        "egt_month": report["metrics"]["egt"]["month"],
        "egt_prior": report["metrics"]["egt"]["prior"],
        "egt_ytd": report["metrics"]["egt"]["ytd"],
        "egt_ytd_prior": report["metrics"]["egt"]["ytd_prior"],
        "receivables_month": report["metrics"]["receivables"]["month"],
        "liquidity_month": report["metrics"]["liquidity"]["month"],
        "payables_month": report["metrics"]["payables"]["month"],
    }


def _provision_instance(tmp_path, setup):
    """Create a temp KMU instance like the packaged acceptance e2e."""
    create = argparse.Namespace(
        tenant="Eval KMU",
        agent="Controlling Pilot",
        output=str(tmp_path),
        full=False,
        no_self_test=True,
        preset="kmu-controlling",
    )
    assert agent_cli.cmd_create(create) == 0
    instance = tmp_path / "eval-kmu" / "controlling-pilot"
    shutil.copyfile(
        DEMO / "account-mapping.json",
        instance / "project" / "pilot" / "account-mapping.json",
    )
    if setup == "demo":
        actuals = instance / "inbox" / "actuals"
        actuals.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            DEMO / "Saldenliste_Muster_Juni2026.xlsx",
            actuals / "Saldenliste_Muster_Juni2026.xlsx",
        )
    elif setup == "empty_inbox":
        actuals = instance / "inbox" / "actuals"
        actuals.mkdir(parents=True, exist_ok=True)
        for leftover in actuals.glob("*"):
            if leftover.is_file():
                leftover.unlink()
    else:
        raise AssertionError(f"unknown eval setup: {setup}")
    return instance


def _run_tool(instance, case):
    payload = json.dumps(case["payload"], ensure_ascii=False, separators=(",", ":"))
    name = case["tool"]
    if name == "ControllingReportTool":
        return ControllingReportTool(instance).safe_run(payload)
    if name == "ControllingComputeTool":
        return ControllingComputeTool(instance).safe_run(payload)
    raise AssertionError(f"unknown eval tool: {name}")


def _assert_fail_closed(raw, instance, case, golden):
    expected = case["expected"]
    assert raw.startswith(expected.get("error_prefix", "FEHLER"))
    contains = expected.get("error_contains")
    if contains:
        assert contains in raw
    if expected.get("no_fabricated_totals"):
        for value in golden["metrics"].values():
            assert value not in raw
    latest = instance / "artifacts" / "latest-controlling-report.json"
    assert not latest.exists()


def _load_persisted_report(instance):
    latest = json.loads(
        (instance / "artifacts" / "latest-controlling-report.json").read_text(
            encoding="utf-8"
        )
    )
    return latest["report"]


def _assert_positive(raw, instance, case, golden):
    expected = case["expected"]
    assert not raw.startswith("FEHLER")
    body = json.loads(raw)
    if expected.get("mode"):
        assert body["mode"] == expected["mode"]
    for key in expected.get("required_artifact_keys", []):
        assert key in body
        assert body[key]
    for relative in expected.get("required_files", []):
        path = instance / relative
        assert path.is_file(), relative
    if case["tool"] == "ControllingComputeTool":
        report = body
    else:
        report = _load_persisted_report(instance)
    if expected.get("source_file"):
        assert report["source"] == expected["source_file"]
        assert report["source"] == golden["source"]
    if expected.get("metrics_from_golden"):
        assert report["report_metadata"] == golden["report_metadata"]
        assert _report_metrics(report) == golden["metrics"]
    if expected.get("sourced_totals"):
        reconciliation = report["reconciliation"]
        for name, value in golden["reconciliation"].items():
            assert reconciliation[name] == value
        assert (
            reconciliation["mapped_source_period_totals"]
            == reconciliation["grouped_period_totals"]
        )
        if case["tool"] == "ControllingReportTool":
            latest = json.loads(
                (instance / "artifacts" / "latest-controlling-report.json").read_text(
                    encoding="utf-8"
                )
            )
            assert latest["acceptance"]["criteria"]["sourced_totals"] is True
    hashes = expected.get("evidence_hashes") or []
    if hashes:
        evidence = json.loads(
            (instance / "artifacts" / "acceptance-evidence.json").read_text(
                encoding="utf-8"
            )
        )
        assert evidence["runs"]
        for run in evidence["runs"]:
            for field in hashes:
                assert _is_sha256(run[field])
            if expected.get("source_file"):
                assert run["source_file"] == expected["source_file"]
        if expected.get("repeatable"):
            kpi_hashes = {run["kpi_result_hash"] for run in evidence["runs"]}
            assert len(kpi_hashes) == 1
            fingerprints = {run["input_fingerprint"] for run in evidence["runs"]}
            assert len(fingerprints) == 1
    return body


def test_eval_set_is_grounded_in_packaged_demo_results():
    payload = _load_eval_set()
    golden = _golden()
    assert payload["golden_source"] == (
        "presets/kmu-controlling/pilot/demo/expected-results.json"
    )
    assert (ROOT / payload["golden_source"]).is_file()
    ids = [case["id"] for case in payload["cases"]]
    assert len(ids) == len(set(ids))
    negatives = [case for case in payload["cases"] if case["expected"].get("fail_closed")]
    assert 1 <= len(negatives) <= 2
    for case in payload["cases"]:
        assert case["tool"] in {"ControllingReportTool", "ControllingComputeTool"}
        assert "payload" in case
        assert case["setup"] in {"demo", "empty_inbox"}
        if not case["expected"].get("fail_closed"):
            assert case["expected"].get("metrics_from_golden") is True
            if case["expected"].get("source_file"):
                assert case["expected"]["source_file"] == golden["source"]


@pytest.mark.parametrize(
    "case",
    _load_eval_set()["cases"],
    ids=lambda case: case["id"],
)
def test_controlling_eval_case(tmp_path, case):
    golden = _golden()
    instance = _provision_instance(tmp_path, case["setup"])
    runs = int(case.get("runs") or 1)
    raw = None
    for _ in range(runs):
        raw = _run_tool(instance, case)
    assert raw is not None
    if case["expected"].get("fail_closed"):
        _assert_fail_closed(raw, instance, case, golden)
        return
    _assert_positive(raw, instance, case, golden)
