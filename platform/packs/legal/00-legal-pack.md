# Domain Pack #3 — Legal (privilege, ethical walls & matter-scoped holds)

> **The third data point — and the first genuine falsifiability test since Finance.** n=2
> (Finance + HR) proved the [pack skeleton](../README.md) is *reusable*; Legal is chosen
> next because it is **near-mechanical in five of six sections** (it reuses HR's
> `matter:<id>`/hold shape and Finance's DMS/SharePoint fidelity) **while introducing the one
> concept the platform had never stress-tested: attorney-client privilege as a retrieval
> gate.** The sharp question is not "can privilege be a label" (obviously — like
> `restricted:mnpi`) but the one the [skeleton's falsifiability rule](../README.md#the-falsifiability-rule)
> exists to catch: *privilege can be **waived**, per matter, per recipient.* Does waiver force
> a **per-recipient dynamic policy the static label→action matrix cannot express** — a real
> horizontal gap → a Governance/Metadata ADR — or does it resolve to a mechanism the platform
> already has? **It resolves. See §0 and the "Privilege & waiver" analysis below — no
> horizontal change.**

- **Cycle:** 13 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — privilege/waiver fit the existing contract; had they *not*, this pack would have raised a horizontal ADR, which is the process working)
- **Regimes declared:** attorney-client privilege + work-product doctrine (bar/ethics rules), litigation hold / e-discovery (FRCP-shaped), GDPR, ISO 27001 / SOC 2, outside-counsel guidelines (OCG, sector)
- **Isolation tier (default):** Isolated ([Storage §5](../../storage/00-storage-architecture.md)) — privilege + ethical-wall blast radius

---

## Why Legal third (and why it is the right stress test)

n=1 proved the mechanism *exists*; n=2 proved it *generalizes* to a structurally different
domain. A third near-identical pack would again prove nothing new — so Legal earns its slot by
combining **maximum inheritance** with **exactly one genuinely new concept**, isolating that
concept as a clean experiment:

- **Attorney-client privilege is a *new kind of restriction*, and privilege *waiver* is the
  part most likely to crack the label lattice.** A static "who is privilege-cleared" set is
  trivially the existing set-membership predicate. But privilege can be **waived** — shared with
  a regulator under a *limited* waiver that must **not** extend to an adversary in separate
  litigation. If waiver were modeled as *removing* the `restricted:privileged` label, that would
  waive to **everyone** — a loosening the bet forbids. So the real test is whether "waived to X
  but still privileged against Y" needs **per-recipient dynamic policy** the static
  [label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen)
  cannot represent. (Answer: no — see "Privilege & waiver" below. Waiver is a *narrowing grant
  edit on the item ACL*, propagated by the existing change-driven re-sync; the label never
  moves. "Per recipient" is exactly what an ACL already **is**.)
- **Ethical walls (information barriers) are a *deny*, not a grant.** A lawyer conflicted off a
  matter must be **denied** its documents even though they hold the firm-wide role that would
  otherwise allow them. This is the sharpest test of the canonical model's
  **[deny-always-wins precedence](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)** —
  does an ethical wall fit the *existing* `deny` half of the predicate, or force a new
  barrier primitive? (Answer: it fits — a wall is a `deny` grant for a principal/group on a
  matter's items; deny-wins is already the first clause of the decision function.)
- **Legal *owns* the litigation-hold concept HR merely borrowed.** `matter:<id>` +
  `legal_hold` is HR's inherited shape; Legal is where it is native, exercising
  `legal_hold > erasure > retention` under real e-discovery preservation duties.
- **The platform must *mirror* privilege, never *compute* it.** Subject-matter waiver (does
  sharing D1 waive privilege on related D2?) is a **legal determination**, not an access-control
  inference. The platform stays a faithful mirror of the source ACL — if a DMS exposes privilege
  as a computed/dynamic rule not resolvable to a principal set, that is the *same*
  `approximate → deny + quarantine` path Finance used for SAP field-level auth.

If any of these forced a horizontal change, that would be the headline finding. **None did** —
see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Legal? | What Legal did instead |
|--------------------|:-------------------------:|------------------------|
| Permissions (canonical model, `map_acl`) | **None** | Privilege-clearance = the existing `allow ∩ principals ≠ ∅` set-membership predicate; **ethical walls = the existing `deny`-wins clause** ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)); **privilege waiver = a narrowing grant edit on the item ACL**, propagated by the *existing* change-driven re-sync ([Workers §5](../../workers/00-ingestion-architecture.md)) — no per-recipient dynamic policy, no new predicate; a DMS that only exposes privilege as a computed rule rides the *existing* §9 quarantine / §10 OBO hatch |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `restricted:privileged`, `restricted:work_product` into the existing `restricted:<class>` extension point ([§4.1](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)); reused `matter:<id>` (HR/Finance) for holds |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** the matrix for `restricted:privileged`/`work_product`; **inherited** the GDPR row + expressed litigation-hold as the existing `legal_hold`-precedence rule |
| RAG (chunking, hybrid, verifier) | **None** | Supplied clause/section parsers behind the *existing* structure-aware seam; supplied an eval set whose headline classes are **privilege negatives** and **waiver correctness** |
| Storage / Workers / API / Deployment | **None** | Chose the *existing* Isolated tier; connector rides the *existing* staged DAG; reuses Finance's DMS/SharePoint fidelity; API `pack:"legal"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** The headline: the one concept most likely to
force a horizontal primitive — **privilege waiver** — resolved to the *composition of two
mechanisms the platform already has*: the label stays put (it governs *what* the restriction
means), and the item ACL is edited to add/remove the cleared principal (it governs *who*).
Waiver is a `who`-change, not a `what`-change, so it rides the existing permission-mutation
path. Per [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit
to this pack adds a "required" row, that edit needs a horizontal ADR.

---

## Privilege & waiver — the falsifiability analysis (the reason this cycle exists)

This is the section a reviewer should read first; it is the whole point of choosing Legal.

**The claim under test.** *"Attorney-client privilege, including per-matter/per-recipient
waiver, is expressible as additive pack data + policy — it does not force a new horizontal
mechanism."*

**Decomposition — separate *what* from *who*:**

1. **Privilege as a restriction (`what`) — a label.** `restricted:privileged` is a §2 registered
   value and a §3 tighten delta: Isolated model pool only, never egresses, masked from any
   principal not in the cleared set. This is structurally identical to `restricted:mnpi`
   (Finance). *Additive.*
2. **Who is privilege-cleared (`who`) — the item ACL.** The set of principals allowed to see a
   privileged item (the client team + retained counsel) is exactly a per-item `allow` set — the
   canonical model's existing shape. *Additive.*
3. **Ethical wall (`who`, negative) — a `deny` grant.** A conflicted attorney is added to the
   item's/matter's `deny` set; deny-wins ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins))
   already evaluates first, before any allow. *Additive — the existing first clause of the
   predicate.*
