"""Tests für die Handoff-Verdrahtung im Orchestrator-Loop (WP-A2, ADR-0019 O4).

A handoff embedded in a step's output is validated against the allowlist before
control could transfer; an invalid handoff is refused (``handoff_refused``).
"""

from core.handoff import HandoffRouter
from core.orchestrator import AgentOrchestrator
from core.planner import Plan, PlanStep
from core.verifier import VerificationResult


class _StubPlanner:
    def __init__(self, steps):
        self._steps = steps

    def draft(self, task, context="", project=None, tools=None):
        return Plan(task=task, steps=list(self._steps), confidence=0.5)


class _StubVerifier:
    def verify(self, output, threshold=7, *, task="", step="", context=None):
        return VerificationResult(passed=True, score=9)


class _HandoffTool:
    """Emits a handoff block toward the given target."""

    def __init__(self, target):
        self.name = "probe"
        self.description = ""
        self._target = target

    def safe_run(self, input_str):
        return (
            "Ich delegiere.\n"
            f'<<HANDOFF>>{{"target": "{self._target}", "task": "Analysiere x"}}<<END_HANDOFF>>'
        )


def _orch(tmp_root, steps, allowlist):
    return AgentOrchestrator(
        tmp_root,
        planner=_StubPlanner(steps),
        verifier=_StubVerifier(),
        handoffs=HandoffRouter(allowlist=allowlist, max_payload_chars=2000),
    )


def _step():
    return PlanStep(id="s1", action="use_tool", description="probe", tool="probe", input="go")


class TestHandoffRefused:
    def test_unlisted_target_is_refused(self, tmp_root):
        orch = _orch(tmp_root, [_step()], allowlist=["reader"])
        result = orch.run("delegiere an hacker", tools={"probe": _HandoffTool("hacker")})
        assert result.success is False
        assert result.metadata["status"] == "handoff_refused"
        assert result.metadata["target"] == "hacker"

    def test_oversized_handoff_is_refused(self, tmp_root):
        class _BigHandoff:
            name = "probe"
            description = ""

            def safe_run(self, input_str):
                big = "x" * 5000
                return f'<<HANDOFF>>{{"target": "reader", "task": "{big}"}}<<END_HANDOFF>>'

        orch = AgentOrchestrator(
            tmp_root,
            planner=_StubPlanner([_step()]),
            verifier=_StubVerifier(),
            handoffs=HandoffRouter(allowlist=["reader"], max_payload_chars=100),
        )
        result = orch.run("delegiere groß", tools={"probe": _BigHandoff()})
        assert result.metadata["status"] == "handoff_refused"


class TestHandoffAccepted:
    def test_allowlisted_target_is_recorded(self, tmp_root):
        orch = _orch(tmp_root, [_step()], allowlist=["reader", "writer"])
        result = orch.run("delegiere an reader", tools={"probe": _HandoffTool("reader")})
        assert result.metadata.get("status") != "handoff_refused"
        assert result.metadata["handoff_count"] == 1
        assert result.metadata["handoffs"][0]["target"] == "reader"

    def test_no_handoff_in_output_is_noop(self, tmp_root):
        class _PlainTool:
            name = "probe"
            description = ""

            def safe_run(self, input_str):
                return "Einfaches Ergebnis ohne Handoff."

        orch = _orch(tmp_root, [_step()], allowlist=["reader"])
        result = orch.run("normale aufgabe", tools={"probe": _PlainTool()})
        assert result.metadata.get("handoff_count", 0) == 0
