# Deployment — Topology, Environments, CI/CD & DR/BCP

> The **physical projection** of everything the previous nine cycles designed. Deployment
> owns *where the logical components run, how code reaches them safely, and how the
> platform survives a region loss* — it introduces **no new logical component** and **no new
> guarantee**; it makes the existing ones affordable, operable, and survivable. This is the
> **last un-seeded platform surface** ([NEXT_STEPS §5](../NEXT_STEPS.md)) and the single place
> the empirical **sizing/tuning numbers** queued by Cycles 5–9 land.

Related upstream: [Platform Overview §3 (three planes)](../architecture/01-platform-overview.md) ·
[Storage](../storage/00-storage-architecture.md) · [Workers](../workers/00-ingestion-architecture.md) ·
[Governance](../governance/00-governance-and-audit.md) · [Metadata](../metadata/00-catalog-and-lineage.md) ·
[API](../api/00-api-surface.md) · [Security](../security/00-security-architecture.md).

---

## 1. What Deployment must satisfy (inputs, not choices)

These are **not** decisions this cycle gets to make freely; they are obligations the prior
cycles explicitly handed down. Every one names its source so the trace is auditable.

| # | Obligation | Handed down by |
|---|------------|----------------|
| **D1** | A **reference topology per tenant tier** (Shared vs. Isolated) plus the **graduation** mechanics for moving a tenant between them without a redesign. | [Storage §3.3, §5.2](../storage/00-storage-architecture.md) |
| **D2** | **Broker choice + worker autoscaling** that realizes the staged-DAG pools and priority classes. | [Workers §3.2, §4, §13](../workers/00-ingestion-architecture.md) |
| **D3** | **SLA-capacity sizing** — the reserved-P0 capacity and relay-poll frequency that *meet* the ratified freshness numbers (≤5/≤2 min principal; ≤15/≤5 min restrictive ACL) at cost. | [Governance §3](../governance/00-governance-and-audit.md), [Workers §4.2, §10](../workers/00-ingestion-architecture.md) |
| **D4** | **Prices + budget-envelope sizes** per tier and **region/residency routing** — the empirical numbers the cost model consumes. | [Governance §7](../governance/00-governance-and-audit.md), [Storage §10](../storage/00-storage-architecture.md) |
| **D5** | **Catalog partitioning + cold-lineage archival + the lineage-integrity-check schedule.** | [Metadata §7, §11](../metadata/00-catalog-and-lineage.md) |
| **D6** | **Gateway / rate-limit / streaming ops** — where the edge terminates, how SSE survives restarts, how rate limits are enforced per tenant. | [API §10.1, §10.3](../api/00-api-surface.md) |
| **D7** | **CI/CD with the connector conformance suite as the production gate**, and **environments** (dev → staging → prod). | [Permissions §11](../permissions/00-authorization-model.md), [Workers §5](../workers/01-connector-framework.md) |
| **D8** | **DR / BCP + backup/restore per store** — RPO/RTO per tier, and whether DR is active-active or active-passive. | [Storage §2, §9](../storage/00-storage-architecture.md), [Governance §6](../governance/00-governance-and-audit.md) |

**Non-negotiable constraint threading all eight:** deployment may **never** trade away a
safety guarantee for an operational convenience. A region failover must not serve stale
*widened* permissions; an autoscaling decision must not starve a P0 revocation; a residency
route must not put one tenant's data in another tenant's region. Deployment is **fail-closed
on infrastructure** exactly as the planes are fail-closed on logic.

---

## 2. Deployment as the physical projection (where it sits)

The [three logical planes](../architecture/01-platform-overview.md) map onto three physically
distinct execution substrates, chosen by their dominant scaling axis:

