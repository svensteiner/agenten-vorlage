"""Pack validators — six checks, one invariant (VALIDATE stage, ADR-0017 §4.2).

Each validator asserts a pack section is a **subset / tightening** of its
horizontal extension point. The composite invariant is the
[ADR-0016 tighten-only rule](platform/architecture/adr/ADR-0016-domain-pack-contract.md)
made *executable*: an accepted pack can only **subtract** capability.

The loader is safe *by construction*, not by decision: its only verbs are
subset-installs into fail-closed extension points. A widening §3 delta composes
to a no-op under most-restrictive-wins; an unregistered §2 label is rejected by
the closed grammar; §6 reuses the ``check.py`` "allowlist ⊆ workers" logic. The
gate is the belt; the closed extension points are the suspenders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bundle import PackBundle

# Restrictiveness ordering (higher = more restrictive). A matrix delta is
# tighten-only iff each label's new action ranks >= its ratified baseline.
_ACTION_RANK: dict[str, int] = {
    "allow": 0,
    "flag": 1,
    "redact": 2,
    "mask": 2,
    "quarantine": 3,
    "deny": 3,
}


@dataclass(frozen=True)
class ExtensionPoints:
    """The horizontal extension points a pack section must fit ⊆.

    Defaults mirror the ratified platform floor; a real loader resolves these
    from the live label schema, policy store, conformance corpus, and registry.
    """

    # §2 closed label grammar: bare tokens + dimension prefixes.
    label_tokens: frozenset[str] = frozenset(
        {"public", "internal", "confidential", "pii", "restricted"}
    )
    label_prefixes: tuple[str, ...] = (
        "pii_class:",
        "restricted:",
        "matter:",
        "visibility:",
        "sensitivity:",
    )
    # §3 ratified baseline label→action matrix (the tighten-only floor).
    baseline_matrix: dict[str, str] = field(
        default_factory=lambda: {
            "public": "allow",
            "internal": "allow",
            "confidential": "mask",
            "pii": "mask",
            "restricted": "deny",
        }
    )
    # §5 approved-model registry.
    approved_models: frozenset[str] = frozenset(
        {"claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-8"}
    )
    # §6 allowlisted handoff targets (the HandoffRouter allowlist).
    handoff_allowlist: frozenset[str] = frozenset({"reader", "compute", "writer"})


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    rejected_by: str = ""
    reasons: tuple[str, ...] = ()


def _label_in_grammar(label: str, ext: ExtensionPoints) -> bool:
    if label in ext.label_tokens:
        return True
    return any(label.startswith(prefix) and len(label) > len(prefix) for prefix in ext.label_prefixes)


# ── The six section validators. Each returns (ok, reason). ────────────────────


def validate_acl_fixtures(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§1 — every ACL fixture must resolve to authorized principals only.

    An ``expected`` principal set that is not a subset of ``authorized`` is an
    over-grant — the exact leak the conformance gate exists to catch, made a
    load-time failure rather than a canary catch (hardens R1).
    """
    for fx in bundle.acl_fixtures:
        expected = set(fx.get("expected", []))
        authorized = set(fx.get("authorized", []))
        if not expected.issubset(authorized):
            leaked = sorted(expected - authorized)
            return False, f"ACL fixture '{fx.get('name', '?')}' over-grants to {leaked}"
    return True, ""


def validate_labels(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§2 — every new label must fall inside the closed classification grammar."""
    for label in bundle.labels:
        if not _label_in_grammar(label, ext):
            return False, f"label '{label}' is outside the closed grammar"
    return True, ""


def validate_matrix_deltas(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§3 — matrix deltas must be tighten-only (the marquee floor invariant)."""
    for label, action in bundle.matrix_deltas.items():
        if action not in _ACTION_RANK:
            return False, f"unknown action '{action}' for label '{label}'"
        baseline = ext.baseline_matrix.get(label, "allow")
        if _ACTION_RANK[action] < _ACTION_RANK[baseline]:
            return False, (
                f"label '{label}' loosens the floor: '{action}' is less restrictive "
                f"than the ratified '{baseline}'"
            )
    return True, ""


def validate_compliance_rows(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§4 — compliance-map rows must be additive (never remove an obligation)."""
    for row in bundle.compliance_rows:
        if str(row.get("op", "add")).lower() == "remove":
            return False, f"compliance row '{row.get('name', '?')}' removes an obligation"
    return True, ""


def validate_eval_models(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§5 — eval fixtures may reference only approved models."""
    for model in bundle.eval_models:
        if model not in ext.approved_models:
            return False, f"eval references unapproved model '{model}'"
    return True, ""


def validate_agent_graph(bundle: PackBundle, ext: ExtensionPoints) -> tuple[bool, str]:
    """§6 — the pack's agent graph must be ⊆ the allowlisted handoff targets."""
    for target in bundle.agent_graph:
        if target not in ext.handoff_allowlist:
            return False, f"agent-graph target '{target}' is not an allowlisted handoff target"
    return True, ""


# Ordered §1..§6; the section label is what ``rejected_by`` reports.
_VALIDATORS: tuple[tuple[str, Any], ...] = (
    ("§1 conformance validator", validate_acl_fixtures),
    ("§2 closed-grammar validator", validate_labels),
    ("§3 tighten-only validator", validate_matrix_deltas),
    ("§4 additive-compliance validator", validate_compliance_rows),
    ("§5 approved-model validator", validate_eval_models),
    ("§6 allowlist-subset validator", validate_agent_graph),
)


def validate_bundle(
    bundle: PackBundle,
    ext: ExtensionPoints | None = None,
    *,
    fail_validator: str | None = None,
) -> ValidationResult:
    """Run the six validators in order; the first failure sets ``rejected_by``.

    ``fail_validator`` injects a synthetic failure at a named section (used by the
    atomicity test to prove a mid-VALIDATE failure installs zero sections).
    """
    ext = ext or ExtensionPoints()
    for section, validator in _VALIDATORS:
        if fail_validator is not None and section.startswith(fail_validator):
            return ValidationResult(ok=False, rejected_by=section, reasons=("injected failure",))
        ok, reason = validator(bundle, ext)
        if not ok:
            return ValidationResult(ok=False, rejected_by=section, reasons=(reason,))
    return ValidationResult(ok=True)
