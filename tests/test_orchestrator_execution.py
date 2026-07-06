"""WP-A4 — the run loop is re-expressed against the ExecutionBackend port.

Two guarantees: (1) the backend is actually driven (start_run → schedule_step →
await_steps), and (2) re-hosting changes no observable output — a spying backend
that delegates to the default in-process one yields the same RunResult a direct
run would (behaviour parity)."""

from pathlib import Path

import brain

from core.execution import InProcessExecutionBackend
from core.orchestrator import AgentOrchestrator, RunSpec


class _SpyBackend:
    """Records port calls, delegates execution to the in-process adapter."""

    def __init__(self):
        self.inner = InProcessExecutionBackend()
        self.calls: list[str] = []

    def start_run(self, run_spec, *, idempotency_key):
        self.calls.append("start_run")
        return self.inner.start_run(run_spec, idempotency_key=idempotency_key)

    def schedule_step(self, run, step, *, idempotency_key):
        self.calls.append("schedule_step")
        return self.inner.schedule_step(run, step, idempotency_key=idempotency_key)

    def await_steps(self, run, steps):
        self.calls.append("await_steps")
        return self.inner.await_steps(run, steps)

    def signal(self, run, name, payload):
        return self.inner.signal(run, name, payload)

    def timer(self, run, seconds):
        return self.inner.timer(run, seconds)

    def resume(self, run_id):
        return self.inner.resume(run_id)


def _orchestrator(tmp_path: Path, backend=None) -> AgentOrchestrator:
    (tmp_path / "state").mkdir(exist_ok=True)
    return AgentOrchestrator(tmp_path, execution_backend=backend)


def test_run_drives_the_execution_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    spy = _SpyBackend()
    result = _orchestrator(tmp_path, backend=spy).run("do a small task")
    # start_run happens once; at least one step is scheduled and awaited.
    assert spy.calls.count("start_run") == 1
    assert "schedule_step" in spy.calls
    assert "await_steps" in spy.calls
    assert isinstance(result.run_spec, RunSpec)


def test_behaviour_parity_between_default_and_spy_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})

    default_result = _orchestrator(tmp_path).run("summarize the notes", request_id="fixed")
    spy_result = _orchestrator(tmp_path, backend=_SpyBackend()).run(
        "summarize the notes", request_id="fixed"
    )

    assert default_result.success == spy_result.success
    assert default_result.metadata["outputs"] == spy_result.metadata["outputs"]
    assert default_result.metadata["dispatch_count"] == spy_result.metadata["dispatch_count"]
    assert default_result.run_spec.run_id == spy_result.run_spec.run_id


def test_run_spec_is_synthesized_for_offline_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    result = _orchestrator(tmp_path).run("a task")
    assert result.run_spec.tenant_id == "local"
    assert result.run_spec.request_id  # a fresh unique id per invocation


def test_repeated_task_on_same_orchestrator_reexecutes_side_effects(tmp_path, monkeypatch):
    """Regression (WP-A4): a long-lived orchestrator (the agent.py singleton
    pattern) running the SAME task text twice must re-execute the tool both
    times — the ExecutionBackend cache must not dedupe two separate runs. Guards
    against the run_id-collision that a task-derived request_id would cause."""
    import json

    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    # A mocked LLM plan that actually dispatches a tool, so the side-effect count
    # is a real (non-vacuous) assertion.
    plan = {"steps": [{"id": "s1", "action": "use_tool", "description": "act", "tool": "probe", "input": "go"}]}
    monkeypatch.setattr(brain, "complete", lambda *a, **k: json.dumps(plan))

    class _CountingTool:
        description = "counts invocations"

        def __init__(self):
            self.calls = 0

        def safe_run(self, input_str: str) -> str:
            self.calls += 1
            return f"call #{self.calls}"

    tool = _CountingTool()
    orch = _orchestrator(tmp_path)  # ONE orchestrator, ONE backend, reused
    r1 = orch.run("run the probe task", tools={"probe": tool})
    r2 = orch.run("run the probe task", tools={"probe": tool})

    # Distinct runs must get distinct run ids (no silent dedupe)...
    assert r1.run_spec.run_id != r2.run_spec.run_id
    # ...and the tool must have run on BOTH passes, not been replayed once. Under
    # the pre-fix task-derived request_id, calls would stay 1 (second run cached).
    assert tool.calls == 2


def test_duplicate_plan_step_ids_do_not_collide_in_backend(tmp_path, monkeypatch):
    """Regression (WP-A4): two plan steps sharing an id must both execute; the
    backend key disambiguates on a per-run sequence, not the plan id alone."""
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    # An LLM plan with two DISTINCT executable steps that share id "dup".
    import json

    payload = {
        "steps": [
            {"id": "dup", "action": "execute", "description": "first action", "tool": None},
            {"id": "dup", "action": "execute", "description": "second action", "tool": None},
        ]
    }
    monkeypatch.setattr(brain, "complete", lambda *a, **k: json.dumps(payload))
    result = _orchestrator(tmp_path).run("do two things")
    outputs = result.metadata["outputs"]
    # Both steps produced their own dispatch output — the second was not a replay
    # of the first (which would make the two outputs identical / drop one).
    assert any("first action" in o for o in outputs)
    assert any("second action" in o for o in outputs)
