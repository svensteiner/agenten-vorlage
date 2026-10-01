from __future__ import annotations

import io
import base64
import hashlib
import json
import ipaddress
import ssl
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import scripts.public_staging_acceptance as staging_acceptance

from scripts.public_staging_acceptance import (
    GITHUB_ACCEPTANCE_TARGET,
    MAX_RESPONSE_LIMIT,
    AcceptanceError,
    StagingClient,
    main,
    read_cookie_file,
    run,
    validate_origin,
)

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:  # pragma: no cover - optional test-only certificate helper
    x509 = None


def _certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = directory / "cert.pem"
    key_path = directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


@unittest.skipUnless(x509 is not None, "cryptography is needed for the local TLS fixture")
class PublicStagingAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        cls.cert, cls.key = _certificate(root)
        cls.created: set[str] = set()
        cls.github_payload = b"fixture"
        cls.github_blob_sha = hashlib.sha1(
            b"blob 7\0" + cls.github_payload,
            usedforsecurity=False,
        ).hexdigest()
        cls.github_sha_patch = mock.patch.object(
            staging_acceptance,
            "GITHUB_ACCEPTANCE_BLOB_SHA",
            cls.github_blob_sha,
        )
        cls.github_sha_patch.start()

        class Handler(BaseHTTPRequestHandler):
            server_version = "StagingFixture/1"

            def _cookie(self) -> str:
                raw = self.headers.get("Cookie", "")
                return "bob" if "_oauth2_proxy=bob" in raw else "alice"

            def _json(self, status: int, value: dict):
                data = json.dumps(value, separators=(",", ":")).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                if self.path == "/redirect":
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header("Location", "/api/health")
                    self.end_headers()
                    return
                if self.path == "/large":
                    data = b"x" * 4096
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if self.path == "/api/health":
                    if not self.headers.get("Cookie"):
                        self._json(401, {"error": "authentication_required"})
                        return
                    self._json(200, {"status": "ok"})
                    return
                if self.path == "/api/readiness":
                    if not self.headers.get("Cookie"):
                        self._json(401, {"error": "authentication_required"})
                        return
                    self._json(200, {"status": "ready"})
                    return
                if self.path == "/api/session":
                    user = self._cookie()
                    self._json(
                        200,
                        {
                            "authenticated": True,
                            "user_id": user,
                            "tenant_id": "fixture-tenant",
                            "roles": ["member", "reviewer"],
                            "csrf_token": "csrf-" + user,
                        },
                    )
                    return
                if self.path == "/api/config":
                    self._json(
                        200,
                        {
                            "default_workspace": "default",
                            "backends": [{"id": "demo", "available": True}],
                        },
                    )
                    return
                if self.path == "/api/agents":
                    self._json(200, {"agents": [{"id": "fixture-agent"}]})
                    return
                if self.path.startswith("/api/conversations/"):
                    conversation_id = self.path.rsplit("/", 1)[-1]
                    if self._cookie() == "alice" and conversation_id in self.server.created:
                        if self.server.hide_alice_resource:
                            self._json(404, {"error": "not_found"})
                        else:
                            self._json(200, {"id": conversation_id})
                    else:
                        self._json(404, {"error": "not_found"})
                    return
                self._json(404, {"error": "not_found"})

            def do_POST(self):  # noqa: N802
                if self.path not in {"/api/conversations", "/api/connectors/github/preview"}:
                    self._json(404, {"error": "not_found"})
                    return
                if self.headers.get("Origin") != self.server.origin:
                    self._json(403, {"error": "csrf_rejected"})
                    return
                user = self._cookie()
                if self.headers.get("X-CSRF-Token") != "csrf-" + user:
                    self._json(403, {"error": "csrf_rejected"})
                    return
                size = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(size))
                if self.path == "/api/connectors/github/preview":
                    if payload != GITHUB_ACCEPTANCE_TARGET:
                        self._json(400, {"error": "invalid_request"})
                        return
                    blob_sha = self.server.github_blob_sha
                    github_payload = b"altered" if self.server.forge_github_content else self.server.github_payload
                    source_url = (
                        "https://github.com/Anil-matcha/Open-Dots/blob/"
                        + GITHUB_ACCEPTANCE_TARGET["ref"]
                        + "/README.md"
                    )
                    snapshot = (
                        "GitHub source: Anil-matcha/Open-Dots@"
                        + GITHUB_ACCEPTANCE_TARGET["ref"]
                        + " README.md (blob "
                        + blob_sha
                        + ")\nSource URL: "
                        + source_url
                        + "\n\n"
                    ).encode("ascii") + github_payload
                    self._json(
                        200,
                        {
                            "name": "github-README.md.txt",
                            "size": len(snapshot),
                            "content_base64": base64.b64encode(snapshot).decode("ascii"),
                            "text": snapshot.decode("ascii"),
                            "source": {
                                **GITHUB_ACCEPTANCE_TARGET,
                                "blob_sha": blob_sha,
                                "url": source_url,
                            },
                        },
                    )
                    return
                self.server.created.add(payload["request_id"])
                self._json(201, {"id": payload["request_id"], "backend": payload["backend"]})

            def log_message(self, format, *args):
                return

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.created = cls.created
        cls.server.hide_alice_resource = False
        cls.server.forge_github_content = False
        cls.server.github_blob_sha = cls.github_blob_sha
        cls.server.github_payload = cls.github_payload
        cls.origin = f"https://127.0.0.1:{cls.server.server_port}"
        cls.server.origin = cls.origin
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cls.cert, cls.key)
        cls.server.socket = tls.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.github_sha_patch.stop()
        cls.temporary.cleanup()

    def _args(self, *extra: str) -> list[str]:
        root = Path(self.temporary.name)
        alice = root / "alice.cookie"
        bob = root / "bob.cookie"
        alice.write_text("_oauth2_proxy=alice-secret", encoding="utf-8")
        bob.write_text("Cookie: _oauth2_proxy=bob-secret", encoding="utf-8")
        return [
            "--live-staging",
            "--origin",
            self.origin,
            "--alice-cookie-file",
            str(alice),
            "--bob-cookie-file",
            str(bob),
            "--ca-file",
            str(self.cert),
            *extra,
        ]

    def test_success_path_checks_isolation_and_never_emits_cookie_or_csrf(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(self._args())
        self.assertEqual(0, code)
        rendered = output.getvalue()
        self.assertNotIn("alice-secret", rendered)
        self.assertNotIn("bob-secret", rendered)
        self.assertNotIn("csrf-alice", rendered)
        result = json.loads(rendered)
        self.assertEqual({"ok": True, "status": "passed", "category": "success"}, {
            key: result[key] for key in ("ok", "status", "category")
        })
        self.assertTrue(all(result["checks"].values()))
        self.assertTrue(result["checks"]["github_preview"])

    def test_github_preview_rejects_content_that_does_not_match_pinned_blob(self):
        self.server.forge_github_content = True
        try:
            result = run(self._args())
        finally:
            self.server.forge_github_content = False
        self.assertFalse(result["ok"])
        self.assertEqual("github_connector", result["category"])
        self.assertFalse(result["checks"]["github_preview"])

    def test_cookie_file_and_origin_validation_are_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cookie"
            path.write_text("_oauth2_proxy=secret\nsecond-header: leaked", encoding="utf-8")
            with self.assertRaises(AcceptanceError):
                read_cookie_file(path)
        for value in (
            "http://example.test",
            "https://example.test/",
            "https://user:password@example.test",
            "https://example.test?query=1",
            "https://example.test/path",
        ):
            with self.subTest(value=value):
                with self.assertRaises(AcceptanceError):
                    validate_origin(value)

    def test_redirects_and_response_bounds_fail_closed(self):
        client = StagingClient(self.origin, ca_file=str(self.cert), response_limit=1024)
        with self.assertRaises(AcceptanceError) as redirect:
            client.request("/redirect")
        self.assertEqual("redirect_refused", redirect.exception.category)
        with self.assertRaises(AcceptanceError) as large:
            client.request("/large")
        self.assertEqual("response_too_large", large.exception.category)
        result = run(self._args("--max-response-bytes", str(MAX_RESPONSE_LIMIT + 1)))
        self.assertEqual("bounds", result["category"])

    def test_missing_live_acknowledgement_is_nonzero_and_sanitized(self):
        args = self._args()
        args.remove("--live-staging")
        result = run(args)
        self.assertEqual({"ok": False, "status": "failed", "category": "live_staging_acknowledgement", "checks": {}}, result)

    def test_bounded_read_only_soak_reports_only_metrics(self):
        result = run(self._args("--soak-requests", "5", "--soak-concurrency", "2"))
        self.assertTrue(result["ok"])
        soak = result["soak"]
        self.assertEqual(5, soak["requests"])
        self.assertEqual({"200": 5}, soak["status_counts"])
        self.assertGreaterEqual(soak["latency_ms"]["p99"], 0)
        self.assertNotIn("alice-secret", json.dumps(result))

    def test_isolation_requires_alice_to_retrieve_the_created_resource(self):
        self.server.hide_alice_resource = True
        try:
            result = run(self._args())
        finally:
            self.server.hide_alice_resource = False
        self.assertFalse(result["ok"])
        self.assertEqual("http_error", result["category"])
        self.assertFalse(result["checks"]["alice_resource_access"])


if __name__ == "__main__":
    unittest.main()
