import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

import core.scheduling as scheduling
from core.scheduling import AdaptiveScheduler, run_scheduled_cycle


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
    assert "salden.xlsx" not in first.task_text
    assert "incoming" not in first.task_text
    assert first.request_id

    repeated = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert repeated.request_id == first.request_id
    scheduler.mark_enqueued(first)
    again = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    assert again.should_enqueue is False
    assert again.reason == "already_enqueued"


def test_changed_input_creates_new_request_id(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    source = tmp_path / "incoming" / "report.csv"
    source.write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path)
    scheduler = AdaptiveScheduler(tmp_path, {})
    first = scheduler.evaluate()
    scheduler.mark_enqueued(first)
    scheduler.record_result(success=True)
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
    assert decision.reason == "pending_approval"

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


def test_parametrized_cycle_uses_instance_root_and_orchestrator(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("safe", encoding="utf-8")
    _write_schedule(tmp_path)
    calls = []

    class FakeOrchestrator:
        def run(self, task, *, tools, request_id):
            calls.append((task, tools, request_id))
            return type("Result", (), {"success": True})()

    outcome = run_scheduled_cycle(
        root=tmp_path,
        agent_config={"agent_name": "instance-agent"},
        orchestrator=FakeOrchestrator(),
        tools={"read": object()},
    )
    assert outcome.should_enqueue
    assert calls and "instance-agent" in calls[0][0]
    assert calls[0][2] == outcome.request_id
    assert (tmp_path / "state" / "scheduler-state.json").is_file()


def test_prompt_never_exposes_tenant_paths_or_hashes(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "secret-client.csv").write_text("sensitive", encoding="utf-8")
    _write_schedule(tmp_path)
    decision = AdaptiveScheduler(tmp_path, {
        "agent_name": "pilot",
        "instance": {"tenant_id": "acme-secret", "agent_id": "pilot-7"},
    }).evaluate()
    assert decision.task_text
    assert "acme-secret" not in decision.task_text
    assert "secret-client.csv" not in decision.task_text
    assert "incoming" not in decision.task_text
    assert "sha256" not in decision.task_text


def test_failures_retry_with_bounded_distinct_attempt_ids(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path, max_consecutive_failures=2)
    scheduler = AdaptiveScheduler(tmp_path, {})
    first = scheduler.evaluate()
    scheduler.mark_enqueued(first)
    scheduler.record_result(success=False)
    retry = scheduler.evaluate()
    assert retry.should_enqueue and retry.reason == "recovery"
    assert retry.request_id != first.request_id
    scheduler.mark_enqueued(retry)
    scheduler.record_result(success=False)
    assert scheduler.evaluate().reason == "frozen_after_failures"


def test_in_flight_request_becomes_failure_after_crash(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path)
    scheduler = AdaptiveScheduler(tmp_path, {})
    first = scheduler.evaluate()
    scheduler.mark_enqueued(first)
    state_path = tmp_path / "state" / "scheduler-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["in_flight_at"] = "2000-01-01T00:00:00+00:00"
    state["in_flight_heartbeat_at"] = "2000-01-01T00:00:00+00:00"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    recovered = AdaptiveScheduler(tmp_path, {}).evaluate()
    assert recovered.should_enqueue and recovered.reason == "recovery"
    assert recovered.request_id != first.request_id


def _required_inputs_config(groups):
    return {
        "adaptive_schedule": {
            "enabled": True,
            "input_globs": ["inbox/**/*"],
            "required_input_groups": groups,
            "prompt_profiles": {
                "missing_data": "Fordere fehlende Daten an: {metadata_json}",
                "new_input": "Pruefe neue Daten: {metadata_json}",
            },
        },
    }


def test_required_inputs_missing_names_only_safe_group_identifiers(tmp_path: Path):
    scheduler = AdaptiveScheduler(tmp_path, _required_inputs_config([
        {"name": "actuals", "globs": ["inbox/actuals-*.csv"], "minimum": 1},
        {"name": "BWA vertraulich", "globs": ["inbox/bwa-*.csv"], "minimum": 1},
    ]))
    decision = scheduler.evaluate()
    assert decision.should_enqueue and decision.reason == "missing_data"
    assert '"id": "actuals"' in decision.task_text
    assert '"id": "group_2"' in decision.task_text
    assert "BWA vertraulich" not in decision.task_text
    assert "inbox" not in decision.task_text
    assert "bwa-" not in decision.task_text
    assert '"required_input_counts": [0, 0]' in decision.task_text


def test_missing_data_cycle_is_successful_toolless_and_not_retried(tmp_path: Path):
    calls = []

    class StatusOrchestrator:
        def run(self, task, *, tools, request_id):
            calls.append((task, tools, request_id))
            return type("Result", (), {"success": True})()

    config = _required_inputs_config([
        {"name": "actuals", "globs": ["inbox/*.csv"], "minimum": 1},
    ])
    first = run_scheduled_cycle(
        root=tmp_path,
        agent_config=config,
        orchestrator=StatusOrchestrator(),
        tools={"compute": object(), "notify": object()},
    )
    repeated = run_scheduled_cycle(
        root=tmp_path,
        agent_config=config,
        orchestrator=StatusOrchestrator(),
        tools={"compute": object(), "notify": object()},
    )

    assert first.should_enqueue and first.reason == "missing_data"
    assert repeated.should_enqueue is False
    assert repeated.reason == "already_enqueued"
    assert len(calls) == 1
    assert calls[0][1] == {}
    state = json.loads(
        (tmp_path / "state" / "scheduler-state.json").read_text(encoding="utf-8")
    )
    assert state["last_result"] == "success"
    assert state["consecutive_failures"] == 0


def test_required_inputs_partial_group_is_missing_and_complete_group_is_new_input(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "bwa-july.csv").write_text("bwa", encoding="utf-8")
    config = _required_inputs_config([
        {"name": "reports", "globs": ["inbox/*.csv"], "minimum": 2},
    ])
    assert AdaptiveScheduler(tmp_path, config).evaluate().reason == "missing_data"
    (inbox / "budget-july.csv").write_text("budget", encoding="utf-8")
    assert AdaptiveScheduler(tmp_path, config).evaluate().reason == "new_input"


def test_unsafe_required_input_globs_fail_closed_as_missing_data(tmp_path: Path):
    scheduler = AdaptiveScheduler(tmp_path, _required_inputs_config([
        {"name": "unsafe", "globs": ["../outside/*", "C:/sensitive/*"], "minimum": 1},
    ]))
    decision = scheduler.evaluate()
    assert decision.reason == "missing_data"


def test_fresh_in_flight_lease_prevents_concurrent_retry(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path)
    first = AdaptiveScheduler(tmp_path, {})
    decision = first.evaluate()
    first.mark_enqueued(decision)

    second = AdaptiveScheduler(tmp_path, {})
    concurrent = second.evaluate()
    assert concurrent.should_enqueue is False
    assert concurrent.reason == "already_enqueued"
    state = json.loads((tmp_path / "state" / "scheduler-state.json").read_text(encoding="utf-8"))
    assert state.get("consecutive_failures", 0) == 0


def test_stale_in_flight_lease_recovers_as_bounded_failure(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path, in_flight_lease_minutes=15)
    scheduler = AdaptiveScheduler(tmp_path, {})
    first = scheduler.evaluate(now=datetime(2026, 7, 21, tzinfo=timezone.utc))
    scheduler.mark_enqueued(first)
    state_path = tmp_path / "state" / "scheduler-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["in_flight_at"] = "2026-07-21T00:00:00+00:00"
    state["in_flight_heartbeat_at"] = "2026-07-21T00:00:00+00:00"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    recovered = AdaptiveScheduler(tmp_path, {}).evaluate(now=datetime(2026, 7, 21, 0, 16, tzinfo=timezone.utc))
    assert recovered.should_enqueue and recovered.reason == "recovery"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["consecutive_failures"] == 1


def test_unsafe_input_and_approval_paths_cannot_escape_instance(tmp_path: Path):
    outside = tmp_path.parent / "outside-approval.json"
    outside.write_text('[{"status": "pending"}]', encoding="utf-8")
    scheduler = AdaptiveScheduler(tmp_path, {
        "adaptive_schedule": {
            "enabled": True,
            "input_globs": ["../outside/*", "C:/outside/*"],
            "approval_state_file": "../outside-approval.json",
            "prompt_profiles": {"periodic_review": "Review: {metadata_json}"},
        },
    })
    decision = scheduler.evaluate()
    assert decision.reason == "periodic_review"
    assert "pending_approval" not in decision.task_text


def test_concurrent_cycles_acquire_one_dispatch_lock_and_execute_once(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path)
    calls: list[str] = []
    barrier = threading.Barrier(2)

    class SlowOrchestrator:
        def run(self, task, *, tools, request_id):
            calls.append(request_id)
            time.sleep(0.1)
            return type("Result", (), {"success": True})()

    outcomes = []

    def run_cycle():
        barrier.wait()
        outcomes.append(run_scheduled_cycle(
            root=tmp_path,
            agent_config={},
            orchestrator=SlowOrchestrator(),
            tools={},
        ))

    threads = [threading.Thread(target=run_cycle) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(calls) == 1
    assert sum(outcome.should_enqueue for outcome in outcomes) == 1


def test_stale_dispatch_lock_is_recovered_using_configured_lease(tmp_path: Path):
    _write_schedule(tmp_path, in_flight_lease_minutes=1)
    lock_path = tmp_path / "state" / "scheduler-state.dispatch.lock"
    lock_path.parent.mkdir()
    lock_path.write_text(json.dumps({"token": "dead", "acquired_at": "2000-01-01T00:00:00+00:00"}), encoding="utf-8")
    scheduler = AdaptiveScheduler(tmp_path, {})
    token = scheduler.acquire_dispatch_lock()
    assert token
    scheduler.release_dispatch_lock(token)
    assert not lock_path.exists()


def test_scheduler_rejects_state_path_outside_instance(tmp_path: Path):
    _write_schedule(tmp_path, state_file="../outside-state.json")

    with pytest.raises(ValueError, match="state"):
        AdaptiveScheduler(tmp_path, {})


def test_fresh_uninitialised_dispatch_lock_is_not_reclaimed(tmp_path: Path):
    """A contender can observe the lock before its owner writes the payload."""
    _write_schedule(tmp_path, in_flight_lease_minutes=1)
    lock_path = tmp_path / "state" / "scheduler-state.dispatch.lock"
    lock_path.parent.mkdir()
    lock_path.touch()

    scheduler = AdaptiveScheduler(tmp_path, {})

    assert scheduler.acquire_dispatch_lock() is None
    assert lock_path.exists()


def test_input_hashing_ignores_symlink_targets_outside_instance(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}-outside.csv"
    outside.write_text("other tenant data", encoding="utf-8")
    link = inbox / "outside.csv"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    scheduler = AdaptiveScheduler(tmp_path, _required_inputs_config([
        {"name": "actuals", "globs": ["inbox/**/*"], "minimum": 1},
    ]))

    assert scheduler._input_hashes() == {}
    assert scheduler.evaluate().reason == "missing_data"


def test_input_hashing_enforces_file_count_and_byte_budgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name in ("a.csv", "b.csv", "c.csv"):
        (inbox / name).write_bytes(b"1234")
    (inbox / "z-oversized.csv").write_bytes(b"12345678901")
    config = _required_inputs_config([])

    monkeypatch.setattr(scheduling, "MAX_INPUT_FILES", 2, raising=False)
    monkeypatch.setattr(scheduling, "MAX_INPUT_FILE_BYTES", 10, raising=False)
    monkeypatch.setattr(scheduling, "MAX_TOTAL_INPUT_BYTES", 100, raising=False)
    count_limited = AdaptiveScheduler(tmp_path, config)._input_hashes()
    assert list(count_limited) == ["inbox/a.csv", "inbox/b.csv"]
    assert "inbox/z-oversized.csv" not in count_limited

    monkeypatch.setattr(scheduling, "MAX_INPUT_FILES", 10)
    monkeypatch.setattr(scheduling, "MAX_TOTAL_INPUT_BYTES", 6)
    byte_limited = AdaptiveScheduler(tmp_path, config)._input_hashes()
    assert list(byte_limited) == ["inbox/a.csv"]


def test_stale_owner_cannot_clear_replacement_in_flight_request(tmp_path: Path):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path, in_flight_lease_minutes=1)
    first_scheduler = AdaptiveScheduler(tmp_path, {})
    first = first_scheduler.evaluate()
    first_scheduler.mark_enqueued(first)

    state_path = tmp_path / "state" / "scheduler-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["in_flight_at"] = "2000-01-01T00:00:00+00:00"
    state["in_flight_heartbeat_at"] = "2000-01-01T00:00:00+00:00"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    replacement_scheduler = AdaptiveScheduler(tmp_path, {})
    replacement = replacement_scheduler.evaluate()
    assert replacement.should_enqueue and replacement.reason == "recovery"
    replacement_scheduler.mark_enqueued(replacement)

    assert first_scheduler.record_result(success=True) is False
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["in_flight_request_id"] == replacement.request_id
    assert replacement_scheduler.record_result(success=True) is True
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "in_flight_request_id" not in state
    assert first_scheduler.record_result(success=False) is False
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["last_result"] == "success"
    assert state["consecutive_failures"] == 0


def test_live_cycle_renews_lease_and_is_not_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "report.csv").write_text("v1", encoding="utf-8")
    _write_schedule(tmp_path, in_flight_lease_minutes=1)
    started = threading.Event()
    finish = threading.Event()

    class BlockingOrchestrator:
        def run(self, task, *, tools, request_id):
            started.set()
            assert finish.wait(timeout=5)
            return type("Result", (), {"success": True})()

    monkeypatch.setattr(
        AdaptiveScheduler,
        "_heartbeat_interval_seconds",
        property(lambda self: 0.01),
        raising=False,
    )
    outcomes = []
    worker = threading.Thread(
        target=lambda: outcomes.append(run_scheduled_cycle(
            root=tmp_path,
            agent_config={},
            orchestrator=BlockingOrchestrator(),
            tools={},
        ))
    )
    worker.start()
    assert started.wait(timeout=5)

    state_path = tmp_path / "state" / "scheduler-state.json"
    probe = AdaptiveScheduler(tmp_path, {})
    token = probe.acquire_dispatch_lock()
    assert token
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["in_flight_at"] = "2000-01-01T00:00:00+00:00"
    state["in_flight_heartbeat_at"] = "2000-01-01T00:00:00+00:00"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    probe.release_dispatch_lock(token)

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("in_flight_heartbeat_at") != "2000-01-01T00:00:00+00:00":
            break
        time.sleep(0.01)
    assert state.get("in_flight_heartbeat_at") != "2000-01-01T00:00:00+00:00"
    concurrent = AdaptiveScheduler(tmp_path, {}).evaluate()
    assert concurrent.should_enqueue is False
    assert concurrent.reason == "already_enqueued"

    finish.set()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert len(outcomes) == 1
