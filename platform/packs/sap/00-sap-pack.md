# Domain Pack #6 — SAP (the first *source-shaped* pack)

> **A source pack, not a policy pack.** Finance, HR, Legal, Audit and KM are
> *concept-shaped* — each stressed a **policy** corner (restrictive `who`-gates, a novel
> concept, a combinatorial rule, the inverse over-refusal case). SAP is the first
> *source-shaped* pack: it introduces **no new policy concept at all**. Its entire content
> is **connector `map_acl` fidelity** for the single hardest source the platform targets —
> the one source with **no document ACL**. This document is therefore the **canonical SAP
> `map_acl` reference** that every SAP-touching pack (Finance FI/CO, HR HCM, Audit GRC)
> cites instead of re-deriving, and it **resolves the sub-question open Q#2 deferred**:
> *the exact `map_acl` fidelity achievable per SAP module.*

- **Cycle:** 16 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** *none of its own* — SAP **inherits** whatever regime the domain riding on it demands (SOX for Finance-on-SAP, GDPR for HCM-on-SAP, PCAOB for Audit-on-GRC)
- **Isolation tier (default):** inherited from the riding domain (Finance/HR/Audit default Isolated); a quarantined SAP class always lands on the [Isolated/quarantine tier](../../storage/00-storage-architecture.md) regardless

---

## Why SAP, and why it is a *different kind* of falsifiability test

The five concept packs answered *"does a new **policy** concept fit the horizontal
surfaces?"* SAP answers a structurally different question:

> **Does the *hardest source's entire authorization model* — every module, every
> authorization construct — fit the connector `map_acl` fidelity contract, with no case
> that is neither `exact` nor quarantinable?**

SAP is the right source to ask it of, for the same reason Finance was the right first pack:

