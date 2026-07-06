# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 15 (Domain Pack #5 — Knowledge Management: the first *inverse* falsifiability test — over-refusal vs. loosening a floor)
- **Last updated:** 2026-07-06
- **Documentation root:** `platform/` — the single source of truth.
- **Gesamtfortschritt:** **≈ 88 %** (Ende Zyklus 15) — siehe §0.1. **Nach jeder Session melden.**

---

## 0.1 Fortschritt (Gesamtstand, gewichtet)

> Gemessen gegen das Endziel: Doku ausreichend, damit ein Team die komplette Plattform
> ohne zusätzliche Architektur-Vorgabe implementieren kann. **Jeden Zyklus fortschreiben.**

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| Vision & Prinzipien | 10 % | 100 % | 10.0 |
| Security-Architektur | 10 % | 80 % | 8.0 |
| Permissions Deep Dive (Z3) | 12 % | 90 % | 10.8 |
| RAG Deep Dive (Z4) | 12 % | 85 % | 10.2 |
| Storage & Tenancy (Z5) | 10 % | 90 % | 9.0 |
| Workers & Connectors (Z6) | 10 % | 90 % | 9.0 |
| Metadata / Katalog / Lineage (Z8) | 6 % | 90 % | 5.4 |
| Governance / Audit / Kosten (Z7) | 8 % | 85 % | 6.8 |
| API-Surface & Verträge (Z9) | 5 % | 90 % | 4.5 |
| Deployment / Topologie / DR (Z10) | 7 % | 90 % | 6.3 |
| Domänen-Pack-Specs (Finance/HR/Legal/Audit/KM …) | 6 % | 85 % | 5.1 |
| Code-Reconciliation (`core/`-Umsetzung) | 4 % | 30 % | 1.2 |
| **Summe** | **100 %** | — | **≈ 88 %** |

**Verlauf:** Z1 ≈ 18 % · Z2/2b ≈ 24 % · Z3 ≈ 33 % · Z4 ≈ 40 % · Z5 ≈ 49 % · Z6 ≈ 58 % · Z7 ≈ 65 % · Z8 ≈ 71 % · Z9 ≈ 76 % · Z10 ≈ 82 % · Z11 ≈ 84 % · Z12 ≈ 85 % · Z13 ≈ 86 % · Z14 ≈ 87 % · **Z15 ≈ 88 %** (KM-Pack — n=5; der erste *inverse* Stresstest: nicht "verweigert die Plattform korrekt?" sondern "*hört* sie auf zu verweigern, wenn sie darf?". Over-Refusal ist ein *Tuning/Eval*-Problem **oberhalb** von Filter und Verifier (Query-Expansion, Rerank/MMR, Dedup, KM-eval-getuntes Modell), **niemals** ein Floor-Aufweichen (breiteres Default-Label, gelockerte Grounding-Schwelle, ungefilterter List-Mode — alle drei abgelehnt und unnötig). **Erster Pack mit leerem §2 + §3** — null neue Vokabeln, null Tighten, null Loosen: Beweis, dass die Low-Restriction-Defaults bereits korrekt kalibriert sind. SAP/SharePoint/Email bleiben reine Connector-Fidelity-Wiederverwendung).

---

## 0. How to run a cycle (process reminder)

1. Read every Markdown file under `platform/` (start with this file).
2. Do the **highest-priority open item** in §6 — not everything.
3. Create/extend Markdown docs (each answers Why / How / Trade-offs / Alternatives /
   Future scalability). Prefer **extending** existing docs over duplicating.
4. If a decision shapes >1 component, add an ADR under
   `architecture/adr/` and link it.
5. Update this file: move items Completed, add new risks/questions, re-prioritize.

---

## 1. Completed work

### Cycle 15 (2026-07-06) — Domain Pack #5 (KM): the first *inverse* falsifiability test — over-refusal
- Wrote **[packs/km/00-km-pack.md](packs/km/00-km-pack.md)** — the **fifth pack**, and the first to
  stress the platform from the **opposite** direction. Finance/HR/Legal/Audit all asked *"does the
  platform correctly **refuse**?"* (over-sharing = safety bug). KM inverts it: broad `internal`, low
  restriction, high recall over Confluence/SharePoint/wikis/portals — the feared failure is
  ***over-refuse*** (an **availability** bug: accessible open content left *unfound* or *needlessly
  masked*).
- **The headline (§0 ledger + the dedicated "Over-refusal" analysis): net horizontal change = none,
  all additive — and, uniquely, additive with *empty §2 and §3*. The falsifiability rule was armed
  against a *loosening* (not a tightening) and did NOT fire.** The pack most tempted to loosen a floor
  to buy recall needed to loosen **nothing**:
  - **Over-refusal is a *tuning/eval* problem *upstream* of the filter and verifier — never a
    floor-loosening problem.** A KM answer is wrongly empty for exactly two reasons: (1) content was
    accessible but *not retrieved* (a recall miss — fixed by the *existing* levers on the
    already-permitted set: query expansion [RAG §4.3], hybrid/rerank/MMR tuning [RAG §5], wiki dedup
    [RAG §6], a KM-eval-tuned model); or (2) content was *not accessible* and the empty answer is
    *correct* (the safety floor working). Neither requires seeing more than the caller may.
  - **Three floor-loosening temptations, each rejected *and* shown unnecessary:** widen the default
    label (`internal`→`public`) — buys **zero** recall (`internal` is already retrievable internally)
    and breaks fail-closed classification; relax the verifier grounding bar — targets the wrong stage
    and converts an availability bug into a **grounding/R2 leak**; add an unfiltered "list mode" —
    structurally impossible (`VectorIndex` port has no unfiltered method) *and* unnecessary (browse =
    the filter-parity catalog read).
- **The reusable articulation (stated once, in the pack):** *recall is bought **upstream of** the
  filter and verifier, on the set the caller may already see; safety is enforced **at and after** the
  filter — the two never trade, so improving one never regresses the other.* Reaffirms
  ADR-0004/ADR-0009 → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **First pack to register ZERO new vocabulary (§2 empty) and apply ZERO tighten deltas (§3 empty),
  and it loosens nothing either** — the empty tables *are* the deliverable: direct evidence that the
  **low-restriction end of the lattice was already complete** and correctly calibrated. Also the
  **lightest compliance footprint** of any pack (ISO 27001/SOC 2 + incidental-PII GDPR, both inherited).
- **Sources:** Confluence (space + page restrictions), SharePoint/OneDrive wikis+portals (reuses
  Finance/HR/Legal fidelity verbatim), internal portals/intranet, Git-hosted wikis. Fidelity-friendly,
  but the fail-closed rule is **not waived** for it (an unresolvable page restriction is still
  quarantined; unlabeled → `internal` never `public`). Supplied conformance fixtures with a deliberate
  *both-ways* emphasis — an **open-content positive** (a space-member *can* read an `internal` page:
  the pack must not over-restrict) **and** the usual restricted-page/computed-restriction/cross-tenant
  negatives (safety floor unchanged). Eval set inverts the headline to **recall / over-refusal
  false-negative** while *retaining* the permission-negative class — proving the gate can chase recall
  without trading away safety (the SoD-detection recall class Audit first surfaced, now the primary bar).
- **No new ADR this cycle** — KM is a *worked instance* of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md);
  the pack instead **documents the floor from the open side** (a tenant demanding "skip the filter" is
  refused) and names the future pack that *would* force an ADR: a *transparency-mode* pack that
  surfaces content beyond strict entitlement (deliberately out of scope, now documented).
