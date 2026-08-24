"""Durable local rental ledger for rentable digital employees.

Separate from the zero-cost controlling demo orders: list prices are stored,
but no payment is captured. Provisionable catalog agents get an instance under
the rental output root; non-provisionable agents remain ledger-only.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
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

from core.agent_catalog import get_agent, list_agents
from core.instance_factory import InstanceProvisionError, provision_instance
from core.rental_onboarding import (
    OnboardingConflict,
    OnboardingValidationError,
    apply_excel,
    apply_reporting_starter,
    apply_starter,
    snapshot_instance,
)


_IDENTITY = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RENTAL_ID = re.compile(r"^rnt_[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_DISPLAY_NAME = 80
_MAX_JSON_BYTES = 64 * 1024
_LOCK_WAIT_SECONDS = 30.0
_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}


class RentalError(RuntimeError):
    """Base class for rental lifecycle errors."""


class RentalValidationError(RentalError):
    """A caller supplied an invalid rental request."""


class RentalConflict(RentalError):
    """An idempotency key or immutable rental state conflicts."""


class RentalNotFound(RentalError):
    """No rental exists in the requested namespace."""


class RentalNotOpenable(RentalError):
    """The rental exists but must not be opened."""


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
        raise RentalConflict("Miete wird bereits verarbeitet.")
    try:
        if lock_path.is_symlink():
            raise RentalConflict("Mietsperre darf kein Link sein.")
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
                    raise RentalConflict("Miete wird bereits verarbeitet.")
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
                    raise RentalConflict("Miete wird bereits verarbeitet.")
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
        raise RentalValidationError("Mietstatus ist unerwartet gross.")
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
            raise RentalNotFound("Miete nicht gefunden.")
        if path.stat().st_size > _MAX_JSON_BYTES:
            raise RentalConflict("Gespeicherte Miete ist ungueltig.")
        value = json.loads(path.read_text(encoding="utf-8"))
    except RentalError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RentalConflict("Gespeicherte Miete ist ungueltig.") from exc
    if not isinstance(value, dict):
        raise RentalConflict("Gespeicherte Miete ist ungueltig.")
    return value


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _digest_bytes(raw)


def _validate_identity(label: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise RentalValidationError(
            f"{label} muss eine kleingeschriebene technische ID sein."
        )
    return value


def _validate_key(value: Any) -> str:
    if not isinstance(value, str) or not _IDEMPOTENCY_KEY.fullmatch(value):
        raise RentalValidationError("Ungueltiger Idempotency-Key.")
    return value


def _validate_rental_id(value: Any) -> str:
    if not isinstance(value, str) or not _RENTAL_ID.fullmatch(value):
        raise RentalNotFound("Miete nicht gefunden.")
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
        raise RentalValidationError("Anzeigename ist ungueltig.")
    return value.strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, FileNotFoundError):
        return False
    return bool(attributes & 0x400)


def _assert_no_redirected_component(path: Path, root: Path) -> None:
    root = root.resolve(strict=True)
    current = path
    while current != root:
        if current.is_symlink() or _is_reparse_point(current):
            raise RentalConflict("Links sind in Mietpfaden nicht erlaubt.")
        current = current.parent
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise RentalConflict("Mietpfad ist ungueltig.") from exc


def _public_rental(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in state.items()
        if not str(key).startswith("_")
    }


def _read_rental_state(path: Path) -> dict[str, Any]:
    state = _read_json(path)
    required = {
        "schema_version",
        "rental_id",
        "tenant_id",
        "agent_id",
        "display_name",
        "status",
        "monthly_price_eur",
        "spent_eur",
        "cancelable",
        "rented_at",
        "cancelled_at",
        "provisionable",
        "provisioned",
        "instance_path",
        "_rent_idempotency_key",
        "_rent_fingerprint",
        "_cancel_idempotency_key",
    }
    try:
        if type(state.get("schema_version")) is not int or state["schema_version"] != 1:
            raise ValueError
        if set(state) != required:
            raise ValueError
        _validate_rental_id(state["rental_id"])
        _validate_identity("tenant_id", state["tenant_id"])
        _validate_identity("agent_id", state["agent_id"])
        if _validate_display_name(state["display_name"]) != state["display_name"]:
            raise ValueError
        if state["status"] not in {"active", "cancelled"}:
            raise ValueError
        if not isinstance(state["monthly_price_eur"], str):
            raise ValueError
        if state["spent_eur"] != "0":
            raise ValueError
        if state["cancelable"] is not True:
            raise ValueError
        if not isinstance(state["rented_at"], str) or not state["rented_at"]:
            raise ValueError
        cancelled_at = state["cancelled_at"]
        if state["status"] == "active":
            if cancelled_at is not None:
                raise ValueError
        elif not isinstance(cancelled_at, str) or not cancelled_at:
            raise ValueError
        if type(state["provisionable"]) is not bool:
            raise ValueError
        if type(state["provisioned"]) is not bool:
            raise ValueError
        instance_path = state["instance_path"]
        if instance_path is not None and not isinstance(instance_path, str):
            raise ValueError
        _validate_key(state["_rent_idempotency_key"])
        if not isinstance(state["_rent_fingerprint"], str) or not _SHA256.fullmatch(
            state["_rent_fingerprint"]
        ):
            raise ValueError
        cancel_key = state["_cancel_idempotency_key"]
        if cancel_key is not None:
            _validate_key(cancel_key)
        if state["status"] == "cancelled" and cancel_key is None:
            raise ValueError
        if state["status"] == "active" and cancel_key is not None:
            raise ValueError
    except (KeyError, RentalError, TypeError, ValueError) as exc:
        raise RentalConflict("Gespeicherte Miete ist ungueltig.") from exc
    return state



def _minimal_pack_writer(instance: Path, tenant_id: str, agent_id: str) -> None:
    """Write a generic valid instance envelope (no controlling preset)."""
    project_dir = instance / "project"
    (project_dir / "workflows").mkdir(parents=True, exist_ok=True)
    identity = {"tenant_id": tenant_id, "agent_id": agent_id}
    (project_dir / "config.json").write_text(
        json.dumps({"instance": identity}, indent=2) + "\n", encoding="utf-8"
    )
    (project_dir / "manifest.json").write_text(
        json.dumps({"instance": identity}, indent=2) + "\n", encoding="utf-8"
    )
    (project_dir / "connectors.yaml").write_text("connectors: []\n", encoding="utf-8")
    (project_dir / "steering-examples.json").write_text("[]\n", encoding="utf-8")
    (project_dir / "SOUL.md").write_text(
        f"# {agent_id}\nGemieteter digitaler Mitarbeiter fuer {tenant_id}.\n",
        encoding="utf-8",
    )
    (project_dir / "workflows" / "main.md").write_text(
        "# Haupt-Workflow\nMinimale gemietete Instanz.\n",
        encoding="utf-8",
    )
    for directory in ("inbox", "data", "imports", "state", "artifacts"):
        (instance / directory).mkdir(exist_ok=True)


class RentalService:
    """Persistent tenant-scoped rental ledger with optional provisioning."""

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._ledger_root = self.output_root / ".ledger"
        if self._ledger_root.is_symlink() or _is_reparse_point(self._ledger_root):
            raise RentalConflict("Mietspeicher darf nicht umgeleitet werden.")
        self._ledger_root.mkdir(exist_ok=True)
        _assert_no_redirected_component(self._ledger_root, self.output_root)

    def list_catalog(self) -> list[dict[str, Any]]:
        return list_agents()

    def _ledger_child(self, directory: str, filename: str) -> Path:
        parent = self._ledger_root / directory
        if parent.is_symlink() or _is_reparse_point(parent):
            raise RentalConflict("Mietspeicher darf nicht umgeleitet werden.")
        parent.mkdir(exist_ok=True)
        _assert_no_redirected_component(parent, self._ledger_root)
        return parent / filename

    def _scope_lock(self, tenant_id: str, agent_id: str) -> Path:
        digest = _digest_bytes(f"{tenant_id}/{agent_id}".encode("utf-8"))
        return self._ledger_child("locks", f"{digest}.lock")

    def _tenant_lock(self, tenant_id: str) -> Path:
        digest = _digest_bytes(tenant_id.encode("utf-8"))
        return self._ledger_child("tenant-locks", f"{digest}.lock")

    def _index_path(self, rental_id: str) -> Path:
        digest = _digest_bytes(rental_id.encode("ascii"))
        return self._ledger_child("index", f"{digest}.json")

    def _active_path(self, tenant_id: str, agent_id: str) -> Path:
        digest = _digest_bytes(f"{tenant_id}/{agent_id}".encode("utf-8"))
        return self._ledger_child("active", f"{digest}.json")

    def _record_dir(self, tenant_id: str) -> Path:
        parent = self._ledger_root / "rentals" / tenant_id
        if parent.is_symlink() or _is_reparse_point(parent):
            raise RentalConflict("Mietspeicher darf nicht umgeleitet werden.")
        parent.mkdir(parents=True, exist_ok=True)
        _assert_no_redirected_component(parent, self._ledger_root)
        return parent

    def _record_path(self, tenant_id: str, rental_id: str) -> Path:
        return self._record_dir(tenant_id) / f"{rental_id}.json"

    def _instance_root(self, tenant_id: str, agent_id: str) -> Path:
        instance = self.output_root / tenant_id / agent_id
        _assert_no_redirected_component(instance, self.output_root)
        return instance

    def _ensure_index(self, state: dict[str, Any]) -> None:
        rental_id = _validate_rental_id(state["rental_id"])
        tenant_id = _validate_identity("tenant_id", state["tenant_id"])
        agent_id = _validate_identity("agent_id", state["agent_id"])
        expected = {
            "schema_version": 1,
            "rental_id": rental_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
        }
        index_path = self._index_path(rental_id)
        if index_path.is_symlink() or _is_reparse_point(index_path):
            raise RentalConflict("Mietindex darf kein Link sein.")
        if index_path.exists():
            if _read_json(index_path) != expected:
                raise RentalConflict("Mietindex widerspricht der Miete.")
            return
        _atomic_json(index_path, expected)

    def rent(
        self,
        tenant_id: str,
        agent_id: str,
        display_name: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        agent_id = _validate_identity("agent_id", agent_id)
        display_name = _validate_display_name(display_name)
        idempotency_key = _validate_key(idempotency_key)

        catalog = get_agent(agent_id)
        if catalog is None:
            raise RentalValidationError("Unbekannter Agent.")

        request_fingerprint = _fingerprint(
            {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "display_name": display_name,
                "monthly_price_eur": catalog["monthly_price_eur"],
            }
        )

        with _file_lock(self._scope_lock(tenant_id, agent_id)):
            active_path = self._active_path(tenant_id, agent_id)
            if active_path.exists():
                pointer = _read_json(active_path)
                existing_id = pointer.get("rental_id")
                if not isinstance(existing_id, str):
                    raise RentalConflict("Aktive Miete ist ungueltig.")
                existing = _read_rental_state(self._record_path(tenant_id, existing_id))
                if existing["status"] != "active":
                    raise RentalConflict("Aktive Miete ist ungueltig.")
                if (
                    existing.get("_rent_idempotency_key") == idempotency_key
                    and existing.get("_rent_fingerprint") == request_fingerprint
                ):
                    self._ensure_index(existing)
                    return _public_rental(existing)
                raise RentalConflict(
                    "Fuer diesen Agenten besteht bereits eine aktive Miete."
                )

            provisioned = False
            instance_path: str | None = None
            if catalog["provisionable"]:
                preset = catalog["preset_id"]
                extra = {}
                if preset is None:
                    extra["_project_writer"] = _minimal_pack_writer
                try:
                    instance = provision_instance(
                        self.output_root,
                        tenant_id,
                        agent_id,
                        preset,
                        **extra,
                    )
                except (InstanceProvisionError, OSError, ValueError) as exc:
                    raise RentalConflict(
                        "Agenten-Instanz konnte nicht angelegt werden."
                    ) from exc
                provisioned = True
                try:
                    instance_path = str(
                        instance.resolve().relative_to(self.output_root)
                    ).replace("\\", "/")
                except ValueError as exc:
                    raise RentalConflict(
                        "Agenten-Instanz liegt ausserhalb des Mietbereichs."
                    ) from exc
                if agent_id == "reporting":
                    try:
                        apply_reporting_starter(instance)
                    except (OnboardingValidationError, OnboardingConflict) as exc:
                        raise RentalConflict(
                            "Reporting-Musterbericht konnte nicht angelegt werden."
                        ) from exc

            rental_id = f"rnt_{secrets.token_hex(16)}"
            state: dict[str, Any] = {
                "schema_version": 1,
                "rental_id": rental_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "display_name": display_name,
                "status": "active",
                "monthly_price_eur": catalog["monthly_price_eur"],
                "spent_eur": "0",
                "cancelable": True,
                "rented_at": _utc_now_iso(),
                "cancelled_at": None,
                "provisionable": catalog["provisionable"],
                "provisioned": provisioned,
                "instance_path": instance_path,
                "_rent_idempotency_key": idempotency_key,
                "_rent_fingerprint": request_fingerprint,
                "_cancel_idempotency_key": None,
            }
            _atomic_json(self._record_path(tenant_id, rental_id), state)
            _atomic_json(
                active_path,
                {
                    "schema_version": 1,
                    "rental_id": rental_id,
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                },
            )
            self._ensure_index(state)
            return _public_rental(state)

    def list_rentals(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        with _file_lock(self._tenant_lock(tenant_id)):
            record_dir = self._record_dir(tenant_id)
            rentals: list[dict[str, Any]] = []
            for path in sorted(record_dir.glob("rnt_*.json")):
                if path.is_symlink() or not path.is_file():
                    continue
                name = path.name
                if not _RENTAL_ID.fullmatch(name[:-5]):
                    continue
                try:
                    state = _read_rental_state(path)
                except RentalError:
                    continue
                if state["tenant_id"] != tenant_id:
                    continue
                rentals.append(_public_rental(state))
            rentals.sort(key=lambda item: item["rented_at"], reverse=True)
            return rentals

    def get_rental(self, tenant_id: str, rental_id: str) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        rental_id = _validate_rental_id(rental_id)
        with _file_lock(self._tenant_lock(tenant_id)):
            state = _read_rental_state(self._record_path(tenant_id, rental_id))
            if state["tenant_id"] != tenant_id or state["rental_id"] != rental_id:
                raise RentalNotFound("Miete nicht gefunden.")
            return _public_rental(state)

    def get_rental_by_id(self, rental_id: str) -> dict[str, Any]:
        rental_id = _validate_rental_id(rental_id)
        index = _read_json(self._index_path(rental_id))
        if index.get("rental_id") != rental_id:
            raise RentalNotFound("Miete nicht gefunden.")
        try:
            tenant_id = _validate_identity("tenant_id", index["tenant_id"])
        except (KeyError, RentalValidationError) as exc:
            raise RentalNotFound("Miete nicht gefunden.") from exc
        return self.get_rental(tenant_id, rental_id)

    def cancel(
        self,
        tenant_id: str,
        rental_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        tenant_id = _validate_identity("tenant_id", tenant_id)
        rental_id = _validate_rental_id(rental_id)
        idempotency_key = _validate_key(idempotency_key)

        index = _read_json(self._index_path(rental_id))
        if index.get("rental_id") != rental_id:
            raise RentalNotFound("Miete nicht gefunden.")
        try:
            indexed_tenant = _validate_identity("tenant_id", index["tenant_id"])
            agent_id = _validate_identity("agent_id", index["agent_id"])
        except (KeyError, RentalValidationError) as exc:
            raise RentalNotFound("Miete nicht gefunden.") from exc
        if indexed_tenant != tenant_id:
            raise RentalNotFound("Miete nicht gefunden.")

        with _file_lock(self._scope_lock(tenant_id, agent_id)):
            state_path = self._record_path(tenant_id, rental_id)
            state = _read_rental_state(state_path)
            if state["tenant_id"] != tenant_id or state["rental_id"] != rental_id:
                raise RentalNotFound("Miete nicht gefunden.")

            if state["status"] == "cancelled":
                if state.get("_cancel_idempotency_key") == idempotency_key:
                    return _public_rental(state)
                raise RentalConflict("Die Miete wurde bereits anders gekuendigt.")

            state["status"] = "cancelled"
            state["cancelled_at"] = _utc_now_iso()
            state["_cancel_idempotency_key"] = idempotency_key
            _atomic_json(state_path, state)

            active_path = self._active_path(tenant_id, agent_id)
            if active_path.exists():
                pointer = _read_json(active_path)
                if pointer.get("rental_id") == rental_id:
                    with contextlib.suppress(FileNotFoundError):
                        active_path.unlink()
            return _public_rental(state)

    def _assert_openable_instance(
        self, tenant_id: str, agent_id: str, instance_path: str
    ) -> Path:
        if "\\" in instance_path or ":" in instance_path:
            raise RentalConflict("Instanzpfad ist ungueltig.")
        relative = PurePosixPath(instance_path)
        if (
            relative.is_absolute()
            or len(relative.parts) != 2
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise RentalConflict("Instanzpfad ist ungueltig.")
        if relative.parts[0] != tenant_id or relative.parts[1] != agent_id:
            raise RentalConflict("Instanzpfad ist ungueltig.")
        candidate = self.output_root.joinpath(*relative.parts)
        if candidate.is_symlink() or _is_reparse_point(candidate):
            raise RentalConflict("Links sind in Mietpfaden nicht erlaubt.")
        _assert_no_redirected_component(candidate, self.output_root)
        try:
            candidate.resolve(strict=False).relative_to(
                self.output_root.resolve(strict=True)
            )
        except ValueError as exc:
            raise RentalConflict("Instanzpfad ist ungueltig.") from exc
        if not candidate.is_dir():
            raise RentalConflict("Instanz nicht gefunden.")
        return candidate

    def open_rental(self, tenant_id: str, rental_id: str) -> dict[str, Any]:
        """Return the public rental only if it may be opened.

        Fail closed: matching tenant, active, provisioned, instance path
        inside the rental root. Links and ``..`` segments are rejected.
        """
        tenant_id = _validate_identity("tenant_id", tenant_id)
        rental_id = _validate_rental_id(rental_id)
        with _file_lock(self._tenant_lock(tenant_id)):
            state = _read_rental_state(self._record_path(tenant_id, rental_id))
            if state["tenant_id"] != tenant_id or state["rental_id"] != rental_id:
                raise RentalNotFound("Miete nicht gefunden.")
            if state["status"] != "active":
                raise RentalNotOpenable("Miete ist gekuendigt.")
            if not state["provisionable"] or not state["provisioned"]:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            instance_path = state["instance_path"]
            if not isinstance(instance_path, str) or not instance_path:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            self._assert_openable_instance(
                tenant_id, state["agent_id"], instance_path
            )
            return _public_rental(state)

    def describe_instance(self, tenant_id: str, rental_id: str) -> dict[str, Any]:
        """Return identity, SOUL/preset, and listed instance files."""
        tenant_id = _validate_identity("tenant_id", tenant_id)
        rental_id = _validate_rental_id(rental_id)
        with _file_lock(self._tenant_lock(tenant_id)):
            state = _read_rental_state(self._record_path(tenant_id, rental_id))
            if state["tenant_id"] != tenant_id or state["rental_id"] != rental_id:
                raise RentalNotFound("Miete nicht gefunden.")
            if state["status"] != "active":
                raise RentalNotOpenable("Miete ist gekuendigt.")
            if not state["provisionable"] or not state["provisioned"]:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            instance_path = state["instance_path"]
            if not isinstance(instance_path, str) or not instance_path:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            instance = self._assert_openable_instance(
                tenant_id, state["agent_id"], instance_path
            )
            catalog = get_agent(state["agent_id"])
            return snapshot_instance(instance, _public_rental(state), catalog)

    def onboard(
        self,
        tenant_id: str,
        rental_id: str,
        *,
        mode: str,
        idempotency_key: str,
        filename: str | None = None,
        file_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """Seed starter files or copy an Excel workbook into the instance."""
        tenant_id = _validate_identity("tenant_id", tenant_id)
        rental_id = _validate_rental_id(rental_id)
        idempotency_key = _validate_key(idempotency_key)
        if mode not in {"starter", "excel"}:
            raise RentalValidationError("Onboarding-Modus ist ungueltig.")
        with _file_lock(self._tenant_lock(tenant_id)):
            state = _read_rental_state(self._record_path(tenant_id, rental_id))
            if state["tenant_id"] != tenant_id or state["rental_id"] != rental_id:
                raise RentalNotFound("Miete nicht gefunden.")
            if state["status"] != "active":
                raise RentalNotOpenable("Miete ist gekuendigt.")
            if not state["provisionable"] or not state["provisioned"]:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            if state["agent_id"] != "controlling":
                raise RentalValidationError(
                    "Onboarding gilt nur fuer den Controlling-Agenten."
                )
            instance_path = state["instance_path"]
            if not isinstance(instance_path, str) or not instance_path:
                raise RentalNotOpenable(
                    "Pack folgt - dieser Agent ist noch nicht oeffenbar."
                )
            instance = self._assert_openable_instance(
                tenant_id, state["agent_id"], instance_path
            )
            try:
                if mode == "starter":
                    apply_starter(instance)
                else:
                    apply_excel(instance, filename or "", file_bytes or b"")
            except OnboardingValidationError as exc:
                raise RentalValidationError(str(exc)) from exc
            except OnboardingConflict as exc:
                raise RentalConflict(str(exc)) from exc
            catalog = get_agent(state["agent_id"])
            return snapshot_instance(instance, _public_rental(state), catalog)

