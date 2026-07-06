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
| Legal | Backlog | DMS, SharePoint, email, matter stores | `legal_hold`/`matter:<id>`, clause chunking, privilege |
| Audit | Backlog | Finance + Legal sources, workpapers | SOX + segregation-of-duties, append-only evidence |
| Knowledge Mgmt | Backlog | Confluence, SharePoint, wikis | Broad `internal`, low restriction, high recall |
| SAP / SharePoint / Email | Backlog | (source-shaped packs) | Reuse Finance/HR connector fidelity work |

Each backlog pack is **fill-in-the-blank** against this skeleton and inherits the
Finance pack's structure verbatim.
