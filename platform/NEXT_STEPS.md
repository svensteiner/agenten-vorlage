# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 10 (Deployment — topology, environments, CI/CD & DR/BCP)
- **Last updated:** 2026-07-06
- **Documentation root:** `platform/` — the single source of truth.
- **Gesamtfortschritt:** **≈ 82 %** (Ende Zyklus 10) — siehe §0.1. **Nach jeder Session melden.**

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
| Metadata / Katalog / Lineage (Z8) | 6 % | 90 % | 5.4 |
| Governance / Audit / Kosten (Z7) | 8 % | 85 % | 6.8 |
| API-Surface & Verträge (Z9) | 5 % | 90 % | 4.5 |
| Deployment / Topologie / DR (Z10) | 7 % | 90 % | 6.3 |
| Domänen-Pack-Specs (Finance/HR/Legal …) | 6 % | 5 % | 0.3 |
| Code-Reconciliation (`core/`-Umsetzung) | 4 % | 30 % | 1.2 |
| **Summe** | **100 %** | — | **≈ 82 %** |

**Verlauf:** Z1 ≈ 18 % · Z2/2b ≈ 24 % · Z3 ≈ 33 % · Z4 ≈ 40 % · Z5 ≈ 49 % · Z6 ≈ 58 % · Z7 ≈ 65 % · Z8 ≈ 71 % · Z9 ≈ 76 % · **Z10 ≈ 82 %**.

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

### Cycle 10 (2026-07-06) — Deployment: topology, environments, CI/CD & DR/BCP
- Wrote **[deployment/00-deployment-topology.md](deployment/00-deployment-topology.md)** — the
  **physical projection** of the whole platform and the **last un-seeded surface**. Introduces
  **no new logical component and no new guarantee**; it makes the existing ones affordable,
  operable, and survivable, and is the single place the **empirical sizing/tuning numbers** queued
  by Cycles 5–9 land. Collected those obligations as **D1–D8**, each tracing to its upstream source.
- **Physical projection:** the [three planes](architecture/01-platform-overview.md) map onto three
  substrates by dominant scaling axis — **edge+query** (stateless, latency-SLO autoscale),
  **ingestion** (stateless workers, scaled on **queue lag** not CPU), **data** (the only stateful
  substrate, hence the only backup/DR owner). Fail independently, blast radius stays separate.
- **Reference topology per tier (D1):** **Shared** (dense multi-tenant pool + two-control isolation)
  vs. **Isolated** (dedicated pool/cluster + per-tenant DEK/BYOK, quarantine hatch), mirroring the
  [Storage isolation tiers](storage/00-storage-architecture.md) one-to-one. **Graduation** =
  blue/green re-index through the `VectorIndex` port (no source re-hit) + a `tenant→placement`
  route flip — a data migration, not a redesign.
- **CI/CD as a safety gate (D7):** the [permission-conformance suite](permissions/00-authorization-model.md)
  is the **un-overridable release veto** (any over-permissive `map_acl` → hard fail, ships in
  quarantine never open); the [eval-before-promotion](governance/00-governance-and-audit.md) battery
  gates model changes; progressive delivery (staging → canary → prod) with the connector canary live;
  policy/allowlist/topology **as code**. **Real tenant data never leaves prod** — staging is
  synthetic but **ACL-shaped** so the gate stays meaningful.
- **SLA-capacity sizing (D2/D3):** **P0 revocation capacity is reserved, never autoscaled** (reacting
  to a revocation backlog is already a breach); P1/P2 autoscale on queue lag; relay-poll cadence set
  **below the SLA budget** — the freshness SLA is really an SLA on cache-TTL+invalidation, which
  query-time principal precedence backstops. Broker: managed queue + Postgres outbox (Shared),
  partitioned log (Isolated). **Safety is provisioned, bulk is elastic.**
- **Cost/residency (D4):** prices + envelope sizes live in a **versioned manifest** promoted through
  the pipeline (a price change is a reviewable commit into the unchanged degradation ladder); the
  safety invariant is inherited verbatim (no envelope/scale-down relaxes a permission). **Region is a
  routing fact** (`tenant→placement`), never a contract change; **data never crosses its residency class.**
- **Metadata ops (D5):** catalog partitioned by `tenant_id`; cold-lineage archival keeps tombstone/
  erasure walkability; a scheduled **lineage-integrity-check** asserts the [Metadata §7](metadata/00-catalog-and-lineage.md)
  invariants (no orphan / version monotonicity / label⊆registry / **no cross-tenant edge, R4**),
  violation → governance incident + write-quarantine.
