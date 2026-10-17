from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agentkit.contracts import ContractError
from agentkit.phase_test_execution import (
    LocalPhaseTestPolicy,
    authorize_phase,
    verify_phase_freshness,
)


class LocalPhaseTestPolicyTests(unittest.TestCase):
    def test_allowed_production_write_requires_baseline_hash(self):
        self.data["snapshot_paths"].append("agentkit/unpinned.py")
        self.data["allowed_write_paths"].append("agentkit/unpinned.py")
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.host = self.root / "host-policy"
        self.host.mkdir()
        self.source = self.workspace / "agentkit" / "worker.py"
        self.source.parent.mkdir()
        self.source.write_text("def work(): return 1\n", encoding="utf-8")
        self.test = self.workspace / "tests" / "test_worker.py"
        self.test.parent.mkdir()
        self.test.write_text("def test_new_behavior(): assert True\n", encoding="utf-8")
        self.manifest_path = self.host / "phase-policy.json"
        self.data = self.manifest()
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return {
            "version": 1,
            "image_ref": "registry.example/agentkit@sha256:" + "a" * 64,
            "image_id": "sha256:" + "a" * 64,
            "dependency_lock_sha256": "b" * 64,
            "host_runner_sha256": "c" * 64,
            "production_files": [{
                "path": "agentkit/worker.py",
                "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            }],
            "snapshot_paths": ["agentkit/worker.py", "tests/test_worker.py"],
            "allowed_write_paths": ["agentkit/worker.py", "tests/test_worker.py"],
            "phases": {
                "red": {
                    "nodeids": ["tests/test_worker.py::test_new_behavior"],
                    "expected_failure_nodeids": ["tests/test_worker.py::test_new_behavior"],
                },
                "targeted": {
                    "nodeids": ["tests/test_worker.py::test_new_behavior"],
                },
                "full": {
                    "test_files": ["tests/test_worker.py"],
                },
            },
            "full_test_roots": ["tests"],
            "full_minimum_test_count": 1,
            "limits": {
                "timeout_seconds": 720,
                "memory_bytes": 2 * 1024**3,
                "memory_swap_bytes": 2 * 1024**3,
                "nano_cpus": 2_000_000_000,
                "pids": 256,
                "output_bytes": 2_000_000,
                "nofile": 256,
                "tmpfs_bytes": 256 * 1024**2,
                "max_file_bytes": 2 * 1024**2,
                "max_snapshot_bytes": 512 * 1024**2,
            },
        }

    def write_manifest(self):
        self.manifest_path.write_text(
            json.dumps(self.data, ensure_ascii=False), encoding="utf-8"
        )

    def load(self):
        return LocalPhaseTestPolicy.from_file(self.manifest_path, self.workspace)

    def test_targeted_selection_preserves_long_source_parameter_nodeid(self):
        nodeid = "tests/test_worker.py::test_full_source[" + "x" * 8192 + "]"
        self.data["phases"]["targeted"]["nodeids"] = [nodeid]
        self.write_manifest()
        try:
            policy = self.load()
        except ContractError as exc:
            self.fail(f"A full-source parametrized nodeid must remain selectable: {exc}")
        self.assertEqual((nodeid,), authorize_phase(policy, "targeted").nodeids)

    def test_targeted_nodeid_still_has_a_finite_character_limit(self):
        nodeid = "tests/test_worker.py::test_full_source[" + "x" * 16384 + "]"
        self.data["phases"]["targeted"]["nodeids"] = [nodeid]
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()

    def test_phase_selection_is_fixed_to_operator_nodeids_and_limits(self):
        policy = self.load()
        plan = authorize_phase(policy, "red")
        self.assertEqual("red", plan.phase)
        self.assertEqual(("tests/test_worker.py::test_new_behavior",), plan.nodeids)
        self.assertEqual(plan.nodeids, plan.expected_failure_nodeids)
        self.assertEqual((), plan.test_files)
        self.assertEqual(policy.sha256, plan.policy_sha256)
        self.assertEqual(720, policy.limits["timeout_seconds"])
        self.assertEqual(2 * 1024**3, policy.limits["memory_bytes"])
        self.assertEqual(256, policy.limits["pids"])
        with self.assertRaises(ContractError):
            authorize_phase(policy, "tests/test_worker.py::test_new_behavior")
        with self.assertRaises(ContractError):
            authorize_phase(policy, "full", nodeids=["tests/test_other.py::test_escape"])

    def test_red_freshness_pins_production_but_allows_mutable_regression_test(self):
        policy = self.load()
        self.test.write_text("def test_new_behavior(): assert False\n", encoding="utf-8")
        verified = verify_phase_freshness(policy, self.workspace, "red")
        self.assertEqual(policy.snapshot_paths, tuple(verified["snapshot_paths"]))
        self.assertEqual(policy.production_hashes[0][1], verified["production_hashes"]["agentkit/worker.py"])
        self.assertEqual(policy.production_hashes[0][1], verified["input_hashes"]["agentkit/worker.py"])
        self.assertRegex(verified["snapshot_sha256"], r"^[0-9a-f]{64}$")
        self.source.write_text("def work(): return 2\n", encoding="utf-8")
        with self.assertRaises(ContractError):
            verify_phase_freshness(policy, self.workspace, "red")

    def test_changed_production_is_allowed_after_red_for_targeted_and_full(self):
        policy = self.load()
        self.source.write_text("def work(): return 2\n", encoding="utf-8")
        verify_phase_freshness(policy, self.workspace, "targeted")
        full_plan = authorize_phase(policy, "full")
        self.assertEqual(("tests/test_worker.py",), full_plan.test_files)
        self.assertEqual(1, full_plan.minimum_test_count)
        verify_phase_freshness(policy, self.workspace, "full")

    def test_write_paths_are_exact_and_immutable(self):
        policy = self.load()
        self.assertTrue(policy.authorize_write("tests/test_worker.py"))
        for path in ("tests/../secret.py", "tests/new.py", ".runs/state.json", "tests\\test_worker.py"):
            with self.subTest(path=path), self.assertRaises(ContractError):
                policy.authorize_write(path)
        with self.assertRaises((AttributeError, TypeError)):
            policy.allowed_write_paths += ("secret.py",)

    def test_manifest_is_bound_and_canonical(self):
        first = self.load()
        self.data["snapshot_paths"] = list(reversed(self.data["snapshot_paths"]))
        self.data["allowed_write_paths"] = list(reversed(self.data["allowed_write_paths"]))
        self.write_manifest()
        second = self.load()
        self.assertEqual(first.sha256, second.sha256)
        self.data["host_runner_sha256"] = "d" * 64
        self.write_manifest()
        self.assertNotEqual(first.sha256, self.load().sha256)

    def test_duplicate_keys_and_manifest_inside_workspace_are_rejected(self):
        self.manifest_path.write_text('{"version":1,"version":1}', encoding="utf-8")
        with self.assertRaises(ContractError):
            self.load()
        inside = self.workspace / "policy.json"
        inside.write_text(json.dumps(self.manifest()), encoding="utf-8")
        with self.assertRaises(ContractError):
            LocalPhaseTestPolicy.from_file(inside, self.workspace)

    def test_rejects_invalid_phase_map_and_missing_red_assertion(self):
        self.data["phases"]["red"]["expected_failure_nodeids"] = []
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()
        self.data = self.manifest()
        self.data["phases"]["unknown"] = {"nodeids": ["tests/test_worker.py::test_new_behavior"]}
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()

    def test_rejects_unsafe_paths_duplicate_aliases_and_noncanonical_nodeids(self):
        invalid_values = [
            ("snapshot_paths", ["tests/../escape.py"]),
            ("snapshot_paths", ["tests/test_worker.py", "tests/TEST_WORKER.py"]),
            ("allowed_write_paths", ["tests/test_worker.py", "tests/TEST_WORKER.py"]),
        ]
        for key, value in invalid_values:
            with self.subTest(key=key, value=value):
                self.data = self.manifest()
                self.data[key] = value
                self.write_manifest()
                with self.assertRaises(ContractError):
                    self.load()
        self.data = self.manifest()
        self.data["phases"]["targeted"]["nodeids"] = ["--collect-only"]
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()

    def test_rejects_limits_above_hard_bounds_and_boolean_numbers(self):
        for field, value in (("timeout_seconds", 721), ("memory_bytes", 2 * 1024**3 + 1),
                             ("pids", 257), ("output_bytes", 2_000_001), ("pids", True)):
            with self.subTest(field=field, value=value):
                self.data = self.manifest()
                self.data["limits"][field] = value
                self.write_manifest()
                with self.assertRaises(ContractError):
                    self.load()

    def test_full_phase_requires_meaningful_minimum_count(self):
        self.data["full_minimum_test_count"] = 0
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()

    def test_full_scope_must_inventory_all_test_files_under_roots(self):
        self.data["phases"]["full"]["test_files"] = []
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()
        self.data = self.manifest()
        self.write_manifest()
        policy = self.load()
        extra = self.workspace / "tests" / "test_unlisted.py"
        extra.write_text("def test_unlisted(): assert True\n", encoding="utf-8")
        with self.assertRaises(ContractError):
            verify_phase_freshness(policy, self.workspace, "full")

    def test_full_test_roots_reject_case_insensitive_nested_aliases(self):
        nested = self.workspace / "tests" / "unit" / "sub" / "test_nested.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("def test_nested(): assert True\n", encoding="utf-8")
        self.data["snapshot_paths"].append("tests/unit/sub/test_nested.py")
        self.data["allowed_write_paths"].append("tests/unit/sub/test_nested.py")
        self.data["phases"]["full"]["test_files"] = [
            "tests/unit/sub/test_nested.py"
        ]
        self.data["full_test_roots"] = ["tests/Unit", "tests/unit/sub"]
        self.write_manifest()

        with self.assertRaises(ContractError):
            self.load()

    def test_manifest_policy_and_workspace_are_bound(self):
        with self.assertRaises(ContractError):
            LocalPhaseTestPolicy()
        other_workspace = self.root / "other-workspace"
        other_workspace.mkdir()
        with self.assertRaises(ContractError):
            verify_phase_freshness(self.load(), other_workspace, "targeted")

    def test_snapshot_symlink_is_rejected_when_host_verifies_freshness(self):
        link = self.workspace / "tests" / "test_link.py"
        try:
            link.symlink_to(self.source)
        except OSError as exc:
            self.skipTest(f"file symlink unavailable: {exc}")
        self.data["snapshot_paths"] = ["agentkit/worker.py", "tests/test_link.py"]
        self.data["allowed_write_paths"] = ["agentkit/worker.py", "tests/test_link.py"]
        self.data["phases"] = {
            "red": {"nodeids": ["tests/test_link.py::test_new_behavior"],
                    "expected_failure_nodeids": ["tests/test_link.py::test_new_behavior"]},
            "targeted": {"nodeids": ["tests/test_link.py::test_new_behavior"]},
            "full": {"test_files": ["tests/test_link.py"]},
        }
        self.write_manifest()
        with self.assertRaises(ContractError):
            verify_phase_freshness(self.load(), self.workspace, "targeted")

    def test_snapshot_file_and_aggregate_sizes_obey_policy(self):
        self.data["limits"]["max_snapshot_bytes"] = 1
        self.data["limits"]["max_file_bytes"] = 1
        self.write_manifest()
        with self.assertRaises(ContractError):
            verify_phase_freshness(self.load(), self.workspace, "full")
        self.data["limits"]["max_snapshot_bytes"] = 1
        self.data["limits"]["max_file_bytes"] = 2
        self.write_manifest()
        with self.assertRaises(ContractError):
            self.load()


if __name__ == "__main__":
    unittest.main()
