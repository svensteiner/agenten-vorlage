# ADR-0002 — Reuse the template's core/project split as the tenancy seed

- **Status:** Accepted (Cycle 1)
- **Deciders:** Enterprise Architecture
- **Supersedes:** —

## Context

The repository already implements a reusable **automation-agent template** with a
strict split: a domain-agnostic `core/` (context builder, planner, governance,
dispatcher, memory, verifier) and a per-project `project/` pack (SOUL/AGENTS spec,
tools, workflows, policies, knowledge, subagents, memory). See
[docs/architecture.md](../../../docs/architecture.md). The platform needs a way to keep
its core generic while delivering many domains.

## Decision

Adopt the template's **core (reusable) + pack (domain-specific)** separation as the
conceptual seed of the platform's **multi-tenant, multi-domain model**:

- The platform **core** = the three planes (query, ingestion, data) + cross-cutting
  concerns. It contains **no** domain logic.
- A **domain pack** = connectors, prompts, metadata schemas, classification rules,
  policies, and evaluation sets for one domain — the platform-scale evolution of
  today's `project/` pack.
- The orchestrator/planner/verifier concepts in `core/` map directly onto the
  platform's Query Plane.

## Consequences

- (+) Continuity: the existing code and mental model are not thrown away; the platform
  is the template "grown up."
- (+) The domain-agnostic-core principle is already proven at small scale.
- (−) The template is single-process and single-tenant today; the platform is
  distributed and multi-tenant. The *concepts* transfer; the *implementation* must be
  re-hosted onto the three-plane, queue-backed topology (tracked in NEXT_STEPS).

## Alternatives

- **Greenfield, ignore the template** — rejected: discards a proven separation and
  working verifier/governance concepts for no benefit.
- **Force the whole platform into the single-process template** — rejected: cannot
  scale ingestion vs. query independently, nor isolate tenants by construction.

## Revisit when

The template's core abstractions (planner/verifier/governance interfaces) prove too
narrow for multi-agent, multi-tenant orchestration — at which point the interfaces are
widened, not the separation abandoned.
