"""Governance policy — deterministic gates (pure logic, no model).

Complements test_governance_order.py (which focuses on the hard-block-before-
autonomy ordering) by covering the approval gate, leaf-write enforcement,
connector declaration, and the audit history.
"""

from pathlib import Path

from core.context import ConnectorSpec, ProjectContext
from core.governance import GovernancePolicy
from core.subagents import SubagentSpec


def _ctx(*, manifest=None, config=None, connectors=None) -> ProjectContext:
    return ProjectContext(
        project_root=Path("."),
        manifest=manifest or {},
        config=config or {},
        connectors=connectors or [],
    )


# ── The approval gate (gate ENABLED, i.e. not full-autonomy) ────────────────

def test_high_risk_blocked_when_approval_enabled():
    ctx = _ctx(config={"require_human_approval": True})
    decision = GovernancePolicy().allow("do it", risk="high", context=ctx, text="benign action")
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert "high-risk" in decision.reason


def test_approval_term_from_manifest_blocks():
    ctx = _ctx(
        manifest={"approval_required_for": ["overwrite"], "hard_block_on_high_risk": False},
        config={"require_human_approval": True},
    )
    decision = GovernancePolicy().allow("please replace the file", context=ctx, text="replace it")
    assert decision.allowed is False
    assert "overwrite" in decision.metadata["matched_terms"]


def test_approval_terms_from_config_string_are_parsed():
    ctx = _ctx(
        manifest={"hard_block_on_high_risk": False},
        config={"require_human_approval": True, "human_approval_required": "custom_term"},
    )
    decision = GovernancePolicy().allow("run custom_term now", context=ctx, text="custom_term")
    assert decision.allowed is False
    assert "custom_term" in decision.metadata["matched_terms"]


def test_ordinary_action_allowed_when_gate_enabled():
    ctx = _ctx(config={"require_human_approval": True})
    decision = GovernancePolicy().allow("summarize the notes", context=ctx, text="summarize")
    assert decision.allowed is True


def test_default_context_requires_approval_for_high_risk_actions():
    decision = GovernancePolicy().allow("send a notification", risk="high", context=_ctx())
    assert decision.allowed is False
    assert decision.requires_approval is True


# ── Full-autonomy mode: ordinary actions pass, still flagged in metadata ────

def test_default_external_communication_category_blocks_notify_tool():
    ctx = _ctx(manifest={"approval_required_for": ["external communication"]})
    decision = GovernancePolicy().allow("send update", context=ctx, tool="notify")
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_default_write_category_blocks_file_write_action():
    ctx = _ctx(manifest={"approval_required_for": ["write"]})
    decision = GovernancePolicy().allow("write the report", context=ctx, tool="file")
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_autonomy_flags_but_allows_ordinary_risky_wording():
    ctx = _ctx(manifest={"autonomy_level": "max"})
    decision = GovernancePolicy().allow("send a notify", risk="high", context=ctx, tool="notify")
    assert decision.allowed is True
    assert decision.metadata["gate"] == "disabled"
    assert decision.metadata["flagged"] is True


# ── Leaf-write enforcement ──────────────────────────────────────────────────

def test_allow_write_orchestrator_without_subagent():
    decision = GovernancePolicy().allow_write(None, context=_ctx())
    assert decision.allowed is True


def test_allow_write_declared_leaf_writer():
    spec = SubagentSpec(name="reporter", can_write=True)
    decision = GovernancePolicy().allow_write(spec, context=_ctx())
    assert decision.allowed is True
    assert "leaf writer" in decision.reason


def test_allow_write_non_leaf_reader_is_blocked():
    spec = SubagentSpec(name="researcher", can_write=False)
    decision = GovernancePolicy().allow_write(spec, context=_ctx(), is_leaf=False)
    assert decision.allowed is False
    assert decision.metadata["pattern"] == "leaf-write"


def test_allow_write_non_writer_but_leaf_is_allowed():
    spec = SubagentSpec(name="researcher", can_write=False)
    decision = GovernancePolicy().allow_write(spec, context=_ctx(), is_leaf=True)
    assert decision.allowed is True


def test_allow_write_disabled_in_manifest():
    ctx = _ctx(manifest={"tool_permissions": {"write_restricted_to_leaf": False}})
    spec = SubagentSpec(name="researcher", can_write=False)
    decision = GovernancePolicy().allow_write(spec, context=ctx)
    assert decision.allowed is True


# ── Connector declaration gate ──────────────────────────────────────────────

def test_allow_connector_without_context_denies():
    decision = GovernancePolicy().allow_connector("slack", context=None)
    assert decision.allowed is False


def test_allow_connector_declared_is_allowed():
    ctx = _ctx(connectors=[ConnectorSpec(name="slack")])
    decision = GovernancePolicy().allow_connector("slack", context=ctx)
    assert decision.allowed is True


def test_allow_connector_undeclared_is_blocked():
    ctx = _ctx(connectors=[ConnectorSpec(name="slack")])
    decision = GovernancePolicy().allow_connector("telegram", context=ctx)
    assert decision.allowed is False
    assert "slack" in decision.metadata["declared"]


def test_allow_connector_none_declared_is_blocked():
    decision = GovernancePolicy().allow_connector("anything", context=_ctx())
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.metadata["declared"] == []


# ── Audit history ───────────────────────────────────────────────────────────

def test_record_and_history_are_append_only_copies():
    policy = GovernancePolicy()
    policy.record("notify", "ok", details="sent")
    policy.record("delete", "blocked")
    history = policy.history()
    assert [h["action"] for h in history] == ["notify", "delete"]
    # history() returns a copy — mutating it must not affect internal state.
    history.clear()
    assert len(policy.history()) == 2