- **SAP has no document ACL** ([Permissions §5.2](../../permissions/00-authorization-model.md#52-sap)).
  Authorization is by **authorization objects**, **roles/profiles** (PFCG), **org levels**
  (company code `BUKRS`, cost center `KOSTL`, plant `WERKS`, controlling area `KOKRS`,
  purchasing org `EKORG`, sales org `VKORG`), **field-level** activity (`ACTVT`) and value
  restrictions, **structural authorizations** (HCM org-tree evaluation paths), and **BW
  analysis authorizations** (characteristic-value / cell-level). It is the source that
  *motivated the [quarantine doctrine](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)
  in the first place.*
- **It is the most-reused source in the pack set.** Finance proved SAP fidelity *for FI/CO
  financial content*; HR reused it *for HCM*; Audit reused it *for GRC*. Until now that
  fidelity was asserted **three times, ad hoc, in three packs**. Cycle 16 consolidates it
  into **one canonical §1** — a DRY win as much as a new data point.

If any SAP module exposed an authorization construct the connector can neither resolve to a
principal set **nor** quarantine, that is a real **R1** gap → a horizontal Permissions ADR,
**not** a pack-local hack (the [falsifiability rule](../README.md#the-falsifiability-rule)).
**None did** — every construct lands in one of three fidelity bands (§1). See §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by SAP? | What SAP did instead |
|--------------------|:-----------------------:|----------------------|
| Permissions (canonical model, `map_acl`) | **None** | **Consolidated** the existing [§5.2 SAP rules](../../permissions/00-authorization-model.md#52-sap) + the [§9 quarantine hatch](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation) into a **module-by-module fidelity matrix** (§1). Every construct maps to Band A (`exact`), Band B (resolve-or-quarantine), or Band C (quarantine/OBO) — no new predicate, no new confidence level |
| Metadata (label schema, catalog, lineage) | **None** | **§2 is empty.** SAP is a *transport*, not a sensitivity domain — the labels SAP content carries are registered by the *domain* pack riding on it (Finance's `restricted:mnpi`, HR's `pii_class:health`), never by the source pack |
| Governance (label matrix, SLA, retention) | **None** | **§3 is empty.** A source tightens no policy; the riding domain's tighten-deltas apply to its SAP-sourced content unchanged |
| RAG (chunking, hybrid, verifier) | **None** | Promoted the **SAP table-serialization parser** (already named in [Finance §5](../finance/00-finance-pack.md)) to the canonical per-content-type parser for all SAP modules, behind the *existing* seam; supplied a **fidelity-band** eval set |
| Storage / Workers / API / Deployment | **None** | Rides the *existing* staged DAG; SAP **change documents** (CDHDR/CDPOS) are the *existing* `subscribe_changes` feed ([Connector §4](../../workers/01-connector-framework.md)); a quarantined class = the *existing* Isolated/quarantine tier; `pack:"sap"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** SAP is the **second pack with an empty §2
and §3** (after [KM](../km/00-km-pack.md)) — but for a structurally different reason. KM's
tables were empty because the **low-restriction defaults were already calibrated**; SAP's
are empty because **a source-shaped pack carries no policy of its own** — it is pure
connector fidelity, and policy belongs to the domain that rides it. Per
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit adds a
"required" row, that edit needs a horizontal ADR.

---

## The three-band fidelity model — the falsifiability analysis (the point of this cycle)

This is the section a reviewer should read first; it is the whole reason to seed SAP.

**The claim under test.** *"Every SAP authorization construct, across every module, is
representable in the canonical model as either an `exact` principal-set requirement, or a
sub-`exact` mapping that the existing confidence gate quarantines — there is no fourth case
that is neither resolvable nor quarantinable."*

Every SAP authorization construct sorts into exactly one of three bands:

### Band A — org-level & role authorization → `exact`
The requirement is **fully expressible as principal set-membership**: a role
(`role:FI_AP_DISPLAY`) plus an org-level value (`orgunit:CC1000`, `orgunit:PLANT2100`).
The Subject's **held SAP roles** ([Permissions §4.1 input 3](../../permissions/00-authorization-model.md#41-inputs))
form the matching principals; `map_acl` emits the item's requirement as those principals;
the [§3 predicate](../../permissions/00-authorization-model.md#3-the-authorization-decision-the-one-function)
decides. This is the case Finance already proved and HR/Audit reused.
**Confidence: `exact` — served on the shared path.**

### Band B — structural / dynamic authorization → *resolve-or-quarantine*
HCM **structural authorizations** (PD/OM org-tree **evaluation paths**), context-sensitive
HR master-data authorizations (`P_ORGINCON`), and dynamic security groups are **computed**,
not static set-membership. Two sub-cases, both already covered:
- **(B1) Pre-resolvable to a principal set at a point in time.** The connector evaluates the
  structural authorization at ingestion, emits the resulting principal set, and keeps it
  fresh via `list_principal_changes` on any org-structure or role-assignment change document
  ([Connector §4](../../workers/01-connector-framework.md), fed into the
  [identity graph §4.2](../../permissions/00-authorization-model.md#42-the-identity-graph)).
  This is **exactly the mechanism [HR §… computed manager-hierarchy](../hr/00-hr-pack.md)
  already rode** — the degenerate/dynamic case of the existing predicate. **Confidence:
  `exact`, provided the re-evaluation stays within the freshness SLA.**
- **(B2) Not stably resolvable** (the evaluation path depends on runtime state the connector
  cannot snapshot faithfully) → **`approximate` → deny + quarantine**, or the
  [§10 OBO hatch](../../permissions/00-authorization-model.md#10-delegated--on-behalf-of-access)
  (SAP principal propagation — read *as the user*, source is the authority).

### Band C — field / row / cell-level authorization → *quarantine (or OBO)*
FI/CO **field-level** authorization (a salary line inside a cost-center report; an `ACTVT`
restriction beyond display), infotype-**subfield** masking, and **BW analysis
authorizations** (characteristic-value / cell-level security *inside* a query result) are
**not representable as a document/item grant** — the restriction is *below* the ACL-carrying
[Item](../../metadata/00-catalog-and-lineage.md#3-the-catalog-schema-m1). Faking it with a
document grant is precisely the R1 leak the confidence gate exists to prevent. So:
**`approximate` → deny + quarantine** on the shared path (the exact path Finance's
field-level salary-line fixture already exercises), with **OBO** as the opt-in escape hatch
for the narrow high-value classes. *Exception:* a **materialized extract** that carries its
own row ACL (a BI export with an exported grant) is an ordinary Band-A item — the row
security became a document grant *at the source*, honestly.

**Why there is no fourth case.** An SAP authorization construct is either (a) expressible as
principal set-membership now → Band A; (b) expressible after a point-in-time evaluation the
connector can keep fresh → Band B1, else not stably resolvable → Band B2 quarantine; or (c)
sub-Item (field/row/cell) → Band C quarantine. "Resolvable to a principal set" and
"quarantinable" are jointly exhaustive: **anything not in (a)/(b1) is sub-`exact`, and
everything sub-`exact` is denied-and-quarantined by construction** — the
[`VectorIndex` port has no unfiltered method](../../storage/00-storage-architecture.md) and
the [persist stage routes sub-`exact` output to quarantine](../../workers/00-ingestion-architecture.md).
There is no representable state in which an unresolvable SAP authorization is *served*. The
rule was armed and did **not** fire.

---

## §1 — Sources & `map_acl` fidelity (the canonical SAP reference)

The module-by-module fidelity matrix. This table is what other packs cite instead of
re-deriving SAP mapping. **Band** is per the three-band model above; **max `acl_confidence`**
is what the connector may declare per [Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract).

| SAP module | Item class | Authorization construct | Principal mapping | Band | Max `acl_confidence` |
|-----------|-----------|-------------------------|-------------------|:----:|:--------------------:|
| **FI / CO** (OData/RFC/BAPI) | Posting / document header | Company code / cost center / plant (`F_BKPF_BUK`, `K_CCA`) | `role:FI_*` + `orgunit:CC<code>` | **A** | `exact` |
| **FI / CO** | Field/row-restricted record (salary line in a CC report) | Field-level `ACTVT` / value auth | — (sub-Item) | **C** | `approximate` → deny + quarantine |
| **MM** (materials mgmt) | Purchase order / requisition | Purchasing org / plant (`M_BEST_EKO`) | `role:MM_*` + `orgunit:EKORG<code>` | **A** | `exact` |
| **SD** (sales & distribution) | Sales document / delivery | Sales org / distribution channel / division (`V_VBAK_VKO`) | `role:SD_*` + `orgunit:VKORG<code>` | **A** | `exact` |
| **HCM / HR** (SuccessFactors, on-prem PA/OM) | Employee infotype record (whole-Item) | Master-data auth `P_ORGIN` (infotype-level) | `role:HR_*` + `orgunit:<orgkey>` | **A** | `exact` when the infotype = one Item's ACL |
| **HCM / HR** | Employee record under **structural** auth | PD/OM evaluation path (org-tree) | pre-evaluated principal set, re-synced on org change | **B1** | `exact` within SLA; else **B2** quarantine |
| **HCM / HR** | Infotype **subfield** (e.g. IT0008 pay component) | Context solution `P_ORGINCON` sub-record | — (sub-Item) | **C** | `approximate` → deny + quarantine |
| **BW / BI** | Query result row/cell | **Analysis authorization** (RSECADMIN, characteristic-value) | — (sub-Item, unless materialized) | **C** | `approximate` → deny + quarantine |
| **BW / BI** | Materialized extract with exported row ACL | Extract carries its own grant | `role:<bi-role>` | **A** | `exact` if the export carries the grant |
| **GRC Access Control** | Risk-analysis report / ruleset (as *content*) | Document/role ACL on the GRC object | `role:GRC_*` | **A** | `exact` |
| **GRC**-derived **SoD read-exclusion** | Item an independent principal must not read | Pre-resolved relation → per-principal `deny` | `deny [<principal>]` | **A** | `exact` (deny-wins) — see note |
| **Any module**, unresolvable dynamic/attribute rule | Any | Rule not resolvable & not sub-Item-only | — | **B2** | quarantine / OBO |

**Note on GRC / SoD.** SoD *prevention* is a **write/transaction control out of the
platform's read plane** — the platform never posts/approves/executes, so there is no SoD
action to gate ([Audit pack, SoD analysis](../audit/00-audit-pack.md)). SoD-derived *read*
exclusions are pre-resolved by the source into a per-principal `deny` (Band A, deny-wins).
SoD *detection* ("who both prepared and approved E?") is an ordinary permission-gated
retrieval over the GRC/audit trail — combinatorial logic in the query, never in the access
predicate. This pack inherits that boundary verbatim; it adds nothing.

**Conformance fixtures (the production gate).** The SAP connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
covering **all three bands** — the source-shaped analogue of a policy pack's fixtures:

1. **Band A positive/negative** — `role:FI_AP_DISPLAY` + `orgunit:CC1000` **sees** CC1000 AP
   documents and **cannot see** CC2000; an MM user with `orgunit:EKORG1000` cannot see
   `EKORG2000` requisitions.
2. **Band C quarantine** — a field-restricted salary line and a BW cell-level-restricted
   query row are **quarantined**, never served with a document grant (the `approximate→deny`
   path).
3. **Band B1 freshness** — an HCM structural-authorization change (employee moves org unit)
   re-evaluates the principal set **within the freshness SLA**
   ([Governance §3.1](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table)),
   verified via query-time principal precedence.
4. **Band B2** — a dynamic authorization the connector cannot snapshot is **quarantined**,
   not approximated up to `exact`.
5. **Revocation** — a revoked SAP role removes access within the SLA (Isolated ≤2 min for
   principals), independent of chunk re-tag.
6. **Cross-tenant** — no SAP chunk of tenant A is ever returned to tenant B (R4).

---

## §2 — Classification-registry values

**Empty — by design.** SAP is a *transport*, not a sensitivity domain. It has no native
sensitivity-labeling equivalent to M365's MIP labels; the sensitivity of SAP-sourced content
is assigned by the **domain pack riding on it** (Finance registers `restricted:mnpi` /
`pii_class:financial`; HR registers `pii_class:health` / `employment`; Audit registers
`restricted:audit_workpaper`) and by the platform classification rules. A source pack that
invented its own vocabulary would be claiming policy that isn't the source's to hold. The
empty table is the evidence: **SAP touches the [classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
only as a consumer of the riding domain's registered values.**

---

## §3 — Label→action *tighten* deltas

**Empty — by design.** A source tightens no policy. SAP-sourced content is governed by the
tighten-deltas of the **riding domain** ([Finance §3](../finance/00-finance-pack.md),
[HR §3](../hr/00-hr-pack.md), [Audit §3](../audit/00-audit-pack.md)) applied to its labels
unchanged. The one thing SAP *does* enforce — quarantine of Band-C/B2 items — is the
**existing** confidence-gate floor, not a new tighten. The
[label-can-only-subtract invariant](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)
is preserved trivially because SAP adds no label rule at all.

---

## §4 — Compliance-map row(s) (declare + inherit)

SAP declares **no regime of its own**; it **inherits** the regime of whatever domain rides on
it, and contributes **one source-specific evidence binding** that strengthens every inherited
row: a SAP-sourced answer's retrieval audit event carries the **SAP table/module + change-doc
number (`CDPOS`) + `source_item_version`**, so the answer is reproducible and attributable to
a specific SAP state.

| Regime | Inherited from (riding domain) | SAP-specific evidence binding |
|--------|-------------------------------|-------------------------------|
| **SOX** | [Finance](../finance/00-finance-pack.md) (FI/CO) | Every FI/CO answer traces to a cited SAP row with its change-doc number + version — a variance answer is reproducible years later |
| **GDPR** | [HR](../hr/00-hr-pack.md) (HCM) | HCM `pii_class:*` masking proven per query; Band-C infotype subfields quarantined, never approximated; erasure completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4) |
| **PCAOB / SOX** | [Audit](../audit/00-audit-pack.md) (GRC) | GRC-derived read-exclusions honored as deny-wins; SoD detection grounded in cited trail rows |
| **ISO 27001 / SOC 2** | any | Isolated tier + per-tenant DEK; read-only source credentials, per-tenant, per-connector ([Connector §7](../../workers/01-connector-framework.md)) |

**No new control was invented.** SAP's compliance posture is entirely *inherited* — the
purest possible demonstration of "a source pack contributes fidelity + evidence, not policy."

---

## §5 — Retrieval / answer eval set (the reusable SAP assets)

This is where a source-shaped pack contributes real, reusable engineering assets — the
**parser** and the **fidelity-band eval set** — rather than policy.

**Parsers (canonical, behind the existing per-content-type seam — [RAG](../../rag/00-retrieval-pipeline.md)):**
- **SAP table serialization** (promoted from [Finance §5](../finance/00-finance-pack.md) to
  the canonical SAP parser): an SAP table/extract is serialized to a stable, **header-aware
  row form** so a chunk is a coherent record, and dense + BM25 both retrieve it (exact
  document/PO/material numbers must match on the keyword half). The
  **mixed-ACL invariant** applies: a chunk never spans two records with different org-unit
  ACLs.
- **Module-aware record shaping** — FI posting, MM PO line, SD sales-doc line, HCM infotype
  record: one record per chunk, org-unit ACL attached at the Item boundary.

**Eval set (the source-shaped headline: *fidelity-band correctness*):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Band-band routing** | Every fixture item lands in its declared band (A served, C quarantined, B resolved-or-quarantined) | 100% correct band; **0** Band-C/B2 items served on the shared path |
| **Permission negatives** | A user without `orgunit:CC2000` cannot obtain CC2000 figures via a cleverly-worded prompt | 0 leaks |
| **Structural-auth freshness (B1)** | An org-move re-evaluates the principal set within SLA | 0 stale grants past SLA |
| **Numeric grounding** | Every SAP figure in an answer traces to a cited row; no synthesized numbers | 100% figures cited or refuse |
| **Refuse-over-guess** | A question answerable only from a quarantined (Band-C) record → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated number | 0 fabrications |

A model or connector version that regresses on **Band-band routing** or **permission
negatives** cannot be promoted for any SAP-sourced tenant — the same gate shape as the
connector conformance canary, applied to fidelity.

---

## §6 — Optional additive API `pack` hint

SAP callers **may** pass `"pack": "sap"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(prefer the SAP-table-tuned parser/model, bias retrieval toward SAP sources). It is even more
purely optional than a domain pack's hint, because **SAP is a source, not a domain**: a caller
almost always asks *as Finance* or *as HR* and the SAP-sourcing is incidental. The hint is
strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"sap"`
  but holds no SAP roles sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)).
- **Omitting it is valid.** The platform infers SAP context from the accessible sources; the
  hint only optimizes routing. Absence never changes correctness.
- **Not a version event** — [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7).

---

## Trade-offs

- **Quarantine over best-effort on Band C.** Refusing to fake SAP field/row/cell-level auth
  with document grants means some restricted records are **unavailable on the shared path**
  rather than approximately available. This trades recall for a hard no-leak guarantee — the
  correct trade for SAP (**R1**), and the trade the whole quarantine doctrine exists to make.
- **Band B point-in-time resolution vs. staleness risk.** Pre-evaluating structural
  authorizations buys `exact` shared-path serving, but binds correctness to the freshness SLA
  on the re-evaluation. Accepted because query-time principal precedence
  ([Permissions §8](../../permissions/00-authorization-model.md#8-freshness-the-stale-permission-problem-r3))
  backstops the highest-severity case (revocation) independent of the re-eval.
- **OBO latency vs. exactness for the narrow classes.** The B2/C escape hatch reintroduces a
  live source call; used only for the highest-value quarantined classes, never as the default
  ([Connector §6](../../workers/01-connector-framework.md)).
- **A canonical source pack vs. per-pack SAP notes.** Consolidating SAP fidelity here means
  Finance/HR/Audit now cite one reference instead of restating it — a DRY win, at the cost of
  one more cross-pack link to keep consistent.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Model SAP field/row/cell security as synthetic document grants** | Rejected: fabricating a document ACL from field-level auth is exactly the R1 leak the confidence gate exists to prevent. Quarantine (Band C) is the honest answer. |
| **Promote Band-B2 dynamic auth to `exact` to raise recall** | Rejected: raising confidence to make an item ingestible is the single change most likely to leak; blocked by the conformance suite ([Permissions §9.4](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)). |
| **A new confidence level between `approximate` and `exact` for SAP** | Rejected: would be a horizontal change to the predicate. The three bands are *presentations* of the existing two-outcome gate (`exact` served / sub-`exact` quarantined), not a new level. |
| **Register SAP sensitivity labels in §2** | Rejected: SAP holds no native sensitivity vocabulary; the riding domain owns classification. A source pack claiming policy is a category error. |
| **A dedicated SAP retrieval pipeline** | Rejected: a horizontal change (the thing the bet forbids). SAP rides the hybrid permission-filtered pipeline unchanged; only the parser + fidelity fixtures are pack-local. |

## Future scalability

- **A new SAP module** (e.g. TRM treasury, RE-FX real estate) = a new §1 matrix row assigned
  to a band + fixtures; no pipeline change. The three-band model already classifies it.
- **A new SAP source system** (S/4HANA Cloud vs. ECC) = a new connector version emitting the
  same `{allow, deny, labels, confidence}`; the fidelity matrix is authorization-model-shaped,
  not release-shaped.
- **SharePoint and Email packs** are now **near-pure fidelity reuse** against this pattern —
  both already exercised (SharePoint in restricted *and* open mode via Finance/HR/Legal/KM;
  Email via HR/Legal/Audit). Their source packs, if written, will be shorter than this one
  (both *have* document ACLs, so no Band-C quarantine story dominates).
- **A future SAP module that exposes an authorization construct that is neither resolvable to
  a principal set nor sub-Item-quarantinable** would be the one case forcing a horizontal
  Permissions ADR — none found across FI/CO, MM, SD, HCM, BW, GRC; documented here so a future
  author knows exactly what would trip the falsifiability rule.

## Related
- [Pack skeleton & the falsifiability rule](../README.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §5.2 (SAP), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Connector §2 (`map_acl`), §4 (change docs), §6 (OBO)](../../workers/01-connector-framework.md)
- Packs that ride this one: [Finance (FI/CO)](../finance/00-finance-pack.md) · [HR (HCM)](../hr/00-hr-pack.md) · [Audit (GRC)](../audit/00-audit-pack.md)
