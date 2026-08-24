"""Schema-locked controlling report (Pydantic models, extra=forbid).

Required keys are grounded in expected-results.json and the compute/artifact
payloads produced by ControllingComputeTool / persist_report_artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReportMetadataModel(StrictModel):
    period_start: str
    period_end: str
    currency: str
    sign_convention: str
    row_identifier: str | list[str]


class GoldenReconciliationModel(StrictModel):
    source_account_count: int
    mapped_account_count: int
    ignored_account_count: int


class GoldenControllingReport(StrictModel):
    """Matches presets/.../expected-results.json."""

    schema_version: int
    source: str
    currency: str
    period: str
    report_metadata: ReportMetadataModel
    metrics: dict[str, str]
    reconciliation: GoldenReconciliationModel


class ComputeReconciliationModel(StrictModel):
    source_account_count: int
    mapped_account_count: int
    ignored_account_count: int
    mapped_source_period_totals: dict[str, Any] | None = None
    grouped_period_totals: dict[str, Any] | None = None
    # Present on privacy-oriented narrative test fixtures, not on golden JSON.
    customer_id: Any | None = None


class ProvenanceModel(StrictModel):
    input_fingerprint: str
    mapping_version: str
    calculation_version: str


class ComputeControllingReport(StrictModel):
    """Matches ControllingComputeTool kmu_report JSON (and sanitized artifact.report)."""

    source: str
    method: str
    metrics: dict[str, dict[str, Any]]
    reconciliation: ComputeReconciliationModel
    report_metadata: ReportMetadataModel | None = None
    period_labels: dict[str, Any] | None = None
    sign_convention: str | None = None
    sign_convention_note: str | None = None
    groups: dict[str, Any] | None = None
    material_deviations: Any | None = None
    availability: dict[str, Any] | None = None
    provenance: ProvenanceModel | None = None
    schema_version: int | None = None
    currency: str | None = None
    period: str | None = None
    # Fixture-only keys used by narrative leak tests; extra product keys still fail.
    raw_rows: Any | None = None
    customer_id: Any | None = None
    file_hash: Any | None = None


ComputeReportModel = ComputeControllingReport


class ControllingArtifact(StrictModel):
    """Matches latest-controlling-report.json envelope."""

    schema_version: int
    report: ComputeControllingReport
    acceptance: dict[str, Any]
    generated_at: str | None = None
    management: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None


GOLDEN_METRIC_KEYS = (
    "revenue_month",
    "material_month",
    "personnel_month",
    "ebitda_month",
    "egt_month",
    "egt_prior",
    "egt_ytd",
    "egt_ytd_prior",
    "receivables_month",
    "liquidity_month",
    "payables_month",
)


@dataclass(frozen=True)
class ReportSchemaResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_controlling_report(data: Any) -> ReportSchemaResult:
    """Return ok / errors. Accepts golden expected-results, compute report, or artifact."""
    if not isinstance(data, dict):
        return ReportSchemaResult(ok=False, errors=["report must be a JSON object"])
    try:
        if _looks_like_artifact(data):
            ControllingArtifact.model_validate(data)
        elif _looks_like_golden(data):
            GoldenControllingReport.model_validate(data)
        else:
            ComputeControllingReport.model_validate(data)
    except ValidationError as exc:
        return ReportSchemaResult(ok=False, errors=_format_errors(exc))
    return ReportSchemaResult(ok=True, errors=[])


def _looks_like_artifact(data: dict[str, Any]) -> bool:
    return isinstance(data.get("report"), dict) and isinstance(data.get("acceptance"), dict)


def _looks_like_golden(data: dict[str, Any]) -> bool:
    metrics = data.get("metrics")
    return (
        "schema_version" in data
        and "currency" in data
        and "period" in data
        and isinstance(metrics, dict)
        and any(key in metrics for key in GOLDEN_METRIC_KEYS)
    )


def _format_errors(exc: ValidationError) -> list[str]:
    errors: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", ()))
        kind = item.get("type", "")
        msg = item.get("msg", "invalid")
        if kind == "missing":
            errors.append(f"missing key: {loc}" if loc else f"missing key: {msg}")
        elif kind == "extra_forbidden":
            errors.append(f"unknown field: {loc}" if loc else f"unknown field: {msg}")
        else:
            errors.append(f"{loc}: {msg}" if loc else str(msg))
    return errors or ["invalid report"]


class ControllingReportModel:
    model_config = {"extra": "forbid"}

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    @classmethod
    def model_validate(cls, data: Any) -> "ControllingReportModel":
        result = validate_controlling_report(data)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        if not isinstance(data, dict):
            raise ValueError("report must be an object")
        return cls(data)
