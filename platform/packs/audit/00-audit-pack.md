# Domain Pack #4 — Audit (SOX evidence, segregation-of-duties & append-only workpapers)

> **The fourth data point — the highest-leverage, lowest-effort pack, and the second
> genuine falsifiability test.** Audit is chosen next because it **inherits almost everything
> already built** (Finance's SOX row + SAP connector fidelity *verbatim*; Legal's `matter:<id>`
> hold + append-only evidence) and introduces **exactly one concept to stress:
> segregation-of-duties (SoD).** The sharp question the [skeleton's falsifiability
> rule](../README.md#the-falsifiability-rule) exists to catch is: *SoD is inherently
> **combinatorial** — "no single principal may hold both **approve** and **post** on the same
> document." Does that relational rule force a predicate the per-principal `deny` set cannot
> express — a real horizontal gap → a Permissions/Governance ADR — or does it resolve to a
> mechanism the platform already has?* **It resolves — but for a sharper reason than Legal's,
> and one worth stating explicitly: the platform is a *read-plane mirror*, not a
> *transaction-control plane*. See §0 and the "Segregation-of-duties" analysis below — no
> horizontal change.**

- **Cycle:** 14 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — SoD fits the existing contract; had it forced a combinatorial access predicate, this pack would have raised a Permissions/Governance ADR, which is the process working)
- **Regimes declared:** SOX (§404 ICFR), PCAOB auditing standards (workpaper retention AS 1215), IIA International Professional Practices Framework (internal audit), ISO 27001 / SOC 2, GDPR
- **Isolation tier (default):** Isolated ([Storage §5](../../storage/00-storage-architecture.md)) — pre-issuance workpapers + SOX evidence blast radius

---

## Why Audit fourth (and why it is the right stress test)

n=1 (Finance) proved the mechanism *exists*; n=2 (HR) proved it *generalizes*; n=3 (Legal) proved
it survives a *genuinely novel concept*. Audit earns its slot by pairing **maximum inheritance**
with **one relational concept the platform has never had to place** — isolating SoD as a clean
experiment, exactly as Legal isolated waiver:

- **Segregation-of-duties is the first *combinatorial* constraint any pack has raised.** Every
  restriction so far has been *unary* — a property of one (principal, item) pair: "is this CPI in
  the cleared set," "is this CPI on the wall." SoD is *relational*: it constrains a **pair of
  actions across a process** ("the preparer of entry E may not be its approver"). A per-principal
  `deny` set is unary by construction. This is the sharpest test yet of whether the canonical
  model's predicate is expressive enough — **or whether combinatorial control is simply out of the
  platform's plane.** (Answer: out of plane. SoD is a *write/transaction* control; the platform is
  a *read* mirror. See "Segregation-of-duties" below.)
