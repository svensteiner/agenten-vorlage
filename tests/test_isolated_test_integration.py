"""Engine-level contracts for the host-owned isolated test action."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentkit.approvals import (
    ApprovalRequired,
    action_digest,
    replay_action_digest,
    workspace_fingerprint,
)
from agentkit.backends import CodexBackend, DeepSeekBackend
from agentkit.api_backend import ApiBackend
from agentkit.anthropic_backend import AnthropicBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.ollama_backend import OllamaBackend
from agentkit.scaffold import create
from agentkit.test_execution import TestExecutionPolicy


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class WorkflowBackend:
    name = "integration-fixture"
    supports_action_approvals = True
    supports_isolated_tests = True

    def __init__(self, *, record_receipt: bool = True, request_approval: bool = False,
                 record_write_after_test: bool = False):
        self.record_receipt = record_receipt
        self.request_test_approval = request_approval
        self.record_write_after_test = record_write_after_test
        self.planner_contexts = []

    def decide(self, context, timeout):
        self.planner_contexts.append(context)
        history = context["history"]
        if not history:
            return {"action": "delegate", "role": "developer", "skills": [],
                    "task": "Run the verified suite", "reason": "test fixture"}
        if history[-1]["decision"]["role"] == "developer":
            return {"action": "delegate", "role": "reviewer", "skills": [],
                    "task": "Review the result", "reason": "test fixture"}
        return {"action": "finish", "role": "", "skills": [],
                "task": "Fixture finished", "reason": "test fixture"}

    @staticmethod
    def _receipt(context, policy):
        return {
            "status": "passed", "run_id": context["run_id"], "reason": "ok",
            "exit_code": 0, "policy_sha256": policy.sha256,
            "test_manifest_sha256": policy.sha256, "test_paths": list(policy.test_paths),
            "expected_test_count": policy.expected_test_count,
            "test_outcomes": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                              "xfailed": 0, "xpassed": 0, "deselected": 0},
            "image_ref": policy.image_ref, "image_id": policy.image_id,
            "dependency_lock_sha256": policy.dependency_lock_sha256,
            "snapshot_sha256": "c" * 64,
            "workspace_fingerprint": workspace_fingerprint(Path(context["workspace"])),
            "duration_seconds": 0.1, "output": "1 passed", "cleanup_confirmed": True,
        }

    def execute(self, decision, context, timeout):
        if decision["role"] == "developer":
            policy = context["test_execution_policy"]
            if self.request_test_approval:
                context["request_approval"]("run_isolated_tests", {}, {"kind": "fixture-test"})
            if self.record_receipt:
                context["begin_test_execution"]()
                context["record_test_execution"](self._receipt(context, policy))
            if self.record_write_after_test:
                context["record_completed_action"]({
                    "kind": "completed_action", "tool": "write_file",
                    "action_sha256": "a" * 64, "replay_sha256": "b" * 64,
                    "post_workspace_fingerprint": workspace_fingerprint(Path(context["workspace"])),
                })
        return {"status": "success", "summary": "fixture result", "artifacts": [],
                "evidence": ["fixture evidence"], "next_actions": []}


class IsolatedTestIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agent", "developer", "integration", "fixture")
        self.workspace = self.agent / "workspace"
        self.manifest = self.root / "test-policy.json"
        self._write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def _write_manifest(self, *, test_hash: str | None = None):
        self.manifest.write_text(json.dumps({
            "version": 1,
            "image_ref": "python@sha256:" + "c" * 64,
            "image_id": "sha256:" + "b" * 64,
            "dependency_lock_sha256": "a" * 64,
            "docker_transport": "native",
            "test_files": [{"path": "tests/test_ok.py", "sha256": test_hash or _sha("test") }],
            "support_files": [],
            "expected_test_count": 1,
            "snapshot_paths": ["tests/test_ok.py"],
        }), encoding="utf-8")

    def policy(self):
        return TestExecutionPolicy.from_file(self.manifest)

    @staticmethod
    def codex_backend():
        # Only command discovery is a fixture; proposal/approval execution stays real.
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            return CodexBackend()

    def test_engine_exposes_only_json_safe_policy_summary_to_planner(self):
        backend = WorkflowBackend()
        policy = self.policy()
        def stop(context, timeout):
            backend.planner_contexts.append(context)
            json.dumps(context)
            return {"action": "blocked", "role": "", "skills": [],
                    "task": "done", "reason": "fixture"}
        backend.decide = stop
        state = Engine(self.agent, self.workspace, backend,
                       test_execution_policy=policy).run("fixture")
        self.assertEqual("blocked", state["status"])
        context = backend.planner_contexts[0]
        self.assertEqual(policy.summary(), context["test_execution_policy_summary"])
        self.assertNotIn("test_execution_policy", context)

    def test_deepseek_provider_context_strips_host_policy_and_callbacks(self):
        policy = self.policy()
        raw = {
            "test_execution_policy": policy,
            "begin_test_execution": Mock(),
            "record_test_execution": Mock(),
            "test_execution_policy_summary": policy.summary(),
            "task": "run tests",
        }
        sanitized = DeepSeekBackend._provider_context(raw)
        self.assertEqual({"task": "run tests",
                          "test_execution_policy_summary": policy.summary()}, sanitized)
        json.dumps(sanitized)

    def test_finish_requires_a_host_receipt_and_fresh_review(self):
        backend = WorkflowBackend(record_receipt=False)
        state = Engine(self.agent, self.workspace, backend,
                       test_execution_policy=self.policy()).run("fixture")
        self.assertNotEqual("completed", state["status"])
        self.assertIsNone(state["latest_test_execution_receipt"])

    def test_host_pass_receipt_allows_finish_only_after_review(self):
        backend = WorkflowBackend()
        state = Engine(self.agent, self.workspace, backend,
                       test_execution_policy=self.policy()).run("fixture")
        self.assertEqual("completed", state["status"])
        self.assertTrue(state["reviewed"])
        self.assertEqual("passed", state["latest_test_execution_receipt"]["status"])
        self.assertEqual(1, state["test_execution_runs"])

    def test_unknown_test_runner_outcome_consumes_durable_attempt_and_stays_in_flight(self):
        class RunnerFailure(WorkflowBackend):
            def execute(self, decision, context, timeout):
                context["begin_test_execution"]()
                raise RuntimeError("test runner transport outcome is unknown")

        state = Engine(self.agent, self.workspace, RunnerFailure(),
                       test_execution_policy=self.policy()).run("fixture")
        self.assertEqual("blocked", state["status"])
        self.assertEqual(1, state["test_execution_runs"])
        self.assertIsNone(state["latest_test_execution_receipt"])
        self.assertEqual("worker", state["in_flight"]["kind"])

    def test_write_after_test_invalidates_receipt_even_if_bytes_are_unchanged(self):
        backend = WorkflowBackend(record_write_after_test=True)
        state = Engine(self.agent, self.workspace, backend,
                       test_execution_policy=self.policy()).run("fixture")
        self.assertNotEqual("completed", state["status"])
        self.assertIsNone(state["latest_test_execution_receipt"])

    def test_pending_test_approval_is_bound_to_test_manifest_digest(self):
        backend = WorkflowBackend(request_approval=True)
        policy = self.policy()
        state = Engine(self.agent, self.workspace, backend, require_approvals=True,
                       test_execution_policy=policy).run("fixture")
        self.assertEqual("awaiting_approval", state["status"])
        pending = state["pending_approval"]
        self.assertEqual(policy.sha256, pending["binding"]["test_execution_policy_sha256"])
        run_dir = self.agent / ".runs" / state["run_id"]
        self._write_manifest(test_hash="d" * 64)
        with self.assertRaisesRegex(ContractError, "test execution policy"):
            Engine(self.agent, self.workspace, backend, require_approvals=True,
                   test_execution_policy=self.policy()).run(
                       "", run_dir=run_dir, approval_id=pending["id"],
                       approval_decision="approve")

    def test_backend_without_explicit_capability_is_rejected_before_dispatch(self):
        class UnknownBackend:
            name = "unknown"

            def decide(self, context, timeout):
                raise AssertionError("must reject before dispatch")

            def execute(self, decision, context, timeout):
                raise AssertionError("must reject before dispatch")

        with self.assertRaisesRegex(ContractError, "isolated test execution"):
            Engine(self.agent, self.workspace, UnknownBackend(),
                   test_execution_policy=self.policy())

    def test_deepseek_tool_is_hidden_without_policy_and_noarg_when_enabled(self):
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"run_isolated_tests"})
        self.assertNotIn("run_isolated_tests", {
            item["function"]["name"] for item in backend.available_tool_specs()
        })
        enabled = backend.available_tool_specs(include_isolated_tests=True)
        spec = next(item["function"] for item in enabled
                    if item["function"]["name"] == "run_isolated_tests")
        self.assertEqual({"type": "object", "properties": {}, "required": [],
                          "additionalProperties": False}, spec["parameters"])

    def test_deepseek_requires_human_approval_before_test_runner(self):
        policy = self.policy()
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"run_isolated_tests"})
        call = {"id": "call-1", "function": {
            "name": "run_isolated_tests", "arguments": "{}",
        }}
        backend._chat = Mock(return_value={"tool_calls": [call]})
        requested = []

        def approve(tool, arguments, continuation):
            requested.append((tool, arguments, continuation))
            raise ApprovalRequired({"tool": tool, "arguments": arguments})

        context = {
            "workspace": str(self.workspace), "sandbox": "read-only",
            "require_approvals": True, "test_execution_policy": policy,
            "test_execution_runs": 0, "completed_actions": [],
            "request_approval": approve,
        }
        with patch("agentkit.backends.run_isolated_tests") as runner:
            with self.assertRaises(ApprovalRequired):
                backend._call("fixture", "report", context, 5)
        self.assertEqual("run_isolated_tests", requested[0][0])
        self.assertEqual({}, requested[0][1])
        self.assertFalse(runner.called)

    def test_deepseek_approved_resume_runs_pinned_suite_from_readonly_reviewer(self):
        policy = self.policy()
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"run_isolated_tests"})
        report = {"status": "success", "summary": "reviewed", "artifacts": [],
                  "evidence": ["suite reviewed"], "next_actions": []}
        backend._chat = Mock(return_value={"content": json.dumps(report)})
        continuation = {
            "messages": [{"role": "user", "content": "Run pinned tests"}],
            "tool_count": 0,
            "call": {"name": "run_isolated_tests", "arguments": {}, "call_id": "test-1"},
            "remaining_calls": [],
        }
        begin_calls = []
        def begin():
            begin_calls.append(True)
        completed = []
        receipts = []
        context = {
            "workspace": str(self.workspace), "sandbox": "read-only", "require_approvals": True,
            "test_execution_policy": policy, "run_id": "a" * 32,
            "test_execution_runs": 0, "begin_test_execution": begin,
            "record_test_execution": receipts.append,
            "record_completed_action": completed.append,
            "approval_resume": continuation,
            "approved_action": {"tool": "run_isolated_tests", "arguments": {},
                                "action_sha256": action_digest("run_isolated_tests", {}),
                                "replay_sha256": replay_action_digest(
                                    "run_isolated_tests", {}, self.workspace)},
        }
        receipt = WorkflowBackend._receipt(context, policy)
        with patch("agentkit.backends.run_isolated_tests", return_value=receipt) as runner:
            result = backend._call("fixture", "report", context, 5)
        self.assertEqual(report, result)
        self.assertEqual(1, runner.call_count)
        self.assertEqual([True], begin_calls)
        self.assertEqual([receipt], receipts)
        self.assertEqual("run_isolated_tests", completed[0]["tool"])

    def test_codex_proposal_is_host_approved_and_callbacks_stay_out_of_prompt(self):
        policy = self.policy()
        backend = self.codex_backend()
        args = {"path": "", "content": "", "old_text": "", "new_text": ""}
        backend._call = Mock(return_value={
            "kind": "proposal", "tool": "run_isolated_tests", "arguments": args,
            "rationale": "Run pinned tests", "report": {
                "status": "blocked", "summary": "pending", "artifacts": [],
                "evidence": [], "next_actions": [],
            },
        })
        requested = []

        def approve(tool, arguments, continuation):
            requested.append((tool, arguments, continuation))
            raise ApprovalRequired({"tool": tool, "arguments": arguments})

        context = {
            "workspace": str(self.workspace), "sandbox": "read-only", "require_approvals": True,
            "test_execution_policy": policy,
            "begin_test_execution": Mock(), "record_test_execution": Mock(),
            "request_approval": approve, "record_completed_action": Mock(),
            "completed_actions": [],
        }
        with patch("agentkit.backends.run_isolated_tests") as runner:
            with self.assertRaises(ApprovalRequired):
                backend.execute({"role": "reviewer", "task": "Run tests"}, context, 5)
        self.assertEqual(("run_isolated_tests", {}, {"kind": "codex-action", "tool": "run_isolated_tests",
                                                       "arguments": {}, "action_history": []}), requested[0])
        self.assertNotIn("begin_test_execution", backend._call.call_args.args[0])
        self.assertNotIn("record_test_execution", backend._call.call_args.args[0])
        self.assertNotIn("TestExecutionPolicy(", backend._call.call_args.args[0])
        self.assertFalse(runner.called)

    def test_codex_legacy_report_serializes_without_any_test_policy_callbacks(self):
        backend = self.codex_backend()
        report = {"status": "success", "summary": "legacy path", "artifacts": [],
                  "evidence": ["serialized"], "next_actions": []}
        backend._call = Mock(return_value=report)
        context = {
            "workspace": str(self.workspace), "sandbox": "read-only", "require_approvals": False,
            "begin_test_execution": Mock(), "record_test_execution": Mock(),
            "test_execution_runs": 0, "run_id": "a" * 32,
            "test_execution_policy_summary": {"sha256": "a" * 64},
        }
        result = backend.execute({"role": "reviewer", "task": "legacy review"}, context, 5)
        self.assertEqual(report, result)
        prompt = backend._call.call_args.args[0]
        self.assertNotIn("begin_test_execution", prompt)
        self.assertNotIn("record_test_execution", prompt)
        self.assertIn("test_execution_policy_summary", prompt)

    def test_codex_approved_resume_runs_one_host_suite_and_records_receipt(self):
        policy = self.policy()
        backend = self.codex_backend()
        report = {"status": "success", "summary": "verified", "artifacts": [],
                  "evidence": ["reviewed"], "next_actions": []}
        backend._call = Mock(return_value={
            "kind": "final", "tool": "none",
            "arguments": {"path": "", "content": "", "old_text": "", "new_text": ""},
            "rationale": "Done", "report": report,
        })
        actions, receipts = [], []
        def record_action(entry):
            actions.append(entry)
        def record_receipt(receipt):
            receipts.append(receipt)
        context = {
            "workspace": str(self.workspace), "sandbox": "read-only", "require_approvals": True,
            "test_execution_policy": policy, "run_id": "a" * 32,
            "test_execution_runs": 0, "begin_test_execution": Mock(),
            "record_test_execution": record_receipt, "record_completed_action": record_action,
            "approval_resume": {"kind": "codex-action", "tool": "run_isolated_tests",
                                "arguments": {}, "action_history": []},
            "approved_action": {"tool": "run_isolated_tests", "arguments": {},
                                "action_sha256": action_digest("run_isolated_tests", {}),
                                "replay_sha256": replay_action_digest("run_isolated_tests", {}, self.workspace)},
            "completed_actions": [],
        }
        receipt = WorkflowBackend._receipt(context, policy)
        with patch("agentkit.backends.run_isolated_tests", return_value=receipt) as runner:
            result = backend.execute({"role": "reviewer", "task": "Resume approved tests"}, context, 5)
        self.assertEqual(report, result)
        self.assertEqual(1, runner.call_count)
        context["begin_test_execution"].assert_called_once_with()
        self.assertEqual([receipt], receipts)
        self.assertEqual("run_isolated_tests", actions[0]["tool"])

    def test_api_adapters_advertise_the_same_host_test_capability(self):
        for backend_type in (DeepSeekBackend, ApiBackend, AnthropicBackend, OllamaBackend):
            self.assertIs(backend_type.supports_isolated_tests, True)

    def test_deepseek_test_run_cap_is_checked_before_runner(self):
        policy = self.policy()
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"run_isolated_tests"})
        context = {
            "workspace": str(self.workspace), "sandbox": "read-only",
            "test_execution_policy": policy,
            "test_execution_runs": policy.limits["max_runs_per_run"],
            "run_id": "a" * 32,
            "begin_test_execution": Mock(),
            "record_test_execution": Mock(),
        }
        with patch("agentkit.backends.run_isolated_tests") as runner:
            with self.assertRaisesRegex(ContractError, "count limit"):
                backend._run_tool("run_isolated_tests", {}, context, 5)
        self.assertFalse(runner.called)

    def test_test_policy_denies_legacy_workspace_pytest(self):
        policy = self.policy()
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"run_pytest"})
        backend._chat = Mock(return_value={
            "tool_calls": [{"id": "call-1", "function": {
                "name": "run_pytest", "arguments": '{"path":"tests/test_ok.py"}',
            }}],
        })
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "test_execution_policy": policy,
        }
        with patch.object(backend, "_run_tool") as run_tool:
            with self.assertRaisesRegex(ContractError, "forbids direct workspace pytest"):
                backend._call("fixture", "report", context, 5)
        self.assertFalse(run_tool.called)

    def test_autonomous_test_policy_does_not_authorize_unlisted_writes(self):
        backend = DeepSeekBackend(api_key="fixture", allowed_tools={"write_file"})
        context = {
            "workspace": str(self.workspace), "test_execution_policy": self.policy(),
            "require_approvals": False,
        }
        with self.assertRaisesRegex(ContractError, "require a host write policy"):
            backend._authorize_action("write_file", {
                "path": "src/app.py", "content": "unsafe",
            }, context)


if __name__ == "__main__":
    unittest.main()
