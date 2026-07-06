# Domain Pack #9 — Document Intelligence (OCR, extraction & platform-*derived* content)

> **The ninth pack — and the first *concept-shaped* pack since KM (Cycle 15), chosen to stress
> the one thing eight prior packs never did: content the platform *derives itself* rather than
> reads from a source.** Finance/HR/Legal/Audit/KM stressed *policy* concepts; SAP/SharePoint/Email
> stressed *source `map_acl` fidelity*. Every one of them handled content whose ACL and labels were
> **read from the source of record**. Document Intelligence inverts the input: OCR text, extracted
> tables/entities/key-value pairs, and a **classification the platform *infers*** (a `pii_class` a
> classifier assigns, not one iManage or SAP declared). The sharp question the
> [skeleton's falsifiability rule](../README.md#the-falsifiability-rule) exists to catch: *when the
> platform manufactures a new artifact, where does its **ACL** come from, and can a **derived label**
> be trusted like a source-declared one — or does a platform-derived ACL/label force a new predicate,
> a new store, or a loosened floor?* **It resolves additively. See §0 and the "Derived content"
> analysis below — the one Metadata extension point it touches (`LineageNode.kind`) is the additive
> growth point [Metadata §9](../../metadata/00-catalog-and-lineage.md) already named for exactly this
> case, not a contract change.**

- **Cycle:** 19 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — derived content fits the existing contract; had a derived ACL needed *computing*, this pack would have raised a horizontal ADR against Metadata/Permissions, which is the process working)
- **Regimes declared:** GDPR (inferred/incidental PII is the headline), EU AI Act (automated content classification transparency), ISO 27001 / SOC 2; **inherits** the riding domain's regime (a DocIntel pipeline over Finance scans inherits SOX; over HR, Art. 9)
- **Isolation tier (default):** inherits the *source* Item's tier — a DocIntel artifact is never placed more openly than the document it was derived from ([Storage §5](../../storage/00-storage-architecture.md))

---

## Why Document Intelligence ninth (and why it is the right stress test)

The eight prior packs share an unstated assumption worth making explicit precisely so it can be
tested: **every artifact's ACL and every artifact's label were *read from* a source of record.** The
canonical model ([ADR-0008](../../architecture/adr/ADR-0008-canonical-principal-acl-model.md)) is a
faithful *mirror* — it never *manufactures* an authorization fact. Document Intelligence is the first
pack where the platform manufactures the *content itself*, which raises two manufacturing questions:

- **When the platform derives an artifact (OCR a scan, extract a table, resolve an entity), what
  ACL does the derived artifact carry?** A derived artifact has no source-declared ACL of its own —
  the OCR text layer of a scanned contract was *produced by the platform*, not stamped by iManage.
  If the pipeline had to **compute** a fresh ACL for it, that would be a new predicate the bet
  forbids. (Answer: it does **not** compute one — a derived artifact **inherits** the ACL of the
  source Item on its backward-lineage path, by construction. See "Derived content" §0-analysis.)
- **When the platform *infers* a classification (a classifier assigns `pii_class:health` to OCR'd
  text a source never labeled), can that derived label be trusted like a source-declared one?** This
  is the **first non-empty §2 since Legal** — DocIntel *owns* a derived-classification vocabulary.
  The sharp question is whether a *wrong* inference can leak. (Answer: no — a derived label may only
  **tighten**, is **fail-closed** on low classifier confidence, and is **provenance-tagged**; a
  false inference costs *availability*, never *safety*, because a label can only subtract capability
  ([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls))
  and the ACL — not the label — is the primary gate.)

