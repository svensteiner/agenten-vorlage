import base64
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from cockpit.public_security import PublicSecurityConfig
from cockpit.public_security import AuthContext
from cockpit.public_server import AuditLog, PublicApplication, WorkspaceQuota, make_public_handler
from cockpit.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://agents.example.test"


class PublicAuditLogTests(unittest.TestCase):
    def test_chain_reopens_without_plain_identity_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit" / "events.jsonl"
            secret = b"a" * 32
            context = AuthContext("private-tenant", "alice@example.test", ("member",))
            audit = AuditLog(path, secret)
            audit.append(
                request_id="a" * 32,
                context=context,
                method="POST",
                path="/api/jobs",
                status=202,
            )
            audit.append(
                request_id="b" * 32,
                context=context,
                method="GET",
                path="/api/jobs/" + "c" * 32,
                status=200,
            )
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("private-tenant", raw)
            self.assertNotIn("alice@example.test", raw)
            AuditLog(path, secret)

            path.write_text(raw.replace('"status":202', '"status":201', 1), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "integrity"):
                AuditLog(path, secret)

    def test_initialized_audit_cannot_silently_restart_after_log_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit" / "events.jsonl"
            secret = b"d" * 32
            AuditLog(path, secret)
            path.unlink()
            with self.assertRaisesRegex(RuntimeError, "missing"):
                AuditLog(path, secret)

    def test_audit_cannot_restart_if_log_and_local_marker_are_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit" / "events.jsonl"
            secret = b"e" * 32
            audit = AuditLog(path, secret)
            path.unlink()
            audit.marker.unlink()
            with self.assertRaisesRegex(RuntimeError, "missing"):
                AuditLog(path, secret)

    def test_existing_empty_audit_directory_is_not_treated_as_fresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit" / "events.jsonl"
            path.parent.mkdir()
            with self.assertRaisesRegex(RuntimeError, "initialization evidence"):
                AuditLog(path, b"f" * 32)

    def test_rotation_is_bounded_chained_and_reopenable(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "audit" / "events.jsonl"
            secret = b"r" * 32
            audit = AuditLog(path, secret, max_bytes=64 * 1024)
            for index in range(300):
                audit.append(
                    request_id=f"{index:032x}",
                    context=None,
                    method="GET",
                    path="/api/jobs/" + "a" * 256,
                    status=200,
                )
            raw = path.read_text(encoding="utf-8")
            self.assertLessEqual(path.stat().st_size, 64 * 1024 + 8_192)
            self.assertIn("audit_rotation", raw)
            self.assertTrue(audit.healthy(minimum_free_bytes=0))
            AuditLog(path, secret, max_bytes=64 * 1024)


class WorkspaceQuotaTests(unittest.TestCase):
    def test_prospective_write_is_atomic_and_cannot_cross_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspaces"
            target = root / "default" / "first.txt"
            target.parent.mkdir(parents=True)
            quota = WorkspaceQuota(root, max_bytes=5, max_files=1)
            quota.write(target, b"12345")
            with self.assertRaisesRegex(ContractError, "byte quota"):
                quota.write(target, b"123456")
            with self.assertRaisesRegex(ContractError, "file quota"):
                quota.write(target.parent / "second.txt", b"")
            self.assertEqual(b"12345", target.read_bytes())
            self.assertFalse((target.parent / "second.txt").exists())

    def test_workspace_write_counts_state_outside_the_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_root = Path(temporary) / "user"
            workspace_root = user_root / "workspaces"
            target = workspace_root / "default" / "result.txt"
            target.parent.mkdir(parents=True)
            state = user_root / "state"
            state.mkdir()
            (state / "conversation.json").write_bytes(b"12345")
            quota = WorkspaceQuota(
                user_root,
                allowed_root=workspace_root,
                max_bytes=5,
                max_files=10,
            )
            with self.assertRaisesRegex(ContractError, "byte quota"):
                quota.write(target, b"x")
            self.assertFalse(target.exists())

    def test_user_state_and_parallel_writes_share_one_prospective_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "user"
            (root / "workspaces").mkdir(parents=True)
            quota = WorkspaceQuota(
                root,
                allowed_root=root / "workspaces",
                max_bytes=6,
                max_files=2,
            )
            barrier = threading.Barrier(2)
            outcomes = []

            def write(name: str) -> None:
                barrier.wait()
                try:
                    quota.write_user(root / "state" / name, b"123456")
                    outcomes.append("written")
                except ContractError:
                    outcomes.append("rejected")

            workers = [threading.Thread(target=write, args=(f"{index}.json",)) for index in range(2)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=2)

            self.assertEqual(["rejected", "written"], sorted(outcomes))
            self.assertEqual((6, 1), quota.usage())
            self.assertTrue(quota.within_limits())

    def test_rejected_write_creates_no_directories_and_directory_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "user"
            workspace = root / "workspaces"
            workspace.mkdir(parents=True)
            quota = WorkspaceQuota(
                root,
                allowed_root=workspace,
                max_bytes=1,
                max_files=10,
                max_directories=2,
            )
            rejected_parent = workspace / "a" / "b"
            with self.assertRaisesRegex(ContractError, "byte quota"):
                quota.write(rejected_parent / "rejected.txt", b"xx")
            self.assertFalse(rejected_parent.exists())

            quota.write(workspace / "one" / "accepted.txt", b"x")
            with self.assertRaisesRegex(ContractError, "directory quota"):
                quota.write(workspace / "two" / "deep" / "blocked.txt", b"")
            self.assertFalse((workspace / "two").exists())


class PublicServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = PublicApplication(
            security=PublicSecurityConfig(
                public_origin=ORIGIN,
                trusted_proxy_cidrs=("127.0.0.1/32",),
                csrf_secret=b"c" * 32,
            ),
            data_root=Path(self.temporary.name) / "data",
            base_agents_root=ROOT / "agents",
            identity_secret=b"i" * 32,
            allowed_backends={"demo"},
            per_user_requests_per_minute=100,
            per_tenant_requests_per_minute=200,
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_public_handler(self.app))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.app.wait_for_jobs(10)
        self.temporary.cleanup()

    @staticmethod
    def identity(user: str, *, roles: str = "member,reviewer", tenant: str = "tenant-a") -> dict[str, str]:
        return {
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "agents.example.test",
            "X-Agent-Tenant": tenant,
            "X-Agent-User": user,
            "X-Agent-Roles": roles,
            "Cookie": f"_oauth2_proxy=session-{user}",
        }

    def request(self, path: str, *, headers=None, method="GET", body=None):
        request = Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={**(headers or {}), **({"Content-Type": "application/json"} if body is not None else {})},
            method=method,
        )
        try:
            with urlopen(request, timeout=5) as response:
                raw = response.read()
                return response.status, dict(response.headers), json.loads(raw) if raw else None
        except HTTPError as exc:
            raw = exc.read()
            return exc.code, dict(exc.headers), json.loads(raw) if raw else None

    def session(self, user: str, **kwargs):
        headers = self.identity(user, **kwargs)
        status, response_headers, value = self.request("/api/session", headers=headers)
        self.assertEqual(200, status, value)
        self.assertIn("csrf_token", value)
        self.assertEqual("max-age=31536000; includeSubDomains", response_headers["Strict-Transport-Security"])
        return headers, value["csrf_token"]

    def cached_runtime(self, user: str):
        return self.app.provisioner.runtime("tenant-a", user, self.app._factory)

    def test_attachment_quota_rejects_the_prospective_write_without_overshoot(self):
        headers, token = self.session("quota-upload")
        mutation = {**headers, "Origin": ORIGIN, "X-CSRF-Token": token}
        conversation_id = "1" * 32
        status, _response_headers, value = self.request(
            "/api/conversations",
            headers=mutation,
            method="POST",
            body={
                "request_id": conversation_id,
                "agent": "programming-agent",
                "workspace": "default",
                "backend": "demo",
                "model": "",
                "title": "Quota upload",
            },
        )
        self.assertEqual(201, status, value)
        cached = self.cached_runtime("quota-upload")
        before = cached.quota.usage()
        cached.quota.max_bytes = before[0] + 100

        status, _response_headers, value = self.request(
            f"/api/conversations/{conversation_id}/attachments",
            headers=mutation,
            method="POST",
            body={
                "request_id": "2" * 32,
                "name": "bounded.txt",
                "content_base64": base64.b64encode(b"x" * 1_000).decode("ascii"),
            },
        )
        self.assertEqual((507, {"error": "quota_exceeded"}), (status, value))
        self.assertEqual(before, cached.quota.usage())
        self.assertEqual([], list((cached.paths.state_root / "attachments").rglob("*.json")))

    def test_parallel_dialog_posts_allow_only_the_write_that_fits(self):
        headers, token = self.session("quota-dialog")
        mutation = {**headers, "Origin": ORIGIN, "X-CSRF-Token": token}

        def create_dialog(request_id: str):
            return self.request(
                "/api/conversations",
                headers=mutation,
                method="POST",
                body={
                    "request_id": request_id,
                    "agent": "programming-agent",
                    "workspace": "default",
                    "backend": "demo",
                    "model": "",
                    "title": "Quota sample",
                },
            )

        status, _headers, value = create_dialog("3" * 32)
        self.assertEqual(201, status, value)
        cached = self.cached_runtime("quota-dialog")
        sample = cached.paths.state_root / "conversations" / ("3" * 32 + ".json")
        sample_size = sample.stat().st_size
        sample.unlink()
        baseline = cached.quota.usage()
        cached.quota.max_bytes = baseline[0] + sample_size
        results = []

        def post(request_id: str) -> None:
            status_code, _headers, body = create_dialog(request_id)
            results.append((status_code, body))

        workers = [threading.Thread(target=post, args=(character * 32,)) for character in ("4", "5")]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)

        self.assertEqual([201, 507], sorted(status for status, _body in results))
        self.assertIn({"error": "quota_exceeded"}, [body for _status, body in results])
        self.assertLessEqual(cached.quota.usage()[0], cached.quota.max_bytes)
        self.assertEqual(1, len(list((cached.paths.state_root / "conversations").glob("*.json"))))

    def test_health_is_minimal_but_every_product_route_requires_identity(self):
        status, _headers, value = self.request("/api/health")
        self.assertEqual((200, {"status": "ok"}), (status, value))
        status, _headers, value = self.request("/api/agents")
        self.assertEqual(401, status)
        self.assertEqual({"error": "authentication_required"}, value)

    def test_authenticated_surface_uses_resource_ids_and_csrf(self):
        headers, token = self.session("alice")
        status, _response_headers, agents = self.request("/api/agents", headers=headers)
        self.assertEqual(200, status)
        assistant = next(item for item in agents["agents"] if item["id"] == "programming-agent")
        self.assertEqual("programming-agent", assistant["path"])
        self.assertNotIn(str(Path(self.temporary.name)), json.dumps(agents))

        payload = {
            "agent": "programming-agent",
            "workspace": "default",
            "backend": "demo",
            "task": "Public multi-user smoke.",
        }
        status, _response_headers, value = self.request("/api/jobs", headers=headers, method="POST", body=payload)
        self.assertEqual(403, status)
        self.assertEqual("csrf_rejected", value["error"])

        mutation_headers = {**headers, "Origin": ORIGIN, "X-CSRF-Token": token}
        status, _response_headers, job = self.request("/api/jobs", headers=mutation_headers, method="POST", body=payload)
        self.assertEqual(202, status, job)
        self.assertEqual("programming-agent", job["agent"])
        self.assertEqual("default", job["workspace"])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status, _response_headers, job = self.request("/api/jobs/" + job["job_id"], headers=headers)
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.03)
        self.assertEqual("completed", job["status"], job)
        self.assertNotIn(str(Path(self.temporary.name)), json.dumps(job))
        audit = (Path(self.temporary.name) / "data" / "audit" / "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("Public multi-user smoke.", audit)
        self.assertNotIn("alice", audit)

    def test_duplicate_session_cookie_and_request_rate_are_rejected(self):
        headers = self.identity("alice")
        headers["Cookie"] = "_oauth2_proxy=first; _oauth2_proxy=second"
        status, _response_headers, value = self.request("/api/session", headers=headers)
        self.assertEqual((401, {"error": "authentication_required"}), (status, value))

        self.app.per_user_requests_per_minute = 1
        headers = self.identity("limited")
        status, _response_headers, _value = self.request("/api/session", headers=headers)
        self.assertEqual(200, status)
        status, response_headers, value = self.request("/api/agents", headers=headers)
        self.assertEqual((429, {"error": "rate_limited"}), (status, value))
        self.assertIn("Retry-After", response_headers)

    def test_aggregate_worker_budget_rejects_before_dispatch(self):
        acquired = [self.app.worker_semaphore.acquire(blocking=False) for _ in range(4)]
        self.assertTrue(all(acquired))
        try:
            headers, token = self.session("busy")
            status, response_headers, value = self.request(
                "/api/jobs",
                headers={**headers, "Origin": ORIGIN, "X-CSRF-Token": token},
                method="POST",
                body={
                    "agent": "programming-agent",
                    "workspace": "default",
                    "backend": "demo",
                    "task": "must not dispatch",
                },
            )
            self.assertEqual((503, {"error": "service_busy"}), (status, value))
            self.assertEqual("1", response_headers["Retry-After"])
        finally:
            for _ in acquired:
                self.app.worker_semaphore.release()

    def test_cross_user_and_cross_tenant_job_ids_are_not_authority(self):
        alice, token = self.session("alice")
        mutation = {**alice, "Origin": ORIGIN, "X-CSRF-Token": token}
        status, _headers, job = self.request("/api/jobs", headers=mutation, method="POST", body={
            "agent": "programming-agent", "workspace": "default", "backend": "demo", "task": "private",
        })
        self.assertEqual(202, status, job)
        job_id = job["job_id"]

        for identity in (self.identity("bob"), self.identity("alice", tenant="tenant-b")):
            status, _headers, value = self.request("/api/jobs/" + job_id, headers=identity)
            self.assertEqual(404, status, value)
            self.assertEqual("job_not_found", value["error"])

    def test_cross_user_conversation_and_job_mutations_return_not_found(self):
        alice, alice_token = self.session("alice")
        alice_mutation = {**alice, "Origin": ORIGIN, "X-CSRF-Token": alice_token}
        conversation_id = "a" * 32
        status, _headers, conversation = self.request(
            "/api/conversations",
            headers=alice_mutation,
            method="POST",
            body={
                "request_id": conversation_id,
                "agent": "programming-agent",
                "workspace": "default",
                "backend": "demo",
                "model": "",
                "title": "Private dialog",
            },
        )
        self.assertEqual(201, status, conversation)

        status, _headers, value = self.request("/api/conversations/" + conversation_id, headers=self.identity("bob"))
        self.assertEqual((404, {"error": "not_found"}), (status, value))

        status, _headers, job = self.request(
            "/api/jobs",
            headers=alice_mutation,
            method="POST",
            body={"agent": "programming-agent", "workspace": "default", "backend": "demo", "task": "private"},
        )
        self.assertEqual(202, status, job)
        bob, bob_token = self.session("bob")
        bob_mutation = {**bob, "Origin": ORIGIN, "X-CSRF-Token": bob_token}
        for suffix, body in (
            ("/resume", {"feedback": "retry", "acknowledge_interruption": True}),
            ("/approval", {"approval_id": "b" * 32, "decision": "reject"}),
        ):
            status, _headers, value = self.request(
                f"/api/jobs/{job['job_id']}{suffix}", headers=bob_mutation, method="POST", body=body
            )
            self.assertEqual((404, {"error": "not_found"}), (status, value))
        status, _headers, value = self.request(
            f"/api/jobs/{job['job_id']}/artifacts?path=demo-result.md", headers=bob
        )
        self.assertEqual((404, {"error": "not_found"}), (status, value))

    def test_roles_and_public_path_boundary_are_enforced(self):
        viewer, viewer_token = self.session("viewer", roles="viewer")
        status, _headers, value = self.request(
            "/api/jobs",
            headers={**viewer, "Origin": ORIGIN, "X-CSRF-Token": viewer_token},
            method="POST",
            body={"agent": "programming-agent", "workspace": "default", "backend": "demo", "task": "no"},
        )
        self.assertEqual(403, status, value)
        self.assertEqual("forbidden", value["error"])

        status, _headers, value = self.request("/api/providers/deepseek", headers=viewer)
        self.assertEqual(200, status, value)
        self.assertNotIn("api_key", value)
        status, _headers, value = self.request(
            "/api/providers/deepseek",
            headers={**viewer, "Origin": ORIGIN, "X-CSRF-Token": viewer_token},
            method="POST",
            body={"action": "save", "api_key": "must-not-be-accepted"},
        )
        self.assertEqual((403, {"error": "forbidden"}), (status, value))

        member, token = self.session("member")
        status, _headers, value = self.request(
            "/api/jobs",
            headers={**member, "Origin": ORIGIN, "X-CSRF-Token": token},
            method="POST",
            body={"agent": str(ROOT / "agents" / "programming-agent"), "workspace": str(ROOT), "backend": "demo", "task": "escape"},
        )
        self.assertEqual(400, status, value)
        self.assertNotIn(str(ROOT), json.dumps(value))

    def test_readiness_is_fail_closed_for_unsafe_backend_configuration(self):
        status, _headers, value = self.request("/api/readiness")
        self.assertEqual((200, {"status": "ready"}), (status, value))
        unsafe = PublicApplication(
            security=self.app.security,
            data_root=Path(self.temporary.name) / "unsafe",
            base_agents_root=ROOT / "agents",
            identity_secret=b"u" * 32,
            allowed_backends={"codex"},
        )
        self.assertFalse(unsafe.ready())
        missing_secret = PublicApplication(
            security=self.app.security,
            data_root=Path(self.temporary.name) / "missing-secret",
            base_agents_root=ROOT / "agents",
            identity_secret=b"m" * 32,
            allowed_backends={"deepseek"},
        )
        self.assertFalse(missing_secret.ready())
        managed = PublicApplication(
            security=self.app.security,
            data_root=Path(self.temporary.name) / "managed",
            base_agents_root=ROOT / "agents",
            identity_secret=b"d" * 32,
            allowed_backends={"deepseek"},
            deepseek_api_key="managed-test-key",
        )
        self.assertTrue(managed.ready())


if __name__ == "__main__":
    unittest.main()