4. **Waiver (`who`, mutation) — a narrowing grant edit, propagated by re-sync.** When counsel
   waives privilege *to a specific recipient X on matter M*, the source-of-record ACL gains X's
   CPI in the cleared/`allow` set for the affected items. The connector re-maps it; the
   [change-driven re-sync](../../workers/00-ingestion-architecture.md) (P1, or P0 if it is a
   *restriction* change) propagates it within the freshness SLA; query-time principal precedence
   ([Permissions §8](../../permissions/00-authorization-model.md#8-freshness-the-stale-permission-problem-r3))
   makes it effective immediately regardless of chunk re-tag. *Additive — the existing
   permission-mutation path, the same one an offboarding or a new share uses.*

**Where it *could* have broken — and the discipline that keeps it additive.** The trap is
modeling waiver as **label removal** (delete `restricted:privileged`). That would waive to
*everyone at once* — a limited waiver to a regulator would silently become a global waiver
reachable by an adversary. That is a **loosening of a floor** and is forbidden. Legal therefore
carries **one pack-local discipline (not a mechanism):**

> **Waiver is *always* modeled as a narrowing edit to the item's cleared-principal set, and
> *never* as removal of the `restricted:privileged` label.** The label is permanent for the
> life of the document; waiver only ever *adds a specific principal* to the cleared set (or, for
> a broad/subject-matter waiver counsel explicitly decides, adds a broader group). "Per
> recipient" is expressed as "which CPIs are in the cleared set," which is what an ACL is.

Because "per recipient" is native to ACLs, the static label→action matrix never has to encode
recipient-specific policy — it only ever says *"`restricted:privileged` → Isolated pool, no
egress, cleared-set-only."* The *cleared set* is data on the item, not policy in the matrix.
**No per-recipient dynamic policy is required, so no horizontal gap exists.**

**The one thing the platform must *refuse* to do.** The platform does **not compute** whether a
disclosure waives privilege (subject-matter waiver is a legal judgment). Counsel decides;
the DMS/matter system's ACL reflects the decision; the platform mirrors it. If a source exposes
privilege only as a *computed* rule the connector cannot resolve to a principal set, that item
takes the existing `approximate → deny + quarantine` path
([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
identical to SAP field-level auth. Refusing to *infer* privilege is what keeps the platform a
faithful ACL mirror rather than a legal-reasoning engine that could leak on a wrong inference.

**Verdict:** the bet holds against its first genuinely novel concept. The falsifiability rule
was armed and did **not** fire. Had waiver required per-recipient matrix policy, this section
would instead be a horizontal ADR proposal against [Governance §4](../../governance/00-governance-and-audit.md) —
that it is not is the finding.

---

## §1 — Sources & `map_acl` fidelity

Legal sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)).
Anything below `exact` is **denied on the shared retrieval path** and quarantined to the
Isolated tier ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
Unlike SAP, a legal **DMS carries a rich per-document ACL** — Legal is *fidelity-friendly*; the
novel cases are the **ethical wall** (a `deny`) and **waiver propagation** (a grant edit).

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **DMS — iManage / NetDocuments** | Document in a matter workspace | `allow = {user/group CPIs on the workspace security}`; **ethical wall → `deny = {walled principals}`**; MIP/DMS label → `sensitivity` | `exact` when workspace security + walls are fully read as principal sets | Per-document ACL + walls are first-class here — [§5.1-shaped](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365); wall = existing deny-wins ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)) |
| **DMS** | Item under a *computed* privilege rule (dynamic barrier not resolvable to a principal set) | — | `approximate` → **deny + quarantine** (or native OBO §10) | The Legal analogue of SAP field-level auth — the platform never *fakes* a privilege grant |
| **Matter / practice-management system** | Matter membership + litigation-hold custodian list | matter-team CPIs → `allow`; `matter:<id>` + `legal_hold` from the hold register | `exact` if membership + hold status are readable grants | Reuses HR's `matter:<id>`/hold shape natively |
| **SharePoint** (M365) | Legal-team site / policy doc (per-item ACL) | Entra objectId → CPI; broken inheritance respected; MIP label → `sensitivity` | `exact` when item-level perms fully read | Reuses Finance/HR SharePoint fidelity verbatim — [§5.1](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365) |
| **Email / Exchange** | Privileged correspondence, counsel threads | Mailbox owner + explicit delegates; per-message ACL; privilege label per message | `exact` per message; thread never retro-grants | Counsel↔client threads are `restricted:privileged` — [§5.3](../../permissions/00-authorization-model.md#53-email--exchange) |

**Conformance fixtures (the production gate).** The Legal connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any Legal source goes live:

1. **Ethical-wall (deny-wins):** an attorney holding the firm-wide legal role but on matter M's
   wall **cannot** retrieve M's documents — the `deny` overrides the `allow` (positive control:
   a non-walled attorney *can*).
