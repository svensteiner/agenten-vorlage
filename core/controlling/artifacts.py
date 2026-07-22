"""Tenant-local, auditable artifacts for the KMU controlling pilot."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import html
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from typing import Any

from core.controlling.tools import (
    DERIVED_RATIO_METRICS,
    DIRECT_BALANCE_METRICS,
    MANDATORY_MAPPING_METRICS,
    PNL_METRIC_NAMES,
    REPORT_PERIODS,
    RESERVED_DERIVED_METRIC_NAMES,
)

if os.name == "nt":
    import msvcrt
else:
    import fcntl


CALCULATION_VERSION = "kmu-report-v1"
_HISTORY_LIMIT = 100
_MAX_HISTORY_BYTES = 1_000_000
_MAX_LEDGER_BYTES = 50 * 1024 * 1024
_MAX_LEDGER_RUNS = 10_000
_MAX_SOURCE_BYTES = 25 * 1024 * 1024
_MAX_MAPPING_BYTES = 1024 * 1024
_ACCEPTANCE_KEY_BYTES = 32
_ACCEPTANCE_LOCK_WAIT_SECONDS = 5
_LOCAL_PILOT_TOOLS = {"read", "compute", "report"}
_ACCEPTANCE_THREAD_LOCK = threading.Lock()


def persist_report_artifacts(
    root: Path,
    report: dict[str, Any],
    management: dict[str, Any],
    *,
    validated_at: datetime,
    draft_created_at: datetime,
) -> dict[str, Any] | None:
    """Write latest/history/acceptance artifacts, or skip incomplete legacy tests."""
    root = root.resolve()
    source = _safe_file(root, report.get("source"), allowed_roots={"inbox", "data", "imports"})
    mapping = _safe_file(root, "project/pilot/account-mapping.json", allowed_roots={"project"})
    if source is None or mapping is None:
        if isinstance(report.get("provenance"), dict):
            raise ValueError("Quelle oder Mapping ist nicht mehr sicher verfügbar.")
        return None

    artifacts = (root / "artifacts").resolve()
    try:
        artifacts.relative_to(root)
    except ValueError:
        raise ValueError("Artefaktordner liegt außerhalb der Instanz.") from None
    if (root / "artifacts").is_symlink():
        raise ValueError("Artefaktordner darf kein Symlink sein.")
    artifacts.mkdir(parents=True, exist_ok=True)
    sanitized_report = {
        key: report[key]
        for key in (
            "source",
            "method",
            "report_metadata",
            "metrics",
            "groups",
            "material_deviations",
            "reconciliation",
        )
        if key in report
    }
    kpi_hash = _json_hash(
        {
            "report_metadata": sanitized_report.get("report_metadata"),
            "metrics": sanitized_report.get("metrics"),
            "reconciliation": sanitized_report.get("reconciliation"),
        }
    )
    external_tools = _enabled_external_tools(root)
    report_provenance = _validated_report_provenance(report, source, mapping)
    run = {
        "recorded_at": _iso(draft_created_at),
        "validation_completed_at": _iso(validated_at),
        "draft_created_at": _iso(draft_created_at),
        "draft_latency_seconds": max(
            0.0, (draft_created_at - validated_at).total_seconds()
        ),
        "input_fingerprint": report_provenance["input_fingerprint"],
        "mapping_version": report_provenance["mapping_version"],
        "calculation_version": report_provenance["calculation_version"],
        "kpi_result_hash": kpi_hash,
        "source_file": report.get("source"),
        "period": sanitized_report.get("report_metadata"),
        "mapped_accounts": report.get("reconciliation", {}).get(
            "mapped_account_count"
        ),
        "formula": report.get("method"),
        "reconciliation_result": report.get("reconciliation"),
        "approval_log": [],
        "external_action_log": [],
        "external_action_capabilities_enabled": external_tools,
        "external_actions_without_explicit_approval": 0,
    }
    return _persist_report_transaction(
        root=root,
        artifacts=artifacts,
        source=source,
        mapping=mapping,
        report=report,
        sanitized_report=sanitized_report,
        management=management,
        run=run,
        external_tools=external_tools,
        kpi_hash=kpi_hash,
        draft_created_at=draft_created_at,
    )


def _persist_report_transaction(
    *,
    root: Path,
    artifacts: Path,
    source: Path,
    mapping: Path,
    report: dict[str, Any],
    sanitized_report: dict[str, Any],
    management: dict[str, Any],
    run: dict[str, Any],
    external_tools: list[str],
    kpi_hash: str,
    draft_created_at: datetime,
) -> dict[str, Any]:
    """Commit state and every shared report view as one serialized transaction."""
    with _acceptance_write_lock(root):
        # Revalidate after waiting for the lock so a replaced source or mapping
        # cannot be persisted with stale compute-time provenance.
        report_provenance = _validated_report_provenance(report, source, mapping)
        acceptance_mapping = _load_acceptance_mapping(
            mapping, expected_hash=report_provenance["mapping_version"]
        )
        key = _acceptance_key(root)
        run = {
            **run,
            "acceptance_criteria": {
                "sourced_totals": _sourced_totals_pass(report, acceptance_mapping),
                "draft_latency": run["draft_latency_seconds"] < 300,
                "approval_safety": not external_tools,
            },
        }
        history, signed_run = _record_acceptance_run_locked(root, run, key)
        runs = [*history.get("runs", []), signed_run][-_HISTORY_LIMIT:]
        repeatable_count = _consecutive_equal_runs(runs)
        criteria = {
            **signed_run["acceptance_criteria"],
            "repeatable_runs": repeatable_count >= 3,
        }
        acceptance = {
            "passed": all(criteria.values()),
            "repeatable_run_count": repeatable_count,
            "criteria": criteria,
        }
        payload = {
            "schema_version": 1,
            "generated_at": _iso(draft_created_at),
            "report": sanitized_report,
            "management": management,
            "provenance": signed_run,
            "acceptance": acceptance,
        }
        stamp = draft_created_at.astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        history_report = artifacts / (
            f"controlling-report-{stamp}-s{signed_run['sequence']}-{kpi_hash[:8]}.json"
        )
        latest = artifacts / "latest-controlling-report.json"
        markdown = artifacts / "latest-controlling-report.md"
        human_report = artifacts / "latest-controlling-report.html"
        history_path = artifacts / "acceptance-evidence.json"
        _atomic_json(history_report, payload)
        _atomic_json(history_path, {"schema_version": 1, "runs": runs})
        _atomic_json(latest, payload)
        _atomic_text(markdown, _markdown(payload))
        _atomic_text(human_report, _html(payload))
        return {
            "artifact": latest.relative_to(root).as_posix(),
            "human_artifact": human_report.relative_to(root).as_posix(),
            "history_artifact": history_report.relative_to(root).as_posix(),
            "acceptance": acceptance,
        }


def read_acceptance_status(root: Path) -> dict[str, Any]:
    """Verify signed acceptance state without creating or modifying any file."""
    empty = {
        "valid": True,
        "passed": False,
        "repeatable_run_count": 0,
        "sequence": 0,
        "run_signature": None,
    }
    root = Path(root).resolve()
    declared_state = root / "state"
    if not declared_state.exists():
        return empty
    if declared_state.is_symlink() or not declared_state.is_dir():
        return {**empty, "valid": False}
    try:
        state = declared_state.resolve(strict=True)
        state.relative_to(root)
    except (OSError, ValueError):
        return {**empty, "valid": False}

    key_path = state / ".acceptance-hmac-key"
    ledger_path = state / "acceptance-ledger.jsonl"
    head_path = state / "acceptance-head.json"
    paths = (key_path, ledger_path, head_path)
    if any(path.is_symlink() for path in paths):
        return {**empty, "valid": False}
    if not any(path.exists() for path in paths):
        return empty
    if not key_path.is_file() or not head_path.is_file():
        return {**empty, "valid": False}
    try:
        key = key_path.read_bytes()
        if len(key) != _ACCEPTANCE_KEY_BYTES:
            raise ValueError("invalid key")
        runs = _read_acceptance_ledger(ledger_path, key)
        head = _read_acceptance_head(head_path, key)
    except (OSError, ValueError):
        return {**empty, "valid": False}

    sequence = runs[-1]["sequence"] if runs else 0
    signature = runs[-1]["run_signature"] if runs else None
    if head["sequence"] != sequence or head["last_run_signature"] != signature:
        return {**empty, "valid": False}
    if not runs:
        return empty

    signed_criteria = runs[-1].get("acceptance_criteria")
    required = {"sourced_totals", "draft_latency", "approval_safety"}
    criteria = (
        {
            name: signed_criteria.get(name) is True
            for name in required
        }
        if isinstance(signed_criteria, dict) and set(signed_criteria) == required
        else {name: False for name in required}
    )
    repeatable_count = _consecutive_equal_runs(runs)
    return {
        "valid": True,
        "passed": all(criteria.values()) and repeatable_count >= 3,
        "repeatable_run_count": repeatable_count,
        "sequence": sequence,
        "run_signature": signature,
        "source_file": runs[-1].get("source_file"),
        "input_fingerprint": runs[-1].get("input_fingerprint"),
        "mapping_version": runs[-1].get("mapping_version"),
    }


def _safe_file(root: Path, relative: Any, *, allowed_roots: set[str]) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (root / relative).resolve()
    try:
        parts = candidate.relative_to(root).parts
    except ValueError:
        return None
    if not parts or parts[0] not in allowed_roots or not candidate.is_file():
        return None
    return candidate


def _sha256(path: Path, *, max_bytes: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("Provenienzdatei ist zu groß.")
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_history(path: Path, key: bytes) -> dict[str, Any]:
    """Strictly validate the derived evidence view.

    The authoritative history lives below ``state``. A modified report artifact
    can therefore never alter the acceptance result.
    """
    try:
        if path.stat().st_size > _MAX_HISTORY_BYTES:
            raise ValueError("Abnahmenachweis ist zu gro\u00df.")
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema_version": 1, "runs": []}
    except (OSError, json.JSONDecodeError):
        raise ValueError("Abnahmenachweis ist besch\u00e4digt.") from None
    runs = value.get("runs") if isinstance(value, dict) else None
    if not isinstance(runs, list) or any(not isinstance(run, dict) for run in runs):
        raise ValueError("Abnahmenachweis ist besch\u00e4digt.")
    candidates = runs[-_HISTORY_LIMIT:]
    verified: list[dict[str, Any]] = []
    previous_signature = (
        candidates[0].get("previous_run_signature") if candidates else None
    )
    first_sequence = candidates[0].get("sequence") if candidates else 1
    if candidates and (
        not isinstance(first_sequence, int)
        or isinstance(first_sequence, bool)
        or first_sequence < 1
    ):
        raise ValueError("Abnahmenachweis ist besch\u00e4digt.")
    previous_sequence = first_sequence - 1
    for run in candidates:
        signature = run.get("run_signature")
        if (
            not isinstance(run.get("sequence"), int)
            or isinstance(run.get("sequence"), bool)
            or run["sequence"] != previous_sequence + 1
            or not isinstance(signature, str)
            or not re_full_sha256(signature)
            or run.get("previous_run_signature") != previous_signature
            or not hmac.compare_digest(signature, _run_signature(run, key))
        ):
            raise ValueError("Abnahmenachweis ist besch\u00e4digt.")
        verified.append(run)
        previous_sequence = run["sequence"]
        previous_signature = signature
    return {"schema_version": 1, "runs": verified}


def _acceptance_state_dir(root: Path) -> Path:
    declared_state = root / "state"
    if declared_state.is_symlink():
        raise ValueError("Abnahmestatus darf nicht \u00fcber einen Symlink liegen.")
    state = declared_state.resolve()
    try:
        state.relative_to(root)
    except ValueError:
        raise ValueError("Abnahmestatus liegt au\u00dferhalb der Instanz.") from None
    state.mkdir(parents=True, exist_ok=True)
    return state


def _acceptance_state_paths(root: Path) -> tuple[Path, Path]:
    state = _acceptance_state_dir(root)
    ledger = state / "acceptance-ledger.jsonl"
    head = state / "acceptance-head.json"
    if ledger.is_symlink() or head.is_symlink():
        raise ValueError("Abnahmestatus darf keine Symlinks verwenden.")
    return ledger, head


def _load_acceptance_state(root: Path, key: bytes) -> dict[str, Any]:
    """Load the signed append-only ledger and enforce its committed head."""
    ledger_path, head_path = _acceptance_state_paths(root)
    ledger_exists = ledger_path.exists()
    head_exists = head_path.exists()
    if ledger_exists and not head_exists:
        raise ValueError("Abnahme-Head fehlt; ein Rollback ist nicht ausgeschlossen.")
    if not head_exists:
        _write_acceptance_head(head_path, 0, None, key)

    head = _read_acceptance_head(head_path, key)
    runs = _read_acceptance_ledger(ledger_path, key) if ledger_exists else []
    ledger_sequence = runs[-1]["sequence"] if runs else 0
    ledger_signature = runs[-1]["run_signature"] if runs else None
    head_sequence = head["sequence"]
    head_signature = head["last_run_signature"]

    if ledger_sequence == head_sequence and ledger_signature == head_signature:
        return {"schema_version": 1, "runs": runs}

    # A process may have crashed after fsyncing one record but before the
    # atomic head update. This is the only recoverable mismatch.
    if (
        ledger_sequence == head_sequence + 1
        and runs[-1].get("previous_run_signature") == head_signature
    ):
        _write_acceptance_head(head_path, ledger_sequence, ledger_signature, key)
        return {"schema_version": 1, "runs": runs}

    raise ValueError("Abnahme-Ledger und Head widersprechen sich; m\u00f6glicher Rollback.")


def _record_acceptance_run_locked(
    root: Path, run: dict[str, Any], key: bytes
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Allocate, sign and commit while the caller holds the write lock."""
    history = _load_acceptance_state(root, key)
    previous = history["runs"][-1] if history["runs"] else None
    signed_run = {
        **run,
        "run_id": secrets.token_hex(16),
        "sequence": previous["sequence"] + 1 if previous else 1,
        "previous_run_signature": previous["run_signature"] if previous else None,
    }
    signed_run["run_signature"] = _run_signature(signed_run, key)
    _commit_acceptance_run(root, signed_run, key)
    return history, signed_run


