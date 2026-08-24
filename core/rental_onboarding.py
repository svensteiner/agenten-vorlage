"""Fail-closed snapshots and onboarding for provisioned rental instances.

Excel uploads are copied byte-for-byte (formulas untouched). Starter files
reuse the packaged kmu-controlling account-mapping example plus small CSVs.
Nothing walks outside the opened instance root.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from core.controlling.tools import ControllingComputeTool


_EXCEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.xlsx$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LIST_ROOTS = ("artifacts", "inbox", "data", "imports")
_MAX_LISTED = 40
_MAX_LIST_BYTES = 8 * 1024 * 1024
_MAX_SOUL_BYTES = 16 * 1024
_MAX_EXCEL_BYTES = 300 * 1024
_MAX_MAPPING_BYTES = 64 * 1024
_MAX_NAME = 120

STARTER_KONTEN_REL = "inbox/actuals/starter-konten.csv"
STARTER_FORECAST_REL = "inbox/forecast/starter-forecast.csv"
STARTER_REPORT_REL = "artifacts/starter-bericht.md"
MAPPING_REL = "project/pilot/account-mapping.json"
DROP_DIR_REL = "imports/actuals"

STARTER_KONTEN_CSV = (
    "Konto,Bezeichnung,Monat,Vormonat,YTD,YTD Vorjahr\n"
    "4000,Umsatzerloese,120000,110000,720000,680000\n"
    "5000,Materialaufwand,48000,45000,290000,270000\n"
    "6000,Personalaufwand,36000,35000,216000,210000\n"
    "6200,Abschreibungen,4000,4000,24000,24000\n"
    "8000,Zinsaufwand,800,800,4800,5000\n"
    "1200,Forderungen aus Lieferungen,22000,20000,22000,18000\n"
    "1000,Bank,15000,14000,15000,12000\n"
    "1600,Verbindlichkeiten aus Lieferungen,18000,17000,18000,16000\n"
)
STARTER_FORECAST_CSV = (
    "Periode,Kategorie,Betrag,Waehrung\n"
    "2026-07,Umsatzerloese,122000,EUR\n"
    "2026-07,Materialaufwand,49000,EUR\n"
    "2026-08,Umsatzerloese,125000,EUR\n"
    "2026-08,Materialaufwand,50000,EUR\n"
)
STARTER_REPORT_MD = (
    "# Starter-Bericht\n"
    "\n"
    "Musterkonten, Forecast und Konten-Mapping liegen in dieser Instanz.\n"
    "Excel-Formeln werden nicht veraendert. Eigene Dateien nach\n"
    "`inbox/actuals/` oder `imports/actuals/` legen.\n"
)


class OnboardingError(RuntimeError):
    """Base class for rental onboarding errors."""


class OnboardingValidationError(OnboardingError):
    """Caller supplied an invalid onboarding request."""


class OnboardingConflict(OnboardingError):
    """Onboarding would overwrite or escape the instance."""


def _presets_root() -> Path:
    return Path(__file__).resolve().parent.parent / "presets"


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, FileNotFoundError):
        return False
    return bool(attributes & 0x400)


def _assert_inside(path: Path, root: Path) -> Path:
    root = root.resolve(strict=True)
    current = path
    while current != root:
        if current.is_symlink() or _is_reparse_point(current):
            raise OnboardingConflict("Links sind in Instanzpfaden nicht erlaubt.")
        if current == current.parent:
            raise OnboardingConflict("Instanzpfad ist ungueltig.")
        current = current.parent
    try:
        resolved = path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise OnboardingConflict("Instanzpfad ist ungueltig.") from exc
    if ".." in resolved.parts:
        raise OnboardingConflict("Instanzpfad ist ungueltig.")
    return path


def _relative_parts(relative: str) -> tuple[str, ...]:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
    ):
        raise OnboardingValidationError("Dateiname ist ungueltig.")
    posix = PurePosixPath(relative)
    if (
        posix.is_absolute()
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise OnboardingValidationError("Dateiname ist ungueltig.")
    if any(len(part) > _MAX_NAME for part in posix.parts):
        raise OnboardingValidationError("Dateiname ist ungueltig.")
    return posix.parts


def _safe_child(instance: Path, relative: str) -> Path:
    parts = _relative_parts(relative)
    if parts[0] not in {"artifacts", "inbox", "data", "imports", "project", "state"}:
        raise OnboardingConflict("Ziel liegt ausserhalb der Instanzbereiche.")
    candidate = instance.joinpath(*parts)
    _assert_inside(candidate.parent if candidate.parent != instance else candidate, instance)
    _assert_inside(candidate, instance)
    return candidate


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
            import time

            time.sleep(0.02 * (attempt + 1))


def _atomic_write(destination: Path, raw: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _assert_inside(destination.parent, destination.parent.resolve(strict=True))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _replace_with_retry(temporary, destination)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_limited(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink() or _is_reparse_point(path) or not path.is_file():
        raise OnboardingConflict("Datei ist unsicher oder fehlt.")
    size = path.stat().st_size
    if size > max_bytes:
        raise OnboardingConflict("Datei ist zu gross.")
    return path.read_bytes()


def _soul_title(instance: Path) -> str | None:
    path = instance / "project" / "SOUL.md"
    try:
        _assert_inside(path, instance)
    except OnboardingError:
        return None
    if path.is_symlink() or _is_reparse_point(path) or not path.is_file():
        return None
    try:
        if path.stat().st_size > _MAX_SOUL_BYTES:
            return None
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("# ").strip()[:80]
    return None


def _list_area(instance: Path, area: str) -> list[dict[str, Any]]:
    root = instance / area
    if not root.exists():
        return []
    if root.is_symlink() or _is_reparse_point(root) or not root.is_dir():
        return []
    try:
        _assert_inside(root, instance)
    except OnboardingError:
        return []
    items: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        if current.is_symlink() or _is_reparse_point(current):
            dirnames[:] = []
            continue
        try:
            _assert_inside(current, instance)
        except OnboardingError:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in {".", ".."} and not name.startswith(".")
        )
        for name in sorted(filenames):
            if name.startswith(".") or len(name) > _MAX_NAME:
                continue
            file_path = current / name
            if file_path.is_symlink() or _is_reparse_point(file_path) or not file_path.is_file():
                continue
            try:
                relative = file_path.resolve(strict=True).relative_to(
                    instance.resolve(strict=True)
                )
            except (OSError, ValueError):
                continue
            posix = relative.as_posix()
            if (
                ".." in relative.parts
                or relative.parts[0] != area
                or "\\" in posix
                or len(posix) > 200
            ):
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > _MAX_LIST_BYTES:
                continue
            items.append({"path": posix, "bytes": size})
            if len(items) >= _MAX_LISTED:
                return items
    return items


def _mapping_present(instance: Path) -> bool:
    path = instance / "project" / "pilot" / "account-mapping.json"
    try:
        _assert_inside(path, instance)
    except OnboardingError:
        return False
    return path.is_file() and not path.is_symlink() and not _is_reparse_point(path)


def snapshot_instance(
    instance: Path,
    rental: dict[str, Any],
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a fail-closed public view of one opened instance."""
    files: list[dict[str, Any]] = []
    for area in _LIST_ROOTS:
        remaining = _MAX_LISTED - len(files)
        if remaining <= 0:
            break
        files.extend(_list_area(instance, area)[:remaining])
    has_actuals = any(
        item["path"].startswith("inbox/actuals/")
        or item["path"].startswith("imports/actuals/")
        or item["path"].startswith("data/actuals/")
        for item in files
    )
    has_forecast = any(item["path"].startswith("inbox/forecast/") for item in files)
    has_mapping = _mapping_present(instance)
    agent_id = rental.get("agent_id")
    supported = agent_id == "controlling"
    if not supported:
        status = "unsupported"
        mode: str | None = None
    elif has_mapping and has_actuals:
        status = "ready"
        if any(item["path"] == STARTER_KONTEN_REL for item in files):
            mode = "starter"
        else:
            mode = "excel"
    else:
        status = "empty"
        mode = None
    preset_id = None
    label = agent_id
    if isinstance(catalog, dict):
        preset_id = catalog.get("preset_id")
        label = catalog.get("label") or agent_id
    artifacts = [item for item in files if item["path"].startswith("artifacts/")]
    inputs = [
        item
        for item in files
        if item["path"].startswith(("inbox/", "data/", "imports/"))
    ]
    return {
        "rental_id": rental["rental_id"],
        "tenant_id": rental["tenant_id"],
        "agent_id": agent_id,
        "display_name": rental["display_name"],
        "instance_path": rental["instance_path"],
        "preset_id": preset_id,
        "label": label,
        "soul_title": _soul_title(instance),
        "artifacts": artifacts,
        "inputs": inputs,
        "onboarding": {
            "supported": supported,
            "status": status,
            "mode": mode,
            "has_mapping": has_mapping,
            "has_actuals": has_actuals,
            "has_forecast": has_forecast,
        },
    }


