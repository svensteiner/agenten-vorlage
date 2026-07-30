"""Tests for the zero-cost local order-to-report lifecycle."""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import multiprocessing
from pathlib import Path
import socket

import pytest

from core import local_kmu_orders as orders_module
from core.local_kmu_orders import (
    LocalKmuOrderService,
    OrderConflict,
    OrderNotFound,
    OrderValidationError,
)
from core.instance_factory import provision_instance


def _service(tmp_path: Path) -> LocalKmuOrderService:
    return LocalKmuOrderService(tmp_path / "instances")


def _create_order_in_child(output_root: str, queue) -> None:
    try:
        order = LocalKmuOrderService(Path(output_root)).create_order(
            tenant_id="muster-kmu",
            agent_id="controlling",
            idempotency_key="checkout-001",
            display_name="Muster KMU",
            budget_eur=Decimal("0"),
        )
        queue.put(("ok", order["order_id"]))
    except Exception as exc:  # pragma: no cover - asserted by parent process
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def test_create_order_provisions_pinned_synthetic_demo_with_zero_cost(tmp_path):
    service = _service(tmp_path)

    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )

    assert order["schema_version"] == 1
    assert order["status"] == "ready"
    assert order["tenant_id"] == "muster-kmu"
    assert order["agent_id"] == "controlling"
    assert order["profile"] == "deterministic_local_demo"
    assert order["cost"] == {"budget_eur": "0", "spent_eur": "0"}
    assert order["acceptance"] == {"passed": False, "repeatable_run_count": 0}
    assert order["status_history"] == ["received", "provisioned", "ready"]
    assert order["external_actions_enabled"] == []

    instance = tmp_path / "instances" / "muster-kmu" / "controlling"
    actuals = instance / "inbox" / "actuals" / "Saldenliste_Muster_Juni2026.xlsx"
    mapping = instance / "project" / "pilot" / "account-mapping.json"
    assert actuals.is_file()
    assert mapping.is_file()
    assert hashlib.sha256(actuals.read_bytes()).hexdigest() == (
        "094946de002992e59c7217dcfe47f7de805c4da880f2e332346c8dfafd2a9ccc"
    )
    assert hashlib.sha256(mapping.read_bytes()).hexdigest() == (
        "8888449eb443cc723d08be2ba20db1e6bf11485ea5ccb33450d8d39cee1145a5"
    )


def test_concurrent_process_create_replays_one_complete_order(tmp_path):
    output_root = tmp_path / "instances"
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    children = [
        context.Process(
            target=_create_order_in_child, args=(str(output_root), queue)
        )
        for _ in range(2)
    ]
    for child in children:
        child.start()
    results = [queue.get(timeout=30) for _ in children]
    for child in children:
        child.join(timeout=30)
        assert child.exitcode == 0

    assert {status for status, _ in results} == {"ok"}
    assert len({order_id for _, order_id in results}) == 1


def test_create_order_replays_same_key_and_conflicts_on_changed_payload(tmp_path):
    service = _service(tmp_path)
    request = {
        "tenant_id": "muster-kmu",
        "agent_id": "controlling",
        "idempotency_key": "checkout-001",
        "display_name": "Muster KMU",
        "budget_eur": Decimal("0"),
    }

    first = service.create_order(**request)
    second = service.create_order(**request)

    assert second == first
    with pytest.raises(OrderConflict):
        service.create_order(**{**request, "display_name": "Andere Firma"})


def test_create_order_retry_repairs_index_after_interrupted_publication(
    tmp_path, monkeypatch
):
    service = _service(tmp_path)
    original_atomic_json = orders_module._atomic_json
    interrupted = False

    def interrupt_index_once(path, payload):
        nonlocal interrupted
        if path.parent.name == "index" and not interrupted:
            interrupted = True
            raise OSError("simulated index publication crash")
        return original_atomic_json(path, payload)

    monkeypatch.setattr(orders_module, "_atomic_json", interrupt_index_once)
    request = {
        "tenant_id": "muster-kmu",
        "agent_id": "controlling",
        "idempotency_key": "checkout-001",
        "display_name": "Muster KMU",
        "budget_eur": Decimal("0"),
    }

    with pytest.raises(OSError):
        service.create_order(**request)

    repaired = service.create_order(**request)

    assert service.get_order_by_id(repaired["order_id"]) == repaired


