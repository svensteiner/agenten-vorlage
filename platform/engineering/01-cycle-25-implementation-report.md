# Engineering Track — Cycle 25 Implementation Report

> **Status:** Implemented (Cycle 25, 2026-07-06). This is the **execution record**
> of the [reconciliation plan](00-core-reconciliation-plan.md): the first coding
> cycle on the `platform/`→`core/` bridge. It turns the two ratified-but-inert
> gates live, adds the `ExecutionBackend` port, and lands the full pack-load
> loader — the marquee acceptance test included. It adds **no ADR** (it discharges
> [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) and
> [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md)).

---

## 0. Headline

The Cycle-24 audit's load-bearing finding — **`core/orchestrator.py` called neither
`WorkerRegistry` nor `HandoffRouter`, so the tool-scope (O3/O5) and handoff (O4)
gates were coded-and-tested yet structurally inert** — is closed. Both gates are
now **called in the run loop** and covered by negative tests. The pack-load loader
exists as `core/packs/` and **`test_pack_validate.py::test_floor_loosening_bundle_fails_validate`
passes**: a floor-loosening bundle is rejected by code, not by review.

- **Test count:** 62 baseline → **131 green** (+69), `tools/check.py` exit 0.
- **Coverage (built/changed modules):** `core/packs/*` 96–100 %, `core/execution.py`
  96 %, `core/orchestrator.py` 80 %, `core/governance.py` hard-block path covered —
  all at or above the ADR-0017/plan **80 % floor**.
- **Tree never broken:** each work package kept the full suite green.

---

## 1. What was built (by work package)

### Front A — orchestrator re-host (the inert gates made live)

| WP | Gap | Deliverable | Where | Test |
|----|-----|-------------|-------|------|
| **A1** | G1 | Tool-scope gate wired into `run()`; the acting worker's `WorkerRegistry` scope is enforced *in the loop*; an out-of-scope tool returns `status: tool_scope_blocked` | [`core/orchestrator.py`](../../core/orchestrator.py) (`_acting_worker`, pre-dispatch check + `filter_tools`) | `test_orchestrator_tool_scope.py` (5) |
| **A2** | G2 | Handoff gate wired in; a handoff in a step's output is validated (allowlist + payload bound) **before** control could transfer; invalid → `status: handoff_refused` | `core/orchestrator.py` (post-dispatch `HandoffRouter.extract`/`validate`) | `test_orchestrator_handoff.py` (4) |
| **A5** | G5 | Governance-order hardening: a **deterministic** destructive/irreversible hard-block class is evaluated **before** the `autonomy_level: max` shortcut, unconditional unless an explicit `hard_block_on_high_risk: false` opt-out | [`core/governance.py`](../../core/governance.py) (`_matched_hard_block_terms`, `_hard_block_enabled`, reordered `allow`) | `test_governance_order.py` (7) |
| **A3** | G3 | `ExecutionBackend` **Protocol with no decision method** + default `InProcessExecutionBackend`; the port-purity grep-invariant is a test | [`core/execution.py`](../../core/execution.py) | `test_execution_port.py` (8) |
| **G4** | G4 | Run identity: `run()` accepts `tenant`/`request_id`, synthesizes a `RunSpec` keyed `(tenant_id, request_id)` when absent (CLI path unbroken) | `core/orchestrator.py` (`RunSpec`, `_run_spec`) | `test_orchestrator_answer_gate.py::TestRunIdentity` (3) |

The **single-answer gate** (ADR-0019 O1) was already structurally single; a test now
pins it (`test_orchestrator_answer_gate.py` — a failing verifier makes a produced
output *not* ship).

### Front B — pack-load loader (`core/packs/`)

| WP | Gap | Module | Stage | Test |
|----|-----|--------|-------|------|
| **B1** | G6 | [`bundle.py`](../../core/packs/bundle.py) — signed, content-addressed, data-only bundle; `verify_bundle` checks content-address **and** HMAC signature | RESOLVE | `test_pack_bundle.py` (9) |
| **B2** | G6, **G7** | [`validators.py`](../../core/packs/validators.py) (six validators, one tighten-only invariant) + [`ledger.py`](../../core/packs/ledger.py) (§0 machine-check → human-ADR route) | VALIDATE | `test_pack_validate.py` (18) |
| **B3** | G6 | [`dryrun.py`](../../core/packs/dryrun.py) (install plan, no mutation) + [`loader.py`](../../core/packs/loader.py) (atomic COMMIT; partial install unrepresentable) | DRY-RUN + COMMIT | `test_pack_atomic.py` (5) |
| **B4** | G8 | [`activation.py`](../../core/packs/activation.py) — tenant-scoped activation, `pack_version` pinning, **fail-closed unload** (a live label blocks its own removal) | ACTIVATE | `test_pack_activation.py` (8) |

---

## 2. Test matrix — the ADR falsifiability checks, now named tests

Each row is one ADR falsifiability check turned into an enforced test (plan §6).

