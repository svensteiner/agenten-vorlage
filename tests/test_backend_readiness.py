import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.backends import (
    CodexBackend,
    _write_codex_schema,
    codex_readiness,
)
from agentkit.contracts import ContractError


class BackendReadinessTests(unittest.TestCase):
    def test_codex_schema_removes_keywords_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            schema = json.loads(
                _write_codex_schema("decision", Path(folder) / "schema.json").read_text()
            )
        self.assertNotIn("uniqueItems", json.dumps(schema))

    def test_global_configuration_is_isolated_without_fast_tier_or_auth_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / "config.toml").write_text(
                'model = "gpt-5.5"\nservice_tier = "priority"\n[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
            )
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch(
                "agentkit.backends.codex_command", return_value=["codex"]
            ), patch("agentkit.backends.run_process") as run:
                run.return_value = ""
                backend = CodexBackend()
                context = {"workspace": folder, "sandbox": "read-only"}
                def fake_process(args, prompt, cwd, timeout):
                    Path(args[args.index("--output-last-message") + 1]).write_text(
                        json.dumps(
                            {
                                "action": "blocked",
                                "role": "",
                                "skills": [],
                                "task": "probe",
                                "reason": "probe",
                            }
                        ),
                        encoding="utf-8",
                    )
                    self.assertIn('--ignore-user-config', args)
                    self.assertNotIn('service_tier="fast"', args)
                    self.assertIn('model_reasoning_effort="low"', args)
                    self.assertEqual('gpt-5.6-luna', args[args.index('--model') + 1])
                    return ""

                run.side_effect = fake_process
                backend._call("probe", "decision", context, 5)
            self.assertIn('service_tier = "priority"', (home / "config.toml").read_text())

    def test_readiness_does_not_claim_live_access_without_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / "config.toml").write_text(
                'model = "gpt-5.5"\nservice_tier = "fast"\n[windows]\nsandbox = "unelevated"\n', encoding="utf-8"
            )
            (home / "auth.json").write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}, clear=False), patch(
                "agentkit.backends.codex_command", return_value=["codex"]
            ), patch("agentkit.backends._read_cli_version", return_value="codex-cli test"):
                result = codex_readiness()
        self.assertTrue(result["installed"])
        self.assertTrue(result["configured"])
        self.assertTrue(result["credentials_present"])
        self.assertFalse(result["live_tested"])
        self.assertFalse(result["live_ok"])

    def test_windows_values_are_selected_without_mutating_config(self):
        for value in ("elevated", "unelevated"):
            with tempfile.TemporaryDirectory() as folder:
                home = Path(folder)
                config = home / "config.toml"
                original = f'[windows]\nsandbox = "{value}"\n'
                config.write_text(original, encoding="utf-8")
                with patch("agentkit.backends.sys.platform", "win32"), patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch("agentkit.backends.codex_command", return_value=["codex"]), patch("agentkit.backends.run_process") as run:
                    def process(args, prompt, cwd, timeout):
                        Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps({"action": "blocked", "role": "", "skills": [], "task": "x", "reason": "x"}), encoding="utf-8")
                        self.assertIn(f'windows.sandbox="{value}"', args)
                        self.assertIn("--ignore-user-config", args)
                        self.assertIn("sandbox_workspace_write.network_access=false", args)
                        self.assertIn('approval_policy="never"', args)
                        self.assertNotIn("--ignore-rules", args)
                        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", args)
                        return ""
                    run.side_effect = process
                    for sandbox in ("read-only", "workspace-write"):
                        CodexBackend()._call("probe", "decision", {"workspace": folder, "sandbox": sandbox}, 5)
                        call_args = run.call_args.args[0]
                        self.assertEqual(sandbox, call_args[call_args.index("--sandbox") + 1])
                self.assertEqual(original, config.read_text(encoding="utf-8"))

    def test_windows_missing_or_malformed_config_fails_before_call(self):
        for contents in (None, "[windows\n", '[windows]\nsandbox = "disabled"\n', '[windows]\nsandbox = true\n', '[windows]\nsandbox = ["elevated"]\n', '[windows]\n'):
            with tempfile.TemporaryDirectory() as folder:
                home = Path(folder)
                if contents is not None:
                    (home / "config.toml").write_text(contents, encoding="utf-8")
                with patch("agentkit.backends.sys.platform", "win32"), patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch("agentkit.backends.codex_command", return_value=["codex"]), patch("agentkit.backends.run_process") as run:
                    with self.assertRaises(ContractError):
                        CodexBackend()
                    run.assert_not_called()

    def test_linux_and_darwin_need_no_windows_config_and_keep_role_flags(self):
        for platform in ("linux", "darwin"):
            with tempfile.TemporaryDirectory() as folder:
                with patch("agentkit.backends.sys.platform", platform), patch.dict(os.environ, {"CODEX_HOME": folder}), patch("agentkit.backends.codex_command", return_value=["codex"]), patch("agentkit.backends.run_process") as run:
                    def process(args, prompt, cwd, timeout):
                        Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps({"action": "blocked", "role": "", "skills": [], "task": "x", "reason": "x"}), encoding="utf-8")
                        self.assertIn("--ignore-user-config", args)
                        self.assertIn("sandbox_workspace_write.network_access=false", args)
                        self.assertFalse(any(arg.startswith("windows.sandbox=") for arg in args))
                        self.assertIn('approval_policy="never"', args)
                        self.assertNotIn("danger", " ".join(args).lower())
                        self.assertNotIn("--ignore-rules", args)
                        return ""
                    run.side_effect = process
                    for sandbox in ("read-only", "workspace-write"):
                        CodexBackend()._call("probe", "decision", {"workspace": folder, "sandbox": sandbox}, 5)
                        call_args = run.call_args.args[0]
                        self.assertEqual(sandbox, call_args[call_args.index("--sandbox") + 1])

    def test_unreadable_or_directory_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            config = home / "config.toml"
            config.mkdir()
            with patch("agentkit.backends.sys.platform", "win32"), patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch("agentkit.backends.codex_command", return_value=["codex"]):
                with self.assertRaises(ContractError):
                    CodexBackend()

    def test_invalid_windows_config_stops_live_readiness_before_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / "config.toml").write_text('[windows]\nsandbox = "disabled"\n', encoding="utf-8")
            with patch("agentkit.backends.sys.platform", "win32"), patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch("agentkit.backends.codex_command", return_value=["codex"]), patch("agentkit.backends._read_cli_version", return_value="codex test"), patch("agentkit.backends.run_process") as run:
                result = codex_readiness(live_test=True)
            self.assertFalse(result["live_tested"])
            self.assertFalse(result["sandbox_configured"])
            self.assertIn("sandbox", result["detail"].lower())
            run.assert_not_called()

    def test_readiness_reports_windows_sandbox_state(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with patch("agentkit.backends.sys.platform", "win32"), patch.dict(os.environ, {"CODEX_HOME": str(home)}), patch("agentkit.backends.codex_command", return_value=["codex"]), patch("agentkit.backends._read_cli_version", return_value="codex test"):
                result = codex_readiness()
        self.assertFalse(result["sandbox_configured"])
        self.assertIsNone(result["windows_sandbox"])
        self.assertIn("sandbox", result["detail"].lower())


if __name__ == "__main__":
    unittest.main()
