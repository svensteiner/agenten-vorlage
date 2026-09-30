import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class CockpitApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "assistant", "developer", "assistant", "Company")
        self.workspace = self.agent / "workspace"
        self.manager = JobManager(self.root)
        self.payload = {"agent": str(self.agent), "workspace": str(self.workspace),
                        "backend": "demo", "task": "Approval demo", "require_approvals": True}

    def tearDown(self):
        for job in self.manager.recent(1000):
            if job.thread:
                job.thread.join(10)
        self.temp.cleanup()

    def settle(self, job):
        if job.thread:
            job.thread.join(10)
            self.assertFalse(job.thread.is_alive())
        return self.manager.snapshot(job)

    def pending(self):
        job = self.manager.start(self.payload)
        value = self.settle(job)
        self.assertEqual("awaiting_approval", value["status"], value)
        self.assertFalse((self.workspace / "demo-result.md").exists())
        return job, value["result"]["pending_approval"]["id"]

    def test_exact_action_approval_survives_restart_and_duplicate_post(self):
        job, approval_id = self.pending()
        self.manager = JobManager(self.root)
        job = self.manager.approval(job.job_id, approval_id, "approve")
        value = self.settle(job)
        self.assertTrue((self.workspace / "demo-result.md").exists())
        self.assertEqual("awaiting_approval", value["status"])
        next_id = value["result"]["pending_approval"]["id"]
        self.assertNotEqual(approval_id, next_id)
        before = (self.workspace / "demo-result.md").read_bytes()
        self.assertIs(job, self.manager.approval(job.job_id, approval_id, "approve"))
        self.assertEqual(before, (self.workspace / "demo-result.md").read_bytes())
        with self.assertRaises(ContractError):
            self.manager.approval(job.job_id, approval_id, "reject")
        final = self.settle(self.manager.approval(job.job_id, next_id, "approve"))
        self.assertEqual("completed", final["status"], final)
        self.assertTrue(final["result"]["reviewed"])

    def test_reject_does_not_write_and_resume_cannot_bypass_pending(self):
        job, approval_id = self.pending()
        with self.assertRaises(ContractError):
            self.manager.resume(job.job_id, "Just run", True)
        value = self.settle(self.manager.approval(job.job_id, approval_id, "reject"))
        self.assertEqual("blocked", value["status"])
        self.assertFalse((self.workspace / "demo-result.md").exists())

    def test_invalid_approval_identity_and_changed_policy_fail(self):
        payload = {**self.payload, "request_id": "d" * 32}
        job = self.manager.start(payload)
        self.settle(job)
        for approval_id, decision in (("f" * 32, "approve"), ("../bad", "approve"), ("f" * 32, "yes")):
            with self.subTest(approval_id=approval_id, decision=decision), self.assertRaises(ContractError):
                self.manager.approval(job.job_id, approval_id, decision)
        with self.assertRaises(ContractError):
            self.manager.start({**payload, "require_approvals": False})

    def test_backend_policy_is_explicit_and_codex_cannot_disable_it(self):
        with patch.object(self.manager, "_run"):
            job = self.manager.start({**self.payload, "backend": "deepseek", "require_approvals": False})
            self.settle(job)
            self.assertTrue(job.payload["require_approvals"])
            job = self.manager.start({**self.payload, "backend": "codex"})
            self.settle(job)
            self.assertTrue(job.payload["require_approvals"])
        with self.assertRaises(ContractError):
            self.manager.start({**self.payload, "require_approvals": "false"})

    def test_codex_default_is_approval_enabled_and_provider_describes_host_executor(self):
        with patch.object(self.manager, "_run"):
            job = self.manager.start({**self.payload, "backend": "codex"})
            self.settle(job)
        self.assertTrue(job.payload["require_approvals"])
        codex = next(item for item in self.manager.configuration()["backends"] if item["id"] == "codex")
        self.assertTrue(codex["tool_approvals"])
        self.assertIn("read-only", codex["approval_detail"])
        self.assertIn("allowlist", codex["approval_detail"])
        self.assertIn("per-tool interception", codex["approval_detail"])

    def test_reserved_approval_dispatch_recovers_after_restart(self):
        job, approval_id = self.pending()
        with patch.object(self.manager, "_run"):
            self.settle(self.manager.approval(job.job_id, approval_id, "approve"))
        self.manager = JobManager(self.root)
        recovered = self.manager.get(job.job_id)
        self.assertEqual("blocked", recovered.status)
        value = self.settle(self.manager.approval(job.job_id, approval_id, "approve"))
        self.assertEqual("awaiting_approval", value["status"])
        self.assertNotEqual(approval_id, value["result"]["pending_approval"]["id"])

    def test_stale_approve_can_be_rejected_without_restoring_old_workspace(self):
        job, approval_id = self.pending()
        (self.workspace / "changed.txt").write_text("New evidence")
        value = self.settle(self.manager.approval(job.job_id, approval_id, "approve"))
        self.assertEqual("error", value["status"])
        self.assertFalse((self.workspace / "demo-result.md").exists())
        value = self.settle(self.manager.approval(job.job_id, approval_id, "reject"))
        self.assertEqual("blocked", value["status"])
        self.assertIsNone(value["result"]["pending_approval"])

    def test_conversation_policy_persists_and_waits_for_approval(self):
        conversations = Conversations(self.manager)
        payload = {**self.payload, "request_id": "e" * 32, "title": "Approval dialog"}
        conversation = conversations.create(payload)
        self.assertTrue(conversation["require_approvals"])
        conversations.send(conversation["id"], {"request_id": "a" * 32, "content": "First turn"})
        self.settle(self.manager.get("a" * 32))
        messages = conversations.get(conversation["id"])["messages"]
        self.assertEqual("awaiting_approval", messages[-1]["status"])
        with self.assertRaises(ContractError):
            conversations.send(conversation["id"], {"request_id": "b" * 32, "content": "Next turn"})
        with self.assertRaises(ContractError):
            conversations.create({**payload, "require_approvals": False})

    def test_http_approval_rejects_cross_origin_and_runs_exact_pending_action(self):
        job, approval_id = self.pending()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/api/jobs/{job.job_id}/approval"
        body = json.dumps({"approval_id": approval_id, "decision": "approve"}).encode()
        try:
            request = Request(url, data=body, headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
            with self.assertRaises(HTTPError) as caught:
                urlopen(request, timeout=3)
            self.assertEqual(403, caught.exception.code)
            self.assertFalse((self.workspace / "demo-result.md").exists())
            with urlopen(Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=3) as response:
                self.assertEqual(202, response.status)
            self.settle(job)
            self.assertTrue((self.workspace / "demo-result.md").is_file())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
