# Governance, Audit & Cost

> Status: **Seeded** (Cycle 7) · Owner: Platform Governance / Security / Finance-Ops

**Scope.** The platform's **policy plane** — model governance, audit-log usage, compliance
mapping per domain, retention/erasure policy, the sensitivity-label policy, the ratified
freshness SLA, and the per-tenant cost model & budgets.

## Documents

- **[00-governance-and-audit.md](00-governance-and-audit.md)** — the governance deep dive.
  Ratifies the three decisions queued by upstream cycles (freshness SLA, label policy,
  retention/erasure/cost), specifies audit usage (retention, access, evidence), model
  governance, the compliance control map, and the safety-preserving cost/budget model (R5).
  Implements [ADR-0012](../architecture/adr/ADR-0012-governance-audit-and-cost.md).

## What Governance owns vs. consumes

Governance owns **policy, not mechanism**: it adds no hot-path runtime component, only a
versioned policy store and a reporting/metering surface over the existing
[audit store](../storage/00-storage-architecture.md). It **consumes** the enforcement points
built by earlier cycles — the [Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md),
the [retrieval filter/redactor](../rag/00-retrieval-pipeline.md), the
[worker priority scheduler](../workers/00-ingestion-architecture.md) — and supplies the
numbers, tables, and budgets they enforce.

## Handed downstream

- **[Deployment](../deployment/)** — actual prices, budget-envelope sizes, SLA capacity
  sizing, data residency/region.
- **[Metadata](../metadata/)** — the classification schema the label policy consumes.
- **[API](../api/)** — the surface exposing budgets, DSAR/erasure, and audit export to clients.