@contextmanager
def _acceptance_write_lock(root: Path) -> Iterator[None]:
    """Serialize writers; the operating system releases the lock after a crash."""
    lock_path = _acceptance_state_dir(root) / ".acceptance-write.lock"
    if not _ACCEPTANCE_THREAD_LOCK.acquire(timeout=_ACCEPTANCE_LOCK_WAIT_SECONDS):
        raise ValueError("Abnahmestatus wird bereits von einem anderen Lauf aktualisiert.")
    handle = None
    locked = False
    try:
        if lock_path.is_symlink():
            raise ValueError("Abnahmesperre darf kein Symlink sein.")
        handle = lock_path.open("a+b", buffering=0)
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            os.fsync(handle.fileno())
        deadline = time.monotonic() + _ACCEPTANCE_LOCK_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                _lock_acceptance_file(handle)
                locked = True
                break
            except OSError:
                time.sleep(0.025)
        if not locked:
            raise ValueError(
                "Abnahmestatus wird bereits von einem anderen Prozess aktualisiert."
            )
        yield
    finally:
        if locked and handle is not None:
            _unlock_acceptance_file(handle)
        if handle is not None:
            handle.close()
        _ACCEPTANCE_THREAD_LOCK.release()


def _lock_acceptance_file(handle: Any) -> None:
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_acceptance_file(handle: Any) -> None:
    try:
        if os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        # Closing the handle below is the final release mechanism after errors.
        pass


