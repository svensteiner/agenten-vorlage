import json
from datetime import datetime, timezone
from pathlib import Path

from core.scheduling import AdaptiveScheduler


def _write_schedule(root: Path, **overrides) -> Path:
    config = {
        "version": 1,
        "input_paths": ["incoming"],
        "review_interval_hours": 24,
        "prompt": {
            "template": "Pruefe {agent_name}: {reasons}. Metadaten: {metadata_json}",
        },
    }
    config.update(overrides)
    path = root / "project" / "schedule.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_missing_schedule_disables_scheduler(tmp_path: Path):
    scheduler = AdaptiveScheduler(tmp_path, {"agent_name": "pilot"})
    assert scheduler.evaluate().should_enqueue is False
    assert scheduler.evaluate().reason == "schedule_disabled"


def test_new_input_enqueues_metadata_only_prompt_and_is_idempotent(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "salden.xlsx").write_text("private ledger values", encoding="utf-8")
    _write_schedule(tmp_path)
    scheduler = AdaptiveScheduler(tmp_path, {"agent_name": "pilot"})

    first = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert first.should_enqueue is True
    assert first.reason == "input_changed"
    assert "private ledger values" not in first.task_text
    assert "salden.xlsx" in first.task_text
    assert first.request_id

    repeated = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert repeated.request_id == first.request_id
    scheduler.mark_enqueued(first)
    again = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert again.should_enqueue is False
    assert again.reason == "idle"


def test_changed_input_creates_new_request_id(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    source = tmp_path / "incoming" / "report.csv"
    source.write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path)
    scheduler = AdaptiveScheduler(tmp_path, {})
    first = scheduler.evaluate()
    scheduler.mark_enqueued(first)
    source.write_text("v2", encoding="utf-8")
    second = scheduler.evaluate()
    assert second.should_enqueue is True
    assert second.request_id != first.request_id


def test_open_approval_and_periodic_review_trigger_work(tmp_path: Path):
    _write_schedule(tmp_path)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "approvals.json").write_text('[{"status": "pending", "id": "a-1"}]', encoding="utf-8")
    scheduler = AdaptiveScheduler(tmp_path, {})
    decision = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert decision.should_enqueue
    assert decision.reason == "approval_pending"

    (state_dir / "approvals.json").write_text("[]", encoding="utf-8")
    scheduler = AdaptiveScheduler(tmp_path, {})
    scheduler.record_result(success=True, now=datetime(2026, 7, 20, tzinfo=timezone.utc))
    review = scheduler.evaluate(now=datetime(2026, 7, 21, 1, tzinfo=timezone.utc))
    assert review.should_enqueue
    assert review.reason == "periodic_review"


def test_failures_freeze_after_three_and_state_is_atomic(tmp_path: Path):
    _write_schedule(tmp_path)
    scheduler = AdaptiveScheduler(tmp_path, {})
    now = datetime(2026, 7, 21, tzinfo=timezone.utc)
    for _ in range(3):
        scheduler.record_result(success=False, now=now)
    frozen = scheduler.evaluate(now=now)
    assert frozen.should_enqueue is False
    assert frozen.reason == "frozen_after_failures"
    assert (tmp_path / "state" / "scheduler-state.json").exists()
    assert not list((tmp_path / "state").glob("*.tmp"))


def test_failure_recovery_is_enqueued_before_review(tmp_path: Path):
    _write_schedule(tmp_path, review_interval_hours=999)
    scheduler = AdaptiveScheduler(tmp_path, {})
    scheduler.record_result(success=False, now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    recovery = scheduler.evaluate(now=datetime(2026, 7, 21, 1, tzinfo=timezone.utc))
    assert recovery.should_enqueue
    assert recovery.reason == "recovery"


def test_embedded_instance_schedule_uses_hourly_preset_profile(tmp_path: Path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "july.csv").write_text("data", encoding="utf-8")
    scheduler = AdaptiveScheduler(tmp_path, {
        "adaptive_schedule": {
            "enabled": True,
            "input_globs": ["inbox/**/*"],
            "state_file": "state/acme-schedule.json",
            "prompt_profiles": {"new_input": "Validiere neue Daten: {metadata_json}"},
            "max_consecutive_failures": 3,
        },
    })
    decision = scheduler.evaluate()
    assert decision.reason == "new_input"
    assert "data" not in decision.task_text
    scheduler.mark_enqueued(decision)
    assert (tmp_path / "state" / "acme-schedule.json").is_file()
