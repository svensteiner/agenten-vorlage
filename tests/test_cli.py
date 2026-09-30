import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentKitCliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
