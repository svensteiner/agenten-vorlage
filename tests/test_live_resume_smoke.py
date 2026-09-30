import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from scripts import live_resume_smoke


class LiveResumeSmokeTests(unittest.TestCase):
    def test_live_flag_and_explicit_bounds_are_required(self):
        with self.assertRaises(SystemExit):
            live_resume_smoke.main(["--model", "gpt-5.6-luna", "--output", "x.json",
                                    "--call-timeout", "30", "--max-seconds", "60"])

    def test_fixture_tests_never_construct_backend_or_run_model(self):
        output = Path("fixture-live-evidence.json")
        with patch.object(live_resume_smoke, "CodexBackend", side_effect=AssertionError("model invoked")):
            with self.assertRaises(SystemExit):
                live_resume_smoke.main(["--live", "--model", "gpt-5.6-luna", "--output", str(output),
                                        "--call-timeout", "1", "--max-seconds", "2"])
        self.assertFalse(output.exists())

    def test_resume_uses_checkpoint_directory_and_requires_acknowledgment(self):
        checkpoint = Path("agent/.runs/run-id/state.json")
        first = unittest.mock.Mock()
        first.run.side_effect = ContractError(
            "Interrupted call may have changed files; resume with --acknowledge-interruption."
        )
        second = unittest.mock.Mock()
        second.run.return_value = {"status": "completed"}
        with patch.object(live_resume_smoke, "Engine", side_effect=[first, second]):
            refused, state = live_resume_smoke._resume(
                Path("agent"), checkpoint, unittest.mock.sentinel.backend
            )
        self.assertTrue(refused)
        self.assertEqual("completed", state["status"])
        self.assertEqual(checkpoint.parent, first.run.call_args.kwargs["run_dir"])
        self.assertEqual(checkpoint.parent, second.run.call_args.kwargs["run_dir"])
        self.assertTrue(second.run.call_args.kwargs["acknowledge_interruption"])

    def test_exited_child_does_not_count_as_interrupted(self):
        proc = unittest.mock.Mock()
        proc.poll.return_value = 3
        self.assertFalse(live_resume_smoke._kill(proc))
        proc.wait.assert_called_once_with(timeout=10)

    def test_deadline_terminates_still_running_resume(self):
        proc = unittest.mock.Mock()
        proc.poll.return_value = None
        with patch.object(live_resume_smoke.time, "monotonic", return_value=10), \
             patch.object(live_resume_smoke, "_kill", return_value=True) as kill:
            with self.assertRaises(TimeoutError):
                live_resume_smoke._wait_bounded(proc, 9)
        kill.assert_called_once_with(proc)

    def test_wait_timeout_terminates_resume(self):
        proc = unittest.mock.Mock()
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired("resume", 1)
        with patch.object(live_resume_smoke.time, "monotonic", return_value=9), \
             patch.object(live_resume_smoke, "_kill", return_value=True) as kill:
            with self.assertRaises(TimeoutError):
                live_resume_smoke._wait_bounded(proc, 10)
        kill.assert_called_once_with(proc)

    def test_qualification_requires_interruption_result_and_workspace_invariant(self):
        base = dict(refused=True, completed=True, marker_in_summary=True,
                    marker_in_report=True, workspace_unchanged=True)
        self.assertTrue(live_resume_smoke._qualification_passed(
            child_terminated=True, **base
        ))
        for field in ("child_terminated", "refused", "completed", "marker_in_summary",
                      "marker_in_report", "workspace_unchanged"):
            case = dict(base, child_terminated=True)
            case[field] = False
            self.assertFalse(live_resume_smoke._qualification_passed(**case), field)

    def test_workspace_manifest_is_bounded_by_entry_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(live_resume_smoke, "MAX_MANIFEST_ENTRIES", 2):
                for name in ("one", "two", "three"):
                    (root / name).write_text(name, encoding="utf-8")
                with self.assertRaises(ValueError):
                    live_resume_smoke._workspace_manifest(root)

    def test_workspace_manifest_fails_closed_over_byte_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "value").write_bytes(b"abcd")
            with patch.object(live_resume_smoke, "MAX_MANIFEST_BYTES", 3):
                with self.assertRaises(ValueError):
                    live_resume_smoke._workspace_manifest(root)

    def test_workspace_manifest_ignores_only_runtime_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "STATUS.md").write_text("# value\n", encoding="utf-8")
            before = live_resume_smoke._workspace_manifest(root)
            (root / ".agentkit.lock").write_bytes(b"")
            self.assertEqual(before, live_resume_smoke._workspace_manifest(root))


if __name__ == "__main__":
    unittest.main()
