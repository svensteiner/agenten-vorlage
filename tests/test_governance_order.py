"""Tests für die Governance-Reihenfolge (WP-A5, ADR-0006): Hard-Block vor Autonomie-Shortcut.

The destructive/irreversible hard-block class is unconditional — it is evaluated
*before* the ``autonomy_level: max`` shortcut, and rests on a deterministic
keyword policy, never on an LLM-produced ``requires_human`` flag.
"""

from core.context import ProjectContext
from core.governance import GovernancePolicy


def _ctx(tmp_path, manifest):
    return ProjectContext(project_root=tmp_path, manifest=manifest, config={})


MAX_AUTONOMY = {"autonomy_level": "max"}


class TestHardBlockUnconditional:
    def test_destructive_action_blocked_even_under_max_autonomy(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, MAX_AUTONOMY)
        decision = gov.allow("delete all records", risk="high", context=ctx, text="delete all records")
        assert decision.allowed is False
        assert decision.metadata["gate"] == "hard_block"

    def test_payment_action_blocked_under_max_autonomy(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, MAX_AUTONOMY)
        decision = gov.allow("issue payment", risk="low", context=ctx, text="wire transfer to vendor")
        # Note: risk was "low" — the hard block does not trust the risk flag,
        # it re-derives from the deterministic destructive vocabulary.
        assert decision.allowed is False

    def test_production_deploy_blocked(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, MAX_AUTONOMY)
        decision = gov.allow("deploy production", risk="high", context=ctx, text="deploy production now")
        assert decision.allowed is False


class TestOrdinaryActionsStillAutonomous:
    def test_benign_action_allowed_under_max_autonomy(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, MAX_AUTONOMY)
        decision = gov.allow("read the report", risk="low", context=ctx, text="read report.csv")
        assert decision.allowed is True
        assert decision.metadata["gate"] == "disabled"

    def test_high_risk_but_non_destructive_flagged_not_blocked(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, MAX_AUTONOMY)
        decision = gov.allow("summarize sensitive data", risk="high", context=ctx, text="summarize")
        # High risk without a destructive keyword is flagged for audit, not blocked,
        # under max autonomy (only the hard-block class is unconditional).
        assert decision.allowed is True
        assert decision.metadata["flagged"] is True


class TestHardBlockOptOut:
    def test_explicit_opt_out_allows_destructive_under_max(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, {"autonomy_level": "max", "hard_block_on_high_risk": False})
        decision = gov.allow("delete records", risk="high", context=ctx, text="delete records")
        # Opt-out is an explicit, auditable manifest decision.
        assert decision.allowed is True


class TestGatedModeUnchanged:
    def test_gated_mode_blocks_high_risk(self, tmp_path):
        gov = GovernancePolicy()
        ctx = _ctx(tmp_path, {"autonomy_level": "gated"})
        decision = gov.allow("do risky thing", risk="high", context=ctx, text="risky")
        assert decision.allowed is False
