# Vision & Principles

> Status: **Foundational** · Owner: Enterprise Architecture · Cycle: 1

## 1. Vision

Build a **reusable private AI platform** that becomes the foundation for every future
AI Studio solution. A new domain solution — Finance, Audit, HR, Legal, Knowledge
Management, SAP, SharePoint, Email, Document Intelligence, Reporting — should be
delivered by **configuration and content packs, not by re-architecting the platform.**

"Private" is a hard requirement, not a feature: customer data, prompts, embeddings,
and model interactions must remain inside a controlled trust boundary (customer VPC,
sovereign cloud, or on-premise) with no uncontrolled egress to third-party services.

### One-sentence definition

> A multi-tenant, permission-aware Retrieval-Augmented Generation platform with
> pluggable connectors, governed model access, and a domain-agnostic core.

## 2. Why this matters (the problem)

Today each AI initiative tends to be rebuilt end-to-end: its own ingestion, its own
vector store, its own auth wiring, its own prompt plumbing, its own audit story. This
is slow, inconsistent, and hard to secure. The consequences:

- **Duplicated security surface** — every project re-implements authz and secrets,
  multiplying the chance of a leak.
- **No shared governance** — no consistent audit trail, cost control, or model policy.
- **Slow time-to-value** — 80% of each project is undifferentiated plumbing.

The platform absorbs that undifferentiated 80% once, correctly, so domain teams spend
their time on the 20% that is actually domain-specific.

## 3. Target domains (must be supportable without redesign)

| Domain | Primary sources | Dominant access pattern |
|--------|-----------------|-------------------------|
| Finance | SAP, ledgers, Excel, reporting DBs | Numeric Q&A, reconciliation, variance |
| Audit | SharePoint, document stores, email | Evidence retrieval, traceability |
| HR | HRIS, policies, contracts | Policy Q&A, highly sensitive PII |
| Legal | Contracts, matter files, email | Clause search, obligation extraction |
| Knowledge Mgmt | Wiki, SharePoint, tickets | Semantic search, summarization |
| SAP | OData/RFC/BAPI, tables | Structured data + text hybrid |
| SharePoint | Sites, libraries, lists | ACL-aware document retrieval |
| Email | Exchange/Graph, archives | Thread summarization, discovery |
| Document Intelligence | PDFs, scans, forms | OCR + extraction + classification |
| Reporting | BI models, warehouses | Natural-language-to-query, narratives |

The common shape across all of them: **connect a source → ingest & classify →
retrieve under the caller's permissions → reason with a governed model → return an
audited, cited answer.** That shape is the platform.

## 4. Design principles (non-negotiable)

1. **Private by default.** No customer data leaves the trust boundary without an
   explicit, logged, policy-approved egress. Models run in-boundary or via a
   contractually-private endpoint. See [Security](../security/00-security-architecture.md).
2. **Permission-faithful retrieval.** The model may only ground its answer on content
   the *end user* is allowed to see. Source-system ACLs are enforced at query time,
   never bypassed by a service account. This is the platform's hardest and most
   important guarantee.
3. **Domain-agnostic core.** The core contains no domain logic. Domains are delivered
   as packs (connectors, prompts, metadata schemas, policies). Inherited from the
   template's core/project split — [ADR-0002](adr/ADR-0002-reuse-existing-template-core.md).
4. **Multi-tenant isolation.** Tenants never share retrievable data, embeddings, or
   caches. Isolation is enforced by construction, not by filtering discipline.
5. **Everything is auditable.** Every retrieval, model call, and answer is traceable:
   who asked, what was retrieved, which model, what policy applied, what was returned.
6. **Model-pluggable.** No hard dependency on a single model vendor. Model access is
   mediated by a gateway so models can be swapped, routed, and governed.
7. **Fail closed.** On any ambiguity in permission, classification, or policy, deny
   and escalate rather than risk exposure. Inherited from the template SOUL.
8. **Immutable, versioned knowledge.** Ingested documents, embeddings, and their
   metadata are versioned; deletes and updates are tracked, never silent.

### Principle trade-offs (stated honestly)

- Principle 2 (permission-faithful retrieval) costs latency and complexity — it
  forbids the easy "index everything with a service account" pattern. We accept this;
  it is the difference between an enterprise platform and a demo.
- Principle 4 (isolation by construction) can raise per-tenant cost (separate
  indexes/namespaces). We accept higher cost for a smaller blast radius. Revisited per
  tenant tier in [Storage](../storage/) and [Permissions](../permissions/).
- Principle 6 (model-pluggable) adds a gateway hop. We accept it for governance,
  cost control, and vendor independence.

## 5. Alternatives considered (platform shape)

| Alternative | Why not (as the default) |
|-------------|--------------------------|
| Buy a single-vendor enterprise search/AI suite | Vendor lock-in, weak private-hosting story, limited control over permission semantics and audit. |
| Per-domain bespoke builds (status quo) | Duplicated security surface, no shared governance, slow. This is the problem we are solving. |
| Pure fine-tuning (bake knowledge into weights) | Stale, unauditable, can't honor per-user permissions, expensive to update. RAG keeps knowledge external, fresh, and permission-checkable. |
| Managed public AI + connectors | Violates "private by default"; data egress unacceptable for Finance/HR/Legal/Audit. |

**Chosen:** a self-built, privately-hosted, permission-aware RAG platform with a
governed model gateway and pluggable domain packs. Recorded as
[ADR-0001](adr/ADR-0001-platform-shape-private-rag.md).

## 6. Future scalability

The vision is realized only if adding domain #11 costs a pack, not a rebuild. Every
architectural decision is tested against one question: **"Does this stay true when we
add a new domain, a new tenant, and 10× the data?"** If a design forces core changes to
onboard a new domain, it is wrong and must be revisited.

## 7. Non-goals (for now)

- Not building a general-purpose model-training platform (we consume governed models).
- Not building a BI/visualization tool (we integrate with reporting, we don't replace it).
- Not supporting fully public, unauthenticated access — every request is attributable.

## Related

- [Platform Overview](01-platform-overview.md)
- [Security Architecture](../security/00-security-architecture.md)
- [ADR Log](adr/)
