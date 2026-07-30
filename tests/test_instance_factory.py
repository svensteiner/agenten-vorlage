"""Contract tests for the UI-neutral local instance factory."""

from __future__ import annotations

import ast
import hashlib
import json
import multiprocessing
import traceback
from pathlib import Path

import pytest

from core.instance_factory import (
    InstanceProvisionError,
    canonical_instance_ids,
    provision_instance,
    validate_instance,
)


def _provision_in_child(output_root: str, queue: multiprocessing.Queue[str]) -> None:
    """Spawn target: exercise the file lock from an independent interpreter."""
    try:
        path = provision_instance(Path(output_root), "Acme GmbH", "Controlling")
        queue.put(str(path))
    except Exception as exc:  # pragma: no cover - asserted in parent process
        queue.put(f"ERROR: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")


def test_canonical_instance_ids_are_stable_and_path_safe() -> None:
    assert canonical_instance_ids(" Acme GmbH ", " Finance Pilot ") == (
        "acme-gmbh",
        "finance-pilot",
    )


def test_provisioned_kmu_instance_is_complete_and_valid(tmp_path: Path) -> None:
    instance = provision_instance(tmp_path, "Acme GmbH", "Controlling")

    assert instance == tmp_path / "acme-gmbh" / "controlling"
    assert validate_instance(instance).ok
    assert all(
        (instance / relative).is_dir()
        for relative in ("inbox", "data", "imports", "state", "artifacts")
    )


def test_repeated_provision_is_idempotent_for_a_valid_instance(tmp_path: Path) -> None:
    first = provision_instance(tmp_path, "acme", "controlling")
    marker = first / "state" / "service-marker.txt"
    marker.write_text("kept", encoding="utf-8")

    second = provision_instance(tmp_path, "acme", "controlling")

    assert second == first
    assert marker.read_text(encoding="utf-8") == "kept"


def test_existing_partial_target_is_refused_without_deletion(tmp_path: Path) -> None:
    target = tmp_path / "acme" / "controlling"
    target.mkdir(parents=True)
    sentinel = target / "keep.txt"
    sentinel.write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(InstanceProvisionError, match="already exists"):
        provision_instance(tmp_path, "acme", "controlling")

    assert sentinel.read_text(encoding="utf-8") == "do not overwrite"


def test_concurrent_provisioning_publishes_one_valid_complete_instance(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    children = [
        context.Process(target=_provision_in_child, args=(str(tmp_path), queue))
        for _ in range(2)
    ]
    for child in children:
        child.start()
    results = [queue.get(timeout=20) for _ in children]
    for child in children:
        child.join(timeout=20)
        assert child.exitcode == 0

    target = tmp_path / "acme-gmbh" / "controlling"
    assert results == [str(target)] * 2
    assert validate_instance(target).ok


def test_provisioning_recovers_a_zero_byte_stable_lock(tmp_path: Path) -> None:
    target = tmp_path / "acme" / "controlling"
    digest = hashlib.sha256(str(target.absolute()).encode("utf-8")).hexdigest()
    lock = tmp_path / ".instance-factory-locks" / f"{digest}.lock"
    lock.parent.mkdir()
    lock.write_bytes(b"")

    instance = provision_instance(tmp_path, "acme", "controlling")

    assert instance == target
    assert lock.read_bytes() == b"0"


def test_provisioning_rejects_redirected_tenant_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    tenant = tmp_path / "acme"
    try:
        tenant.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable for this test account")

    with pytest.raises(InstanceProvisionError, match="links|reparse"):
        provision_instance(tmp_path, "acme", "controlling")

    assert not (outside / "controlling").exists()


def test_validation_detects_instance_identity_mismatch(tmp_path: Path) -> None:
    instance = provision_instance(tmp_path, "acme", "controlling")
    config_path = instance / "project" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["instance"]["agent_id"] = "other"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    report = validate_instance(instance)

    assert not report.ok
    assert any("agent_id" in problem for problem in report.problems)


def test_validation_reports_non_utf8_required_file_without_crashing(
    tmp_path: Path,
) -> None:
    instance = provision_instance(tmp_path, "acme", "controlling")
    (instance / "project" / "SOUL.md").write_bytes(b"\xff")

    report = validate_instance(instance)

    assert not report.ok
    assert any("SOUL.md" in problem for problem in report.problems)


def test_validation_rejects_required_file_redirected_outside_project(
    tmp_path: Path,
) -> None:
    instance = provision_instance(tmp_path, "acme", "controlling")
    soul = instance / "project" / "SOUL.md"
    outside = tmp_path / "outside-soul.md"
    outside.write_text(soul.read_text(encoding="utf-8"), encoding="utf-8")
    soul.unlink()
    try:
        soul.symlink_to(outside)
    except OSError:
        pytest.skip("File symlinks unavailable for this test account")

    report = validate_instance(instance)

    assert not report.ok
    assert any("SOUL.md" in problem for problem in report.problems)


@pytest.mark.parametrize(
    ("field", "unsafe_reference"),
    (
        ("connector", "../../outside.yaml"),
        ("skill", "../../outside"),
    ),
)
def test_validation_rejects_manifest_references_outside_project(
    tmp_path: Path, field: str, unsafe_reference: str
) -> None:
    instance = provision_instance(tmp_path, "acme", "controlling")
    manifest_path = instance / "project" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if field == "connector":
        manifest["connectors"] = {"config_file": unsafe_reference}
    else:
        manifest["skills"] = [unsafe_reference]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_instance(instance)

    assert not report.ok
    assert any("unsichere" in problem or "Skill" in problem for problem in report.problems)


def test_core_factory_has_no_ui_or_runtime_import_boundary() -> None:
    source = Path(__file__).resolve().parent.parent / "core" / "instance_factory.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert not ({"agent_cli", "agent", "brain"} & imported)
