import tempfile
import unittest
from pathlib import Path

from scripts import live_smoke


class LiveSmokeTests(unittest.TestCase):
    def test_classifies_provider_authentication_without_returning_summary(self):
        summary = "DeepSeek API returned HTTP 401; authorization: Bearer sk-live-secret-value"
        self.assertEqual("provider_authentication", live_smoke.classify_blocked_summary(summary))
        self.assertNotIn("sk-live-secret-value", live_smoke._sanitize_blocked_summary(summary))

    def test_classifies_blocked_summary_categories(self):
        cases = {
            "DeepSeek API returned HTTP 503": "provider_http",
            "upstream returned HTTP/1.1 503": "provider_http",
            "DeepSeek API request timed out": "provider_network",
            "DeepSeek returned invalid structured JSON": "contract",
            "Planner stopped because the review is blocked": "workflow_blocked",
        }
        for summary, expected in cases.items():
            with self.subTest(summary=summary):
                self.assertEqual(expected, live_smoke.classify_blocked_summary(summary))

    def test_bounded_read_rejects_oversize_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "value.bin"
            path.write_bytes(b"abcd")
            with self.assertRaises(ValueError):
                live_smoke._read_bounded(path, 3)
            self.assertEqual(b"abcd", live_smoke._read_bounded(path, 4))

    def test_reported_artifact_matches_normalized_path_only(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            target = workspace / "RESULT.txt"
            self.assertTrue(live_smoke._artifact_was_reported(
                workspace, target, {"RESULT.txt"}
            ))
            self.assertTrue(live_smoke._artifact_was_reported(
                workspace, target, {str(target)}
            ))
            self.assertFalse(live_smoke._artifact_was_reported(
                workspace, target, {"nested/RESULT.txt", "NOT-RESULT.txt"}
            ))


if __name__ == "__main__":
    unittest.main()
