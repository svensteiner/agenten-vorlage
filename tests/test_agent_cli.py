"""Tests für agent_cli.py — Onboarding-Generator + Selbsttest (Zyklus 30).

agent_cli.py liegt im Repo-Root (kein Paket), daher wird es — wie test_check.py
es für tools/check.py tut — per importlib geladen.
"""
import importlib.util
import json
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

    def test_factory_commands_accept_instance_identity(self):
        parser = agent_cli.build_parser()
        create = parser.parse_args(["create", "--tenant", "acme", "--agent", "inbox", "--preset", "kmu-controlling"])
        validate = parser.parse_args(["validate", "--instance", "instances/acme/inbox"])
        run = parser.parse_args(["run", "--instance", "instances/acme/inbox", "--task", "smoke"])
        assert (create.tenant, create.agent) == ("acme", "inbox")
        assert create.preset == "kmu-controlling"
        assert validate.instance == "instances/acme/inbox"
        assert run.task == "smoke"


class TestInstanceFactory:
    def test_create_kmu_controlling_preset_has_hourly_adaptive_schedule_and_safe_defaults(self, tmp_path):
        args = agent_cli.argparse.Namespace(
            tenant="Acme GmbH", agent="Controlling", output=str(tmp_path), full=False,
            no_self_test=False, preset="kmu-controlling",
        )

        assert agent_cli.cmd_create(args) == 0
        project = tmp_path / "acme-gmbh" / "controlling" / "project"
        config = json.loads((project / "config.json").read_text(encoding="utf-8"))
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))

        assert config["loop_interval_minutes"] == 60
        schedule = config["adaptive_schedule"]
        assert schedule["schema_version"] == 1
        assert schedule["enabled"] is True
        assert set(schedule["prompt_profiles"]) == {
            "new_input", "changed_input", "recovery", "pending_approval", "periodic_review"
        }
        assert schedule["max_consecutive_failures"] >= 1
        assert manifest["approval_required_for"] == ["external communication", "send", "publish"]

    def test_kmu_controlling_preset_writes_operating_files_and_preserves_identity(self, tmp_path):
        args = agent_cli.argparse.Namespace(
            tenant="Acme", agent="Finance Pilot", output=str(tmp_path), full=False,
            no_self_test=True, preset="kmu-controlling",
        )

        assert agent_cli.cmd_create(args) == 0
        project = tmp_path / "acme" / "finance-pilot" / "project"
        config = json.loads((project / "config.json").read_text(encoding="utf-8"))
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))

        assert config["instance"] == {"tenant_id": "acme", "agent_id": "finance-pilot"}
        assert manifest["instance"] == {"tenant_id": "acme", "agent_id": "finance-pilot"}
        assert (project / "SOUL.md").is_file()
        assert (project / "workflows" / "main.md").is_file()
        assert (project / "knowledge" / "kpi-rules.md").is_file()
        assert "deterministisch" in (project / "SOUL.md").read_text(encoding="utf-8").lower()

    def test_create_places_identity_in_separate_tenant_agent_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_cli, "_collect_answers", lambda mode="beginner": _make_answers())
        args = agent_cli.argparse.Namespace(
            tenant="Acme GmbH", agent="Inbox Triage", output=str(tmp_path), full=False,
            no_self_test=False,
        )
        assert agent_cli.cmd_create(args) == 0
        instance = tmp_path / "acme-gmbh" / "inbox-triage"
        config = json.loads((instance / "project" / "config.json").read_text(encoding="utf-8"))
        assert config["instance"] == {"tenant_id": "acme-gmbh", "agent_id": "inbox-triage"}

    def test_create_refuses_existing_target_without_merging(self, tmp_path, monkeypatch):
        target = tmp_path / "acme" / "inbox"
        target.mkdir(parents=True)
        sentinel = target / "keep.txt"
        sentinel.write_text("do not overwrite", encoding="utf-8")
        monkeypatch.setattr(agent_cli, "_collect_answers", lambda mode="beginner": _make_answers())
        args = agent_cli.argparse.Namespace(
            tenant="acme", agent="inbox", output=str(tmp_path), full=False,
            no_self_test=False,
        )
        assert agent_cli.cmd_create(args) == 1
        assert sentinel.read_text(encoding="utf-8") == "do not overwrite"

    def test_validate_detects_identity_mismatch(self, tmp_path):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(instance, _make_answers(), tenant_id="acme", agent_id="other")
        report = agent_cli._validate_instance(instance)
        assert not report.ok
        assert any("agent_id" in problem for problem in report.problems)

    def test_run_uses_selected_instance_root_and_identity(self, tmp_path, monkeypatch, capsys):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(instance, _make_answers(), tenant_id="acme", agent_id="inbox")
        called = {}

        class FakeOrchestrator:
            def __init__(self, root):
                called["root"] = Path(root)

            def run(self, task, *, tenant=None):
                called.update(task=task, tenant=tenant)
                return type("Result", (), {"success": True})()

        monkeypatch.setattr(agent_cli, "_instance_orchestrator", FakeOrchestrator)
        args = agent_cli.argparse.Namespace(instance=str(instance), task="offline smoke", tenant=None, extra=[])
        assert agent_cli.cmd_run(args) == 0
        assert called == {"root": instance, "task": "offline smoke", "tenant": "acme"}
        assert "acme/inbox" in capsys.readouterr().out

    def test_run_rejects_tenant_that_differs_from_instance(self, tmp_path, monkeypatch, capsys):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(instance, _make_answers(), tenant_id="acme", agent_id="inbox")
        monkeypatch.setattr(
            agent_cli,
            "_instance_orchestrator",
            lambda root: pytest.fail("orchestrator must not start for a tenant mismatch"),
        )
        args = agent_cli.argparse.Namespace(
            instance=str(instance), task="offline smoke", tenant="other", extra=[]
        )
        assert agent_cli.cmd_run(args) == 1
        assert "other" in capsys.readouterr().out


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
