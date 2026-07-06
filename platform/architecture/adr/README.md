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
| [0005](ADR-0005-template-consolidation-council.md) | Template consolidation: one core, harvest the v3.0 fork | Accepted |
| [0006](ADR-0006-fail-closed-autonomy-default.md) | Fail-closed autonomy is the template default | Accepted |
| [0007](ADR-0007-client-configuration-surface.md) | Client configuration surface (local settings UI) | Accepted |
| [0008](ADR-0008-canonical-principal-acl-model.md) | Normalize every source ACL into one canonical principal model | Accepted |
| [0009](ADR-0009-hybrid-retrieval-and-chunking.md) | Hybrid permission-filtered retrieval with structure-aware chunking | Accepted |
| [0010](ADR-0010-storage-topology-and-tenancy.md) | Storage topology & tenancy: five-store data plane, pgvector-default vector layer, tenant = customer org | Accepted |
| [0011](ADR-0011-ingestion-workers-and-connector-framework.md) | Ingestion plane: staged-DAG workers, at-least-once + idempotent writes, conformance-gated connector contract | Accepted |
| [0012](ADR-0012-governance-audit-and-cost.md) | Governance plane: ratified SLA/label/retention policy, audit-as-evidence, safety-preserving cost model | Accepted |
| [0013](ADR-0013-canonical-metadata-lineage-schema.md) | Canonical metadata, catalog & lineage schema as a shared, versioned contract | Accepted |
| [0014](ADR-0014-api-contract-surface.md) | API contract surface: token-bound identity, dual sync/streaming answer, job-based heavy work, URL-major versioning | Accepted |
| [0015](ADR-0015-deployment-dr-and-regional-topology.md) | Deployment DR & regional topology: active-passive per residency region, ACL-first recovery, rebuilt vectors | Accepted |
| [0016](ADR-0016-domain-pack-contract.md) | Domain pack contract: a pack is additive data + policy (tighten-only), never a horizontal change | Accepted |
| [0017](ADR-0017-runtime-pack-load-spi.md) | Runtime pack-load SPI: a validating, fail-closed loader that makes the pack contract executable (a floor-loosening pack is structurally rejected, not merely reviewed) | Accepted |
| [0018](ADR-0018-model-hosting-and-serving-posture.md) | Model hosting & serving posture: a dual-track fabric (in-boundary OSS + contractually-private managed), routed per (tenant tier × data class) behind the Model Gateway; closes open Q#3 | Accepted |
| [0019](ADR-0019-agent-orchestration-posture.md) | Agent orchestration posture: extend `core/`'s planner/verifier into the distributed orchestrator (choke points stay ours); adopt durable execution behind an `ExecutionBackend` port, never a framework that owns the loop; closes open Q#6 | Accepted |

New ADRs are added by later cycles as decisions are made.