| Class | Asserts | Test | Result |
|-------|---------|------|:------:|
| Tool-scope negative | a `reader` calling `notify`/`file_write` is blocked *in the loop* | `test_orchestrator_tool_scope.py` | ✅ |
| Handoff negative | an unlisted / oversized handoff is refused by the loop | `test_orchestrator_handoff.py` | ✅ |
| Single-answer | a produced output does not ship without the one verifier pass | `test_orchestrator_answer_gate.py` | ✅ |
| Governance order | a destructive step is hard-blocked even under `autonomy_level: max` | `test_governance_order.py` | ✅ |
| Port purity | the `ExecutionBackend` Protocol exposes **no** decision verb (grep-invariant) | `test_execution_port.py` | ✅ |
| **Pack loosening (marquee)** | a floor-loosening bundle **fails VALIDATE by code** (`rejected_by == "§3 tighten-only validator"`) | `test_pack_validate.py` | ✅ |
| Pack atomicity | a mid-VALIDATE or mid-COMMIT failure installs **zero** sections | `test_pack_atomic.py` | ✅ |
| Pack unload | a live label blocks its own removal (fail-closed unload) | `test_pack_activation.py` | ✅ |

The two ADRs' own checks now resolve as *tests*, not prose:
[ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md) — *can a
sub-agent call an out-of-scope tool / hand off to an unlisted target / answer
without the gate? → **no**, by test*; [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md)
— *is a floor-loosening pack structurally rejected? → **yes**, by test*.

---

## 3. Notable design decisions taken during implementation

- **Tool-scope applies to sub-agents, not to orchestrator-direct action.** When no
  sub-agent is selected and no explicit `step.metadata["worker"]` is set,
  `_acting_worker` returns `None` and the loop skips the scope check — the
  orchestrator itself is acting and governance is the gate there, consistent with
  the existing `allow_write` "No subagent — orchestrator write allowed" semantics.
  This makes least-privilege enforcement *per-agent* (the ADR-0019 intent) without
  over-blocking the trusted single-actor path.
- **The hard block re-derives risk deterministically.** It does not trust the
  planner's `requires_human` flag (which can be LLM-set); it re-matches a fixed
  destructive/irreversible vocabulary in `core/governance.py`. This is the ADR-0006
  "escalation is a deterministic policy decision" requirement made structural.
  *Behavior change:* a destructive task now hard-blocks **even under the template's
  default `autonomy_level: max`** — the intended fail-closed posture; an explicit
  `hard_block_on_high_risk: false` restores full autonomy for that class.
- **The `ExecutionBackend` carries opaque activities.** `Step.activity` is a
  caller-supplied callable the port never inspects — the *what* stays in the
  decision plane, the *when/whether/retry* moves to the execution plane. A
  distributed adapter carries a serializable handle instead; the in-process adapter
  runs it immediately, giving behaviour parity.
- **The loader is data-only.** A bundle *references* a connector, never ships one;
  new connector code stays a platform PR through the connector gate. "Load a pack"
  is always "install validated config," never "run untrusted code on the retrieval
  path."

---

## 4. Definition-of-done status (plan §8)

| # | Criterion | Status |
|---|-----------|:------:|
| 1 | `run()` **calls** `WorkerRegistry` and `HandoffRouter`, covered by negative tests | ✅ |
| 2 | High-risk hard block unconditional w.r.t. the autonomy shortcut | ✅ |
| 3 | `ExecutionBackend` Protocol with no decision method + in-process adapter + purity test | ✅ (port + adapter) · ⏳ *loop not yet re-expressed against the port — WP-A4* |
| 4 | Loader runs RESOLVE→VALIDATE→DRY-RUN→COMMIT→ACTIVATE; floor-loosening test passes; atomicity; fail-closed unload | ✅ |
| 5 | CI enforces `--cov=core --cov-fail-under=80`; `check.py` + suite green | ⏳ *coverage measured 80–100 % on built modules; CI gate config = WP-C1* |
| 6 | Tree never pushed broken — every WP a green commit | ✅ |

**Remaining (handed to Cycle 26):**
- **WP-A4** — re-express `run()` against the `InProcessExecutionBackend` (behaviour
  parity; the port + `RunSpec` already exist, so this is a mechanical seam swap).
- **WP-C1** — add the `--cov=core --cov-fail-under=80` gate to `pytest.ini`/CI
  (GitHub Actions), after backfilling coverage on the legacy `planner`/`brain`/
  `subagents` LLM paths so the whole-`core` floor holds (today the *built* modules
  clear it; the legacy LLM modules would need mocked-model tests first).

---

## 5. Files

**New:** `core/execution.py`; `core/packs/{__init__,bundle,validators,ledger,dryrun,loader,activation}.py`;
`tests/test_execution_port.py`, `tests/test_pack_{bundle,validate,atomic,activation}.py`,
`tests/test_orchestrator_{tool_scope,handoff,answer_gate}.py`, `tests/test_governance_order.py`.
**Changed:** `core/orchestrator.py` (wiring + run identity), `core/governance.py` (hard-block order).

## Related

- [00-core-reconciliation-plan.md](00-core-reconciliation-plan.md) — the plan this executes.
- [ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) · [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md) — discharged here.
