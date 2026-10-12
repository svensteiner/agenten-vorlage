import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentkit.api_backend import ApiBackend
from agentkit.cli import parser
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.scaffold import create


class ApiBackendTests(unittest.TestCase):
    def backend(self, **kwargs):
        return ApiBackend("test-model", api_key="fixture-key", base_url="https://provider.example/v1", **kwargs)

    @unittest.skipUnless(shutil.which("git"), "Git required")
    def test_git_inspection_reads_real_diff_and_rejects_parent_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            git("init")
            (root / "app.py").write_text("before\n", encoding="utf-8")
            git("add", "app.py")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "baseline")
            (root / "app.py").write_text("after\n", encoding="utf-8")
            backend = self.backend()
            result = json.loads(backend._run_tool("inspect_git", {}, {"workspace": str(root), "sandbox": "read-only"}, 10))
            self.assertEqual("ok", result["status"])
            self.assertIn(" M app.py", result["git_status"])
            self.assertIn("-before", result["diff_head"])
            self.assertIn("+after", result["diff_head"])
            self.assertFalse(result["truncated"])
            self.assertEqual("after\n", (root / "app.py").read_text())
            child = root / "child"
            child.mkdir()
            result = json.loads(backend._run_tool("inspect_git", {}, {"workspace": str(child)}, 10))
            self.assertEqual("workspace_is_not_git_root", result["reason"])
            with self.assertRaises(ContractError):
                backend._run_tool("inspect_git", {"command": "reset"}, {"workspace": str(root)}, 10)

    def test_request_uses_selected_provider_and_tools(self):
        backend = self.backend()
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "{}"}}]
        }).encode()
        with patch("agentkit.backends.urllib.request.build_opener", return_value=opener):
            result = backend._chat([{"role": "user", "content": "fixture"}], 5,
                                   tools=backend.available_tool_specs("read-only"))
        request = opener.open.call_args.args[0]
        self.assertEqual("https://provider.example/v1/chat/completions", request.full_url)
        self.assertEqual("Bearer fixture-key", request.get_header("Authorization"))
        payload = json.loads(request.data)
        self.assertEqual("test-model", payload["model"])
        self.assertIn("tools", payload)
        self.assertNotIn("response_format", payload)
        self.assertEqual("{}", result["content"])

    def test_optional_json_mode_does_not_change_tool_policy(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"{}"}}]}'
        with patch("agentkit.backends.urllib.request.build_opener", return_value=opener):
            self.backend(json_mode=False)._chat([], 5)
        self.assertNotIn("response_format", json.loads(opener.open.call_args.args[0].data))
        with self.assertRaises(ContractError):
            self.backend()._run_tool("write_file", {"path": "x", "content": "x"}, {"sandbox": "read-only"}, 5)

    def test_missing_configuration_never_falls_back_to_deepseek(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "wrong-provider-key",
                                     "DEEPSEEK_MODEL": "wrong-model"}, clear=True):
            with self.assertRaises(ContractError):
                ApiBackend()

    def test_environment_configuration_and_endpoint_identity(self):
        with patch.dict(os.environ, {"AGENTKIT_API_KEY": "fixture-key",
                                     "AGENTKIT_API_MODEL": "model-a",
                                     "AGENTKIT_API_BASE_URL": "https://provider.example/v1",
                                     "AGENTKIT_API_JSON_MODE": "off"}, clear=True):
            backend = ApiBackend()
        self.assertFalse(backend.json_mode)
        other = ApiBackend("model-a", api_key="fixture-key", base_url="https://other.example/v1")
        self.assertNotEqual(backend.name, other.name)
        self.assertEqual(backend.name, self.backend().name)
        self.assertNotIn("fixture-key", backend.name)

    def test_unsafe_provider_urls_and_keys_are_rejected(self):
        for url in ("http://provider.example", "https://user:password@provider.example",
                    "https://provider.example?key=x", "https://provider.example#x"):
            with self.subTest(url=url), self.assertRaises(ContractError):
                ApiBackend("test", api_key="fixture-key", base_url=url)
        with self.assertRaises(ContractError):
            ApiBackend("test", api_key="bad\nkey", base_url="https://provider.example")

    def test_cli_accepts_provider_independent_backend(self):
        args = parser().parse_args(["run", "--agent", "agent", "--backend", "api", "--task", "fixture"])
        self.assertEqual("api", args.backend)

    def test_checkpoint_cannot_resume_with_different_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            agent = create(Path(folder) / "agent", "developer", "agent", "Company")
            backend = self.backend()
            backend.decide = MagicMock(return_value={
                "action": "blocked", "role": "", "skills": [], "task": "fixture pause", "reason": "fixture"
            })
            state = Engine(agent, agent / "workspace", backend).run("fixture")
            other = ApiBackend("test-model", api_key="fixture-key", base_url="https://other.example/v1")
            with self.assertRaises(ContractError):
                Engine(agent, agent / "workspace", other).run("", run_dir=agent / ".runs" / state["run_id"])

    def test_api_tool_write_and_review_complete_only_after_approval(self):
        decision = {"action": "delegate", "role": "developer", "skills": [], "task": "fixture", "reason": "fixture"}
        review = {**decision, "role": "reviewer"}
        finish = {"action": "finish", "role": "", "skills": [], "task": "done", "reason": "verified"}
        report = {"status": "success", "summary": "fixture verified", "artifacts": ["result.txt"],
                  "evidence": ["fixture evidence"], "next_actions": []}
        tool = {"role": "assistant", "tool_calls": [{"id": "write-1", "type": "function", "function": {
            "name": "write_file", "arguments": json.dumps({"path": "result.txt", "content": "fixture result"})
        }}]}
        responses = [{"content": json.dumps(decision)}, tool, {"content": json.dumps(report)},
                     {"content": json.dumps(review)}, {"content": json.dumps(report)}, {"content": json.dumps(finish)}]
        with tempfile.TemporaryDirectory() as folder:
            agent = create(Path(folder) / "agent", "developer", "agent", "Company")
            backend = self.backend()
            workspace = agent / "workspace"
            with patch.object(backend, "_chat", side_effect=responses):
                state = Engine(agent, workspace, backend, require_approvals=True).run("fixture write")
                self.assertEqual("awaiting_approval", state["status"])
                self.assertFalse((workspace / "result.txt").exists())
                state = Engine(agent, workspace, backend).run(
                    "", run_dir=agent / ".runs" / state["run_id"],
                    approval_id=state["pending_approval"]["id"], approval_decision="approve",
                )
            self.assertEqual("completed", state["status"], state["summary"])
            self.assertTrue(state["reviewed"])
            self.assertEqual("fixture result", (workspace / "result.txt").read_text())
