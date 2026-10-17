from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.backends import CodexBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.phase_test_execution import LocalPhaseTestPolicy, authorize_phase, verify_phase_freshness
from agentkit.scaffold import create
from agentkit.write_policy import WritePolicy


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EngineCodexLocalPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agent", "developer", "phase-test", "Example")
        self.workspace = self.agent / "workspace"
        self.source = self.workspace / "agentkit" / "worker.py"
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_text("def work(): return 1\n", encoding="utf-8")
        tests = self.workspace / "tests"
        tests.mkdir(exist_ok=True)
        self.test_file = tests / "test_worker.py"
        self.test_file.write_text("def test_worker(): assert True\n", encoding="utf-8")
        manifest = {
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
                    "nodeids": ["tests/test_worker.py::test_worker"],
                    "expected_failure_nodeids": ["tests/test_worker.py::test_worker"],
                },
                "targeted": {"nodeids": ["tests/test_worker.py::test_worker"]},
                "full": {"test_files": ["tests/test_worker.py"]},
            },
            "full_test_roots": ["tests"],
            "full_minimum_test_count": 1,
            "limits": {
                "timeout_seconds": 720, "memory_bytes": 2 * 1024**3,
                "memory_swap_bytes": 2 * 1024**3, "nano_cpus": 2_000_000_000,
                "pids": 256, "output_bytes": 2_000_000, "nofile": 1024,
                "tmpfs_bytes": 256 * 1024**2, "max_file_bytes": 8 * 1024**2,
                "max_snapshot_bytes": 512 * 1024**2,
            },
        }
        self.policy_path = self.root / "local-phase-policy.json"
        self.policy_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.phase_policy = LocalPhaseTestPolicy.from_file(self.policy_path, self.workspace)
        self.write_policy = WritePolicy(["agentkit/worker.py", "tests/test_worker.py"])

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def decision(action="delegate", role="developer"):
        return {
            "action": action, "role": role, "skills": [],
            "task": "Verify the bounded local phase workflow.",
            "reason": "The phase receipt must be current.",
        }

    @staticmethod
    def report():
        return {
            "status": "success", "summary": "The assigned work is complete.",
            "artifacts": [], "evidence": ["Completed the requested checks."],
            "next_actions": [],
        }

    @staticmethod
    def _step_arguments(*, path="", content="", phase=None):
        return {
            "path": path, "content": content, "old_text": "", "new_text": "",
            "start_line": None, "max_lines": None, "phase": phase,
        }

    @staticmethod
    def codex_backend_fixture():
        with patch("agentkit.backends.codex_command", return_value=["codex-fixture"]) as command, \
                patch("agentkit.backends._windows_sandbox_selection", return_value="unelevated") as sandbox:
            backend = CodexBackend()
        command.assert_called_once_with()
        sandbox.assert_called_once_with()
        return backend

    def proposal(self, tool, *, path="", content="", phase=None):
        return {
            "kind": "proposal", "tool": tool,
            "arguments": self._step_arguments(path=path, content=content, phase=phase),
            "rationale": "Use the host-authorized action.",
            "report": {
                "status": "blocked", "summary": "Action requested.",
                "artifacts": [], "evidence": [], "next_actions": [],
            },
        }

    def final_action(self):
        return {
            "kind": "final", "tool": "none",
            "arguments": self._step_arguments(),
            "rationale": "The assigned phase sequence is complete.",
            "report": self.report(),
        }

    def phase_receipt(self, phase, run_id):
        freshness = verify_phase_freshness(self.phase_policy, self.workspace, phase)
        plan = authorize_phase(self.phase_policy, phase)
        nodeids = list(plan.nodeids or ("tests/test_worker.py::test_worker",))
        files = sorted({node.split("::", 1)[0] for node in nodeids})
        if phase == "red":
            reason, exit_code = "expected_red_reproduced", 1
            outcome = {"outcome": "failed", "exception_type": "AssertionError", "when": "call"}
        else:
            reason, exit_code = "ok", 0
            outcome = {"outcome": "passed", "exception_type": None, "when": "call"}
        value = {
            "schema": "agentkit/local-phase-receipt-v1", "status": "passed",
            "run_id": run_id, "phase": phase, "reason": reason,
            "outcome_source": "pytest_child_report",
            "exit_code": exit_code, "policy_sha256": self.phase_policy.sha256,
            "host_runner_sha256": self.phase_policy.host_runner_sha256,
            "image_ref": self.phase_policy.image_ref, "image_id": self.phase_policy.image_id,
            "dependency_lock_sha256": self.phase_policy.dependency_lock_sha256,
            "snapshot_sha256": freshness["snapshot_sha256"],
            "workspace_post_snapshot_sha256": freshness["snapshot_sha256"],
            "input_hashes": freshness["input_hashes"],
            "collection": {
                "nodeids_sha256": _digest(nodeids), "count": len(nodeids),
                "files_sha256": _digest(files), "files_count": len(files),
            },
            "outcomes": {node: outcome for node in nodeids},
            "scratch_post_hashes": freshness["input_hashes"],
            "cleanup_confirmed": True, "duration_seconds": 0.01, "output": "",
        }
        value["receipt_sha256"] = _digest(value)
        return value

    def run_engine(self, *, include_full=True):
        backend = self.codex_backend_fixture()
        decisions = iter([
            self.decision(), self.decision(role="reviewer"),
            self.decision("finish", ""),
            *([] if include_full else [self.decision("blocked", "")]),
        ])
        phase_actions = [
            self.proposal("run_local_tests", phase="red"),
            self.proposal("write_file", path="agentkit/worker.py", content="def work(): return 2\n"),
            self.proposal("run_local_tests", phase="targeted"),
        ]
        if include_full:
            phase_actions.append(self.proposal("run_local_tests", phase="full"))
        phase_actions.append(self.final_action())
        actions = iter(phase_actions)
        prompts = []
        reviewer_steps = iter([
            {
                "kind": "proposal", "tool": "read_file",
                "arguments": {"path": "agentkit/worker.py", "content": "", "old_text": "",
                              "new_text": "", "start_line": 1, "max_lines": 40},
                "rationale": "Inspect the changed implementation.",
                "report": {"status": "blocked", "summary": "Observation requested.",
                           "artifacts": [], "evidence": [], "next_actions": []},
            },
            {
                "kind": "final", "tool": "none",
                "arguments": {"path": "", "content": "", "old_text": "", "new_text": "",
                              "start_line": None, "max_lines": None},
                "rationale": "Review complete.",
                "report": self.report(),
            },
        ])

        def fake_call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            if contract == "decision":
                return next(decisions)
            if contract == "codex_action_step":
                return next(actions)
            if contract == "codex_private_review_action_step":
                return next(reviewer_steps)
            if contract == "report":
                return self.report()
            raise AssertionError(f"Unexpected Codex contract: {contract}")

        def fake_phase(policy, workspace, phase, *, run_id, timeout, runner=None, results_dir):
            self.assertEqual(self.phase_policy.sha256, policy.sha256)
            self.assertEqual(self.workspace.resolve(), workspace.resolve())
            return self.phase_receipt(phase, run_id)

        with patch("agentkit.backends.codex_command", return_value=["codex-fixture"]), \
                patch.object(CodexBackend, "_call", side_effect=fake_call), \
                patch("agentkit.phase_test_runtime.run_phase", side_effect=fake_phase):
            state = Engine(
                self.agent, self.workspace, backend,
                write_policy=self.write_policy,
                local_phase_policy=self.phase_policy,
            ).run("Complete the verified local phase workflow")
        return state, prompts

    def test_engine_recovers_from_pre_red_write_denial_without_unauthorized_mutation(self):
        self.source.write_text("def work(): return 1\n", encoding="utf-8")
        original_test = self.test_file.read_text(encoding="utf-8")
        backend = self.codex_backend_fixture()
        decisions = iter([
            self.decision(), self.decision(role="reviewer"),
            self.decision("finish", ""),
        ])
        actions = iter([
            self.proposal("write_file", path="agentkit/worker.py", content="def work(): return 9\n"),
            self.proposal("write_file", path="tests/test_worker.py", content="def test_worker(): assert True\n# updated\n"),
            self.final_action(),
        ])
        prompts = []

        def fake_call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            if contract == "decision":
                return next(decisions)
            if contract == "codex_action_step":
                return next(actions)
            if contract == "codex_private_review_action_step":
                return {
                    "kind": "final", "tool": "none",
                    "arguments": {"path": "", "content": "", "old_text": "", "new_text": "",
                                  "start_line": None, "max_lines": None},
                    "rationale": "Review complete.", "report": self.report(),
                }
            if contract == "report":
                return self.report()
            raise AssertionError(f"Unexpected Codex contract: {contract}")

        with patch("agentkit.backends.codex_command", return_value=["codex-fixture"]), \
                patch.object(CodexBackend, "_call", side_effect=fake_call), \
                patch("agentkit.phase_test_runtime.run_phase") as run_phase:
            state = Engine(
                self.agent, self.workspace, backend,
                write_policy=self.write_policy, local_phase_policy=self.phase_policy,
            ).run("Try to edit before reproducing the regression")

        self.assertEqual("blocked", state["status"])
        self.assertEqual("def work(): return 1\n", self.source.read_text(encoding="utf-8"))
        self.assertNotEqual(original_test, self.test_file.read_text(encoding="utf-8"))
        action_prompts = [prompt for prompt, contract in prompts if contract == "codex_action_step"]
        self.assertGreaterEqual(len(action_prompts), 2)
        self.assertIn("rejected_proposal", action_prompts[1])
        self.assertIn("With stale RED", action_prompts[1])
        run_phase.assert_not_called()

    def test_real_engine_phase_write_review_finish_flow_uses_private_callbacks(self):
        state, prompts = self.run_engine(include_full=True)
        self.assertEqual("completed", state["status"], state.get("summary"))
        self.assertEqual("def work(): return 2\n", self.source.read_text(encoding="utf-8"))
        attempts = state["local_phase_execution"]["attempts"]
        self.assertEqual(["red", "targeted", "full"], [item["phase"] for item in attempts])
        self.assertTrue(state["reviewed"])
        self.assertEqual(2, sum(
            contract == "codex_private_review_action_step" for _, contract in prompts
        ))
        self.assertTrue(all("authorize_local_mutation" not in prompt for prompt, _ in prompts))
        self.assertTrue(all('"run_local_phase"' not in prompt for prompt, _ in prompts))
        self.assertTrue(all('"local_phase_policy"' not in prompt for prompt, _ in prompts))

    def test_missing_fresh_full_phase_cannot_finish(self):
        state, _ = self.run_engine(include_full=False)
        self.assertEqual("blocked", state["status"])
        self.assertNotEqual("completed", state["status"])
        self.assertEqual(["red", "targeted"], [item["phase"] for item in state["local_phase_execution"]["attempts"]])
        rejected = [entry for entry in state["history"] if entry.get("completion_rejected")]
        self.assertTrue(rejected)
        self.assertIn("full", rejected[-1]["completion_rejected"])

    def test_stale_red_recovers_only_via_exact_baseline_edit_then_fresh_red(self):
        baseline_source = self.source.read_bytes()
        prompts = []
        decisions = iter([
            self.decision(), self.decision(role="reviewer"), self.decision("finish", ""),
        ])

        def action(tool, *, path="", content="", old_text="", new_text="", phase=None):
            return {
                "kind": "proposal", "tool": tool,
                "arguments": {
                    "path": path, "content": content, "old_text": old_text,
                    "new_text": new_text, "start_line": None, "max_lines": None,
                    "phase": phase,
                },
                "rationale": "Use one host-authorized action.",
                "report": {"status": "blocked", "summary": "Action requested.",
                           "artifacts": [], "evidence": [], "next_actions": []},
            }

        worker_actions = iter([
            action("run_local_tests", phase="red"),
            action("edit_file", path="agentkit/worker.py", old_text="return 1", new_text="return 3"),
            action("write_file", path="tests/test_worker.py", content="def test_worker(): assert False\n"),
            action("edit_file", path="agentkit/worker.py", old_text="return 3", new_text="return 99"),
            action("restore_production_baseline", path="agentkit/worker.py"),
            action("run_local_tests", phase="red"),
            action("edit_file", path="agentkit/worker.py", old_text="return 1", new_text="return 2"),
            action("run_local_tests", phase="targeted"),
            action("run_local_tests", phase="full"),
            {
                "kind": "final", "tool": "none",
                "arguments": {"path": "", "content": "", "old_text": "", "new_text": "",
                              "start_line": None, "max_lines": None, "phase": None},
                "rationale": "All required phases and review are complete.",
                "report": self.report(),
            },
        ])
        reviewer_actions = iter([
            {
                "kind": "proposal", "tool": "read_file",
                "arguments": {"path": "agentkit/worker.py", "content": "", "old_text": "",
                              "new_text": "", "start_line": 1, "max_lines": 20},
                "rationale": "Inspect the final source.",
                "report": {"status": "blocked", "summary": "Observation requested.",
                           "artifacts": [], "evidence": [], "next_actions": []},
            },
            {
                "kind": "final", "tool": "none",
                "arguments": {"path": "", "content": "", "old_text": "", "new_text": "",
                              "start_line": None, "max_lines": None},
                "rationale": "Review complete.", "report": self.report(),
            },
        ])

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            if contract == "decision":
                return next(decisions)
            if contract == "codex_action_step":
                return next(worker_actions)
            if contract == "codex_private_review_action_step":
                return next(reviewer_actions)
            raise AssertionError(f"Unexpected Codex contract: {contract}")

        phase_calls = []

        def fake_phase(policy, workspace, phase, *, run_id, timeout, runner=None, results_dir):
            phase_calls.append(phase)
            if phase == "red" and phase_calls.count("red") == 2:
                self.assertEqual(baseline_source, self.source.read_bytes())
            return self.phase_receipt(phase, run_id)

        with patch("agentkit.backends.codex_command", return_value=["codex-fixture"]), \
                patch.object(CodexBackend, "_call", side_effect=call), \
                patch("agentkit.phase_test_runtime.run_phase", side_effect=fake_phase):
            state = Engine(
                self.agent, self.workspace, self.codex_backend_fixture(),
                write_policy=self.write_policy, local_phase_policy=self.phase_policy,
            ).run("Recover from stale RED safely and verify the correction")

        self.assertEqual("completed", state["status"], state.get("summary"))
        self.assertEqual(baseline_source.replace(b"return 1", b"return 2"),
                         self.source.read_bytes())
        self.assertEqual("def test_worker(): assert False\n",
                         self.test_file.read_text(encoding="utf-8"))
        self.assertEqual(["red", "red", "targeted", "full"], phase_calls)
        self.assertIn("rejected_proposal", prompts[5][0])
        self.assertNotIn("def work(): return 1", prompts[4][0])
        restore_entry = next(
            item for item in state["completed_actions"]
            if item["tool"] == "restore_production_baseline"
        )
        self.assertEqual({"path": "agentkit/worker.py"}, restore_entry["arguments"])
        self.assertIn(hashlib.sha256(baseline_source).hexdigest(), restore_entry["result"])
        restore_receipts = [
            item for item in state["write_provenance_receipts"]
            if item["action_sha256"] == restore_entry["action_sha256"]
        ]
        self.assertEqual(1, len(restore_receipts))
        self.assertEqual("present", restore_receipts[0]["state"])
        self.assertEqual(hashlib.sha256(baseline_source).hexdigest(), restore_receipts[0]["sha256"])
        self.assertTrue(state["reviewed"])

        run_dir = self.agent / ".runs" / state["run_id"]
        cache_dir = run_dir / "private-production-baseline"
        cache_manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
        (cache_dir / cache_manifest["files"][0]["blob"]).write_bytes(b"tampered baseline")
        with self.assertRaises(ContractError):
            Engine(
                self.agent, self.workspace, self.codex_backend_fixture(),
                write_policy=self.write_policy, local_phase_policy=self.phase_policy,
            ).run(
                "", run_dir=run_dir, feedback="Resume after cache validation.",
                acknowledge_interruption=True,
            )


if __name__ == "__main__":
    unittest.main()
