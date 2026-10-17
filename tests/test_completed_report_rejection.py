from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.backends import CodexBackend
from agentkit.contracts import CompletedReportRejected, ContractError
from agentkit.engine import Engine
from agentkit.scaffold import create
from agentkit.write_policy import WritePolicy


def delegate(role="developer"):
    return {"action": "delegate", "role": role, "skills": [],
            "task": "Inspect and report", "reason": "Fixture"}


def finish():
    return {"action": "finish", "role": "", "skills": [],
            "task": "Finish", "reason": "Fixture"}


def valid_report(status="success"):
    return {"status": status, "summary": "Observed result", "artifacts": [],
            "evidence": ["Observed fixture"], "next_actions": []}


class SequenceBackend:
    name = "codex"
    supports_action_approvals = True
    supports_write_policy = True

    def __init__(self, decisions, outcomes):
        self.decisions = iter(decisions)
        self.outcomes = iter(outcomes)
        self.contexts = []
        self.execute_calls = 0

    def decide(self, context, timeout):
        self.contexts.append(context)
        return next(self.decisions)

    def execute(self, decision, context, timeout):
        self.execute_calls += 1
        outcome = next(self.outcomes)
        if callable(outcome):
            return outcome(context)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class CompletedReportRejectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agent", "developer", "agent", "company")
        self.workspace = self.agent / "workspace"
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text(
            '[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
        )
        self.codex_env = patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        self.codex_env.start()

    def tearDown(self):
        self.codex_env.stop()
        self.temp.cleanup()

    def test_codex_normal_return_with_invalid_schema_is_typed_and_redacted(self):
        secret = "private-model-report-3db3e8"
        malformed = {**valid_report(), "unexpected": secret}
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        with patch.object(backend, "_call", return_value=malformed) as call:
            with self.assertRaises(CompletedReportRejected) as caught:
                backend.execute(delegate(), {"workspace": str(self.workspace),
                                             "sandbox": "read-only"}, 10)
        self.assertEqual(1, call.call_count)
        self.assertEqual("report_schema_invalid", caught.exception.reason)
        self.assertNotIn(secret, json.dumps(caught.exception.observation))

    def test_codex_normal_return_with_unsafe_artifact_path_is_typed(self):
        report = {**valid_report(), "artifacts": [".runs/state.json"]}
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        with patch.object(backend, "_call", return_value=report) as call:
            with self.assertRaises(CompletedReportRejected) as caught:
                backend.execute(delegate(), {"workspace": str(self.workspace),
                                             "sandbox": "read-only"}, 10)
        self.assertEqual(1, call.call_count)
        self.assertEqual("artifact_path_invalid", caught.exception.reason)
        self.assertEqual(0, caught.exception.observation["artifact_index"])
        self.assertNotIn(".runs/state.json", json.dumps(caught.exception.observation))

    def test_codex_valid_report_is_returned_unchanged(self):
        report = valid_report()
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        with patch.object(backend, "_call", return_value=report) as call:
            returned = backend.execute(delegate(), {"workspace": str(self.workspace),
                                                    "sandbox": "read-only"}, 10)
        self.assertIs(report, returned)
        self.assertEqual(1, call.call_count)

    def test_approval_gated_final_report_uses_typed_validation_after_envelope(self):
        response = {
            "kind": "final", "tool": "none",
            "arguments": {"path": "", "content": "", "old_text": "",
                          "new_text": "", "start_line": None, "max_lines": None},
            "rationale": "Done", "report": {**valid_report(), "extra": "secret"},
        }
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": True, "completed_actions": []}
        with patch.object(backend, "_call", return_value=response) as call:
            with self.assertRaises(CompletedReportRejected):
                backend.execute(delegate(), context, 10)
        self.assertEqual(1, call.call_count)

    def test_invalid_gated_action_envelope_is_not_typed_report_rejection(self):
        response = {
            "kind": "final", "tool": "write_file",
            "arguments": {"path": "", "content": "", "old_text": "",
                          "new_text": "", "start_line": None, "max_lines": None},
            "rationale": "Bad envelope", "report": valid_report(),
        }
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": True, "completed_actions": []}
        with patch.object(backend, "_call", return_value=response):
            with self.assertRaises(ContractError) as caught:
                backend.execute(delegate(), context, 10)
        self.assertNotIsInstance(caught.exception, CompletedReportRejected)

    def test_missing_gated_report_is_typed_instead_of_unknown_keyerror(self):
        response = {
            "kind": "final", "tool": "none",
            "arguments": {"path": "", "content": "", "old_text": "",
                          "new_text": "", "start_line": None, "max_lines": None},
            "rationale": "Missing report",
        }
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": True, "completed_actions": []}
        with patch.object(backend, "_call", return_value=response) as call:
            with self.assertRaises(CompletedReportRejected) as caught:
                backend.execute(delegate(), context, 10)
        self.assertEqual(1, call.call_count)
        self.assertEqual("report_schema_invalid", caught.exception.reason)

    def test_backend_exception_remains_unknown_and_is_not_typed(self):
        marker = ContractError("untrusted backend boundary")
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            backend = CodexBackend()
        with patch.object(backend, "_call", side_effect=marker):
            with self.assertRaises(ContractError) as caught:
                backend.execute(delegate(), {"workspace": str(self.workspace),
                                             "sandbox": "read-only"}, 10)
        self.assertIs(marker, caught.exception)
        self.assertNotIsInstance(caught.exception, CompletedReportRejected)

    def test_engine_backend_exception_preserves_worker_in_flight(self):
        backend = SequenceBackend([delegate()], [RuntimeError("transport outcome unknown")])
        state = Engine(self.agent, self.workspace, backend).run("Inspect")
        self.assertEqual("blocked", state["status"])
        self.assertEqual("worker", state["in_flight"]["kind"])

    def test_generic_backend_invalid_artifact_keeps_legacy_unknown_handling(self):
        malformed = {**valid_report(), "artifacts": ["missing.txt"]}
        backend = SequenceBackend([delegate()], [malformed])
        state = Engine(self.agent, self.workspace, backend).run("Inspect")
        self.assertEqual("blocked", state["status"])
        self.assertEqual("worker", state["in_flight"]["kind"])
        self.assertNotIn("worker_return", state["history"][0])

    def test_rejection_observation_is_bounded_allowlisted_metadata(self):
        secret = "untrusted-private-report-value" * 1000
        rejection = CompletedReportRejected("report_schema_invalid", {
            "report_type": "object", "report_sha256": "A" * 64,
            "report_bytes": 200_001, "artifact_count": 10_000,
            "artifact_index": 99, "raw_report": secret,
        })
        encoded = json.dumps(rejection.safe_observation())
        self.assertLess(len(encoded.encode("utf-8")), 1_000)
        self.assertNotIn(secret, encoded)
        self.assertNotIn("raw_report", encoded)
        self.assertIsNone(rejection.observation["report_sha256"])
        self.assertIsNone(rejection.observation["report_bytes"])
        self.assertNotIn("artifact_index", rejection.observation)

    def test_engine_rejects_returned_bad_report_then_replans_without_reexecute(self):
        secret = "must-not-reach-planner-7da040"
        backend = SequenceBackend(
            [delegate(), finish(), {"action": "blocked", "role": "", "skills": [],
                                    "task": "Stop", "reason": "Fixture"}],
            [CompletedReportRejected("report_schema_invalid", {
                "report_type": "object", "report_sha256": "a" * 64,
                "report_bytes": 128, "artifact_count": 0,
            })],
        )
        state = Engine(self.agent, self.workspace, backend).run("Inspect")
        self.assertEqual("blocked", state["status"])
        self.assertEqual(1, backend.execute_calls)
        self.assertIsNone(state["in_flight"])
        self.assertEqual(2, state["failures"])
        worker = state["history"][0]
        self.assertNotIn("report", worker)
        self.assertEqual("report_schema_invalid", worker["worker_return"]["reason"])
        self.assertNotIn(secret, json.dumps(backend.contexts[-1]))
        self.assertIn("worker_return", backend.contexts[-1]["history"][0])

    def test_finish_cannot_reuse_older_success_after_latest_bad_return(self):
        backend = SequenceBackend(
            [delegate(), delegate("reviewer"), finish(),
             {"action": "blocked", "role": "", "skills": [],
              "task": "Stop", "reason": "Fixture"}],
            [valid_report(), CompletedReportRejected("artifact_path_invalid", {
                "report_type": "object", "report_sha256": "b" * 64,
                "report_bytes": 96, "artifact_count": 1, "artifact_index": 0,
            })],
        )
        state = Engine(self.agent, self.workspace, backend).run("Inspect")
        self.assertEqual("blocked", state["status"])
        self.assertEqual(2, backend.execute_calls)
        self.assertEqual("success", state["history"][0]["report"]["status"])
        self.assertNotIn("report", state["history"][1])
        self.assertGreaterEqual(len(state["history"]), 3)
        self.assertIn("completion_rejected", state["history"][2])
        self.assertIsNone(state["in_flight"])

    def test_completed_actions_survive_report_rejection_and_approval_still_works(self):
        source = self.workspace / "src.py"
        source.write_text("before\n", encoding="utf-8")
        policy = WritePolicy(["src.py"])

        def write_then_reject(context):
            source.write_text("after\n", encoding="utf-8")
            context["record_completed_action"]({
                "kind": "completed_action", "tool": "write_file",
                "arguments": {"path": "src.py"}, "action_sha256": "c" * 64,
                "replay_sha256": "d" * 64,
                "post_workspace_fingerprint": __import__(
                    "agentkit.approvals", fromlist=["workspace_fingerprint"]
                ).workspace_fingerprint(self.workspace),
            })
            raise CompletedReportRejected("artifact_path_invalid", {
                "report_type": "object", "report_sha256": "e" * 64,
                "report_bytes": 120, "artifact_count": 1, "artifact_index": 0,
            })

        backend = SequenceBackend(
            [delegate(), {"action": "blocked", "role": "", "skills": [],
                          "task": "Stop", "reason": "Fixture"}],
            [write_then_reject],
        )
        state = Engine(self.agent, self.workspace, backend, write_policy=policy).run("Write")
        self.assertEqual("blocked", state["status"])
        self.assertEqual("after\n", source.read_text(encoding="utf-8"))
        self.assertEqual(1, len(state["completed_actions"]))
        self.assertEqual(1, len(state["write_provenance_receipts"]))
        self.assertEqual(1, state["run_write_provenance"]["write_receipt_count"])

    def test_approval_required_state_is_not_consumed_by_report_handling(self):
        def request_approval(context):
            return context["request_approval"](
                "write_file", {"path": "src.py", "content": "after"},
                {"kind": "codex-action", "tool": "write_file",
                 "arguments": {"path": "src.py", "content": "after"},
                 "action_history": []},
            )

        backend = SequenceBackend([delegate()], [request_approval])
        state = Engine(self.agent, self.workspace, backend, require_approvals=True).run("Write")
        self.assertEqual("awaiting_approval", state["status"])
        self.assertIsNotNone(state["pending_approval"])
        self.assertIsNone(state["in_flight"])
        self.assertEqual([], state["history"][0].get("worker_return", {}).get("reason", []))


if __name__ == "__main__":
    unittest.main()
