# Metadata

> Status: **Seeded** (Cycle 8) · Owner: Data / Platform Architecture

**Scope.** The catalog, the lineage graph, and the classification/label vocabulary — the
connective-tissue schema every plane touches but none owned.

## Documents

- [00-catalog-and-lineage.md](00-catalog-and-lineage.md) — the canonical **catalog schema**
  (Document → Item → Chunk → Version), the **lineage graph** (source→raw→parsed→chunk→vector,
  + the erasure/legal-hold tombstone), the closed **classification/label vocabulary** the
  ACL `labels` and the [Governance §4](../governance/00-governance-and-audit.md) matrix key
  off, how catalog/lineage back **audit evidence**, and the write-boundary **schema
  versioning** that keeps four consumers from drifting. Decision recorded in
  [ADR-0013](../architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md).

**This folder holds the *schema*, not a store** — the metadata lives in the relational
source-of-truth store ([Storage §4.2](../storage/00-storage-architecture.md)); it is
*emitted* by the ingestion persist stage ([Workers §2, §9](../workers/00-ingestion-architecture.md))
and *consumed* by Governance, RAG citation, and the erasure workflow. Do not duplicate store
topology or ingestion mechanics here — link instead.
