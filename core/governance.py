"""Governance rules for reusable automation agents."""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from .context import ProjectContext


@dataclass
class GovernanceDecision:
    allowed: bool
    reason: str = ""
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernancePolicy:
    """Policy layer for cooldowns, approval gates, and risk checks."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def allow(
        self,
        action: str,
        *,
        risk: str = "low",
        context: ProjectContext | None = None,
        tool: str | None = None,
        text: str = "",
    ) -> GovernanceDecision:
        combined = " ".join(part for part in [action, tool or "", text] if part).lower()
        approval_terms = self._approval_terms(context)

        if risk == "high":
            return GovernanceDecision(
                allowed=False,
                reason=f"{action} blocked by high-risk policy.",
                requires_approval=True,
                metadata={"risk": risk, "tool": tool},
            )
        matched_terms = self._matched_approval_terms(approval_terms, combined)
        if matched_terms:
            return GovernanceDecision(
                allowed=False,
                reason=f"{action} requires approval for: {', '.join(matched_terms)}.",
                requires_approval=True,
                metadata={"matched_terms": matched_terms, "tool": tool},
            )
        return GovernanceDecision(allowed=True)

    def record(self, action: str, outcome: str, details: str = "") -> None:
        self._history.append(
            {
                "action": action,
                "outcome": outcome,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def _approval_terms(self, context: ProjectContext | None) -> list[str]:
        if context is None:
            return []

        terms: list[str] = []
        manifest_terms = context.manifest.get("approval_required_for", [])
        if isinstance(manifest_terms, str):
            terms.extend([item.strip() for item in manifest_terms.split(",")])
        elif isinstance(manifest_terms, list):
            terms.extend(str(item).strip() for item in manifest_terms)

        config_terms = context.config.get("human_approval_required", [])
        if isinstance(config_terms, str):
            terms.extend([item.strip() for item in config_terms.split(",")])
        elif isinstance(config_terms, list):
            terms.extend(str(item).strip() for item in config_terms)

        normalized = []
        for term in terms:
            if term and term.lower() not in normalized:
                normalized.append(term.lower())
        return normalized

    def _matched_approval_terms(self, terms: list[str], text: str) -> list[str]:
        aliases = {
            "delete": ["delete", "remove", "lösch", "loesch", "entfern"],
            "overwrite": ["overwrite", "replace", "überschreib", "ueberschreib", "ersetze"],
            "bulk changes": ["bulk", "massenänder", "massenaender", "massenhaft"],
            "destructive": ["delete", "remove", "lösch", "loesch", "overwrite", "überschreib"],
        }
        matches: list[str] = []
        for term in terms:
            candidates = aliases.get(term, [term])
            if any(candidate in text for candidate in candidates):
                matches.append(term)
        return matches
