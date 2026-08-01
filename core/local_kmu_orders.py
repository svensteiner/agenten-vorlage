"""Durable, zero-cost local demo orders for the KMU controlling pilot.

This module is deliberately UI-neutral.  It provisions the packaged synthetic
demo, runs the deterministic report tool three times, and exposes only a
verified fixed report.  It does not call an LLM, create a payment, or enable an
external action.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import tempfile
import threading
import time
from typing import Any, Iterator
import unicodedata

from core.controlling import read_verified_latest_report_html
from core.controlling.artifacts import read_acceptance_status
from core.controlling.narrative import ControllingReportTool
from core.instance_factory import InstanceProvisionError, provision_instance


_IDENTITY = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ORDER_ID = re.compile(r"^ord_[0-9a-f]{32}$")
_VERIFY_OPERATION_ID = re.compile(r"^verify-[0-9a-f]{24}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_DISPLAY_NAME = 80
_MAX_JSON_BYTES = 64 * 1024
_LOCK_WAIT_SECONDS = 30.0
_DEMO_INVENTORY_BYTES = 724
_DEMO_INVENTORY_SHA256 = (
    "6c6f94b1df2c0f228f50242880aea8200b43ff5b40e118ba13fe4f17b95ddb63"
)
_STATE_FILE = "local-demo-order.json"
_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}


class OrderError(RuntimeError):
    """Base class for local order lifecycle errors."""


class OrderValidationError(OrderError):
    """A caller supplied an invalid local-demo request."""


class OrderConflict(OrderError):
    """An idempotency key or immutable order state conflicts."""


class OrderNotFound(OrderError):
    """No order exists in the requested namespace."""


def _thread_lock(key: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


@contextlib.contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
    """Lock one stable byte across threads and processes."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    key = str(lock_path.resolve())
    local_lock = _thread_lock(key)
    if not local_lock.acquire(timeout=_LOCK_WAIT_SECONDS):
        raise OrderConflict("Bestellung wird bereits verarbeitet.")
    try:
        if lock_path.is_symlink():
            raise OrderConflict("Bestellsperre darf kein Link sein.")
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT)
        with os.fdopen(descriptor, "r+b", buffering=0) as stream:
            if os.fstat(stream.fileno()).st_size < 1:
                stream.seek(0)
                stream.write(b"0")
                os.fsync(stream.fileno())
            stream.seek(0)
            deadline = time.monotonic() + _LOCK_WAIT_SECONDS
            if os.name == "nt":
                import msvcrt

                while time.monotonic() < deadline:
                    try:
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise OrderConflict("Bestellung wird bereits verarbeitet.")
                try:
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                while time.monotonic() < deadline:
                    try:
                        fcntl.flock(  # type: ignore[attr-defined]
                            stream.fileno(),
                            fcntl.LOCK_EX  # type: ignore[attr-defined]
                            | fcntl.LOCK_NB,  # type: ignore[attr-defined]
                        )
                        break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise OrderConflict("Bestellung wird bereits verarbeitet.")
                try:
                    yield
                finally:
                    fcntl.flock(  # type: ignore[attr-defined]
                        stream.fileno(), fcntl.LOCK_UN  # type: ignore[attr-defined]
                    )
    finally:
        local_lock.release()


