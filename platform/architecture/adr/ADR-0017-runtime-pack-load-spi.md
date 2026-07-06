# ADR-0017 — Runtime pack-load SPI: a validating, fail-closed loader that makes the pack contract executable

- **Status:** Accepted (Cycle 21)
- **Deciders:** Platform Architecture, Enterprise Architecture, Security & Governance, Data Architecture, Platform Engineering
- **Relates to:** [ADR-0016](ADR-0016-domain-pack-contract.md) (the *architectural* pack
  contract this SPI **enforces** — ADR-0016 §"Revisit when" explicitly names this ADR),
  [ADR-0013](ADR-0013-canonical-metadata-lineage-schema.md) (the closed label schema §2
  registers into; write-boundary validation reused), [ADR-0012](ADR-0012-governance-audit-and-cost.md)
  (the label→action matrix §3 tightens; model-version pinning pattern reused for pack
  versions), [ADR-0011](ADR-0011-ingestion-workers-and-connector-framework.md) (the
  conformance suite the loader feeds; the staged-DAG shape the load lifecycle mirrors),
  [ADR-0008](ADR-0008-canonical-principal-acl-model.md) (the `map_acl` fidelity a pack
  declares, never redefines), [ADR-0010](ADR-0010-storage-topology-and-tenancy.md) (the
  filter-only `VectorIndex` port that makes an unfiltered path unrepresentable),
  [ADR-0014](ADR-0014-api-contract-surface.md) (admin-can-only-tighten; the additive `pack`
  hint), [Pack-load SPI design](../../packs/01-pack-load-spi.md), [Packs skeleton](../../packs/README.md)

## Context

