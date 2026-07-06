# AI Studio — Private AI Platform (Architecture)

This folder is the **single source of truth** for the architecture of the AI Studio
private AI platform. It is maintained incrementally by the Continuous Architecture
Agent. Every execution extends this documentation; nothing is redesigned from scratch.

> **Relationship to the code repository.** The surrounding repository (`core/`,
> `project/`, `agent.py`) is a reusable automation-agent template. The platform
> documented here is the larger enterprise system that this template will grow into:
> a reusable, private, multi-domain AI platform. The template's "reusable core +
> project pack" split is the seed of the platform's tenancy model — see
> [ADR-0002](architecture/adr/ADR-0002-reuse-existing-template-core.md).

## Start here

1. [NEXT_STEPS.md](NEXT_STEPS.md) — **read first every cycle.** Backlog, risks,
   decisions, priorities, recommended implementation order.
2. [Vision & Principles](architecture/00-vision-and-principles.md) — what we are
   building and the non-negotiable design principles.
3. [Platform Overview](architecture/01-platform-overview.md) — high-level (C4
   context + container) architecture with diagrams.
4. [Architecture Decision Records](architecture/adr/) — the log of *why*.

## Domain map

Each folder owns one architectural concern. Documents are numbered so reading order
is stable.

| Folder | Concern | Status |
|--------|---------|--------|
| [architecture/](architecture/) | Vision, high-level structure, ADR log | **Seeded** |
| [security/](security/) | Identity, isolation, data protection, threat model | **Seeded** |
| [rag/](rag/) | Retrieval-augmented generation pipeline | **Seeded** |
| [permissions/](permissions/) | Authorization, ACL propagation, row/document-level access | **Seeded** |
| [storage/](storage/) | Object, vector, relational, cache storage | **Seeded** |
| [metadata/](metadata/) | Catalog, lineage, classification, tagging | **Seeded** |
| [workers/](workers/) | Ingestion, embedding, and job orchestration | **Seeded** |
| [api/](api/) | External API surface, contracts, versioning | **Seeded** |
| [deployment/](deployment/) | Topology, environments, CI/CD, DR | **Seeded** |
| [governance/](governance/) | Model governance, audit, compliance, cost | **Seeded** |
| [models/](models/) | Model hosting & serving substrate (in-boundary OSS vs. contractually-private managed), per-tier×class routing behind the Gateway — **resolves open Q#3** | **Seeded (Cycle 22)** |
| [orchestration/](orchestration/) | Agent orchestration posture: extend `core/`'s planner/verifier loop into the distributed multi-agent orchestrator (choke points stay ours); durable execution behind an `ExecutionBackend` port; bounded pack-declared agent graphs — **resolves open Q#6** | **Seeded (Cycle 23)** |
| [packs/](packs/) | Domain packs (**all 10 planned seeded** — Finance + HR + Legal + Audit + KM + SAP + SharePoint + Email + Document Intelligence + Reporting) + the **[runtime pack-load SPI](packs/01-pack-load-spi.md)** (the fail-closed loader that makes the pack contract executable) — the "new domain = pack, not redesign" proof | **Surface complete (Cycle 20); load SPI designed (Cycle 21)** |
| [engineering/](engineering/) | The `platform/`→`core/` **reconciliation track**: ground-truth `core/` audit + gap ledger + sequenced TDD build plan discharging [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md) (pack-load loader) & [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) (orchestrator re-host). **Cycle 25 executed it** — inert gates wired live, `ExecutionBackend` port, full `core/packs/` loader (marquee test green); 62→131 tests. Remaining: WP-A4 + CI coverage gate | **Seeded (Cycle 24) · Executed (Cycle 25)** |

## Documentation contract

Every document in this folder must answer: **Why**, **How**, **Trade-offs**,
**Alternatives**, and **Future scalability**. Decisions that shape more than one
component are recorded as an ADR and linked from the relevant document.