def _replace_with_retry(source: Path, destination: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(source, destination)
            return
        except PermissionError as exc:
            if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32}:
                raise
            if attempt == 4:
                raise
            time.sleep(0.02 * (attempt + 1))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    raw = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if len(raw) > _MAX_JSON_BYTES:
        raise OrderValidationError("Bestellstatus ist unerwartet groß.")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _replace_with_retry(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise OrderNotFound("Bestellung nicht gefunden.")
        if path.stat().st_size > _MAX_JSON_BYTES:
            raise OrderConflict("Gespeicherte Bestellung ist ungültig.")
        value = json.loads(path.read_text(encoding="utf-8"))
    except OrderError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OrderConflict("Gespeicherte Bestellung ist ungültig.") from exc
    if not isinstance(value, dict):
        raise OrderConflict("Gespeicherte Bestellung ist ungültig.")
    return value


def _read_order_state(path: Path) -> dict[str, Any]:
    """Read and validate the complete durable schema before using nested fields."""
    state = _read_json(path)
    base_fields = {
        "schema_version",
        "order_id",
        "tenant_id",
        "agent_id",
        "display_name",
        "profile",
        "status",
        "status_history",
        "cost",
        "acceptance",
        "external_actions_enabled",
        "_create_idempotency_key",
        "_create_fingerprint",
    }
    verification_fields = {"verification", "verification_operation_id"}
    try:
        if type(state.get("schema_version")) is not int or state["schema_version"] != 1:
            raise ValueError
        if set(state) not in {frozenset(base_fields), frozenset(base_fields | verification_fields)}:
            raise ValueError
        _validate_order_id(state["order_id"])
        _validate_identity("tenant_id", state["tenant_id"])
        _validate_identity("agent_id", state["agent_id"])
        if _validate_display_name(state["display_name"]) != state["display_name"]:
            raise ValueError
        if state["profile"] != "deterministic_local_demo":
            raise ValueError

        status = state["status"]
        history = state["status_history"]
        allowed_statuses = {"ready", "verifying", "failed", "accepted"}
        allowed_history = {
            "received",
            "provisioned",
            "ready",
            "verifying",
            "failed",
            "accepted",
        }
        if (
            status not in allowed_statuses
            or not isinstance(history, list)
            or not 3 <= len(history) <= 32
            or history[:3] != ["received", "provisioned", "ready"]
            or history[-1] != status
            or any(item not in allowed_history for item in history)
        ):
            raise ValueError

        if state["cost"] != {"budget_eur": "0", "spent_eur": "0"}:
            raise ValueError
        acceptance = state["acceptance"]
        if not isinstance(acceptance, dict) or set(acceptance) != {
            "passed",
            "repeatable_run_count",
        }:
            raise ValueError
        passed = acceptance["passed"]
        repeatable_count = acceptance["repeatable_run_count"]
        if (
            type(passed) is not bool
            or type(repeatable_count) is not int
            or (passed, repeatable_count) not in {(False, 0), (True, 3)}
            or (status == "accepted") is not passed
            or state["external_actions_enabled"] != []
        ):
            raise ValueError

        _validate_key(state["_create_idempotency_key"])
        if not isinstance(state["_create_fingerprint"], str) or not _SHA256.fullmatch(
            state["_create_fingerprint"]
        ):
            raise ValueError

        verification = state.get("verification")
        if verification is None:
            if set(state) != base_fields or status != "ready":
                raise ValueError
        else:
            if (
                set(state) != base_fields | verification_fields
                or not isinstance(verification, dict)
                or set(verification) != {"idempotency_key", "operation_id"}
            ):
                raise ValueError
            _validate_key(verification["idempotency_key"])
            operation_id = verification["operation_id"]
            if (
                not isinstance(operation_id, str)
                or not _VERIFY_OPERATION_ID.fullmatch(operation_id)
                or state["verification_operation_id"] != operation_id
                or status == "ready"
            ):
                raise ValueError
    except (KeyError, OrderError, TypeError, ValueError) as exc:
        raise OrderConflict("Gespeicherte Bestellung ist ungültig.") from exc
    return state


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _digest_bytes(raw)


def _validate_identity(label: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise OrderValidationError(
            f"{label} muss eine kleingeschriebene technische ID sein."
        )
    return value


def _validate_key(value: Any) -> str:
    if not isinstance(value, str) or not _IDEMPOTENCY_KEY.fullmatch(value):
        raise OrderValidationError("Ungültiger Idempotency-Key.")
    return value


def _validate_order_id(value: Any) -> str:
    if not isinstance(value, str) or not _ORDER_ID.fullmatch(value):
        raise OrderNotFound("Bestellung nicht gefunden.")
    return value


def _validate_display_name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > _MAX_DISPLAY_NAME
        or any(
            unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            for character in value
        )
    ):
        raise OrderValidationError("Firmenname ist ungültig.")
    return value.strip()


def _validate_zero_budget(value: Any) -> None:
    if type(value) is not Decimal or value != Decimal("0"):
        raise OrderValidationError("Die lokale Demo erlaubt ausschließlich 0 EUR.")


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, FileNotFoundError):
        return False
    return bool(attributes & 0x400)


