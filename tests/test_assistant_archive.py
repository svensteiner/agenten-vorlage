import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class AssistantArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "assistant", "developer", "assistant", "Company")
        self.manager = JobManager(self.root)

    def tearDown(self):
        for job in self.manager.recent(1000):
            if job.thread:
                job.thread.join(10)
        self.temp.cleanup()

    def test_archive_restart_restore_preserves_pack_and_existing_dialog(self):
        dialogs = Conversations(self.manager)
        conversation = dialogs.create({"request_id": "1" * 32, "agent": str(self.agent), "backend": "demo",
                                       "workspace": str(self.agent / "workspace"), "title": "Archive"})
        attachment = dialogs.upload(conversation["id"], {"request_id": "2" * 32, "name": "x.txt",
            "content_base64": base64.b64encode(b"archive-bytes").decode()})
        dialogs.send(conversation["id"], {"request_id": "3" * 32, "content": "Use it",
                                            "attachment_ids": [attachment["id"]]})
        self.manager.get("3" * 32).thread.join(10)
        pack_before = (self.agent / "agent.json").read_bytes()
        self.assertTrue(self.manager.archive_agent({"agent": str(self.agent), "archived": True})["archived"])
        self.assertEqual(pack_before, (self.agent / "agent.json").read_bytes())
        self.assertEqual([], self.manager.agents())
        self.assertTrue(self.manager.agents(include_archived=True)[0]["archived"])
        restored_manager = JobManager(self.root)
        self.assertEqual([], restored_manager.agents())
        self.assertTrue(restored_manager.agents(include_archived=True)[0]["archived"])
        restored = Conversations(restored_manager).get(conversation["id"])
        self.assertEqual(attachment, restored["messages"][0]["attachments"][0])
        self.assertEqual((b"archive-bytes", "x.txt"), Conversations(restored_manager).download(conversation["id"], attachment["id"]))
        restored_manager.archive_agent({"agent": str(self.agent), "archived": False})
        self.assertFalse(restored_manager.agents()[0]["archived"])

        self.manager.archive_agent({"agent": str(self.agent), "archived": True})
        pending = self.manager.start({"agent": str(self.agent), "workspace": str(self.agent / "workspace"),
                                      "backend": "demo", "task": "Archived approval", "require_approvals": True})
        pending.thread.join(10)
        pending_state = self.manager.snapshot(pending)
        self.assertEqual("awaiting_approval", pending_state["status"])
        resumed = self.manager.approval(pending.job_id, pending_state["result"]["pending_approval"]["id"], "approve")
        resumed.thread.join(10)
        second = self.manager.snapshot(resumed)
        self.assertEqual("awaiting_approval", second["status"])
        final = self.manager.approval(pending.job_id, second["result"]["pending_approval"]["id"], "approve")
        final.thread.join(10)
        self.assertFalse(final.thread.is_alive())
        self.assertEqual("completed", final.status)
        self.assertTrue(final.result["reviewed"])

    def test_invalid_and_corrupt_state_fail_explicitly(self):
        with self.assertRaises(ContractError):
            self.manager.archive_agent({"agent": str(self.agent), "archived": "true"})
        with self.assertRaises(ContractError):
            self.manager.archive_agent({"agent": str(self.root / "missing"), "archived": True})
        nested = create(self.root / "agents" / "nested" / "evil", "developer", "evil", "Company")
        with self.assertRaises(ContractError):
            self.manager.archive_agent({"agent": str(nested), "archived": True})
        corrupt_pack = self.root / "agents" / "corrupt"
        corrupt_pack.mkdir(parents=True)
        (corrupt_pack / "agent.json").write_text("not-json", encoding="utf-8")
        archive_state = self.root / "cockpit" / ".runs" / "assistant-settings" / "archive.json"
        self.assertFalse(archive_state.exists())
        with self.assertRaises(ContractError):
            self.manager.archive_agent({"agent": str(corrupt_pack), "archived": True})
        self.assertFalse(archive_state.exists())
        state = self.root / "cockpit" / ".runs" / "assistant-settings" / "archive.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text('{"version":1,"agents":{"bad":true}}', encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.agents()
        with self.assertRaises(ContractError):
            self.manager.archive_agent({"agent": str(self.agent), "archived": False})
        state.write_text("not-json", encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.agents()
        state.write_text("x" * 512_001, encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.agents()
        state.unlink()
        state.mkdir()
        with self.assertRaises(ContractError):
            self.manager.agents()

    def test_http_archive_idempotency_visibility_and_origin(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            def request(method, payload=None, origin=None, query=""):
                headers = {"Content-Type": "application/json"}
                if origin:
                    headers["Origin"] = origin
                return urlopen(Request(base + ("/api/agents/archive" if method == "POST" else "/api/agents") + query, method=method,
                                       data=json.dumps(payload).encode() if payload is not None else None,
                                       headers=headers), timeout=3)
            with request("POST", {"agent": str(self.agent), "archived": True}) as response:
                archived = json.loads(response.read())
            self.assertTrue(archived["archived"])
            with request("POST", {"agent": str(self.agent), "archived": True}) as response:
                self.assertTrue(json.loads(response.read())["archived"])
            with request("GET") as response:
                self.assertEqual([], json.loads(response.read())["agents"])
            with request("GET", query="?include_archived=true") as response:
                self.assertTrue(json.loads(response.read())["agents"][0]["archived"])
            with self.assertRaises(HTTPError) as error:
                request("POST", {"agent": str(self.agent), "archived": False}, "https://foreign.example")
            self.assertEqual(403, error.exception.code)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


if __name__ == "__main__":
    unittest.main()
