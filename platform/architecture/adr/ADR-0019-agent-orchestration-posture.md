# ADR-0019 — Agent orchestration posture: extend `core/` into the distributed orchestrator; adopt durable execution behind a port, never an agent framework that owns the loop

- **Status:** Accepted (Cycle 23)
- **Deciders:** Platform Engineering, Enterprise Architecture, Security & Governance
- **Relates to:** [ADR-0002](ADR-0002-reuse-existing-template-core.md) (the core/project split this
  extends — ADR-0002 §"Revisit when" explicitly anticipated this decision), [ADR-0003](ADR-0003-model-gateway-indirection.md)
  + [ADR-0010](ADR-0010-storage-topology-and-tenancy.md) (the "commodity behind a port" pattern reused
  for the `ExecutionBackend`), [ADR-0004](ADR-0004-permission-faithful-retrieval.md) (the query-time
  permission gate every step honors), [ADR-0014](ADR-0014-api-contract-surface.md) (the single verifier
  answer gate the loop sequences), [ADR-0012](ADR-0012-governance-audit-and-cost.md) (the per-step
  governance gate + the fan-out-as-capability budget lever), [ADR-0006](ADR-0006-fail-closed-autonomy-default.md)
  (fail-closed autonomy the loop enforces), [ADR-0011](ADR-0011-ingestion-workers-and-connector-framework.md)
  (the at-least-once + idempotent durable-execution discipline reused), [ADR-0016](ADR-0016-domain-pack-contract.md)/[ADR-0017](ADR-0017-runtime-pack-load-spi.md)
  (the pack that declares a domain's agent graph), [Orchestration design](../../orchestration/00-agent-orchestration.md)

## Context

[ADR-0002](ADR-0002-reuse-existing-template-core.md) adopted the template's `core/` (planner, dispatcher,
governance, verifier, memory) as the platform's conceptual seed and deferred one thing to the engineering
track: *"the single-process template must be re-hosted onto the three-plane, queue-backed topology,"* naming
the risk in its own "Revisit when" — **the core abstractions proving too narrow for multi-agent, multi-tenant
orchestration.** [NEXT_STEPS open Q#6](../../NEXT_STEPS.md) framed the open decision precisely: *extend the
existing `core/` planner/verifier into the distributed orchestrator, or adopt a framework?*

With every step a request touches already fixed — retrieval behind the [permission filter](ADR-0004-permission-faithful-retrieval.md),
inference through the [Model Gateway](ADR-0003-model-gateway-indirection.md), answers through one
[verifier gate](ADR-0014-api-contract-surface.md), actions through the [governance gate](ADR-0012-governance-audit-and-cost.md)
— this is the **last open architecture question** on the platform surface. It is not cosmetic: the
orchestrator is the loop *inside which* those gates must sit. A general agent framework's defining feature is
that **it owns the plan→act loop and calls tools itself** — exactly the location the platform's five choke
points occupy. Choosing an orchestrator is therefore a choice about **whether the platform's hardest
guarantees stay in a choke point we control.**

## Decision

**Extend the `core/` planner / dispatcher / verifier / governance loop into the platform's distributed
multi-agent orchestrator — the orchestration logic and choke points stay ours and in-boundary — and adopt a
commodity durable-execution substrate for the distributed plumbing only, behind a narrow `ExecutionBackend`
port. Do not adopt an agent framework that owns planning, tool-calling, routing, or the answer gate.**

1. **Two planes, cleanly split.** The **decision plane** (what to do next, whether it is allowed, whether the
   result is good enough, who may hand off to whom) is ours — the template's [`AgentOrchestrator`](../../../core/orchestrator.py)
   grown up. The **execution plane** (durable state, retries, timers, fan-out, resume) is adopted commodity
   machinery behind the `ExecutionBackend` port. O1–O5 (the safety invariants) are properties of the decision
   plane; O6–O7 (durability, no lock-in) are satisfied by the port.

2. **The same five gates, re-hosted, in the same order.** Every step passes governance → tool-scope
   ([`WorkerRegistry`](../../../core/workers.py)) → permission filter → Model Gateway → and the run ends in
   **exactly one** [`Verifier`](../../../core/verifier.py) answer gate. Distribution changes *where* a step runs,
   never *whether* it passes a gate. No new safety predicate is introduced.

3. **Multi-agent is bounded, not emergent.** A run is a bounded DAG over a **pack-declared, allowlisted agent
   graph**; agent→agent control transfer is the existing [`HandoffRouter`](../../../core/handoff.py) (target
   allowlist + schema-validated payload + size bound), carrying the end-user context on every hop. The reachable
   agent/tool set is a static, reviewable, per-tenant fact — not a runtime surprise. The agent graph installs
   through the [pack-load SPI](ADR-0017-runtime-pack-load-spi.md) as validated config (one additive validator).

4. **Commodity behind a port (the reused bargain).** The `ExecutionBackend` port has **no method that makes a
   decision** — it cannot plan, pick a tool, call a model, or emit an answer, exactly as the
   [`VectorIndex` port has no unfiltered-search method](ADR-0010-storage-topology-and-tenancy.md). A substrate
   swap (Temporal → managed durable-workflow service → queue+state composition) is one adapter, never a caller
   change (R7). Durability is at-least-once + idempotent effects — the [ingestion-plane discipline](ADR-0011-ingestion-workers-and-connector-framework.md)
   reused.

5. **Fail-closed and tenant-bounded throughout.** High-risk steps hard-block before the autonomy shortcut
   ([ADR-0006](ADR-0006-fail-closed-autonomy-default.md)); an unlisted/oversized handoff is refused; a
   verification failure without a repair is a `200` "no answer," never an ungrounded emission; every hop carries
   `tenant_id` + budget, and the [degradation ladder](ADR-0012-governance-audit-and-cost.md) throttles fan-out
   as a **capability** lever that never relaxes a gate (R5).

**The orchestration falsifiability check** (mirroring the pack/SPI rules): *can a sub-agent emit an answer
without the single verifier gate, or call a tool outside its `WorkerRegistry` scope, or hand off to an
unlisted target?* — **no to all three**, by (2)/(3), structurally.

## Consequences

- (+) **The platform's hardest guarantees stay in a choke point we control.** Permission-faithful retrieval,
  the single answer gate, and governed inference remain un-bypassable because the loop that invokes them is
  ours and in-boundary — not a vendor's agentic loop that calls tools itself.
- (+) **Net horizontal change = none, all additive.** The distributed orchestrator enforces the same five
  gates in the same order as the in-process loop; multi-agent workflows are pack-declared config. Onboarding
  domain #11's multi-agent flow is a pack, not an orchestrator change — the founding bet applied to orchestration.
- (+) **Lock-in is bounded to one adapter** (`ExecutionBackend`), the `VectorIndex`/Gateway pattern reused a
  third time; the reasoning-quality lever (planner model + prompt) stays independent of the substrate.
- (+) **The `core/` reconciliation gets its second concrete target** — re-host `AgentOrchestrator` onto the
  port, alongside the [pack-load SPI](ADR-0017-runtime-pack-load-spi.md) implementation.
- (−) **We own the loop code** rather than inheriting a framework's ecosystem. Accepted: the loop is small and
  its whole value is that the gates live inside it; we still buy the hard commodity (durable execution).
- (−) **Bounded multi-agent forecloses emergent autonomy.** Deliberate: auditability (Principle 5) and
  fail-closed (Principle 7) require the agent set + handoff edges to be a static per-tenant fact.
- (−) **The durable-execution substrate is now safety-relevant infra.** Mitigated by idempotent at-least-once
  effects and by the substrate having no decision authority — a substrate bug re-runs a *gated* step, never
  bypasses a gate.

## Alternatives

- **Adopt a general agent framework as the orchestrator** (LangGraph / AutoGen / CrewAI / Semantic Kernel /
  an assistants API). Rejected: its core feature — owning the loop and calling tools/models itself — is exactly
  where O1–O3 require our gates; adopting it either scatters the choke points outside our control or reduces the
  framework to wrapped dead weight. Its *ideas* (planning/reflection strategies) are adoptable *inside* our loop
  via the Gateway; its *control* of the loop is not.
- **Extend `core/` but also build durable execution from scratch.** Rejected: durable, resumable, exactly-once
  distributed execution is a solved commodity with deep failure-mode surface — undifferentiated work and a
  reliability risk. Adopt it behind the `ExecutionBackend` port.
- **Wrap a framework behind our own facade.** Rejected: pays the framework's constraints (state model, version
  churn, prompt conventions) while delivering none of its value, since we must re-enter our gates on every hop.
