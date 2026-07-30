"""Operation-id replay and verified report-byte contracts."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from core.controlling import artifacts as artifacts_module
from core.controlling.artifacts import (
    read_acceptance_status,
    read_verified_latest_report_html,
)
from core.controlling.narrative import ControllingReportTool
from test_controlling_artifacts import _aggregate_report, _write_acceptance_mapping


def _tool_with_valid_inputs(tmp_path, monkeypatch) -> ControllingReportTool:
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source.parent.mkdir(parents=True)
    source.write_text("Konto;Monat\n4000;1\n", encoding="utf-8")
    _write_acceptance_mapping(tmp_path)
    tool = ControllingReportTool(tmp_path)
    monkeypatch.setattr(
        tool._compute,
        "safe_run",
        lambda *_: json.dumps(_aggregate_report(tmp_path), ensure_ascii=False),
    )
    return tool


def test_operation_id_replays_its_original_result_without_new_acceptance_run(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    first = json.loads(tool.safe_run('{"source":"auto","operation_id":"order-1"}'))
    replay = json.loads(tool.safe_run('{"source":"auto","operation_id":"order-1"}'))

    assert replay == first
    assert read_acceptance_status(tmp_path)["sequence"] == 1


def test_distinct_operation_ids_create_distinct_signed_runs(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    for operation_id in ("order-1", "order-2", "order-3"):
        json.loads(tool.safe_run(json.dumps({"operation_id": operation_id})))

    status = read_acceptance_status(tmp_path)
    assert status["sequence"] == 3
    assert status["passed"] is True


def test_operation_id_allows_safe_child_slot_separator(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    response = json.loads(tool.safe_run('{"operation_id":"verify-order-1:3"}'))

    assert response["operation_id"] == "verify-order-1:3"


def test_operation_id_replays_original_result_after_later_operation(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    first = json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    json.loads(tool.safe_run('{"operation_id":"order-2"}'))
    replay = json.loads(tool.safe_run('{"operation_id":"order-1"}'))

    assert replay == first
    assert read_acceptance_status(tmp_path)["sequence"] == 2


def test_latest_operation_replay_repairs_interrupted_shared_publication(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    original_atomic_json = artifacts_module._atomic_json
    interrupted = False

    def interrupt_after_commit(path, value):
        nonlocal interrupted
        if path.name == "acceptance-evidence.json" and not interrupted:
            interrupted = True
            raise OSError("simulated crash after signed commit")
        return original_atomic_json(path, value)

    monkeypatch.setattr(artifacts_module, "_atomic_json", interrupt_after_commit)
    first = tool.safe_run('{"operation_id":"order-1"}')
    assert first.startswith("FEHLER:")
    assert read_acceptance_status(tmp_path)["sequence"] == 1

    replay = json.loads(tool.safe_run('{"operation_id":"order-1"}'))

    assert replay["operation_id"] == "order-1"
    assert read_acceptance_status(tmp_path)["sequence"] == 1
    assert (tmp_path / "artifacts" / "latest-controlling-report.html").is_file()


def test_next_operation_recovers_uncommitted_partial_ledger_suffix(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    ledger = tmp_path / "state" / "acceptance-ledger.jsonl"
    with ledger.open("ab") as stream:
        stream.write(b'{"partial_uncommitted_append":')

    second = json.loads(tool.safe_run('{"operation_id":"order-2"}'))

    assert second["operation_id"] == "order-2"
    assert read_acceptance_status(tmp_path)["sequence"] == 2
    assert ledger.read_bytes().endswith(b"\n")


def test_concurrent_same_operation_id_creates_one_signed_run(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: json.loads(tool.safe_run('{"operation_id":"order-1"}')),
                range(2),
            )
        )

    assert responses[0] == responses[1]
    assert read_acceptance_status(tmp_path)["sequence"] == 1


def test_reused_operation_id_with_different_result_fails_closed(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    changed = _aggregate_report(tmp_path)
    changed["metrics"]["ebitda"]["month"] = "999"
    monkeypatch.setattr(tool._compute, "safe_run", lambda *_: json.dumps(changed))

    response = tool.safe_run('{"operation_id":"order-1"}')

    assert response.startswith("FEHLER:")
    assert read_acceptance_status(tmp_path)["sequence"] == 1


def test_reused_operation_id_with_semantically_equal_but_changed_source_conflicts(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    source.write_text("Konto;Monat\n4000;01\n", encoding="utf-8")

    response = tool.safe_run('{"operation_id":"order-1"}')

    assert response.startswith("FEHLER:")
    evidence = json.loads(
        (tmp_path / "artifacts" / "acceptance-evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(evidence["runs"]) == 1


def test_replay_revalidates_source_after_waiting_for_acceptance_lock(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    source = tmp_path / "inbox" / "actuals" / "demo.csv"
    original_lock = artifacts_module._acceptance_write_lock

    @contextmanager
    def lock_then_replace_source(root):
        with original_lock(root):
            source.write_text("Konto;Monat\n4000;01\n", encoding="utf-8")
            yield

    monkeypatch.setattr(
        artifacts_module, "_acceptance_write_lock", lock_then_replace_source
    )

    response = tool.safe_run('{"operation_id":"order-1"}')

    assert response.startswith("FEHLER:")
    assert read_acceptance_status(tmp_path)["sequence"] == 1


@pytest.mark.parametrize(
    "operation_id",
    ("", " ", "../order", "order/id", "order\\id", "order\n1", "a" * 129, 3),
)
def test_operation_id_must_be_a_bounded_safe_string(tmp_path, monkeypatch, operation_id):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)

    response = tool.safe_run(json.dumps({"operation_id": operation_id}))

    assert response.startswith("FEHLER: operation_id")
    assert not (tmp_path / "state" / "acceptance-ledger.jsonl").exists()


def test_verified_latest_report_html_returns_opened_validated_bytes(tmp_path, monkeypatch):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))

    html_bytes = read_verified_latest_report_html(tmp_path)

    assert html_bytes == (tmp_path / "artifacts" / "latest-controlling-report.html").read_bytes()


def test_verified_latest_report_can_require_signed_three_run_acceptance(
    tmp_path, monkeypatch
):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))

    with pytest.raises(ValueError, match="3/3"):
        read_verified_latest_report_html(tmp_path, require_passed=True)

    json.loads(tool.safe_run('{"operation_id":"order-2"}'))
    json.loads(tool.safe_run('{"operation_id":"order-3"}'))

    assert read_verified_latest_report_html(tmp_path, require_passed=True).startswith(
        b"<!doctype html>"
    )


@pytest.mark.parametrize("mutation", ("tamper", "oversize", "symlink"))
def test_verified_latest_report_html_fails_closed(tmp_path, monkeypatch, mutation):
    tool = _tool_with_valid_inputs(tmp_path, monkeypatch)
    json.loads(tool.safe_run('{"operation_id":"order-1"}'))
    html = tmp_path / "artifacts" / "latest-controlling-report.html"
    if mutation == "tamper":
        html.write_text("tampered", encoding="utf-8")
    elif mutation == "oversize":
        monkeypatch.setattr(artifacts_module, "_MAX_PUBLISHED_VIEW_BYTES", 1)
    else:
        target = tmp_path / "html-target"
        target.write_text(html.read_text(encoding="utf-8"), encoding="utf-8")
        html.unlink()
        try:
            html.symlink_to(target)
        except OSError:
            pytest.skip("Symlinks unavailable for this test account")

    with pytest.raises(ValueError):
        read_verified_latest_report_html(tmp_path)
