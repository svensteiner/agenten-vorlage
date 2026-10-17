import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

from agentkit import cli
from agentkit.scaffold import create
from agentkit.test_execution import TestExecutionPolicy


ROOT = Path(__file__).resolve().parents[1]


class AgentKitCliTests(unittest.TestCase):
    def test_cli_loads_operator_test_policy_and_passes_it_to_engine(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            agent = create(root / "agent", "developer", "agent", "company")
            manifest = root / "tests.json"
            manifest.write_text(json.dumps({
                "version": 1,
                "image_ref": "python@sha256:" + "c" * 64,
                "image_id": "sha256:" + "b" * 64,
                "dependency_lock_sha256": "a" * 64,
                "docker_transport": "native",
                "test_files": [{"path": "tests/test_ok.py", "sha256": "d" * 64}],
                "support_files": [],
                "expected_test_count": 1,
                "snapshot_paths": ["tests/test_ok.py"],
            }), encoding="utf-8")
            fixture_backend = SimpleNamespace(name="codex", model="test",
                                              supports_action_approvals=True)
            with patch.object(cli, "CodexBackend", return_value=fixture_backend), \
                 patch.object(cli, "Engine") as engine, redirect_stdout(StringIO()):
                engine.return_value.run.return_value = {"status": "blocked"}
                result = cli.main([
                    "run", "--agent", str(agent), "--backend", "codex", "--task", "fixture",
                    "--test-policy", str(manifest),
                ])
            self.assertEqual(2, result)
            policy = engine.call_args.kwargs["test_execution_policy"]
            self.assertIs(type(policy), TestExecutionPolicy)
            self.assertEqual(TestExecutionPolicy.from_file(manifest).sha256, policy.sha256)

    def test_demo_backend_rejects_isolated_test_policy_before_run(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            agent = create(root / "agent", "developer", "agent", "company")
            manifest = root / "tests.json"
            manifest.write_text(json.dumps({
                "version": 1,
                "image_ref": "python@sha256:" + "c" * 64,
                "image_id": "sha256:" + "b" * 64,
                "dependency_lock_sha256": "a" * 64,
                "docker_transport": "native",
                "test_files": [{"path": "tests/test_ok.py", "sha256": "d" * 64}],
                "support_files": [],
                "expected_test_count": 1,
                "snapshot_paths": ["tests/test_ok.py"],
            }), encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as error:
                code = cli.main([
                    "run", "--agent", str(agent), "--backend", "demo", "--task", "fixture",
                    "--test-policy", str(manifest),
                ])
            self.assertEqual(1, code)
            self.assertIn("isolated test execution", json.loads(error.getvalue())["summary"])

    def test_strict_autonomous_cli_completion_and_resume_bind_exact_file_list(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = self.init_agent(Path(temp_name), "strict-agent")
            result, completed = self.run_cli(
                "run", "--agent", agent, "--backend", "demo", "--task", "bounded demo",
                "--allow-write", "demo-result.md", "--autonomous-writes",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(completed["reviewed"])
            self.assertFalse(completed["require_approvals"])
            self.assertTrue(completed["write_policy_sha256"])
            run_dir = agent / ".runs" / completed["run_id"]
            artifact = agent / "workspace" / "demo-result.md"
            before = artifact.read_bytes()
            result, resumed = self.run_cli(
                "resume", "--agent", agent, "--backend", "demo", "--run-dir", run_dir,
                "--allow-write", "demo-result.md", "--autonomous-writes",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(completed["write_policy_sha256"], resumed["write_policy_sha256"])
            for policy_args in ([], ["--allow-write", "other.md"]):
                rejected = subprocess.run(
                    [sys.executable, "-m", "agentkit", "resume", "--agent", str(agent),
                     "--backend", "demo", "--run-dir", str(run_dir), *policy_args],
                    cwd=ROOT, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(1, rejected.returncode)
                self.assertIn("write policy", json.loads(rejected.stderr)["summary"])
            self.assertEqual(before, artifact.read_bytes())

    def test_cli_rejects_unbounded_autonomy_and_conflicting_modes_before_backend(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = create(Path(temp_name) / "agent", "developer", "agent", "company")
            for extra in (
                ["--autonomous-writes"],
                ["--allow-write", "allowed.py", "--autonomous-writes", "--require-approvals"],
                ["--allow-write", "../outside.py"],
            ):
                with self.subTest(extra=extra), patch.object(cli, "CodexBackend") as backend, \
                     redirect_stdout(StringIO()), redirect_stderr(StringIO()) as error:
                    code = cli.main(["run", "--agent", str(agent), "--backend", "codex",
                                     "--task", "bounded", *extra])
                    self.assertEqual(1, code)
                    self.assertEqual("error", json.loads(error.getvalue())["status"])
                    backend.assert_not_called()

    def test_cli_exact_allowlist_does_not_disable_approvals_unless_explicit(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = create(Path(temp_name) / "agent", "developer", "agent", "company")
            for autonomous in (False, True):
                with self.subTest(autonomous=autonomous), patch.object(cli, "CodexBackend"), \
                     patch.object(cli, "Engine") as engine, redirect_stdout(StringIO()):
                    engine.return_value.run.return_value = {"status": "blocked"}
                    code = cli.main(["run", "--agent", str(agent), "--backend", "codex",
                                     "--task", "bounded", "--allow-write", "src/a.py",
                                     "--allow-write", "src/b.py",
                                     *(["--autonomous-writes"] if autonomous else [])])
                    self.assertEqual(2, code)
                    self.assertEqual(not autonomous, engine.call_args.kwargs["require_approvals"])
                    self.assertEqual(("src/a.py", "src/b.py"),
                                     engine.call_args.kwargs["write_policy"].paths)

    def test_cli_autonomous_resume_cannot_remove_existing_approval_requirement(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = self.init_agent(Path(temp_name), "sticky-agent")
            result, paused = self.run_cli(
                "run", "--agent", agent, "--backend", "demo", "--task", "bounded demo",
                "--allow-write", "demo-result.md", "--require-approvals",
            )
            self.assertEqual(2, result.returncode, result.stderr)
            run_dir = agent / ".runs" / paused["run_id"]
            result, resumed = self.run_cli(
                "resume", "--agent", agent, "--backend", "demo", "--run-dir", run_dir,
                "--allow-write", "demo-result.md", "--autonomous-writes",
                "--approval-id", paused["pending_approval"]["id"],
                "--approval-decision", "approve",
            )
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertEqual("awaiting_approval", resumed["status"])
            self.assertTrue(resumed["require_approvals"])
            self.assertNotEqual(paused["pending_approval"]["id"], resumed["pending_approval"]["id"])
            self.assertNotIn("ACCEPTED", (agent / "workspace" / "demo-result.md").read_text(encoding="utf-8"))

    def test_explicit_model_routing_is_wired_without_disabling_approvals(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = create(Path(temp_name) / "agent", "developer", "agent", "company")
            def backend(model):
                return SimpleNamespace(name="codex", model=model, supports_action_approvals=True)
            with patch.object(cli, "CodexBackend", side_effect=backend), \
                 patch.object(cli, "Engine") as engine, redirect_stdout(StringIO()):
                engine.return_value.run.return_value = {"status": "blocked"}
                result = cli.main(["run", "--agent", str(agent), "--backend", "codex",
                    "--model", "cheap", "--repair-model", "repair", "--review-model", "review",
                    "--repair-after", "1", "--task", "bounded"])
                self.assertEqual(2, result)
                routed = engine.call_args.args[2]
                self.assertEqual("cheap", routed.model)
                self.assertEqual("repair", routed.recovery.model)
                self.assertEqual("review", routed.reviewer.model)
                self.assertEqual(1, routed.repair_after)
                self.assertTrue(engine.call_args.kwargs["require_approvals"])

    def run_cli(self, *args):
        env = os.environ.copy()
        env.pop("DEEPSEEK_API_KEY", None)
        result = subprocess.run(
            [sys.executable, "-m", "agentkit", *map(str, args)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"CLI did not emit JSON: rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}")
        return result, value

    def init_agent(self, root, name):
        result, value = self.run_cli(
            "init", root / name, "--profile", "developer", "--name", name, "--company", "FixtureCompany"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return Path(value["created"])

    def test_demo_completion_and_completed_resume_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = self.init_agent(Path(temp_name), "demo-agent")
            result, completed = self.run_cli(
                "run", "--agent", agent, "--backend", "demo", "--task", "Run the offline demo"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("completed", completed["status"])
            run_dir = agent / ".runs" / completed["run_id"]
            artifact = agent / "workspace" / "demo-result.md"
            before = artifact.read_bytes()
            result, replay = self.run_cli(
                "resume", "--agent", agent, "--backend", "demo", "--run-dir", run_dir
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("completed", replay["status"])
            self.assertEqual(before, artifact.read_bytes())
            self.assertTrue(replay["reviewed"])

    def test_approval_resume_uses_each_exact_pending_id(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = self.init_agent(Path(temp_name), "approval-agent")
            result, paused = self.run_cli(
                "run", "--agent", agent, "--backend", "demo", "--require-approvals",
                "--task", "Run the approval demo",
            )
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertEqual("awaiting_approval", paused["status"])
            run_dir = agent / ".runs" / paused["run_id"]
            state_path = run_dir / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            approval_id = state["pending_approval"]["id"]
            self.assertIsNone(state["in_flight"])
            result, next_state = self.run_cli(
                "resume", "--agent", agent, "--backend", "demo", "--run-dir", run_dir,
                "--approval-id", approval_id, "--approval-decision", "approve",
            )
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertEqual("awaiting_approval", next_state["status"])
            next_approval = next_state["pending_approval"]["id"]
            self.assertNotEqual(approval_id, next_approval)
            result, final = self.run_cli(
                "resume", "--agent", agent, "--backend", "demo", "--run-dir", run_dir,
                "--approval-id", next_approval, "--approval-decision", "approve",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("completed", final["status"])
            self.assertTrue((agent / "workspace" / "demo-result.md").is_file())

    def test_model_backends_cannot_disable_action_approvals_in_cli(self):
        with tempfile.TemporaryDirectory() as temp_name:
            agent = create(Path(temp_name) / "agent", "developer", "agent", "company")
            for backend_name, constructor in (("codex", "CodexBackend"), ("deepseek", "DeepSeekBackend")):
                with self.subTest(backend=backend_name), \
                     patch.object(cli, constructor, return_value=Mock(name=backend_name)), \
                     patch.object(cli, "Engine") as engine, redirect_stdout(StringIO()):
                    engine.return_value.run.return_value = {"status": "blocked"}
                    result = cli.main(["run", "--agent", str(agent), "--backend", backend_name,
                                       "--task", "bounded"])
                    self.assertEqual(2, result)
                    self.assertTrue(engine.call_args.kwargs["require_approvals"])


if __name__ == "__main__":
    unittest.main()
