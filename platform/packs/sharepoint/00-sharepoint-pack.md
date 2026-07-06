# Domain Pack #7 — SharePoint / OneDrive (the *fidelity-friendly* source pack)

> **The second source-shaped pack — and SAP's mirror image.** [SAP](../sap/00-sap-pack.md)
> was the hardest source: **no document ACL**, so its whole story was *quarantine* (can
> everything sub-`exact` be denied-and-quarantined?). SharePoint is the **easiest** source:
> it carries a **rich item-level document ACL**, so almost everything is `exact`. That flips
> the falsifiability question. SAP's feared failure was **quarantining too much** (an
> availability cost paid for safety). SharePoint's feared failure is the **opposite and more
> dangerous one — a silent *over*-grant**: a sharing link, a guest principal, or a broken
> inheritance that quietly widens access *beyond* what the canonical `{allow, deny, labels,
> confidence}` model can faithfully represent. This document is the **canonical SharePoint /
> OneDrive `map_acl` reference** that Finance, HR, Legal, Audit and KM all cite instead of
> re-deriving — every one of them already reads SharePoint, in restricted *and* open mode.

- **Cycle:** 17 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** *none of its own* — SharePoint **inherits** whatever regime the domain riding on it demands (SOX for Finance-on-SharePoint, GDPR for HR-on-SharePoint, privilege for Legal-on-SharePoint, ISO 27001 / SOC 2 baseline for all)
- **Isolation tier (default):** inherited from the riding domain; an item whose item-level permissions could not be fully read always lands on the [Isolated/quarantine tier](../../storage/00-storage-architecture.md) regardless

---

## Why SharePoint, and why it is the *inverse* falsifiability test

The five concept packs asked *"does a new **policy** concept fit?"* SAP asked *"can the
**hardest source's** entire authorization model be served-or-quarantined with no fourth
case?"* SharePoint asks the mirror question:

> **Can the *most permissive* source's every sharing construct — item permissions, broken
> inheritance, sharing links, "anyone" links, external/guest principals, MIP labels, dynamic
> groups — be mapped to the canonical model *without ever producing a silent over-grant*,
> and without inventing a new principal category or a new predicate?**

SharePoint is the right source to ask this of because its richness is exactly what tempts a
silent widening:

- **Its ACL is genuinely item-level** ([Permissions §5.1](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365)):
  broken inheritance, unique permissions, sharing links, sensitivity labels. Rich fidelity is
  a *gift* (mostly `exact`) but a *trap* (the sharing surface can widen access in ways a naive
  connector would flatten into "public").
- **It is the most-reused *document* source in the pack set.** Finance/HR/Legal/Audit/KM all
  read SharePoint. Until now that fidelity was asserted **five times, ad hoc**. Cycle 17
  consolidates it into **one canonical §1** — a DRY win, exactly as SAP did for its module set.

