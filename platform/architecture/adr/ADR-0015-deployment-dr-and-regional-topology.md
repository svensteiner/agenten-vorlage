# ADR-0015 — Deployment DR & regional topology: active-passive per residency region, ACL-first recovery, rebuilt vectors

- **Status:** Accepted (Cycle 10)
- **Deciders:** Platform Architecture, Enterprise Architecture, Security & Governance, Platform Engineering
- **Relates to:** [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (the permission
  guarantee a failover must not regress), [ADR-0010](ADR-0010-storage-topology-and-tenancy.md)
  (five-store data plane, isolation tiers, `VectorIndex` port, per-tenant DEK — the substrate
  DR replicates), [ADR-0011](ADR-0011-ingestion-workers-and-connector-framework.md) (priority
  classes + outbox relay whose capacity DR sizing reserves),
  [ADR-0012](ADR-0012-governance-audit-and-cost.md) (the ratified freshness SLA a standby must
  honor + the cost envelopes DR provisioning consumes),
  [ADR-0014](ADR-0014-api-contract-surface.md) (tenancy-in-token, which makes region a routing
  concern not a contract change), [Deployment deep dive](../../deployment/00-deployment-topology.md) (full detail)

## Context

Nine cycles designed the platform's logical planes, policy, and contracts and each **deferred
its physical sizing and survivability** to "the deployment cycle" — reference topology per tier,
broker/autoscaling, SLA-capacity sizing, prices/envelopes, residency routing, catalog
partitioning/archival, gateway/streaming ops, and **DR/BCP**. `deployment/` was the **last
un-seeded platform surface** ([NEXT_STEPS §5](../../NEXT_STEPS.md)).

Most of those inputs are *tuning knobs* that the deep dive resolves without a cross-component
decision. **Three questions are genuinely cross-component** — they constrain Storage, Workers,
API, and Governance simultaneously, and if answered ad hoc would let the platform's hardest
guarantee (permission-faithful retrieval) be silently regressed by an infrastructure choice:

1. **Is DR active-active or active-passive across regions?** — determines whether two regions
   can ever hold a *different permission state* for the same tenant.
2. **What recovers first after a disaster?** — determines whether the platform can come back
   serving content before its ACLs are authoritative.
3. **Is the vector store backed up or rebuilt?** — determines whether a restore can resurrect a
   vector snapshot that disagrees with the recovered ACLs.

## Decision

1. **DR is active-passive within a residency class.** Each tenant has a **single authoritative
   write region**; a warm standby in another region *of the same residency class* receives async
   replication and is promoted only on a declared disaster. **No cross-region active-active
   writes.** Rationale: an active-active write topology forces either cross-region coordination
   on the ACL-write path (unacceptable latency on the safety path) or a window where two regions
   disagree on a revocation — a **stale-widened-permission** state the platform forbids
   ([ADR-0004](ADR-0004-permission-faithful-retrieval.md)). Data never crosses its residency
   class; replication targets an in-class region only.

2. **Recovery is ACL-first, fail-closed.** Restore order is **relational SoT (ACL of record +
   catalog) → object store → vector rebuild → cache warm**. Retrieval is unavailable until the
   SoT is authoritative; it **never** serves content under an un-recovered or stale permission
   state. The platform comes back the way it runs: fail-closed. A promoted standby must not serve
   a permission state older than the ratified [freshness SLA](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table);
   because [query-time principal precedence](../../storage/00-storage-architecture.md#7-consistency--the-acl-denormalization-coherence-problem)
   evaluates the current principal set at read time, a failover cannot resurrect a revoked grant.

3. **The vector/keyword store is rebuilt, not backed up.** Recovery re-indexes from the
   object-store parsed artifacts through the [`VectorIndex` port](../../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
   (the blue/green re-index path = the restore path). Only the SoT, object store, and audit store
   are primary-backed-up. Rationale: a restored vector snapshot could disagree with the recovered
   ACLs; a rebuild from the authoritative artifact is **consistency-safe by construction**.

4. **Tiered RPO/RTO, provisioned safety, elastic bulk.** Shared: RPO ≤15 min / RTO ≤4 h.
   Isolated: RPO ≤5 min / RTO ≤1 h (tighter replication, pre-warmed standby, per-tenant DEK
   pre-provisioned in-class). **P0 revocation capacity is reserved, not autoscaled**; P1/P2 scale
   on queue lag. Reacting to a revocation backlog is already an SLA breach — safety is provisioned
   in advance, bulk is elastic on demand.

Full topology, environments, CI/CD gates, sizing, and per-store backup/restore matrix:
[Deployment deep dive](../../deployment/00-deployment-topology.md).

## Consequences

- (+) There is **never a window** where two regions disagree on a tenant's permissions; the
  revocation SLA holds across a failover, not just in steady state.
- (+) Recovery is **fail-closed** — the platform cannot come back serving unfiltered or stale-
  permission content, because ACLs recover before content is queryable.
- (+) The restore path **reuses the graduation/re-embed machinery** ([Storage §8](../../storage/00-storage-architecture.md),
  Deployment §3.3) — DR is not a separate mechanism to build and drift; a re-index is a re-index.
- (+) Residency is a **routing fact** (`tenant → placement`), so a new region is additive and
  never a contract change ([ADR-0014](ADR-0014-api-contract-surface.md) anticipated this).
- (+) Backup surface is smaller (vectors excluded) and every restore is consistency-guaranteed.
- (−) Active-passive accepts a **bounded RTO + a promotion gap** instead of zero-downtime
  failover; accepted for the single-authoritative-permission-state property.
- (−) Reserved P0 capacity is **paid for while mostly idle**; accepted because reactive scaling
  structurally cannot meet a revocation SLA.
- (−) Vector rebuild makes RTO **longer** than a snapshot restore would; accepted because a stale
  vector snapshot is a correctness risk a rebuild eliminates.
- (−) Per-residency-class standbys **duplicate infrastructure** per class; accepted as the cost
  of in-boundary DR for regulated tenants.

## Alternatives

- **Active-active multi-region writes** — rejected as default: cross-region ACL-write
  coordination or a permission-disagreement window is unacceptable on the safety path. Revisit
  for a read-mostly global tenant with a single-region write anchor + read replicas.
- **Content-first (or parallel) recovery** — rejected: any ordering that can make content
  queryable before its ACL of record is authoritative is a leak path; ACL-first is the only
  fail-closed ordering.
- **Backing up the vector store as primary** — rejected: a restored snapshot can disagree with
  recovered ACLs; the object-artifact rebuild is the only consistency-safe restore.
- **Single global cluster, no residency regions** — rejected: violates the in-boundary/residency
  guarantee the target sectors require.
- **Fully-elastic workers with no reserved P0** — rejected: cannot meet the ratified revocation
  SLA; the reserved lane is the capacity expression of "safety is provisioned, not reactive."

## Revisit when

- **A global read-mostly tenant** needs sub-second cross-region reads → add read replicas behind
  a single-region write anchor (still not active-active writes).
- **A sovereign / in-country-DR tier** is contracted → add a topology-manifest row + RPO/RTO
  cell; the replication + gate machinery is unchanged.
- **Measured RTO proves too slow** for a tier's contract → tighten replication cadence / pre-warm
  more of the standby (a sizing change), before reconsidering active-active.
- **A store is added** (a graduation engine) → add its backup/restore row; the ACL-first recovery
  ordering is store-agnostic and does not change.