2. **Privilege positive + negative:** a client-team member retrieves a `restricted:privileged`
   memo; a principal outside the cleared set **cannot**, and it is **masked**, never partially
   leaked.
3. **Waiver as a narrowing grant edit:** after a limited waiver adds regulator-CPI to matter M's
   cleared set, regulator-CPI sees the waived documents **and** an adversary-CPI in separate
   litigation still **cannot** — and the `restricted:privileged` **label is still present**
   (waiver did not remove it). Propagates within the freshness SLA.
4. **Litigation-hold vs. erasure:** a `matter:<id>` + `legal_hold` document survives an erasure
   request (`legal_hold > erasure > retention`), proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4).
5. **Cross-tenant:** no Legal chunk of tenant A ever reaches tenant B (R4), inherited unchanged.

---

## §2 — Classification-registry values (the vocabulary Legal registers)

Legal **registers** these values into the tenant [classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
extension points — it does not invent new dimensions. An unregistered label is a write-boundary
schema violation → DLQ ([Workers §8.1](../../workers/00-ingestion-architecture.md)), never
silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:privileged` | Attorney-client privileged communications (counsel↔client legal advice) |
| `sensitivity` | `restricted:work_product` | Attorney work-product doctrine (materials prepared in anticipation of litigation) |
| `legal_hold` | `matter:<id>` | Any record under a litigation / e-discovery preservation hold **(reused verbatim from HR/Finance)** |

`restricted:privileged` and `restricted:work_product` slot into the existing lattice
(`public < internal < confidential < restricted:*`), so **most-restrictive-wins** composition is
inherited unchanged. A privileged litigation memo prepared in anticipation of suit, under an
active hold, resolves to `restricted:privileged` + `restricted:work_product` + `legal_hold:true`
— the most restrictive action of each dimension applies. **Neither is a new dimension** — both
are the `restricted:<class>` extension point the [Metadata schema](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
already defines, exactly as Finance registered `restricted:mnpi`.

> **Note on ethical walls (deliberately *not* a label).** A wall is **not** registered as a
> `sensitivity` value — it is a **`deny` grant** on the item ACL. Modeling it as a label would
> conflate *what the restriction is* with *who is barred*, and would lose the deny-wins
> semantics. Keeping the wall in the ACL is what lets it reuse the existing predicate unchanged.

---

## §3 — Label→action *tighten* deltas

Legal **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:privileged` | Only to principals in the item's **cleared set** (client team + retained counsel); **masked** for everyone else; ethical-wall `deny` overrides any allow | **Isolated model pool only**; masked in prompt unless the caller is in the cleared set | **Never** any external egress; **never** in batch/analytics export | Stricter than `confidential`: adds model-pool restriction + hard egress block + wall interaction (mirrors Finance `restricted:mnpi`) |
| `restricted:work_product` | Cleared-set-only, same as privileged | Isolated pool | No external egress; no batch export | Same shape as `restricted:privileged`; distinct label so a *waiver of privilege* need not waive *work-product* (they can be waived independently) |
| `legal_hold:true` (`matter:*`) | Unchanged (visibility unaffected) | Unchanged | **Never auto-deleted** — preservation override ([Governance §5.3](../../governance/00-governance-and-audit.md#53-legal-hold-overrides-erasure--retention)); e-discovery duty to preserve | Inherited from HR/Finance, not tightened |

**Waiver is expressed on the ACL, not in this matrix.** These rows are *static* — they never
mention a recipient. Who is cleared for a `restricted:privileged` item is the item's cleared set
(§1/§0), edited by counsel's waiver decision. This is precisely why waiver needs no matrix
change: the matrix governs *what the label permits*, the ACL governs *whom* — and waiver only
touches the latter.

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
Splitting privilege and work-product into two labels is a *tighten*/precision move (independent
waiver), never a grant.

---

## §4 — Compliance-map row(s) (declare + inherit)

Legal **inherits** the GDPR and ISO rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain)
and adds a **privilege/hold** binding over *existing* controls; it does not re-derive mechanism.
The evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | Legal-specific evidence binding |
|--------|-----------------------------------|--------------------------------|
| **Attorney-client privilege + work-product (ethics/bar rules)** | `restricted:*` label + cleared-set ACL + deny-wins walls + Isolated pool + egress block + append-only audit | Every privileged retrieval audit event names the cleared principal and the `restricted:privileged` label; **the waiver decision itself is an audited ACL-change event** (who waived, to whom, on which matter) — provable, not asserted |
| **Litigation hold / e-discovery (FRCP-shaped)** | `legal_hold`-precedence override + retention schedule + lineage tombstone | A `matter:<id>` hold blocks premature deletion; preservation completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4); reuses HR/Finance mechanism verbatim |
| **GDPR** | Right-to-erasure + DSAR; PII masking; residency; private-by-default; `legal_hold > erasure > retention` | Erasure of personal data honored *except* where a `matter:<id>` hold preserves it — the partial-erasure outcome proven by traversal, same as HR |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Isolated tier + per-tenant DEK for the Legal tenant |
| **Outside-counsel guidelines (OCG, sector)** | Isolated tier + residency routing + egress block | Client-mandated confidentiality/residency expressed as existing Isolated-tier + region-lock controls, no new mechanism |

**No new control was invented.** Legal's compliance posture is a *selection and binding* of
controls the platform already operates — including the **waiver-decision-as-audit-event**, which
is just the existing policy/ACL-change audit trail applied to a privilege waiver.

---

## §5 — Retrieval / answer eval set

The Legal pack supplies (a) the **parsers** that make its content retrievable and (b) the **eval
corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **Contracts / agreements** — **clause-level chunking** (reuses RAG's structure-aware
  heading/clause seam; a clause is a coherent, citable unit). The mixed-ACL invariant means a
  chunk never spans two documents with different cleared sets.
- **Briefs / memos / opinions** — heading/section chunking; `restricted:privileged` /
  `work_product` labels carried per section.
- **Privileged email** — per-message chunking (the ACL-carrying Item); privilege label per
  message; a thread never retro-grants across messages.

**Eval set (grounding · refusal · privilege negatives · waiver correctness):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Privilege permission negatives** | A principal outside the cleared set (incl. a walled attorney) cannot obtain `restricted:privileged` content via any cleverly-worded prompt | 0 leaks (a permission test, not an accuracy test) |
| **Waiver correctness** | After a *limited* waiver to recipient X, X retrieves the waived document **and** an adversary Y still cannot — waiver did **not** over-share, and the label is still present | 0 over-waiver on the held-out set |
| **Ethical-wall enforcement** | A walled attorney is denied matter-M documents even holding the firm-wide role (deny-wins) | 0 wall breaches |
| **Clause grounding** | A contract-clause answer ("what is the termination notice period?") traces to a cited clause; no invented term | 100% legal claims cited or the answer refuses |
| **Refuse-over-guess** | A question about a matter the caller can't access → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated legal fact | 0 fabrications on the held-out no-access set |
| **Hold vs. erasure correctness** | A `matter:<id>`-held document survives an erasure request while non-held personal data is erased | 0 deletion of held records; 0 retrieval of erased content |

A model that regresses on **privilege negatives**, **waiver correctness**, or **ethical-wall
enforcement** cannot be promoted for the Legal tenant — the same gate shape as HR/Finance,
retargeted to Legal's failure modes (which are dominated by *who*, not *accuracy*).

---

## §6 — Optional additive API `pack` hint

Legal callers **may** pass `"pack": "legal"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(e.g. prefer the Legal eval-tuned model, bias retrieval toward matter sources, apply clause-aware
chunking). It is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"legal"`
  but is outside a matter's cleared set (or is on its ethical wall) sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an
  authorization input, and it cannot override a wall.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the
  hint only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"legal"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7),
  not a breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Waiver-as-grant-edit vs. a "waiver mode."** Modeling waiver as a narrowing ACL edit (never a
  label removal) is less convenient than a "declare this matter waived" toggle, but the toggle is
  exactly the loosening that would turn a *limited* waiver into a *global* one. The extra
  discipline buys a hard guarantee that a limited waiver can never over-share — the correct trade
  for privilege.
