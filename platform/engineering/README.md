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
| [00-core-reconciliation-plan.md](00-core-reconciliation-plan.md) | Ground-truth `core/` audit, gap ledger vs. the two ADRs, two target designs (orchestrator re-host + pack-load loader), and a sequenced TDD work-package plan with falsifiability tests | **Seeded (Cycle 24)** |

**Key finding driving the plan:** `core/orchestrator.py` today calls neither
[`WorkerRegistry`](../../core/workers.py) nor [`HandoffRouter`](../../core/handoff.py) — both
are fully built and unit-tested (62 tests green) but **inert** in the run loop. Making those
two ratified gates live is the highest-leverage, lowest-risk first move.

This is a **coding-cycle brief**, not an architecture doc: it is written to be executed against
the real code, keeping the tree green at every step (`--cov=core --cov-fail-under=80`).
