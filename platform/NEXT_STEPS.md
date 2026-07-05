# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 5 (Storage & tenancy deep dive)
- **Last updated:** 2026-07-05
- **Documentation root:** `platform/` — the single source of truth.
- **Gesamtfortschritt:** **≈ 49 %** (Ende Zyklus 5) — siehe §0.1. **Nach jeder Session melden.**

---

## 0.1 Fortschritt (Gesamtstand, gewichtet)

> Gemessen gegen das Endziel: Doku ausreichend, damit ein Team die komplette Plattform
> ohne zusätzliche Architektur-Vorgabe implementieren kann. **Jeden Zyklus fortschreiben.**

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| Vision & Prinzipien | 10 % | 100 % | 10.0 |
| Security-Architektur | 10 % | 80 % | 8.0 |
| Permissions Deep Dive (Z3) | 12 % | 90 % | 10.8 |
| RAG Deep Dive (Z4) | 12 % | 85 % | 10.2 |
| Storage & Tenancy (Z5) | 10 % | 90 % | 9.0 |
| Workers & Connectors | 10 % | 0 % | 0.0 |
| Metadata / Katalog / Lineage | 6 % | 0 % | 0.0 |
| Governance / Audit / Kosten | 8 % | 0 % | 0.0 |
| API-Surface & Verträge | 5 % | 0 % | 0.0 |
| Deployment / Topologie / DR | 7 % | 0 % | 0.0 |
| Domänen-Pack-Specs (Finance/HR/Legal …) | 6 % | 5 % | 0.3 |
| Code-Reconciliation (`core/`-Umsetzung) | 4 % | 30 % | 1.2 |
| **Summe** | **100 %** | — | **≈ 49 %** |

**Verlauf:** Z1 ≈ 18 % · Z2/2b ≈ 24 % · Z3 ≈ 33 % · Z4 ≈ 40 % · **Z5 ≈ 49 %**.

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

### Cycle 5 (2026-07-05) — Storage & tenancy deep dive
- Wrote **[storage/00-storage-architecture.md](storage/00-storage-architecture.md)** — the
  data-plane payoff. Turns the Cycle 3+4 hard requirements (S1 set-overlap filtering,
  S2 hybrid-under-one-filter, S3 versioned upsert/delete, S4 isolation-by-construction,
  S5 in-boundary+BYOK, S6 rich metadata, S7 append-only audit) into a selected topology:
  the **five-store data plane** (object / vector+keyword / relational-source-of-truth /
  cache / append-only audit), each assigned by scaling axis, consistency, and blast radius.
- **Resolved open question #1 (FINAL):** vector layer = **pgvector-in-Postgres as default**
  (co-locates vector + `text[]` ACL arrays w/ GIN `&&` + `tsvector` full-text + metadata in
  one transaction → both hybrid halves share one filter, ACL denormalization is drift-free),
  **graduating** per-tenant to Qdrant / Elasticsearch on *measured* thresholds. Confirms &
  finalizes [ADR-0009 §6](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)'s
  provisional lean. Introduced the **`VectorIndex` port with no unfiltered-search method** —
  filter-during-retrieval ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md))
  becomes *structurally* impossible to bypass, and vector lock-in (R7) is bounded to one adapter.
- **Resolved open question #5 (FINAL):** **a tenant = one customer organization** (isolation
  & governance boundary); departments/domains are ACL/`visibility` scopes and packs *within*
  a tenant — aligns the storage isolation primitive with the CPI identity namespace.
- Specified **two isolation tiers** per store (Shared: namespace/schema/prefix + RLS +
  unconditional `tenant_id`, two independent controls; Isolated: dedicated cluster/DB/bucket +
  BYOK), **envelope encryption w/ per-tenant DEKs + crypto-erasure**, the
  **ACL-denormalization coherence** rules (same-transaction at pgvector tier; transactional
  outbox at dedicated-engine tier; query-time principal precedence covers the residual gap),
  **re-embed migrations** (blue/green from the parsed object-store artifact — no source re-hit),
  and **right-to-erasure** propagation across all five stores (audit retained as event).
- Recorded **[ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)**.
- Updated indexes: ADR index, `storage/README.md` (stub → real), `platform/README.md`
  domain map (storage → **Seeded**).
- **Directly de-risks:** R4 (cross-tenant → namespace **and** predicate, two controls;
  per-tenant DEK), R5 (cost → pgvector-default + object tiering + quantization levers),
  R7 (vector lock-in → `VectorIndex` port, one adapter per engine).
