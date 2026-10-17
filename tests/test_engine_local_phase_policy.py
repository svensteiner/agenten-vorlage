"""Private phase execution requires explicit compatible host boundaries."""
import unittest

from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.routing import EscalatingBackend
from agentkit.write_policy import WritePolicy
from tests import test_phase_test_execution as fixtures
from unittest.mock import patch


class PrivateBackend:
    name = "codex"
    supports_write_policy = True
    supports_local_phase_tests = True


class EngineLocalPhasePolicyTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.LocalPhaseTestPolicyTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.workspace = fixture.workspace
        self.policy = fixture.load()
        self.writes = WritePolicy(self.policy.allowed_write_paths)

    def construct(self, backend=None, **kwargs):
        options = dict(write_policy=self.writes, local_phase_policy=self.policy)
        options.update(kwargs)
        with patch("agentkit.engine.Catalog") as catalog:
            catalog.return_value.config = {"limits": {}}
            return Engine(self.workspace, self.workspace, backend or PrivateBackend(), **options)

    def test_exact_private_policy_is_retained(self):
        engine = self.construct()
        self.assertIs(engine.local_phase_policy, self.policy)

    def test_incompatible_backend_is_rejected_before_any_dispatch(self):
        backend = PrivateBackend()
        backend.supports_local_phase_tests = False
        with self.assertRaises(ContractError):
            self.construct(backend)

    def test_exact_write_scope_and_autonomous_profile_are_required(self):
        for options in ({"write_policy": None}, {"write_policy": WritePolicy([])},
                        {"require_approvals": True}, {"local_phase_policy": object()}):
            with self.subTest(options=options), self.assertRaises(ContractError):
                self.construct(**options)

    def test_routing_requires_every_leg_to_support_private_phase_execution(self):
        first, recovery = PrivateBackend(), PrivateBackend()
        self.assertTrue(EscalatingBackend(first, recovery=recovery).supports_local_phase_tests)
        recovery.supports_local_phase_tests = False
        self.assertFalse(EscalatingBackend(first, recovery=recovery).supports_local_phase_tests)


if __name__ == "__main__":
    unittest.main()
