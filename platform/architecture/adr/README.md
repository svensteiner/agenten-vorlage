# Architecture Decision Records (ADRs)

An ADR captures a single significant decision: its context, the choice, the
alternatives, and the consequences. ADRs are **append-only**. A decision is never
edited away — if it changes, a new ADR **supersedes** the old one and links back.

## Format

Each ADR uses: **Status** (Proposed / Accepted / Superseded), **Context**,
**Decision**, **Consequences**, **Alternatives**, **Revisit-when**.

## Index

| ID | Title | Status |
|----|-------|--------|
| [0001](ADR-0001-platform-shape-private-rag.md) | Platform shape: privately-hosted, permission-aware RAG | Accepted |
| [0002](ADR-0002-reuse-existing-template-core.md) | Reuse the template's core/project split as the tenancy seed | Accepted |
| [0003](ADR-0003-model-gateway-indirection.md) | All inference goes through a Model Gateway | Accepted |
| [0004](ADR-0004-permission-faithful-retrieval.md) | Enforce end-user permissions at query time | Accepted |

New ADRs are added by later cycles as decisions are made.
