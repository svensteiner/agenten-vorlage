import unittest
from dataclasses import FrozenInstanceError

from cockpit.public_security import (
    AuthContext,
    PublicSecurityConfig,
    PublicSecurityError,
    RateLimiter,
    csrf_token,
    security_headers,
    validate_request,
    verify_csrf,
)


class PublicSecurityTests(unittest.TestCase):
    def setUp(self):
        self.config = PublicSecurityConfig(
            public_origin="https://agents.example.test",
            trusted_proxy_cidrs=("10.0.0.0/8", "127.0.0.1/32"),
            csrf_secret=b"test-secret-that-is-long-enough!!",
        )
        self.base_headers = {
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "agents.example.test",
            "X-Agent-Tenant": "tenant-a",
            "X-Agent-User": "user-1",
            "X-Agent-Roles": "member, reviewer",
        }

    def test_auth_context_is_immutable_and_normalized(self):
        context = validate_request("10.1.2.3", self.base_headers, self.config)
        self.assertEqual(context, AuthContext("tenant-a", "user-1", ("member", "reviewer")))
        with self.assertRaises(FrozenInstanceError):
            context.tenant_id = "other"

    def test_proxy_and_forwarded_values_are_exact(self):
        with self.assertRaises(PublicSecurityError):
            validate_request("192.0.2.1", self.base_headers, self.config)
        for name, value in (("X-Forwarded-Proto", "http"), ("X-Forwarded-Host", "evil.example")):
            headers = dict(self.base_headers)
            headers[name] = value
            with self.assertRaises(PublicSecurityError):
                validate_request("10.1.2.3", headers, self.config)

    def test_identity_header_validation_rejects_ambiguous_values(self):
        for name, value in (
            ("X-Agent-Tenant", "tenant/a"),
            ("X-Agent-User", "user\nforged"),
            ("X-Agent-Roles", "member,,admin"),
            ("X-Agent-Roles", "member,admin;drop"),
        ):
            headers = dict(self.base_headers)
            headers[name] = value
            with self.assertRaises(PublicSecurityError):
                validate_request("10.1.2.3", headers, self.config)
        headers = dict(self.base_headers)
        headers["X-Agent-Roles"] = ",".join(f"role{index}" for index in range(17))
        with self.assertRaises(PublicSecurityError):
            validate_request("10.1.2.3", headers, self.config)

    def test_csrf_token_is_bound_to_identity_and_session(self):
        context = validate_request("10.1.2.3", self.base_headers, self.config)
        token = csrf_token(self.config.csrf_secret, context, "session-1")
        verify_csrf("POST", {"Origin": self.config.public_origin, "Cookie": "session=x", "X-CSRF-Token": token}, context, "session-1", self.config)
        with self.assertRaises(PublicSecurityError):
            verify_csrf("POST", {"Origin": self.config.public_origin, "Cookie": "session=x", "X-CSRF-Token": token}, context, "session-2", self.config)
        with self.assertRaises(PublicSecurityError):
            verify_csrf("POST", {"Origin": self.config.public_origin, "Cookie": "session=x", "X-CSRF-Token": "bad"}, context, "session-1", self.config)

    def test_csrf_is_required_for_browser_mutations_and_origin_is_exact(self):
        context = AuthContext("tenant-a", "user-1", ("member",))
        headers = {"Origin": self.config.public_origin}
        with self.assertRaises(PublicSecurityError):
            verify_csrf("PUT", headers, context, "session-1", self.config)
        token = csrf_token(self.config.csrf_secret, context, "session-1")
        verify_csrf("PUT", {**headers, "X-CSRF-Token": token}, context, "session-1", self.config)
        with self.assertRaises(PublicSecurityError):
            verify_csrf("DELETE", {"Origin": "https://evil.example"}, context, "session-1", self.config)
        with self.assertRaises(PublicSecurityError):
            verify_csrf("POST", {"X-CSRF-Token": token}, context, "session-1", self.config)
        verify_csrf("GET", {"Origin": "https://evil.example"}, context, "session-1", self.config)

    def test_rate_limiter_covers_ip_user_tenant_and_is_bounded(self):
        limiter = RateLimiter(window_seconds=60, max_entries=3)
        self.assertTrue(limiter.allow("ip:1", limit=1).allowed)
        self.assertFalse(limiter.allow("ip:1", limit=1).allowed)
        self.assertTrue(limiter.allow("user:1", limit=1).allowed)
        self.assertTrue(limiter.allow("tenant:1", limit=1).allowed)
        self.assertLessEqual(limiter.entry_count, 3)

    def test_security_headers_do_not_expose_configuration(self):
        headers = security_headers(self.config)
        self.assertEqual(headers["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("test-secret", repr(headers))

    def test_fixed_tenant_is_server_controlled(self):
        config = PublicSecurityConfig(
            public_origin=self.config.public_origin,
            trusted_proxy_cidrs=self.config.trusted_proxy_cidrs,
            csrf_secret=self.config.csrf_secret,
            fixed_tenant_id="company-a",
        )
        headers = dict(self.base_headers)
        headers["X-Agent-Tenant"] = "attacker-choice"
        context = validate_request("127.0.0.1", headers, config)
        self.assertEqual("company-a", context.tenant_id)


if __name__ == "__main__":
    unittest.main()
