"""Fail-closed construction of a compact actual-versus-budget brief.

This module deliberately accepts aggregate KMU report objects only. It never
receives source rows, account labels, or filesystem capabilities.
"""

from decimal import Decimal, InvalidOperation
import re
from typing import Any


_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_RECONCILIATION_KEYS = (
    "source_account_count",
    "mapped_account_count",
    "ignored_account_count",
)


def _decimal(value: Any, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"Ungültiger aggregierter Wert: {label}.")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Ungültiger aggregierter Wert: {label}.") from None
    if not parsed.is_finite():
        raise ValueError(f"Ungültiger aggregierter Wert: {label}.")
    return parsed


def _format(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def _comparison(actual: Any, budget: Any, label: str) -> dict[str, str | None]:
    """Compare one value without fabricating a value for unavailable ratios."""
    if actual is None and budget is None:
        return {
            "actual": None,
            "budget": None,
            "delta": None,
            "relative_delta_percent": None,
        }
    if actual is None or budget is None:
        raise ValueError(f"Ungleiche Verfügbarkeit für {label}.")
    actual_value = _decimal(actual, f"{label}.actual")
    budget_value = _decimal(budget, f"{label}.budget")
    delta = actual_value - budget_value
    return {
        "actual": _format(actual_value),
        "budget": _format(budget_value),
        "delta": _format(delta),
        "relative_delta_percent": (
            None
            if budget_value == 0
            else _format(delta / abs(budget_value) * Decimal("100"))
        ),
    }


def _report_parts(
    report: Any, role: str
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if not isinstance(report, dict):
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    for key in (
        "report_metadata",
        "metrics",
        "groups",
        "provenance",
        "reconciliation",
        "source",
    ):
        if key not in report:
            raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    metadata, metrics, groups = (
        report["report_metadata"],
        report["metrics"],
        report["groups"],
    )
    provenance, reconciliation = report["provenance"], report["reconciliation"]
    if not all(
        isinstance(value, dict)
        for value in (metadata, metrics, groups, provenance, reconciliation)
    ):
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    if not isinstance(report["source"], str) or not report["source"].strip():
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    if set(provenance) < {
        "input_fingerprint",
        "mapping_version",
        "calculation_version",
    }:
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    if (
        not all(
            isinstance(provenance[key], str) and provenance[key].strip()
            for key in ("input_fingerprint", "mapping_version", "calculation_version")
        )
        or not _FINGERPRINT.fullmatch(provenance["input_fingerprint"])
        or not _FINGERPRINT.fullmatch(provenance["mapping_version"])
    ):
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    for key in _RECONCILIATION_KEYS:
        value = reconciliation.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    if (
        reconciliation["source_account_count"]
        != reconciliation["mapped_account_count"]
        + reconciliation["ignored_account_count"]
    ):
        raise ValueError(f"Ungültiger {role}-Aggregatbericht.")
    return metadata, metrics, groups, provenance, reconciliation


def _group_identity(group: Any, label: str) -> tuple[set[str], int]:
    if not isinstance(group, dict) or not isinstance(group.get("account_ids"), list):
        raise ValueError(f"Ungültige Gruppendaten: {label}.")
    account_ids = group["account_ids"]
    if not all(
        isinstance(account, str) and account.strip() for account in account_ids
    ) or len(account_ids) != len(set(account_ids)):
        raise ValueError(f"Ungültige Gruppendaten: {label}.")
    row_count = group.get("row_count")
    if (
        isinstance(row_count, bool)
        or not isinstance(row_count, int)
        or row_count < len(account_ids)
    ):
        raise ValueError(f"Ungültige Gruppendaten: {label}.")
    return set(account_ids), row_count


def monthly_variance_brief(
    actual_report: dict[str, Any], budget_report: dict[str, Any]
) -> dict[str, Any]:
    """Compare two validated aggregate reports without exposing account details."""
    (
        actual_metadata,
        actual_metrics,
        actual_groups,
        actual_provenance,
        actual_reconciliation,
    ) = _report_parts(actual_report, "Ist")
    (
        budget_metadata,
        budget_metrics,
        budget_groups,
        budget_provenance,
        budget_reconciliation,
    ) = _report_parts(budget_report, "Budget")
    if actual_metadata != budget_metadata:
        raise ValueError("Ist- und Budget-Bericht haben unterschiedliche Metadaten.")
    if (
        actual_provenance["mapping_version"] != budget_provenance["mapping_version"]
        or actual_provenance["calculation_version"]
        != budget_provenance["calculation_version"]
    ):
        raise ValueError(
            "Ist- und Budget-Bericht verwenden unterschiedliche Berechnungsversionen."
        )
    if (
        set(actual_metrics) != set(budget_metrics)
        or set(actual_groups) != set(budget_groups)
    ):
        raise ValueError("Ist- und Budget-Bericht sind nicht vergleichbar.")
    if any(
        actual_reconciliation[key] != budget_reconciliation[key]
        for key in _RECONCILIATION_KEYS
    ):
        raise ValueError("Ist- und Budget-Bericht haben unterschiedliche Kontenzahlen.")

    metrics: dict[str, dict[str, str | None]] = {}
    for name in sorted(actual_metrics):
        actual_metric, budget_metric = actual_metrics[name], budget_metrics[name]
        if not isinstance(actual_metric, dict) or not isinstance(budget_metric, dict):
            raise ValueError("Ungültige Kennzahl-Aggregate.")
        metrics[name] = _comparison(
            actual_metric.get("month"),
            budget_metric.get("month"),
            f"metrics.{name}",
        )

    drivers: list[dict[str, Any]] = []
    for name in sorted(actual_groups):
        actual_group, budget_group = actual_groups[name], budget_groups[name]
        if _group_identity(actual_group, name) != _group_identity(budget_group, name):
            raise ValueError("Ist- und Budget-Bericht haben unterschiedliche Kontensätze.")
        comparison = _comparison(
            actual_group.get("month"),
            budget_group.get("month"),
            f"groups.{name}",
        )
        if comparison["delta"] is None:
            continue
        drivers.append({"group": name, **comparison})
    drivers.sort(
        key=lambda item: (
            -abs(_decimal(item["delta"], "group.delta")),
            item["group"],
        )
    )

    def reconciliation(values: dict[str, Any]) -> dict[str, int]:
        return {key: values[key] for key in _RECONCILIATION_KEYS}

    return {
        "kind": "monthly_actual_vs_budget_brief",
        "status": "computed_unapproved",
        "report_metadata": actual_metadata,
        "metrics": metrics,
        "top_group_drivers": drivers,
        "sources": {
            "actual": {
                "source": actual_report["source"],
                "fingerprint": actual_provenance["input_fingerprint"],
            },
            "budget": {
                "source": budget_report["source"],
                "fingerprint": budget_provenance["input_fingerprint"],
            },
            "mapping_version": actual_provenance["mapping_version"],
        },
        "reconciliation": {
            "actual": reconciliation(actual_reconciliation),
            "budget": reconciliation(budget_reconciliation),
        },
        "limitations": [
            "computed_from_provided_actual_and_budget_sources",
            "not_approved",
        ],
    }
