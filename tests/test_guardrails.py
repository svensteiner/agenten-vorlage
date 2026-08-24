"""Deterministic input/output guardrails."""

from pathlib import Path

from core.context import ProjectContext
from core.governance import GovernancePolicy
from core.guardrails import InputGuardrail, OutputGuardrail, check_input_guardrail, check_output_guardrail
from core.verifier import Verifier


def test_input_tripwire_inventiere_buchungen():
    result = check_input_guardrail("Bitte inventiere Buchungen fuer Juni.")
    assert result.tripwire is True
    assert "Buchungen" in result.reason or "booking" in result.reason.lower()
    assert InputGuardrail().check("inventiere Buchungen")["tripwire"] is True


def test_input_tripwire_bookings_without_source():
    result = check_input_guardrail("Create bookings without source for the ledger")
    assert result.tripwire is True


def test_input_pass_normal_request():
    result = check_input_guardrail("Erstelle den Controlling-Bericht aus der Saldenliste.")
    assert result.tripwire is False
    assert result.reason == ""


def test_output_tripwire_amounts_without_sources():
    result = check_output_guardrail("EBITDA liegt bei 2.800 EUR im Monat.")
    assert result.tripwire is True
    assert "amounts" in result.reason
    assert OutputGuardrail().check("Umsatz 203.500 €")["tripwire"] is True


def test_output_tripwire_success_without_sources():
    result = check_output_guardrail("Report successfully completed with all KPIs.")
    assert result.tripwire is True
    assert "success" in result.reason


def test_output_pass_with_source_evidence():
    blob = (
        '{"source": "inbox/actuals/Saldenliste_Muster_Juni2026.xlsx", '
        '"method": "mapping", "reconciliation": {"mapped_account_count": 20}, '
        '"metrics": {"ebitda": {"month": "2800"}}}'
    )
    result = check_output_guardrail(blob)
    assert result.tripwire is False


def test_governance_wires_input_guardrail():
    ctx = ProjectContext(
        project_root=Path("."),
        config={"require_human_approval": False},
        manifest={"autonomy_level": "max", "hard_block_on_high_risk": False},
    )
    decision = GovernancePolicy().allow(
        "run",
        context=ctx,
        text="inventiere Buchungen ohne Beleg",
    )
    assert decision.allowed is False
    assert "input_guardrail" in decision.reason or decision.metadata.get("gate") == "input_guardrail"


def test_verifier_fails_closed_on_output_guardrail(monkeypatch):
    import brain

    monkeypatch.setattr(
        brain,
        "evaluate",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("guardrail must short-circuit")),
    )
    result = Verifier().verify("EBITDA 2.800 EUR and no Belege attached")
    assert result.passed is False
    assert result.metadata.get("mode") == "output_guardrail"
    assert any("output_guardrail" in item for item in result.feedback)
