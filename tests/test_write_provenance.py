from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentkit.approvals import action_digest, replay_action_digest
from agentkit.backends import CodexBackend, DeepSeekBackend
from agentkit.api_backend import ApiBackend
from agentkit.anthropic_backend import AnthropicBackend
from agentkit.ollama_backend import OllamaBackend
from agentkit.write_policy import WritePolicy
from agentkit.write_provenance import (
    capture_baseline,
    make_write_receipt,
    summarize_run_writes,
    unknown_baseline,
    validate_baseline,
)


class WriteProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        (self.workspace / "src").mkdir()
        self.target = self.workspace / "src" / "app.py"
        self.target.write_text("pre-existing working tree content\n", encoding="utf-8")
        self.policy = WritePolicy(["src/app.py"])

    def tearDown(self):
        self.temp.cleanup()

    def test_test_only_run_does_not_attribute_preexisting_file_to_run(self):
        baseline = capture_baseline(self.workspace, self.policy)
        current = summarize_run_writes(self.workspace, self.policy, baseline, [])

        self.assertEqual("complete", current["status"])
        self.assertEqual([], current["changed_by_run"])
        self.assertEqual([], current["changed_without_matching_receipt"])
        self.assertEqual([], current["unknown_paths"])
        self.assertEqual(0, current["write_receipt_count"])

    def test_host_write_receipt_attributes_only_current_net_change(self):
        baseline = capture_baseline(self.workspace, self.policy)
        self.target.write_text("changed by the host action\n", encoding="utf-8")
        receipt = make_write_receipt(
            self.workspace, self.policy,
            {"tool": "write_file", "arguments": {"path": "src/app.py"},
             "action_sha256": "a" * 64},
        )

        current = summarize_run_writes(self.workspace, self.policy, baseline, [receipt])

        self.assertEqual(["src/app.py"], current["changed_by_run"])
        self.assertEqual([], current["changed_without_matching_receipt"])
        self.assertEqual(1, current["write_receipt_count"])

    def test_changed_file_without_matching_host_receipt_is_not_credited(self):
        baseline = capture_baseline(self.workspace, self.policy)
        self.target.write_text("changed outside a recorded host action\n", encoding="utf-8")

        current = summarize_run_writes(self.workspace, self.policy, baseline, [])

        self.assertEqual([], current["changed_by_run"])
        self.assertEqual(["src/app.py"], current["changed_without_matching_receipt"])

    def test_reverting_to_start_digest_removes_net_change_attribution(self):
        original = self.target.read_text(encoding="utf-8")
        baseline = capture_baseline(self.workspace, self.policy)
        self.target.write_text("temporary host edit\n", encoding="utf-8")
        receipt = make_write_receipt(
            self.workspace, self.policy,
            {"tool": "edit_file", "arguments": {"path": "src/app.py"},
             "action_sha256": "b" * 64},
        )
        self.target.write_text(original, encoding="utf-8")

        current = summarize_run_writes(self.workspace, self.policy, baseline, [receipt])

        self.assertEqual([], current["changed_by_run"])
        self.assertEqual([], current["changed_without_matching_receipt"])

    def test_exact_baseline_restore_is_a_recorded_write_without_net_change_claim(self):
        original = self.target.read_bytes()
        baseline = capture_baseline(self.workspace, self.policy)
        self.target.write_bytes(b"temporary implementation change\n")
        self.target.write_bytes(original)
        receipt = make_write_receipt(
            self.workspace, self.policy,
            {"tool": "restore_production_baseline", "arguments": {"path": "src/app.py"},
             "action_sha256": "c" * 64},
        )

        current = summarize_run_writes(self.workspace, self.policy, baseline, [receipt])

        self.assertEqual(1, current["write_receipt_count"])
        self.assertEqual([], current["changed_by_run"])
        self.assertEqual([], current["changed_without_matching_receipt"])

    def test_legacy_resume_without_baseline_is_unknown_not_recaptured(self):
        baseline = unknown_baseline(self.policy)
        validate_baseline(baseline, self.policy)
        self.target.write_text("changed before resume\n", encoding="utf-8")

        current = summarize_run_writes(self.workspace, self.policy, baseline, [])

        self.assertEqual("unknown", current["status"])
        self.assertEqual([], current["changed_by_run"])
        self.assertEqual([], current["changed_without_matching_receipt"])
        self.assertEqual(["src/app.py"], current["unknown_paths"])

    def test_baseline_validation_rejects_path_aliases_and_policy_mismatch(self):
        baseline = capture_baseline(self.workspace, self.policy)
        forged = {**baseline, "files": [
            {"path": "src/../src/app.py", "state": "present",
             "sha256": hashlib.sha256(b"pre-existing working tree content\n").hexdigest()}
        ]}
        with self.assertRaises(ValueError):
            validate_baseline(forged, self.policy)
        with self.assertRaises(ValueError):
            validate_baseline(baseline, WritePolicy(["other.py"]))

    def test_aggregate_overflow_retains_per_path_unknown_states(self):
        paths = [f"src/file-{index}.py" for index in range(3)]
        for relative in paths:
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"x" * (1536 * 1024))
        policy = WritePolicy(paths)

        baseline = capture_baseline(self.workspace, policy)

        self.assertEqual("unknown", baseline["status"])
        self.assertEqual(paths, [entry["path"] for entry in baseline["files"]])
        self.assertTrue(all(entry["state"] == "unknown" for entry in baseline["files"]))
        validate_baseline(baseline, policy)
        summary = summarize_run_writes(self.workspace, policy, baseline, [])
        self.assertEqual("unknown", summary["status"])
        self.assertEqual(3, summary["unknown_path_count"])

    def test_unapproved_direct_write_records_host_completed_action(self):
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "write_policy": self.policy, "completed_actions": [], "run_id": "fixture-run",
            "task": "update file", "instructions": "", "require_approvals": False,
            "record_completed_action": Mock(),
        }
        backend = DeepSeekBackend.__new__(DeepSeekBackend)
        backend.api_key = "offline-fixture"
        backend.allowed_tools = DeepSeekBackend.supported_tools
        arguments = {"path": "src/app.py", "content": "new content\n"}
        backend._chat = Mock(side_effect=[
            {"tool_calls": [{"id": "call-1", "type": "function", "function": {
                "name": "write_file", "arguments": json.dumps(arguments),
            }}]},
            {"content": json.dumps({
                "status": "success", "summary": "Updated", "artifacts": [],
                "evidence": ["Host write was recorded"], "next_actions": [],
            })},
        ])

        result = backend._call("do the update", "report", context, 10.0)

        self.assertEqual("success", result["status"])
        self.assertEqual("new content\n", self.target.read_text(encoding="utf-8"))
        context["record_completed_action"].assert_called_once()
        completed = context["record_completed_action"].call_args.args[0]
        self.assertEqual("write_file", completed["tool"])
        self.assertEqual("src/app.py", completed["arguments"]["path"])

    def test_unapproved_resumed_sibling_write_records_host_completed_action(self):
        first_args = {"path": "src/app.py", "content": "first\n"}
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "write_policy": self.policy, "completed_actions": [], "run_id": "fixture-run",
            "task": "update file", "instructions": "", "require_approvals": False,
            "record_completed_action": Mock(),
            "approved_action": {"tool": "write_file", "arguments": first_args,
                                "action_sha256": action_digest("write_file", first_args),
                                "replay_sha256": replay_action_digest("write_file", first_args, self.workspace)},
            "approval_resume": {
                "messages": [{"role": "user", "content": "finish writes"}],
                "tool_count": 0,
                "call": {"name": "write_file", "arguments": first_args, "call_id": "first"},
                "remaining_calls": [{"id": "second", "function": {
                    "name": "write_file", "arguments": json.dumps({
                        "path": "src/app.py", "content": "second\n",
                    }),
                }}],
            },
        }
        backend = DeepSeekBackend.__new__(DeepSeekBackend)
        backend.api_key = "offline-fixture"
        backend.allowed_tools = DeepSeekBackend.supported_tools
        backend._chat = Mock(return_value={"content": json.dumps({
            "status": "success", "summary": "Updated", "artifacts": [],
            "evidence": ["Host writes were recorded"], "next_actions": [],
        })})

        result = backend._call("resume", "report", context, 10.0)

        self.assertEqual("success", result["status"])
        self.assertEqual("second\n", self.target.read_text(encoding="utf-8"))
        self.assertEqual(2, context["record_completed_action"].call_count)

    def test_planner_worker_and_reviewer_prompts_use_host_provenance(self):
        for backend_type in (CodexBackend, DeepSeekBackend, ApiBackend, AnthropicBackend, OllamaBackend):
            with self.subTest(backend=backend_type.__name__):
                captured = {}
                backend = backend_type.__new__(backend_type)
                def fake_call(prompt, contract, context, timeout):
                    captured.update(prompt=prompt, context=context)
                    if contract == "codex_action_step":
                        return {"kind": "final", "tool": "none",
                                "arguments": {"path": "", "content": "", "old_text": "",
                                              "new_text": "", "start_line": None, "max_lines": None},
                                "rationale": "No edit in prompt test.",
                                "report": {"status": "success", "summary": "Fixture",
                                           "artifacts": [], "evidence": ["Fixture"],
                                           "next_actions": []}}
                    if contract == "report":
                        return {"status": "success", "summary": "Fixture", "artifacts": [],
                                "evidence": ["Fixture"], "next_actions": []}
                    return {"action": "blocked", "role": "", "skills": [],
                            "task": "paused", "reason": "fixture"}
                backend._call = fake_call
                context = {"task": "Inspect", "history": [], "workspace": str(self.workspace),
                           "execution_budget": {"wall_seconds_remaining": 32.5,
                                                "call_timeout_seconds": 12.0,
                                                "steps_remaining": 3},
                           "run_write_provenance": {
                               "status": "complete", "baseline_status": "captured",
                               "changed_by_run": [], "changed_without_matching_receipt": [],
                               "unknown_paths": [], "unknown_path_count": 0,
                               "write_receipt_count": 0,
                           }}
                backend.decide(context, 1.0)
                self.assertIn("a passing test receipt alone does not prove source changed", captured["prompt"].lower())
                self.assertIn("one bounded, independently verifiable slice", captured["prompt"].lower())
                self.assertIn('"wall_seconds_remaining": 32.5', captured["prompt"])
                self.assertIn('"current_call_timeout_upper_bound_seconds": 1.0', captured["prompt"])
                for role in ("developer", "reviewer"):
                    worker_context = dict(context)
                    if backend_type is CodexBackend:
                        worker_context.update({"sandbox": "workspace-write", "write_policy": self.policy,
                                               "completed_actions": [], "run_id": "prompt-fixture"})
                        backend._execute_approval_gated(
                            {"action": "delegate", "role": role, "skills": [],
                             "task": "Work", "reason": "fixture"}, worker_context, 1.0
                        )
                    else:
                        backend.execute({"action": "delegate", "role": role, "skills": [],
                                         "task": "Work", "reason": "fixture"}, worker_context, 1.0)
                    self.assertIn("a passing test receipt alone does not prove source changed", captured["prompt"].lower())
                    self.assertIn("one bounded, independently verifiable slice", captured["prompt"].lower())
                    self.assertIn('"call_timeout_seconds": 12.0', captured["prompt"])
                    self.assertIn('"current_call_timeout_upper_bound_seconds": 1.0', captured["prompt"])

    def test_deepseek_tool_loop_refreshes_remaining_model_call_budget(self):
        clock = [10.0]
        observed = []
        context = {
            "workspace": str(self.workspace), "sandbox": "read-only",
            "completed_actions": [], "run_id": "fixture-run", "task": "inspect source",
            "instructions": "", "require_approvals": False,
        }
        backend = DeepSeekBackend.__new__(DeepSeekBackend)
        backend.api_key = "offline-fixture"
        backend.allowed_tools = DeepSeekBackend.supported_tools
        original_validate = backend._validate_messages

        def slow_validate(messages):
            result = original_validate(messages)
            if "[AgentKit invocation budget:" in messages[0].get("content", ""):
                clock[0] += 1.0
            return result

        backend._validate_messages = slow_validate
        backend._run_tool = Mock(return_value="fixture source observation")

        def chat(messages, timeout, tools=None):
            observed.append((messages[0]["content"], timeout))
            if len(observed) == 1:
                clock[0] += 2.0
                return {"tool_calls": [{"id": "read-1", "type": "function", "function": {
                    "name": "read_file", "arguments": json.dumps({"path": "src/app.py"}),
                }}]}
            return {"content": json.dumps({
                "status": "success", "summary": "Inspected", "artifacts": [],
                "evidence": ["Read the requested source"], "next_actions": [],
            })}

        backend._chat = chat
        with unittest.mock.patch("agentkit.backends.time.monotonic", side_effect=lambda: clock[0]):
            result = backend._call("inspect", "report", context, 10.0)

        self.assertEqual("success", result["status"])
        self.assertEqual(2, len(observed))
        self.assertIn("[AgentKit invocation budget: 10.000 seconds remain", observed[0][0])
        self.assertIn("[AgentKit invocation budget: 4.000 seconds remain", observed[1][0])
        self.assertEqual([9.0, 3.0], [entry[1] for entry in observed])

    def test_deepseek_report_repair_dispatch_deducts_validation_and_fails_if_expired(self):
        report = {"status": "success", "summary": "Observed", "artifacts": [],
                  "evidence": ["Fixture observation"], "next_actions": []}
        tool_call = {"id": "read-1", "type": "function", "function": {
            "name": "read_file", "arguments": json.dumps({"path": "src/app.py"}),
        }}

        for validation_delay, expected_repair_timeout in ((2.0, 8.0), (11.0, None)):
            with self.subTest(validation_delay=validation_delay):
                clock = [100.0]
                calls = []
                backend = DeepSeekBackend.__new__(DeepSeekBackend)
                backend.api_key = "offline-fixture"
                backend.allowed_tools = DeepSeekBackend.supported_tools
                backend.repair_structured_report = True
                backend.max_tool_calls = 4
                context = {"workspace": str(self.workspace), "sandbox": "read-only",
                           "completed_actions": [], "require_approvals": False}
                backend._run_tool = Mock(return_value="fixture observation")
                original_validate = backend._validate_messages

                def delayed_repair_validation(messages):
                    result = original_validate(messages)
                    if any("Current model-call budget:" in message.get("content", "")
                           for message in messages):
                        clock[0] += validation_delay
                    return result

                backend._validate_messages = delayed_repair_validation

                def chat(messages, timeout, tools=None):
                    calls.append((messages, timeout))
                    if len(calls) == 1:
                        return {"tool_calls": [tool_call]}
                    if len(calls) == 2:
                        return {"content": "not valid JSON"}
                    return {"content": json.dumps(report)}

                backend._chat = chat
                with unittest.mock.patch("agentkit.backends.time.monotonic", side_effect=lambda: clock[0]):
                    if expected_repair_timeout is None:
                        with self.assertRaisesRegex(RuntimeError, "during request preparation"):
                            backend._call("inspect", "report", context, 10.0)
                    else:
                        self.assertEqual(report, backend._call("inspect", "report", context, 10.0))

                self.assertEqual(2 if expected_repair_timeout is None else 3, len(calls))
                if expected_repair_timeout is not None:
                    self.assertEqual(expected_repair_timeout, calls[2][1])

    def test_codex_dispatch_deducts_prompt_preparation_from_worker_deadline(self):
        clock = [50.0]
        backend = CodexBackend.__new__(CodexBackend)
        backend._call = Mock(return_value={
            "kind": "final", "tool": "none",
            "arguments": {"path": "", "content": "", "old_text": "", "new_text": "",
                          "start_line": None, "max_lines": None},
            "rationale": "No action needed.",
            "report": {"status": "success", "summary": "Observed", "artifacts": [],
                       "evidence": ["Fixture evidence"], "next_actions": []},
        })
        context = {"workspace": str(self.workspace), "sandbox": "read-only",
                   "completed_actions": [], "task": "observe", "history": []}

        def slow_fingerprint(_workspace):
            clock[0] += 2.0
            return "f" * 64

        with patch("agentkit.backends.time.monotonic", side_effect=lambda: clock[0]), \
             patch("agentkit.backends.workspace_fingerprint", side_effect=slow_fingerprint):
            result = backend._execute_approval_gated(
                {"action": "delegate", "role": "developer", "skills": [],
                 "task": "bounded", "reason": "fixture"}, context, 10.0,
            )

        self.assertEqual("success", result["status"])
        self.assertEqual(8.0, backend._call.call_args.args[3])
        self.assertIn('"current_call_timeout_upper_bound_seconds": 10.0',
                      backend._call.call_args.args[0])

    def test_deepseek_dispatch_deducts_prompt_preparation_from_worker_deadline(self):
        clock = [50.0]
        backend = DeepSeekBackend.__new__(DeepSeekBackend)
        backend._call = Mock(return_value={
            "status": "success", "summary": "Observed", "artifacts": [],
            "evidence": ["Fixture evidence"], "next_actions": [],
        })

        def slow_context(context, **_kwargs):
            clock[0] += 2.0
            return context

        backend._provider_context = slow_context
        with patch("agentkit.backends.time.monotonic", side_effect=lambda: clock[0]):
            result = backend.execute(
                {"action": "delegate", "role": "researcher", "skills": [],
                 "task": "bounded", "reason": "fixture"},
                {"task": "observe", "history": [], "sandbox": "read-only"},
                10.0,
            )

        self.assertEqual("success", result["status"])
        self.assertEqual(8.0, backend._call.call_args.args[3])


if __name__ == "__main__":
    unittest.main()
