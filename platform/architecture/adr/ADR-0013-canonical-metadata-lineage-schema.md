# ADR-0013 — Canonical metadata, catalog & lineage schema as a shared, versioned contract

- **Status:** Accepted (Cycle 8)
- **Deciders:** Data Architecture, Platform Architecture, Security & Governance
- **Relates to:** [ADR-0008](ADR-0008-canonical-principal-acl-model.md) (the `resource_id`/CPI
  discipline and the ACL+labels shape this catalogs), [ADR-0009](ADR-0009-hybrid-retrieval-and-chunking.md)
  (the chunk/version granularity and embedding versioning this addresses), [ADR-0010](ADR-0010-storage-topology-and-tenancy.md)
  (the relational source-of-truth store that holds this; the §7 coherence rules it inherits),
  [ADR-0011](ADR-0011-ingestion-workers-and-connector-framework.md) (the persist stage that emits
  the catalog + lineage; write-boundary validation), [ADR-0012](ADR-0012-governance-audit-and-cost.md)
  (the label→action matrix that consumes the classification schema; erasure/retention; audit-as-evidence),
  [Metadata deep dive](../../metadata/00-catalog-and-lineage.md) (full detail)

## Context

Five cycles built machinery that each **referred to the same metadata** — `resource_id`,
`source_item_version`, `labels`, `embed_model`, "lineage tombstone", "catalog row" — but **no
document owned their definitions**. Storage *holds* the catalog + identity graph + lineage
([§4.2](../../storage/00-storage-architecture.md)); Workers *emits* lineage + an ingestion audit
event at persist ([§2, §9](../../workers/00-ingestion-architecture.md)); Governance's label→action
matrix *consumes* a classification schema ([§4](../../governance/00-governance-and-audit.md)); RAG
and Permissions *produce* the labels and version keys on every chunk. The shape was named four
times and defined zero times.

This is the last un-seeded cross-cutting store concern ([NEXT_STEPS §5](../../NEXT_STEPS.md)), and
its absence is the one gap that lets consumers drift: an unenforceable label (a hole in the
Governance matrix), an un-addressable re-sync (a hole in R3), an unprovable erasure (a hole in
GDPR compliance), an un-explainable citation (a hole in audit-as-evidence). The forcing question:
**can the catalog, lineage graph, and classification vocabulary be a single, versioned, shared
contract without adding a new store or re-opening five prior decisions?**

## Decision

1. **Canonicalize, don't re-invent.** Metadata is **held in the relational source-of-truth store**
   ([ADR-0010 §4.2](ADR-0010-storage-topology-and-tenancy.md)) with a denormalized subset on each
   chunk; this ADR fixes the *schema and the graph*, adding **no new storage engine**. Coherence is
   [Storage §7](../../storage/00-storage-architecture.md)'s existing same-tx / outbox rules.
2. **A four-level catalog** — Document → Item → Chunk → Version — keyed on `resource_id` +
   `source_item_version`. The **Item** level is defined as the finest source unit carrying *one*
   ACL, which is where [RAG §2.2](../../rag/00-retrieval-pipeline.md)'s mixed-ACL invariant lives.
   `resource_id` is the platform-wide join key; `source_item_version` is the coherence key;
   `superseded_by` records version history (Principle 8).
3. **A closed classification vocabulary** with registered extension points:
   `sensitivity ∈ {public, internal, confidential, restricted:<class>}`, `pii ∈ {true,false} +
   pii_class:<type>`, `legal_hold ∈ {true,false} + matter:<id>`. **An unregistered label is a
   write-boundary schema violation** (DLQ, never stored) — this is what makes the
   [Governance §4](../../governance/00-governance-and-audit.md) matrix *total*: every label a chunk
   can carry has a defined action. Unlabeled defaults to `internal`, never `public` (fail-closed
   classification).
4. **An explicit lineage graph** `source→raw→parsed→chunk→vector`, emitted at persist time carrying
   the ingestion `job_trace_id`, traversable **both directions**: forward for erasure-completeness
   and re-embed, backward for audit/citation evidence. The `re_embedded_from` edge is itself the
   proof a re-embed was source-independent ([Workers §6](../../workers/00-ingestion-architecture.md)).
5. **A content-free erasure/legal-hold tombstone** that records *what/when/why/which-nodes* of a
   deletion but never the content — the concrete shape of [Storage §9](../../storage/00-storage-architecture.md)'s
   "lineage tombstone" and the [Governance §5](../../governance/00-governance-and-audit.md) legal
   balance (audit retained, content erased; `legal_hold > erasure > retention`).
