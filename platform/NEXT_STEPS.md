# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 1 (foundation established)
- **Last updated:** 2026-07-05
- **Documentation root:** `platform/` — the single source of truth.

---

## 0. How to run a cycle (process reminder)

1. Read every Markdown file under `platform/` (start with this file).
2. Do the **highest-priority open item** in §6 — not everything.
3. Create/extend Markdown docs (each answers Why / How / Trade-offs / Alternatives /
   Future scalability). Prefer **extending** existing docs over duplicating.
4. If a decision shapes >1 component, add an ADR under
   `architecture/adr/` and link it.
5. Update this file: move items Completed, add new risks/questions, re-prioritize.

---

## 1. Completed work

### Cycle 1 (2026-07-05) — Foundation
- Established `platform/` as the documentation root with a per-concern folder layout
  (architecture, security, rag, permissions, storage, metadata, workers, api,
  deployment, governance) and a navigation index (`platform/README.md`).
- **[Vision & Principles](architecture/00-vision-and-principles.md)** — mission,
  target domains, 8 non-negotiable principles, honest trade-offs, non-goals.
- **[Platform Overview](architecture/01-platform-overview.md)** — C4 context +
  container diagrams, the **three-plane model** (Query / Ingestion / Data + cross-
  cutting), request and ingestion lifecycles as sequence diagrams.
- **[Security Architecture](security/00-security-architecture.md)** — trust boundary,
  identity/authz, multi-tenant isolation tiers, data protection, STRIDE + OWASP-LLM
  threat model, fail-closed doctrine.
- **[ADR log](architecture/adr/)** — ADR-0001 (private RAG shape), ADR-0002 (reuse
  template core as tenancy seed), ADR-0003 (model gateway), ADR-0004 (permission-
  faithful retrieval).

---

## 2. Architecture decisions (accepted so far)

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| ADR-0001 | Privately-hosted, permission-aware RAG | Fresh, auditable, per-user-filterable knowledge in-boundary |
| ADR-0002 | Reuse template core/project split as tenancy seed | Continuity; domain-agnostic core already proven |
| ADR-0003 | All inference via a Model Gateway | One choke point for governance, cost, vendor independence |
| ADR-0004 | Enforce end-user permissions at query time | Safe for Finance/HR/Legal/Audit; fail closed |

---

## 3. Open questions (need a decision in an upcoming cycle)

1. **Vector store choice** — self-hosted (pgvector, Qdrant, Milvus, Weaviate, Elastic)
   vs. managed private. Drives Storage + Deployment. **Blocks the RAG deep dive.**
2. **Permission normalization model** — one canonical principal/ACL model that
   SharePoint, SAP, email, and file shares all map into. Hardest correctness problem.
3. **Model hosting** — in-boundary OSS models vs. contractually-private managed
   endpoints (or both, by tenant tier). Drives cost, latency, and compliance posture.
4. **Chunking & embedding strategy** — per-domain vs. universal; how to handle tables
   (Finance/SAP), long contracts (Legal), and email threads.
5. **Tenancy granularity** — is a "tenant" a customer, a department, or a domain?
   Affects isolation tiers and cost model.
6. **Agent framework** — extend the existing `core/` planner/verifier into the
   distributed orchestrator, or adopt a framework? (Relates to ADR-0002.)
7. **Freshness SLA** — acceptable staleness window between a source change (content or
   ACL) and the index reflecting it. Drives connector/worker design.

---

## 4. Technical risks (tracked)

| # | Risk | Severity | Mitigation direction |
|---|------|----------|----------------------|
| R1 | **Permission-model mismatch** — source ACLs can't be faithfully normalized → leak | **Critical** | Canonical principal model + per-connector conformance tests; isolation-tier fallback |
| R2 | **Prompt injection via retrieved content** | **Critical** | Retrieved text = data not instructions; verifier; tool-call policy gate |
| R3 | **Stale permissions** — user loses access but index still serves it | High | Short TTL query-time re-check; change-driven re-sync; query-time precedence |
| R4 | **Cross-tenant leakage** via a filtering bug | High | Isolate by namespace/cluster, not just `tenant_id` filter; fail closed |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | Gateway budgets, model tiering, tenant cost model, storage tiers |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | Connector contract + conformance test suite; versioned connectors |
| R7 | **Vendor lock-in** at model or vector layer | Medium | Gateway indirection (models); abstraction over vector store |
| R8 | **Ingestion backlog** starves freshness | Medium | Queue backpressure, autoscaling workers, prioritization by domain |

---

## 5. Documentation gaps (folders still empty / thin)

- `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding). **Empty.**
- `permissions/` — the canonical ACL model + per-source mapping. **Empty. Highest value.**
- `storage/` — vector/object/relational/cache choices + isolation tiers. **Empty.**
- `metadata/` — catalog, lineage, classification schema. **Empty.**
- `workers/` — ingestion/embedding job orchestration, queue design. **Empty.**
- `api/` — external API surface, contracts, versioning. **Empty.**
- `deployment/` — topology, environments, CI/CD, DR/BCP. **Empty.**
- `governance/` — model governance, audit usage, compliance mapping, cost. **Empty.**

---

## 6. Priority list & recommended implementation order

Ordered by **architectural leverage** (unblocks the most, de-risks the most).

### ▶ Cycle 2 (do next): **Permissions & Identity deep dive**
Write `permissions/00-authorization-model.md`. Define the **canonical principal/ACL
model** and how SharePoint, SAP, email, and file-share ACLs map into it; specify
query-time enforcement, delegated access, caching/TTL, and the per-connector
**permission-conformance test**. *Why first:* it is the platform's hardest correctness
guarantee (R1, R3, R4) and it gates trustworthy retrieval. Depends on nothing new.

### Cycle 3: **RAG pipeline deep dive**
Write `rag/00-retrieval-pipeline.md`: chunking strategy, embeddings, hybrid
(vector+keyword) search, reranking, permission filtering integration, grounding &
citation, and the verifier's contract. Resolves open questions 4; needs a provisional
answer to open question 1.

### Cycle 4: **Storage & tenancy deep dive**
Write `storage/00-storage-architecture.md`: vector/object/relational/cache selection,
isolation tiers (namespace vs. cluster), encryption/BYOK, versioning & deletion.
Resolves open questions 1 and 5.

### Cycle 5: **Ingestion workers & connectors**
Write `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md`:
queue design, worker scaling, connector contract, change detection, freshness SLA
(open question 7), backpressure (R8).

### Cycle 6: **Governance, audit & cost**
Write `governance/00-governance-and-audit.md`: model governance, audit-log usage,
compliance mapping (per domain), cost model and budgets (R5).

### Later (backlog)
- `api/` — external API contracts & versioning.
- `deployment/` — reference topology, environments, CI/CD, DR/BCP.
- `metadata/` — catalog & lineage schema (partially informed by permissions + storage).
- Per-domain **pack specifications** (Finance, HR, Legal, ...) once the core deep dives
  are stable — proving the "new domain = pack, not redesign" bet.
- Reconcile `platform/` architecture with the existing `core/` code
  (ADR-0002 implementation path).

---

## 7. Consistency checklist (run before ending each cycle)

- [ ] New docs answer Why / How / Trade-offs / Alternatives / Future scalability.
- [ ] New cross-component decisions captured as an ADR and linked.
- [ ] No duplicated content; extended existing docs where possible.
- [ ] `platform/README.md` domain-map statuses updated.
- [ ] This file's §1, §3, §4, §6 updated.
