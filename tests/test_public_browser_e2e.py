from __future__ import annotations

import json
import ipaddress
import ssl
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cockpit.public_security import PublicSecurityConfig
from cockpit.public_server import BoundedThreadingHTTPServer, PublicApplication, make_public_handler

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from playwright.sync_api import sync_playwright
except ImportError:  # The normal unit matrix intentionally has no browser dependencies.
    x509 = None
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[1]


class _QuietTlsServer(BoundedThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], ssl.SSLEOFError):
            return
        super().handle_error(request, client_address)


def _certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_path = directory / "key.pem"
    cert_path = directory / "cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


@unittest.skipUnless(
    sync_playwright is not None and x509 is not None,
    "install the e2e extra and cryptography",
)
class PublicBrowserReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.app = PublicApplication(
            security=PublicSecurityConfig(
                public_origin="https://agents.example.test",
                trusted_proxy_cidrs=("127.0.0.1/32",),
                csrf_secret=b"b" * 32,
            ),
            data_root=cls.root / "data",
            base_agents_root=ROOT / "agents",
            identity_secret=b"i" * 32,
            identity_issuer="https://identity.example.test/realms/company",
            identity_client_id="agentkit-public-browser-test",
            allowed_backends={"demo"},
            per_user_requests_per_minute=200,
            per_tenant_requests_per_minute=400,
        )
        cls.server = _QuietTlsServer(
            ("127.0.0.1", 0), make_public_handler(cls.app), max_workers=8
        )
        cls.origin = f"https://127.0.0.1:{cls.server.server_port}"
        cls.app.security = PublicSecurityConfig(
            public_origin=cls.origin,
            trusted_proxy_cidrs=("127.0.0.1/32",),
            csrf_secret=b"b" * 32,
        )
        cls.cert_path, cls.key_path = _certificate(cls.root)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cls.cert_path, cls.key_path)
        cls.server.socket = tls.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temporary.cleanup()

    def new_page(self, user: str = "alice"):
        context = self.browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900},
            extra_http_headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": f"127.0.0.1:{self.server.server_port}",
                "X-Agent-Tenant": "browser-tenant",
                "X-Agent-User": user,
                "X-Agent-Roles": "member,reviewer",
            },
        )
        context.add_cookies(
            [{"name": "_oauth2_proxy", "value": f"session-{user}", "url": self.origin}]
        )
        page = context.new_page()
        errors: list[str] = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        self.addCleanup(context.close)
        return page, errors

    def test_public_authenticated_demo_workflow_and_browser_safety(self):
        page, console_errors = self.new_page()
        page.goto(self.origin + "/", wait_until="domcontentloaded")
        page.get_by_text("Verbunden", exact=True).wait_for(timeout=10_000)
        page.locator("#run").wait_for(state="visible", timeout=5_000)
        self.assertTrue(page.locator("#run").is_disabled() is False)
        self.assertEqual(1, page.locator("h1").count())
        unnamed = page.evaluate("""() => [...document.querySelectorAll('button,a,input,select,textarea')]
          .filter(e => {
            if (e.matches('input[type="hidden"]')) return false;
            const labelledBy = (e.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean)
              .map(id => document.getElementById(id)?.textContent || '').join(' ');
            const explicit = e.id ? document.querySelector(`label[for="${CSS.escape(e.id)}"]`)?.textContent || '' : '';
            const wrapping = e.closest('label')?.textContent || '';
            const native = ['BUTTON', 'A'].includes(e.tagName) ? e.textContent || '' :
              e.matches('input[type="button"],input[type="submit"]') ? e.value || '' : '';
            return ![e.getAttribute('aria-label') || '', labelledBy, explicit, wrapping, native,
              e.getAttribute('title') || ''].some(value => value.trim());
          }).map(e => e.outerHTML)""")
        self.assertEqual([], unnamed)

        page.locator("#task").fill("Öffentlicher Browser-Abnahmelauf")
        with page.expect_response(
            lambda response: response.url.endswith("/api/jobs") and response.request.method == "POST"
        ) as response_info:
            page.locator("#run").click()
        job = response_info.value.json()
        self.assertRegex(job["job_id"], r"^[0-9a-f]{32}$")
        self.assertEqual("default", job["workspace"])
        self.assertNotIn(str(self.root), json.dumps(job))

        approval = page.locator("#approvalCard")
        approval.wait_for(state="visible", timeout=10_000)
        self.assertEqual("write_file", page.locator("#approvalTool").inner_text())
        self.assertNotIn(str(self.root), page.locator("#approvalArguments").inner_text())
        page.locator("#approveAction").click()
        page.wait_for_function(
            "() => document.querySelector('#approvalCard')?.hidden === false",
            timeout=10_000,
        )
        page.locator("#approveAction").click()
        page.wait_for_function(
            "() => document.querySelector('#jobStatus')?.textContent.trim() === 'Abgeschlossen'",
            timeout=20_000,
        )
        self.assertIn("ACCEPTED", page.locator("#timeline").inner_text())
        self.assertNotIn(str(self.root), page.locator("body").inner_text())
        self.assertEqual([], console_errors)

    def test_user_sessions_are_isolated_in_browser(self):
        alice, _ = self.new_page("alice")
        alice.goto(self.origin + "/", wait_until="domcontentloaded")
        alice.get_by_text("Verbunden", exact=True).wait_for(timeout=10_000)
        alice.locator("#task").fill("Alice private browser job")
        with alice.expect_response(lambda response: response.url.endswith("/api/jobs") and response.request.method == "POST") as response_info:
            alice.locator("#run").click()
        job_id = response_info.value.json()["job_id"]

        bob, _ = self.new_page("bob")
        bob.goto(self.origin + "/", wait_until="domcontentloaded")
        bob.get_by_text("Verbunden", exact=True).wait_for(timeout=10_000)
        response = bob.request.get(self.origin + "/api/jobs/" + job_id)
        self.assertEqual(404, response.status)
        self.assertEqual("job_not_found", response.json()["error"])
        self.assertNotIn("Alice private browser job", bob.locator("body").inner_text())


if __name__ == "__main__":
    unittest.main()
