import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.providers import ProviderSettings


class _FakeDpapi:
    available = True

    def protect_bytes(self, value):
        return b"wrapped:" + value

    def unprotect_bytes(self, value):
        if not value.startswith(b"wrapped:"):
            raise ValueError("bad blob")
        return value[8:]


class ProviderSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_environment_fallback_and_invalid_values(self):
        settings = ProviderSettings(self.path)
        self.assertEqual(settings.status()["source"], "none")
        os.environ["DEEPSEEK_API_KEY"] = "environment-key"
        self.assertEqual(settings.api_key(), "environment-key")
        self.assertEqual(settings.status()["source"], "environment")
        os.environ["DEEPSEEK_API_KEY"] = "bad key"
        self.assertEqual(settings.api_key(), "")
        for value in ("", "a" * 513, "bad\nkey", "ümlaut"):
            with self.assertRaises(ContractError):
                settings.save(value)

    def test_dpapi_roundtrip_and_stored_precedence(self):
        settings = ProviderSettings(self.path)
        settings._dpapi = _FakeDpapi()
        settings.save("stored-key")
        os.environ["DEEPSEEK_API_KEY"] = "environment-key"
        self.assertEqual(settings.api_key(), "stored-key")
        self.assertEqual(settings.status(), {"configured": True, "source": "stored", "storage_available": True})
        restarted = ProviderSettings(self.path)
        restarted._dpapi = _FakeDpapi()
        self.assertEqual(restarted.api_key(), "stored-key")
        settings.clear()
        self.assertEqual(settings.api_key(), "environment-key")

    def test_corrupt_stored_value_fails_closed_without_environment_fallback(self):
        settings = ProviderSettings(self.path)
        settings._dpapi = _FakeDpapi()
        settings.save("stored-key")
        os.environ["DEEPSEEK_API_KEY"] = "environment-key"
        record = json.loads(settings.path.read_text(encoding="utf-8"))
        record["protected"] = base64.b64encode(b"corrupt").decode("ascii")
        settings.path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ContractError):
            settings.api_key()
        self.assertEqual(settings.status()["source"], "none")

    @unittest.skipUnless(sys.platform == "win32", "Windows CurrentUser DPAPI required")
    def test_real_current_user_dpapi_roundtrip_restart_and_tamper(self):
        secret = "real-dpapi-synthetic-key"
        settings = ProviderSettings(self.path)
        settings.save(secret)
        raw = settings.path.read_text(encoding="utf-8")
        self.assertNotIn(secret, raw)
        restarted = ProviderSettings(self.path)
        self.assertEqual(restarted.api_key(), secret)
        record = json.loads(raw)
        encrypted = bytearray(base64.b64decode(record["protected"]))
        encrypted[-1] ^= 1
        record["protected"] = base64.b64encode(encrypted).decode("ascii")
        settings.path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ContractError):
            restarted.api_key()

    def test_unavailable_storage_keeps_environment_and_rejects_save(self):
        settings = ProviderSettings(self.path)
        settings._dpapi.available = False
        os.environ['DEEPSEEK_API_KEY'] = 'synthetic-environment'
        self.assertEqual('synthetic-environment', settings.api_key())
        with self.assertRaises(ContractError):
            settings.save('synthetic-local')
        self.assertFalse(settings.path.exists())

    def test_failed_encryption_preserves_previous_value(self):
        settings = ProviderSettings(self.path)
        settings._dpapi = _FakeDpapi()
        settings.save('synthetic-original')
        before = settings.path.read_bytes()
        with patch.object(settings._dpapi, 'protect_bytes', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                settings.save('synthetic-replacement')
        self.assertEqual(before, settings.path.read_bytes())
        self.assertEqual('synthetic-original', settings.api_key())

    def test_permission_failure_does_not_fallback_to_environment(self):
        settings = ProviderSettings(self.path)
        os.environ['DEEPSEEK_API_KEY'] = 'synthetic-environment'
        with patch.object(Path, 'lstat', side_effect=PermissionError('fixture')):
            self.assertIn('error', settings.status())
            with self.assertRaises(ContractError):
                settings.api_key()


if __name__ == "__main__":
    unittest.main()
