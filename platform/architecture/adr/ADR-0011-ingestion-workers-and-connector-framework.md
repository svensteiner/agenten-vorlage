# ADR-0011 — Ingestion plane: staged-DAG workers, at-least-once + idempotent writes, and a conformance-gated connector contract

- **Status:** Accepted (Cycle 6)
- **Deciders:** Platform / Data Engineering, Enterprise Architecture, Security Architecture
- **Relates to:** [ADR-0010](ADR-0010-storage-topology-and-tenancy.md) (implements its §7
  coherence relay, §8 re-embed migration, §9 erasure), [ADR-0008](ADR-0008-canonical-principal-acl-model.md)
  (the connector's `map_acl` produces the canonical ACL this normalizes),
  [ADR-0009](ADR-0009-hybrid-retrieval-and-chunking.md) (executes its chunking/embedding
  rules on the write side), [ADR-0004](ADR-0004-permission-faithful-retrieval.md) /
  [ADR-0006](ADR-0006-fail-closed-autonomy-default.md) (fail-closed doctrine applied to the
  write path), [ADR-0005](ADR-0005-template-consolidation-council.md) (`WorkerRegistry`
  least-privilege runtime), [ADR-0003](ADR-0003-model-gateway-indirection.md) (in-boundary
  embedding), [Ingestion deep dive](../../workers/00-ingestion-architecture.md) +
  [Connector Framework](../../workers/01-connector-framework.md) (full detail)

## Context

The **ingestion plane** ([Overview §3.2](../01-platform-overview.md)) was the last major
un-designed subsystem. Cycles 3–5 fixed **what must be true of the data at rest** —
permission-faithful, hybrid-searchable, versioned, isolated, coherent — and each handed
Workers concrete, non-negotiable obligations: the **ACL-denormalization coherence relay** and
**re-embed migration** ([Storage §7–§8](../../storage/00-storage-architecture.md)), the
**change-driven re-sync** of content and permissions and the **connector mapping contract**
([Permissions §5, §8, §11](../../permissions/00-authorization-model.md)), the
**mixed-ACL chunk invariant** and **embedding versioning** ([RAG §2–§3](../../rag/00-retrieval-pipeline.md)),
and the tracked **ingestion-backlog risk R8**. Until Workers was specified, Deployment topology
could not be sized and the write path was not implementable end to end.

The forcing question: how do we keep a five-store data plane **fresh, coherent, and
permission-faithful** under flaky sources, permission churn, embedding-model upgrades, and 10×
load — without any of it becoming a leak or a silent SLA breach?

## Decision

1. **Ingestion is a staged DAG of durable, independently-retryable, independently-scalable
   stages** (fetch → parse → map_acl → chunk → embed → persist), each reading and writing a
   durable artifact. A failure resumes from the last completed stage; the expensive source
   fetch happens **once per version**. Bulk backfill and change-driven deltas converge on the
   **same idempotent stages 4–6**.
2. **At-least-once delivery + idempotent, version-keyed writes** (keyed on
   `tenant + resource_id + source_item_version`). We refuse to depend on exactly-once broker
   semantics; replays and outbox double-delivery are made harmless instead. The `TaskQueue`
   sits behind a narrow port; per-`resource_id` ordering only (a newer ACL must never lose to
   a replayed older one).
3. **Strict priority classes with fairness guards** — **P0 revocation/security** (≤5 min
   principal / ≤15 min restricted-ACL), **P1 content delta**, **P2 backfill/re-embed/
   reconciliation** — so a bulk backfill can never starve a permission revocation (**R8**).
   P0 preempts and is reserved capacity; fairness floors prevent starvation of P1/P2 and of
   any single tenant.
4. **The Storage §7 coherence relay is a transactional outbox** at the dedicated-engine tier
   (the pgvector tier is same-transaction, no relay). Intent committed atomically with the
   relational write; relayed at-least-once, idempotently, in per-`resource_id` order; **relay
   lag is bounded by and measured against the freshness SLA**.
5. **Re-embed / re-chunk migrations are blue/green P2 jobs that read the parsed object
   artifact — never the source** ([Storage §8](../../storage/00-storage-architecture.md)):
   version-filtered so mixed embedding spaces never degrade recall mid-migration; ACL
   re-carried from the current canonical record, not re-derived.
6. **One conformance-gated connector contract** (`list_items`, `fetch`, `map_acl`,
   `subscribe_changes`, `list_principal_changes`, `capabilities`). A connector **cannot**:
   query or write the source on the shared path, emit a sub-`exact` chunk to the shared index,
   build the query predicate, or raise its own `acl_confidence`. **No connector serves
   shared-path retrieval until it passes the permission-conformance suite**
   ([Permissions §11](../../permissions/00-authorization-model.md)) in CI **and** a periodic
   production canary that **auto-quarantines** a source on drift (**R1/R6**).
7. **Least privilege across the write path** ([ADR-0005](ADR-0005-template-consolidation-council.md)
   `WorkerRegistry`): the credential to *read a source* and the credential to *write the ACL
   of record* live in **different worker pools**; read-only per-tenant source creds; every
   write is audited. Under load the plane **drops recall before it drops a revocation** —
   fail-closed ([ADR-0004](ADR-0004-permission-faithful-retrieval.md)/[ADR-0006](ADR-0006-fail-closed-autonomy-default.md))
   applied to ingestion.

Full detail, DAG table, relay sequence, priority/fairness model, failure/DLQ model, and
observability: [Ingestion deep dive](../../workers/00-ingestion-architecture.md) +
[Connector Framework](../../workers/01-connector-framework.md).

## Consequences

- (+) The write path is now fully specified end to end; Deployment can size worker pools,
  broker, and per-tier topology.
- (+) Idempotent version-keyed writes make retries, replays, and outbox double-delivery
  harmless — the load-bearing simplification that lets us use an honest at-least-once broker.
- (+) Priority + fairness make **R8 both survivable and observable** (queue-lag alarms); the
  safety-critical P0 path is fastest and belt-and-suspendered by query-time principal
  precedence ([Storage §7](../../storage/00-storage-architecture.md)).
- (+) The outbox makes the dedicated-tier ACL denormalization coherent without a distributed
  transaction; the pgvector tier pays nothing.
- (+) Re-embed from the parsed artifact makes model upgrades routine and source-independent.
- (+) The narrow, schema-validated, conformance-gated connector contract keeps "new source =
  connector + suite, not redesign" true and makes even third-party connectors safe to admit —
  they cannot leak past the gate or write a malformed ACL past the schema boundary.
- (−) A staged DAG + priority scheduler + outbox relay + dual change-detection is materially
  more machinery than a monolithic ingest job; justified by resumability, R8, and coherence.
- (−) The conformance gate slows new-source onboarding (fixture corpus + passing suite
  required) — a deliberate cost: a source that can't prove its ACL mapping shouldn't serve
  regulated content.
- (−) The reconciliation crawl and OBO escape hatch add source load / latency; bounded by
  throttling (P2) and by being opt-in per class.

## Alternatives

- **Monolithic ingest job** — rejected: any failure re-hits the source; scales to the slowest
  stage; a poison item stalls everything.
- **Exactly-once queue semantics** — rejected: not honestly guaranteeable across a
  heterogeneous relational+vector+object write; idempotent version-keyed writes achieve the
  same effect cheaper.
- **Single FIFO queue** — rejected: a backfill starves a revocation re-sync (R8).
- **Dual-write to relational + vector without an outbox** (dedicated tier) — rejected: a crash
  between writes leaves a permanent stale-ACL chunk (R3/R4).
- **Re-embed by re-crawling the source** — rejected: needless source load / rate-limit
  exposure / fails if the source is offline; the parsed artifact exists to avoid this.
- **Poll-only change detection** — rejected as primary: can't meet a 5-min P0 SLA at scale;
  webhooks primary, reconciliation crawl as the lossy-feed backstop.
- **Bespoke integration per source / trusting declared confidence / mapping by email-name** —
  rejected: erodes the source-agnostic core, and each is a direct R1 leak vector.
- **One worker identity with all credentials** — rejected: a compromise could both exfiltrate
  a source and rewrite ACLs; per-stage least privilege splits the two.

## Revisit when

- [Governance](../../governance/) (Cycle 7) **ratifies the freshness SLA** (open Q#7) → fold
  the ratified P0/P1 numbers into the priority-class targets and the relay-lag alarm.
- A tenant graduates to a dedicated vector engine → its persist stage switches from same-tx to
  the outbox relay (a Deployment runbook event; no ADR change — the `VectorIndex` port keeps
  the write shape stable).
- [Deployment](../../deployment/) selects the concrete broker per tier (Postgres/Redis-queue →
  Kafka/NATS/SQS) → confirm it satisfies the `TaskQueue` port (durable, at-least-once,
  per-key order, DLQ).
- A source exposes a materially better change feed, or a new content type needs a new
  parser/chunking rule → a new connector version / stage-2 parser; the DAG and gate are
  unchanged.
- Sustained P0 DLQ or relay-lag alarms in production → tune reserved P0 capacity / relay poll
  frequency (cost tuning, not redesign).
