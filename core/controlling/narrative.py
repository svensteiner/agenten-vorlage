"""Deterministic management narrative for sourced controlling reports."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .artifacts import persist_report_artifacts, validate_operation_id
from .report_schema import validate_controlling_report
from .tools import ControllingComputeTool, pilot_availability
from .variance import monthly_variance_brief


class ControllingReportTool:
    """Produces an approval-safe, source-backed management draft."""

    description = "Drafts a deterministic German management update from a sourced report."

    def __init__(self, instance_root: Path):
        self._root = instance_root
        self._compute = ControllingComputeTool(instance_root)

    def safe_run(self, input_str: str) -> str:
        try:
            request = json.loads(input_str) if input_str else {}
        except json.JSONDecodeError:
            return "FEHLER: Berichtsanfrage muss ein JSON-Objekt sein."
        if not isinstance(request, dict):
            return "FEHLER: Berichtsanfrage muss ein JSON-Objekt sein."
        if "actual_source" in request or "budget_source" in request:
            return self._two_source_safe_run(request)
        source = request.get("source", "auto")
        try:
            operation_id = validate_operation_id(request.get("operation_id"))
        except ValueError as exc:
            return f"FEHLER: operation_id {exc}"
        raw_report = self._compute.safe_run(
            json.dumps({"operation": "kmu_report", "source": source})
        )
        if raw_report.startswith("FEHLER"):
            return raw_report
        try:
            report = json.loads(raw_report)
        except json.JSONDecodeError:
            return "FEHLER: Rechenbericht ist nicht lesbar."
        if not isinstance(report, dict):
            return "FEHLER: Rechenbericht ist unvollstaendig."
        schema = validate_controlling_report(report)
        if not schema.ok:
            return "FEHLER: Berichtsschema ungueltig: " + "; ".join(schema.errors)
        return self._draft_and_persist(report, operation_id)

    def _two_source_safe_run(self, request: dict[str, Any]) -> str:
        """Build a report from one explicit actual and one explicit budget file."""
        allowed = {"actual_source", "budget_source", "operation_id"}
        required = {"actual_source", "budget_source"}
        if set(request) - allowed or not required <= set(request):
            return (
                "FEHLER: Zwei-Quellen-Bericht benoetigt genau actual_source und "
                "budget_source sowie optional operation_id."
            )
        actual_source = request["actual_source"]
        budget_source = request["budget_source"]
        if any(
            not isinstance(source, str)
            or not source.strip()
            or source.strip() == "auto"
            for source in (actual_source, budget_source)
        ):
            return "FEHLER: Ist- und Budget-Quelle muessen explizit angegeben werden."
        try:
            operation_id = validate_operation_id(request.get("operation_id"))
        except ValueError as exc:
            return f"FEHLER: operation_id {exc}"

        actual_raw = self._compute.safe_run(
            json.dumps({"operation": "kmu_report", "source": actual_source})
        )
        if actual_raw.startswith("FEHLER"):
            return actual_raw
        budget_raw = self._compute.safe_run(
            json.dumps({"operation": "kmu_report", "source": budget_source})
        )
        if budget_raw.startswith("FEHLER"):
            return budget_raw
        try:
            actual_report = json.loads(actual_raw)
            budget_report = json.loads(budget_raw)
            if not isinstance(actual_report, dict) or not isinstance(budget_report, dict):
                raise ValueError("Rechenberichte sind unvollstaendig.")
            if actual_report.get("source") == budget_report.get("source"):
                raise ValueError("Ist- und Budget-Quelle muessen unterschiedliche Dateien sein.")
            for candidate in (actual_report, budget_report):
                schema = validate_controlling_report(candidate)
                if not schema.ok:
                    return "FEHLER: Berichtsschema ungueltig: " + "; ".join(schema.errors)
            variance = monthly_variance_brief(actual_report, budget_report)
            report = self._with_budget_variance_availability(actual_report)
        except (json.JSONDecodeError, ValueError) as exc:
            return f"FEHLER: {exc}"
        return self._draft_and_persist(report, operation_id, variance=variance)

    @staticmethod
    def _with_budget_variance_availability(report: dict[str, Any]) -> dict[str, Any]:
        """Mark budget variance as present without changing the legacy report route."""
        availability = report.get("availability")
        if availability != pilot_availability():
            raise ValueError("Rechenbericht hat einen ungueltigen Verfuegbarkeitsvertrag.")
        return {
            **report,
            "availability": {
                **availability,
                "budget_variance": {
                    "status": "available",
                    "processing": "two_source_actual_vs_budget",
                },
            },
        }

    def _draft_and_persist(
        self,
        report: dict[str, Any],
        operation_id: str | None,
        *,
        variance: dict[str, Any] | None = None,
    ) -> str:
        validated_at = datetime.now(timezone.utc)
        draft = self._fallback(report, variance=variance)
        draft_created_at = datetime.now(timezone.utc)
        try:
            persisted = persist_report_artifacts(
                self._root,
                report,
                draft,
                validated_at=validated_at,
                draft_created_at=draft_created_at,
                operation_id=operation_id,
            )
        except (OSError, ValueError) as exc:
            return f"FEHLER: Bericht konnte nicht revisionssicher gespeichert werden: {exc}"
        if persisted:
            draft.update(persisted)
        return json.dumps(draft, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _fallback(
        report: dict[str, Any], *, variance: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        metrics = report.get("metrics", {})
        ebitda = metrics.get("ebitda", {}).get("month")
        egt = metrics.get("egt", {}).get("month")
        legacy_draft = {
            "mode": "deterministic_fallback",
            "summary": (
                "Der Bericht basiert auf der geprüften Quelle. "
                f"EBITDA im Monat: {ebitda}. EGT im Monat: {egt}."
            ),
            "alarms": [
                f"Materielle Abweichungen: {len(report.get('material_deviations', []))}.",
                "Budgetabweichung nicht verfügbar: in diesem Piloten nicht verarbeitet.",
                "Forderungsalterung nicht verfügbar: in diesem Piloten nicht verarbeitet.",
            ],
            "actions": [
                "Kontenzuordnung prüfen.",
                "Abweichungen priorisieren.",
                "Management-Entwurf intern freigeben.",
            ],
            "citations": {"source": report["source"], "method": report["method"]},
        }
        if variance is None:
            return legacy_draft

        ebitda_variance = variance.get("metrics", {}).get("ebitda", {})
        delta = ebitda_variance.get("delta", "-")
        relative = ebitda_variance.get("relative_delta_percent")
        relative_text = "nicht berechenbar" if relative is None else f"{relative} %"
        return {
            "mode": "deterministic_fallback",
            "summary": (
                "Der Bericht basiert auf den geprueften Ist- und Budgetquellen. "
                f"EBITDA im Monat: Ist {ebitda_variance.get('actual', ebitda)}, "
                f"Budget {ebitda_variance.get('budget', '-')}, "
                f"Abweichung {delta} ({relative_text}). EGT im Monat: {egt}."
            ),
            "alarms": [
                f"Materielle Abweichungen: {len(report.get('material_deviations', []))}.",
                f"EBITDA-Abweichung zum Budget: {delta} ({relative_text}).",
                "Forderungsalterung nicht verfuegbar: in diesem Piloten nicht verarbeitet.",
            ],
            "actions": [
                "Budgetabweichungen nach Bereichen priorisieren.",
                "Kontenzuordnung pruefen.",
                "Management-Entwurf intern freigeben.",
            ],
            "citations": {
                "source": report["source"],
                "method": report["method"],
                "budget_source": variance["sources"]["budget"]["source"],
            },
            "variance": variance,
        }
