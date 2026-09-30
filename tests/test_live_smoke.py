import tempfile
import unittest
from pathlib import Path

from scripts import live_smoke


class LiveSmokeTests(unittest.TestCase):
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
