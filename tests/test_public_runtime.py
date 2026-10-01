import json
import base64
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from agentkit.backends import DeepSeekBackend
from cockpit.conversations import Conversations
from cockpit.server import JobManager


ROOT = Path(__file__).resolve().parents[1]


class PublicRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.user_root = Path(self.temporary.name)
        shutil.copytree(ROOT / "agents", self.user_root / "agents")
        (self.user_root / "generated").mkdir()
        (self.user_root / "workspaces" / "default").mkdir(parents=True)
        self.manager = JobManager(
            template_root=ROOT,
            state_dir=self.user_root / "state",
            agent_roots=(self.user_root / "agents", self.user_root / "generated"),
            generated_root=self.user_root / "generated",
            workspace_root=self.user_root / "workspaces",
            public_mode=True,
            allowed_backends={"demo"},
        )

    def tearDown(self):
        self.temporary.cleanup()

    def wait(self, job_id: str) -> dict:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            job = self.manager.get(job_id)
            self.assertIsNotNone(job)
            result = self.manager.snapshot(job)
            if result["status"] not in {"queued", "running"}:
                return result
            time.sleep(0.02)
        self.fail("public demo job did not finish")

    def test_public_resource_references_never_expose_host_paths(self):
        agents = self.manager.agents()
        agent = next(item for item in agents if item["id"] == "programming-agent")
        self.assertEqual("programming-agent", agent["path"])
        self.assertNotIn(str(self.user_root), json.dumps(agents))

        job = self.manager.start({
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "task": "Public tenant smoke test.",
        })
        result = self.wait(job.job_id)
        self.assertEqual("completed", result["status"], result)
        self.assertEqual("programming-agent", result["agent"])
        self.assertEqual("default", result["workspace"])
        self.assertNotIn(str(self.user_root), json.dumps(result))
        self.assertTrue((self.user_root / "workspaces" / "default" / "demo-result.md").is_file())

    def test_aggregate_worker_slot_is_released_after_completion(self):
        semaphore = threading.BoundedSemaphore(1)
        manager = JobManager(
            template_root=ROOT,
            state_dir=self.user_root / "slot-state",
            agent_roots=(self.user_root / "agents", self.user_root / "generated"),
            generated_root=self.user_root / "generated",
            workspace_root=self.user_root / "workspaces",
            public_mode=True,
            allowed_backends={"demo"},
            worker_semaphore=semaphore,
        )
        job = manager.start({
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "task": "release the aggregate worker slot",
        })
        job.thread.join(10)
        self.assertEqual("completed", job.status, manager.snapshot(job))
        self.assertTrue(semaphore.acquire(blocking=False))
        semaphore.release()

    def test_public_paths_and_host_execution_are_fail_closed(self):
        absolute_agent = str(self.user_root / "agents" / "programming-agent")
        invalid = [
            {"agent": absolute_agent, "workspace": "default", "backend": "demo"},
            {"agent": "programming-agent", "workspace": "../escape", "backend": "demo"},
            {"agent": "programming-agent", "workspace": str(self.user_root), "backend": "demo"},
            {"agent": "programming-agent", "workspace": "default", "backend": "codex"},
        ]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(ContractError):
                self.manager.start({**fields, "task": "must be rejected"})

    def test_public_conversation_persists_only_resource_ids(self):
        conversations = Conversations(self.manager)
        value = conversations.create({
            "request_id": "1" * 32,
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "model": "",
            "title": "Tenant dialog",
            "require_approvals": True,
        })
        self.assertEqual("programming-agent", value["agent"])
        self.assertEqual("default", value["workspace"])
        raw = (self.manager.state_dir / "conversations" / (value["id"] + ".json")).read_text(encoding="utf-8")
        self.assertNotIn(str(self.user_root), raw)

    def test_public_workspace_rejects_symlink_or_junction(self):
        outside = self.user_root / "outside"
        outside.mkdir()
        link = self.user_root / "workspaces" / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks require privileges on this host")
        with self.assertRaises(ContractError):
            self.manager._workspace_path("linked")

    def test_public_model_tool_policy_cannot_execute_workspace_code(self):
        backend = DeepSeekBackend(
            api_key="test-only",
            allowed_tools={"list_files", "read_file", "write_file", "edit_file"},
        )
        names = {
            spec["function"]["name"]
            for spec in backend.available_tool_specs("workspace-write")
        }
        self.assertEqual({"list_files", "read_file", "write_file", "edit_file"}, names)
        with self.assertRaisesRegex(ContractError, "execution policy"):
            backend._run_tool(
                "run_pytest",
                {"path": "."},
                {"workspace": str(self.user_root / "workspaces" / "default"), "sandbox": "workspace-write"},
                5,
            )

    def test_public_model_write_uses_quota_writer_before_filesystem_mutation(self):
        workspace = self.user_root / "workspaces" / "default"
        backend = DeepSeekBackend(api_key="fixture-key", allowed_tools={"write_file"})
        calls = []

        def reject(target: Path, data: bytes) -> None:
            calls.append((target, data))
            raise ContractError("Workspace byte quota exceeded.")

        with self.assertRaisesRegex(ContractError, "quota exceeded"):
            backend._run_tool(
                "write_file",
                {"path": "bounded.txt", "content": "blocked"},
                {"workspace": str(workspace), "sandbox": "workspace-write", "mutation_writer": reject},
                5,
            )
        self.assertEqual([((workspace / "bounded.txt").resolve(), b"blocked")], calls)
        self.assertFalse((workspace / "bounded.txt").exists())

    def test_public_provider_status_uses_only_managed_secret(self):
        manager = JobManager(
            template_root=ROOT,
            state_dir=self.user_root / "managed-state",
            agent_roots=(self.user_root / "agents", self.user_root / "generated"),
            generated_root=self.user_root / "generated",
            workspace_root=self.user_root / "workspaces",
            public_mode=True,
            allowed_backends={"deepseek"},
            provider_api_key="managed-test-key",
        )
        status = manager.provider_status()
        self.assertEqual(
            {"configured": True, "source": "managed", "storage_available": False},
            status,
        )
        self.assertNotIn("managed-test-key", json.dumps(manager.configuration()))

    def test_public_configuration_omits_disabled_codex_and_host_readiness(self):
        with patch("cockpit.server.codex_readiness", side_effect=AssertionError("must not inspect host")):
            configuration = self.manager.configuration()
        self.assertEqual(["demo"], [backend["id"] for backend in configuration["backends"]])
        self.assertNotIn("credentials_present", json.dumps(configuration))

    def test_public_uploads_do_not_invoke_document_or_image_parsers(self):
        conversations = Conversations(self.manager)
        value = conversations.create({
            "request_id": "2" * 32,
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "model": "",
            "title": "Safe uploads",
        })
        for name, content in (("invoice.pdf", b"%PDF-fake"), ("scan.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20)):
            with self.subTest(name=name), self.assertRaisesRegex(ContractError, "text attachments"):
                conversations.upload(value["id"], {
                    "request_id": "3" * 32,
                    "name": name,
                    "content_base64": base64.b64encode(content).decode("ascii"),
                })

    def test_public_approval_snapshot_redacts_internal_paths_and_continuation(self):
        job = self.manager.start({
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "task": "Approval redaction.",
            "require_approvals": True,
        })
        result = self.wait(job.job_id)
        self.assertEqual("awaiting_approval", result["status"], result)
        serialized = json.dumps(result, ensure_ascii=False)
        for value in (self.user_root, self.user_root / "workspaces" / "default"):
            self.assertNotIn(str(value).replace("\\", "\\\\"), serialized)
        self.assertNotIn("core_snapshot", serialized)
        self.assertNotIn('"binding"', serialized)
        self.assertNotIn('"continuation"', serialized)
        pending = result["result"]["pending_approval"]
        self.assertEqual({"id", "tool", "arguments", "action_sha256"}, set(pending))

    def test_public_redaction_handles_normalized_separators_and_windows_case(self):
        workspace = self.manager._workspace_path("default")
        agent = self.manager._agent_path("programming-agent")
        leaked_workspace = str(workspace).replace("\\", "/")
        leaked_agent = str(agent).replace("\\", "/")
        if os.name == "nt":
            leaked_workspace = leaked_workspace.upper()
            leaked_agent = leaked_agent.upper()
        value = self.manager._public_redact(
            {"summary": f"workspace={leaked_workspace}; agent={leaked_agent}"},
            {"workspace": "default", "agent": "programming-agent"},
        )
        serialized = json.dumps(value)
        self.assertNotIn(leaked_workspace, serialized)
        self.assertNotIn(leaked_agent, serialized)
        self.assertIn("workspace=default", value["summary"])
        self.assertIn("agent=programming-agent", value["summary"])


if __name__ == "__main__":
    unittest.main()