def _mapping_example_bytes() -> bytes:
    source = (
        _presets_root() / "kmu-controlling" / "pilot" / "account-mapping.example.json"
    )
    if not source.is_file() or source.is_symlink():
        raise OnboardingConflict("Konten-Mapping-Vorlage fehlt.")
    raw = source.read_bytes()
    if not raw or len(raw) > _MAX_MAPPING_BYTES:
        raise OnboardingConflict("Konten-Mapping-Vorlage ist ungueltig.")
    json.loads(raw.decode("utf-8"))
    return raw


def _write_if_absent_or_same(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.is_symlink() or _is_reparse_point(path) or not path.is_file():
            raise OnboardingConflict("Zieldatei ist unsicher.")
        existing = path.read_bytes()
        if existing == raw:
            return
        raise OnboardingConflict("Zieldatei existiert bereits mit anderem Inhalt.")
    _atomic_write(path, raw)


def apply_starter(instance: Path) -> None:
    """Seed mapping, sample accounts, forecast, report, and CSV drop folder."""
    mapping_path = _safe_child(instance, MAPPING_REL)
    _write_if_absent_or_same(mapping_path, _mapping_example_bytes())
    _write_if_absent_or_same(
        _safe_child(instance, STARTER_KONTEN_REL),
        STARTER_KONTEN_CSV.encode("utf-8"),
    )
    _write_if_absent_or_same(
        _safe_child(instance, STARTER_FORECAST_REL),
        STARTER_FORECAST_CSV.encode("utf-8"),
    )
    _write_if_absent_or_same(
        _safe_child(instance, STARTER_REPORT_REL),
        STARTER_REPORT_MD.encode("utf-8"),
    )
    drop = _safe_child(instance, DROP_DIR_REL)
    drop.mkdir(parents=True, exist_ok=True)
    _assert_inside(drop, instance)


def _validate_excel_name(filename: str) -> str:
    if not isinstance(filename, str) or not _EXCEL_NAME.fullmatch(filename):
        raise OnboardingValidationError("Excel-Dateiname ist ungueltig.")
    lowered = filename.lower()
    if ".." in filename or filename.startswith(".") or "/" in filename:
        raise OnboardingValidationError("Excel-Dateiname ist ungueltig.")
    if not lowered.endswith(".xlsx"):
        raise OnboardingValidationError("Nur XLSX ist erlaubt.")
    return filename


def apply_excel(instance: Path, filename: str, raw: bytes) -> None:
    """Copy an XLSX into inbox/actuals without rewriting cells or formulas."""
    filename = _validate_excel_name(filename)
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise OnboardingValidationError("Excel-Datei fehlt.")
    payload = bytes(raw)
    if len(payload) > _MAX_EXCEL_BYTES:
        raise OnboardingValidationError("Excel-Datei ist zu gross.")
    try:
        ControllingComputeTool._validate_xlsx_archive(
            Path(filename), raw=payload
        )
    except ValueError as exc:
        raise OnboardingValidationError(str(exc)) from exc
    mapping_path = _safe_child(instance, MAPPING_REL)
    if not mapping_path.exists():
        _write_if_absent_or_same(mapping_path, _mapping_example_bytes())
    target = _safe_child(instance, f"inbox/actuals/{filename}")
    _write_if_absent_or_same(target, payload)
    drop = _safe_child(instance, DROP_DIR_REL)
    drop.mkdir(parents=True, exist_ok=True)
