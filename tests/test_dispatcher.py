"""Dispatcher — the single side-effect seam (pure routing logic, no model)."""

from core.dispatcher import Dispatcher, DispatchResult
from core.planner import PlanStep


def _step(**kw) -> PlanStep:
    base = {"id": "step_1", "action": "execute", "description": "do the thing"}
    base.update(kw)
    return PlanStep(**base)


class _EchoTool:
    def safe_run(self, input_str: str) -> str:
        return f"ECHO:{input_str}"


class _FailingTool:
    def safe_run(self, input_str: str) -> str:
        return "FEHLER: could not run"


def test_dispatch_runs_available_tool():
    result = Dispatcher().dispatch(_step(tool="echo", input="hi"), tools={"echo": _EchoTool()})
    assert isinstance(result, DispatchResult)
    assert result.success is True
    assert result.output == "ECHO:hi"
    assert result.tool == "echo"


def test_dispatch_tool_output_starting_with_fehler_is_failure():
    result = Dispatcher().dispatch(_step(tool="bad"), tools={"bad": _FailingTool()})
    assert result.success is False
    assert result.output.startswith("FEHLER")


def test_dispatch_missing_tool_fails_closed():
    result = Dispatcher().dispatch(_step(tool="ghost"), tools={})
    assert result.success is False
    assert "not available" in result.output
    assert result.metadata["step"] == "step_1"


def test_dispatch_use_tool_without_tool_is_error():
    result = Dispatcher().dispatch(_step(action="use_tool", tool=None), tools={})
    assert result.success is False
    assert "requires a tool" in result.output
    assert result.metadata["action"] == "use_tool"


def test_dispatch_planning_step_without_tool_is_recorded():
    result = Dispatcher().dispatch(_step(action="inspect", tool=None, description="look around"))
    assert result.success is True
    assert "Planned step recorded" in result.output
    assert result.metadata["action"] == "inspect"


def test_dispatch_defaults_empty_tools_to_none():
    # tools=None branch must be handled without raising.
    result = Dispatcher().dispatch(_step(action="inspect", tool=None))
    assert result.success is True
