import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class AssistantInstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "assistant", "developer", "assistant", "Company")
        self.manager = JobManager(self.root)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        self.server_thread = __import__("threading").Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(2)
        self.temp.cleanup()

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(self.base + path, data=data, method=method,
                          headers={"Content-Type": "application/json"} if data else {})
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())

    def test_http_read_write_cas_and_idempotent_retry(self):
        path = "/api/agents/instructions?agent=" + str(self.agent).replace("\\", "/")
        status, current = self.request("GET", path)
        self.assertEqual(200, status)
        self.assertEqual(current["revision"], hashlib.sha256((self.agent / "SOUL.md").read_bytes()).hexdigest())
        changed = self.request("POST", "/api/agents/instructions", {
            "agent": str(self.agent), "text": current["text"] + "\nOwner edit.", "revision": current["revision"]
        })[1]
        self.assertNotEqual(current["revision"], changed["revision"])
        self.assertEqual(changed, self.request("POST", "/api/agents/instructions", {
            "agent": str(self.agent), "text": changed["text"], "revision": "0" * 64
        })[1])
        with self.assertRaises(HTTPError) as error:
            self.request("POST", "/api/agents/instructions", {
                "agent": str(self.agent), "text": "Another edit", "revision": current["revision"]
            })
        self.assertEqual(409, error.exception.code)

    def test_validation_and_symlink_are_rejected(self):
        current = self.manager.get_instructions(str(self.agent))
        for text in ("", "\x00bad", "a" * 32_001):
            with self.assertRaises(ContractError):
                self.manager.update_instructions({"agent": str(self.agent), "text": text, "revision": current["revision"]})
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "x", "revision": "bad"})
        soul = self.agent / "SOUL.md"
        backup = soul.read_bytes()
        soul.unlink()
        try:
            try:
                soul.symlink_to(self.agent / "README.md")
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    self.skipTest("Windows symlink privilege is unavailable")
                raise
            with self.assertRaises(ContractError):
                self.manager.get_instructions(str(self.agent))
        finally:
            if soul.exists() or soul.is_symlink():
                soul.unlink()
            soul.write_bytes(backup)

    def test_legacy_job_blocks_instruction_edit_but_core_is_complete(self):
        current = self.manager.get_instructions(str(self.agent))
        job_id = "a" * 32
        (self.manager.state_dir / f"{job_id}.json").write_text(json.dumps({
            "job_id": job_id, "payload": {"agent": str(self.agent), "run_id": "b" * 32}, "status": "blocked"
        }), encoding="utf-8")
        self.manager._load()
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        captured = self.manager.capture_core(str(self.agent))
        self.assertIn("STATUS.md", captured["core_snapshot"])
        self.assertIn("WORKFLOW.md", captured["core_snapshot"])

    def test_unknown_canonical_job_state_fails_closed(self):
        current = self.manager.get_instructions(str(self.agent))
        job_id = "c" * 32
        (self.manager.state_dir / f"{job_id}.json").write_text("not-json", encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        self.assertEqual(current["revision"], self.manager.get_instructions(str(self.agent))["revision"])

    def test_nonterminal_snapshot_status_hash_and_identity_are_checked(self):
        current = self.manager.get_instructions(str(self.agent))
        job_id = "d" * 32
        job_file = self.manager.state_dir / f"{job_id}.json"
        base = {"job_id": job_id, "payload": {
            "agent": str(self.agent), "run_id": "e" * 32,
            "core_snapshot": "captured core", "core_sha256": "0" * 64,
        }, "status": "blocked"}
        value = json.loads(json.dumps(base))
        value["payload"]["core_snapshot"] = " "
        job_file.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        value = json.loads(json.dumps(base))
        value["status"] = "unknown"
        job_file.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        value = json.loads(json.dumps(base))
        value["payload"].pop("core_sha256")
        value["payload"]["run_id"] = "invalid"
        job_file.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ContractError):
            self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        job_file.unlink()

        run_id = "f" * 32
        run_dir = self.agent / ".runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text(json.dumps({
            "run_id": "0" * 32, "agent": "assistant", "status": "completed"
        }), encoding="utf-8")
        try:
            with self.assertRaises(ContractError):
                self.manager.update_instructions({"agent": str(self.agent), "text": "blocked", "revision": current["revision"]})
        finally:
            (run_dir / "state.json").unlink()
            run_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
