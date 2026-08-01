"""Tenant-local, auditable artifacts for the KMU controlling pilot."""

from __future__ import annotations

from collections.abc import Iterator
import contextlib
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
import stat
import threading
import time
from typing import Any

from core.controlling.tools import (
    ControllingComputeTool,
    DERIVED_RATIO_METRICS,
    DIRECT_BALANCE_METRICS,
    MANDATORY_MAPPING_METRICS,
    PNL_METRIC_NAMES,
    REPORT_PERIODS,
    RESERVED_DERIVED_METRIC_NAMES,
    _SIGN_CONVENTION,
    _SIGN_CONVENTION_NOTE,
    pilot_availability,
    is_safe_report_label,
    labels_are_unique,
)
from core.controlling.variance import monthly_variance_brief

if os.name == "nt":
    import msvcrt
else:
    import fcntl


CALCULATION_VERSION = "kmu-report-v3"
PRESENTATION_VERSION = "management-renderer-v3"
_HISTORY_LIMIT = 100
_MAX_HISTORY_BYTES = 1_000_000
_MAX_LEDGER_BYTES = 50 * 1024 * 1024
_MAX_LEDGER_RUNS = 10_000
_MAX_SOURCE_BYTES = 25 * 1024 * 1024
_MAX_MAPPING_BYTES = 1024 * 1024
_MAX_POLICY_BYTES = 1024 * 1024
_MAX_PUBLISHED_VIEW_BYTES = 50 * 1024 * 1024
_MAX_OPERATION_ID_CHARS = 128
_ACCEPTANCE_KEY_BYTES = 32
_ACCEPTANCE_LOCK_WAIT_SECONDS = 5
_LOCAL_PILOT_TOOLS = {"read", "compute", "report"}
_REQUIRED_APPROVAL_TERMS = {"external communication", "send", "publish"}
_REQUIRED_REPEATABLE_CRITERIA = frozenset(
    {"sourced_totals", "draft_latency", "approval_safety"}
)
_ACCEPTANCE_THREAD_LOCK = threading.Lock()


def persist_report_artifacts(
    root: Path,
    report: dict[str, Any],
    management: dict[str, Any],
    *,
    validated_at: datetime,
    draft_created_at: datetime,
    operation_id: str | None = None,
) -> dict[str, Any] | None:
    """Write latest/history/acceptance artifacts, or skip incomplete legacy tests."""
    root = root.resolve()
    operation_id = validate_operation_id(operation_id)
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
    report_provenance = _validated_report_provenance(report, source, mapping)
    variance_binding = _validated_management_variance(
        root, report, management, source, report_provenance
    )
    budget_source: Path | None = None
    budget_provenance: dict[str, str] | None = None
    if variance_binding is not None:
        budget_source, budget_provenance = variance_binding

    sanitized_report = {
        key: report[key]
        for key in (
            "source",
            "method",
            "report_metadata",
            "period_labels",
            "sign_convention",
            "sign_convention_note",
            "metrics",
            "groups",
            "material_deviations",
            "reconciliation",
            "availability",
        )
        if key in report
    }
    # Kept as kpi_result_hash for ledger compatibility, but it now binds the
    # complete persisted draft rather than only a KPI subset.
    kpi_hash = _json_hash({"report": sanitized_report, "management": management})
    run = {
        "recorded_at": _iso(draft_created_at),
        "validation_completed_at": _iso(validated_at),
        "draft_created_at": _iso(draft_created_at),
        "draft_latency_seconds": (draft_created_at - validated_at).total_seconds(),
        "input_fingerprint": report_provenance["input_fingerprint"],
        "mapping_version": report_provenance["mapping_version"],
        "calculation_version": report_provenance["calculation_version"],
        "presentation_version": PRESENTATION_VERSION,
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
        "external_actions_without_explicit_approval": 0,
    }
    if budget_provenance is not None:
        run = {**run, **budget_provenance}
    return _persist_report_transaction(
        root=root,
        artifacts=artifacts,
        source=source,
        mapping=mapping,
        report=report,
        sanitized_report=sanitized_report,
        management=management,
        run=run,
        kpi_hash=kpi_hash,
        draft_created_at=draft_created_at,
        operation_id=operation_id,
        budget_source=budget_source,
    )


