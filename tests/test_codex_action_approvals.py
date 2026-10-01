import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from agentkit.backends import CodexBackend, DeepSeekBackend
from agentkit.contracts import ContractError, read_json
from agentkit.engine import Engine
from agentkit.scaffold import create
from agentkit.storage import save


class CodexActionApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # CodexBackend validates the Windows sandbox configuration at
        # construction time.  Keep these fixture-only tests independent of
        # the developer/CI user's real ~/.codex directory while exercising
        # the production validation unchanged.
        self.codex_home = Path(self.tmp.name) / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text(
            '[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
        )
        self._codex_home = patch.dict(
            os.environ, {"CODEX_HOME": str(self.codex_home)}, clear=False
        )
        self._codex_home.start()
        self.agent = create(Path(self.tmp.name) / "agent", "developer", "agent", "company")
        self.workspace = self.agent / "workspace"

    def tearDown(self):
        self._codex_home.stop()
        self.tmp.cleanup()

    @staticmethod
    def decision(role="developer", task="perform bounded work"):
        return {"action": "delegate", "role": role, "skills": [], "task": task, "reason": "fixture"}

    @staticmethod
    def proposal(tool="write_file", path="result.txt", content="RESULT"):
        return {"kind": "proposal", "tool": tool,
                "arguments": {"path": path, "content": content, "old_text": "", "new_text": ""},
                "rationale": "bounded action",
                "report": {"status": "blocked", "summary": "Awaiting approval.", "artifacts": [],
                           "evidence": [], "next_actions": []}}

    @staticmethod
    def final(summary="verified", artifacts=None):
        return {"kind": "final", "tool": "none",
                "arguments": {"path": "", "content": "", "old_text": "", "new_text": ""},
                "rationale": "bounded work complete",
                "report": {"status": "success", "summary": summary, "artifacts": artifacts or [],
                           "evidence": ["fixture verified"], "next_actions": []}}

    @staticmethod
    def finish(task="done"):
        return {"action": "finish", "role": "", "skills": [], "task": task, "reason": "fixture"}

    def engine(self, backend=None):
        return Engine(self.agent, self.workspace, backend or CodexBackend(), require_approvals=True)

    def approve(self, state, decision="approve"):
        return self.engine().run("", run_dir=self.agent / ".runs" / state["run_id"],
                                 approval_id=state["pending_approval"]["id"], approval_decision=decision)

    def test_running_becomes_awaiting_before_any_codex_write(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal(path="created.txt", content="safe")]):
            state = self.engine().run("create file")
        self.assertEqual("awaiting_approval", state["status"])
        self.assertIsNone(state["in_flight"])
        self.assertFalse((self.workspace / "created.txt").exists())
        self.assertEqual("write_file", state["pending_approval"]["tool"])

    def test_fresh_engine_approval_executes_exact_write_once_and_next_test_needs_approval(self):
        (self.workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        responses = [self.decision(), self.proposal(path="created.txt", content="once"),
                     self.proposal("run_pytest", path="test_ok.py", content=""), self.final("all verified"),
                     self.decision("reviewer", "review changes"),
                     {"status": "success", "summary": "reviewed", "artifacts": [],
                      "evidence": ["reviewed"], "next_actions": []}, self.finish()]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses) as call:
            state = self.engine().run("write and test")
            first_approval = state["pending_approval"]["id"]
            state = self.approve(state)
            self.assertEqual("awaiting_approval", state["status"])
            self.assertEqual("run_pytest", state["pending_approval"]["tool"])
            self.assertEqual("once", (self.workspace / "created.txt").read_text())
            with self.assertRaises(ContractError):
                self.engine().run("", run_dir=self.agent / ".runs" / state["run_id"],
                                  approval_id=first_approval, approval_decision="approve")
            state = self.approve(state)
        self.assertEqual("completed", state["status"])
        self.assertEqual(2, len(state["approvals"]))
        self.assertEqual(7, call.call_count)

    def test_reject_has_zero_effects_and_audit_record(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal(path="no.txt")]):
            state = self.approve(self.engine().run("reject"), "reject")
        self.assertEqual("blocked", state["status"])
        self.assertFalse((self.workspace / "no.txt").exists())
        self.assertEqual("reject", state["approvals"][0]["decision"])

    def test_stale_duplicate_and_cross_run_approvals_are_rejected(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal()]):
            state = self.engine().run("stale")
        approval = state["pending_approval"]["id"]
        (self.workspace / "external.txt").write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.approve(state)
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal()]):
            other = self.engine().run("other")
        with self.assertRaises(ContractError):
            self.engine().run("", run_dir=self.agent / ".runs" / other["run_id"], approval_id=approval, approval_decision="approve")

    def test_unknown_outcome_after_real_write_requires_ack_feedback_and_never_replays(self):
        def write_then_lose(name, arguments, context, timeout):
            (self.workspace / arguments["path"]).write_text(arguments["content"], encoding="utf-8")
            raise RuntimeError("lost after write")
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal(),
                                                                {"action": "blocked", "role": "", "skills": [],
                                                                 "task": "inspect evidence", "reason": "fixture"}]), \
             patch("agentkit.backends.DeepSeekBackend._run_tool", side_effect=write_then_lose) as tool:
            state = self.approve(self.engine().run("uncertain"))
            run_dir = self.agent / ".runs" / state["run_id"]
            self.assertTrue(state["in_flight"])
            self.assertNotIn("approval_resume", read_json(run_dir / "state.json"))
            with self.assertRaises(ContractError):
                self.engine().run("", run_dir=run_dir, feedback="inspect")
            state = self.engine().run("", run_dir=run_dir, feedback="already written; inspect",
                                     acknowledge_interruption=True)
        self.assertEqual(1, tool.call_count)
        self.assertEqual("blocked", state["status"])

    def test_write_invalidates_review_until_subsequent_reviewer(self):
        reviewer = {"status": "success", "summary": "reviewed", "artifacts": [], "evidence": ["reviewed"], "next_actions": []}
        responses = [self.decision(), self.proposal(), self.final(artifacts=["result.txt"]),
                     self.decision("reviewer", "review changes"), reviewer,
                     {"action": "finish", "role": "", "skills": [], "task": "done", "reason": "fixture"}]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses):
            state = self.approve(self.engine().run("review me"))
        self.assertEqual("completed", state["status"])
        self.assertTrue(state["reviewed"])

    def test_invalid_paths_hidden_args_shell_paths_oversize_and_history_are_rejected(self):
        invalid = [([], {}),
                   ("write_file", {"path": "../escape", "content": "x"}),
                   ("write_file", {"path": ".runs/state", "content": "x"}),
                   ("write_file", {"path": ".git/config", "content": "x"}),
                   ("write_file", {"path": ".GIT/hooks/post-checkout", "content": "x"}),
                   ("write_file", {"path": "nested/__pycache__/x.pyc", "content": "x"}),
                   ("run_pytest", {"path": "tests;whoami"}),
                   ("write_file", {"path": "x", "content": "x", "old_text": "hidden"}),
                   ("write_file", {"path": "x", "content": "x" * 200001})]
        for tool, args in invalid:
            with self.subTest(tool=tool, args=list(args)), self.assertRaises(ContractError):
                CodexBackend._validate_action(tool, args)
        with patch("agentkit.backends.codex_command", return_value=["codex"]):
            with self.assertRaises(ContractError):
                CodexBackend()._execute_approval_gated(
                    self.decision(), {"workspace": str(self.workspace), "sandbox": "workspace-write",
                                      "approval_resume": {"kind": "codex-action", "tool": "write_file",
                                                          "arguments": {"path": "x", "content": "x"},
                                                          "action_history": [{}] * 48}}, 5)

    def test_tampered_visible_manifest_fails_closed_before_execution(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal()]):
            state = self.engine().run("tamper manifest")
        run_dir = self.agent / ".runs" / state["run_id"]
        persisted = read_json(run_dir / "state.json")
        persisted["pending_approval"]["arguments"]["content"] = "TAMPERED"
        save(run_dir / "state.json", persisted)
        with self.assertRaises(ContractError):
            self.engine().run("", run_dir=run_dir,
                              approval_id=state["pending_approval"]["id"], approval_decision="approve")
        self.assertFalse((self.workspace / "result.txt").exists())

    def test_tampered_continuation_cannot_execute_another_action(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), self.proposal()]):
            state = self.engine().run("tamper continuation")
        run_dir = self.agent / ".runs" / state["run_id"]
        persisted = read_json(run_dir / "state.json")
        persisted["pending_approval"]["continuation"]["arguments"] = {
            "path": "other.txt", "content": "OTHER"
        }
        save(run_dir / "state.json", persisted)
        with self.assertRaises(ContractError):
            self.engine().run("", run_dir=run_dir,
                              approval_id=state["pending_approval"]["id"], approval_decision="approve")
        self.assertFalse((self.workspace / "result.txt").exists())
        self.assertFalse((self.workspace / "other.txt").exists())

    def test_duplicate_model_proposal_is_corrected_without_second_approval_or_write(self):
        (self.workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        write = self.proposal(path="created.txt", content="once")
        responses = [self.decision(), write, write,
                     self.proposal("run_pytest", path="test_ok.py", content=""), self.final("verified"),
                     self.decision("reviewer", "review changes"),
                     {"status": "success", "summary": "reviewed", "artifacts": [],
                      "evidence": ["reviewed"], "next_actions": []}, self.finish()]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses), \
             patch("agentkit.backends.DeepSeekBackend._run_tool",
                   wraps=DeepSeekBackend._run_tool) as tool:
            state = self.engine().run("write once and test")
            state = self.approve(state)
            self.assertEqual("run_pytest", state["pending_approval"]["tool"])
            self.assertEqual(1, tool.call_count)
            write_calls = [call for call in tool.call_args_list if call.args[1] == "write_file"]
            self.assertEqual(1, len(write_calls))
            self.assertEqual("once", (self.workspace / "created.txt").read_text())
            state = self.approve(state)
        self.assertEqual("completed", state["status"])
        self.assertEqual(["write_file", "run_pytest"], [entry["tool"] for entry in state["approvals"]])

    def test_persistent_duplicate_proposals_exhaust_correction_budget_without_replay(self):
        write = self.proposal(path="created.txt", content="once")
        responses = [self.decision(), write, *([write] * (CodexBackend.max_proposal_corrections + 1))]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses), \
             patch("agentkit.backends.DeepSeekBackend._run_tool", wraps=DeepSeekBackend._run_tool) as tool:
            state = self.approve(self.engine().run("do not loop"))
        self.assertEqual("blocked", state["status"])
        self.assertIn("already completed", state["summary"])
        self.assertEqual(1, tool.call_count)
        self.assertEqual(1, len(state["approvals"]))
        self.assertEqual("once", (self.workspace / "created.txt").read_text())

    def test_invalid_semantic_proposal_is_corrected_before_any_approval(self):
        invalid = self.proposal("edit_file", path="created.txt", content="hidden")
        invalid["arguments"].update(old_text="", new_text="fixed")
        valid = self.proposal(path="created.txt", content="safe")
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=[self.decision(), invalid, valid]) as call:
            state = self.engine().run("correct invalid proposal")
        self.assertEqual("awaiting_approval", state["status"])
        self.assertEqual("write_file", state["pending_approval"]["tool"])
        self.assertEqual("safe", state["pending_approval"]["arguments"]["content"])
        self.assertFalse((self.workspace / "created.txt").exists())
        self.assertEqual(3, call.call_count)

    def test_persistent_invalid_semantic_proposals_exhaust_without_approval(self):
        invalid = self.proposal("edit_file", path="created.txt", content="hidden")
        invalid["arguments"].update(old_text="", new_text="fixed")
        responses = [self.decision(), *([invalid] * (CodexBackend.max_proposal_corrections + 1))]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses):
            state = self.engine().run("fail closed")
        self.assertEqual("blocked", state["status"])
        self.assertIn("invalid action proposals", state["summary"])
        self.assertEqual([], state["approvals"])
        self.assertIsNone(state["pending_approval"])
        self.assertFalse((self.workspace / "created.txt").exists())

    def test_same_pytest_action_is_allowed_after_observed_workspace_change(self):
        (self.workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        run_test = self.proposal("run_pytest", path="test_ok.py", content="")
        responses = [self.decision(), run_test,
                     self.proposal(path="change.txt", content="changed"), run_test]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses), \
             patch("agentkit.backends.DeepSeekBackend._run_tool", wraps=DeepSeekBackend._run_tool) as tool:
            state = self.engine().run("test, change, retest")
            state = self.approve(state)
            self.assertEqual("write_file", state["pending_approval"]["tool"])
            state = self.approve(state)
        self.assertEqual("awaiting_approval", state["status"])
        self.assertEqual("run_pytest", state["pending_approval"]["tool"])
        self.assertEqual(["run_pytest", "write_file"], [entry["tool"] for entry in state["approvals"]])
        self.assertEqual(2, tool.call_count)

    def test_completed_action_is_not_reproposed_by_a_later_worker_assignment(self):
        write = self.proposal(path="created.txt", content="once")
        repeated = self.proposal(
            path="CREATED.TXT" if os.name == "nt" else "created.txt",
            content="once",
        )
        review = {
            "status": "needs_revision", "summary": "request a different follow-up",
            "artifacts": [], "evidence": ["fixture review"], "next_actions": ["follow up"],
        }
        responses = [
            self.decision(), write, self.final("first worker complete", ["created.txt"]),
            self.decision("reviewer", "review first worker"), review,
            self.decision("developer", "perform follow-up"), repeated,
            self.proposal(path="different.txt", content="different"),
        ]
        with patch("agentkit.backends.codex_command", return_value=["codex"]), \
             patch.object(CodexBackend, "_call", side_effect=responses), \
             patch("agentkit.backends.DeepSeekBackend._run_tool",
                   wraps=DeepSeekBackend._run_tool) as tool:
            state = self.engine().run("persist replay protection across assignments")
            state = self.approve(state)
        self.assertEqual("awaiting_approval", state["status"])
        self.assertEqual("different.txt", state["pending_approval"]["arguments"]["path"])
        self.assertEqual(1, len(state["approvals"]))
        self.assertEqual(1, len(state["completed_actions"]))
        self.assertEqual(1, tool.call_count)
        self.assertEqual("once", (self.workspace / "created.txt").read_text())


if __name__ == "__main__":
    unittest.main()
