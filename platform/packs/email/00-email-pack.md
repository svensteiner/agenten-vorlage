# Domain Pack #8 — Email / Exchange (the *last source pack* — the transport-vs-storage test)

> **The third and last source-shaped pack — and the simplest of all sources.** [SAP](../sap/00-sap-pack.md)
> was the hardest source (**no document ACL** → the whole story was *quarantine*).
> [SharePoint](../sharepoint/00-sharepoint-pack.md) was the easiest *document* source (**rich
> item-level ACL** → almost everything `exact`, but a sharing-link surface that tempts a silent
> *over*-grant). Email is simpler still: a message's ACL is just its **mailbox owner + explicit
> delegates**, and there is **no sharing-link surface at all**. Its one interesting trap is
> unique to messaging: the temptation to treat a message's **transport-time recipient set**
> (To / Cc / Bcc / distribution-list membership) as a **storage-time read grant** on the
> archived copy. This document is the **canonical Email / Exchange `map_acl` reference** that
> HR, Legal and Audit cite instead of re-deriving — all three already read email (grievance
> mail, privileged mail, the audit correspondence trail).

- **Cycle:** 18 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- **Regimes declared:** *none of its own* — Email **inherits** whatever regime the domain riding on it demands (GDPR for HR-on-email, attorney-client privilege for Legal-on-email, SOX/PCAOB for Finance-/Audit-on-email, ISO 27001 / SOC 2 baseline for all)
- **Isolation tier (default):** inherited from the riding domain; a message whose mailbox delegate set could not be fully resolved always lands on the [Isolated/quarantine tier](../../storage/00-storage-architecture.md) regardless

---

## Why Email, and why it is the *transport-vs-storage* falsifiability test

The five concept packs (Finance/HR/Legal/Audit/KM) asked *"does a new **policy** concept
fit?"* The two prior source packs asked the source-shaped version: SAP — *"can the **hardest
source's** entire authorization model be served-or-quarantined with no fourth case?"*;
SharePoint — *"can the **most permissive** source's every sharing construct be mapped without a
silent over-grant?"* Email asks the **narrowest, sharpest** source-shaped question:

> **Can every Exchange access construct — mailbox ownership, delegate access, shared mailboxes,
> Send-As / Send-on-Behalf, per-message thread ACLs, distribution-list membership — be mapped to
> the canonical model *without ever treating a message's transport-time audience as a
> storage-time read grant*, and without inventing a new principal category or a new predicate?**

Email is the right source to ask this of because messaging is where **transport and storage are
easiest to conflate**, and conflating them is precisely a silent *over*-grant (the same failure
family SharePoint stressed, reached by a different mechanism):