def _commit_acceptance_run(root: Path, run: dict[str, Any], key: bytes) -> None:
    if run.get("sequence", 0) > _MAX_LEDGER_RUNS:
        raise ValueError("Abnahme-Ledger enth\u00e4lt zu viele L\u00e4ufe.")
    ledger_path, head_path = _acceptance_state_paths(root)
    _append_acceptance_ledger(ledger_path, run)
    _write_acceptance_head(
        head_path,
        run["sequence"],
        run["run_signature"],
        key,
    )


def _read_acceptance_ledger(path: Path, key: bytes) -> list[dict[str, Any]]:
    if path.is_symlink():
        raise ValueError("Abnahme-Ledger darf kein Symlink sein.")
    try:
        if path.stat().st_size > _MAX_LEDGER_BYTES:
            raise ValueError("Abnahme-Ledger ist zu gro\u00df.")
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError):
        raise ValueError("Abnahme-Ledger konnte nicht sicher gelesen werden.") from None
    if len(lines) > _MAX_LEDGER_RUNS:
        raise ValueError("Abnahme-Ledger enth\u00e4lt zu viele L\u00e4ufe.")

    runs: list[dict[str, Any]] = []
    previous_signature: str | None = None
    for sequence, line in enumerate(lines, start=1):
        try:
            run = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError("Abnahme-Ledger ist besch\u00e4digt.") from None
        if not isinstance(run, dict):
            raise ValueError("Abnahme-Ledger ist besch\u00e4digt.")
        signature = run.get("run_signature")
        if (
            run.get("sequence") != sequence
            or isinstance(run.get("sequence"), bool)
            or run.get("previous_run_signature") != previous_signature
            or not isinstance(signature, str)
            or not re_full_sha256(signature)
            or not hmac.compare_digest(signature, _run_signature(run, key))
        ):
            raise ValueError("Abnahme-Ledger ist besch\u00e4digt.")
        runs.append(run)
        previous_signature = signature
    return runs


