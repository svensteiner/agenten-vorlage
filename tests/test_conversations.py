import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.agent = create(self.root / "agents" / "assistant", "developer", "assistant", "Company")
        self.manager = JobManager(self.root)
        self.conversations = Conversations(self.manager)
        self.payload = {"request_id": "1" * 32, "title": "Test dialogue", "agent": str(self.agent),
                        "workspace": str(self.agent / "workspace"), "backend": "demo"}
        self.conversation = self.conversations.create(self.payload)
        self.cid = self.conversation["id"]

    def tearDown(self):
        for job in self.manager.recent(1000):
            if job.thread:
                job.thread.join(10)
        self.temporary.cleanup()

    def send(self, content, request_id):
        result = self.conversations.send(self.cid, {"content": content, "request_id": request_id})
        job = self.manager.get(request_id)
        if job.thread:
            job.thread.join(10)
        return result, job

    def test_creation_is_idempotent_and_bound(self):
        self.assertEqual(self.conversation, self.conversations.create(self.payload))
        with self.assertRaises(ContractError):
            self.conversations.create({**self.payload, "title": "Another dialog"})
        with self.assertRaises(ContractError):
            self.conversations.get("../../escape")

    def test_codex_dialog_defaults_to_sticky_approval_policy(self):
        payload = {**self.payload, "request_id": "4" * 32, "backend": "codex"}
        conversation = self.conversations.create(payload)
        self.assertTrue(conversation["require_approvals"])
        self.assertTrue(self.conversations.create(payload)["require_approvals"])
        self.assertTrue(self.conversations.create({**payload, "require_approvals": False})["require_approvals"])
        restarted = Conversations(JobManager(self.root))
        self.assertTrue(restarted.get(conversation["id"])["require_approvals"])

    def test_two_turns_keep_entire_visible_context_across_restart(self):
        _, first = self.send("Remember marker FIRST-123", "2" * 32)
        _, second = self.send("Use the earlier marker", "3" * 32)
        self.assertEqual("completed", second.status)
        self.assertIn("Remember marker FIRST-123", second.result["task"])
        self.assertIn(first.result["summary"], second.result["task"])
        self.assertIn("Use the earlier marker", second.result["task"])
        restarted = Conversations(JobManager(self.root))
        messages = restarted.get(self.cid)["messages"]
        self.assertEqual(["user", "assistant", "user", "assistant"], [item["role"] for item in messages])
        self.assertEqual(first.result["summary"], messages[1]["content"])
        self.assertEqual("Use the earlier marker", messages[2]["content"])

    def test_duplicate_message_is_exactly_one_job(self):
        _, job = self.send("One task", "2" * 32)
        with patch.object(self.manager, "start") as start:
            self.conversations.send(self.cid, {"content": "One task", "request_id": "2" * 32})
        start.assert_not_called()
        self.assertEqual(2, len(self.conversations.get(self.cid)["messages"]))
        with self.assertRaises(ContractError):
            self.conversations.send(self.cid, {"content": "Changed", "request_id": job.job_id})

    def test_parallel_retries_dispatch_once_and_active_turn_blocks_next(self):
        payload = {"content": "One task", "request_id": "2" * 32}
        with patch.object(self.manager, "_run") as run:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.conversations.send, self.cid, payload) for _ in range(2)]
                for future in futures:
                    future.result(timeout=5)
            self.manager.get(payload["request_id"]).thread.join(2)
            self.assertEqual(1, run.call_count)
            with self.assertRaises(ContractError):
                self.conversations.send(self.cid, {"content": "Too soon", "request_id": "3" * 32})
        self.assertEqual(2, len(self.conversations.get(self.cid)["messages"]))

    def test_reserved_message_recovers_without_duplicate_after_dispatch_failure(self):
        payload = {"content": "Crash before job dispatch", "request_id": "2" * 32}
        with patch.object(self.manager, "start", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                self.conversations.send(self.cid, payload)
        snapshot = self.conversations.get(self.cid)
        self.assertIsNone(snapshot["active_job_id"])
        self.assertEqual("interrupted", snapshot["messages"][1]["status"])
        self.conversations = Conversations(self.manager)
        self.conversations.send(self.cid, payload)
        self.manager.get(payload["request_id"]).thread.join(10)
        self.assertEqual(2, len(self.conversations.get(self.cid)["messages"]))

    def test_company_change_and_context_overflow_fail_without_new_turn(self):
        self.send("First", "2" * 32)
        self.conversations.max_context_chars = 1
        with self.assertRaises(ContractError):
            self.conversations.send(self.cid, {"content": "Next", "request_id": "3" * 32})
        self.assertEqual(2, len(self.conversations.get(self.cid)["messages"]))
        config_file = self.agent / "agent.json"
        config = json.loads(config_file.read_text(encoding="utf-8"))
        config["company"] = "DifferentCompany"
        config_file.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(ContractError):
            self.conversations.send(self.cid, {"content": "Cross company", "request_id": "4" * 32})

    def test_old_jobs_load_on_demand_for_conversation_history(self):
        _, job = self.send("Keep history", "2" * 32)
        self.manager.jobs.clear()
        snapshot = self.conversations.get(self.cid)
        self.assertEqual(job.result["summary"], snapshot["messages"][1]["content"])
        self.assertEqual("completed", snapshot["messages"][1]["status"])

    def test_assistant_host_provenance_comes_from_job_snapshot_and_survives_restore(self):
        forged = {"status": "complete", "write_receipt_count": 99}
        self.conversations.send(
            self.cid,
            {"content": "Check provenance binding", "request_id": "2" * 32,
             "run_write_provenance": forged},
        )
        job = self.manager.get("2" * 32)
        job.thread.join(10)
        provenance = {
            "status": "complete",
            "baseline_status": "captured",
            "changed_by_run": ["content/result.md"],
            "changed_without_matching_receipt": [],
            "unknown_paths": [],
            "unknown_path_count": 0,
            "write_receipt_count": 1,
        }
        job.result["run_write_provenance"] = provenance
        self.manager._persist(job)

        restored = Conversations(JobManager(self.root)).get(self.cid)["messages"]
        self.assertNotIn("run_write_provenance", restored[0])
        self.assertEqual(provenance, restored[1]["run_write_provenance"])

    def test_oversized_provenance_is_dropped_instead_of_truncated(self):
        valid = {
            "status": "complete",
            "baseline_status": "captured",
            "changed_by_run": [],
            "changed_without_matching_receipt": [],
            "unknown_paths": [],
            "unknown_path_count": 0,
            "write_receipt_count": 0,
        }
        cases = (
            {"changed_by_run": ["src/file.py"] * 65},
            {"changed_by_run": ["x" * 501]},
            {"write_receipt_count": 49},
            {"unknown_path_count": 65},
        )
        for changes in cases:
            with self.subTest(changes=tuple(changes)):
                payload = {**valid, **changes}
                snapshot = {"result": {"run_write_provenance": payload}}
                self.assertIsNone(Conversations._write_provenance(snapshot))

    def test_public_conversation_never_exposes_host_provenance(self):
        public_root = self.root / "public"
        workspace_root = public_root / "workspaces"
        (workspace_root / "default").mkdir(parents=True)
        manager = JobManager(
            self.root,
            state_dir=public_root / "state",
            public_mode=True,
            workspace_root=workspace_root,
        )
        conversations = Conversations(manager)
        conversation = conversations.create({
            "request_id": "8" * 32,
            "title": "Public provenance fixture",
            "agent": "assistant",
            "workspace": "default",
            "backend": "demo",
        })
        conversations.send(conversation["id"], {
            "content": "Public fixture run",
            "request_id": "9" * 32,
            "run_write_provenance": {
                "status": "complete",
                "baseline_status": "captured",
                "changed_by_run": ["forged.txt"],
                "changed_without_matching_receipt": [],
                "unknown_paths": [],
                "unknown_path_count": 0,
                "write_receipt_count": 1,
            },
        })
        job = manager.get("9" * 32)
        job.thread.join(10)
        job.result["run_write_provenance"] = {
            "status": "complete",
            "baseline_status": "captured",
            "changed_by_run": ["private/path.txt"],
            "changed_without_matching_receipt": [],
            "unknown_paths": [],
            "unknown_path_count": 0,
            "write_receipt_count": 1,
        }
        manager._persist(job)

        messages = conversations.get(conversation["id"])["messages"]
        self.assertNotIn("run_write_provenance", messages[0])
        self.assertNotIn("run_write_provenance", messages[1])
        self.assertNotIn("private/path.txt", json.dumps(messages))
        for item in manager.recent(1000):
            if item.thread:
                item.thread.join(10)

    def test_existing_task_id_cannot_be_claimed_by_conversation(self):
        payload = {key: value for key, value in self.payload.items() if key not in {"title", "request_id"}}
        job = self.manager.start({**payload, "task": "Ordinary task", "request_id": "2" * 32})
        job.thread.join(10)
        with self.assertRaises(ContractError):
            self.conversations.send(self.cid, {"content": "Hijack", "request_id": job.job_id})
        self.assertEqual([], self.conversations.get(self.cid)["messages"])

    def test_http_conversation_roundtrip_and_cross_origin_rejection(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            request = Request(base + f"/api/conversations/{self.cid}/messages",
                              data=json.dumps({"content": "HTTP conversation", "request_id": "2" * 32}).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=5) as response:
                self.assertEqual(202, response.status)
                self.assertEqual(self.cid, json.load(response)["id"])
            self.manager.get("2" * 32).thread.join(10)
            with urlopen(base + f"/api/conversations/{self.cid}", timeout=5) as response:
                data = json.load(response)
            self.assertEqual("completed", data["messages"][-1]["status"])
            self.assertIsNone(data["active_job_id"])
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + "/api/conversations", headers={"Origin": "https://evil.example"}), timeout=5)
            self.assertEqual(403, caught.exception.code)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
