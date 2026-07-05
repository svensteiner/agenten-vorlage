# ADR-0006 — Fail-closed autonomy is the template default

- **Status:** Accepted (Cycle 2, council-driven)
- **Deciders:** Security & Governance Architect (council) + architecture agent
- **Relates to:** [Security Architecture §9/§10](../../security/00-security-architecture.md),
  [ADR-0005](ADR-0005-template-consolidation-council.md)

## Context

An earlier merge (PR #1, "full-autonomy mode") shipped the template with
`approval_required_for: []`, `autonomy_level: "max"`, and a `core/governance.py` whose
`_approval_required()` returned `False` by default. The result: `GovernancePolicy.allow()`
returned `allowed=True` for **every** action — including `risk="high"` and matched
destructive terms (delete/overwrite/bulk) — merely tagging them `flagged` in metadata.

The Security Architect flagged this as a **fail-open regression** that directly
contradicts the platform's own Security Architecture: §9 names "governance policy engine
+ approval gates" as the mitigation for *excessive agency*, and §10 mandates a
fail-closed doctrine ("ambiguity → deny + audit + escalate"). "Log-after-the-fact" is a
detective control, not a preventive one — useless for irreversible actions. For a
template destined for Finance/HR/Legal/Audit, fail-open cannot be the default.

## Decision

The template ships **fail-closed by default**:

- `project/manifest.json`: `autonomy_level: "gated"`,
  `approval_required_for: ["delete", "overwrite", "bulk changes", "external_send"]`.
- `core/governance.py` `_approval_required()`: returns **`True` by default** (gate ON).
  It returns `False` **only** when a deployment explicitly opts in via
  `autonomy_level: "max"` in the manifest (or `require_human_approval: false` in
  `config.json`). A `None` context also fails closed.
- Full autonomy remains available, but as a **deliberate, documented per-deployment
  opt-in** for trusted, low-risk contexts — never the out-of-box posture.

## Consequences

- (+) The default template denies destructive/high-risk actions until approved —
  aligned with the fail-closed doctrine and safe for regulated domains.
- (+) Autonomy is one explicit flag away for users who genuinely want it.
- (−) Users who relied on the previous auto-approve default must set
  `autonomy_level: "max"` to restore it. This is intentional friction.

## Follow-up (tracked in NEXT_STEPS)

The council recommends a deeper hardening: the **high-risk hard block should run before
the autonomy shortcut**, so even `autonomy_level: max` cannot silently perform an
irreversible action, and escalation should be a deterministic policy decision rather
than an LLM-emitted `needs_human` flag. Deferred to the v3.0-harvest cycle to keep this
merge surgical.

## Alternatives

- **Keep fail-open default** — rejected: contradicts the security doctrine; incident risk.
- **Remove autonomy entirely** — rejected: legitimate low-risk automation use exists;
  make it opt-in, not impossible.
