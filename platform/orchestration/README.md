# Orchestration

> Status: **Seeded** (Cycle 23) · Owner: Platform Engineering / Enterprise Architecture / Security

**Scope.** What runs the **plan → act → verify loop** across multiple agents, tools, and machines:
the posture (extend the `core/` planner/verifier vs. adopt an agent framework), the split between the
**decision plane** (ours, in-boundary — planner, governance gate, dispatcher, verifier, handoff router,
tool scoping) and the **execution plane** (adopted commodity durable execution behind an `ExecutionBackend`
port), bounded pack-declared multi-agent graphs, and the tenant/budget/audit context that rides every hop.
This folder owns **orchestration posture**; it does *not* re-open the
[permission filter](../architecture/adr/ADR-0004-permission-faithful-retrieval.md), the
[single verifier gate](../architecture/adr/ADR-0014-api-contract-surface.md), the
[Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md), or the
[governance gate](../architecture/adr/ADR-0012-governance-audit-and-cost.md) — it fixes the **loop that
sequences** them when a request spans many agents.

## Documents

- **[00-agent-orchestration.md](00-agent-orchestration.md)** — the decision: **extend `core/`'s
  planner/dispatcher/verifier/governance loop into the distributed multi-agent orchestrator** (the
  choke points stay ours and in-boundary), and adopt commodity **durable execution behind an
  `ExecutionBackend` port** for the distributed plumbing only — never a framework that owns planning
  or tool-calling. Bounded, pack-declared multi-agent graphs; the same five gates re-hosted onto the
  queue-backed topology. **Resolves open Q#6.** Implements
  [ADR-0019](../architecture/adr/ADR-0019-agent-orchestration-posture.md).

Reuses the "commodity behind a port" pattern from
[ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) (Model Gateway) and
[ADR-0010 §3.4](../storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
(`VectorIndex` port); grows the [core template loop](../../core/orchestrator.py) named in
[ADR-0002](../architecture/adr/ADR-0002-reuse-existing-template-core.md); installs pack-declared agent
graphs through the [pack-load SPI](../packs/01-pack-load-spi.md). Hands substrate **sizing** to
[Deployment](../deployment/00-deployment-topology.md) and handoff-edge hardening to
[Security](../security/00-security-architecture.md).
