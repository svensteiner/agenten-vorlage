# engineering/ — the `platform/` → `core/` reconciliation track

This folder owns the **engineering projection** of the architecture: how the ratified
`platform/` design is realized in the `core/` code template. It holds no new architectural
decisions — it *discharges* existing ADRs into a build plan.

It exists because every open architecture question (Q#1–Q#7) is closed and the only remaining
weighted gap ([NEXT_STEPS §0.1](../NEXT_STEPS.md)) is **code-reconciliation**: the two
fully-specified but not-yet-built targets named by
[ADR-0017](../architecture/adr/ADR-0017-runtime-pack-load-spi.md) and
[ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md).

| Doc | Purpose | Status |
|-----|---------|--------|
| [00-core-reconciliation-plan.md](00-core-reconciliation-plan.md) | Ground-truth `core/` audit, gap ledger vs. the two ADRs, two target designs (orchestrator re-host + pack-load loader), and a sequenced TDD work-package plan with falsifiability tests | **Seeded (Cycle 24) · Executed (Cycle 25)** |
| [01-cycle-25-implementation-report.md](01-cycle-25-implementation-report.md) | Execution record of the plan: work packages shipped, test matrix results, design decisions, definition-of-done status | **Implemented (Cycle 25)** |

**Key finding driving the plan (Cycle 24):** `core/orchestrator.py` called neither
[`WorkerRegistry`](../../core/workers.py) nor [`HandoffRouter`](../../core/handoff.py) — both
were fully built and unit-tested but **inert** in the run loop. **Cycle 25 wired both gates
live** (tool-scope → `tool_scope_blocked`, handoff → `handoff_refused`), added the
[`ExecutionBackend`](../../core/execution.py) port, and built the complete
[`core/packs/`](../../core/packs/) loader — the marquee test
`test_floor_loosening_bundle_fails_validate` is green. **62 → 131 tests, `check.py` exit 0.**
Remaining: **WP-A4** (re-express `run()` against the port) + **WP-C1** (CI coverage gate).

This is a **coding-cycle brief**, not an architecture doc: it is written to be executed against
the real code, keeping the tree green at every step (`--cov=core --cov-fail-under=80`).
