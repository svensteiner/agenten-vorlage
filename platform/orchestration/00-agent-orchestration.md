# Agent Orchestration

> Status: **Foundational** · Owner: Platform Engineering / Enterprise Architecture / Security · Cycle: 23
> Implements [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md).
> **Resolves open Q#6** (agent-framework orchestrator posture — *extend the existing `core/`
> planner/verifier into the distributed orchestrator, or adopt a framework?*), the **last open
> architecture question** on the platform surface. It was left open by
> [ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md) ("the *concepts* transfer;
> the *implementation* must be re-hosted onto the three-plane, queue-backed topology") and named in
> its own "Revisit when."
> This document does **not** re-open [ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md)
> (the query-time permission gate), the [verifier contract](../rag/00-retrieval-pipeline.md) (the single
> answer gate), or [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) (the Model
> Gateway) — it **fixes the one thing those left open**: *what runs the plan → act → verify loop when a
> request spans multiple agents, tools, and machines, and whether that runner is our code or a vendor's.*

Orchestration is the **last open horizontal decision** (its only peers were the `core/` code-reconciliation
and — now closed — open Q#3, model hosting). Everything a single agent step *touches* was fixed in earlier
cycles: retrieval runs behind the [permission filter](../permissions/00-authorization-model.md#4-query-time-enforcement)
(ADR-0004); every model call goes through the [Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md)
(ADR-0003); every answer passes one [verifier gate](../api/00-api-surface.md) (ADR-0014); every action is
[governance-gated and audited](../governance/00-governance-and-audit.md) (ADR-0012). What none of them fixed
is the **loop that sequences those steps across agents and machines**: is it the template's in-process
`AgentOrchestrator`, grown up onto the queue-backed topology — or a third-party agent framework (LangGraph,
AutoGen, CrewAI, Semantic Kernel, an assistants API)?

---

## 1. What the orchestrator must satisfy (inputs, not choices)

Hard requirements inherited from earlier cycles. An orchestration design that violates any of them has
failed its one job.

| # | Requirement | Source | Why it binds the orchestrator |
|---|-------------|--------|-------------------------------|
| O1 | **The verifier is the single answer gate.** No content reaches a caller except through the one grounding/guardrail verifier. | [ADR-0014](../architecture/adr/ADR-0014-api-contract-surface.md), [RAG §7](../rag/00-retrieval-pipeline.md) | The loop may fan out to N agents, but *exactly one* gate emits the answer; an orchestrator that lets a sub-agent reply directly breaks R2. |
| O2 | **Every step is permission-faithful and Gateway-routed.** Retrieval filters on the *end user's* principals; inference goes through the Model Gateway. | [ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md), [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md), [Principle 2](../architecture/00-vision-and-principles.md) | The end-user identity + tenant must ride *every* hop (including agent→agent handoffs); the orchestrator may never widen scope by acting as a service account. |
| O3 | **Every step is governance-gated and audited.** Tool calls pass the policy gate; who/what/which-model/what-policy is recorded. | [ADR-0012](../architecture/adr/ADR-0012-governance-audit-and-cost.md), [Principle 5](../architecture/00-vision-and-principles.md) | The plan→act loop is where actions originate; the governance choke point must sit *inside* the loop, not beside a black box that calls tools itself. |
| O4 | **Fail closed.** On any ambiguity in permission, classification, policy, or step outcome, deny/escalate — never proceed on a guess. | [Principle 7](../architecture/00-vision-and-principles.md), [ADR-0006](../architecture/adr/ADR-0006-fail-closed-autonomy-default.md) | A high-risk step blocks *before* the autonomy shortcut; a failed/uncertain step degrades to human escalation, not to a silent best-effort continuation. |
| O5 | **Tenant-isolated and resource-bounded.** No agent, tool, or memory crosses a tenant boundary; runs respect the tenant's cost envelope. | [Principle 4](../architecture/00-vision-and-principles.md), [Storage §5](../storage/00-storage-architecture.md), [Governance §7](../governance/00-governance-and-audit.md) (R5) | Orchestration is where fan-out multiplies cost and blast radius; the run carries a `tenant_id` on every hop and a budget the degradation ladder can throttle *capability before safety*. |
| O6 | **Durable, resumable, at-least-once with idempotent effects.** A crashed run resumes without double-acting; a long run survives a restart. | [ADR-0011](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md) (the ingestion-DAG discipline) | A multi-step, multi-machine loop needs the *same* durable-execution property the ingestion plane already has — checkpointed state, retries, idempotency keys. |
| O7 | **No new hot-path lock-in.** The distributed-execution substrate is swappable; the safety-bearing logic is ours. | [Principle 6](../architecture/00-vision-and-principles.md), R7, [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md)/[ADR-0010](../architecture/adr/ADR-0010-storage-topology-and-tenancy.md) | Whatever runs the loop must be replaceable behind a port, exactly as models sit behind the Gateway and vectors behind the `VectorIndex` port. |

**The load-bearing observation:** O1–O5 are all statements about *where the choke points sit*. A general
agent framework's core value proposition is that **it owns the plan→act loop and calls tools itself** — which
is precisely the place O1–O3 require *our* gates to live. A framework that plans, routes, and calls tools is
not a neutral runtime; it is a **competing choke point** that would scatter the very invariants
[ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md)/[ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md)/[ADR-0014](../architecture/adr/ADR-0014-api-contract-surface.md)
spent five cycles consolidating.

---

## 2. The decision in one paragraph

**Extend the existing `core/` planner / dispatcher / verifier / governance loop into the platform's
distributed multi-agent orchestrator — the orchestration *logic and choke points stay ours and in-boundary*
— and adopt a commodity durable-execution substrate for the *distributed plumbing only* (durable state,
retries, timers, fan-out), behind a narrow `ExecutionBackend` port.** We do **not** adopt an agent framework
that owns planning, tool-calling, routing, or the answer gate. This is the orchestration projection of the
pattern the platform already uses twice: **keep the safety-bearing decision in a choke point we control
([Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md), the permission filter), and put
the swappable commodity behind a port ([`VectorIndex`](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)).**
Concretely: the template's [`AgentOrchestrator`](../../core/orchestrator.py) *already is* the loop
([`Planner`](../../core/planner.py) → [`GovernancePolicy`](../../core/governance.py) →
[`Dispatcher`](../../core/dispatcher.py) → [`SubagentManager`](../../core/subagents.py) →
[`Verifier`](../../core/verifier.py)), with multi-agent primitives already present — the
[`HandoffRouter`](../../core/handoff.py) (allowlisted, schema-validated agent→agent control transfer) and the
[`WorkerRegistry`](../../core/workers.py) (per-agent tool scoping). The distributed orchestrator is these
existing primitives **re-hosted** onto the queue-backed topology, exactly as
[ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md) foresaw — *concepts transfer,
implementation re-hosts* — not a new design.

---

## 3. The orchestrator, drawn

```
                          ┌──────────────────────────────────────────────────────────────┐
   token-bound request →  │                    core/ ORCHESTRATOR (ours)                   │
   (tenant, end-user      │                                                                │
    principals, budget)   │   Planner ──► Governance gate ──► Dispatcher ──► Verifier gate │
                          │      │            (O3)                │   (O2)       (O1)       │
                          │      │  plan = bounded DAG of steps   │                         │
                          │      ▼                                ▼                         │
                          │   HandoffRouter                   WorkerRegistry                │
                          │   (allowlist + schema, O2/O4)     (per-agent tool scope, O3/O5) │
                          └───────────────┬───────────────────────────┬────────────────────┘
                                          │  every step / handoff      │  every tool + model call
                                          │  carries (tenant, user,    │  passes the same gates
                                          │  budget, idempotency key)  │
                                          ▼                            ▼
              ┌───────────────────────────────────────┐   ┌───────────────────────────────────┐
              │   ExecutionBackend PORT (O6/O7)        │   │   The already-fixed step surface   │
              │   durable state · retries · timers ·   │   │   • permission filter (ADR-0004)   │
              │   fan-out · resume — commodity,        │   │   • Model Gateway (ADR-0003)       │
              │   swappable adapter                    │   │   • tools via connectors (ADR-0011)│
              │   (Temporal / durable queue / …)       │   │   • audit event per hop (ADR-0012) │
              └───────────────────────────────────────┘   └───────────────────────────────────┘
                     the "distributed plumbing"                   nothing here re-decided
                     we ADOPT (behind a port)                     — the orchestrator only sequences it
```

Two planes, cleanly split:

- **The decision plane (ours, in-boundary):** what to do next, whether it is allowed, whether the result is
  good enough, who may hand off to whom. This is `core/`, grown up. It is the plane that *must* be ours
  because O1–O5 are properties of it.
- **The execution plane (adopted, behind `ExecutionBackend`):** how the steps are durably run, retried,
  timed, fanned out, and resumed across machines. This is commodity distributed-systems machinery with no
  safety semantics of its own — the plane where a framework/substrate earns its keep and where lock-in is
  bounded to one adapter (O7).

---

## 4. Why extend, not adopt (the core of the decision)

### 4.1 A framework wants the choke point we already own

Every general agent framework's headline feature is an **agentic loop that plans and calls tools for you**.
Adopting one means one of two bad outcomes:

- **Let it call tools and models directly** → it becomes a second place where retrieval and inference
  happen, *outside* the permission filter (O2), the Model Gateway (O2), and the governance gate (O3). The
  platform's hardest guarantee — [permission-faithful retrieval](../architecture/00-vision-and-principles.md)
  — would depend on a vendor's loop honoring the end-user's principals on every hop. That is exactly the
  "index/act with a service account" anti-pattern [Principle 2](../architecture/00-vision-and-principles.md)
  forbids, re-introduced at the orchestration layer.
- **Wrap every framework tool-call to re-enter our gates** → you have re-implemented the orchestrator *around*
  the framework, paying its constraints (its state model, its prompt conventions, its version churn) for a
  loop you now fully control anyway. The framework becomes dead weight between the caller and the gates.

Neither is worth it. The loop is **~200 lines of sequencing** ([`AgentOrchestrator.run`](../../core/orchestrator.py))
whose entire value is that our gates are *inside* it; a framework's value is the loop, which is the part we
must not delegate.

### 4.2 We already have the multi-agent primitives — as fail-closed, inspectable code

The three things a multi-agent framework sells are already present and already fail-closed:

| Multi-agent need | Framework feature | What `core/` already has |
|------------------|-------------------|--------------------------|
| **Agent→agent control transfer** | "handoffs" / "routing" / edges | [`HandoffRouter`](../../core/handoff.py): a target **allowlist** + **schema-validated** payload + a payload-size bound. A handoff to an unlisted target is refused; the end-user context rides the payload. **Bounded, not emergent.** |
| **Tool scoping per agent** | per-agent tool sets | [`WorkerRegistry`](../../core/workers.py): each worker/agent gets a scoped tool set by trust level — least privilege by construction (O3/O5). |
| **Plan / act / reflect / verify** | the agentic loop | [`Planner`](../../core/planner.py) (plan = a bounded DAG of typed steps), [`Dispatcher`](../../core/dispatcher.py) (tool execution), [`Verifier`](../../core/verifier.py) (grounding/quality gate with self-correction), [`GovernancePolicy`](../../core/governance.py) (per-step risk gate). |

Extending these to the distributed topology is **additive**: the plan becomes a persisted DAG, a step becomes
a durable-execution activity, a handoff becomes a queued message to another agent worker — but the *predicates*
(allowlist, schema, tool-scope, verifier threshold, governance risk) are unchanged. This is why the change is
**net horizontal = none** (see §6): no new safety predicate is introduced; the existing ones are re-hosted.

### 4.3 Multi-agent is bounded, never emergent

A deliberate stance the extend-path makes enforceable and a framework's "autonomous agents negotiate freely"
default fights: **the set of agents, their tools, and the legal handoffs between them are declared, not
discovered at runtime.** A run is a *bounded DAG over an allowlisted agent graph*, not an open-ended swarm.
Rationale:

- **Auditability (Principle 5):** "which agents could have touched this answer, with which tools?" must be a
  static, reviewable fact per tenant/pack — not a property of what an LLM decided to spawn.
- **Fail-closed (O4):** an agent may only hand off to a target on its allowlist; an unresolvable or unlisted
  target is a refused handoff, not an improvised one.
- **Blast-radius (O5):** bounded fan-out is what makes the cost envelope enforceable and the tenant boundary
  provable.

The agent graph and its handoff allowlist are **pack-declared** — the [domain pack](../packs/README.md)'s §6
workflow hint grows into "which sub-agents this domain uses and how they may hand off," installed by the
[pack-load SPI](../packs/01-pack-load-spi.md) as validated declarative config. So *adding a domain's
multi-agent workflow is a pack, not an orchestrator change* — the founding bet, applied to orchestration.

### 4.4 What we *do* adopt — the `ExecutionBackend` port

The genuinely hard, genuinely commodity part is **durable distributed execution**: checkpointing a
half-finished multi-step run, retrying a failed activity with backoff, firing timers, fanning out and
joining, resuming after a crash exactly once. Building this from scratch would be reinventing a workflow
engine. So we **adopt** it — a durable-execution substrate (Temporal-class) or a durable-queue + state-store
composition — **behind an `ExecutionBackend` port** with a small surface:

```
ExecutionBackend (port):
    start_run(run_spec, tenant, idempotency_key) -> run_handle
    schedule_step(run_handle, step, idempotency_key) -> step_handle   # at-least-once, idempotent
    await_steps(run_handle, step_handles) -> results                  # join / fan-in
    signal / timer / resume                                           # durability primitives
    # NOTE: no method plans, selects a tool, calls a model, or emits an answer.
```

The port deliberately has **no method that makes a decision** — it cannot plan, cannot pick a tool, cannot
call a model, cannot emit an answer. Like the [`VectorIndex` port that has no unfiltered-search method](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7),
the `ExecutionBackend` port has **no method that bypasses a gate** — the decision plane is simply not
expressible through it. A substrate swap (Temporal → a managed durable-workflow service → a queue+Postgres
composition for a small tenant) is one adapter, never a caller change (O7). This is the exact
Model-Gateway/`VectorIndex` bargain: **adopt the commodity, behind a port; own the safety.**

---

## 5. The distributed run, end to end

1. **Admission.** A [token-bound request](../api/00-api-surface.md) enters at the API edge: tenant + end-user
   principals + budget resolved once, never from the URL. The orchestrator opens a **run** on the
   `ExecutionBackend` keyed by `(tenant_id, request_id)` — the run context that rides every subsequent hop.
2. **Plan.** The `Planner` drafts a **bounded DAG** of typed steps (retrieve / reason / tool / handoff /
   verify), scoped to the tenant's pack-declared agent graph. The plan is persisted (durable, resumable — O6).
3. **Per-step gates (unchanged from single-process).** For each step, in order: **governance gate** (risk
   policy, high-risk hard-blocks *before* the autonomy shortcut — O3/O4/[ADR-0006](../architecture/adr/ADR-0006-fail-closed-autonomy-default.md));
   **tool scope** (`WorkerRegistry` — the agent may only call its allowlisted tools — O3/O5); **retrieval**
   under the end-user permission filter (O2); **inference** through the Model Gateway (O2). Each step is a
   durable activity with an idempotency key (O6); a retry never double-acts.
4. **Handoff (multi-agent).** If a step yields a `HandoffRequest`, the `HandoffRouter` validates target ∈
   allowlist + schema + payload bound; the run context (tenant, user, budget) is carried into the target
   agent's queued step. An unlisted/oversized/malformed handoff is **refused** (O4), not improvised. Fan-out
   is bounded by the pack-declared graph.
5. **Single answer gate.** When the DAG completes, **exactly one** `Verifier` pass produces the answer
   (grounding + guardrails + self-correction); no sub-agent ever replies to the caller directly (O1). A
   verification failure without a repair is a fail-closed non-answer (a `200` "no answer," per
   [API §](../api/00-api-surface.md)), never an ungrounded emission.
6. **Budget + audit throughout.** Every hop debits the tenant budget (the [degradation ladder](../governance/00-governance-and-audit.md#7-cost)
   throttles *capability before safety* — a budget cap defers P2 / drops to a cheaper model tier / narrows
   fan-out, but **never** relaxes a gate — O5/R5) and emits an [audit event](../governance/00-governance-and-audit.md)
   (who / what / which model / which policy / which agents — O3, Principle 5). A crash resumes the run from
   its last durable checkpoint (O6).

The shape is **identical to the single-process `AgentOrchestrator.run` loop** — the same five gates in the
same order — with each step re-hosted as a durable, tenant-scoped, queued activity. That identity *is* the
proof the extension is additive.

---

## 6. Why this changes nothing horizontal

Consistent with every cycle since [ADR-0016](../architecture/adr/ADR-0016-domain-pack-contract.md): **net
horizontal change = none, all additive.**

- **No new safety predicate.** The distributed orchestrator enforces the *same* five gates
  (governance → tool-scope → permission filter → Model Gateway → verifier) in the same order as the
  in-process loop. Distribution changes *where* a step runs, never *whether* it passes a gate.
- **No new choke point; the existing ones stay single.** One verifier answer gate (O1), one Model Gateway
  (O2), one permission filter (O2), one governance gate (O3) — the orchestrator *sequences* them; it does not
  add a rival. Adopting a framework would have added a rival; extending `core/` does not.
- **No new hot-path lock-in.** The only adopted component is the `ExecutionBackend`, confined to one adapter
  behind a port with no decision method (O7) — the `VectorIndex`/Gateway pattern reused a third time.
- **Multi-agent workflows are pack-declared, not core changes.** A domain's agent graph + handoff allowlist
  install through the [pack-load SPI](../packs/01-pack-load-spi.md) as validated config — so a new domain's
  orchestration is *additive data*, exactly like its labels and ACL fixtures. Onboarding domain #11's
  multi-agent flow is a pack, not a redesign ([Vision §6](../architecture/00-vision-and-principles.md)).
- **This is the payoff of [ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md).** "The
  concepts transfer; the implementation re-hosts onto the queue-backed topology" was written in Cycle 1;
  this document discharges it. Hard to *decide* (a fashionable framework is tempting), trivial to *wire* (the
  primitives already exist) — the sign of a good earlier decision.

---

## 7. Trade-offs (stated honestly)

- **Build-the-loop vs. buy-the-loop.** We carry the orchestrator loop ourselves rather than inheriting a
  framework's ecosystem (its integrations, its community patterns, its prompt libraries). Accepted: the loop
  is small and the reason to own it — the gates live inside it — is non-negotiable. We still *buy* the hard
  part (durable execution) behind the port.
- **Bounded multi-agent vs. emergent autonomy.** Declaring the agent graph up front forecloses "let agents
  self-organize." Accepted deliberately: auditability (Principle 5) and fail-closed (Principle 7) require the
  agent set and handoff edges to be a static, reviewable, per-tenant fact — not a runtime surprise. A domain
  that needs more agents adds them to its pack graph; it never spawns them ad hoc.
- **Extending core is more up-front work than importing a framework.** Re-hosting planner/verifier/handoff
  onto durable execution is real engineering. Accepted: it is bounded (the primitives exist and are
  unit-tested), and it avoids the far larger cost of retrofitting five safety invariants around a black-box
  loop — and the perpetual tax of tracking a fast-moving framework's breaking changes.
- **A framework might reason better today.** Some frameworks ship clever planning/reflection loops. But the
  *planner* is itself model-mediated behind the Gateway — we can adopt a better planning *prompt/strategy*
  inside our loop without adopting the framework's *control* of the loop. The reasoning quality lever is the
  model + prompt, not the orchestrator vendor.
- **Durable-execution substrate is now safety-relevant infra.** A bug in the `ExecutionBackend` (a lost
  idempotency key, a double-run) is an availability/correctness event. Mitigated by at-least-once + idempotent
  effects (O6, the [ingestion-plane discipline](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md)
  reused) and by the substrate having *no* decision authority — the worst a substrate bug does is re-run a
  gated step, never bypass a gate.

---

## 8. Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Adopt a general agent framework that owns the plan→act→tool loop** (LangGraph / AutoGen / CrewAI / Semantic Kernel / an assistants API) | **Rejected as the orchestrator.** Its core feature — owning the loop and calling tools/models itself — is precisely where O1–O3 require *our* gates (verifier, permission filter, Model Gateway, governance). Adopting it either scatters those choke points outside our control or reduces the framework to dead weight we wrap on every call. A framework's *ideas* (planning strategies, reflection prompts) can be adopted *inside* our loop via the Gateway; its *control* of the loop cannot. |
| **Extend `core/` for the loop; build durable execution from scratch too** | Rejected: durable, resumable, exactly-once distributed execution is a solved commodity with deep failure-mode surface; reinventing it is undifferentiated work and a reliability risk. Adopt it behind the `ExecutionBackend` port instead — the "buy the commodity, own the safety" split. |
| **Wrap a framework behind our own facade** ("use it but hide it") | Rejected: pays the framework's constraints (state model, version churn, prompt conventions) while delivering none of its value, because we must re-enter our gates on every hop anyway. If we control the loop, we should own the ~200 lines, not shim them. |
| **Emergent multi-agent (agents self-organize, discover peers, spawn freely)** | Rejected: unauditable (Principle 5) and un-fail-closable (Principle 7) — the reachable agent/tool set must be a static per-tenant fact. Bounded DAG over a pack-declared allowlisted graph instead. |
| **Keep the single-process template loop unchanged** | Rejected: it cannot scale query vs. ingestion independently, survive a crash mid-run, isolate tenants by construction, or bound fan-out cost — exactly the gaps [ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md) flagged for re-hosting. The *concepts* stay; the *implementation* must move onto the durable, queued topology. |
| **Per-domain bespoke orchestration** (each pack ships its own runner) | Rejected: re-scatters the choke points the platform consolidated and re-introduces per-domain drift — the anti-pattern the [pack contract](../architecture/adr/ADR-0016-domain-pack-contract.md) exists to kill. Orchestration is core; only the *agent graph* is pack data. |

---

## 9. Future scalability

- **A new domain's multi-agent workflow** is a **pack graph + handoff allowlist**, installed by the
  [pack-load SPI](../packs/01-pack-load-spi.md) as validated config — additive data, not an orchestrator
  change. Domain #11's agents are a pack, not a rebuild.
- **A new execution substrate** (a managed durable-workflow service, a lighter queue+state composition for a
  small Isolated tenant, an on-prem engine for a sovereign one) slots in as **one `ExecutionBackend`
  adapter** — the routing/gates are unchanged, exactly as a new `hosting_posture` or vector engine slots in.
- **A better planning/reflection strategy** is adopted **inside** the loop as a Gateway-mediated model +
  prompt change (an eval-gated [registry](../governance/00-governance-and-audit.md#8-g6--model-governance)
  choice), never as a change of orchestrator vendor — the reasoning lever and the control lever stay separate.
- **A future *action-taking* platform** (write-back / transaction execution, today explicitly out of the
  [read-plane-mirror scope](../packs/audit/00-audit-pack.md)) reuses this same bounded, gated, durable loop —
  the governance gate simply gains write-risk policies. The orchestrator is built to grow *actions* without
  growing a new control plane.
- **The `core/` implementation** is the concrete engineering target: re-host `AgentOrchestrator` onto the
  `ExecutionBackend` port, alongside the [pack-load SPI](../packs/01-pack-load-spi.md) implementation (the two
  first `platform/`→`core/` reconciliation targets). *Falsifiability check for the implementation:* can a
  sub-agent emit an answer without passing the single verifier gate, or call a tool outside its
  `WorkerRegistry` scope, in a unit test? Expected: **no** — both are structurally unreachable.

---

## 10. What this hands to other documents

- **[NEXT_STEPS §3](../NEXT_STEPS.md):** closes **open Q#6** — the last open architecture question. Both
  remaining items are now on the **engineering track** (implement the pack-load SPI + the orchestrator loop
  in `core/`).
- **[Packs / pack-load SPI](../packs/01-pack-load-spi.md):** a pack's §6 workflow hint grows into a
  **pack-declared agent graph + handoff allowlist**, validated and installed as declarative config — the SPI
  gains one additive validator (agent-graph ⊆ allowlisted-targets), no new lifecycle stage.
- **[Governance §7](../governance/00-governance-and-audit.md):** the run-level budget + the degradation ladder
  now bind **fan-out** as a capability lever (narrow fan-out before touching a gate); an audit event records
  the agent set per answer.
- **[Deployment](../deployment/00-deployment-topology.md):** the `ExecutionBackend` substrate is a topology
  choice per tier (managed durable-workflow service vs. queue+state composition) with reserved capacity for
  P0-class runs — a sizing input alongside reserved-P0 and the Track-A GPU pool, not a redesign.
- **[Security](../security/00-security-architecture.md):** agent→agent handoffs are an intra-boundary trust
  edge; the handoff allowlist + schema validation + carried end-user context are the controls that keep a
  handoff from becoming a privilege-escalation path.

## Related

- [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md) — the decision record.
- [ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md) — the core/project split this extends; named this decision in its "Revisit when."
- [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) / [ADR-0010 §3.4](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7) — the "commodity behind a port" pattern reused for `ExecutionBackend`.
- [ADR-0004](../architecture/adr/ADR-0004-permission-faithful-retrieval.md) / [ADR-0014](../architecture/adr/ADR-0014-api-contract-surface.md) — the permission filter and the single verifier gate the loop sequences.
- [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) — the pack-load SPI that installs the pack-declared agent graph.
