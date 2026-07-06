# Model Hosting & Serving

> Status: **Foundational** · Owner: Platform / Security / Data Architecture · Cycle: 22
> Implements [ADR-0018](../architecture/adr/ADR-0018-model-hosting-and-serving-posture.md).
> **Resolves open Q#3** (model hosting — in-boundary OSS vs. contractually-private managed,
> per tenant tier), left open since [Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance)
> recorded it as the one un-closed field of the approved-model registry.
> This document does **not** re-open the [Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md)
> indirection, the [label→trust routing matrix](../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen),
> or the [approved-model registry](../governance/00-governance-and-audit.md#8-g6--model-governance) —
> it **fills the one field those mechanisms left open**: *where the model physically runs, per
> tenant tier, and how a request is routed to the right serving track by data class.*

Model **hosting** is the last open horizontal decision on the platform-surface side (the only
peers are the `core/` code-reconciliation and open Q#6, the orchestrator posture). Everything
downstream of a model call was fixed in earlier cycles: [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md)
made the **Model Gateway the single choke point**; [Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance)
made **no model serve production until it is in the approved-model registry with an eval score**;
[Governance §4/§7.1](../governance/00-governance-and-audit.md) made **routing a function of the
data class**. What none of them fixed is the **serving substrate**: does inference run on GPUs
*inside* the trust boundary, or on a *contractually-private managed endpoint* reached over private
networking? [Principle 1](../architecture/00-vision-and-principles.md) already admits **both**
("Models run in-boundary **or** via a contractually-private endpoint") — this document closes
*which, for whom, and how the choice is enforced rather than trusted.*

---

## 1. What model hosting must satisfy (inputs, not choices)

These are hard requirements inherited from earlier cycles. A hosting design that violates any of
them has failed its one job.

| # | Requirement | Source | Why it binds hosting |
|---|-------------|--------|----------------------|
| M1 | **Private by default** — no customer data (prompt, retrieved content, embedding) egresses the trust boundary without an explicit, logged, policy-approved egress. | [Principle 1](../architecture/00-vision-and-principles.md), [Vision §5](../architecture/00-vision-and-principles.md) | A public model API is disqualified outright; every serving track must be in-boundary **or** contractually-private with private networking. |
| M2 | **The Model Gateway is the only caller.** No service calls a serving endpoint directly. | [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md), [Principle 6](../architecture/00-vision-and-principles.md) | Hosting is a set of endpoints *behind* the Gateway's logical roles; the choice of track must be invisible to callers. |
| M3 | **Routing is a function of data class**, driven by the label matrix. | [Governance §4, §7.1, §8](../governance/00-governance-and-audit.md) | `confidential`/`pii` may not be sent to a lower-trust track; hosting must express a per-class trust ordering. |
| M4 | **Nothing serves until it passes the eval-before-promotion gate** and is in the registry with a recorded hosting posture + data-handling terms. | [Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance) | Hosting posture is a *registry field*, not a per-deployment secret; the gate is the model analogue of the connector conformance gate. |
| M5 | **Fail closed on any routing/availability ambiguity** — deny/queue, never silently fall back to a lower-trust track. | [Principle 7](../architecture/00-vision-and-principles.md), [Governance §7.3](../governance/00-governance-and-audit.md) (R5) | A `pii` request must never spill to a cheaper managed endpoint because the in-boundary pool is busy. |
| M6 | **Residency is honored** — a tenant's inference stays within its residency class. | [Deployment §7.2](../deployment/00-deployment-topology.md), [Storage §13](../storage/00-storage-architecture.md) | Hosting is where "in-boundary" becomes a *physical fact*, not a label — for the tenants that require it. |
| M7 | **No new hot-path component; no vendor lock-in.** | [Principle 6](../architecture/00-vision-and-principles.md), R7, [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) | Hosting adds serving *endpoints*, not a new runtime service; a track swap is an adapter change, never a caller change. |

---

## 2. The decision in one paragraph

**The platform serves models through a dual-track serving fabric — Track A (in-boundary,
self-hosted open-weight models on reserved GPUs inside the trust boundary) and Track B
(contractually-private managed endpoints reached over private networking) — with the track
selected per `(tenant tier × data class)` by the existing label→trust matrix, resolved and
enforced by the Model Gateway, and recorded as a closed `hosting_posture` field on every
approved-model registry entry.** Neither track is a public API; both satisfy M1. The choice is a
**routing-policy value behind the Gateway**, which is exactly why "both, by tier" costs nothing
architecturally — [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) built the
indirection precisely so the serving substrate can vary without any caller knowing.

---

## 3. The two serving tracks

```
                         ┌──────────────────────────────────────────────┐
                         │              Model Gateway (ADR-0003)          │
   caller (orchestrator, │   role → policy → track selection (§4)         │
   classifier, verifier, │   • token-bound tenant  • data class (labels)  │
   pack eval, SPI DRY-RUN)│   • registry lookup     • fail-closed (M5)     │
                         └───────────────┬───────────────┬────────────────┘
                                         │               │
                    highest-trust /      │               │  capability / elastic /
                    physical possession  │               │  cheaper-bulk
                                         ▼               ▼
                         ┌───────────────────────┐   ┌───────────────────────────┐
                         │  TRACK A               │   │  TRACK B                   │
                         │  In-boundary OSS       │   │  Contractually-private      │
                         │  open-weight models    │   │  managed endpoint           │
                         │  on reserved GPUs       │   │  (private networking:       │
                         │  inside the VPC /       │   │   PrivateLink / VPC peer;   │
                         │  sovereign region       │   │   zero-retention/no-train   │
                         │                         │   │   contractual terms)        │
                         │  privacy = physical      │   │  privacy = contract +       │
                         │  possession (M6 fact)   │   │  network isolation          │
                         └───────────────────────┘   └───────────────────────────┘
                                  in-boundary                 in-boundary-equivalent
                                  (M1 by construction)        (M1 by contract + M1 egress-gate)
```

### Track A — In-boundary, self-hosted open-weight models

Open-weight models (Llama / Mistral / Qwen-class and successors) run on **reserved GPU capacity
inside the tenant's trust boundary** (customer VPC, sovereign cloud, or on-premise).

- **Strengths:** maximum privacy — weights *and* inference are physically in-boundary, so M1/M6
  hold **by construction** (there is no endpoint to egress to); no per-token vendor cost; residency
  is a physical fact; strongest posture for regulated/sovereign tenants and for `confidential`/`pii`.
- **Costs:** reserved-GPU **fixed cost** (idle capacity still bills), an operational burden (model
  ops, quantization, scaling, patching), and a possible **capability gap** vs. frontier models on
  the hardest reasoning tasks.

### Track B — Contractually-private managed endpoints

A managed model endpoint (e.g. a cloud provider's dedicated/private model service) reached over
**private networking** (no traversal of the public internet), under a contract that guarantees
**zero data retention and no training on customer data**, and — for the strictest sub-case — a
**single-tenant dedicated deployment**.

- **Strengths:** frontier capability, elastic scale, no GPU operations; ideal for `public`/`internal`
  bulk work and for Standard tenants who want top capability without running a GPU fleet.
- **Costs:** privacy rests on **contract + network isolation**, not physical possession (the DPA /
  zero-retention / no-train terms must be recorded and audited — M4); residency is a *region +
  contract* fact, not a possession fact; per-token cost; a vendor-concentration exposure (R7),
  bounded by the Gateway adapter.

### The `hosting_posture` registry field (closes M4)

Q#3 was, precisely, the *hosting-posture* field of the [approved-model registry](../governance/00-governance-and-audit.md#8-g6--model-governance)
left open. It is now a **closed enum**, recorded per model version:

| `hosting_posture` | Track | Privacy basis | Typical use |
|-------------------|:-----:|---------------|-------------|
| `in_boundary_oss` | A | Physical possession (weights + inference in-boundary) | Isolated/sovereign tenants; `confidential`/`pii` for any tenant |
| `managed_private` | B | Contract (zero-retention/no-train) + private networking | Standard tenants; `public`/`internal` bulk; capability-critical roles |
| `managed_private_dedicated` | B | Contract + private networking + single-tenant deployment | Standard tenants with elevated needs short of full Isolation |

A registry entry with `managed_private*` **must** carry its data-handling terms (DPA reference,
retention = 0, training = none, sub-processor list); the eval gate refuses to promote a managed
model whose terms field is empty. This makes M1's "contractually-private" a *recorded, auditable
fact*, not a verbal assurance.

---

## 4. Routing: per `(tenant tier × data class)`

The posture is **not a single global choice** — it is a per-tenant-tier default overlaid with a
per-data-class trust floor, resolved by the *existing* label→trust matrix ([Governance §4/§7.1](../governance/00-governance-and-audit.md)).
The Gateway computes the track at call time from the token-bound tenant + the data class of the
material being sent.

| Tenant tier | `public` / `internal` | `confidential` / `pii` | Rule |
|-------------|-----------------------|------------------------|------|
| **Isolated** (regulated: finance-supervisory, HIPAA-like, sovereign) | Track A (dedicated in-boundary pool) | Track A (dedicated in-boundary pool) | **Track A only.** Nothing leaves physical possession. Matches the [Governance §9 sector row](../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain) ("dedicated model pool"). |
| **Standard** | Track B (`managed_private`, cheaper-bulk tier) | **highest-trust track** — Track A pool **or** `managed_private_dedicated`, per tenant policy | Default Track B for capability/cost; a **data-class floor** lifts `confidential`/`pii` to the highest-trust track. This is [Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance) "routing by data class" made concrete. |

- **The data-class floor is tighten-only** — a tenant may pin *everything* to Track A (stricter),
  but may **never** route `confidential`/`pii` down to a cheaper track (the [admin-can-only-tighten](../architecture/adr/ADR-0014-api-contract-surface.md)
  rule applied to model routing).
- **Selection is a registry query, not code:** the Gateway picks the highest-trust *approved*
  model whose `hosting_posture` satisfies the required floor for `(tenant, class, role)`. Adding a
  track or a model is a registry entry, not a Gateway change (M7).

### Fail-closed routing (M5)

If the required track is unavailable — the in-boundary GPU pool is saturated, or the managed
endpoint is unreachable — the request **degrades within the same-or-higher trust tier, or is
queued/denied; it never falls back to a lower-trust track.** A `pii` request whose Track A pool is
down does **not** spill to Track B `managed_private`; it waits or fails. This is the model-serving
projection of the platform-wide safety invariant: **capability (and availability) may degrade;
the trust floor may not** ([Governance §7.3](../governance/00-governance-and-audit.md), R5). The
degradation ladder ([Governance §7.3](../governance/00-governance-and-audit.md)) already degrades
*to a cheaper model tier*; this document adds the boundary condition that "cheaper tier" is only
ever selected from tracks that still satisfy the data-class floor.

---

## 5. Why this changes nothing horizontal

Consistent with every cycle since ADR-0016: **net horizontal change = none, all additive.**

- **No new hot-path component.** Track A and Track B are *serving endpoints* behind the existing
  Model Gateway; the registry, the label matrix, and the routing policy already exist. This
  document fixes **two data values** — the `hosting_posture` enum and the per-tier default routing
  map — and **one boundary condition** (fail-closed track fallback). Callers are unchanged; they
  still request a logical role and never learn which track answered (M2).
- **No new predicate, no new principal category.** Routing consumes the *existing* data-class labels
  and the *existing* tenant tier; it introduces no new axis.
- **The `VectorIndex`/permission planes are untouched.** Hosting is about *where inference runs*,
  not *what content is retrievable* — the ACL filter runs before any model sees anything, on either
  track. A mis-hosted model can, at worst, cost capability or (if the fail-closed rule were broken)
  leak *to a vendor under contract*, never widen a user's read access.
- **This is the payoff of [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md).**
  "Both, by tenant tier" is expressible as pure policy *only because* the Gateway indirection was
  built first. Q#3 was hard to *decide* and trivial to *wire* — the sign of a good earlier decision.

---

## 6. Trade-offs

- **Physical possession vs. frontier capability.** Track A maximizes privacy and residency-as-fact
  but may trail frontier reasoning and carries reserved-GPU fixed cost; Track B maximizes capability
  and elasticity but rests privacy on contract + network isolation. The dual-track routing takes
  each where it is strongest instead of forcing one global compromise.
- **Two serving stacks vs. one.** Operating both Track A (GPU/model ops) and Track B (endpoint/
  contract management) is more surface than a single track. Accepted: it is the only posture that
  serves *both* a sovereign Isolated tenant *and* a cost-sensitive Standard tenant without redesign
  — the "supportable without redesign" test ([Vision §6](../architecture/00-vision-and-principles.md)).
- **Routing correctness is now safety-relevant.** A mis-route of `pii` to a lower-trust track is a
  reportable event. Mitigated by making routing a **registry+matrix query** (not bespoke code), by
  the fail-closed fallback rule (M5), and by an **eval/conformance class that asserts no `pii`
  fixture is ever routed to a `managed_private` posture** (the model-routing analogue of the
  permission-negative conformance class). Every model call already records model+posture in the
  audit event ([Governance §6.1/§8](../governance/00-governance-and-audit.md)), so "did any request
  ever route below its floor?" is a query, not an assertion.
- **Vendor concentration (Track B) vs. ops burden (Track A).** Track B concentrates on a managed
  vendor (R7); Track A moves that risk onto internal ops. The Gateway adapter bounds the Track B
  lock-in to one adapter (the model analogue of the `VectorIndex` port); Track A's ops burden is
  bounded by using open-weight models with commodity serving runtimes.

---

## 7. Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Single global in-boundary OSS only** | Rejected as the default: caps capability for *every* tenant (including those with no regulatory need), and pays reserved-GPU cost for `public`/`internal` bulk that a managed tier serves cheaper. Over-provisions privacy where it isn't required. It **remains** the whole posture for the Isolated tier. |
| **Single global managed-private only** | Rejected: cannot satisfy Isolated/sovereign tenants who require *physical* in-boundary possession (M6), and concentrates all inference on one vendor (R7). Privacy-by-contract is insufficient where the mandate is physical. |
| **Public model API + connectors** | Rejected by [Principle 1 / Vision §5](../architecture/00-vision-and-principles.md): uncontrolled data egress is unacceptable for Finance/HR/Legal/Audit. Never in scope. |
| **Per-service model choice (no Gateway routing)** | Rejected: re-scatters the choke point [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) consolidated — secrets, cost control, and the data-class floor would each be re-implemented per service and bypassable. |
| **Fail-open fallback (spill to a cheaper track under load)** | Rejected: converts an availability event into a safety event; a `pii` prompt reaching a lower-trust endpoint because a pool was busy is exactly the leak the platform exists to prevent (M5). |
| **Leave hosting a per-deployment secret (status quo)** | Rejected: an un-recorded posture can't be audited or eval-gated; making `hosting_posture` a closed registry field with attached data-handling terms is what turns "contractually private" into provable evidence (M4). |

---

## 8. Future scalability

- **A new model class** (multimodal, long-context, a reasoning specialist) is a **new registry
  entry with a `hosting_posture` + eval score**, routed by the same matrix — not a re-decision.
- **A new serving substrate** (e.g. confidential-computing enclaves / TEEs that make a managed
  endpoint *physically* attestable) slots in as a **new `hosting_posture` value** with its own trust
  rank in the matrix; the routing rule (highest-trust approved model satisfying the floor) is
  unchanged.
- **On-device / in-process inference** is the case [ADR-0003 "revisit-when"](../architecture/adr/ADR-0003-model-gateway-indirection.md)
  already named: the Gateway becomes an in-process policy layer, but the indirection — and this
  posture field — stay.
- **Empirical sizing is handed to [Deployment](../deployment/00-deployment-topology.md)** (see §9):
  Track A reserved-GPU pool sizing and Track B managed-endpoint pricing are numbers the cost model
  and the reference topology consume, exactly as the SLA-capacity and cost-envelope inputs were
  queued to Deployment in earlier cycles — a tuning input, not a redesign.

---

## 9. What this hands to other documents

- **[Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance):** the
  `hosting_posture` enum + mandatory data-handling-terms field close the one open registry field;
  the per-tier×class routing map is the concrete form of "routing policy by data class."
- **[Deployment §7](../deployment/00-deployment-topology.md):** Track A reserved-GPU pool sizing (a
  reserved-capacity class alongside reserved-P0) and Track B endpoint pricing/region routing feed
  the versioned pricing/envelope manifest (D4) and the residency map (§7.2).
- **[Security](../security/00-security-architecture.md):** Track B private-networking (PrivateLink/
  VPC-peering) + zero-egress verification, and Track A GPU-pool tenant isolation, are the network/
  boundary controls that make M1 physical (a follow-up hardening item, see NEXT_STEPS §6).
- **[Pack-load SPI §5](../packs/01-pack-load-spi.md):** a pack's eval gate consumes whatever the
  approved-model registry holds — orthogonal to hosting, now fully specified on the hosting side.

## Related

- [ADR-0018](../architecture/adr/ADR-0018-model-hosting-and-serving-posture.md) — the decision record.
- [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) — the Gateway indirection this posture rides on.
- [Governance §8](../governance/00-governance-and-audit.md#8-g6--model-governance) — the approved-model registry & eval gate.
- [Vision & Principles §4](../architecture/00-vision-and-principles.md) — Principle 1 (private by default), Principle 6 (model-pluggable).
