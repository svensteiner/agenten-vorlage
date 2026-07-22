"""Tests für agent_cli.py — Onboarding-Generator + Selbsttest (Zyklus 30).

agent_cli.py liegt im Repo-Root (kein Paket), daher wird es — wie test_check.py
es für tools/check.py tut — per importlib geladen.
"""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.controlling import artifacts as artifacts_module
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from core.scheduling import ScheduledDecision
from core.controlling.artifacts import persist_report_artifacts
from core.controlling.tools import _SIGN_CONVENTION, _SIGN_CONVENTION_NOTE, pilot_availability

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
        (generated_project / "project" / "workflows" / "main.md").write_text(
            "", encoding="utf-8"
        )
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("main.md" in p for p in report.problems)

    def test_invalid_json_is_a_problem(self, generated_project: Path):
        (generated_project / "project" / "manifest.json").write_text(
            "{ kaputt", encoding="utf-8"
        )
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("ungültiges JSON" in p for p in report.problems)

    def test_manifest_skill_without_skill_md_is_a_problem(
        self, generated_project: Path
    ):
        # Skill-Datei löschen, obwohl das Manifest sie weiterhin listet.
        skill_md = (
            generated_project
            / "project"
            / "skills"
            / "earnings-analysieren"
            / "SKILL.md"
        )
        skill_md.unlink()
        report = agent_cli._self_test_project(generated_project)
        assert not report.ok
        assert any("earnings-analysieren" in p for p in report.problems)

    def test_manifest_missing_connector_file_is_a_problem(
        self, generated_project: Path
    ):
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
        create = parser.parse_args(
            [
                "create",
                "--tenant",
                "acme",
                "--agent",
                "inbox",
                "--preset",
                "kmu-controlling",
            ]
        )
        validate = parser.parse_args(["validate", "--instance", "instances/acme/inbox"])
        run = parser.parse_args(["run", "--instance", "instances/acme/inbox", "--loop"])
        assert (create.tenant, create.agent) == ("acme", "inbox")
        assert create.preset == "kmu-controlling"
        assert validate.instance == "instances/acme/inbox"
        assert run.loop is True

    def test_status_accepts_instance_path(self):
        parser = agent_cli.build_parser()
        status = parser.parse_args(
            ["status", "--instance", "instances/acme/controlling"]
        )
        assert status.instance == "instances/acme/controlling"


