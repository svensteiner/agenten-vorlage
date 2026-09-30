import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.attachments import Attachments


_FIXTURE = Path(__file__).parent / "fixtures" / "ocr" / "reference.png"
PNG = _FIXTURE.read_bytes() if _FIXTURE.is_file() else b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


class ImageAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Attachments(self.temp.name)
        self.binding = {"conversation_id": "a" * 32, "company": "Acme",
                        "agent": "agent", "workspace": "workspace"}

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, request="b" * 32, name="scan.png", data=PNG):
        return {"request_id": request, "name": name,
                "content_base64": base64.b64encode(data).decode("ascii")}

    @staticmethod
    def ocr_result(text="Invoice 123", language="en-US"):
        return 0, json.dumps({"text": text, "extraction_method": "windows-ocr", "language": language}), ""

    def test_upload_context_download_and_restart_reuse_persisted_ocr(self):
        with patch("cockpit.attachments._process_result", return_value=self.ocr_result()) as process:
            metadata = self.store.put(self.binding, self.payload())
            self.assertEqual("windows-ocr", metadata["extraction_method"])
            self.assertEqual("en-US", metadata["language"])
            self.assertEqual({"metadata": metadata, "text": "Invoice 123"},
                             self.store.read(self.binding, metadata["id"]))
            self.assertEqual((PNG, "scan.png"), self.store.download(self.binding, metadata["id"]))
            restarted = Attachments(self.temp.name)
            self.assertEqual(metadata, restarted.put(self.binding, self.payload()))
            process.assert_called_once()

    def test_image_ocr_contract_errors_are_generic_and_bounded(self):
        with self.assertRaises(ContractError) as corrupt:
            self.store.put(self.binding, self.payload(data=b"not-an-image"))
        self.assertIn("corrupt", str(corrupt.exception).lower())
        with patch("cockpit.attachments._process_result", return_value=(1, '{"error":"private"}', "secret")):
            with self.assertRaises(ContractError) as unavailable:
                self.store.put(self.binding, self.payload(request="c" * 32))
        self.assertNotIn("private", str(unavailable.exception))
        with patch("cockpit.attachments._process_result", return_value=self.ocr_result(language="en-US\nsecret")):
            with self.assertRaises(ContractError):
                self.store.put(self.binding, self.payload(request="f" * 32))
        with patch("cockpit.attachments._process_result", side_effect=subprocess.TimeoutExpired("ocr", 12)):
            with self.assertRaises(ContractError) as timed_out:
                self.store.put(self.binding, self.payload(request="d" * 32))
        self.assertIn("Zeitlimit", str(timed_out.exception))

    def test_corrupt_persisted_ocr_metadata_fails_closed_without_rerun(self):
        with patch("cockpit.attachments._process_result", return_value=self.ocr_result()):
            metadata = self.store.put(self.binding, self.payload())
        path = Path(self.temp.name) / "attachments" / self.binding["conversation_id"] / f"{metadata['id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record.pop("extraction_method")
        path.write_text(json.dumps(record), encoding="utf-8")
        with patch("cockpit.attachments._process_result", side_effect=AssertionError("OCR must not rerun")):
            with self.assertRaises(ContractError):
                self.store.read(self.binding, metadata["id"])
            with self.assertRaises(ContractError):
                self.store.put(self.binding, self.payload())

    def test_image_limits_and_metadata_are_scoped(self):
        oversized = PNG + b"x" * (2 * 1024 * 1024)
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(data=oversized))
        with patch("cockpit.attachments._process_result", return_value=self.ocr_result(language="de-DE")):
            image = self.store.put(self.binding, self.payload())
        self.assertEqual({"extraction_method", "language"}, set(image) - {"id", "name", "size", "sha256", "created_at"})
        text = self.store.put(self.binding, {
            "request_id": "e" * 32, "name": "note.txt",
            "content_base64": base64.b64encode(b"plain").decode("ascii")
        })
        self.assertNotIn("extraction_method", text)
        self.assertNotIn("language", text)

    @unittest.skipUnless(sys.platform == "win32", "Windows OCR is only available on Windows")
    def test_real_windows_ocr_fixture_flows_through_conversation_and_restart(self):
        from agentkit.scaffold import create
        from cockpit.conversations import Conversations
        from cockpit.server import JobManager

        root = Path(self.temp.name) / "studio"
        agent = create(root / "agents" / "assistant", "developer", "assistant", "Company")
        manager = JobManager(root)
        dialogs = Conversations(manager)
        conversation = dialogs.create({
            "request_id": "1" * 32, "agent": str(agent), "backend": "demo",
            "workspace": str(agent / "workspace"), "title": "OCR",
        })
        fixture = Path(__file__).parent / "fixtures" / "ocr" / "reference.png"
        data = fixture.read_bytes()
        item = dialogs.upload(conversation["id"], {
            "request_id": "2" * 32, "name": "reference.png",
            "content_base64": base64.b64encode(data).decode("ascii"),
        })
        extracted = dialogs.attachments.read(dialogs._attachment_binding(dialogs._read(conversation["id"])), item["id"])["text"]
        self.assertIn("930", extracted)
        self.assertIn("4711", extracted)
        dialogs.send(conversation["id"], {
            "request_id": "3" * 32, "content": "Use the image reference.",
            "attachment_ids": [item["id"]],
        })
        job = manager.get("3" * 32)
        self.assertIsNotNone(job)
        job.thread.join(20)
        self.assertEqual("completed", job.status)
        self.assertIn("930", job.result["task"])
        self.assertFalse((agent / "workspace" / "reference.png").exists())

        restarted = Conversations(JobManager(root))
        self.assertEqual(item, restarted.get(conversation["id"])["messages"][0]["attachments"][0])
        self.assertEqual((data, "reference.png"), restarted.download(conversation["id"], item["id"]))


if __name__ == "__main__":
    unittest.main()