def _append_acceptance_ledger(path: Path, run: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ValueError("Abnahme-Ledger darf kein Symlink sein.")
    encoded = (
        json.dumps(run, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    current_size = path.stat().st_size if path.exists() else 0
    if current_size + len(encoded) > _MAX_LEDGER_BYTES:
        raise ValueError("Abnahme-Ledger ist zu gro\u00df.")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        raise ValueError("Abnahme-Ledger konnte nicht gespeichert werden.") from None


def _read_acceptance_head(path: Path, key: bytes) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("Abnahme-Head darf kein Symlink sein.")
    try:
        head = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("Abnahme-Head ist besch\u00e4digt.") from None
    expected_keys = {
        "schema_version",
        "sequence",
        "last_run_signature",
        "head_signature",
    }
    sequence = head.get("sequence") if isinstance(head, dict) else None
    last_signature = head.get("last_run_signature") if isinstance(head, dict) else None
    signature = head.get("head_signature") if isinstance(head, dict) else None
    if (
        not isinstance(head, dict)
        or set(head) != expected_keys
        or head.get("schema_version") != 1
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 0
        or (sequence == 0 and last_signature is not None)
        or (
            sequence > 0
            and not (isinstance(last_signature, str) and re_full_sha256(last_signature))
        )
        or not isinstance(signature, str)
        or not re_full_sha256(signature)
        or not hmac.compare_digest(signature, _head_signature(head, key))
    ):
        raise ValueError("Abnahme-Head ist besch\u00e4digt.")
    return head


def _write_acceptance_head(
    path: Path,
    sequence: int,
    last_run_signature: str | None,
    key: bytes,
) -> None:
    head: dict[str, Any] = {
        "schema_version": 1,
        "sequence": sequence,
        "last_run_signature": last_run_signature,
    }
    head["head_signature"] = _head_signature(head, key)
    _atomic_private_json(path, head)


def _head_signature(head: dict[str, Any], key: bytes) -> str:
    unsigned = {
        name: value for name, value in head.items() if name != "head_signature"
    }
    encoded = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def _atomic_private_json(path: Path, value: Any) -> None:
    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        raise ValueError("Abnahme-Head konnte nicht gespeichert werden.") from None
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _acceptance_key(root: Path) -> bytes:
    state = _acceptance_state_dir(root)
    key_path = state / ".acceptance-hmac-key"
    if key_path.is_symlink():
        raise ValueError("Abnahmeschlüssel darf kein Symlink sein.")
    try:
        key = key_path.read_bytes()
    except FileNotFoundError:
        candidate = secrets.token_bytes(_ACCEPTANCE_KEY_BYTES)
        temporary = key_path.with_name(
            f".{key_path.name}.{secrets.token_hex(16)}.tmp"
        )
        try:
            descriptor = os.open(
                temporary,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(candidate)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, key_path)
            key = candidate
        except OSError:
            raise ValueError(
                "Abnahmeschl\u00fcssel konnte nicht angelegt werden."
            ) from None
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    except OSError:
        raise ValueError("Abnahmeschlüssel konnte nicht gelesen werden.") from None
    if len(key) != _ACCEPTANCE_KEY_BYTES:
        raise ValueError("Abnahmeschlüssel ist ungültig.")
    return key


def _run_signature(run: dict[str, Any], key: bytes) -> str:
    unsigned = {name: value for name, value in run.items() if name != "run_signature"}
    encoded = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _validated_report_provenance(
    report: dict[str, Any], source: Path, mapping: Path
) -> dict[str, str]:
    provenance = report.get("provenance")
    required = {"input_fingerprint", "mapping_version", "calculation_version"}
    if not isinstance(provenance, dict) or set(provenance) != required:
        raise ValueError("Rechenprovenienz fehlt oder ist unvollständig.")
    input_fingerprint = provenance.get("input_fingerprint")
    mapping_version = provenance.get("mapping_version")
    if (
        not isinstance(input_fingerprint, str)
        or not re_full_sha256(input_fingerprint)
        or not isinstance(mapping_version, str)
        or not re_full_sha256(mapping_version)
        or provenance.get("calculation_version") != CALCULATION_VERSION
    ):
        raise ValueError("Rechenprovenienz ist ungültig.")
    if (
        _sha256(source, max_bytes=_MAX_SOURCE_BYTES) != input_fingerprint
        or _sha256(mapping, max_bytes=_MAX_MAPPING_BYTES) != mapping_version
    ):
        raise ValueError("Eingabe oder Mapping wurde nach der Berechnung verändert.")
    return {
        "input_fingerprint": input_fingerprint,
        "mapping_version": mapping_version,
        "calculation_version": CALCULATION_VERSION,
    }


def _consecutive_equal_runs(runs: list[dict[str, Any]]) -> int:
    if not runs:
        return 0
    keys = (
        "input_fingerprint",
        "mapping_version",
        "calculation_version",
        "kpi_result_hash",
    )
    expected = tuple(runs[-1].get(key) for key in keys)
    count = 0
    for run in reversed(runs):
        if tuple(run.get(key) for key in keys) != expected:
            break
        count += 1
    return count


def _load_acceptance_mapping(
    path: Path, *, expected_hash: str
) -> dict[str, Any] | None:
    try:
        mapping_bytes = path.read_bytes()
        if (
            len(mapping_bytes) > _MAX_MAPPING_BYTES
            or hashlib.sha256(mapping_bytes).hexdigest() != expected_hash
        ):
            return None
        mapping = json.loads(mapping_bytes.decode("utf-8"))
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError, RecursionError):
        return None
    return mapping if isinstance(mapping, dict) else None


def _sourced_totals_pass(
    report: dict[str, Any], mapping: dict[str, Any] | None
) -> bool:
    reconciliation = report.get("reconciliation")
    metadata = report.get("report_metadata")
    if (
        not isinstance(reconciliation, dict)
        or not isinstance(metadata, dict)
        or not isinstance(mapping, dict)
    ):
        return False
    source = reconciliation.get("source_account_count")
    mapped = reconciliation.get("mapped_account_count")
    ignored = reconciliation.get("ignored_account_count")
    counts_ok = all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in (source, mapped, ignored)
    ) and source > 0 and source == mapped + ignored
    metadata_ok = all(
        isinstance(metadata.get(key), str) and metadata[key].strip()
        for key in ("period_start", "period_end", "currency", "sign_convention")
    )
    return bool(
        counts_ok
        and metadata_ok
        and _reconciled_report_values_pass(report, reconciliation, mapping)
        and report.get("source")
        and report.get("method")
    )


def _reconciled_report_values_pass(
    report: dict[str, Any],
    reconciliation: dict[str, Any],
    mapping: dict[str, Any],
) -> bool:
    mapping_groups = mapping.get("groups")
    metric_refs = mapping.get("metrics")
    report_groups = report.get("groups")
    report_metrics = report.get("metrics")
    mapped_source = reconciliation.get("mapped_source_period_totals")
    grouped = reconciliation.get("grouped_period_totals")
    if (
        not isinstance(mapping_groups, dict)
        or not mapping_groups
        or not all(
            isinstance(name, str) and name and isinstance(rule, dict)
            for name, rule in mapping_groups.items()
        )
        or not isinstance(metric_refs, dict)
        or not MANDATORY_MAPPING_METRICS <= set(metric_refs)
        or RESERVED_DERIVED_METRIC_NAMES.intersection(metric_refs)
        or not isinstance(report_groups, dict)
        or not isinstance(report_metrics, dict)
        or not isinstance(mapped_source, dict)
        or not isinstance(grouped, dict)
    ):
        return False

    non_ignored_groups = {
        name for name, rule in mapping_groups.items() if rule.get("ignored") is not True
    }
    if not report_groups or set(report_groups) != non_ignored_groups:
        return False
    pnl_groups = {
        ref
        for metric_name, refs in metric_refs.items()
        if isinstance(metric_name, str)
        and metric_name.casefold() in PNL_METRIC_NAMES
        and isinstance(refs, list)
        for ref in refs
        if isinstance(ref, str)
    }

    normalized_groups: dict[str, dict[str, Decimal | None]] = {}
    mapped_row_count = 0
    for group_name in report_groups:
        group = report_groups.get(group_name)
        if not isinstance(group, dict):
            return False
        group_account_ids = group.get("account_ids")
        row_count = group.get("row_count")
        if (
            set(group) != {*REPORT_PERIODS, "account_ids", "row_count"}
            or not isinstance(group_account_ids, list)
            or any(
                not isinstance(account_id, str) or not account_id.strip()
                for account_id in group_account_ids
            )
            or len(set(group_account_ids)) != len(group_account_ids)
            or not isinstance(row_count, int)
            or isinstance(row_count, bool)
            or row_count < len(group_account_ids)
        ):
            return False
        mapped_row_count += row_count
        normalized_groups[group_name] = {}
        for period in REPORT_PERIODS:
            valid, value = _validated_optional_decimal(group.get(period))
            if not valid:
                return False
            normalized_groups[group_name][period] = value
        if (
            (row_count == 0) != (not group_account_ids)
            or row_count == 0
            and any(normalized_groups[group_name][period] is not None for period in REPORT_PERIODS)
            or row_count > 0
            and any(
                normalized_groups[group_name][period] is None
                for period in ("month", "prior")
            )
        ):
            return False
        if group_account_ids and group_name in pnl_groups and any(
            normalized_groups[group_name][period] is None
            for period in ("ytd", "ytd_prior")
        ):
            return False
    if mapped_row_count != reconciliation.get("mapped_account_count"):
        return False

    for period in REPORT_PERIODS:
        expected_total = sum(
            (
                value
                for values in normalized_groups.values()
                if (value := values[period]) is not None
            ),
            Decimal("0"),
        )
        source_total = _validated_decimal(mapped_source.get(period))
        grouped_total = _validated_decimal(grouped.get(period))
        if source_total != expected_total or grouped_total != expected_total:
            return False

    expected_metric_names = set(metric_refs)
    expected_metric_names.update(
        name
        for name, numerator, _denominator in DERIVED_RATIO_METRICS
        if numerator in normalized_groups
    )
    expected_metric_names.update(
        name
        for name, group_name in DIRECT_BALANCE_METRICS
        if group_name in normalized_groups
    )
    if set(report_metrics) != expected_metric_names:
        return False

    for metric_name, refs in metric_refs.items():
        if (
            not isinstance(metric_name, str)
            or not metric_name
            or not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or any(
                not isinstance(ref, str)
                or ref not in non_ignored_groups
                or ref not in normalized_groups
                for ref in refs
            )
        ):
            return False
        expected_values = {
            period: _sum_optional_group_values(normalized_groups, refs, period)
            for period in REPORT_PERIODS
        }
        expected_accounts = sorted(
            {
                account_id
                for ref in refs
                for account_id in report_groups[ref]["account_ids"]
            }
        )
        if not _report_metric_passes(
            report_metrics.get(metric_name),
            expected_values,
            expected_accounts,
            mandatory=metric_name in MANDATORY_MAPPING_METRICS,
        ):
            return False

    for metric_name, numerator, denominator in DERIVED_RATIO_METRICS:
        if numerator not in normalized_groups:
            continue
        expected_values = {}
        for period in REPORT_PERIODS:
            a = normalized_groups[numerator][period]
            b = normalized_groups.get(denominator, {}).get(period)
            expected_values[period] = abs(a) / abs(b) if a is not None and b else None
        expected_accounts = sorted(
            set(report_groups[numerator]["account_ids"])
            | set(report_groups.get(denominator, {}).get("account_ids", []))
        )
        if not _report_metric_passes(
            report_metrics.get(metric_name), expected_values, expected_accounts
        ):
            return False

    for metric_name, group_name in DIRECT_BALANCE_METRICS:
        if group_name in normalized_groups and not _report_metric_passes(
            report_metrics.get(metric_name),
            normalized_groups[group_name],
            report_groups[group_name]["account_ids"],
        ):
            return False
    return True


def _sum_optional_group_values(
    groups: dict[str, dict[str, Decimal | None]], refs: list[str], period: str
) -> Decimal | None:
    values = [groups[ref][period] for ref in refs if groups[ref][period] is not None]
    return sum(values, Decimal("0")) if values else None


def _report_metric_passes(
    metric: Any,
    expected_values: dict[str, Decimal | None],
    expected_account_ids: list[str],
    *,
    mandatory: bool = False,
) -> bool:
    if (
        not isinstance(metric, dict)
        or set(metric) != {*REPORT_PERIODS, "account_ids"}
        or metric.get("account_ids") != expected_account_ids
    ):
        return False
    for period in REPORT_PERIODS:
        valid, actual = _validated_optional_decimal(metric.get(period))
        if not valid or mandatory and actual is None or actual != expected_values[period]:
            return False
    return True


def _validated_decimal(value: Any) -> Decimal | None:
    valid, decimal = _validated_optional_decimal(value)
    return decimal if valid else None


def _validated_optional_decimal(value: Any) -> tuple[bool, Decimal | None]:
    if value is None:
        return True, None
    if isinstance(value, bool):
        return False, None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False, None
    return (True, decimal) if decimal.is_finite() else (False, None)


def _enabled_external_tools(root: Path) -> list[str]:
    try:
        manifest = json.loads(
            (root / "project" / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []
    permissions = manifest.get("tool_permissions", {}) if isinstance(manifest, dict) else {}
    enabled = permissions.get("enabled", []) if isinstance(permissions, dict) else []
    return (
        sorted(
            {
                str(name).lower()
                for name in enabled
                if str(name).lower() not in _LOCAL_PILOT_TOOLS
            }
        )
        if isinstance(enabled, list)
        else []
    )


def _markdown(payload: dict[str, Any]) -> str:
    report = payload["report"]
    management = payload["management"]
    metadata = report.get("report_metadata", {})
    lines = [
        "# KMU-Controlling-Report",
        "",
        f"Zeitraum: {metadata.get('period_start', '–')} bis {metadata.get('period_end', '–')}",
        f"Währung: {metadata.get('currency', '–')}",
        "",
        "## Management-Fazit",
        "",
        str(management.get("summary", "")),
        "",
        "## Kennzahlen",
        "",
        "| Kennzahl | Monat | Vergleich | YTD | YTD Vorjahr |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in report.get("metrics", {}).items():
        if not isinstance(values, dict):
            continue
        lines.append(
            f"| {name} | {values.get('month', '–')} | {values.get('prior', '–')} "
            f"| {values.get('ytd', '–')} | {values.get('ytd_prior', '–')} |"
        )
    lines.extend(["", "## Nächste Schritte", ""])
    lines.extend(f"- {item}" for item in management.get("actions", []))
    acceptance = payload["acceptance"]
    lines.extend(
        [
            "",
            "## Pilot-Abnahme",
            "",
            f"Status: {'bestanden' if acceptance['passed'] else 'noch offen'}",
            f"Identische Wiederholungsläufe: {acceptance['repeatable_run_count']}/3",
            "",
            f"Quelle: {report.get('source', '–')}",
            f"Methode: {report.get('method', '–')}",
            "",
        ]
    )
    return "\n".join(lines)


def _html(payload: dict[str, Any]) -> str:
    """Render a dependency-free management report that is safe to open locally."""
    report = payload["report"]
    management = payload["management"]
    metadata = report.get("report_metadata", {})
    acceptance = payload["acceptance"]
    def esc(value: Any) -> str:
        return html.escape(str(value), quote=True)
    metric_rows = []
    for name, values in report.get("metrics", {}).items():
        if not isinstance(values, dict):
            continue
        cells = "".join(
            f"<td>{esc(values.get(period, '–'))}</td>"
            for period in ("month", "prior", "ytd", "ytd_prior")
        )
        metric_rows.append(f"<tr><th>{esc(name.upper())}</th>{cells}</tr>")
    alarms = "".join(
        f"<li>{esc(item)}</li>" for item in management.get("alarms", [])
    )
    actions = "".join(
        f"<li>{esc(item)}</li>" for item in management.get("actions", [])
    )
    status = "Bestanden" if acceptance["passed"] else "Noch offen"
    status_class = "passed" if acceptance["passed"] else "open"
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KMU-Controlling-Report</title><style>
body{{font-family:Arial,sans-serif;background:#f3f6fa;color:#142033;margin:0}}main{{max-width:1050px;margin:32px auto;background:#fff;padding:40px;border-radius:14px;box-shadow:0 8px 30px #1d35571a}}
h1{{margin:0 0 8px;color:#102a43}}.meta{{color:#52677d;margin-bottom:28px}}.summary{{font-size:1.15rem;line-height:1.6;background:#edf4fb;padding:18px;border-left:5px solid #2463a9}}
table{{width:100%;border-collapse:collapse;margin:24px 0}}th,td{{padding:11px;border-bottom:1px solid #dce5ee;text-align:right}}th:first-child{{text-align:left}}thead th{{background:#102a43;color:#fff}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}li{{margin:9px 0}}.badge{{display:inline-block;padding:7px 12px;border-radius:999px;font-weight:bold}}.passed{{background:#d8f3dc;color:#1b5e20}}.open{{background:#fff1cc;color:#7a5200}}footer{{margin-top:30px;color:#60758a;font-size:.9rem}}@media(max-width:700px){{main{{margin:0;padding:22px;border-radius:0}}.grid{{grid-template-columns:1fr}}}}
</style></head><body><main><h1>KMU-Controlling-Report</h1>
<div class="meta">Zeitraum: {esc(metadata.get('period_start', '–'))} bis {esc(metadata.get('period_end', '–'))} · Währung: {esc(metadata.get('currency', '–'))}</div>
<p class="summary">{esc(management.get('summary', ''))}</p>
<table><thead><tr><th>Kennzahl</th><th>Monat</th><th>Vergleich</th><th>YTD</th><th>YTD Vorjahr</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table>
<div class="grid"><section><h2>Alarme</h2><ul>{alarms or '<li>Keine.</li>'}</ul></section><section><h2>Nächste Schritte</h2><ol>{actions}</ol></section></div>
<h2>Pilot-Abnahme</h2><span class="badge {status_class}">{status}</span> <span>{acceptance['repeatable_run_count']}/3 identische Wiederholungsläufe</span>
<footer>Quelle: {esc(report.get('source', '–'))}<br>Methode: {esc(report.get('method', '–'))}</footer>
</main></body></html>"""


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _iso(value: datetime) -> str:
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