class TestPilotStatus:
    @staticmethod
    def _instance(tmp_path: Path) -> Path:
        instance = tmp_path / "acme" / "controlling"
        agent_cli._write_template_project(
            instance,
            agent_cli._kmu_controlling_answers(),
            tenant_id="acme",
            agent_id="controlling",
        )
        agent_cli._apply_preset(instance, "kmu-controlling")
        return instance

    @staticmethod
    def _signed_acceptance(instance: Path, runs: int = 4) -> None:
        source = instance / "inbox" / "actuals" / "demo.csv"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("Konto;Monat\n4000;1\n7000;0\n", encoding="utf-8")
        mapping = instance / "project" / "pilot" / "account-mapping.json"
        mapping_definition = json.loads(
            (
                Path(agent_cli.__file__).parent
                / "presets"
                / "kmu-controlling"
                / "pilot"
                / "account-mapping.example.json"
            ).read_text(encoding="utf-8")
        )
        mapping_definition["metrics"]["ebitda"] = ["revenue"]
        mapping_definition["metrics"]["egt"] = ["revenue", "depreciation"]
        mapping.write_text(json.dumps(mapping_definition), encoding="utf-8")
        periods = ("month", "prior", "ytd", "ytd_prior")
        groups = {
            name: {
                **{period: None for period in periods},
                "account_ids": [],
                "row_count": 0,
            }
            for name, rule in mapping_definition["groups"].items()
            if rule.get("ignored") is not True
        }
        groups["revenue"] = {
            **{period: "1" for period in periods},
            "account_ids": ["4000"],
            "row_count": 1,
        }
        groups["depreciation"] = {
            **{period: "0" for period in periods},
            "account_ids": ["7000"],
            "row_count": 1,
        }

        def aggregate_metric(refs, period):
            values = [int(groups[ref][period]) for ref in refs if groups[ref][period] is not None]
            return str(sum(values)) if values else None

        report = {
            "source": "inbox/actuals/demo.csv",
            "method": "approved deterministic mapping",
            "report_metadata": {
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "currency": "EUR",
                "sign_convention": _SIGN_CONVENTION,
            },
            "period_labels": {
                period: mapping_definition["columns"][period] for period in periods
            },
            "sign_convention": _SIGN_CONVENTION,
            "sign_convention_note": _SIGN_CONVENTION_NOTE,
            "metrics": {
                name: {
                    **{
                        period: aggregate_metric(
                            mapping_definition["metrics"][name], period
                        )
                        for period in periods
                    },
                    "account_ids": sorted(
                        {
                            account_id
                            for ref in mapping_definition["metrics"][name]
                            for account_id in groups[ref]["account_ids"]
                        }
                    ),
                }
                for name in mapping_definition["metrics"]
            },
            "groups": groups,
            "material_deviations": [],
            "availability": pilot_availability(),
            "reconciliation": {
                "source_account_count": 2,
                "mapped_account_count": 2,
                "ignored_account_count": 0,
                "mapped_source_period_totals": {
                    period: "1" for period in periods
                },
                "grouped_period_totals": {
                    period: "1.0" for period in periods
                },
            },
            "provenance": {
                "input_fingerprint": hashlib.sha256(source.read_bytes()).hexdigest(),
                "mapping_version": hashlib.sha256(mapping.read_bytes()).hexdigest(),
                "calculation_version": "kmu-report-v3",
            },
        }
        for metric_name in ("material_ratio", "personnel_ratio"):
            report["metrics"][metric_name] = {
                **{period: None for period in periods},
                "account_ids": ["4000"],
            }
        for metric_name in ("receivables", "liquidity", "payables"):
            report["metrics"][metric_name] = {
                **{period: None for period in periods},
                "account_ids": [],
            }
        management = {
            "summary": "Belegter Testbericht.",
            "alarms": [],
            "actions": ["Prüfen", "Freigeben", "Überwachen"],
        }
        now = datetime.now(timezone.utc)
        for _ in range(runs):
            persist_report_artifacts(
                instance,
                report,
                management,
                validated_at=now,
                draft_created_at=now,
            )

    @staticmethod
    def _loop_health(
        instance: Path,
        *,
        status: str = "running",
        poll_result: str = "success",
        updated_at: str | None = None,
    ) -> None:
        (instance / "state" / "loop-health.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": status,
                    "updated_at": updated_at or datetime.now(timezone.utc).isoformat(),
                    "poll_result": poll_result,
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _production_evidence(instance: Path, external: Path, **overrides) -> Path:
        now = datetime.now(timezone.utc)
        current_overrides = overrides.pop("current_overrides", {})
        evidence_id = "synthetic-001"
        fingerprints = {
            "deployment": "deploy-sha256:synthetic",
            "image": "image-sha256:synthetic",
            "acl_parent_chain": "acl-sha256:synthetic",
            "namespace_volume": "volume-sha256:synthetic",
        }
        evidence = {
            "schema_version": 1,
            "attestation_id": evidence_id,
            "tenant_id": "acme",
            "agent_id": "controlling",
            "deployment_generation": "generation-synthetic-1",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "signed_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "service_identity": "svc-acme-controlling",
            "tenant_identity": "tenant-acme",
            "fingerprints": fingerprints,
            "matrix": {name: "passed" for name in agent_cli.PRODUCTION_MATRIX_OUTCOMES},
        }
        evidence.update(overrides)
        attestation_dir = external / "attestations" / evidence_id
        keys_dir = external / "keys"
        runtime_dir = external / "runtime"
        attestation_dir.mkdir(parents=True)
        keys_dir.mkdir()
        runtime_dir.mkdir()
        signers = {}
        for name in ("platform", "security", "control-plane"):
            private = Ed25519PrivateKey.generate()
            signers[name] = private
            (keys_dir / f"{name}.pub").write_bytes(
                base64.b64encode(
                    private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                )
            )
        root_signer = Ed25519PrivateKey.generate()
        agent_cli.CONTROL_PLANE_ROOT_PUBLIC_KEY_B64 = base64.b64encode(
            root_signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        ).decode("ascii")
        key_pins = {
            f"{name}.pub": hashlib.sha256(
                signers[name].public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).hexdigest()
            for name in ("platform", "security", "control-plane")
        }
        trust_config = {
            "schema_version": 1,
            "trust_config_id": "synthetic-trust-001",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "signed_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "key_pins": key_pins,
        }
        config_bytes = agent_cli._canonical_json(trust_config)
        (external / "trust-config.json").write_bytes(config_bytes)
        (external / "trust-config.sig").write_bytes(
            base64.b64encode(root_signer.sign(config_bytes))
        )
        canonical = agent_cli._canonical_json(evidence)
        (attestation_dir / "attestation.json").write_bytes(canonical)
        for name in ("platform", "security"):
            (attestation_dir / f"{name}.sig").write_bytes(
                base64.b64encode(signers[name].sign(canonical))
            )
        facts = {
            name: evidence[name]
            for name in (
                "schema_version", "attestation_id", "tenant_id", "agent_id",
                "deployment_generation", "service_identity", "tenant_identity", "fingerprints",
                "issued_at", "signed_at", "expires_at",
            )
        }
        facts["issued_at"] = (now - timedelta(minutes=1)).isoformat()
        facts["signed_at"] = now.isoformat()
        facts["expires_at"] = (now + timedelta(minutes=10)).isoformat()
        facts.update(current_overrides)
        facts_bytes = agent_cli._canonical_json(facts)
        runtime_tenant = runtime_dir / "acme" / "controlling"
        runtime_tenant.mkdir(parents=True)
        (runtime_tenant / "current-facts.json").write_bytes(facts_bytes)
        (runtime_tenant / "current-facts.sig").write_bytes(
            base64.b64encode(signers["control-plane"].sign(facts_bytes))
        )
        reference = instance / "state" / "production-attestation-reference.json"
        reference.write_text(
            json.dumps({"schema_version": 1, "attestation_id": evidence_id}),
            encoding="utf-8",
        )
        return external

    def _production_ready(self, instance: Path) -> None:
        self._signed_acceptance(instance)
        self._loop_health(instance)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": datetime.now(timezone.utc).isoformat(),
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

    def test_ready_instance_shows_green_operator_summary(
        self, tmp_path, capsys
    ):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance)
        self._loop_health(instance)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": "2026-07-21T19:00:00+00:00",
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )
        output = capsys.readouterr().out

        assert result == 0
        assert "acme/controlling" in output
        assert "GRÜN" in output
        assert "3/3" in output
        assert "4/3" not in output
        assert "0/3" in output
        assert "latest-controlling-report.html" in output

    @pytest.mark.parametrize(
        ("replacement", "label"),
        [
            (b"<html>tampered</html>", "modified"),
            (b"\xff", "invalid-utf8"),
            (b"x" * (agent_cli.MAX_MANAGEMENT_REPORT_HTML_BYTES + 1), "oversized"),
        ],
        ids=["modified", "invalid-utf8", "oversized"],
    )
    def test_status_rejects_unverified_management_report_view(
        self, tmp_path, capsys, replacement, label
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        html = instance / "artifacts" / "latest-controlling-report.html"
        html.write_bytes(replacement)

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )
        output = capsys.readouterr().out

        assert result == 1, label
        assert "ROT" in output
        assert "Managementreport: nicht verfügbar bzw. nicht verifiziert" in output
        assert str(html) not in output

    @pytest.mark.parametrize("mutation", ["missing-management", "wrong-report-type"])
    def test_status_fails_closed_for_renderer_invalid_latest_payload(
        self, tmp_path, capsys, mutation
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        latest = instance / "artifacts" / "latest-controlling-report.json"
        payload = json.loads(latest.read_text(encoding="utf-8"))
        if mutation == "missing-management":
            payload.pop("management")
        else:
            payload["report"] = []
        latest.write_text(json.dumps(payload), encoding="utf-8")

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    def test_status_rejects_stale_management_report_view(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)
        html = instance / "artifacts" / "latest-controlling-report.html"
        stale = html.read_bytes()
        self._signed_acceptance(instance, runs=1)
        html.write_bytes(stale)
        self._loop_health(instance)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": datetime.now(timezone.utc).isoformat(),
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    def test_status_rejects_symlinked_management_report_view(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        html = instance / "artifacts" / "latest-controlling-report.html"
        outside = tmp_path / "outside-report.html"
        outside.write_bytes(html.read_bytes())
        html.unlink()
        try:
            html.symlink_to(outside)
        except OSError:
            pytest.skip("Symlinks are unavailable on this test host")

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    def test_interrupted_view_publication_leaves_status_red(
        self, tmp_path, capsys, monkeypatch
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        latest = instance / "artifacts" / "latest-controlling-report.json"
        published = latest.read_bytes()
        original_atomic_text = artifacts_module._atomic_text

        def interrupt_html(path, text):
            if path.name == "latest-controlling-report.html":
                raise OSError("synthetic interrupted HTML publication")
            original_atomic_text(path, text)

        monkeypatch.setattr(artifacts_module, "_atomic_text", interrupt_html)
        with pytest.raises(OSError, match="interrupted HTML"):
            self._signed_acceptance(instance, runs=1)
        assert latest.read_bytes() == published

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    @pytest.mark.parametrize("health", [{}, {"schema_version": 1, "status": "frozen"}])
    def test_required_supervisor_health_makes_status_red(self, tmp_path, capsys, health):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        config_path = instance / "project" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["supervisor"] = {"supervisor_required": True, "crash_threshold": 3,
                                "base_backoff_seconds": 1, "max_backoff_seconds": 2}
        config_path.write_text(json.dumps(config), encoding="utf-8")
        (instance / "state" / "supervisor-health.json").write_text(
            json.dumps(health), encoding="utf-8"
        )
        assert agent_cli.cmd_status(agent_cli.argparse.Namespace(instance=str(instance))) == 1
        assert "ROT" in capsys.readouterr().out

    def test_production_status_requires_external_evidence(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        self._production_ready(instance)

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    def test_production_status_rejects_malformed_or_incomplete_evidence(self, tmp_path, capsys, monkeypatch):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        external = tmp_path / "trust"
        external.mkdir()
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(external))
        (instance / "state" / "production-attestation-reference.json").write_text(
            json.dumps({"schema_version": 1, "attestation_id": "synthetic-001"}),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "overrides",
        [
            {"tenant_id": "other"},
            {"expires_at": "2020-01-01T00:00:00+00:00"},
        ],
    )
    def test_production_status_rejects_mismatched_or_expired_evidence(
        self, tmp_path, capsys, monkeypatch, overrides
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        trust = self._production_evidence(instance, tmp_path / "trust", **overrides)
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    @pytest.mark.parametrize("inside_instance", [True, False])
    def test_production_status_rejects_overlapping_tenant_trust_root(self, tmp_path, capsys, monkeypatch, inside_instance):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        local = instance / "state" / "trust" if inside_instance else tmp_path
        trust = self._production_evidence(instance, local)
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    @pytest.mark.parametrize(
        ("mutation", "current_overrides"),
        [
            ("tamper", {}),
            (None, {"expires_at": "2020-01-01T00:00:00+00:00"}),
            (None, {"deployment_generation": "replayed-generation"}),
        ],
    )
    def test_production_status_rejects_tampered_stale_or_replayed_runtime_facts(
        self, tmp_path, capsys, monkeypatch, mutation, current_overrides
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        trust = self._production_evidence(
            instance, tmp_path / "trust", current_overrides=current_overrides
        )
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))
        if mutation == "tamper":
            path = trust / "attestations" / "synthetic-001" / "attestation.json"
            path.write_bytes(path.read_bytes().replace(b"synthetic", b"tampered", 1))

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    @pytest.mark.parametrize("trust_root", ["\\\\server\\share", "//server/share", "C:\\relative\\..\\escape"])
    def test_production_status_rejects_unc_or_invalid_trust_root(
        self, tmp_path, capsys, monkeypatch, trust_root
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, trust_root)

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    @pytest.mark.parametrize("case", ["missing_config", "wrong_root", "key_swap", "duplicate"])
    def test_production_status_rejects_untrusted_or_duplicate_trust_keys(
        self, tmp_path, capsys, monkeypatch, case
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        trust = self._production_evidence(instance, tmp_path / "trust")
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))
        if case == "missing_config":
            (trust / "trust-config.json").unlink()
        elif case == "wrong_root":
            path = trust / "trust-config.sig"
            path.write_bytes(base64.b64encode(Ed25519PrivateKey.generate().sign(
                (trust / "trust-config.json").read_bytes()
            )))
        elif case == "key_swap":
            replacement = Ed25519PrivateKey.generate().public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw
            )
            (trust / "keys" / "platform.pub").write_bytes(base64.b64encode(replacement))
        else:
            raw = (trust / "keys" / "platform.pub").read_bytes()
            (trust / "keys" / "security.pub").write_bytes(raw)

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    def test_production_status_rejects_root_swap(self, tmp_path, capsys, monkeypatch):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        first_trust = self._production_evidence(instance, tmp_path / "trust-one")
        self._production_evidence(instance, tmp_path / "trust-two")
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(first_trust))

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    def test_production_status_rejects_reference_path_traversal(self, tmp_path, capsys, monkeypatch):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        trust = self._production_evidence(instance, tmp_path / "trust")
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))
        (instance / "state" / "production-attestation-reference.json").write_text(
            json.dumps({"schema_version": 1, "attestation_id": "../other"}),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 1
        assert "Produktionsfreigabe: ROT" in capsys.readouterr().out

    def test_production_status_accepts_complete_external_synthetic_evidence(
        self, tmp_path, capsys, monkeypatch
    ):
        instance = self._instance(tmp_path)
        self._production_ready(instance)
        trust = self._production_evidence(instance, tmp_path / "trust")
        monkeypatch.setenv(agent_cli.PRODUCTION_TRUST_ROOT_ENV, str(trust))

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance), production=True)
        )

        assert result == 0
        assert "Produktionsfreigabe: GRÜN" in capsys.readouterr().out

    @pytest.mark.parametrize("poll_result", ["success", "idle", "already_enqueued"])
    def test_fresh_running_loop_health_allows_green_status(
        self, tmp_path, capsys, poll_result
    ):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)
        self._loop_health(instance, poll_result=poll_result)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": datetime.now(timezone.utc).isoformat(),
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 0
        assert "GRÜN" in capsys.readouterr().out

    @pytest.mark.parametrize(
        ("health", "raw"),
        [
            (
                {
                    "status": "running",
                    "updated_at": "2020-01-01T00:00:00+00:00",
                    "poll_result": "success",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "running",
                    "updated_at": "not-a-date",
                    "poll_result": "success",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "running",
                    "updated_at": "2026-07-22T01:00:00",
                    "poll_result": "success",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "running",
                    "updated_at": "0001-01-01T00:00:00+14:00",
                    "poll_result": "success",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "running",
                    "updated_at": "FUTURE",
                    "poll_result": "success",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "running",
                    "updated_at": "NOW",
                    "poll_result": "success",
                    "schema_version": True,
                },
                None,
            ),
            (
                {
                    "status": "error",
                    "updated_at": "NOW",
                    "poll_result": "error",
                    "schema_version": 1,
                },
                None,
            ),
            (
                {
                    "status": "stopped",
                    "updated_at": "NOW",
                    "poll_result": "stopped",
                    "schema_version": 1,
                },
                None,
            ),
            (None, "{kaputt"),
        ],
    )
    def test_unhealthy_loop_health_is_red(self, tmp_path, capsys, health, raw):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)
        if health is not None:
            health = dict(health)
            if health["updated_at"] == "NOW":
                health["updated_at"] = datetime.now(timezone.utc).isoformat()
            elif health["updated_at"] == "FUTURE":
                health["updated_at"] = "2999-01-01T00:00:00+00:00"
            raw = json.dumps(health)
        (instance / "state" / "loop-health.json").write_text(
            raw, encoding="utf-8"
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    def test_missing_loop_health_is_red(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    @pytest.mark.parametrize("interval", [True, 0, 1441, 10**100])
    def test_invalid_loop_interval_makes_status_red(
        self, tmp_path, capsys, interval
    ):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)
        self._loop_health(instance)
        config_path = instance / "project" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["loop_interval_minutes"] = interval
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param(b"\xff", id="invalid-utf8"),
            pytest.param(b"[" * 1100 + b"]" * 1100, id="recursive-json"),
            pytest.param(
                b"{" + b'"x":0,' * 180000 + b'"y":0}',
                id="over-size-limit",
            ),
            pytest.param(
                b'{"number":' + b"9" * 5000 + b"}",
                id="integer-digit-limit",
            ),
        ],
    )
    def test_status_json_reader_fails_closed_for_unsafe_payloads(
        self, tmp_path, payload
    ):
        root = tmp_path / "instance"
        (root / "state").mkdir(parents=True)
        (root / "state" / "loop-health.json").write_bytes(payload)

        value, invalid = agent_cli._read_status_json(
            root, "state/loop-health.json"
        )

        assert value == {}
        assert invalid is True

    def test_forged_latest_report_cannot_turn_status_green(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        (instance / "artifacts" / "latest-controlling-report.json").write_text(
            json.dumps(
                {"acceptance": {"passed": True, "repeatable_run_count": 99}}
            ),
            encoding="utf-8",
        )
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": "2026-07-21T19:00:00+00:00",
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )
        output = capsys.readouterr().out

        assert result == 1
        assert "GRÜN" not in output

    def test_status_rejects_symlinked_artifact_directory(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        outside = tmp_path / "outside-artifacts"
        outside.mkdir()
        (outside / "latest-controlling-report.json").write_text(
            json.dumps(
                {"acceptance": {"passed": True, "repeatable_run_count": 3}}
            ),
            encoding="utf-8",
        )
        artifacts = instance / "artifacts"
        artifacts.rmdir()
        try:
            artifacts.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("Symlinks are unavailable on this test host")

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out

    def test_status_does_not_render_untrusted_multiline_timestamp(
        self, tmp_path, capsys
    ):
        instance = self._instance(tmp_path)
        self._signed_acceptance(instance, runs=3)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "success",
                    "last_result_at": "2026-07-21T19:00:00+00:00\nFAKE-GRÜN",
                    "consecutive_failures": 0,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )
        output = capsys.readouterr().out

        assert result == 1
        assert "FAKE-GRÜN" not in output

    def test_failed_loop_shows_red_and_action(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        (instance / "state" / "adaptive-schedule.json").write_text(
            json.dumps(
                {
                    "last_result": "failed",
                    "last_result_at": "2026-07-21T19:00:00+00:00",
                    "consecutive_failures": 3,
                }
            ),
            encoding="utf-8",
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )
        output = capsys.readouterr().out

        assert result == 1
        assert "ROT" in output
        assert "3/3" in output
        assert "Fehler beheben" in output

    def test_malformed_status_state_fails_closed(self, tmp_path, capsys):
        instance = self._instance(tmp_path)
        (instance / "state" / "adaptive-schedule.json").write_text(
            "{kaputt", encoding="utf-8"
        )

        result = agent_cli.cmd_status(
            agent_cli.argparse.Namespace(instance=str(instance))
        )

        assert result == 1
        assert "ROT" in capsys.readouterr().out


class TestInstanceFactory:
    def test_create_kmu_controlling_preset_has_hourly_adaptive_schedule_and_safe_defaults(
        self, tmp_path
    ):
        args = agent_cli.argparse.Namespace(
            tenant="Acme GmbH",
            agent="Controlling",
            output=str(tmp_path),
            full=False,
            no_self_test=False,
            preset="kmu-controlling",
        )

        assert agent_cli.cmd_create(args) == 0
        project = tmp_path / "acme-gmbh" / "controlling" / "project"
        config = json.loads((project / "config.json").read_text(encoding="utf-8"))
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))

        assert config["loop_interval_minutes"] == 60
        assert config["quality_threshold"] == 8
        schedule = config["adaptive_schedule"]
        assert schedule["schema_version"] == 1
        assert schedule["enabled"] is True
        assert {
            "new_input",
            "changed_input",
            "recovery",
            "pending_approval",
            "periodic_review",
        }.issubset(schedule["prompt_profiles"])
        assert "approval_pending" not in schedule["prompt_profiles"]
        assert schedule["max_consecutive_failures"] >= 1
        assert manifest["approval_required_for"] == [
            "external communication",
            "send",
            "publish",
        ]
        instance = project.parent
        assert all(
            (instance / directory).is_dir()
            for directory in ("inbox", "data", "imports", "state", "artifacts")
        )

    def test_kmu_controlling_preset_writes_operating_files_and_preserves_identity(
        self, tmp_path
    ):
        args = agent_cli.argparse.Namespace(
            tenant="Acme",
            agent="Finance Pilot",
            output=str(tmp_path),
            full=False,
            no_self_test=True,
            preset="kmu-controlling",
        )

        assert agent_cli.cmd_create(args) == 0
        project = tmp_path / "acme" / "finance-pilot" / "project"
        config = json.loads((project / "config.json").read_text(encoding="utf-8"))
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))

        assert config["instance"] == {"tenant_id": "acme", "agent_id": "finance-pilot"}
        assert manifest["instance"] == {
            "tenant_id": "acme",
            "agent_id": "finance-pilot",
        }
        assert (project / "SOUL.md").is_file()
        assert (project / "workflows" / "main.md").is_file()
        assert (project / "knowledge" / "kpi-rules.md").is_file()
        assert (
            "deterministisch"
            in (project / "SOUL.md").read_text(encoding="utf-8").lower()
        )

    def test_create_places_identity_in_separate_tenant_agent_root(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            agent_cli, "_collect_answers", lambda mode="beginner": _make_answers()
        )
        args = agent_cli.argparse.Namespace(
            tenant="Acme GmbH",
            agent="Inbox Triage",
            output=str(tmp_path),
            full=False,
            no_self_test=False,
        )
        assert agent_cli.cmd_create(args) == 0
        instance = tmp_path / "acme-gmbh" / "inbox-triage"
        config = json.loads(
            (instance / "project" / "config.json").read_text(encoding="utf-8")
        )
        assert config["instance"] == {
            "tenant_id": "acme-gmbh",
            "agent_id": "inbox-triage",
        }

    def test_create_refuses_existing_target_without_merging(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "acme" / "inbox"
        target.mkdir(parents=True)
        sentinel = target / "keep.txt"
        sentinel.write_text("do not overwrite", encoding="utf-8")
        monkeypatch.setattr(
            agent_cli, "_collect_answers", lambda mode="beginner": _make_answers()
        )
        args = agent_cli.argparse.Namespace(
            tenant="acme",
            agent="inbox",
            output=str(tmp_path),
            full=False,
            no_self_test=False,
        )
        assert agent_cli.cmd_create(args) == 1
        assert sentinel.read_text(encoding="utf-8") == "do not overwrite"

    def test_validate_detects_identity_mismatch(self, tmp_path):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(
            instance, _make_answers(), tenant_id="acme", agent_id="other"
        )
        report = agent_cli._validate_instance(instance)
        assert not report.ok
        assert any("agent_id" in problem for problem in report.problems)

    def test_run_uses_selected_instance_root_and_identity(
        self, tmp_path, monkeypatch, capsys
    ):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(
            instance, _make_answers(), tenant_id="acme", agent_id="inbox"
        )
        called = {}

        class FakeOrchestrator:
            def __init__(self, root):
                called["root"] = Path(root)

            def run(self, task, *, tools=None, tenant=None):
                called.update(task=task, tools=tools, tenant=tenant)
                return type("Result", (), {"success": True})()

        monkeypatch.setattr(agent_cli, "_instance_orchestrator", FakeOrchestrator)
        args = agent_cli.argparse.Namespace(
            instance=str(instance), task="offline smoke", tenant=None, extra=[]
        )
        assert agent_cli.cmd_run(args) == 0
        assert called == {
            "root": instance,
            "task": "offline smoke",
            "tools": {},
            "tenant": "acme",
        }
        assert "acme/inbox" in capsys.readouterr().out

    def test_one_shot_kmu_run_receives_local_controlling_tools(
        self, tmp_path, monkeypatch
    ):
        instance = tmp_path / "acme" / "controlling"
        agent_cli._write_template_project(
            instance,
            agent_cli._kmu_controlling_answers(),
            tenant_id="acme",
            agent_id="controlling",
        )
        agent_cli._apply_preset(instance, "kmu-controlling")
        called = {}

        class FakeOrchestrator:
            def __init__(self, root):
                called["root"] = Path(root)

            def run(self, task, *, tools=None, tenant=None):
                called.update(task=task, tools=tools, tenant=tenant)
                return type("Result", (), {"success": True})()

        monkeypatch.setattr(agent_cli, "_instance_orchestrator", FakeOrchestrator)
        args = agent_cli.argparse.Namespace(
            instance=str(instance), task="calculate KPIs", tenant=None, extra=[]
        )

        assert agent_cli.cmd_run(args) == 0
        assert set(called["tools"]) == {"read", "compute", "report"}
        assert called["tenant"] == "acme"

    def test_run_rejects_tenant_that_differs_from_instance(
        self, tmp_path, monkeypatch, capsys
    ):
        instance = tmp_path / "acme" / "inbox"
        agent_cli._write_template_project(
            instance, _make_answers(), tenant_id="acme", agent_id="inbox"
        )
        monkeypatch.setattr(
            agent_cli,
            "_instance_orchestrator",
            lambda root: pytest.fail(
                "orchestrator must not start for a tenant mismatch"
            ),
        )
        args = agent_cli.argparse.Namespace(
            instance=str(instance), task="offline smoke", tenant="other", extra=[]
        )
        assert agent_cli.cmd_run(args) == 1
        assert "other" in capsys.readouterr().out

    def test_instance_schedule_cycle_uses_instance_root_and_preserves_tenant(
        self, tmp_path, monkeypatch
    ):
        instance = tmp_path / "acme" / "controlling"
        agent_cli._write_template_project(
            instance,
            agent_cli._kmu_controlling_answers(),
            tenant_id="acme",
            agent_id="controlling",
        )
        agent_cli._apply_preset(instance, "kmu-controlling")
        config = json.loads(
            (instance / "project" / "config.json").read_text(encoding="utf-8")
        )
        calls = {}

        class FakeOrchestrator:
            def run(self, task, *, tools=None, tenant=None, request_id=None):
                calls.update(
                    task=task, tools=tools, tenant=tenant, request_id=request_id
                )
                return type("Result", (), {"success": True})()

        def fake_cycle(*, root, agent_config, orchestrator, tools):
            calls.update(root=root, agent_config=agent_config, tools_argument=tools)
            orchestrator.run("scheduled", tools=tools, request_id="request-1")
            return ScheduledDecision(True, "new_input", "request-1", "scheduled")

        monkeypatch.setattr(agent_cli, "run_scheduled_cycle", fake_cycle)
        agent_cli._run_instance_schedule_cycle(
            instance, config, "acme", FakeOrchestrator()
        )

        assert calls["root"] == instance
        assert calls["agent_config"] == config
        assert calls["tenant"] == "acme"
        assert calls["request_id"] == "request-1"
        assert set(calls["tools_argument"]) == {"read", "compute", "report"}

    def test_instance_schedule_idle_does_not_run_orchestrator(
        self, tmp_path, monkeypatch
    ):
        instance = tmp_path / "acme" / "controlling"
        config = {"instance": {"tenant_id": "acme", "agent_id": "controlling"}}

        class FailingOrchestrator:
            def run(self, *args, **kwargs):
                pytest.fail("idle schedule must not invoke the orchestrator")

        monkeypatch.setattr(
            agent_cli,
            "run_scheduled_cycle",
            lambda **kwargs: ScheduledDecision(False, "idle"),
        )
        decision = agent_cli._run_instance_schedule_cycle(
            instance, config, "acme", FailingOrchestrator()
        )
        assert decision.reason == "idle"

    @pytest.mark.parametrize(
        ("decision", "expected"),
        [
            (ScheduledDecision(True, "new_input", execution_success=True), ("running", "success")),
            (ScheduledDecision(True, "new_input", execution_success=False), ("error", "error")),
            (ScheduledDecision(True, "new_input"), ("error", "error")),
            (ScheduledDecision(False, "idle"), ("running", "idle")),
            (ScheduledDecision(False, "already_enqueued"), ("running", "already_enqueued")),
        ],
        ids=("success", "failure", "unknown", "idle", "already-enqueued"),
    )
    def test_decision_loop_health_requires_successful_execution(
        self, decision, expected
    ):
        assert agent_cli._decision_loop_health(decision) == expected

    def test_instance_loop_writes_error_for_failed_dispatch(
        self, tmp_path, monkeypatch
    ):
        writes = []
        monkeypatch.setattr(
            agent_cli,
            "_run_instance_schedule_cycle",
            lambda *_args: ScheduledDecision(
                True, "new_input", execution_success=False
            ),
        )
        monkeypatch.setattr(
            agent_cli,
            "_write_loop_health",
            lambda _root, status, result: writes.append((status, result)),
        )
        monkeypatch.setattr(
            agent_cli.time,
            "sleep",
            lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt),
        )

        agent_cli._run_instance_loop(
            tmp_path, {"loop_interval_minutes": 60}, "acme", object()
        )

        assert writes == [("error", "error"), ("stopped", "stopped")]

    def test_fresh_kmu_missing_data_cycle_records_success_and_waits(
        self, tmp_path, monkeypatch
    ):
        import brain
        from core.controlling import ControllingComputeTool, ControllingReportTool

        instance = tmp_path / "acme" / "controlling"
        agent_cli._write_template_project(
            instance,
            agent_cli._kmu_controlling_answers(),
            tenant_id="acme",
            agent_id="controlling",
        )
        agent_cli._apply_preset(instance, "kmu-controlling")
        config = json.loads(
            (instance / "project" / "config.json").read_text(encoding="utf-8")
        )
        monkeypatch.setattr(
            brain,
            "complete",
            lambda *a, **k: pytest.fail("missing-data status must not call a planner LLM"),
        )
        monkeypatch.setattr(
            brain,
            "evaluate",
            lambda *a, **k: {
                "score": 5,
                "passes": False,
                "feedback": ["LLM nicht verfuegbar"],
            },
        )
        monkeypatch.setattr(
            ControllingComputeTool,
            "safe_run",
            lambda *a, **k: pytest.fail("missing-data status must not compute KPIs"),
        )
        monkeypatch.setattr(
            ControllingReportTool,
            "safe_run",
            lambda *a, **k: pytest.fail("missing-data status must not write a report"),
        )
        orchestrator = agent_cli._instance_orchestrator(instance)

        first = agent_cli._run_instance_schedule_cycle(
            instance, config, "acme", orchestrator
        )
        repeated = agent_cli._run_instance_schedule_cycle(
            instance, config, "acme", orchestrator
        )

        assert first.should_enqueue and first.reason == "missing_data"
        assert repeated.should_enqueue is False
        assert repeated.reason == "already_enqueued"
        state = json.loads(
            (instance / "state" / "adaptive-schedule.json").read_text(
                encoding="utf-8"
            )
        )
        assert state["last_result"] == "success"
        assert state["consecutive_failures"] == 0
        runs = json.loads(
            (instance / "state" / "core" / "runs.json").read_text(
                encoding="utf-8"
            )
        )
        assert len(runs) == 1
        assert [step["action"] for step in runs[0]["steps"]] == ["status", "wait"]
        assert all(step["tool"] is None for step in runs[0]["steps"])

    def test_run_loop_uses_instance_config_interval(self, tmp_path, monkeypatch):
        instance = tmp_path / "acme" / "controlling"
        agent_cli._write_template_project(
            instance, _make_answers(), tenant_id="acme", agent_id="controlling"
        )
        config_path = instance / "project" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["loop_interval_minutes"] = 60
        config_path.write_text(json.dumps(config), encoding="utf-8")
        calls = {}

        monkeypatch.setattr(
            agent_cli,
            "_instance_orchestrator",
            lambda root: calls.setdefault("root", root) or object(),
        )
        monkeypatch.setattr(
            agent_cli,
            "_run_instance_loop",
            lambda root, cfg, tenant, orchestrator: calls.update(
                loop=(root, cfg["loop_interval_minutes"], tenant, orchestrator)
            ),
        )
        args = agent_cli.argparse.Namespace(
            instance=str(instance), task=None, tenant=None, extra=[], loop=True
        )

        assert agent_cli.cmd_run(args) == 0
        assert calls["loop"][:3] == (instance, 60, "acme")

    @pytest.mark.parametrize("interval", [True, 0, 1441, 10**100])
    def test_instance_loop_rejects_invalid_interval(self, tmp_path, interval):
        with pytest.raises(ValueError, match="loop interval"):
            agent_cli._run_instance_loop(
                tmp_path,
                {"loop_interval_minutes": interval},
                "acme",
                object(),
            )

        assert not (tmp_path / "state" / "loop-health.json").exists()

    def test_loop_health_rejects_symlinked_state_directory(self, tmp_path):
        instance = tmp_path / "instance"
        outside = tmp_path / "outside"
        instance.mkdir()
        outside.mkdir()
        try:
            (instance / "state").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("Symlinks are unavailable on this test host")

        with pytest.raises(OSError):
            agent_cli._write_loop_health(instance, "running", "success")

        assert not (outside / "loop-health.json").exists()

    def test_instance_loop_survives_cycle_error_until_stopped(
        self, tmp_path, monkeypatch, capsys
    ):
        calls = []

        def failing_cycle(*args, **kwargs):
            calls.append("cycle")
            raise RuntimeError("temporary failure")

        def stop_after_wait(seconds):
            calls.append(("wait", seconds))
            raise KeyboardInterrupt

        monkeypatch.setattr(agent_cli, "_run_instance_schedule_cycle", failing_cycle)
        monkeypatch.setattr(agent_cli.time, "sleep", stop_after_wait)
        agent_cli._run_instance_loop(
            tmp_path, {"loop_interval_minutes": 60}, "acme", object()
        )

        assert calls == ["cycle", ("wait", 3600)]
        health = json.loads(
            (tmp_path / "state" / "loop-health.json").read_text(encoding="utf-8")
        )
        assert health["status"] == "stopped"
        assert health["poll_result"] == "stopped"
        assert "temporary failure" not in json.dumps(health)
        assert "temporary failure" not in capsys.readouterr().out

    def test_instance_loop_records_each_poll_and_error_without_details(
        self, tmp_path, monkeypatch, capsys
    ):
        decisions = iter(
            [
                ScheduledDecision(True, "missing_data", execution_success=True),
                ScheduledDecision(False, "already_enqueued"),
                ScheduledDecision(False, "schedule_disabled"),
                ScheduledDecision(False, "frozen_after_failures"),
                ScheduledDecision(False, "untrusted_detail"),
            ]
        )
        writes = []

        def cycle(*args, **kwargs):
            try:
                return next(decisions)
            except StopIteration:
                raise RuntimeError("synthetic customer detail")

        def record(root, status, poll_result):
            writes.append((status, poll_result))

        def sleep(_seconds):
            if len(writes) >= 6:
                raise KeyboardInterrupt

        monkeypatch.setattr(agent_cli, "_run_instance_schedule_cycle", cycle)
        monkeypatch.setattr(agent_cli, "_write_loop_health", record)
        monkeypatch.setattr(agent_cli.time, "sleep", sleep)

        agent_cli._run_instance_loop(
            tmp_path, {"loop_interval_minutes": 60}, "acme", object()
        )

        assert writes == [
            ("running", "success"),
            ("running", "already_enqueued"),
            ("error", "error"),
            ("error", "error"),
            ("error", "error"),
            ("error", "error"),
            ("stopped", "stopped"),
        ]
        output = capsys.readouterr().out
        assert "synthetic customer detail" not in output
        assert "untrusted_detail" not in output

    def test_supervisor_restarts_with_bounded_exponential_backoff(self, tmp_path):
        class Child:
            def __init__(self, code): self.code = code
            def poll(self): return self.code

        children = iter([Child(7), Child(9), Child(0)])
        sleeps = []
        def clock():
            return datetime(2026, 1, 1, tzinfo=timezone.utc)
        rc = agent_cli._supervise_instance(
            tmp_path,
            {"supervisor": {"crash_threshold": 3, "base_backoff_seconds": 2, "max_backoff_seconds": 3}},
            child_factory=lambda _command: next(children), sleep=sleeps.append, now=clock,
        )
        assert rc == 1
        assert sleeps == [2, 3]
        health = json.loads((tmp_path / "state" / "supervisor-health.json").read_text(encoding="utf-8"))
        assert health["status"] == "frozen"
        assert health["restart_count"] == 2
        assert health["consecutive_crashes"] == 3
        assert health["exit_code"] == 0

    def test_supervisor_freezes_at_crash_threshold(self, tmp_path):
        class Child:
            def poll(self): return 12

        sleeps = []
        rc = agent_cli._supervise_instance(
            tmp_path,
            {"supervisor": {"crash_threshold": 2, "base_backoff_seconds": 1, "max_backoff_seconds": 1}},
            child_factory=lambda _command: Child(), sleep=sleeps.append,
        )
        assert rc == 1 and sleeps == [1]
        health = json.loads((tmp_path / "state" / "supervisor-health.json").read_text(encoding="utf-8"))
        assert health["status"] == "frozen"
        assert health["consecutive_crashes"] == 2

    def test_supervisor_refreshes_long_backoff_in_heartbeat_chunks(self, tmp_path):
        class Child:
            def poll(self): return 1
        sleeps = []
        assert agent_cli._supervise_instance(
            tmp_path, {"supervisor": {"crash_threshold": 2, "base_backoff_seconds": 3600, "max_backoff_seconds": 3600}},
            child_factory=lambda _command: Child(), sleep=sleeps.append,
        ) == 1
        assert sleeps == [60] * 60

    def test_supervisor_health_rejects_symlinked_state(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        try:
            (tmp_path / "state").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("Symlinks are unavailable on this test host")
        with pytest.raises(OSError):
            agent_cli._write_supervisor_health(tmp_path, "running", 0, 0, None)
        assert not (outside / "supervisor-health.json").exists()

    def test_supervisor_clean_interrupt_stops_without_restart(self, tmp_path):
        calls = []
        class Child:
            def poll(self):
                raise KeyboardInterrupt

        assert agent_cli._supervise_instance(
            tmp_path, {}, child_factory=lambda _command: calls.append(1) or Child()
        ) == 0
        assert calls == [1]
        health = json.loads((tmp_path / "state" / "supervisor-health.json").read_text(encoding="utf-8"))
        assert health["status"] == "stopped"

    def test_supervisor_refreshes_health_while_child_is_running(self, tmp_path):
        writes = []
        class Child:
            def __init__(self): self.calls = 0
            def poll(self):
                self.calls += 1
                return None if self.calls == 1 else 4
        real_write = agent_cli._write_supervisor_health
        def record(*args, **kwargs):
            writes.append(args[1])
            return real_write(*args, **kwargs)
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(agent_cli, "_write_supervisor_health", record)
            agent_cli._supervise_instance(
                tmp_path, {"supervisor": {"crash_threshold": 1, "base_backoff_seconds": 1, "max_backoff_seconds": 1}},
                child_factory=lambda _command: Child(), sleep=lambda _seconds: None,
            )
        assert writes[:2] == ["running", "running"]

    def test_supervisor_spawn_failure_freezes_not_running(self, tmp_path):
        def fail_spawn(_command):
            raise OSError("synthetic")
        assert agent_cli._supervise_instance(
            tmp_path, {"supervisor": {"crash_threshold": 1, "base_backoff_seconds": 1, "max_backoff_seconds": 1}},
            child_factory=fail_spawn,
        ) == 1
        health = json.loads((tmp_path / "state" / "supervisor-health.json").read_text(encoding="utf-8"))
        assert health["status"] == "frozen"

    def test_supervisor_interrupt_terminates_live_child(self, tmp_path):
        class Child:
            def __init__(self): self.terminated = False
            def poll(self): return None
            def terminate(self): self.terminated = True
            def wait(self, timeout=None): return 0
        child = Child()
        def interrupt(_seconds): raise KeyboardInterrupt
        assert agent_cli._supervise_instance(tmp_path, {}, child_factory=lambda _command: child, sleep=interrupt) == 0
        assert child.terminated

    def test_supervisor_lock_rejects_duplicate_and_health_has_no_path(self, tmp_path):
        with agent_cli._supervisor_lock(tmp_path):
            with pytest.raises(RuntimeError, match="already running"):
                with agent_cli._supervisor_lock(tmp_path):
                    pass
        agent_cli._write_supervisor_health(tmp_path, "running", 0, 0, None)
        raw = (tmp_path / "state" / "supervisor-health.json").read_text(encoding="utf-8")
        assert str(tmp_path) not in raw
        assert agent_cli._supervisor_health_is_fresh(json.loads(raw))

    def test_supervisor_health_rejects_malformed_stale_and_frozen(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        health = {"schema_version": 1, "status": "frozen", "restart_count": 3,
                  "consecutive_crashes": 3, "exit_code": 1,
                  "updated_at": now.isoformat(), "next_restart_at": None}
        assert agent_cli._supervisor_health_is_fresh(health, now)
        health["updated_at"] = "not-a-time"
        assert not agent_cli._supervisor_health_is_fresh(health, now)

    @pytest.mark.parametrize("raw", [None, "enabled", ["enabled"], 1])
    def test_supervisor_config_rejects_present_non_object(self, raw):
        with pytest.raises(ValueError, match="must be an object"):
            agent_cli._supervisor_config({"supervisor": raw})

    def test_supervisor_health_requires_valid_backoff_schedule(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        health = {"schema_version": 1, "status": "backoff", "restart_count": 1,
                  "consecutive_crashes": 1, "exit_code": 1, "updated_at": now.isoformat(),
                  "next_restart_at": (now + timedelta(seconds=60)).isoformat()}
        assert agent_cli._supervisor_health_is_fresh(health, now)
        health["next_restart_at"] = None
        assert not agent_cli._supervisor_health_is_fresh(health, now)
        health["status"] = "running"
        assert agent_cli._supervisor_health_is_fresh(health, now)
        health["next_restart_at"] = (now + timedelta(seconds=1)).isoformat()
        assert not agent_cli._supervisor_health_is_fresh(health, now)


class TestCmdSetupSelfTest:
    def test_self_test_runs_and_succeeds(self, tmp_path: Path, capsys, monkeypatch):
        out_root = tmp_path / "out"
        args = agent_cli.argparse.Namespace(
            output=str(out_root), force=True, full=False, no_self_test=False
        )
        # Fragen umgehen: _collect_answers durch feste Antworten ersetzen.
        monkeypatch.setattr(
            agent_cli, "_collect_answers", lambda mode="beginner": _make_answers()
        )
        rc = agent_cli.cmd_setup(args)
        captured = capsys.readouterr()
        assert rc == 0
        assert "Selbsttest" in captured.out
        assert "einsatzbereit" in captured.out

    def test_self_test_failure_returns_nonzero(
        self, tmp_path: Path, capsys, monkeypatch
    ):
        out_root = tmp_path / "out"
        args = agent_cli.argparse.Namespace(
            output=str(out_root), force=True, full=False, no_self_test=False
        )
        monkeypatch.setattr(
            agent_cli, "_collect_answers", lambda mode="beginner": _make_answers()
        )

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
