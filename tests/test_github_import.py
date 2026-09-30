import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class GitHubImportTests(unittest.TestCase):
    def test_preview_origin_and_immutable_attachment_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = create(root / "agents" / "github-demo", "developer", "github-demo", "Fixture")
            manager = JobManager(root)
            dialogs = Conversations(manager)
            conversation = dialogs.create({"request_id": "1" * 32, "agent": str(agent),
                                          "workspace": str(agent / "workspace"), "backend": "demo"})
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(manager))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            raw = b"Source: https://github.com/example/repository/blob/main/README.md\nGITHUB-IMPORT-930"
            preview = {"name": "github-README.md.txt", "size": len(raw), "text": raw.decode(),
                       "content_base64": base64.b64encode(raw).decode(), "source": {"blob_sha": "a" * 40}}
            payload = {"owner": "example", "repo": "repository", "path": "README.md", "ref": "main"}

            def post(path, data, origin=None):
                headers = {"Content-Type": "application/json"}
                if origin:
                    headers["Origin"] = origin
                return urlopen(Request(base + path, data=json.dumps(data).encode(), headers=headers), timeout=5)

            try:
                with patch("cockpit.server.preview_file", return_value=preview) as fetch:
                    with self.assertRaises(HTTPError) as rejected:
                        post("/api/connectors/github/preview", payload, "https://foreign.example")
                    self.assertEqual(403, rejected.exception.code)
                    fetch.assert_not_called()
                    with post("/api/connectors/github/preview", payload) as response:
                        loaded = json.loads(response.read())
                    fetch.assert_called_once_with(payload)
                    self.assertEqual(preview, loaded)
                    self.assertEqual([], manager.recent())
                    self.assertEqual([], dialogs.get(conversation["id"])["messages"])

                # The explicit import uses preview bytes, not a second network fetch.
                upload = {"request_id": "2" * 32, "name": loaded["name"],
                          "content_base64": loaded["content_base64"]}
                path = f"/api/conversations/{conversation['id']}/attachments"
                with patch("cockpit.server.preview_file", side_effect=AssertionError("must not refetch")):
                    with post(path, upload) as response:
                        attachment = json.loads(response.read())
                    with post(path, upload) as response:
                        self.assertEqual(attachment, json.loads(response.read()))
                    restored = Conversations(JobManager(root))
                    self.assertEqual((raw, preview["name"]), restored.download(conversation["id"], attachment["id"]))
                    changed = {**upload, "content_base64": base64.b64encode(b"Changed upstream").decode()}
                    with self.assertRaises(HTTPError) as rejected:
                        post(path, changed)
                    self.assertEqual(400, rejected.exception.code)
                    dialogs.send(conversation["id"], {"request_id": "3" * 32, "content": "Use this reference",
                                                       "attachment_ids": [attachment["id"]]})
                    job = manager.get("3" * 32)
                    job.thread.join(10)
                    self.assertFalse(job.thread.is_alive())
                    self.assertEqual("completed", job.status, job.error)
                    self.assertIn("GITHUB-IMPORT-930", job.result["task"])
                    self.assertIn("https://github.com/example/repository", job.result["task"])
                    self.assertFalse((agent / "workspace" / preview["name"]).exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(3)
