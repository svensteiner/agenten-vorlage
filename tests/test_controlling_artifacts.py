from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from multiprocessing import get_context
import os
import threading
import time

import pytest

from core.controlling import artifacts as artifacts_module
from core.controlling.artifacts import persist_report_artifacts, read_acceptance_status
from core.controlling.narrative import ControllingReportTool


def _hold_acceptance_lock_in_process(root, ready, *, crash=False):
    with artifacts_module._acceptance_write_lock(root):
        ready.set()
        if crash:
            os._exit(0)
        time.sleep(0.5)


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
        "metrics": {
            "ebitda": {"month": "2800", "prior": "3000", "ytd": "8400", "ytd_prior": "9000", "account_ids": ["4000"]},
            "depreciation": {"month": "-3000", "prior": "-2900", "ytd": "-9000", "ytd_prior": "-8500", "account_ids": ["7000"]},
            "egt": {"month": "-2250", "prior": "21780", "ytd": "66700", "ytd_prior": "105200", "account_ids": ["4000", "5000"]},
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
        "provenance": {
            "input_fingerprint": hashlib.sha256(source.read_bytes()).hexdigest(),
            "mapping_version": hashlib.sha256(mapping.read_bytes()).hexdigest(),
            "calculation_version": "kmu-report-v1",
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
    assert evidence["runs"][-1]["mapped_accounts"] == 2
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


def test_acceptance_history_rejects_duplicated_replayed_runs(tmp_path, monkeypatch):
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
    (tmp_path / "project" / "pilot" / "account-mapping.json").write_text(
        '{"schema_version":1}', encoding="utf-8"
    )
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
