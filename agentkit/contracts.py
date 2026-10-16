"""Validated boundaries for configuration, model decisions and worker reports."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
LIBRARY = ROOT / "library"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContractError(ValueError):
    """Invalid or out-of-scope input; do not execute it."""


def slug(value: str) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value) or len(value) > 64:
        raise ContractError("Use 1–64 lowercase letters, digits and single hyphens.")
    return value


def schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


def validate(value: object, name: str) -> None:
    # Read-only path checks also import this module under isolated Python.
    # Schema dependencies are needed only when validating a model/config value.
    from jsonschema import Draft202012Validator

    errors = sorted(
        Draft202012Validator(schema(name)).iter_errors(value), key=lambda e: str(e.path)
    )
    if errors:
        first = errors[0]
        raise ContractError(
            f"{name}: {'.'.join(map(str, first.path)) or '$'}: {first.message}"
        )


def inside(root: Path, relative: str) -> Path:
    """Reject traversal, absolute paths and symlinks escaping the selected root."""
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ContractError("Expected a nonempty relative path.")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ContractError(f"Path escapes its root: {relative}")
    return target


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))