[ADR-0016](ADR-0016-domain-pack-contract.md) fixed *what a pack is allowed to be* — six
additive sections, tighten-only, a §0 horizontal-change ledger — and the ten Seeded domain
packs (Cycles 11–20) proved that contract on paper: every one carries a `§0 = "none, all
additive"` ledger. But ADR-0016 deliberately deferred the **runtime plugin mechanism** (how
a pack is *loaded*) to the engineering track ([open Q#6](../../NEXT_STEPS.md)), and named it
in its own "Revisit when": *"A runtime pack SPI is built → add an ADR for the plugin
mechanism; it must enforce this contract, and this ADR becomes its specification."*

That gap is now the highest-leverage open item. A paper pack governs nothing: today a
`restricted:mnpi` label or a SAP fidelity fixture lives only in prose, hand-copied into ten
horizontal configs by humans — reintroducing the exact per-domain drift ADR-0016 exists to
kill. The pack contract is only as strong as the mechanism that installs it. The decision
this ADR fixes: **what is the loader, and how does it make *tighten-only* an executable gate
rather than a review-time promise?**

## Decision

**A pack is loaded by a validating, transactional, fail-closed SPI that installs each of the
six sections into its existing horizontal extension point, and structurally rejects any pack
that would loosen a floor.** The loader adds **no hot-path component**; it is a control-plane
mechanism writing into stores that already exist.

1. **The pack artifact is a signed, versioned, content-addressed bundle** (not the Markdown
   spec) carrying the machine-readable projection of the six sections — **data + declarative
   config only, no read-path code.** A pack *references* an already-built, independently
   conformance-gated Connector implementation; it never ships one. New connector code is a
   platform PR through the connector gate, not a pack load.

2. **The load lifecycle is a staged, transactional pipeline** — RESOLVE → VALIDATE → DRY-RUN
   → COMMIT (atomic) → ACTIVATE (tenant-scoped) — mirroring the ingestion DAG. **All six
   sections commit in one transaction or none do:** partial installation is the one state
   that could transiently loosen a floor, so it is unrepresentable.

3. **VALIDATE is the safety gate: six validators, one invariant.** Each section is checked
   `⊆` its extension point — §1 fixtures against the [conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
   (no `allow` broader than its principal set), §2 values against the [closed label
   grammar](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3),
   §3 deltas against the [label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)
   (tighten-only), §4 rows against the [control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain),
   §5 corpus for the mandatory permission-negative class, §6 hint as additive metadata only.
   The composite invariant is ADR-0016 §2 made executable: **an accepted pack can only
   subtract capability.**

4. **The loader is safe by construction, not by decision.** Its only verbs are
   subset-installs into fail-closed extension points: the `VectorIndex` port has no
   unfiltered method to bind, the label schema is a closed grammar (an unregistered value
   → DLQ), the matrix composes most-restrictive-wins (a widening delta is a no-op or a
   rejected write). The gate is the belt; the closed extension points are the suspenders.

5. **The §0 ledger is machine-checked.** A pack loads on the standard path only if its
   manifest ledger equals `"none, all additive."` A pack claiming a horizontal change (the
   falsifiability rule firing) is routed to a **human ADR gate** — refused until a
   horizontal ADR raises the floor it needs. ADR-0016's falsifiability rule becomes an
   enforced control-flow branch.

6. **Versioning, hot-load, rollback.** Per-tenant-pinnable `pack_version` (reusing the
   [model-version pinning pattern](../../governance/00-governance-and-audit.md#8-g6--model-governance))
   + an SPI `schema_version` gated by `min_platform_schema`. A pack loads with **no code
   deploy** (validated data + a route flip); rollback is a route-flip to the additive prior
   version; unload is fail-closed (a live label blocks its own removal). Every load is a
   signed, audited governance event.

**The SPI's own falsifiability check** (mirroring the pack rule): *can a pack load with no
code deploy, and is a floor-loosening pack structurally rejected by the loader?* — **yes to
both**, by (4) and (6).

## Consequences

- (+) **The pack contract becomes executable.** *Tighten-only* is a rejected write, not a
  review convention; the worst a bad or malicious pack does is fail to load (availability),
  never loosen a floor (safety) — fail-closed applied to extensibility itself.
- (+) **Onboarding a domain is a config operation** end to end: with connectors already
  built, a new pack loads with no deploy — the founding bet realized in running behaviour,
  not just on paper.
- (+) **Every load is provable** (signature + plan diff + conformance result + audit event):
  "which pack version governs this tenant, and did it ever loosen a floor?" is a query.
- (+) **The `core/` code-reconciliation now has a concrete first target** — the loader is the
  smallest `platform/`→`core/` mechanism that turns the paper contract into running code.
- (−) **A Markdown↔bundle build-step lockstep** is extra machinery; mitigated by generating
  the bundle from the pack's Markdown tables so there is one hand-authored source.
- (−) **Some domains still need a platform deploy** (a genuinely new connector); deliberate —
  shipping read-path code in a pack is the exact door the SPI keeps shut.
- (−) **The atomic six-section commit is heavier** than incremental installs; chosen because
  partial installation is the only floor-loosening transient, and transactionality removes it.

## Alternatives

- **Hand-install packs into ten configs (status quo).** Rejected: reintroduces per-domain
  drift; the contract is unenforced.
- **A general code-plugin system (packs ship read-path code).** Rejected: equates "load a
  pack" with "run untrusted code on the retrieval path" — unbounded attack surface, direct
  violation of the no-hot-path-component rule.
- **Trust the author, validate in PR review only.** Rejected: turns a safety property into a
  human-vigilance property; the SPI's whole value is *structural* rejection.
- **Per-section non-atomic installs.** Rejected: a partially-installed pack is a transient
  loosening — the one state the platform must never occupy.
- **Doc-contract only, no SPI (defer indefinitely).** Rejected now (was correct at ADR-0016):
  with the pack surface complete, the unenforced contract is the binding constraint on
  turning ten paper packs into a capability.

## Revisit when

- **A pack legitimately needs a horizontal change** → the §0 ledger machine-check fails and
  routes to the ADR gate; raise the horizontal ADR, move the floor, then the pack loads
  clean. (This ADR's loader is *how* that gate is enforced.)
- **A seventh pack section / new section grammar is needed** → an SPI `schema_version` bump
  with a new validator (additive, `min_platform_schema`-gated), not a loader rewrite.
- **A pack marketplace / external publishers** → extend the trust model (§4.3 of the design)
  into a publisher-allowlist + revocation; the signed content-addressed bundle already is the
  distributable shape.
- **The `core/` implementation lands** → this ADR is its specification; any deviation the
  implementation forces is a new ADR, not a silent drift.
