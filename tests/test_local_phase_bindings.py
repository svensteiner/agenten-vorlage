"""Private test actions retain canonical replay and approval bindings."""
import tempfile
import unittest
from pathlib import Path

from agentkit.approvals import binding, replay_action_digest
from agentkit.contracts import ContractError


class LocalPhaseBindingTests(unittest.TestCase):
    def test_local_policy_binding_is_explicit_and_legacy_binding_stays_unchanged(self):
        arguments = dict(run_id="run", agent="agent", company="company", workspace="workspace",
                         backend="codex", model="model", fingerprint="fingerprint")
        legacy = binding(**arguments)
        self.assertNotIn("local_phase_policy_sha256", legacy)
        first = binding(**arguments, local_phase_policy_sha256="a" * 64)
        second = binding(**arguments, local_phase_policy_sha256="b" * 64)
        self.assertNotEqual(first, second)
        self.assertEqual({k: v for k, v in first.items() if k != "local_phase_policy_sha256"}, legacy)

    def test_phase_replay_binds_phase_and_workspace_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "worker.py"
            source.write_text("before", encoding="utf-8")
            red = replay_action_digest("run_local_tests", {"phase": "red"}, workspace)
            full = replay_action_digest("run_local_tests", {"phase": "full"}, workspace)
            self.assertNotEqual(red, full)
            source.write_text("after", encoding="utf-8")
            self.assertNotEqual(full, replay_action_digest(
                "run_local_tests", {"phase": "full"}, workspace))

    def test_phase_action_rejects_hidden_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments in ({}, {"phase": "shell"}, {"phase": "full", "path": "test.py"}):
                with self.subTest(arguments=arguments), self.assertRaises(ContractError):
                    replay_action_digest("run_local_tests", arguments, Path(directory))


if __name__ == "__main__":
    unittest.main()
