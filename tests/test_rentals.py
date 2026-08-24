"""Durable rental ledger: rent, cancel, list, path safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.rentals import (
    RentalConflict,
    RentalNotFound,
    RentalNotOpenable,
    RentalService,
    RentalValidationError,
)


def _service(tmp_path: Path) -> RentalService:
    return RentalService(tmp_path / "rentals")


def test_list_catalog_matches_public_catalog(tmp_path):
    service = _service(tmp_path)
    catalog = service.list_catalog()
    assert [item["agent_id"] for item in catalog] == [
        "controlling",
        "reporting",
        "rechnungen",
        "vertraege",
    ]


def test_rent_controlling_provisions_preset_instance(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    assert rental["schema_version"] == 1
    assert rental["status"] == "active"
    assert rental["cancelable"] is True
    assert rental["monthly_price_eur"] == "400"
    assert rental["spent_eur"] == "0"
    assert rental["provisionable"] is True
    assert rental["provisioned"] is True
    assert rental["cancelled_at"] is None
    assert rental["rented_at"].endswith("Z")
    assert rental["rental_id"].startswith("rnt_")
    instance = tmp_path / "rentals" / "muster-kmu" / "controlling"
    assert instance.is_dir()
    assert (instance / "project" / "knowledge" / "kpi-rules.md").is_file()
    assert rental["instance_path"] == "muster-kmu/controlling"


def test_rent_reporting_provisions_generic_pack(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-001",
    )
    assert rental["provisioned"] is True
    instance = tmp_path / "rentals" / "muster-kmu" / "reporting"
    assert (instance / "project" / "SOUL.md").is_file()
    assert (instance / "project" / "workflows" / "main.md").is_file()
    assert not (instance / "project" / "knowledge" / "kpi-rules.md").exists()


def test_rent_non_provisionable_is_ledger_only(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="rechnungen",
        display_name="Muster KMU",
        idempotency_key="rent-invoices-001",
    )
    assert rental["status"] == "active"
    assert rental["provisionable"] is False
    assert rental["provisioned"] is False
    assert rental["instance_path"] is None
    assert rental["monthly_price_eur"] == "600"
    assert not (tmp_path / "rentals" / "muster-kmu" / "rechnungen").exists()


def test_rent_is_idempotent_for_same_key_and_payload(tmp_path):
    service = _service(tmp_path)
    first = service.rent(
        tenant_id="muster-kmu",
        agent_id="vertraege",
        display_name="Muster KMU",
        idempotency_key="rent-contracts-001",
    )
    second = service.rent(
        tenant_id="muster-kmu",
        agent_id="vertraege",
        display_name="Muster KMU",
        idempotency_key="rent-contracts-001",
    )
    assert first["rental_id"] == second["rental_id"]
    assert first["status"] == "active"


def test_rent_conflicts_on_active_rental_with_different_key(tmp_path):
    service = _service(tmp_path)
    service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    with pytest.raises(RentalConflict):
        service.rent(
            tenant_id="muster-kmu",
            agent_id="controlling",
            display_name="Muster KMU",
            idempotency_key="rent-controlling-002",
        )


def test_unknown_agent_fails_closed(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(RentalValidationError, match="Unbekannter Agent"):
        service.rent(
            tenant_id="muster-kmu",
            agent_id="payroll",
            display_name="Muster KMU",
            idempotency_key="rent-unknown-001",
        )


@pytest.mark.parametrize(
    "tenant_id,agent_id",
    [
        ("../escape", "controlling"),
        ("muster/kmu", "controlling"),
        ("C:windows", "controlling"),
        ("muster-kmu", "../controlling"),
        ("muster-kmu", "controlling/../x"),
        ("", "controlling"),
    ],
)
def test_rent_rejects_unsafe_ids(tmp_path, tenant_id, agent_id):
    service = _service(tmp_path)
    with pytest.raises(RentalValidationError):
        service.rent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            display_name="Muster KMU",
            idempotency_key="rent-unsafe-001",
        )


def test_list_and_get_rental(tmp_path):
    service = _service(tmp_path)
    controlling = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    reporting = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-001",
    )
    listed = service.list_rentals("muster-kmu")
    ids = {item["rental_id"] for item in listed}
    assert controlling["rental_id"] in ids
    assert reporting["rental_id"] in ids
    fetched = service.get_rental("muster-kmu", controlling["rental_id"])
    assert fetched["agent_id"] == "controlling"
    by_id = service.get_rental_by_id(controlling["rental_id"])
    assert by_id["rental_id"] == controlling["rental_id"]


def test_cancel_is_idempotent_and_conflicts_on_other_key(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-001",
    )
    cancelled = service.cancel(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        idempotency_key="cancel-001",
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelled_at"]
    replay = service.cancel(
        tenant_id="muster-kmu",
        rental_id=rental["rental_id"],
        idempotency_key="cancel-001",
    )
    assert replay["rental_id"] == cancelled["rental_id"]
    assert replay["cancelled_at"] == cancelled["cancelled_at"]
    with pytest.raises(RentalConflict):
        service.cancel(
            tenant_id="muster-kmu",
            rental_id=rental["rental_id"],
            idempotency_key="cancel-002",
        )


def test_cancel_unknown_or_foreign_rental_is_not_found(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    with pytest.raises(RentalNotFound):
        service.cancel(
            tenant_id="muster-kmu",
            rental_id="rnt_" + "ab" * 16,
            idempotency_key="cancel-missing",
        )
    with pytest.raises(RentalNotFound):
        service.cancel(
            tenant_id="other-kmu",
            rental_id=rental["rental_id"],
            idempotency_key="cancel-foreign",
        )
    with pytest.raises(RentalNotFound):
        service.get_rental("muster-kmu", "not-a-rental")
    with pytest.raises(RentalValidationError):
        service.list_rentals("../escape")


def test_rent_after_cancel_creates_new_active_rental(tmp_path):
    service = _service(tmp_path)
    first = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    service.cancel(
        tenant_id="muster-kmu",
        rental_id=first["rental_id"],
        idempotency_key="cancel-001",
    )
    second = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-002",
    )
    assert second["status"] == "active"
    assert second["rental_id"] != first["rental_id"]
    listed = service.list_rentals("muster-kmu")
    assert {item["status"] for item in listed} == {"active", "cancelled"}


def test_rentals_do_not_touch_demo_order_root(tmp_path):
    service = _service(tmp_path)
    service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    assert not (tmp_path / "instances").exists()
    assert not list(tmp_path.rglob("local-demo-order.json"))


def test_open_rental_returns_active_provisioned_instance(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    opened = service.open_rental("muster-kmu", rental["rental_id"])
    assert opened["rental_id"] == rental["rental_id"]
    assert opened["provisioned"] is True
    assert opened["status"] == "active"
    assert opened["instance_path"] == "muster-kmu/controlling"


def test_open_rental_rejects_cancelled_and_ledger_only(tmp_path):
    service = _service(tmp_path)
    controlling = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
    service.cancel(
        tenant_id="muster-kmu",
        rental_id=controlling["rental_id"],
        idempotency_key="cancel-001",
    )
    with pytest.raises(RentalNotOpenable, match="gekuendigt"):
        service.open_rental("muster-kmu", controlling["rental_id"])

    invoices = service.rent(
        tenant_id="muster-kmu",
        agent_id="rechnungen",
        display_name="Muster KMU",
        idempotency_key="rent-invoices-001",
    )
    with pytest.raises(RentalNotOpenable, match="Pack folgt"):
        service.open_rental("muster-kmu", invoices["rental_id"])


def test_open_rental_rejects_wrong_tenant(tmp_path):
    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="reporting",
        display_name="Muster KMU",
        idempotency_key="rent-reporting-001",
    )
    with pytest.raises(RentalNotFound):
        service.open_rental("other-kmu", rental["rental_id"])


def test_open_rental_rejects_path_escape(tmp_path):
    import json

    service = _service(tmp_path)
    rental = service.rent(
        tenant_id="muster-kmu",
        agent_id="controlling",
        display_name="Muster KMU",
        idempotency_key="rent-controlling-001",
    )
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
        service.open_rental("muster-kmu", rental["rental_id"])

    state["instance_path"] = "muster-kmu/controlling/../../secret"
    record.write_text(
        json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RentalConflict, match="Instanzpfad"):
        service.open_rental("muster-kmu", rental["rental_id"])
