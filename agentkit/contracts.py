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


class CompletedReportRejected(ContractError):
    """A backend returned normally, but its report failed host-side validation.

    This signal is intentionally distinct from transport and timeout errors,
    whose outcome may be unknown. Its attached observation is allowlisted,
    bounded metadata only; report text and arbitrary provider values are never
    retained here.
    """

    REASONS = frozenset({"report_schema_invalid", "artifact_path_invalid"})
    REPORT_TYPES = frozenset({
        "object", "array", "string", "number", "boolean", "null", "unserializable",
    })

    def __init__(self, reason: str, observation: object = None):
        if type(reason) is not str or reason not in self.REASONS:
            raise ValueError("Unknown completed-report rejection reason.")
        self.reason = reason
        self.observation = self._safe_metadata(observation)
        super().__init__(f"Codex returned a report rejected by host validation ({reason}).")

    @classmethod
    def _safe_metadata(cls, observation: object) -> dict[str, object]:
        value = observation if type(observation) is dict else {}
        report_type = value.get("report_type")
        report_sha256 = value.get("report_sha256")
        report_bytes = value.get("report_bytes")
        artifact_count = value.get("artifact_count")
        artifact_index = value.get("artifact_index")
        safe = {
            "report_type": (report_type if type(report_type) is str
                            and report_type in cls.REPORT_TYPES else "unserializable"),
            "report_sha256": report_sha256 if _is_sha256(report_sha256) else None,
            "report_bytes": (report_bytes if type(report_bytes) is int
                             and 0 <= report_bytes <= 200_000 else None),
            "artifact_count": (artifact_count if type(artifact_count) is int
                               and 0 <= artifact_count <= 40 else None),
        }
        if type(artifact_index) is int and 0 <= artifact_index < 40:
            safe["artifact_index"] = artifact_index
        return safe

    def safe_observation(self) -> dict[str, object]:
        """Return a fresh JSON-safe projection suitable for the run checkpoint."""
        reason = self.reason if type(self.reason) is str and self.reason in self.REASONS else "report_schema_invalid"
        return {"reason": reason, **self._safe_metadata(self.observation)}


def _is_sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


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
