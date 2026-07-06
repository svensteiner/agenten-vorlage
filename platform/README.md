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
| [packs/](packs/) | Domain packs (Finance + HR + Legal + Audit + KM + SAP + SharePoint + Email seeded) — the "new domain = pack, not redesign" proof | **Finance + HR + Legal + Audit + KM + SAP + SharePoint + Email seeded** |

## Documentation contract

Every document in this folder must answer: **Why**, **How**, **Trade-offs**,
**Alternatives**, and **Future scalability**. Decisions that shape more than one
component are recorded as an ADR and linked from the relevant document.