- **Audit *owns* the append-only-evidence concept the platform already provides.** The
  [append-only audit store](../../storage/00-storage-architecture.md) (S7) + immutable versioned
  knowledge (Principle 8) + the [hash-chained audit trail](../../governance/00-governance-and-audit.md#6-audit)
  are the audit function's native substrate — Audit consumes them, adds nothing.
- **Audit is the reflexive pack.** SOX §404 makes the *auditor's* evidence trail a legal
  artifact; ISO 27001 / SOC 2 make the *platform itself* an audited system. The controls Audit
  needs to *retrieve over* are the same controls the platform runs *on itself* — a satisfying
  closure, and a reason its compliance row is nearly pure inheritance.
- **The platform must *surface* SoD conflicts, never *enforce* SoD transactions.** Detecting "who
  both prepared and approved" is a **read-side analytics query** over the audit trail — exactly
  the Audit pack's job, permission-gated like any other retrieval. *Preventing* the second action
  is a **write-side control in the source system of record** (SAP GRC, the ERP), which a read-only
  knowledge platform never executes. Conflating the two is the trap.

If any of these forced a horizontal change, that would be the headline finding. **None did** —
see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Audit? | What Audit did instead |
|--------------------|:-------------------------:|------------------------|
| Permissions (canonical model, `map_acl`) | **None** | SoD-derived *read* restrictions = the existing `deny`-wins clause ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)), a per-principal `deny` grant identical in shape to Legal's ethical wall; the *combinatorial* half of SoD is a **write-side control the platform does not execute** (read-plane mirror — see analysis); a source that exposes an SoD-derived restriction only as a *computed* rule not resolvable to a principal set rides the *existing* §9 quarantine / §10 OBO hatch |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `restricted:audit_workpaper` into the existing `restricted:<class>` extension point ([§4.1](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)); reused `matter:<id>` (Legal/HR/Finance) for engagement/retention holds |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** the matrix for `restricted:audit_workpaper` (pre-issuance masking + egress block); **inherited** the SOX + GDPR + ISO rows verbatim; expressed PCAOB AS 1215 7-year workpaper retention as the *existing* retention schedule + `legal_hold`-precedence rule |
| RAG (chunking, hybrid, verifier) | **None** | Supplied workpaper/testing-matrix parsers behind the *existing* structure-aware seam; supplied an eval set whose headline classes are **SoD-conflict detection recall** and **pre-issuance permission negatives** |
| Storage / Workers / API / Deployment | **None** | Chose the *existing* Isolated tier; append-only evidence = the *existing* S7 audit store; connector rides the *existing* staged DAG; reuses Finance's SAP + Legal's DMS fidelity; API `pack:"audit"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** The headline: the one concept most likely to
force a horizontal primitive — **combinatorial SoD** — resolved not by *composing* existing
mechanisms (as Legal's waiver did) but by a **plane boundary**: SoD *prevention* is a
transaction-control concern the read-only platform never owns, and SoD *detection* is an ordinary
permission-faithful retrieval whose combinatorial logic lives **in the query and the source data,
never in the access predicate.** Per [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md),
if a future edit to this pack adds a "required" row, that edit needs a horizontal ADR.

---

## Segregation-of-duties — the falsifiability analysis (the reason this cycle exists)

This is the section a reviewer should read first; it is the whole point of choosing Audit.

**The claim under test.** *"Segregation-of-duties — including combinatorial rules of the form 'no
single principal may hold both approve and post on the same document' — is expressible as additive
pack data + policy; it does not force a new horizontal access-control predicate."*

**The decomposition — separate *prevention* from *detection*, and *action* from *read*:**

SoD is one word for two different controls that live in two different planes:

1. **SoD as a *preventive* control (write plane) — not the platform's job.** "The preparer of a
   journal entry may not post it" is enforced at the moment of the *posting action*, inside the
   **source system of record** (SAP GRC, the ERP's authorization objects). It is a constraint on
   *executing a transaction*. The AI Studio platform is a **read-only, permission-faithful
   knowledge platform** ([ADR-0001](../../architecture/adr/ADR-0001-platform-shape-private-rag.md),
   [ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)): it retrieves and
   answers over knowledge; it **never posts, approves, or executes** a business transaction.
   Therefore **there is no SoD action for the platform to gate** — the combinatorial rule has no
   hot-path evaluation point here, because the platform never reaches the state the rule guards.
   *Not a gap — out of plane.*

2. **SoD as it *projects onto read access* — a per-principal `deny`, pre-resolved by the source.**
   Where SoD *does* restrict *reading* (e.g. "an auditor independent of the audited unit must not
   read that unit's draft self-assessment"; "a preparer must not see the reviewer's sign-off"),
   the source system resolves the relation into a concrete principal set at its boundary and
   exposes it as an ACL. The connector `map_acl`s it into a **`deny` grant** on the affected items;
   deny-wins ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins))
   already evaluates first. This is **structurally identical to Legal's ethical wall** — the
   relation ("who is the preparer") is computed *at the source*, the platform mirrors a unary
   per-principal `deny`. *Additive — the existing first clause of the predicate.*

3. **SoD as a *detective* control (read plane) — an ordinary retrieval, combinatorial logic in the
   query.** The Audit function's actual daily need is to *find* violations: "list users who both
   prepared and approved an entry this quarter." This is a **read** over the SoX/GRC audit trail
   (the source's transaction log), answered by the platform like any other permission-gated
   question. The combinatorial join ("prepared ∩ approved on the same E") lives **in the query and
   in the source data**, *not* in the platform's access-control predicate — the platform simply
   retrieves the trail rows the caller is permitted to see and answers over them. The verifier
   grounds the answer in cited trail rows (refuse-over-guess). *Additive — this is exactly what a
   permission-faithful RAG platform is for.*

**Where it *could* have broken — and why it doesn't.** The trap is trying to make the platform's
**access predicate itself** enforce the relational rule — e.g. "deny read to the approval artifact
to any caller who appears as preparer in the linked transaction, *computed live at query time from
the caller's own history*." Two escape hatches, both *existing*, cover this without a new predicate:

- If the source **pre-resolves** the relation into an ACL (the normal case), it is a unary `deny`
  — case (2) above. *Additive.*
- If the source exposes it **only as a computed rule** the connector cannot resolve to a principal
  set, that item takes the **existing** `approximate → deny + quarantine` path
  ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
  identical to SAP field-level auth (Finance) and computed-privilege (Legal). The platform never
  *fakes* a combinatorial grant. *Additive — the existing quarantine hatch.*

There is no third case in which the read-only platform must *itself compute* a combinatorial SoD
decision to serve a request — because the combinatorial decision is either (a) already an ACL, or
(b) a *transaction* the platform never performs, or (c) a *query result* the platform grounds and
returns. **No relational access predicate is required, so no horizontal gap exists.**

> **The reusable articulation (worth stating once, here).** *The platform enforces
> **who-may-read**, never **who-may-act**. Any control phrased as a constraint on actions —
> SoD, four-eyes, maker-checker, dual-authorization — is enforced in the source system of record;
> the platform mirrors whatever **read** restriction that control produces (a `deny`), and
> **retrieves over** whatever **evidence** that control leaves behind (the audit trail). Detection
> is in scope; prevention of an action is out of plane.* This reaffirms
> [ADR-0001](../../architecture/adr/ADR-0001-platform-shape-private-rag.md) /
> [ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md) rather than
> extending them — which is why Audit needs **no new ADR** (see Trade-offs for when a future pack
> *would* force one).

**Verdict:** the bet holds against its first *combinatorial* concept. The falsifiability rule was
armed and did **not** fire — but this is the closest a pack has come to the boundary, and the
reason it doesn't fire is a **scoping** fact (read-plane mirror), not a composition trick. Had the
platform been asked to *prevent* the second action, that would be a new transaction-control plane —
a horizontal change the bet forbids, and correctly out of scope. That it is out of scope is the
finding.

---

## §1 — Sources & `map_acl` fidelity

Audit sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)).
Anything below `exact` is **denied on the shared retrieval path** and quarantined to the Isolated
tier ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
Audit is **fidelity-friendly** where it reuses Legal's DMS/workpaper ACLs and **fidelity-hard**
where it reuses Finance's SAP (no document ACL) — both cases are already solved.

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **Audit-management / GRC system** (AuditBoard, Workiva, SAP GRC) | Workpaper, test-of-controls matrix, engagement file | `allow = {engagement-team CPIs}`; **independence/SoD exclusion → `deny = {conflicted principals}`**; workpaper state (draft/issued) → `sensitivity` | `exact` when engagement membership + exclusions are readable principal sets | SoD read-exclusion = existing deny-wins ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)); the analogue of Legal's ethical wall |
| **SAP / ERP** (FI/CO, GRC Access Control) | Journal entry, approval record, transaction log row | Row/record scope → `allow`; SoD-derived read-exclusion → `deny`; **computed SoD rule not resolvable to a principal set** → `approximate` → **deny + quarantine** (or native OBO §10) | `exact` only when scope + exclusions map to grants; else `approximate` | **Reuses Finance's SAP fidelity + field-level-auth quarantine verbatim** — the platform never fakes a grant |
| **DMS — iManage / NetDocuments / SharePoint** | Issued audit report, memo, evidence PDF | Per-document ACL → `allow`; MIP/DMS label → `sensitivity` | `exact` when item-level perms fully read | **Reuses Legal/Finance DMS + SharePoint fidelity verbatim** |
| **Append-only evidence store** (the platform's own S7 trail) | Retrieval/policy/ACL-change audit event | Role-gated read ([Governance §6.2](../../governance/00-governance-and-audit.md)); itself audited | `exact` (native to the platform) | The reflexive case — Audit retrieves over the platform's *own* hash-chained trail; no external connector |
| **Email / Exchange** | Auditor↔auditee correspondence, management representations | Mailbox owner + explicit delegates; per-message ACL | `exact` per message | Reuses Legal/HR email fidelity — [§5.3](../../permissions/00-authorization-model.md#53-email--exchange) |

**Conformance fixtures (the production gate).** The Audit connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any Audit source goes live:

1. **SoD read-exclusion (deny-wins):** a principal excluded from engagement E for independence
   **cannot** retrieve E's workpapers even holding the firm-wide audit role — the `deny` overrides
   the `allow` (positive control: a non-excluded team member *can*).
2. **Pre-issuance workpaper positive + negative:** an engagement-team member retrieves a
   `restricted:audit_workpaper` draft; a principal outside the team **cannot**, and it is
   **masked**, never partially leaked; after issuance, the *issued report* follows its own
   (broader) ACL.
3. **Computed-SoD quarantine:** a SAP-exposed SoD rule that the connector cannot resolve to a
   principal set → the affected records are **denied on the shared path + quarantined**, never
   approximately served (identical to Finance field-level auth).
4. **Engagement-hold vs. erasure:** a `matter:<id>` + `legal_hold` workpaper survives an erasure
   request (`legal_hold > erasure > retention`) under PCAOB 7-year retention, proven by
   [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4).
5. **Cross-tenant:** no Audit chunk of tenant A ever reaches tenant B (R4), inherited unchanged.

---

## §2 — Classification-registry values (the vocabulary Audit registers)

Audit **registers** one value into the tenant [classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
extension point — it does not invent new dimensions. An unregistered label is a write-boundary
schema violation → DLQ ([Workers §8.1](../../workers/00-ingestion-architecture.md)), never silently
stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:audit_workpaper` | Pre-issuance audit workpapers, test-of-controls matrices, draft findings (PCAOB AS 1215 material; highly restricted until the report issues) |
| `legal_hold` | `matter:<id>` | Any workpaper/evidence under an engagement retention hold or litigation preservation **(reused verbatim from Legal/HR/Finance)** |

