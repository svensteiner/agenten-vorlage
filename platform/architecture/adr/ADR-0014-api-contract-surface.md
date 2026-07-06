# ADR-0014 — API contract surface: token-bound identity, dual sync/streaming answer, job-based heavy work, URL-major versioning

- **Status:** Accepted (Cycle 9)
- **Deciders:** Platform Architecture, Enterprise Architecture, Security & Governance
- **Relates to:** [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (query-time
  enforcement — the reason identity must ride the token, not a parameter),
  [ADR-0003](ADR-0003-model-gateway-indirection.md) (the Model Gateway the answer
  endpoint fronts), [ADR-0007](ADR-0007-client-configuration-surface.md) (the local
  settings UI this admin API is the multi-tenant successor to),
  [ADR-0008](ADR-0008-canonical-principal-acl-model.md) (effective-principal resolution
  and OBO the edge exposes), [ADR-0012](ADR-0012-governance-audit-and-cost.md) (the
  policy/budget/DSAR/audit surfaces the admin & privacy groups expose),
  [ADR-0013](ADR-0013-canonical-metadata-lineage-schema.md) (the canonical identifiers
  citations and catalog/lineage endpoints return),
  [API deep dive](../../api/00-api-surface.md) (full detail)

## Context

Seven prior cycles built planes and policy stores whose outward-facing needs were each
deferred to "the API cycle": the query/answer contract ([RAG](../../rag/00-retrieval-pipeline.md)),
the admin/policy surface, DSAR/erasure/audit-export ([Governance](../../governance/00-governance-and-audit.md)),
and catalog-browse/lineage/DSAR-status ([Metadata](../../metadata/00-catalog-and-lineage.md)).
`api/` was the **last major un-seeded platform surface** ([NEXT_STEPS §5](../../NEXT_STEPS.md)).

Several contract-shape questions are genuinely **cross-component** — they constrain more
than one plane and, if decided ad hoc per endpoint, would let the platform's hardest
guarantee (permission-faithful retrieval) be re-argued at the edge. The forcing
questions: **Where does the end-user identity live on the wire? Is an answer synchronous
or streamed — and does streaming get to skip the verifier? Are DSAR/erasure/export held
connections or jobs? How does the surface version so continuous pack growth never breaks
a caller?**

## Decision

1. **Identity travels in the token, never in the URL or body.** The gateway derives
   `{tenant, subject, effective principals, delegation}` from an IdP-issued bearer token
   ([ADR-0008](ADR-0008-canonical-principal-acl-model.md)); tenancy is **not** a URL path
   segment. A client cannot *assert* who it is as a request field — impersonation is not
   representable. Delegation/OBO uses **token exchange** (actor + subject), and retrieval
   always runs under the **subject's** principals; the actor never widens access. A
   **client-credentials** token has no end-user principals, so a service account
   structurally **cannot** read user-restricted knowledge — only administer.
2. **One response envelope, typed errors, everywhere.** Every endpoint returns
   `{ok, data, error, meta}`; `meta.request_id` **equals** the audit correlation id.
   Error `type` is a closed enum; messages are leak-free and a hidden resource returns
   `not_found`, never a message that confirms its existence.
3. **Two answer modes, one verifier gate.** `POST /v1/answers` (sync) and
   `/v1/answers:stream` (SSE) share the same contract; the streamed `final` event is
   emitted **only after the verifier passes** ([RAG §7](../../rag/00-retrieval-pipeline.md)).
   Streaming is a latency-perception optimization, **never** a grounding bypass.
   "No permitted data" is a `200` success (`grounding:"no_accessible_information"`), not
   an error — so absence of access can't leak as an error and can't be faked as one.
4. **Heavy work is a job, not a held connection.** DSAR, erasure, audit-export,
   connector backfill, and re-embed return a `job_id` + status URL and share **one**
   async pattern (`GET /v1/jobs/{id}`). Only the query answer may stream. Erasure/DSAR
   status returns the [Metadata lineage-tombstone](../../metadata/00-catalog-and-lineage.md)
   evidence — completeness is **proven by a traversal**, not asserted.
5. **The admin API can only tighten.** The Governance & Admin group is a thin,
   self-auditing CRUD over the [policy store](../../governance/00-governance-and-audit.md);
   a write that would loosen a platform floor (widen a label capability, disable the ACL
   filter, throttle a P0 revocation, raise a budget above a contracted ceiling, pin an
   un-evaluated model) is rejected `422 policy_blocked`. Every write is an audited
   governance event.
6. **Filter parity on all reads.** Catalog-browse/lineage apply the **identical**
   permission predicate as retrieval ([RAG §4.2](../../rag/00-retrieval-pipeline.md));
   there is no unfiltered "list mode" that could leak existence or titles.
7. **URL-major versioning, additive-by-default, deprecation windows.** Major version in
   the path (`/v1/…`); additive changes (new endpoints/optional fields) are unversioned
   and clients **must ignore unknown fields**; breaking changes get a new major with
   `Deprecation`/`Sunset` signaling and per-version usage reporting. **A new domain pack
   is not a version event** — the "pack, not redesign" bet applied to the wire format.

Full endpoint list, envelope schema, and auth flows: [API deep dive](../../api/00-api-surface.md).

## Consequences

- (+) The permission-faithful guarantee ([ADR-0004](ADR-0004-permission-faithful-retrieval.md))
  is enforced **once, at a small number of audited choke points**, not re-argued per
  endpoint; cross-tenant/impersonation access is unrepresentable on the wire.
- (+) Uniform envelope + `request_id`=audit-id makes **every client interaction
  traceable** and every error branchable without string parsing.
- (+) Streaming improves perceived latency **without** opening a grounding hole; the
  verifier gate is a contract invariant, not an implementation detail.
- (+) One job pattern serves five heavy endpoints — clients learn it once; erasure
  becomes **provable to a regulator** via the status evidence.
- (+) Tenant admins get self-service policy/budget/model control that **cannot** regress
  safety; the local [ADR-0007](ADR-0007-client-configuration-surface.md) panel graduates
  cleanly to a multi-tenant, audited API.
- (+) Continuous pack growth never breaks callers (additive rule) — the edge inherits the
  platform's core scalability bet.
- (−) Tenancy-in-token hurts URL readability and forces admin tooling to decode tokens;
  accepted for the impersonation-proof property.
- (−) One envelope wraps even trivial reads; accepted for uniform client + audit handling.
- (−) Async-by-default pushes polling/subscription complexity to clients; accepted
  because held connections don't survive erasure/export durations.
- (−) REST-first defers a GraphQL-style flexible read surface; accepted because arbitrary
  client-shaped queries fight per-field ACL/label redaction.

## Alternatives

- **GraphQL as the primary surface** — rejected: resolver-shaped queries make the
  permission filter and per-field label redaction an ACL side-channel risk, and cost
  attribution per field is hard. Possible later as a read-only, filter-wrapped catalog view.
- **Tenancy in the URL path** (`/t/{tenant}/…`) — rejected: makes tenant a client-supplied
  assertion; token-derived tenant is the only trustworthy source.
- **gRPC-first external API** — rejected as the edge default (browser/agent reach, human-
  debuggable audit favor HTTP+JSON); remains available for internal plane-to-plane traffic.
- **Synchronous DSAR/erasure/export** — rejected: cross-store propagation + completeness
  proofs exceed any safe request timeout; jobs make progress and evidence first-class.
- **Streaming that completes before verification** — rejected outright: it would let an
  ungrounded/policy-violating answer reach the user; the verifier gate is non-negotiable.
- **Header-only versioning** — rejected as primary (less visible in logs/audit); URL-major
  with header-based deprecation *signaling* instead.
- **Admin API writing policy straight to stores** — rejected: bypasses the eval gate and
  self-audit; it must go through the policy store's validated mutations.

## Revisit when

- **A flexible read/analytics surface is needed** → add a read-only, permission-filter-
  wrapped GraphQL or batch-query endpoint reusing the same predicate and job pattern.
- **Push delivery is required** → add webhooks for job completion (additive to §10.1);
  polling stays as the floor.
- **Data residency / per-region endpoints** → same contract behind a residency-routing
  gateway; tenancy-in-token keeps region a [Deployment](../../deployment/) concern, not a
  contract change.
- **Finer authorization scopes** beyond `query/admin/dpo` → additive scope claims;
  existing tokens keep working.
- **A breaking contract change becomes unavoidable** → cut `/v2/` with a deprecation
  window and per-version usage reporting (§11); never mutate `/v1/` semantics in place.
