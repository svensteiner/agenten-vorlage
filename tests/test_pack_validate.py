"""Tests für core.packs — VALIDATE: the tighten-only invariant + §0 ledger.

The marquee acceptance test of the whole engineering track lives here:
``test_floor_loosening_bundle_fails_validate`` — ADR-0017's "structurally
rejected by the loader, not by review" proven in CI.
"""

from core.packs.bundle import make_bundle
from core.packs.ledger import ROUTE_HUMAN_ADR_GATE, ROUTE_STANDARD, check_ledger
from core.packs.loader import Loader
from core.packs.validators import ExtensionPoints, validate_bundle


class TestFloorLooseningIsRejected:
    def test_floor_loosening_bundle_fails_validate(self):
        # The defining test: a §3 delta that loosens the pii floor.
        bundle = make_bundle(matrix_deltas={"pii": "allow"})
        result = Loader().validate(bundle)
        assert not result.ok
        assert result.rejected_by == "§3 tighten-only validator"  # rejected by CODE

    def test_loosening_confidential_rejected(self):
        bundle = make_bundle(matrix_deltas={"confidential": "allow"})
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§3 tighten-only validator"

    def test_tightening_is_accepted(self):
        # public → deny is *more* restrictive: allowed.
        bundle = make_bundle(matrix_deltas={"public": "deny", "confidential": "deny"})
        assert validate_bundle(bundle).ok

    def test_equal_restrictiveness_is_accepted(self):
        bundle = make_bundle(matrix_deltas={"pii": "mask"})  # == baseline
        assert validate_bundle(bundle).ok

    def test_unknown_action_rejected(self):
        bundle = make_bundle(matrix_deltas={"pii": "sudo"})
        assert not validate_bundle(bundle).ok


class TestClosedGrammar:
    def test_label_outside_grammar_rejected(self):
        bundle = make_bundle(labels=("totally_new_dimension",))
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§2 closed-grammar validator"

    def test_label_within_prefix_accepted(self):
        bundle = make_bundle(labels=("pii_class:health", "restricted:privileged"))
        assert validate_bundle(bundle).ok


class TestAclFixtures:
    def test_over_grant_rejected(self):
        bundle = make_bundle(
            acl_fixtures=({"name": "leak", "expected": ["u1", "u2"], "authorized": ["u1"]},)
        )
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§1 conformance validator"

    def test_faithful_fixture_accepted(self):
        bundle = make_bundle(
            acl_fixtures=({"name": "ok", "expected": ["u1"], "authorized": ["u1", "u2"]},)
        )
        assert validate_bundle(bundle).ok


class TestEvalModelsAndAgentGraph:
    def test_unapproved_model_rejected(self):
        bundle = make_bundle(eval_models=("gpt-4o",))
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§5 approved-model validator"

    def test_unlisted_agent_target_rejected(self):
        bundle = make_bundle(agent_graph=("attacker",))
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§6 allowlist-subset validator"

    def test_allowlisted_agent_graph_accepted(self):
        bundle = make_bundle(agent_graph=("reader", "writer"))
        assert validate_bundle(bundle).ok


class TestComplianceRows:
    def test_remove_obligation_rejected(self):
        bundle = make_bundle(compliance_rows=({"name": "sox", "op": "remove"},))
        result = validate_bundle(bundle)
        assert not result.ok
        assert result.rejected_by == "§4 additive-compliance validator"

    def test_add_obligation_accepted(self):
        bundle = make_bundle(compliance_rows=({"name": "sox", "op": "add"},))
        assert validate_bundle(bundle).ok


class TestLedger:
    def test_additive_ledger_routes_standard(self):
        bundle = make_bundle(ledger="none, all additive")
        res = check_ledger(bundle)
        assert res.ok and res.route == ROUTE_STANDARD

    def test_horizontal_ledger_routes_to_human_gate(self):
        bundle = make_bundle(ledger="adds a new principal category")
        res = check_ledger(bundle)
        assert not res.ok
        assert res.route == ROUTE_HUMAN_ADR_GATE

    def test_loader_routes_horizontal_pack_out(self):
        bundle = make_bundle(ledger="raises the floor")
        result = Loader().load(bundle)
        assert not result.ok
        assert result.route == ROUTE_HUMAN_ADR_GATE


class TestCustomExtensionPoints:
    def test_tenant_can_pin_stricter_baseline(self):
        strict = ExtensionPoints(baseline_matrix={"internal": "mask"})
        bundle = make_bundle(matrix_deltas={"internal": "allow"})  # loosens the stricter floor
        assert not validate_bundle(bundle, strict).ok