```
          ┌─────────────────────── Region (residency boundary) ───────────────────────┐
          │                                                                            │
  clients │   ┌── Edge ──┐   ┌──────── Query Plane ────────┐   ┌── Ingestion Plane ──┐ │
  ───────►│   │ API GW    │──►│ Answer svc · Model Gateway  │   │ Worker pools (DAG)  │ │
   (IdP   │   │ TLS term  │   │ Reranker · Verifier         │   │ P0/P1/P2 · broker   │ │
   token) │   │ ratelimit │   └──────────────┬──────────────┘   └──────────┬──────────┘ │
          │   └───────────┘                  │                             │            │
          │                          ┌───────▼─────────────────────────────▼────────┐   │
          │                          │              Data Plane (stateful)           │   │
          │                          │  object · pgvector/engine · relational-SoT   │   │
          │                          │  cache · append-only audit                   │   │
          │                          └──────────────────────────────────────────────┘   │
          └────────────────────────────────────────────────────────────────────────────┘
                     replication (async, same-residency-class only) ──► DR region
```

- **Edge + Query Plane** — stateless, horizontally scaled, latency-SLO-driven. Runs as
  containerized services behind an autoscaler keyed on request concurrency + p95 latency.
- **Ingestion Plane** — stateless *workers*, throughput-driven, scaled on **queue lag**
  (not CPU) so a backlog is what pulls capacity ([Workers §4.2](../workers/00-ingestion-architecture.md)).
- **Data Plane** — stateful, scaled *vertically first then by graduation*
  ([Storage §3.3](../storage/00-storage-architecture.md)); the only substrate with durable
  state, hence the only one with a backup/DR obligation of its own.

**Why this split:** three axes (latency, throughput, durability) that scale independently and
fail independently. Co-locating them would couple a stateless scale-out event to a stateful
one and blur the blast radius. This is the physical restatement of the plane separation the
[overview](../architecture/01-platform-overview.md) argued logically.

---

## 3. Reference topology per tenant tier (D1)

