# ADR-0001 — Platform shape: privately-hosted, permission-aware RAG

- **Status:** Accepted (Cycle 1)
- **Deciders:** Enterprise Architecture
- **Supersedes:** —

## Context

AI Studio needs a foundation that supports many enterprise domains (Finance, Audit,
HR, Legal, Knowledge Management, SAP, SharePoint, Email, Document Intelligence,
Reporting) without redesign. The data is sensitive and regulated; customers require
that data stay inside a controlled trust boundary. Knowledge changes constantly and
must remain auditable and permission-checkable per user.

## Decision

Build a **self-hosted, private, permission-aware Retrieval-Augmented Generation (RAG)
platform** with a governed model gateway and pluggable domain packs. Knowledge stays
**external** to the model (indexed and retrieved), not baked into weights.

## Consequences

- (+) Knowledge is fresh, auditable, and can be filtered per user's permissions.
- (+) Data stays in-boundary; models are hosted privately or via private endpoints.
- (+) New domains are additive (connector + pack).
- (−) We own significant infrastructure (ingestion, vector store, gateway, audit).
- (−) Permission-aware retrieval adds query-time complexity and latency.

## Alternatives

- **Single-vendor AI suite** — lock-in, weak private-hosting and permission semantics.
- **Per-domain bespoke builds** — the current problem: duplicated security, no shared
  governance, slow.
- **Fine-tuning knowledge into models** — stale, unauditable, can't honor per-user ACLs.
- **Public managed AI + connectors** — violates the private-by-default requirement.

## Revisit when

Model context windows and private on-device capabilities change enough that a
retrieval-light or fine-tune-heavy design becomes competitive on freshness *and*
per-user permission fidelity — not just on convenience.