def validate_operation_id(operation_id: Any) -> str | None:
    """Validate the optional caller-owned idempotency key.

    The value is persisted in a signed ledger record, never used as a path, and
    deliberately limited to a portable ASCII subset so callers cannot smuggle
    control characters or ambiguous Unicode into durable audit evidence.
    """
    if operation_id is None:
        return None
    if not isinstance(operation_id, str):
        raise ValueError("muss eine Zeichenkette sein.")
    if not 1 <= len(operation_id) <= _MAX_OPERATION_ID_CHARS:
        raise ValueError(f"muss 1 bis {_MAX_OPERATION_ID_CHARS} Zeichen lang sein.")
    if not operation_id[0].isalnum() or not operation_id[0].isascii():
        raise ValueError("muss mit einem ASCII-Buchstaben oder einer Ziffer beginnen.")
    if any(
        not (character.isascii() and (character.isalnum() or character in ".:_-"))
        for character in operation_id
    ):
        raise ValueError(
            "darf nur ASCII-Buchstaben, Ziffern, '.', ':', '_' und '-' enthalten."
        )
    return operation_id


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
    kpi_hash: str,
    draft_created_at: datetime,
    operation_id: str | None,
    budget_source: Path | None,
) -> dict[str, Any]:
    """Commit state and every shared report view as one serialized transaction."""
    with _acceptance_write_lock(root):
        # Revalidate after waiting for the lock so a replaced source or mapping
        # cannot be replayed or persisted with stale compute-time provenance.
        report_provenance = _validated_report_provenance(report, source, mapping)
        locked_variance_binding = _validated_management_variance(
            root, report, management, source, report_provenance
        )
        if (budget_source is None) != (locked_variance_binding is None):
            raise ValueError("Budget-Provenienz hat sich waehrend der Speicherung geaendert.")
        budget_provenance: dict[str, str] | None = None
        if locked_variance_binding is not None:
            locked_budget_source, budget_provenance = locked_variance_binding
            if locked_budget_source != budget_source:
                raise ValueError("Budget-Quelle hat sich waehrend der Speicherung geaendert.")
        acceptance_mapping = _load_acceptance_mapping(
            mapping, expected_hash=report_provenance["mapping_version"]
        )
        run = {
            **run,
            "input_fingerprint": report_provenance["input_fingerprint"],
            "mapping_version": report_provenance["mapping_version"],
            "calculation_version": report_provenance["calculation_version"],
        }
        if budget_provenance is not None:
            run = {**run, **budget_provenance}
        key: bytes | None = None
        history: dict[str, Any] | None = None
        if operation_id is not None:
            key = _acceptance_key(root)
            history = _load_acceptance_state(root, key)
            existing = next(
                (
                    prior
                    for prior in history["runs"]
                    if prior.get("operation_id") == operation_id
                ),
                None,
            )
            if existing is not None:
                operation_binding_fields = (
                    "source_file",
                    "input_fingerprint",
                    "mapping_version",
                    "calculation_version",
                    "presentation_version",
                    "kpi_result_hash",
                    "budget_source_file",
                    "budget_input_fingerprint",
                )
                existing_binding = {
                    field: existing.get(field) for field in operation_binding_fields
                }
                current_binding = {
                    field: run.get(field) for field in operation_binding_fields
                }
                if not hmac.compare_digest(
                    _json_hash(existing_binding), _json_hash(current_binding)
                ):
                    raise ValueError(
                        "Operation-ID wurde bereits fuer eine andere Anfrage verwendet."
                    )
                return _replay_committed_operation(root, existing)
        policy_snapshot = _approval_policy_snapshot(root)
        policy_hash = _json_hash(policy_snapshot)
        if key is None:
            key = _acceptance_key(root)
        if history is None:
            history = _load_acceptance_state(root, key)
        signing_policy_snapshot = _approval_policy_snapshot(root)
        signing_policy_hash = _json_hash(signing_policy_snapshot)
        if not hmac.compare_digest(policy_hash, signing_policy_hash):
            signing_policy_snapshot = _invalidated_policy_snapshot(
                signing_policy_snapshot, "policy_changed_during_acceptance"
            )
            signing_policy_hash = _json_hash(signing_policy_snapshot)
        policy_snapshot = signing_policy_snapshot
        policy_hash = signing_policy_hash
        next_sequence = history["runs"][-1]["sequence"] + 1 if history["runs"] else 1
        stamp = draft_created_at.astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        history_name = f"controlling-report-{stamp}-s{next_sequence}-{kpi_hash[:8]}.json"
        historical_html_name = f"controlling-report-{stamp}-s{next_sequence}-{kpi_hash[:8]}.html"
        run = {
            **run,
            "approval_policy_snapshot": policy_snapshot,
            "approval_policy_hash": policy_hash,
            "external_action_capabilities_enabled": policy_snapshot[
                "enabled_external_capabilities"
            ],
            "acceptance_criteria": {
                "sourced_totals": _sourced_totals_pass(
                    report,
                    acceptance_mapping,
                    has_budget_variance=budget_provenance is not None,
                ),
                "draft_latency": 0 <= run["draft_latency_seconds"] < 300,
                "approval_safety": _approval_safety_pass(run, policy_snapshot),
            },
        }
        if operation_id is not None:
            run = {
                **run,
                "operation_id": operation_id,
                "history_artifact": f"artifacts/{history_name}",
                "human_artifact": f"artifacts/{historical_html_name}",
            }
        history, signed_run = _prepare_acceptance_run_locked(
            root, run, key, history=history
        )
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
        # JSON is written with sorted keys. Render from that same canonical
        # object so reloading latest JSON and rendering it produces identical
        # UTF-8 HTML bytes.
        payload = json.loads(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        history_report = artifacts / history_name
        historical_human_report = artifacts / historical_html_name
        latest = artifacts / "latest-controlling-report.json"
        markdown = artifacts / "latest-controlling-report.md"
        human_report = artifacts / "latest-controlling-report.html"
        history_path = artifacts / "acceptance-evidence.json"
        # Publish immutable operation evidence before committing its signed
        # ledger record.  A crash here leaves only an unreferenced artifact;
        # retry may safely allocate and commit the operation again.
        _atomic_json(history_report, payload)
        if operation_id is not None:
            _atomic_text(historical_human_report, render_html(payload))
        _commit_acceptance_run(root, signed_run, key)
        # The latest JSON is the status authority.  Publish it only after every
        # human-facing shared view is durable, otherwise an interrupted write
        # could make a new report look accepted without a matching review view.
        _atomic_json(history_path, {"schema_version": 1, "runs": runs})
        _atomic_text(markdown, _markdown(payload))
        _atomic_text(human_report, render_html(payload))
        _atomic_json(latest, payload)
        result = {
            "artifact": latest.relative_to(root).as_posix(),
            "human_artifact": human_report.relative_to(root).as_posix(),
            "history_artifact": history_report.relative_to(root).as_posix(),
            "acceptance": acceptance,
        }
        if operation_id is not None:
            result = {
                **result,
                "operation_id": operation_id,
                "artifact": history_report.relative_to(root).as_posix(),
                "human_artifact": historical_human_report.relative_to(root).as_posix(),
            }
        return result


def _replay_committed_operation(root: Path, run: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable committed result for one already-signed operation."""
    operation_id = run.get("operation_id")
    history_artifact = run.get("history_artifact")
    human_artifact = run.get("human_artifact")
    if (
        not isinstance(operation_id, str)
        or validate_operation_id(operation_id) != operation_id
        or not isinstance(history_artifact, str)
        or not isinstance(human_artifact, str)
    ):
        raise ValueError("Gespeicherte Operation ist unvollstaendig.")
    payload = _read_committed_operation_payload(root, history_artifact)
    if payload.get("provenance") != run:
        raise ValueError("Gespeicherte Operation wurde veraendert.")
    management = payload.get("management")
    acceptance = payload.get("acceptance")
    if not isinstance(management, dict) or not isinstance(acceptance, dict):
        raise ValueError("Gespeicherte Operation ist unvollstaendig.")
    human_bytes = _read_committed_operation_file(root, human_artifact)
    if human_bytes != render_html(payload).encode("utf-8"):
        raise ValueError("Gespeicherte Operation wurde veraendert.")
    # If the latest committed operation crashed after ledger/head commit but
    # before publishing shared views, rebuild those views from its immutable,
    # signed operation artifacts.  Replaying an older operation must never
    # roll the latest report backwards.
    key = _acceptance_key(root)
    history = _load_acceptance_state(root, key)
    latest_run = history["runs"][-1] if history["runs"] else None
    if (
        isinstance(latest_run, dict)
        and latest_run.get("run_signature") == run.get("run_signature")
    ):
        artifacts = root / "artifacts"
        runs = history["runs"][-_HISTORY_LIMIT:]
        _atomic_json(
            artifacts / "acceptance-evidence.json",
            {"schema_version": 1, "runs": runs},
        )
        _atomic_text(artifacts / "latest-controlling-report.md", _markdown(payload))
        _atomic_text(
            artifacts / "latest-controlling-report.html", render_html(payload)
        )
        _atomic_json(artifacts / "latest-controlling-report.json", payload)
    return {
        **management,
        "operation_id": operation_id,
        "artifact": history_artifact,
        "human_artifact": human_artifact,
        "history_artifact": history_artifact,
        "acceptance": acceptance,
    }


def _read_committed_operation_payload(root: Path, relative: str) -> dict[str, Any]:
    raw = _read_committed_operation_file(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Gespeicherte Operation ist beschaedigt.") from None
    if not isinstance(payload, dict):
        raise ValueError("Gespeicherte Operation ist beschaedigt.")
    return payload


def _read_committed_operation_file(root: Path, relative: str) -> bytes:
    """Read one fixed operation artifact without accepting arbitrary paths."""
    relative_path = Path(relative)
    if (
        relative_path.is_absolute()
        or relative_path.parts[:1] != ("artifacts",)
        or len(relative_path.parts) != 2
        or relative_path.name.startswith(".")
    ):
        raise ValueError("Gespeicherter Operationspfad ist ungueltig.")
    artifact = root / relative_path
    try:
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("Gespeicherter Operationspfad ist ungueltig.")
        size = artifact.stat().st_size
        if size < 0 or size > _MAX_PUBLISHED_VIEW_BYTES:
            raise ValueError("Gespeicherte Operation ist zu gross.")
        with artifact.open("rb") as handle:
            raw = handle.read(_MAX_PUBLISHED_VIEW_BYTES + 1)
        if len(raw) != size or len(raw) > _MAX_PUBLISHED_VIEW_BYTES:
            raise ValueError("Gespeicherte Operation wurde veraendert.")
        return raw
    except OSError:
        raise ValueError("Gespeicherte Operation konnte nicht sicher gelesen werden.") from None


def read_acceptance_status(root: Path) -> dict[str, Any]:
    """Verify signed acceptance state without creating or modifying any file."""
    return _read_acceptance_status(root)


def read_verified_latest_report_html(
    root: Path, *, require_passed: bool = False
) -> bytes:
    """Return the fixed latest HTML bytes only when their signed bundle verifies.

    The acceptance lock serializes this verification with report publication.
    Crucially, the returned bytes are the already-opened bytes that were
    verified, rather than a second path-based read after verification.
    """
    root = Path(root).resolve()
    with _acceptance_write_lock(root):
        bundle = _read_published_view_bundle(root)
        status = _read_acceptance_status(root, published_bundle=bundle)
        if not status["valid"]:
            raise ValueError("Signiertes Berichtsbundle ist ungueltig.")
        if require_passed and not status["passed"]:
            raise ValueError("Bericht hat die signierte 3/3-Abnahme nicht bestanden.")
        return bundle[2]


def _read_acceptance_status(
    root: Path, *, published_bundle: tuple[bytes, bytes, bytes] | None = None
) -> dict[str, Any]:
    """Verify signed acceptance state, optionally against already-opened views."""
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

    latest_run = runs[-1]
    if (
        latest_run.get("calculation_version") != CALCULATION_VERSION
        or latest_run.get("presentation_version") != PRESENTATION_VERSION
    ):
        return {**empty, "valid": False, "sequence": sequence, "run_signature": signature}
    if not _current_signed_inputs_match(root, latest_run):
        return {**empty, "valid": False, "sequence": sequence, "run_signature": signature}

    current_policy = _approval_policy_snapshot(root)
    last_policy_hash = runs[-1].get("approval_policy_hash")
    if (
        not _valid_policy_evidence(runs[-1])
        or not current_policy["policy_valid"]
        or not isinstance(last_policy_hash, str)
        or not hmac.compare_digest(last_policy_hash, _json_hash(current_policy))
    ):
        return {**empty, "valid": False, "sequence": sequence, "run_signature": signature}
    signed_criteria = runs[-1].get("acceptance_criteria")
    criteria = (
        {
            name: signed_criteria.get(name) is True
            for name in _REQUIRED_REPEATABLE_CRITERIA
        }
        if (
            isinstance(signed_criteria, dict)
            and set(signed_criteria) == _REQUIRED_REPEATABLE_CRITERIA
        )
        else {name: False for name in _REQUIRED_REPEATABLE_CRITERIA}
    )
    repeatable_count = _consecutive_equal_runs(runs)
    expected_acceptance = {
        "passed": all(criteria.values()) and repeatable_count >= 3,
        "repeatable_run_count": repeatable_count,
        "criteria": {**criteria, "repeatable_runs": repeatable_count >= 3},
    }
    if not _published_report_views_match(
        root, runs[-1], expected_acceptance, bundle=published_bundle
    ):
        return {**empty, "valid": False, "sequence": sequence, "run_signature": signature}
    return {
        "valid": True,
        "passed": expected_acceptance["passed"],
        "repeatable_run_count": repeatable_count,
        "sequence": sequence,
        "run_signature": signature,
        "source_file": runs[-1].get("source_file"),
        "input_fingerprint": runs[-1].get("input_fingerprint"),
        "mapping_version": runs[-1].get("mapping_version"),
    }


def _published_report_views_match(
    root: Path,
    run: dict[str, Any],
    expected_acceptance: dict[str, Any],
    *,
    bundle: tuple[bytes, bytes, bytes] | None = None,
) -> bool:
    """Bind signed acceptance to the exact latest machine and human views."""
    try:
        payload_bytes, markdown, html_bytes = bundle or _read_published_view_bundle(root)
        payload = json.loads(payload_bytes.decode("utf-8"))
        provenance = payload.get("provenance") if isinstance(payload, dict) else None
        report = payload.get("report") if isinstance(payload, dict) else None
        management = payload.get("management") if isinstance(payload, dict) else None
        acceptance = payload.get("acceptance") if isinstance(payload, dict) else None
        result_hash = run.get("kpi_result_hash")
        if (
            not isinstance(provenance, dict)
            or not isinstance(report, dict)
            or not isinstance(management, dict)
            or not isinstance(acceptance, dict)
            or not isinstance(acceptance.get("passed"), bool)
            or not isinstance(acceptance.get("repeatable_run_count"), int)
            or isinstance(acceptance.get("repeatable_run_count"), bool)
            or acceptance != expected_acceptance
            or payload.get("schema_version") != 1
            or payload.get("generated_at") != run.get("draft_created_at")
            or payload.get("provenance") != run
            or not isinstance(result_hash, str)
            or not re_full_sha256(result_hash)
            or not hmac.compare_digest(
                _json_hash({"report": report, "management": management}), result_hash
            )
            or provenance.get("sequence") != run.get("sequence")
            or not isinstance(provenance.get("run_signature"), str)
            or not isinstance(run.get("run_signature"), str)
            or not hmac.compare_digest(
                provenance["run_signature"], run["run_signature"]
            )
        ):
            return False
        return (
            markdown == _markdown(payload).encode("utf-8")
            and html_bytes == render_html(payload).encode("utf-8")
        )
    except (
        OSError, UnicodeDecodeError, ValueError, TypeError, KeyError,
        AttributeError, RecursionError, OverflowError, json.JSONDecodeError,
    ):
        return False


def _read_published_view_bundle(root: Path) -> tuple[bytes, bytes, bytes]:
    """Pin root/artifacts and read the three latest views as one stable bundle."""
    lexical_root = Path(os.path.abspath(root))
    if not _policy_path_components_safe(lexical_root):
        raise ValueError("Unsicherer Artefaktpfad.")
    return (
        _read_published_view_bundle_windows(lexical_root)
        if os.name == "nt"
        else _read_published_view_bundle_posix(lexical_root)
    )


def _read_published_view_bundle_windows(root: Path) -> tuple[bytes, bytes, bytes]:
    """Pin the complete Windows view hierarchy by handles, not path lookups."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
    final = kernel32.GetFinalPathNameByHandleW
    final.argtypes, final.restype = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD], wintypes.DWORD
    read = kernel32.ReadFile
    read.argtypes, read.restype = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID], wintypes.BOOL
    seek = kernel32.SetFilePointerEx
    seek.argtypes, seek.restype = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD], wintypes.BOOL
    info = kernel32.GetFileInformationByHandle

    class FileInfo(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("creation_low", wintypes.DWORD), ("creation_high", wintypes.DWORD), ("access_low", wintypes.DWORD), ("access_high", wintypes.DWORD), ("write_low", wintypes.DWORD), ("write_high", wintypes.DWORD), ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD), ("links", wintypes.DWORD), ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

    info.argtypes, info.restype = [wintypes.HANDLE, ctypes.POINTER(FileInfo)], wintypes.BOOL
    artifacts = root / "artifacts"
    names = ("latest-controlling-report.json", "latest-controlling-report.md", "latest-controlling-report.html")
    paths = [root, artifacts, *(artifacts / name for name in names)]
    invalid = ctypes.c_void_p(-1).value
    handles: list[Any] = []
    try:
        for index, path in enumerate(paths):
            flags = 0x00200000 | (0x02000000 if index < 2 else 0)
            handle = create(str(path), 0x80000000, 0x00000001, None, 3, flags, None)
            if handle in (invalid, None):
                raise OSError(ctypes.get_last_error(), "CreateFileW failed")
            handles.append(handle)
            if _windows_final_path(final, handle) != os.path.normcase(str(path.resolve(strict=True))):
                raise ValueError("Artefaktpfad wurde umgeleitet.")
        if os.path.dirname(_windows_final_path(final, handles[1])) != _windows_final_path(final, handles[0]):
            raise ValueError("Artefaktordner gehört nicht zum Root.")
        if any(os.path.dirname(_windows_final_path(final, handle)) != _windows_final_path(final, handles[1]) for handle in handles[2:]):
            raise ValueError("Artefaktdatei gehört nicht zum Artefaktordner.")
        before = []
        for handle in handles[2:]:
            item = FileInfo()
            if not info(handle, ctypes.byref(item)) or item.attributes & 0x400:
                raise ValueError("Artefakt ist kein regulärer Handle.")
            size = (item.size_high << 32) | item.size_low
            if size > _MAX_PUBLISHED_VIEW_BYTES:
                raise ValueError("Artefakt ist zu groß.")
            before.append(item)
        raws = [_windows_read_published_handle(read, seek, handle) for handle in handles[2:]]
        for handle, identity, raw in zip(handles[2:], before, raws):
            after = FileInfo()
            size = (identity.size_high << 32) | identity.size_low
            if not info(handle, ctypes.byref(after)) or _windows_file_identity(identity) != _windows_file_identity(after) or len(raw) != size:
                raise ValueError("Artefakt wurde verändert.")
        return tuple(raws)  # type: ignore[return-value]
    finally:
        for handle in reversed(handles):
            close(handle)


