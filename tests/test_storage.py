import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.storage import save


class StorageTests(unittest.TestCase):
    def test_checkpoint_replace_retries_transient_windows_sharing_error(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            target.write_text("old", encoding="utf-8")
            original_replace = os.replace
            calls = {"count": 0}

            def flaky_replace(source, destination):
                calls["count"] += 1
                if calls["count"] < 3:
                    raise PermissionError("synthetic sharing violation")
                return original_replace(source, destination)

            with patch("agentkit.storage.os.name", "nt"), patch("agentkit.storage.os.replace", side_effect=flaky_replace):
                save(target, {"status": "running"})
            self.assertEqual({"status": "running"}, json.loads(target.read_text(encoding="utf-8")))
            self.assertEqual(3, calls["count"])

    def test_checkpoint_replace_still_surfaces_persistent_permission_error(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            target.write_text("old", encoding="utf-8")
            with patch("agentkit.storage.os.name", "nt"), patch("agentkit.storage.os.replace", side_effect=PermissionError("synthetic denial")):
                with self.assertRaises(PermissionError):
                    save(target, {"status": "running"})
            self.assertEqual("old", target.read_text(encoding="utf-8"))
            self.assertEqual([], list(Path(directory).glob(".checkpoint-*")))

    def test_checkpoint_replace_surfaces_nonpermission_error_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            target.write_text("old", encoding="utf-8")
            calls = {"count": 0}

            def failed_replace(_source, _destination):
                calls["count"] += 1
                raise OSError("synthetic disk failure")

            with patch("agentkit.storage.os.name", "nt"), patch(
                "agentkit.storage.os.replace", side_effect=failed_replace
            ):
                with self.assertRaisesRegex(OSError, "synthetic disk failure"):
                    save(target, {"status": "running"})

            self.assertEqual(1, calls["count"])
            self.assertEqual("old", target.read_text(encoding="utf-8"))
            self.assertEqual([], list(Path(directory).glob(".checkpoint-*")))

    def test_checkpoint_replace_uses_one_attempt_on_posix(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            calls = {"count": 0}

            def failed_replace(_source, _destination):
                calls["count"] += 1
                raise PermissionError("synthetic sharing violation")

            with patch("agentkit.storage.os.name", "posix"), patch(
                "agentkit.storage.os.replace", side_effect=failed_replace
            ):
                with self.assertRaises(PermissionError):
                    save(target, {"status": "running"})

            self.assertEqual(1, calls["count"])
            self.assertEqual([], list(Path(directory).glob(".checkpoint-*")))


if __name__ == "__main__":
    unittest.main()
