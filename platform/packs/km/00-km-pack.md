# Domain Pack #5 — Knowledge Management (the inverse stress: broad `internal`, high recall)

> **The fifth data point — and the first pack that stresses the platform from the
> *opposite* direction.** Finance, HR, Legal, and Audit all interrogated one corner:
> *"does the platform correctly **refuse**?"* — over-sharing is a safety bug, and every
> pack so far armed the fail-closed machinery against it. KM deliberately inverts the
> question. Its content is broadly `internal`, lightly restricted, and read by many; the
> feared failure mode is not *over-share* but ***over-refuse*** — does the pipeline, tuned
> on four restrictive packs, now leave *accessible* open content **unfound** or
> **needlessly masked**? The sharp question the [skeleton's falsifiability
> rule](../README.md#the-falsifiability-rule) exists to catch is: *to maximize recall on
> open content, must the pack **loosen** a platform floor — widen the default label, relax
> the verifier's grounding bar, or add an unfiltered "list mode"? If yes, that is a real
> horizontal gap → an ADR. If the recall is instead recoverable **entirely within the
> existing floors**, the platform's low-restriction defaults are proven correctly
> calibrated.* **They are. KM tightens nothing and loosens nothing — the first pack whose
> §0 ledger is empty on *both* sides. See §0 and the "Over-refusal" analysis below — no
> horizontal change.**

- **Cycle:** 15 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — KM fits the existing contract; had high recall *required* loosening a floor, this pack would have raised a RAG/Governance/Permissions ADR, which is the process working)
- **Regimes declared:** ISO 27001 / SOC 2 (information handling), GDPR (incidental PII in free-text content) — a deliberately *light* footprint; KM inherits, invents nothing
- **Isolation tier (default):** Shared ([Storage §5](../../storage/00-storage-architecture.md)) — low blast radius (`internal`, no `restricted:*` by default); a KM sub-tenant hosting confidential engineering runbooks may graduate up, a placement decision not a redesign

---

## Why KM fifth (and why it is the right stress test)

n=1 (Finance) proved the mechanism *exists*; n=2 (HR) proved it *generalizes*; n=3 (Legal) proved
it survives a *genuinely novel concept*; n=4 (Audit) proved it survives the first *combinatorial*
concept. Each pushed the **restrictive** corner harder. KM earns its slot by being the first pack
that pushes the **opposite** corner — and it is the more important test than it looks, because a
platform that only ever gets *more* fail-closed eventually becomes useless:

- **Every prior pack could only *fail open* (leak).** KM is the first pack whose characteristic
  failure is *fail closed on content that should be served* — an **availability** bug, not a safety
  bug. A knowledge platform that refuses to surface a Confluence page the caller is plainly entitled
  to read has failed just as surely as one that leaks a payslip — but the four packs so far never
  exercised that direction. KM is the calibration check for the low-restriction end of the lattice.
- **KM is where the fail-closed defaults meet their natural counter-pressure.** The whole platform
  is built to *subtract* capability when unsure: unlabeled content defaults to `internal` not
  `public` ([Metadata M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)),
  the verifier *refuses* rather than guess ([RAG §7](../../rag/00-retrieval-pipeline.md)), retrieval
  runs on the *permitted* set only ([ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)).
  KM asks: with those defaults, does high-recall retrieval over broadly-accessible content still
  *work well*, or do the safety defaults accidentally suppress recall the caller is entitled to?
- **KM is the pack most tempted to loosen a floor — which is exactly why it is the test.** The
  naïve way to "improve KM recall" is to reach for a floor: make unlabeled content `public`, relax
  the grounding bar so the model answers from thin context, add an unfiltered "list everything"
  mode. **Each of those is the trap** the falsifiability rule is built to catch — and each is
  *unnecessary*, because the recall is recoverable with levers that already exist and never touch a
  floor (see the analysis). KM's value is proving the temptation is avoidable.