- Updated indexes: `packs/README.md` (KM → **Seeded**, 1st inverse test), `platform/README.md` domain
  map (packs → **Finance + HR + Legal + Audit + KM seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=5** and to its **first inverse
  (over-refusal) corner**; proves the fail-closed defaults don't suppress legitimate recall; re-exercises
  the SharePoint connector fidelity in *open* mode (complementing the restricted-mode exercise);
  re-validates R2 from the other side (a lowered grounding bar as an *anti*-pattern is now documented).
- ⏳ **Handed to later cycles:** the **source-shaped** packs (SAP / SharePoint / Email) are now pure
  connector-fidelity reuse (both restricted- and open-mode SharePoint paths exercised); the runtime
  **pack-load SPI** (open Q#6-adjacent) is still the engineering track; open Q#3 (model hosting) still
  feeds each pack's eval-tuned model choice.

### Cycle 14 (2026-07-06) — Domain Pack #4 (Audit): the first *combinatorial*-concept falsifiability test
- Wrote **[packs/audit/00-audit-pack.md](packs/audit/00-audit-pack.md)** — the **fourth pack**,
  chosen as the **highest-leverage / lowest-effort** slot: it inherits almost everything already
  built (**Finance's SOX row + SAP fidelity verbatim**; **Legal's `matter:<id>` hold + append-only
  evidence**) and introduces **exactly one concept to stress: segregation-of-duties (SoD)** — the
  first *combinatorial* constraint any pack has raised (every prior restriction was *unary*: a
  property of one (principal, item) pair; SoD is *relational* — "the preparer of entry E may not be
  its approver").
- **The headline (§0 ledger + the dedicated "Segregation-of-duties" analysis): net horizontal change
  = none, all additive — the falsifiability rule was armed and did NOT fire, but for a *sharper*
  reason than Legal's.** Legal's waiver held by *composing* two existing mechanisms; Audit's SoD
  holds because of a **plane boundary**. SoD is one word for two controls in two planes:
  - **SoD as *prevention* (write plane) — out of the platform's plane.** "Preparer may not post" is
    a constraint on *executing a transaction*, enforced in the source system of record (SAP GRC /
    the ERP). The platform is a **read-only, permission-faithful knowledge platform**
    ([ADR-0001](architecture/adr/ADR-0001-platform-shape-private-rag.md)/[ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md));
    it **never posts/approves/executes** — so **there is no SoD action for it to gate.** Not a gap;
    out of plane.
  - **SoD as it *projects onto read access* — a per-principal `deny`, pre-resolved by the source.**
    An independence/SoD *read*-exclusion is structurally identical to Legal's **ethical wall**: the
    source resolves the relation into a principal set, the connector `map_acl`s it into a `deny`
    grant, deny-wins evaluates first. *Additive.*
  - **SoD as *detection* (read plane) — an ordinary permission-gated retrieval.** "Which users both
    prepared and approved?" is a **read** over the audit trail; the combinatorial join lives **in
    the query and the source data, never in the access predicate.** The verifier grounds it in cited
    trail rows. *Additive — exactly what a permission-faithful RAG platform is for.*
- **The reusable articulation (stated once, in the pack):** *the platform enforces
  **who-may-read**, never **who-may-act**. Any action-phrased control — SoD, four-eyes,
  maker-checker, dual-authorization — is enforced in the source; the platform mirrors the **read**
  restriction it produces (a `deny`) and **retrieves over** the **evidence** it leaves (the trail).
  Detection in scope; prevention of an action out of plane.* This **reaffirms** ADR-0001/0004 rather
  than extending them → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **Where it could have broken:** trying to make the *access predicate itself* compute the relation
  live. Covered by two *existing* hatches: pre-resolved → unary `deny`; computed-and-unresolvable →
  the *existing* `approximate → deny + quarantine` path (identical to SAP field-level auth / Legal
  computed-privilege). No third case exists → no horizontal gap.
- **Sources:** GRC/audit-management (AuditBoard/Workiva/SAP GRC), SAP/ERP (reuses Finance fidelity +
  field-level-auth quarantine verbatim), DMS/SharePoint (reuses Legal/Finance), the platform's **own
  S7 append-only trail** (the reflexive case), email. Registered **`restricted:audit_workpaper`**
  (pre-issuance masking + egress block); reused `matter:<id>` for PCAOB AS 1215 7-yr retention holds.
  Supplied conformance fixtures (SoD read-exclusion deny-wins, pre-issuance pos/neg, computed-SoD
  quarantine, hold-vs-erasure, cross-tenant) and an eval set whose headline classes are
  **pre-issuance permission negatives** and — a deliberate first — **SoD-conflict *detection*
  recall** (missing a real conflict is an audit failure), the first sighting of the *over-refusal*
  failure mode KM will make its headline.
- **No new ADR this cycle** — Audit is a *worked instance* of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md);
  the pack instead **documents the plane boundary** as the explicit reason no transaction-control ADR
  was needed (and names the future pack that *would* need one: an action-taking pack).
- Updated indexes: `packs/README.md` (Audit → **Seeded**, 1st combinatorial test), `platform/README.md`
  domain map (packs → **Finance + HR + Legal + Audit seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=4** and to its **first
  combinatorial concept**; hardens the SOX/evidence story (Finance's row, now reused + reflexive:
  the platform's own SOC 2 evidence is the trail Audit queries); re-exercises R1 (computed-SoD
  quarantine), R4 (cross-tenant), and the `legal_hold > erasure > retention` precedence under PCAOB
  retention; makes the **read-plane-mirror scope boundary** an explicit, cited statement.
- ⏳ **Handed to later cycles:** **KM** is next as the deliberate *inverse* stress (broad `internal`,
  high recall, low restriction — does the pipeline *over*-refuse on open content?); the runtime
  **pack-load SPI** (open Q#6-adjacent) is still the engineering track; a future **action-taking**
  pack would be the one case forcing a horizontal transaction-control ADR (deliberately out of scope,
  now documented).

### Cycle 13 (2026-07-06) — Domain Pack #3 (Legal): the first genuine novel-concept falsifiability test
- Wrote **[packs/legal/00-legal-pack.md](packs/legal/00-legal-pack.md)** — the **third pack**, chosen
  because it is *near-mechanical in five of six sections* (reuses HR's `matter:<id>`/hold shape +
  Finance's DMS/SharePoint fidelity) **while introducing the one concept the platform had never
  stress-tested: attorney-client privilege as a retrieval gate.** Unlike HR (a *different shape* of
  known mechanism), Legal is the first pack that could have **falsified** the bet with a genuinely
  new primitive. It did not.
- **The headline (§0 ledger + the dedicated "Privilege & waiver" analysis): net horizontal change =
  none, all additive — the falsifiability rule was armed and did NOT fire.** The concept most likely
  to force a horizontal primitive — **privilege *waiver*, per matter, per recipient** — resolved to
  the *composition of two mechanisms the platform already has*, by separating **what** from **who**:
  - **What** (the restriction) = a `restricted:privileged` label — a §2 registered value + §3 tighten
    delta, structurally identical to Finance's `restricted:mnpi`.
  - **Who** (the cleared set) = the **item ACL** — the existing per-item `allow` set.
  - **Waiver** = a **narrowing grant edit on the item ACL**, propagated by the *existing*
    change-driven re-sync ([Workers §5](workers/00-ingestion-architecture.md)); **never** a label
    removal (which would over-waive to *everyone* — the trap). "Per recipient" is exactly what an ACL
    *is*, so the **static label→action matrix never encodes recipient-specific policy → no horizontal
    gap.** Recorded as **one pack-local discipline** (waiver = ACL edit, label stays), not a mechanism.
- **Ethical walls (information barriers) = the *existing* deny-wins clause**
  ([Permissions §3.1](permissions/00-authorization-model.md#31-precedence-deny-always-wins)): a
  conflicted attorney is a `deny` grant on the matter's items; deny already evaluates first, before
  any allow. Deliberately **not** modeled as a label (that would lose deny semantics) — kept in the ACL.
- **The one thing the platform must *refuse*:** it does **not compute** subject-matter waiver (a legal
  determination); it **mirrors** counsel's decision as reflected in the source ACL. A DMS exposing
  privilege only as a *computed* rule takes the *existing* `approximate → deny + quarantine` path —
  identical to SAP field-level auth. Refusing to *infer* privilege is what keeps the platform a
  faithful ACL mirror rather than a legal-reasoning engine that could leak on a wrong inference.
- **Sources:** DMS (iManage/NetDocuments — rich per-document ACL + walls, so Legal is *fidelity-friendly*
  unlike SAP), SharePoint, privileged email, matter/practice-management stores; **clause-level chunking**
  reuses RAG's structure-aware seam. Registered `restricted:privileged` + `restricted:work_product`
  (independently waivable → two labels); reused `matter:<id>` verbatim. Supplied conformance fixtures
  (ethical-wall deny-wins, privilege pos/neg, **waiver-as-grant-edit that does not over-share and keeps
  the label**, hold-vs-erasure, cross-tenant) and an eval set whose headline classes are **privilege
  negatives**, **waiver correctness**, and **ethical-wall enforcement**.
- **No new ADR this cycle** — [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) already
  ratifies the pack contract; Legal is a *worked instance* of it. (A pack that *had* forced per-recipient
  matrix policy would have needed a horizontal Governance ADR — that section instead documents *why the
  gap does not exist*.)
- Updated indexes: `packs/README.md` pack table (Legal → **Seeded**, 1st novel-concept test),
  `platform/README.md` domain map (packs → **Finance + HR + Legal seeded**).
- **Directly strengthens (no new risk owned):** turns "even a genuinely new restriction type = pack,
  not redesign" from an *untested* claim into a *tested* one (n=3, first novel concept); binds a new
  audit dimension (**the waiver decision itself is an audited ACL-change event**); re-exercises R1
  (computed-privilege quarantine), R3 (waiver propagation within the freshness SLA), R4 (cross-tenant),
  and the `legal_hold > erasure > retention` precedence under e-discovery preservation.
- ⏳ **Handed to later cycles:** **Audit** is now almost entirely inherited (Finance SOX row +
  segregation-of-duties as another `deny`-grant + append-only evidence + Legal's `matter:<id>` hold),
  then **KM** as the deliberate *inverse* stress (broad `internal`, high recall — does the pipeline
  *over*-refuse on open content?). The runtime **pack-load SPI** (open Q#6-adjacent) is still the
  engineering track.

### Cycle 12 (2026-07-06) — Domain Pack #2 (HR): the second, structurally-different data point
- Wrote **[packs/hr/00-hr-pack.md](packs/hr/00-hr-pack.md)** — the **second pack**, chosen to
  stress a **different corner** than Finance so the bet is tested for *reusability*, not just
  *possibility*. One pack proves the mechanism exists; a second, structurally-different pack is
  the first evidence the [skeleton](packs/README.md) *generalizes*.
- **The headline (§0 ledger): net horizontal change = none, all additive — the skeleton
  generalized from n=1 to n=2 cleanly.** The case most likely to force a new primitive —
  **employee-self-scoped ACLs** ("a subject may see *only their own* record") — resolved to the
  **degenerate case of the existing set-membership predicate**: a one-element `allow` set = the
  owner's CPI, and the subject's own CPI is *already* one of their effective principals
  ([Permissions §4.1](permissions/00-authorization-model.md)). No "owner-of" concept was added.
- **Computed manager-hierarchy visibility** ("manager sees reports N levels down", dynamic
  security groups) that is *not* expressible as static set-membership rides the **existing §9
  quarantine / §10 OBO escape hatch** — the *same one Finance used for SAP field-level auth*.
  The R1 confidence gate held against a second, different ABAC shape.
- **Special-category data:** registered `pii_class:health` (GDPR Art. 9 — already the Metadata
  schema's named example), `pii_class:employment`, and `restricted:works_council`; **tightened**
  the label matrix with a **manager-visibility carve-out** (health data masked even from a
  subordinate's own line manager by default) — a *tighten*, never a grant.
- **GDPR as the *primary* regime (Finance leaned SOX):** exercised the reflexive **self-DSAR**
  (employee is both subject and caller — the existing DSAR job, unchanged) and the
  **`legal_hold > erasure > retention`** precedence under real conflict (an erasure request is
  *partially* honored — HR content erased, statutorily-retained payroll held — provable by
  lineage traversal).
- **Sources:** Workday + SAP-HCM/SuccessFactors (**reuses Finance's SAP connector fidelity work
  verbatim**), SharePoint (HR policy library, broadly `internal`, high recall), grievance email.
  Supplied self-scope + health-masking + erasure/retention conformance fixtures and an eval set
  whose headline classes are **self-scope permission negatives** and **health-field masking**.
- **No new ADR this cycle** — [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)
  already ratifies the pack contract; HR is a *worked instance* of it, exactly as Finance was.
  (A new pack that *did* force a horizontal change would have needed one — HR did not.)
- Updated indexes: `packs/README.md` pack table (HR → **Seeded**), `platform/README.md` domain
  map (packs → **Finance + HR seeded**).
- **Directly strengthens (no new risk owned):** turns "new domain = pack, not redesign" from a
  claim backed by *one* example into one backed by **two structurally-different examples**;
  re-exercises R1 (a second ABAC shape quarantined), R4 (cross-tenant + self-scope blast radius),
  and the erasure/legal-hold precedence end to end.
- ⏳ **Handed to later cycles:** Legal / Audit / KM / SAP / SharePoint / Email packs stay
  fill-in-the-blank (Legal reuses HR's `matter:*`/grievance-hold shape; Audit reuses Finance's
  SOX row); the runtime **pack-load SPI** (open Q#6-adjacent) is still the engineering track.

### Cycle 11 (2026-07-06) — Domain Pack #1 (Finance) + the reusable pack-spec skeleton
- Opened the **`packs/`** folder — the first *vertical* surface, after all ten horizontals were
  Seeded (Cycle 10). Its purpose is to **prove the founding bet** (*"new domain = pack, not
  redesign"*), asserted ten times and until now proven zero times.
- Wrote **[packs/README.md](packs/README.md)** — the **reusable six-part pack-spec skeleton**
  (every future pack is fill-in-the-blank): (1) sources + `map_acl` fidelity + conformance
  fixtures; (2) classification-registry values; (3) label→action *tighten* deltas; (4)
  compliance-map rows; (5) retrieval/answer eval set + parsers; (6) optional additive API `pack`
  hint. Each section plugs into **one already-built horizontal extension point** — the author
  fills blanks, never designs mechanism. Added the mandatory **§0 horizontal-change ledger** and
  the **falsifiability rule** (if a pack *can't* fit, that's a real horizontal gap → a horizontal
  ADR, never a pack-local hack).
- Wrote **[packs/finance/00-finance-pack.md](packs/finance/00-finance-pack.md)** — the **reference
  pack**, deliberately the hardest (SAP has *no document ACL*; Finance data is simultaneously
  `confidential` + PII + legally held; SOX makes the audit trail contractual; numbers must be
  grounded-or-refused). Its **§0 ledger records ZERO horizontal changes** across all ten surfaces —
  the bet held against the worst case. Concretely: SAP `map_acl` fidelity target + 4 conformance
  fixtures (incl. `approximate→deny+quarantine` for field-level auth, and revocation-within-SLA);
  registered `restricted:mnpi`/`restricted:supervisory` + `pii_class:financial`/`tax`; tighten-only
  label deltas (MNPI → Isolated model pool + egress block); inherited SOX/GDPR/ISO compliance rows
  with evidence bindings; SAP-table/ledger/Excel parsers + a numeric-grounding / refuse-over-guess /
  permission-negatives eval set; the additive `pack:"finance"` hint (identity still governs).
- Recorded **[ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)** — ratifies the pack
  contract as a genuinely cross-component decision (it constrains all ten horizontal surfaces at
  once): **a pack is additive data + policy, tighten-only, six sections, with a mandatory
  horizontal-change ledger.** The worst a misconfigured pack can do is over-restrict (availability
  bug), never over-expose (safety bug) — fail-closed applied to extensibility.
- Updated indexes: ADR index, `platform/README.md` domain map (added `packs/` → **Finance seeded**).
- **Directly strengthens (no new risk owned):** turns the founding bet from a slogan into a
  **reviewable, blockable contract** (a non-additive §0 ledger row is a PR-visible event);
  exercises and validates R1 (SAP quarantine), R5 (Isolated-tier cost trade), and the
  audit-as-evidence promise end to end.
- ⏳ **Handed to later cycles:** HR / Legal / Audit / KM / SAP / SharePoint / Email packs are now
  fill-in-the-blank against the Finance template; the runtime **pack-load SPI** (how a pack is
  *loaded* at runtime) is deferred to the engineering track (open Q#6); open Q#3 (model hosting)
  still feeds each pack's eval-tuned model choice.

### Cycle 10 (2026-07-06) — Deployment: topology, environments, CI/CD & DR/BCP
- Wrote **[deployment/00-deployment-topology.md](deployment/00-deployment-topology.md)** — the
  **physical projection** of the whole platform and the **last un-seeded surface**. Introduces
  **no new logical component and no new guarantee**; it makes the existing ones affordable,
  operable, and survivable, and is the single place the **empirical sizing/tuning numbers** queued
  by Cycles 5–9 land. Collected those obligations as **D1–D8**, each tracing to its upstream source.
- **Physical projection:** the [three planes](architecture/01-platform-overview.md) map onto three
  substrates by dominant scaling axis — **edge+query** (stateless, latency-SLO autoscale),
  **ingestion** (stateless workers, scaled on **queue lag** not CPU), **data** (the only stateful
  substrate, hence the only backup/DR owner). Fail independently, blast radius stays separate.
- **Reference topology per tier (D1):** **Shared** (dense multi-tenant pool + two-control isolation)
  vs. **Isolated** (dedicated pool/cluster + per-tenant DEK/BYOK, quarantine hatch), mirroring the
  [Storage isolation tiers](storage/00-storage-architecture.md) one-to-one. **Graduation** =
  blue/green re-index through the `VectorIndex` port (no source re-hit) + a `tenant→placement`
  route flip — a data migration, not a redesign.
- **CI/CD as a safety gate (D7):** the [permission-conformance suite](permissions/00-authorization-model.md)
  is the **un-overridable release veto** (any over-permissive `map_acl` → hard fail, ships in
  quarantine never open); the [eval-before-promotion](governance/00-governance-and-audit.md) battery
  gates model changes; progressive delivery (staging → canary → prod) with the connector canary live;
  policy/allowlist/topology **as code**. **Real tenant data never leaves prod** — staging is
  synthetic but **ACL-shaped** so the gate stays meaningful.
- **SLA-capacity sizing (D2/D3):** **P0 revocation capacity is reserved, never autoscaled** (reacting
  to a revocation backlog is already a breach); P1/P2 autoscale on queue lag; relay-poll cadence set
  **below the SLA budget** — the freshness SLA is really an SLA on cache-TTL+invalidation, which
  query-time principal precedence backstops. Broker: managed queue + Postgres outbox (Shared),
  partitioned log (Isolated). **Safety is provisioned, bulk is elastic.**
- **Cost/residency (D4):** prices + envelope sizes live in a **versioned manifest** promoted through
  the pipeline (a price change is a reviewable commit into the unchanged degradation ladder); the
  safety invariant is inherited verbatim (no envelope/scale-down relaxes a permission). **Region is a
  routing fact** (`tenant→placement`), never a contract change; **data never crosses its residency class.**
- **Metadata ops (D5):** catalog partitioned by `tenant_id`; cold-lineage archival keeps tombstone/
  erasure walkability; a scheduled **lineage-integrity-check** asserts the [Metadata §7](metadata/00-catalog-and-lineage.md)
  invariants (no orphan / version monotonicity / label⊆registry / **no cross-tenant edge, R4**),
  violation → governance incident + write-quarantine.
- **DR/BCP (D8) → [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md):**
  **active-passive per residency region** (no active-active writes → **never** a window where two
  regions disagree on a revocation); **ACL-first, fail-closed recovery** (SoT→object→vector-rebuild→
  cache; permissions recover before content is queryable); **vectors rebuilt, not backed up**
  (a restored snapshot could disagree with recovered ACLs; the object-artifact rebuild is
  consistency-safe); tiered RPO/RTO (Shared ≤15 min/≤4 h, Isolated ≤5 min/≤1 h). The failover safety
  rule reuses query-time principal precedence — a failover cannot resurrect a revoked grant.
- Recorded **[ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md)**.
- Updated indexes: ADR index, `deployment/README.md` (stub → real), `platform/README.md` domain map
  (deployment → **Seeded**).
- **Directly strengthens (no new risk owned):** **closes the residual/"empirical" half of R3, R5, R8**
  (SLA-capacity sizing, prices/envelopes, autoscaling tuning now have a home) and **operationalizes R4**
  (partition pruning + the scheduled cross-tenant-edge integrity check). **All eight core platform
  surfaces are now Seeded — §5 is fully closed.**
- ⏳ **Handed to later cycles:** per-domain **pack specs** (Finance/HR/Legal — proves the "new domain =
  deployment of data+policy, not a topology change" bet end to end); open Q#3 (model-hosting posture per
  tier) feeds the concrete instance/model manifest; open Q#6 (agent framework) and the `core/`
  reconciliation remain the engineering track.

### Cycle 9 (2026-07-06) — API: external surface, contracts & versioning
- Wrote **[api/00-api-surface.md](api/00-api-surface.md)** — the platform's **outward
  contract** and the **last major un-seeded surface**. It is a *contract, not a new component*:
  the outward face of the [API Gateway](architecture/01-platform-overview.md) (Plane 1) and the
  [Governance policy store](governance/00-governance-and-audit.md). Discharges the client-facing
  needs three cycles queued (Governance → budgets/DSAR/audit-export; Metadata → catalog/lineage/
  DSAR-status; RAG+Permissions → the query endpoint that carries the subject token).
- **Five resource groups:** Query & Answer · Catalog & Lineage · Governance & Admin · Privacy &
  Audit (DSAR/erasure/export) · Ingestion ops, plus a shared async **Jobs** surface. Aligned to
  caller + owning plane/policy.
- **Six design tenets** = the outward projection of the platform principles: identity in the token
  not the URL/body; fail-closed at the edge; one envelope; heavy work is a job; idempotent writes;
  versioned & deprecable.
- **Query/answer contract:** sync `POST /v1/answers` + streaming `/v1/answers:stream`, **one
  verifier gate for both** (streamed `final` event emitted only after the verifier passes — streaming
  is never a grounding bypass). "No permitted data" is a **`200` success**
  (`grounding:"no_accessible_information"`), never an error — so absence of access can't leak as (or
  be faked as) an error. Citations expose the canonical `resource_id`+`source_item_version` from
  [Metadata §3](metadata/00-catalog-and-lineage.md).
- **Token → subject at the edge:** IdP bearer token → `{tenant, subject, effective principals,
  delegation}`; tenancy **derived from the token, never a URL segment** (impersonation
  unrepresentable). OBO via **token exchange** (actor + subject; retrieval runs under the subject).
  A **client-credentials** token has no end-user principals → a service account **structurally cannot**
  read user-restricted knowledge — kills the "index-everything under a service account" anti-pattern
  at the API layer.
- **One response envelope** `{ok,data,error,meta}` with **typed error enums**, leak-free messages,
  and `meta.request_id` == the audit correlation id; hidden resources return `not_found`, never a
  message confirming existence.
- **Admin API can only tighten:** thin self-auditing CRUD over the Governance policy store; a write
  that would loosen a platform floor (widen a label, disable the ACL filter, throttle a P0 revocation,
  raise a budget above ceiling, pin an un-evaluated model) → `422 policy_blocked`. Successor to the
  local [ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md) `control_panel.py`.
- **Privacy group** (DSAR/erasure/audit-export) = **jobs**; erasure status returns the
  [Metadata lineage-tombstone](metadata/00-catalog-and-lineage.md) evidence — completeness is
  **proven by a traversal**, `legal_hold` blocks with `422`. **Filter parity** on catalog/lineage
  reads (identical predicate to retrieval; no unfiltered "list mode" side-channel).
- **Versioning:** URL-major (`/v1/`), additive-by-default (clients must ignore unknown fields),
  breaking → new major + `Deprecation`/`Sunset` + per-version usage reporting. **A new domain pack
  is not a version event.**
- Recorded **[ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md)**.
- Updated indexes: ADR index, `api/README.md` (stub → real), `platform/README.md` domain map
  (api → **Seeded**).
- **Directly strengthens (no new risk owned):** the A1/A6 obligations — permission-faithful retrieval
  ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)) enforced once at audited
  choke points instead of re-argued per endpoint; budget/rate limits couple to
  [Governance §7.3](governance/00-governance-and-audit.md) and **throttle cost, never safety** (R5).
- ⏳ **Handed to downstream cycles:** concrete gateway/broker/topology + per-region residency routing +
  rate-limit sizing + streaming transport ops → [Deployment](deployment/); each domain pack's optional
  `pack` hint + any pack-specific endpoints ride the additive rule (no contract change).

### Cycle 8 (2026-07-06) — Metadata: catalog, lineage & classification schema
- Wrote **[metadata/00-catalog-and-lineage.md](metadata/00-catalog-and-lineage.md)** — the
  **connective-tissue schema**. Five prior cycles referred to the same nouns (`resource_id`,
  `source_item_version`, `labels`, `embed_model`, "lineage tombstone", "catalog row") but **no
  document owned their definitions**; this cycle canonicalizes them so the four consumers
  (Storage holds, Workers emits, RAG/citation + Governance/evidence read) share **one contract
  instead of four component-local shapes**. Adds **no new store** (metadata lives in the
  relational source of truth, [Storage §4.2](storage/00-storage-architecture.md)) and **no
  hot-path component** (lineage is a byproduct of the persist write already done).
- **Canonical catalog:** four-level hierarchy **Document → Item → Chunk → Version**, keyed on
  `resource_id` + `source_item_version`. The **Item** level is defined as the finest source unit
  carrying *one* ACL — that is where [RAG §2.2](rag/00-retrieval-pipeline.md)'s mixed-ACL
  invariant lives (per-message emails, per-sheet workbooks). `resource_id` = the platform-wide
  join key; `source_item_version` = the coherence key; `superseded_by` = version history
  (Principle 8). A denormalized chunk projection (labels, ACL arrays, `embed_model`,
  `section_path`) keeps retrieval + citation single-store reads.
- **Closed classification vocabulary** (M3): `sensitivity ∈ {public,internal,confidential,
  restricted:<class>}`, `pii ∈ {true,false}+pii_class:<type>`, `legal_hold ∈ {true,false}+
  matter:<id>`. **An unregistered label is a write-boundary schema violation → DLQ, never
  stored** — this is what makes the [Governance §4](governance/00-governance-and-audit.md) matrix
  *total* (every label a chunk can carry has a defined action). Unlabeled defaults to `internal`,
  never `public` (fail-closed classification).
- **Explicit lineage graph** (M2) `source→raw→parsed→chunk→vector`, emitted at persist carrying
  the ingestion `job_trace_id`, **traversable both directions**: forward = erasure-completeness +
  re-embed; backward = audit/citation evidence. The `re_embedded_from` edge is itself the proof a
  re-embed was source-independent ([Workers §6](workers/00-ingestion-architecture.md)).
- **Content-free erasure/legal-hold tombstone** (M4) — the concrete shape of
  [Storage §9](storage/00-storage-architecture.md)'s "lineage tombstone" + the
  [Governance §5](governance/00-governance-and-audit.md) legal balance (`legal_hold > erasure >
  retention`; audit retained, content erased). "No silent orphans" becomes a **provable graph
  walk**, not an assertion.
- **Metadata as the audit-evidence base** (M5): every Governance promise resolves to a catalog
  column or a lineage traversal addressable by the `resource_id`/`job_trace_id` an audit event
  already carries — [Governance §6.3](governance/00-governance-and-audit.md)'s "can the log prove
  it?" is answered by a query, not a reconstruction. Hence metadata lives transactionally with the
  ACL of record, not in a lagging analytics copy.
- **Anti-drift discipline** (M6): a `schema_version` + write-boundary validation (violation → DLQ,
  same mechanism as a malformed `map_acl`) + additive-with-migration evolution — a shared change
  can't become a silent cross-component break. Integrity invariants: every chunk has a live
  lineage path or a tombstone; version monotonicity; label ⊆ registry; no cross-tenant edge (R4).
- Recorded **[ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)**.
- Updated indexes: ADR index, `metadata/README.md` (stub → real), `platform/README.md` domain map
  (metadata → **Seeded**).
- **Directly strengthens (no new risk owned):** R1 (quarantine now auditable via `acl_confidence`
  in the catalog + orphan check), R3 (re-sync is addressable because identifiers are canonical),
  and makes Governance's erasure/retention/label promises **provable** (the evidence is a
  traversal). Closes the **last un-seeded cross-cutting store concern** (§5).
- ⏳ **Handed to downstream cycles:** the catalog-browse / lineage / DSAR-status client surface →
  [API](api/); catalog partitioning + cold-lineage archival + the lineage-integrity-check schedule
  → [Deployment](deployment/); each domain pack registers its `restricted:<class>` /
  `pii_class:<type>` values in the classification registry ([Metadata §4.1](metadata/00-catalog-and-lineage.md)).

### Cycle 7 (2026-07-06) — Governance, audit & cost
- Wrote **[governance/00-governance-and-audit.md](governance/00-governance-and-audit.md)** —
  the **policy plane**. Governance owns *policy, not mechanism*: it adds **no hot-path runtime
  component**, only a versioned (itself-audited) policy store + a reporting/metering surface over
  the existing [audit store](storage/00-storage-architecture.md); every enforcement point already
  exists (Model Gateway, retrieval filter/redactor, worker scheduler). Closes the three
  ratifications the upstream cycles queued (G1–G3) plus audit usage (G4), cost/R5 (G5), model
  governance (G6), and compliance mapping (G7).
- **Ratified freshness SLA (closes open Q#7):** contractual per-tier numbers — principal change
  **≤5 min** (Standard) / **≤2 min** (Isolated); restrictive resource-ACL **≤15 / ≤5 min**;
  widening ≤60 / ≤15 min; public best-effort. A breach = alarm **+** recorded governance incident
  (contractual reporting event for Isolated). Made affordable by the fact that query-time principal
  precedence ([Storage §7](storage/00-storage-architecture.md)) already closes offboarding
  independent of the re-tag — the tight number is really an SLA on cache-TTL+invalidation.
- **Ratified label→action policy:** platform-owned default matrix (`public`/`internal`/
  `confidential`/`pii`/`legal_hold`/`restricted:<class>`) mapping each label to retrieval / prompt /
  routing / egress, composing **most-restrictive-wins**; tenants may **tighten, never loosen**;
  labels can only subtract capability ([Permissions §7](permissions/00-authorization-model.md)
  invariant preserved).
- **Ratified retention / erasure / legal-hold:** per-store schedule (audit ≥1 yr hot / ≥7 yr cold;
  raw object 90 d→archival; DLQ 30 d; cache 5–15 min); right-to-erasure as an SLA-bound DSAR
  workflow using [Storage §9](storage/00-storage-architecture.md) propagation, **erasure recorded as
  an audit event**, **audit trail itself exempt**; precedence **legal-hold > erasure > retention**.
- **Cost model & R5 (design-mitigated):** every cost-bearing event carries `tenant_id`; per-tenant→
  pack→workload attribution; budget envelopes degrade **capability before safety** (80–100 % →
  cheaper tier + defer P2 + tighten cache; 100 % → block new P2, queue P1, alert). **A budget cap
  can never relax a permission, skip the ACL filter, or throttle a P0 revocation** — fail-closed on
  spend.
- **Audit-as-evidence:** *a promise the audit log can't evidence is not a governable promise* —
  the SLA, labels, erasure, and budgets are each proven by their event type; audit read access is
  role-gated + itself audited; hash-chain verified on schedule.
- **Model governance:** approved-model registry + **eval-before-promotion** gate (grounding, refusal
  calibration, jailbreak resistance, pack task accuracy) + per-tenant version pinning/rollback + model
  version in every retrieval audit event. **Compliance map** binds existing controls to GDPR / SOX /
  ISO 27001-SOC 2 / sector per domain, each cell evidence-backed.
- Recorded **[ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)**.
- Updated indexes: ADR index, `governance/README.md` (stub → real), `platform/README.md` domain
  map (governance → **Seeded**).
- **Directly de-risks:** R5 (cost → metering + attribution + budget envelopes + safety-preserving
  degradation ladder); **closes the SLA-number half of R3** and the label-policy dependency.
- **Closed open question #7** (freshness SLA — ratified) — see §3.
- ⏳ **Handed to downstream cycles:** actual prices / budget-envelope sizes / per-tier SLA capacity
  sizing / data residency → [Deployment](deployment/); classification schema the label policy
  consumes → [Metadata](metadata/); the client-facing surface for budgets / DSAR / audit export →
  [API](api/). Open Q#3 (model hosting) feeds the approved-model registry when decided.

### Cycle 6 (2026-07-05) — Ingestion workers & connectors
- Wrote **[workers/00-ingestion-architecture.md](workers/00-ingestion-architecture.md)** — the
  write-plane engine. Turns the Cycle 3–5 write-side obligations (W1 idempotent version-keyed
  writes, W2 ACL-denorm coherence, W3 change-driven re-sync, W4 source-independent re-embed,
  W5 mixed-ACL invariant at write time, W6 least-privilege per-tenant execution, W7 backpressure)
  into a selected shape: a **staged DAG** (fetch → parse → map_acl → chunk → embed → persist),
  each stage reading/writing a durable artifact so failures resume without re-hitting the source.
- Wrote **[workers/01-connector-framework.md](workers/01-connector-framework.md)** — the
  source-specific boundary: a **six-method `Connector` port** (`list_items`, `fetch`, `map_acl`,
  `subscribe_changes`, `list_principal_changes`, `capabilities`); per-source `map_acl` duties
  (R1 implementation); versioning + fault isolation (R6); and the **permission-conformance suite
  as the production gate** ([Permissions §11](permissions/00-authorization-model.md)) running in
  CI **and** a production canary that **auto-quarantines** a source on drift.
- **Key decisions:** (a) **at-least-once delivery + idempotent version-keyed writes** — refuse
  exactly-once, make replays/outbox-double-delivery harmless; (b) **strict priority classes with
  fairness guards** (P0 revocation/security ≤5/≤15 min · P1 content delta · P2 backfill/re-embed/
  reconciliation) so a backfill can **never** starve a revocation (**R8 core**); (c) the
  [Storage §7](storage/00-storage-architecture.md) coherence relay = **transactional outbox** at
  the dedicated-engine tier (pgvector tier stays same-transaction); (d) re-embed/re-chunk =
  **blue/green P2 jobs reading the parsed object artifact, never the source**
  ([Storage §8](storage/00-storage-architecture.md)); (e) **least privilege split** — the
  read-source credential and the write-ACL credential live in different worker pools; (f) under
  load the plane **drops recall before it drops a revocation** (fail-closed on the write path).
- Recorded **[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md)**.
- Updated indexes: ADR index, `workers/README.md` (stub → real), `platform/README.md` domain
  map (workers → **Seeded**).
- **Directly de-risks:** R8 (backlog → freshness: priority + fairness + lag alarms, made
  *observable*), R6 (connector fragility: independent versioning + schema-validated boundary +
  conformance canary), R3 write-half (change-driven content/ACL re-sync + P0 principal re-sync).
- **Strengthened open question #7** (freshness SLA): the priority-class model now *implements*
  the proposed ≤5/≤15 min targets and the relay-lag/queue-lag alarms that enforce them — still
  **pending [Governance](governance/) ratification** of the actual numbers.
- ⏳ **Handed to downstream cycles:** freshness-SLA ratification (Q#7) + per-tenant ingest cost +
  DLQ/retention policy → [Governance](governance/) (Cycle 7); concrete broker choice per tier +
  worker autoscaling topology + secret provisioning → [Deployment](deployment/); lineage schema
  emitted by the persist stage → [Metadata](metadata/).

### Cycle 5 (2026-07-05) — Storage & tenancy deep dive
- Wrote **[storage/00-storage-architecture.md](storage/00-storage-architecture.md)** — the
  data-plane payoff. Turns the Cycle 3+4 hard requirements (S1 set-overlap filtering,
  S2 hybrid-under-one-filter, S3 versioned upsert/delete, S4 isolation-by-construction,
  S5 in-boundary+BYOK, S6 rich metadata, S7 append-only audit) into a selected topology:
  the **five-store data plane** (object / vector+keyword / relational-source-of-truth /
  cache / append-only audit), each assigned by scaling axis, consistency, and blast radius.
- **Resolved open question #1 (FINAL):** vector layer = **pgvector-in-Postgres as default**
  (co-locates vector + `text[]` ACL arrays w/ GIN `&&` + `tsvector` full-text + metadata in
  one transaction → both hybrid halves share one filter, ACL denormalization is drift-free),
  **graduating** per-tenant to Qdrant / Elasticsearch on *measured* thresholds. Confirms &
  finalizes [ADR-0009 §6](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)'s
  provisional lean. Introduced the **`VectorIndex` port with no unfiltered-search method** —
  filter-during-retrieval ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md))
  becomes *structurally* impossible to bypass, and vector lock-in (R7) is bounded to one adapter.
- **Resolved open question #5 (FINAL):** **a tenant = one customer organization** (isolation
  & governance boundary); departments/domains are ACL/`visibility` scopes and packs *within*
  a tenant — aligns the storage isolation primitive with the CPI identity namespace.
- Specified **two isolation tiers** per store (Shared: namespace/schema/prefix + RLS +
  unconditional `tenant_id`, two independent controls; Isolated: dedicated cluster/DB/bucket +
  BYOK), **envelope encryption w/ per-tenant DEKs + crypto-erasure**, the
  **ACL-denormalization coherence** rules (same-transaction at pgvector tier; transactional
  outbox at dedicated-engine tier; query-time principal precedence covers the residual gap),
  **re-embed migrations** (blue/green from the parsed object-store artifact — no source re-hit),
  and **right-to-erasure** propagation across all five stores (audit retained as event).
- Recorded **[ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)**.
- Updated indexes: ADR index, `storage/README.md` (stub → real), `platform/README.md`
  domain map (storage → **Seeded**).
- **Directly de-risks:** R4 (cross-tenant → namespace **and** predicate, two controls;
  per-tenant DEK), R5 (cost → pgvector-default + object tiering + quantization levers),
  R7 (vector lock-in → `VectorIndex` port, one adapter per engine).
- ⏳ **Handed to downstream cycles:** the **transactional-outbox relay** + **re-embed/re-sync
  jobs** → [Workers](workers/) (Cycle 6, must honor the §7 coherence bound and the freshness
  SLA); **retention + legal-hold tombstone + per-tenant cost metering + erasure ratification**
  → [Governance](governance/) (Cycle 7); **per-tier topology, graduation thresholds, backup/DR**
  → [Deployment](deployment/); **catalog + lineage schema** detail → [Metadata](metadata/).

### Cycle 4 (2026-07-05) — RAG retrieval pipeline deep dive
- Wrote **[rag/00-retrieval-pipeline.md](rag/00-retrieval-pipeline.md)** — the query-plane
  payoff. Specifies **structure-aware chunking** (heading/clause/table-row/per-email-message,
  with the **mixed-ACL invariant**: a chunk never spans two items with different ACLs),
  **universal embedding space + per-domain normalization** (not per-domain models;
  versioned re-embed on model upgrade), **hybrid search** (dense + BM25, RRF fusion) with
  the **permission predicate pushed into *both* engines** (consumed from Permissions §6,
  not re-specified), **cross-encoder reranking** (+ MMR, degradable latency dial), **context
  assembly** (dedup / budget / cite-tag / label redaction) with the **prompt-injection (R2)
  data-boundary defense**, the **verifier contract** (grounding / citation validity /
  no-context honesty / guardrails / label compliance — refuse-over-guess), a latency budget,
  and a **provisional vector-store position** (open Q#1).
- Recorded **[ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)** —
  hybrid permission-filtered retrieval + structure-aware chunking. Obeys ADR-0004, pushes
  the ADR-0008 predicate into search, mediated by ADR-0003 gateway.
- Updated indexes: ADR index, `rag/README.md` (stub → real), `platform/README.md` domain
  map (rag → **Seeded**).
- **Directly de-risks:** R2 (prompt injection → retrieved-text-as-data boundary + verifier
  backstop). Design mitigation now documented, not just named.
- **Answered open questions:** #4 (chunking & embedding strategy — **decided**:
  structure-aware chunking + universal space + per-domain normalization).
- **Provisionally answered:** #1 (vector store — pgvector for small tenants graduating to a
  dedicated engine; **Storage/Cycle 5 owns the final call**).
- ⏳ **Handed to downstream cycles:** vector + keyword indexes must support efficient
  **set-overlap filtering** on principal arrays and **hybrid search under one metadata
  filter** (hard selection criteria → Storage); chunk parsers per content-type + embedding
  jobs + re-embed migration → Workers; audit-trail fields (principals, chunk IDs, rerank
  scores, verifier verdict) → Governance.

### Cycle 3 (2026-07-05) — Permissions & Identity deep dive
- Wrote **[permissions/00-authorization-model.md](permissions/00-authorization-model.md)** —
  the platform's hardest correctness guarantee. Defines the **canonical four-noun model**
  (Subject / Principal / Grant / Resource), the **Canonical Principal Identifier**
  (`tenant:source:type:stable-id`, keyed on non-reusable source ids), the **single
  decision predicate** (tenant → confidence=`exact` → deny-wins → require-allow),
  query-time **effective-principal resolution** via an identity graph (nested-group
  expansion + explicit cross-source links), **filter-during-retrieval** mechanics,
  per-source ACL mapping (SharePoint / SAP / Email / file share), **sensitivity labels as
  a second independent gate**, the **freshness** strategy (query-time precedence + short
  revocable TTL + change-driven re-sync), the **unmappable-source quarantine doctrine**,
  delegated/OBO access, and the **permission-conformance test suite** (the production gate).
- Recorded **[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)** —
  normalize every source ACL into one canonical model (the *how* behind ADR-0004's *what*).
  Owns risks R1, R3, R4.
- Updated indexes: ADR index, `permissions/README.md` (stub → real), `platform/README.md`
  domain map (permissions → **Seeded**).
- **Directly de-risks:** R1 (mismatch → conformance suite + confidence-gated deny),
  R3 (staleness → query-time precedence + SLA), R4 (cross-tenant → tenant-namespaced CPIs).
- **Provisionally answered open questions:** #2 (permission normalization model — decided),
  #7 (freshness SLA — proposed: principals ≤5 min, restricted resource ACLs ≤15 min,
  pending Governance ratification).
- ⏳ **Handed to downstream cycles:** vector store must support efficient **set-overlap
  filtering** on principal arrays (hard requirement → Storage, open question #1); label
  policy + SLA ratification → Governance; change-driven re-sync → Workers.

### Cycle 2b (2026-07-05) — v3.0 harvest + client settings UI
- **Client settings UI** ([ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md)):
  `control_panel.py` + `EINSTELLUNGEN.bat` — browser page (stdlib only) to set autonomy,
  models, limits **and manage connectors** (`connectors.yaml` allowlist) with validation;
  syncs `config.json` + `project/manifest.json`. End-to-end tested.
- **Harvested v3.0 assets onto the core** ([ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md)):
  `core/workers.py` (least-privilege WorkerRegistry), `core/handoff.py` (allowlisted
  router), `tools/check.py` (project-pack validator, CI exit codes),
  `scripts/deploy.{sh,ps1}`, `pytest.ini`, `requirements-dev.txt`. Added `workers`/
  `handoffs` config to `project/manifest.json`.
- **Tests:** 62 green (23 workers + 24 handoff + 11 check + 4 tools).
- ⏳ **Still staged (not done):** wiring `WorkerRegistry`/`HandoffRouter` INTO
  `core/orchestrator` at runtime; rewriting v3.0's `test_agent.py` against `core/`;
  retargeting `test_brain`/`test_governance`; coverage gate `--cov=core --cov-fail-under=80`;
  deeper governance hardening (high-risk block before autonomy shortcut, per ADR-0006).

### Cycle 2 (2026-07-05) — Branch consolidation (design council)
- Convened a **5-member design council** (Enterprise Architect, Senior Engineer,
  Security & Governance, QA & Test, Redundancy & Consistency) to reconcile 4 divergent
  template branches into "the perfect agent template."
- **Decision → [ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md):**
  keep `core/`+`project/` as base, **merged `tender-feistel`** (skills, connectors,
  steering examples, leaf-write governance, financial-services patterns), and defined a
  **harvest plan** for the v3.0 (`kind-keller`) fork instead of merging it wholesale.
- **Security fix → [ADR-0006](architecture/adr/ADR-0006-fail-closed-autonomy-default.md):**
  reverted the fail-open full-autonomy default to **fail-closed-by-default**
  (`core/governance.py._approval_required` now defaults True; autonomy is explicit opt-in
  via `autonomy_level: "max"`).
- Merge landed on `main`, core modules import clean, existing tests pass.
- ⏳ **Not yet merged:** the v3.0 asset harvest (see §6 Cycle 2b) and the other
  contained branches are superseded.

### Cycle 1 (2026-07-05) — Foundation
- Established `platform/` as the documentation root with a per-concern folder layout
  (architecture, security, rag, permissions, storage, metadata, workers, api,
  deployment, governance) and a navigation index (`platform/README.md`).
- **[Vision & Principles](architecture/00-vision-and-principles.md)** — mission,
  target domains, 8 non-negotiable principles, honest trade-offs, non-goals.
- **[Platform Overview](architecture/01-platform-overview.md)** — C4 context +
  container diagrams, the **three-plane model** (Query / Ingestion / Data + cross-
  cutting), request and ingestion lifecycles as sequence diagrams.
- **[Security Architecture](security/00-security-architecture.md)** — trust boundary,
  identity/authz, multi-tenant isolation tiers, data protection, STRIDE + OWASP-LLM
  threat model, fail-closed doctrine.
- **[ADR log](architecture/adr/)** — ADR-0001 (private RAG shape), ADR-0002 (reuse
  template core as tenancy seed), ADR-0003 (model gateway), ADR-0004 (permission-
  faithful retrieval).

---

## 2. Architecture decisions (accepted so far)

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| ADR-0001 | Privately-hosted, permission-aware RAG | Fresh, auditable, per-user-filterable knowledge in-boundary |
| ADR-0002 | Reuse template core/project split as tenancy seed | Continuity; domain-agnostic core already proven |
| ADR-0003 | All inference via a Model Gateway | One choke point for governance, cost, vendor independence |
| ADR-0004 | Enforce end-user permissions at query time | Safe for Finance/HR/Legal/Audit; fail closed |
| ADR-0008 | Normalize every source ACL into one canonical principal model | One filterable predicate; new source = connector + conformance test, not a redesign |
| ADR-0009 | Hybrid permission-filtered retrieval + structure-aware chunking | Exact-token + semantic recall; safety stays one index predicate; new domain = parser, not a pipeline change |
| ADR-0010 | Five-store data plane; pgvector-default vector layer (graduate on measured need) behind a filter-only `VectorIndex` port; tenant = customer org | Meets every S1–S7 requirement; ACL stays a single-store `WHERE`; unfiltered search is unrepresentable; lock-in bounded to one adapter |
| ADR-0011 | Ingestion = staged-DAG workers; at-least-once + idempotent version-keyed writes; priority classes (P0 revoke > P1 delta > P2 backfill); outbox coherence relay; conformance-gated connector contract | Resumable/scalable/contained ingestion; backlog can't starve a revocation (R8); new source = connector + suite, not redesign; write path fail-closed |
| ADR-0012 | Governance = policy plane (no hot-path component); ratified per-tier freshness SLA + label→action matrix + retention/erasure; audit-as-evidence; per-tenant budgets that degrade capability-before-safety; eval-gated model registry; per-domain compliance map | Promises become contractual & provable; cost control (R5) can never regress into a safety leak; new domain inherits a control map, not a redesign |
| ADR-0013 | Canonical metadata: four-level catalog (Doc→Item→Chunk→Version) + explicit bidirectional lineage graph + closed classification vocabulary + content-free erasure tombstone; held in the relational SoT, no new store; versioned + write-boundary-validated | Four consumers share one contract not four shapes; the Governance label matrix becomes total; erasure-completeness & audit-evidence become provable queries; new domain/artifact type = additive registration, not a schema redesign |
| ADR-0014 | API contract: token-bound identity (tenancy never in URL) + OBO via token exchange; dual sync/streaming answer under one verifier gate; "no access" is a 200; one typed-error envelope; heavy work = jobs; admin-can-only-tighten; filter-parity reads; URL-major additive versioning | Permission-faithful retrieval enforced once at audited choke points not re-argued per endpoint; impersonation/cross-tenant unrepresentable on the wire; budgets throttle cost not safety; new pack = additive, not a version event |
| ADR-0015 | Deployment DR: active-passive per residency region (no active-active writes); ACL-first fail-closed recovery (SoT→object→vector-rebuild→cache); vectors rebuilt not backed up; tiered RPO/RTO; reserved (not autoscaled) P0 capacity | No cross-region window disagrees on a revocation; the platform recovers fail-closed (permissions before content); a restore can't resurrect a vector snapshot that disagrees with recovered ACLs; the revocation SLA is provisioned in advance |
| ADR-0016 | Domain pack contract: a pack is additive data + policy, **tighten-only**, exactly six sections, with a mandatory §0 horizontal-change ledger + a falsifiability rule (can't-fit → horizontal ADR, never a pack-local hack) | Makes "new domain = pack, not redesign" a reviewable/blockable contract not a slogan; a misconfigured pack can only over-restrict (availability), never over-expose (safety); Finance (reference pack) proved zero horizontal changes against the hardest domain |

---

## 3. Open questions (need a decision in an upcoming cycle)

1. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Vector store choice~~ — **pgvector-in-Postgres is the default** (co-locates vector +
   `text[]` ACL arrays w/ GIN `&&` + `tsvector` + metadata in one transactional store),
   **graduating per-tenant** to Qdrant / Elasticsearch on *measured* thresholds (chunk count,
   QPS/SLA, keyword dominance, isolation mandate). All engines sit behind a **`VectorIndex`
   port that has no unfiltered-search method**. See [Storage §3](storage/00-storage-architecture.md).
   Remaining sub-question deferred to [Workers](workers/): the transactional-outbox relay
   that keeps the denormalized chunk-ACL coherent at the dedicated-engine tier.
2. ✅ **DECIDED (Cycle 3, [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)).**
   ~~Permission normalization model~~ — canonical four-noun model + CPI, normalize at
   ingestion, enforce one predicate at query time. Remaining sub-question deferred to
   connector cycles: the exact `map_acl` fidelity achievable per SAP module.
3. **Model hosting** — in-boundary OSS models vs. contractually-private managed
   endpoints (or both, by tenant tier). Drives cost, latency, and compliance posture.
   **Cycle 7 note:** Governance built the **approved-model registry + eval-before-promotion
   gate** ([Governance §8](governance/00-governance-and-audit.md)) that *any* hosting choice
   flows through; the label→trust routing matrix ([Governance §4](governance/00-governance-and-audit.md))
   already expresses the compliance side. The still-open decision is the concrete
   *in-boundary-vs-managed-private posture per tenant tier* — feed it into the registry when
   decided (may warrant its own ADR; [ADR-0012 revisit-when](architecture/adr/ADR-0012-governance-audit-and-cost.md)).
4. ✅ **DECIDED (Cycle 4, [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)).**
   ~~Chunking & embedding strategy~~ — **structure-aware chunking** (heading/clause/table-row/
   per-email-message; mixed-ACL invariant) + **universal embedding space with per-domain
   text normalization** (not per-domain models) + versioned re-embed on model upgrade. See
   [RAG §2–§3](rag/00-retrieval-pipeline.md). Remaining sub-question deferred to Workers:
   the exact per-content-type parser fidelity (OCR layout, SAP table serialization).
5. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Tenancy granularity~~ — **a tenant = one customer organization** (isolation & governance
   boundary owning its data, identity namespace, policies, cost envelope). Departments and
   domains are ACL/`visibility` scopes and packs *within* a tenant, not separate tenants —
   this keeps the CPI identity namespace and nested-group resolution intact. See
   [Storage §5](storage/00-storage-architecture.md).
6. **Agent framework** — extend the existing `core/` planner/verifier into the
   distributed orchestrator, or adopt a framework? (Relates to ADR-0002.)
7. ✅ **DECIDED (Cycle 7, [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)).**
   ~~Freshness SLA~~ — **ratified as contractual per-tier numbers**
   ([Governance §3](governance/00-governance-and-audit.md)): principal change ≤5 min
   (Standard) / ≤2 min (Isolated); restrictive resource-ACL ≤15 / ≤5 min; widening ≤60 / ≤15 min;
   public best-effort. A breach is an alarm **and** a recorded governance incident (contractual
   reporting event for Isolated tenants). Workers already *implements and measures* these
   ([workers §4.2, §10](workers/00-ingestion-architecture.md)); Governance fixed the promise +
   consequences. Remaining sub-question deferred to [Deployment](deployment/): the
   reserved-P0-capacity / relay-poll-frequency **sizing** that meets each ratified number at cost
   (a tuning knob, not a redesign).

---

## 4. Technical risks (tracked)

| # | Risk | Severity | Mitigation direction |
|---|------|----------|----------------------|
| R1 | **Permission-model mismatch** — source ACLs can't be faithfully normalized → leak | **Critical** | ✅ *Design mitigated (Cycle 3):* canonical model + `acl_confidence` gate (approximate→deny) + per-connector conformance suite + quarantine tier. Residual: correct **implementation** of each connector's `map_acl`. |
| R2 | **Prompt injection via retrieved content** | **Critical** | ✅ *Design mitigated (Cycle 4, [RAG §6.1, §7](rag/00-retrieval-pipeline.md)):* retrieved text delivered inside a data boundary (not instructions), retrieved content cannot alter tool/routing/citation policy, verifier enforces grounding + guardrails as the backstop. Residual: implementation hardening of the verifier + red-team corpus. |
| R3 | **Stale permissions** — user loses access but index still serves it | High | ✅ *Design mitigated (Cycles 3+6):* query-time principal precedence ([Permissions §8](permissions/00-authorization-model.md)) closes offboarding regardless of chunk lag; the write half — **change-driven content/ACL re-sync at P0/P1** + the **outbox relay bounded by the freshness SLA** ([workers §5, §7](workers/00-ingestion-architecture.md)) — closes the resource-re-tag case; relay/queue lag is alarmed (§10). Residual: SLA number ratification (Q#7). |
| R4 | **Cross-tenant leakage** via a filtering bug | High | ✅ *Design mitigated (Cycle 5, [Storage §5.2](storage/00-storage-architecture.md)):* Shared tier uses **two independent controls** (per-tenant namespace/schema **and** an unconditional `tenant_id` predicate); Isolated tier = dedicated cluster/DB/bucket + per-tenant DEK; the `VectorIndex` port takes a `tenant` on every call (cross-tenant query unrepresentable). Residual: correct namespace provisioning per tenant. |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | ✅ *Design mitigated (Cycle 7, [Governance §7](governance/00-governance-and-audit.md)):* per-tenant **metering + attribution** (every cost event carries `tenant_id`, assembled tenant→pack→workload), **budget envelopes**, and a **graceful-degradation ladder** that degrades *capability before safety* (cheaper model tier + defer P2 + tighten cache; then block new P2, queue P1) — **a budget cap can never relax a permission, skip the ACL filter, or throttle a P0 revocation**. Upstream levers (model tiering [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md), quantization/tiering [Storage §10](storage/00-storage-architecture.md), embed batching [Workers §4.3](workers/00-ingestion-architecture.md)) now have an owner that pulls them. Residual: actual **prices + envelope sizes** per tier ([Deployment](deployment/), empirical). |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | ✅ *Design mitigated (Cycle 6, [connector §3, §5](workers/01-connector-framework.md)):* independently-versioned connectors + a **schema-validated** return boundary (malformed ACL → DLQ, never the store) + the **conformance suite as a production canary** that **auto-quarantines** a source on semantic drift. Residual: implementation of each connector's change-detection. |
| R7 | **Vendor lock-in** at model or vector layer | Medium | ✅ *Design mitigated (Cycle 5, [Storage §3.4](storage/00-storage-architecture.md)):* the **`VectorIndex` port** confines each engine to one adapter; a tenant migration is a re-index through the port, not a pipeline rewrite (the vector-layer analogue of the Model Gateway). Models already covered by [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md). |
| R8 | **Ingestion backlog** starves freshness | Medium | ✅ *Design mitigated (Cycle 6, [workers §4, §10](workers/00-ingestion-architecture.md)):* **strict priority classes** (P0 revoke > P1 delta > P2 backfill) with **fairness guards** so a backfill can't starve a revocation; bounded-lease backpressure; per-tenant weighted-fair scheduling; **queue-lag alarms** make a looming SLA breach loud, not silent. Residual: autoscaling tuning ([Deployment](deployment/)). |

---

## 5. Documentation gaps (folders still empty / thin)

- ✅ `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding, verifier). **Seeded (Cycle 4).**
- ✅ `permissions/` — canonical ACL model + per-source mapping. **Seeded (Cycle 3).**
- ✅ `storage/` — five-store data plane, pgvector-default vector layer + `VectorIndex` port, tenancy definition, isolation tiers, encryption/BYOK, coherence, migrations, erasure. **Seeded (Cycle 5).** Resolved open Q#1 (final) + Q#5 (final); mitigated R4/R5/R7 by design.
- ✅ `workers/` — staged-DAG ingestion, `IngestionTask` queue + idempotent version-keyed writes, priority classes (R8), outbox coherence relay, re-embed migrations, change-driven re-sync, DLQ, least-privilege posture, connector contract + conformance gate. **Seeded (Cycle 6).** Mitigated R8/R6/R3-write by design; strengthened Q#7.
- ✅ `metadata/` — canonical four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification/label vocabulary, content-free erasure tombstone, metadata-as-audit-evidence, schema versioning/validation. **Seeded (Cycle 8).** Closed the last un-seeded cross-cutting store concern; made Governance's label matrix total and its erasure/audit promises provable.
- ✅ `api/` — external surface: five resource groups, token-bound identity + OBO, query/answer + streaming contract (one verifier gate), one typed-error envelope, async-job pattern, admin-can-only-tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major versioning. **Seeded (Cycle 9).** Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued; enforced permission-faithfulness once at the edge.
- ✅ `deployment/` — physical projection: per-tier reference topology + graduation, environments,
  safety-gated CI/CD (conformance suite as un-overridable release veto), reserved-P0 SLA-capacity
  sizing, cost-envelope/residency routing, catalog partitioning + cold-lineage archival + integrity
  checks, gateway/rate-limit/streaming ops, and **ACL-first active-passive DR/BCP** with per-store
  backup/restore. **Seeded (Cycle 10).** Discharged the sizing/tuning inputs Cycles 5–9 queued;
  closed the residual/empirical half of R3/R5/R8 and operationalized R4.

**→ All eight core platform surfaces (architecture, security, permissions, rag, storage, workers,
metadata, api, governance, deployment) are now Seeded. §5 is fully closed.** The remaining work is
domain-pack specifications, code reconciliation, and the two open engineering questions (Q#3, Q#6).
- ✅ `governance/` — policy plane: ratified freshness SLA + label→action matrix + retention/erasure, audit usage (retention/access/evidence), per-tenant cost model & budgets (R5), model governance, compliance map. **Seeded (Cycle 7).** Closed open Q#7; mitigated R5 by design.

---

## 6. Priority list & recommended implementation order

Ordered by **architectural leverage** (unblocks the most, de-risks the most).

### ✅ Cycle 2b (DONE — see §1): harvested deploy scripts, `tools/check.py`,
`core/workers.py`, `core/handoff.py`, tests (62 green), and shipped the client settings
UI with connector management. Remaining harvest work moved to Cycle 2c below.

### ⏸ Cycle 2c (OPEN — parallel *engineering* track, not the architecture-doc path):
**Wire the harvested modules into the runtime + finish tests.** This is code work on the
`core/` template, independent of the platform architecture docs. Pick it up in a coding
cycle; the doc track (below) does not depend on it.
1. **Wire `WorkerRegistry` + `HandoffRouter` into `core/orchestrator`/`dispatcher`** so
   the ported modules actually scope tools and route handoffs at runtime (currently they
   are available + configured + unit-tested, but not yet called by the loop). Reconcile
   worker trust-level ↔ tender leaf-write into ONE governance API.
2. **Finish the test port:** rewrite v3.0's `test_agent.py` against `core/orchestrator`;
   retarget `test_brain`/`test_governance` to the `core/` modules; enforce
   `--cov=core --cov-fail-under=80` in CI (GitHub Actions).
3. **Deeper governance hardening** (ADR-0006 follow-up): run the high-risk hard block
   *before* the autonomy shortcut; make escalation a deterministic policy decision, not an
   LLM `needs_human` flag.
4. **Onboarding UX polish** — fold kind's plain-German beginner prompts + self-test into
   `agent_cli.py`; add Python-check/pip-install robustness to the `.bat` launchers. Then
   **delete** the superseded `kind-keller` branch content.
**Do NOT push a broken tree — gate on tests green.**

### ✅ Cycle 3 (DONE — see §1): **Permissions & Identity deep dive**
Wrote `permissions/00-authorization-model.md` + [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md).
Canonical model, query-time enforcement, freshness, conformance suite. Mitigates R1/R3/R4
by design; decided open question #2; provisional answer to #7.

### ✅ Cycle 4 (DONE — see §1): **RAG pipeline deep dive**
Wrote `rag/00-retrieval-pipeline.md` + [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md).
Structure-aware chunking, universal embedding space, hybrid search consuming the permission
filter, reranking, grounding/citation, verifier contract. Decided open question #4; mitigated
R2 by design; provisional answer to #1.

### ✅ Cycle 5 (DONE — see §1): **Storage & tenancy deep dive**
Wrote `storage/00-storage-architecture.md` + [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md).
Five-store data plane, pgvector-default vector layer behind a filter-only `VectorIndex` port,
tenant = customer org, isolation tiers, encryption/BYOK, ACL-denormalization coherence,
re-embed migrations, erasure. Resolved open questions 1 (final) and 5 (final); mitigated
R4/R5/R7 by design.

### ✅ Cycle 6 (DONE — see §1): **Ingestion workers & connectors**
Wrote `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md` +
[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).
Staged-DAG pipeline, idempotent version-keyed writes, priority classes + fairness (R8),
outbox coherence relay ([Storage §7](storage/00-storage-architecture.md)), re-embed
migrations, change-driven re-sync, DLQ, least-privilege posture, six-method connector
contract, conformance gate + canary. Mitigated R8/R6/R3-write by design; strengthened Q#7.

### ✅ Cycle 7 (DONE — see §1): **Governance, audit & cost**
Wrote `governance/00-governance-and-audit.md` + [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md).
Policy plane (no hot-path component): ratified freshness SLA per tier (closed Q#7), label→action
matrix, retention/erasure/legal-hold; audit-as-evidence (retention/access/hash-chain); per-tenant
cost model + budgets that degrade capability-before-safety (mitigated R5 by design); eval-gated
model registry; per-domain compliance map. Handed Deployment the prices/envelopes/SLA-capacity
sizing, Metadata the classification schema, and API the budget/DSAR/audit-export surface.

### ✅ Cycle 8 (DONE — see §1): **Metadata — catalog, lineage & classification schema**
Wrote `metadata/00-catalog-and-lineage.md` + [ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md).
Four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification
vocabulary (makes the Governance matrix total), content-free erasure tombstone, metadata-as-audit-
evidence, schema versioning/validation. Held in the relational SoT — no new store, no hot-path
component. Closed the last un-seeded cross-cutting store concern; strengthened R1/R3 and made
Governance's erasure/retention/label promises provable. A cross-component schema decision *did*
emerge → ADR-0013.

### ✅ Cycle 9 (DONE — see §1): **API — external surface, contracts & versioning**
Wrote `api/00-api-surface.md` + [ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md).
Five resource groups, token-bound identity + OBO (tenancy never in the URL), dual sync/streaming
query contract under one verifier gate, one typed-error envelope, async-job pattern, admin-can-only-
tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major additive
versioning. Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued;
enforced permission-faithful retrieval once at the edge (a contract-shape decision was cross-component
→ ADR-0014).

### ✅ Cycle 10 (DONE — see §1): **Deployment — topology, environments, CI/CD, DR/BCP**
Wrote `deployment/00-deployment-topology.md` + [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md).
Physical projection of the three planes; per-tier topology + graduation; safety-gated CI/CD
(conformance suite as release veto); reserved-P0 SLA-capacity sizing; cost-envelope/residency
routing; catalog partitioning + cold-lineage archival + integrity checks; gateway/streaming ops;
**ACL-first active-passive DR** with per-store backup/restore (a cross-component DR decision → ADR-0015).
Discharged the sizing/tuning inputs Cycles 5–9 queued; **closed §5 — all core surfaces Seeded.**

### ✅ Cycle 11 (DONE — see §1): **Domain Pack #1 — Finance + the pack-spec skeleton**
Wrote `packs/README.md` (the reusable six-part skeleton + §0 ledger + falsifiability rule),
`packs/finance/00-finance-pack.md` (the reference pack), and
[ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) (the pack contract).
Finance's §0 horizontal-change ledger records **zero** horizontal changes against the hardest
domain — the founding bet held. HR/Legal/Audit/KM/SAP/SharePoint/Email packs are now
fill-in-the-blank against the Finance template.

### ✅ Cycle 12 (DONE — see §1): **Domain Pack #2 — HR**
Wrote `packs/hr/00-hr-pack.md` against the [pack skeleton](packs/README.md). No new ADR (HR is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md), like Finance).
**§0 ledger = none, all additive — the skeleton generalized from n=1 to n=2 cleanly.** The hardest
case (employee-self-scoped ACLs) resolved to the *degenerate* set-membership predicate (owner CPI is
already an effective principal); computed manager-hierarchy rules reused the §9/§10 escape hatch.
Registered `pii_class:health`/`employment`/`restricted:works_council`; tightened the matrix with a
manager-visibility carve-out; exercised the reflexive self-DSAR and `legal_hold > erasure > retention`.

### ✅ Cycle 13 (DONE — see §1): **Domain Pack #3 — Legal (privilege, ethical walls & holds)**
Wrote `packs/legal/00-legal-pack.md` against the [skeleton](packs/README.md). No new ADR (Legal is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First genuine
novel-concept falsifiability test since Finance — the rule was armed and did NOT fire.** Privilege
*waiver* resolved additively by separating **what** (`restricted:privileged` label) from **who** (item
ACL): waiver = a *narrowing ACL grant edit* propagated by the existing re-sync, **never** a label
removal; "per recipient" is what an ACL already is, so the static label→action matrix needs no
recipient policy. Ethical walls = the existing deny-wins clause. Registered `restricted:privileged` +
`restricted:work_product`; reused `matter:<id>`. The platform *mirrors* privilege (computed/unresolvable
privilege → `approximate → deny + quarantine`), never *computes* waiver.

### ✅ Cycle 14 (DONE — see §1): **Domain Pack #4 — Audit (mostly inherited) + segregation-of-duties**
Wrote `packs/audit/00-audit-pack.md` against the [skeleton](packs/README.md). No new ADR (Audit is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First
*combinatorial*-concept falsifiability test — the rule was armed and did NOT fire, but for a sharper
reason than Legal's:** SoD *prevention* is a write/transaction control **out of the platform's plane**
(read-plane mirror — the platform never posts/approves/executes); SoD *read*-exclusion = the existing
deny-wins clause (a unary `deny`, pre-resolved by the source, identical to Legal's ethical wall); SoD
*detection* ("who both prepared and approved?") = an ordinary permission-gated retrieval whose
combinatorial join lives in the query + source data, never in the access predicate. Registered
`restricted:audit_workpaper`; inherited Finance's SOX row + SAP fidelity + Legal's `matter:<id>` hold +
the S7 append-only trail verbatim. Documented the **read-plane-mirror scope boundary** as the explicit
reason no transaction-control ADR was needed (and named the future *action-taking* pack that would).

### ✅ Cycle 15 (DONE — see §1): **Domain Pack #5 — Knowledge Management (the inverse stress)**
Wrote `packs/km/00-km-pack.md` against the [skeleton](packs/README.md). No new ADR (KM is a worked
instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First *inverse*
(over-refusal) falsifiability test — the rule was armed against a *loosening* and did NOT fire.**
Over-refusal resolved as a *tuning/eval* problem **upstream** of the filter and verifier (query
expansion, rerank/MMR, dedup, KM-eval-tuned model on the *already-permitted* set), **never** a
floor-loosening one — all three temptations (widen default label, relax grounding bar, unfiltered list
mode) rejected *and* shown unnecessary. **First pack with empty §2 + §3** (zero new vocabulary, zero
tighten, zero loosen) — the empty tables *are* the proof the low-restriction defaults are already
calibrated. Eval headline inverted to **recall / over-refusal** while retaining the permission-negative
class (recall chased without trading away safety).

### ▶ Cycle 16 (do next): **Domain Pack #6 — SAP (the first source-shaped pack)** *(or KM-adjacent runtime SPI, see below)*
Write `packs/sap/00-sap-pack.md` against the [skeleton](packs/README.md). *Why next:* the five
concept-driven packs (Finance/HR/Legal/Audit/KM) have now stressed every *policy* corner — the
restrictive `who`-gated cases **and** the inverse over-refusal case. The remaining packs are
**source-shaped**, not concept-shaped: their whole content is **connector `map_acl` fidelity**, and SAP
is the hardest and most-reused of them (no document ACL; row/record scope; field-level authorization;
FI/CO + HCM + GRC modules). Finance already proved SAP fidelity *for financial content* and Audit/HR
reused it — Cycle 16 consolidates SAP as a **first-class source pack** whose §1 is the canonical SAP
`map_acl` reference all other packs cite, with the module-by-module fidelity matrix (the sub-question
open Q#2 deferred: *exact `map_acl` fidelity achievable per SAP module*). *Falsifiability check:* if any
SAP module exposes authorization the connector cannot resolve to a principal set *and* cannot quarantine,
that is a real R1 gap → a Permissions ADR; expected resolution: every unresolvable case rides the
*existing* `approximate → deny + quarantine` hatch (as Finance's field-level auth already does). Then
SharePoint and Email are near-pure fidelity reuse (both already exercised — SharePoint in restricted
*and* open mode). **Alternative for this slot:** if the engineering track is preferred over more doc
packs, pick up the **runtime pack-load SPI** (below) — the doc contract (ADR-0016) is fixed; the code
mechanism that *loads* a pack at runtime is not yet built.

### Later (backlog)
- Further **pack specifications** after KM — the **source-shaped** SAP, SharePoint, Email (pure
  connector-fidelity reuse; both SharePoint modes already exercised), then Document Intelligence /
  Reporting — reusing the Cycle-11 skeleton; each **inherits** a compliance-map row
  ([Governance §9](governance/00-governance-and-audit.md)) and the Finance §0-ledger discipline.
- **Runtime pack-load SPI** (open Q#6-adjacent): how a pack is *loaded* at runtime (the engineering
  form of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)); the doc contract is fixed,
  the code mechanism is not yet built.
- **Cycle 2c engineering track** (still open) — wire `WorkerRegistry`/`HandoffRouter` into the
  runtime, finish the test port + coverage gate, deeper governance hardening (see §6 Cycle 2c).
- Reconcile `platform/` architecture with the existing `core/` code (ADR-0002 implementation path).
- Resolve open **Q#3** (model hosting — in-boundary OSS vs. contractually-private managed, per tier)
  → feed the approved-model registry ([Governance §8](governance/00-governance-and-audit.md)) + the
  Deployment instance/model manifest ([Deployment §7](deployment/00-deployment-topology.md)); may warrant its own ADR.
- Resolve open **Q#6** (agent framework — extend `core/` planner/verifier vs. adopt a framework).

---

## 7. Consistency checklist (run before ending each cycle)

- [ ] New docs answer Why / How / Trade-offs / Alternatives / Future scalability.
- [ ] New cross-component decisions captured as an ADR and linked.
- [ ] No duplicated content; extended existing docs where possible.
- [ ] `platform/README.md` domain-map statuses updated.
- [ ] This file's §1, §3, §4, §6 updated.