- **DR/BCP (D8) → [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md):**
  **active-passive per residency region** (no active-active writes → **never** a window where two
  regions disagree on a revocation); **ACL-first, fail-closed recovery** (SoT→object→vector-rebuild→
  cache; permissions recover before content is queryable); **vectors rebuilt, not backed up**
  (a restored snapshot could disagree with recovered ACLs; the object-artifact rebuild is
  consistency-safe); tiered RPO/RTO (Shared ≤15 min/≤4 h, Isolated ≤5 min/≤1 h). The failover safety
  rule reuses query-time principal precedence — a failover cannot resurrect a revoked grant.
- Recorded **[ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md)**.
- Updated indexes: ADR index, `deployment/README.md` (stub → real), `platform/README.md` domain map
  (deployment → **Seeded**).
- **Directly strengthens (no new risk owned):** **closes the residual/"empirical" half of R3, R5, R8**
  (SLA-capacity sizing, prices/envelopes, autoscaling tuning now have a home) and **operationalizes R4**
  (partition pruning + the scheduled cross-tenant-edge integrity check). **All eight core platform
  surfaces are now Seeded — §5 is fully closed.**
- ⏳ **Handed to later cycles:** per-domain **pack specs** (Finance/HR/Legal — proves the "new domain =
  deployment of data+policy, not a topology change" bet end to end); open Q#3 (model-hosting posture per
  tier) feeds the concrete instance/model manifest; open Q#6 (agent framework) and the `core/`
  reconciliation remain the engineering track.

### Cycle 9 (2026-07-06) — API: external surface, contracts & versioning
- Wrote **[api/00-api-surface.md](api/00-api-surface.md)** — the platform's **outward
  contract** and the **last major un-seeded surface**. It is a *contract, not a new component*:
  the outward face of the [API Gateway](architecture/01-platform-overview.md) (Plane 1) and the
  [Governance policy store](governance/00-governance-and-audit.md). Discharges the client-facing
  needs three cycles queued (Governance → budgets/DSAR/audit-export; Metadata → catalog/lineage/
  DSAR-status; RAG+Permissions → the query endpoint that carries the subject token).
- **Five resource groups:** Query & Answer · Catalog & Lineage · Governance & Admin · Privacy &
  Audit (DSAR/erasure/export) · Ingestion ops, plus a shared async **Jobs** surface. Aligned to
  caller + owning plane/policy.
- **Six design tenets** = the outward projection of the platform principles: identity in the token
  not the URL/body; fail-closed at the edge; one envelope; heavy work is a job; idempotent writes;
  versioned & deprecable.
- **Query/answer contract:** sync `POST /v1/answers` + streaming `/v1/answers:stream`, **one
  verifier gate for both** (streamed `final` event emitted only after the verifier passes — streaming
  is never a grounding bypass). "No permitted data" is a **`200` success**
  (`grounding:"no_accessible_information"`), never an error — so absence of access can't leak as (or
  be faked as) an error. Citations expose the canonical `resource_id`+`source_item_version` from
  [Metadata §3](metadata/00-catalog-and-lineage.md).
- **Token → subject at the edge:** IdP bearer token → `{tenant, subject, effective principals,
  delegation}`; tenancy **derived from the token, never a URL segment** (impersonation
  unrepresentable). OBO via **token exchange** (actor + subject; retrieval runs under the subject).
  A **client-credentials** token has no end-user principals → a service account **structurally cannot**
  read user-restricted knowledge — kills the "index-everything under a service account" anti-pattern
  at the API layer.
- **One response envelope** `{ok,data,error,meta}` with **typed error enums**, leak-free messages,
  and `meta.request_id` == the audit correlation id; hidden resources return `not_found`, never a
  message confirming existence.
- **Admin API can only tighten:** thin self-auditing CRUD over the Governance policy store; a write
  that would loosen a platform floor (widen a label, disable the ACL filter, throttle a P0 revocation,
  raise a budget above ceiling, pin an un-evaluated model) → `422 policy_blocked`. Successor to the
  local [ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md) `control_panel.py`.
