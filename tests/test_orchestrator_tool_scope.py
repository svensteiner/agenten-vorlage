"""Tests für die Tool-Scope-Verdrahtung im Orchestrator-Loop (WP-A1, ADR-0019 O3/O5).

The WorkerRegistry is enforced *in the loop*, not merely available: a step whose
acting worker lacks the tool is blocked with status ``tool_scope_blocked``.
"""

from core.orchestrator import AgentOrchestrator
from core.planner import Plan, PlanStep
from core.verifier import VerificationResult
from core.workers import WorkerRegistry


class _StubPlanner:
    def __init__(self, steps):
        self._steps = steps

    def draft(self, task, context="", project=None, tools=None):
        return Plan(task=task, steps=list(self._steps), confidence=0.5)


class _StubVerifier:
    def __init__(self, passed=True):
        self._passed = passed

    def verify(self, output, threshold=7, *, task="", step="", context=None):
        return VerificationResult(passed=self._passed, score=9 if self._passed else 1)


class _MockTool:
    def __init__(self, name, output="OK"):
        self.name = name
        self.description = ""
        self._output = output

    def safe_run(self, input_str):
        return self._output


REGISTRY = WorkerRegistry(
    {
        "workers": {
            "reader": {"tools": ["file_read", "web_search"], "trust_level": "low"},
            "writer": {"tools": ["file_write", "notify"], "trust_level": "high"},
        }
    }
)


def _orch(tmp_root, steps, **kw):
    return AgentOrchestrator(
        tmp_root,
        planner=_StubPlanner(steps),
        verifier=_StubVerifier(kw.pop("passed", True)),
        workers=REGISTRY,
        **kw,
    )


class TestToolScopeBlocked:
    def test_reader_calling_notify_is_blocked_in_the_loop(self, tmp_root):
        step = PlanStep(
            id="s1",
            action="use_tool",
            description="notify the team",
            tool="notify",
            input="hi",
            metadata={"worker": "reader"},  # reader has no notify scope
        )
        orch = _orch(tmp_root, [step])
        result = orch.run("sende eine benachrichtigung", tools={"notify": _MockTool("notify")})
        assert result.success is False
        assert result.metadata["status"] == "tool_scope_blocked"
        assert result.metadata["worker"] == "reader"
        assert result.metadata["tool"] == "notify"

    def test_reader_calling_file_write_is_blocked(self, tmp_root):
        step = PlanStep(
            id="s1",
            action="use_tool",
            description="write output",
            tool="file_write",
            input="write:x.txt|hi",
            metadata={"worker": "reader"},
        )
        orch = _orch(tmp_root, [step])
        result = orch.run("schreibe etwas", tools={"file_write": _MockTool("file_write")})
        assert result.metadata["status"] == "tool_scope_blocked"


class TestToolScopeAllowed:
    def test_writer_may_use_notify(self, tmp_root):
        step = PlanStep(
            id="s1",
            action="use_tool",
            description="notify the team",
            tool="notify",
            input="hi",
            metadata={"worker": "writer"},
        )
        orch = _orch(tmp_root, [step])
        result = orch.run("sende benachrichtigung", tools={"notify": _MockTool("notify", "SENT")})
        assert result.metadata.get("status") != "tool_scope_blocked"
        assert result.success is True

    def test_reader_may_use_web_search(self, tmp_root):
        step = PlanStep(
            id="s1",
            action="use_tool",
            description="recherchiere",
            tool="web_search",
            input="query",
            metadata={"worker": "reader"},
        )
        orch = _orch(tmp_root, [step])
        result = orch.run("recherchiere etwas", tools={"web_search": _MockTool("web_search", "R")})
        assert result.metadata.get("status") != "tool_scope_blocked"

    def test_orchestrator_direct_action_is_not_scope_gated(self, tmp_root):
        # No explicit worker + no sub-agent → orchestrator acts, governance covers it.
        step = PlanStep(id="s1", action="use_tool", description="notify", tool="notify", input="hi")
        orch = _orch(tmp_root, [step])
        result = orch.run("melde etwas", tools={"notify": _MockTool("notify", "SENT")})
        assert result.metadata.get("status") != "tool_scope_blocked"
