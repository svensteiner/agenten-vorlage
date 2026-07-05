# Storage

> Status: **Seeded** (Cycle 5) · Owner: Data / Platform Architecture

**Scope.** Vector / object / relational / cache / audit store selection; multi-tenant
isolation tiers; encryption & BYOK; versioning, migrations & deletion.

## Documents

- **[00-storage-architecture.md](00-storage-architecture.md)** — the five-store data
  plane, the vector-store final decision (open Q#1: pgvector-default, graduate to a
  dedicated engine on measured pressure), the tenancy definition (open Q#5: tenant =
  customer org), isolation tiers, encryption/BYOK, ACL-denormalization coherence,
  re-embed migrations, and right-to-erasure. Implements
  [ADR-0010](../architecture/adr/ADR-0010-storage-topology-and-tenancy.md).

Consumes the hard selection criteria from
[Permissions §6](../permissions/00-authorization-model.md) and
[RAG §9](../rag/00-retrieval-pipeline.md); hands re-sync/re-embed jobs to
[Workers](../workers/) and retention/cost/erasure ratification to
[Governance](../governance/).
