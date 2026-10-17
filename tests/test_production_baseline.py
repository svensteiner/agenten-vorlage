from __future__ import annotations

import unittest

from agentkit.contracts import ContractError
from agentkit.production_baseline import (
    capture_production_baseline,
    load_production_baseline,
    validate_run_cache_parent,
)
from tests.test_phase_test_execution import LocalPhaseTestPolicyTests


class ProductionBaselineTests(unittest.TestCase):
    def setUp(self):
        fixture = LocalPhaseTestPolicyTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.fixture = fixture
        self.policy = fixture.load()
        self.run_id = "1" * 32
        self.agent_root = fixture.root / "agent"
        self.agent_root.mkdir()
        self.run_dir = self.agent_root / ".runs" / self.run_id
        self.run_dir.mkdir(parents=True)

    def test_cache_restores_original_bytes_after_workspace_changes(self):
        original = self.fixture.source.read_bytes()
        captured, cache_hash = capture_production_baseline(
            self.policy, self.fixture.workspace, self.run_id, self.run_dir
        )
        self.fixture.source.write_bytes(b"changed after the run began")

        loaded = load_production_baseline(
            self.policy, self.fixture.workspace, self.run_id, self.run_dir, cache_hash
        )

        self.assertEqual({"agentkit/worker.py": original}, captured)
        self.assertEqual(captured, loaded)
        self.assertNotEqual(original, self.fixture.source.read_bytes())
        self.assertFalse((self.run_dir / "private-production-baseline").is_relative_to(
            self.fixture.workspace
        ))

    def test_missing_or_modified_cache_fails_closed_without_recapture(self):
        _, cache_hash = capture_production_baseline(
            self.policy, self.fixture.workspace, self.run_id, self.run_dir
        )
        self.fixture.source.write_bytes(b"modified workspace cannot become baseline")
        blob = next((self.run_dir / "private-production-baseline").glob("*.blob"))
        blob.write_bytes(b"tampered cache content")

        with self.assertRaises(ContractError):
            load_production_baseline(
                self.policy, self.fixture.workspace, self.run_id, self.run_dir, cache_hash
            )

        blob.unlink()
        with self.assertRaises(ContractError):
            load_production_baseline(
                self.policy, self.fixture.workspace, self.run_id, self.run_dir, cache_hash
            )

    def test_cache_rejects_wrong_run_or_policy_identity(self):
        _, cache_hash = capture_production_baseline(
            self.policy, self.fixture.workspace, self.run_id, self.run_dir
        )
        with self.assertRaises(ContractError):
            load_production_baseline(
                self.policy, self.fixture.workspace, "2" * 32, self.run_dir, cache_hash
            )

    def test_cache_path_inside_mutable_workspace_is_rejected(self):
        workspace_run = self.fixture.workspace / "run-cache"
        workspace_run.mkdir()
        with self.assertRaises(ContractError):
            capture_production_baseline(
                self.policy, self.fixture.workspace, self.run_id, workspace_run
            )

    def test_lexical_reparse_run_path_is_rejected_before_resolution(self):
        link = self.agent_root / ".runs-link"
        actual = self.agent_root / ".runs"
        try:
            link.symlink_to(actual, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Directory symlink creation is unavailable: {exc}")

        with self.assertRaises(ContractError):
            validate_run_cache_parent(link / self.run_id, self.agent_root)


if __name__ == "__main__":
    unittest.main()