def test_create_order_recovers_a_zero_byte_stable_lock(tmp_path):
    service = _service(tmp_path)
    lock = service._scope_lock("muster-kmu", "controlling")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"")

    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )

    assert order["status"] == "ready"
    assert lock.read_bytes() == b"0"


def test_service_rejects_redirected_internal_storage(tmp_path):
    output_root = tmp_path / "instances"
    output_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    service_root = output_root / ".local-kmu-orders"
    try:
        service_root.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable for this test account")

    with pytest.raises(OrderConflict, match="umgeleitet"):
        LocalKmuOrderService(output_root)

    assert list(outside.iterdir()) == []


def test_create_rejects_redirected_instance_state(tmp_path):
    output_root = tmp_path / "instances"
    instance = provision_instance(
        output_root, "muster-kmu", "controlling", "kmu-controlling"
    )
    state = instance / "state"
    state.rmdir()
    outside = tmp_path / "outside-state"
    outside.mkdir()
    try:
        state.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable for this test account")
    service = LocalKmuOrderService(output_root)

    with pytest.raises(OrderConflict, match="Instanzstatus"):
        service.create_order(
            tenant_id="muster-kmu",
            agent_id="controlling",
            idempotency_key="checkout-001",
            display_name="Muster KMU",
            budget_eur=Decimal("0"),
        )

    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "relative",
    (
        "inbox/actuals/Saldenliste_Muster_Juni2026.xlsx",
        "project/pilot/account-mapping.json",
        "project/pilot/demo/inventory.json",
    ),
)
def test_verification_rejects_tampered_pinned_demo_inputs(tmp_path, relative):
    service = _service(tmp_path)
    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )
    target = tmp_path / "instances" / "muster-kmu" / "controlling" / relative
    target.write_bytes(target.read_bytes() + b"tampered")

    with pytest.raises(OrderConflict, match="Inventar"):
        service.verify_order(
            tenant_id="muster-kmu",
            agent_id="controlling",
            order_id=order["order_id"],
            idempotency_key="verify-001",
        )

    assert not (
        tmp_path
        / "instances"
        / "muster-kmu"
        / "controlling"
        / "state"
        / "acceptance-ledger.jsonl"
    ).exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", ""),
        ("tenant_id", "../fremd"),
        ("tenant_id", "Muster-KMU"),
        ("tenant_id", "münchen"),
        ("agent_id", r"..\fremd"),
        ("agent_id", "controlling/other"),
        ("idempotency_key", ""),
        ("idempotency_key", "x" * 129),
    ],
)
def test_create_order_rejects_noncanonical_identity_and_keys(
    tmp_path, field, value
):
    service = _service(tmp_path)
    request = {
        "tenant_id": "muster-kmu",
        "agent_id": "controlling",
        "idempotency_key": "checkout-001",
        "display_name": "Muster KMU",
        "budget_eur": Decimal("0"),
    }
    request[field] = value

    with pytest.raises(OrderValidationError):
        service.create_order(**request)


@pytest.mark.parametrize(
    "budget",
    [Decimal("0.01"), Decimal("-1"), True, "0", float("nan")],
)
def test_create_order_rejects_every_nonzero_or_untyped_budget(tmp_path, budget):
    service = _service(tmp_path)

    with pytest.raises(OrderValidationError):
        service.create_order(
            tenant_id="muster-kmu",
            agent_id="controlling",
            idempotency_key="checkout-001",
            display_name="Muster KMU",
            budget_eur=budget,
        )


