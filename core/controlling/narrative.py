"""Deterministic management narrative for sourced controlling reports."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .artifacts import persist_report_artifacts
from .tools import ControllingComputeTool


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
        source = request.get("source", "auto")
        raw_report = self._compute.safe_run(
            json.dumps({"operation": "kmu_report", "source": source})
        )
        if raw_report.startswith("FEHLER"):
            return raw_report
        report = json.loads(raw_report)
        validated_at = datetime.now(timezone.utc)
        draft = self._fallback(report)
        draft_created_at = datetime.now(timezone.utc)
        try:
            persisted = persist_report_artifacts(
                self._root,
                report,
                draft,
                validated_at=validated_at,
                draft_created_at=draft_created_at,
            )
        except (OSError, ValueError) as exc:
            return f"FEHLER: Bericht konnte nicht revisionssicher gespeichert werden: {exc}"
        if persisted:
            draft.update(persisted)
        return json.dumps(draft, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _fallback(report: dict[str, Any]) -> dict[str, Any]:
        metrics = report.get("metrics", {})
        ebitda = metrics.get("ebitda", {}).get("month")
        egt = metrics.get("egt", {}).get("month")
        return {
            "mode": "deterministic_fallback",
            "summary": (
                "Der Bericht basiert auf der geprüften Quelle. "
                f"EBITDA im Monat: {ebitda}. EGT im Monat: {egt}."
            ),
            "alarms": [
                f"Materielle Abweichungen: {len(report.get('material_deviations', []))}."
            ],
            "actions": [
                "Kontenzuordnung prüfen.",
                "Abweichungen priorisieren.",
                "Management-Entwurf intern freigeben.",
            ],
            "citations": {"source": report["source"], "method": report["method"]},
        }
