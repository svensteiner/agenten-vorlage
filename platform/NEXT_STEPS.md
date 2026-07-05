# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 7 (Governance, audit & cost)
- **Last updated:** 2026-07-06
- **Documentation root:** `platform/` — the single source of truth.
- **Gesamtfortschritt:** **≈ 65 %** (Ende Zyklus 7) — siehe §0.1. **Nach jeder Session melden.**

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
| Workers & Connectors (Z6) | 10 % | 90 % | 9.0 |
| Metadata / Katalog / Lineage | 6 % | 0 % | 0.0 |
| Governance / Audit / Kosten (Z7) | 8 % | 85 % | 6.8 |
| API-Surface & Verträge | 5 % | 0 % | 0.0 |
| Deployment / Topologie / DR | 7 % | 0 % | 0.0 |
| Domänen-Pack-Specs (Finance/HR/Legal …) | 6 % | 5 % | 0.3 |
| Code-Reconciliation (`core/`-Umsetzung) | 4 % | 30 % | 1.2 |
| **Summe** | **100 %** | — | **≈ 65 %** |

**Verlauf:** Z1 ≈ 18 % · Z2/2b ≈ 24 % · Z3 ≈ 33 % · Z4 ≈ 40 % · Z5 ≈ 49 % · Z6 ≈ 58 % · **Z7 ≈ 65 %**.

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

### Cycle 7 (2026-07-06) — Governance, audit & cost
- Wrote **[governance/00-governance-and-audit.md](governance/00-governance-and-audit.md)** —
  the **policy plane**. Governance owns *policy, not mechanism*: it adds **no hot-path runtime
  component**, only a versioned (itself-audited) policy store + a reporting/metering surface over
  the existing [audit store](storage/00-storage-architecture.md); every enforcement point already
  exists (Model Gateway, retrieval filter/redactor, worker scheduler). Closes the three
  ratifications the upstream cycles queued (G1–G3) plus audit usage (G4), cost/R5 (G5), model
  governance (G6), and compliance mapping (G7).
