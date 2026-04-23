"""Governance rules for reusable automation agents."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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

    def allow(self, action: str, *, risk: str = "low") -> GovernanceDecision:
        if risk == "high":
            return GovernanceDecision(
                allowed=False,
                reason=f"{action} blocked by high-risk policy.",
                requires_approval=True,
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
