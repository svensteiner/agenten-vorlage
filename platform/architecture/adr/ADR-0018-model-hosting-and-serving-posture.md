# ADR-0018 — Model hosting & serving posture: a dual-track fabric, routed per (tenant tier × data class) behind the Model Gateway

- **Status:** Accepted (Cycle 22)
- **Deciders:** Platform Architecture, Security Architecture, Data Architecture, Enterprise Architecture, Platform Governance
- **Relates to:** [ADR-0003](ADR-0003-model-gateway-indirection.md) (the Model Gateway
  choke point this posture rides on — its "revisit-when" anticipated the serving-substrate
  question), [ADR-0012](ADR-0012-governance-audit-and-cost.md) (the approved-model registry +
  eval-before-promotion gate + label→trust routing this posture fills the open field of),
  [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (the ACL filter runs *before* any model
  sees content — hosting never touches the read gate), [ADR-0010](ADR-0010-storage-topology-and-tenancy.md)
  / [ADR-0015](ADR-0015-deployment-dr-and-regional-topology.md) (residency class + isolation tiers
  this routing honors), [Model Hosting & Serving design](../../models/00-model-hosting-and-serving.md),
  [Governance §8](../../governance/00-governance-and-audit.md#8-g6--model-governance)

## Context

Every mechanism *downstream* of a model call was fixed in earlier cycles.
[ADR-0003](ADR-0003-model-gateway-indirection.md) made the **Model Gateway the single choke point**
for all inference; [ADR-0012](ADR-0012-governance-audit-and-cost.md) / [Governance §8](../../governance/00-governance-and-audit.md#8-g6--model-governance)
made **no model serve production until it is in the approved-model registry with an eval score**,
and made **routing a function of the data class** (`confidential`/`pii` → highest-trust tier).
What none of them fixed is the **serving substrate**: does inference physically run on GPUs *inside*
the trust boundary, or on a *contractually-private managed endpoint* reached over private networking?

This is **open Q#3**, tracked since Cycle 7. Governance §8 recorded it as the one un-closed field of
the registry — the `hosting_posture` — and deferred the concrete decision. [Principle 1](../00-vision-and-principles.md)
already admits *both* options ("Models run in-boundary **or** via a contractually-private endpoint");
the platform surface is otherwise complete (all ten domain packs Seeded, the pack-load SPI designed),
so this is now the highest-leverage open item on the architecture-doc track. The decision to fix:
**which serving substrate, for which tenant tier and data class, and how the choice is *enforced*
rather than trusted.**

## Decision

**The platform serves models through a dual-track serving fabric, with the track selected per
`(tenant tier × data class)` by the existing label→trust matrix, resolved and enforced by the Model
Gateway, and recorded as a closed `hosting_posture` field on every approved-model registry entry.**
Neither track is a public API; both satisfy "private by default." The choice is a routing-policy
value behind the Gateway — no new hot-path component.

1. **Two tracks, both private.**
   - **Track A — in-boundary self-hosted OSS:** open-weight models on **reserved GPUs inside the
     trust boundary** (VPC / sovereign / on-prem). Privacy and residency hold **by construction** —
     there is no endpoint to egress to. Higher fixed (reserved-GPU) cost + model-ops burden.
   - **Track B — contractually-private managed endpoint:** a managed model service over **private
     networking** (no public internet) under **zero-retention / no-training** contractual terms;
     `managed_private_dedicated` for a single-tenant deployment. Frontier capability + elastic,
     privacy by contract + network isolation, per-token cost.

2. **`hosting_posture` is a closed registry enum** — `{in_boundary_oss, managed_private,
   managed_private_dedicated}` — recorded per model version. A `managed_private*` entry **must**
   carry its data-handling terms (DPA, retention = 0, training = none, sub-processor list); the eval
   gate refuses to promote one whose terms field is empty. This turns "contractually private" into a
   recorded, auditable fact.

3. **Routing is per `(tenant tier × data class)`, tighten-only.**
   - **Isolated** tier → **Track A only** (dedicated in-boundary pool), every class — matches the
     [Governance §9 sector row](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain).
   - **Standard** tier → default Track B (`managed_private`, cheaper-bulk) for `public`/`internal`;
     a **data-class floor** lifts `confidential`/`pii` to the highest-trust track (Track A pool or
     `managed_private_dedicated`). A tenant may pin stricter, never route a sensitive class down
     (the [admin-can-only-tighten](ADR-0014-api-contract-surface.md) rule applied to model routing).
   - Selection is a **registry query** — the Gateway picks the highest-trust *approved* model whose
     posture satisfies the required floor for `(tenant, class, role)`. Adding a track/model is a
     registry entry, not a Gateway change.

4. **Fail closed on availability (M5).** If the required track is unavailable, the request degrades
   *within the same-or-higher trust tier* or is queued/denied — it **never** falls back to a
   lower-trust track. A `pii` request whose Track A pool is down does not spill to Track B. The
   [degradation ladder](../../governance/00-governance-and-audit.md) may only pick a cheaper tier
   *from tracks that still satisfy the data-class floor*.

## Consequences

- (+) **Q#3 is closed** with the honest answer — *both, by tier and data class* — and it is
  expressible as pure policy because [ADR-0003](ADR-0003-model-gateway-indirection.md) built the
  indirection first: hard to decide, trivial to wire.
- (+) **Both a sovereign Isolated tenant and a cost-sensitive Standard tenant are served without
  redesign** — the "supportable without redesign" test met on the hosting axis.
- (+) **Hosting posture becomes provable:** the `hosting_posture` + data-handling-terms field plus
  the model+posture stamp on every audit event make "did any request route below its floor?" a
  query, not an assertion.
- (+) **No new hot-path component, no new predicate.** Two data values (the enum + the per-tier map)
  and one boundary condition (fail-closed fallback); callers unchanged; the ACL/read plane untouched.
- (−) **Two serving stacks to operate** (GPU/model ops for A; endpoint/contract management for B) —
  accepted as the price of covering both mandates.
- (−) **Routing correctness is now safety-relevant** — a mis-route of `pii` to a lower-trust track is
  a reportable event; mitigated by making routing a registry+matrix query, the fail-closed rule, and
  a conformance/eval class asserting no `pii` fixture ever routes to a `managed_private` posture.
- (−) **Track B carries a vendor-concentration exposure** (R7), bounded to one Gateway adapter (the
  model analogue of the `VectorIndex` port).

## Alternatives

- **Single global in-boundary OSS only.** Rejected as default: caps capability for every tenant and
  pays reserved-GPU cost for bulk work a managed tier serves cheaper. Retained *as the whole posture
  for the Isolated tier.*
- **Single global managed-private only.** Rejected: cannot give Isolated/sovereign tenants *physical*
  possession; concentrates all inference on one vendor.
- **Public model API + connectors.** Rejected by [Principle 1 / Vision §5](../00-vision-and-principles.md):
  uncontrolled egress is unacceptable for Finance/HR/Legal/Audit.
- **Per-service model choice (no Gateway routing).** Rejected: re-scatters the choke point
  [ADR-0003](ADR-0003-model-gateway-indirection.md) consolidated; the data-class floor would be
  re-implemented per service and bypassable.
- **Fail-open fallback (spill to a cheaper track under load).** Rejected: converts an availability
  event into a safety leak — the exact failure the platform exists to prevent.
- **Leave hosting a per-deployment secret (status quo).** Rejected: an un-recorded posture can't be
  audited or eval-gated; the closed registry field with attached terms is what makes "contractually
  private" evidence rather than assurance.

## Revisit when

- **A new serving substrate becomes attestable** (confidential-computing enclaves / TEEs that make a
  managed endpoint *physically* provable) → add a new `hosting_posture` value with its own trust rank
  in the matrix; the routing rule is unchanged.
- **A new model class** (multimodal, long-context, reasoning specialist) → a new registry entry +
  eval score + posture, not a re-decision.
- **Inference moves on-device / in-process** → the case [ADR-0003 "revisit-when"](ADR-0003-model-gateway-indirection.md)
  already named: the Gateway becomes an in-process policy layer, but this posture field stays.
- **A managed vendor's terms change** (retention/training/sub-processors) → registry re-eval and, if
  breached, de-approval — the model analogue of a connector conformance-canary auto-quarantine.
