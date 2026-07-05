# ADR-0007 — Client configuration surface (settings UI)

- **Status:** Accepted (Cycle 2c)
- **Deciders:** Architecture agent, with the product requirement from the platform owner
- **Relates to:** [ADR-0006](ADR-0006-fail-closed-autonomy-default.md),
  [Platform Overview](../01-platform-overview.md) (admin/config plane)

## Context

The template is meant to be delivered as a **tool for clients**, not only for
engineers. Configuration (autonomy level, model provider, quality/limits, behaviour
flags) previously lived only in hand-edited JSON (`config.json`, `project/manifest.json`).
Editing JSON by hand is error-prone, intimidating for non-technical clients, and — for
safety-critical settings like the autonomy gate ([ADR-0006](ADR-0006-fail-closed-autonomy-default.md)) —
a real risk (a stray comma disables the agent; a wrong value silently disables the
approval gate).

## Decision

Ship a **local web-based settings surface** (`control_panel.py`, launched via
`EINSTELLUNGEN.bat`) as the client-facing way to configure the agent.

- **Standard library only** (`http.server`) — no Flask/Node, no install step; runs on
  any machine that already runs the agent.
- **Single source of truth for UI + validation:** a `SETTINGS_SPEC` list drives both
  rendering and server-side validation, so they cannot drift.
- **Safe writes:** binds to `127.0.0.1` only; only known keys are writable; input is
  validated (ranges, choices) before persisting; invalid JSON fails loud rather than
  resetting config.
- **Consistency:** saving the autonomy level updates `config.json`
  (`autonomy_level`, `require_human_approval`) **and** `project/manifest.json`
  (`autonomy_level`, `approval_required_for`) together, so the governance layer and the
  runtime never disagree.
- **Safety UX:** switching to full-autonomy shows an inline warning; "Gated" is the
  presented-safe default (per ADR-0006).
- **Connector management:** the panel also edits `project/connectors.yaml` — the
  governance allowlist ([ADR-0004](ADR-0004-permission-faithful-retrieval.md) at template
  scale). Adding/removing a data source is done in the UI; security-relevant fields the UI
  doesn't render (`tools_enabled`, `required`) are **preserved** on save, never silently
  dropped.

## Consequences

- (+) Clients configure the agent without touching code/JSON.
- (+) Safety-critical settings are guarded by validation and a visible warning.
- (+) Zero new dependencies; trivial to run and to port.
- (−) A minimal single-file server, not a hardened multi-user web app — intentionally
  local-only. Multi-user/tenant admin is a platform-scale concern, not this template's.
- (−) Two config files still exist (`config.json` runtime vs `manifest.json` pack); the
  panel keeps them in sync but the duplication should eventually be consolidated
  (tracked in NEXT_STEPS).

## Platform significance

This local panel is the **seed of the platform's Admin/Config plane**. At platform
scale it becomes a proper multi-tenant admin UI (per-tenant policies, model routing,
connector management, audit views) behind the API Gateway and IdP — see
[Platform Overview](../01-platform-overview.md). The concepts (spec-driven forms,
validated writes, autonomy-as-explicit-opt-in) carry forward; the hosting hardens.

## Alternatives

- **CLI-only settings** (extend `agent_cli.py`) — rejected as the primary client
  surface: less approachable for non-technical clients, though the CLI wizard remains
  for project scaffolding.
- **Hand-edited JSON** (status quo) — rejected: error-prone and unsafe for the autonomy
  gate.
- **Full web framework (Flask/FastAPI + SPA)** — rejected for now: adds dependencies and
  build tooling for a local single-user panel; revisit at platform scale.

## Revisit when

The template is deployed for multiple concurrent users/tenants, or settings outgrow a
single-file form — then graduate to the platform Admin plane with authN/authZ.
