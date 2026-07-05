# ADR-0003 — All inference goes through a Model Gateway

- **Status:** Accepted (Cycle 1)
- **Deciders:** Enterprise Architecture, Security Architecture
- **Supersedes:** —

## Context

Multiple services (orchestrator, classifier, verifier, future agents) need model
inference. Letting each call a model provider directly would scatter credentials,
prevent central cost/policy control, and hard-wire a vendor.

## Decision

Introduce a **Model Gateway**: a single in-boundary service that mediates **all**
model calls. Responsibilities:

- **Routing** — map a logical model role (e.g. `reasoning`, `embedding`, `cheap-bulk`)
  to a concrete endpoint by policy. Enables Haiku/Sonnet/Opus-style tiering and vendor
  swap without touching callers.
- **Policy enforcement** — block disallowed models, enforce per-tenant model
  allowlists, apply prompt/response redaction, enforce token/cost budgets.
- **Secrets custody** — provider credentials live only in the gateway.
- **Observability & audit** — every inference is traced (tenant, role, tokens, cost,
  latency, policy applied) to the append-only audit log.
- **Resilience** — retries, timeouts, fallback routing, circuit breaking.

## Consequences

- (+) One choke point for governance, cost, redaction, and vendor independence.
- (+) Callers depend on a stable logical interface, not a vendor SDK.
- (−) One extra network hop and a component that must be highly available.
- (−) The gateway is a high-value target and a potential bottleneck — it must be
  horizontally scalable and hardened (see [Security](../../security/00-security-architecture.md)).

## Alternatives

- **Direct provider calls per service** — rejected: no central control, scattered
  secrets, vendor lock-in per service.
- **Thin shared client library (no service)** — rejected: policy/cost/redaction can be
  bypassed by not using the library; secrets still spread to every service.

## Revisit when

Inference moves fully on-device/in-process such that a network gateway adds latency
without governance benefit — then the gateway becomes an in-process policy layer, but
the indirection stays.
