"""Safe narrative layer: aggregate evidence in, management JSON out."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from typing import Any

import brain

from .artifacts import persist_report_artifacts
from .tools import ControllingComputeTool


_METRIC_NAMES = (
    "ebitda",
    "egt",
    "material_ratio",
    "personnel_ratio",
    "receivables",
    "liquidity",
    "payables",
)
_PERIOD_NAMES = ("month", "prior", "ytd", "ytd_prior")
_RECONCILIATION_COUNTS = (
    "source_account_count",
    "mapped_account_count",
    "ignored_account_count",
)
_RECONCILIATION_TOTALS = (
    "mapped_source_period_totals",
    "grouped_period_totals",
)
_NUMBER_RE = re.compile(
    r"(?<![\w])(?P<number>[-+]?\d+(?:[.,]\d+)*)"
    r"(?P<percent>\s*%)?(?![\w])"
)
_ACCOUNT_ID_RE = re.compile(
    r"\b(?:konto(?:nummer|-?id)?|account(?:\s*(?:number|id))?)\b"
    r"[^\d\n]{0,20}\d",
    re.IGNORECASE,
)
_EXTERNAL_SEND_RE = re.compile(
    r"\b(?:extern\w*|(?:ver)?send\w*|schick\w*|weiterleit\w*|"
    r"(?:\u00fcber|ueber)mittel\w*|e-?mail\w*|mail\w*|upload\w*|"
    r"hochlad\w*|shar(?:e|ed|ing)|forward\w*|publish\w*|"
    r"ver\u00f6ffentlich\w*|veroeffentlich\w*|teil(?:e|en|t))\b",
    re.IGNORECASE,
)


class ControllingReportTool:
    """Produces an approval-safe management draft without exposing raw ledgers."""

    description = (
        "Drafts a German management update from a sourced aggregate controlling report."
    )

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
        model = self._narrative_model()
        draft = None
        if model:
            evidence = self._aggregate_evidence(report)
            prompt = json.dumps(
                {
                    "evidence": evidence,
                    "required": {
                        "summary": "exactly three German sentences",
                        "alarms": "array, maximum four",
                        "actions": "array, exactly three",
                    },
                },
                ensure_ascii=False,
            )
            response = brain.complete(
                "Return only strict JSON. Use only supplied aggregate numbers "
                "verbatim. Never mention accounts or identifiers, and never "
                "instruct anyone to send, share, upload, or publish anything.",
                prompt,
                temperature=0.1,
                max_tokens=500,
                model=model,
            )
            parsed = self._valid(response, evidence)
            if parsed is not None:
                parsed["mode"] = "model_draft"
                parsed["citations"] = {
                    "source": report["source"],
                    "method": report["method"],
                }
                draft = parsed
        if draft is None:
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

    @classmethod
    def _aggregate_evidence(cls, report: dict[str, Any]) -> dict[str, Any]:
        raw_metrics = report.get("metrics", {})
        metrics = {
            name: cls._period_values(raw_metrics[name])
            for name in _METRIC_NAMES
            if isinstance(raw_metrics, dict)
            and isinstance(raw_metrics.get(name), dict)
        }
        raw_reconciliation = report.get("reconciliation", {})
        reconciliation: dict[str, Any] = {}
        if isinstance(raw_reconciliation, dict):
            for name in _RECONCILIATION_COUNTS:
                value = raw_reconciliation.get(name)
                if cls._aggregate_value(value):
                    reconciliation[name] = value
            for name in _RECONCILIATION_TOTALS:
                values = raw_reconciliation.get(name)
                if isinstance(values, dict):
                    reconciliation[name] = cls._period_values(values)
        return {"metrics": metrics, "reconciliation": reconciliation}

    @classmethod
    def _period_values(cls, values: dict[str, Any]) -> dict[str, Any]:
        return {
            period: values[period]
            for period in _PERIOD_NAMES
            if period in values and cls._aggregate_value(values[period])
        }

    @staticmethod
    def _aggregate_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return False
        try:
            return Decimal(str(value)).is_finite()
        except InvalidOperation:
            return False

    def _narrative_model(self) -> str | None:
        try:
            manifest = json.loads(
                (self._root / "project" / "manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return None
        value = (
            manifest.get("model", {}).get("narrative")
            if isinstance(manifest.get("model"), dict)
            else None
        )
        return value.strip() if isinstance(value, str) and value.strip() else None

    @classmethod
    def _valid(
        cls, raw: str, evidence: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict) or set(data) - {"summary", "alarms", "actions"}:
            return None
        summary, alarms, actions = (
            data.get("summary"),
            data.get("alarms"),
            data.get("actions"),
        )
        if (
            not isinstance(summary, str)
            or len(re.findall(r"[.!?](?:\s|$)", summary.strip())) != 3
        ):
            return None
        if (
            not isinstance(alarms, list)
            or len(alarms) > 4
            or not all(isinstance(item, str) for item in alarms)
        ):
            return None
        if (
            not isinstance(actions, list)
            or len(actions) != 3
            or not all(isinstance(item, str) for item in actions)
        ):
            return None
        text = "\n".join((summary, *alarms, *actions))
        if (
            _ACCOUNT_ID_RE.search(text)
            or _EXTERNAL_SEND_RE.search(text)
            or not cls._numbers_are_grounded(text, evidence)
        ):
            return None
        return {"summary": summary, "alarms": alarms, "actions": actions}

    @classmethod
    def _numbers_are_grounded(
        cls, text: str, evidence: dict[str, Any]
    ) -> bool:
        grounded = cls._decimals(evidence)
        ratio_metrics = evidence.get("metrics", {})
        ratios = cls._decimals(
            {
                name: values
                for name, values in ratio_metrics.items()
                if name.endswith("_ratio")
            }
            if isinstance(ratio_metrics, dict)
            else {}
        )
        for match in _NUMBER_RE.finditer(text):
            candidates = cls._number_candidates(match.group("number"))
            if match.group("percent"):
                candidates = {candidate / Decimal("100") for candidate in candidates}
                if not candidates & ratios:
                    return False
            elif not candidates & grounded:
                return False
        return True

    @classmethod
    def _decimals(cls, value: Any) -> set[Decimal]:
        if isinstance(value, dict):
            return set().union(*(cls._decimals(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(cls._decimals(item) for item in value))
        if value is None or isinstance(value, bool):
            return set()
        try:
            decimal = Decimal(str(value))
        except InvalidOperation:
            return set()
        return {decimal} if decimal.is_finite() else set()

    @staticmethod
    def _number_candidates(raw: str) -> set[Decimal]:
        normalized = raw
        if "," in normalized and "." in normalized:
            decimal_separator = "," if normalized.rfind(",") > normalized.rfind(".") else "."
            grouping_separator = "." if decimal_separator == "," else ","
            normalized = normalized.replace(grouping_separator, "").replace(
                decimal_separator, "."
            )
        elif normalized.count(",") == 1:
            normalized = normalized.replace(",", ".")
        elif normalized.count(",") > 1:
            normalized = normalized.replace(",", "")
        elif normalized.count(".") > 1:
            normalized = normalized.replace(".", "")
        try:
            candidates = {Decimal(normalized)}
        except InvalidOperation:
            return set()
        separator = "," if "," in raw and "." not in raw else "."
        groups = raw.lstrip("+-").split(separator)
        if len(groups) > 1 and all(len(group) == 3 for group in groups[1:]):
            candidates.add(Decimal(raw.replace(separator, "")))
        return {candidate for candidate in candidates if candidate.is_finite()}

    @staticmethod
    def _fallback(report: dict[str, Any]) -> dict[str, Any]:
        metrics = report.get("metrics", {})
        ebitda = metrics.get("ebitda", {}).get("month")
        egt = metrics.get("egt", {}).get("month")
        return {
            "mode": "deterministic_fallback",
            "summary": f"Der Bericht basiert auf der geprüften Quelle. EBITDA im Monat: {ebitda}. EGT im Monat: {egt}.",
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
