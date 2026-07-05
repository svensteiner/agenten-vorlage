# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 3 (permissions & identity deep dive)
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

### Cycle 3 (2026-07-05) — Permissions & Identity deep dive
- Wrote **[permissions/00-authorization-model.md](permissions/00-authorization-model.md)** —
  the platform's hardest correctness guarantee. Defines the **canonical four-noun model**
  (Subject / Principal / Grant / Resource), the **Canonical Principal Identifier**
  (`tenant:source:type:stable-id`, keyed on non-reusable source ids), the **single
  decision predicate** (tenant → confidence=`exact` → deny-wins → require-allow),
  query-time **effective-principal resolution** via an identity graph (nested-group
  expansion + explicit cross-source links), **filter-during-retrieval** mechanics,
  per-source ACL mapping (SharePoint / SAP / Email / file share), **sensitivity labels as
  a second independent gate**, the **freshness** strategy (query-time precedence + short
  revocable TTL + change-driven re-sync), the **unmappable-source quarantine doctrine**,
  delegated/OBO access, and the **permission-conformance test suite** (the production gate).
- Recorded **[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)** —
  normalize every source ACL into one canonical model (the *how* behind ADR-0004's *what*).
  Owns risks R1, R3, R4.
- Updated indexes: ADR index, `permissions/README.md` (stub → real), `platform/README.md`
  domain map (permissions → **Seeded**).
- **Directly de-risks:** R1 (mismatch → conformance suite + confidence-gated deny),
  R3 (staleness → query-time precedence + SLA), R4 (cross-tenant → tenant-namespaced CPIs).
- **Provisionally answered open questions:** #2 (permission normalization model — decided),
  #7 (freshness SLA — proposed: principals ≤5 min, restricted resource ACLs ≤15 min,
  pending Governance ratification).