If any SharePoint sharing construct produced access the canonical model could not represent
**without either a new principal type or a silent public grant**, that is a real **R1/R4**
gap → a horizontal Permissions ADR, **not** a pack-local hack (the
[falsifiability rule](../README.md#the-falsifiability-rule)). **None did** — every construct
maps to an explicit grant, a deny, a flagged grant, or a quarantine (§1). See §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by SharePoint? | What SharePoint did instead |
|--------------------|:------------------------------:|-----------------------------|
| Permissions (canonical model, `map_acl`) | **None** | **Consolidated** the existing [§5.1 SharePoint rules](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365) into a **construct-by-construct fidelity matrix** (§1). Every construct maps to an explicit `allow`, a `deny` (broken-inheritance removal), a **flagged** grant (`sharing:anonymous` — never a silent public grant), or a quarantine (permissions not fully read / unresolvable dynamic group). No new principal category, no new predicate |
| Metadata (label schema, catalog, lineage) | **None** | **§2 is empty.** SharePoint *maps* MIP sensitivity labels into `labels.sensitivity`, but the label **values** are registered by the *domain* riding on it (Finance's `restricted:mnpi`, Legal's `restricted:privileged`), never by the source pack. SharePoint is a label **carrier/mapper**, not a label **owner** |
| Governance (label matrix, SLA, retention) | **None** | **§3 is empty.** A source tightens no policy; the riding domain's tighten-deltas apply to its SharePoint-sourced content unchanged. The "anyone"-link flag is *surfaced* to governance, not *acted on* by the source pack |
| RAG (chunking, hybrid, verifier) | **None** | Reuses the **existing** structure-aware document/Office-file parsers behind the per-content-type seam; the **mixed-ACL invariant** ([RAG §2.2](../../rag/00-retrieval-pipeline.md)) already handles per-item permission breaks; supplied an over-grant-focused eval set |
| Storage / Workers / API / Deployment | **None** | Rides the *existing* staged DAG; SharePoint/Graph **change notifications + delta queries** are the *existing* `subscribe_changes` feed ([Connector §4](../../workers/01-connector-framework.md)); a not-fully-read item = the *existing* quarantine tier; `pack:"sharepoint"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** SharePoint is the **third pack with an empty
§2 and §3** (after [KM](../km/00-km-pack.md) and [SAP](../sap/00-sap-pack.md)) — for the same
structural reason as SAP: **a source-shaped pack carries no policy of its own.** Per
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit adds a
"required" row, that edit needs a horizontal ADR.

---

## The over-grant analysis — the falsifiability test (the point of this cycle)

This is the section a reviewer should read first; it is the whole reason to seed SharePoint.

**The claim under test.** *"Every SharePoint sharing construct is representable in the
canonical model as an explicit `allow`, an explicit `deny`, a **flagged** grant that is never
a silent public grant, or a sub-`exact` mapping the confidence gate quarantines — there is no
construct that silently widens access beyond the canonical model, and none that needs a new
principal category or a new predicate."*

Where a naive connector would leak, and why the canonical model does not:

### 1. Broken inheritance → the *effective* item ACL, not the library's
A document with **unique permissions** must not be assumed to inherit its library's ACL
([Permissions §5.1](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365),
[§3 evaluation table "Broken inheritance"](../../permissions/00-authorization-model.md)). The
connector resolves the **effective** item-level ACL; a chunk records that, per the
[mixed-ACL invariant](../../rag/00-retrieval-pipeline.md). A break that *removes* access is an
explicit `deny` (deny-wins). **Faithful — the item level is exactly where SharePoint's ACL
lives, so there is no sub-Item Band-C case at all** (SharePoint's structural advantage over
SAP, and the reason this pack is shorter).

### 2. Sharing links → explicit grants, "anyone" links → a *flagged* grant, never public
This is the construct most likely to force a silent widening. Three sub-cases, all additive:
- **Specific-people links** → explicit `allow` grants to the named principals' CPIs. `exact`.
- **Org-wide ("people in the organization") links** → an `allow` to the tenant's **all-org**
  principal (an ordinary, well-known CPI). This *is* a real grant and is served as one — the
  content is `internal`-visible by the org's own decision. `exact`.
- **"Anyone" / anonymous links** → an `allow` to a synthetic **`sharing:anonymous-link:<id>`
  principal**, carrying a **`sharing:anonymous` policy flag**, and — crucially — **the
  anonymous principal is *not* silently added to an arbitrary authenticated caller's effective
  set.** The [§5.1 rule](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365)
  is enforced verbatim: *an "anyone" link on a restricted item is a policy flag, not a silent
  public grant.* The flag is surfaced to governance / the riding domain (who may treat the item
  as effectively public, or review it); the **source pack defaults fail-closed** — absence of a
  decision means the anonymous grant does not widen access. **No new principal *category* (an
  anonymous principal is still a CPI in the tenant namespace); no silent grant.**

### 3. External / guest (B2B) principals → ordinary tenant-namespaced CPIs
An Entra **guest** (`#EXT#`) user is a real principal in the *host* tenant's directory with a
stable objectId. It maps to an ordinary `<tenant>:aad:user:<objectId>` CPI
([Permissions §4.1](../../permissions/00-authorization-model.md#41-inputs)) — inside the host
tenant's namespace, so **R4 cross-tenant isolation is unaffected** (a guest of tenant A is a
principal *of tenant A*, never a bridge to tenant B). `exact`. No new principal category.

### 4. Dynamic / computed membership (Azure AD dynamic groups) → resolve-or-quarantine
An Entra **dynamic group** (rule-based membership) is computed, not static — structurally
identical to [SAP's Band B](../sap/00-sap-pack.md#band-b--structural--dynamic-authorization--resolve-or-quarantine):
pre-resolve to a principal set kept fresh by `list_principal_changes` on the group-change
signal → `exact` within the freshness SLA; if not stably resolvable → `approximate → deny +
quarantine`. **The same mechanism, reused verbatim — no new machinery.**

### 5. Permissions not fully readable → quarantine (the one hard floor)
`acl_confidence = exact` **only when item-level permissions were fully read**
([Permissions §5.1](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365)).
Graph throttling, a permissions API gap, or an unresolvable principal ⇒ `approximate` ⇒
**denied on the shared path + quarantined** ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
A partially-read ACL is never rounded up to `exact`.

**Why there is no silent over-grant, and no new predicate.** Every SharePoint construct is one
of: (a) an explicit `allow` to a real CPI → served; (b) an explicit `deny` (inheritance-break
removal) → deny-wins; (c) an "anyone" link → a *flagged* grant that fail-closes by default,
never silently public; (d) a computed group → resolve-or-quarantine (Band B); or (e) an
unreadable ACL → quarantine. The one construct that *looks* like it needs a "public" concept —
the "anyone" link — is handled by **flag-and-fail-closed**, so the canonical model needs
**no anonymous/public predicate and no new principal category.** The rule was armed against a
*widening* and did **not** fire.

---

## §1 — Sources & `map_acl` fidelity (the canonical SharePoint reference)

The construct-by-construct fidelity matrix. This table is what other packs cite instead of
re-deriving SharePoint mapping. **Max `acl_confidence`** is what the connector may declare per
[Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract).

| Source construct | Principal / grant mapping | Outcome | Max `acl_confidence` |
|------------------|---------------------------|---------|:--------------------:|
| **Item permission** (inherited or unique) | Entra user/group → CPI by **objectId**; effective item-level ACL | `allow[]` | `exact` (item perms fully read) |
| **Broken inheritance removing access** | The removed principal | `deny[]` (deny-wins) | `exact` |
| **M365-group grant** | Expand M365 group → security-group members → CPIs | `allow[]` | `exact` |
| **Specific-people sharing link** | Named recipients → CPIs | `allow[]` | `exact` |
| **Org-wide sharing link** | Tenant all-org principal | `allow[]` (a real internal grant) | `exact` |
| **"Anyone" / anonymous link** | `sharing:anonymous-link:<id>` synthetic CPI **+ `sharing:anonymous` flag** | `allow[]` **flagged**, fail-closed by default — **never** a silent public grant | `exact` (mapping faithful; serving governed by policy flag) |
| **External / guest (`#EXT#`) principal** | `<tenant>:aad:user:<objectId>` in the **host** tenant namespace | `allow[]` | `exact` |
| **Azure AD dynamic group** | Pre-evaluated principal set, re-synced on group-change | `allow[]` if resolvable within SLA; else deny + quarantine | `exact` within SLA; else **quarantine** |
| **MIP sensitivity label** | → `labels.sensitivity` (value owned by riding domain, §2) | label carried, not authored | n/a (label channel) |
| **Item whose permissions could not be fully read** | — | `approximate` → deny + quarantine | `approximate` → quarantine |

**No Band-C (sub-Item) row.** Unlike SAP, SharePoint's ACL never lives *below* the
ACL-carrying [Item](../../metadata/00-catalog-and-lineage.md#3-the-catalog-schema-m1) — a
document *is* the unit that carries the permission. That absence is the structural reason this
matrix is shorter than SAP's three-band model.

**Conformance fixtures (the production gate).** The SharePoint connector ships a fixture set
for the [permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate),
weighted toward the **over-grant** failure mode (the source-shaped analogue of SAP's
quarantine-weighted set):

1. **Broken-inheritance negative** — a doc with unique permissions removing a user is **not**
   served to that user even though the library ACL would allow them (deny-wins on the effective ACL).
2. **"Anyone"-link non-widening** — an item shared via an "anyone" link is **not** silently
   served to an arbitrary authenticated caller who is not otherwise entitled; the item carries
   the `sharing:anonymous` flag and the anonymous principal does **not** enter the caller's
   effective set by default (fail-closed).
3. **Guest isolation (R4)** — a guest principal of tenant A is never treated as a principal of
   tenant B; a cross-tenant query returns nothing.
4. **Dynamic-group freshness (Band B)** — removing a user from a dynamic group's rule scope
   revokes access **within the freshness SLA** ([Governance §3.1](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table)),
   verified via query-time principal precedence.
5. **Not-fully-read quarantine** — an item whose permissions could not be fully enumerated is
   **quarantined**, never served at `exact`.
6. **Open-mode positive** — a space/site member **can** read an `internal` page they are
   entitled to (the pack must not *over*-restrict either — the [KM inverse](../km/00-km-pack.md) lens).
7. **Revocation** — removing a user's Entra group membership revokes access within the SLA,
   independent of chunk re-tag.

---

## §2 — Classification-registry values

**Empty — by design.** SharePoint *carries* MIP sensitivity labels into `labels.sensitivity`,
but the **values** those labels map to (`confidential`, `restricted:mnpi`,
`restricted:privileged`, …) are registered by the **domain pack riding on it**
([Finance §2](../finance/00-finance-pack.md), [Legal §2](../legal/00-legal-pack.md)) and by
the platform classification rules. A source pack that invented its own vocabulary would be
claiming policy that isn't the source's to hold. SharePoint touches the
[classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
only as a **carrier/mapper** of the riding domain's registered values — the empty table is the
evidence. (Contrast SAP, which carries *no* native label at all; SharePoint carries the label
but does not *own* it.)

---

## §3 — Label→action *tighten* deltas

**Empty — by design.** A source tightens no policy. SharePoint-sourced content is governed by
the tighten-deltas of the **riding domain** ([Finance §3](../finance/00-finance-pack.md),
[HR §3](../hr/00-hr-pack.md), [Legal §3](../legal/00-legal-pack.md)) applied to its labels
unchanged. The one thing SharePoint *does* enforce beyond a plain grant — the **`sharing:anonymous`
flag** and **quarantine of not-fully-read items** — are the **existing** confidence-gate and
policy-flag floors, not new tighten rules. The
[label-can-only-subtract invariant](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)
is preserved trivially because SharePoint adds no label rule of its own.

---

## §4 — Compliance-map row(s) (declare + inherit)

SharePoint declares **no regime of its own**; it **inherits** the regime of whatever domain
rides on it, and contributes **one source-specific evidence binding** that strengthens every
inherited row: a SharePoint-sourced answer's retrieval audit event carries the **site/library
+ item objectId + `source_item_version` (Graph eTag/driveItem version)** and, where present,
the **`sharing:anonymous` flag**, so the answer is reproducible and any over-share risk is
attributable to a specific item state.

| Regime | Inherited from (riding domain) | SharePoint-specific evidence binding |
|--------|-------------------------------|--------------------------------------|
| **SOX** | [Finance](../finance/00-finance-pack.md) | A cited SharePoint item traces to its objectId + version; sharing-link flags are audited |
| **GDPR** | [HR](../hr/00-hr-pack.md) | `pii_class:*` masking proven per query; erasure completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4); guest-principal access is auditable |
| **Attorney-client privilege** | [Legal](../legal/00-legal-pack.md) | Ethical-wall `deny` grants honored deny-wins; MIP `restricted:privileged` label carried into `labels.sensitivity` |
| **ISO 27001 / SOC 2** | any | Isolated tier + per-tenant DEK; read-only Graph credential, per-tenant, per-connector ([Connector §7](../../workers/01-connector-framework.md)); anonymous-link flag = a reportable exposure control |

**No new control was invented.** SharePoint's compliance posture is entirely *inherited* — its
one native contribution is **evidence** (item/version/sharing-flag), not policy.

---

## §5 — Retrieval / answer eval set (the reusable SharePoint assets)

Where a source-shaped pack contributes reusable engineering assets — the **parsers** and the
**over-grant eval set** — rather than policy.

**Parsers (existing per-content-type seam — [RAG](../../rag/00-retrieval-pipeline.md), no new parser):**
- **Office documents** (Word/Excel/PowerPoint), PDF, `.aspx`/wiki pages, list items — all
  ride the **existing** structure-aware parsers; SharePoint contributes fixtures, not a new
  parser (unlike SAP, which promoted the table-serialization parser). The **mixed-ACL
  invariant** applies: a chunk never spans two items with different effective ACLs (already
  the pipeline default — SharePoint's per-item permission breaks are exactly what it guards).

**Eval set (the source-shaped headline: *no silent over-grant*):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Over-grant negatives** | No "anyone"-link, guest, or broken-inheritance construct silently widens access to an unentitled caller | **0** silent over-grants |
| **Broken-inheritance correctness** | The *effective* item ACL is enforced, not the library's | 100% effective-ACL match |
| **Dynamic-group freshness (Band B)** | A membership change revokes access within SLA | 0 stale grants past SLA |
| **Not-fully-read quarantine** | An item with unreadable perms is quarantined, never served at `exact` | 0 approximate items served |
| **Over-refusal / recall** ([KM lens](../km/00-km-pack.md)) | An entitled caller *does* get the `internal` content they may see | 0 false refusals on entitled content |
| **Grounding + citation** | Every answer cites the SharePoint item + version it came from | 100% cited or refuse |

A model or connector version that regresses on **over-grant negatives** cannot be promoted for
any SharePoint-sourced tenant — the same gate shape as the connector conformance canary,
applied to the *widening* failure mode.

---

## §6 — Optional additive API `pack` hint

SharePoint callers **may** pass `"pack": "sharepoint"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(bias retrieval toward SharePoint sources, prefer the SharePoint-tuned eval profile). Like SAP,
it is even more purely optional than a domain pack's hint, because **SharePoint is a source,
not a domain**: a caller almost always asks *as Finance*, *as HR* or *as Legal* and the
SharePoint-sourcing is incidental. The hint is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes
  `pack:"sharepoint"` but holds no grants sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). In particular the hint
  **never** activates an "anyone"-link grant.
- **Omitting it is valid.** The platform infers SharePoint context from the accessible sources.
- **Not a version event** — [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7).

---

## Trade-offs

- **Flag-and-fail-closed on "anyone" links vs. best-effort availability.** Refusing to treat an
  "anyone" link as a silent public grant means some content an org *did* intend to share
  broadly is unavailable to an arbitrary caller until governance acts on the flag. This trades
  recall for a hard no-silent-over-grant guarantee — the correct trade (**R4/R1**), and the
  inverse of SAP's quarantine trade.
- **Item-level permission resolution cost.** Reading effective item-level ACLs (not assuming
  library inheritance) is more Graph calls and more ingestion work than trusting the library
  ACL. Accepted: assuming inheritance is precisely the silent-over-grant bug this pack exists
  to prevent.
- **Dynamic-group point-in-time resolution vs. staleness.** Identical trade to SAP Band B —
  pre-evaluation buys `exact` shared-path serving, bound to the freshness SLA; query-time
  principal precedence backstops revocation independent of the re-eval.
- **A canonical source pack vs. per-pack SharePoint notes.** Consolidating fidelity here means
  Finance/HR/Legal/Audit/KM cite one reference instead of restating it — a DRY win, at the cost
  of one more cross-pack link to keep consistent.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Treat an "anyone" link as a `public`-label grant** | Rejected: silently widening a restricted item to everyone is exactly the R4/R1 over-grant leak. The link becomes a *flagged* grant that fail-closes by default; governance decides, not the source pack. |
| **Trust library inheritance to save Graph calls** | Rejected: broken inheritance is common in SharePoint; assuming it is the classic over-share bug. The connector resolves the *effective* item ACL. |
| **Add an anonymous/public principal category to the canonical model** | Rejected: a horizontal predicate change. An anonymous link maps to an ordinary synthetic CPI + a policy flag — no new category needed. |
| **Register MIP sensitivity vocabulary in §2** | Rejected: SharePoint *carries* MIP labels but does not *own* their values; the riding domain registers them. A source pack claiming label policy is a category error (same rule as SAP). |
| **A dedicated SharePoint retrieval pipeline** | Rejected: a horizontal change (the thing the bet forbids). SharePoint rides the hybrid permission-filtered pipeline and existing parsers unchanged; only the fidelity fixtures + eval set are pack-local. |

## Future scalability

- **A new M365 surface** (Teams messages, Loop, Planner, Lists) = a new §1 matrix row for its
  ACL construct + fixtures; no pipeline change. The over-grant analysis already classifies each
  (a Teams channel grant is an ordinary `allow`; a Teams "anyone" link reuses the flag).
- **A new sharing construct** (a future Graph sharing type) = a new matrix row mapped to
  `allow` / `deny` / flagged-grant / quarantine; the four outcomes are exhaustive by
  construction.
- **Email** (Cycle 18) is now the **last source pack** — per-message ACL, delegates, shared
  mailboxes (already exercised via HR/Legal/Audit). It is even *simpler* than SharePoint: a
  message's ACL is its mailbox owner + explicit delegates, with no sharing-link surface, so its
  pack will be shorter still.
- **The one case that would force a horizontal ADR** — a SharePoint sharing construct that
  cannot be mapped to an explicit grant, a deny, a flagged grant, or a quarantine *without*
  silently widening access — is now named explicitly; none found across item perms, broken
  inheritance, sharing links, "anyone" links, guests, dynamic groups, or MIP labels.

## Related
- [Pack skeleton & the falsifiability rule](../README.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [SAP pack — the first source-shaped pack (SharePoint's mirror)](../sap/00-sap-pack.md)
- [Permissions §5.1 (SharePoint/OneDrive), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Connector §2 (`map_acl`), §4 (change notifications/delta), §7 (least-privilege credential)](../../workers/01-connector-framework.md)
- Packs that ride this one: [Finance](../finance/00-finance-pack.md) · [HR](../hr/00-hr-pack.md) · [Legal](../legal/00-legal-pack.md) · [Audit](../audit/00-audit-pack.md) · [KM](../km/00-km-pack.md)
