# ADR-0008 — Normalize every source ACL into one canonical principal model

- **Status:** Accepted (Cycle 3)
- **Deciders:** Data Architecture, Security Architecture, Enterprise Architecture
- **Relates to:** [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (the *what*:
  enforce end-user permissions at query time), [Security §3–§5](../../security/00-security-architecture.md),
  [Permissions deep dive](../../permissions/00-authorization-model.md) (the *how*)

## Context

[ADR-0004](ADR-0004-permission-faithful-retrieval.md) committed the platform to
answering a user only from content they may see in the source — enforced by
**filtering during retrieval**. That decision left the mechanism open: *against what
representation of permissions do we filter?*

The candidate sources (SharePoint, SAP, Exchange, file shares) have mutually
incompatible authorization models — item ACLs, role/authorization objects, mailbox
ownership, NTFS allow/deny ACEs. Filtering a vector query during retrieval is only
possible if the permission data lives **beside the chunk**, in **one** shape the store
can filter on. So we must choose: keep permissions native and enforce per-source at
query time, or normalize into a single canonical model at ingestion.

This is the platform's highest-severity correctness decision — it owns risks R1
(mismatch → leak), R3 (staleness), and R4 (cross-tenant leak).

## Decision

Normalize every source's access control into **one canonical model** and enforce
against it:

1. **Four nouns** — Subject, Principal, Grant, Resource. Every source principal becomes
   a **Canonical Principal Identifier** `tenant:source:type:stable-id`, keyed on the
   source's **stable, non-reusable** id (Entra objectId, AD SID, SAP role) — never a
   display name or email.
2. **Per-chunk ACL** — each Resource stores `{allow[], deny[], labels, acl_confidence,
   source_item_version}`. Enforcement is one predicate: tenant match → confidence must
   be `exact` → deny-wins → require an allow.
3. **Effective principals resolved at query time** from IdP claims + a platform
   **identity graph** (authoritative nested-group expansion + explicit, audited
   cross-source identity links), cached with a short, revocable TTL.
4. **Confidence-gated fail-closed** — a source that cannot be mapped to `exact` is
   `approximate`/`unknown` and is **denied on the shared retrieval path**, then
   quarantined to a stricter isolation tier or served via native query-time delegation.
5. **Conformance test as the production gate** — no connector serves production
   retrieval until it passes the permission-conformance suite (positive, negative,
   deny-precedence, nesting, broken inheritance, revocation/re-share freshness,
   ambiguity-denies, cross-tenant, label gate).

Full detail lives in the [Permissions deep dive](../../permissions/00-authorization-model.md).

## Consequences

- (+) Enables filter-during-retrieval (ADR-0004) with **one** store-level predicate,
  no live source call on the hot path — safe *and* fast.
- (+) New source = new connector + passing conformance suite; the decision predicate and
  storage schema never change (the "new domain = pack" bet applied to authz).
- (+) Cross-tenant leakage (R4) is structurally impossible: CPIs are tenant-namespaced
  and tenant match is the first, unconditional check.
- (−) Every connector must faithfully lower its source model and **prove** it via the
  conformance suite — real, ongoing per-source engineering cost.
- (−) Sources with inexpressible semantics lose shared-path recall (denied/quarantined)
  until represented exactly — accepted; a leaked answer costs more than a missing one.
- (−) Query-time principal resolution + short TTLs add latency and a freshness pipeline
  (identity graph, change-driven re-sync) — accepted as the price of R3 mitigation.

## Alternatives

- **Native per-source authorization at query time (no normalization)** — rejected as
  the default: N live source calls per query, cannot filter-during-retrieval, couples
  query availability to every source. Retained as the escape hatch for unmappable,
  highest-sensitivity classes.
- **Match identities across sources by email/name** — rejected: reused/reassigned
  identifiers silently transfer access. Links are explicit and audited.
- **Allow-overrides-deny precedence** — rejected: a broad allow would re-open a targeted
  exclusion; deny must win.
- **Trust the IdP token's group claims as complete** — rejected: token group lists are
  truncated; the identity graph is authoritative.

## Revisit when

- A strategically important source (e.g. a core SAP module) cannot reach `exact`
  confidence at acceptable cost — may justify investing in native delegation as a
  first-class path rather than an escape hatch.
- A domain requires genuine attribute-based access control (ABAC) that cannot be modeled
  as principals or label-policy — may extend the four-noun model with an attribute
  dimension.