def _windows_read_published_handle(read_file: Any, set_pointer: Any, handle: Any) -> bytes:
    import ctypes
    from ctypes import wintypes

    if not set_pointer(handle, 0, None, 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx failed")
    buffer = ctypes.create_string_buffer(_MAX_PUBLISHED_VIEW_BYTES + 1)
    count = wintypes.DWORD()
    if not read_file(handle, buffer, len(buffer), ctypes.byref(count), None):
        raise OSError(ctypes.get_last_error(), "ReadFile failed")
    if count.value > _MAX_PUBLISHED_VIEW_BYTES:
        raise ValueError("Artefakt ist zu groß.")
    first = buffer.raw[:count.value]
    if not set_pointer(handle, 0, None, 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx failed")
    count = wintypes.DWORD()
    if not read_file(handle, buffer, len(buffer), ctypes.byref(count), None):
        raise OSError(ctypes.get_last_error(), "ReadFile failed")
    second = buffer.raw[:count.value]
    if first != second:
        raise ValueError("Artefakt wurde während des Lesens verändert.")
    return first


def _read_published_view_bundle_posix(root: Path) -> tuple[bytes, bytes, bytes]:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        root_fd = os.open(root, directory_flags)
        descriptors.append(root_fd)
        artifacts_fd = os.open("artifacts", directory_flags, dir_fd=root_fd)
        descriptors.append(artifacts_fd)
        names = ("latest-controlling-report.json", "latest-controlling-report.md", "latest-controlling-report.html")
        fds = [os.open(name, file_flags, dir_fd=artifacts_fd) for name in names]
        descriptors.extend(fds)
        root_identity, artifacts_identity = os.fstat(root_fd), os.fstat(artifacts_fd)
        identities = [os.fstat(fd) for fd in fds]
        if not stat.S_ISDIR(root_identity.st_mode) or not stat.S_ISDIR(artifacts_identity.st_mode):
            raise ValueError("Artefaktordner ist ungültig.")
        raws = [_read_published_fd_twice(fd, identity) for fd, identity in zip(fds, identities)]
        if (
            not all(_same_policy_file_state(identity, os.fstat(fd)) for fd, identity in zip(fds, identities))
            or not _same_policy_identity(root_identity, os.stat(root, follow_symlinks=False))
            or not _same_policy_identity(artifacts_identity, os.stat("artifacts", dir_fd=root_fd, follow_symlinks=False))
            or any(not _same_policy_identity(identity, os.stat(name, dir_fd=artifacts_fd, follow_symlinks=False)) for name, identity in zip(names, identities))
        ):
            raise ValueError("Artefakt-Bundle wurde verändert.")
        return tuple(raws)  # type: ignore[return-value]
    finally:
        for descriptor in reversed(descriptors):
            with contextlib.suppress(OSError):
                os.close(descriptor)


def _read_published_fd_twice(descriptor: int, identity: os.stat_result) -> bytes:
    if not stat.S_ISREG(identity.st_mode) or identity.st_size > _MAX_PUBLISHED_VIEW_BYTES:
        raise ValueError("Artefakt ist ungültig oder zu groß.")
    os.lseek(descriptor, 0, os.SEEK_SET)
    first = os.read(descriptor, _MAX_PUBLISHED_VIEW_BYTES + 1)
    middle = os.fstat(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    second = os.read(descriptor, _MAX_PUBLISHED_VIEW_BYTES + 1)
    after = os.fstat(descriptor)
    if (
        len(first) > _MAX_PUBLISHED_VIEW_BYTES
        or first != second
        or len(first) != identity.st_size
        or not _same_policy_file_state(identity, middle)
        or not _same_policy_file_state(identity, after)
    ):
        raise ValueError("Artefakt wurde während des Lesens verändert.")
    return first


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


def _current_signed_inputs_match(root: Path, run: dict[str, Any]) -> bool:
    """Verify current safe source, mapping, and optional budget bytes."""
    actual_and_mapping_match = (
        _current_signed_input_matches(
            root,
            run.get("source_file"),
            allowed_roots={"inbox", "data", "imports"},
            max_bytes=_MAX_SOURCE_BYTES,
            expected_hash=run.get("input_fingerprint"),
        )
        and _current_signed_input_matches(
            root,
            "project/pilot/account-mapping.json",
            allowed_roots={"project"},
            max_bytes=_MAX_MAPPING_BYTES,
            expected_hash=run.get("mapping_version"),
        )
    )
    budget_source = run.get("budget_source_file")
    budget_fingerprint = run.get("budget_input_fingerprint")
    if budget_source is None and budget_fingerprint is None:
        return actual_and_mapping_match
    if (
        not isinstance(budget_source, str)
        or not isinstance(budget_fingerprint, str)
        or not re_full_sha256(budget_fingerprint)
    ):
        return False
    return actual_and_mapping_match and _current_signed_input_matches(
        root,
        budget_source,
        allowed_roots={"inbox", "data", "imports"},
        max_bytes=_MAX_SOURCE_BYTES,
        expected_hash=budget_fingerprint,
    )


def _current_signed_input_matches(
    root: Path,
    relative: Any,
    *,
    allowed_roots: set[str],
    max_bytes: int,
    expected_hash: Any,
) -> bool:
    if not isinstance(relative, str) or not relative.strip() or not isinstance(expected_hash, str):
        return False
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return False
    if not relative_path.parts or relative_path.parts[0] not in allowed_roots or not re_full_sha256(expected_hash):
        return False
    try:
        raw = _read_current_signed_input(root, relative_path, max_bytes=max_bytes)
    except (OSError, ValueError):
        return False
    current_hash = hashlib.sha256(raw).hexdigest()
    return hmac.compare_digest(current_hash, expected_hash)


def _read_current_signed_input(root: Path, relative: Path, *, max_bytes: int) -> bytes:
    """Read one current provenance authority from pinned handles/descriptors."""
    lexical_root = Path(os.path.abspath(root))
    if not _policy_path_components_safe(lexical_root):
        raise ValueError("Unsicherer Eingabepfad.")
    return (
        _read_current_signed_input_windows(lexical_root, relative, max_bytes=max_bytes)
        if os.name == "nt"
        else _read_current_signed_input_posix(lexical_root, relative, max_bytes=max_bytes)
    )


def _after_current_input_first_read() -> None:
    """No-op seam used only to exercise replacement races in regression tests."""


def _after_current_input_root_open() -> None:
    """No-op seam used only to exercise root-path races in regression tests."""


def _read_current_signed_input_posix(root: Path, relative: Path, *, max_bytes: int) -> bytes:
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        root_fd = os.open(root, directory_flags)
        descriptors.append(root_fd)
        _after_current_input_root_open()
        parent_fd = root_fd
        directory_entries: list[tuple[str, int, os.stat_result]] = []
        for part in relative.parts[:-1]:
            descriptor = os.open(part, directory_flags, dir_fd=parent_fd)
            descriptors.append(descriptor)
            identity = os.fstat(descriptor)
            if not stat.S_ISDIR(identity.st_mode):
                raise ValueError("Eingabeordner ist ungültig.")
            directory_entries.append((part, parent_fd, identity))
            parent_fd = descriptor
        file_name = relative.parts[-1]
        file_fd = os.open(file_name, file_flags, dir_fd=parent_fd)
        descriptors.append(file_fd)
        root_identity = os.fstat(root_fd)
        file_identity = os.fstat(file_fd)
        if not stat.S_ISDIR(root_identity.st_mode) or not stat.S_ISREG(file_identity.st_mode):
            raise ValueError("Eingabe ist ungültig.")
        raw = _read_current_input_fd_twice(file_fd, file_identity, max_bytes=max_bytes)
        if (
            not _same_policy_file_state(file_identity, os.fstat(file_fd))
            or not _same_policy_identity(root_identity, os.stat(root, follow_symlinks=False))
            or not _policy_path_components_safe(root)
            or any(
                not _same_policy_identity(identity, os.stat(name, dir_fd=parent, follow_symlinks=False))
                for name, parent, identity in directory_entries
            )
            or not _same_policy_identity(file_identity, os.stat(file_name, dir_fd=parent_fd, follow_symlinks=False))
        ):
            raise ValueError("Eingabe wurde verändert.")
        return raw
    finally:
        for descriptor in reversed(descriptors):
            with contextlib.suppress(OSError):
                os.close(descriptor)


def _read_current_input_fd_twice(descriptor: int, identity: os.stat_result, *, max_bytes: int) -> bytes:
    if identity.st_size > max_bytes:
        raise ValueError("Eingabe ist zu groß.")
    os.lseek(descriptor, 0, os.SEEK_SET)
    first = os.read(descriptor, max_bytes + 1)
    middle = os.fstat(descriptor)
    _after_current_input_first_read()
    os.lseek(descriptor, 0, os.SEEK_SET)
    second = os.read(descriptor, max_bytes + 1)
    after = os.fstat(descriptor)
    if (
        len(first) > max_bytes
        or first != second
        or len(first) != identity.st_size
        or not _same_policy_file_state(identity, middle)
        or not _same_policy_file_state(identity, after)
    ):
        raise ValueError("Eingabe wurde während des Lesens verändert.")
    return first


def _read_current_signed_input_windows(root: Path, relative: Path, *, max_bytes: int) -> bytes:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
    final = kernel32.GetFinalPathNameByHandleW
    final.argtypes, final.restype = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD], wintypes.DWORD
    read = kernel32.ReadFile
    read.argtypes, read.restype = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID], wintypes.BOOL
    seek = kernel32.SetFilePointerEx
    seek.argtypes, seek.restype = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD], wintypes.BOOL
    info = kernel32.GetFileInformationByHandle

    class FileInfo(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("creation_low", wintypes.DWORD), ("creation_high", wintypes.DWORD), ("access_low", wintypes.DWORD), ("access_high", wintypes.DWORD), ("write_low", wintypes.DWORD), ("write_high", wintypes.DWORD), ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD), ("links", wintypes.DWORD), ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

    info.argtypes, info.restype = [wintypes.HANDLE, ctypes.POINTER(FileInfo)], wintypes.BOOL
    paths = [root]
    current = root
    for part in relative.parts:
        current = current / part
        paths.append(current)
    if any(_is_link_or_junction(path) for path in paths):
        raise ValueError("Eingabepfad wurde umgeleitet.")
    invalid = ctypes.c_void_p(-1).value
    handles: list[Any] = []
    try:
        for index, path in enumerate(paths):
            flags = 0x00200000 | (0x02000000 if index < len(paths) - 1 else 0)
            handle = create(str(path), 0x80000000, 0x00000001, None, 3, flags, None)
            if handle in (invalid, None):
                raise OSError(ctypes.get_last_error(), "CreateFileW failed")
            handles.append(handle)
            if _windows_final_path(final, handle) != os.path.normcase(str(path.resolve(strict=True))):
                raise ValueError("Eingabepfad wurde umgeleitet.")
            if index == 0:
                _after_current_input_root_open()
        file_handle = handles[-1]
        before = FileInfo()
        if not info(file_handle, ctypes.byref(before)) or before.attributes & 0x400:
            raise ValueError("Eingabe ist kein regulärer Handle.")
        size = (before.size_high << 32) | before.size_low
        if size > max_bytes:
            raise ValueError("Eingabe ist zu groß.")
        first = _windows_read_current_input_handle(read, seek, file_handle, max_bytes=max_bytes)
        _after_current_input_first_read()
        second = _windows_read_current_input_handle(read, seek, file_handle, max_bytes=max_bytes)
        after = FileInfo()
        if (
            not info(file_handle, ctypes.byref(after))
            or _windows_file_identity(before) != _windows_file_identity(after)
            or first != second
            or len(first) != size
            or not _policy_path_components_safe(root)
            or any(_is_link_or_junction(path) for path in paths)
            or any(
                _windows_final_path(final, handle) != os.path.normcase(str(path.resolve(strict=True)))
                for path, handle in zip(paths, handles)
            )
        ):
            raise ValueError("Eingabe wurde verändert.")
        return first
    finally:
        for handle in reversed(handles):
            close(handle)