def test_verification_runs_three_distinct_operations_without_model_or_egress(
    tmp_path, monkeypatch
):
    service = _service(tmp_path)
    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("model or external network access is forbidden")

    import brain
    from core.orchestrator import AgentOrchestrator

    monkeypatch.setattr(brain, "_call_llm", forbidden)
    monkeypatch.setattr(brain, "complete", forbidden)
    monkeypatch.setattr(brain, "evaluate", forbidden)
    monkeypatch.setattr(brain, "_get_client", forbidden)
    monkeypatch.setattr(brain, "_azure_client", forbidden)
    monkeypatch.setattr(brain, "_onprem_client", forbidden)
    monkeypatch.setattr(AgentOrchestrator, "run", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)

    verified = service.verify_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        order_id=order["order_id"],
        idempotency_key="verify-001",
    )

    assert verified["status"] == "accepted"
    assert verified["acceptance"] == {
        "passed": True,
        "repeatable_run_count": 3,
    }
    assert verified["cost"] == {"budget_eur": "0", "spent_eur": "0"}
    assert verified["external_actions_enabled"] == []
    assert verified["status_history"][-2:] == ["verifying", "accepted"]

    evidence = json.loads(
        (
            tmp_path
            / "instances"
            / "muster-kmu"
            / "controlling"
            / "artifacts"
            / "acceptance-evidence.json"
        ).read_text(encoding="utf-8")
    )
    assert len(evidence["runs"]) == 3
    assert [run["operation_id"] for run in evidence["runs"]] == [
        f"{verified['verification_operation_id']}:1",
        f"{verified['verification_operation_id']}:2",
        f"{verified['verification_operation_id']}:3",
    ]
    assert all(run["external_action_log"] == [] for run in evidence["runs"])


def test_verification_replay_does_not_add_acceptance_runs(tmp_path):
    service = _service(tmp_path)
    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )
    request = {
        "tenant_id": "muster-kmu",
        "agent_id": "controlling",
        "order_id": order["order_id"],
        "idempotency_key": "verify-001",
    }

    first = service.verify_order(**request)
    second = service.verify_order(**request)

    assert second == first
    evidence_path = (
        tmp_path
        / "instances"
        / "muster-kmu"
        / "controlling"
        / "artifacts"
        / "acceptance-evidence.json"
    )
    assert len(json.loads(evidence_path.read_text(encoding="utf-8"))["runs"]) == 3
    with pytest.raises(OrderConflict):
        service.verify_order(**{**request, "idempotency_key": "verify-002"})


def test_order_access_is_tenant_and_agent_scoped(tmp_path):
    service = _service(tmp_path)
    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )

    with pytest.raises(OrderNotFound):
        service.get_order(
            tenant_id="anderes-kmu",
            agent_id="controlling",
            order_id=order["order_id"],
        )
    with pytest.raises(OrderNotFound):
        service.verify_order(
            tenant_id="anderes-kmu",
            agent_id="controlling",
            order_id=order["order_id"],
            idempotency_key="verify-001",
        )


def test_report_bytes_are_unavailable_before_acceptance_and_fixed_afterwards(
    tmp_path,
):
    service = _service(tmp_path)
    order = service.create_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        idempotency_key="checkout-001",
        display_name="Muster KMU",
        budget_eur=Decimal("0"),
    )

    with pytest.raises(OrderConflict):
        service.read_report_html(
            tenant_id="muster-kmu",
            agent_id="controlling",
            order_id=order["order_id"],
        )

    service.verify_order(
        tenant_id="muster-kmu",
        agent_id="controlling",
        order_id=order["order_id"],
        idempotency_key="verify-001",
    )
    report = service.read_report_html(
        tenant_id="muster-kmu",
        agent_id="controlling",
        order_id=order["order_id"],
    )

    assert report.startswith(b"<!doctype html>")
    assert b"KMU-Controlling" in report
    assert len(report) > 3_000