- **Refusing to compute subject-matter waiver vs. helpfulness.** The platform will not *infer*
  that disclosing D1 waives privilege on D2; it mirrors counsel's decision as reflected in the
  source ACL. This means the platform is less "smart" about privilege than a legal-reasoning tool
  — deliberately, because a wrong waiver inference is a malpractice-grade leak, not a UX blemish.
- **Ethical walls as `deny` grants vs. a barrier subsystem.** Keeping walls in the existing
  deny-wins predicate (rather than a separate information-barrier engine) means wall correctness
  depends on the connector reading the wall as a resolvable principal set. Where a DMS exposes a
  wall only as a computed rule, that content is quarantined (the R1 trade), not approximately
  served.
- **Isolated tier by default vs. cost.** Legal defaults to Isolated (privilege + wall blast
  radius). More expensive than Shared, but the honest default; a Legal sub-tenant handling only
  broadly-`internal` policy/precedent content could graduate *down* — a placement decision, not a
  redesign.
- **Two labels (`privileged` + `work_product`) vs. one.** Splitting them adds a registered value
  but lets privilege be waived without waiving work-product (they are legally distinct and
  independently waivable) — precision that would otherwise force a special case.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Model waiver as removing the `restricted:privileged` label** | **Rejected — this is the trap.** Label removal waives to *everyone*; a limited waiver would silently become global and reach an adversary. Waiver must be a *narrowing edit to the cleared set*, label intact (§0, "Privilege & waiver"). |
