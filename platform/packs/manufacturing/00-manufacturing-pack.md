# Domain Pack #12 — Manufacturing / Shop-Floor (the machine-authored-data + export-control test)

> **The first pack whose primary data has no human author — and the first with a
> nationality-conditioned regime.** Every pack from Finance through Procurement resolved
> access over content a *person* created and a source system ACL'd to *people*: a document,
> a message, a ledger row, a bid. Manufacturing's core content is **machine-generated
> telemetry** — a PLC tag, a sensor stream, an MES cycle-count, an SPC measurement — authored
> by *equipment*, not an employee, and therefore carrying **no native per-user ACL of its
> own**. On top of that it introduces **export-controlled technical data** (ITAR / EAR): a
> CNC program or an engineering drawing that only **US persons** may read. "US persons only"
> *looks* like a citizenship predicate the decision function has never had. If the founding
> bet — *"new domain = pack, not redesign"* — survives an author-less data stream and a
> nationality-gated regime without a new predicate, it has been stressed on two genuinely
> new axes at once. This document is both the Manufacturing spec **and** the worked example
> that machine data is *just a container-inherited ACL* and export control is *just a
> mirrored group*.

- **Cycle:** 31 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** Export control (**ITAR** 22 CFR 120–130 / **EAR** 15 CFR 730–774 — US-persons + no-offshore-egress), product-safety & quality traceability (**ISO 9001 / IATF 16949 / AS9100**), worker safety / EHS (**OSHA** incident & SDS records), GDPR (operator-shift PII), SOX (production data feeding COGS — inherited from Finance)
- **Isolation tier (default):** Standard, with a **per-source lift to Isolated** for export-controlled technical data and trade-secret process IP ([Storage §5](../../storage/00-storage-architecture.md))

---

## Why Manufacturing is the right next stress test (and where it could crack)

The domain-pack surface was declared complete at Reporting (Cycle 20), and Procurement (Cycle 29)
proved it holds for **external-party, time-gated** domains beyond the planned ten. Manufacturing is
the [Cycle 31 refinement](../../NEXT_STEPS.md) precisely because it pushes on two mechanisms neither
the ten planned packs *nor* Procurement exercised — so it is the honest test of whether the surface is
*complete* or merely *complete for human-authored, domestically-scoped content*:

- **The primary content has no human author, and therefore no native user-ACL.** A document has an
  owner; a mailbox has a delegate; a PO has a requester. A **temperature trace from oven #7** has none
  of these — it was emitted by a device. Every earlier pack's ACL fidelity started from *a grant a person
  or source placed on an item*. If a stream carries no ACL, the tempting default is *"machine data is
  operational, make it broadly `internal`"* — a **silent floor-loosen**. The failure mode is
  *author-less data defaulting open*.
