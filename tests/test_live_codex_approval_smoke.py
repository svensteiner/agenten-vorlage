from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from subprocess import CompletedProcess
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_codex_approval_smoke", ROOT / "scripts" / "live_codex_approval_smoke.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class LiveCodexApprovalSmokeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "Git is required for the live baseline")
    def test_fixture_git_baseline_measures_only_expected_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            MODULE._write_fixture(workspace)
            self.assertEqual(([], []), MODULE._git_changes(workspace))

            (workspace / "app.py").write_bytes(MODULE.EXPECTED_APP)
            self.assertEqual(
                ([" M app.py"], ["app.py"]), MODULE._git_changes(workspace)
            )

            (workspace / "unexpected.txt").write_text("unexpected", encoding="utf-8")
            status, changed = MODULE._git_changes(workspace)
            self.assertEqual(["app.py"], changed)
            self.assertIn("?? unexpected.txt", status)

    def test_policy_allows_only_exact_write_edit_and_test(self):
        write = {"tool": "write_file", "arguments": {"path": "app.py", "content": MODULE.EXPECTED_APP.decode()}}
        edit = {"tool": "edit_file", "arguments": {"path": "app.py", "old_text": MODULE.ORIGINAL_APP.decode(), "new_text": MODULE.EXPECTED_APP.decode()}}
        pytest = {"tool": "run_pytest", "arguments": {"path": "test_app.py"}}
        for pending in (write, edit, pytest):
            self.assertTrue(MODULE.allowed_action(pending, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP))
        self.assertFalse(MODULE.allowed_action({"tool": "write_file", "arguments": {"path": "other.py", "content": MODULE.EXPECTED_APP.decode()}}, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP))
        self.assertFalse(MODULE.allowed_action({"tool": "run_pytest", "arguments": {"path": "-q"}}, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP))

    def test_policy_reject_mode_rejects_everything(self):
        pending = {"tool": "write_file", "arguments": {"path": "app.py", "content": MODULE.EXPECTED_APP.decode()}}
        self.assertEqual("reject", MODULE.policy_decision(pending, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP, reject=True))

    def test_policy_accepts_targeted_edit_only_when_final_bytes_are_exact(self):
        args = {"path": "app.py", "old_text": "'before'", "new_text": "'after'"}
        pending = {"tool": "edit_file", "arguments": args}
        self.assertTrue(MODULE.allowed_action(pending, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP))
        for overrides in ({"new_text": "'after'; raise RuntimeError()"}, {"old_text": ""},
                          {"path": "test_app.py"}, {"extra": "hidden"}):
            with self.subTest(overrides=overrides):
                self.assertFalse(MODULE.allowed_action(
                    {"tool": "edit_file", "arguments": {**args, **overrides}},
                    original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP,
                ))

    def test_sequence_policy_allows_exactly_one_mutation_then_one_test(self):
        write = {"tool": "write_file", "arguments": {
            "path": "app.py", "content": MODULE.EXPECTED_APP.decode()
        }}
        test = {"tool": "run_pytest", "arguments": {"path": "test_app.py"}}
        self.assertEqual("approve", MODULE.sequence_decision(write, []))
        self.assertEqual("approve", MODULE.sequence_decision(test, ["write_file"]))
        self.assertEqual("reject", MODULE.sequence_decision(write, ["write_file"]))
        self.assertEqual("reject", MODULE.sequence_decision(test, ["write_file", "run_pytest"]))
        self.assertEqual("reject", MODULE.sequence_decision(write, [], reject=True))

    def test_fixture_policy_does_not_construct_backend_or_call_model(self):
        pending = {"tool": "run_pytest", "arguments": {"path": "test_app.py"}}
        with patch.object(MODULE, "CodexBackend", side_effect=AssertionError("fixture must not construct backend")) as backend:
            self.assertEqual("approve", MODULE.policy_decision(pending, original=MODULE.ORIGINAL_APP, expected=MODULE.EXPECTED_APP))
            backend.assert_not_called()

    def test_cli_requires_live_and_restricts_model(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "evidence.json"
            with self.assertRaises(SystemExit):
                MODULE.main(["--model", MODULE.MODEL, "--output", str(output)])
            with self.assertRaises(SystemExit):
                MODULE.main(["--live", "--model", "gpt-5.5", "--output", str(output)])

    def test_live_budget_is_shared_across_both_scenarios(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "evidence.json"
            with patch.object(MODULE, "_cli_version", return_value="unavailable"), \
                 patch.object(MODULE, "_scenario", return_value={"initial_status": "blocked"}) as scenario, \
                 patch.object(MODULE.time, "monotonic", side_effect=[100.0, 100.0, 130.0, 131.0]):
                result = MODULE.run_live(MODULE.MODEL, output, call_timeout=45, max_seconds=60)
        self.assertFalse(result["passed"])
        self.assertEqual(2, scenario.call_count)
        self.assertEqual((45, 60), scenario.call_args_list[0].args[2:4])
        self.assertEqual((30, 30), scenario.call_args_list[1].args[2:4])

    def test_cli_version_uses_the_same_resolved_command_as_backend(self):
        completed = CompletedProcess(["node", "codex.js", "--version"], 0,
                                     stdout="codex-cli 0.159.2\n", stderr="")
        with patch.object(MODULE, "codex_command", return_value=["node", "codex.js"]), \
             patch.object(MODULE.subprocess, "run", return_value=completed) as run:
            self.assertEqual("0.159.2", MODULE._cli_version())
        self.assertEqual(["node", "codex.js", "--version"], run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
