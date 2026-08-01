"""UI-neutral, atomic provisioning for local preset instances.

The factory deliberately has no dependency on the CLI or runtime.  It is safe
for a local service to call repeatedly: a matching, fully validated instance is
returned unchanged; an incomplete or foreign tree is never repaired in place.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Callable


_REQUIRED_PROJECT_FILES = (
    ("SOUL.md", "Identität (SOUL.md)"),
    ("config.json", "Konfiguration (config.json)"),
    ("manifest.json", "Manifest (manifest.json)"),
    ("workflows/main.md", "Haupt-Workflow (workflows/main.md)"),
    ("connectors.yaml", "Datenquellen (connectors.yaml)"),
    ("steering-examples.json", "Planner-Beispiele (steering-examples.json)"),
)
_MUTABLE_TOP_LEVEL_DIRECTORIES = ("inbox", "data", "imports", "state", "artifacts")
ProjectWriter = Callable[[Path, str, str], None]
_LOCK_WAIT_SECONDS = 30.0


class InstanceProvisionError(RuntimeError):
    """Provisioning could not safely publish or reuse an instance."""


@dataclass(frozen=True)
class InstanceValidationReport:
    passed: tuple[str, ...]
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


def _canonical_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("instance identifiers must be strings")
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "agent"


def canonical_instance_ids(tenant_id: str, agent_id: str) -> tuple[str, str]:
    """Return the canonical tenant and agent directory identifiers."""
    return _canonical_id(tenant_id), _canonical_id(agent_id)


def instance_identity(instance: Path) -> tuple[str, str]:
    """Read the canonical identity encoded in an ``<tenant>/<agent>`` path."""
    path = Path(instance)
    if len(path.parts) < 2:
        raise ValueError("Instanzpfad muss <tenant>/<agent> enthalten")
    return path.parent.name, path.name


def _deep_merge(base: dict[object, object], overlay: dict[object, object]) -> dict[object, object]:
    merged = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            merged[key] = _deep_merge(dict(existing), dict(value))
        else:
            merged[key] = value
    return merged


def _is_link_or_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, FileNotFoundError):
        attributes = 0
    return path.is_symlink() or bool(attributes & 0x400)


def _safe_project_reference(project_dir: Path, value: object) -> Path | None:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
    ):
        return None
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    candidate = project_dir.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=False).relative_to(project_dir.resolve(strict=True))
    except (OSError, ValueError):
        return None
    current = candidate
    while current != project_dir:
        if _is_link_or_reparse(current):
            return None
        current = current.parent
    return candidate


def apply_preset(instance: Path, preset: str, presets_root: Path) -> None:
    """Overlay a packaged preset while retaining the generated identity."""
    preset_dir = Path(presets_root) / preset
    if not preset_dir.is_dir():
        raise ValueError(f"Unbekanntes Preset: {preset}")
    project_dir = Path(instance) / "project"

    for filename in ("config.json", "manifest.json"):
        generated = json.loads((project_dir / filename).read_text(encoding="utf-8"))
        overlay = json.loads((preset_dir / filename).read_text(encoding="utf-8"))
        if not isinstance(generated, dict) or not isinstance(overlay, dict):
            raise ValueError(f"Preset {preset} contains an invalid {filename}")
        identity = generated.get("instance")
        merged = _deep_merge(generated, overlay)
        if identity is not None:
            merged["instance"] = identity
        (project_dir / filename).write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    for source in preset_dir.rglob("*"):
        if not source.is_file() or source.name in {"config.json", "manifest.json"}:
            continue
        destination = project_dir / source.relative_to(preset_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    if preset == "kmu-controlling":
        for directory in _MUTABLE_TOP_LEVEL_DIRECTORIES:
            (Path(instance) / directory).mkdir(exist_ok=True)


def _default_kmu_writer(instance: Path, tenant_id: str, agent_id: str) -> None:
    """Write only the generic envelope; the packaged preset supplies its content."""
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


def validate_instance(
    instance: Path, *, _expected_identity: tuple[str, str] | None = None
) -> InstanceValidationReport:
    """Validate the published structure and path-bound instance identity offline."""
    instance = Path(instance)
    if _is_link_or_reparse(instance):
        return InstanceValidationReport(
            (), ("Instanzpfad darf kein Link oder Reparse Point sein.",)
        )
    project_dir = instance / "project"
    if _is_link_or_reparse(project_dir):
        return InstanceValidationReport(
            (), ("Projektpfad darf kein Link oder Reparse Point sein.",)
        )
    passed: list[str] = []
    problems: list[str] = []
    for relative, label in _REQUIRED_PROJECT_FILES:
        path = _safe_project_reference(project_dir, relative)
        try:
            present = bool(
                path is not None
                and path.is_file()
                and path.read_text(encoding="utf-8").strip()
            )
        except (OSError, UnicodeDecodeError):
            present = False
        if present:
            passed.append(label)
        else:
            problems.append(f"{label}: Datei fehlt oder ist leer ({relative})")

    documents: dict[str, dict[object, object]] = {}
    for relative in ("config.json", "manifest.json", "steering-examples.json"):
        path = _safe_project_reference(project_dir, relative)
        if path is None or not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            problems.append(f"{relative}: ungültiges JSON — {exc}")
            continue
        passed.append(f"{relative} ist gültiges JSON")
        if isinstance(document, dict):
            documents[relative] = document

    manifest = documents.get("manifest.json")
    if manifest is not None:
        connectors = manifest.get("connectors")
        config_file = connectors.get("config_file") if isinstance(connectors, dict) else None
        if config_file:
            connector_path = _safe_project_reference(project_dir, config_file)
            if connector_path is not None and connector_path.is_file():
                passed.append(f"Connector-Datei referenziert & vorhanden ({config_file})")
            else:
                problems.append(
                    f"Manifest verweist auf fehlende/unsichere Connector-Datei: {config_file}"
                )
        skills = manifest.get("skills")
        if isinstance(skills, list):
            for slug in skills:
                skill_file = _safe_project_reference(
                    project_dir, f"skills/{slug}/SKILL.md"
                )
                try:
                    skill_present = bool(
                        skill_file is not None
                        and skill_file.is_file()
                        and skill_file.read_text(encoding="utf-8").strip()
                    )
                except (OSError, UnicodeDecodeError):
                    skill_present = False
                if skill_present:
                    passed.append(f"Skill vorhanden: {slug}")
                else:
                    problems.append(f"Manifest listet Skill '{slug}', aber skills/{slug}/SKILL.md fehlt")

    try:
        tenant_id, agent_id = _expected_identity or instance_identity(instance)
        expected = {"tenant_id": tenant_id, "agent_id": agent_id}
        config_identity = documents.get("config.json", {}).get("instance")
        manifest_identity = documents.get("manifest.json", {}).get("instance")
        if config_identity == expected and manifest_identity == expected:
            passed.append(f"Instanzidentität bestätigt: {tenant_id}/{agent_id}")
        else:
            problems.append(
                "Instanzidentität stimmt nicht: "
                f"erwartet {expected}, erhalten config={config_identity}, manifest={manifest_identity}"
            )
    except ValueError as exc:
        problems.append(f"Instanzidentität konnte nicht geprüft werden: {exc}")
    return InstanceValidationReport(tuple(passed), tuple(problems))


@contextlib.contextmanager
def _provision_lock(output_root: Path, target: Path):
    """Use a stable lock file outside the target that works across processes."""
    lock_root = output_root / ".instance-factory-locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    if _is_link_or_reparse(lock_root):
        raise InstanceProvisionError("instance factory lock root is redirected")
    digest = hashlib.sha256(str(target.absolute()).encode("utf-8")).hexdigest()
    lock_path = lock_root / f"{digest}.lock"
    if lock_path.is_symlink():
        raise InstanceProvisionError("instance factory lock must not be a symlink")
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
                raise InstanceProvisionError("instance provisioning lock timed out")
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
                raise InstanceProvisionError("instance provisioning lock timed out")
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]


def _discard_own_staging(staging: Path) -> None:
    """Remove only a uniquely named staging tree, never a computed target."""
    if staging.exists():
        shutil.rmtree(staging)


def provision_instance(
    output_root: Path,
    tenant_id: str,
    agent_id: str,
    preset: str | None = "kmu-controlling",
    *,
    _project_writer: ProjectWriter | None = None,
    _presets_root: Path | None = None,
) -> Path:
    """Atomically provision or safely reuse one local instance.

    The four positional/public arguments form the service API.  A matching
    existing validated instance is returned unchanged; an existing invalid tree
    raises :class:`InstanceProvisionError` and is deliberately left untouched.
    """
    canonical_tenant, canonical_agent = canonical_instance_ids(tenant_id, agent_id)
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / canonical_tenant / canonical_agent
    presets_root = _presets_root or Path(__file__).resolve().parent.parent / "presets"
    if preset not in {None, "kmu-controlling"}:
        raise InstanceProvisionError(f"Unbekanntes Preset: {preset}")

    with _provision_lock(output_root, target):
        if _is_link_or_reparse(target.parent) or _is_link_or_reparse(target):
            raise InstanceProvisionError(
                "instance target must not use links or reparse points"
            )
        try:
            target.parent.resolve(strict=False).relative_to(output_root)
            target.resolve(strict=False).relative_to(output_root)
        except ValueError as exc:
            raise InstanceProvisionError(
                "instance target escaped the output root"
            ) from exc
        if target.exists():
            report = validate_instance(target)
            if report.ok:
                return target
            raise InstanceProvisionError(
                f"instance already exists but is invalid and was left untouched: {target}"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        if _is_link_or_reparse(target.parent):
            raise InstanceProvisionError(
                "instance tenant directory must not be redirected"
            )
        staging = target.parent / f".{canonical_agent}.staging-{uuid.uuid4().hex}"
        try:
            writer = _project_writer or _default_kmu_writer
            writer(staging, canonical_tenant, canonical_agent)
            if preset is not None:
                apply_preset(staging, preset, presets_root)
            report = validate_instance(
                staging, _expected_identity=(canonical_tenant, canonical_agent)
            )
            if not report.ok:
                raise InstanceProvisionError(
                    "staged instance failed validation: " + "; ".join(report.problems)
                )
            try:
                os.replace(staging, target)
            except FileExistsError:
                report = validate_instance(target)
                if report.ok:
                    return target
                raise InstanceProvisionError(
                    f"instance target appeared but is invalid and was left untouched: {target}"
                )
            return target
        finally:
            _discard_own_staging(staging)