- **Export-controlled data is legible only to a subset of persons defined by *nationality*.** ITAR §120.62
  restricts technical data to **US persons**; EAR adds deemed-export rules. The static allow/deny ACL
  set ([§2.2](../../permissions/00-authorization-model.md#22-resource-acl-shape-stored-per-chunk)) has no
  "…and only if the reader is a US person" clause. This is the sharpest corner: *does a nationality-gated
  regime force a new principal attribute and a new predicate?*
- **Manufacturing is intensely action-adjacent — it is the shop floor.** Issue a machine command, release
  a work order, adjust a setpoint, halt a line — all are writes to physical equipment, some safety-critical.
  If the platform were tempted to *actuate* anything, that would be a new (and dangerous) plane. It is not:
  Manufacturing rides the **read-plane-mirror** boundary [Audit](../audit/00-audit-pack.md) already drew.
- **OEE / yield dashboards are aggregates over mixed-ACL machine rows.** A plant-wide OEE number rolls up
  per-line, per-shift rows. This is the [Reporting](../reporting/00-reporting-pack.md) arithmetic-inference
  corner reused — *filter rows before aggregating*, never the reverse.

If any of these forced a horizontal change, that is the finding. **None did** — see §0. The first two
(author-less data, the nationality gate) *looked* like they would and did not; the reasons are §1.1 and §1.2.

---

## §0 — Horizontal-change ledger (the proof of the bet)

| Horizontal surface | Change required by Manufacturing? | What Manufacturing did instead |
|--------------------|:---------------------------------:|--------------------------------|
| Permissions (canonical model, `map_acl`) | **None** | Machine telemetry **inherits its asset-container ACL** (work-center / line / plant) via [lineage](../../metadata/00-catalog-and-lineage.md), the same inherit-source-ACL rule [DocIntel](../document-intelligence/00-document-intelligence-pack.md) built for derived content; an item whose container ACL is unresolvable is **quarantined**, never defaulted open (§1.1). Export control is a **mirrored `us_persons` group** → an ordinary allow-set, not a nationality predicate (§1.2). |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `restricted:export_controlled` + `restricted:trade_secret` into the existing `restricted:<class>` extension point (§2). Asset provenance rides the **existing** `LineageNode.kind` additive node-kind growth [Metadata §9](../../metadata/00-catalog-and-lineage.md) already named. Operator-shift PII rides the **existing** `pii` dimension. |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** the matrix for the two new labels (§3); **inherited** the ITAR/EAR, ISO/IATF, OSHA and SOX rows (§4). |
| RAG (chunking, hybrid, verifier) | **None** | Supplied time-series-window / SPC-table / BOM / work-instruction / CNC-program parsers behind the existing per-content-type seam; supplied an eval set (§5) including the author-less-data and export-control negatives. |
| Storage / Workers / API / Deployment | **None** | Standard tier with a per-source **lift** to Isolated for export-controlled + trade-secret content (an *existing* placement choice); high-volume telemetry rides the existing staged ingestion DAG with the existing **change-driven/batched** modes; `pack:"manufacturing"` is the existing optional additive hint. |
| Orchestration / action plane | **None** | Manufacturing is **read-plane-mirror** ([Audit §-boundary](../audit/00-audit-pack.md)) — the platform never commands equipment, releases work orders, or changes a setpoint. No actuation plane is introduced. |

**Net horizontal change: none. All additive.** The pack is data + two registered labels + tightened
policy + fixtures + an eval corpus. The **twelfth consecutive all-additive ledger**, and the first to hold
it across **author-less machine data** and a **nationality-conditioned regime**. If a future edit adds a row
with "required," that edit needs a horizontal ADR.

---

### §1.1 — Why author-less machine data is *just a container-inherited ACL* (the falsifiability test — held)

The tempting mistake is to treat a stream with no per-user ACL as a new *ownerless* item class with a
default grant ("telemetry is operational → visible to any `internal` reader"). That default is a **silent
floor-loosen** — exactly the SharePoint over-grant failure, arriving through a different door. It is
unnecessary, because the platform already has the discipline for *content whose ACL is not authored on the
item itself*: **inherit the ACL from the resolvable source of authority, and fail closed when it cannot be
resolved.**

- **The authority is the physical asset's container, not the byte stream.** A PLC tag, a sensor reading, an
  MES event, an SPC sample all belong to an **asset** (machine / cell / line / work-center / plant), and the
  MES / historian / asset registry (SAP PP/PM, AVEVA PI, Ignition, Aveva/Wonderware) holds an **access grant
  on that asset or work-center** — "who may see line 3 / plant Wuppertal." The connector mirrors *that* grant
  and the telemetry item **inherits it via lineage** (`LineageNode.kind: asset_container`), exactly as a
  [DocIntel](../document-intelligence/00-document-intelligence-pack.md) derived artifact inherits its source
  Item ACL. A stream spanning two work-centers with different ACLs takes the **intersection**, never the union.
- **No resolvable container ⇒ quarantine, never a default grant.** If a telemetry source cannot be tied to an
  asset whose ACL resolves to `exact`, the item is **denied on the shared path and quarantined**
  ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
  the same confidence gate every other pack uses. **"Author-less" never resolves to "reader-less-so-open."**
  A wrong resolution costs *availability, never safety* — the DocIntel invariant reused.
- **`us_persons`-style groups and asset-ownership groups are ordinary principals.** Whoever the source says
  may read line 3 is a set of CPIs (a role, an org-unit group, named operators). The platform mirrors that
  set; the ordinary allow-set predicate walls plant A's operators from plant B's line exactly as it walls two
  SharePoint sites.

**Result:** author-less data costs *fidelity work at the connector* (correctly resolving the asset→container→ACL
chain and refusing to invent a grant), never a new access rule or an "ownerless-item" default. The bet holds.

### §1.2 — Why export control (ITAR/EAR) is *just a mirrored group*, not a nationality predicate (the sharper test — held)

ITAR restricts technical data to **US persons**; a naïve reading says the decision function must learn the
reader's *nationality* and gate on it — a new principal attribute **and** a new clause in `is_permitted`, i.e.
a floor change. It does not, because of the platform's oldest discipline, first stated for privilege in
[Legal](../legal/00-legal-pack.md): **the platform mirrors an authorization fact, it never computes one.**

- **The source of record already encodes eligibility as group membership.** In a compliant manufacturer, an
  export-controlled drawing / CNC program / spec lives in a **PLM/PDM system** (Teamcenter, Windchill, 3DEXPERIENCE)
  or a controlled vault, and access is granted to an **`ITAR-US-persons` security group** whose membership was
  vetted by the export-compliance function (an empirical, HR/legal-verified fact — citizenship, green-card,
  approved TAA/license). The platform **mirrors that group** as a set of CPIs. Eligibility is *read from the
  source*, never *derived by the platform from a nationality field*.
- **The allow-set does the walling.** An export-controlled Item's ACL allow-set = `{ITAR-US-persons group CPIs}`
  (∩ the asset-container ACL from §1.1). A non-US-person is simply **not in the group**, so `is_permitted`
  returns false at "need at least one allow" — **no new predicate, no citizenship attribute on the subject.**
  A "deemed export" (a foreign national physically reading in-country) is the *same* non-membership deny.
- **`restricted:export_controlled` (§2) is defence-in-depth, not the primary gate.** The label adds an
  Isolated-pool + **no-offshore-egress** tightening (no non-US-region model, no export of the content off
  US soil) so that *even if* a connector wrongly captured a broad grant, the label still blocks egress and
  shared-pool exposure ([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
  The ACL/group is the primary gate; the label subtracts capability on top.
- **Fail-closed on ambiguity.** If the connector cannot faithfully determine whether an item is export-controlled
  or whether the reader is in the vetted group (`acl_confidence` below `exact`), the item is **quarantined** —
  the §9 confidence gate. An unverifiable export status costs *availability, never a violation*.

**Result:** a nationality-conditioned regime is expressed as *the ordinary allow-set over a mirrored, source-vetted
group* — no citizenship attribute and no `us_person_only` clause enter the decision function. The one thing the
platform must **not** do — *itself* determine who is a US person from a nationality field — is named as the future
ADR below.

---

## §1 — Sources & `map_acl` fidelity

Manufacturing sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)). Anything below
`exact` is **denied on the shared retrieval path** and quarantined
([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **MES / historian** (SAP ME/MII, Ignition, AVEVA PI, Wonderware) | Telemetry stream / cycle-count / OEE event | **Inherited** from the asset-container ACL via lineage (`role:PROD_*` + `orgunit:<plant/line/work-center>`) | `exact` iff the asset→container→ACL chain resolves; else **deny + quarantine** | §1.1 — author-less data; inherits the container ACL, never defaults open |
| **SPC / quality** (quality LIMS, InfinityQS, SAP QM) | SPC sample / inspection / NCR / CAPA | `role:QA_*` + `orgunit:<plant>`; links to the [Audit](../audit/00-audit-pack.md)/quality NCR flow | `exact` iff item perms fully read | NCR/CAPA reuse Audit's append-only evidence + Quality-nonconformance handling |
| **PLM / PDM** (Teamcenter, Windchill, 3DEXPERIENCE) | Engineering drawing / spec / **CNC-NC program** / BOM | Item-level ACL → CPIs; export-controlled items → **`ITAR-US-persons` group** + `restricted:export_controlled`; trade-secret process IP → `restricted:trade_secret` | `exact` when item perms + control status fully read; else **deny + quarantine** | §1.2 — export control is a mirrored group, not a nationality predicate |
| **SAP PP / PM** (production planning / plant maintenance) | Work order / routing / maintenance notification / vendor-master | `role:PP_*`/`PM_*` + `orgunit:<plant>` | `exact` iff expressible as principal set-membership | Inherits the [SAP pack](../sap/00-sap-pack.md) three-band model verbatim (Band B/C → resolve-or-quarantine) |
| **CMMS / EHS** (Maximo, SAP EHS) | Maintenance record / SDS / OSHA incident (operator PII) | `orgunit:<plant>` + EHS roles; injured-operator PII → `pii` | `exact` when record perms read | OSHA incident narratives carry operator-shift `pii`; masked per §3 |
| **Supplier collaboration** (VMI, shared forecasts, ASN) | Shared forecast / kanban / drawing shared to a supplier | **Guest CPI** (reuses [Procurement §1.1](../procurement/00-procurement-pack.md) external-principal handling) | `exact` when the per-supplier grant is read; **"all suppliers" link → flag-and-fail-closed** | External-principal handling inherited from Procurement verbatim; a rival supplier is a different CPI |

**Conformance fixtures (the production gate)** — for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate),
must pass in CI **and** as the production canary before any Manufacturing source goes live:

1. **Author-less data inherits, never defaults.** A telemetry stream for line 3 is readable **only** by
   principals in line 3's container ACL (positive); a reader with `internal` access to a *different* plant
   **cannot** read it (negative) — proven by the inherited container ACL, not a broad `internal` default.
2. **Unresolvable asset container → quarantine.** A telemetry source that cannot be tied to an asset whose
   ACL resolves to `exact` is **quarantined**, not served as `internal` (the `approximate → deny` path).
3. **Export-control containment.** A non-US-person CPI (not in the `ITAR-US-persons` group) **cannot** retrieve
   an export-controlled drawing / CNC program via any prompt (permission-negative, **0 leaks**); a vetted
   US-person in the group can (positive).
4. **Cross-plant / cross-work-center wall.** Plant A operators cannot read plant B's line telemetry; the
   allow-set walls them exactly as it walls two SharePoint sites.
5. **Supplier VMI containment.** A supplier guest CPI sees only the forecast/drawing shared to *it*, never a
   competitor's or buyer-internal process IP ("all suppliers" link → flag-and-fail-closed) — Procurement rule reused.

---

## §2 — Classification-registry values (the vocabulary Manufacturing registers)

Manufacturing **registers** two values into the existing `restricted:<class>`
[extension point](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions) — it invents no new
dimension. An unregistered label is a write-boundary schema violation → DLQ
([Workers §8.1](../../workers/00-ingestion-architecture.md)), never silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:export_controlled` | ITAR/EAR-controlled technical data — drawings, specs, CNC/NC programs, controlled test data; defence-in-depth on top of the `ITAR-US-persons` group ACL (§1.2) |
| `sensitivity` | `restricted:trade_secret` | Process IP that is the crown jewel — recipes/formulations, tolerance bands, tooling/CNC programs, proprietary process parameters; NDA-and-competitive-harm content a source may not itself flag |
| `pii` | *(none — reuses existing)* | Operator-shift PII (names, badge IDs, injury narratives in OSHA/EHS records) rides the **existing** `pii` dimension; GDPR still applies to shop-floor staff |

These slot into the existing lattice (`public < internal < confidential < restricted:*`), so
**most-restrictive-wins** composition is inherited unchanged. A CNC program that is both export-controlled and
a trade secret resolves to `restricted:export_controlled` + `restricted:trade_secret` — the most restrictive
action of each dimension applies.

**This is the 7th pack with a non-empty §2** (after Finance, HR, Legal, Audit-`workpaper`, DocIntel,
Procurement) — Manufacturing genuinely owns confidentiality concepts (export control, process trade secret)
that a raw telemetry source does not carry, so it is *concept-shaped* on §2 while *source-shaped* on §1.

---

## §3 — Label→action *tighten* deltas

Manufacturing **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:export_controlled` | Only to principals in the `ITAR-US-persons` group ∩ the item ACL | **US-region Isolated model pool only** — no non-US-region model may see the content (deemed-export control) | **No** egress off US soil; excluded from batch/analytics export and any offshore processing | Stricter than `confidential`: adds region-pinned model pool + no-offshore-egress (ITAR/EAR posture) |
| `restricted:trade_secret` | Only to principals in the item ACL (need-to-know process owners) | Isolated model pool for the trade-secret tenant | **No** external egress; excluded from batch/analytics export and cross-tenant benchmarking | Stricter than `confidential`: adds model-pool restriction + egress block (competitive-harm posture) |
| `pii:true` (operator) | Masked in context ([RAG §6.4](../../rag/00-retrieval-pipeline.md)) unless the ACL explicitly permits the raw field | Masked in prompt by default | Excluded from batch export | Inherited PII handling — no Manufacturing-specific rule |

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
Manufacturing adds no rule that would let a label *grant* access; the ACL (and, for export control, the mirrored
group) is the sole grant path.

---

## §4 — Compliance-map row(s) (declare + inherit)

Manufacturing **inherits** existing rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain);
it does not re-derive controls. Evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | Manufacturing-specific evidence binding |
|--------|-----------------------------------|-----------------------------------------|
| **Export control** (ITAR 22 CFR 120–130 / EAR) | Isolated tier; region-pinned model pool; no-offshore-egress label; quarantine of unmappable sources; per-tenant DEK | Export-control containment (§1.2) is the *technical evidence* of compliance — an access log proves only vetted `ITAR-US-persons` CPIs, from US-region infrastructure, ever retrieved a controlled item; no offshore egress event exists |
| **Quality & product safety** (ISO 9001 / IATF 16949 / AS9100) | Append-only audit; immutable versioned knowledge; per-answer attribution | Every retrieval over an SPC/NCR/CAPA record is audited with `resource_id` + subject + model version → a quality investigation or recall is reproducible and attributable; reuses [Audit](../audit/00-audit-pack.md) append-only evidence |
| **Worker safety / EHS** (OSHA 29 CFR 1904 incident & SDS records) | Append-only audit; PII masking; least privilege | Incident narratives audited; injured-operator `pii` masked per query; SDS retrieval permission-gated to plant EHS scope |
| **SOX** (production data → COGS) | Append-only audit; least privilege; ≥7-yr retention | Inherited from [Finance](../finance/00-finance-pack.md) verbatim — yield/scrap/labor figures feeding cost accounting carry the same attribution and retention |
| **GDPR** (operator-shift PII) | Right-to-erasure + DSAR; PII masking; residency | `pii` masking proven per query on operator fields; an operator erasure proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4) |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Isolated tier + per-tenant DEK for export-controlled/trade-secret content |

**No new control was invented.** Manufacturing's compliance posture is a *selection and binding* of controls
the platform already operates. Export-compliance vetting (who is a US person) is a **source-side** control the
platform mirrors, not runs — see §1.2.

---

## §5 — Retrieval / answer eval set

The pack supplies (a) the **parsers** that make its content retrievable and (b) the **eval corpus** that
gates any model change through the [eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **Time-series telemetry windows** — a raw stream is downsampled/windowed into stable, timestamped,
  tag-labelled summaries (min/max/mean/excursions per interval) so a natural-language question ("did oven 7 run
  hot on the 2 pm shift?") matches a bounded chunk; a chunk never spans two assets with different ACLs
  (mixed-ACL invariant).
- **SPC / inspection tables** — serialized to a stable, header-aware row form (reuses the
  [SAP-table serialization](../finance/00-finance-pack.md) approach) so exact part/lot numbers match on the
  BM25 half; one measurement record per chunk.
- **BOM / routing** — one node/operation per chunk; a chunk never spans two org-unit ACLs.
- **Work instructions & CNC/NC programs** — parsed as controlled documents; export-control/trade-secret status
  drives the §2 labels; a program chunk never mixes a controlled and an uncontrolled revision.

**Eval set (grounding · refusal · pack task accuracy · the new negatives):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Author-less-data negative** | Telemetry with no native user-ACL is never served on a broad `internal` default — only via the inherited container ACL | **0 leaks** on the held-out cross-plant set (permission test) |
| **Export-control negative** | A non-US-person CPI never retrieves an ITAR/EAR-controlled drawing/CNC program via any prompt | **0 leaks**; **0 offshore-egress events** on controlled content |
| **Cross-plant containment** | Plant A principals never retrieve plant B line telemetry | **0 leaks** |
| **Numeric grounding** | Every measurement/yield/OEE figure in an answer traces to a cited chunk; no synthesized readings | 100% figures cited or the answer refuses |
| **Refuse-over-guess** | "What was line 3's scrap rate last shift?" with no accessible source → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated number | 0 fabrications on the no-access set |
| **OEE aggregate over permitted rows** | A plant-OEE rollup is computed **only** over rows the caller may read (filter-then-aggregate), never reconstructing a masked line | Pack-accuracy threshold; **0 leaks** — the [Reporting](../reporting/00-reporting-pack.md) invariant reused |

A model that regresses on the **author-less-data**, **export-control**, or **cross-plant** negatives cannot be
promoted for the Manufacturing tenant — the same gate shape as the connector conformance canary, applied to
the model.

---

## §6 — Optional additive API `pack` hint

Manufacturing callers **may** pass `"pack": "manufacturing"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (prefer the
Manufacturing eval-tuned model, bias retrieval toward MES/PLM/SPC sources). It is strictly additive:

- **Identity still governs.** The hint never widens access — a non-US-person who passes `pack:"manufacturing"`
  but is not in an export-controlled item's `ITAR-US-persons` group sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an authorization input.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the hint only
  optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"manufacturing"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7).

---

## Trade-offs

- **Inherit the container ACL vs. a telemetry-native ACL.** Machine data *inherits* the asset-container's grant
  rather than carrying its own. This trades a dependency on the asset registry / MES being faithfully mapped
  (bad mapping → quarantine, not a leak) for the correct guarantee: the platform never invents a grant for
  author-less content, and "no ACL" can never mean "open."
- **Mirror the export-control group vs. compute US-person eligibility.** The platform *mirrors* the
  source-vetted `ITAR-US-persons` group rather than deriving nationality itself. This trades a slightly looser
  coupling (a newly-vetted person becomes visible only after the group re-syncs, within the freshness SLA) for
  the correct guarantee: the platform never becomes the authority on export eligibility — the same "mirror,
  never compute" discipline that keeps Legal from computing privilege waiver.
- **Quarantine over best-effort on unresolvable assets / ambiguous control status.** Telemetry whose asset ACL
  or export status can't be read to `exact` is unavailable on the shared path rather than approximately
  available. Trades recall for a hard no-leak/no-violation guarantee — the correct trade (R1).
- **Isolated + region-pinned pool for controlled content vs. cost.** Export-controlled and trade-secret content
  lifts to Isolated + a US-region model pool, more expensive than Standard. Accepted: an ITAR violation is a
  criminal-liability event and a leaked process recipe is a competitive catastrophe, not a UX blemish.
- **Read-plane only vs. shop-floor actuation.** The platform answers questions about the floor; it never
  commands it. This forgoes a "close the loop / auto-adjust setpoint" capability in exchange for never owning a
  safety-critical write plane — the correct trade for physical equipment.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Treat author-less telemetry as an ownerless item class with a default `internal` grant** | Rejected: a silent floor-loosen (the SharePoint over-grant through a new door). Machine data inherits the asset-container ACL; unresolvable → quarantine (§1.1). |
| **Add a `nationality` / `us_person` attribute to the subject and a clause to `is_permitted`** | Rejected: a new principal attribute *and* a new predicate = a floor change. Export eligibility is a source-vetted group the platform mirrors; the ordinary allow-set walls non-members (§1.2). |
| **Let the platform determine US-person status from an HR nationality field** | Rejected *today* — it would make the platform the authority on export eligibility (compute, not mirror). Named as the one future ADR below. |
| **Have the platform issue machine commands / release work orders / adjust setpoints** | Rejected: introduces a safety-critical actuation plane the bet forbids. Manufacturing is read-plane-mirror ([Audit](../audit/00-audit-pack.md)). |
| **A Manufacturing-specific (time-series) retrieval pipeline** | Rejected: a horizontal change. Manufacturing rides the hybrid permission-filtered pipeline unchanged; only parsers + eval + two labels are pack-local. |
| **Loosen masking for "any plant engineer" on operator PII** | Rejected: loosening a floor. Engineers who need raw operator PII get an explicit ACL grant; the label default stays masked. |

## Future scalability

- **A new plant / line / MES source** = a new §1 row + fixtures; no pipeline change. The author-less-data and
  cross-plant fixtures are reused verbatim as the acceptance gate.
- **Supply-chain / logistics packs** are now closer to fill-in-the-blank: telemetry-style tracking events reuse
  Manufacturing's container-inherited-ACL rule; supplier collaboration reuses [Procurement](../procurement/00-procurement-pack.md)'s
  external-principal handling; the operational flows ride the read-plane-mirror boundary unchanged.
- **A CRM / customer-data pack** now inherits both the external-principal handling (Procurement) and the
  aggregate-over-mixed-ACL rule (Reporting), leaving little new to prove.
- **The one named future ADR:** *the platform itself determining export-control eligibility* (computing who is a
  US person from a nationality/citizenship field, rather than mirroring a source-vetted group) — e.g. if a tenant
  has no PLM system of record for the `ITAR-US-persons` group. That would introduce a computed
  eligibility/attribute predicate into the decision function and is therefore a **horizontal decision**,
  deliberately out of scope today and quarantined behind "mirror the source." This is Manufacturing's analogue of
  Procurement's named future ADR (a platform-computed unseal timer) and Reporting's (serving a total over
  unreadable rows).

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §2.1 (CPI), §3 (the one predicate), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Document Intelligence pack (inherit-source-ACL, no-ACL ≠ open)](../document-intelligence/00-document-intelligence-pack.md) · [Procurement pack (external principal, mirror-not-compute)](../procurement/00-procurement-pack.md) · [Legal pack (mirror-not-compute)](../legal/00-legal-pack.md) · [Audit pack (read-plane-mirror boundary)](../audit/00-audit-pack.md) · [SAP pack (PP/PM three-band fidelity)](../sap/00-sap-pack.md) · [Reporting pack (filter-then-aggregate)](../reporting/00-reporting-pack.md)
- [Metadata §4 (classification registry), §9 (additive node kinds)](../../metadata/00-catalog-and-lineage.md) · [Governance §4 (label matrix), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, parsers)](../../rag/00-retrieval-pipeline.md) · [API §5, §11](../../api/00-api-surface.md)