| **Add a per-recipient dynamic privilege-policy engine to Governance** | Rejected: unnecessary. "Per recipient" is what an ACL already is; the static label→action matrix + the mutable item ACL cover waiver without recipient-specific matrix policy. Adding an engine would be the horizontal change the bet forbids. |
| **Model ethical walls as a new sensitivity label** | Rejected: a wall is a *deny* about *who*, not a *what*; it belongs in the deny-wins ACL predicate ([§3.1](../../permissions/00-authorization-model.md#31-precedence-deny-always-wins)), which already evaluates first. A label would lose deny semantics. |
| **Have the platform *infer* subject-matter waiver** | Rejected: waiver is a legal determination, not an access-control inference; a wrong inference leaks. The platform mirrors the source ACL; unresolvable computed privilege is quarantined (same as SAP field auth). |
| **A Legal-specific retrieval/privilege pipeline** | Rejected: would be a horizontal change. Legal rides the hybrid permission-filtered pipeline + clause-aware chunking (existing seam); only parsers + eval + registered labels + the waiver discipline are pack-local. |
| **Bespoke Legal compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): Legal inherits GDPR/ISO rows + binds privilege/hold evidence; re-deriving controls is the anti-pattern. |

## Future scalability

- **Audit pack** is now almost entirely inherited: Finance's SOX row + segregation-of-duties
  (another `deny`-grant application) + append-only evidence + Legal's `matter:<id>`/hold shape.
- **Knowledge Management** is the deliberate *inverse* stress next: broad `internal`, low
  restriction, high recall — does the pipeline *over*-refuse on open content? (A different failure
  mode than Legal's *who*-dominated one.)
- **A new Legal source** (e.g. a contract-lifecycle-management system, an e-discovery platform) =
  a new §1 row + fixtures; no pipeline change.
- **A new privilege-adjacent regime** (e.g. a jurisdiction's litigation-privilege variant) = a new
  §4 compliance row binding existing controls — no redesign.
- **Cross-border privilege / conflicting waiver rules** = a §3 residency-lock tighten + an
  Isolated-tier placement, expressed as existing controls.
- **A Legal-tuned model** enters through the existing eval gate (§5) and is routed by the existing
  label→trust policy — a config change, not a code change.

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack](../finance/00-finance-pack.md) · [HR pack](../hr/00-hr-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §3.1 (deny-wins), §4 (effective principals), §5 (per-source mapping), §8 (freshness), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §4 (classification registry — `restricted:<class>`), §5.2 (erasure/hold tombstone)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §5 (erasure/retention/legal-hold), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, clause chunking, parsers)](../../rag/00-retrieval-pipeline.md) · [Workers §5 (change-driven re-sync)](../../workers/00-ingestion-architecture.md) · [API §4, §5, §11](../../api/00-api-surface.md)