def _windows_read_current_input_handle(read_file: Any, set_pointer: Any, handle: Any, *, max_bytes: int) -> bytes:
    import ctypes
    from ctypes import wintypes

    if not set_pointer(handle, 0, None, 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx failed")
    buffer = ctypes.create_string_buffer(max_bytes + 1)
    count = wintypes.DWORD()
    if not read_file(handle, buffer, len(buffer), ctypes.byref(count), None):
        raise OSError(ctypes.get_last_error(), "ReadFile failed")
    if count.value > max_bytes:
        raise ValueError("Eingabe ist zu groß.")
    return buffer.raw[:count.value]


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
    if ledger_exists:
        try:
            runs = _read_acceptance_ledger(ledger_path, key)
        except ValueError:
            runs = _recover_torn_ledger_suffix(ledger_path, key, head)
    else:
        runs = []
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


def _prepare_acceptance_run_locked(
    root: Path,
    run: dict[str, Any],
    key: bytes,
    *,
    history: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Allocate and sign while the caller holds the write lock."""
    history = history if history is not None else _load_acceptance_state(root, key)
    previous = history["runs"][-1] if history["runs"] else None
    signed_run = {
        **run,
        "run_id": secrets.token_hex(16),
        "sequence": previous["sequence"] + 1 if previous else 1,
        "previous_run_signature": previous["run_signature"] if previous else None,
    }
    signed_run["run_signature"] = _run_signature(signed_run, key)
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
        raw = path.read_bytes()
    except FileNotFoundError:
        return []
    except OSError:
        raise ValueError("Abnahme-Ledger konnte nicht sicher gelesen werden.") from None
    return _decode_acceptance_ledger(raw, key)


def _decode_acceptance_ledger(raw: bytes, key: bytes) -> list[dict[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise ValueError("Abnahme-Ledger ist besch\u00e4digt.") from None
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


def _recover_torn_ledger_suffix(
    path: Path, key: bytes, head: dict[str, Any]
) -> list[dict[str, Any]]:
    """Discard only an uncommitted partial final append beyond the signed head."""
    try:
        if path.stat().st_size > _MAX_LEDGER_BYTES:
            raise ValueError("Abnahme-Ledger ist zu gross.")
        raw = path.read_bytes()
    except OSError:
        raise ValueError("Abnahme-Ledger konnte nicht sicher gelesen werden.") from None
    if not raw or raw.endswith(b"\n"):
        raise ValueError("Abnahme-Ledger ist besch\u00e4digt.")
    boundary = raw.rfind(b"\n")
    committed = raw[: boundary + 1] if boundary >= 0 else b""
    runs = _decode_acceptance_ledger(committed, key)
    sequence = runs[-1]["sequence"] if runs else 0
    signature = runs[-1]["run_signature"] if runs else None
    if sequence != head["sequence"] or signature != head["last_run_signature"]:
        raise ValueError("Abnahme-Ledger ist besch\u00e4digt.")
    try:
        with path.open("r+b", buffering=0) as handle:
            handle.truncate(len(committed))
            os.fsync(handle.fileno())
    except OSError:
        raise ValueError("Abnahme-Ledger konnte nicht repariert werden.") from None
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


def _two_source_availability() -> dict[str, dict[str, str]]:
    """Return the only availability contract permitted for a budget comparison."""
    return {
        **pilot_availability(),
        "budget_variance": {
            "status": "available",
            "processing": "two_source_actual_vs_budget",
        },
    }


def _validated_management_variance(
    root: Path,
    report: dict[str, Any],
    management: dict[str, Any],
    source: Path,
    report_provenance: dict[str, str],
) -> tuple[Path, dict[str, str]] | None:
    """Validate the compact two-source brief before it becomes signed evidence.

    The management layer carries the comparison so the underlying report remains
    the actuals-only aggregate.  This validates the exact source bindings and
    only permits deterministic aggregate values; no source rows are persisted.
    """
    if not isinstance(management, dict):
        raise ValueError("Management-Entwurf ist ungueltig.")
    variance = management.get("variance")
    if variance is None:
        if report.get("availability") != pilot_availability():
            raise ValueError("Budget-Verfuegbarkeit erfordert einen Zwei-Quellen-Nachweis.")
        return None
    if "variance" in report:
        raise ValueError("Ist-Bericht darf keine Budgetabweichung enthalten.")
    required = {
        "kind",
        "status",
        "report_metadata",
        "metrics",
        "top_group_drivers",
        "sources",
        "reconciliation",
        "limitations",
    }
    if not isinstance(variance, dict) or set(variance) != required:
        raise ValueError("Budgetabweichung ist unvollstaendig.")
    if (
        variance.get("kind") != "monthly_actual_vs_budget_brief"
        or variance.get("status") != "computed_unapproved"
        or variance.get("report_metadata") != report.get("report_metadata")
        or variance.get("limitations")
        != [
            "computed_from_provided_actual_and_budget_sources",
            "not_approved",
        ]
        or report.get("availability") != _two_source_availability()
    ):
        raise ValueError("Budgetabweichung hat einen ungueltigen Vertrag.")

    sources = variance.get("sources")
    if not isinstance(sources, dict) or set(sources) != {
        "actual",
        "budget",
        "mapping_version",
    }:
        raise ValueError("Budgetquellen sind unvollstaendig.")
    actual = sources.get("actual")
    budget = sources.get("budget")
    budget_fingerprint = budget.get("fingerprint") if isinstance(budget, dict) else None
    if (
        not isinstance(actual, dict)
        or set(actual) != {"source", "fingerprint"}
        or actual.get("source") != report.get("source")
        or actual.get("fingerprint") != report_provenance["input_fingerprint"]
        or sources.get("mapping_version") != report_provenance["mapping_version"]
        or not isinstance(budget, dict)
        or set(budget) != {"source", "fingerprint"}
        or not isinstance(budget_fingerprint, str)
        or not re_full_sha256(budget_fingerprint)
    ):
        raise ValueError("Budgetquellen sind ungueltig.")
    budget_source = _safe_file(
        root, budget.get("source"), allowed_roots={"inbox", "data", "imports"}
    )
    if budget_source is None or budget_source == source:
        raise ValueError("Budgetquelle ist nicht sicher oder nicht getrennt.")
    if _sha256(budget_source, max_bytes=_MAX_SOURCE_BYTES) != budget_fingerprint:
        raise ValueError("Budgetquelle wurde nach der Berechnung veraendert.")

    budget_raw = ControllingComputeTool(root).safe_run(
        json.dumps({"operation": "kmu_report", "source": budget["source"]})
    )
    if budget_raw.startswith("FEHLER"):
        raise ValueError("Budgetquelle konnte nicht erneut reconciled werden.")
    try:
        budget_report = json.loads(budget_raw)
        expected_variance = monthly_variance_brief(report, budget_report)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Budgetabweichung konnte nicht erneut reconciled werden.") from exc
    if variance != expected_variance:
        raise ValueError("Budgetabweichung stimmt nicht mit den Quellen ueberein.")

    report_reconciliation = report.get("reconciliation")
    if not isinstance(report_reconciliation, dict):
        raise ValueError("Ist-Bericht ist nicht reconciled.")
    expected_counts = {
        key: report_reconciliation.get(key)
        for key in (
            "source_account_count",
            "mapped_account_count",
            "ignored_account_count",
        )
    }
    reconciliation = variance.get("reconciliation")
    if (
        not isinstance(reconciliation, dict)
        or set(reconciliation) != {"actual", "budget"}
        or reconciliation.get("actual") != expected_counts
        or reconciliation.get("budget") != expected_counts
    ):
        raise ValueError("Budgetabweichung ist nicht reconciled.")
    _validated_variance_values(variance)
    return budget_source, {
        "budget_source_file": budget["source"],
        "budget_input_fingerprint": budget["fingerprint"],
    }


def _validated_variance_values(variance: dict[str, Any]) -> None:
    """Reject malformed or raw-looking values before rendering a compact table."""
    metrics = variance.get("metrics")
    drivers = variance.get("top_group_drivers")
    if not isinstance(metrics, dict) or not isinstance(drivers, list):
        raise ValueError("Budgetabweichung enthaelt keine aggregierten Werte.")
    for name, comparison in metrics.items():
        if not is_safe_report_label(name) or not isinstance(comparison, dict):
            raise ValueError("Budgetabweichung enthaelt ungueltige Kennzahlen.")
        _validated_variance_comparison(comparison)
    for driver in drivers:
        if (
            not isinstance(driver, dict)
            or set(driver) != {
                "group",
                "actual",
                "budget",
                "delta",
                "relative_delta_percent",
            }
            or not is_safe_report_label(driver.get("group"))
        ):
            raise ValueError("Budgetabweichung enthaelt ungueltige Treiber.")
        _validated_variance_comparison(
            {
                field: driver[field]
                for field in ("actual", "budget", "delta", "relative_delta_percent")
            }
        )
        if driver.get("delta") is None:
            raise ValueError("Budgetabweichung enthaelt ungueltige Treiber.")


def _validated_variance_comparison(comparison: dict[str, Any]) -> None:
    required = {"actual", "budget", "delta", "relative_delta_percent"}
    if set(comparison) != required:
        raise ValueError("Budgetabweichung enthaelt ungueltige Vergleichswerte.")
    for field in ("actual", "budget", "delta", "relative_delta_percent"):
        value = comparison.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or _validated_optional_decimal(value)[0] is False:
            raise ValueError("Budgetabweichung enthaelt ungueltige Vergleichswerte.")


def _consecutive_equal_runs(runs: list[dict[str, Any]]) -> int:
    if not runs:
        return 0
    keys = (
        "input_fingerprint",
        "budget_source_file",
        "budget_input_fingerprint",
        "mapping_version",
        "calculation_version",
        "presentation_version",
        "kpi_result_hash",
        "approval_policy_hash",
    )
    expected = tuple(runs[-1].get(key) for key in keys)
    count = 0
    for run in reversed(runs):
        criteria = run.get("acceptance_criteria")
        if (
            tuple(run.get(key) for key in keys) != expected
            or not _valid_policy_evidence(run)
            or not isinstance(criteria, dict)
            or not all(
                criteria.get(name) is True
                for name in _REQUIRED_REPEATABLE_CRITERIA
            )
        ):
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
    report: dict[str, Any],
    mapping: dict[str, Any] | None,
    *,
    has_budget_variance: bool = False,
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
    mapping_columns = mapping.get("columns")
    expected_labels = (
        {period: mapping_columns.get(period) for period in REPORT_PERIODS}
        if isinstance(mapping_columns, dict)
        else None
    )
    semantics_ok = (
        isinstance(expected_labels, dict)
        and all(is_safe_report_label(label) for label in expected_labels.values())
        and labels_are_unique(list(expected_labels.values()))
        and report.get("period_labels") == expected_labels
        and report.get("sign_convention") == _SIGN_CONVENTION
        and report.get("sign_convention_note") == _SIGN_CONVENTION_NOTE
        and metadata.get("sign_convention") == _SIGN_CONVENTION
        and report.get("availability")
        == (_two_source_availability() if has_budget_variance else pilot_availability())
    )
    return bool(
        counts_ok
        and metadata_ok
        and semantics_ok
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
    if any(
        period not in mapped_source or period not in grouped
        for period in REPORT_PERIODS
    ):
        return False

    for period in REPORT_PERIODS:
        values = [
            normalized_groups[group_name][period]
            for group_name in report_groups
            if report_groups[group_name]["row_count"] > 0
        ]
        expected_total = (
            None
            if any(value is None for value in values)
            else sum(values, Decimal("0"))
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
    values = [groups[ref][period] for ref in refs]
    return None if any(value is None for value in values) else sum(values, Decimal("0"))


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


def _approval_policy_snapshot(root: Path) -> dict[str, Any]:
    """Read the two policy authorities once, bounded and fail-closed."""
    errors: list[str] = []
    config, manifest = _read_policy_bundle(root, errors)

    autonomy_level = "standard"
    require_human_approval = True
    if isinstance(config, dict):
        raw_approval = config.get("require_human_approval", True)
        if raw_approval is True:
            require_human_approval = True
        elif raw_approval is False:
            require_human_approval = False
            errors.append("human_approval_disabled")
        else:
            require_human_approval = False
            errors.append("invalid_require_human_approval")

    approval_terms: list[str] = []
    enabled_external_capabilities: list[str] = []
    if isinstance(manifest, dict):
        raw_autonomy = manifest.get("autonomy_level", "standard")
        if isinstance(raw_autonomy, str) and raw_autonomy == raw_autonomy.strip() and raw_autonomy:
            autonomy_level = raw_autonomy.lower()
        else:
            autonomy_level = "invalid"
            errors.append("invalid_autonomy_level")
        raw_terms = manifest.get("approval_required_for")
        if not isinstance(raw_terms, list) or any(
            not isinstance(term, str) or not term or term != term.strip()
            for term in raw_terms
        ):
            errors.append("invalid_approval_required_for")
        else:
            approval_terms = sorted({" ".join(term.lower().split()) for term in raw_terms})
            if not _REQUIRED_APPROVAL_TERMS <= set(approval_terms):
                errors.append("missing_required_approval_terms")

        permissions = manifest.get("tool_permissions")
        if not isinstance(permissions, dict) or permissions.get("default") != "disabled":
            errors.append("invalid_tool_permissions")
        else:
            enabled = permissions.get("enabled")
            if not isinstance(enabled, list) or any(
                not isinstance(name, str) or not name or name != name.strip()
                for name in enabled
            ):
                errors.append("invalid_enabled_tools")
            else:
                normalized_tools = sorted({name.lower() for name in enabled})
                enabled_external_capabilities = [
                    name for name in normalized_tools if name not in _LOCAL_PILOT_TOOLS
                ]
                if enabled_external_capabilities:
                    errors.append("external_tool_enabled")

    policy_valid = not errors
    return {
        "schema_version": 1,
        "policy_valid": policy_valid,
        "gate_active": policy_valid and autonomy_level != "max" and require_human_approval,
        "autonomy_level": autonomy_level,
        "require_human_approval": require_human_approval,
        "approval_terms": approval_terms,
        "enabled_external_capabilities": enabled_external_capabilities,
        "validation_errors": sorted(set(errors)),
    }


def _read_policy_bundle(
    root: Path, errors: list[str]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Pin and read config+manifest as one stable, bounded filesystem bundle."""
    try:
        lexical_root = Path(os.path.abspath(root))
        if not _policy_path_components_safe(lexical_root):
            raise ValueError
        return (
            _read_policy_bundle_windows(lexical_root)
            if os.name == "nt"
            else _read_policy_bundle_posix(lexical_root)
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        RecursionError,
    ):
        errors.append("invalid_policy_bundle")
        return None, None


def _read_policy_bundle_posix(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    directory_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        root_fd = os.open(root, directory_flags)
        descriptors.append(root_fd)
        project_fd = os.open("project", directory_flags, dir_fd=root_fd)
        descriptors.append(project_fd)
        file_fds = []
        for name in ("config.json", "manifest.json"):
            descriptor = os.open(name, file_flags, dir_fd=project_fd)
            file_fds.append(descriptor)
            descriptors.append(descriptor)
        root_identity = os.fstat(root_fd)
        project_identity = os.fstat(project_fd)
        file_identities = [os.fstat(fd) for fd in file_fds]
        if not stat.S_ISDIR(root_identity.st_mode) or not stat.S_ISDIR(project_identity.st_mode):
            raise ValueError
        if any(not stat.S_ISREG(item.st_mode) for item in file_identities):
            raise ValueError
        raw = [_read_policy_fd_twice(fd, identity) for fd, identity in zip(file_fds, file_identities)]
        if any(
            not _same_policy_file_state(identity, os.fstat(fd))
            for fd, identity in zip(file_fds, file_identities)
        ):
            raise ValueError
        if not _same_policy_identity(root_identity, os.stat(root, follow_symlinks=False)):
            raise ValueError
        if not _same_policy_identity(project_identity, os.stat("project", dir_fd=root_fd, follow_symlinks=False)):
            raise ValueError
        for name, identity in zip(("config.json", "manifest.json"), file_identities):
            if not _same_policy_identity(identity, os.stat(name, dir_fd=project_fd, follow_symlinks=False)):
                raise ValueError
        return _decode_policy_bundle(raw)
    finally:
        for descriptor in reversed(descriptors):
            with contextlib.suppress(OSError):
                os.close(descriptor)


def _read_policy_fd_twice(descriptor: int, identity: os.stat_result) -> bytes:
    if identity.st_size > _MAX_POLICY_BYTES:
        raise ValueError
    os.lseek(descriptor, 0, os.SEEK_SET)
    first = os.read(descriptor, _MAX_POLICY_BYTES + 1)
    middle = os.fstat(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    second = os.read(descriptor, _MAX_POLICY_BYTES + 1)
    after = os.fstat(descriptor)
    if (
        len(first) > _MAX_POLICY_BYTES
        or first != second
        or not _same_policy_file_state(identity, middle)
        or not _same_policy_file_state(identity, after)
        or identity.st_size != len(first)
    ):
        raise ValueError
    return first


def _read_policy_bundle_windows(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    final_path = kernel32.GetFinalPathNameByHandleW
    final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    final_path.restype = wintypes.DWORD
    read_file = kernel32.ReadFile
    read_file.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    read_file.restype = wintypes.BOOL
    set_pointer = kernel32.SetFilePointerEx
    set_pointer.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
    set_pointer.restype = wintypes.BOOL
    get_info = kernel32.GetFileInformationByHandle

    class FileInfo(ctypes.Structure):
        _fields_ = [
            ("attributes", wintypes.DWORD), ("creation_low", wintypes.DWORD),
            ("creation_high", wintypes.DWORD), ("access_low", wintypes.DWORD),
            ("access_high", wintypes.DWORD), ("write_low", wintypes.DWORD),
            ("write_high", wintypes.DWORD), ("volume", wintypes.DWORD),
            ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD),
            ("links", wintypes.DWORD), ("index_high", wintypes.DWORD),
            ("index_low", wintypes.DWORD),
        ]

    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileInfo)]
    get_info.restype = wintypes.BOOL
    invalid = ctypes.c_void_p(-1).value
    handles: list[Any] = []
    project = root / "project"
    paths = [root, project, project / "config.json", project / "manifest.json"]
    try:
        if not _policy_path_components_safe(root) or any(
            _is_link_or_junction(path) for path in paths
        ):
            raise ValueError
        for index, path in enumerate(paths):
            flags = 0x00200000 | (0x02000000 if index < 2 else 0)
            handle = create_file(str(path), 0x80000000, 0x00000001, None, 3, flags, None)
            if handle == invalid or handle is None:
                raise OSError(ctypes.get_last_error(), "CreateFileW failed")
            handles.append(handle)
            if _windows_final_path(final_path, handle) != os.path.normcase(str(path.resolve(strict=True))):
                raise ValueError
        raws = []
        for handle in handles[2:]:
            before = FileInfo()
            if not get_info(handle, ctypes.byref(before)):
                raise OSError(ctypes.get_last_error(), "GetFileInformationByHandle failed")
            size = (before.size_high << 32) | before.size_low
            if size > _MAX_POLICY_BYTES or before.attributes & 0x400:
                raise ValueError
            first = _windows_read_policy_handle(read_file, set_pointer, handle)
            second = _windows_read_policy_handle(read_file, set_pointer, handle)
            after = FileInfo()
            if (
                not get_info(handle, ctypes.byref(after))
                or _windows_file_identity(before) != _windows_file_identity(after)
                or first != second
                or len(first) != size
            ):
                raise ValueError
            raws.append(first)
        if not _policy_path_components_safe(root) or any(
            _is_link_or_junction(path) for path in paths
        ):
            raise ValueError
        return _decode_policy_bundle(raws)
    finally:
        for handle in reversed(handles):
            close_handle(handle)


def _windows_final_path(final_path: Any, handle: Any) -> str:
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    length = final_path(handle, buffer, len(buffer), 0)
    if not length or length >= len(buffer):
        raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(value)


def _windows_file_identity(info: Any) -> tuple[int, ...]:
    return (
        info.attributes,
        info.creation_low,
        info.creation_high,
        info.write_low,
        info.write_high,
        info.volume,
        info.size_high,
        info.size_low,
        info.index_high,
        info.index_low,
    )


def _windows_read_policy_handle(read_file: Any, set_pointer: Any, handle: Any) -> bytes:
    import ctypes
    from ctypes import wintypes

    if not set_pointer(handle, 0, None, 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx failed")
    buffer = ctypes.create_string_buffer(_MAX_POLICY_BYTES + 1)
    read = wintypes.DWORD()
    if not read_file(handle, buffer, len(buffer), ctypes.byref(read), None):
        raise OSError(ctypes.get_last_error(), "ReadFile failed")
    if read.value > _MAX_POLICY_BYTES:
        raise ValueError
    return buffer.raw[: read.value]


def _decode_policy_bundle(raws: list[bytes]) -> tuple[dict[str, Any], dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for raw in raws:
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        values.append(value)
    return values[0], values[1]


def _policy_path_components_safe(root: Path) -> bool:
    current = Path(root.anchor)
    try:
        if not root.is_absolute() or _is_link_or_junction(current):
            return False
        parts = root.parts
        start = 1 if parts and parts[0] == root.anchor else 0
        for part in parts[start:]:
            current /= part
            if _is_link_or_junction(current):
                return False
        return True
    except (OSError, ValueError):
        return False


def _invalidated_policy_snapshot(snapshot: dict[str, Any], error: str) -> dict[str, Any]:
    errors = snapshot.get("validation_errors")
    return {
        **snapshot,
        "policy_valid": False,
        "gate_active": False,
        "validation_errors": sorted({*(errors if isinstance(errors, list) else []), error}),
    }


def _is_link_or_junction(path: Path) -> bool:
    """Reject every name that could redirect this security-sensitive read."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction is not None and is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    except (OSError, ValueError):
        return True


def _same_policy_identity(
    expected: os.stat_result | None, actual: os.stat_result | None
) -> bool:
    return (
        expected is not None
        and actual is not None
        and expected.st_dev == actual.st_dev
        and expected.st_ino == actual.st_ino
        and expected.st_mode == actual.st_mode
    )


def _same_policy_file_state(
    expected: os.stat_result | None, actual: os.stat_result | None
) -> bool:
    return (
        _same_policy_identity(expected, actual)
        and expected is not None
        and actual is not None
        and expected.st_size == actual.st_size
        and expected.st_mtime_ns == actual.st_mtime_ns
        and expected.st_ctime_ns == actual.st_ctime_ns
    )


def _approval_safety_pass(run: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    return (
        snapshot["policy_valid"] is True
        and snapshot["gate_active"] is True
        and _REQUIRED_APPROVAL_TERMS <= set(snapshot["approval_terms"])
        and snapshot["enabled_external_capabilities"] == []
        and run.get("approval_log") == []
        and run.get("external_action_log") == []
        and run.get("external_actions_without_explicit_approval") == 0
    )


def _valid_policy_evidence(run: dict[str, Any]) -> bool:
    snapshot = run.get("approval_policy_snapshot")
    policy_hash = run.get("approval_policy_hash")
    return (
        isinstance(snapshot, dict)
        and isinstance(policy_hash, str)
        and re_full_sha256(policy_hash)
        and hmac.compare_digest(policy_hash, _json_hash(snapshot))
        and snapshot.get("schema_version") == 1
        and snapshot.get("policy_valid") is True
        and snapshot.get("gate_active") is True
        and snapshot.get("enabled_external_capabilities") == []
        and isinstance(snapshot.get("approval_terms"), list)
        and _REQUIRED_APPROVAL_TERMS <= set(snapshot["approval_terms"])
    )


def _management_material_deviations(report: dict[str, Any]) -> list[tuple[str, str]]:
    """Return the five largest report-backed movements in a stable display form."""
    raw_deviations = report.get("material_deviations")
    if not isinstance(raw_deviations, list):
        return []

    parsed: list[tuple[Decimal, str, str]] = []
    for item in raw_deviations:
        if not isinstance(item, dict):
            continue
        account_id = item.get("account_id")
        raw_amount = item.get("month_vs_prior")
        if not isinstance(account_id, str) or not account_id.strip() or isinstance(raw_amount, bool):
            continue
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, ValueError):
            continue
        if not amount.is_finite():
            continue
        amount_text = str(amount.copy_abs()) if amount.is_zero() else str(amount)
        parsed.append(
            (amount, account_id, amount_text if amount < 0 else f"+{amount_text}")
        )

    parsed.sort(key=lambda item: (-abs(item[0]), item[1]))
    return [(account_id, amount) for _, account_id, amount in parsed[:5]]


def _availability_limitations(report: dict[str, Any]) -> list[str]:
    if report.get("availability") == _two_source_availability():
        return [
            "Forderungsalterung: nicht verf\u00fcgbar (in diesem Piloten nicht verarbeitet)."
        ]
    if report.get("availability") != pilot_availability():
        return []
    return [
        "Budgetabweichung: nicht verfügbar (in diesem Piloten nicht verarbeitet).",
        "Forderungsalterung: nicht verfügbar (in diesem Piloten nicht verarbeitet).",
    ]


def _management_variance_drivers(management: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only the compact, aggregate rows intended for human rendering."""
    variance = management.get("variance")
    if not isinstance(variance, dict):
        return []
    drivers = variance.get("top_group_drivers")
    if not isinstance(drivers, list):
        return []
    rows = []
    for driver in drivers:
        if (
            isinstance(driver, dict)
            and isinstance(driver.get("group"), str)
            and driver["group"].strip()
        ):
            rows.append(
                {
                    "group": driver["group"],
                    "actual": driver.get("actual", "-"),
                    "budget": driver.get("budget", "-"),
                    "delta": driver.get("delta", "-"),
                    "relative_delta_percent": driver.get(
                        "relative_delta_percent", "-"
                    ),
                }
            )
    return rows


def _markdown(payload: dict[str, Any]) -> str:
    report = payload["report"]
    management = payload["management"]
    metadata = report.get("report_metadata", {})
    labels = report.get("period_labels", {})
    def markdown_cell(value: Any) -> str:
        return (
            html.escape(str(value), quote=False)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("!", "\\!")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
    lines = [
        "# KMU-Controlling-Report",
        "",
        f"Zeitraum: {metadata.get('period_start', '–')} bis {metadata.get('period_end', '–')}",
        f"Währung: {metadata.get('currency', '–')}",
        "",
        f"Vorzeichenkonvention: {report.get('sign_convention_note', '–')}",
        "",
        "## Management-Fazit",
        "",
        str(management.get("summary", "")),
        "",
        "## Kennzahlen",
        "",
        "| Kennzahl | "
        + " | ".join(markdown_cell(labels.get(period, "–")) for period in REPORT_PERIODS)
        + " |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in report.get("metrics", {}).items():
        if not isinstance(values, dict):
            continue
        lines.append(
            f"| {name} | {values.get('month', '–')} | {values.get('prior', '–')} "
            f"| {values.get('ytd', '–')} | {values.get('ytd_prior', '–')} |"
        )
    variance_drivers = _management_variance_drivers(management)
    if variance_drivers:
        lines.extend(
            [
                "",
                "## Budgetabweichungen",
                "",
                "| Bereich | Ist | Budget | Abweichung | Abweichung % |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        lines.extend(
            "| {group} | {actual} | {budget} | {delta} | {relative} |".format(
                group=markdown_cell(driver["group"]),
                actual=markdown_cell("-" if driver["actual"] is None else driver["actual"]),
                budget=markdown_cell("-" if driver["budget"] is None else driver["budget"]),
                delta=markdown_cell("-" if driver["delta"] is None else driver["delta"]),
                relative=markdown_cell(
                    "-"
                    if driver["relative_delta_percent"] is None
                    else driver["relative_delta_percent"]
                ),
            )
            for driver in variance_drivers
        )
    deviations = _management_material_deviations(report)
    if deviations:
        lines.extend(
            [
                "",
                "## Wesentliche Abweichungen",
                "",
                "| Konto | Monat ggü. Vormonat |",
                "|---|---:|",
            ]
        )
        lines.extend(
            f"| {markdown_cell(account_id)} | {markdown_cell(amount)} |"
            for account_id, amount in deviations
        )
    limitations = _availability_limitations(report)
    if limitations:
        lines.extend(["", "## Verfügbarkeitsgrenzen", ""])
        lines.extend(f"- {limitation}" for limitation in limitations)
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


def render_html(payload: dict[str, Any]) -> str:
    """Render the canonical human management-report view for a payload."""
    return _html(payload)


def _html(payload: dict[str, Any]) -> str:
    """Render a dependency-free management report that is safe to open locally."""
    report = payload["report"]
    management = payload["management"]
    metadata = report.get("report_metadata", {})
    labels = report.get("period_labels", {})
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
    deviation_rows = "".join(
        f"<tr><th>{esc(account_id)}</th><td>{esc(amount)}</td></tr>"
        for account_id, amount in _management_material_deviations(report)
    )
    deviations_section = (
        "<h2>Wesentliche Abweichungen</h2>"
        "<table><thead><tr><th>Konto</th><th>Monat ggü. Vormonat</th>"
        f"</tr></thead><tbody>{deviation_rows}</tbody></table>"
        if deviation_rows
        else ""
    )
    variance_rows = "".join(
        "<tr><th>{group}</th><td>{actual}</td><td>{budget}</td><td>{delta}</td>"
        "<td>{relative}</td></tr>".format(
            group=esc(driver["group"]),
            actual=esc("-" if driver["actual"] is None else driver["actual"]),
            budget=esc("-" if driver["budget"] is None else driver["budget"]),
            delta=esc("-" if driver["delta"] is None else driver["delta"]),
            relative=esc(
                "-"
                if driver["relative_delta_percent"] is None
                else driver["relative_delta_percent"]
            ),
        )
        for driver in _management_variance_drivers(management)
    )
    variance_section = (
        "<h2>Budgetabweichungen</h2><table><thead><tr><th>Bereich</th>"
        "<th>Ist</th><th>Budget</th><th>Abweichung</th><th>Abweichung %</th>"
        f"</tr></thead><tbody>{variance_rows}</tbody></table>"
        if variance_rows
        else ""
    )
    availability_section = "".join(
        f"<li>{esc(limitation)}</li>"
        for limitation in _availability_limitations(report)
    )
    if availability_section:
        availability_section = (
            "<section><h2>Verfügbarkeitsgrenzen</h2><ul>"
            f"{availability_section}</ul></section>"
        )
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
<p class="meta">Vorzeichenkonvention: {esc(report.get('sign_convention_note', '–'))}</p>
<table><thead><tr><th>Kennzahl</th>{''.join(f'<th>{esc(labels.get(period, "–"))}</th>' for period in REPORT_PERIODS)}</tr></thead><tbody>{''.join(metric_rows)}</tbody></table>
{variance_section}
{deviations_section}
{availability_section}
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
    _atomic_bytes(path, text.encode("utf-8"))


def _atomic_bytes(path: Path, data: bytes) -> None:
    """Atomically replace an artifact after syncing its complete byte payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        # Directory fsync is unsupported on Windows and some filesystems; the
        # data file has already been synced, so lack of directory support is
        # deliberately best-effort rather than a portability failure.
        with contextlib.suppress(OSError):
            directory_fd = os.open(
                path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_BINARY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _iso(value: datetime) -> str:
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