- **Privacy group** (DSAR/erasure/audit-export) = **jobs**; erasure status returns the
  [Metadata lineage-tombstone](metadata/00-catalog-and-lineage.md) evidence — completeness is
  **proven by a traversal**, `legal_hold` blocks with `422`. **Filter parity** on catalog/lineage
  reads (identical predicate to retrieval; no unfiltered "list mode" side-channel).
- **Versioning:** URL-major (`/v1/`), additive-by-default (clients must ignore unknown fields),
  breaking → new major + `Deprecation`/`Sunset` + per-version usage reporting. **A new domain pack
  is not a version event.**
- Recorded **[ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md)**.
- Updated indexes: ADR index, `api/README.md` (stub → real), `platform/README.md` domain map
  (api → **Seeded**).
- **Directly strengthens (no new risk owned):** the A1/A6 obligations — permission-faithful retrieval
  ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)) enforced once at audited
  choke points instead of re-argued per endpoint; budget/rate limits couple to
  [Governance §7.3](governance/00-governance-and-audit.md) and **throttle cost, never safety** (R5).
- ⏳ **Handed to downstream cycles:** concrete gateway/broker/topology + per-region residency routing +
  rate-limit sizing + streaming transport ops → [Deployment](deployment/); each domain pack's optional
  `pack` hint + any pack-specific endpoints ride the additive rule (no contract change).

### Cycle 8 (2026-07-06) — Metadata: catalog, lineage & classification schema
- Wrote **[metadata/00-catalog-and-lineage.md](metadata/00-catalog-and-lineage.md)** — the
  **connective-tissue schema**. Five prior cycles referred to the same nouns (`resource_id`,
  `source_item_version`, `labels`, `embed_model`, "lineage tombstone", "catalog row") but **no
  document owned their definitions**; this cycle canonicalizes them so the four consumers
  (Storage holds, Workers emits, RAG/citation + Governance/evidence read) share **one contract
  instead of four component-local shapes**. Adds **no new store** (metadata lives in the
  relational source of truth, [Storage §4.2](storage/00-storage-architecture.md)) and **no
  hot-path component** (lineage is a byproduct of the persist write already done).
- **Canonical catalog:** four-level hierarchy **Document → Item → Chunk → Version**, keyed on
  `resource_id` + `source_item_version`. The **Item** level is defined as the finest source unit
  carrying *one* ACL — that is where [RAG §2.2](rag/00-retrieval-pipeline.md)'s mixed-ACL
  invariant lives (per-message emails, per-sheet workbooks). `resource_id` = the platform-wide
  join key; `source_item_version` = the coherence key; `superseded_by` = version history
  (Principle 8). A denormalized chunk projection (labels, ACL arrays, `embed_model`,
  `section_path`) keeps retrieval + citation single-store reads.
- **Closed classification vocabulary** (M3): `sensitivity ∈ {public,internal,confidential,
  restricted:<class>}`, `pii ∈ {true,false}+pii_class:<type>`, `legal_hold ∈ {true,false}+
  matter:<id>`. **An unregistered label is a write-boundary schema violation → DLQ, never
  stored** — this is what makes the [Governance §4](governance/00-governance-and-audit.md) matrix
  *total* (every label a chunk can carry has a defined action). Unlabeled defaults to `internal`,
  never `public` (fail-closed classification).
- **Explicit lineage graph** (M2) `source→raw→parsed→chunk→vector`, emitted at persist carrying
  the ingestion `job_trace_id`, **traversable both directions**: forward = erasure-completeness +
  re-embed; backward = audit/citation evidence. The `re_embedded_from` edge is itself the proof a
  re-embed was source-independent ([Workers §6](workers/00-ingestion-architecture.md)).
- **Content-free erasure/legal-hold tombstone** (M4) — the concrete shape of
  [Storage §9](storage/00-storage-architecture.md)'s "lineage tombstone" + the
  [Governance §5](governance/00-governance-and-audit.md) legal balance (`legal_hold > erasure >
  retention`; audit retained, content erased). "No silent orphans" becomes a **provable graph
  walk**, not an assertion.
- **Metadata as the audit-evidence base** (M5): every Governance promise resolves to a catalog
  column or a lineage traversal addressable by the `resource_id`/`job_trace_id` an audit event
  already carries — [Governance §6.3](governance/00-governance-and-audit.md)'s "can the log prove
  it?" is answered by a query, not a reconstruction. Hence metadata lives transactionally with the
  ACL of record, not in a lagging analytics copy.
