# Deployment

> Status: **Seeded** (Cycle 10)

**Scope.** The **physical projection** of the logical platform: reference topology per tenant
tier, environments, CI/CD (conformance/eval gates), SLA-capacity sizing, cost/residency routing,
catalog partitioning/archival, gateway/streaming ops, and DR/BCP. Introduces **no new logical
component and no new guarantee** — it makes the existing ones affordable, operable, and survivable.

## Documents

- **[00-deployment-topology.md](00-deployment-topology.md)** — the deep dive. Maps the
  [three planes](../architecture/01-platform-overview.md) onto edge/query/ingestion/data
  substrates; specifies the Shared/Isolated tiers + graduation; the safety-gated CI/CD pipeline
  (the [connector conformance suite](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
  as an un-overridable release veto); reserved-P0 SLA-capacity sizing; cost-envelope/residency
  routing; catalog partitioning + cold-lineage archival + integrity checks; and DR/BCP with
  **ACL-first, fail-closed recovery**.

## Key decision

- **[ADR-0015](../architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md)** —
  active-passive DR per residency region, ACL-first recovery ordering, vectors rebuilt (not
  backed up), tiered RPO/RTO with reserved (not autoscaled) P0 capacity.

## Consumes (the inputs five cycles queued here)

[Storage §3.3/§5.2](../storage/00-storage-architecture.md) (tiers) ·
[Workers §3.2/§4/§10](../workers/00-ingestion-architecture.md) (broker, priority, SLA obs) ·
[Governance §3/§7](../governance/00-governance-and-audit.md) (SLA numbers, cost) ·
[Metadata §7/§11](../metadata/00-catalog-and-lineage.md) (partitioning, archival, integrity) ·
[API §10](../api/00-api-surface.md) (rate-limit/streaming ops).

Follows the documentation contract (Why / How / Trade-offs / Alternatives / Future scalability).
