# RAG (Retrieval-Augmented Generation)

> Status: **Seeded** · Owner: RAG / Query-Plane Architecture

The query-plane payoff: turn a user question plus the **already-permitted** corpus into a
**grounded, cited, verified** answer. This folder owns chunking, embeddings, hybrid
(vector + keyword) search, reranking, context assembly, grounding/citation, and the
verifier contract. It **consumes** the permission filter from
[permissions/](../permissions/00-authorization-model.md) — it does not re-specify
authorization.

## Documents

1. [00-retrieval-pipeline.md](00-retrieval-pipeline.md) — structure-aware chunking (with
   the mixed-ACL invariant), universal embedding space + per-domain normalization, hybrid
   search with the permission predicate pushed into both engines, cross-encoder reranking,
   context assembly + prompt-injection (R2) defense, the verifier contract
   (grounding / citation / no-context honesty / guardrails / label compliance), latency
   budget, and the provisional vector-store position (open Q#1).

## Decisions

- [ADR-0009](../architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md) — hybrid
  permission-filtered retrieval + structure-aware chunking (this folder's decision).
- Obeys [ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md) (filter
  during retrieval) and pushes the [ADR-0008](../architecture/adr/ADR-0008-canonical-principal-acl-model.md)
  predicate into search.

Follows the documentation contract (Why / How / Trade-offs / Alternatives / Future
scalability). Downstream folders ([storage/](../storage/) — vector store selection,
[workers/](../workers/) — chunk parsers + embedding jobs, [governance/](../governance/) —
audit trail) consume this pipeline — link here rather than duplicating.
