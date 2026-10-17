from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.approvals import ApprovalRequired, action_digest, replay_action_digest
from agentkit.backends import CodexBackend
from agentkit.contracts import ContractError, schema, validate
from agentkit.phase_test_execution import LocalPhaseTestPolicy
from agentkit.phase_test_runtime import LocalPhaseProposalRejected
from agentkit.write_policy import WritePolicy


class CodexLocalPhaseTests(unittest.TestCase):
    def setUp(self):
        codex_command_patch = patch(
            "agentkit.backends.codex_command", return_value=["codex-fixture"]
        )
        sandbox_selection_patch = patch(
            "agentkit.backends._windows_sandbox_selection", return_value=None
        )
        self.codex_command = codex_command_patch.start()
        self.windows_sandbox_selection = sandbox_selection_patch.start()
        self.addCleanup(codex_command_patch.stop)
        self.addCleanup(sandbox_selection_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "agentkit").mkdir()
        (self.workspace / "tests").mkdir()
        source = self.workspace / "agentkit" / "worker.py"
        source.write_text("def work(): return 1\n", encoding="utf-8")
        test = self.workspace / "tests" / "test_worker.py"
        test.write_text("def test_worker(): assert True\n", encoding="utf-8")
        manifest = {
            "version": 1,
            "image_ref": "registry.example/agentkit@sha256:" + "a" * 64,
            "image_id": "sha256:" + "a" * 64,
            "dependency_lock_sha256": "b" * 64,
            "host_runner_sha256": "c" * 64,
            "production_files": [{
                "path": "agentkit/worker.py",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
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
                "timeout_seconds": 720,
                "memory_bytes": 2 * 1024**3,
                "memory_swap_bytes": 2 * 1024**3,
                "nano_cpus": 2_000_000_000,
                "pids": 256,
                "output_bytes": 2_000_000,
                "nofile": 1024,
                "tmpfs_bytes": 256 * 1024**2,
                "max_file_bytes": 8 * 1024**2,
                "max_snapshot_bytes": 512 * 1024**2,
            },
        }
        self.policy_path = self.root / "phase-policy.json"
        self.policy_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.phase_policy = LocalPhaseTestPolicy.from_file(
            self.policy_path, self.workspace
        )
        self.write_policy = WritePolicy([
            "agentkit/worker.py", "tests/test_worker.py"
        ])
        self.step_args = {
            "path": "", "content": "", "old_text": "", "new_text": "",
            "start_line": None, "max_lines": None, "phase": "targeted",
        }
        self.proposal = {
            "kind": "proposal", "tool": "run_local_tests",
            "arguments": self.step_args,
            "rationale": "Run the host-selected targeted phase.",
            "report": self.blocked_report(),
        }
        self.final = {
            "kind": "final", "tool": "none",
            "arguments": {**self.step_args, "phase": None},
            "rationale": "The phase result is recorded.",
            "report": {
                "status": "success", "summary": "Verified.", "artifacts": [],
                "evidence": ["phase receipt"], "next_actions": [],
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def blocked_report():
        return {
            "status": "blocked", "summary": "Action requested.", "artifacts": [],
            "evidence": [], "next_actions": [],
        }

    def context(self, callback):
        return {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "write_policy": self.write_policy,
            "local_phase_policy": self.phase_policy,
            "run_local_phase": callback,
            "run_id": "1" * 32,
        }

    def receipt(self, phase="targeted", status="passed"):
        return {
            "schema": "agentkit/local-phase-receipt-v1", "phase": phase,
            "outcome_source": "pytest_child_report",
            "run_id": "1" * 32,
            "status": status, "reason": "ok", "policy_sha256": self.phase_policy.sha256,
            "snapshot_sha256": "d" * 64, "receipt_sha256": "e" * 64,
            "cleanup_confirmed": True,
            "collection": {"count": 1, "nodeids_sha256": "f" * 64},
            "output": "PRIVATE-RAW-OUTPUT-MUST-NOT-REACH-MODEL",
        }

    def phase_proposal(self, phase):
        return {**self.proposal, "arguments": {**self.step_args, "phase": phase}}

    def test_known_phase_order_rejection_is_feedback_then_red_can_run(self):
        callback = unittest.mock.Mock(side_effect=[
            LocalPhaseProposalRejected("Regression phases require a reproduced RED."),
            self.receipt("red"),
        ])
        responses = [self.proposal, self.phase_proposal("red"), self.final]
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            return responses[len(prompts) - 1]

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            report = CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "run RED first"},
                self.context(callback), 10,
            )

        self.assertEqual("success", report["status"])
        self.assertEqual(["targeted", "red"], [
            entry.args[0] for entry in callback.call_args_list
        ])
        self.assertIn("rejected_proposal", prompts[1][0])
        self.assertIn("reproduced RED", prompts[1][0])
        self.assertEqual("codex_action_step", prompts[2][1])

    def test_post_reservation_contract_error_propagates_without_reprompt(self):
        callback = unittest.mock.Mock(
            side_effect=ContractError("Phase outcome is unknown after reservation.")
        )
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            return self.proposal

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            with self.assertRaisesRegex(ContractError, "unknown after reservation"):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "run tests"},
                    self.context(callback), 10,
                )

        callback.assert_called_once()
        self.assertEqual(1, len(prompts))

    def test_repeated_known_phase_rejections_use_existing_correction_limit(self):
        callback = unittest.mock.Mock(
            side_effect=LocalPhaseProposalRejected("Run RED before regression phases.")
        )
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            return self.proposal

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            with self.assertRaisesRegex(ContractError, "repeatedly proposed a phase-ordering"):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "run tests"},
                    self.context(callback), 10,
                )

        self.assertEqual(CodexBackend.max_proposal_corrections + 1, len(prompts))
        self.assertEqual(CodexBackend.max_proposal_corrections + 1, callback.call_count)

    def test_phase_action_calls_only_host_callback_and_exposes_bounded_receipt(self):
        callback = unittest.mock.Mock(return_value=self.receipt())
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract, context))
            return self.proposal if len(prompts) == 1 else self.final

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            report = CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "test"}, self.context(callback), 10
            )

        self.assertEqual("success", report["status"])
        self.assertEqual(1, callback.call_count)
        self.assertEqual("targeted", callback.call_args.args[0])
        self.assertGreater(callback.call_args.args[1], 0)
        self.assertLessEqual(callback.call_args.args[1], 10)
        self.assertEqual("codex_action_step", prompts[0][1])
        self.assertEqual("codex_action_step", prompts[1][1])
        self.assertNotIn('"run_local_phase"', prompts[0][0])
        self.assertNotIn('"local_phase_policy"', prompts[0][0])
        self.assertIn("targeted", prompts[1][0])
        self.assertIn("passed", prompts[1][0])
        self.assertNotIn("PRIVATE-RAW-OUTPUT-MUST-NOT-REACH-MODEL", prompts[1][0])

    def test_invalid_phase_and_missing_strict_context_never_call_callback(self):
        callback = unittest.mock.Mock(return_value=self.receipt())
        invalid = {**self.proposal, "arguments": {**self.step_args, "phase": "custom"}}
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=invalid):
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "test"}, self.context(callback), 10
                )
        callback.assert_not_called()
        unsupported = self.context(callback)
        unsupported.pop("write_policy")
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.proposal):
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "test"}, unsupported, 10
                )
        callback.assert_not_called()
        mismatched = self.context(callback)
        mismatched["write_policy"] = WritePolicy(["agentkit/worker.py"])
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.proposal):
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "test"}, mismatched, 10
                )
        callback.assert_not_called()

    def test_backend_fixture_does_not_depend_on_host_cli_or_windows_config(self):
        backend = CodexBackend()

        self.assertEqual(["codex-fixture"], backend.command)
        self.assertIsNone(backend.windows_sandbox)
        self.codex_command.assert_called_once_with()
        self.windows_sandbox_selection.assert_called_once_with()

    def test_local_action_is_not_a_public_action_or_path_bearing_tool(self):
        with self.assertRaises(ContractError):
            CodexBackend._validate_action("run_local_tests", {"phase": "targeted"})
        hidden = {**self.step_args, "path": "tests/test_worker.py"}
        with self.assertRaises(ContractError):
            CodexBackend._action_from_step(
                {**self.proposal, "arguments": hidden}, allow_local_phase=True
            )

    def test_local_policy_mutation_requires_host_runtime_authorization(self):
        write = {
            **self.proposal,
            "tool": "write_file",
            "arguments": {
                "path": "agentkit/worker.py", "content": "def work(): return 2\n",
                "old_text": "", "new_text": "", "start_line": None,
                "max_lines": None, "phase": None,
            },
        }
        callback = unittest.mock.Mock(return_value=self.receipt())
        context = self.context(callback)
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=[write, self.final]), \
                patch("agentkit.backends.DeepSeekBackend._run_tool") as execute:
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "edit"}, context, 10
                )
        execute.assert_not_called()

        authorize = unittest.mock.Mock(return_value=None)
        context["authorize_local_mutation"] = authorize
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=[write, self.final]), \
                patch("agentkit.backends.DeepSeekBackend._run_tool", return_value="written") as execute:
            result = CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "edit"}, context, 10
            )
        self.assertEqual("success", result["status"])
        authorize.assert_called_once_with(
            "write_file", {"path": "agentkit/worker.py", "content": "def work(): return 2\n"}
        )
        execute.assert_called_once()

    def test_pre_red_production_write_is_rejected_then_test_edit_can_run(self):
        original_source = (self.workspace / "agentkit/worker.py").read_text(encoding="utf-8")
        original_test = (self.workspace / "tests/test_worker.py").read_text(encoding="utf-8")
        production_write = {
            **self.proposal,
            "tool": "write_file",
            "arguments": {
                "path": "agentkit/worker.py", "content": "def work(): return 2\n",
                "old_text": "", "new_text": "", "start_line": None,
                "max_lines": None, "phase": None,
            },
        }
        test_write = {
            **self.proposal,
            "tool": "write_file",
            "arguments": {
                "path": "tests/test_worker.py", "content": "def test_worker(): assert True\n# changed\n",
                "old_text": "", "new_text": "", "start_line": None,
                "max_lines": None, "phase": None,
            },
        }
        responses = [production_write, test_write, self.final]
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append((prompt, contract))
            return responses[len(prompts) - 1]

        authorize = unittest.mock.Mock(side_effect=[
            LocalPhaseProposalRejected(
                "Production changes require a reproduced RED."
            ),
            None,
        ])
        context = self.context(unittest.mock.Mock(return_value=self.receipt()))
        context["authorize_local_mutation"] = authorize

        def write_file(backend, tool, arguments, _context, _timeout):
            (self.workspace / arguments["path"]).write_text(
                arguments["content"], encoding="utf-8"
            )
            return "written"

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call), \
                patch("agentkit.backends.DeepSeekBackend._run_tool", side_effect=write_file) as execute:
            report = CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "make a test-only change"}, context, 10
            )

        self.assertEqual("success", report["status"])
        self.assertEqual(original_source, (self.workspace / "agentkit/worker.py").read_text(encoding="utf-8"))
        self.assertNotEqual(original_test, (self.workspace / "tests/test_worker.py").read_text(encoding="utf-8"))
        self.assertEqual(1, execute.call_count)
        self.assertEqual("tests/test_worker.py", execute.call_args.args[2]["path"])
        self.assertIn("rejected_proposal", prompts[1][0])

    def test_unknown_phase_receipt_stops_without_retry(self):
        callback = unittest.mock.Mock(return_value=self.receipt(status="unknown"))
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.proposal):
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "test"}, self.context(callback), 10
                )
        callback.assert_called_once()

    def test_approval_continuation_runs_only_the_approved_phase(self):
        callback = unittest.mock.Mock(return_value=self.receipt())
        approve = unittest.mock.Mock()
        context = self.context(callback)
        context.update(require_approvals=True, request_approval=approve)
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.proposal):
            with self.assertRaises(ApprovalRequired):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "test"}, context, 10
                )
        callback.assert_not_called()
        approve.assert_called_once()
        approved_args = {"phase": "targeted"}
        action_context = self.context(callback)
        action_context.update(
            approval_resume={
                "kind": "codex-action", "tool": "run_local_tests",
                "arguments": approved_args, "action_history": [],
            },
            approved_action={
                "tool": "run_local_tests", "arguments": approved_args,
                "action_sha256": action_digest("run_local_tests", approved_args),
                "replay_sha256": replay_action_digest(
                    "run_local_tests", approved_args, self.workspace
                ),
            },
            completed_actions=[],
        )
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.final):
            report = CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "test"}, action_context, 10
            )
        self.assertEqual("success", report["status"])
        callback.assert_called_once()
        self.assertEqual("targeted", callback.call_args.args[0])

    def test_approval_continuation_does_not_convert_phase_denial_to_retry(self):
        callback = unittest.mock.Mock(
            side_effect=LocalPhaseProposalRejected("Phase sequence changed after approval.")
        )
        approved_args = {"phase": "targeted"}
        context = self.context(callback)
        context.update(
            approval_resume={
                "kind": "codex-action", "tool": "run_local_tests",
                "arguments": approved_args, "action_history": [],
            },
            approved_action={
                "tool": "run_local_tests", "arguments": approved_args,
                "action_sha256": action_digest("run_local_tests", approved_args),
                "replay_sha256": replay_action_digest(
                    "run_local_tests", approved_args, self.workspace
                ),
            },
            completed_actions=[],
        )
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", return_value=self.final) as model_call:
            with self.assertRaisesRegex(
                LocalPhaseProposalRejected, "changed after approval"
            ):
                CodexBackend()._execute_approval_gated(
                    {"role": "worker", "task": "resume approved phase"},
                    context, 10,
                )
        callback.assert_called_once()
        model_call.assert_not_called()

    def test_local_schema_disables_native_shell_and_preserves_standard_schema(self):
        captured = {}

        def run_process(args, prompt, cwd, timeout, **kwargs):
            captured["args"] = args
            captured["prompt"] = prompt
            schema_path = Path(args[args.index("--output-schema") + 1])
            captured["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
            result_path = Path(args[args.index("--output-last-message") + 1])
            result_path.write_text("{}", encoding="utf-8")

        context = self.context(lambda phase, timeout: self.receipt(phase))
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch("agentkit.backends.run_process", side_effect=run_process):
            CodexBackend()._call("prompt", "codex_action_step", context, 10)

        args = captured["args"]
        disabled_tools = [args[index + 1] for index, value in enumerate(args[:-1])
                          if value == "--disable"]
        self.assertEqual(["multi_agent", "shell_tool"], disabled_tools)
        self.assertEqual("run_local_tests", captured["schema"]["properties"]["tool"]["enum"][-1])
        self.assertEqual("run_isolated_tests", __import__("agentkit.contracts", fromlist=["schema"]).schema(
            "codex_action_step"
        )["properties"]["tool"]["enum"][-1])

    def test_private_prompt_manifest_and_examples_match_local_action_schema(self):
        prompts = []

        def call(prompt, contract, context, timeout):
            prompts.append(prompt)
            return self.final

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "implement and verify"},
                self.context(unittest.mock.Mock(return_value=self.receipt())), 10,
            )

        prompt = prompts[0]
        local_schema = schema("codex_local_action_step")
        schema_tools = set(local_schema["properties"]["tool"]["enum"]) - {"none"}
        manifest_line = next(line for line in prompt.splitlines() if line.startswith("AVAILABLE_HOST_ACTIONS_JSON="))
        example_line = next(line for line in prompt.splitlines() if line.startswith("LOCAL_ACTION_EXAMPLE_JSON="))
        phase_example_line = next(line for line in prompt.splitlines() if line.startswith("LOCAL_PHASE_EXAMPLE_JSON="))
        manifest = json.loads(manifest_line.split("=", 1)[1])
        example = json.loads(example_line.split("=", 1)[1])
        phase_example = json.loads(phase_example_line.split("=", 1)[1])
        listed_tools = {item["tool"] for item in manifest["available_host_actions"]}

        self.assertEqual(
            {"read_file", "list_files", "inspect_git", "write_file", "edit_file", "run_local_tests"},
            listed_tools,
        )
        self.assertTrue(listed_tools.issubset(schema_tools))
        self.assertEqual(
            set(manifest["schema_compatibility_only_not_enabled_here"]),
            schema_tools - listed_tools,
        )
        self.assertIn("PRIVATE LOCAL HOST-ACTION PROTOCOL", prompt)
        self.assertEqual(set(local_schema["properties"]["arguments"]["required"]), set(example["arguments"]))
        self.assertIsNone(example["arguments"]["phase"])
        validate(example, "codex_local_action_step")
        validate(phase_example, "codex_local_action_step")
        self.assertEqual("run_local_tests", phase_example["tool"])
        self.assertEqual(
            {"phase": ["red", "targeted", "full"]},
            manifest["available_host_actions"][-1]["parameters"],
        )

    def test_public_prompt_does_not_receive_private_phase_protocol(self):
        prompts = []
        context = self.context(unittest.mock.Mock(return_value=self.receipt()))
        context.pop("local_phase_policy")
        context.pop("run_local_phase")
        public_final = {
            **self.final,
            "arguments": {key: value for key, value in self.final["arguments"].items() if key != "phase"},
        }

        def call(prompt, contract, context, timeout):
            prompts.append(prompt)
            return public_final

        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
                patch.object(CodexBackend, "_call", side_effect=call):
            CodexBackend()._execute_approval_gated(
                {"role": "worker", "task": "implement and verify"}, context, 10
            )

        self.assertEqual(1, len(prompts))
        self.assertNotIn("PRIVATE LOCAL HOST-ACTION PROTOCOL", prompts[0])
        self.assertNotIn("AVAILABLE_HOST_ACTIONS_JSON=", prompts[0])
        self.assertNotIn("LOCAL_PHASE_EXAMPLE_JSON=", prompts[0])


if __name__ == "__main__":
    unittest.main()
