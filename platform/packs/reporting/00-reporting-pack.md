# Domain Pack #10 — Reporting (dashboards, BI extracts & the *aggregate* over mixed-authorization rows)

> **The tenth and *last* pack — and the one that closes the domain-pack surface.** It is the most
> inheritance-heavy of all packs: a dashboard tile, a BI extract, a report row is a **derived artifact
> over source tables**, so it reuses [Document Intelligence's](../document-intelligence/00-document-intelligence-pack.md)
> *derived-artifact-inherits-source-ACL* rule **verbatim** and [SAP's](../sap/00-sap-pack.md) BW/BI +
> [Finance's](../finance/00-finance-pack.md) fidelity for its sources. It is chosen last on purpose:
> it introduces **exactly one concept eleven prior packs never stressed — the *aggregate*.** A report
> cell is rarely one source row; it is a **rollup** (a sum, a count, an average) over *many* rows the
> caller may only *partially* access. That raises the one question the
> [skeleton's falsifiability rule](../README.md#the-falsifiability-rule) exists to catch: *when a
> single displayed value is the aggregate of many rows with **heterogeneous ACLs**, whom may it be
> shown to — and can a total leak a row the caller could not read individually (the small-cell /
> differencing seam)? Does aggregation force a new predicate, a disclosure-control engine, or a
> loosened floor?* **It resolves additively. See §0 and the "Aggregation" analysis below — the
> defense is the *existing* filter-then-aggregate order (ADR-0004), not a new mechanism.**

- **Cycle:** 20 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — aggregation fits the existing contract; had the platform needed to *compute-and-serve* a total over rows the caller can't read, this pack would have raised a horizontal ADR for statistical disclosure control, which is the process working)
- **Regimes declared:** **inherits** the riding domain's regime (a Finance report inherits SOX; an HR headcount dashboard inherits Art. 9; an Audit KPI inherits PCAOB) — a report *presents* a domain, it *is* no domain; plus ISO 27001 / SOC 2 inherited
- **Isolation tier (default):** inherits the *most restrictive* contributing source Item's tier — a report is never placed more openly than the tightest row it aggregates ([Storage §5](../../storage/00-storage-architecture.md))

---

## Why Reporting tenth (and why it is the right final stress test)

Nine prior packs handled artifacts in a **one-to-one or many-to-one *content*** relationship with
their sources: an Item, a chunk, an OCR text layer, an extracted entity — each traces back to a source
span whose ACL it inherits. [Document Intelligence](../document-intelligence/00-document-intelligence-pack.md)
introduced the *derived* artifact and proved a derivation **inherits, never manufactures**
authorization (multi-source merge = intersection, never union). Reporting takes DocIntel's merge rule
and stresses its **sharpest corner**: the derived value is not a *concatenation* of source content
(an entity node listing spans) but an **arithmetic aggregate** (a sum/count/avg) that **destroys the
row boundary** — and an aggregate has a failure mode entity-merge did not:

- **Aggregation can *reconstruct* a value the caller may not read.** A department salary total over
  *one* employee **is** that employee's salary. A total over two rows, differenced against a total
  over one, leaks the second. This is the classic **statistical-disclosure / differencing** problem,
  and it is the first time any pack's derivation could leak **not by widening an ACL but by *arithmetic
  inference*** — a total that individually gates fine can still reveal a masked row. If the platform
  had to add k-anonymity / small-cell suppression / differential privacy to serve aggregates safely,
  that would be a new hot-path mechanism the bet forbids. **(Answer: it does not — because the platform
  never aggregates rows the caller can't already read. See "Aggregation" §0-analysis.)**
- **A report is drawn from *many* sources at once (a dashboard tile joins SAP BW + a Finance ledger +
  a SharePoint list).** So the "whose ACL does the derived value carry?" question is DocIntel's
  multi-source merge, but now the norm rather than the exception. **(Answer: the aggregate carries the
  **intersection** of its contributing rows' ACLs — most-restrictive-wins — exactly the DocIntel merge
  rule, reused verbatim.)**

If either forced a horizontal change, that would be the headline finding. **Neither did** — see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Reporting? | What Reporting did instead |
|--------------------|:-----------------------------:|------------------------|
| Permissions (canonical model, `map_acl`) | **None** | A **query-time** aggregate is computed **only over rows the caller's ACL already admits** — the [query-time filter](../../permissions/00-authorization-model.md#4-query-time-enforcement) runs *before* the aggregation stage, so a total can never include a masked row (filter-then-aggregate). A **pre-materialized** report Item carries its **own** source ACL (an ordinary Item — the [SAP Band-A materialized-extract exception](../sap/00-sap-pack.md)). A cross-source rollup takes the **intersection** of contributing ACLs (most-restrictive-wins, the *existing* mixed-ACL invariant / DocIntel merge rule); an aggregate whose contributing set the platform *cannot* fully resolve rides the *existing* `approximate → deny + quarantine` hatch ([§9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) |
| Metadata (label schema, catalog, lineage) | **None** (additive lineage only) | A report/aggregate is a `derived_artifact` node whose backward-lineage edges point at every contributing source row — reusing DocIntel's `LineageNode.kind` growth ([Metadata §9](../../metadata/00-catalog-and-lineage.md)), **already blessed**; **no new dimension, no new store**. Erasing a contributing source row tombstones the aggregate (or forces its recompute) via the forward lineage walk |
| Governance (label matrix, SLA, retention) | **None** | **Inherited** the riding domain's compliance row and label matrix; a report **tightens** to its most-restrictive contributing label (never loosens). No policy engine added — an aggregate's label is `⊆ registry` exactly like any chunk's |
| RAG (chunking, hybrid, verifier) | **None** | A pre-materialized report is chunked by its structure (table rows / sections) using the *existing* structure-aware seam ([RAG §2.1](../../rag/00-retrieval-pipeline.md)); the **verifier** grounds every reported number in its cited source rows (the *existing* numeric-grounding bar Finance defined) — a report that can't cite its rows refuses, it does not guess |
| Storage / Workers / API / Deployment | **None** | Report ingestion/refresh is ordinary staged-DAG **parse + re-sync** work ([Workers §2, §5](../../workers/00-ingestion-architecture.md)); the report is written under the *most-restrictive contributing source's* tier ([Storage §5](../../storage/00-storage-architecture.md)); API `pack:"reporting"` is the *existing* optional additive hint |

**Net horizontal change: none, all additive.** The headline: the concept most likely to force a
horizontal primitive — an **aggregate that leaks a masked row by arithmetic inference** — resolves
because the platform **never computes-and-serves a total over rows the caller cannot already read**.
The defense is not a new disclosure-control component; it is the **order of two stages that already
exist** — the ACL filter runs *before* aggregation ([ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)),
so any aggregate a caller receives is computed over a set they could have retrieved row-by-row, and
therefore reveals nothing new. Per [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md),
if a future edit to this pack requires the platform to *serve a total over rows the caller can't
individually read* (a legitimate "department total, not individual salaries" requirement), that edit
needs a horizontal ADR for statistical disclosure control — deliberately out of scope, quarantined
today (see Future scalability).

---

## Aggregation — the falsifiability analysis (the reason this cycle exists)

This is the section a reviewer should read first; it is the whole point of choosing Reporting last.

**The claim under test.** *"A report — a dashboard tile, a BI extract, an aggregate row — is
expressible as additive pack data + policy; an aggregate over rows with heterogeneous ACLs does not
force a new predicate, a disclosure-control engine, or a loosened floor, even though a total can in
principle reconstruct a masked row."*

**Decomposition — separate the two ways a report value comes to exist:**

1. **Pre-materialized aggregate (the source already computed it).** A BW query result, a Power BI
   dataset row, a nightly ledger-rollup table, a published dashboard snapshot — these are **Items that
   already exist in the source** and carry the source's **own ACL** on that materialized artifact. The
   source decided who may see the total. The platform **mirrors** that ACL exactly like any document —
   this is the [SAP Band-A materialized-extract case](../sap/00-sap-pack.md) ("a materialized extract
   carrying its own row ACL is an ordinary Band-A item"). *Additive — nothing new.*
2. **Query-time aggregate (the platform computes it in answering a question).** "What was total Q3
   travel spend?" The pipeline retrieves the contributing rows **through the ACL filter first**
   ([Permissions §4](../../permissions/00-authorization-model.md#4-query-time-enforcement)), then
   aggregates **only what survived the filter**. The caller therefore only ever sees a total over rows
   they **could have retrieved individually** — the aggregate is strictly *less* revealing than the
   rows it sums. **Filter-then-aggregate, never aggregate-then-filter.** *Additive — it is the existing
   query-time-enforcement order.*

**Where it *could* have broken — and why it does not.** Three traps, all disarmed:

- **Trap A — the small-cell / differencing leak (the sharp one).** If the platform ever computed a
  total over rows the caller *cannot* read and displayed just the total, an aggregate over one masked
  row would **be** that row, and a difference of two aggregates would reconstruct the delta. This is
  the trap that *looks* like it needs k-anonymity / small-cell suppression / differential privacy.
  **It is disarmed by construction, not by a disclosure-control engine:** the platform never computes
  an aggregate over rows outside the caller's ACL (Trap-A's premise is unreachable — the filter
  removed those rows *before* the aggregation stage ran). A caller can only difference aggregates built
  from rows they can each already read, which leaks nothing. **The one seam through which aggregation
  leaks — aggregate-then-filter — is not a code path the platform has.**
- **Trap B — a cross-source rollup that should carry a *narrower* ACL than any single input.** A tile
  joining SAP BW `{A,B}`, a Finance ledger `{B,C}`, and a SharePoint list `{B}` produces a value whose
  correct audience is whoever may read **every** contributing row. This is DocIntel's multi-source
  merge: the aggregate carries the **intersection** (`{B}` here, most-restrictive-wins), splits per
  source, or quarantines — **never the union** (a union would show A a value depending on the ledger
  row A can't read). *The existing merge rule, reused verbatim.*
- **Trap C — an aggregate whose contributing set is not fully resolvable** (a rollup over a BW analysis
  authorization the connector can't enumerate to a principal set — [SAP Band-C](../sap/00-sap-pack.md)).
  The platform cannot prove the caller may read every contributing row, so it **cannot** honestly serve
  the total. It takes the *existing* `approximate → deny + quarantine` path
  ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
  denied on the shared retrieval path, never approximately served. **The fourth sighting of a hatch
  already built** (SAP field-auth, Legal computed-privilege, DocIntel redaction-cell).

Because a served aggregate is *always* computed over the caller's own permitted set (query-time) or
carries the source's own ACL (pre-materialized), Reporting carries **one pack-local discipline (not a
mechanism):**

> **The aggregation discipline — the platform aggregates only over rows the caller may already read,
> and mirrors (never re-computes) a source-materialized total's ACL.** (1) *Query-time:*
> **filter-then-aggregate** — the ACL predicate runs before the aggregation stage, so every displayed
> total is a function of rows the caller could have retrieved individually; a total therefore reveals
> nothing a row-by-row read would not. (2) *Pre-materialized:* a source-computed report Item carries
> the **source's own ACL** on that artifact (Band-A mirror). (3) *Cross-source:* a rollup carries the
> **intersection** of its contributing rows' ACLs (DocIntel merge), splits, or quarantines — never the
> union; an unresolvable contributing set is quarantined, never approximately served.

This is the Reporting analogue of DocIntel's "derivation inherits or tightens, never widens" and
Audit's "read-plane mirror" disciplines: a single stated rule that keeps a genuinely new capability
(arithmetic aggregation) inside the additive contract. Because the rule is *filter-first / mirror /
intersect*, the worst a misconfigured Reporting pipeline can do is over-mask a tile or quarantine a
rollup (availability), never over-expose a masked row (safety) — fail-closed applied to *aggregation*.

**Verdict:** the bet holds against its first — and the platform's last-planned — *aggregation* concept.
The falsifiability rule was armed against an **arithmetic-inference leak** and did **not** fire: the
platform never aggregates rows the caller can't read, so no total reconstructs a masked value; the
defense is the *existing* filter-then-aggregate order, not a new disclosure-control engine. Had a
tenant required the platform to **serve a total over rows the caller cannot individually read** (a
legitimate statistical-disclosure use case), this section would instead be a horizontal ADR proposal
for a suppression / differential-privacy control against [Permissions](../../permissions/00-authorization-model.md) /
[Governance](../../governance/00-governance-and-audit.md); that it is not — because that requirement is
deliberately out of scope and quarantined — is the finding. **This is the tenth consecutive `§0 =
none, all additive` ledger; the domain-pack surface is now complete.**

---

## §1 — Sources & `map_acl` fidelity

A report's "source" is often **another pack's already-ingested content** joined and aggregated (it
rolls up Finance's ledgers, SAP BW cubes, HR headcounts). Its `map_acl` job is therefore mostly
**inheritance + intersection**, not fresh mapping — the fidelity target is *"the report/aggregate's
ACL equals the intersection of its contributing source rows' ACLs (or the source-materialized artifact's
own ACL), provably, via lineage."* Anything below `exact` is **denied on the shared retrieval path**
and quarantined ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).

| Source / input | Item class | Principal mapping | Max `acl_confidence` | Notes |
|----------------|-----------|-------------------|:--------------------:|-------|
| **SAP BW / BI (analysis authorizations)** | A BW query result / InfoProvider extract | Reuses the [SAP pack's three-band model](../sap/00-sap-pack.md): org-level → **Band A `exact`**; structural → **Band B** resolve-or-quarantine; characteristic/cell-level analysis auth → **Band C** quarantine | per SAP band | Reporting adds **no** SAP fidelity — it cites the SAP pack verbatim |
| **Power BI / Tableau / Qlik dataset or published report** | A pre-materialized report Item carrying its own ACL | The BI tool's row-level-security / workspace ACL is mapped like any source ACL (`map_acl`); a materialized artifact with its own audience is **Band-A** | `exact` iff the RLS/workspace ACL was fully read | The SAP Band-A materialized-extract case, generalized to any BI tool |
| **Finance reporting DB / ledger rollup table** | A pre-aggregated table (row = a rollup) | Inherits the table's row ACL (Finance fidelity, reused) | `exact` iff source `exact` | Finance pack fidelity, reused |
| **SharePoint-hosted report / dashboard export** | A file/list Item | The SharePoint item-level ACL ([SharePoint pack](../sharepoint/00-sharepoint-pack.md), reused; "anyone"-link → flag-and-fail-closed) | `exact` iff item perms fully read | SharePoint fidelity, reused |
| **Query-time aggregate over source rows** | A `derived_artifact` computed in answering | Computed **only over rows the caller's ACL already admits** (filter-then-aggregate); the aggregate is served iff the caller is entitled to **every** contributing row | `exact` iff every contributing row resolved `exact` for this caller; else **quarantine** | The falsifiability corner — filter runs before aggregation; a total never includes a masked row |
| **Cross-source rollup** (a tile joining D1, D2, …) | A `derived_artifact` merging rows across sources | ACL = **intersection** of contributing source ACLs (most-restrictive-wins), else **split per source**, else **quarantine** | `exact` only if the merged ACL is fully resolvable; else **quarantine** | DocIntel's multi-source merge rule, reused verbatim — never the union |
| **Small-cell / unresolvable-contributor aggregate** | An aggregate the platform can't prove the caller may fully see | — | `approximate` → **deny + quarantine** (or native OBO §10) | The platform never serves a total it cannot ground in rows the caller may read |

**Conformance fixtures (the production gate).** The Reporting connector/pipeline ships a fixture set
for the [permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any Reporting pipeline goes live:

1. **Filter-then-aggregate (positive + negative):** a query-time total over rows `{r1∈A, r2∈A, r3∈B}`
   returns, for caller-in-A-only, the sum of `{r1,r2}` — **r3 is filtered out before the sum**; the
   caller never sees a total that includes a row they can't read.
2. **Small-cell / differencing non-leak:** a caller cannot reconstruct a masked row by differencing two
   aggregates — because every aggregate they can obtain is built only from rows they can each read
   (the aggregate-then-filter path does not exist). 0 reconstructions on the held-out set.
3. **Cross-source rollup = intersection, never union:** a tile aggregating D1`{A,B}`, D2`{B,C}` is
   visible **only** to B; A cannot obtain a value depending on D2, C cannot on D1.
4. **Pre-materialized report mirrors source ACL:** a published Power BI report with RLS `{finance-mgr}`
   is retrievable by a finance-mgr and masked from everyone else — the platform mirrors, never
   recomputes, the source's audience.
5. **Unresolvable-contributor quarantine:** an aggregate over a BW analysis-authorization the connector
   can't enumerate to a principal set is `approximate → deny + quarantine`, never approximately served.
6. **Lineage completeness:** erasing a contributing source row tombstones or forces recompute of every
   aggregate that consumed it (forward lineage walk, [Metadata §5.2](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4)) —
   no stale aggregate keeps a value derived from erased data.
7. **Cross-tenant:** no report/aggregate of tenant A ever aggregates or reaches tenant B (R4), inherited
   unchanged.

---

## §2 — Classification-registry values (the vocabulary Reporting registers)

**Empty — this is the fifth pack with an empty §2** (after KM, SAP, SharePoint, Email), and for the
source-shaped packs' exact reason generalized: **a report carries no policy of its own — it *presents*
the riding domain's.** A finance dashboard's numbers are `restricted:mnpi`/`confidential` because
**Finance** declared them so; an HR headcount tile is `pii_class:*` because **HR** did. Reporting
**inherits and composes** those labels (most-restrictive-wins across contributing rows); it invents no
new classification dimension and no new value. A report tile that aggregates a `restricted:mnpi` ledger
row is itself **at least** `restricted:mnpi` — the composition is the existing lattice, unchanged.

> A report claiming a label vocabulary of its own would be the same **category error** the SAP pack
> named: presentation is not policy. The one nuance vs. the source packs — a report may compose labels
> from *several* domains at once (a cross-domain executive dashboard) — is handled by the existing
> **most-restrictive-wins** composition, not a new value.

---

## §3 — Label→action *tighten* deltas

**Empty — no new tighten delta.** A report **inherits** its contributing rows' labels and their
existing matrix rows, composed most-restrictive-wins. There is no report-specific label to tighten,
because §2 registered none. The one behavior worth stating explicitly is **not** a new delta but a
consequence of composition:

- A report/aggregate resolves to the **most restrictive** label among its contributing rows (a tile
  mixing `internal` and `restricted:mnpi` rows is enforced as `restricted:mnpi`), and to the
  **most restrictive tier** among them ([Storage §5](../../storage/00-storage-architecture.md)). This
  is the mixed-ACL invariant applied to labels — *inherited*, not a new rule.

Every enforcement outcome for a report is therefore already defined by the contributing domains' §3
deltas; Reporting adds none.

---

## §4 — Compliance-map row(s) (declare + inherit)

Reporting **inherits** the compliance rows of whatever domains it aggregates; it declares no regime of
its own. The evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)),
now carrying the aggregate's backward-lineage to its contributing rows.

| Regime | Inherited controls (already built) | Reporting-specific evidence binding |
|--------|-----------------------------------|-----------------------------------|
| **The riding domain's regime** (SOX / Art. 9 / PCAOB / …) | Whatever each *contributing* domain's compliance row binds | A report **inherits every** contributing domain's regime — a tile joining a Finance ledger and an HR headcount is **both** SOX- and Art.9-relevant; the aggregate never escapes any contributing source's compliance envelope (it inherited the intersection ACL + most-restrictive tier) |
| **SOX (financial reporting integrity)** | Numeric grounding + refuse-over-guess (Finance); audit-as-evidence; `legal_hold > erasure > retention` | A reported financial number is **grounded in cited source rows or the answer refuses** (the Finance numeric-grounding bar, reused); the report's lineage is the SOX evidence that a figure traces to its ledger source |
| **GDPR (aggregated PII)** | Right-to-erasure + DSAR; PII masking; residency; `pii_class:*` | Erasing a source row forces every aggregate consuming it to tombstone/recompute (lineage walk) — a DSAR reaches PII *inside an aggregate*, not only free-standing PII |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | A report lives under the *most-restrictive contributing source's* tier/DEK — no separate isolation surface |

**No new control was invented.** Reporting's compliance posture is a *selection, inheritance, and
composition* of controls the platform already operates. The one Reporting-specific obligation — that a
reported **number** is grounded in its source rows — is the **existing** Finance numeric-grounding /
verifier bar, retargeted, not a new control.

---

## §5 — Retrieval / answer eval set

The Reporting pack supplies (a) the **parsers** that make report/dashboard content retrievable and (b)
the **eval corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance). Its
headline failure mode is unique among packs: an **arithmetic** leak, not a content one.

**Parsers (behind the existing per-content-type seam — [RAG §2.1](../../rag/00-retrieval-pipeline.md)):**
- **Tabular report / BI extract** — table-row chunking (reuses RAG's structure-aware seam); the
  mixed-ACL invariant keeps a row chunk within one ACL; a rollup row carries its contributing-row
  lineage edges.
- **Dashboard / tile export** — section + tile chunking; each tile's cited source query is captured so
  the verifier can ground the displayed number.
- **SAP BW serialization** — reuses the [SAP-pack table-serialization parser](../sap/00-sap-pack.md)
  verbatim; Reporting adds no new SAP parser.

**Eval set (aggregation non-leak · numeric grounding · inheritance/intersection correctness):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Filter-then-aggregate permission negatives** | A caller cannot obtain a total that includes a row outside their ACL via any cleverly-worded prompt (the filter runs before the sum) | 0 leaks (a masked row never enters an aggregate the caller receives) |
| **Small-cell / differencing non-leak** | A caller cannot reconstruct a masked value by differencing two aggregates; every aggregate they can obtain is built from rows they can each read | 0 reconstructions on the held-out differencing set |
| **Cross-source intersection correctness** | An answer citing a cross-source rollup exposes only the intersection of contributing ACLs; never a value depending on a source the caller can't read | 0 cross-source over-grants on the held-out set |
| **Numeric grounding (SOX)** | Every reported number traces to cited source rows; no invented or mis-summed figure | 100% reported numbers cited or the answer refuses |
| **Refuse-over-guess** | A question about a report/aggregate the caller can't fully access → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated or partial total presented as complete | 0 fabrications on the held-out no-access set |
| **Aggregate erasure completeness** | Erasing a contributing source row removes/recomputes every aggregate that consumed it; no stale total survives | 0 retrieval of an aggregate over erased rows |

A model that regresses on **filter-then-aggregate negatives**, **small-cell non-leak**, or
**cross-source intersection** cannot be promoted for a Reporting pipeline — the same gate shape as
every prior pack, retargeted to Reporting's dominant failure mode (**arithmetic inference**, the one
leak vector no prior pack had).

---

## §6 — Optional additive API `pack` hint

Reporting callers **may** pass `"pack": "reporting"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (e.g.
prefer the tabular/numeric-tuned model, bias retrieval toward report tables and dashboard tiles, apply
table-aware chunking, tighten the numeric-grounding bar). It is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"reporting"`
  but is outside a contributing row's ACL sees no aggregate over that row
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an authorization
  input; an aggregate never carries an ACL broader than the intersection of its inputs.
- **Omitting it is valid.** The platform infers report context from the accessible content; the hint
  only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"reporting"` is
  [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7), not a
  breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Filter-then-aggregate vs. aggregate-then-filter.** Filtering rows *before* summing means the
  platform cannot serve a legitimate "you may see the department total but not individual salaries"
  aggregate over rows the caller can't read individually — that requires statistical disclosure
  control the platform deliberately does not have. The trade buys a hard guarantee (no total ever
  reconstructs a masked row) at the cost of that one class of aggregate, which is quarantined, not
  approximately served. This is the honest fail-closed direction.
- **Intersection (most-restrictive-wins) vs. union for cross-source rollups.** Intersection means a
  cross-source tile is visible to fewer people than any single contributing source — an availability
  cost. Union would be a leak (showing a value that depends on a row the caller can't read). The bet
  forbids the union; the availability cost is the fail-closed-preferred direction (the DocIntel trade,
  re-applied).
- **Mirror a pre-materialized total vs. recompute it.** The platform mirrors a source-materialized
  report's ACL rather than recomputing whether the caller may see each contributing row. This trusts
  the source's audience decision (Band-A) — correct, because the source *is* the authority on its own
  materialized artifact; recomputing would be the platform second-guessing a source ACL, which it never
  does for any Item.
- **Quarantining unresolvable-contributor aggregates vs. serving them.** An aggregate over a source the
  platform can't enumerate to a principal set is denied+quarantined (the R1 trade), not approximately
  served — the same honest availability cost SAP Band-C, Legal computed-privilege, and DocIntel
  redaction-cells pay. Fourth sighting of the same hatch.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Aggregate first, then check if the caller may see the total** (aggregate-then-filter) | **Rejected — this is the trap.** It is the exact seam through which small-cell/differencing leaks: a total over one masked row *is* that row. The platform filters rows *before* aggregating, so a served total is always a function of rows the caller could read individually. |
| **Add a small-cell suppression / k-anonymity / differential-privacy engine** | Rejected for the default path — it would be a new hot-path mechanism the bet forbids, and it is **unnecessary** because filter-then-aggregate makes the leak unreachable. It is named as the **one future ADR** if a tenant genuinely needs to serve aggregates over rows the caller can't read (out of scope today). |
| **Union the ACLs of a cross-source rollup** | Rejected: union *widens* — a tile joining D1`{A,B}` and D2`{B,C}` under a union `{A,B,C}` would show A a value depending on D2's row A can't read. The rollup takes the **intersection** (most-restrictive-wins), splits, or quarantines. |
| **Recompute a pre-materialized report's audience instead of mirroring it** | Rejected: the source is the authority on its own materialized artifact (Band-A); the platform mirrors source ACLs, it never second-guesses them. |
| **Give reports their own label vocabulary** | Rejected (§2 empty): a report *presents* the riding domain's policy; a presentation-owns-policy claim is the SAP category error. Labels compose most-restrictive-wins from contributing rows. |
| **A Reporting-specific aggregation store / pipeline** | Rejected: would be a horizontal change. Reports ride the existing parse stage + staged DAG; an aggregate is the *additive* `LineageNode.kind` DocIntel already blessed — not a new store. |
| **Bespoke Reporting compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): Reporting inherits every contributing domain's regime + reuses Finance's numeric-grounding bar; re-deriving controls is the anti-pattern. |

## Future scalability

- **The domain-pack surface is now complete.** Ten packs — six concept-shaped
  (Finance/HR/Legal/Audit/KM/DocIntel), three source-shaped (SAP/SharePoint/Email), and Reporting
  (aggregation) — every one with a `§0 = none, all additive` ledger. The founding bet ("new domain =
  pack, not redesign") is now proven across policy concepts, source fidelity, derived content, and
  arithmetic aggregation. A new domain (Procurement, Manufacturing, CRM) is a fill-in-the-blank pack.
- **A new aggregate type** (a windowed time-series rollup, a pivot, a materialized cube) = the same
  filter-then-aggregate / intersection / lineage discipline — additive, no redesign.
- **A better numeric/tabular model** enters through the existing eval gate (§5) and is routed by the
  existing label→trust policy — a config change, not a code change.
- **Per-cell provenance** for a regulated reported number = extend the aggregate's backward-lineage to
  cite each contributing row ([Metadata §9](../../metadata/00-catalog-and-lineage.md)) — an additive
  schema change, the SOX evidence path.
- **The one future case that *would* force a horizontal ADR** is named explicitly: a tenant requiring
  the platform to **serve an aggregate over rows the caller cannot individually read** (a legitimate
  statistical-disclosure requirement — "the department total is releasable even though the individual
  salaries are not"). That needs a **suppression / differential-privacy control** — a new mechanism
  against [Permissions](../../permissions/00-authorization-model.md) / [Governance](../../governance/00-governance-and-audit.md),
  deliberately out of scope and **quarantined today** (an aggregate over rows the caller can't fully
  read is denied, not served). Making the platform *safely disclose* such a total would be that ADR,
  not a pack edit — the tenth pack ends, as the first did, by naming the exact boundary at which the
  bet would next be tested.

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack (numeric grounding)](../finance/00-finance-pack.md) · [Document Intelligence pack (derived-ACL inheritance + multi-source merge)](../document-intelligence/00-document-intelligence-pack.md) · [SAP pack (BW fidelity + Band-A materialized-extract)](../sap/00-sap-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md) · [ADR-0004 — Query-time permission enforcement](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)
- [Permissions §4 (query-time enforcement), §7 (labels subtract), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §3 (chunk ACL projection), §5.1 (lineage node/edge), §5.2 (erasure tombstone), §9 (additive node-kind growth)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §8 (model/eval gate), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG §2.1 (table/structure-aware chunking), §2.2 (mixed-ACL invariant), verifier (numeric grounding)](../../rag/00-retrieval-pipeline.md) · [Workers §2 (parse stage), §5 (re-sync), §8.1 (DLQ)](../../workers/00-ingestion-architecture.md) · [Storage §5 (tiers)](../../storage/00-storage-architecture.md) · [API §4, §5, §11](../../api/00-api-surface.md)
