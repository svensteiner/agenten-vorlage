from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agentkit.catalog import Catalog
from agentkit.marketing_snapshot import MAX_DAILY_REPORTS, SnapshotError, build_snapshot


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agents" / "x-growth-agent"


class MarketingAgentPackTests(unittest.TestCase):
    def test_pack_is_valid_and_contains_the_full_growth_workflow(self):
        catalog = Catalog(AGENT)
        self.assertEqual("x-growth-agent", catalog.config["id"])
        self.assertTrue(catalog.config["require_review"])
        self.assertEqual(
            {
                "strategist",
                "researcher",
                "content-editor",
                "verifier",
                "operator",
                "reporter",
            },
            set(catalog.roles),
        )
        self.assertTrue(catalog.roles["verifier"]["can_review"])
        self.assertEqual("read-only", catalog.roles["operator"]["sandbox"])
        self.assertIn("live-action", catalog.roles["operator"]["skills"])

    def test_pack_defines_measured_visibility_without_claiming_live_execution(self):
        core = Catalog(AGENT).core()
        self.assertIn("qualifizierte Sichtbarkeit", core)
        self.assertIn("24h", core)
        self.assertIn("bestehende Marketingbot-Pipeline", core)
        self.assertIn("keine direkte Live-X-Ausfuehrung", core)

    def test_one_click_launcher_targets_marketingbot_and_real_codex(self):
        script = (ROOT / "Start-Marketing-Agent.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("C:\\Users\\botrunner\\projects\\marketingbot", script)
        self.assertIn("marketing_snapshot.py", script)
        self.assertIn("-DefaultWorkspace $Snapshot", script)
        self.assertNotIn("-DefaultWorkspace $MarketingbotPath", script)
        self.assertIn('"x-growth-agent"', script)
        self.assertIn('"codex"', script)
        self.assertIn("-OpenBrowser", script)

    def test_one_click_coding_launcher_uses_the_reviewed_programming_agent(self):
        script = (ROOT / "Start-Coding-Agent.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('"programming-agent"', script)
        self.assertIn('"codex"', script)
        self.assertIn("OpenBrowser = $true", script)

    def test_coding_launcher_forwards_optional_execution_profiles_to_mock_studio(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            self.skipTest("PowerShell is unavailable; static launcher contract is checked separately.")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = root / "Start-Coding-Agent.ps1"
            launcher.write_bytes((ROOT / "Start-Coding-Agent.ps1").read_bytes())
            (root / "Start-AI-Studio.ps1").write_text(
                """param(
                    [int]$Port,
                    [string]$DefaultWorkspace,
                    [string]$PreferredAgent,
                    [string]$PreferredBackend,
                    [string]$StarterTask,
                    [string]$ExecutionProfiles,
                    [switch]$OpenBrowser
                )
                [ordered]@{
                    Port = $Port
                    DefaultWorkspace = $DefaultWorkspace
                    PreferredAgent = $PreferredAgent
                    PreferredBackend = $PreferredBackend
                    StarterTask = $StarterTask
                    ExecutionProfiles = $ExecutionProfiles
                    OpenBrowser = [bool]$OpenBrowser
                } | ConvertTo-Json -Compress | Set-Content -LiteralPath $env:AGENTKIT_LAUNCH_CAPTURE -Encoding utf8
                exit 7
                """,
                encoding="utf-8",
            )
            capture = root / "capture.json"
            env = {**os.environ, "AGENTKIT_LAUNCH_CAPTURE": str(capture)}
            workspace = root / "workspace with spaces"
            profile = root / "host profiles.json"
            for with_profile in (False, True):
                args = [shell, "-NoProfile", "-File", str(launcher), "-Port", "8766",
                        "-Workspace", str(workspace), "-Task", "bounded task"]
                if with_profile:
                    args.extend(["-ExecutionProfiles", str(profile)])
                completed = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
                self.assertEqual(7, completed.returncode, completed.stderr)
                received = json.loads(capture.read_text(encoding="utf-8-sig"))
                self.assertEqual(8766, received["Port"])
                self.assertEqual(str(workspace), received["DefaultWorkspace"])
                self.assertEqual("programming-agent", received["PreferredAgent"])
                self.assertEqual("codex", received["PreferredBackend"])
                self.assertEqual("bounded task", received["StarterTask"])
                self.assertEqual(str(profile) if with_profile else "", received["ExecutionProfiles"])
                self.assertTrue(received["OpenBrowser"])

    def test_snapshot_copies_only_allowlisted_evidence_and_redacts_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "marketingbot"
            output = root / "snapshots"
            known_token = "sk-" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
            (source / "state").mkdir(parents=True)
            (source / "reports" / "daily").mkdir(parents=True)
            (source / "STATUS.md").write_text(
                f"ready {known_token} api_key=TOPSECRET123\n"
                "Authorization: Basic dXNlcjpwYXNzd29yZA==\n"
                '{"authorization":"Basic YWRtaW46c2VjcmV0","cookie":"session=abc xyz"}\n'
                'api_secret=VERYSECRET bearer_token=BEARERSECRET secret="two words hidden"\n'
                'clientSecret="CAMELSECRET" refreshToken=CAMELTOKEN\n'
                'database_url=https://user:pass@example.com/path\n',
                encoding="utf-8",
            )
            (source / "state" / "external_directive.json").write_text(
                '{"goal":"qualified visibility"}\n', encoding="utf-8"
            )
            (source / ".env").write_text("PASSWORD=DO-NOT-COPY\n", encoding="utf-8")
            (source / "bot.py").write_text("raise SystemExit\n", encoding="utf-8")
            for index in range(MAX_DAILY_REPORTS + 2):
                (source / "reports" / "daily" / f"2026-10-{index + 1:02d}.md").write_text(
                    f"report {index}\n", encoding="utf-8"
                )

            snapshot = build_snapshot(source, output)
            all_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in snapshot.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("TOPSECRET123", all_text)
            self.assertNotIn(known_token, all_text)
            self.assertNotIn("dXNlcjpwYXNzd29yZA==", all_text)
            self.assertNotIn("YWRtaW46c2VjcmV0", all_text)
            self.assertNotIn("session=abc xyz", all_text)
            self.assertNotIn("VERYSECRET", all_text)
            self.assertNotIn("BEARERSECRET", all_text)
            self.assertNotIn("two words hidden", all_text)
            self.assertNotIn("CAMELSECRET", all_text)
            self.assertNotIn("CAMELTOKEN", all_text)
            self.assertNotIn("user:pass", all_text)
            self.assertIn("Authorization: [REDACTED]", all_text)
            self.assertIn("https://[REDACTED]@example.com/path", all_text)
            self.assertFalse((snapshot / ".env").exists())
            self.assertFalse((snapshot / "bot.py").exists())
            self.assertEqual(
                MAX_DAILY_REPORTS,
                len(list((snapshot / "reports" / "daily").glob("*.md"))),
            )
            manifest = json.loads(
                (snapshot / "SNAPSHOT-MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(1, manifest["schema_version"])
            self.assertTrue(all("sha256" in item for item in manifest["files"]))

    def test_failed_snapshot_does_not_leave_a_partial_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "marketingbot"
            output = root / "snapshots"
            source.mkdir()
            with self.assertRaises(SnapshotError):
                build_snapshot(source, output)
            self.assertEqual([], list(output.iterdir()))


if __name__ == "__main__":
    unittest.main()
