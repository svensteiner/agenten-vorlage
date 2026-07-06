# Models

> Status: **Seeded** (Cycle 22) · Owner: Platform / Security / Data Architecture

**Scope.** Where models physically run (the serving substrate); the dual-track hosting fabric
(in-boundary self-hosted OSS vs. contractually-private managed endpoints); per-`(tenant tier ×
data class)` routing behind the Model Gateway; the `hosting_posture` registry field. This folder
owns **hosting**; it does *not* re-open the [Model Gateway](../architecture/adr/ADR-0003-model-gateway-indirection.md)
indirection, the [approved-model registry / eval gate](../governance/00-governance-and-audit.md#8-g6--model-governance),
or the [label→trust routing matrix](../governance/00-governance-and-audit.md) — it fills the one
field those mechanisms left open.

## Documents

- **[00-model-hosting-and-serving.md](00-model-hosting-and-serving.md)** — the dual-track serving
  fabric (Track A in-boundary OSS / Track B contractually-private managed), the closed
  `hosting_posture` enum, the per-tier×class routing map, and the fail-closed track-fallback rule.
  **Resolves open Q#3.** Implements [ADR-0018](../architecture/adr/ADR-0018-model-hosting-and-serving-posture.md).

Consumes the choke-point + registry + routing mechanisms from
[ADR-0003](../architecture/adr/ADR-0003-model-gateway-indirection.md) and
[Governance §4/§8](../governance/00-governance-and-audit.md); hands GPU-pool/endpoint **sizing &
pricing** to [Deployment §7](../deployment/00-deployment-topology.md) and network-boundary
hardening to [Security](../security/00-security-architecture.md).
