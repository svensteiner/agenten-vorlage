# The distributed `ExecutionBackend` substrate — adapter design & per-tier sizing

> Status: **Seeded** (Cycle 27) · Owner: Platform Engineering / Deployment / Security
> Discharges the substrate half of [ADR-0019 §4.4](../architecture/adr/ADR-0019-agent-orchestration-posture.md)
> and the sizing input [Orchestration §10 → Deployment](00-agent-orchestration.md#10-what-this-hands-to-other-documents).
> **No new ADR** — this is the *engineering/deployment projection* of a decision already ratified (ADR-0019);
> it introduces no new cross-component choice, only the concrete adapter shape and the numbers that size it.

---

## 0. Why this document exists (the gap it closes)

[ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md) resolved the orchestration posture:
**own the decision plane, adopt a commodity durable-execution substrate behind the
[`ExecutionBackend` port](../../core/execution.py)**. Cycles 25–26 then *built* the port in code — the
`ExecutionBackend` Protocol (no decision method, grep-invariant enforced) and the default
[`InProcessExecutionBackend`](../../core/execution.py), with the orchestrator's `run()` loop re-expressed
against it at behaviour parity (193 tests green).

What does **not** yet exist is the thing the port was built *for*: the **distributed adapter** — the one that
turns a single-process loop into a crash-resilient, tenant-isolated, fan-out-bounded distributed orchestrator —
and the **capacity sizing** that makes it affordable per tenant tier. ADR-0019 named it "Temporal-class" in one
line and handed sizing to Deployment; neither has a home. This document is that home. It answers, concretely:

- **What is the distributed adapter?** (§2 the port recap · §3 the adapter, drawn · §4 exactly-once discipline)
- **How is it sized per tier?** (§5 a reserved-capacity class alongside reserved-P0 and the Track-A GPU pool)
- **How does a substrate get swapped or added?** (§6 the adapter-swap contract)
- **Trade-offs / Alternatives / Future scalability** (§7–§9)

It is a **tuning input, not a redesign** — the same phrase [Deployment §6](../deployment/00-deployment-topology.md#6-sla-capacity-sizing-d2-d3-meeting-the-ratified-freshness-numbers-at-cost)
uses for reserved-P0 and [Models](../models/00-model-hosting-and-serving.md) uses for the GPU pool. Nothing
horizontal changes; the port already exists, and this fills in the adapter behind it.

---

## 1. What the substrate must satisfy (inputs, not choices)

These are inherited constraints. The adapter design does not get to relax any of them.

| # | Constraint | Source |
|---|-----------|--------|
| S1 | **No decision authority.** The adapter implements only `start_run / schedule_step / await_steps / signal / timer / resume`. It never plans, selects a tool, calls a model, verifies, or allows. | [`core/execution.py` `DECISION_VERBS`](../../core/execution.py); [Orchestration §4.4](00-agent-orchestration.md#44-what-we-do-adopt-the-executionbackend-port) |
| S2 | **At-least-once + idempotent effects → exactly-once *observable* execution.** A redelivered activity must not double-act. | O6; [ingestion-plane discipline, ADR-0011](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md) |
| S3 | **Tenant isolation by construction.** A run is keyed `(tenant_id, request_id)`; no activity, timer, signal, or queue crosses a tenant boundary. | [`RunSpec`](../../core/execution.py); R4; [Storage §5.2](../storage/00-storage-architecture.md) |
| S4 | **Durable & resumable.** A crash mid-run resumes from the last checkpoint; the plan DAG is persisted. | O6; [Orchestration §5](00-agent-orchestration.md#5-the-distributed-run-end-to-end) |
| S5 | **In-boundary for the Isolated tier.** An Isolated / sovereign tenant's run state (which encodes *what the user asked* and *which items were retrieved*) must not leave the trust boundary — the substrate follows the same residency rule as content. | [Models Track A](../models/00-model-hosting-and-serving.md); [Deployment §7.2](../deployment/00-deployment-topology.md#72-region--residency-routing) |
| S6 | **Fan-out is bounded and budget-debited.** The number of concurrent agent activities per run is capped by the pack-declared graph; the [degradation ladder](../governance/00-governance-and-audit.md#7-cost) may *narrow* fan-out (a capability lever) but never relax a gate. | [Orchestration §4.3](00-agent-orchestration.md#43-multi-agent-is-bounded-never-emergent), §6; R5 |
| S7 | **One adapter, no caller change.** Swapping substrate is a second class implementing the Protocol — the orchestrator loop, the gates, and every caller are untouched. | O7; the [`VectorIndex`](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)/[Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md) bargain |

**The load-bearing observation:** every one of S1–S7 is a property the *port* already guarantees or the
*in-process adapter* already models. The distributed adapter's job is to preserve them across machines and
crashes — not to invent new ones. That is precisely why this is additive: the safety surface is fixed; only
the durability mechanism grows.

---

## 2. The port, recapped (the seam being filled)

From [`core/execution.py`](../../core/execution.py), the surface the adapter must implement:

```
ExecutionBackend (Protocol — no decision method):
    start_run(run_spec: RunSpec, *, idempotency_key)        -> RunHandle
    schedule_step(run: RunHandle, step: Step, *, idem_key)  -> StepHandle   # at-least-once
    await_steps(run: RunHandle, steps) -> list[StepResult]                  # fan-in / join
    signal(run, name, payload) -> None                                      # external event in
    timer(run, seconds) -> None                                             # durable timer
    resume(run_id) -> RunHandle                                             # crash recovery
```

- `Step.activity` is an **opaque callable** in-process; a distributed adapter carries a **serializable activity
  handle** instead (a registered activity name + serialized inputs), because a live closure cannot cross a
  wire or survive a crash. This substitution is the *entire* difference between the two adapters — the
  decision plane still decides *what* the activity is; the adapter only moves *when/whether/retry* off-box.
- `start_run` is **idempotent on `run_id`** (see the in-process adapter: starting the same run twice returns
  the same handle). The distributed adapter inherits this as its exactly-once anchor (§4).

---

## 3. The distributed adapter, drawn

The adapter is a thin translation layer: orchestrator calls in → durable-workflow substrate primitives out.
It owns **no policy**; it owns **serialization, idempotency-key derivation, tenant-scoped routing, and result
boxing**.

```
   Decision plane (ours, in-boundary — core/orchestrator.py)
   ┌──────────────────────────────────────────────────────────────┐
   │ Planner → Governance → ToolScope → [Permission filter] →      │
   │ Model Gateway → Handoff → Verifier   (the five gates, in order)│
   └───────────────┬──────────────────────────────────────────────┘
                   │ ExecutionBackend port  (no decision method — S1)
                   ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ DistributedExecutionBackend  (the adapter this doc designs)    │
   │   • serialize Step.activity → (activity_name, inputs)          │
   │   • derive idempotency_key = f(run_id, step_id, seq)  (S2)     │
   │   • route on tenant_id → per-tenant task queue / namespace (S3)│
   │   • box DispatchResult into StepResult.metadata (parity)       │
   └───────────────┬──────────────────────────────────────────────┘
                   │  substrate SDK  (Temporal-class / queue+state)
                   ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Durable-execution substrate  (adopted commodity)              │
   │   workflow state · retry+backoff · timers · fan-out/join ·    │
   │   exactly-once activity dispatch · crash-resume                │
   │   ── Activity workers (execute the opaque activity) ──         │
   └──────────────────────────────────────────────────────────────┘
```

**Two candidate substrate shapes** sit behind the *same* adapter interface — the choice is per tier (§5):

1. **Temporal-class durable-workflow engine** (Temporal / a managed durable-workflow service).
   The run is a **workflow**; each `schedule_step` is an **activity** with the substrate's native
   retry/timeout/idempotency; `await_steps` is activity-future join; `signal`/`timer` map 1:1 to workflow
   signals/timers; `resume` is automatic (event-sourced replay). **Best fit** where fan-out, long-running
   multi-agent DAGs, and crash-resume matter — the Standard-tier default and any multi-agent-heavy tenant.

2. **Durable-queue + state-store composition** (managed queue + Postgres run-state table, the
   [ingestion outbox pattern](../workers/00-ingestion-architecture.md) reused).
   `schedule_step` enqueues; `await_steps` polls the run-state table; `signal`/`timer` are rows; `resume`
   rehydrates from the table. **Best fit** for a **small Isolated / sovereign tenant** where standing up a
   full workflow engine in-boundary is disproportionate, or where the operator mandates a minimal
   dependency surface. Lower ceiling (fan-out and long timers are more manual), lower floor (no engine to
   operate).

Both are *adapters behind the one port* — S7. Adding a third (an on-prem sovereign engine) is the same move.

---

## 4. Exactly-once *observable* execution (the safety-relevant core — S2)

A durable substrate guarantees **at-least-once** activity dispatch (a worker crash after acting but before
ack forces a redelivery). The platform needs **exactly-once observable effect**. The gap is closed the same
way the ingestion plane closes it — **idempotent, version/key-addressed effects** — not by the substrate
promising something it structurally cannot.

- **The idempotency key is derived, not random.** `idempotency_key = f(run_id, step_id, seq)`. The Cycle-26
  hardening is the ground truth here: an omitted `request_id` defaults to a **fresh `uuid4` per invocation**
  (so a long-lived orchestrator running the same task twice does *not* replay a cached result and skip side
  effects), and the execution key carries a **per-run step-sequence number** so two plan steps sharing an id
  cannot collide. The distributed adapter inherits both — they are the exactly-once anchors, already
  regression-tested (`test_each_run_gets_a_distinct_identity`,
  `test_repeated_task_on_same_orchestrator_reexecutes_side_effects`,
  `test_duplicate_plan_step_ids_do_not_collide_in_backend`).
- **Effects are idempotent by construction, not by luck.** A retrieval is a pure read (naturally idempotent).
  A model call is debited once per idempotency key (the [Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md)
  dedups on the key). The verifier answer gate runs **exactly once** per run (O1) — the substrate schedules
  it as a single terminal activity keyed on `run_id`, so a resume never produces a second answer.
- **The worst a substrate bug can do is re-run a *gated* step, never bypass a gate** (Orchestration §7). This
  is the whole payoff of S1: because the adapter carries no decision authority, an at-least-once redelivery
  re-enters governance → tool-scope → permission-filter → Gateway → verifier *again* — a double-check, never a
  skipped check. A lost message degrades *availability* (the run stalls until resume), never *safety*.

**Falsifiability check** (mirroring the orchestration one): *can a substrate redelivery, timer misfire, or
crash-resume cause a sub-agent to answer without the verifier gate, act on a tool outside its `WorkerRegistry`
scope, or double-execute a side effect?* — **no to all three**, because the adapter replays the *activity*
through the unchanged decision plane and the effect is idempotency-keyed. That "no" is the proof the
distributed adapter is additive.

---

## 5. Per-tier substrate sizing (the Deployment input, D2/D3/D9)

This is the **reserved-capacity class** the orchestration doc handed to Deployment — sized the same way as
[reserved-P0](../deployment/00-deployment-topology.md#62-reserved-p0-capacity-the-sizing-that-makes-the-sla-affordable)
and the [Track-A GPU pool](../models/00-model-hosting-and-serving.md): **reserve safety-critical capacity in
advance; autoscale bulk on demand.**

| Dimension | Shared tier (default) | Isolated / high-volume tier |
|-----------|----------------------|-----------------------------|
| **Substrate shape** | Temporal-class engine (managed or self-run), multi-tenant with per-tenant **task queue + namespace** (S3). | **In-boundary** engine (S5) — Temporal-class self-hosted for high-volume; queue+state composition (§3.2) for a small sovereign tenant. Per-tenant dedicated namespace. |
| **Tenant isolation** | Namespace + task-queue per tenant; workflow IDs prefixed `tenant_id:` (cross-tenant workflow unrepresentable — the `RunSpec` key). | Dedicated engine/DB **per tenant** at the top of the tier; namespace-per-tenant below. |
| **Reserved run capacity** | A standing pool of **warm activity workers** sized to *peak concurrent P0/P1 runs* (a revocation-triggered re-answer, an interactive query), so a safety-class run never queues behind a P2 batch. P2 (backfill re-answers, eval runs) **autoscales on queue lag.** | Same asymmetry, sized to the tenant's contracted concurrency; reserved higher because the tenant paid for a fixed floor. |
| **Fan-out cap** | Per-run concurrent-activity ceiling from the **pack-declared agent graph** (S6); the degradation ladder narrows it before touching a gate. | Same; a sovereign tenant may contract a higher ceiling — a config value, not a redesign. |
| **Durable timer / long-run budget** | Bounded max run wall-clock; a run exceeding it is checkpointed and its continuation queued at P2 (no unbounded standing state). | Same; longer contracted ceilings permitted. |
| **Placement / residency** | Substrate co-located in the tenant's residency region ([Deployment §7.2](../deployment/00-deployment-topology.md#72-region--residency-routing)). | Substrate **in-boundary**, same residency class as content and the Track-A GPU pool — run state never egresses (S5). |

**The sizing asymmetry, stated once:** you **reserve** the capacity to *start and finish a safety-class run
promptly* (a P0 revocation re-answer must not wait), and you **autoscale** the capacity for *bulk/batch runs*
(backfill re-answers, eval sweeps) on measured queue lag. This is the reserved-P0 rule applied to the
orchestration plane — identical shape, different resource. The empirical numbers (worker counts, engine
instance sizing, $/run) land in Deployment's **versioned pricing/envelope manifest**
([§7.1](../deployment/00-deployment-topology.md#71-where-the-empirical-numbers-land)), promoted through the
same reviewable pipeline as every other price — so a capacity change is a commit, not a code change.

---

## 6. The adapter-swap contract (S7, made concrete)

A new substrate is onboarded exactly like a new [`VectorIndex`](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
engine or a new [`hosting_posture`](../models/00-model-hosting-and-serving.md):

1. **Implement the six-method Protocol.** Nothing else. The port-purity test
   ([`test_execution_port.py`](../../core/execution.py)) is the machine gate — a candidate adapter that grows a
   decision verb fails CI, structurally.
2. **Pass the parity suite.** The new adapter must reproduce the in-process adapter's
   `success / outputs / dispatch_count / run_id` on the existing parity tests (`test_orchestrator_execution.py`),
   *and* drive its own primitives (parity must not be achieved by bypassing the substrate — the Cycle-26 spy
   test pins this).
3. **Pass the exactly-once regression suite** (§4) under injected redelivery / crash-resume — the distributed
   adapter's *additional* burden over the in-process one, since only it faces those failure modes.
4. **Declare its residency + isolation properties** for the tenant→substrate placement map (the same map that
   drives [graduation §3.3](../deployment/00-deployment-topology.md#33-graduation-shared--isolated-without-redesign)).

There is **no step that touches the orchestrator loop, the gates, or any caller.** That absence *is* the
lock-in bound (R7): the substrate is confined to one adapter with no decision authority.

---

## 7. Trade-offs (stated honestly)

- **Adopt-the-engine vs. compose-from-primitives.** A Temporal-class engine buys crash-resume, retries,
  timers, and fan-out as a solved commodity — at the cost of operating (or paying for) the engine and
  tracking its version surface. The queue+state composition has a lower operational floor but a lower
  capability ceiling (manual fan-out/timers). **Resolution: tier-select** — engine where fan-out/resume earn
  their keep (Shared default, high-volume Isolated); composition for a small sovereign tenant where a full
  engine is disproportionate. Both behind the one port, so the choice is reversible per tenant.
- **Durable state is now safety-*relevant* infra.** Run state encodes the user's question and the retrieved
  item set — sensitive. Mitigated by S3 (tenant-keyed, no cross-tenant state) and S5 (in-boundary for
  Isolated, same residency as content); the substrate is inside the audited boundary, not a third-party SaaS
  holding Isolated-tenant run state.
- **At-least-once redelivery costs compute, not correctness.** A redelivered activity re-runs the gated step
  (idempotent effect), so a flaky worker inflates cost/latency, never access. Accepted: the degradation
  ladder and per-run budget bound the cost; the alternative (exactly-once delivery) is a distributed-systems
  fiction the platform correctly refuses to depend on.
- **Reserving orchestration capacity has a standing cost.** Warm workers for safety-class runs are paid for
  whether or not a revocation storm happens — the same bet as reserved-P0. Accepted for the same reason:
  *reacting* to a safety-class backlog is already an SLA/security event.
- **Bounded fan-out can throttle a legitimately-wide run.** A pack-declared ceiling may queue a large
  multi-agent sweep. Accepted deliberately (S6): an unbounded fan-out is a cost- and blast-radius hazard; a
  domain that needs a wider graph raises its pack's ceiling — a reviewable config change, not a runtime
  surprise.

---

## 8. Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Bake a specific engine (Temporal) into `core/` directly** — skip the adapter | **Rejected.** Re-introduces the exact hot-path lock-in the port exists to prevent (R7/O7); an Isolated tenant that cannot run that engine in-boundary would be stranded. The port + tier-selected adapters cost one indirection and buy substrate optionality. |
| **Exactly-once *delivery* from the substrate** (rely on the broker's dedup) | **Rejected as the primary mechanism.** Exactly-once delivery across crashes is not generally achievable; depending on it is fragile. Idempotent, key-addressed *effects* (S2, §4) make at-least-once delivery *safe* — the robust discipline the ingestion plane already proves. |
| **One shared substrate for all tenants, no per-tenant namespace** | **Rejected.** Violates S3/R4 — a filtering bug in a shared workflow namespace is a cross-tenant blast radius on the orchestration plane. Per-tenant namespace/queue (or dedicated engine, Isolated) is the two-control isolation reused. |
| **Managed third-party durable-workflow SaaS for the Isolated tier** | **Rejected for Isolated.** Its run state (question + retrieved-item identifiers) would egress the boundary — an S5 violation, the orchestration analogue of routing `pii` to a `managed_private` model track. Permitted for Shared `public`/`internal` where the [Models Track-B](../models/00-model-hosting-and-serving.md) logic already allows a contractually-private managed dependency. |
| **Unbounded, engine-native fan-out** (let the engine parallelize freely) | **Rejected.** Fan-out is a budget + blast-radius lever (S6/R5); the ceiling must be a pack-declared, auditable fact, not an engine default. The engine parallelizes *within* the declared ceiling. |
| **No reserved capacity — autoscale everything** | **Rejected.** A P0 revocation re-answer autoscaling from cold is already a freshness/security breach. Reserve safety-class run capacity; autoscale bulk. |

---

## 9. Future scalability

- **A new substrate** (a managed durable-workflow service, an on-prem sovereign engine, a lighter
  queue+state build for a tiny tenant) slots in as **one adapter** (§6) — routing and gates unchanged, exactly
  as a new vector engine or `hosting_posture` slots in. The lock-in stays bounded to that adapter (R7).
- **A new tenant tier** (e.g. an air-gapped sovereign tier) is a **placement-map + adapter-selection** entry,
  not a loop change — the substrate follows content residency (S5) by the same rule that already pins region.
- **A future *action-taking* platform** (write-back / transaction execution, today out of the
  [read-plane-mirror scope](../packs/audit/00-audit-pack.md)) reuses this substrate unchanged: a write is just
  a non-idempotent activity, and S2's idempotency-key discipline is *exactly* what makes at-least-once safe
  for writes too. The governance gate gains write-risk policies; the execution plane does not change.
- **Multi-region / follow-the-sun runs** (a run that spans residency-compatible regions) are a substrate
  routing feature *within a residency class* — never across one (S5, [Deployment §7.2](../deployment/00-deployment-topology.md#72-region--residency-routing)).
- **The `core/` distributed adapter** is the concrete next engineering target *if and when* a tenant's scale
  demands it — but note it is **out of `core/` by design** (the in-process adapter is the permanent
  small-tenant/test backend). Building it is a deployment-driven decision gated on measured need (fan-out
  depth, run durability requirement, crash-resume SLA), not a standing obligation. The paper design here is
  the de-risking; the code is pulled by demand.

---

## Related

- [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md) — the orchestration posture this
  substrate implements (the decision this doc *projects*, not re-opens).
- [Orchestration §4.4, §5, §10](00-agent-orchestration.md) — the port, the distributed run, and the sizing
  hand-off this document receives.
- [`core/execution.py`](../../core/execution.py) — the built port + in-process adapter + `DECISION_VERBS`
  grep-invariant + `RunSpec` this adapter implements.
- [Deployment §6, §7](../deployment/00-deployment-topology.md) — the reserved-capacity + versioned
  pricing/envelope manifest this sizing feeds into.
- [Models §2–§4](../models/00-model-hosting-and-serving.md) — the in-boundary-vs-contractually-private routing
  rule reused for substrate placement (S5).
- [ADR-0011](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md) — the at-least-once +
  idempotent-effect discipline (S2) reused from the ingestion plane.
- [ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) /
  [ADR-0010 §3.4](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7) — the
  "commodity behind a port" pattern, reused a fourth time.
