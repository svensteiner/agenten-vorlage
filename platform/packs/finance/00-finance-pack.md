# Domain Pack #1 — Finance

> **The reference pack.** Finance is the first domain pack and deliberately the
> hardest: it exercises every cross-cutting mechanism the ten horizontal cycles built —
> row/record-level source ACLs (SAP), the full label lattice
> (`restricted:<class>` + `pii_class:<type>` + `legal_hold`), the SOX/GDPR
> compliance rows, and per-content-type parsers (SAP table serialization). If the
> platform's founding bet — *"new domain = pack, not redesign"* — survives Finance, it
> survives. This document is both the Finance spec **and** the worked example of the
> [pack-spec skeleton](../README.md).

- **Cycle:** 11 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** SOX, GDPR, ISO 27001 / SOC 2, sector (finance supervisory)
- **Isolation tier (default):** Isolated ([Storage §5](../../storage/00-storage-architecture.md)) — SOX + supervisory posture

---

## Why Finance first (and why it is the right stress test)

The bet has been *asserted* ten times and *proven* zero times. Proving it needs a domain
that pushes on the mechanisms most likely to crack:

- **SAP has no document ACL.** Authorization is by authorization objects / org levels, not
  by a readable per-object grant. This is the single hardest input to the
  [canonical principal model](../../permissions/00-authorization-model.md#52-sap) — if the
  `acl_confidence` gate and quarantine doctrine can hold Finance safely, they hold anything.
- **Finance data is simultaneously `confidential`, PII-bearing, and legally held.** It is
  the only domain that exercises all three [label dimensions](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
  at once, under **most-restrictive-wins**.
- **SOX makes the audit trail a contract, not a nicety.** Finance forces the
  [audit-as-evidence](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)
  promise to be real.
- **Numbers must be grounded or refused.** A hallucinated figure in a variance answer is
  worse than "I don't know" — Finance is the strongest test of the
  [verifier's refuse-over-guess contract](../../rag/00-retrieval-pipeline.md).

If any of these forced a horizontal change, that would be the finding. **None did** — see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Finance? | What Finance did instead |
|--------------------|:---------------------------:|--------------------------|
| Permissions (canonical model, `map_acl`) | **None** | Declared a SAP `map_acl` fidelity target + fixtures against the *existing* §5.2 rules and §5.5 contract |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `restricted:*` / `pii_class:*` values into the existing registry extension point (§4.1) |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** existing matrix rows; **inherited** the SOX + GDPR compliance rows |
| RAG (chunking, hybrid, verifier) | **None** | Supplied SAP-table + ledger parsers behind the existing per-content-type parser seam; supplied an eval set |
| Storage / Workers / API / Deployment | **None** | Chose the *existing* Isolated tier; connector rides the *existing* staged DAG; API `pack:"finance"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** The pack is data + registered vocabulary +
tightened policy + fixtures + an eval corpus. This ledger is the falsifiable claim of
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md); if a future edit to
this pack adds a row with "required," that edit needs a horizontal ADR.

---

## §1 — Sources & `map_acl` fidelity

Finance sources and the **maximum `acl_confidence`** each connector must declare per item
class ([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)).
Anything below `exact` is **denied on the shared retrieval path** and quarantined to the
Isolated tier ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
Finance never fakes field-level security with document grants.

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **SAP FI/CO** (OData/RFC/BAPI) | Posting / document header | `role:FI_*` + `orgunit:CC<code>` (company code, cost center, plant) | `exact` **iff** the requirement is expressible as principal set-membership | Held SAP roles → matching principals ([§5.2](../../permissions/00-authorization-model.md#52-sap)) |
| **SAP FI/CO** | Field/row-restricted record (e.g. salary line in a cost-center report) | — | `approximate` → **deny + quarantine** | Field-level auth is *not* representable as a document grant |
| **General ledger / reporting DB** | Report / extract row | `role:<report-acl>` + `orgunit:*` | `exact` if the extract carries its own row ACL; else `approximate` | Row-level DB security honored or quarantined |
| **Excel workbooks** (SharePoint) | Per-sheet (the ACL-carrying [Item](../../metadata/00-catalog-and-lineage.md#3-the-catalog-schema-m1)) | Entra objectId → CPI; MIP label → `sensitivity` | `exact` when item-level SharePoint perms fully read | Mixed-ACL invariant: a chunk never spans two sheets with different ACLs |
| **Reporting DBs / BI extracts** | Materialized report | `role:<bi-role>` | `exact` if the BI layer exports its grant; else quarantine | |

**Conformance fixtures (the production gate).** The Finance connector ships a fixture set
for the [permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any Finance source goes live:

1. A user with `role:FI_AP_DISPLAY` + `orgunit:CC1000` **sees** CC1000 AP documents and
   **cannot see** CC2000 documents (positive + negative).
2. A cost-center report containing a field-restricted salary line is **quarantined**, not
   served with a document-level grant (the `approximate→deny` path).
3. A revoked SAP role removes access **within the freshness SLA**
   ([Governance §3.1](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table), Isolated ≤2 min for principals)
   — verified via query-time principal precedence, independent of chunk re-tag.
4. An Excel workbook with two differently-permissioned sheets yields chunks whose ACLs
   **never merge** across the sheet boundary.

---

## §2 — Classification-registry values (the vocabulary Finance registers)

Finance **registers** these values into the tenant [classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
extension points — it does not invent new dimensions. An unregistered label is a
write-boundary schema violation → DLQ ([Workers §8.1](../../workers/00-ingestion-architecture.md)),
never silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:mnpi` | Material non-public information (pre-announcement earnings, M&A) |
| `sensitivity` | `restricted:supervisory` | Data under finance-supervisory confidentiality |
| `pii` | `pii_class:financial` | Bank/account numbers, individual compensation |
| `pii` | `pii_class:tax` | Tax IDs, individual tax records |
| `legal_hold` | `matter:<id>` | Any Finance record placed under a litigation/audit hold |

These slot into the existing lattice
(`public < internal < confidential < restricted:*`), so **most-restrictive-wins**
composition is inherited unchanged. An MNPI-bearing, compensation-containing, legally-held
ledger row resolves to `restricted:mnpi` + `pii_class:financial` + `legal_hold:true` — the
most restrictive action of each dimension applies.

---

## §3 — Label→action *tighten* deltas

Finance **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:mnpi` | Only to principals holding the MNPI-cleared grant | **Isolated model pool only** ([Governance §3.1](../../governance/00-governance-and-audit.md)) | **No** external egress; no batch export | Stricter than `confidential`: adds a model-pool restriction + egress block |
| `restricted:supervisory` | Isolated tier only | Isolated pool | Region-locked to residency class | Adds residency lock |
| `pii_class:financial` / `pii_class:tax` | Masked in context ([RAG §6.4](../../rag/00-retrieval-pipeline.md)) unless the subject's grant explicitly permits the raw field | Masked in prompt by default | Excluded from any batch/analytics export | Adds masking + batch-exclusion |
| `legal_hold:true` (`matter:*`) | Unchanged (visibility unaffected) | Unchanged | **Never auto-deleted** — retention override ([Governance §5.3](../../governance/00-governance-and-audit.md#53-legal-hold-overrides-erasure--retention)) | Inherited, not tightened |

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
Finance adds no rule that would let a label *grant* access.

---

## §4 — Compliance-map row(s) (declare + inherit)

Finance **inherits** the SOX and GDPR/ISO rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain);
it does not re-derive controls. The evidence for each cell is an **existing** audit-event
type ([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | Finance-specific evidence binding |
|--------|-----------------------------------|-----------------------------------|
| **SOX** | Append-only audit; immutable versioned knowledge (Principle 8); per-stage least privilege; ≥7-yr audit retention | Every Finance answer's retrieval audit event carries `resource_id` + `source_item_version` + model version → a variance answer is reproducible and attributable years later |
| **GDPR** | Right-to-erasure + DSAR; PII masking; residency; private-by-default | `pii_class:financial`/`tax` masking proven per query; erasure completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4); `legal_hold > erasure` blocks premature deletion of held records |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Isolated tier + per-tenant DEK for the Finance tenant |
| **Sector (supervisory)** | Isolated tier + dedicated model pool + stricter SLA + quarantine of unmappable sources | `restricted:mnpi`/`supervisory` route only to the Isolated pool (§3) |

**No new control was invented.** Finance's compliance posture is a *selection and binding*
of controls the platform already operates — the definition of "inherits a posture."

---

## §5 — Retrieval / answer eval set

The Finance pack supplies (a) the **parsers** that make its content retrievable and (b) the
**eval corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **SAP table serialization** — an SAP table/extract is serialized to a stable, header-aware
  row form so a chunk is a coherent record, and dense + BM25 both retrieve it (exact
  document/PO numbers must match on the keyword half).
- **Ledger / reporting rows** — one accounting record per chunk; the mixed-ACL invariant
  means a chunk never spans two records with different org-unit ACLs.
- **Excel** — per-sheet chunking (the ACL-carrying Item), preserving header context per row.

**Eval set (grounding · refusal · pack task accuracy):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Numeric grounding** | Every figure in an answer traces to a cited chunk; no synthesized numbers | 100% figures cited or the answer refuses |
| **Refuse-over-guess** | "What was Q4 EBITDA?" with no accessible source → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated number | 0 fabrications on the held-out no-access set |
| **Reconciliation / variance** | Multi-record numeric Q&A returns the right figure with citations | Pack-accuracy threshold (set per model, tightened over releases) |
| **Permission negatives** | A user without CC2000 access cannot obtain CC2000 figures via a cleverly-worded prompt | 0 leaks (this is a permission test, not just an accuracy test) |
| **MNPI handling** | An `restricted:mnpi` chunk never reaches a non-Isolated model or an egress path | 0 violations |

A model that regresses on **numeric grounding**, **permission negatives**, or **MNPI
handling** cannot be promoted for the Finance tenant — the same gate shape as the connector
conformance canary, applied to the model.

---

## §6 — Optional additive API `pack` hint

Finance callers **may** pass `"pack": "finance"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(e.g. prefer the Finance eval-tuned model, bias retrieval toward Finance sources). It is
strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes
  `pack:"finance"` but lacks Finance principals sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an
  authorization input.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the
  hint only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"finance"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7),
  not a breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Isolated tier by default vs. cost.** Finance defaults to the Isolated tier (dedicated
  pool + per-tenant DEK + Isolated model pool for MNPI). This is more expensive than Shared,
  but the SOX + supervisory posture and the MNPI egress rules make it the honest default. A
  Finance sub-tenant with no MNPI could graduate *down* to Shared — a placement decision, not
  a redesign.
- **Quarantine over best-effort on SAP field security.** Refusing to fake SAP field-level
  auth with document grants means some field-restricted records are **unavailable on the
  shared path** rather than approximately available. This trades recall for a hard no-leak
  guarantee — the correct trade for Finance ([R1](../../NEXT_STEPS.md)).
- **Refuse-over-guess vs. helpfulness.** The numeric-grounding bar makes Finance answers
  refuse more often than a general-purpose assistant would. Accepted: a wrong number in
  Finance is a liability, not a UX blemish.
- **Registering vocabulary vs. free-text convenience.** Requiring `restricted:mnpi` etc. to
  be registered before use adds a setup step, but it is exactly what keeps the Governance
  matrix total and the DLQ meaningful ([Metadata §4.1](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)).

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Model SAP field security as synthetic document grants** | Rejected: fabricating a document ACL from field-level auth is exactly the R1 leak the confidence gate exists to prevent. Quarantine is the honest answer. |
| **A Finance-specific retrieval pipeline** | Rejected: would be a horizontal change (the thing the bet forbids). Finance rides the hybrid permission-filtered pipeline unchanged; only parsers + eval are pack-local. |
| **A dedicated Finance vector store schema** | Rejected: the five-store plane + `VectorIndex` port already carry ACL arrays + labels; Finance needs no schema change, only registered label values. |
| **Loosen masking for "internal Finance analysts"** | Rejected: that is loosening a floor. Analysts who need raw PII fields get an explicit grant; the label default stays masked. |
| **Bespoke Finance compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): Finance inherits the SOX/GDPR rows + binds evidence; re-deriving controls is the anti-pattern. |

## Future scalability

- **HR, Legal, Audit packs** are now **fill-in-the-blank** against this document's §1–§6.
  Audit especially reuses Finance's SOX row and SAP connector fidelity nearly verbatim.
- **A new Finance source** (e.g. a treasury system) = a new §1 row + fixtures; no pipeline
  change.
- **A new supervisory regime** = a new §4 compliance row binding existing controls
  ([Governance §12](../../governance/00-governance-and-audit.md#12-future-scalability)).
- **A tighter Finance SLA** = a ratified number change → Deployment raises reserved P0
  capacity; no redesign.
- **A Finance-tuned model** enters through the existing eval gate (§5) and is routed by the
  existing label→trust policy — a config change, not a code change.

## Related
- [Pack skeleton & the falsifiability rule](../README.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §5.2 (SAP), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §4 (classification registry)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, parsers)](../../rag/00-retrieval-pipeline.md) · [API §5, §11](../../api/00-api-surface.md)