Two tiers, mirroring the [Storage isolation tiers](../storage/00-storage-architecture.md#52-isolation-tiers-concretizing-security-5)
one-to-one so there is **one** isolation vocabulary across the platform.

### 3.1 Shared tier (default)

- **Compute:** a shared, multi-tenant pool for edge/query/ingestion; every request and job
  carries the token-derived `tenant_id` and the two independent Shared-tier data controls
  (per-tenant namespace/schema **and** the unconditional `tenant_id` predicate,
  [Storage §5.2](../storage/00-storage-architecture.md)) apply unchanged.
- **Data:** pgvector-in-Postgres (default vector layer), one logical DB with per-tenant schema
  + RLS; object store with per-tenant prefix; shared cache keyed by `tenant_id`.
- **Economics:** high density, lowest cost/tenant. This is where a new tenant starts.

### 3.2 Isolated tier (regulated / high-volume)

- **Compute:** dedicated node pool (or cluster) per isolated tenant — no shared query/worker
  process touches two isolated tenants.
- **Data:** dedicated Postgres cluster / bucket / cache, **per-tenant DEK + BYOK**
  ([Storage §6](../storage/00-storage-architecture.md)); the [quarantine escape hatch](../storage/00-storage-architecture.md#53-the-isolated-escape-hatch-is-where-permissions-9-quarantine-lands)
  lands here.
- **Economics:** higher fixed cost, bought deliberately for a compliance mandate or a measured
  scale threshold — never the default.

### 3.3 Graduation (Shared → Isolated) without redesign

Graduation is a **data migration through stable ports**, not a re-architecture — this is the
payoff of the [`VectorIndex` port](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
and the canonical identifiers ([Metadata §3](../metadata/00-catalog-and-lineage.md)):

1. Provision the isolated cluster + DEK; register the tenant's residency region.
2. **Blue/green re-index** through the `VectorIndex` port from the object-store parsed
   artifacts ([Storage §8](../storage/00-storage-architecture.md)) — *no source re-hit*,
   identical to a re-embed migration.
3. Cut over the `tenant_id → placement` routing entry (§7.2); drain the shared namespace;
   crypto-erase the residue via DEK destruction.

**Graduation triggers** (measured, from [Storage §3.3](../storage/00-storage-architecture.md)):
chunk count, QPS/latency-SLO pressure, keyword-search dominance, or an **isolation mandate**
(the one non-measured trigger — a contract term flips it immediately).

---

## 4. Environments

Three promoted environments plus ephemeral preview, identical in shape, differing only in
scale and data class.

| Env | Purpose | Data | Isolation from prod |
|-----|---------|------|---------------------|
| **dev** | Fast iteration, unit/integration. | Synthetic + fixture corpora only. | Separate account/project; no prod network path. |
| **staging** | Release candidate; runs the **full conformance + eval gates** against a *permission-representative* synthetic corpus. | Synthetic, but ACL-shaped like prod. | Separate account; mirrors prod topology at 1/N scale. |
| **prod** | Live tenants. | Real tenant data, per-region. | The residency boundary itself. |
| **preview (ephemeral)** | Per-PR review app. | Synthetic. | Torn down on merge; never touches tenant data. |

**Rule — real tenant data never leaves prod.** Staging reproduces *shape* (ACL topology,
label distribution, volume profile) with synthetic content so the conformance suite exercises
the permission predicate without a copy of regulated content existing outside the residency
boundary. This is the deployment expression of the fail-closed doctrine.

---

## 5. CI/CD — the connector conformance suite is the production gate (D7)

The pipeline is **safety-gated, not just test-gated**. The
[permission-conformance suite](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
is not one test among many — it is the **release veto**.

```
 commit ─► build+unit ─► integration ─► [CONFORMANCE GATE] ─► [EVAL GATE] ─► staging ─► canary ─► prod
                                              │                    │
                                    ACL/label leak = 0        grounding/refusal/
                                    (hard fail, no override)  jailbreak thresholds
```

- **Conformance gate (hard, un-overridable):** every connector's `map_acl` is replayed
  against its golden ACL fixtures; **any** over-permissive result (a principal seeing a chunk
  it must not) fails the build with no manual override path. A connector that cannot pass ships
  in **quarantine mode** ([Workers §7.3](../workers/00-ingestion-architecture.md)), never open.
- **Eval gate (model changes):** the [eval-before-promotion](../governance/00-governance-and-audit.md#8-g6--model-governance)
  battery (grounding, refusal calibration, jailbreak resistance, per-pack accuracy) must clear
  the registry thresholds before a model version is promotable. Deployment *enforces* the gate
  Governance *defined*.
- **Progressive delivery:** staging → **canary** (single-tenant or 1% traffic, with the
  [connector production canary](../workers/01-connector-framework.md) auto-quarantine live) →
  full prod. Rollback is a routing revert, not a rebuild.
- **Config & policy as code:** the Governance policy store, connector allowlist
  (`connectors.yaml`), and topology manifests are versioned and promoted through the same
  pipeline; a policy change is a reviewable, audited, revertible commit — the multi-tenant
  successor to [ADR-0007](../architecture/adr/ADR-0007-client-configuration-surface.md)'s local panel.

**Migrations** ([database-migrations discipline](../storage/00-storage-architecture.md#8-versioning--re-embed-migrations-principle-8)):
schema changes are **expand → migrate → contract**, additive-first, so a rollback never strands
a forward-written row. A re-embed is a blue/green background job, never an in-place mutation.

---

## 6. SLA-capacity sizing (D2, D3) — meeting the ratified freshness numbers at cost

The [freshness SLA](../governance/00-governance-and-audit.md#31-the-ratified-sla-table) is a
*promise*; this section is the *capacity that keeps it*. It is a **tuning knob, not a redesign** —
the priority-class machinery already exists in [Workers §4](../workers/00-ingestion-architecture.md).

### 6.1 Broker choice

| Tier | Broker | Why |
|------|--------|-----|
| Shared | Managed cloud queue (SQS/Pub-Sub-class) with a Postgres **transactional outbox** as the coherence relay ([Workers §5](../workers/00-ingestion-architecture.md)). | At-least-once + idempotent version-keyed writes make the queue's redelivery harmless; managed = no broker to operate. |
| Isolated / high-volume | Dedicated Kafka/NATS-class partitioned log, partition-keyed by `tenant_id`. | Per-tenant ordering + replay + throughput headroom; isolation of the queue itself ([Workers §3.3](../workers/00-ingestion-architecture.md)). |

### 6.2 Reserved-P0 capacity (the sizing that makes the SLA affordable)

- **P0 (revocation/security) runs on a reserved, never-starved lane** — a standing minimum of
  warm P0 workers per tenant-shard so a revocation never queues behind a backfill
  ([Workers §4.2 fairness guard](../workers/00-ingestion-architecture.md)). Reserved-P0 is
  sized to the *peak concurrent principal-change rate* (offboarding storms, group deletions),
  not the average.
- **Relay-poll frequency** for the outbox coherence relay is set **below the SLA budget**: to
  hit ≤5 min (Standard) / ≤2 min (Isolated) principal freshness, the relay polls on a cadence
  (e.g. sub-minute) that leaves margin for the invalidation + cache-TTL tail — the SLA is really
  an SLA on *cache-TTL + invalidation latency*, which query-time principal precedence
  ([Storage §7](../storage/00-storage-architecture.md)) already backstops.
- **P1/P2 autoscale on queue lag**; **P0 does not** — P0 is provisioned, not reactive, because
  reacting to a revocation backlog *is already an SLA breach*. This is the core sizing asymmetry:
  **you scale bulk on demand and reserve safety in advance.**

### 6.3 Query-plane autoscaling

Answer/reranker/verifier services scale on p95 latency + concurrency against the
[latency budget](../rag/00-retrieval-pipeline.md). The reranker (the expensive, degradable
stage) has a documented latency-dial fallback, so a capacity shortfall degrades *quality
gracefully* rather than breaching the SLO — capability before availability-panic.

---

## 7. Cost, budget-envelope sizing & residency routing (D4)

### 7.1 Where the empirical numbers land

[Governance §7](../governance/00-governance-and-audit.md) built the metering, attribution, and
degradation ladder but explicitly deferred the *actual prices and envelope sizes*. Deployment
owns them because they are **infrastructure facts** (instance prices, storage $/GB-mo, egress,
model $/1k-tok), not policy. They live in a **versioned pricing/envelope manifest** promoted
through §5's pipeline, so a price change is a reviewable commit that flows into the same budget
machinery — no code change.

- **Envelope defaults** are seeded per tier from the reference topology's steady-state cost
  (Shared tenant baseline vs. Isolated fixed floor + variable) and then tuned from measured
  spend; the degradation ladder (80–100% → cheaper tier + defer P2 + tighten cache; 100% →
  block new P2, queue P1) is unchanged — Deployment only supplies the numbers it triggers on.
- **The safety invariant is inherited verbatim:** no envelope, price signal, or scale-down may
  relax a permission, skip the ACL filter, or throttle a P0 revocation
  ([Governance §7.3](../governance/00-governance-and-audit.md), R5).

### 7.2 Region / residency routing

- A tenant is pinned to a **residency region** at onboarding (recorded in the same
  `tenant → placement` map that drives graduation §3.3). The
  [token-bound identity](../api/00-api-surface.md#4-authn--authz-at-the-edge) carries the tenant;
  the gateway resolves tenant → region → cluster. **Region is a deployment concern, never a
  contract change** — exactly as [ADR-0014 "revisit-when"](../architecture/adr/ADR-0014-api-contract-surface.md)
  anticipated.
- **Data does not cross its residency class.** Replication (§9) targets only a DR region *within
  the same residency class*; a tenant's content, vectors, catalog, and audit all stay in-class.
  This is what makes "in-boundary" a physical fact, not a label.

---

## 8. Catalog partitioning, cold-lineage archival & integrity checks (D5)

Concretizes the operations [Metadata §7, §11](../metadata/00-catalog-and-lineage.md) deferred.

- **Catalog partitioning:** the relational catalog partitions by `tenant_id` (and, at high
  volume, sub-partitions by `document_id` hash) so a tenant's catalog reads/writes and its
  erasure traversals never scan another tenant's rows — partition pruning is the performance
  half of the R4 two-control isolation.
- **Cold-lineage archival:** live lineage edges stay hot in the SoT for the active retention
  window; edges older than the window (still needed for audit evidence) roll to cheaper cold
  storage **with the tombstone/erasure guarantees intact** — an archived edge is still walkable
  to prove erasure completeness, just slower. Archival never deletes an edge that a live chunk
  or an open legal-hold depends on.
- **Lineage-integrity-check schedule:** a scheduled P2 job walks the graph asserting the
  [Metadata §7 invariants](../metadata/00-catalog-and-lineage.md) — every chunk has a live
  lineage path **or** a tombstone; version monotonicity; label ⊆ registry; **no cross-tenant
  edge (R4)**. A violation raises a governance incident and quarantines the affected shard's
  writes, same mechanism as a malformed `map_acl`. Runs on a cadence tighter than the audit
  retention hot window so drift is caught long before it could reach an audit.

---

## 9. DR / BCP & backup-restore per store (D8) — see [ADR-0015](../architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md)

### 9.1 Posture: active-passive per residency region, tiered RPO/RTO

The cross-component decision this cycle owns (→ **ADR-0015**): DR is **active-passive within a
residency class**, not active-active. An active-active write topology across regions would force
either cross-region ACL-write coordination (unacceptable latency on the safety path) or a window
where two regions disagree on a revocation — a **stale-widened-permission risk** the platform
forbids. Active-passive keeps a single authoritative write region per tenant and an async-
replicated warm standby.

| Tier | RPO (max data loss) | RTO (max downtime) | Mechanism |
|------|--------------------:|-------------------:|-----------|
| Shared | ≤ 15 min | ≤ 4 h | Async streaming replication of Postgres + object versioning + audit ship; standby promoted on declared disaster. |
| Isolated | ≤ 5 min | ≤ 1 h | Tighter replication cadence + pre-warmed standby cluster + per-tenant DEK pre-provisioned in the standby region (same residency class). |

### 9.2 Per-store backup/restore

| Store | Backup | Restore-tested by |
|-------|--------|-------------------|
| Relational SoT (catalog, ACL of record, metadata) | Continuous WAL archiving + periodic base backup; PITR. | Scheduled restore drill into staging; **the SoT is the recovery anchor** — vectors are derivable, ACLs are not. |
| Vector/keyword (pgvector or engine) | **Not primary-backed up — rebuilt.** Re-indexed from object-store parsed artifacts through the `VectorIndex` port. | The blue/green re-index path (§3.3) *is* the restore path. |
| Object (raw + parsed) | Versioned + cross-region-replicated (in-class); immutable retention per [Governance §5](../governance/00-governance-and-audit.md). | Object-level integrity check; it seeds vector rebuild. |
| Cache | **Not backed up** — reconstructable; cold-start accepted. | N/A. |
| Append-only audit | Replicated + hash-chain verified on schedule; **retained even through erasure** ([Governance §6](../governance/00-governance-and-audit.md)). | Hash-chain continuity check post-restore. |

**Recovery ordering:** SoT (authoritative ACLs + catalog) → object (source of truth for content)
→ vector rebuild → cache warm. **Permissions recover before content is queryable** — the
platform comes back fail-closed: if the ACL of record hasn't recovered, retrieval serves
nothing, never serves unfiltered.

### 9.3 The failover safety rule

A promoted standby **must not** serve a permission state older than the freshness SLA. Because
query-time principal precedence ([Storage §7](../storage/00-storage-architecture.md)) evaluates
the *current* principal set at read time, and the standby recovers the SoT first, a failover
cannot resurrect a revoked grant — the same invariant that closes offboarding closes DR.

---

## 10. Observability & runbooks

Deployment makes the planes' promises *watchable*:

- **SLA signals:** relay-lag and queue-lag alarms ([Workers §10](../workers/00-ingestion-architecture.md))
  are the freshness-SLA smoke detectors; a looming breach is loud, not silent.
- **Correlation:** `meta.request_id` == the audit correlation id ([API §6](../api/00-api-surface.md))
  threads a single trace from edge → retrieval → verifier → audit; ops and compliance read the
  *same* id.
- **Golden signals per plane:** query (p95 latency, verifier-refusal rate, no-access rate),
  ingestion (queue lag by priority class, DLQ depth, conformance-canary status), data (replication
  lag, backup freshness, integrity-check pass rate).
- **Runbooks** exist for: region failover, connector auto-quarantine, budget-envelope breach,
  lineage-integrity violation, and hash-chain break — each maps to an already-defined governance
  incident type, so an operator's action and the compliance record are the same event.

---

## 11. Trade-offs

- **Active-passive DR (chosen) vs. active-active:** active-passive accepts a bounded RTO and a
  brief promotion gap in exchange for a **single authoritative permission state** — no window
  where two regions disagree on a revocation. Active-active's zero-RTO is not worth a
  stale-permission risk on the safety path. (See ADR-0015.)
- **Vector store rebuilt, not backed up:** trades a longer restore for a smaller backup surface
  and a *guaranteed-consistent* rebuild (the object artifact is the truth); a restored stale
  vector snapshot could disagree with the recovered ACLs — rebuild can't.
- **Reserved P0 vs. fully-elastic workers:** paying for warm P0 capacity that is idle most of
  the time buys a revocation SLA that reactive autoscaling structurally cannot meet. Safety is
  provisioned; bulk is elastic.
- **Synthetic-shaped staging vs. prod-data staging:** losing real-data fidelity in staging is
  the price of keeping regulated content inside the residency boundary; ACL-shape fidelity keeps
  the conformance gate meaningful.
- **Shared-tier density vs. blast radius:** the Shared tier's low cost/tenant concentrates more
  tenants behind the two-control isolation; accepted because the controls are independent and the
  Isolated tier exists precisely for tenants who cannot accept shared compute.

---

## 12. Alternatives considered

- **Active-active multi-region writes** — rejected as default (see §11, ADR-0015); revisit for a
  read-mostly global tenant with a single-region write anchor.
- **Backing up the vector store as primary** — rejected: a restored vector snapshot can disagree
  with recovered ACLs; the object-artifact rebuild is consistency-safe by construction.
- **One global cluster, no residency regions** — rejected: violates in-boundary/residency
  guarantees for regulated domains; residency regions are non-optional for the target sectors.
- **Kubernetes-everywhere from day one** — deferred as a mandate: the container/orchestrator
  choice is left to the operating org; this doc specifies *properties* (stateless scale-out,
  queue-lag autoscaling, reserved-P0, blue/green) that any of K8s/Nomad/managed-serverless can
  satisfy. Over-specifying the orchestrator would be a redesign trigger the platform avoids.
- **Manual, ticket-gated releases** — rejected: the conformance/eval gates must be *machine*-
  enforced and un-overridable; a human override path is exactly the hole they close.
- **Copying prod data into staging** — rejected: no regulated content leaves the residency
  boundary; synthetic ACL-shaped corpora preserve gate fidelity without the exposure.

---

## 13. Future scalability

- **New region** = provision a residency region + register a `tenant → placement` route; no
  contract or component change (the token already carries tenant; the gateway already routes).
- **New tenant tier** (e.g. a "sovereign" tier with in-country DR) = a new row in the topology
  manifest + RPO/RTO cell, reusing the same replication and gate machinery.
- **New store** (should a graduation engine be added) = one `VectorIndex`/port adapter + a
  backup/restore row; the recovery-ordering rule (ACLs first) is store-agnostic.
- **Domain packs** deploy as additive config (allowlist + policy rows + optional pack endpoints,
  [ADR-0014](../architecture/adr/ADR-0014-api-contract-surface.md)) — **a new domain is a
  deployment of data + policy, never a topology change.** This closes the platform's founding
  bet at the infrastructure layer: *new domain = pack, not redesign — all the way down to where
  the bytes run.*

---

## Related

- [ADR-0015 — Deployment DR & regional topology](../architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md) (this cycle)
- [Platform Overview §3](../architecture/01-platform-overview.md) — the logical planes this projects
- [Storage §3.3, §5.2, §6, §7, §8, §9](../storage/00-storage-architecture.md) — tiers, DEK, coherence, migrations, erasure
- [Workers §3.2, §4, §5, §10](../workers/00-ingestion-architecture.md) — broker, priority, relay, SLA observability
- [Governance §3, §5, §6, §7](../governance/00-governance-and-audit.md) — SLA, retention, audit, cost
- [Metadata §7, §11](../metadata/00-catalog-and-lineage.md) — partitioning, archival, integrity
- [API §4, §6, §10](../api/00-api-surface.md) — edge identity, request-id correlation, rate/streaming ops
- [Permissions §11](../permissions/00-authorization-model.md) — the conformance suite the CI gate enforces