- ⏳ **Handed to downstream cycles:** the **transactional-outbox relay** + **re-embed/re-sync
  jobs** → [Workers](workers/) (Cycle 6, must honor the §7 coherence bound and the freshness
  SLA); **retention + legal-hold tombstone + per-tenant cost metering + erasure ratification**
  → [Governance](governance/) (Cycle 7); **per-tier topology, graduation thresholds, backup/DR**
  → [Deployment](deployment/); **catalog + lineage schema** detail → [Metadata](metadata/).

### Cycle 4 (2026-07-05) — RAG retrieval pipeline deep dive
- Wrote **[rag/00-retrieval-pipeline.md](rag/00-retrieval-pipeline.md)** — the query-plane
  payoff. Specifies **structure-aware chunking** (heading/clause/table-row/per-email-message,
  with the **mixed-ACL invariant**: a chunk never spans two items with different ACLs),
  **universal embedding space + per-domain normalization** (not per-domain models;
  versioned re-embed on model upgrade), **hybrid search** (dense + BM25, RRF fusion) with
  the **permission predicate pushed into *both* engines** (consumed from Permissions §6,
  not re-specified), **cross-encoder reranking** (+ MMR, degradable latency dial), **context
  assembly** (dedup / budget / cite-tag / label redaction) with the **prompt-injection (R2)
  data-boundary defense**, the **verifier contract** (grounding / citation validity /
  no-context honesty / guardrails / label compliance — refuse-over-guess), a latency budget,
  and a **provisional vector-store position** (open Q#1).
- Recorded **[ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)** —
  hybrid permission-filtered retrieval + structure-aware chunking. Obeys ADR-0004, pushes
  the ADR-0008 predicate into search, mediated by ADR-0003 gateway.
- Updated indexes: ADR index, `rag/README.md` (stub → real), `platform/README.md` domain
  map (rag → **Seeded**).
- **Directly de-risks:** R2 (prompt injection → retrieved-text-as-data boundary + verifier
  backstop). Design mitigation now documented, not just named.
- **Answered open questions:** #4 (chunking & embedding strategy — **decided**:
  structure-aware chunking + universal space + per-domain normalization).
- **Provisionally answered:** #1 (vector store — pgvector for small tenants graduating to a
  dedicated engine; **Storage/Cycle 5 owns the final call**).
- ⏳ **Handed to downstream cycles:** vector + keyword indexes must support efficient
  **set-overlap filtering** on principal arrays and **hybrid search under one metadata
  filter** (hard selection criteria → Storage); chunk parsers per content-type + embedding
  jobs + re-embed migration → Workers; audit-trail fields (principals, chunk IDs, rerank
  scores, verifier verdict) → Governance.

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
| ADR-0009 | Hybrid permission-filtered retrieval + structure-aware chunking | Exact-token + semantic recall; safety stays one index predicate; new domain = parser, not a pipeline change |
| ADR-0010 | Five-store data plane; pgvector-default vector layer (graduate on measured need) behind a filter-only `VectorIndex` port; tenant = customer org | Meets every S1–S7 requirement; ACL stays a single-store `WHERE`; unfiltered search is unrepresentable; lock-in bounded to one adapter |

---

## 3. Open questions (need a decision in an upcoming cycle)

1. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Vector store choice~~ — **pgvector-in-Postgres is the default** (co-locates vector +
   `text[]` ACL arrays w/ GIN `&&` + `tsvector` + metadata in one transactional store),
   **graduating per-tenant** to Qdrant / Elasticsearch on *measured* thresholds (chunk count,
   QPS/SLA, keyword dominance, isolation mandate). All engines sit behind a **`VectorIndex`
   port that has no unfiltered-search method**. See [Storage §3](storage/00-storage-architecture.md).
   Remaining sub-question deferred to [Workers](workers/): the transactional-outbox relay
   that keeps the denormalized chunk-ACL coherent at the dedicated-engine tier.
2. ✅ **DECIDED (Cycle 3, [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)).**
   ~~Permission normalization model~~ — canonical four-noun model + CPI, normalize at
   ingestion, enforce one predicate at query time. Remaining sub-question deferred to
   connector cycles: the exact `map_acl` fidelity achievable per SAP module.
3. **Model hosting** — in-boundary OSS models vs. contractually-private managed
   endpoints (or both, by tenant tier). Drives cost, latency, and compliance posture.
4. ✅ **DECIDED (Cycle 4, [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)).**
   ~~Chunking & embedding strategy~~ — **structure-aware chunking** (heading/clause/table-row/
   per-email-message; mixed-ACL invariant) + **universal embedding space with per-domain
   text normalization** (not per-domain models) + versioned re-embed on model upgrade. See
   [RAG §2–§3](rag/00-retrieval-pipeline.md). Remaining sub-question deferred to Workers:
   the exact per-content-type parser fidelity (OCR layout, SAP table serialization).
5. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Tenancy granularity~~ — **a tenant = one customer organization** (isolation & governance
   boundary owning its data, identity namespace, policies, cost envelope). Departments and
   domains are ACL/`visibility` scopes and packs *within* a tenant, not separate tenants —
   this keeps the CPI identity namespace and nested-group resolution intact. See
   [Storage §5](storage/00-storage-architecture.md).
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
| R2 | **Prompt injection via retrieved content** | **Critical** | ✅ *Design mitigated (Cycle 4, [RAG §6.1, §7](rag/00-retrieval-pipeline.md)):* retrieved text delivered inside a data boundary (not instructions), retrieved content cannot alter tool/routing/citation policy, verifier enforces grounding + guardrails as the backstop. Residual: implementation hardening of the verifier + red-team corpus. |
| R3 | **Stale permissions** — user loses access but index still serves it | High | Short TTL query-time re-check; change-driven re-sync; query-time precedence |
| R4 | **Cross-tenant leakage** via a filtering bug | High | ✅ *Design mitigated (Cycle 5, [Storage §5.2](storage/00-storage-architecture.md)):* Shared tier uses **two independent controls** (per-tenant namespace/schema **and** an unconditional `tenant_id` predicate); Isolated tier = dedicated cluster/DB/bucket + per-tenant DEK; the `VectorIndex` port takes a `tenant` on every call (cross-tenant query unrepresentable). Residual: correct namespace provisioning per tenant. |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | Gateway budgets, model tiering, tenant cost model, storage tiers |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | Connector contract + conformance test suite; versioned connectors |
| R7 | **Vendor lock-in** at model or vector layer | Medium | ✅ *Design mitigated (Cycle 5, [Storage §3.4](storage/00-storage-architecture.md)):* the **`VectorIndex` port** confines each engine to one adapter; a tenant migration is a re-index through the port, not a pipeline rewrite (the vector-layer analogue of the Model Gateway). Models already covered by [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md). |
| R8 | **Ingestion backlog** starves freshness | Medium | Queue backpressure, autoscaling workers, prioritization by domain |

---

## 5. Documentation gaps (folders still empty / thin)

- ✅ `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding, verifier). **Seeded (Cycle 4).**
- ✅ `permissions/` — canonical ACL model + per-source mapping. **Seeded (Cycle 3).**
- ✅ `storage/` — five-store data plane, pgvector-default vector layer + `VectorIndex` port, tenancy definition, isolation tiers, encryption/BYOK, coherence, migrations, erasure. **Seeded (Cycle 5).** Resolved open Q#1 (final) + Q#5 (final); mitigated R4/R5/R7 by design.
- `metadata/` — catalog, lineage, classification schema. **Empty.** (Storage holds these; Metadata specifies the schema.)
- `workers/` — ingestion/embedding job orchestration, queue design. **Empty. Highest value now.** Hard inputs from Cycle 5: the transactional-outbox relay (§7 coherence), re-embed/re-sync jobs from the parsed object artifact, backpressure (R8).
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

### ✅ Cycle 4 (DONE — see §1): **RAG pipeline deep dive**
Wrote `rag/00-retrieval-pipeline.md` + [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md).
Structure-aware chunking, universal embedding space, hybrid search consuming the permission
filter, reranking, grounding/citation, verifier contract. Decided open question #4; mitigated
R2 by design; provisional answer to #1.

### ✅ Cycle 5 (DONE — see §1): **Storage & tenancy deep dive**
Wrote `storage/00-storage-architecture.md` + [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md).
Five-store data plane, pgvector-default vector layer behind a filter-only `VectorIndex` port,
tenant = customer org, isolation tiers, encryption/BYOK, ACL-denormalization coherence,
re-embed migrations, erasure. Resolved open questions 1 (final) and 5 (final); mitigated
R4/R5/R7 by design.

### ▶ Cycle 6 (do next): **Ingestion workers & connectors**
Write `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md`:
queue design, worker scaling, connector contract, change detection, freshness SLA
(open question 7), backpressure (R8). **Consumes Cycle 3:** the connector contract must
include `map_acl` + `list_principal_changes` + the permission-conformance suite as gates.
**Consumes Cycle 5:** implement the **transactional-outbox relay** that keeps the
denormalized chunk-ACL coherent at the dedicated-engine tier ([Storage §7](storage/00-storage-architecture.md)),
and the **re-embed/re-sync jobs** that read the parsed artifact from the object store
(no source re-hit, [Storage §8](storage/00-storage-architecture.md)). *Why next:* Storage
has now fixed the write-side contract (versioned upsert, coherence bound, migration shape);
Workers is the last piece before the ingestion plane is fully specified and unblocks
Deployment topology.

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
