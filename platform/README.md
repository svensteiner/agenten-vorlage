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
| [security/](security/) | Identity, isolation, data protection, threat model. **Cycle 28:** [trust-edge hardening](security/01-trust-edge-hardening.md) — the three edges earlier cycles handed to Security (E1 Track-B managed-endpoint egress, E2 substrate run-state residency/isolation S3/S5, E3 agent→agent handoff privilege-escalation), each with construction + independent predicate + runtime verifier + fail-closed default + audit evidence; +5 threat-model entries. | **Seeded (Cycle 1) · Extended (Cycle 28)** |
| [rag/](rag/) | Retrieval-augmented generation pipeline | **Seeded** |
| [permissions/](permissions/) | Authorization, ACL propagation, row/document-level access | **Seeded** |
| [storage/](storage/) | Object, vector, relational, cache storage | **Seeded** |
| [metadata/](metadata/) | Catalog, lineage, classification, tagging | **Seeded** |
| [workers/](workers/) | Ingestion, embedding, and job orchestration | **Seeded** |
| [api/](api/) | External API surface, contracts, versioning | **Seeded** |
| [deployment/](deployment/) | Topology, environments, CI/CD, DR | **Seeded** |
| [governance/](governance/) | Model governance, audit, compliance, cost | **Seeded** |
| [models/](models/) | Model hosting & serving substrate (in-boundary OSS vs. contractually-private managed), per-tier×class routing behind the Gateway — **resolves open Q#3** | **Seeded (Cycle 22)** |
| [orchestration/](orchestration/) | Agent orchestration posture: extend `core/`'s planner/verifier loop into the distributed multi-agent orchestrator (choke points stay ours); durable execution behind an `ExecutionBackend` port; bounded pack-declared agent graphs — **resolves open Q#6**. **Cycle 27:** the distributed [`ExecutionBackend` substrate](orchestration/01-execution-backend-substrate.md) — adapter design (two substrate shapes behind the built port), exactly-once *observable* execution, per-tier reserved-capacity sizing, adapter-swap contract. | **Seeded (Cycle 23) · Extended (Cycle 27)** |
| [packs/](packs/) | Domain packs (**10 planned seeded** — Finance + HR + Legal + Audit + KM + SAP + SharePoint + Email + Document Intelligence + Reporting; **+ Procurement, the first external-counterparty + sealed-bid test, Cycle 29; + Manufacturing, the first author-less-machine-data + export-control test, Cycle 31**) + the **[runtime pack-load SPI](packs/01-pack-load-spi.md)** (the fail-closed loader that makes the pack contract executable) — the "new domain = pack, not redesign" proof | **Planned surface complete (Cycle 20); load SPI designed (Cycle 21); +Procurement (Cycle 29); +Manufacturing (Cycle 31)** |
| [engineering/](engineering/) | The `platform/`→`core/` **reconciliation track**: ground-truth `core/` audit + gap ledger + sequenced TDD build plan discharging [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md) (pack-load loader) & [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) (orchestrator re-host). **Cycles 25–26 executed it** — inert gates wired live, full `core/packs/` loader (marquee test green), `run()` re-expressed against the `ExecutionBackend` port (behaviour parity), whole-`core` coverage floor locked in CI; 62→131→193 tests. **Definition-of-done fully met.** | **Seeded (Cycle 24) · Executed (Cycles 25–26) — COMPLETE** |

## Documentation contract

Every document in this folder must answer: **Why**, **How**, **Trade-offs**,
**Alternatives**, and **Future scalability**. Decisions that shape more than one
component are recorded as an ADR and linked from the relevant document.
