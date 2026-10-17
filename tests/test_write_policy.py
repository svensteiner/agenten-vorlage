import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agentkit.approvals import action_digest, replay_action_digest
from agentkit.backends import CodexBackend, DeepSeekBackend, DemoBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.scaffold import create
from agentkit.write_policy import WritePolicy


class WritePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_policy_is_immutable_and_digest_is_order_independent(self):
        source = ["src/main.py", "tests/test_main.py"]
        first = WritePolicy(source)
        second = WritePolicy(["tests/test_main.py", "src/main.py"])
        source.append("README.md")

        self.assertEqual(("src/main.py", "tests/test_main.py"), first.paths)
        self.assertEqual(first.sha256, second.sha256)
        with self.assertRaises((AttributeError, TypeError)):
            first.paths += ("README.md",)

    def test_rejects_noncanonical_or_internal_policy_paths(self):
        for path in (
            "../outside.py", "src/../outside.py", "./main.py", "src//main.py",
            "C:/outside.py", "\\\\server\\share\\file.py", "src\\main.py",
            ".runs/state.json", ".git/config", "src/CON.txt", "src/name.",
        ):
            with self.subTest(path=path), self.assertRaises(ContractError):
                WritePolicy([path])

    def test_rejects_case_aliases_in_policy_and_action_paths(self):
        with self.assertRaises(ContractError):
            WritePolicy(["src/Main.py", "src/main.py"])
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "Allowed.py").write_text("existing", encoding="utf-8")
        policy = WritePolicy(["src/Allowed.py"])

        with self.assertRaises(ContractError):
            policy.authorize(self.workspace, "src/allowed.py")

    def test_exact_file_policy_rejects_before_creating_forbidden_target(self):
        policy = WritePolicy(["src/allowed.py"])
        allowed = policy.authorize(self.workspace, "src/allowed.py")
        self.assertEqual("allowed.py", allowed.name)
        self.assertEqual("src", allowed.parent.name)
        with self.assertRaises(ContractError):
            policy.authorize(self.workspace, "src/forbidden.py")
        self.assertFalse((self.workspace / "src").exists())

    def test_rejects_linked_parent_even_when_target_name_is_allowed(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.workspace / "src"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        policy = WritePolicy(["src/allowed.py"])

        with self.assertRaises(ContractError):
            policy.authorize(self.workspace, "src/allowed.py")
        self.assertFalse((outside / "allowed.py").exists())

    def test_final_mutation_boundary_rechecks_target(self):
        policy = WritePolicy(["allowed.txt"])
        context = {"workspace": str(self.workspace), "write_policy": policy}
        forbidden = self.workspace / "other.txt"

        with self.assertRaises(ContractError):
            DeepSeekBackend._write_mutation(context, forbidden, b"blocked")
        self.assertFalse(forbidden.exists())

    def test_shared_inode_target_is_rejected_before_mutation(self):
        external = self.root / "protected.txt"
        external.write_text("protected", encoding="utf-8")
        linked = self.workspace / "allowed.txt"
        try:
            os.link(external, linked)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard links are unavailable: {exc}")
        context = {
            "workspace": str(self.workspace), "write_policy": WritePolicy(["allowed.txt"]),
        }

        with self.assertRaisesRegex(ContractError, "hard-link"):
            DeepSeekBackend._write_mutation(context, linked, b"replacement")
        self.assertEqual("protected", external.read_text(encoding="utf-8"))

    def test_deepseek_denies_unlisted_write_before_mutation(self):
        backend = DeepSeekBackend(api_key="fixture")
        context = {
            "workspace": str(self.workspace),
            "sandbox": "workspace-write",
            "write_policy": WritePolicy(["allowed.txt"]),
        }

        with self.assertRaises(ContractError):
            backend._run_tool(
                "write_file", {"path": "denied.txt", "content": "blocked"}, context, 5
            )
        self.assertFalse((self.workspace / "denied.txt").exists())

    def test_deepseek_executes_exact_allowed_write(self):
        backend = DeepSeekBackend(api_key="fixture")
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "write_policy": WritePolicy(["allowed.txt"]),
        }

        result = backend._run_tool(
            "write_file", {"path": "allowed.txt", "content": "allowed"}, context, 5
        )
        self.assertIn('"written"', result)
        self.assertEqual("allowed", (self.workspace / "allowed.txt").read_text(encoding="utf-8"))

    def test_deepseek_denies_before_requesting_human_approval(self):
        backend = DeepSeekBackend(api_key="fixture")
        callback = Mock(side_effect=AssertionError("must not request approval"))
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "require_approvals": True, "write_policy": WritePolicy(["allowed.txt"]),
            "request_approval": callback,
        }
        call = {"id": "w", "function": {
            "name": "write_file", "arguments": {"path": "denied.txt", "content": "blocked"}
        }}
        with patch.object(backend, "_chat", return_value={"tool_calls": [call]}):
            with self.assertRaises(ContractError):
                backend._call("task", "report", context, 5)
        callback.assert_not_called()
        self.assertFalse((self.workspace / "denied.txt").exists())

    def test_deepseek_resumed_batch_checks_each_sibling_before_approval(self):
        backend = DeepSeekBackend(api_key="fixture")
        first = {"path": "allowed.txt", "content": "allowed"}
        continuation = {
            "messages": [{"role": "user", "content": "task"}], "tool_count": 0,
            "call": {"name": "write_file", "arguments": first, "call_id": "first"},
            "remaining_calls": [{"id": "second", "function": {
                "name": "write_file", "arguments": {"path": "denied.txt", "content": "blocked"}
            }}],
        }
        callback = Mock(side_effect=AssertionError("denied sibling must not reach approval"))
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "require_approvals": True, "write_policy": WritePolicy(["allowed.txt"]),
            "approval_resume": continuation,
            "approved_action": {
                "tool": "write_file", "arguments": first,
                "action_sha256": action_digest("write_file", first),
                "replay_sha256": replay_action_digest("write_file", first, self.workspace),
            },
            "request_approval": callback,
        }

        with self.assertRaises(ContractError):
            backend._call("task", "report", context, 5)
        callback.assert_not_called()
        self.assertEqual("allowed", (self.workspace / "allowed.txt").read_text(encoding="utf-8"))
        self.assertFalse((self.workspace / "denied.txt").exists())

    def test_policy_mode_disables_project_execution_tools(self):
        backend = DeepSeekBackend(api_key="fixture")
        context = {
            "workspace": str(self.workspace),
            "sandbox": "workspace-write",
            "write_policy": WritePolicy(["tests/test_ok.py"]),
        }

        with self.assertRaisesRegex(ContractError, "disabled"):
            backend._run_tool("run_pytest", {"path": "tests/test_ok.py"}, context, 5)

    def test_engine_rejects_backend_without_explicit_policy_capability(self):
        class UnknownBackend:
            name = "unknown"

            def decide(self, context, timeout):
                raise AssertionError("must reject before dispatch")

            def execute(self, decision, context, timeout):
                raise AssertionError("must reject before dispatch")

        agent = create(self.root / "agent", "developer", "agent", "company")
        with self.assertRaisesRegex(ContractError, "write policy"):
            Engine(agent, agent / "workspace", UnknownBackend(), write_policy=WritePolicy(["x.py"]))

    def test_engine_rejects_policy_subclasses_that_could_override_authorization(self):
        class PermissivePolicy(WritePolicy):
            def authorize_action(self, workspace, tool, arguments):
                return workspace / arguments["path"]

        agent = create(self.root / "agent", "developer", "agent", "company")
        with self.assertRaisesRegex(ContractError, "host-created WritePolicy"):
            Engine(
                agent, agent / "workspace", DemoBackend(),
                write_policy=PermissivePolicy(["allowed.txt"]),
            )

    def test_policy_digest_is_sticky_on_resume(self):
        agent = create(self.root / "agent", "developer", "agent", "company")
        workspace = agent / "workspace"
        policy = WritePolicy(["demo-result.md"])
        state = Engine(agent, workspace, DemoBackend(), write_policy=policy).run("demo")
        self.assertEqual("completed", state["status"])
        self.assertEqual(policy.sha256, state["write_policy_sha256"])

        with self.assertRaisesRegex(ContractError, "write policy"):
            Engine(
                agent, workspace, DemoBackend(), write_policy=WritePolicy(["other.txt"])
            ).run("", run_dir=agent / ".runs" / state["run_id"], feedback="resume")

    def test_pending_approval_binds_policy_and_preserves_operator_gate(self):
        agent = create(self.root / "agent", "developer", "agent", "company")
        workspace = agent / "workspace"
        policy = WritePolicy(["demo-result.md"])
        engine = Engine(
            agent, workspace, DemoBackend(), require_approvals=True, write_policy=policy
        )
        state = engine.run("demo")
        run_dir = agent / ".runs" / state["run_id"]
        pending = state["pending_approval"]
        self.assertEqual(policy.sha256, pending["binding"]["write_policy_sha256"])

        with self.assertRaisesRegex(ContractError, "write policy"):
            Engine(
                agent, workspace, DemoBackend(),
                write_policy=WritePolicy(["other.txt"]),
            ).run("", run_dir=run_dir, approval_id=pending["id"], approval_decision="approve")
        self.assertFalse((workspace / "demo-result.md").exists())

        resumed = Engine(
            agent, workspace, DemoBackend(), write_policy=policy
        ).run("", run_dir=run_dir, approval_id=pending["id"], approval_decision="approve")
        self.assertEqual("awaiting_approval", resumed["status"])
        self.assertTrue((workspace / "demo-result.md").is_file())

    def test_human_approval_still_required_for_allowed_policy_action(self):
        agent = create(self.root / "agent", "developer", "agent", "company")
        workspace = agent / "workspace"
        policy = WritePolicy(["demo-result.md"])
        state = Engine(
            agent, workspace, DemoBackend(), require_approvals=True, write_policy=policy
        ).run("demo")

        self.assertEqual("awaiting_approval", state["status"])
        self.assertFalse((workspace / "demo-result.md").exists())
        self.assertEqual(policy.sha256, state["write_policy_sha256"])

    def test_codex_policy_mode_uses_read_only_proposal_and_host_execution(self):
        codex_home = self.root / "codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text(
            '[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
        )
        with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}, clear=False), \
             patch("agentkit.backends.codex_command", return_value=["codex-fixture"]):
            backend = CodexBackend()
        policy = WritePolicy(["allowed.txt"])
        decision = {
            "action": "delegate", "role": "developer", "skills": [],
            "task": "write allowed file", "reason": "fixture",
        }
        proposal = {
            "kind": "proposal", "tool": "write_file",
            "arguments": {"path": "allowed.txt", "content": "approved by policy", "old_text": "", "new_text": ""},
            "rationale": "fixture", "report": {
                "status": "blocked", "summary": "proposal", "artifacts": [],
                "evidence": [], "next_actions": [],
            },
        }
        final = {
            "kind": "final", "tool": "none",
            "arguments": {"path": "", "content": "", "old_text": "", "new_text": ""},
            "rationale": "done", "report": {
                "status": "success", "summary": "written", "artifacts": ["allowed.txt"],
                "evidence": ["host wrote the allowed file"], "next_actions": [],
            },
        }
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "require_review": False, "review_pending": False,
            "require_approvals": False, "history": [], "steps_remaining": 2,
            "completed_actions": [], "write_policy": policy,
        }
        with patch.object(CodexBackend, "_call", side_effect=[proposal, final]) as call:
            result = backend.execute(decision, context, 5)

        self.assertEqual("success", result["status"])
        self.assertEqual("approved by policy", (self.workspace / "allowed.txt").read_text())
        self.assertEqual("read-only", call.call_args_list[0].args[2]["sandbox"])

    def test_codex_policy_never_approves_forbidden_proposal(self):
        codex_home = self.root / "codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text(
            '[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
        )
        with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}, clear=False), \
             patch("agentkit.backends.codex_command", return_value=["codex-fixture"]):
            backend = CodexBackend()
        decision = {
            "action": "delegate", "role": "developer", "skills": [],
            "task": "write forbidden file", "reason": "fixture",
        }
        proposal = {
            "kind": "proposal", "tool": "write_file",
            "arguments": {"path": "denied.txt", "content": "blocked", "old_text": "", "new_text": ""},
            "rationale": "fixture", "report": {
                "status": "blocked", "summary": "proposal", "artifacts": [],
                "evidence": [], "next_actions": [],
            },
        }
        context = {
            "workspace": str(self.workspace), "sandbox": "workspace-write",
            "require_approvals": True, "history": [], "steps_remaining": 2,
            "completed_actions": [], "write_policy": WritePolicy(["allowed.txt"]),
            "request_approval": lambda *args: self.fail("forbidden proposal reached approval"),
        }
        with patch.object(CodexBackend, "_call", return_value=proposal):
            with self.assertRaises(ContractError):
                backend.execute(decision, context, 5)
        self.assertFalse((self.workspace / "denied.txt").exists())


if __name__ == "__main__":
    unittest.main()
