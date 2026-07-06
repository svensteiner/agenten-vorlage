# The Runtime Pack-Load SPI — how a pack becomes a live capability

> **Status:** Seeded (Cycle 21). This is the **engineering form** of
> [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md): the doc contract
> fixed *what a pack is allowed to be* (six additive sections, tighten-only, a §0
> horizontal-change ledger); this document fixes *how a pack is loaded at runtime* and
> — the whole point — **how a floor-loosening pack is structurally rejected by the
> loader, not merely by review.** Ratified as [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md).

The ten domain packs proved the founding bet on paper. Each is a Markdown document whose
§0 ledger reads *"none, all additive."* But a paper pack governs nothing: today a
`restricted:mnpi` label, a SAP `map_acl` fidelity fixture, or a Finance tighten-delta
lives only in prose. The **pack-load SPI** is the code mechanism that reads those six
sections out of a machine-readable pack artifact and installs each one into the exact
horizontal extension point [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md)
named — under a validator that makes the contract's *tighten-only* rule an executable
gate rather than a promise.

This document answers **Why**, **How**, **Trade-offs**, **Alternatives**, and **Future
scalability**, per the [documentation contract](../README.md#documentation-contract).

---

## 1. Why an SPI at all (and why now)

**Why.** Without a loader, a pack is enforced by humans copying its prose into ten
horizontal configs. That reintroduces exactly the drift [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md)
exists to kill: a Finance engineer hand-edits the label schema, an HR engineer forgets a
conformance fixture, an Audit engineer widens a default "just this once." The pack
contract is only as strong as the mechanism that installs it. An SPI turns "the pack says
so" into "the platform enforces so, or refuses to load the pack."

**Why now.** With the [domain-pack surface complete](README.md) (Cycle 20), the SPI is the
single highest-leverage remaining move: it is the one piece that converts ten proven paper
packs into a runtime capability, and it is the **prerequisite** for the `core/`
code-reconciliation ([NEXT_STEPS §6 Cycle 2c](../NEXT_STEPS.md)). It also discharges the
engineering half of open **Q#6** (agent framework) by fixing how domain content plugs into
the runtime, independent of the orchestrator choice.

**The one non-negotiable requirement.** The loader is a **safety gate, not a convenience**.
Its correctness property is the same fail-closed posture every horizontal surface already
holds: *the worst a misconfigured or malicious pack can do is fail to load (an availability
event), never loosen a floor (a safety event).* Everything below is in service of that one
sentence.

---

## 2. The pack artifact — from prose to a validated bundle

A loadable pack is **not** the Markdown spec; the spec is the human-readable rationale.
The loadable artifact is a **signed, versioned bundle** whose contents are the
machine-readable projection of the six sections. The Markdown pack doc and the bundle are
kept in lockstep by a build step (§6.2), so the ledger and the loaded behaviour can never
silently diverge.

```
pack-finance-1.4.0.pack/            # a content-addressed, signed bundle
├── pack.manifest.json              # identity, version, section inventory, signature ref
├── 01-sources/
│   ├── connectors.yaml             # which Connector impls + config (NOT credentials)
│   └── conformance/                # §1 map_acl fidelity FIXTURES (the gate corpus)
│       ├── finance-sap-fico.jsonl
│       └── ...
├── 02-classification/
│   └── registry.json               # §2 restricted:<class> / pii_class:<type> / matter:<id>
├── 03-labels/
│   └── tighten-deltas.json         # §3 label→action deltas (tighten-only)
├── 04-compliance/
│   └── control-map.json            # §4 declared + inherited regime rows
├── 05-eval/
│   ├── eval-set.jsonl              # §5 retrieval/answer eval corpus
│   └── parsers.yaml                # §5 per-content-type parser bindings
└── 06-api/
    └── pack-hint.json              # §6 optional additive "pack" hint metadata
```

The bundle is **data + declarative config only** — it carries **no executable code on the
hot path** ([ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md) §2: a pack adds
no hot-path component). The *one* code-adjacent element is the connector **binding** in
`01-sources/connectors.yaml`, which names a Connector implementation and its non-secret
config; the implementation itself is a first-class, independently-versioned, already-
conformance-gated platform artifact ([Connector framework §3](../workers/01-connector-framework.md)),
**not** something the pack ships. A pack references a connector; it never *is* one. (See
§4.1 for why this is the sharp line that keeps a pack from becoming an arbitrary plugin.)

`pack.manifest.json` is the spine:

```json
{
  "pack_id": "finance",
  "pack_version": "1.4.0",
  "schema_version": 3,                       // the SPI contract version (see §5)
  "sections": { "1": "sha256:…", "2": "sha256:…", "…": "…" },
  "declares_registry": ["restricted:mnpi", "restricted:supervisory",
                        "pii_class:financial", "pii_class:tax"],
  "inherits_from": [],                        // e.g. Audit inherits Finance's SOX row
  "ledger": "none, all additive",             // the machine-checkable §0 claim
  "signature": "…",                           // provenance (see §4.3)
  "min_platform_schema": 3
}
```

---

## 3. The load lifecycle — five stages, fail-closed at each seam

A pack is loaded by a **staged pipeline that mirrors the ingestion DAG**
([Workers §2](../workers/00-ingestion-architecture.md)): each stage reads the prior stage's
validated output, and **any stage failing aborts the whole load — a pack is never
partially installed.** Partial installation is the one state that could loosen a floor
(e.g. a registry value installed but its tighten-delta dropped), so the loader is
**transactional**: all six sections commit together or none do.

```
┌─────────┐   ┌──────────┐   ┌─────────────┐   ┌──────────┐   ┌─────────┐
│ RESOLVE │──▶│ VALIDATE │──▶│  DRY-RUN /  │──▶│  COMMIT  │──▶│ACTIVATE │
│ bundle  │   │  ⊆ floor │   │   PLAN      │   │ (atomic) │   │ (scoped)│
└─────────┘   └──────────┘   └─────────────┘   └──────────┘   └─────────┘
   fetch +      the safety      compute the       write the      flip the
   verify sig   gate (§4)       diff, run the     6 sections     tenant→pack
   + schema     — fail here     conformance       in ONE txn     route; audit
   version      = reject        suite on the      to the SoT     the load as a
                                fixtures                         governance event
```

1. **RESOLVE.** Fetch the content-addressed bundle, verify its signature and
   `min_platform_schema`, and confirm every section hash in the manifest matches its file.
   A tampered or truncated bundle stops here.

2. **VALIDATE (the safety gate — §4).** Each section is checked `⊆` its horizontal
   extension point. This is where *tighten-only* becomes executable. A pack that tries to
   widen a label, disable a filter, relax an SLA, or register a value outside the schema's
   grammar is **rejected with a typed error** — it never reaches COMMIT.

3. **DRY-RUN / PLAN.** Compute the exact diff the load would apply (which registry values
   are new, which deltas tighten which cells, which fixtures join the gate corpus) and
   **run the pack's own conformance fixtures against the named connectors** in a sandbox.
   If any fixture would produce an *over-permissive* `map_acl` (an `allow` broader than the
   fixture's expected principal set), the load fails **closed** — identical to the
   [production canary](../workers/01-connector-framework.md#5-the-conformance-suite-is-the-production-gate-r1r6-primary-control)
   that auto-quarantines a drifting source. The plan is the reviewable artifact in CI
   (§6.1).

4. **COMMIT (atomic).** Write all six sections into the relational source of truth
   ([Storage §4.2](../storage/00-storage-architecture.md)) in **one transaction**, stamped
   with `pack_id` + `pack_version` + `job_trace_id`. Because the SoT already holds the
   [label schema](../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3),
   the [governance policy store](../governance/00-governance-and-audit.md), and the catalog,
   the pack's registrations live transactionally beside the contracts they extend — no
   lagging copy, no cross-store race.

5. **ACTIVATE (scoped).** Flip the `tenant → active-packs` route so retrieval, the label
   matrix, and the conformance gate begin honouring the new pack for that tenant only. The
   load is itself an **audited governance event** ([Governance §6](../governance/00-governance-and-audit.md)):
   who loaded which pack version, the plan diff, and the conformance result — so a pack
   activation is as provable as any other privileged change.

Rollback is the inverse route-flip to the prior `pack_version` (§5.2); because COMMIT is
versioned and additive, the prior version's rows are never overwritten, only deactivated.

---

## 4. The safety gate — six validators, one invariant

VALIDATE is the heart of the SPI. Each of the six sections has a **validator that proves it
is a subset of** its horizontal extension point. The composite invariant is
[ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md) §2 made executable:
**every accepted pack can only subtract capability.**

| § | Validator checks that… | Rejects (fails closed) when… | Extension point |
|:-:|------------------------|------------------------------|-----------------|
| **1** | every declared source binds a **registered** Connector impl; every conformance fixture is well-formed and its expected outcome is `allow`⊆known-principals / `deny` / `quarantine` | a fixture asserts an `allow` broader than its principal set, or names an unregistered connector, or omits the required cross-tenant/revocation cases | [Connector port](../workers/01-connector-framework.md) + [conformance suite](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate) |
| **2** | each registry value matches the **closed grammar** `restricted:<class>` / `pii_class:<type>` / `matter:<id>` and is **new or identical** (never a redefinition of an existing value's meaning) | a value is outside the grammar, or redefines an existing class, or introduces a new label **dimension** (that is a [Metadata ADR](../architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md), not a pack) | [closed label schema](../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3) |
| **3** | every label→action delta is a **tighten** — it may add a mask, a dedicated model pool, or an egress block, and may only move a cell toward *more* restrictive | a delta widens any cell, removes a mask, or downgrades a label vs. the platform default matrix | [label→action matrix](../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen) |
| **4** | declared regime rows resolve to existing control cells; inherited rows name a real ancestor pack | a compliance row claims a control the platform doesn't have, or inherits from a non-existent pack | [Governance control map](../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain) |
| **5** | the eval set is well-formed and its parser bindings name registered parsers; the set includes the mandatory **permission-negative** class | the eval corpus lacks permission negatives (a pack must be evaluable for *over*-serving), or binds an unknown parser | [eval-before-promotion gate](../governance/00-governance-and-audit.md#8-g6--model-governance) + [verifier](../rag/00-retrieval-pipeline.md) |
| **6** | the `pack` hint is **additive metadata only** — a routing/telemetry tag, never an access input | the hint is referenced by any access decision, or requires a new required API field | [additive versioning rule](../api/00-api-surface.md#11-versioning--deprecation-policy-a7) |

**The structural reason a floor-loosening pack cannot load** is that each validator checks
a *subset* relation against a floor the pack cannot see or address:

- The [`VectorIndex` port has no unfiltered method](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
  — so §1 cannot install a retrieval path that skips the ACL filter; there is no such
  method to bind.
- The label schema is a **closed grammar** — so §2 cannot register a value the matrix
  won't have an action for; an unregistered label is a [write-boundary violation → DLQ](../metadata/00-catalog-and-lineage.md#8-schema-versioning--validation-m6--the-anti-drift-discipline),
  the *same* mechanism a malformed `map_acl` hits.
- The matrix composes **most-restrictive-wins** — so §3's deltas are applied by
  intersection with the platform default; a "widening" delta is a no-op at worst and a
  rejected write at validation.

The loader therefore does not *decide* to be safe; it is **safe by construction**, because
the only operations it can perform are subset-installs into fail-closed extension points.
The gate is the belt; the closed extension points are the suspenders.

### 4.1 Why the connector is referenced, not shipped

The single most dangerous thing a plugin system can do is let a plugin ship arbitrary
code that runs on the read path. The SPI forecloses this: a pack's §1 **names** a Connector
implementation (already built, independently versioned, and itself conformance-gated), it
does not contain one. New source code (a genuinely new connector) is a **platform PR
through the connector framework's own gate**, not a pack load. This keeps the pack surface
exactly what [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md) promised —
data + policy — and keeps the attack surface of "load a pack" down to "install validated
declarative config," never "execute untrusted code."

### 4.2 The §0 ledger is machine-checked, not just asserted

`pack.manifest.json.ledger` must equal `"none, all additive"` for a pack to load on the
**standard path**. A pack claiming any horizontal change (the falsifiability rule firing)
cannot load through the SPI at all — it is routed to a **human ADR gate**: the load is
refused until a horizontal ADR is merged that *raises the floor the pack needs*, at which
point the floor moves and the pack once again reads "none, all additive" against the new
floor. This makes [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md)'s
falsifiability rule an **enforced control-flow branch**, not a review-time convention.

### 4.3 Provenance and trust

Each bundle is signed; the loader verifies the signature against the tenant's allowlisted
pack publishers before RESOLVE completes. This means the safety gate defends two distinct
threats: a *well-meaning but wrong* pack (caught by the six validators) and a *malicious*
pack (caught by signature + the same validators — a forged pack still cannot express a
floor-loosening operation). Loading is a privileged, audited, admin-can-only-tighten
operation ([API admin surface](../api/00-api-surface.md)); a pack load can never itself
raise a budget above ceiling, pin an un-evaluated model, or throttle a P0 revocation.

---

## 5. Versioning, hot-load, and rollback

### 5.1 Two version axes

- **`pack_version`** (e.g. `finance/1.4.0`) — the pack content. Additive by default: a new
  registry value or a tighter delta is a minor bump; a **removal** of a tighten (the only
  potentially-loosening pack change) forces the ADR gate (§4.2). Pack versions are
  **per-tenant pinnable** exactly like [model versions](../governance/00-governance-and-audit.md#8-g6--model-governance),
  so a tenant upgrades a pack on its own schedule.
- **`schema_version`** (the SPI contract itself) — bumped only when the *shape* of a pack
  changes (a seventh section, a new section grammar). A bundle declares
  `min_platform_schema`; the loader refuses a bundle newer than it understands. This is the
  [ADR-0013 anti-drift discipline](../architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)
  applied to the pack contract.

### 5.2 Hot-load without a code deploy — the falsifiability check for the SPI

The design's own falsifiability test (mirroring the pack falsifiability rule): **can a pack
be loaded with no code deploy, and is a floor-loosening pack structurally rejected by the
loader?** Both must be *yes* or the SPI has failed its purpose.

- **No code deploy → yes.** A pack is validated declarative data committed to the SoT and a
  route flip. Nothing is compiled or shipped; ACTIVATE is a config change the running
  platform picks up. (The *exception* that proves the rule: a pack needing a **new
  connector implementation** does need a platform deploy — but that is new *platform* code
  through the connector gate, not the pack, precisely per §4.1.)
- **Floor-loosening rejected structurally → yes.** Shown in §4: the loader's only verbs are
  subset-installs into fail-closed extension points; a loosening operation is unrepresentable
  or rejected at VALIDATE, never a matter of whether a reviewer noticed.

### 5.3 Rollback and unload

Because COMMIT is additive and versioned, rollback is a **route-flip to the prior
`pack_version`** — the prior rows were never deleted. A full **unload** (a tenant offboards
a domain) deactivates the route and schedules the pack's registry values and deltas for
retention-governed removal ([Governance §5](../governance/00-governance-and-audit.md));
content ingested under the pack follows the normal [erasure/lineage tombstone](../metadata/00-catalog-and-lineage.md#5-the-lineage-graph-m2-and-the-erasure-tombstone-m4)
path. Unloading a pack **cannot** orphan a label: a chunk still carrying a to-be-removed
`restricted:<class>` blocks the removal (fail-closed — a live label always has an action),
exactly the [total-matrix invariant](../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)
the schema guarantees.

---

## 6. How the SPI plugs into the existing pipeline (no new hot-path component)

The SPI adds **no runtime component to the read or write hot path**. It is a
**control-plane loader** that writes into stores that already exist:

### 6.1 CI is the primary gate

The DRY-RUN plan (§3.3) runs in CI as a **release veto**, reusing the
[deployment safety-gate pattern](../deployment/00-deployment-topology.md): the
[permission-conformance suite](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
is *already* the un-overridable veto for connectors; the pack loader simply feeds it the
pack's §1 fixtures. A pack whose plan shows any over-permissive fixture, any non-additive
ledger, or any failed validator **fails the build** and ships in quarantine, never open —
the same "ships fail-closed or not at all" property the platform holds everywhere.

### 6.2 The Markdown ↔ bundle lockstep

A build step derives the machine-readable bundle sections from the pack's Markdown tables
(or validates that a hand-authored bundle matches its doc). This keeps the human ledger and
the loaded behaviour identical: a doc that says "tightens `restricted:mnpi`" and a bundle
that widens it cannot both pass. The Markdown remains the source of *rationale*; the bundle
is the source of *behaviour*; the build step asserts they agree.

### 6.3 Runtime consumers are unchanged

Retrieval reads the (now pack-extended) label arrays and ACL predicate exactly as before;
the verifier reads the (now pack-extended) label→action matrix exactly as before; the
conformance canary reads the (now pack-extended) fixture corpus exactly as before. **No
consumer knows a pack was loaded** — it sees only a larger closed vocabulary and a stricter
matrix, both of which it already handles totally. That invisibility is the proof the SPI is
additive: if a consumer needed a code change to honour a pack, the pack would have breached
the horizontal contract.

---

## 7. Trade-offs

- **(+) The pack contract becomes executable.** *Tighten-only* stops being a review
  convention and becomes a rejected write. The worst a bad pack does is fail to load.
- **(+) Onboarding a domain is a config operation.** With connectors already built, a new
  pack is loaded with no code deploy — the founding bet realized end to end.
- **(+) Every load is provable.** Signature + plan diff + conformance result + audit event
  make "which pack version governs this tenant, and did it ever loosen a floor?" a query,
  not an investigation.
- **(−) The build-step lockstep (§6.2) is extra machinery.** A pack must be authored twice
  (prose + bundle) or generated from one to the other. Mitigated by generating the bundle
  from the Markdown tables so there is one hand-authored source.
- **(−) The connector-referenced-not-shipped line (§4.1) means some domains still need a
  platform deploy** (when they need a genuinely new connector). Deliberate: shipping
  arbitrary read-path code in a pack is the exact door the SPI must keep shut.
- **(−) The atomic six-section COMMIT is heavier than incremental installs.** Chosen because
  partial installation is the one state that could loosen a floor; transactionality buys the
  fail-closed guarantee.

---

## 8. Alternatives considered

- **Hand-install packs into ten configs (status quo).** Rejected: reintroduces the exact
  per-domain drift [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md) exists
  to prevent; the contract is unenforced.
- **A general code-plugin system (packs ship read-path code).** Rejected: makes "load a
  pack" equivalent to "run untrusted code on the retrieval path," an unbounded attack
  surface and a direct violation of the no-hot-path-component rule. The SPI deliberately
  restricts a pack to validated declarative config (§4.1).
- **Trust the pack author (load without a validator, review in PR).** Rejected: turns a
  safety property into a human-vigilance property. The whole value of the SPI is that a
  floor-loosening pack is rejected *structurally*, so a tired reviewer cannot be the last
  line of defence.
- **Per-section independent (non-atomic) installs.** Rejected: a partially-installed pack
  (registry value present, tighten-delta missing) is a transient *loosening* — precisely the
  state the platform must never occupy. Atomicity is the fix.
- **Version packs but never unload.** Rejected: a tenant offboarding a domain must be able
  to remove its vocabulary; the fail-closed unload (§5.3, a live label blocks its own
  removal) makes this safe.

---

## 9. Future scalability

- **A new domain (Procurement, Manufacturing, CRM)** is a new bundle validated and loaded by
  the *same* SPI — no loader change. The SPI generalizes across domains for the same reason
  the six-section skeleton does: it plugs into fixed extension points, not per-domain code.
- **A pack marketplace.** Signed, versioned, content-addressed bundles are already the shape
  of a distributable artifact; the trust model (§4.3) is the seed of a publisher allowlist.
- **A seventh section** (should a future horizontal surface grow an extension point) is a
  `schema_version` bump with a new validator — additive, `min_platform_schema`-gated, never
  a rewrite of the existing five.
- **Cross-pack composition** (Audit inheriting Finance's SOX row today) generalizes through
  `inherits_from` in the manifest — the loader resolves the DAG of pack dependencies and
  validates the composite against the same floors, so composition can tighten but never
  loosen.
- **The `core/` code-reconciliation** ([NEXT_STEPS §6](../NEXT_STEPS.md)) now has a concrete
  target: the loader is the first `platform/`→`core/` mechanism to implement, because it is
  the smallest piece that turns the paper contract into running behaviour.

---

## 10. What this cycle deliberately did **not** do

- **No implementation.** This is the *architecture* of the SPI; the `core/` code is the
  engineering-track follow-up (Cycle 2c-adjacent). Doc-contract-first keeps the decision
  ahead of the code, exactly as [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md)
  did for the pack contract.
- **No resolution of Q#3 (model hosting).** The SPI's §5 eval gate consumes whatever the
  approved-model registry holds; the hosting posture is orthogonal and still open.
- **No new horizontal surface.** The loader writes only into stores that already exist
  (label schema, policy store, conformance corpus, catalog) — its §0-equivalent ledger is
  itself *"none, all additive."* The SPI is, fittingly, the platform loading itself the way
  a pack loads a domain.
