# ADR-0010 — Storage topology & tenancy: five-store data plane, pgvector-default vector layer, tenant = customer org

- **Status:** Accepted (Cycle 5)
- **Deciders:** Data / Platform Architecture, Enterprise Architecture, Security Architecture
- **Relates to:** [ADR-0009](ADR-0009-hybrid-retrieval-and-chunking.md) (whose provisional
  vector-store lean this confirms and finalizes), [ADR-0008](ADR-0008-canonical-principal-acl-model.md)
  (the canonical ACL this store denormalizes onto chunks and filters on),
  [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (filter-during-retrieval, enforced
  at the `VectorIndex` port by construction), [ADR-0003](ADR-0003-model-gateway-indirection.md)
  (the vendor-independence pattern reused for the vector layer),
  [Storage deep dive](../../storage/00-storage-architecture.md) (full detail)

## Context

The data plane ([Overview §3.3](../01-platform-overview.md)) was the last un-designed
bottleneck: [Permissions](../../permissions/00-authorization-model.md) (Cycle 3) and
[RAG](../../rag/00-retrieval-pipeline.md) (Cycle 4) both handed Storage **hard, concrete
requirements** — efficient principal **set-overlap filtering**, **hybrid search under one
shared metadata filter**, **versioned upsert/delete**, per-tenant **isolation by
construction**, in-boundary + BYOK encryption — and two open questions were Storage's to
close: **#1 (vector store — final)** and **#5 (tenancy granularity)**. Until they were
answered, [Workers](../../workers/) and [Deployment](../../deployment/) could not build.
ADR-0009 §6 recorded a *provisional* pgvector→dedicated-engine lean and explicitly deferred
the final call to this cycle.

## Decision

1. **Five distinct stores, not one.** Object (raw+parsed, immutable/versioned), Vector+keyword
   (chunks: embedding + ACL arrays + full-text + metadata), Relational/metadata (catalog +
   canonical ACL of record + identity graph + lineage — the source of truth), Cache
   (revocable decision cache + session), and an **append-only, hash-chained Audit** store,
   **physically separate** from operational data. Each has a different scaling axis,
   consistency need, and blast radius.
2. **Vector layer (open Q#1 — FINAL): pgvector-in-Postgres is the default**; graduate a
   tenant to a dedicated engine (Qdrant; Elasticsearch/OpenSearch when keyword/aggregation
   dominates) on **measured** thresholds (chunk count, QPS/SLA, keyword dominance, isolation
   mandate). pgvector co-locates the vector, the `text[]` ACL arrays (GIN `&&` set-overlap),
   full-text (`tsvector`), and metadata in **one transactional store**, so both halves of
   hybrid search share one filter by construction and the ACL denormalization is a
   same-transaction write. Confirms and finalizes ADR-0009 §6's provisional lean.
3. **A narrow `VectorIndex` port with no unfiltered-search method.** Every engine sits
   behind one adapter; `hybrid_search` **requires** a `tenant` and a `CompiledPredicate`
   (produced by Permissions §6, passed opaque). Unfiltered search is **unrepresentable** —
   filter-during-retrieval ([ADR-0004](ADR-0004-permission-faithful-retrieval.md)) becomes a
   structural guarantee, and vector-engine lock-in (R7) is bounded to one adapter.
4. **Tenancy (open Q#5 — FINAL): a tenant is an isolation & governance boundary = one
   customer organization.** Departments and domains are **not** tenants — they are ACL/
   `visibility` scopes and domain packs *within* a tenant. This aligns the storage isolation
   primitive with the CPI identity namespace (`tenant:source:type:id`).
5. **Two isolation tiers, by construction.** Shared (per-tenant namespace/schema/prefix +
   RLS + an unconditional `tenant_id` predicate — two independent controls) and Isolated
   (dedicated cluster/database/bucket + BYOK) for regulated/large/high-sensitivity tenants.
   [Permissions §9](../../permissions/00-authorization-model.md) quarantine lands here as an
   Isolated-tier dedicated index.
6. **Envelope encryption with per-tenant DEKs; BYOK for Isolated.** Enables tenant-scoped
   key compromise and **crypto-erasure** as a fast, provable deletion primitive. Immutable
   versioned knowledge; deletion propagates to all five stores (audit retained as event).

Full detail, scoring tables, coherence rules, and cost levers:
[Storage deep dive](../../storage/00-storage-architecture.md).

## Consequences

- (+) Every upstream hard requirement (S1–S7) is met by an explicitly-chosen store; the
  permission filter stays a **single-store index predicate** (safety costs a `WHERE`).
- (+) The `VectorIndex` port makes the unsafe query path **unrepresentable** and bounds R7
  to one adapter — a tenant migration is a re-index, not a pipeline rewrite.
- (+) pgvector default keeps the common tenant simple and the ACL/vector write atomic
  (no coherence drift at that tier); dedicated engines are paid for only on measured need.
- (+) Tenant = customer org keeps the identity namespace, nested-group resolution, and
  isolation boundary consistent; departments/domains reuse the existing ACL/pack machinery.
- (+) Per-tenant DEK + BYOK give crypto-erasure and a regulated-procurement-grade privacy
  posture; blast radius of a key compromise is one tenant.
- (−) Five stores = more surfaces to isolate, encrypt, back up, and keep coherent; the
  ACL-denormalization coherence hazard (drift → stale filter) is real and needs the
  transactional-outbox discipline at the dedicated-engine tier (Storage §7).
- (−) pgvector-then-graduate accepts a future per-tenant migration for tenants that outgrow
  it — mitigated (not eliminated) by the port making it a re-index.
- (−) Isolated tier + BYOK raise per-tenant cost and add customer-KMS availability as a
  dependency — priced per tenant, not defaulted.

## Alternatives

- **One store for everything** — rejected: forces the weakest scaling axis on all data and
  makes append-only audit unenforceable in a mutable table (pgvector *does* co-locate
  vector+relational+keyword at small scale, but object/cache/audit stay separate).
- **Dedicated vector engine for all tenants from day one** — rejected as default: cost/ops
  overhead for the majority below graduation thresholds.
- **Managed public vector/object store** — rejected: data egress violates Principle 1.
- **Query-time join to the relational ACL (no denormalization)** — rejected: reintroduces
  per-candidate ACL lookup the normalization ([ADR-0008](ADR-0008-canonical-principal-acl-model.md))
  exists to avoid.
- **`tenant_id` column as the only tenant boundary** — rejected: one filter bug = leak; we
  add an independent namespace/cluster boundary (R4).
- **Tenant = department/domain** — rejected: fractures the identity namespace and
  nested-group resolution.
- **Shared KMS key for all tenants** — rejected: platform-wide compromise radius; no
  crypto-erasure.

## Revisit when

- A tenant crosses the §3.3 graduation thresholds → provision the dedicated engine behind
  the same `VectorIndex` port (no ADR change; a Deployment runbook event).
- [Workers](../../workers/) (Cycle 6) designs the transactional-outbox relay → confirm the
  §7 coherence bound against the freshness SLA (open Q#7).
- [Governance](../../governance/) (Cycle 7) ratifies retention + erasure + per-tenant cost
  metering → fold the audit-retention and legal-hold-tombstone rules into policy.
- A vector engine appears that natively co-locates ACL set-overlap **and** horizontal scale
  without the coherence tax → re-evaluate the pgvector-default/graduate split.
