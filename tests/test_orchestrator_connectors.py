"""Connector declarations are enforced before an identifiable connector tool runs."""

from pathlib import Path

from core.context import ConnectorSpec, ProjectContext
from core.orchestrator import AgentOrchestrator
from core.planner import Plan, PlanStep
from core.verifier import VerificationResult
from tools.notify import NotifyTool
from tools.web_search import WebSearchTool


class _StubPlanner:
    def __init__(self, step):
        self.step = step

    def draft(self, task, context="", project=None, tools=None):
        return Plan(task=task, steps=[self.step], confidence=1.0)


class _StubVerifier:
    def verify(self, *args, **kwargs):
        return VerificationResult(passed=True, score=10)


class _ConnectorTool:
    connector_name = "undeclared-crm"

    def __init__(self):
        self.calls = 0

    def safe_run(self, input_str):
        self.calls += 1
        return "sent"


class _InternalTool:
    def __init__(self):
        self.calls = 0

    def safe_run(self, input_str):
        self.calls += 1
        return "done"


def _orch(tmp_path: Path, step: PlanStep, connectors):
    orch = AgentOrchestrator(tmp_path, planner=_StubPlanner(step), verifier=_StubVerifier())
    orch.context_builder.build = lambda: ProjectContext(
        project_root=tmp_path,
        config={"require_human_approval": True},
        connectors=connectors,
    )
    return orch


def test_undeclared_identified_connector_is_blocked_before_tool_execution(tmp_path):
    step = PlanStep(id="s1", action="use_tool", description="sync", tool="sync", input="go")
    tool = _ConnectorTool()
    result = _orch(tmp_path, step, [ConnectorSpec(name="declared-crm")]).run(
        "sync customer data", tools={"sync": tool}
    )

    assert result.success is False
    assert result.metadata["status"] == "connector_blocked"
    assert tool.calls == 0


def test_internal_tool_without_connector_identity_is_not_connector_blocked(tmp_path):
    step = PlanStep(id="s1", action="use_tool", description="calculate", tool="calculate", input="1+1")
    tool = _InternalTool()
    result = _orch(tmp_path, step, [ConnectorSpec(name="declared-crm")]).run(
        "calculate", tools={"calculate": tool}
    )

    assert result.success is True
    assert tool.calls == 1


def test_web_search_uses_documented_connector_name(tmp_path, monkeypatch):
    tool = WebSearchTool()
    calls = []
    monkeypatch.setattr(tool, "run", lambda value: calls.append(value) or "sent")
    step = PlanStep(id=tool.name, action="use_tool", description="external", tool=tool.name, input="go")

    blocked = _orch(tmp_path, step, []).run("external task", tools={tool.name: tool})
    assert blocked.metadata["status"] == "connector_blocked"
    assert calls == []

    allowed = _orch(tmp_path, step, [ConnectorSpec(name="web-search")]).run(
        "external task", tools={tool.name: tool}
    )
    assert tool.connector_name == "web-search"
    assert allowed.success is True
    assert calls == ["go"]


def test_unprefixed_notify_requires_both_channel_connectors(tmp_path, monkeypatch):
    tool = NotifyTool()
    calls = []
    monkeypatch.setattr(tool, "run", lambda value: calls.append(value) or "sent")
    step = PlanStep(id="notify", action="use_tool", description="external", tool="notify", input="hello")

    blocked = _orch(tmp_path, step, [ConnectorSpec(name="slack")]).run("notify", tools={"notify": tool})
    assert blocked.metadata["status"] == "connector_blocked"
    assert blocked.metadata["connector"] == "telegram"
    assert calls == []

    allowed = _orch(tmp_path, step, [ConnectorSpec(name="slack"), ConnectorSpec(name="telegram")]).run(
        "notify", tools={"notify": tool}
    )
    assert allowed.success is True
    assert calls == ["hello"]


def test_prefixed_notify_requires_only_its_selected_channel(tmp_path, monkeypatch):
    tool = NotifyTool()
    calls = []
    monkeypatch.setattr(tool, "run", lambda value: calls.append(value) or "sent")
    step = PlanStep(id="notify", action="use_tool", description="external", tool="notify", input="telegram:hello")

    allowed = _orch(tmp_path, step, [ConnectorSpec(name="telegram")]).run("notify", tools={"notify": tool})
    assert tool.connector_names("telegram:hello") == ("telegram",)
    assert allowed.success is True
    assert calls == ["telegram:hello"]
