import base64
import json
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.attachments import Attachments


class AttachmentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Attachments(self.temp.name)
        self.binding = {"conversation_id": "a" * 32, "company": "Acme",
                        "agent": "agent", "workspace": "workspace"}

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, request="b" * 32, name="note.txt", text="Hällo"):
        return {"request_id": request, "name": name,
                "content_base64": base64.b64encode(text.encode()).decode()}

    def test_round_trip_unicode_and_restart(self):
        metadata = self.store.put(self.binding, self.payload())
        self.assertEqual(metadata["name"], "note.txt")
        self.assertEqual(self.store.read(self.binding, metadata["id"]),
                         {"metadata": metadata, "text": "Hällo"})
        self.assertEqual(self.store.download(self.binding, metadata["id"]), ("Hällo".encode(), "note.txt"))
        restarted = Attachments(self.temp.name)
        self.assertEqual(restarted.put(self.binding, self.payload()), metadata)

    def test_bom_is_accepted_but_nul_and_binary_rejected(self):
        bom = base64.b64encode(b"\xef\xbb\xbfhello\n").decode()
        result = self.store.put(self.binding, {"request_id": "c" * 32, "name": "x.md", "content_base64": bom})
        self.assertEqual(self.store.read(self.binding, result["id"])["text"], "hello\n")
        binary = base64.b64encode(b"\xff\xfe").decode()
        with self.assertRaises(ContractError):
            self.store.put(self.binding, {"request_id": "d" * 32, "name": "x.md", "content_base64": binary})
        nul = base64.b64encode(b"a\x00b").decode()
        with self.assertRaises(ContractError):
            self.store.put(self.binding, {"request_id": "e" * 32, "name": "x.md", "content_base64": nul})

    def test_limits_paths_and_duplicate_mismatch(self):
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(name="..\\escape.txt"))
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(name="x.exe"))
        self.store.put(self.binding, self.payload())
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(text="changed"))
        too_big = base64.b64encode(b"x" * 32769).decode()
        with self.assertRaises(ContractError):
            self.store.put(self.binding, {"request_id": "f" * 32, "name": "x.txt", "content_base64": too_big})
        for index in range(1, 20):
            request = f"{index:032x}"
            self.store.put(self.binding, self.payload(request=request, name=f"{index}.txt", text="x"))
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(request="1" * 32, name="last.txt"))

    def test_binding_and_integrity_are_verified(self):
        metadata = self.store.put(self.binding, self.payload())
        other = dict(self.binding, conversation_id="c" * 32)
        with self.assertRaises(ContractError):
            self.store.read(other, metadata["id"])
        with self.assertRaises(ContractError):
            self.store.read(dict(self.binding, company="Other"), metadata["id"])
        with self.assertRaises(ContractError):
            self.store.put(dict(self.binding, company="Other"), self.payload())
        path = Path(self.temp.name) / "attachments" / self.binding["conversation_id"] / (metadata["id"] + ".json")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["content_base64"] = base64.b64encode(b"tampered").decode()
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ContractError):
            self.store.download(self.binding, metadata["id"])
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload())

    def test_parallel_duplicate_uploads_create_one_immutable_record(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.store.put(self.binding, self.payload()), range(8)))
        self.assertEqual(1, len({item["id"] for item in results}))
        self.assertEqual(1, len(list(self.store.directory.rglob("*.json"))))

    @patch("cockpit.attachments._MAX_TOTAL_BYTES", 512 * 1024)
    def test_total_byte_quota_and_retry_at_capacity(self):
        first = None
        for number in range(16):
            metadata = self.store.put(self.binding, self.payload(request=f"{number:032x}", text="x" * 32768))
            if number == 0:
                first = metadata
        self.assertEqual(first, self.store.put(self.binding, self.payload(request="0" * 32, text="x" * 32768)))
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(request="f" * 32, text="x"))

    def test_corrupt_store_does_not_bypass_quota_or_retry_identity(self):
        item = self.store.put(self.binding, self.payload())
        path = self.store.directory / self.binding["conversation_id"] / (item["id"] + ".json")
        path.write_text("[]")
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(request="f" * 32))


if __name__ == "__main__":
    unittest.main()
