# Domain Packs

A **domain pack** is the *only* thing that changes when AI Studio onboards a new
knowledge domain — Finance, HR, Legal, Audit, Knowledge Management, SAP, SharePoint,
Email, Document Intelligence, Reporting. This is the operational form of the founding
bet stated in [Vision §2–§3](../architecture/00-vision-and-principles.md) and now
ratified as a contract in [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md):

> **A new domain is delivered by configuration and content, not by re-architecting the
> platform.** A pack is *additive data + policy* projected onto the ten already-Seeded
> horizontal surfaces. It **may only tighten**; it can never loosen a platform floor,
> add a hot-path component, or change a horizontal contract.

If a pack *cannot* be expressed within this contract, that inability is the headline
finding — it means a horizontal surface is genuinely incomplete, and the fix is a
horizontal ADR, **not** a pack-local workaround. (See "The falsifiability rule" below.)

---

## The pack-spec skeleton (the six-part contract)

Every pack document is the same six sections, in the same order. Each section plugs a
pack's specifics into **one** horizontal extension point that already exists — the pack
author fills blanks, never designs mechanism.

| # | Section | Plugs into (the already-built extension point) | Direction |
|:-:|---------|-----------------------------------------------|-----------|
| **1** | **Sources & `map_acl` fidelity** | The six-method [`Connector` port](../workers/01-connector-framework.md) + the [per-source ACL mapping](../permissions/00-authorization-model.md#5-per-source-acl-mapping-the-connectors-hardest-job) rules + the [conformance suite](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate) | declares fidelity target + fixtures |
| **2** | **Classification-registry values** | The registered extension points of the [closed label schema](../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3) — `restricted:<class>`, `pii_class:<type>`, `matter:<id>` | registers vocabulary |
| **3** | **Label→action *tighten* deltas** | The platform [label→action matrix](../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen) (tenants may tighten, never loosen) | tightens policy |
| **4** | **Compliance-map row(s)** | The [Governance control map](../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain) (a pack *inherits* rows, declares regimes) | declares + inherits |
| **5** | **Retrieval / answer eval set** | The [model eval-before-promotion gate](../governance/00-governance-and-audit.md#8-g6--model-governance) + the [verifier contract](../rag/00-retrieval-pipeline.md) + per-content-type parsers | supplies eval corpus |
| **6** | **Optional additive API `pack` hint** | The [additive versioning rule](../api/00-api-surface.md#11-versioning--deprecation-policy-a7) (`"pack": "..."` is a hint; identity still governs) | additive only |

A pack MUST also carry a short **§0 "Horizontal-change ledger"** that lists, explicitly,
every horizontal document it touched — the expected value is **"none, all additive"**.
That ledger is the proof of the bet, made auditable per pack.

### The falsifiability rule

The skeleton is designed to be **falsifiable**. If, while writing §1–§6, a pack would
force *any* of the following, stop and raise a horizontal ADR instead of hacking around it:

- a **new hot-path component** (Governance/§2 says packs add none);
- a **loosened** platform floor (a widened label, a disabled ACL filter, a relaxed SLA);
- a **change to a horizontal contract** (a new required API field, a new predicate, a
  new store);
- an ACL fidelity that **cannot** reach `exact` on the shared path *and* cannot be
  quarantined (would mean the [confidence gate](../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation) is insufficient).

A pack that triggers this rule has found a real gap. That is a **success of the process**,
not a failure of the pack — it converts an unstated assumption into a tracked decision.

---

## Index

| Pack | Status | Primary sources | Hardest features it exercises |
|------|--------|-----------------|-------------------------------|
| [Finance](finance/00-finance-pack.md) | **Seeded (Cycle 11)** — the reference pack | SAP (FI/CO), ledgers, Excel, reporting DBs | Row/record-level SAP ACLs, `restricted:*`+`pii_class`+`legal_hold`, SOX compliance row, SAP-table parsers |
| [HR](hr/00-hr-pack.md) | **Seeded (Cycle 12)** — the 2nd data point | Workday/SAP HCM, SharePoint, email | Employee-self-scoped ACLs, `pii_class:health` (Art. 9), GDPR-primary erasure vs. statutory retention |
| [Legal](legal/00-legal-pack.md) | **Seeded (Cycle 13)** — 1st novel-concept test | DMS (iManage/NetDocuments), SharePoint, email, matter stores | Attorney-client **privilege + waiver** (falsifiability test — held), **ethical walls = deny-wins**, `matter:<id>` holds, clause chunking |
| [Audit](audit/00-audit-pack.md) | **Seeded (Cycle 14)** — 1st combinatorial test | GRC/audit-mgmt (AuditBoard/Workiva/SAP GRC), SAP, DMS, the platform's own S7 trail | **Segregation-of-duties** (falsifiability test — held; SoD prevention is *out of plane*, detection is a read), SOX/PCAOB inherited from Finance, `restricted:audit_workpaper`, append-only evidence |
| [Knowledge Mgmt](km/00-km-pack.md) | **Seeded (Cycle 15)** — 1st *inverse* (over-refusal) test | Confluence, SharePoint, wikis, portals | **High recall over broad `internal`** (falsifiability test — held; recall bought *within* the floors, never by loosening one), **first pack with empty §2 + §3** (zero new vocabulary, zero tighten), over-refusal eval headline |
| [SAP](sap/00-sap-pack.md) | **Seeded (Cycle 16)** — the 1st *source-shaped* pack | SAP FI/CO, MM, SD, HCM/SuccessFactors, BW/BI, GRC | **The canonical SAP `map_acl` reference** (resolves open Q#2's per-module sub-question) — the **three-band fidelity model** (A `exact` / B resolve-or-quarantine / C quarantine) proves *no SAP construct is neither resolvable nor quarantinable*; **2nd pack with empty §2 + §3** (a source carries no policy of its own) |
| [SharePoint](sharepoint/00-sharepoint-pack.md) | **Seeded (Cycle 17)** — the 2nd source-shaped pack (SAP's *mirror*) | SharePoint / OneDrive / M365 | **The canonical SharePoint `map_acl` reference** — the *inverse* falsifiability test: SAP's risk was *quarantining too much*, SharePoint's is a **silent *over*-grant**. Every sharing construct (broken inheritance, sharing links, **"anyone" links → flag-and-fail-closed, never silent public**, guests, dynamic groups, MIP) maps to `allow`/`deny`/flagged-grant/quarantine — no new principal category, no new predicate; **3rd pack with empty §2 + §3**; **no Band-C** (ACL is item-level) |
| [Email](email/00-email-pack.md) | **Seeded (Cycle 18)** — the 3rd & last source-shaped pack | Exchange / Outlook / M365 mail | **The canonical Email `map_acl` reference** — the *transport-vs-storage* falsifiability test: a message's ACL is its **mailbox owner + delegates**, never its transport audience. Every construct (mailbox owner, delegate, shared mailbox, Send-As, per-message thread ACL, **distribution-list membership → no grant**, To/Cc/Bcc → content-not-ACL) maps to `allow`/`deny`/quarantine — no new principal category, no new predicate; **4th pack with empty §2 + §3**; **no Band-C, no sharing-link surface** (shortest matrix) |
| [Document Intelligence](document-intelligence/00-document-intelligence-pack.md) | **Seeded (Cycle 19)** — 1st *derived-content* test; 1st non-empty §2 since Legal | OCR/scans, table/entity/form extraction over other packs' content | **Platform-*derived* content** (falsifiability test — held): a derived artifact **never carries an ACL of its own** — it *inherits* the source Item ACL via lineage (multi-source merge = intersection/split/quarantine, **never union**); a **derived label** may only **tighten**, is **fail-closed** on low classifier confidence, and is **provenance-stamped** (`label_source: derived`) — a wrong derivation costs *availability, never safety*. The one Metadata touch (`LineageNode.kind` for a secondary derived index) is the additive node-kind growth [Metadata §9](../metadata/00-catalog-and-lineage.md) already named — not a contract change; unresolvable narrowing sub-Items ride the existing `approximate → deny + quarantine` hatch |
| [Reporting](reporting/00-reporting-pack.md) | **Seeded (Cycle 20)** — 1st *aggregation* test; **the pack that completes the domain-pack surface** | SAP BW/BI, Power BI/Tableau/Qlik, Finance reporting DBs, SharePoint-hosted reports | **The *aggregate* over mixed-authorization rows** (falsifiability test — held): a report is a *derived artifact* reusing DocIntel's inherit-source-ACL rule + SAP BW/Finance fidelity verbatim. The sharp new corner is **arithmetic inference** — a total can reconstruct a masked row (small-cell/differencing). Disarmed **by construction, not by a disclosure-control engine**: the platform **filters rows before aggregating**, so a served total is always a function of rows the caller could read individually; a pre-materialized report carries the source's own ACL (**Band-A**); a cross-source rollup carries the **intersection** (never union); an unresolvable-contributor aggregate is **quarantined**. **5th pack with empty §2 + §3** (a report *presents* the riding domain's policy, owns none). The one future ADR is named: *serving* a total over rows the caller can't read (statistical disclosure control) — out of scope, quarantined today |

**The domain-pack surface is complete (Cycle 20).** All ten planned packs are Seeded —
six concept-shaped (Finance/HR/Legal/Audit/KM/Document Intelligence), three source-shaped
(SAP/SharePoint/Email), and Reporting (aggregation) — every one with a `§0 = none, all
additive` ledger. The founding bet is now proven across policy concepts, source `map_acl`
fidelity, platform-derived content, and arithmetic aggregation. A **new** domain
(Procurement, Manufacturing, CRM, …) is a fill-in-the-blank pack against this skeleton,
inheriting the Finance pack's structure verbatim — not a redesign.
