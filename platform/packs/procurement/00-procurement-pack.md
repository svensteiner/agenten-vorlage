# Domain Pack #11 — Procurement / Sourcing (the external-counterparty test)

> **The first pack whose principals are not (only) the tenant's own employees.**
> Every pack from Finance through Reporting resolved access among *internal* principals —
> employees, roles, org units of the buyer organization. Procurement introduces the
> **counterparty principal**: a *supplier* who is an external human, party to the tenant's
> data, and who must be simultaneously (a) *granted* access to their own bid / PO / contract
> and (b) *walled off* from every competing supplier's. On top of that it introduces a
> **temporal integrity** corner no earlier pack had: a **sealed bid** must be invisible even
> to the buyer's *own authorized* evaluators until the bid-opening moment. If the platform's
> founding bet — *"new domain = pack, not redesign"* — survives an external principal and a
> time-gated seal without a new predicate, it has been stressed on a genuinely new axis.
> This document is both the Procurement spec **and** the worked example that the external
> principal is *just a principal* and the seal is *just a mirrored ACL*.

- **Cycle:** 29 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** Anti-bribery/anti-corruption (FCPA / UK Bribery Act), GDPR (supplier-contact PII),
  SOX (procurement feeds AP — three-way-match control), public-procurement fairness (FAR / EU Directive
  2014/24 where the tenant is a public body), sanctions/restricted-party screening (read-plane mirror only — §7)
- **Isolation tier (default):** Standard, with a **per-source lift to Isolated** for sealed-tender
  and supplier-confidential-pricing content ([Storage §5](../../storage/00-storage-architecture.md))

---

## Why Procurement is the right next stress test (and where it could crack)

The domain-pack surface was declared complete at Reporting (Cycle 20): all ten planned packs held
with a `§0 = none, all additive` ledger. Procurement is deliberately *not* one of the planned ten —
it is picked as the [Cycle 29 refinement](../../NEXT_STEPS.md) precisely because it pushes on two
mechanisms no earlier pack exercised, so it is the honest test of whether the surface is *complete* or
merely *complete for internally-scoped domains*:

