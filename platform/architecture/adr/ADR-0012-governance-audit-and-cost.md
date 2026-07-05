# ADR-0012 — Governance plane: ratified SLA/label/retention policy, audit-as-evidence, and a safety-preserving cost model

- **Status:** Accepted (Cycle 7)
- **Deciders:** Platform Governance, Security Architecture, Finance-Ops, Enterprise Architecture
- **Relates to:** [ADR-0003](ADR-0003-model-gateway-indirection.md) (the choke point model
  governance flows through), [ADR-0004](ADR-0004-permission-faithful-retrieval.md) /
  [ADR-0006](ADR-0006-fail-closed-autonomy-default.md) (fail-closed doctrine, now applied to
  *spend*), [ADR-0008](ADR-0008-canonical-principal-acl-model.md) (labels are the second gate
  this ratifies the policy for), [ADR-0010](ADR-0010-storage-topology-and-tenancy.md) (audit
  store, erasure, per-tenant cost attribution this consumes), [ADR-0011](ADR-0011-ingestion-workers-and-connector-framework.md)
  (the priority-class SLA this ratifies the numbers for),
  [Governance deep dive](../../governance/00-governance-and-audit.md) (full detail)

## Context

Cycles 1–6 built machinery **capable** of being fresh, isolated, auditable, and bounded, and
every one of them deferred the same class of question to Governance: *what is the actual
promised number, retained for how long, at what cost, and who ratifies it?* Three
ratifications were explicitly queued ([NEXT_STEPS §6, Cycle 7](../../NEXT_STEPS.md)):