def _assert_plain_path(path: Path, root: Path, *, regular_file: bool) -> Path:
    root = root.resolve(strict=True)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise OrderConflict("Demo-Inventar verlässt seinen erlaubten Bereich.") from exc
    current = path
    while current != root:
        if current.is_symlink() or _is_reparse_point(current):
            raise OrderConflict("Links sind im Demo-Inventar nicht erlaubt.")
        current = current.parent
    if regular_file and not path.is_file():
        raise OrderConflict("Demo-Inventar enthält keine reguläre Datei.")
    return resolved


def _assert_no_redirected_component(path: Path, root: Path) -> None:
    root = root.resolve(strict=True)
    current = path
    while current != root:
        if current.is_symlink() or _is_reparse_point(current):
            raise OrderConflict("Links sind in Demo-Zielpfaden nicht erlaubt.")
        current = current.parent
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise OrderConflict("Demo-Zielpfad ist ungültig.") from exc


def _copy_atomic(raw: bytes, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".seed", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination_stream:
            destination_stream.write(raw)
            destination_stream.flush()
            os.fsync(destination_stream.fileno())
        _replace_with_retry(temporary, destination)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _public_order(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in state.items()
        if not key.startswith("_") and key != "verification"
    }


def _acceptance_is_current(instance: Path) -> bool:
    """Treat an unreadable or superseded report as not accepted, never as current."""
    try:
        acceptance = read_acceptance_status(instance)
    except (OSError, ValueError):
        return False
    return (
        acceptance.get("valid") is True
        and acceptance.get("passed") is True
        and acceptance.get("repeatable_run_count") == 3
    )


def _reset_stale_accepted_order(state: dict[str, Any]) -> None:
    """Require a fresh three-run verification after an accepted view goes stale."""
    state.pop("verification", None)
    state.pop("verification_operation_id", None)
    state["acceptance"] = {"passed": False, "repeatable_run_count": 0}
    state["status"] = "ready"
    state["status_history"].append("ready")


class LocalKmuOrderService:
    """Persistent local order-to-report service for the synthetic demo."""

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._service_root = self.output_root / ".local-kmu-orders"
        if self._service_root.is_symlink() or _is_reparse_point(
            self._service_root
        ):
            raise OrderConflict("Bestellspeicher darf nicht umgeleitet werden.")
        self._service_root.mkdir(exist_ok=True)
        _assert_no_redirected_component(self._service_root, self.output_root)

    def _instance(self, tenant_id: str, agent_id: str) -> Path:
        instance = self.output_root / tenant_id / agent_id
        _assert_no_redirected_component(instance, self.output_root)
        return instance

    def _state_path(self, tenant_id: str, agent_id: str) -> Path:
        instance = self._instance(tenant_id, agent_id)
        state = instance / "state"
        if instance.exists():
            if (
                not instance.is_dir()
                or not state.is_dir()
                or state.is_symlink()
                or _is_reparse_point(state)
            ):
                raise OrderConflict("Instanzstatus ist nicht sicher beschreibbar.")
            _assert_no_redirected_component(state, instance)
        return state / _STATE_FILE

    def _service_child(self, directory: str, filename: str) -> Path:
        parent = self._service_root / directory
        if parent.is_symlink() or _is_reparse_point(parent):
            raise OrderConflict("Bestellspeicher darf nicht umgeleitet werden.")
        parent.mkdir(exist_ok=True)
        _assert_no_redirected_component(parent, self._service_root)
        return parent / filename

    def _scope_lock(self, tenant_id: str, agent_id: str) -> Path:
        digest = _digest_bytes(f"{tenant_id}/{agent_id}".encode("utf-8"))
        return self._service_child("locks", f"{digest}.lock")

    def _index_path(self, order_id: str) -> Path:
        digest = _digest_bytes(order_id.encode("ascii"))
        return self._service_child("index", f"{digest}.json")

    def _ensure_order_index(self, state: dict[str, Any]) -> None:
        try:
            order_id = _validate_order_id(state["order_id"])
            tenant_id = _validate_identity("tenant_id", state["tenant_id"])
            agent_id = _validate_identity("agent_id", state["agent_id"])
        except (KeyError, OrderError) as exc:
            raise OrderConflict("Gespeicherte Bestellung ist ungültig.") from exc
        expected = {
            "schema_version": 1,
            "order_id": order_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
        }
        index_path = self._index_path(order_id)
        if index_path.is_symlink() or _is_reparse_point(index_path):
            raise OrderConflict("Bestellindex darf kein Link sein.")
        if index_path.exists():
            if _read_json(index_path) != expected:
                raise OrderConflict("Bestellindex widerspricht der Bestellung.")
            return
        _atomic_json(index_path, expected)

    def _seed_demo(self, instance: Path) -> None:
        _assert_no_redirected_component(instance, self.output_root)
        for directory in ("project", "inbox", "state", "artifacts"):
            area = instance / directory
            if (
                not area.is_dir()
                or area.is_symlink()
                or _is_reparse_point(area)
            ):
                raise OrderConflict("Agenten-Instanz enthält unsichere Speicherpfade.")
            _assert_no_redirected_component(area, instance)
        demo_root = instance / "project" / "pilot" / "demo"
        inventory_path = demo_root / "inventory.json"
        _assert_plain_path(inventory_path, instance, regular_file=True)
        inventory_raw = inventory_path.read_bytes()
        if (
            len(inventory_raw) != _DEMO_INVENTORY_BYTES
            or _digest_bytes(inventory_raw) != _DEMO_INVENTORY_SHA256
        ):
            raise OrderConflict("Demo-Inventar stimmt nicht mit dem Paket überein.")
        try:
            inventory = json.loads(inventory_raw.decode("utf-8"))
            entries = inventory["files"]
        except (UnicodeDecodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise OrderConflict("Demo-Inventar ist ungültig.") from exc
        if (
            inventory.get("schema_version") != 1
            or inventory.get("profile") != "deterministic_local_demo"
            or not isinstance(entries, list)
        ):
            raise OrderConflict("Demo-Inventar ist ungültig.")

        for entry in entries:
            if not isinstance(entry, dict):
                raise OrderConflict("Demo-Inventar ist ungültig.")
            source_name = entry.get("source")
            if (
                not isinstance(source_name, str)
                or PurePosixPath(source_name).parts != (source_name,)
                or "\\" in source_name
                or ":" in source_name
            ):
                raise OrderConflict("Demo-Quelldatei ist ungültig.")
            source = demo_root / source_name
            _assert_plain_path(source, demo_root, regular_file=True)
            raw = source.read_bytes()
            if (
                len(raw) != entry.get("bytes")
                or _digest_bytes(raw) != entry.get("sha256")
            ):
                raise OrderConflict("Demo-Quelldatei stimmt nicht mit Inventar überein.")

            destination_text = entry.get("destination")
            if destination_text is None:
                continue
            if not isinstance(destination_text, str):
                raise OrderConflict("Demo-Zielpfad ist ungültig.")
            relative = PurePosixPath(destination_text)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in destination_text
                or ":" in destination_text
                or relative.parts[0] not in {"inbox", "project"}
            ):
                raise OrderConflict("Demo-Zielpfad ist ungültig.")
            destination = instance.joinpath(*relative.parts)
            _assert_no_redirected_component(destination, instance)
            if destination.exists():
                if (
                    destination.is_symlink()
                    or not destination.is_file()
                    or _digest_bytes(destination.read_bytes()) != entry["sha256"]
                ):
                    raise OrderConflict("Vorhandene Demo-Datei weicht vom Inventar ab.")
            else:
                _copy_atomic(raw, destination)
            copied = destination.read_bytes()
            if len(copied) != entry["bytes"] or _digest_bytes(copied) != entry["sha256"]:
                raise OrderConflict("Demo-Datei konnte nicht sicher veröffentlicht werden.")

    def create_order(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        idempotency_key: str,
        display_name: str,
        budget_eur: Decimal,
    ) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        agent_id = _validate_identity("agent_id", agent_id)
        idempotency_key = _validate_key(idempotency_key)
        display_name = _validate_display_name(display_name)
        _validate_zero_budget(budget_eur)
        request_fingerprint = _fingerprint(
            {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "display_name": display_name,
                "budget_eur": "0",
                "profile": "deterministic_local_demo",
            }
        )

        with _file_lock(self._scope_lock(tenant_id, agent_id)):
            state_path = self._state_path(tenant_id, agent_id)
            if state_path.exists():
                existing_state = _read_order_state(state_path)
                if (
                    existing_state.get("_create_idempotency_key") == idempotency_key
                    and existing_state.get("_create_fingerprint")
                    == request_fingerprint
                ):
                    self._seed_demo(self._instance(tenant_id, agent_id))
                    self._ensure_order_index(existing_state)
                    return _public_order(existing_state)
                raise OrderConflict("Für diese Agenten-ID besteht bereits eine Bestellung.")

            try:
                instance = provision_instance(
                    self.output_root, tenant_id, agent_id, "kmu-controlling"
                )
            except (InstanceProvisionError, OSError, ValueError) as exc:
                raise OrderConflict("Agenten-Instanz konnte nicht angelegt werden.") from exc
            self._seed_demo(instance)

            order_id = f"ord_{secrets.token_hex(16)}"
            state: dict[str, Any] = {
                "schema_version": 1,
                "order_id": order_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "display_name": display_name,
                "profile": "deterministic_local_demo",
                "status": "ready",
                "status_history": ["received", "provisioned", "ready"],
                "cost": {"budget_eur": "0", "spent_eur": "0"},
                "acceptance": {"passed": False, "repeatable_run_count": 0},
                "external_actions_enabled": [],
                "_create_idempotency_key": idempotency_key,
                "_create_fingerprint": request_fingerprint,
            }
            _atomic_json(state_path, state)
            self._ensure_order_index(state)
            return _public_order(state)

    def get_order(
        self, *, tenant_id: str, agent_id: str, order_id: str
    ) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        agent_id = _validate_identity("agent_id", agent_id)
        order_id = _validate_order_id(order_id)
        with _file_lock(self._scope_lock(tenant_id, agent_id)):
            state = _read_order_state(self._state_path(tenant_id, agent_id))
            if (
                state.get("tenant_id") != tenant_id
                or state.get("agent_id") != agent_id
                or state.get("order_id") != order_id
            ):
                raise OrderNotFound("Bestellung nicht gefunden.")
            if state.get("status") == "accepted" and not _acceptance_is_current(
                self._instance(tenant_id, agent_id)
            ):
                _reset_stale_accepted_order(state)
                _atomic_json(self._state_path(tenant_id, agent_id), state)
            return _public_order(state)

    def _scope_for_order(self, order_id: str) -> tuple[str, str]:
        order_id = _validate_order_id(order_id)
        index = _read_json(self._index_path(order_id))
        if index.get("order_id") != order_id:
            raise OrderNotFound("Bestellung nicht gefunden.")
        try:
            tenant_id = _validate_identity("tenant_id", index["tenant_id"])
            agent_id = _validate_identity("agent_id", index["agent_id"])
        except (KeyError, OrderValidationError) as exc:
            raise OrderNotFound("Bestellung nicht gefunden.") from exc
        return tenant_id, agent_id

    def get_order_by_id(self, order_id: str) -> dict[str, Any]:
        tenant_id, agent_id = self._scope_for_order(order_id)
        return self.get_order(
            tenant_id=tenant_id, agent_id=agent_id, order_id=order_id
        )

    def verify_order(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        order_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        agent_id = _validate_identity("agent_id", agent_id)
        order_id = _validate_order_id(order_id)
        idempotency_key = _validate_key(idempotency_key)

        with _file_lock(self._scope_lock(tenant_id, agent_id)):
            state_path = self._state_path(tenant_id, agent_id)
            state = _read_order_state(state_path)
            if (
                state.get("tenant_id") != tenant_id
                or state.get("agent_id") != agent_id
                or state.get("order_id") != order_id
            ):
                raise OrderNotFound("Bestellung nicht gefunden.")
            self._seed_demo(self._instance(tenant_id, agent_id))
            if state.get("status") == "accepted" and not _acceptance_is_current(
                self._instance(tenant_id, agent_id)
            ):
                _reset_stale_accepted_order(state)
                _atomic_json(state_path, state)

            verification = state.get("verification")
            if verification is not None:
                if (
                    not isinstance(verification, dict)
                    or verification.get("idempotency_key") != idempotency_key
                ):
                    raise OrderConflict("Die Prüfung wurde bereits anders gestartet.")
                if state.get("status") == "accepted":
                    return _public_order(state)
                operation_id = verification.get("operation_id")
                if not isinstance(operation_id, str):
                    raise OrderConflict("Gespeicherte Prüfung ist ungültig.")
            else:
                operation_id = f"verify-{secrets.token_hex(12)}"
                state["verification"] = {
                    "idempotency_key": idempotency_key,
                    "operation_id": operation_id,
                }
                state["verification_operation_id"] = operation_id
                state["status"] = "verifying"
                state["status_history"].append("verifying")
                _atomic_json(state_path, state)

            tool = ControllingReportTool(self._instance(tenant_id, agent_id))
            for slot in range(1, 4):
                result = tool.safe_run(
                    json.dumps(
                        {
                            "source": "auto",
                            "operation_id": f"{operation_id}:{slot}",
                        },
                        separators=(",", ":"),
                    )
                )
                if result.startswith("FEHLER"):
                    state["status"] = "failed"
                    state["status_history"].append("failed")
                    _atomic_json(state_path, state)
                    raise OrderConflict(result)

            acceptance = read_acceptance_status(
                self._instance(tenant_id, agent_id)
            )
            if (
                not acceptance.get("valid")
                or not acceptance.get("passed")
                or acceptance.get("repeatable_run_count") != 3
            ):
                state["status"] = "failed"
                state["status_history"].append("failed")
                _atomic_json(state_path, state)
                raise OrderConflict("Die drei Kontrollläufe wurden nicht bestätigt.")

            state["acceptance"] = {
                "passed": True,
                "repeatable_run_count": 3,
            }
            state["status"] = "accepted"
            state["status_history"].append("accepted")
            _atomic_json(state_path, state)
            return _public_order(state)

    def verify_order_by_id(
        self, *, order_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        tenant_id, agent_id = self._scope_for_order(order_id)
        return self.verify_order(
            tenant_id=tenant_id,
            agent_id=agent_id,
            order_id=order_id,
            idempotency_key=idempotency_key,
        )

    def read_report_html(
        self, *, tenant_id: str, agent_id: str, order_id: str
    ) -> bytes:
        order = self.get_order(
            tenant_id=tenant_id, agent_id=agent_id, order_id=order_id
        )
        if order.get("status") != "accepted" or not order["acceptance"]["passed"]:
            raise OrderConflict("Bericht ist noch nicht freigegeben.")
        try:
            return read_verified_latest_report_html(
                self._instance(tenant_id, agent_id), require_passed=True
            )
        except (OSError, ValueError) as exc:
            raise OrderConflict("Der freigegebene Bericht ist ungültig.") from exc

    def read_report_html_by_id(self, order_id: str) -> bytes:
        tenant_id, agent_id = self._scope_for_order(order_id)
        return self.read_report_html(
            tenant_id=tenant_id, agent_id=agent_id, order_id=order_id
        )
