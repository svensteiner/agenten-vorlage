import json

from core.controlling.narrative import ControllingReportTool


def _aggregate_report():
    return {
        "source": "inbox/actuals/demo.csv",
        "method": "mapping-defined account groups; month/prior/ytd aggregation",
        "report_metadata": {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "currency": "EUR",
            "sign_convention": "source_native",
            "row_identifier": ["account_id"],
        },
        "metrics": {
            "ebitda": {"month": "2800", "account_ids": ["4000"]},
            "egt": {"month": "-2250", "account_ids": ["4000", "5000"]},
        },
        "groups": {"revenue": {"month": "203500", "account_ids": ["4000"]}},
        "material_deviations": [
            {"account_id": "5000", "month_vs_prior": "-22600"}
        ],
        "reconciliation": {
            "source_account_count": 2,
            "mapped_account_count": 2,
            "ignored_account_count": 0,
        },
        "raw_rows": [{"account_id": "4000", "customer": "must-not-persist"}],
    }


def test_report_writes_human_and_machine_artifacts_with_acceptance_evidence(
    tmp_path, monkeypatch
):
    (tmp_path / "inbox" / "actuals").mkdir(parents=True)
    (tmp_path / "project" / "pilot").mkdir(parents=True)
    (tmp_path / "inbox" / "actuals" / "demo.csv").write_text(
        "Konto;Monat\n4000;1\n", encoding="utf-8"
    )
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(), ensure_ascii=False),
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
    assert evidence["runs"][-1]["mapped_accounts"] == 2
    assert evidence["runs"][-1]["approval_log"] == []
    assert evidence["runs"][-1]["external_action_log"] == []
    assert responses[-1]["acceptance"]["passed"] is True


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
