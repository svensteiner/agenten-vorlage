# Domain Pack #2 — HR (Human Resources)

> **The second data point.** One pack proves the *mechanism* exists (Finance, Cycle 11);
> a **second, structurally different** pack proves the mechanism is *reusable* — which is
> the founding bet itself. HR is the right second precisely because it stresses a
> **different corner** than Finance: **employee-self-scoped ACLs** (a subject may see
> *only their own* records — the hardest principal-derivation case), **`pii_class:health`**
> as special-category data (GDPR Art. 9), **GDPR right-to-erasure as the primary regime**
> (Finance leaned SOX), and **Workday / SAP-HCM + SharePoint + email** as mixed sources.
> If the [pack skeleton](../README.md) generalizes from n=1 to n=2 without a horizontal
> change, the bet is *reusable*, not just *possible*. It did — see §0.

- **Cycle:** 12 · **Status:** Seeded · **Contract:** [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md) (no new ADR — the pack contract already covers this)
- **Regimes declared:** GDPR (primary, incl. Art. 9 special-category), works-council / co-determination (sector), ISO 27001 / SOC 2, local labor-law statutory retention
- **Isolation tier (default):** Isolated ([Storage §5](../../storage/00-storage-architecture.md)) — special-category data + self-scoped exposure risk

---

## Why HR second (and why it is a *different* stress test than Finance)

Finance proved the mechanism against the hardest *authorization-object* source (SAP with no
document ACL). Repeating a near-identical pack would prove nothing new. HR earns its slot by
pushing on mechanisms Finance left *un-stressed*:

