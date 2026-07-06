"""Tests für das einzelne Verifier-Antwort-Gate (ADR-0019 O1) + Run-Identität (G4).

No output reaches the caller as a success without the one verifier pass.
"""

from core.orchestrator import AgentOrchestrator, RunSpec
from core.planner import Plan, PlanStep
from core.verifier import VerificationResult


class _StubPlanner:
    def draft(self, task, context="", project=None, tools=None):
        return Plan(
            task=task,
            steps=[PlanStep(id="s1", action="use_tool", description="probe", tool="probe", input="go")],
            confidence=0.5,
        )


class _RecordingVerifier:
    def __init__(self, passed):
        self.calls = 0
        self._passed = passed

    def verify(self, output, threshold=7, *, task="", step="", context=None):
        self.calls += 1
        return VerificationResult(passed=self._passed, score=9 if self._passed else 1)


class _MockTool:
    name = "probe"
    description = ""

    def safe_run(self, input_str):
        return "ein ergebnis"


def _orch(tmp_root, verifier):
    return AgentOrchestrator(tmp_root, planner=_StubPlanner(), verifier=verifier)


class TestAnswerGate:
    def test_failing_verifier_makes_run_unsuccessful(self, tmp_root):
        verifier = _RecordingVerifier(passed=False)
        result = _orch(tmp_root, verifier).run("tu etwas", tools={"probe": _MockTool()})
        assert verifier.calls >= 1  # the gate was consulted
        assert result.success is False  # output did not ship despite being produced
        assert result.metadata["outputs"]  # output existed...
        # ...but success is gated on the verifier, not on step execution.

    def test_passing_verifier_ships_the_output(self, tmp_root):
        verifier = _RecordingVerifier(passed=True)
        result = _orch(tmp_root, verifier).run("tu etwas", tools={"probe": _MockTool()})
        assert verifier.calls == 1
        assert result.success is True


class TestRunIdentity:
    def test_run_spec_synthesized_when_absent(self, tmp_root):
        result = _orch(tmp_root, _RecordingVerifier(True)).run("tu etwas", tools={"probe": _MockTool()})
        assert isinstance(result.run_spec, RunSpec)
        assert result.run_spec.tenant_id == "local"
        assert result.run_spec.request_id  # deterministic hash of the task

    def test_run_spec_is_deterministic_per_task(self, tmp_root):
        orch = _orch(tmp_root, _RecordingVerifier(True))
        r1 = orch.run("gleiche aufgabe", tools={"probe": _MockTool()})
        r2 = orch.run("gleiche aufgabe", tools={"probe": _MockTool()})
        assert r1.run_spec.request_id == r2.run_spec.request_id

    def test_explicit_tenant_and_request_id_are_honored(self, tmp_root):
        result = _orch(tmp_root, _RecordingVerifier(True)).run(
            "tu etwas", tools={"probe": _MockTool()}, tenant="acme", request_id="req-1"
        )
        assert result.run_spec.run_id == "acme:req-1"
