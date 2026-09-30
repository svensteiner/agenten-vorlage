import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

COCKPIT = Path(__file__).resolve().parents[1] / "cockpit"
sys.path.insert(0, str(COCKPIT))

from server import Job, JobManager, ThreadingHTTPServer, make_handler  # noqa: E402
from agentkit.contracts import ContractError  # noqa: E402
from agentkit.scaffold import create  # noqa: E402


class CockpitHttpTests(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.TemporaryDirectory()
        self.manager = JobManager(state_dir=Path(self.state.name))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.state.cleanup()

    def get_json(self, path):
        with urlopen(self.base + path, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_agents_endpoint_lists_programming_agent(self):
        data = self.get_json("/api/agents")
        self.assertTrue(any(item["id"] == "programming-agent" for item in data["agents"]))

    def test_codex_configuration_requires_selected_windows_sandbox(self):
        for configured in (False, True):
            with self.subTest(sandbox_configured=configured), patch(
                "server.codex_readiness",
                return_value={"installed": True, "credentials_present": True,
                              "sandbox_configured": configured},
            ):
                data = self.get_json("/api/config")
            backend = next(item for item in data["backends"] if item["id"] == "codex")
            self.assertEqual(backend["available"], configured)
            if not configured:
                self.assertIn("Windows-Sandbox", backend["detail"])

    def test_demo_job_runs_through_http(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = {
                "agent": str(Path(__file__).resolve().parents[1] / "agents" / "programming-agent"),
                "backend": "demo",
                "workspace": directory,
                "task": "Demonstriere den lokalen Cockpit-Lauf.",
            }
            request = Request(
                self.base + "/api/jobs",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=3) as response:
                job = json.loads(response.read().decode("utf-8"))
            self.assertIn(job["status"], {"queued", "running", "completed"})
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                job = self.get_json("/api/jobs/" + job["job_id"])
                if job["status"] in {"completed", "blocked", "error"}:
                    break
                time.sleep(0.05)
            self.assertEqual("completed", job["status"], job.get("error") or job.get("result"))
            self.assertTrue((Path(directory) / "demo-result.md").is_file())

    def test_job_history_is_persisted_and_listed(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = {
                "agent": str(Path(__file__).resolve().parents[1] / "agents" / "programming-agent"),
                "backend": "demo",
                "workspace": directory,
                "task": "Persistiere den Demo-Lauf.",
            }
            request = Request(
                self.base + "/api/jobs",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=3) as response:
                job = json.loads(response.read().decode("utf-8"))
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = self.get_json("/api/jobs/" + job["job_id"])
                if current["status"] == "completed":
                    break
                time.sleep(0.05)
            history = self.get_json("/api/jobs")
            self.assertTrue(any(item["job_id"] == job["job_id"] for item in history["jobs"]))
            restarted = JobManager(state_dir=Path(self.state.name))
            restored = restarted.get(job["job_id"])
            self.assertIsNotNone(restored)
            self.assertEqual("completed", restored.status)

    def test_cross_origin_and_rebinding_requests_are_rejected(self):
        for headers in ({"Origin": "https://evil.example"}, {"Host": "evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base + "/api/jobs", headers=headers), timeout=3)
            self.assertEqual(403, caught.exception.code)

    def test_invalid_http_bodies_fail_without_starting_jobs(self):
        for content, headers in ((b'{}', {"Content-Type": "text/plain"}), (b'[]', {"Content-Type": "application/json"}), (b'{', {"Content-Type": "application/json"}), (b'{"backend":[]}', {"Content-Type": "application/json"}), (b'{}', {"Content-Type": "application/json", "Content-Length": "-1"})):
            with self.subTest(content=content, headers=headers), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base + "/api/jobs", data=content, headers=headers), timeout=3)
            self.assertEqual(400, caught.exception.code)
        self.assertEqual([], self.manager.recent())

    def test_config_does_not_expose_provider_key(self):
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-secret-not-for-browser"}):
            config = self.get_json("/api/config")
        self.assertNotIn("test-secret-not-for-browser", json.dumps(config))
        self.assertTrue(next(b for b in config["backends"] if b["id"] == "deepseek")["available"])

    def test_inline_scripts_require_matching_content_hash(self):
        import base64
        import hashlib
        import re
        with urlopen(self.base + "/", timeout=3) as response:
            body = response.read()
            policy = response.headers["Content-Security-Policy"]
        script_policy = next(part for part in policy.split(";") if "script-src" in part)
        self.assertNotIn("unsafe-inline", script_policy)
        scripts = re.findall(rb"<script>(.*?)</script>", body, flags=re.DOTALL)
        self.assertTrue(scripts)
        for script in scripts:
            digest = base64.b64encode(hashlib.sha256(script).digest()).decode("ascii")
            self.assertIn("'sha256-" + digest + "'", script_policy)


class CockpitRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "test", "developer", "test", "test")
        self.manager = JobManager(self.root)
        self.payload = {"agent": str(self.agent), "workspace": str(self.agent / "workspace"), "backend": "demo", "task": "Demo"}

    def tearDown(self):
        for job in self.manager.recent():
            if job.thread:
                job.thread.join(5)
        self.temp.cleanup()

    def test_assistant_creation_is_persistent_and_rejects_traversal(self):
        assistant = self.manager.create_agent({"name": "writer", "profile": "research", "instructions": "Write clearly."})
        self.assertEqual("writer", assistant["id"])
        self.assertIn("Write clearly.", (Path(assistant["path"]) / "SOUL.md").read_text(encoding="utf-8"))
        with self.assertRaises(ContractError):
            self.manager.create_agent({"name": "../escape"})
        with self.assertRaises(ContractError):
            self.manager.create_agent({"name": "writer"})

    def test_run_identity_is_durable_before_worker_dispatch(self):
        with patch.object(self.manager, "_run"):
            job = self.manager.start(self.payload)
            job.thread.join(2)
        saved = json.loads(self.manager._job_file(job.job_id).read_text(encoding="utf-8"))
        self.assertEqual(32, len(saved["payload"]["run_id"]))
        restarted = JobManager(self.root)
        self.assertEqual("blocked", restarted.get(job.job_id).status)
        recovered = restarted.resume(job.job_id, "No worker ran; continue.", True)
        recovered.thread.join(5)
        self.assertEqual("completed", recovered.status)
        self.assertEqual(saved["payload"]["run_id"], recovered.result["run_id"])

    def test_capacity_and_double_resume_are_rejected(self):
        self.manager.max_active = 1
        with patch.object(self.manager, "_run"):
            job = self.manager.start(self.payload)
            job.thread.join(2)
            with self.assertRaises(ContractError):
                self.manager.start(self.payload)
            with self.assertRaises(ContractError):
                self.manager.resume(job.job_id, "Again", True)

    def test_bad_persisted_identity_cannot_escape_state_directory(self):
        malicious = {"job_id": "../escape", "payload": {}, "status": "running"}
        (self.manager.state_dir / "bad.json").write_text(json.dumps(malicious), encoding="utf-8")
        restarted = JobManager(self.root)
        self.assertEqual([], restarted.recent())
        self.assertFalse((self.manager.state_dir.parent / "escape.json").exists())

    def test_newest_jobs_are_listed_first(self):
        with patch.object(self.manager, "_run"):
            first = self.manager.start(self.payload)
            first.thread.join(2)
            second = self.manager.start(self.payload)
            second.thread.join(2)
        # Use distinct times: Windows clock resolution can give both starts the
        # same timestamp, which does not define a chronological ordering.
        first.created_at = "2026-09-30T10:00:00+00:00"
        second.created_at = "2026-09-30T10:00:01+00:00"
        self.assertEqual(second.job_id, self.manager.recent()[0].job_id)

    def test_unknown_backend_and_nonboolean_acknowledgment_are_rejected(self):
        with self.assertRaises(ContractError):
            self.manager.start({**self.payload, "backend": "unknown"})
        with self.assertRaises(ContractError):
            self.manager.resume("missing", "resume", "false")

    def test_followup_keeps_context_and_rejects_cross_workspace(self):
        parent = self.manager.start(self.payload)
        parent.thread.join(5)
        self.assertEqual("completed", parent.status)
        child = self.manager.start({**self.payload, "task": "Follow up", "parent_job_id": parent.job_id})
        child.thread.join(5)
        self.assertIn("Previous result", child.result["task"])
        self.assertEqual("Follow up", child.public()["task"])
        self.assertEqual(parent.job_id, child.public()["parent_job_id"])
        with self.assertRaises(ContractError):
            self.manager.start({**self.payload, "workspace": str(self.root), "parent_job_id": parent.job_id})

    def test_only_reported_artifacts_can_be_downloaded(self):
        job = self.manager.start(self.payload)
        job.thread.join(5)
        self.assertIn(b"ACCEPTED", self.manager.artifact(job.job_id, "demo-result.md"))
        for name in ("../agent.json", "unreported.txt"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.manager.artifact(job.job_id, name)
        (self.agent / "workspace" / "demo-result.md").write_bytes(b"x" * 2_000_001)
        with self.assertRaises(ContractError):
            self.manager.artifact(job.job_id, "demo-result.md")
        internal = self.agent / "workspace" / ".git" / "config"
        internal.parent.mkdir()
        internal.write_text("credential = secret", encoding="utf-8")
        report_record = next(
            record for record in job.result["history"] if "report" in record
        )
        report_record["report"]["artifacts"].append(".git/config")
        with self.assertRaises(ContractError):
            self.manager.artifact(job.job_id, ".git/config")

    @unittest.skipUnless(os.name == "nt", "NTFS alternate streams are Windows-only")
    def test_reported_alternate_data_stream_cannot_be_downloaded(self):
        job = self.manager.start(self.payload)
        job.thread.join(5)
        stream_name = "demo-result.md:private"
        Path(str(self.agent / "workspace" / "demo-result.md") + ":private").write_bytes(
            b"TOPSECRET"
        )
        report_record = next(
            record for record in job.result["history"] if "report" in record
        )
        report_record["report"]["artifacts"].append(stream_name)
        with self.assertRaises(ContractError):
            self.manager.artifact(job.job_id, stream_name)

    def test_missing_checkpoint_requires_explicit_acknowledgment(self):
        with patch.object(self.manager, "_run"):
            job = self.manager.start(self.payload)
            job.thread.join(2)
        restarted = JobManager(self.root)
        with self.assertRaises(ContractError):
            restarted.resume(job.job_id, "Continue", False)

    def test_start_is_idempotent_across_retry_and_restart(self):
        payload = {**self.payload, "request_id": "a" * 32}
        job = self.manager.start(payload)
        job.thread.join(5)
        replay = self.manager.start(payload)
        self.assertIs(job, replay)
        restarted = JobManager(self.root)
        restored = restarted.start(payload)
        self.assertEqual(job.job_id, restored.job_id)
        self.assertEqual(job.result["run_id"], restored.result["run_id"])
        self.assertIsNone(restored.thread)
        with self.assertRaises(ContractError):
            restarted.start({**payload, "task": "Changed payload"})

    def test_execution_context_is_part_of_idempotency_identity(self):
        payload = {**self.payload, "request_id": "a" * 32}
        with patch.object(self.manager, "_run"):
            job = self.manager.start(payload, conversation_id="b" * 32, execution_task="First context")
            job.thread.join(2)
            with self.assertRaises(ContractError):
                self.manager.start(payload, conversation_id="b" * 32, execution_task="Changed context")

    def test_followup_replay_does_not_require_parent_in_memory(self):
        parent = self.manager.start(self.payload)
        parent.thread.join(5)
        payload = {**self.payload, "task": "Follow up", "request_id": "a" * 32, "parent_job_id": parent.job_id}
        child = self.manager.start(payload)
        child.thread.join(5)
        self.manager.jobs.clear()
        replay = self.manager.start(payload)
        self.assertEqual(child.job_id, replay.job_id)
        self.assertEqual(child.result["run_id"], replay.result["run_id"])
        self.assertIsNone(replay.thread)

    def test_old_interrupted_job_is_recovered_outside_completed_history_cache(self):
        with patch.object(self.manager, "_run"):
            interrupted = self.manager.start(self.payload)
            interrupted.thread.join(2)
        for number in range(105):
            self.manager._persist(Job(f"{number:032x}", dict(interrupted.payload), status="completed"))
        restarted = JobManager(self.root)
        self.assertIn(interrupted.job_id, restarted.jobs)
        self.assertEqual("blocked", restarted.jobs[interrupted.job_id].status)
        self.assertEqual(100, sum(job.status == "completed" for job in restarted.jobs.values()))


if __name__ == "__main__":
    unittest.main()
