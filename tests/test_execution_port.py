"""Tests für core.execution — the ExecutionBackend port has NO decision method.

The port-purity test is the grep-invariant that makes ADR-0019's "the execution
plane cannot make a decision" a machine check, mirroring the VectorIndex
no-unfiltered-method rule.
"""
import pytest

from core.execution import (
    DECISION_VERBS,
    ExecutionBackend,
    InProcessExecutionBackend,
    RunSpec,
    Step,
    StepResult,
)


def _port_methods() -> set[str]:
    return {name for name in dir(ExecutionBackend) if not name.startswith("_")}


class TestPortPurity:
    def test_port_exposes_no_decision_method(self):
        methods = _port_methods()
        # No method name may contain a decision verb.
        for method in methods:
            for verb in DECISION_VERBS:
                assert verb not in method, f"port method '{method}' leaks decision verb '{verb}'"

    def test_port_surface_is_exactly_the_execution_verbs(self):
        assert _port_methods() == {
            "start_run",
            "schedule_step",
            "await_steps",
            "signal",
            "timer",
            "resume",
        }

    def test_inprocess_backend_satisfies_protocol(self):
        assert isinstance(InProcessExecutionBackend(), ExecutionBackend)


class TestInProcessBackend:
    def test_schedule_and_await_runs_activity(self):
        backend = InProcessExecutionBackend()
        spec = RunSpec(tenant_id="t", request_id="r1")
        run = backend.start_run(spec, idempotency_key=spec.run_id)

        calls: list[str] = []

        def activity() -> StepResult:
            calls.append("ran")
            return StepResult(id="s1", output="done", success=True)

        sh = backend.schedule_step(run, Step(id="s1", activity=activity), idempotency_key="s1")
        results = backend.await_steps(run, [sh])
        assert [r.output for r in results] == ["done"]
        assert calls == ["ran"]

    def test_await_is_idempotent(self):
        backend = InProcessExecutionBackend()
        spec = RunSpec(tenant_id="t", request_id="r1")
        run = backend.start_run(spec, idempotency_key=spec.run_id)
        counter: list[int] = []

        def activity() -> StepResult:
            counter.append(1)
            return StepResult(id="s1", output="x")

        sh = backend.schedule_step(run, Step(id="s1", activity=activity), idempotency_key="s1")
        backend.await_steps(run, [sh])
        backend.await_steps(run, [sh])  # cached — activity runs once
        assert len(counter) == 1

    def test_start_run_is_idempotent(self):
        backend = InProcessExecutionBackend()
        spec = RunSpec(tenant_id="t", request_id="r1")
        r1 = backend.start_run(spec, idempotency_key=spec.run_id)
        r2 = backend.start_run(spec, idempotency_key=spec.run_id)
        assert r1 is r2

    def test_resume_unknown_run_raises(self):
        backend = InProcessExecutionBackend()
        with pytest.raises(KeyError):
            backend.resume("nope")

    def test_run_id_format(self):
        assert RunSpec(tenant_id="acme", request_id="abc").run_id == "acme:abc"