6. **Metadata is the audit evidence base.** Every Governance promise resolves to a catalog column or
   a lineage traversal addressable by the `resource_id`/`job_trace_id` an audit event already
   carries — so [Governance §6.3](../../governance/00-governance-and-audit.md)'s "can the log prove
   it?" is answered by a query, not a reconstruction. This is why metadata lives transactionally
   with the ACL of record, not in a lagging analytics copy.
7. **A versioned schema validated at the write boundary, evolved additively.** The schema has four
   consumers; a `schema_version` + write-boundary validation (violation → DLQ, like a malformed
   `map_acl`) + additive-with-migration evolution keeps a shared change from becoming a silent
   cross-component break. The contract has one owner (this ADR + the deep dive) and an append-only
   change record.

Full schemas (catalog row, chunk projection, label dimensions, lineage node/edge, tombstone) and
the evidence-traversal table: [Metadata deep dive](../../metadata/00-catalog-and-lineage.md).

## Consequences

- (+) The four consumers (Storage/Workers/RAG/Governance) now share **one defined vocabulary and
  graph** instead of four component-local shapes — schema drift becomes a validated write failure,
  not a latent leak.
- (+) **Governance's matrix becomes total**: a closed, registered label set means every label has a
  defined action — no fail-open holes.
- (+) **Erasure-completeness and audit-evidence become queries, not reconstructions** — GDPR "no
  silent orphans" and "prove permission-faithfulness" are lineage traversals with a provable answer.
- (+) Adds **no new store and no hot-path component** — reuses the relational source of truth and the
  persist stage that already writes; lineage is a byproduct of the existing write.
- (+) Extension points (`restricted:<class>`, `pii_class:<type>`, new `LineageNode.kind`) make new
  domains and derived-artifact types **additive**, not schema redesigns — the "pack, not redesign"
  bet applied to metadata.
- (−) A closed vocabulary imposes a **registration step** for a new class; accepted because a
  free-text label is an unenforceable label.
- (−) Storing explicit lineage edges costs **write volume and a coherence surface**; accepted because
  erasure/audit must be provable, not best-effort.
- (−) Write-boundary validation + versioned migration **slows casual field additions**; the intended
  cost of a four-consumer contract.
- (−) The relational store carries more; mitigated by partitioning + cold-lineage archival
  ([Storage §10](../../storage/00-storage-architecture.md)) — a Deployment tuning input.

## Alternatives

- **A dedicated data-catalog/lineage product** (OpenMetadata, DataHub, Marquez) — rejected as
  default: a second system to keep coherent with the ACL of record, typically outside the per-tenant
  trust boundary (Principle 1). Reconsidered only at cross-tenant-analytics scale.
- **Free-text tag vocabulary** — rejected: makes the Governance matrix partial (fail-open); closed
  set + registered extensions instead.
- **Derive lineage on demand from object-store key conventions** — rejected: erasure-completeness and
  audit-evidence would be a fragile reconstruction, not a provable traversal.
- **Metadata as an eventually-consistent analytics copy** — rejected as source of truth: audit and
  erasure must read the transactional truth; an analytics export downstream is fine.
- **No Item level (chunk hangs off document)** — rejected: loses the mixed-ACL boundary
  ([RAG §2.2](../../rag/00-retrieval-pipeline.md)).
- **Mutable "current" flag instead of a version chain** — rejected: loses version history
  (Principle 8) and makes partial-migration state ambiguous.

## Revisit when

- **Cross-tenant governance analytics becomes a product need** → an export of the closed-vocabulary
  metadata to an analytics store (safe *because* the vocabulary is closed); may reopen the
  dedicated-catalog trade-off for that surface only.
- **A new derived-artifact type** (summary index, knowledge-graph triples) → add a `LineageNode.kind`
  + `relation` (additive; erasure/evidence traversals pick it up automatically).
- **Per-token / substring provenance** is required for a regulated answer → extend `section_path` or
  add a substring lineage edge (additive schema change, §8).
- **A new compliance regime introduces a content class** → register the value + add a Governance
  matrix row; no schema change.
- **Catalog volume outgrows the relational store** → partition/archival tuning in
  [Deployment](../../deployment/); fold back only if the source-of-truth model itself must change.