- **Anti-drift discipline** (M6): a `schema_version` + write-boundary validation (violation → DLQ,
  same mechanism as a malformed `map_acl`) + additive-with-migration evolution — a shared change
  can't become a silent cross-component break. Integrity invariants: every chunk has a live
  lineage path or a tombstone; version monotonicity; label ⊆ registry; no cross-tenant edge (R4).
- Recorded **[ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)**.
- Updated indexes: ADR index, `metadata/README.md` (stub → real), `platform/README.md` domain map
  (metadata → **Seeded**).
- **Directly strengthens (no new risk owned):** R1 (quarantine now auditable via `acl_confidence`
  in the catalog + orphan check), R3 (re-sync is addressable because identifiers are canonical),
  and makes Governance's erasure/retention/label promises **provable** (the evidence is a
  traversal). Closes the **last un-seeded cross-cutting store concern** (§5).
- ⏳ **Handed to downstream cycles:** the catalog-browse / lineage / DSAR-status client surface →
  [API](api/); catalog partitioning + cold-lineage archival + the lineage-integrity-check schedule
  → [Deployment](deployment/); each domain pack registers its `restricted:<class>` /
  `pii_class:<type>` values in the classification registry ([Metadata §4.1](metadata/00-catalog-and-lineage.md)).

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
| ADR-0013 | Canonical metadata: four-level catalog (Doc→Item→Chunk→Version) + explicit bidirectional lineage graph + closed classification vocabulary + content-free erasure tombstone; held in the relational SoT, no new store; versioned + write-boundary-validated | Four consumers share one contract not four shapes; the Governance label matrix becomes total; erasure-completeness & audit-evidence become provable queries; new domain/artifact type = additive registration, not a schema redesign |
| ADR-0014 | API contract: token-bound identity (tenancy never in URL) + OBO via token exchange; dual sync/streaming answer under one verifier gate; "no access" is a 200; one typed-error envelope; heavy work = jobs; admin-can-only-tighten; filter-parity reads; URL-major additive versioning | Permission-faithful retrieval enforced once at audited choke points not re-argued per endpoint; impersonation/cross-tenant unrepresentable on the wire; budgets throttle cost not safety; new pack = additive, not a version event |
| ADR-0015 | Deployment DR: active-passive per residency region (no active-active writes); ACL-first fail-closed recovery (SoT→object→vector-rebuild→cache); vectors rebuilt not backed up; tiered RPO/RTO; reserved (not autoscaled) P0 capacity | No cross-region window disagrees on a revocation; the platform recovers fail-closed (permissions before content); a restore can't resurrect a vector snapshot that disagrees with recovered ACLs; the revocation SLA is provisioned in advance |

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
- ✅ `metadata/` — canonical four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification/label vocabulary, content-free erasure tombstone, metadata-as-audit-evidence, schema versioning/validation. **Seeded (Cycle 8).** Closed the last un-seeded cross-cutting store concern; made Governance's label matrix total and its erasure/audit promises provable.
- ✅ `api/` — external surface: five resource groups, token-bound identity + OBO, query/answer + streaming contract (one verifier gate), one typed-error envelope, async-job pattern, admin-can-only-tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major versioning. **Seeded (Cycle 9).** Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued; enforced permission-faithfulness once at the edge.
- ✅ `deployment/` — physical projection: per-tier reference topology + graduation, environments,
  safety-gated CI/CD (conformance suite as un-overridable release veto), reserved-P0 SLA-capacity
  sizing, cost-envelope/residency routing, catalog partitioning + cold-lineage archival + integrity
  checks, gateway/rate-limit/streaming ops, and **ACL-first active-passive DR/BCP** with per-store
  backup/restore. **Seeded (Cycle 10).** Discharged the sizing/tuning inputs Cycles 5–9 queued;
  closed the residual/empirical half of R3/R5/R8 and operationalized R4.

