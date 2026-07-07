"""Tests für agent_cli.py — Onboarding-Generator + Selbsttest (Zyklus 30).

agent_cli.py liegt im Repo-Root (kein Paket), daher wird es — wie test_check.py
es für tools/check.py tut — per importlib geladen.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_CLI_PATH = Path(__file__).resolve().parent.parent / "agent_cli.py"
_spec = importlib.util.spec_from_file_location("agent_cli", _CLI_PATH)
agent_cli = importlib.util.module_from_spec(_spec)
sys.modules["agent_cli"] = agent_cli
_spec.loader.exec_module(agent_cli)


def _make_answers(**overrides):
    """Vollständige OnboardingAnswers mit sinnvollen Defaults für Tests."""
    base = dict(
        project_name="Test Projekt",
        customer_or_team="Team A",
        main_problem="E-Mails sortieren",
        success_criteria="Posteingang leer",
        non_goals="Keine Experimente",
        role="automation agent",
        language="Deutsch",
        tone="klar",
        domain_expertise="Prozesswissen",
        hard_limits="Nichts löschen",
        trigger="täglich um 8 Uhr",
        inputs="E-Mails",
        steps="1. Lesen\n2. Sortieren",
        validation="Erst prüfen",
        escalation="Bei Unklarheit fragen",
        tools=["read", "notify"],
        require_approval_for="Versenden, Löschen",
        never_do="Nie ohne Freigabe löschen",
        retry_policy="Einmal retryen",
        quality_threshold="7/10",
        keep_forever="Regeln",
        keep_temporarily="Zwischenstand",
        remember_between_runs="Learnings",
        recurring_tasks=["Earnings analysieren", "Meeting vorbereiten"],
        external_sources="Bloomberg, Excel",
    )
    base.update(overrides)
    return agent_cli.OnboardingAnswers(**base)


@pytest.fixture
def generated_project(tmp_path: Path) -> Path:
    """Erzeugt ein vollständiges Projekt-Instance in tmp_path."""
    target = tmp_path / "instance"
    agent_cli._write_template_project(target, _make_answers())
    return target


# ─── SelfTestReport ─────────────────────────────────────────────────────────

class TestSelfTestReport:
    def test_ok_when_no_problems(self):
        r = agent_cli.SelfTestReport(passed=("a",), problems=())
        assert r.ok is True

    def test_not_ok_with_problem(self):
        r = agent_cli.SelfTestReport(passed=(), problems=("kaputt",))
        assert r.ok is False

    def test_is_immutable(self):
        r = agent_cli.SelfTestReport(passed=(), problems=())
        with pytest.raises((AttributeError,)):
            r.passed = ("x",)  # type: ignore[misc]


# ─── _self_test_project — Happy path ─────────────────────────────────────────

class TestSelfTestHappyPath:
    def test_freshly_generated_project_passes(self, generated_project: Path):
        report = agent_cli._self_test_project(generated_project)
        assert report.ok, f"unerwartete Probleme: {report.problems}"
        assert report.problems == ()

    def test_reports_core_files_as_passed(self, generated_project: Path):
        report = agent_cli._self_test_project(generated_project)
        joined = "\n".join(report.passed)
        assert "SOUL.md" in joined
        assert "manifest.json" in joined
        assert "connectors.yaml" in joined

    def test_reports_each_manifest_skill_present(self, generated_project: Path):
        report = agent_cli._self_test_project(generated_project)
        joined = "\n".join(report.passed)
        # beide wiederkehrenden Aufgaben werden zu Skills
        assert "earnings-analysieren" in joined
        assert "meeting-vorbereiten" in joined

    def test_project_without_skills_still_passes(self, tmp_path: Path):
        target = tmp_path / "noskills"
        agent_cli._write_template_project(target, _make_answers(recurring_tasks=[]))
        report = agent_cli._self_test_project(target)
        assert report.ok


# ─── _self_test_project — Negative paths ─────────────────────────────────────

class TestSelfTestNegativePaths:
    def test_missing_core_file_is_a_problem(self, generated_project: Path):
        (generated_project / "project" / "SOUL.md").unlink()
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("SOUL.md" in p for p in report.problems)

    def test_empty_core_file_is_a_problem(self, generated_project: Path):
        (generated_project / "project" / "workflows" / "main.md").write_text("", encoding="utf-8")
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("main.md" in p for p in report.problems)

    def test_invalid_json_is_a_problem(self, generated_project: Path):
        (generated_project / "project" / "manifest.json").write_text("{ kaputt", encoding="utf-8")
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("ungültiges JSON" in p for p in report.problems)

    def test_manifest_skill_without_skill_md_is_a_problem(self, generated_project: Path):
        # Skill-Datei löschen, obwohl das Manifest sie weiterhin listet.
        skill_md = generated_project / "project" / "skills" / "earnings-analysieren" / "SKILL.md"
        skill_md.unlink()
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("earnings-analysieren" in p for p in report.problems)

    def test_manifest_missing_connector_file_is_a_problem(self, generated_project: Path):
        (generated_project / "project" / "connectors.yaml").unlink()
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("Connector" in p or "connectors.yaml" in p for p in report.problems)


# ─── CLI-Verdrahtung ─────────────────────────────────────────────────────────

class TestParser:
    def test_setup_accepts_no_self_test_flag(self):
        parser = agent_cli.build_parser()
        args = parser.parse_args(["setup", "--no-self-test"])
        assert args.no_self_test is True

    def test_no_self_test_defaults_false(self):
        parser = agent_cli.build_parser()
        args = parser.parse_args(["setup"])
        assert args.no_self_test is False


class TestCmdSetupSelfTest:
    def test_self_test_runs_and_succeeds(self, tmp_path: Path, capsys, monkeypatch):
        out_root = tmp_path / "out"
        args = agent_cli.argparse.Namespace(
            output=str(out_root), force=True, full=False, no_self_test=False
        )
        # Fragen umgehen: _collect_answers durch feste Antworten ersetzen.
        monkeypatch.setattr(agent_cli, "_collect_answers", lambda mode="beginner": _make_answers())
        rc = agent_cli.cmd_setup(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "Selbsttest" in captured.out
        assert "einsatzbereit" in captured.out

    def test_self_test_failure_returns_nonzero(self, tmp_path: Path, capsys, monkeypatch):
        out_root = tmp_path / "out"
        args = agent_cli.argparse.Namespace(
            output=str(out_root), force=True, full=False, no_self_test=False
        )
        monkeypatch.setattr(agent_cli, "_collect_answers", lambda mode="beginner": _make_answers())

        # Nach dem Schreiben eine Kern-Datei entfernen, damit der Selbsttest scheitert.
        real_write = agent_cli._write_template_project

        def _write_then_break(target_dir, ans):
            real_write(target_dir, ans)
            (target_dir / "project" / "SOUL.md").unlink()

        monkeypatch.setattr(agent_cli, "_write_template_project", _write_then_break)
        rc = agent_cli.cmd_setup(args)
        captured = capsys.readouterr()
        assert rc == 1
        assert "Problem" in captured.out
