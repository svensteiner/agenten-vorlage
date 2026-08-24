"""RunBudget fail-closed metering."""

from decimal import Decimal
from pathlib import Path

import brain

from core.budget import RunBudget, evaluate_run_budget
from core.context import ProjectContext
from core.governance import GovernancePolicy
from core.orchestrator import AgentOrchestrator
from core.planner import Plan, PlanStep, Planner


def test_charge_and_check_under_cap():
    budget = RunBudget(max_usd=Decimal("1.00"), max_tokens=1000)
    budget.charge(tokens=10, usd="0.25")
    assert budget.spent_usd == Decimal("0.25")
    assert budget.spent_tokens == 10
    assert budget.remaining()["usd"] == Decimal("0.75")
    assert budget.remaining()["tokens"] == 990
    assert budget.exceeded is False
    assert budget.deny_reason == ""
    assert budget.check().allowed is True


def test_charge_over_usd_cap_denied():
    budget = RunBudget(max_usd=Decimal("0.01"), max_tokens=None)
    budget.charge(usd="0.05")
    assert budget.exceeded is True
    assert "budget_exceeded" in budget.deny_reason
    assert "402" in budget.deny_reason


def test_none_cap_is_unlimited():
    budget = RunBudget(max_usd=None, max_tokens=None)
    budget.charge(tokens=10_000_000, usd="9999.99")
    assert budget.exceeded is False
    assert budget.remaining() == {"usd": None, "tokens": None}


def test_config_max_usd_overspent_denied():
    check = evaluate_run_budget(
        {"run_budget": {"max_usd": "0.01", "max_tokens": 1000}},
        spent_usd="0.05",
        spent_tokens=0,
    )
    assert check is not None
    assert check.allowed is False
    assert "budget_exceeded" in check.reason


def test_under_budget_allowed():
    check = evaluate_run_budget(
        {"run_budget": {"max_usd": "1.00", "max_tokens": 100}},
        spent_usd="0.05",
        spent_tokens=10,
    )
    assert check is not None
    assert check.allowed is True


def test_no_config_allowed():
    assert evaluate_run_budget({}, spent_usd="100", spent_tokens=1_000_000) is None
    assert evaluate_run_budget(None, spent_usd="100") is None


def test_governance_allow_consults_budget():
    ctx = ProjectContext(
        project_root=Path("."),
        config={"run_budget": {"max_usd": "0.01"}, "require_human_approval": False},
        manifest={"autonomy_level": "max"},
    )
    denied = GovernancePolicy().allow(
        "run",
        context=ctx,
        text="summarize",
        spent_usd="0.05",
    )
    assert denied.allowed is False
    assert "budget_exceeded" in denied.reason
    allowed = GovernancePolicy().allow(
        "run",
        context=ctx,
        text="summarize",
        spent_usd="0.005",
    )
    assert allowed.allowed is True


class _BudgetPlanner(Planner):
    def draft(self, task, context="", project=None, tools=None):
        return Plan(
            task=task,
            steps=[
                PlanStep(
                    id="expensive",
                    action="execute",
                    description="paid step",
                    tool="echo",
                    input="hello",
                    metadata={"usd": "0.05", "tokens": 1},
                )
            ],
            confidence=1.0,
        )


class _Echo:
    def __init__(self):
        self.calls = 0

    def safe_run(self, input_str: str = "") -> str:
        self.calls += 1
        return f"echo:{input_str}"


def test_orchestrator_denies_before_dispatch_when_over_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    (tmp_path / "state").mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "config.json").write_text(
        '{"run_budget": {"max_usd": "0.01", "max_tokens": 100}, "require_human_approval": false}',
        encoding="utf-8",
    )
    (tmp_path / "project" / "manifest.json").write_text(
        '{"autonomy_level": "max", "hard_block_on_high_risk": false}',
        encoding="utf-8",
    )
    echo = _Echo()
    orch = AgentOrchestrator(tmp_path, planner=_BudgetPlanner())
    result = orch.run("do work", tools={"echo": echo})
    assert result.success is False
    assert echo.calls == 0
    assert result.governance is not None
    assert result.governance.allowed is False
    assert "budget_exceeded" in (result.governance.reason or "")
    assert result.metadata.get("status") == "budget_exceeded"


def test_orchestrator_allows_under_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    monkeypatch.setattr(brain, "evaluate", lambda *a, **k: {})
    (tmp_path / "state").mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "config.json").write_text(
        '{"run_budget": {"max_usd": "1.00"}, "require_human_approval": false, "quality_threshold": 1}',
        encoding="utf-8",
    )
    (tmp_path / "project" / "manifest.json").write_text(
        '{"autonomy_level": "max", "hard_block_on_high_risk": false}',
        encoding="utf-8",
    )

    class CheapPlanner(Planner):
        def draft(self, task, context="", project=None, tools=None):
            return Plan(
                task=task,
                steps=[
                    PlanStep(
                        id="cheap",
                        action="execute",
                        description="cheap step with source evidence",
                        tool="echo",
                        input="ok",
                        metadata={"usd": "0.01", "tokens": 1},
                    )
                ],
                confidence=1.0,
            )

    echo = _Echo()
    orch = AgentOrchestrator(tmp_path, planner=CheapPlanner())
    result = orch.run("summarize notes with source evidence", tools={"echo": echo})
    assert echo.calls == 1
    assert result.governance is not None
    assert result.governance.allowed is True