- ⏳ **Handed to downstream cycles:** vector store must support efficient **set-overlap
  filtering** on principal arrays (hard requirement → Storage, open question #1); label
  policy + SLA ratification → Governance; change-driven re-sync → Workers.

### Cycle 2b (2026-07-05) — v3.0 harvest + client settings UI
- **Client settings UI** ([ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md)):
  `control_panel.py` + `EINSTELLUNGEN.bat` — browser page (stdlib only) to set autonomy,
  models, limits **and manage connectors** (`connectors.yaml` allowlist) with validation;
  syncs `config.json` + `project/manifest.json`. End-to-end tested.
- **Harvested v3.0 assets onto the core** ([ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md)):
  `core/workers.py` (least-privilege WorkerRegistry), `core/handoff.py` (allowlisted
  router), `tools/check.py` (project-pack validator, CI exit codes),
  `scripts/deploy.{sh,ps1}`, `pytest.ini`, `requirements-dev.txt`. Added `workers`/
  `handoffs` config to `project/manifest.json`.
- **Tests:** 62 green (23 workers + 24 handoff + 11 check + 4 tools).
- ⏳ **Still staged (not done):** wiring `WorkerRegistry`/`HandoffRouter` INTO
  `core/orchestrator` at runtime; rewriting v3.0's `test_agent.py` against `core/`;
  retargeting `test_brain`/`test_governance`; coverage gate `--cov=core --cov-fail-under=80`;
  deeper governance hardening (high-risk block before autonomy shortcut, per ADR-0006).

### Cycle 2 (2026-07-05) — Branch consolidation (design council)
- Convened a **5-member design council** (Enterprise Architect, Senior Engineer,
  Security & Governance, QA & Test, Redundancy & Consistency) to reconcile 4 divergent
  template branches into "the perfect agent template."
- **Decision → [ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md):**
  keep `core/`+`project/` as base, **merged `tender-feistel`** (skills, connectors,
  steering examples, leaf-write governance, financial-services patterns), and defined a
  **harvest plan** for the v3.0 (`kind-keller`) fork instead of merging it wholesale.
- **Security fix → [ADR-0006](architecture/adr/ADR-0006-fail-closed-autonomy-default.md):**
  reverted the fail-open full-autonomy default to **fail-closed-by-default**
  (`core/governance.py._approval_required` now defaults True; autonomy is explicit opt-in
  via `autonomy_level: "max"`).
- Merge landed on `main`, core modules import clean, existing tests pass.
- ⏳ **Not yet merged:** the v3.0 asset harvest (see §6 Cycle 2b) and the other
  contained branches are superseded.

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
| ADR-0008 | Normalize every source ACL into one canonical principal model | One filterable predicate; new source = connector + conformance test, not a redesign |

---

## 3. Open questions (need a decision in an upcoming cycle)

1. **Vector store choice** — self-hosted (pgvector, Qdrant, Milvus, Weaviate, Elastic)
   vs. managed private. Drives Storage + Deployment. **Blocks the RAG deep dive.**
2. ✅ **DECIDED (Cycle 3, [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)).**
   ~~Permission normalization model~~ — canonical four-noun model + CPI, normalize at
   ingestion, enforce one predicate at query time. Remaining sub-question deferred to
   connector cycles: the exact `map_acl` fidelity achievable per SAP module.
3. **Model hosting** — in-boundary OSS models vs. contractually-private managed
   endpoints (or both, by tenant tier). Drives cost, latency, and compliance posture.
4. **Chunking & embedding strategy** — per-domain vs. universal; how to handle tables
   (Finance/SAP), long contracts (Legal), and email threads.
5. **Tenancy granularity** — is a "tenant" a customer, a department, or a domain?
   Affects isolation tiers and cost model.
6. **Agent framework** — extend the existing `core/` planner/verifier into the
   distributed orchestrator, or adopt a framework? (Relates to ADR-0002.)
7. **Freshness SLA** — acceptable staleness window between a source change (content or
   ACL) and the index reflecting it. Drives connector/worker design. **Provisional
   (Cycle 3):** principal changes ≤5 min, restricted resource-ACL changes ≤15 min,
   public best-effort — pending [Governance](governance/) ratification and a cost check
   in the Workers cycle.

---

## 4. Technical risks (tracked)

| # | Risk | Severity | Mitigation direction |
|---|------|----------|----------------------|
| R1 | **Permission-model mismatch** — source ACLs can't be faithfully normalized → leak | **Critical** | ✅ *Design mitigated (Cycle 3):* canonical model + `acl_confidence` gate (approximate→deny) + per-connector conformance suite + quarantine tier. Residual: correct **implementation** of each connector's `map_acl`. |
| R2 | **Prompt injection via retrieved content** | **Critical** | Retrieved text = data not instructions; verifier; tool-call policy gate |
| R3 | **Stale permissions** — user loses access but index still serves it | High | Short TTL query-time re-check; change-driven re-sync; query-time precedence |
| R4 | **Cross-tenant leakage** via a filtering bug | High | Isolate by namespace/cluster, not just `tenant_id` filter; fail closed |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | Gateway budgets, model tiering, tenant cost model, storage tiers |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | Connector contract + conformance test suite; versioned connectors |
| R7 | **Vendor lock-in** at model or vector layer | Medium | Gateway indirection (models); abstraction over vector store |
| R8 | **Ingestion backlog** starves freshness | Medium | Queue backpressure, autoscaling workers, prioritization by domain |

---

## 5. Documentation gaps (folders still empty / thin)

- `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding). **Empty. Highest value now** (consumes the permission filter).
- ✅ `permissions/` — canonical ACL model + per-source mapping. **Seeded (Cycle 3).**
- `storage/` — vector/object/relational/cache choices + isolation tiers. **Empty.** Now has a hard input: must support principal set-overlap filtering (see permissions §6).
- `metadata/` — catalog, lineage, classification schema. **Empty.**
- `workers/` — ingestion/embedding job orchestration, queue design. **Empty.**
- `api/` — external API surface, contracts, versioning. **Empty.**
- `deployment/` — topology, environments, CI/CD, DR/BCP. **Empty.**
- `governance/` — model governance, audit usage, compliance mapping, cost. **Empty.**

---

## 6. Priority list & recommended implementation order

Ordered by **architectural leverage** (unblocks the most, de-risks the most).

### ✅ Cycle 2b (DONE — see §1): harvested deploy scripts, `tools/check.py`,
`core/workers.py`, `core/handoff.py`, tests (62 green), and shipped the client settings
UI with connector management. Remaining harvest work moved to Cycle 2c below.

### ⏸ Cycle 2c (OPEN — parallel *engineering* track, not the architecture-doc path):
**Wire the harvested modules into the runtime + finish tests.** This is code work on the
`core/` template, independent of the platform architecture docs. Pick it up in a coding
cycle; the doc track (below) does not depend on it.
1. **Wire `WorkerRegistry` + `HandoffRouter` into `core/orchestrator`/`dispatcher`** so
   the ported modules actually scope tools and route handoffs at runtime (currently they
   are available + configured + unit-tested, but not yet called by the loop). Reconcile
   worker trust-level ↔ tender leaf-write into ONE governance API.
2. **Finish the test port:** rewrite v3.0's `test_agent.py` against `core/orchestrator`;
   retarget `test_brain`/`test_governance` to the `core/` modules; enforce
   `--cov=core --cov-fail-under=80` in CI (GitHub Actions).
3. **Deeper governance hardening** (ADR-0006 follow-up): run the high-risk hard block
   *before* the autonomy shortcut; make escalation a deterministic policy decision, not an
   LLM `needs_human` flag.
4. **Onboarding UX polish** — fold kind's plain-German beginner prompts + self-test into
   `agent_cli.py`; add Python-check/pip-install robustness to the `.bat` launchers. Then
   **delete** the superseded `kind-keller` branch content.
**Do NOT push a broken tree — gate on tests green.**

### ✅ Cycle 3 (DONE — see §1): **Permissions & Identity deep dive**
Wrote `permissions/00-authorization-model.md` + [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md).
Canonical model, query-time enforcement, freshness, conformance suite. Mitigates R1/R3/R4
by design; decided open question #2; provisional answer to #7.

### ▶ Cycle 4 (do next): **RAG pipeline deep dive**
Write `rag/00-retrieval-pipeline.md`: chunking strategy, embeddings, hybrid
(vector+keyword) search, reranking, **integration of the permission filter from
[permissions §6](permissions/00-authorization-model.md)** (retrieval must apply the
allow/deny + `acl_confidence=exact` + tenant predicate — do not re-specify it, consume
it), grounding & citation, and the verifier's contract. *Why next:* the permission
model now exists to plug into; RAG is the query-plane payoff and unblocks nothing until
it's specified. Resolves open question #4; needs a provisional answer to #1.

### Cycle 5: **Storage & tenancy deep dive**
Write `storage/00-storage-architecture.md`: vector/object/relational/cache selection,
isolation tiers (namespace vs. cluster), encryption/BYOK, versioning & deletion.
**Hard input from Cycle 3:** the vector store MUST support efficient principal
**set-overlap filtering** (allow/deny arrays) — this is now a selection criterion, not a
nice-to-have. Resolves open questions 1 and 5.

### Cycle 6: **Ingestion workers & connectors**
Write `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md`:
queue design, worker scaling, connector contract, change detection, freshness SLA
(open question 7), backpressure (R8). **Consumes Cycle 3:** the connector contract must
include `map_acl` + `list_principal_changes` + the permission-conformance suite as gates.

### Cycle 7: **Governance, audit & cost**
Write `governance/00-governance-and-audit.md`: model governance, audit-log usage,
compliance mapping (per domain), cost model and budgets (R5). **Ratify from Cycle 3:**
the freshness SLA (open question #7) and the sensitivity-label policy (permissions §7).

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
