# ADR-0009 — Hybrid permission-filtered retrieval with structure-aware chunking

- **Status:** Accepted (Cycle 4)
- **Deciders:** RAG / Query-Plane Architecture, Enterprise Architecture, Security Architecture
- **Relates to:** [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (filter during
  retrieval — the invariant this pipeline obeys), [ADR-0008](ADR-0008-canonical-principal-acl-model.md)
  (canonical ACL — the predicate this pipeline pushes into search),
  [ADR-0003](ADR-0003-model-gateway-indirection.md) (embeddings/reranker/generator mediated
  by the gateway), [RAG deep dive](../../rag/00-retrieval-pipeline.md) (full detail)

## Context

The permission model is defined ([ADR-0008](ADR-0008-canonical-principal-acl-model.md))
and committed to *filtering during retrieval* ([ADR-0004](ADR-0004-permission-faithful-retrieval.md)).
What remained open ([NEXT_STEPS §3](../../NEXT_STEPS.md) open questions #4, and provisional
#1): **how** content is chunked and embedded, **how** it is searched, and **how** an answer
is grounded and verified — without weakening the ACL guarantee. Regulated domains query
both by concept ("the indemnity clause") and by exact token (invoice / statute / SAP
document numbers, names); one retrieval mode cannot serve both, and a naive chunker
corrupts tables, clauses, and — most dangerously — mixes email-message ACLs into one
unfilterable chunk. This decision fixes the query-plane payoff so downstream cycles
(Storage, Workers, Governance) build against one contract.

## Decision

Adopt a **hybrid, permission-filtered, reranked, verified** retrieval pipeline:

1. **Structure-aware chunking.** Cut on semantic/structural boundaries (heading, clause,
   table row-group, per email **message**), token budget as a bound not the cut. A chunk
   **never spans two source items with different ACLs** — a permission-safety invariant.
   Each chunk carries stable `resource_id` + `source_item_version` + the canonical ACL.
2. **Universal embedding space + per-domain normalization** (not per-domain models).
   One general-purpose in-boundary embedding model; domain shape (tables, clauses, email)
   handled in pre-embed text normalization. `embed_model`+`embed_dim` recorded per vector;
   upgrades are versioned re-embed migrations, never in-place swaps.
3. **Hybrid search = dense (vector) + sparse (BM25/full-text), fused with RRF.** The
   compiled permission predicate (tenant → `acl_confidence='exact'` → allow-overlap →
   deny-wins → label policy) is pushed into **both** engines' metadata filters, pre-ranking.
4. **Cross-encoder reranking** on the permitted top-K, then MMR diversity; degradable to
   fusion-only as a logged per-tier latency dial.
5. **Grounded generation + verifier contract.** Retrieved text is untrusted data inside a
   data boundary (R2 defense); the verifier enforces grounding, citation validity,
   no-context honesty, guardrails, and label compliance — **refuse over guess**.
6. **Provisional vector store (open Q#1):** pgvector for small tenants (co-located
   vectors + ACL arrays + full-text + metadata, native set-overlap), graduating to a
   dedicated engine (Qdrant/Elasticsearch) for scale. **[Storage](../../storage/) owns
   the final selection**; this ADR only records the requirements and the lean.

Full detail: [RAG deep dive](../../rag/00-retrieval-pipeline.md).

## Consequences

- (+) Exact-token **and** semantic recall in one path; cross-encoder gives the precision
  regulated answers need.
- (+) The ACL guarantee stays a **single index predicate** applied to both engines — safety
  costs a `WHERE`, not N source calls (honors [ADR-0004](ADR-0004-permission-faithful-retrieval.md)/[ADR-0008](ADR-0008-canonical-principal-acl-model.md)).
- (+) One vector space keeps cross-domain queries and one migration pipeline; new domain =
  parser + normalization rule, not a pipeline change.
- (+) Verifier + data-boundary give a concrete R2 (prompt-injection) defense-in-depth.
- (−) More engines + a reranker + a verifier = higher latency and an extra model call;
  mitigated by rerank-top-K-only, caching, and a degradable latency tier.
- (−) Structure-aware chunking needs a per-content-type parser (Workers cost) vs. a trivial
  splitter — accepted to protect table/clause/thread integrity and the mixed-ACL invariant.
- (−) Universal embeddings slightly underperform a per-domain-tuned model — accepted;
  recoverable later via an opt-in named space without redesign.

## Alternatives

- **Pure vector or pure keyword** — rejected: each misses half the query population
  (identifiers vs. paraphrase).
- **No reranker** — rejected as default (coarse precision); retained as a latency degrade.
- **Fixed-size chunks everywhere** — rejected: corrupts tables/clauses and mixes email ACLs.
- **Per-domain embedding models by default** — rejected: N incompatible spaces, N
  migrations, no cross-domain query; deferred as an opt-in named space.
- **No verifier (trust model citations)** — rejected: ungrounded/injected answers would
  reach users in regulated domains.

## Revisit when

- A tenant/domain proves the universal embedding space materially under-serves it → grant
  it a named embedding space (already an anticipated extension, no predicate change).
- [Storage](../../storage/) (Cycle 5) selects the production vector store → supersede the
  provisional lean in §6 with the final choice (this ADR stays; Storage records the pick).
- Reranking latency becomes the dominant SLA breach at scale → revisit rerank model /
  distillation / ANN-side reranking.
