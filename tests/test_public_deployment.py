"""Static guardrails for the public deployment contract."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "public" / "docker-compose.production.yml"


class PublicDeploymentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose_text = COMPOSE.read_text(encoding="utf-8")
        cls.compose = yaml.safe_load(cls.compose_text)
        cls.services = cls.compose["services"]

    def test_public_artifacts_exist(self):
        for relative in (
            "Dockerfile.public",
            ".dockerignore",
            "deploy/public/Caddyfile",
            "deploy/public/secrets.example",
            "deploy/public/public.env.example",
            "deploy/public/requirements-build.lock",
            "deploy/public/requirements-runtime.lock",
            "docs/PUBLIC-DEPLOYMENT.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_dockerfile_requires_digest_and_uses_readiness(self):
        dockerfile = (ROOT / "Dockerfile.public").read_text(encoding="utf-8")
        self.assertIn("ARG PYTHON_BASE_IMAGE", dockerfile)
        self.assertIn("FROM ${PYTHON_BASE_IMAGE}", dockerfile)
        self.assertIn("@sha256:", dockerfile)
        self.assertNotIn("python:3.12.8", dockerfile)
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/api/readiness", dockerfile)
        self.assertIn("cockpit.public_server", dockerfile)
        self.assertNotIn("/var/run/docker.sock", dockerfile)
        self.assertIn("--require-hashes", dockerfile)
        self.assertIn("--no-build-isolation --no-deps", dockerfile)
        self.assertIn("requirements-runtime.lock", dockerfile)

    def test_public_python_dependency_closure_is_hash_locked_without_pytest(self):
        runtime = (ROOT / "deploy" / "public" / "requirements-runtime.lock").read_text(encoding="utf-8")
        build = (ROOT / "deploy" / "public" / "requirements-build.lock").read_text(encoding="utf-8")
        for lockfile in (runtime, build):
            requirements = [line for line in lockfile.splitlines() if "==" in line]
            hashes = [line for line in lockfile.splitlines() if "--hash=sha256:" in line]
            self.assertTrue(requirements)
            self.assertEqual(len(requirements), len(hashes))
        self.assertNotIn("pytest", runtime.lower())
        self.assertIn("setuptools==84.0.0", build)
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("docker build", workflow)
        self.assertIn("assert importlib.util.find_spec('pytest') is None", workflow)

    def test_only_tls_proxy_publishes_ports_and_app_is_private(self):
        self.assertNotIn("ports", self.services["app"])
        self.assertNotIn("ports", self.services["auth-proxy"])
        self.assertEqual(self.services["reverse-proxy"]["ports"], ["443:443", "80:80"])
        self.assertEqual(self.services["app"]["networks"], ["frontend", "egress"])
        self.assertEqual(self.services["auth-proxy"]["networks"], ["edge", "frontend"])
        self.assertTrue(self.compose["networks"]["frontend"]["internal"])
        self.assertNotIn("egress", self.services["auth-proxy"]["networks"])
        self.assertNotIn("egress", self.services["reverse-proxy"]["networks"])
        self.assertNotIn("egress", self.services["app-data-init"].get("networks", []))
        self.assertEqual(self.services["app-data-init"]["network_mode"], "none")
        self.assertFalse(self.compose["networks"]["egress"].get("internal", False))

    def test_third_party_runtime_images_require_immutable_digests(self):
        app_image = self.services["app"]["image"]
        self.assertIn("AGENTKIT_APP_IMAGE", app_image)
        self.assertIn("image@sha256", app_image)
        self.assertEqual(app_image, self.services["app-data-init"]["image"])
        for service in ("auth-proxy", "reverse-proxy"):
            image = self.services[service]["image"]
            self.assertIn(":?set an immutable", image)
            self.assertIn("image@sha256", image)

    def test_runtime_services_are_hardened(self):
        for name in ("app", "auth-proxy", "reverse-proxy"):
            service = self.services[name]
            self.assertEqual(service["read_only"], True, name)
            self.assertIn("ALL", service["cap_drop"], name)
            self.assertIn("no-new-privileges:true", service["security_opt"], name)
            self.assertNotIn("/var/run/docker.sock", str(service.get("volumes", [])))
            self.assertNotEqual(service.get("privileged", False), True, name)
        self.assertNotIn("worker", self.services)
        self.assertNotIn("AGENTKIT_REQUIRE_ISOLATED_WORKER", self.compose_text)

    def test_public_identity_csrf_tenant_and_backend_policy_are_explicit(self):
        environment = self.services["app"]["environment"]
        self.assertEqual(environment["AGENTKIT_PUBLIC_BACKENDS"], "${AGENTKIT_PUBLIC_BACKENDS:-demo}")
        for key in (
            "AGENTKIT_TENANT_ID",
            "AGENTKIT_AUTH_ALLOWED_DOMAIN",
            "AGENTKIT_AUTH_ALLOWED_GROUP",
        ):
            self.assertIn(":?", environment[key])
        self.assertEqual(environment["AGENTKIT_IDENTITY_USER_HEADER"], "X-Forwarded-Email")
        self.assertEqual(environment["AGENTKIT_IDENTITY_ROLES_HEADER"], "X-Forwarded-Groups")
        self.assertEqual(environment["AGENTKIT_CSRF_SECRET_FILE"], "/run/secrets/csrf_secret")
        self.assertEqual(environment["AGENTKIT_IDENTITY_SECRET_FILE"], "/run/secrets/identity_secret")
        self.assertEqual(environment["AGENTKIT_PROVIDER_CREDENTIALS_FILE"], "/run/secrets/provider_credentials")
        for key, default in (
            ("AGENTKIT_MAX_REQUESTS_PER_USER_PER_MINUTE", "120"),
            ("AGENTKIT_MAX_REQUESTS_PER_TENANT_PER_MINUTE", "1000"),
            ("AGENTKIT_MAX_CACHED_RUNTIMES", "128"),
            ("AGENTKIT_MAX_USERS_PER_TENANT", "100"),
            ("AGENTKIT_STORAGE_QUOTA_BYTES", "268435456"),
            ("AGENTKIT_STORAGE_QUOTA_FILES", "10000"),
            ("AGENTKIT_MAX_JOBS_PER_USER_PER_HOUR", "20"),
            ("AGENTKIT_MAX_JOBS_PER_TENANT_PER_HOUR", "200"),
            ("AGENTKIT_MAX_CONCURRENT_JOBS", "4"),
            ("AGENTKIT_MAX_ACTIVE_JOBS_PER_USER", "2"),
            ("AGENTKIT_MAX_HTTP_WORKERS", "32"),
            ("AGENTKIT_AUDIT_MAX_BYTES", "8388608"),
        ):
            self.assertEqual(environment[key], "${" + key + ":-" + default + "}")
        proxy_args = self.services["auth-proxy"]["command"]
        for argument in (
            "--trusted-proxy-ip=172.30.0.0/24",
            "--pass-user-headers=true",
            "--pass-basic-auth=false",
            "--pass-access-token=false",
            "--pass-authorization-header=false",
            "--skip-auth-strip-headers=false",
            "--session-cookie-minimal=true",
            "--cookie-httponly=true",
            "--cookie-expire=8h",
            "--cookie-refresh=1h",
            "--request-logging=false",
            "--auth-logging=false",
        ):
            self.assertIn(argument, proxy_args)
        self.assertNotIn("--skip-auth-strip-headers=true", self.compose_text)

    def test_edge_proxy_strips_identity_headers_and_bounds_request_body(self):
        caddyfile = (ROOT / "deploy" / "public" / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn("max_size 3MB", caddyfile)
        for header in (
            "X-Forwarded-Email",
            "X-Forwarded-Groups",
            "X-Forwarded-User",
            "X-Forwarded-Preferred-Username",
            "X-Forwarded-Access-Token",
            "X-Agent-Tenant",
            "X-Agent-User",
            "X-Agent-Roles",
        ):
            self.assertIn(f"header_up -{header}", caddyfile)
        self.assertIn("header_up -X-Agent-*", caddyfile)

    def test_build_context_excludes_deployment_secrets_and_certificates(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("**/secrets", dockerignore)
        self.assertIn("**/certs", dockerignore)
        self.assertIn("deploy/public/public.env", dockerignore)

    def test_secrets_are_file_backed_and_not_inline(self):
        secrets = self.compose["secrets"]
        for name in (
            "csrf_secret",
            "identity_secret",
            "provider_credentials",
            "oidc_client_secret",
            "session_cookie_secret",
        ):
            self.assertIn(name, secrets)
            self.assertIn("file", secrets[name])
            self.assertNotIn("value", secrets[name])
        self.assertTrue(secrets["provider_credentials"]["file"].endswith("provider_credentials.json"))
        self.assertNotIn("sk-", self.compose_text)

    def test_cookie_secret_is_documented_as_raw_32_bytes(self):
        docs = (ROOT / "docs" / "PUBLIC-DEPLOYMENT.md").read_text(encoding="utf-8")
        secrets = (ROOT / "deploy" / "public" / "secrets.example").read_text(encoding="utf-8")
        self.assertIn("exactly 32 raw random bytes", secrets)
        self.assertIn("openssl rand -out deploy/public/secrets/session_cookie_secret 32", docs)
        self.assertNotIn("base64.urlsafe_b64encode", docs)

    def test_docs_state_safe_scope_and_external_acceptance(self):
        docs = (ROOT / "docs" / "PUBLIC-DEPLOYMENT.md").read_text(encoding="utf-8")
        self.assertIn("api.deepseek.com:443", docs)
        self.assertIn("eigene, nicht\ninterne `egress`-Bridge-Netz", docs)
        for phrase in (
            "excludes Codex execution",
            "run_pytest",
            "Text attachments",
            "real\nOIDC provider",
            "independent security and",
            "not evidence",
        ):
            self.assertIn(phrase, docs)

    def test_digest_gate_is_wired_into_ci(self):
        gate = (ROOT / "scripts" / "check_public_image_digests.py").read_text(encoding="utf-8")
        self.assertIn("--verify", gate)
        for image_name in (
            "AGENTKIT_APP_IMAGE",
            "AGENTKIT_OAUTH2_PROXY_IMAGE",
            "AGENTKIT_CADDY_IMAGE",
        ):
            self.assertIn(image_name, gate)
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("check_public_image_digests.py", workflow)
        self.assertIn("--platform linux/amd64", workflow)
        self.assertIn("/api/readiness", workflow)


if __name__ == "__main__":
    unittest.main()
