"""Explicit, provider-preserving model escalation without transport retries."""
from __future__ import annotations

import hashlib
import json

from .contracts import ContractError
from .engine import Backend


class EscalatingBackend:
    """Route one assignment; the Engine still owns budgets, approvals and review."""

    def __init__(self, primary: Backend, *, recovery: Backend | None = None,
                 reviewer: Backend | None = None, repair_after: int = 2):
        if type(repair_after) is not int or not 1 <= repair_after <= 10:
            raise ContractError("repair_after must be an integer between 1 and 10.")
        backends = [backend for backend in (primary, recovery, reviewer) if backend is not None]
        if any(backend.name != primary.name for backend in backends):
            raise ContractError("Model routing must preserve the configured provider/backend.")
        self.primary, self.recovery, self.reviewer = primary, recovery, reviewer
        self.repair_after = repair_after
        self.name = primary.name
        self.model = getattr(primary, "model", None)
        self.supports_action_approvals = all(
            getattr(backend, "supports_action_approvals", False) for backend in backends)

    @property
    def approval_identity(self) -> str:
        policy = {"version": 1, "backend": self.name, "repair_after": self.repair_after,
                  "models": [getattr(backend, "model", None) if backend is not None else None
                             for backend in (self.primary, self.recovery, self.reviewer)]}
        # A pending approval covers the whole routing configuration.
        # Changing a recovery/review model must invalidate it, even if primary stays.
        return "routing-v1:" + hashlib.sha256(
            json.dumps(policy, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _revisions(context: dict) -> int:
        roles = context["catalog"]["roles"]
        revisions = 0
        for record in context.get("history", []):
            report = record.get("report", {})
            role = roles.get(record.get("decision", {}).get("role"), {})
            if (report.get("status") == "success" and role.get("can_review")
                    and report.get("evidence")):
                revisions = 0
            elif report.get("status") == "needs_revision":
                revisions += 1
        return revisions

    def _select(self, decision: dict, context: dict) -> tuple[Backend, str]:
        if context["catalog"]["roles"][decision["role"]]["can_review"] and self.reviewer is not None:
            return self.reviewer, "independent_review"
        if self.recovery is not None and self._revisions(context) >= self.repair_after:
            return self.recovery, "repeated_revision"
        return self.primary, "primary"

    def execution_route(self, decision: dict, context: dict) -> dict:
        backend, reason = self._select(decision, context)
        return {"backend": backend.name, "model": getattr(backend, "model", None),
                "reason": reason, "revisions": self._revisions(context)}

    def decide(self, context: dict, timeout: float) -> dict:
        return self.primary.decide(context, timeout)

    def execute(self, decision: dict, context: dict, timeout: float) -> dict:
        backend, _ = self._select(decision, context)
        # Never catch/retry an interrupted tool or unknown provider outcome.
        return backend.execute(decision, context, timeout)