- **The counterparty is an external principal.** A supplier's buyer-side contact is not an employee of
  the buyer tenant. Earlier packs' effective-principal sets were `{employee} ∪ groups ∪ roles`, all
  internal ([Permissions §4](../../permissions/00-authorization-model.md#4-resolving-the-subjects-effective-principals-query-time)).
  If a supplier ever gets portal/query access, the platform must (a) grant them *their own* items and
  (b) never leak a competing supplier's bid or any buyer-internal content — **the SharePoint over-grant
  test, but with the principal outside the org.** The failure mode is a *silent cross-counterparty leak*.
- **A sealed bid is invisible even to an authorized reader — until a time.** Sealed-tender integrity
  (anti-collusion) requires that between submission and the published opening moment, **no principal —
  not even the tender's own buyer-side evaluator** — can read a bid. The static allow/deny ACL set
  ([§2.2](../../permissions/00-authorization-model.md#22-resource-acl-shape-stored-per-chunk)) has no
  "…but not before T" clause. This is the sharpest corner: *does time-gated visibility force a new
  predicate?*
- **Procurement is action-adjacent.** Raise a PO, approve a requisition, *award* a contract — all are
  writes. If the platform were tempted to *take* a procurement action, that would be a new plane. It is
  not: Procurement rides the **read-plane-mirror** boundary [Audit](../audit/00-audit-pack.md) already drew.
- **Three-way match = segregation of duties, again.** Requester ≠ approver ≠ goods-receiver is procurement
  SoD; sanctions screening is a control the *source* runs. Both are the Audit SoD result reused verbatim.

If any of these forced a horizontal change, that is the finding. **None did** — see §0. Two of them (the
external principal, the sealed bid) *looked* like they would and did not; the reasons are §1.1 and §1.2.

---

## §0 — Horizontal-change ledger (the proof of the bet)

| Horizontal surface | Change required by Procurement? | What Procurement did instead |
|--------------------|:-------------------------------:|------------------------------|
| Permissions (canonical model, `map_acl`) | **None** | An **external supplier is a CPI like any other** — `<tenant>:<source>:guest:<objectId>` (the type field is already open; SharePoint guests use it). Tenant namespacing means the supplier CPI lives *under the buyer tenant*, so R4 holds unchanged. Sealed-bid visibility is a **mirrored ACL that starts empty** (§1.2), not a new time predicate. |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `restricted:supplier_confidential` + `restricted:sealed_bid` into the existing `restricted:<class>` extension point (§2). Supplier-contact PII rides the **existing** `pii` dimension — no new `pii_class` invented. |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** the matrix for the two new labels (§3); **inherited** the SOX, GDPR, anti-bribery and public-procurement rows (§4). |
| RAG (chunking, hybrid, verifier) | **None** | Supplied bid-table / contract-clause / PO-line parsers behind the existing per-content-type seam; supplied an eval set (§5) including the cross-counterparty leak negative. |
| Storage / Workers / API / Deployment | **None** | Standard tier with a per-source **lift** to Isolated for sealed/confidential content (an *existing* placement choice); connector rides the existing staged DAG; `pack:"procurement"` is the existing optional additive hint. |
| Orchestration / action plane | **None** | Procurement is **read-plane-mirror** ([Audit §-boundary](../audit/00-audit-pack.md)) — the platform never awards, posts, or approves. No action plane is introduced. |

**Net horizontal change: none. All additive.** The pack is data + two registered labels + tightened
policy + fixtures + an eval corpus. The **eleventh consecutive all-additive ledger**, and the first
to hold it across an *external* principal and a *temporal* seal. If a future edit adds a row with
"required," that edit needs a horizontal ADR.

---

### §1.1 — Why an external supplier is *just a principal* (the falsifiability test — held)

The tempting mistake is to model "supplier" as a new *principal category* with its own access rule
("suppliers may see items tagged for their company"). That would be a new predicate — a floor change.
It is unnecessary:

- A supplier's buyer-side identity is issued in the buyer's IdP as a **guest / B2B external identity**
  (Entra B2B guest, an Ariba/Coupa vendor account federated in, etc.). It normalizes to a CPI exactly
  like an employee: `acme:aad:guest:8f3c-…` or `acme:ariba:vendor:V-40021`
  ([Permissions §2.1](../../permissions/00-authorization-model.md#21-canonical-principal-identifier-cpi)).
- **Tenant namespacing makes the leak-across-tenants impossible by construction.** The supplier CPI is
  prefixed with the *buyer* tenant `acme`; it is a principal *inside* the buyer's data plane, ACL'd to
  specific items. R4 (`resource.tenant_id != subject.tenant_id → deny`) is untouched.
- **Cross-*counterparty* confidentiality is the ordinary allow-set.** A bid Item's ACL allow-set =
  `{buyer-side evaluators}` ∪ `{that one supplier's guest CPI}`. A *competing* supplier is a **different
  guest CPI**, not in the allow set, so `is_permitted` returns false at "need at least one allow"
  ([Permissions §3](../../permissions/00-authorization-model.md#3-the-authorization-decision-the-one-function)).
  No new rule — the same predicate that walls two SharePoint sites apart walls two suppliers apart.
- **An external principal reaching internal content is the SharePoint over-grant test inverted onto a
  guest, and held the same way**: a guest CPI simply is not in the allow-set of `internal`/`confidential`
  buyer items, so they are denied. A source construct that *would* silently grant a guest broad access
  (an Ariba "all-suppliers" group, an "anyone with the link" bid portal) maps to **flag-and-fail-closed**,
  never a silent grant — the exact [SharePoint §1 rule](../sharepoint/00-sharepoint-pack.md).

**Result:** the external principal costs *fidelity work at the connector* (correctly mapping guest
identities and refusing to synthesize a grant), never a new access predicate. The bet holds.

### §1.2 — Why a sealed bid is *just a mirrored ACL that starts empty* (the sharper test — held)

Sealed-tender integrity says: between submission and opening, **no one** reads the bid. The static ACL
has no temporal clause, so naïvely this needs a "visible-after-T" predicate — a floor change. It does not,
because of the platform's oldest discipline, first stated for privilege in [Legal](../legal/00-legal-pack.md):
**the platform mirrors an authorization fact, it never computes one.**

- The **source procurement system holds the seal.** Ariba/Coupa/Jaggaer (or a public e-tendering portal)
  keeps a submitted bid sealed and **exposes no read grant** until the opening event. The connector,
  mirroring faithfully, captures an ACL whose allow-set is **empty** (or buyer-side only for metadata) —
  which resolves to *deny for everyone* under "need at least one allow." **A sealed bid is not specially
  handled; it is an item that currently grants no one read.**
- At the opening moment, the **source publishes the grants** (evaluators, and later the awarded/losing
  suppliers per the tender's disclosure rules). The **existing change-driven re-sync**
  ([Workers §change-driven](../../workers/00-ingestion-architecture.md)) propagates the new ACL within the
  freshness SLA. Visibility flips because the *mirrored fact* changed — the platform computed nothing.
- **`restricted:sealed_bid` (§2) is defence-in-depth, not the primary gate.** The label adds an Isolated-pool
  + no-egress tightening so that *even if* a connector wrongly captured a grant on sealed content, the label
  still blocks egress and shared-pool exposure. The ACL is the primary gate; the label subtracts capability
  on top ([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
- **Fail-closed on ambiguity.** If the connector cannot faithfully determine whether an item is still sealed
  (`acl_confidence` below `exact`), it is **quarantined**, not served — the [§9 confidence gate](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)
  reused. An unsealing that the platform cannot verify costs *availability, never integrity*.

**Result:** time-gated visibility is expressed as *the ordinary ACL evolving as the source unseals* —
no `visible-after-T` predicate enters the decision function. The one thing the platform must **not** do —
*itself* enforce an unseal timer it computed — is named as the future ADR below.

---

## §1 — Sources & `map_acl` fidelity

Procurement sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)). Anything below
`exact` is **denied on the shared retrieval path** and quarantined
([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **S2P suite** (Ariba / Coupa / Jaggaer / Ivalua) | Requisition / PO / receipt header | `role:<buyer-role>` + `orgunit:<company/plant>` + buyer-side evaluator CPIs | `exact` iff expressible as principal set-membership | Buyer-internal items — same shape as SAP MM (§below) |
| **S2P suite** | **Bid / quote (sealed)** | Allow-set **empty until opening** (source holds seal); post-opening: `{evaluators}` ∪ `{submitting supplier guest CPI}` per disclosure rules | `exact` iff seal state is faithfully read; else **deny + quarantine** | §1.2 — mirror the seal, never compute the timer. `restricted:sealed_bid` label as defence-in-depth |
| **S2P suite** | **Bid / contract (open, per-supplier)** | `{buyer evaluators}` ∪ `{that supplier's guest CPI}` — **that supplier only** | `exact` iff the per-supplier grant is read exactly | §1.1 — a competing supplier is a different CPI, not in the allow-set → walled by the ordinary predicate |
| **SAP MM** (OData/RFC/BAPI) | PO / contract / vendor-master record | `role:MM_*` + `orgunit:<purch-org / plant>` | `exact` iff expressible as principal set-membership | Inherits the [SAP pack](../sap/00-sap-pack.md) three-band model verbatim (Band B/C → resolve-or-quarantine) |
| **CLM** (contract-lifecycle mgmt: Icertis, DocuSign CLM, Conga) | Executed contract / clause | Item-level ACL → CPIs; NDA-bound clauses → `restricted:supplier_confidential` | `exact` when item perms fully read | Contract clause chunking reuses the [Legal](../legal/00-legal-pack.md) clause parser |
| **Supplier portal / vendor master** | Vendor-contact record (external PII) | Guest CPI + buyer AP/sourcing roles | `exact` when portal grant read; **"all suppliers" / anonymous link → flag-and-fail-closed** | External-PII handling rides existing `pii` dimension; over-grant test = SharePoint mirror |
| **Email / SharePoint** (negotiations, RFx docs) | Message / document | Inherited from [Email](../email/00-email-pack.md) / [SharePoint](../sharepoint/00-sharepoint-pack.md) packs | per those packs | Negotiation threads carry `restricted:supplier_confidential` where NDA-bound |

**Conformance fixtures (the production gate)** — for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate),
must pass in CI **and** as the production canary before any Procurement source goes live:

1. **Cross-counterparty wall.** Supplier A's guest CPI **sees** its own bid and **cannot see** supplier
   B's bid on the same tender (positive + negative) — proven at query time by the allow-set, not by a bid tag.
2. **Sealed-bid invisibility.** A submitted-but-not-yet-opened bid is **invisible to the tender's own
   buyer-side evaluator** (allow-set empty); after a simulated opening event + re-sync, the evaluator sees
   it **within the freshness SLA** — visibility flips because the mirrored ACL changed.
3. **External-principal containment.** A supplier guest CPI **cannot** retrieve any `internal`/`confidential`
   buyer content (not in the allow-set), and a cleverly-worded prompt cannot obtain it (permission-negative).
4. **Unresolvable seal state → quarantine.** A bid whose seal state cannot be read to `exact` is
   **quarantined**, not served with a guessed grant (the `approximate → deny` path).
5. **"All suppliers" group → flag-and-fail-closed**, never a silent broad grant (SharePoint over-grant rule).

---

## §2 — Classification-registry values (the vocabulary Procurement registers)

Procurement **registers** two values into the existing `restricted:<class>`
[extension point](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions) — it invents no new
dimension. An unregistered label is a write-boundary schema violation → DLQ
([Workers §8.1](../../workers/00-ingestion-architecture.md)), never silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:supplier_confidential` | Supplier cost breakdowns, confidential pricing, proprietary technical proposals — NDA-bound counterparty IP |
| `sensitivity` | `restricted:sealed_bid` | A bid under sealed-tender integrity — defence-in-depth on top of the empty-until-opening ACL (§1.2) |
| `pii` | *(none — reuses existing)* | Supplier-contact PII (names, emails, phone of a supplier's staff) rides the **existing** `pii` dimension; GDPR still applies to a counterparty's employees |

These slot into the existing lattice (`public < internal < confidential < restricted:*`), so
**most-restrictive-wins** composition is inherited unchanged. A sealed bid containing confidential
pricing and supplier-contact PII resolves to `restricted:sealed_bid` + `restricted:supplier_confidential`
+ `pii:true` — the most restrictive action of each dimension applies.

**This is the 6th pack with a non-empty §2** (after Finance, HR, Legal, Audit-`workpaper`, DocIntel) —
Procurement genuinely owns confidentiality concepts a source does not carry, so it is *concept-shaped*,
not source-shaped.

---

## §3 — Label→action *tighten* deltas

Procurement **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:supplier_confidential` | Only to principals in the item ACL (buyer evaluators + owning supplier) | **Isolated model pool** for the confidential-content tenant | **No** external egress; excluded from batch/analytics export | Stricter than `confidential`: adds model-pool restriction + egress block (NDA posture) |
| `restricted:sealed_bid` | Governed by the (empty-until-opening) ACL; label never *grants* | Isolated pool only | **No** egress; **no** cross-bid analytics until opening | Defence-in-depth over §1.2 — even a mis-captured grant cannot egress or reach a shared pool |
| `pii:true` (supplier contact) | Masked in context ([RAG §6.4](../../rag/00-retrieval-pipeline.md)) unless the ACL explicitly permits the raw field | Masked in prompt by default | Excluded from batch export | Inherited PII handling — no Procurement-specific rule |

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
Procurement adds no rule that would let a label — including `sealed_bid` — *grant* access; the ACL is the
sole grant path.

---

## §4 — Compliance-map row(s) (declare + inherit)

Procurement **inherits** existing rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain);
it does not re-derive controls. Evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | Procurement-specific evidence binding |
|--------|-----------------------------------|---------------------------------------|
| **Anti-bribery / anti-corruption** (FCPA, UK Bribery Act) | Append-only audit; per-answer attribution; immutable versioned knowledge | Every retrieval over gift/hospitality/agent-payment records is audited with `resource_id` + subject + model version → an anti-corruption review is reproducible and attributable |
| **SOX** (procurement → AP three-way match) | Append-only audit; least privilege; ≥7-yr retention | Inherited from [Finance](../finance/00-finance-pack.md)/[Audit](../audit/00-audit-pack.md) verbatim — three-way-match **detection** ("who requested and approved the same PO?") is an ordinary permission-gated read (SoD detection, not prevention — §7) |
| **GDPR** (supplier-contact PII) | Right-to-erasure + DSAR; PII masking; residency; private-by-default | `pii` masking proven per query on supplier-contact fields; a supplier-contact erasure proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4) |
| **Public procurement fairness** (FAR / EU Dir. 2014/24, where the tenant is a public body) | Isolated tier; quarantine of unmappable sources; fail-closed on ambiguity | Sealed-bid invisibility (§1.2) + cross-counterparty wall (§1.1) are the *technical evidence* of tender fairness — a bid could not have been read early or by a rival |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Isolated tier + per-tenant DEK for the sealed/confidential-content tenant |

**No new control was invented.** Procurement's compliance posture is a *selection and binding* of controls
the platform already operates. Sanctions/restricted-party screening is a **source-side** control the
platform mirrors, not runs — see §7.

---

## §5 — Retrieval / answer eval set

The pack supplies (a) the **parsers** that make its content retrievable and (b) the **eval corpus** that
gates any model change through the [eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **Bid / RFx tables** — a bid line-item table is serialized to a stable, header-aware row form (reuses the
  [SAP-table serialization](../finance/00-finance-pack.md) approach), so exact PO/tender numbers match on the
  BM25 half; a chunk never spans two suppliers' lines (mixed-ACL invariant).
- **Contract clauses** — reuses the [Legal](../legal/00-legal-pack.md) clause parser; NDA/confidentiality
  clauses drive the `restricted:supplier_confidential` label.
- **PO / requisition lines** — one procurement record per chunk; a chunk never spans two org-unit ACLs.

**Eval set (grounding · refusal · pack task accuracy · the new negatives):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Cross-counterparty negative** | Supplier A can never obtain supplier B's bid/pricing via any prompt | **0 leaks** (permission test, not accuracy) |
| **Sealed-bid temporal negative** | No principal — including the tender's evaluator — retrieves a bid before its opening event | **0 pre-opening reads** on the held-out sealed set |
| **External-principal containment** | A supplier guest CPI never retrieves buyer `internal`/`confidential` content | **0 leaks** |
| **Numeric grounding** | Every price/quantity in an answer traces to a cited chunk; no synthesized figures | 100% figures cited or the answer refuses |
| **Refuse-over-guess** | "What did vendor X quote?" with no accessible/opened source → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated figure | 0 fabrications on the no-access set |
| **Three-way-match detection** | "Which POs had the same requester and approver?" returns the right join with citations, over permitted rows only | Pack-accuracy threshold; **0 leaks** of rows the caller can't read |

A model that regresses on the **cross-counterparty**, **sealed-bid**, or **external-principal** negatives
cannot be promoted for the Procurement tenant — the same gate shape as the connector conformance canary,
applied to the model.

---

## §6 — Optional additive API `pack` hint

Procurement callers **may** pass `"pack": "procurement"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (prefer the
Procurement eval-tuned model, bias retrieval toward S2P/CLM sources). It is strictly additive:

- **Identity still governs.** The hint never widens access — a supplier guest who passes
  `pack:"procurement"` but is not in an item's allow-set sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an authorization input.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the hint only
  optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"procurement"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7).

---

## Trade-offs

- **Mirror the seal vs. platform-enforced unseal timer.** Procurement *mirrors* the source's seal state
  (empty ACL until opening) rather than the platform *computing* an unseal time. This trades a slightly
  looser coupling (the platform's view flips only after re-sync catches the source's opening event, within
  the freshness SLA) for the correct guarantee: the platform never becomes the authority on tender timing —
  the same "mirror, never compute" discipline that keeps Legal from computing privilege waiver.
- **Quarantine over best-effort on ambiguous seal state.** A bid whose seal state can't be read to `exact`
  is unavailable on the shared path rather than approximately available. Trades recall for a hard
  no-early-read guarantee — the correct trade for tender integrity (R1).
- **External principals cost connector fidelity, not a new rule.** Correctly mapping guest/B2B identities
  and refusing to synthesize an "all suppliers" grant is real connector work; the payoff is that the access
  *decision* stays the one trivial predicate.
- **Isolated lift for confidential/sealed content vs. cost.** Sealed and NDA-bound content lifts to the
  Isolated pool + no-egress, which is more expensive than Standard. Accepted: a leaked competitor price or an
  early-read bid is a legal and fairness liability, not a UX blemish.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Model "supplier" as a new principal category with a bespoke visibility rule** | Rejected: a guest is already a CPI; a bespoke rule is a new predicate = a floor change. The ordinary allow-set walls counterparties apart (§1.1). |
| **Add a `visible_after` temporal field to the ACL and a time clause to `is_permitted`** | Rejected: that is a new predicate. The source holds the seal; the platform mirrors an ACL that starts empty and flips on re-sync (§1.2). |
| **Let the platform enforce the unseal timer itself** | Rejected *today* — it would make the platform the authority on tender timing (compute, not mirror). Named as the one future ADR below. |
| **Have the platform award/approve/post procurement actions** | Rejected: introduces a write/action plane the bet forbids. Procurement is read-plane-mirror ([Audit](../audit/00-audit-pack.md)); SoD prevention and sanctions screening are source-side controls. |
| **A Procurement-specific retrieval pipeline** | Rejected: a horizontal change. Procurement rides the hybrid permission-filtered pipeline unchanged; only parsers + eval + two labels are pack-local. |
| **Loosen masking for "internal category managers"** | Rejected: loosening a floor. Managers who need raw supplier-contact PII get an explicit ACL grant; the label default stays masked. |

## Future scalability

- **A new S2P/CLM source** (a new e-tendering portal, a new contract system) = a new §1 row + fixtures; no
  pipeline change. The cross-counterparty and sealed-bid fixtures are reused verbatim as the acceptance gate.
- **Manufacturing / Supply-chain packs** are now closer to fill-in-the-blank: supplier-collaboration
  (shared forecasts, VMI) reuses Procurement's external-principal handling; the shop-floor/BOM confidentiality
  reuses `restricted:supplier_confidential`.
- **The one named future ADR:** *the platform itself enforcing a computed unseal timer* (rather than
  mirroring the source's seal) — e.g. if a tenant runs tenders **inside** the platform with no external
  e-tendering system of record. That would introduce a time-conditioned authorization predicate and is
  therefore a **horizontal decision**, deliberately out of scope today and quarantined behind "mirror the
  source." This is Procurement's analogue of Reporting's named future ADR (serving a total over unreadable
  rows / statistical disclosure control).

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §2.1 (CPI), §3 (the one predicate), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [SharePoint pack (over-grant / guest handling)](../sharepoint/00-sharepoint-pack.md) · [Legal pack (mirror-not-compute)](../legal/00-legal-pack.md) · [Audit pack (SoD, read-plane-mirror boundary)](../audit/00-audit-pack.md) · [SAP pack (MM three-band fidelity)](../sap/00-sap-pack.md)
- [Metadata §4 (classification registry)](../../metadata/00-catalog-and-lineage.md) · [Governance §4 (label matrix), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, parsers)](../../rag/00-retrieval-pipeline.md) · [API §5, §11](../../api/00-api-surface.md)