- **Emergent multi-agent (agents self-organize / spawn freely).** Rejected: unauditable and un-fail-closable —
  the reachable agent/tool set must be a static per-tenant fact. Bounded DAG over an allowlisted graph instead.
- **Keep the single-process template loop unchanged.** Rejected: cannot scale query vs. ingestion
  independently, survive a mid-run crash, isolate tenants by construction, or bound fan-out cost — the gaps
  ADR-0002 flagged for re-hosting.
- **Per-domain bespoke orchestration (each pack ships its own runner).** Rejected: re-scatters the choke
  points and re-introduces per-domain drift — the anti-pattern [ADR-0016](ADR-0016-domain-pack-contract.md)
  exists to kill. Orchestration is core; only the agent graph is pack data.

## Revisit when

- **A pack legitimately needs an agent graph the current handoff/tool-scope grammar can't express** → add an
  additive orchestration-schema validator to the [pack-load SPI](ADR-0017-runtime-pack-load-spi.md), not a
  loop rewrite (the SPI `schema_version` bump pattern).
- **A framework proves it can host our gates without owning the loop** (e.g. a pure durable-execution engine
  with no opinion on tool-calling) → it is an `ExecutionBackend` adapter, adopted behind the port — the
  decision stands, only the substrate changes.
- **The platform gains an action-taking (write-back) plane** → the same bounded, gated, durable loop grows
  write-risk governance policies; this is an extension of the loop, not a new control plane, and would carry
  its own ADR for the transaction-control semantics named in [Audit](../../packs/audit/00-audit-pack.md).
- **The `core/` implementation lands** → this ADR + [the orchestration design](../../orchestration/00-agent-orchestration.md)
  are its specification; any deviation the implementation forces is a new ADR, not a silent drift.