- the **freshness SLA** — [Workers §4.2/§10](../../workers/00-ingestion-architecture.md)
  *implements and measures* ≤5/≤15 min, but only a policy owner can make it a **promise**
  ([Permissions §8](../../permissions/00-authorization-model.md), open Q#7);
- the **sensitivity-label policy** — [Permissions §7](../../permissions/00-authorization-model.md)
  fixed labels as a second, restrict-only gate but left the label→action mapping to Governance;
- **retention + legal-hold + right-to-erasure + per-tenant cost metering** —
  [Storage §9–§10](../../storage/00-storage-architecture.md) built the mechanisms; the durations,
  the legal balance, and the budget were unowned.

R5 (cost blow-up) was also the last high-severity risk with levers but no owner of the budget
that pulls them. The forcing question: how do we make the platform's promises **contractual and
provable** without adding a hot-path component or letting cost control ever weaken safety?

## Decision

1. **Governance is a policy plane, not a runtime component.** It adds only a **versioned,
   itself-audited policy store** and a **reporting/metering surface** over the existing audit
   log. Every enforcement point already exists (Model Gateway, retrieval filter/redactor, worker
   scheduler, audit store); Governance supplies *configuration*, adding **no hot-path latency**.
2. **The freshness SLA is ratified** as contractual per-tier numbers: principal change ≤5 min
   (Standard) / ≤2 min (Isolated); restrictive resource-ACL ≤15 / ≤5 min; widening ≤60 / ≤15 min;
   public best-effort. A breach is an alarm **and** a recorded governance incident (contractual
   reporting event for Isolated tenants). The tight principal number is affordable because
   query-time principal precedence ([Storage §7](../../storage/00-storage-architecture.md)) already
   closes offboarding independent of the re-tag.
3. **The label→action policy is ratified** as a platform-owned default matrix (`public` /
   `internal` / `confidential` / `pii` / `legal_hold` / `restricted:<class>`) mapping each label to
   retrieval / prompt / routing / egress actions, composing **most-restrictive-wins**. Tenants may
   **tighten, never loosen**; labels can only subtract capability (Permissions §7 invariant
   preserved). Enforced at the already-built retrieval and Gateway points.
4. **Retention, erasure, and legal-hold are ratified.** Per-store retention schedule (audit ≥1 yr
   hot / ≥7 yr cold; raw object 90 days→archival; DLQ 30 days; cache 5–15 min); right-to-erasure is
   an SLA-bound DSAR workflow using Storage §9 propagation with the **erasure recorded as an audit
   event** and the **audit trail itself exempt**; precedence **legal-hold > erasure > retention**.
5. **Audit is the evidence base.** A promise the audit log cannot evidence is not a governable
   promise. Audit read access is role-gated and itself audited; the hash-chain is verified on a
   schedule; the SLA, label policy, erasure, and budgets are each *proven* by their event type.
6. **A per-tenant cost model with safety-preserving graceful degradation** (R5). Every cost-bearing
   event carries `tenant_id`; per-tenant→pack→workload attribution assembles the bill. Budget
   envelopes degrade **capability before safety**: 80–100% → cheaper model tier + defer P2 +
   tighten cache; 100% → block new P2, queue (not drop) P1, alert. **A budget cap can never relax a
   permission, skip the ACL filter, or throttle a P0 revocation** — fail-closed on spend.
7. **Model governance through the Gateway:** an approved-model registry with provenance + hosting
   posture + data terms; **eval-before-promotion** (grounding, refusal calibration, jailbreak
   resistance, pack task accuracy); per-tenant version pinning + rollback; model version captured in
   every retrieval audit event. The model analogue of the connector conformance gate.
8. **Compliance mapping** binds existing controls to regimes (GDPR / SOX / ISO 27001-SOC 2 /
   sector) per domain, each cell evidence-backed by an audit-event type. A new domain pack
   **inherits** rows; it does not re-derive controls.

Full tables (SLA per tier, label matrix, retention schedule, cost degradation ladder, compliance
map): [Governance deep dive](../../governance/00-governance-and-audit.md).

## Consequences

- (+) The platform's core promises (freshness, labels, retention, erasure) are now **contractual
  and provable**, not merely implemented — every regulated domain (Finance/HR/Legal/Audit) can be
  sold against a fixed, evidenced posture.
- (+) **R5 moves to design-mitigated:** metering + attribution + budget envelopes + a degradation
  ladder that is structurally forbidden from touching safety, so cost control can never regress into
  an R1/R3/R4 leak.
- (+) Adding no hot-path component keeps query latency untouched and decouples often-changing policy
  from stable mechanism (the ACL/label separation, generalized to the whole plane).
- (+) Audit-as-evidence gives a single design test for future controls ("can the log prove it?") and
  a ready auditor story (design + running proof per compliance cell).
- (+) Eval-gated model governance mirrors the connector gate — nothing (source or model) serves
  production without passing a gate.
- (−) Ratified numbers reduce per-deployment wiggle room; mitigated by explicit per-tenant/-regime
  overrides (tighten-only for labels).
- (−) Comprehensive audit is itself a storage-cost and privacy surface (retention + access control
  needed); accepted as the price of Principle 5 and of provability.
- (−) Policy changes are a recorded config deploy, not a live toggle — deliberate, but slower than a
  runtime switch.
- (−) The actual **prices, budget-envelope sizes, and eval thresholds** remain commercial/empirical
  inputs, tuned in [Deployment](../../deployment/) with real telemetry (residual of G1/G5).

## Alternatives

- **Leave SLA/retention as per-deployment config** — rejected: an un-promised SLA can't be a
  contract or an incident; a ratified default with overrides is both firm and flexible.
- **Label policy inside the authorization predicate** — rejected: couples volatile compliance policy
  to the stable identity predicate ([Permissions §7](../../permissions/00-authorization-model.md)).
- **Erase the audit trail on a GDPR request** — rejected: erasure applies to content, not to the
  non-repudiation record; retaining the *event* (not the content) is the standard balance.
- **Hard budget cut-off** — rejected: a cliff harms availability and could pressure a safety
  shortcut; a capability-before-safety ladder is the fail-closed-on-spend design.
- **A runtime governance service on the hot path** — rejected: latency + a new failure point on
  every query; policy is compiled config consumed by existing enforcement points.
- **Per-domain bespoke compliance write-ups** — rejected: re-derives controls per pack (the Vision
  anti-pattern); a shared, evidence-backed control map that packs inherit is the "pack not redesign"
  posture.
- **Model governance by allowlist only** — rejected: admits a regressed model; an eval gate is
  required before promotion.

## Revisit when

- **Real usage telemetry lands** → set the actual prices, budget-envelope sizes, and per-tier SLA
  capacity in [Deployment](../../deployment/); fold back if a ratified number proves unmeetable at
  cost.
- **Open Q#3 (model hosting) is decided** → the approved-model registry (§8) gains the concrete
  in-boundary-vs-managed-private posture per tenant tier; may warrant its own ADR.
- **A new regime or the EU AI Act obligation** applies → add a compliance-map row + any genuinely
  new control (scoped addition, not redesign).
- **A tenant tier needs a tighter SLA** → ratify the number here; Deployment sizes to it (no ADR
  change — [Workers §13](../../workers/00-ingestion-architecture.md) already expresses the knob).
- **Sustained budget-degradation events** in production → tune envelope sizes / degradation
  thresholds (policy tuning, not redesign).
