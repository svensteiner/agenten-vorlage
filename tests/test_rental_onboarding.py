"""Instance snapshot and onboarding for provisioned rentals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.rentals import (
    RentalConflict,
    RentalNotOpenable,
    RentalService,
    RentalValidationError,
)
from core.rental_onboarding import (
    OnboardingValidationError,
    STARTER_FORECAST_CSV,
    STARTER_KONTEN_CSV,
    STARTER_REPORT_MD,
    apply_excel,
    apply_starter,
)


def _service(tmp_path: Path) -> RentalService:
    return RentalService(tmp_path / "rentals")


def _rent_controlling(tmp_path: Path) -> tuple[RentalService, dict]:
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-onboard-001",
    )
    return service, rental


def test_describe_controlling_instance_shows_soul_and_preset(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    snapshot = service.describe_instance("muster-kmu", rental["rental_id"])
    assert snapshot["display_name"] == "Muster KMU"
    assert snapshot["agent_id"] == "controlling"
    assert snapshot["preset_id"] == "kmu-controlling"
    assert snapshot["instance_path"] == "muster-kmu/controlling"
    assert snapshot["soul_title"]
    assert snapshot["onboarding"]["supported"] is True
    assert snapshot["onboarding"]["status"] == "empty"
    assert snapshot["onboarding"]["has_mapping"] is False
    assert snapshot["artifacts"] == []


def test_describe_reporting_instance_is_minimal_pack(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-onboard-001",
    )
    snapshot = service.describe_instance("muster-kmu", rental["rental_id"])
    assert snapshot["preset_id"] is None
    assert snapshot["soul_title"]
    assert snapshot["onboarding"]["supported"] is False
    assert snapshot["onboarding"]["status"] == "unsupported"
    report = next(item for item in snapshot["artifacts"] if item["path"] == "artifacts/starter-bericht.md")
    assert "Reporting-Musterbericht" in report["preview"]
    instance = tmp_path / "rentals" / "muster-kmu" / "reporting" / "artifacts" / "starter-bericht.md"
    assert instance.is_file()


def test_describe_rejects_ledger_only_and_cancelled(tmp_path):
    service = _service(tmp_path)
    invoices = service.rent(
        tenant_id="muster-kmu",
        agent_id="rechnungen",
        display_name="Muster KMU",
        idempotency_key="rent-invoices-onboard-001",
    )
    with pytest.raises(RentalNotOpenable, match="Pack folgt"):
        service.describe_instance("muster-kmu", invoices["rental_id"])

    controlling = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-onboard-002",
    )
    service.cancel(
        tenant_id="muster-kmu",
        rental_id=controlling["rental_id"],
        idempotency_key="cancel-onboard-001",
    )
    with pytest.raises(RentalNotOpenable, match="gekuendigt"):
        service.describe_instance("muster-kmu", controlling["rental_id"])


def test_describe_rejects_path_escape(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    record = (
        tmp_path
        / "rentals"
        / ".ledger"
        / "rentals"
        / "muster-kmu"
        / f"{rental['rental_id']}.json"
    )
    state = json.loads(record.read_text(encoding="utf-8"))
    state["instance_path"] = "../escape"
    record.write_text(
        json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RentalConflict, match="Instanzpfad"):
        service.describe_instance("muster-kmu", rental["rental_id"])


def test_starter_onboarding_writes_mapping_accounts_report_forecast(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    snapshot = service.onboard(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        mode="starter",
        idempotency_key="starter-001",
    )
    instance = tmp_path / "rentals" / "muster-kmu" / "controlling"
    mapping = instance / "project" / "pilot" / "account-mapping.json"
    konten = instance / "inbox" / "actuals" / "starter-konten.csv"
    forecast = instance / "inbox" / "forecast" / "starter-forecast.csv"
    report = instance / "artifacts" / "starter-bericht.md"
    drop = instance / "imports" / "actuals"
    assert mapping.is_file()
    assert konten.read_text(encoding="utf-8") == STARTER_KONTEN_CSV
    assert forecast.read_text(encoding="utf-8") == STARTER_FORECAST_CSV
    assert report.read_text(encoding="utf-8") == STARTER_REPORT_MD
    assert drop.is_dir()
    assert snapshot["onboarding"]["status"] == "ready"
    assert snapshot["onboarding"]["mode"] == "starter"
    assert snapshot["onboarding"]["has_mapping"] is True
    assert snapshot["onboarding"]["has_actuals"] is True
    assert snapshot["onboarding"]["has_forecast"] is True
    assert any(item["path"] == "artifacts/starter-bericht.md" for item in snapshot["artifacts"])
    report = next(item for item in snapshot["artifacts"] if item["path"] == "artifacts/starter-bericht.md")
    assert report["preview"].startswith("# Starter-Bericht")
    replay = service.onboard(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        mode="starter",
        idempotency_key="starter-002",
    )
    assert replay["onboarding"]["status"] == "ready"


def test_starter_rejects_reporting_and_ledger_only(tmp_path):
    service = _service(tmp_path)
    reporting = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-starter-001",
    )
    with pytest.raises(RentalValidationError, match="Controlling"):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=reporting["rental_id"],
            mode="starter",
            idempotency_key="starter-reporting",
        )
    invoices = service.rent(
        tenant_id="muster-kmu",
        agent_id="rechnungen",
        display_name="Muster KMU",
        idempotency_key="rent-invoices-starter-001",
    )
    with pytest.raises(RentalNotOpenable, match="Pack folgt"):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=invoices["rental_id"],
            mode="starter",
            idempotency_key="starter-invoices",
        )


def test_excel_onboarding_copies_bytes_verbatim(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    source = (
        Path(__file__).resolve().parents[1]
        / "presets"
        / "kmu-controlling"
        / "pilot"
        / "demo"
        / "Saldenliste_Muster_Juni2026.xlsx"
    )
    raw = source.read_bytes()
    snapshot = service.onboard(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        mode="excel",
        idempotency_key="excel-001",
        filename="Saldenliste_Muster.xlsx",
        file_bytes=raw,
    )
    instance = tmp_path / "rentals" / "muster-kmu" / "controlling"
    stored = instance / "inbox" / "actuals" / "Saldenliste_Muster.xlsx"
    assert stored.read_bytes() == raw
    mapping = instance / "project" / "pilot" / "account-mapping.json"
    assert mapping.is_file()
    assert snapshot["onboarding"]["status"] == "ready"
    assert snapshot["onboarding"]["mode"] == "excel"
    replay = service.onboard(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        mode="excel",
        idempotency_key="excel-002",
        filename="Saldenliste_Muster.xlsx",
        file_bytes=raw,
    )
    assert stored.read_bytes() == raw
    assert replay["onboarding"]["has_actuals"] is True


@pytest.mark.parametrize(
    "filename",
    ["../escape.xlsx", "foo/bar.xlsx", ".hidden.xlsx", "notes.txt", "C:abs.xlsx"],
)
def test_excel_rejects_unsafe_names(tmp_path, filename):
    service, rental = _rent_controlling(tmp_path)
    with pytest.raises(RentalValidationError):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="excel",
            idempotency_key="excel-unsafe",
            filename=filename,
            file_bytes=b"PK\x03\x04not-a-real-xlsx",
        )


def test_excel_rejects_non_zip_payload(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    with pytest.raises(RentalValidationError):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="excel",
            idempotency_key="excel-garbage",
            filename="salden.xlsx",
            file_bytes=b"not-an-xlsx",
        )


def test_apply_excel_does_not_rewrite_formulas(tmp_path):
    instance = tmp_path / "tenant" / "controlling"
    for directory in ("project/pilot", "inbox", "artifacts", "imports", "state"):
        (instance / directory).mkdir(parents=True)
    source = (
        Path(__file__).resolve().parents[1]
        / "presets"
        / "kmu-controlling"
        / "pilot"
        / "demo"
        / "Saldenliste_Muster_Juni2026.xlsx"
    )
    raw = source.read_bytes()
    apply_starter(instance)
    apply_excel(instance, "kunde.xlsx", raw)
    stored = instance / "inbox" / "actuals" / "kunde.xlsx"
    assert stored.read_bytes() == raw
    with pytest.raises(OnboardingValidationError):
        apply_excel(instance, "../x.xlsx", raw)


def test_onboard_rejects_invalid_mode(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    with pytest.raises(RentalValidationError, match="Onboarding-Modus"):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="magic",
            idempotency_key="mode-001",
        )


def test_excel_rejects_empty_and_oversized(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    with pytest.raises(RentalValidationError):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="excel",
            idempotency_key="excel-empty",
            filename="salden.xlsx",
            file_bytes=b"",
        )
    with pytest.raises(RentalValidationError):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="excel",
            idempotency_key="excel-huge",
            filename="salden.xlsx",
            file_bytes=b"a" * (301 * 1024),
        )


def test_describe_skips_hidden_and_lists_only_instance_areas(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    instance = tmp_path / "rentals" / "muster-kmu" / "controlling"
    (instance / "artifacts" / ".secret.md").write_text("nope", encoding="utf-8")
    (instance / "artifacts" / "sichtbar.md").write_text("ok", encoding="utf-8")
    (instance / "project" / "not-listed.md").write_text("skip", encoding="utf-8")
    snapshot = service.describe_instance("muster-kmu", rental["rental_id"])
    paths = {item["path"] for item in snapshot["artifacts"]}
    assert "artifacts/sichtbar.md" in paths
    assert "artifacts/.secret.md" not in paths
    assert all(not item["path"].startswith("project/") for item in snapshot["inputs"])


def test_starter_conflicts_on_modified_target(tmp_path):
    service, rental = _rent_controlling(tmp_path)
    instance = tmp_path / "rentals" / "muster-kmu" / "controlling"
    target = instance / "inbox" / "actuals"
    target.mkdir(parents=True, exist_ok=True)
    (target / "starter-konten.csv").write_text("anders", encoding="utf-8")
    with pytest.raises(RentalConflict):
        service.onboard(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            mode="starter",
            idempotency_key="starter-conflict",
        )

