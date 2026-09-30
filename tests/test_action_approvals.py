import tempfile
import unittest
from unittest.mock import patch
import json
from pathlib import Path

from agentkit.backends import DemoBackend, DeepSeekBackend, CodexBackend
from agentkit.contracts import ContractError, read_json
from agentkit.approvals import ApprovalRequired
from agentkit.engine import Engine
from agentkit.scaffold import create


class ActionApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = create(Path(self.tmp.name) / "agent", "developer", "agent", "company")
        self.workspace = self.agent / "workspace"

    def tearDown(self):
        self.tmp.cleanup()

    def test_approve_exact_demo_writes_once_per_proposal(self):
        engine = Engine(self.agent, self.workspace, DemoBackend(), require_approvals=True)
        state = engine.run("demo")
        self.assertEqual("awaiting_approval", state["status"])
        self.assertIsNone(state["in_flight"])
        self.assertEqual("write_file", state["pending_approval"]["tool"])
        run_dir = self.agent / ".runs" / state["run_id"]
        for _ in range(2):
            approval = state["pending_approval"]["id"]
            state = Engine(self.agent, self.workspace, DemoBackend()).run(
                "", run_dir=run_dir, approval_id=approval, approval_decision="approve"
            )
        self.assertEqual("completed", state["status"])
        self.assertIn("ACCEPTED", (self.workspace / "demo-result.md").read_text())

    def test_reject_does_not_write_and_is_audited(self):
        state = Engine(self.agent, self.workspace, DemoBackend(), require_approvals=True).run("demo")
        run_dir = self.agent / ".runs" / state["run_id"]
        state = Engine(self.agent, self.workspace, DemoBackend()).run(
            "", run_dir=run_dir, approval_id=state["pending_approval"]["id"], approval_decision="reject"
        )
        self.assertEqual("blocked", state["status"])
        self.assertFalse((self.workspace / "demo-result.md").exists())
        self.assertEqual("reject", state["approvals"][0]["decision"])

    def test_stale_approval_after_workspace_change_is_rejected(self):
        state = Engine(self.agent, self.workspace, DemoBackend(), require_approvals=True).run("demo")
        (self.workspace / "outside.txt").write_text("changed")
        with self.assertRaises(ValueError):
            Engine(self.agent, self.workspace, DemoBackend()).run(
                "", run_dir=self.agent / ".runs" / state["run_id"],
                approval_id=state["pending_approval"]["id"], approval_decision="approve"
            )

    def test_deepseek_batch_checkpoint_has_read_once_and_exact_pending_writes(self):
        backend = DeepSeekBackend(api_key="fixture")
        calls = [
            {"id": "r", "function": {"name": "read_file", "arguments": {"path": "a.txt"}}},
            {"id": "w1", "function": {"name": "write_file", "arguments": {"path": "a.txt", "content": "one"}}},
            {"id": "w2", "function": {"name": "write_file", "arguments": {"path": "b.txt", "content": "two"}}},
        ]
        captured = {}
        def approve(name, arguments, continuation):
            captured.update(name=name, arguments=arguments, continuation=continuation)
            raise ApprovalRequired(captured)
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": True, "request_approval": approve}
        with patch.object(backend, "_chat", return_value={"tool_calls": calls}), patch.object(
            backend, "_run_tool", return_value="read-result"
        ) as run:
            with self.assertRaises(ApprovalRequired):
                backend._call("task", "report", context, 5)
        self.assertEqual(["read_file"], [c.args[0] for c in run.call_args_list])
        self.assertEqual("write_file", captured["name"])
        self.assertEqual("a.txt", captured["arguments"]["path"])
        self.assertEqual(1, len(captured["continuation"]["remaining_calls"]))

    def test_deepseek_resumed_siblings_cannot_bypass_tool_budget(self):
        backend = DeepSeekBackend(api_key="fixture")
        backend.max_tool_calls = 1
        continuation = {
            "messages": [{"role": "user", "content": "task"}], "tool_count": 0,
            "call": {"name": "write_file", "arguments": {"path": "a.txt", "content": "one"}, "call_id": "w1"},
            "remaining_calls": [{"id": "w2", "function": {"name": "write_file", "arguments": {"path": "b.txt", "content": "two"}}}],
        }
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": False, "approval_resume": continuation}
        with patch.object(backend, "_run_tool", return_value="ok") as run:
            with self.assertRaises(Exception):
                backend._call("task", "report", context, 5)
        self.assertEqual(1, run.call_count)

    def test_deepseek_unknown_tool_outcome_is_not_replayed_by_fixture(self):
        backend = DeepSeekBackend(api_key="fixture")
        continuation = {
            "messages": [{"role": "user", "content": "task"}], "tool_count": 0,
            "call": {"name": "write_file", "arguments": {"path": "a.txt", "content": "one"}, "call_id": "w1"},
            "remaining_calls": [],
        }
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write",
                   "require_approvals": False, "approval_resume": continuation}
        with patch.object(backend, "_run_tool", side_effect=RuntimeError("unknown")) as run:
            with self.assertRaises(RuntimeError):
                backend._call("task", "report", context, 5)
        self.assertEqual(1, run.call_count)

    def test_engine_deepseek_batch_resumes_exact_worker_without_planner_replay(self):
        backend = DeepSeekBackend(api_key="fixture")
        backend.max_tool_calls = 3
        (self.workspace / "source.txt").write_text("read me")
        decision = {"action": "delegate", "role": "developer", "skills": [], "task": "Write two files", "reason": "fixture"}
        stop = {"action": "blocked", "role": "", "skills": [], "task": "Fixture worker verified", "reason": "fixture"}
        calls = [{"id": key, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
                 for key, name, arguments in (
                     ("r", "read_file", {"path": "source.txt"}),
                     ("w1", "write_file", {"path": "one.txt", "content": "ONE"}),
                     ("w2", "write_file", {"path": "two.txt", "content": "TWO"}))]
        report = {"status": "success", "summary": "Two files written", "artifacts": ["one.txt", "two.txt"],
                  "evidence": ["Actual fixture writes"], "next_actions": []}
        with patch.object(backend, "decide", side_effect=[decision, stop]) as planner, \
             patch.object(backend, "_chat", side_effect=[{"role": "assistant", "tool_calls": calls}, {"content": json.dumps(report)}]) as chat, \
             patch.object(backend, "_run_tool", wraps=backend._run_tool) as tool:
            state = Engine(self.agent, self.workspace, backend, require_approvals=True).run("Fixture batch")
            self.assertEqual("awaiting_approval", state["status"], state["summary"])
            run_dir = self.agent / ".runs" / state["run_id"]
            for expected_path in ("one.txt", "two.txt"):
                self.assertEqual(expected_path, state["pending_approval"]["arguments"]["path"])
                self.assertEqual(1, planner.call_count)
                state = Engine(self.agent, self.workspace, backend).run(
                    "", run_dir=run_dir, approval_id=state["pending_approval"]["id"], approval_decision="approve")
            self.assertEqual("blocked", state["status"])
            self.assertEqual("Fixture worker verified", state["summary"])
            self.assertEqual(["read_file", "write_file", "write_file"], [call.args[0] for call in tool.call_args_list])
            self.assertEqual(2, planner.call_count)
            self.assertEqual(2, chat.call_count)
            self.assertEqual("ONE", (self.workspace / "one.txt").read_text())
            self.assertEqual("TWO", (self.workspace / "two.txt").read_text())

    def test_unknown_outcome_requires_acknowledgment_and_never_replays_continuation(self):
        backend = DeepSeekBackend(api_key="fixture")
        decision = {"action": "delegate", "role": "developer", "skills": [], "task": "Write", "reason": "fixture"}
        stop = {"action": "blocked", "role": "", "skills": [], "task": "Inspect unknown outcome", "reason": "fixture"}
        call = {"id": "w", "type": "function", "function": {"name": "write_file", "arguments": '{"path":"one.txt","content":"ONE"}'}}
        def uncertain(*args):
            (self.workspace / "one.txt").write_text("ONE")
            raise RuntimeError("Lost result after write")
        with patch.object(backend, "decide", side_effect=[decision, stop]) as planner, \
             patch.object(backend, "_chat", return_value={"role": "assistant", "tool_calls": [call]}), \
             patch.object(backend, "_run_tool", side_effect=uncertain) as tool:
            state = Engine(self.agent, self.workspace, backend, require_approvals=True).run("Unknown fixture")
            run_dir = self.agent / ".runs" / state["run_id"]
            state = Engine(self.agent, self.workspace, backend).run(
                "", run_dir=run_dir, approval_id=state["pending_approval"]["id"], approval_decision="approve")
            self.assertEqual("blocked", state["status"])
            self.assertTrue(state["in_flight"])
            self.assertNotIn("approval_resume", read_json(run_dir / "state.json"))
            with self.assertRaises(ContractError):
                Engine(self.agent, self.workspace, backend).run(
                    "", run_dir=run_dir, approval_id="a" * 32, approval_decision="approve", acknowledge_interruption=True)
            with self.assertRaises(ContractError):
                Engine(self.agent, self.workspace, backend).run("", run_dir=run_dir, feedback="Inspect")
            resumed = Engine(self.agent, self.workspace, backend).run(
                "", run_dir=run_dir, feedback="File inspected; do not rewrite", acknowledge_interruption=True)
            self.assertEqual("Inspect unknown outcome", resumed["summary"])
            self.assertEqual(1, tool.call_count)
            self.assertEqual(2, planner.call_count)

    def test_codex_rejects_unsupported_tool_approval_policy(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            with self.assertRaises(ContractError):
                Engine(self.agent, self.workspace, CodexBackend(), require_approvals=True)

    def test_new_run_cannot_consume_an_approval_response(self):
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, DemoBackend()).run(
                "New task", approval_id="a" * 32, approval_decision="approve")


if __name__ == "__main__":
    unittest.main()
