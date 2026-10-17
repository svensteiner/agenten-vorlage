"""The host, rather than worker reports, owns phase ordering and freshness."""
import hashlib
import json
import unittest
from unittest.mock import patch

from agentkit.contracts import ContractError
from agentkit.phase_test_execution import verify_phase_freshness
from agentkit.phase_test_runtime import LocalPhaseProposalRejected, LocalPhaseRuntime
from tests import test_phase_test_execution as fixtures


class LocalPhaseRuntimeTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.LocalPhaseTestPolicyTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.fixture, self.policy = fixture, fixture.load()
        self.state = LocalPhaseRuntime.initial_state(self.policy)
        self.checkpoints = []
        self.runtime = LocalPhaseRuntime(self.policy, fixture.workspace, "a" * 32, self.state,
                                        lambda: self.checkpoints.append(json.loads(json.dumps(self.state))))

    def receipt(self, policy, workspace, phase, **kwargs):
        self.assertIsNotNone(self.checkpoints[-1]["in_flight"], "reserve before dispatch")
        current = verify_phase_freshness(policy, workspace, phase)
        def digest(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                             separators=(",", ":")).encode()).hexdigest()
        value = {"schema": "agentkit/local-phase-receipt-v1", "status": "passed", "run_id": "a" * 32,
                 "outcome_source": "pytest_child_report",
                 "phase": phase, "reason": "expected_red_reproduced" if phase == "red" else "ok",
                 "exit_code": 1 if phase == "red" else 0, "policy_sha256": policy.sha256,
                 "host_runner_sha256": policy.host_runner_sha256, "image_ref": policy.image_ref,
                 "image_id": policy.image_id, "dependency_lock_sha256": policy.dependency_lock_sha256,
                 "snapshot_sha256": current["snapshot_sha256"], "input_hashes": current["input_hashes"],
                 "workspace_post_snapshot_sha256": current["snapshot_sha256"],
                 "collection": {"nodeids_sha256": digest(["tests/test_worker.py::test_new_behavior"]), "count": 1,
                                "files_sha256": digest(["tests/test_worker.py"]), "files_count": 1},
                 "outcomes": {"tests/test_worker.py::test_new_behavior": {
                     "outcome": "failed" if phase == "red" else "passed",
                     "exception_type": "AssertionError" if phase == "red" else None,
                     "when": "call"}},
                 "scratch_post_hashes": current["input_hashes"], "cleanup_confirmed": True,
                 "duration_seconds": 1, "output": ""}
        value["receipt_sha256"] = hashlib.sha256(json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        return value

    def test_targeted_and_production_writes_require_red(self):
        with patch("agentkit.phase_test_runtime.run_phase") as runner:
            checkpoints_before = len(self.checkpoints)
            with self.assertRaises(ContractError) as targeted_denial:
                self.runtime.execute("targeted", 10)
            self.assertEqual(
                "LocalPhaseProposalRejected", type(targeted_denial.exception).__name__
            )
            self.assertEqual(checkpoints_before, len(self.checkpoints))
            self.assertIsNone(self.state["in_flight"])
            with self.assertRaises(ContractError) as write_denial:
                self.runtime.authorize_mutation("edit_file", {"path": "agentkit/worker.py"})
            self.assertEqual(
                "LocalPhaseProposalRejected", type(write_denial.exception).__name__
            )
            runner.assert_not_called()
        self.runtime.authorize_mutation("write_file", {"path": "tests/test_worker.py"})

    def test_full_requires_targeted_and_completion_requires_current_snapshot(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt):
            self.runtime.execute("red", 10)
            self.runtime.authorize_mutation("edit_file", {"path": "agentkit/worker.py"})
            self.fixture.source.write_text("changed production", encoding="utf-8")
            with self.assertRaises(ContractError) as denied:
                self.runtime.execute("full", 10)
            self.assertEqual(
                "LocalPhaseProposalRejected", type(denied.exception).__name__
            )
            self.runtime.execute("targeted", 10)
            self.runtime.execute("full", 10)
            self.runtime.require_completion()
            self.fixture.source.write_text("later modification", encoding="utf-8")
            with self.assertRaises(ContractError):
                self.runtime.require_completion()

    def test_modified_regression_test_invalidates_red(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt):
            self.runtime.execute("red", 10)
        (self.fixture.workspace / "tests/test_worker.py").write_text("changed test", encoding="utf-8")
        with self.assertRaises(ContractError) as denied:
            self.runtime.execute("targeted", 10)
        self.assertEqual(
            "LocalPhaseProposalRejected", type(denied.exception).__name__
        )

    def test_stale_red_allows_path_only_baseline_restore_but_blocks_unresolved_runs(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt):
            self.runtime.execute("red", 10)
        (self.fixture.workspace / "tests/test_worker.py").write_text(
            "def test_worker(): assert False\n", encoding="utf-8"
        )
        self.fixture.source.write_bytes(b"def work(): return 3\n")
        baseline_hash = dict(self.policy.production_hashes)["agentkit/worker.py"]
        with self.assertRaises(LocalPhaseProposalRejected):
            self.runtime.authorize_mutation(
                "write_file", {"path": "agentkit/worker.py"}, "0" * 64
            )

        self.runtime.authorize_mutation(
            "restore_production_baseline", {"path": "agentkit/worker.py"}, baseline_hash
        )
        with self.assertRaises(LocalPhaseProposalRejected):
            self.runtime.authorize_mutation(
                "restore_production_baseline", {"path": "tests/test_worker.py"}, baseline_hash
            )

        self.state["in_flight"] = {"phase": "targeted", "snapshot_sha256": "a" * 64}
        with self.assertRaises(ContractError):
            self.runtime.authorize_mutation(
                "restore_production_baseline", {"path": "agentkit/worker.py"}, baseline_hash
            )
        self.state["in_flight"] = None
        self.state["attempts"].append({"status": "unknown"})
        with self.assertRaises(ContractError):
            self.runtime.authorize_mutation(
                "restore_production_baseline", {"path": "agentkit/worker.py"}, baseline_hash
            )

    def test_modified_conftest_invalidates_red(self):
        helper = self.fixture.workspace / "tests/conftest.py"
        helper.write_text("# initial fixtures\n", encoding="utf-8")
        self.fixture.data["snapshot_paths"].append("tests/conftest.py")
        self.fixture.write_manifest()
        self.policy = self.fixture.load()
        self.state = LocalPhaseRuntime.initial_state(self.policy)
        self.runtime = LocalPhaseRuntime(self.policy, self.fixture.workspace, "a" * 32, self.state,
                                        lambda: self.checkpoints.append(json.loads(json.dumps(self.state))))
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt):
            self.runtime.execute("red", 10)
        helper.write_text("# changed fixtures\n", encoding="utf-8")
        with self.assertRaises(ContractError):
            self.runtime.execute("targeted", 10)

    def test_exception_keeps_durable_reservation_and_resume_cannot_replay(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                self.runtime.execute("red", 10)
        self.assertIsNotNone(self.state["in_flight"])
        with self.assertRaises(ContractError):
            LocalPhaseRuntime(self.policy, self.fixture.workspace, "a" * 32, self.state, lambda: None)

    def test_typed_phase_callback_error_after_reservation_is_blocking(self):
        with patch(
            "agentkit.phase_test_runtime.run_phase",
            side_effect=LocalPhaseProposalRejected("late denial"),
        ):
            with self.assertRaisesRegex(ContractError, "after reservation"):
                self.runtime.execute("red", 10)
        self.assertIsNotNone(self.state["in_flight"])
        self.assertEqual(1, len(self.checkpoints))
        with self.assertRaises(ContractError):
            LocalPhaseRuntime(
                self.policy, self.fixture.workspace, "a" * 32, self.state,
                lambda: None,
            )

    def test_completion_without_any_test_is_rejected(self):
        with self.assertRaises(ContractError):
            self.runtime.require_completion()

    def test_known_duplicate_is_rejected_before_new_reservation(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt) as runner:
            self.runtime.execute("red", 10)
            before = len(self.checkpoints)
            with self.assertRaises(ContractError) as denied:
                self.runtime.execute("red", 10)
            self.assertEqual(
                "LocalPhaseProposalRejected", type(denied.exception).__name__
            )
            self.assertEqual(1, runner.call_count)
        self.assertIsNone(self.state["in_flight"])
        self.assertEqual(before, len(self.checkpoints))

    def test_results_directory_does_not_duplicate_run_identifier_in_windows_paths(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt) as runner:
            self.runtime.execute("red", 10)
        self.assertEqual(self.policy.source_path.parent / "phase-results",
                         runner.call_args.kwargs["results_dir"])

    def test_resume_rejects_reordered_individually_valid_receipts(self):
        with patch("agentkit.phase_test_runtime.run_phase", side_effect=self.receipt):
            for phase in ("red", "targeted", "full"):
                self.runtime.execute(phase, 10)
        red, targeted, full = self.state["attempts"]
        for invalid_order in ([targeted, red, full], [red, full, targeted]):
            self.state["attempts"] = invalid_order
            with self.subTest(order=[r["phase"] for r in invalid_order]), self.assertRaises(ContractError):
                LocalPhaseRuntime(self.policy, self.fixture.workspace, "a" * 32, self.state, lambda: None)


if __name__ == "__main__":
    unittest.main()
