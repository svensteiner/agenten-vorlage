# ADR-0016 — Domain pack contract: a pack is additive data + policy, never a horizontal change

- **Status:** Accepted (Cycle 11)
- **Deciders:** Platform Architecture, Enterprise Architecture, Security & Governance, Data Architecture
- **Relates to:** [ADR-0002](ADR-0002-reuse-existing-template-core.md) (the core/project
  split this generalizes into pack/horizontal), [ADR-0004](ADR-0004-permission-faithful-retrieval.md)
  (the floor a pack may never loosen), [ADR-0008](ADR-0008-canonical-principal-acl-model.md)
  (a pack adds a connector + conformance fixtures, not a new predicate),
  [ADR-0013](ADR-0013-canonical-metadata-lineage-schema.md) (a pack *registers* label values
  into the closed vocabulary), [ADR-0012](ADR-0012-governance-audit-and-cost.md) (a pack
  *inherits* compliance rows + *tightens* the label matrix), [ADR-0014](ADR-0014-api-contract-surface.md)
  (a pack is additive on the wire — the `pack` hint), [Vision §2–§3](../../architecture/00-vision-and-principles.md)
  (the founding bet), [Packs skeleton](../../packs/README.md), [Finance pack](../../packs/finance/00-finance-pack.md)

## Context

The platform's founding thesis — *"a new domain is delivered by configuration and content
packs, not by re-architecting the platform"* ([Vision §2](../../architecture/00-vision-and-principles.md)) —
had been **asserted in ten cycles and proven in none**. Every horizontal surface
(permissions, rag, storage, workers, metadata, api, deployment, governance) is now Seeded,
so the highest-leverage move is to make the bet **concrete, enforceable, and falsifiable**
before ten domain teams build packs ad hoc.

Left unspecified, "domain pack" would drift: one team would add a Finance-only retrieval
path, another a bespoke compliance write-up, a third a new required API field "just for HR."
Each is individually reasonable and collectively fatal — they turn the horizontal platform
back into per-domain forks, the exact anti-pattern the platform exists to kill. The decision
that shapes **all ten horizontal surfaces at once** is: *what, precisely, is a pack allowed
to be?*

## Decision

**A domain pack is additive data + policy projected onto the existing horizontal surfaces
through their already-built extension points. It may only tighten. It is exactly six
sections, and it carries a horizontal-change ledger proving it changed no horizontal
contract.**

1. **The six-part contract.** Every pack is the same six sections, each plugging into one
   pre-existing extension point ([Packs skeleton](../../packs/README.md)):
   (1) sources + `map_acl` fidelity target + conformance fixtures;
   (2) classification-registry values it registers;
   (3) label→action *tighten* deltas;
   (4) compliance-map rows it declares + inherits;
   (5) retrieval/answer eval set + per-content-type parsers;
   (6) an optional additive API `pack` hint.

2. **Tighten-only, never loosen.** A pack can subtract capability (stricter labels, a
   dedicated model pool, an egress block) but can **never** widen a label, disable the ACL
   filter, relax an SLA, add a hot-path component, or introduce a new store. This preserves
   every platform floor ([ADR-0004](ADR-0004-permission-faithful-retrieval.md),
   [Permissions §7](../../permissions/00-authorization-model.md), [Governance §4](../../governance/00-governance-and-audit.md)).

3. **The horizontal-change ledger is mandatory (§0).** Each pack lists every horizontal
   document it touched; the required value is **"none, all additive."** The ledger makes the
   bet auditable *per pack*, not just claimed platform-wide.

4. **The falsifiability rule.** If a pack cannot be expressed within (1)–(2), it has found a
   real gap in a horizontal surface. The remedy is a **horizontal ADR**, never a pack-local
   workaround. A pack that triggers this rule is a success of the process — it converts an
   unstated assumption into a tracked decision.

**Finance is the reference pack** ([Finance pack](../../packs/finance/00-finance-pack.md)):
its §0 ledger records **zero** horizontal changes while exercising the hardest mechanisms
(SAP row/record ACLs, the full label lattice, SOX/GDPR rows, SAP-table parsers). The bet
held against the worst case.

## Consequences

- (+) The founding bet is now a **contract with a test** (the §0 ledger), not a slogan. A PR
  that adds a pack with a non-additive ledger row is a reviewable, blockable event.
- (+) HR, Legal, Audit, KM, SAP, SharePoint, Email packs are **fill-in-the-blank** against
  the Finance template — onboarding a domain is bounded, estimable work.
- (+) The tighten-only rule means a pack **cannot become a leak vector**: the worst a
  misconfigured pack can do is over-restrict (a availability bug), never over-expose (a
  safety bug). This is the fail-closed posture applied to extensibility.
- (+) Compliance posture is **inherited + evidence-bound**, so a new regulated domain does
  not re-derive controls ([Governance §9](../../governance/00-governance-and-audit.md)).
- (−) The six-section straitjacket can feel rigid for a genuinely novel domain; mitigated by
  the falsifiability rule, which turns "the skeleton doesn't fit" into a first-class, tracked
  horizontal decision rather than a silent deviation.
- (−) The tighten-only rule means a domain that legitimately needs a *looser* default (rare)
  must change the horizontal floor via ADR — deliberately high-friction, because loosening a
  floor is exactly the decision that must not be made pack-locally.

## Alternatives

- **No formal pack contract (packs are "whatever a domain team needs")** — rejected: guarantees
  per-domain drift back into forks; the platform's whole value proposition dies. (Vision anti-pattern.)
- **Packs may add horizontal features "when justified"** — rejected: every fork is locally
  justified; the ledger's value is that it admits *no* horizontal change without a horizontal
  ADR, making the exception explicit and rare.
- **A code-plugin SPI instead of a doc contract** — deferred, not rejected: the runtime
  plugin mechanism (how a pack is *loaded*) is an engineering-track concern
  ([open Q#6](../../NEXT_STEPS.md)); this ADR fixes the *architectural* contract a plugin SPI
  must later enforce. Doc-contract-first keeps the decision ahead of the code.
- **Per-domain tenancy instead of packs-within-a-tenant** — rejected in
  [ADR-0010](ADR-0010-storage-topology-and-tenancy.md) (tenant = customer org; packs are
  scopes within it); this ADR is consistent with that boundary.

## Revisit when

- **A pack's §0 ledger legitimately needs a "required" horizontal change** → that is the
  falsifiability rule firing; raise the horizontal ADR it points to, then update this contract
  only if the *shape* of packs must change (not merely one surface).
- **A runtime pack SPI is built** (open Q#6 resolved) → add an ADR for the plugin mechanism;
  it must enforce this contract, and this ADR becomes its specification.
- **A domain needs a genuinely new label *dimension*** (not just a value) → that is a
  Metadata-schema change ([ADR-0013](ADR-0013-canonical-metadata-lineage-schema.md)), not a
  pack change; revisit the registry extension model there.
