# Engineering Track — `platform/` → `core/` Reconciliation Plan

> **Status:** Seeded (Cycle 24) · **Executed (Cycle 25)** — Front A (WP-A1/A2/A5/A3 + G4)
> and all of Front B (WP-B1–B4) are implemented and green; see the
> [Cycle-25 implementation report](01-cycle-25-implementation-report.md). Remaining:
> **WP-A4** (re-express `run()` against the port) + **WP-C1** (CI coverage gate).
>
> This is the **engineering projection** of the architecture
> docs, not a new architectural decision. Every open architecture question (Q#1–Q#7) is
> closed; the only remaining weighted gap is *code-reconciliation*
> ([NEXT_STEPS §0.1](../NEXT_STEPS.md)). This document is that gap's implementation
> blueprint: it turns two fully-specified paper targets —
> [ADR-0017 (pack-load SPI)](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) and
> [ADR-0019 (orchestration posture)](../architecture/adr/ADR-0019-agent-orchestration-posture.md) —
> into a **sequenced, test-first work plan grounded in the actual `core/` template.**
> It adds **no ADR** (it introduces no cross-component decision — it *discharges* two).

---

## 0. Why this document exists

The platform has 12 seeded architecture surfaces and 19 ADRs. What it does **not** yet have
is a single place that answers the coding cycle's only real question: *given the `core/`
template as it stands today, what exactly do we build, in what order, and how do we prove
each step is safe before the next?*

Two ADRs name their `core/` implementation as "handed to a later cycle" but neither is an
implementation plan:

- **[ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md)** specifies *what a
  loader must guarantee* (transactional, fail-closed, six validators). It does not say which
  `core/` module holds it, what its Python surface is, or which unit test proves a
  floor-loosening bundle is rejected.
- **[ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md)** specifies the
  *posture* (extend `core/`, adopt an `ExecutionBackend` port). It does not say that
  [`AgentOrchestrator.run`](../../core/orchestrator.py) **today does not call**
  [`WorkerRegistry`](../../core/workers.py) or [`HandoffRouter`](../../core/handoff.py) at
  all — the primitives exist, are configured, and are unit-tested (62 tests green), but the
  loop never invokes them.

This document closes that gap. It is deliberately **code-shaped**: module names, function
signatures, test names, and a definition-of-done per work package.

### Why / How / Trade-offs / Alternatives / Future scalability (doc contract)

- **Why:** a coding cycle needs a build order that keeps the tree green at every step; the
  ADRs give the destination, not the road. Writing the road down once prevents the coding
  cycle from re-deriving it under time pressure and drifting from the ratified gates.
- **How:** a ground-truth audit of `core/` (§1), a gap ledger against the two ADRs (§2), two
  target designs with Python surfaces (§3, §4), and a sequenced TDD work-package list with
  falsifiability checks (§5–§7).
- **Trade-offs:** a plan can go stale against the code it describes. Mitigated by anchoring
  every claim to a named file/line-shape and by making the plan's own consistency a
  [checklist item](#8-definition-of-done). We accept some duplication of the ADRs' *rationale*
  in exchange for a self-contained coder brief.
- **Alternatives:** (a) let the coding cycle read the ADRs directly — rejected: the
  `WorkerRegistry`-not-wired fact is invisible from the docs and only surfaces by reading
  `core/`; a coder would rediscover it late. (b) put this in an ADR — rejected: it is not a
  decision, and ADRs are for cross-component *choices*, not build orders.
- **Future scalability:** the same shape (audit → gap → target → sequenced WPs) is the
  template for every later `platform/`→`core/` reconciliation (a new store adapter, a new
  Gateway backend). This is the first instance of a reusable engineering-bridge pattern.

---

## 1. Ground truth — what `core/` is today

Audited Cycle 24. The template already implements the **single-process** form of the
decision plane. The loop in [`AgentOrchestrator.run`](../../core/orchestrator.py) is, in order:

```
context.build()
  → planner.draft(task)                         # Plan of typed steps
  → governance.allow(task)          [GATE 1]    # task-level admission
  → for step in plan.steps:
        governance.allow(step, risk=…)  [GATE 1']  # per-step risk gate
        subagents.select / subagents.run           # optional sub-agent
        dispatcher.dispatch(step, tools)  [SIDE EFFECT]  # the only effect site
  → verifier.verify(joined outputs) [GATE 5]    # single answer gate + self-repair
  → memory.save(run) + runtime.write_heartbeat
```

Mapping the [five choke points (ADR-0019 §5)](../architecture/adr/ADR-0019-agent-orchestration-posture.md)
onto this code:

| # | Gate (ADR-0019) | Where it lives today | Status |
|---|-----------------|----------------------|--------|
| 1 | **Governance gate** | `governance.allow(...)` — task + per-step | ✅ present, called |
| 2 | **Model Gateway** | via `brain.evaluate` in `verifier`; planner/subagents call the model | ⚠️ present but **not** yet a single explicit gateway seam in `core/` |
| 3 | **Permission filter** | (retrieval plane — not in the template's toy loop; lives in `platform/` storage/rag design) | ⛔ out of the template's scope; N/A to this loop |
| 4 | **Tool scope** (`WorkerRegistry`) | `core/workers.py` — **fully built + unit-tested** | ❌ **NOT called by `orchestrator.run`** |
| 5 | **Verifier answer gate** | `verifier.verify(...)` — single, with self-repair | ✅ present, called |

Plus the multi-agent primitive:

| Primitive | Where | Status |
|-----------|-------|--------|
| **`HandoffRouter`** (allowlisted, schema-validated agent→agent transfer) | `core/handoff.py` — **fully built + unit-tested** (`test_handoff.py`, 24 tests) | ❌ **NOT called by `orchestrator.run`** |
| **`WorkerRegistry`** (per-agent tool scope) | `core/workers.py` — **fully built + unit-tested** (`test_workers.py`, 23 tests) | ❌ not wired into the loop |
| **`check.py` gate** | `tools/check.py` — validates `manifest.json`/`config.json`; enforces **exactly-one-writer** leaf-write + handoff-allowlist-⊆-workers | ✅ present, green (`test_check.py`, 11 tests) |

**The single most load-bearing finding:** `core/orchestrator.py` imports
`ContextBuilder, Dispatcher, GovernancePolicy, MemoryStore, Planner, SubagentManager,
RuntimeStore, Verifier` — and **neither `WorkerRegistry` nor `HandoffRouter`**. So the two
gates the platform most wants un-bypassable (tool-scope O3/O5, and handoff O4) are *coded and
tested but structurally inert*. This is precisely the
[Cycle 2c open item](../NEXT_STEPS.md) ("available + configured + unit-tested, but not yet
called by the loop") and the concrete meaning of "re-host the primitives" in ADR-0019.

Baseline to preserve: **62 tests pass** (`pytest -q`), `tools/check.py` green.

---

## 2. Gap ledger — ADR requirement vs. code reality

| # | Required by | Requirement | Today | Gap class |
|---|-------------|-------------|-------|-----------|
| G1 | ADR-0019 §5.3 | Each step runs under the acting agent's `WorkerRegistry` tool scope | `dispatcher.dispatch` gets the *full* `tools` dict; no scoping | **Wire-in** |
| G2 | ADR-0019 §5.4 | A `HandoffRequest` in a step's output is validated (allowlist+schema+size) before control transfers | Loop never inspects output for handoffs | **Wire-in** |
| G3 | ADR-0019 §4.4 | Durable execution behind an `ExecutionBackend` **port with no decision method** | No port exists; loop is a synchronous `for` | **New port + adapter** |
| G4 | ADR-0019 §5.1 | A run is keyed `(tenant_id, request_id)`, resumable | `run()` takes a bare `task`; no run identity | **New concept** |
| G5 | ADR-0006 follow-up ([NEXT_STEPS §6 Cycle 2c.3](../NEXT_STEPS.md)) | High-risk **hard block runs *before*** the autonomy shortcut; escalation is a deterministic policy decision, not an LLM `needs_human` flag | Order/ownership to be verified in `governance.py` | **Harden** |
| G6 | ADR-0017 | A pack loads via RESOLVE→VALIDATE→DRY-RUN→COMMIT→ACTIVATE; six validators; §0 ledger machine-checked | No loader module exists | **New module** |
| G7 | ADR-0017 | A **floor-loosening bundle fails VALIDATE in a unit test**, not review | Not testable — no loader | **New test class** |
| G8 | ADR-0017 §versioning | Per-tenant `pack_version` pinning; fail-closed unload (a live label blocks its own removal) | N/A | **New module** |

Two independent build fronts fall out of this ledger, matching
[NEXT_STEPS Cycle 24](../NEXT_STEPS.md):

- **Front A — Orchestrator re-host** (G1, G2, G3, G4, G5): wire the inert primitives into the
  loop, then lift the loop onto a durable port.
- **Front B — Pack-load loader** (G6, G7, G8): a new control-plane module with a
  machine-checked ledger and a fail-closed validator suite.

They are **independent** and can proceed in parallel; Front A is higher leverage (it makes an
existing, tested gate actually enforce) and lower risk (no new dependency), so it sequences first.

---

## 3. Target A — orchestrator re-host

### 3.1 Design principle

**Wire before you distribute.** The re-host is two moves that must not be conflated:

1. **In-process wiring (G1, G2, G5-harden)** — make the loop *call* `WorkerRegistry` and
   `HandoffRouter`. This is pure `core/` work, no new dependency, and it makes two ratified
   gates real. It is independently valuable even if distribution never ships.
2. **Port extraction (G3, G4)** — introduce the `ExecutionBackend` port and re-express the
   loop against it, with an in-memory adapter as the default. Distribution (a Temporal-class
   adapter) is then a *second adapter*, never a caller change.

Doing (1) first means every safety gate is enforced *before* the plumbing changes — so a
distribution bug can only affect availability, never bypass a gate (the ADR-0019 §7 trade-off,
realized in build order).

### 3.2 In-process wiring (WP-A1, WP-A2, WP-A5)

**`AgentOrchestrator.__init__`** gains two optional collaborators, defaulted from the manifest
(same pattern as `planner`/`verifier`), so the change is additive and existing callers are
unaffected:

```python
def __init__(self, project_root, *, planner=None, dispatcher=None,
             verifier=None, governance=None,
             workers: WorkerRegistry | None = None,      # NEW
             handoffs: HandoffRouter | None = None):     # NEW
    ...
    self.workers  = workers  or load_registry(self._manifest())
    self.handoffs = handoffs or load_router(self._manifest())
```

**Tool scoping (G1).** Before `dispatcher.dispatch`, the loop resolves the acting worker for
the step and narrows the tools:

```python
scoped = self.workers.filter_tools(acting_worker, tools)      # core/workers.py, exists
ok, reason = self.workers.check_permission(acting_worker, step.tool)
if step.tool and not ok:
    return RunResult(success=False, governance=…, metadata={"status": "tool_scope_blocked", "reason": reason})
dispatch = self.dispatcher.dispatch(step, tools=scoped)        # scoped, not full
```

`filter_tools` and `check_permission` already exist and are unit-tested — the wiring is the
deliverable, not the mechanism. *Where does `acting_worker` come from?* From the step's
sub-agent selection (`subagents.select`) mapped to a worker role, defaulting to the least-privileged
reader when unmapped (fail-closed).

**Handoff validation (G2).** After a step produces output, the loop offers it to the router;
an invalid handoff is refused, not improvised:

```python
req = self.handoffs.extract(dispatch.output) or self.handoffs.extract_from_plan(plan_dict)
if req:
    ok, reason = self.handoffs.validate(req)     # allowlist + payload bound, exists
    if not ok:
        return RunResult(success=False, metadata={"status": "handoff_refused", "reason": reason})
    # enqueue the target step carrying the run context (tenant, user, budget)
```

**Governance-order hardening (G5).** Verify in `core/governance.py` that the **high-risk hard
block is evaluated before** any `autonomy_level == "max"` shortcut, and that escalation is a
deterministic branch on policy, not a trust of an LLM-produced `needs_human` boolean. If the
current order lets `max` autonomy skip the hard block, reorder so the hard block is
unconditional (this is the ADR-0006 fail-closed default made structural). `check.py` already
*warns* that `autonomy_level: max` is fail-open — this WP makes the warning's risk unreachable
for the hard-block class.

### 3.3 The `ExecutionBackend` port (WP-A3, WP-A4)

New module `core/execution.py`. The port surface is exactly
[ADR-0019 §4.4](../architecture/adr/ADR-0019-agent-orchestration-posture.md#44-what-we-do-adopt--the-executionbackend-port)
— **no method makes a decision**:

```python
from typing import Protocol, Sequence

class ExecutionBackend(Protocol):
    def start_run(self, run_spec: "RunSpec", *, tenant: str, idempotency_key: str) -> "RunHandle": ...
    def schedule_step(self, run: "RunHandle", step: "Step", *, idempotency_key: str) -> "StepHandle": ...
    def await_steps(self, run: "RunHandle", steps: Sequence["StepHandle"]) -> list["StepResult"]: ...
    def signal(self, run: "RunHandle", name: str, payload: dict) -> None: ...
    def timer(self, run: "RunHandle", seconds: float) -> None: ...
    def resume(self, run_id: str) -> "RunHandle": ...
    # NOTE: no plan(), no select_tool(), no call_model(), no answer(). By construction.
```

Default adapter `InProcessExecutionBackend` — a synchronous, dict-backed implementation that
makes `start_run`/`schedule_step`/`await_steps` run the step immediately and store results in
memory. This lets `orchestrator.run` be re-expressed against the port **with identical
observable behaviour** (the existing 62 + new tests stay green), proving the port is a faithful
seam. A distributed adapter (Temporal-class) is a later, out-of-`core/`-scope deliverable that
implements the same Protocol.

**Falsifiability guarantee (structural):** the Protocol has no decision method, so a
`grep` test in CI can assert the port module names none of `{plan, tool, model, answer,
verify, allow}` in its method set — the "no gate is expressible through the port" invariant
becomes a machine check, mirroring the
[`VectorIndex` no-unfiltered-method rule](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7).

### 3.4 Run identity (G4)

A `RunSpec`/`RunHandle` dataclass keyed `(tenant_id, request_id)`. `orchestrator.run` gains an
optional `tenant`/`request_id`; when absent it synthesizes a local single-tenant run so the CLI
path is unbroken. This is the minimal carrier for the run context ADR-0019 §5.1 requires;
budget/audit debiting is stubbed to the existing `memory.save` until the governance cost plane
is wired.

---

## 4. Target B — pack-load loader

### 4.1 Module map

New package `core/packs/`:

| Module | Responsibility | ADR-0017 stage |
|--------|----------------|----------------|
| `bundle.py` | Parse + verify a **signed, content-addressed** pack bundle (data-only; a connector is *referenced*, never shipped) | RESOLVE |
| `validators.py` | Six validators, one per section, each asserting `section ⊆ extension_point` | VALIDATE |
| `ledger.py` | Machine-check the §0 horizontal-change ledger == `"none, all additive"`; else route to the human-ADR gate | VALIDATE |
| `dryrun.py` | Compute the install plan without committing; runnable in CI as a release veto | DRY-RUN |
| `loader.py` | Orchestrate the staged pipeline; **all-or-nothing** commit | COMMIT (atomic) |
| `activation.py` | Tenant-scoped activation + per-tenant `pack_version` pinning + fail-closed unload | ACTIVATE |

### 4.2 The one invariant, six checks

Each validator checks a pack section is a **subset / tightening** of its horizontal extension
point — the [ADR-0016 tighten-only rule](../architecture/adr/ADR-0016-domain-pack-contract.md)
made executable:

| § | Validator | Extension point it must fit ⊆ |
|---|-----------|-------------------------------|
| §1 | ACL fixtures pass the conformance suite | [permission conformance gate](../permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate) |
| §2 | Every new label ∈ the closed grammar | [classification schema](../metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3) |
| §3 | Matrix deltas are tighten-only | [label→action matrix](../governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen) |
| §4 | Compliance-map rows are additive | governance compliance map |
| §5 | Eval fixtures reference only approved models | [model registry](../governance/00-governance-and-audit.md#8-g6--model-governance) |
| §6 | Agent graph ⊆ allowlisted handoff targets | `HandoffRouter` allowlist (the ADR-0019 additive validator) |

**Safe by construction, not by decision:** the loader's only verbs are *subset-installs into
fail-closed extension points*. There is no verb that can widen — a widening §3 delta composes
to a no-op under most-restrictive-wins; an unregistered §2 value is rejected by the closed
grammar; §6 reuses the existing `check.py` "allowlist ⊆ workers" logic. The gate is the belt;
the closed extension points are the suspenders.

### 4.3 The falsifiability test (G7) — the acceptance criterion

The **defining unit test** of this target:

```python
def test_floor_loosening_bundle_fails_validate():
    bundle = make_bundle(matrix_delta={"pii": "allow"})   # loosens a floor
    result = Loader(fixtures).validate(bundle)
    assert not result.ok
    assert result.rejected_by == "§3 tighten-only validator"   # rejected by CODE, not review
```

If this test can be made to pass (a loosening bundle *is* rejected by the validator, not by a
human), G7 is discharged and ADR-0017's headline claim ("structurally rejected by the loader")
is proven in CI. A companion test asserts a **partial** install is unrepresentable (COMMIT is
atomic): injecting a failure into validator #4 must leave *zero* of the six sections installed.

### 4.4 No new hot path

The loader writes only into stores that already exist (label schema, policy store, conformance
corpus, catalog). Runtime consumers (retrieval, verifier, `HandoffRouter`) see only *a larger
closed vocabulary + a stricter matrix + a longer allowlist* — all already handled totally. That
invisibility is the proof the loader is additive; its own §0-equivalent ledger is
*"none, all additive."*

---

## 5. Sequenced work packages (TDD, keep the tree green)

Ordered by leverage × safety. Each WP is **red → green → refactor**, ends with the full suite +
`tools/check.py` green, and never lands a broken tree.

| WP | Front | Deliverable | Discharges | Gate to advance |
|----|-------|-------------|------------|-----------------|
| **A1** | A | Wire `WorkerRegistry` into the loop; step tools are scoped; out-of-scope tool → `tool_scope_blocked` | G1 | new `test_orchestrator_tool_scope.py` green; 62 baseline green |
| **A2** | A | Wire `HandoffRouter` into the loop; invalid handoff → `handoff_refused` | G2 | `test_orchestrator_handoff.py` green |
| **A5** | A | Governance-order hardening: hard block before autonomy shortcut; deterministic escalation | G5 | `test_governance_order.py` green (a `max`-autonomy high-risk task is still hard-blocked) |
| **A3** | A | `core/execution.py` port + `InProcessExecutionBackend`; CI grep-invariant (no decision method) | G3 | `test_execution_port.py` green; behaviour parity (all prior tests green) |
| **A4** | A | Re-express `run()` against the port; `RunSpec/RunHandle` keyed `(tenant, request_id)` | G4 | full suite green, CLI path unbroken |
| **B1** | B | `core/packs/bundle.py` — parse + signature/content-address verify | G6 (partial) | `test_pack_bundle.py` green |
| **B2** | B | `validators.py` (six) + `ledger.py`; **the floor-loosening test** | G6, **G7** | `test_pack_validate.py::test_floor_loosening_bundle_fails_validate` green |
| **B3** | B | `loader.py` atomic COMMIT + `dryrun.py` CI veto | G6 | `test_pack_atomic.py` (partial-install unrepresentable) green |
| **B4** | B | `activation.py` — tenant-scoped, `pack_version` pin, fail-closed unload | G8 | `test_pack_activation.py` green |
| **C1** | — | Finish the v3.0 test port; enforce `--cov=core --cov-fail-under=80` in CI (GitHub Actions) | [Cycle 2c.2](../NEXT_STEPS.md) | coverage gate green on CI |

**Recommended order:** A1 → A2 → A5 → B1 → B2 → B3 → (A3 → A4) → B4 → C1. Rationale: A1/A2/A5
turn *already-built, inert* gates live for the least effort and highest safety yield; B1–B3
deliver the loader's provable core (including G7, the marquee acceptance test) without waiting
on distribution; A3/A4 (the port) can slot in once wiring is proven; C1 locks the coverage
floor last so it gates the whole.

---

## 6. Test matrix (what "done" is measured by)

| Class | Asserts | New test file |
|-------|---------|---------------|
| **Tool-scope negative** | a reader worker calling `file_write` is blocked *in the loop*, not just in the registry | `test_orchestrator_tool_scope.py` |
| **Handoff negative** | an unlisted / oversized / malformed handoff is refused by the loop | `test_orchestrator_handoff.py` |
| **Single-answer** | no sub-agent output reaches the caller without the one `verifier` pass | `test_orchestrator_answer_gate.py` |
| **Governance order** | a high-risk step is hard-blocked even under `autonomy_level: max` | `test_governance_order.py` |
| **Port purity** | the `ExecutionBackend` Protocol exposes no decision method (grep-invariant) | `test_execution_port.py` |
| **Behaviour parity** | re-hosting onto the in-process backend changes no observable output | existing 62 stay green |
| **Pack loosening (marquee)** | a floor-loosening bundle fails VALIDATE by code | `test_pack_validate.py` |
| **Pack atomicity** | a mid-validate failure installs zero sections | `test_pack_atomic.py` |
| **Pack unload** | a live label blocks its own removal (fail-closed unload) | `test_pack_activation.py` |

These map 1:1 onto the two ADRs' own falsifiability checks
([ADR-0019 §](../architecture/adr/ADR-0019-agent-orchestration-posture.md):
*can a sub-agent answer without the gate / call an out-of-scope tool / hand off to an unlisted
target? — no, structurally*; [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md):
*no-code-deploy load? floor-loosening pack structurally rejected? — yes to both*). Turning each
ADR check into a named test is how the paper claim becomes an enforced one.

---

## 7. Trade-offs, alternatives, future scalability (per work-package theme)

- **Wire-in before port (A1/A2 before A3/A4).** *Trade-off:* the loop is touched twice (once to
  call the primitives, once to re-express against the port). *Alternative:* extract the port
  first and wire the primitives inside it — rejected: it couples the low-risk, high-value gate
  wiring to the new-dependency port work, so a port bug would block a shippable safety fix.
  *Future:* the port, once in, absorbs a distributed adapter with no further loop change.
- **In-process adapter as default.** *Trade-off:* it is not the production substrate. *Alt:*
  build the Temporal adapter directly — rejected: it drags a heavy dependency into `core/` and
  makes tests slow/flaky. *Future:* the in-process adapter stays forever as the unit-test and
  small-Isolated-tenant backend; the distributed one is additive.
- **Loader as data-only.** *Trade-off:* a pack cannot ship read-path code, so a genuinely new
  connector is still a platform PR through the connector gate. *Alt:* let packs ship code —
  rejected: it turns "load a pack" into "run untrusted code on the retrieval path," the exact
  risk ADR-0017 exists to foreclose. *Future:* a pack marketplace ships the same signed
  content-addressed bundle unchanged.
- **Coverage gate last (C1).** *Trade-off:* early WPs land before the 80% floor is enforced.
  *Alt:* enforce coverage from A1 — rejected: it would block the first safety wiring on
  backfilling legacy tests. *Future:* once C1 lands, every later WP inherits the floor.

---

## 8. Definition of done

The engineering track is complete when:

1. `AgentOrchestrator.run` **calls** `WorkerRegistry` and `HandoffRouter` — the two inert gates
   are live and covered by negative tests (G1, G2).
2. The high-risk hard block is unconditional w.r.t. the autonomy shortcut (G5).
3. `core/execution.py` exposes an `ExecutionBackend` Protocol with **no decision method**, a
   default in-process adapter, and behaviour parity with the pre-port loop (G3, G4).
4. `core/packs/` loads a bundle through RESOLVE→VALIDATE→DRY-RUN→COMMIT→ACTIVATE, and
   **`test_pack_validate.py::test_floor_loosening_bundle_fails_validate` passes** (G6, G7);
   partial install is unrepresentable (atomicity); unload is fail-closed (G8).
5. CI enforces `--cov=core --cov-fail-under=80`; `tools/check.py` and the full suite are green.
6. **The tree is never pushed broken** — every WP is a green commit.

Until then, the platform is *architecturally complete and code-partially-reconciled*: the
`platform/` docs are sufficient to build from, and this plan is the build order.

---

## Related

- [ADR-0017 — Runtime pack-load SPI](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) ·
  [packs/01-pack-load-spi.md](../packs/01-pack-load-spi.md) — Target B's specification.
- [ADR-0019 — Agent orchestration posture](../architecture/adr/ADR-0019-agent-orchestration-posture.md) ·
  [orchestration/00-agent-orchestration.md](../orchestration/00-agent-orchestration.md) — Target A's specification.
- [ADR-0002 — Reuse template core](../architecture/adr/ADR-0002-reuse-existing-template-core.md) — the
  "concepts transfer, implementation re-hosts" bet this plan discharges.
- [NEXT_STEPS §6 Cycle 24 + Cycle 2c](../NEXT_STEPS.md) — the backlog items this plan sequences.
- `core/orchestrator.py`, `core/workers.py`, `core/handoff.py`, `core/governance.py`,
  `tools/check.py` — the audited ground truth.