- **The archived copy's ACL is the *mailbox it lives in*, not the message's original audience**
  ([Permissions §5.3](../../permissions/00-authorization-model.md#53-email--exchange)). A message
  is granted to its **mailbox owner** and explicit **delegates**; **distribution-list membership
  does *not* grant read to the archived copy** unless the source system says so, and a
  **forwarded/quoted thread does *not* retroactively grant earlier recipients**. Each message
  keeps its own ACL.
- **It is a broadly-reused *correspondence* source.** HR (grievance mail), Legal (privileged
  mail), Audit (the correspondence trail) all read email. Until now that fidelity was asserted
  **three times, ad hoc**. Cycle 18 consolidates it into **one canonical §1** — the same DRY win
  SAP did for its module set and SharePoint did for its sharing constructs.

If any Exchange construct produced access the canonical model could not represent **without
either a new principal type or a silent grant from a transport fact**, that would be a real
**R1/R4** gap → a horizontal Permissions ADR, **not** a pack-local hack (the
[falsifiability rule](../README.md#the-falsifiability-rule)). **None did** — every construct
maps to an explicit `allow`, a `deny`, or a quarantine (§1). See §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Email? | What Email did instead |
|--------------------|:-------------------------:|------------------------|
| Permissions (canonical model, `map_acl`) | **None** | **Consolidated** the existing [§5.3 Email/Exchange rules](../../permissions/00-authorization-model.md#53-email--exchange) into a **construct-by-construct fidelity matrix** (§1). Every construct maps to an explicit `allow` (mailbox owner / delegate / shared-mailbox delegate set), a `deny` (revoked delegate), or a quarantine (unresolvable delegate set). A distribution-list / To-Cc-Bcc audience is **not** a grant on the archived copy → no over-grant. No new principal category, no new predicate |
| Metadata (label schema, catalog, lineage) | **None** | **§2 is empty.** A message carries no native sensitivity label of its own; whatever label applies (`confidential`, `restricted:privileged`, `pii_class:health`) is registered by the *domain* riding on it. The [Item](../../metadata/00-catalog-and-lineage.md#3-the-catalog-schema-m1) = one message (its own ACL), so the **mixed-ACL invariant** already covers per-message thread breaks |
| Governance (label matrix, SLA, retention) | **None** | **§3 is empty.** A source tightens no policy; the riding domain's tighten-deltas apply to its email-sourced content unchanged. Litigation-hold on a mailbox is the *existing* `legal_hold`/`matter:<id>` mechanism ([Legal §3](../legal/00-legal-pack.md)), surfaced from Exchange, not a new rule |
| RAG (chunking, hybrid, verifier) | **None** | Reuses the **existing** per-email-message chunker behind the per-content-type seam; the **mixed-ACL invariant** ([RAG §2.2](../../rag/00-retrieval-pipeline.md)) is *exactly* the per-message-in-a-thread guard; supplied a transport-vs-storage over-grant eval set |
| Storage / Workers / API / Deployment | **None** | Rides the *existing* staged DAG; Exchange/Graph **change notifications + mail delta** are the *existing* `subscribe_changes` feed ([Connector §4](../../workers/01-connector-framework.md)); an unresolvable delegate set = the *existing* quarantine tier; `pack:"email"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** Email is the **fourth pack with an empty §2 and
§3** (after [KM](../km/00-km-pack.md), [SAP](../sap/00-sap-pack.md) and
[SharePoint](../sharepoint/00-sharepoint-pack.md)) — for the same structural reason as the other
two source packs: **a source-shaped pack carries no policy of its own.** Per
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit adds a
"required" row, that edit needs a horizontal ADR.

---

## The transport-vs-storage analysis — the falsifiability test (the point of this cycle)

This is the section a reviewer should read first; it is the whole reason to seed Email.

**The claim under test.** *"Every Exchange access construct is representable in the canonical
model as an explicit `allow` to a real CPI (mailbox owner, delegate, or shared-mailbox delegate
set), an explicit `deny` (a revoked delegate), or a sub-`exact` mapping the confidence gate
quarantines — and a message's transport-time audience (To/Cc/Bcc, distribution-list membership,
a forwarded thread's earlier recipients) is **never** silently promoted to a read grant on the
archived copy. There is no construct that needs a new principal category or a new predicate."*

Where a naive connector would leak, and why the canonical model does not:

### 1. The archived copy's ACL = its mailbox, not the message's audience
A message stored in Alice's mailbox is granted to **Alice (mailbox owner) + Alice's delegates**
([Permissions §5.3](../../permissions/00-authorization-model.md#53-email--exchange)). It is
**not** granted to everyone on the original To/Cc line, and **not** to the members of a
distribution list the message was sent to. Those are *transport* facts (who received a copy at
send time), not *storage* facts (who may read *this archived copy*). A connector that expanded
the DL into `allow`s would silently over-grant every list member read access to one mailbox's
archive — the email analogue of SharePoint's "anyone"-link trap. **The connector maps only the
mailbox's own ACL; the audience is captured as *content* (headers), never as a grant.** `exact`.

### 2. Per-message thread ACLs → the mixed-ACL invariant, not a thread-wide grant
A thread is a sequence of messages; **each message keeps its own ACL**
([Permissions §5.3](../../permissions/00-authorization-model.md#53-email--exchange)). A
forwarded or quoted thread does **not** retroactively grant its earlier recipients read to a
later archived copy, and a later reply landing in a new mailbox does not widen the earlier
messages. The [Item](../../metadata/00-catalog-and-lineage.md#3-the-catalog-schema-m1) is the
**single message**, and the [mixed-ACL invariant](../../rag/00-retrieval-pipeline.md) —
"a chunk never spans two items with different ACLs" — is *exactly* the guarantee that a chunk
never fuses two thread messages with different mailbox ACLs. **The per-email-message chunker
already exists** (RAG §2.2 names it); Email adds fixtures, not machinery. `exact`.

### 3. Delegate access, Send-As, Send-on-Behalf, Full-Access → explicit `allow`s
Exchange **delegate** and mailbox-permission constructs (Full Access, Send As, Send on Behalf)
resolve to real directory principals with stable objectIds → ordinary
`<tenant>:aad:user:<objectId>` CPIs ([Permissions §4.1](../../permissions/00-authorization-model.md#41-inputs)).
A **Full-Access delegate** is an `allow` on the mailbox's messages; a **removed delegate** is a
`deny` / grant removal propagated by the existing change-driven re-sync
([Workers §5](../../workers/00-ingestion-architecture.md)). Send-As / Send-on-Behalf are *write*
(compose) rights with **no read implication** for the platform — the platform is
[read-only](../../architecture/adr/ADR-0001-platform-shape-private-rag.md), so it mirrors only
the **read** grant (Full Access / owner), never a send right. `exact`. No new principal category.

### 4. Shared mailboxes → a principal-set expansion (Band A `exact`)
A **shared mailbox** grants read to its **delegate set** — an ordinary static principal-set
expansion, identical in shape to expanding an M365 group ([SharePoint §1](../sharepoint/00-sharepoint-pack.md#1--sources--map_acl-fidelity-the-canonical-sharepoint-reference)):
resolve the delegate set → CPIs → `allow[]`. If (and only if) that delegate set is itself
governed by a **dynamic/rule-based group**, it takes the *existing* [SAP Band B](../sap/00-sap-pack.md#band-b--structural--dynamic-authorization--resolve-or-quarantine)
path — pre-resolve + `list_principal_changes`, else quarantine. The default shared-mailbox case
is static → **Band A `exact`**. No new machinery.

### 5. Distribution lists → membership is *not* a read grant on the archive
A **distribution list (DL)** is a transport construct: sending to `all-hands@` delivered a copy
into each recipient's mailbox, but **DL membership does not grant read to any single archived
copy** ([Permissions §5.3](../../permissions/00-authorization-model.md#53-email--exchange)) —
unless the source system explicitly models it as a shared/journal mailbox with its own ACL, in
which case it is case 4 (a shared mailbox), mapped on *its own* delegate set. Membership alone →
**no `allow`**. This is the one construct most likely to force a silent over-grant, and the
canonical model handles it by **refusing to derive a storage grant from a transport fact**. No
new predicate.

### 6. Mailbox / message perms not fully readable → quarantine (the one hard floor)
`acl_confidence = exact` **only when the mailbox's effective delegate/permission set was fully
read**. Graph throttling, an unresolvable delegate principal, or a mailbox-permission API gap ⇒
`approximate` ⇒ **denied on the shared path + quarantined**
([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
A partially-read mailbox ACL is never rounded up to `exact`.

**Why there is no silent over-grant, and no new predicate.** Every Exchange construct is one of:
(a) an explicit `allow` to a real CPI (mailbox owner, delegate, or shared-mailbox delegate set)
→ served; (b) an explicit `deny` (revoked delegate) → deny-wins; (c) a dynamic delegate set →
resolve-or-quarantine (Band B); or (d) an unreadable mailbox ACL → quarantine. The three
constructs that *look* like they might widen access — the To/Cc/Bcc audience, a forwarded
thread, and distribution-list membership — are all **transport facts captured as content, never
as grants.** The canonical model needs **no "recipient" predicate and no new principal
category.** The rule was armed against a *transport-to-storage widening* and did **not** fire.

**No Band-C (sub-Item) case.** Like SharePoint, Email's ACL never lives *below* the ACL-carrying
Item: the message (with its attachments) *is* the unit that carries the permission. An attachment
inherits its message's ACL. That absence is the structural reason this matrix is short.

---

## §1 — Sources & `map_acl` fidelity (the canonical Email reference)

The construct-by-construct fidelity matrix. This table is what HR/Legal/Audit cite instead of
re-deriving Exchange mapping. **Max `acl_confidence`** is what the connector may declare per
[Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract).

| Source construct | Principal / grant mapping | Outcome | Max `acl_confidence` |
|------------------|---------------------------|---------|:--------------------:|
| **Mailbox owner** | Owner → CPI by objectId | `allow[]` | `exact` |
| **Delegate / Full-Access mailbox permission** | Delegate principal → CPI | `allow[]` | `exact` |
| **Revoked delegate** | The removed delegate | `deny[]` / grant removal (deny-wins) | `exact` |
| **Shared mailbox (static delegate set)** | Expand delegate set → CPIs | `allow[]` | `exact` |
| **Shared mailbox governed by a dynamic group** | Pre-evaluated delegate set, re-synced on group-change | `allow[]` if resolvable within SLA; else deny + quarantine | `exact` within SLA; else **quarantine** |
| **Send-As / Send-on-Behalf** | (compose/write right) | **no read `allow`** (platform is read-only) | n/a (not a read grant) |
| **To / Cc / Bcc recipient set** | (transport audience) | captured as **header content**, **not** a grant | n/a (content, not ACL) |
| **Distribution-list membership** | (transport delivery) | **no `allow`** on the archived copy | n/a (transport, not storage) |
| **Journal / shared archive mailbox** | Mapped on **its own** delegate set (case = shared mailbox) | `allow[]` | `exact` |
| **Per-message thread ACL** | Each message = one Item, its own mailbox ACL | `allow[]` per message (mixed-ACL invariant) | `exact` |
| **Mailbox whose delegate/perm set could not be fully read** | — | `approximate` → deny + quarantine | `approximate` → quarantine |

**No Band-C (sub-Item) row** and **no sharing-link row** — Email is the shortest source matrix:
its ACL is item-level (the message) *and* it has no anonymous/sharing-link surface, so it carries
neither SAP's Band-C quarantine story nor SharePoint's flagged-grant story.

**Conformance fixtures (the production gate).** The Email connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate),
weighted toward the **transport-vs-storage over-grant** failure mode:

1. **Distribution-list non-grant** — a message sent to a DL is **not** served to an arbitrary
   DL member who is not a delegate of the mailbox it is archived in (membership ≠ read grant).
2. **Thread-audience non-widening** — an earlier message in a forwarded thread is **not**
   served to a later recipient who was not on the earlier message's mailbox ACL (each message
   keeps its own ACL).
3. **To/Cc/Bcc non-grant** — being on the recipient line of a message archived in someone
   else's mailbox does **not** grant read to that archived copy.
4. **Delegate positive/negative** — a Full-Access delegate *can* read; a revoked delegate
   *cannot*, within the freshness SLA (deny-wins, query-time principal precedence).
5. **Shared-mailbox delegate-set correctness** — the shared mailbox is served to exactly its
   delegate set, no more.
6. **Dynamic delegate-set freshness (Band B)** — removing a user from a rule-governed shared
   mailbox's group revokes access within the [freshness SLA](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table).
7. **Not-fully-read quarantine** — a mailbox whose permissions could not be enumerated is
   **quarantined**, never served at `exact`.
8. **Cross-tenant isolation (R4)** — a mailbox principal of tenant A is never a principal of
   tenant B; a cross-tenant query returns nothing.
9. **Revocation** — removing a delegate revokes access within the SLA, independent of chunk re-tag.

---

## §2 — Classification-registry values

**Empty — by design.** A message carries no native sensitivity vocabulary of its own. Whatever
label applies to email-sourced content (`confidential`, `restricted:privileged`,
`pii_class:health`, `legal_hold`+`matter:<id>`) is registered by the **domain pack riding on it**
([Legal §2](../legal/00-legal-pack.md), [HR §2](../hr/00-hr-pack.md)) and by the platform
classification rules. A source pack that invented its own vocabulary would be claiming policy
that isn't the source's to hold — the same rule as [SAP](../sap/00-sap-pack.md#2--classification-registry-values)
and [SharePoint](../sharepoint/00-sharepoint-pack.md#2--classification-registry-values). Where
Exchange *does* surface a signal (an Exchange sensitivity/retention/hold tag), the connector
**carries** it into the label channel; it does not **own** the value. The empty table is the
evidence.

---

## §3 — Label→action *tighten* deltas

**Empty — by design.** A source tightens no policy. Email-sourced content is governed by the
tighten-deltas of the **riding domain** ([Legal §3](../legal/00-legal-pack.md),
[HR §3](../hr/00-hr-pack.md)) applied to its labels unchanged. The one thing Email *does* enforce
beyond a plain grant — **refusing to promote a transport audience to a grant** and **quarantining
not-fully-read mailboxes** — are the **existing** canonical-model rule and confidence-gate floor,
not new tighten rules. The
[label-can-only-subtract invariant](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)
is preserved trivially because Email adds no label rule of its own.

---

## §4 — Compliance-map row(s) (declare + inherit)

Email declares **no regime of its own**; it **inherits** the regime of whatever domain rides on
it, and contributes **one source-specific evidence binding** that strengthens every inherited
row: an email-sourced answer's retrieval audit event carries the **mailbox + internetMessageId +
`source_item_version` (Graph message change-key)**, so the answer is reproducible and any
over-share risk is attributable to a specific message state in a specific mailbox.

| Regime | Inherited from (riding domain) | Email-specific evidence binding |
|--------|-------------------------------|---------------------------------|
| **GDPR** | [HR](../hr/00-hr-pack.md) | `pii_class:*` masking proven per query; erasure completeness across archived copies proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4); a message maps to its mailbox owner, so subject-scoping is auditable |
| **Attorney-client privilege** | [Legal](../legal/00-legal-pack.md) | Ethical-wall `deny` grants honored deny-wins; a privileged message's ACL is its mailbox + delegates, never its transport audience — so privilege is not waived by a Cc line |
| **SOX / PCAOB** | [Finance](../finance/00-finance-pack.md) / [Audit](../audit/00-audit-pack.md) | A cited email traces to mailbox + internetMessageId + change-key; litigation-hold (`legal_hold`+`matter:<id>`) surfaced from Exchange hold, `legal_hold > erasure > retention` |
| **ISO 27001 / SOC 2** | any | Isolated tier + per-tenant DEK; read-only Graph mail credential, per-tenant, per-connector ([Connector §7](../../workers/01-connector-framework.md)); transport-vs-storage discipline = a reportable no-over-grant control |

**No new control was invented.** Email's compliance posture is entirely *inherited* — its one
native contribution is **evidence** (mailbox / message-id / change-key), not policy.

---

## §5 — Retrieval / answer eval set (the reusable Email assets)

Where a source-shaped pack contributes reusable engineering assets — the **parser** and the
**over-grant eval set** — rather than policy.

**Parsers (existing per-content-type seam — [RAG](../../rag/00-retrieval-pipeline.md)):**
- **MIME / RFC-822 message parsing** (headers, body parts, quoted-thread boundaries, attachments)
  rides the **existing** per-email-message chunker; the **mixed-ACL invariant** is the parser's
  hardest job — split a thread into per-message items so a chunk never fuses two mailbox ACLs
  (already the pipeline default). Attachments are parsed by the existing content-type parsers
  (PDF/Office) and inherit the message's ACL. Email contributes **fixtures**, not a new parser
  (unlike SAP, which promoted the table-serialization parser).

**Eval set (the source-shaped headline: *no transport-to-storage over-grant*):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Transport-vs-storage over-grant negatives** | No DL membership, To/Cc/Bcc audience, or forwarded-thread recipient silently gains read to an archived copy | **0** silent over-grants |
| **Per-message thread correctness** | Each message's own mailbox ACL is enforced; no thread-wide widening | 100% per-message ACL match |
| **Delegate / shared-mailbox correctness** | The mailbox is served to exactly its owner + delegate set | 100% delegate-set match |
| **Dynamic delegate-set freshness (Band B)** | A membership change revokes access within SLA | 0 stale grants past SLA |
| **Not-fully-read quarantine** | A mailbox with unreadable perms is quarantined, never served at `exact` | 0 approximate items served |
| **Over-refusal / recall** ([KM lens](../km/00-km-pack.md)) | A legitimate delegate *does* get the mail they may read | 0 false refusals on entitled mail |
| **Grounding + citation** | Every answer cites the mailbox + message it came from | 100% cited or refuse |

A model or connector version that regresses on **transport-vs-storage over-grant negatives**
cannot be promoted for any email-sourced tenant — the same gate shape as the connector
conformance canary, applied to the *widening* failure mode.

---

## §6 — Optional additive API `pack` hint

Email callers **may** pass `"pack": "email"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(bias retrieval toward mail sources, prefer the email-tuned eval profile). Like SAP and
SharePoint, it is even more purely optional than a domain pack's hint, because **Email is a
source, not a domain**: a caller almost always asks *as HR*, *as Legal* or *as Audit* and the
email-sourcing is incidental. The hint is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"email"`
  but holds no mailbox grants sees nothing ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)).
  In particular the hint **never** promotes a transport audience (a DL, a Cc line) to a grant.
- **Omitting it is valid.** The platform infers email context from the accessible sources.
- **Not a version event** — [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7).

---

## Trade-offs

- **Refusing transport-as-grant vs. best-effort availability.** Not treating DL membership or a
  Cc line as a read grant means some content a recipient *did* receive is not retrievable to them
  *from another mailbox's archive* — they can only read the copy in a mailbox they own or are a
  delegate of. This trades recall for a hard no-silent-over-grant guarantee — the correct trade
  (**R4/R1**), and structurally the same trade SharePoint made on "anyone" links.
- **Per-message thread splitting cost.** Splitting every thread into per-message items (so a
  chunk never fuses two mailbox ACLs) is more parsing work than indexing a thread as one blob.
  Accepted: indexing a thread as one ACL is precisely the thread-wide over-grant bug this pack
  exists to prevent.
- **Dynamic delegate-set point-in-time resolution vs. staleness.** Identical trade to SAP Band B
  and SharePoint dynamic groups — pre-evaluation buys `exact` shared-path serving, bound to the
  freshness SLA; query-time principal precedence backstops revocation independent of the re-eval.
- **A canonical source pack vs. per-pack email notes.** Consolidating fidelity here means
  HR/Legal/Audit cite one reference instead of restating it — a DRY win, at the cost of one more
  cross-pack link to keep consistent.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Treat To/Cc/Bcc recipients or DL members as `allow`s on the archived copy** | Rejected: silently widening every archived copy to its transport audience is exactly the R4/R1 over-grant leak. The audience is captured as header *content*; the ACL is the mailbox. |
| **Index a thread as one Item with a merged ACL** | Rejected: a forwarded/quoted thread must not retroactively grant earlier recipients. Each message is its own Item; the mixed-ACL invariant enforces it. |
| **Add a "recipient" or "audience" principal category to the canonical model** | Rejected: a horizontal predicate change. A recipient set is transport content, not a storage grant — no new category needed. |
| **Mirror Send-As / Send-on-Behalf as a read grant** | Rejected: those are *write* (compose) rights; the platform is read-only and mirrors only the read grant (Full Access / owner). |
| **A dedicated Email retrieval pipeline** | Rejected: a horizontal change (the thing the bet forbids). Email rides the hybrid permission-filtered pipeline and the existing per-message chunker unchanged; only the fidelity fixtures + eval set are pack-local. |

## Future scalability

- **A new messaging surface** (Teams chat/channel messages, Slack, chat archives) = a new §1
  matrix row for its ACL construct + fixtures; no pipeline change. The transport-vs-storage
  analysis already classifies each (a channel membership is a real `allow`; a @-mention or a
  broadcast audience is transport content, not a grant).
- **A new Exchange construct** (a future mailbox-permission type) = a new matrix row mapped to
  `allow` / `deny` / quarantine; the outcomes are exhaustive by construction.
- **The source-pack surface is now complete.** With Finance/HR/Legal/Audit/KM (concept-shaped)
  and SAP/SharePoint/Email (source-shaped) seeded, the remaining packs — **Document Intelligence**
  and **Reporting** — are *concept-shaped reuse* against the same skeleton, and the **runtime
  pack-load SPI** (open Q#6-adjacent) becomes the primary remaining track.
- **The one case that would force a horizontal ADR** — an Exchange construct that cannot be
  mapped to an explicit grant, a deny, or a quarantine *without* deriving a storage grant from a
  transport fact — is now named explicitly; none found across mailbox ownership, delegates,
  shared mailboxes, Send-As/Send-on-Behalf, per-message thread ACLs, or distribution lists.

## Related
- [Pack skeleton & the falsifiability rule](../README.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [SAP pack — the 1st source-shaped pack (quarantine story)](../sap/00-sap-pack.md)
- [SharePoint pack — the 2nd source-shaped pack (over-grant story)](../sharepoint/00-sharepoint-pack.md)
- [Permissions §5.3 (Email/Exchange), §9 (quarantine), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Connector §2 (`map_acl`), §4 (change notifications/delta), §7 (least-privilege credential)](../../workers/01-connector-framework.md)
- [RAG §2.2 (per-email-message chunking, mixed-ACL invariant)](../../rag/00-retrieval-pipeline.md)
- Packs that ride this one: [HR](../hr/00-hr-pack.md) · [Legal](../legal/00-legal-pack.md) · [Audit](../audit/00-audit-pack.md)