- **Self-scoped access is the degenerate corner of set-membership.** An employee's own
  personnel record grants to essentially *one* principal — the employee — plus a small HR
  admin set and a manager chain. This is the sharpest test of the
  [canonical principal model](../../permissions/00-authorization-model.md#4-resolving-the-subjects-effective-principals-query-time):
  does "may see only their own record" fit the *existing* `allow ∩ principals ≠ ∅` predicate,
  or does it force a new *owner-of* concept? (Answer: it fits — the owning subject's own CPI
  is already one of their effective principals, [Permissions §4.1](../../permissions/00-authorization-model.md#41-inputs). No horizontal change.)
- **Health data is special-category (GDPR Art. 9), not merely PII.** Occupational-health,
  sick-leave, disability, and benefits/medical records demand handling *stricter* than the
  ordinary `pii:true` floor — the first real exercise of a `pii_class:health` **tighten**
  delta ([Governance §4.1](../../governance/00-governance-and-audit.md), [Metadata §4.1](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions) which already names `pii_class:health` as the example).
- **GDPR erasure is the *primary* regime, in direct tension with statutory retention.**
  Finance treated GDPR as secondary to SOX; HR inverts it. Payroll and tax records carry a
  **statutory retention** obligation (a `legal_hold`-shaped floor) that must survive an
  employee's erasure request — the strongest test of the
  [`legal_hold > erasure > retention`](../../governance/00-governance-and-audit.md#53-legal-hold-overrides-erasure--retention) precedence.
- **The data subject is also a system user.** An employee filing a DSAR about *their own*
  data is both subject and caller. Finance never exercised this reflexive case.

If any of these forced a horizontal change, that would be the finding. **None did** — see §0.

---

## §0 — Horizontal-change ledger (the proof of the bet)

Every horizontal document this pack touched, and how:

| Horizontal surface | Change required by HR? | What HR did instead |
|--------------------|:----------------------:|---------------------|
| Permissions (canonical model, `map_acl`) | **None** | Self-scoped access = the existing `allow ∩ principals ≠ ∅` predicate where `allow` = `{owner-CPI, role:HR_*, manager chain}` and the subject's *own* CPI is already an effective principal ([§4.1](../../permissions/00-authorization-model.md#41-inputs)); computed "manager can see reports N levels down" that is *not* representable as principal set-membership rides the *existing* §9 quarantine / §10 OBO escape hatch — the same one Finance used for SAP field-level auth |
| Metadata (label schema, catalog, lineage) | **None** | **Registered** `pii_class:health`, `pii_class:employment`, `restricted:works_council` into the existing registry extension point ([§4.1](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)) — `pii_class:health` is already the schema's named example |
| Governance (label matrix, SLA, retention) | **None** | **Tightened** existing matrix rows for special-category data; **inherited** the GDPR compliance row; expressed statutory retention as an existing `legal_hold`-precedence rule |
| RAG (chunking, hybrid, verifier) | **None** | Supplied Workday/HCM + policy-document parsers behind the existing per-content-type seam; supplied an eval set incl. self-scope permission negatives |
| Storage / Workers / API / Deployment | **None** | Chose the *existing* Isolated tier; connector rides the *existing* staged DAG; reuses Finance's *existing* SAP connector fidelity work for SAP-HCM; API `pack:"hr"` is the *existing* optional additive hint |

**Net horizontal change: none. All additive.** The headline: the skeleton generalized from
n=1 (Finance) to n=2 (HR) **cleanly** — the second, structurally-different domain fits the
same six sections without touching a horizontal contract. The self-scoped-ACL case, the one
most likely to force an "owner-of" primitive, resolved to the *degenerate* case of the
predicate that already exists. Per [ADR-0016](../../architecture/adr/ADR-0016-domain-pack-contract.md),
if a future edit to this pack adds a "required" row, that edit needs a horizontal ADR.

---

## §1 — Sources & `map_acl` fidelity

HR sources and the **maximum `acl_confidence`** each connector must declare per item class
([Permissions §5.5](../../permissions/00-authorization-model.md#55-the-mapping-contract)).
Anything below `exact` is **denied on the shared retrieval path** and quarantined to the
Isolated tier ([Permissions §9](../../permissions/00-authorization-model.md#9-when-a-source-cant-be-faithfully-normalized-r1-mitigation)).
The novel case for HR is **self-scoped ownership**, expressed below as a normal principal set.

| Source | Item class | Principal mapping | Max `acl_confidence` | Notes |
|--------|-----------|-------------------|:--------------------:|-------|
| **Workday** (REST/RaaS) | Worker/personnel record | `allow = {user:<worker-CPI>, role:HR_ADMIN, role:HR_BP_<orgunit>, manager-chain-principals}` | `exact` **iff** ownership + the manager relationship are exposed as resolvable principals | Self-scope = a one-element owner set; the subject's own CPI is already an effective principal ([§4.1](../../permissions/00-authorization-model.md#41-inputs)) |
| **Workday** | Computed row-level rule (e.g. "manager sees reports ≤ N levels down", dynamic security group) | — | `approximate` → **deny + quarantine** (or native OBO §10) | Attribute-/computation-based auth not representable as static set-membership — the HR analogue of SAP field-level auth |
| **SAP HCM / SuccessFactors** (OData/RFC) | Infotype record (payroll, org, time) | `role:HR_*` + `orgunit:<code>` (personnel area/subarea) + owner CPI | `exact` if expressible as role + org-unit + owner set; else `approximate` | **Reuses Finance's SAP connector fidelity work** ([Finance §1](../finance/00-finance-pack.md)) verbatim — [§5.2](../../permissions/00-authorization-model.md#52-sap) |
| **SharePoint** (M365) | HR policy doc / personnel file (per-item ACL) | Entra objectId → CPI; broken inheritance respected; MIP label → `sensitivity` | `exact` when item-level perms fully read | HR policy library is broadly `internal`; personnel files carry restrictive item ACLs — [§5.1](../../permissions/00-authorization-model.md#51-sharepoint--onedrive-m365) |
| **Email / Exchange** | HR case correspondence, grievance threads | Mailbox owner + explicit delegates; per-message ACL | `exact` per message; thread never retro-grants | Grievance/health threads are highly restricted — [§5.3](../../permissions/00-authorization-model.md#53-email--exchange) |

**Conformance fixtures (the production gate).** The HR connector ships a fixture set for the
[permission-conformance suite](../../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate)
that must pass in CI **and** as the production canary before any HR source goes live:

1. **Self-scope positive + negative:** employee A retrieves A's own compensation record and
   **cannot** retrieve employee B's — the sharpest single-owner set-membership test.
2. **Manager chain:** a manager retrieves a direct report's record **iff** the manager
   relationship is exposed as a resolvable principal; a *computed* "two-levels-down" rule the
   connector marks `approximate` is **quarantined**, never served with a synthetic grant.
3. **Special-category masking:** a `pii_class:health` field (sick-leave reason, disability
   status) is **masked** in retrieved context unless the subject's grant explicitly permits
   the raw field ([RAG §6.4](../../rag/00-retrieval-pipeline.md)).
4. **Revocation freshness:** a terminated employee's access is removed **within the freshness
   SLA** ([Governance §3.1](../../governance/00-governance-and-audit.md#31-the-ratified-sla-table), Isolated ≤2 min for principals) via query-time principal precedence — the offboarding case HR exercises hardest.
5. **Cross-tenant:** no HR chunk of tenant A ever reaches tenant B (R4), inherited unchanged.

---

## §2 — Classification-registry values (the vocabulary HR registers)

HR **registers** these values into the tenant [classification registry](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
extension points — it does not invent new dimensions. An unregistered label is a
write-boundary schema violation → DLQ ([Workers §8.1](../../workers/00-ingestion-architecture.md)),
never silently stored.

| Dimension | Registered value | Applies to |
|-----------|------------------|-----------|
| `sensitivity` | `restricted:works_council` | Data under works-council / co-determination confidentiality (e.g. Betriebsrat-restricted matters) |
| `pii` | `pii_class:health` | Occupational-health, sick-leave reason, disability, benefits/medical — **special-category, GDPR Art. 9** |
| `pii` | `pii_class:employment` | Compensation, performance ratings, disciplinary records, national ID / tax ID |
| `legal_hold` | `matter:<id>` | Any HR record under a litigation, grievance, or investigation hold |

These slot into the existing lattice (`public < internal < confidential < restricted:*`), so
**most-restrictive-wins** composition is inherited unchanged. A sick-leave record naming a
diagnosis, tied to a named employee, under an active grievance resolves to
`restricted:works_council` (if applicable) + `pii_class:health` + `legal_hold:true` — the most
restrictive action of each dimension applies. `pii_class:health` is **not a new dimension** —
it is the exact extension point the [Metadata schema](../../metadata/00-catalog-and-lineage.md#41-the-label-dimensions)
already names as its example.

---

## §3 — Label→action *tighten* deltas

HR **tightens** the [platform label→action matrix](../../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen);
it never loosens a floor. Every delta below only *subtracts* capability.

| Label | Retrieval | Prompt / model | Egress | Delta vs. platform default |
|-------|-----------|----------------|--------|----------------------------|
| `pii_class:health` | Only to principals holding an explicit health-data grant; **masked by default** for everyone else, incl. line managers | **Isolated model pool only**; masked in prompt unless the grant permits the raw field | **Never** in any batch/analytics export; no external egress | Stricter than ordinary `pii:true`: adds model-pool restriction + a manager-visibility carve-out (special-category ≠ ordinary personnel data) |
| `pii_class:employment` | Masked in context unless the subject's grant permits the raw field | Masked in prompt by default | Excluded from batch/analytics export | Adds masking + batch-exclusion (same shape as Finance `pii_class:financial`) |
| `restricted:works_council` | Isolated tier only; only to co-determination-cleared principals | Isolated pool | Region-locked to residency class; no cross-border transfer | Adds residency lock + a clearance gate (mirrors Finance `restricted:supervisory`) |
| `legal_hold:true` (`matter:*`) | Unchanged (visibility unaffected) | Unchanged | **Never auto-deleted** — retention override ([Governance §5.3](../../governance/00-governance-and-audit.md#53-legal-hold-overrides-erasure--retention)); also carries **statutory retention** (payroll/tax) as an inherited floor | Inherited, not tightened |

**Invariant preserved:** a label can only *subtract* capability
([Permissions §7](../../permissions/00-authorization-model.md#7-sensitivity-labels-are-enforced-in-addition-to-acls)).
The manager-visibility carve-out for `pii_class:health` is a *tighten* (managers who could see
ordinary personnel data are **denied** the health field), never a grant.

---

## §4 — Compliance-map row(s) (declare + inherit)

HR **inherits** the GDPR and ISO rows of the
[Governance control map](../../governance/00-governance-and-audit.md#9-g7--compliance-mapping-control--regime-per-domain);
it does not re-derive controls. GDPR is HR's **primary** regime (Finance's was SOX). The
evidence for each cell is an **existing** audit-event type
([Governance §6.3](../../governance/00-governance-and-audit.md#63-audit-as-sla--compliance-evidence)).

| Regime | Inherited controls (already built) | HR-specific evidence binding |
|--------|-----------------------------------|------------------------------|
| **GDPR (primary, incl. Art. 9)** | Right-to-erasure + DSAR; PII masking; residency; private-by-default; `legal_hold > erasure > retention` | A self-DSAR (employee about their own data) runs the *existing* DSAR job ([API privacy group](../../api/00-api-surface.md)); erasure completeness proven by [lineage traversal](../../metadata/00-catalog-and-lineage.md#52-erasure--legal-hold-tombstone-m4); statutory payroll retention blocks premature deletion via `legal_hold` precedence; `pii_class:health` masking proven per query |
| **Works-council / co-determination (sector)** | Isolated tier + `restricted:*` clearance gate + label-based routing | `restricted:works_council` routes only to the Isolated pool and cleared principals (§3); co-determined analytics categories are batch-excluded |
| **ISO 27001 / SOC 2** | Encryption + BYOK; tenant isolation; change-managed policy store | Isolated tier + per-tenant DEK for the HR tenant |
| **Labor-law statutory retention** | Retention schedule + `legal_hold`-precedence override ([Governance §5](../../governance/00-governance-and-audit.md)) | Payroll/tax records carry a statutory-retention floor expressed as an inherited retention rule — no new mechanism |

**No new control was invented.** HR's compliance posture is a *selection and binding* of
controls the platform already operates — including the reflexive self-DSAR, which is just the
existing DSAR workflow with the subject and caller being the same identity.

---

## §5 — Retrieval / answer eval set

The HR pack supplies (a) the **parsers** that make its content retrievable and (b) the **eval
corpus** that gates any model change through the
[eval-before-promotion gate](../../governance/00-governance-and-audit.md#8-g6--model-governance).

**Parsers (behind the existing per-content-type seam — [RAG open sub-Q](../../rag/00-retrieval-pipeline.md)):**
- **Workday / SAP-HCM records** — serialized to a stable, header-aware row form (one worker
  record / infotype per chunk); **reuses the Finance SAP-table serializer**. The mixed-ACL
  invariant means a chunk never spans two workers with different owner sets.
- **HR policy documents** (SharePoint) — heading-structured chunking; broadly `internal`, high
  recall (the HR handbook is meant to be found), so policy answers do not over-refuse.
- **Case / grievance email** — per-message chunking (the ACL-carrying Item), health and
  matter labels carried per message.

**Eval set (grounding · refusal · pack task accuracy · self-scope negatives):**

| Eval class | What it proves | Pass bar |
|-----------|----------------|----------|
| **Self-scope permission negatives** | Employee A cannot obtain employee B's compensation/health data via any cleverly-worded prompt | 0 leaks (this is a permission test, not an accuracy test) |
| **Health-field masking** | A `pii_class:health` field never appears unmasked to a principal without the explicit health grant — **including the subject's own line manager** | 0 unmasked exposures on the held-out set |
| **Policy grounding** | An HR-policy answer ("how many carry-over vacation days?") traces to a cited handbook chunk; no invented rule | 100% policy claims cited or the answer refuses |
| **Refuse-over-guess** | A question about a record the caller can't access → a `200` "no accessible information" ([API §5.1](../../api/00-api-surface.md)), never a fabricated fact | 0 fabrications on the held-out no-access set |
| **Erasure/retention correctness** | An erased employee's content is unretrievable **while** statutory-retained payroll survives under `legal_hold` | 0 retrieval of erased content; 0 premature deletion of held records |

A model that regresses on **self-scope negatives**, **health-field masking**, or
**erasure/retention correctness** cannot be promoted for the HR tenant — the same gate shape
as the Finance eval set, retargeted to HR's failure modes.

---

## §6 — Optional additive API `pack` hint

HR callers **may** pass `"pack": "hr"` on
[`POST /v1/answers`](../../api/00-api-surface.md#51-synchronous-ask) as a routing/eval hint
(e.g. prefer the HR eval-tuned model, bias retrieval toward HR sources). It is strictly
additive:

- **Identity still governs.** The hint never widens access — a caller who passes `pack:"hr"`
  but lacks HR principals sees nothing, and a caller who passes `pack:"hr"` still cannot see
  another employee's self-scoped record
  ([API §4](../../api/00-api-surface.md#4-authn--authz-at-the-edge)). The hint is not an
  authorization input.
- **Omitting it is valid.** The platform infers pack context from the accessible sources; the
  hint only optimizes routing. Absence never changes correctness.
- **Not a version event.** Adding `pack:"hr"` is [additive versioning](../../api/00-api-surface.md#11-versioning--deprecation-policy-a7),
  not a breaking change — clients that ignore it keep working.

---

## Trade-offs

- **Self-scope masking of health data from line managers vs. managerial convenience.** HR
  masks `pii_class:health` even from a subordinate's own manager by default. This is stricter
  than many HRIS defaults, but Art. 9 special-category data is exactly the case where "the
  manager can already see the personnel file" must **not** silently extend to medical facts. A
  manager who legitimately needs the raw field gets an explicit grant — a decision, not a
  default.
- **Quarantine over best-effort on computed manager-hierarchy rules.** Refusing to fake a
  computed "N-levels-down" visibility rule with static grants means some hierarchy-derived
  access is **unavailable on the shared path** rather than approximately available — the same
  R1 trade Finance made for SAP field security. Native OBO (§10) is the escape hatch where the
  latency is acceptable.
- **GDPR erasure vs. statutory retention.** The two obligations genuinely conflict for payroll;
  the platform resolves it deterministically (`legal_hold > erasure`) rather than case-by-case.
  Trade-off: an employee's erasure request is *partially* honored (identity/HR content erased,
  statutorily-retained payroll held) — the honest, defensible outcome, and it is **provable**
  by lineage traversal.
- **Isolated tier by default vs. cost.** HR defaults to Isolated (special-category exposure +
  self-scope blast radius). More expensive than Shared, but the honest default; an HR sub-tenant
  handling only broadly-`internal` policy content could graduate *down* — a placement decision,
  not a redesign.

## Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Add an "owner-of" / self-scope primitive to the canonical model** | Rejected: self-scope is the *degenerate* case of the existing set-membership predicate (a one-element `allow` set = the owner's CPI). Adding a primitive would be a horizontal change the bet forbids — and an unnecessary one. |
| **Model computed manager-hierarchy visibility as synthetic grants** | Rejected: fabricating a static ACL from a dynamic rule is the R1 leak the confidence gate exists to prevent. Quarantine or native OBO is the honest answer (same as Finance/SAP). |
| **Treat `pii_class:health` as ordinary `pii:true`** | Rejected: special-category data (Art. 9) warrants a *tighter* action than the ordinary PII floor; that tightening is exactly what §3 is for. |
| **A HR-specific retrieval or DSAR pipeline** | Rejected: would be a horizontal change. HR rides the hybrid permission-filtered pipeline and the existing DSAR job unchanged; only parsers + eval + registered labels are pack-local. |
| **Bespoke HR compliance write-up** | Rejected ([Governance §11](../../governance/00-governance-and-audit.md#11-alternatives-considered)): HR inherits the GDPR row + binds evidence; re-deriving controls is the anti-pattern. |

## Future scalability

- **Legal and Audit packs** remain fill-in-the-blank against the [skeleton](../README.md);
  Legal reuses HR's `matter:<id>`/grievance-hold shape, Audit reuses Finance's SOX row.
- **A new HR source** (e.g. a benefits provider, an ATS/recruiting system) = a new §1 row +
  fixtures; no pipeline change. Recruiting adds candidate-consent handling as another §3 tighten
  delta, not a mechanism.
- **A new special-category rule** (e.g. `pii_class:biometric` for time-clock biometrics) = a new
  registered §2 value + a §3 tighten delta binding existing masking/routing controls.
- **A tighter works-council SLA or a new co-determination regime** = a ratified number change /
  a new §4 compliance row binding existing controls — no redesign.
- **An HR-tuned model** enters through the existing eval gate (§5) and is routed by the existing
  label→trust policy — a config change, not a code change.

## Related
- [Pack skeleton & the falsifiability rule](../README.md) · [Finance reference pack](../finance/00-finance-pack.md)
- [ADR-0016 — Domain pack contract](../../architecture/adr/ADR-0016-domain-pack-contract.md)
- [Permissions §4 (effective principals), §5 (per-source mapping), §9 (quarantine), §10 (OBO), §11 (conformance)](../../permissions/00-authorization-model.md)
- [Metadata §4 (classification registry — `pii_class:health`)](../../metadata/00-catalog-and-lineage.md)
- [Governance §4 (label matrix), §5 (erasure/retention/legal-hold), §9 (compliance map)](../../governance/00-governance-and-audit.md)
- [RAG (verifier, masking, parsers)](../../rag/00-retrieval-pipeline.md) · [API §4 (authz), §5, §11](../../api/00-api-surface.md)