**→ All eight core platform surfaces (architecture, security, permissions, rag, storage, workers,
metadata, api, governance, deployment) are now Seeded. §5 is fully closed.** The remaining work is
domain-pack specifications, code reconciliation, and the two open engineering questions (Q#3, Q#6).
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

### ✅ Cycle 8 (DONE — see §1): **Metadata — catalog, lineage & classification schema**
Wrote `metadata/00-catalog-and-lineage.md` + [ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md).
Four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification
vocabulary (makes the Governance matrix total), content-free erasure tombstone, metadata-as-audit-
evidence, schema versioning/validation. Held in the relational SoT — no new store, no hot-path
component. Closed the last un-seeded cross-cutting store concern; strengthened R1/R3 and made
Governance's erasure/retention/label promises provable. A cross-component schema decision *did*
emerge → ADR-0013.

### ✅ Cycle 9 (DONE — see §1): **API — external surface, contracts & versioning**
Wrote `api/00-api-surface.md` + [ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md).
Five resource groups, token-bound identity + OBO (tenancy never in the URL), dual sync/streaming
query contract under one verifier gate, one typed-error envelope, async-job pattern, admin-can-only-
tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major additive
versioning. Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued;
enforced permission-faithful retrieval once at the edge (a contract-shape decision was cross-component
→ ADR-0014).

### ✅ Cycle 10 (DONE — see §1): **Deployment — topology, environments, CI/CD, DR/BCP**
Wrote `deployment/00-deployment-topology.md` + [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md).
Physical projection of the three planes; per-tier topology + graduation; safety-gated CI/CD
(conformance suite as release veto); reserved-P0 SLA-capacity sizing; cost-envelope/residency
routing; catalog partitioning + cold-lineage archival + integrity checks; gateway/streaming ops;
**ACL-first active-passive DR** with per-store backup/restore (a cross-component DR decision → ADR-0015).
Discharged the sizing/tuning inputs Cycles 5–9 queued; **closed §5 — all core surfaces Seeded.**

### ▶ Cycle 11 (do next): **Domain Pack #1 — Finance (the proof of the founding bet)**
Write `packs/finance/00-finance-pack.md` (new `packs/` folder). *Why next:* every horizontal
surface is now Seeded, so the highest-leverage remaining move is to **prove "new domain = pack, not
redesign" end to end** against the stable core — the platform's founding thesis, so far only
asserted. Finance first because it exercises the hardest cross-cutting features already built:
row/record-level ACLs (SAP), `restricted:<class>`/`pii_class` labels + `legal_hold`
([Metadata §4](metadata/00-catalog-and-lineage.md)), the SOX/audit compliance-map row
([Governance §9](governance/00-governance-and-audit.md)), and per-content-type parsers
(SAP table serialization, [RAG open sub-Q](rag/00-retrieval-pipeline.md)). The pack spec should be
a **template**: (1) the sources + each source's `map_acl` fidelity target + conformance fixtures;
(2) the classification-registry values the pack registers (`restricted:<class>`, `pii_class:<type>`);
(3) the label→action deltas it *tightens* (never loosens); (4) its compliance-map row (SOX/GDPR
cells, evidence-backed); (5) its retrieval/answer eval set (grounding, refusal, pack task accuracy);
(6) the *optional* additive API `pack` hint ([ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md)) —
**demonstrating zero changes to any horizontal doc.** If the pack forces a horizontal change, that
change is itself the finding (the bet is weaker than claimed) and warrants an ADR. Establish the
**reusable pack-spec skeleton** here so HR/Legal/Audit/KM/SAP/SharePoint packs are fill-in-the-blank.

### Later (backlog)
- Further **pack specifications** (HR, Legal, Audit, Knowledge Mgmt, SAP, SharePoint, Email, …)
  reusing the Cycle-11 skeleton; each **inherits** a compliance-map row
  ([Governance §9](governance/00-governance-and-audit.md)).
- **Cycle 2c engineering track** (still open) — wire `WorkerRegistry`/`HandoffRouter` into the
  runtime, finish the test port + coverage gate, deeper governance hardening (see §6 Cycle 2c).
- Reconcile `platform/` architecture with the existing `core/` code (ADR-0002 implementation path).
- Resolve open **Q#3** (model hosting — in-boundary OSS vs. contractually-private managed, per tier)
  → feed the approved-model registry ([Governance §8](governance/00-governance-and-audit.md)) + the
  Deployment instance/model manifest ([Deployment §7](deployment/00-deployment-topology.md)); may warrant its own ADR.
- Resolve open **Q#6** (agent framework — extend `core/` planner/verifier vs. adopt a framework).

---

## 7. Consistency checklist (run before ending each cycle)

- [ ] New docs answer Why / How / Trade-offs / Alternatives / Future scalability.
- [ ] New cross-component decisions captured as an ADR and linked.
- [ ] No duplicated content; extended existing docs where possible.
- [ ] `platform/README.md` domain-map statuses updated.
- [ ] This file's §1, §3, §4, §6 updated.