`restricted:audit_workpaper` slots into the existing lattice
(`public < internal < confidential < restricted:*`), so **most-restrictive-wins** composition is
inherited unchanged. A pre-issuance workpaper documenting a SOX control test over MNPI-adjacent
financials, under a retention hold, resolves to `restricted:audit_workpaper` +
(inherited) `confidential`/`pii_class:financial` + `legal_hold:true` — the most restrictive action
of each dimension applies. It is the **`restricted:<class>` extension point** the
[Metadata schema](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions) already defines,
exactly as Finance registered `restricted:mnpi` and Legal `restricted:privileged`.

> **Note on SoD (deliberately *not* a label).** SoD independence exclusion is **not** registered
> as a `sensitivity` value — it is a **`deny` grant** on the item ACL. Modeling it as a label would
> conflate *what the restriction is* with *who is barred*, and would lose deny-wins semantics —
> exactly the reasoning that keeps Legal's ethical walls in the ACL. Keeping SoD in the ACL is what
> lets it reuse the existing predicate unchanged.

---

## §3 — Label→action *tighten* deltas

Audit **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:audit_workpaper` | Only to principals on the **engagement team**; **masked** for everyone else; SoD/independence `deny` overrides any allow | **Isolated model pool only**; masked in prompt unless the caller is on the engagement team | **Never** any external egress; **never** in batch/analytics export until issuance | Stricter than `confidential`: adds model-pool restriction + hard egress block + SoD-exclusion interaction (mirrors Finance `restricted:mnpi`, Legal `restricted:privileged`) |
| `legal_hold:true` (`matter:*`) | Unchanged (visibility unaffected) | Unchanged | **Never auto-deleted** — preservation override ([Governance §5.3](../../governance/00-governance-and-audit.md#53-legal-hold-overrides-erasure--retention)); PCAOB AS 1215 7-year retention + litigation preservation | Inherited from Legal/HR/Finance, not tightened |

**SoD is expressed on the ACL, not in this matrix.** These rows are *static* — they never mention
a caller's other roles or prior actions. Who is excluded from an engagement is the item's `deny`
set (§1/§0), written by the source's independence/SoD logic. This is precisely why SoD needs no
matrix change: the matrix governs *what the label permits*, the ACL governs *whom* — and SoD only
touches the latter (as a `deny`).

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).

---

## §4 — Compliance-map row(s) (declare + inherit)

Audit **inherits** the SOX, GDPR, and ISO rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain)
and adds an **SoD/workpaper** binding over *existing* controls; it does not re-derive mechanism.
The evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | Audit-specific evidence binding |
|--------|-----------------------------------|--------------------------------|
| **SOX §404 (ICFR)** | Append-only audit; immutable versioned knowledge (Principle 8); per-stage least privilege; ≥7-yr audit retention — **inherited verbatim from Finance** | Every workpaper retrieval audit event carries `resource_id` + `source_item_version` + model version → an audit conclusion is reproducible and attributable years later; **SoD read-exclusions are provable deny-grants in the ACL-change trail** |
| **PCAOB AS 1215 (workpaper retention)** | Retention schedule + `legal_hold`-precedence + lineage tombstone | 7-year workpaper preservation enforced as the existing retention floor + `matter:<id>` hold; preservation completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4) |
| **IIA IPPF (internal audit independence)** | deny-wins ACL + role-gated audit read | Independence enforced as an SoD `deny` grant (an auditor excluded from a unit they operate in cannot read that unit's draft self-assessment); the exclusion itself is an audited ACL fact |
| **GDPR** | Right-to-erasure + DSAR; PII masking; residency; `legal_hold > erasure > retention` | Erasure of personal data in evidence honored *except* where a `matter:<id>` hold preserves it — partial-erasure outcome proven by traversal, same as HR/Legal |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed, self-auditing policy store; hash-chained trail | **Reflexive:** the very controls Audit retrieves *over* are the controls the platform runs *on itself* — the platform's own SOC 2 evidence is the append-only trail Audit queries |

**No new control was invented.** Audit's compliance posture is a *selection and binding* of
controls the platform already operates — the SOX and evidence story is **Finance's row reused**,
and the one addition (SoD-exclusion-as-deny) is the same deny-grant mechanism Legal used for walls.

---

## §5 — Retrieval / answer eval set

The Audit pack supplies (a) the **parsers** that make its content retrievable and (b) the **eval
corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **Workpapers / test-of-controls matrices** — table-row + section chunking (reuses RAG's
  structure-aware + table-row seam; a control-test row is a coherent, citable unit). The mixed-ACL
  invariant means a chunk never spans two engagements with different teams.
- **Audit reports / memos / findings** — heading/section chunking; `restricted:audit_workpaper`
  carried per section until issuance.
- **SAP / ERP transaction & approval logs** — reuses Finance's SAP-table/ledger serialization
  verbatim; a transaction row (preparer, approver, poster, timestamp) is the citable unit an
  SoD-detection query joins over.

**Eval set (grounding · refusal · SoD-detection recall · pre-issuance negatives):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Pre-issuance permission negatives** | A principal outside the engagement team (incl. an SoD-excluded auditor) cannot obtain `restricted:audit_workpaper` content via any cleverly-worded prompt | 0 leaks (a permission test, not an accuracy test) |
| **SoD-conflict detection recall** | Asked "which users both prepared and approved an entry in Q3," the answer enumerates every conflicting pair present in the *accessible* trail — the combinatorial join is grounded in cited trail rows | ≥ target recall on the held-out labelled set; 0 invented pairs |
| **SoD-exclusion enforcement** | An SoD/independence-excluded auditor is denied the excluded unit's workpapers even holding the firm-wide role (deny-wins) | 0 exclusion breaches |
| **Computed-SoD quarantine** | A SAP-exposed computed SoD rule that cannot resolve to a principal set → the records are quarantined, not approximately served | 0 approximate serves of unresolvable SoD records |
| **Evidence grounding** | An audit conclusion ("control C operated effectively in Q2") traces to cited workpaper rows; no invented test result | 100% audit claims cited or the answer refuses |
| **Refuse-over-guess** | A question about an engagement the caller can't access → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated finding | 0 fabrications on the held-out no-access set |
| **Hold vs. erasure correctness** | A `matter:<id>`-held workpaper survives an erasure request while non-held personal data is erased | 0 deletion of held records; 0 retrieval of erased content |

A model that regresses on **pre-issuance negatives**, **SoD-detection recall**, or **SoD-exclusion
enforcement** cannot be promoted for the Audit tenant — the same gate shape as Finance/HR/Legal,
retargeted to Audit's failure modes (a mix of *who* — exclusions — and *recall* — finding every
conflict). Note the deliberate asymmetry vs. Legal: Audit's headline risk includes a **recall**
class (missing a real SoD conflict is an audit failure), the first hint of the *over-refusal*
failure mode that KM will stress next.

---

## §6 — Optional additive API `pack` hint

Audit callers **may** pass `"pack": "audit"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (e.g.
prefer the Audit eval-tuned model, bias retrieval toward workpaper/GRC sources, apply table-row
chunking for control matrices). It is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"audit"`
  but is outside an engagement team (or SoD-excluded) sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an
  authorization input, and it cannot override an SoD `deny`.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the hint
  only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"audit"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7),
  not a breaking change — clients that ignore it keep working.

---

## Trade-offs

- **SoD detection in-scope vs. SoD prevention out-of-plane.** The platform will *find* SoD
  conflicts (a read) but will never *block* the offending transaction (a write) — that stays in
  SAP GRC / the ERP. Less "complete" than a GRC suite, but honest: a read-only mirror that pretends
  to enforce transaction controls would be a false assurance. The correct division is detection
  here, prevention at the source.
- **SoD-exclusion as a `deny` grant vs. a combinatorial rule engine.** Keeping SoD read-exclusions
  in the existing deny-wins predicate (rather than a relational-policy engine) means correctness
  depends on the source resolving the relation into a principal set. Where a source exposes SoD
  only as a computed rule, that content is quarantined (the R1 trade), not approximately served —
  the same trade Finance made for field-level auth and Legal for computed privilege.
- **Pre-issuance Isolated tier by default vs. cost.** Audit defaults to Isolated (pre-issuance
  workpaper + SOX-evidence blast radius). More expensive than Shared, but the honest default; an
  Audit sub-tenant handling only *issued* reports (broadly `internal`) could graduate *down* — a
  placement decision, not a redesign.
- **Reflexive dependency (the platform audits itself).** Audit retrieving over the platform's own
  hash-chained trail is elegant but couples Audit's completeness to the trail's integrity — which
  is why the [scheduled hash-chain verification](../../governance/00-governance-and-audit.md#6-audit)
  and the [lineage-integrity check](../../deployment/00-deployment-topology.md) are load-bearing for
  this pack specifically.
- **When a future pack *would* force the ADR this one avoided.** If a pack ever asks the platform
  to *take an action under a four-eyes / dual-authorization rule* (i.e. the platform becomes a
  write actor), that is the transaction-control plane this analysis rules out — and it would need a
  new horizontal ADR (a scope extension of [ADR-0001](../../architecture/adr/ADR-0001-platform-shape-private-rag.md)),
  not a pack hack. Recording *why* Audit did not need it is what makes that future boundary crisp.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Add a combinatorial/relational SoD policy engine to Permissions or Governance** | **Rejected — this is the trap.** SoD *prevention* is a write-side control the read-only platform never executes; SoD *read* restrictions are already unary `deny` grants; SoD *detection* is an ordinary permission-gated query whose join lives in the data. A relational access-predicate engine would be the horizontal change the bet forbids, built for a plane the platform is not in. |
| **Model SoD exclusion as a new sensitivity label** | Rejected: an exclusion is a *deny* about *who*, not a *what*; it belongs in the deny-wins ACL predicate ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)), which already evaluates first. A label would lose deny semantics — same reasoning as Legal's ethical walls. |
| **Have the platform *enforce* SoD by blocking a second action** | Rejected: the platform is not a transaction engine ([ADR-0001](../../architecture/adr/ADR-0001-platform-shape-private-rag.md)/[ADR-0004](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)); it mirrors read access and retrieves over evidence. Enforcement stays in the source system of record. |
| **Re-derive a bespoke Audit append-only evidence store** | Rejected: the platform's S7 append-only, hash-chained audit store already *is* the evidence substrate; Audit consumes it. Building a second is duplication. |
| **A bespoke SOX/PCAOB compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): Audit inherits Finance's SOX row + binds SoD/workpaper evidence; re-deriving controls is the anti-pattern. |

## Future scalability

- **Knowledge Management** is the deliberate *inverse* stress next: broad `internal`, low
  restriction, high recall — does the pipeline *over*-refuse on open content? Audit's SoD-detection
  **recall** eval class is the first sighting of that failure mode; KM makes it the headline.
- **A new Audit source** (e.g. a continuous-controls-monitoring tool, an external-audit platform) =
  a new §1 row + fixtures; no pipeline change.
- **A new SoD-adjacent regime** (e.g. a sector's specific independence rule) = a new §4 compliance
  row binding existing controls — no redesign.
- **A future *action-taking* pack** (the platform executes a workflow step) = the one case that
  *would* need a horizontal transaction-control ADR — deliberately out of scope, and now
  documented as the explicit boundary (Trade-offs).
- **An Audit-tuned model** enters through the existing eval gate (§5) and is routed by the existing
  label→trust policy — a config change, not a code change.

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack](../finance/00-finance-pack.md) · [HR pack](../hr/00-hr-pack.md) · [Legal pack](../legal/00-legal-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md) · [ADR-0001 — Private RAG shape](../../architecture/adr/ADR-0001-platform-shape-private-rag.md) · [ADR-0004 — Permission-faithful retrieval](../../architecture/adr/ADR-0004-permission-faithful-retrieval.md)
- [Permissions §3.1 (deny-wins), §5 (per-source mapping), §8 (freshness), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §4 (classification registry — `restricted:<class>`), §5.2 (erasure/hold tombstone)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §5 (erasure/retention/legal-hold), §6 (audit), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, table-row chunking, parsers)](../../rag/00-retrieval-pipeline.md) · [Storage §7 (append-only audit store)](../../storage/00-storage-architecture.md) · [API §4, §5, §11](../../api/00-api-surface.md)