- **Ratified freshness SLA (closes open Q#7):** contractual per-tier numbers — principal change
  **≤5 min** (Standard) / **≤2 min** (Isolated); restrictive resource-ACL **≤15 / ≤5 min**;
  widening ≤60 / ≤15 min; public best-effort. A breach = alarm **+** recorded governance incident
  (contractual reporting event for Isolated). Made affordable by the fact that query-time principal
  precedence ([Storage §7](storage/00-storage-architecture.md)) already closes offboarding
  independent of the re-tag — the tight number is really an SLA on cache-TTL+invalidation.
- **Ratified label→action policy:** platform-owned default matrix (`public`/`internal`/
  `confidential`/`pii`/`legal_hold`/`restricted:<class>`) mapping each label to retrieval / prompt /
  routing / egress, composing **most-restrictive-wins**; tenants may **tighten, never loosen**;
  labels can only subtract capability ([Permissions §7](permissions/00-authorization-model.md)
  invariant preserved).
- **Ratified retention / erasure / legal-hold:** per-store schedule (audit ≥1 yr hot / ≥7 yr cold;
  raw object 90 d→archival; DLQ 30 d; cache 5–15 min); right-to-erasure as an SLA-bound DSAR
  workflow using [Storage §9](storage/00-storage-architecture.md) propagation, **erasure recorded as
  an audit event**, **audit trail itself exempt**; precedence **legal-hold > erasure > retention**.
- **Cost model & R5 (design-mitigated):** every cost-bearing event carries `tenant_id`; per-tenant→
  pack→workload attribution; budget envelopes degrade **capability before safety** (80–100 % →
  cheaper tier + defer P2 + tighten cache; 100 % → block new P2, queue P1, alert). **A budget cap
  can never relax a permission, skip the ACL filter, or throttle a P0 revocation** — fail-closed on
  spend.
- **Audit-as-evidence:** *a promise the audit log can't evidence is not a governable promise* —
  the SLA, labels, erasure, and budgets are each proven by their event type; audit read access is
  role-gated + itself audited; hash-chain verified on schedule.
- **Model governance:** approved-model registry + **eval-before-promotion** gate (grounding, refusal
  calibration, jailbreak resistance, pack task accuracy) + per-tenant version pinning/rollback + model
  version in every retrieval audit event. **Compliance map** binds existing controls to GDPR / SOX /
  ISO 27001-SOC 2 / sector per domain, each cell evidence-backed.
- Recorded **[ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)**.
- Updated indexes: ADR index, `governance/README.md` (stub → real), `platform/README.md` domain
  map (governance → **Seeded**).
- **Directly de-risks:** R5 (cost → metering + attribution + budget envelopes + safety-preserving
  degradation ladder); **closes the SLA-number half of R3** and the label-policy dependency.
- **Closed open question #7** (freshness SLA — ratified) — see §3.
- ⏳ **Handed to downstream cycles:** actual prices / budget-envelope sizes / per-tier SLA capacity
  sizing / data residency → [Deployment](deployment/); classification schema the label policy
  consumes → [Metadata](metadata/); the client-facing surface for budgets / DSAR / audit export →
  [API](api/). Open Q#3 (model hosting) feeds the approved-model registry when decided.

### Cycle 6 (2026-07-05) — Ingestion workers & connectors
- Wrote **[workers/00-ingestion-architecture.md](workers/00-ingestion-architecture.md)** — the
  write-plane engine. Turns the Cycle 3–5 write-side obligations (W1 idempotent version-keyed
  writes, W2 ACL-denorm coherence, W3 change-driven re-sync, W4 source-independent re-embed,
  W5 mixed-ACL invariant at write time, W6 least-privilege per-tenant execution, W7 backpressure)
  into a selected shape: a **staged DAG** (fetch → parse → map_acl → chunk → embed → persist),
  each stage reading/writing a durable artifact so failures resume without re-hitting the source.
- Wrote **[workers/01-connector-framework.md](workers/01-connector-framework.md)** — the
  source-specific boundary: a **six-method `Connector` port** (`list_items`, `fetch`, `map_acl`,
  `subscribe_changes`, `list_principal_changes`, `capabilities`); per-source `map_acl` duties
  (R1 implementation); versioning + fault isolation (R6); and the **permission-conformance suite
  as the production gate** ([Permissions §11](permissions/00-authorization-model.md)) running in
  CI **and** a production canary that **auto-quarantines** a source on drift.
- **Key decisions:** (a) **at-least-once delivery + idempotent version-keyed writes** — refuse
  exactly-once, make replays/outbox-double-delivery harmless; (b) **strict priority classes with
  fairness guards** (P0 revocation/security ≤5/≤15 min · P1 content delta · P2 backfill/re-embed/
  reconciliation) so a backfill can **never** starve a revocation (**R8 core**); (c) the
  [Storage §7](storage/00-storage-architecture.md) coherence relay = **transactional outbox** at
  the dedicated-engine tier (pgvector tier stays same-transaction); (d) re-embed/re-chunk =
  **blue/green P2 jobs reading the parsed object artifact, never the source**
  ([Storage §8](storage/00-storage-architecture.md)); (e) **least privilege split** — the
  read-source credential and the write-ACL credential live in different worker pools; (f) under
  load the plane **drops recall before it drops a revocation** (fail-closed on the write path).
- Recorded **[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md)**.
- Updated indexes: ADR index, `workers/README.md` (stub → real), `platform/README.md` domain
  map (workers → **Seeded**).
- **Directly de-risks:** R8 (backlog → freshness: priority + fairness + lag alarms, made
  *observable*), R6 (connector fragility: independent versioning + schema-validated boundary +
  conformance canary), R3 write-half (change-driven content/ACL re-sync + P0 principal re-sync).
- **Strengthened open question #7** (freshness SLA): the priority-class model now *implements*
  the proposed ≤5/≤15 min targets and the relay-lag/queue-lag alarms that enforce them — still
  **pending [Governance](governance/) ratification** of the actual numbers.
- ⏳ **Handed to downstream cycles:** freshness-SLA ratification (Q#7) + per-tenant ingest cost +
  DLQ/retention policy → [Governance](governance/) (Cycle 7); concrete broker choice per tier +
  worker autoscaling topology + secret provisioning → [Deployment](deployment/); lineage schema
  emitted by the persist stage → [Metadata](metadata/).

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
| ADR-0011 | Ingestion = staged-DAG workers; at-least-once + idempotent version-keyed writes; priority classes (P0 revoke > P1 delta > P2 backfill); outbox coherence relay; conformance-gated connector contract | Resumable/scalable/contained ingestion; backlog can't starve a revocation (R8); new source = connector + suite, not redesign; write path fail-closed |
| ADR-0012 | Governance = policy plane (no hot-path component); ratified per-tier freshness SLA + label→action matrix + retention/erasure; audit-as-evidence; per-tenant budgets that degrade capability-before-safety; eval-gated model registry; per-domain compliance map | Promises become contractual & provable; cost control (R5) can never regress into a safety leak; new domain inherits a control map, not a redesign |

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
   **Cycle 7 note:** Governance built the **approved-model registry + eval-before-promotion
   gate** ([Governance §8](governance/00-governance-and-audit.md)) that *any* hosting choice
   flows through; the label→trust routing matrix ([Governance §4](governance/00-governance-and-audit.md))
   already expresses the compliance side. The still-open decision is the concrete
   *in-boundary-vs-managed-private posture per tenant tier* — feed it into the registry when
   decided (may warrant its own ADR; [ADR-0012 revisit-when](architecture/adr/ADR-0012-governance-audit-and-cost.md)).
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
7. ✅ **DECIDED (Cycle 7, [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)).**
   ~~Freshness SLA~~ — **ratified as contractual per-tier numbers**
   ([Governance §3](governance/00-governance-and-audit.md)): principal change ≤5 min
   (Standard) / ≤2 min (Isolated); restrictive resource-ACL ≤15 / ≤5 min; widening ≤60 / ≤15 min;
   public best-effort. A breach is an alarm **and** a recorded governance incident (contractual
   reporting event for Isolated tenants). Workers already *implements and measures* these
   ([workers §4.2, §10](workers/00-ingestion-architecture.md)); Governance fixed the promise +
   consequences. Remaining sub-question deferred to [Deployment](deployment/): the
   reserved-P0-capacity / relay-poll-frequency **sizing** that meets each ratified number at cost
   (a tuning knob, not a redesign).

---

## 4. Technical risks (tracked)

| # | Risk | Severity | Mitigation direction |
|---|------|----------|----------------------|
| R1 | **Permission-model mismatch** — source ACLs can't be faithfully normalized → leak | **Critical** | ✅ *Design mitigated (Cycle 3):* canonical model + `acl_confidence` gate (approximate→deny) + per-connector conformance suite + quarantine tier. Residual: correct **implementation** of each connector's `map_acl`. |
| R2 | **Prompt injection via retrieved content** | **Critical** | ✅ *Design mitigated (Cycle 4, [RAG §6.1, §7](rag/00-retrieval-pipeline.md)):* retrieved text delivered inside a data boundary (not instructions), retrieved content cannot alter tool/routing/citation policy, verifier enforces grounding + guardrails as the backstop. Residual: implementation hardening of the verifier + red-team corpus. |
| R3 | **Stale permissions** — user loses access but index still serves it | High | ✅ *Design mitigated (Cycles 3+6):* query-time principal precedence ([Permissions §8](permissions/00-authorization-model.md)) closes offboarding regardless of chunk lag; the write half — **change-driven content/ACL re-sync at P0/P1** + the **outbox relay bounded by the freshness SLA** ([workers §5, §7](workers/00-ingestion-architecture.md)) — closes the resource-re-tag case; relay/queue lag is alarmed (§10). Residual: SLA number ratification (Q#7). |
| R4 | **Cross-tenant leakage** via a filtering bug | High | ✅ *Design mitigated (Cycle 5, [Storage §5.2](storage/00-storage-architecture.md)):* Shared tier uses **two independent controls** (per-tenant namespace/schema **and** an unconditional `tenant_id` predicate); Isolated tier = dedicated cluster/DB/bucket + per-tenant DEK; the `VectorIndex` port takes a `tenant` on every call (cross-tenant query unrepresentable). Residual: correct namespace provisioning per tenant. |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | ✅ *Design mitigated (Cycle 7, [Governance §7](governance/00-governance-and-audit.md)):* per-tenant **metering + attribution** (every cost event carries `tenant_id`, assembled tenant→pack→workload), **budget envelopes**, and a **graceful-degradation ladder** that degrades *capability before safety* (cheaper model tier + defer P2 + tighten cache; then block new P2, queue P1) — **a budget cap can never relax a permission, skip the ACL filter, or throttle a P0 revocation**. Upstream levers (model tiering [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md), quantization/tiering [Storage §10](storage/00-storage-architecture.md), embed batching [Workers §4.3](workers/00-ingestion-architecture.md)) now have an owner that pulls them. Residual: actual **prices + envelope sizes** per tier ([Deployment](deployment/), empirical). |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | ✅ *Design mitigated (Cycle 6, [connector §3, §5](workers/01-connector-framework.md)):* independently-versioned connectors + a **schema-validated** return boundary (malformed ACL → DLQ, never the store) + the **conformance suite as a production canary** that **auto-quarantines** a source on semantic drift. Residual: implementation of each connector's change-detection. |
| R7 | **Vendor lock-in** at model or vector layer | Medium | ✅ *Design mitigated (Cycle 5, [Storage §3.4](storage/00-storage-architecture.md)):* the **`VectorIndex` port** confines each engine to one adapter; a tenant migration is a re-index through the port, not a pipeline rewrite (the vector-layer analogue of the Model Gateway). Models already covered by [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md). |
| R8 | **Ingestion backlog** starves freshness | Medium | ✅ *Design mitigated (Cycle 6, [workers §4, §10](workers/00-ingestion-architecture.md)):* **strict priority classes** (P0 revoke > P1 delta > P2 backfill) with **fairness guards** so a backfill can't starve a revocation; bounded-lease backpressure; per-tenant weighted-fair scheduling; **queue-lag alarms** make a looming SLA breach loud, not silent. Residual: autoscaling tuning ([Deployment](deployment/)). |

---

## 5. Documentation gaps (folders still empty / thin)

- ✅ `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding, verifier). **Seeded (Cycle 4).**
- ✅ `permissions/` — canonical ACL model + per-source mapping. **Seeded (Cycle 3).**
- ✅ `storage/` — five-store data plane, pgvector-default vector layer + `VectorIndex` port, tenancy definition, isolation tiers, encryption/BYOK, coherence, migrations, erasure. **Seeded (Cycle 5).** Resolved open Q#1 (final) + Q#5 (final); mitigated R4/R5/R7 by design.
- ✅ `workers/` — staged-DAG ingestion, `IngestionTask` queue + idempotent version-keyed writes, priority classes (R8), outbox coherence relay, re-embed migrations, change-driven re-sync, DLQ, least-privilege posture, connector contract + conformance gate. **Seeded (Cycle 6).** Mitigated R8/R6/R3-write by design; strengthened Q#7.
- `metadata/` — catalog, lineage, classification schema. **Empty.** (Storage holds these; Workers emits lineage at persist; Metadata specifies the schema; Governance §4 consumes the classification schema.) **Highest doc value now.**
- `api/` — external API surface, contracts, versioning. **Empty.** (Governance handed it the budget / DSAR / audit-export surface.)
- `deployment/` — topology, environments, CI/CD, DR/BCP. **Empty. Now heavily loaded** — Cycles 5/6/7 have queued concrete sizing/tuning inputs (per-tier topology, graduation thresholds, broker choice, autoscaling, SLA-capacity sizing, prices/envelopes, region/residency).
- ✅ `governance/` — policy plane: ratified freshness SLA + label→action matrix + retention/erasure, audit usage (retention/access/evidence), per-tenant cost model & budgets (R5), model governance, compliance map. **Seeded (Cycle 7).** Closed open Q#7; mitigated R5 by design.

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

### ✅ Cycle 6 (DONE — see §1): **Ingestion workers & connectors**
Wrote `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md` +
[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).
Staged-DAG pipeline, idempotent version-keyed writes, priority classes + fairness (R8),
outbox coherence relay ([Storage §7](storage/00-storage-architecture.md)), re-embed
migrations, change-driven re-sync, DLQ, least-privilege posture, six-method connector
contract, conformance gate + canary. Mitigated R8/R6/R3-write by design; strengthened Q#7.

### ✅ Cycle 7 (DONE — see §1): **Governance, audit & cost**
Wrote `governance/00-governance-and-audit.md` + [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md).
Policy plane (no hot-path component): ratified freshness SLA per tier (closed Q#7), label→action
matrix, retention/erasure/legal-hold; audit-as-evidence (retention/access/hash-chain); per-tenant
cost model + budgets that degrade capability-before-safety (mitigated R5 by design); eval-gated
model registry; per-domain compliance map. Handed Deployment the prices/envelopes/SLA-capacity
sizing, Metadata the classification schema, and API the budget/DSAR/audit-export surface.

### ▶ Cycle 8 (do next): **Metadata — catalog, lineage & classification schema**
Write `metadata/00-catalog-and-lineage.md`. *Why next:* it is now the **last un-seeded
cross-cutting store concern** and three cycles feed directly into it — Storage *holds* catalog +
lineage + classification ([Storage §4.2](storage/00-storage-architecture.md)), Workers *emits*
lineage at the persist stage ([Workers §2, §9](workers/00-ingestion-architecture.md)), and
Governance's label→action policy *consumes* the classification schema
([Governance §4](governance/00-governance-and-audit.md)). Specify: the **catalog schema**
(document/item/chunk/version), the **lineage graph** (source→artifact→chunk→vector, + the erasure
tombstone [Storage §9](storage/00-storage-architecture.md)), the **classification/label schema**
(the vocabulary the ACL `labels` and the Governance matrix key off, [Permissions §2.2](permissions/00-authorization-model.md)),
and how catalog/lineage back **audit evidence** ([Governance §6.3](governance/00-governance-and-audit.md))
and **re-embed migrations** ([Workers §6](workers/00-ingestion-architecture.md)). No new ADR
expected unless a cross-component schema decision emerges.

### Later (backlog)
- `deployment/` — reference topology, environments, CI/CD, DR/BCP. **Now the most heavily-loaded
  backlog item:** per-tier storage topology + graduation thresholds ([Storage §3.3](storage/00-storage-architecture.md)),
  broker choice + worker autoscaling ([Workers §3.2, §13](workers/00-ingestion-architecture.md)),
  SLA-capacity sizing + prices/envelopes + region/residency ([Governance §3, §7](governance/00-governance-and-audit.md)).
- `api/` — external API contracts & versioning (incl. the budget / DSAR / audit-export surface
  Governance handed up).
- Per-domain **pack specifications** (Finance, HR, Legal, ...) once the core deep dives
  are stable — proving the "new domain = pack, not redesign" bet; each pack now **inherits** a
  compliance-map row ([Governance §9](governance/00-governance-and-audit.md)).
- Reconcile `platform/` architecture with the existing `core/` code
  (ADR-0002 implementation path).
- Resolve open Q#3 (model hosting) → feed the approved-model registry ([Governance §8](governance/00-governance-and-audit.md)).

---

## 7. Consistency checklist (run before ending each cycle)

- [ ] New docs answer Why / How / Trade-offs / Alternatives / Future scalability.
- [ ] New cross-component decisions captured as an ADR and linked.
- [ ] No duplicated content; extended existing docs where possible.
- [ ] `platform/README.md` domain-map statuses updated.
- [ ] This file's §1, §3, §4, §6 updated.
