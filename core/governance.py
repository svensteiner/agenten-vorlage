"""Governance rules for reusable automation agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .context import ProjectContext

if TYPE_CHECKING:
    from .subagents import SubagentSpec


@dataclass
class GovernanceDecision:
    allowed: bool
    reason: str = ""
    requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernancePolicy:
    """Policy layer for cooldowns, approval gates, risk checks, and leaf-write enforcement."""

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
        matched_terms = self._matched_approval_terms(approval_terms, combined)
        hard_block_terms = self._matched_hard_block_terms(combined)
        would_gate = risk == "high" or bool(matched_terms)

        # ── Hard block, evaluated BEFORE the autonomy shortcut (ADR-0006, G5) ──
        # The hard-block class — destructive / irreversible operations detected
        # by a *deterministic* keyword policy, not by trusting an LLM-produced
        # `requires_human` flag — is unconditional. A full-autonomy deployment
        # may skip the *approval* gate for ordinary actions, but can never skip
        # the hard block unless it explicitly opts out via manifest
        # `hard_block_on_high_risk: false`. This makes the check.py "max is
        # fail-open" warning unreachable for the hard-block class.
        if hard_block_terms and self._hard_block_enabled(context):
            return GovernanceDecision(
                allowed=False,
                reason=(
                    f"{action} hard-blocked (irreversible/destructive): "
                    f"{', '.join(hard_block_terms)}."
                ),
                requires_approval=True,
                metadata={
                    "gate": "hard_block",
                    "risk": risk,
                    "tool": tool,
                    "hard_block_terms": hard_block_terms,
                },
            )

        # Full-autonomy mode (default): never block ordinary actions. Risky
        # actions are still flagged in metadata so the run leaves an audit trail.
        if not self._approval_required(context):
            return GovernanceDecision(
                allowed=True,
                metadata={
                    "gate": "disabled",
                    "flagged": would_gate,
                    "risk": risk,
                    "tool": tool,
                    "matched_terms": matched_terms,
                },
            )

        if risk == "high":
            return GovernanceDecision(
                allowed=False,
                reason=f"{action} blocked by high-risk policy.",
                requires_approval=True,
                metadata={"risk": risk, "tool": tool},
            )
        if matched_terms:
            return GovernanceDecision(
                allowed=False,
                reason=f"{action} requires approval for: {', '.join(matched_terms)}.",
                requires_approval=True,
                metadata={"matched_terms": matched_terms, "tool": tool},
            )
        return GovernanceDecision(allowed=True)

    # Deterministic hard-block vocabulary (ADR-0006). Irreversible / destructive
    # operations that must never be reachable via the autonomy shortcut. Kept as
    # a fixed policy in code, not derived from a model's judgement.
    _HARD_BLOCK_TERMS: tuple[str, ...] = (
        "delete",
        "remove",
        "lösch",
        "loesch",
        "entfern",
        "overwrite",
        "überschreib",
        "ueberschreib",
        "drop table",
        "truncate",
        "bulk",
        "massenlösch",
        "massenloesch",
        "payment",
        "zahlung",
        "wire transfer",
        "überweis",
        "ueberweis",
        "deploy production",
        "production deploy",
    )

    def _hard_block_enabled(self, context: ProjectContext | None) -> bool:
        """Whether the unconditional hard block is active (default: True).

        A deployment may opt out for the hard-block class by setting
        ``hard_block_on_high_risk: false`` in project/manifest.json — an explicit,
        auditable decision, never an implicit consequence of ``autonomy_level``.
        """
        if context is None:
            return True
        manifest = context.manifest if isinstance(context.manifest, dict) else {}
        return bool(manifest.get("hard_block_on_high_risk", True))

    def _matched_hard_block_terms(self, text: str) -> list[str]:
        return [term for term in self._HARD_BLOCK_TERMS if term in text]

    def _approval_required(self, context: ProjectContext | None) -> bool:
        """Whether the human-approval gate is active.

        Fail-closed by default: the gate is ON unless the deployment explicitly
        opts into full autonomy. Opt in by setting "autonomy_level": "max" in
        project/manifest.json (trusted, low-risk deployments only), or by setting
        "require_human_approval": false in project/config.json.
        See platform/security/00-security-architecture.md (fail-closed doctrine).
        """
        if context is None:
            return True
        manifest = context.manifest if isinstance(context.manifest, dict) else {}
        if str(manifest.get("autonomy_level", "")).lower() == "max":
            return False
        return bool(context.config.get("require_human_approval", True))

    def allow_write(
        self,
        subagent: "SubagentSpec | None",
        *,
        context: ProjectContext | None = None,
        is_leaf: bool = False,
    ) -> GovernanceDecision:
        """Enforce the leaf-write pattern: only the final subagent in a chain may write.

        The pattern from Anthropic's financial-services templates: read-only subagents
        gather and process data; a single leaf subagent is the only one allowed to
        produce persistent output. This prevents uncoordinated writes from multiple
        agents and makes the write surface auditable.
        """
        manifest = (context.manifest if context else {}) or {}
        tool_perms = manifest.get("tool_permissions", {}) if isinstance(manifest, dict) else {}
        write_restricted = tool_perms.get("write_restricted_to_leaf", True)

        if not write_restricted:
            return GovernanceDecision(allowed=True, reason="write_restricted_to_leaf disabled in manifest.")

        if subagent is None:
            return GovernanceDecision(allowed=True, reason="No subagent — orchestrator write allowed.")

        if subagent.can_write:
            return GovernanceDecision(allowed=True, reason=f"{subagent.name} is declared as leaf writer.")

        if is_leaf:
            return GovernanceDecision(allowed=True, reason=f"{subagent.name} is the leaf in this chain.")

        return GovernanceDecision(
            allowed=False,
            reason=(
                f"{subagent.name} is not a leaf writer. "
                "Set 'can_write: true' in AGENT.md frontmatter to allow writes."
            ),
            requires_approval=False,
            metadata={"subagent": subagent.name, "pattern": "leaf-write"},
        )

    def allow_connector(
        self,
        connector_name: str,
        *,
        context: ProjectContext | None = None,
    ) -> GovernanceDecision:
        """Only connectors declared in connectors.yaml may be used."""
        if context is None:
            return GovernanceDecision(
                allowed=False,
                reason="No project context — cannot verify connector declaration.",
            )
        declared = {c.name for c in context.connectors}
        if not declared:
            return GovernanceDecision(
                allowed=True,
                reason="No connectors declared — connector check skipped.",
            )
        if connector_name in declared:
            return GovernanceDecision(allowed=True, reason=f"Connector '{connector_name}' is declared.")
        return GovernanceDecision(
            allowed=False,
            reason=(
                f"Connector '{connector_name}' is not declared in connectors.yaml. "
                "Add it there before using it."
            ),
            requires_approval=True,
            metadata={"connector": connector_name, "declared": sorted(declared)},
        )

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
