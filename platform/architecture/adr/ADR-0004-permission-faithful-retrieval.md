# ADR-0004 — Enforce end-user permissions at query time

- **Status:** Accepted (Cycle 1)
- **Deciders:** Enterprise Architecture, Security Architecture
- **Supersedes:** —

## Context

Enterprise sources (SharePoint, SAP, file shares, email) have rich, per-item access
control. A naive RAG system indexes everything with a service account and answers from
the full corpus — leaking restricted content to any user via answers, snippets, or
citations. For Finance/HR/Legal/Audit this is disqualifying.

## Decision

The platform is **permission-faithful**: an answer may only be grounded on content the
**requesting end user** is authorized to see in the source system. Concretely:

1. **Capture ACLs at ingestion.** Each chunk stores the source's authorization data
   (principals, groups, sensitivity labels) as retrievable metadata.
2. **Resolve the user's effective permissions at query time** from the IdP (group/role
   claims) plus source-system entitlements, cached with a short TTL.
3. **Filter during retrieval**, not after. The vector/keyword query is constrained by
   the user's permitted principals so disallowed chunks are never ranked, snippetted,
   or sent to the model.
4. **Fail closed.** If permissions can't be resolved or a chunk's ACL is unknown, it is
   excluded. Ambiguity → deny.
5. **Re-verify freshness.** Because source ACLs change, query-time checks take
   precedence over ingestion-time snapshots; stale-permission windows are minimized by
   short cache TTLs and change-driven re-sync.

## Consequences

- (+) The platform can serve regulated, sensitive domains safely.
- (+) Trust: users only ever see what they're entitled to.
- (−) Retrieval must join against permission metadata → added latency and complexity.
- (−) Requires every connector to faithfully extract and normalize source ACLs
  (a hard, per-source problem — see [Permissions](../../permissions/)).
- (−) A permission-model mismatch (source semantics vs. platform model) is a real
  risk; mitigated by a normalized principal model and per-connector conformance tests.

## Alternatives

- **Post-filter after retrieval** — rejected: restricted content still enters ranking
  and can leak via scores/snippets; larger attack surface.
- **Per-user indexes** — rejected as default: storage-explosive and slow to update;
  reserved as an option for very-high-sensitivity tenants.
- **Trust the model to withhold** — rejected: models are not an access-control boundary.

## Revisit when

A source system's permission model cannot be faithfully normalized; that domain may
require per-user indexing or a stricter isolation tier rather than shared retrieval.
