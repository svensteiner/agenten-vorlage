# Workers — Ingestion & Connector Framework

> Status: **Seeded (Cycle 6)** · Owner: Platform / Data Engineering
> Implements [ADR-0011](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).

The **ingestion plane** ([Overview §3.2](../architecture/01-platform-overview.md)) — the write
path that keeps the [five-store data plane](../storage/00-storage-architecture.md) fresh,
coherent, and permission-faithful. Everything the query plane guarantees is only as true as
the workers that populate and maintain the stores behind it.

## Read in order

1. **[00-ingestion-architecture.md](00-ingestion-architecture.md)** — the generic engine:
   the staged-DAG pipeline, the `IngestionTask` queue + at-least-once/idempotent write model,
   worker pools and **priority classes** (R8), the **ACL-coherence outbox relay**
   ([Storage §7](../storage/00-storage-architecture.md)), **re-embed migrations**
   ([Storage §8](../storage/00-storage-architecture.md)), change-driven re-sync (R3 write
   half), the failure/DLQ model, the least-privilege security posture, and the observability
   that makes the freshness SLA measurable.
2. **[01-connector-framework.md](01-connector-framework.md)** — the source-specific boundary:
   the six-method `Connector` contract, `map_acl` per source (R1 implementation), versioning
   and fault isolation (R6), change detection, and the **conformance suite as the production
   gate** ([Permissions §11](../permissions/00-authorization-model.md)).

## What this cycle resolved

- Implements the write-side contract handed down by [Storage §7–§9](../storage/00-storage-architecture.md)
  (coherence relay, re-embed migration, erasure propagation).
- Executes the connector obligations from [Permissions §5, §8, §11](../permissions/00-authorization-model.md)
  and the chunking/embedding rules from [RAG §2–§3](../rag/00-retrieval-pipeline.md).
- **Mitigates R8** (backlog → freshness) by priority classes + fairness guards + lag alarms;
  co-mitigates **R3** (re-sync half), **R6** (connector fragility → conformance canary).

## Handed downstream

- **Freshness-SLA ratification** (open Q#7), per-tenant ingest cost, and DLQ/retention policy
  → [Governance](../governance/) (Cycle 7).
- **Broker choice per tier, worker autoscaling topology, secret provisioning** →
  [Deployment](../deployment/).
- **Lineage schema** emitted by the persist stage → [Metadata](../metadata/).
