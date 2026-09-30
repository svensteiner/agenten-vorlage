import base64
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


class ConversationAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "assistant", "developer", "assistant", "Company")
        self.manager = JobManager(self.root)
        self.dialogs = Conversations(self.manager)
        self.payload = {"request_id": "1" * 32, "agent": str(self.agent), "backend": "demo",
                        "workspace": str(self.agent / "workspace"), "title": "Files"}
        self.cid = self.dialogs.create(self.payload)["id"]

    def tearDown(self):
        for job in self.manager.recent(1000):
            if job.thread:
                job.thread.join(10)
        self.temp.cleanup()

    def upload(self, aid="a" * 32, text="ATTACHMENT-4711: Grüße", name="notes.txt", cid=None):
        return self.dialogs.upload(cid or self.cid, {"request_id": aid, "name": name,
                                   "content_base64": base64.b64encode(text.encode()).decode()})

    def send(self, request_id="2" * 32, attachments=None):
        result = self.dialogs.send(self.cid, {"request_id": request_id, "content": "Use the reference file",
                                           "attachment_ids": attachments or []})
        job = self.manager.get(request_id)
        job.thread.join(10)
        self.assertFalse(job.thread.is_alive())
        self.assertEqual("completed", job.status)
        return result, job

    def test_attachment_context_and_original_download_survive_restart_and_next_turn(self):
        metadata = self.upload()
        self.assertFalse((self.agent / "workspace" / "notes.txt").exists())
        _, first = self.send(attachments=[metadata["id"]])
        self.assertIn("ATTACHMENT-4711", first.result["task"])
        self.assertIn("untrusted reference data", first.result["task"])
        _, second = self.send("3" * 32)
        self.assertIn("ATTACHMENT-4711", second.result["task"])
        restored = Conversations(JobManager(self.root))
        self.assertEqual(metadata, restored.get(self.cid)["messages"][0]["attachments"][0])
        content, name = restored.download(self.cid, metadata["id"])
        self.assertEqual("notes.txt", name)
        self.assertEqual("ATTACHMENT-4711: Grüße".encode(), content)

    def test_message_retry_identity_includes_attachments(self):
        first, second = self.upload(), self.upload("b" * 32, "Different")
        self.send(attachments=[first["id"]])
        with self.assertRaises(ContractError):
            self.send(attachments=[second["id"]])
        with patch.object(self.manager, "start") as start:
            self.dialogs.send(self.cid, {"request_id": "2" * 32, "content": "Use the reference file",
                                       "attachment_ids": [first["id"]]})
        start.assert_not_called()

    def test_cross_conversation_and_invalid_references_never_dispatch(self):
        metadata = self.upload()
        other = self.dialogs.create({**self.payload, "request_id": "4" * 32})["id"]
        with self.assertRaises(ContractError):
            self.dialogs.download(other, metadata["id"])
        with patch.object(self.manager, "start") as start:
            for values in (["f" * 32], ["../bad"], "wrong", [metadata["id"]] * 2, [str(i) * 32 for i in range(6)]):
                with self.subTest(values=values), self.assertRaises((ContractError, OSError)):
                    self.dialogs.send(self.cid, {"request_id": "2" * 32, "content": "Use", "attachment_ids": values})
        start.assert_not_called()
        self.assertEqual([], self.dialogs.get(self.cid)["messages"])

    def test_context_overflow_is_explicit_before_message_reservation(self):
        first = self.upload(text="A" * 32000)
        second = self.upload("b" * 32, "B" * 32000)
        with self.assertRaisesRegex(ContractError, "context limit"):
            self.send(attachments=[first["id"], second["id"]])
        self.assertEqual([], self.dialogs.get(self.cid)["messages"])

    def test_interrupted_reservation_keeps_original_attachment_identity(self):
        metadata = self.upload()
        payload = {"request_id": "2" * 32, "content": "Use the reference file", "attachment_ids": [metadata["id"]]}
        with patch.object(self.manager, "start", side_effect=RuntimeError("dispatch interrupted")), self.assertRaises(RuntimeError):
            self.dialogs.send(self.cid, payload)
        self.assertEqual("interrupted", self.dialogs.get(self.cid)["messages"][0]["status"])
        restored = Conversations(JobManager(self.root))
        with self.assertRaises(ContractError):
            restored.send(self.cid, {**payload, "attachment_ids": []})
        self.send(attachments=[metadata["id"]])
        self.assertEqual(2, len(self.dialogs.get(self.cid)["messages"]))

    def test_company_change_prevents_upload_and_download(self):
        metadata = self.upload()
        config_path = self.agent / "agent.json"
        config = json.loads(config_path.read_text())
        config["company"] = "OtherCompany"
        config_path.write_text(json.dumps(config))
        with self.assertRaises(ContractError):
            self.upload("b" * 32)
        with self.assertRaises(ContractError):
            self.dialogs.download(self.cid, metadata["id"])

    def test_http_upload_download_headers_and_origin_guards(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/api/conversations/{self.cid}/attachments"
        raw = b"<script>never execute me</script>"
        body = json.dumps({"request_id": "a" * 32, "name": "reference.html",
                           "content_base64": base64.b64encode(raw).decode()}).encode()
        try:
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base, data=body, headers={"Content-Type": "application/json", "Origin": "https://evil.example"}), timeout=3)
            self.assertEqual(403, caught.exception.code)
            caught.exception.close()
            with urlopen(Request(base, data=body, headers={"Content-Type": "application/json"}), timeout=3) as response:
                metadata = json.load(response)
                self.assertEqual(201, response.status)
            with urlopen(base + "/" + metadata["id"], timeout=3) as response:
                self.assertEqual(raw, response.read())
                self.assertTrue(response.headers["Content-Disposition"].startswith("attachment;"))
                self.assertIn("reference.html", response.headers["Content-Disposition"])
                self.assertIn("application/octet-stream", response.headers["Content-Type"])
                self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
