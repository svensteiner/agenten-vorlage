# API

> Status: **Seeded** (Cycle 9) · Owner: Platform / Enterprise Architecture

**Scope.** The external contract of the platform — the endpoints clients call, the
identity they must present, the shape of every response, how long-running work is
exposed, and how the surface evolves without breaking callers.

## Documents

- **[00-api-surface.md](00-api-surface.md)** — the full API surface: five resource
  groups (Query & Answer, Catalog & Lineage, Governance & Admin, Privacy & Audit,
  Ingestion ops), token-bound auth & OBO, the query/answer + streaming contract, the
  response envelope & typed error model, the async-job pattern, pagination/rate-limiting,
  and the versioning/deprecation policy.

## Key decisions

- **[ADR-0014](../architecture/adr/ADR-0014-api-contract-surface.md)** — token-bound
  identity (tenancy never in the URL), dual sync/streaming answer under one verifier gate,
  job-based heavy work, admin-can-only-tighten, filter-parity on reads, URL-major
  versioning.

This surface fronts the [API Gateway](../architecture/01-platform-overview.md) and the
[Governance policy store](../governance/00-governance-and-audit.md). It exposes — it does
not re-decide — obligations from [Permissions](../permissions/00-authorization-model.md),
[RAG](../rag/00-retrieval-pipeline.md), [Governance](../governance/00-governance-and-audit.md),
and [Metadata](../metadata/00-catalog-and-lineage.md).
