# Permissions

> Status: **Seeded** · Owner: Security & Data Architecture

The platform's hardest correctness guarantee: a user is answered **only** from content
they may see in the source system, at query time. This folder owns the canonical
authorization model, per-source ACL mapping, query-time enforcement, freshness, and the
conformance test that gates any connector from serving production retrieval.

## Documents

1. [00-authorization-model.md](00-authorization-model.md) — canonical principal/ACL
   model (four nouns), the single decision predicate, effective-principal resolution
   (identity graph), per-source mapping (SharePoint / SAP / Email / file share),
   filter-during-retrieval, sensitivity labels, freshness (R3), unmappable-source
   doctrine (R1), delegated access, and the permission-conformance test suite.

## Decisions

- [ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md) — enforce
  end-user permissions at query time (the *what*).
- [ADR-0008](../architecture/adr/ADR-0008-canonical-principal-acl-model.md) — normalize
  every source ACL into one canonical model (the *how*).

Follows the documentation contract (Why / How / Trade-offs / Alternatives / Future
scalability). Downstream folders ([rag/](../rag/), [storage/](../storage/),
[workers/](../workers/), [governance/](../governance/)) consume this model — link here
rather than duplicating.