- **KM's content shape is the widest the platform has seen.** Wikis, portals, and collaboration
  spaces are free-text, densely cross-linked, heavily duplicated (the same policy restated in five
  pages), and often *stale*. That stresses chunking, dedup, and reranking — but all three are
  **existing RAG levers** ([RAG §2, §5, §6](../../rag/00-retrieval-pipeline.md)), tuned by config
  and an eval-selected model, never by a pipeline change.

If any of these forced a horizontal change, that would be the headline finding. **None did** —
see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by KM? | What KM did instead |
|--------------------|:----------------------:|---------------------|
| Permissions (canonical model, `map_acl`) | **None** | KM is **fidelity-friendly**: Confluence space membership + page restrictions and SharePoint site/page ACLs map to `allow`/`deny` grants that reach `exact` for the common case; a page whose restriction is only a *computed* audience rides the *existing* §9 `approximate → deny + quarantine` hatch. No new predicate; recall never comes from a *weaker* predicate |
| Metadata (label schema, catalog, lineage) | **None** | **Registered nothing.** KM is the **first pack to add zero classification vocabulary** — its content lives in the already-defined `public`/`internal` (and occasionally inherited `confidential`) values. It relies on the *existing* fail-closed default (unlabeled → `internal`, [M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)) rather than adding a new lax label |
| Governance (label matrix, SLA, retention) | **None** | **Tightened nothing; loosened nothing** — the **first pack with an empty §3 delta table**. It uses the platform's *existing* `public`/`internal` matrix rows ([Governance §4.1](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)) verbatim. The "widening/public" freshness row (best-effort) is *already* the right SLA for open content ([Governance §3](../../governance/00-governance-and-audit.md)) |
| RAG (chunking, hybrid, verifier) | **None** | Recall is raised with **existing, within-permission levers only**: query rewrite/expansion ([§4.3](../../rag/00-retrieval-pipeline.md)), hybrid-fusion + reranker/MMR tuning ([§5](../../rag/00-retrieval-pipeline.md)), dedup for restated content ([§6](../../rag/00-retrieval-pipeline.md)), and a **KM-eval-tuned model**. The verifier's grounding bar and no-context-honesty rule are **untouched** — over-refusal is fixed *upstream* of the verifier, never by lowering it |
| Storage / Workers / API / Deployment | **None** | Chose the *existing* Shared tier (low blast radius); wiki/portal parsing rides the *existing* staged DAG; connectors reuse SharePoint fidelity (Finance/HR/Legal) verbatim; API `pack:"km"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive — and, uniquely, additive with an *empty* §2 and
§3.** The headline: the pack most tempted to *loosen* a floor to buy recall needed to loosen
**nothing** — the recall was recoverable entirely inside the existing floors, and the low-restriction
defaults (`internal`-not-`public`, refuse-over-guess, filter-during-retrieval) turned out to be
**already correctly calibrated** for the open-content end. Per
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit to this pack
adds a "loosen" row (a widened default, a relaxed grounding bar, an unfiltered list mode), that edit
needs a horizontal ADR — and would be the process catching a real gap.

---

## Over-refusal — the falsifiability analysis (the reason this cycle exists)

This is the section a reviewer should read first; it is the whole point of choosing KM.

**The claim under test.** *"High recall over broadly-accessible open content is achievable without
loosening any platform floor. Over-refusal — the platform declining to surface content the caller
is entitled to read — is a **tuning/eval** problem solved **upstream, within** the existing floors,
never a **floor-loosening** problem."*

**The decomposition — separate the *cause* of over-refusal from the tempting *cure*, and reject
every cure that loosens a floor:**

A KM answer can be wrongly empty ("no accessible information") for exactly two reasons, and the
correct fix for each is a lever that already exists and touches no floor:

1. **The content was accessible but *not retrieved* (a recall miss).** The caller was entitled to
   the page, but hybrid search + rerank did not surface it into the assembled context, so the
   verifier honestly reported an empty context. **This is the real KM failure mode — and it lives
   entirely *before* the permission filter and the verifier.** The fix is the *existing* recall
   toolbox operating on the already-permitted candidate set: query rewrite/acronym expansion
   ([RAG §4.3](../../rag/00-retrieval-pipeline.md)), hybrid-fusion weighting and a higher candidate
   `k`, reranker/MMR tuning ([RAG §5](../../rag/00-retrieval-pipeline.md)), better wiki chunking so a
   cross-linked answer isn't split across chunks, and a **KM-eval-tuned model**. None of these
   change *what the caller may see*; they change *how well the platform finds what the caller may
   already see*. *Additive — the existing retrieval levers.*

2. **The content was *not accessible* — and the empty answer is correct.** Even in KM, a
   space-restricted page or a `confidential` runbook the caller lacks must return "no accessible
   information." This is not over-refusal; it is the safety floor doing its job. Distinguishing (1)
   from (2) is precisely what the eval set measures: the over-refusal false-negative rate on a
   held-out set of pages the caller *provably can* access, held separate from the permission-negative
   set. *Additive — the existing verifier contract.*

**Where it *could* have broken — the three floor-loosening temptations, each rejected:**

- **Tempt: widen the default label — make unlabeled content `public`, or push `internal` → `public`
  for reach.** *Rejected — and unnecessary.* Unnecessary because `internal` content is **already
  fully retrievable** to internal principals: the platform matrix allows `internal` retrieval
  verbatim ([Governance §4.1](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)) —
  there is no refusal to "fix" here, so recall gains nothing. Rejected because widening the default
  would violate fail-closed classification ([Metadata M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3):
  unlabeled → `internal`, never `public`) and could expose a mislabeled sensitive page to *external*
  egress. This is the exact loosen-a-floor move [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
  forbids a pack from making.
- **Tempt: relax the verifier's grounding / no-context-honesty bar so the model answers from thin
  context instead of refusing.** *Rejected — and it targets the wrong stage.* An over-refusal caused
  by an *empty context* (cause 1) is a **retrieval** miss; lowering the grounding bar would not
  surface the missing page — it would make the model **fabricate** from whatever weak signal
  remained, converting an availability bug into a **grounding/R2 leak** (the platform's central
  safety guarantee, [RAG §7](../../rag/00-retrieval-pipeline.md)). The grounding bar is a floor; the
  fix is upstream recall, not a lowered floor.
- **Tempt: add an unfiltered "list mode" / "return everything in the space" bypass for open
  content.** *Rejected — and structurally impossible anyway.* The `VectorIndex` port has **no
  unfiltered-search method** by construction ([Storage §3.4](../../storage/00-storage-architecture.md),
  [ADR-0010](../../architecture/adr/ADR-0010-storage-topology-and-tenancy.md)); filter-during-retrieval
  cannot be bypassed even deliberately. And it is unnecessary: a list/browse surface is the
  *filter-parity* catalog read ([API §…](../../api/00-api-surface.md#4-authn--authz-at-the-edge)),
  which applies the identical predicate — there is no accessible-content list mode to add, only the
  same predicate over a browse query.

There is no fourth cause of over-refusal that would require the read-only platform to *see more than
the caller may* — because the recall deficit is always either (a) a retrieval-tuning miss on the
*already-permitted* set, or (b) a *correct* refusal on genuinely-inaccessible content. **No floor
must move, so no horizontal gap exists.**

> **The reusable articulation (worth stating once, here).** *Recall is bought **upstream of the
> filter and the verifier**, on the set the caller may already see; safety is enforced **at and
> after** the filter. The two never trade against each other, so improving one never regresses the
> other. Over-refusal is a signal to tune retrieval and the model on the permitted set — never a
> licence to widen a label, lower the grounding bar, or unfilter a search.* This reaffirms
> [ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md) /
> [ADR-0009](../../architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md) rather than extending
> them — which is why KM needs **no new ADR** (see Trade-offs for when a future pack *would* force one).

**Verdict:** the bet holds against its first *inverse* (over-refusal) stress. The falsifiability
rule was armed and did **not** fire — and this is the first pack for which it was armed against a
*loosening* rather than a *tightening*. KM proves the platform's low-restriction defaults are
correctly calibrated: an open-content, high-recall domain fits the fail-closed platform with **zero
new vocabulary, zero tighten deltas, and zero loosened floors**. Every prior pack asked "does the
platform refuse when it must?" KM asks "does the platform *stop* refusing when it may?" — and the
answer is yes, delivered by tuning, not by weakening a guarantee.

---

## §1 — Sources & `map_acl` fidelity

KM sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)). Anything
below `exact` is **denied on the shared retrieval path** and quarantined
([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
KM is **fidelity-friendly** — most content is `internal` with clean space/site-level ACLs — but the
fail-closed rule is **not relaxed** for it: an unresolvable page restriction is quarantined exactly
as a SAP field-level rule is, even though KM's *default* is open.

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **Confluence** (Cloud / Data Center) | Space page, blog post, comment, attachment | `allow = {space-member CPIs}` (space permission) narrowed by **page/parent restrictions → `allow`/`deny`**; anonymous-access spaces → `public` (only if the source itself marks it so) | `exact` when space + page restrictions are readable principal sets | Most pages are `internal` to a space; page restrictions are a clean per-item ACL. A restriction expressed only as a *computed/dynamic* audience → `approximate` → deny + quarantine |
| **SharePoint / OneDrive** (wikis, portals, doc libraries) | Site page, wiki page, list item, document | Site/library/item ACL → `allow`/`deny`; broken inheritance honored per item | `exact` when item-level perms fully read | **Reuses Finance/HR/Legal SharePoint fidelity verbatim** ([Permissions §5.1](../../permissions/00-authorization-model.md)) |
| **Internal portals / intranet / static docs sites** | Page, article, uploaded doc | Group/audience → `allow`; `internal`-to-org by default (fail-closed, never `public` unless the source declares public) | `exact` when audience maps to a principal set; else `approximate` → quarantine | Unlabeled/ambient content defaults to `internal` per [Metadata M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3) — recall over it is fine (internal principals may read it); it is **never** promoted to `public` |
| **Wiki/README stores** (e.g. Git-hosted docs, DevOps wikis) | Repo doc, README, wiki page | Repo/project membership → `allow` | `exact` when repo membership is a readable principal set | Reuses the file-share/site mapping shape; no new mechanism |

**Conformance fixtures (the production gate).** The KM connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any KM source goes live. Note the
deliberate emphasis shift: KM's fixtures test **both** that safety holds **and** that open content is
*not* over-restricted:

1. **Open-content positive (the KM-specific check):** an `internal` Confluence page in a space the
   caller belongs to **is retrievable** — the pack must not accidentally over-restrict broadly-shared
   content (the inverse of every prior pack's headline). A caller who is a space member and asks a
   question the page answers gets it cited.
2. **Restricted-page negative (safety floor still holds):** a page with a tighter *page restriction*
   (e.g. an HR-sensitive draft in an otherwise-open space) is **not** retrievable by a space member
   who lacks the page restriction — `deny`/restriction overrides the space `allow`; masked, never
   partially leaked.
3. **Public-only-if-declared:** a page the source marks anonymous/public maps to `public`; an
   *unlabeled* page maps to `internal`, **never** `public` (fail-closed classification positive
   control).
4. **Computed-restriction quarantine:** a page restriction the connector cannot resolve to a
   principal set → the page is **denied on the shared path + quarantined**, never approximately
   served (identical to Finance field-level auth) — the fail-closed rule is not waived because KM is
   "mostly open."
5. **Cross-tenant:** no KM chunk of tenant A ever reaches tenant B (R4), inherited unchanged.

---

## §2 — Classification-registry values (the vocabulary KM registers)

**KM registers nothing.** It is the **first pack to add zero classification vocabulary** — a result
worth stating plainly, because it is the direct evidence that the platform's *existing* low-end
labels are sufficient for an open-content domain.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| — | *(none)* | KM content lives entirely in the already-defined `public` / `internal` values, with occasional **inherited** `confidential` for a restricted runbook and inherited `pii_class:*` for incidental personal data in free text |

KM relies on two *existing* facts rather than new labels:

- **The fail-closed default is the right default for open content.** Unlabeled wiki/portal content
  defaults to `internal` ([Metadata M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)),
  which is *exactly* what a knowledge domain wants: readable by internal principals, blocked from
  external egress, never silently `public`. No new lax label is needed — and inventing one
  (`km_open`, say) would be the loosen-a-floor trap.
- **Occasional sensitivity is *inherited*, not invented.** A KM space that happens to hold a
  `confidential` architecture doc or a page with a name/email in it reuses the existing
  `confidential` / `pii_class:*` values and their existing masking — KM adds no dimension for this.

That the pack contributes an **empty** §2 (and §3) is the pack's central finding restated as a
table: the low-restriction end of the lattice was already complete.

---

## §3 — Label→action *tighten* deltas

**KM tightens nothing — the first pack with an empty delta table.** It uses the platform
[label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)
verbatim.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `internal` | Allowed to internal principals | Verbatim; in-boundary models | Blocked to external; internal export logged | **No delta** — the platform default is already correct for KM's bulk content |
| `public` | Allowed | Verbatim | Allowed per tenant policy | **No delta** — only content the *source* marks public |
| `confidential` / `pii_class:*` (inherited, rare) | Per existing matrix | Per existing matrix | Per existing matrix | **Inherited, not tightened** — KM does not relax them either |

**And, critically, KM loosens nothing.** The temptation catalogued in the analysis — a widened
default, a relaxed grounding bar, an unfiltered list mode — is *absent* here by design. A tenant that
asked KM to "just return everything, skip the filter" would be asking to loosen a floor; the platform
**refuses** ([Governance §4.2](../../governance/00-governance-and-audit.md), admin-can-only-tighten
[API §…](../../api/00-api-surface.md)) — which is KM confirming the floor is a floor *from the open
side*.

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)) —
KM subtracts nothing and adds nothing, and that is the intended result.

---

## §4 — Compliance-map row(s) (declare + inherit)

KM's compliance footprint is the **lightest of any pack** — a further sign of its low-restriction
nature. It **inherits** the ISO 27001 / SOC 2 and GDPR rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain)
and declares no sector regime. It does not re-derive mechanism.

| Regime | Inherited controls (already built) | KM-specific evidence binding |
|--------|-----------------------------------|------------------------------|
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store; hash-chained trail; role-gated access | Standard information-handling controls; every KM retrieval is an audited event with `resource_id` + `source_item_version` + model version — a wiki answer is attributable to its cited page version |
| **GDPR** | Right-to-erasure + DSAR; PII masking; residency; `legal_hold > erasure > retention` | **Incidental** personal data in free-text pages (a name/email in a meeting note) is masked by the *existing* `pii_class:*` machinery and erasable by the *existing* DSAR job — KM adds no PII-handling mechanism, only inherits it for the free-text case |

**No new control was invented, and none was relaxed.** KM's compliance posture is a *thin selection*
of platform controls — the notable fact is how *few* it needs, which is the compliance-side echo of
its empty §2/§3.

---

## §5 — Retrieval / answer eval set

The KM pack supplies (a) the **parsers** that make wiki/portal content retrievable and (b) the
**eval corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).
**KM's eval headline is the inverse of every prior pack's:** the primary metric is **recall /
answer coverage** and the **over-refusal false-negative rate**, *not* a permission-negative leak
rate — while permission negatives are *still* tested (the safety floor never drops, it just stops
being the headline).

**Parsers (behind the existing per-content-type seam — [RAG §2](../../rag/00-retrieval-pipeline.md)):**
- **Wiki / portal pages** — heading/section chunking (reuses RAG's structure-aware seam); densely
  cross-linked pages chunk on headings so a linked concept stays a coherent, citable unit. The
  mixed-ACL invariant still holds: a chunk never spans two pages with different restrictions.
- **Restated/duplicated content** — the same policy appears in many pages; **dedup at context
  assembly** ([RAG §6](../../rag/00-retrieval-pipeline.md)) is load-bearing for KM so the model isn't
  handed eight near-duplicate chunks. An *existing* lever, tuned, not added.
- **Stale content** — `source_item_version` + `superseded_by` ([Metadata](../../metadata/00-catalog-and-lineage.md))
  let retrieval prefer the current version; no new mechanism.

**Eval set (recall · over-refusal · grounding · permission negatives still tested):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Recall / answer coverage (the KM headline)** | Asked a question answered by an accessible page, the pipeline surfaces and cites it — it does not wrongly return "no accessible information" on content the caller *can* read | ≥ target recall on the held-out accessible-content set |
| **Over-refusal false-negative rate** | The rate at which the platform refuses on *genuinely accessible* content (the availability bug KM exists to catch) is below target — measured on a set of (caller, page) pairs where the caller provably has access | ≤ target false-refusal rate |
| **Permission negatives (safety floor — still enforced)** | A page-restricted or `confidential` page the caller lacks is **not** retrievable via any cleverly-worded prompt — high recall did **not** buy a leak | 0 leaks (unchanged from every prior pack) |
| **Public-vs-internal correctness** | An unlabeled page is treated as `internal` (blocked from external egress), a source-declared public page as `public` | 0 unlabeled pages egressed externally |
| **Grounding (unchanged)** | Every factual claim traces to a cited page version; the model does not fabricate from thin context — the grounding bar is **not** lowered to raise recall | 100% claims cited or refuse |
| **Dedup / freshness quality** | Restated content is de-duplicated; the *current* version is preferred over a superseded one | No answer grounded solely in a `superseded_by` version when a current one is accessible |

A model that regresses on **recall / over-refusal** cannot be promoted for the KM tenant — the same
gate shape as Finance/HR/Legal/Audit, retargeted to KM's failure mode. **The deliberate contrast:**
Audit first surfaced a *recall* eval class (missing a real SoD conflict is a failure); KM makes recall
and over-refusal the *primary* bar. Yet the permission-negative class is retained unchanged — proving
the gate can chase recall **without** trading away the safety floor, which is the whole thesis.

---

## §6 — Optional additive API `pack` hint

KM callers **may** pass `"pack": "km"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (e.g.
prefer the KM recall-tuned model, bias retrieval toward wiki/portal sources, apply heading-section
chunking, enable aggressive dedup). It is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"km"` but
  lacks a page restriction sees nothing ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)).
  The hint tunes *recall on the permitted set*; it is **not** an authorization input and cannot
  unfilter a search.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the hint
  only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"km"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7),
  not a breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Recall tuning vs. the floor it must not cross.** KM's recall is bought by config and an
  eval-tuned model on the *permitted* set. That means a genuinely low-recall KM deployment is fixed
  by *tuning*, which is slower and less dramatic than the tempting "just unfilter it" — but the
  temptation is a floor breach. The honest trade: recall is an *optimization* problem bounded by the
  safety floor, never a *floor-relaxation* problem. A tenant wanting recall *beyond* what the floors
  allow is asking for a leak.
- **Fail-closed default (`internal`) vs. "obviously public" content.** Unlabeled content defaults to
  `internal`, so truly-public marketing pages that *should* be `public` require the source to mark
  them so. Slightly more conservative than a "default public for KM" would be — but that default is
  exactly the loosen-a-floor move the pack rejects; the conservative default protects a *mislabeled*
  sensitive page from external egress at the cost of one explicit `public` marking.
- **Shared tier by default vs. the occasional confidential space.** KM defaults to Shared (low
  blast radius). A KM sub-tenant hosting confidential engineering runbooks graduates *up* to Isolated
  — a placement decision, not a redesign, mirroring Audit graduating *down* for issued-only content.
- **Empty §2/§3 as a feature, not a gap.** A reviewer might read "registers nothing, tightens
  nothing" as an under-specified pack. It is the opposite: the empty tables are the *evidence* that
  the low-restriction end of the platform was already complete — the pack's deliverable is the proof,
  not new mechanism.
- **When a future pack *would* force the ADR this one avoided.** If a pack ever demanded recall that
  *requires* loosening a floor — a domain whose value proposition is "surface content the caller
  isn't strictly entitled to" (e.g. an intentional org-wide-transparency mode that overrides per-space
  restrictions) — that is a horizontal change to the permission-faithful contract
  ([ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)), needing a new ADR,
  not a pack hack. Recording *why* KM did not need it makes that future boundary crisp.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Widen the default label (unlabeled → `public`, or `internal` → `public`) to raise reach** | **Rejected — this is the trap.** `internal` content is already fully retrievable to internal principals, so this buys *zero* recall; and it violates fail-closed classification ([Metadata M3](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)), risking external egress of a mislabeled sensitive page. A loosened floor is the horizontal change the bet forbids. |
| **Relax the verifier's grounding / no-context-honesty bar so it answers from thin context** | Rejected: an empty context is a *retrieval* miss (fix upstream); lowering the bar makes the model **fabricate**, converting an availability bug into a grounding/R2 leak — trading the platform's central safety guarantee for recall it wouldn't even gain. |
| **Add an unfiltered "list everything in the space" mode for open content** | Rejected: structurally impossible (the `VectorIndex` port has no unfiltered method, [Storage §3.4](../../storage/00-storage-architecture.md)) and unnecessary — browse is the *filter-parity* catalog read applying the identical predicate ([API §4](../../api/00-api-surface.md)). |
| **Register a new lax `km_open` label to mark broadly-shared content** | Rejected: the existing `internal` value already carries exactly this semantics (readable internally, no external egress); a new lax label adds vocabulary the closed schema doesn't need and invites mislabeling toward *over*-exposure. |
| **A bespoke KM-specific recall pipeline separate from the platform hybrid search** | Rejected ([ADR-0009](../../architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)): recall is raised by tuning the *existing* hybrid-search/rerank/dedup levers and an eval-tuned model — a second pipeline is duplication and would fork the safety guarantee. |

## Future scalability

- **KM proves the low-restriction end is calibrated** — future open-content domains (a
  customer-support knowledge base, a public-docs site, an internal FAQ) are now pure fill-in-the-blank
  with, likely, the same empty §2/§3.
- **The source-shaped packs (SAP / SharePoint / Email) are next** and are pure connector-fidelity
  reuse — KM already exercised the SharePoint fidelity path in its open-content mode, complementing
  Finance/HR/Legal's restricted-mode exercise of the same connector.
- **A new KM source** (e.g. a Notion/Slack knowledge export, a Git-wiki) = a new §1 row + fixtures;
  no pipeline change. The recall levers are already the platform's.
- **A recall-tuned KM model** enters through the existing eval gate (§5, now with recall/over-refusal
  as the headline metric) and is routed by the existing label→trust policy — a config change, not a
  code change.
- **A future *transparency-mode* pack** (deliberately surfacing content beyond strict entitlement) =
  the one case that *would* need a horizontal ADR loosening the permission-faithful contract —
  deliberately out of scope, and now documented as the explicit boundary (Trade-offs).

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack](../finance/00-finance-pack.md) · [HR pack](../hr/00-hr-pack.md) · [Legal pack](../legal/00-legal-pack.md) · [Audit pack](../audit/00-audit-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md) · [ADR-0004 — Permission-faithful retrieval](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md) · [ADR-0009 — Hybrid retrieval & chunking](../../architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)
- [Permissions §5 (per-source mapping), §7 (labels), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §4 (classification registry; fail-closed default)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix — `public`/`internal` rows), §8 (model eval gate), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG §2 (chunking), §4.3 (query expansion), §5 (rerank/MMR), §6 (dedup), §7 (verifier)](../../rag/00-retrieval-pipeline.md) · [Storage §3.4 (VectorIndex port)](../../storage/00-storage-architecture.md) · [API §4, §5, §11](../../api/00-api-surface.md)