If either forced a horizontal change, that would be the headline finding. **Neither did** — see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by Document Intelligence? | What Document Intelligence did instead |
|--------------------|:-----------------------------------------:|------------------------|
| Permissions (canonical model, `map_acl`) | **None** | A derived artifact **carries no ACL of its own** — it *inherits* the ACL of the source Item on its backward-[lineage](../../metadata/00-catalog-and-lineage.md#51-the-lineage-node-and-edge) path; multi-source merges hit the *existing* **mixed-ACL invariant** ([RAG §2.2](../../rag/00-retrieval-pipeline.md)) (split, or intersect-most-restrictive, or quarantine); a derived sub-Item whose *correct* ACL is narrower-and-unresolvable rides the *existing* `approximate → deny + quarantine` hatch ([§9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) |
| Metadata (label schema, catalog, lineage) | **Additive only — the *designed* extension point** | **Registered** `restricted:extracted` and `derived`-provenance-tagged `pii_class:*`/`sensitivity` values into the existing `restricted:<class>`/`pii_class:<type>` extension points ([§4.1](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)); a *secondary* derived index (entity/KG store) is the additive `LineageNode.kind` + `relation` growth [Metadata §9](../../metadata/00-catalog-and-lineage.md) **already named** ("new derived artifact type = a new `LineageNode.kind` + `relation`") — the graph was designed to grow node kinds; OCR/table extraction are ordinary **parse-stage** outputs (`parsed_as`), no new node needed |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** the matrix for `restricted:extracted`; **inherited** the GDPR/AI-Act rows; a derived label enforces *identically* to a source label (the matrix doesn't ask where a label came from — it's still `⊆ registry`), so no policy engine is added |
| RAG (chunking, hybrid, verifier) | **None** | OCR/Doc-Intelligence content is *already* a named chunking content type ([RAG §2.1](../../rag/00-retrieval-pipeline.md) — "Scanned / OCR (Doc Intelligence): Layout blocks from OCR, then prose rules"); supplied an eval set whose headline classes are **extraction grounding** and **derived-classification fail-closed correctness** |
| Storage / Workers / API / Deployment | **None** | OCR/extraction are **parse-stage** work on the *existing* staged DAG ([Workers §2](../../workers/00-ingestion-architecture.md)); the derived artifact is written under the *source Item's* tier ([Storage §5](../../storage/00-storage-architecture.md)); API `pack:"document_intelligence"` is the *existing* optional additive hint |

**Net horizontal change: none, all additive.** The one Metadata touch (a `LineageNode.kind` for a
secondary derived index) is **not** a contract change — it is the additive node-kind growth
[Metadata §9](../../metadata/00-catalog-and-lineage.md) explicitly designed for and named this exact
case for, exactly as Legal was the first pack to exercise the label extension point beyond Finance.
The headline: the two concepts most likely to force a horizontal primitive — a **derived ACL** and a
**derived label** — resolve because (a) a derivation **inherits** authorization, never manufactures
it, and (b) a derivation may only **tighten**, never widen, in *both* planes. Per
[ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md), if a future edit to this pack
adds a *required* API field, a new predicate, or a *computed* ACL, that edit needs a horizontal ADR.

---

## Derived content — the falsifiability analysis (the reason this cycle exists)

This is the section a reviewer should read first; it is the whole point of choosing Document
Intelligence.

**The claim under test.** *"Content the platform derives itself — OCR text, extracted
tables/entities, and an inferred classification — is expressible as additive pack data + policy; a
derived ACL and a derived label do not force a new horizontal mechanism."*

**Decomposition — separate the *content*, the *ACL*, and the *label*:**

1. **Derived *content* — a parse-stage output on the existing DAG.** OCR (image/scanned PDF →
   text), table extraction, key-value/form extraction, and entity extraction are all forms of
   **parsing** — turning a raw artifact into structured, chunkable text. The pipeline already has a
   `raw --parsed_as--> parsed_artifact` stage ([Workers §2](../../workers/00-ingestion-architecture.md),
   [Metadata §5.1](../../metadata/00-catalog-and-lineage.md#51-the-lineage-node-and-edge)) and OCR is
   *already* a named RAG chunking content type ([RAG §2.1](../../rag/00-retrieval-pipeline.md)). A
   scanned document's OCR text is a `parsed_artifact`, its extracted tables are table-row chunks. **No
   new stage, no new node kind** for the core case. *Additive.*
2. **Derived *ACL* — inherited, never manufactured.** A `parsed_artifact` is a **lineage descendant**
   of its `source_item`; the chunk projection denormalizes the *source Item's* ACL arrays
   ([Metadata §3](../../metadata/00-catalog-and-lineage.md), the mixed-ACL invariant). So the OCR text
   of a contract with ACL `{client-team, counsel}` carries **exactly** `{client-team, counsel}` — the
   platform never invents a broader (or any) ACL for what it derived. This is the crux: **a derivation
   is an ACL-*inheriting* operation, structurally identical to chunking or re-embedding, which already
   inherit.** *Additive.*
3. **Derived *label* — registered vocabulary, tighten-only, fail-closed, provenance-tagged.** A
   classifier that reads OCR'd text and infers `pii_class:health` is the first case of a label the
   *platform* assigns rather than the *source* declares. It resolves additively under three
   disciplines (see the "derived-label discipline" below): the value is **registered** in the
   classification registry (§2, a non-empty §2 — DocIntel *owns* this vocabulary); it may only
   **tighten** (add a mask, never remove or downgrade a label); and a **low-confidence** classifier
   output **fails closed** (defaults to the *more* restrictive label, never the less). *Additive.*

**Where it *could* have broken — and why it does not.** Two traps, both disarmed:

- **Trap A — a derived artifact that should be *narrower* than its source.** Redaction/PII-cell
  extraction can produce a sub-Item (a single extracted salary figure) whose *correct* ACL is
  **narrower** than the source document, and which the platform **cannot resolve** to a principal set
  (who exactly may see *this cell* is a source-level authorization fact the extraction doesn't carry).
  This is the Document-Intelligence twin of **SAP field-level auth** and **Legal computed-privilege**:
  a sub-Item whose ACL is sub-`exact`. It takes the *existing* `approximate → deny + quarantine` path
  ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)) —
  denied on the shared retrieval path, never approximately served. **No new predicate; the third
  sighting of a hatch already built.**
- **Trap B — a *wrong* inferred label that leaks.** A classifier could **under**-label (miss PII) or
  **over**-label (false positive). Under-labeling looks dangerous but **cannot cause a leak past the
  ACL**: a label is a *second, independent* gate that only *subtracts* capability
  ([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls));
  a *missing* derived label merely fails to *add* an extra mask — the ACL gate (the primary safety
  boundary) is untouched, so no principal sees content their ACL didn't already permit. Over-labeling
  → over-restriction → an **availability** cost, which is the fail-closed-preferred direction (the
  same trade KM ratified). The residual — a *derivation that removes/downgrades* a label — is
  forbidden outright by the tighten-only discipline. **A wrong derivation costs availability, never
  safety.**

Because the derived ACL is *inherited* (not computed) and the derived label is *tighten-only + fail-
closed*, DocIntel carries **one pack-local discipline (not a mechanism):**

> **The derivation discipline — a platform-derived artifact may only ever *inherit or tighten*
> authorization, never widen it, in either plane.** (1) *ACL:* a derived artifact carries the ACL of
> the source Item on its backward-lineage path; a multi-source derivation obeys the mixed-ACL
> invariant (split, or take the intersection = most-restrictive, or quarantine) and **never** the
> union. (2) *Label:* a derived label may only *add* a `restricted:*`/`pii_class:*` mask; it may
> **never** remove or downgrade an existing label, and a low-confidence inference resolves to the
> *more* restrictive outcome. Every derived label is stamped `label_source: derived` + classifier
> id + version, so it is auditable and reviewable — but its *enforcement* is identical to a source
> label.

This is the Document-Intelligence analogue of Legal's "waiver = ACL edit, label stays" discipline:
a single stated rule that keeps a genuinely new capability inside the additive contract. Because the
rule is *tighten-or-inherit only*, the worst a misconfigured DocIntel pipeline can do is over-mask or
over-quarantine (availability), never over-expose (safety) — fail-closed applied to *derivation*.

**Verdict:** the bet holds against its first *derived-content* concept. The falsifiability rule was
armed against a *manufactured* authorization fact and did **not** fire — the platform never
manufactures one; it inherits and tightens. Had a derived ACL needed *computing* on the shared path,
this section would instead be a horizontal ADR proposal against
[Metadata](../../metadata/00-catalog-and-lineage.md) / [Permissions](../../permissions/00-authorization-model.md);
that it is not is the finding.

---

## §1 — Sources & `map_acl` fidelity

Document Intelligence is unusual: its "source" is often **another pack's already-ingested content**
(it OCRs Finance's scanned invoices, extracts entities from Legal's contracts). Its `map_acl` job is
therefore mostly **inheritance**, not fresh mapping — the fidelity target is *"the derived artifact's
ACL equals the source Item's ACL, provably, via lineage."* Anything below `exact` is **denied on the
shared retrieval path** and quarantined ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).

| Source / input | Item class | Principal mapping | Max `acl_confidence` | Notes |
|----------------|-----------|-------------------|:--------------------:|-------|
| **Scanned document / image (OCR)** | The OCR text layer of a source document | **Inherits** the source Item's `allow`/`deny` set via the `parsed_as` lineage edge — no fresh ACL | `exact` iff the source Item's ACL was `exact` (inheritance never *raises* confidence) | OCR is a parse stage ([Workers §2](../../workers/00-ingestion-architecture.md)); the RAG OCR chunker already exists ([RAG §2.1](../../rag/00-retrieval-pipeline.md)) |
| **Structured extraction** (tables, key-value, forms) | Extracted table-row / field chunk of a source document | Inherits the source Item ACL; a per-row source ACL (if the source carries one) is respected, else the document ACL | `exact` iff source ACL `exact` | Table-row chunking reuses RAG's structure-aware seam; the mixed-ACL invariant keeps a chunk within one ACL |
| **Entity extraction / resolution** | An extracted entity mention (bound to its source span) | Inherits the source Item ACL of the span it was extracted from | `exact` iff source `exact` | An entity mention is *content*, not a principal; entity *resolution across documents* obeys the merge rule below |
| **Multi-source derived artifact** (an entity/KG node merging spans from D1, D2, …) | A `derived_artifact` node (new `LineageNode.kind`, per [Metadata §9](../../metadata/00-catalog-and-lineage.md)) | ACL = **intersection** of contributing source ACLs (most-restrictive-wins), else **split per source**, else **quarantine** | `exact` only if the merged ACL is fully resolvable; else **quarantine** | The mixed-ACL invariant applied to a *manufactured* node — never the union |
| **Redaction / PII-cell extraction** | A sub-Item whose correct ACL is *narrower* and unresolvable | — | `approximate` → **deny + quarantine** (or native OBO §10) | The DocIntel twin of SAP field-level auth / Legal computed-privilege — the platform never *fakes* a narrower grant |
| **Inferred classification** (classifier output) | Not an Item — a **label** on the chunk | n/a (label plane, not ACL plane) | n/a | Governed by §2/§3 + the derived-label discipline; a low-confidence output fails closed |

**Conformance fixtures (the production gate).** The Document Intelligence connector/pipeline ships a
fixture set for the [permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any DocIntel pipeline goes live:

1. **ACL inheritance (positive + negative):** the OCR text of a document with ACL `{A,B}` is
   retrievable by A and B **and** masked from C — the derived artifact never widened the source ACL.
2. **Multi-source merge = intersection, never union:** a derived entity node merging spans from
   D1`{A,B}` and D2`{B,C}` is retrievable **only** by B (the intersection); A cannot reach D2's
   contribution and C cannot reach D1's — a merge never grants across source boundaries.
3. **Derived-label fail-closed:** a classifier output below the confidence threshold resolves to the
   **more** restrictive label (e.g. quarantine or `confidential`), never the less; over-labeling is an
   availability event, not a leak.
4. **Redaction sub-Item quarantine:** an extracted PII cell whose correct ACL is narrower-and-
   unresolvable is `approximate → deny + quarantine`, never approximately served on the shared path.
5. **Lineage completeness:** erasing the source Item tombstones **every** derived artifact (OCR text,
   extracted tables, entity nodes) via the forward lineage walk ([Metadata §5.2](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4)) —
   no orphaned derived content survives the source's erasure.
6. **Cross-tenant:** no DocIntel-derived chunk of tenant A ever reaches tenant B (R4), inherited
   unchanged.

---

## §2 — Classification-registry values (the vocabulary Document Intelligence registers)

**This is the first non-empty §2 since Legal (Cycle 13)** — and it is non-empty for a *new* reason:
the four source packs (SAP/SharePoint/Email) and KM had empty §2 because a source *carries no policy
of its own*; DocIntel's §2 is non-empty because it **owns a derived-classification vocabulary** — the
labels a classifier *assigns* rather than reads. DocIntel **registers** these into the existing
[classification registry](../../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3)
extension points; it invents **no new dimension**. An unregistered label is a write-boundary schema
violation → DLQ ([Workers §8.1](../../workers/00-ingestion-architecture.md)), never silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:extracted` | A derived artifact (extracted table/entity/KG node) that a tenant wants held to a distinct policy from the source prose — always **at least** as restrictive as its source |
| `pii` / `pii_class` | `pii_class:*` (existing values) **+ a `label_source: derived` provenance stamp** | PII a classifier *inferred* in OCR'd/extracted text (the source never labeled it) — the values are the existing ones (`health`/`financial`/…); the *provenance stamp* is what is new |
| `sensitivity` | existing values **+ `label_source: derived` stamp** | An inferred sensitivity (a classifier reads a document and infers `confidential`) — tighten-only, fail-closed |

**The novel element is the `label_source` provenance stamp, not a new label value.** `restricted:extracted`
slots into the existing lattice (`public < internal < confidential < restricted:*`), so **most-
restrictive-wins** composition is inherited unchanged. A derived `pii_class:health` on an OCR'd medical
form composes with the document's inherited `confidential` exactly as a source-declared label would —
the enforcement matrix (§3, Governance §4) never asks *where* a label came from; it only asks that the
label is `⊆ registry`. The stamp exists purely so a derived label is **auditable and reviewable**
(who/what/which-model-version inferred it), not because enforcement differs.

> **Note on why a derived label is not a new *dimension*.** A tempting mistake is to add a
> `derived_sensitivity` dimension parallel to `sensitivity`. Rejected: that would fork the matrix and
> let a derived label enforce *differently* from a source one — the seam through which a wrong
> inference could someday be given *looser* treatment "because it's only inferred." Keeping derived
> labels in the **same** dimension with a **provenance stamp** means they enforce identically and can
> only tighten. Provenance is metadata *about* the label, never a second enforcement path.

---

## §3 — Label→action *tighten* deltas

Document Intelligence **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `restricted:extracted` | Only to principals in the derived artifact's **inherited** ACL (= the source Item's cleared set); masked otherwise | Isolated model pool when the source was Isolated; else inherits the source's routing | Never external egress beyond what the source permits | Stricter-or-equal to the source's own label — a derived artifact is **never** placed more openly than its source |
| `pii_class:*` `(label_source: derived)` | Same masking as a source-declared `pii_class:*` | Same PII-masking prompt rule | Same egress block | **Identical** enforcement to a source label; the only difference is the audit stamp |
| any derived label under **low classifier confidence** | **Fail closed** — resolve to the more-restrictive label or quarantine | — | — | The derived-label discipline: uncertainty tightens, never loosens |

**The derivation can only tighten (both planes).** These rows never *add* a grant. A derived label
adds a mask; a derived artifact inherits (or intersects to) the source ACL. There is no row here that
widens access relative to the source, by construction — which is exactly what makes a misconfigured
DocIntel pipeline an availability risk, never a safety one.

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
Provenance-stamping a label and requiring inference to fail closed are *precision/tighten* moves,
never grants.

---

## §4 — Compliance-map row(s) (declare + inherit)

Document Intelligence **inherits** the GDPR and ISO rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain)
and adds a **derived-content transparency** binding over *existing* controls; it does not re-derive
mechanism. The evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)),
now carrying the derived-label provenance stamp.

| Regime | Inherited controls (already built) | DocIntel-specific evidence binding |
|--------|-----------------------------------|-----------------------------------|
| **GDPR (inferred / incidental PII)** | Right-to-erasure + DSAR; PII masking; residency; `pii_class:*` label; `legal_hold > erasure > retention` | An **inferred** `pii_class:health` is masked identically to a declared one; erasure of the source Item tombstones every derived artifact (lineage walk) — a DSAR reaches *derived* PII, not only source PII, provably |
| **EU AI Act (automated content classification transparency)** | Model registry + eval-before-promotion gate + model version in every retrieval audit event | Every derived label carries `label_source: derived` + classifier id + version — the classification is **explainable and reviewable**, satisfying the "automated decision transparency" expectation without a new control |
| **The riding domain's regime** (SOX/privilege/Art.9/…) | Whatever the *source* domain's compliance row already binds | A DocIntel pipeline **inherits** the source's regime — OCR over Finance scans is SOX-relevant, over HR is Art. 9; the derived artifact never escapes the source's compliance envelope (it inherited the source ACL and tier) |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Derived artifacts live under the *source Item's* tier/DEK — no separate isolation surface |

**No new control was invented.** DocIntel's compliance posture is a *selection and binding* of
controls the platform already operates — including the **derived-label provenance stamp**, which is
just the existing model-version audit field applied to a classification decision.

---

## §5 — Retrieval / answer eval set

The Document Intelligence pack supplies (a) the **parsers** that make derived content retrievable and
(b) the **eval corpus** that gates any model/classifier change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG §2.1](../../rag/00-retrieval-pipeline.md)):**
- **Scanned / OCR** — layout blocks from OCR, then prose rules (the content type RAG §2.1 already
  names); the OCR text is a `parsed_artifact` inheriting the source ACL.
- **Tables / forms / key-value** — table-row and field chunking (reuses RAG's structure-aware seam);
  the mixed-ACL invariant keeps a row chunk within one ACL.
- **Entities / relations** — entity mentions bound to their source span (so a citation traces to the
  document + span it came from); cross-document entity resolution obeys the §1 merge rule.

**Eval set (extraction grounding · derived-classification fail-closed · inheritance correctness):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **ACL-inheritance permission negatives** | A principal outside the source Item's cleared set cannot obtain its OCR text / extracted tables / entities via any cleverly-worded prompt | 0 leaks (a permission test — a derivation never widened the source ACL) |
| **Multi-source merge correctness** | An answer citing a merged entity node exposes only the intersection of contributing source ACLs; never a fact from a source the caller can't read | 0 cross-source over-grants on the held-out set |
| **Derived-classification fail-closed** | A below-threshold classifier output tightens (more-restrictive label / quarantine), never loosens | 0 loosening on the held-out low-confidence set |
| **Extraction grounding** | An answer built on extracted tables/entities traces to a cited source span; no invented cell value or hallucinated entity | 100% extracted claims cited or the answer refuses |
| **OCR-noise robustness** | A garbled OCR span does not produce a confidently-wrong grounded answer; low OCR quality → refuse or flag, never fabricate | 0 confident fabrications on the noisy-OCR set |
| **Refuse-over-guess** | A question about a document the caller can't access → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated extracted fact | 0 fabrications on the held-out no-access set |
| **Erasure completeness** | Erasing a source Item removes every derived artifact from retrieval (lineage walk); no orphaned OCR text or entity node survives | 0 retrieval of derived content after source erasure |

A model or classifier that regresses on **ACL-inheritance negatives**, **merge correctness**, or
**derived-classification fail-closed** cannot be promoted for a DocIntel pipeline — the same gate
shape as the concept packs, retargeted to DocIntel's failure modes (which are dominated by *derived-
authorization inheritance*, not source accuracy).

---

## §6 — Optional additive API `pack` hint

DocIntel callers **may** pass `"pack": "document_intelligence"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint (e.g.
prefer the OCR/extraction-tuned model, bias retrieval toward extracted tables/entities, apply layout-
aware chunking). It is strictly additive:

- **Identity still governs.** The hint never widens access — a caller who passes
  `pack:"document_intelligence"` but is outside a source document's inherited ACL sees nothing
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an authorization
  input, and a derived artifact never carries an ACL broader than its source.
- **Omitting it is valid.** The platform infers pack context from the accessible derived artifacts;
  the hint only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"document_intelligence"` is
  [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7), not a
  breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Derived ACL = inheritance vs. per-artifact ACLs.** Inheriting the source Item's ACL (rather than
  letting a derivation carry its own) is less flexible than a "grant the extracted table separately"
  toggle — but that toggle is exactly the seam through which a derivation could *widen* access. The
  inheritance rule buys a hard guarantee that a derived artifact is never more open than its source;
  the rare case that genuinely needs a *narrower* ACL is quarantined (Trap A), not approximately
  served.
- **Tighten-only + fail-closed derived labels vs. recall.** A fail-closed classifier over-masks on
  low confidence, costing some availability (a document wrongly flagged `confidential` is harder to
  find). This is the KM trade re-applied: uncertainty resolves toward safety. The lever to recover
  recall is *better classifier eval* (§5), never *loosening the fail-closed rule*.
- **Provenance-stamped derived labels vs. a separate dimension.** Keeping derived labels in the same
  dimension with a `label_source` stamp (rather than a `derived_sensitivity` dimension) means they
  enforce identically to source labels and can only tighten — at the cost of not being able to give
  inferred labels *special* (looser) treatment, which is precisely the treatment the bet forbids.
- **Quarantining unresolvable sub-Items vs. serving them approximately.** A PII cell whose correct
  ACL the platform can't resolve is denied+quarantined (the R1 trade), not approximately served — the
  same honest availability cost SAP field-level auth and Legal computed-privilege pay.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Let a derived artifact carry its own freshly-computed ACL** | **Rejected — this is the trap.** Computing an ACL for manufactured content is a new predicate the platform doesn't have and the bet forbids; a wrong computation over-grants. A derivation *inherits* the source Item ACL (or intersects, or quarantines) — it never manufactures one (§0, "Derived content"). |
| **Union the ACLs of a multi-source derived node** | Rejected: union *widens* — an entity node merging D1`{A,B}` and D2`{B,C}` under a union `{A,B,C}` would let A read D2's contribution. The merge takes the **intersection** (most-restrictive-wins), splits per source, or quarantines. |
| **Add a `derived_sensitivity` label dimension** | Rejected: forks the enforcement matrix and creates a path where an inferred label could be treated more loosely. Derived labels stay in the existing dimension with a provenance stamp; enforcement is identical, tighten-only. |
| **Trust a low-confidence classifier output and label optimistically** | Rejected: a derived label must **fail closed** — uncertainty resolves to the *more* restrictive outcome. Optimistic labeling is the one derivation move that could loosen a floor. |
| **A DocIntel-specific derivation store / pipeline** | Rejected: would be a horizontal change. OCR/extraction ride the existing parse stage + staged DAG; a secondary derived index is the *additive* `LineageNode.kind` growth Metadata §9 already blessed — not a new store. |
| **Bespoke DocIntel compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): DocIntel inherits GDPR/ISO/the-riding-domain rows + binds the AI-Act transparency evidence to the existing model-version audit field; re-deriving controls is the anti-pattern. |

## Future scalability

- **Reporting pack** (the last backlog pack) is now the natural next slot: dashboards/BI extracts
  reuse SAP BW/Finance fidelity + DocIntel's *derived-artifact-inherits-source-ACL* rule verbatim (a
  report row derived from a source table inherits that table's ACL, exactly as an extracted cell does).
- **A new derived artifact type** (a summary index, a knowledge-graph triple, a vector of vectors) =
  a new `LineageNode.kind` + `relation` ([Metadata §9](../../metadata/00-catalog-and-lineage.md)) +
  the same inheritance/tighten discipline — additive, no redesign.
- **A better OCR/extraction model** enters through the existing eval gate (§5) and is routed by the
  existing label→trust policy — a config change, not a code change.
- **Per-token / per-span provenance** for a regulated extracted answer = extend `section_path` / add a
  chunk-substring lineage edge ([Metadata §9](../../metadata/00-catalog-and-lineage.md)) — an additive
  schema change, not a redesign.
- **The one future case that *would* force a horizontal ADR** is named explicitly: a derivation whose
  correct ACL must be *computed by the platform on the shared retrieval path* (not inherited, not
  quarantinable) — e.g. an automated redaction the platform is *trusted to enforce as a grant* rather
  than mirror. That is deliberately out of scope and quarantined today; making the platform *compute*
  a narrowing grant would be a Permissions/Metadata ADR, not a pack edit.

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack](../finance/00-finance-pack.md) · [Legal pack (last non-empty §2)](../legal/00-legal-pack.md) · [KM pack (last concept-shaped pack)](../km/00-km-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §3.1 (deny-wins), §7 (labels subtract), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §3 (catalog/chunk ACL projection), §4 (classification registry), §5.1 (lineage node/edge), §5.2 (erasure tombstone), §9 (additive node-kind growth)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §8 (model/eval gate), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG §2.1 (OCR/Doc-Intelligence chunking), §2.2 (mixed-ACL invariant), verifier](../../rag/00-retrieval-pipeline.md) · [Workers §2 (parse stage), §5 (re-sync), §8.1 (DLQ)](../../workers/00-ingestion-architecture.md) · [API §4, §5, §11](../../api/00-api-surface.md)
