# ADR-0005 — Template consolidation: one core, harvest the fork

- **Status:** Accepted (Cycle 2, council-driven)
- **Deciders:** 5-member design council (Enterprise Architect, Senior Engineer,
  Security & Governance Architect, QA & Test Architect, Redundancy & Consistency
  Reviewer) — synthesized by the architecture agent
- **Supersedes:** — · **Relates to:** [ADR-0002](ADR-0002-reuse-existing-template-core.md)

## Context

Four divergent branches existed for the agent template:
`main` (hardened `core/` + `project/` base, + `platform/` docs),
`claude/tender-feistel-a414f8` (a clean superset of `main` adding skills, connectors,
steering examples, leaf-write governance, financial-services patterns),
`claude/kind-keller-601f08` ("v3.0" — a **flat-root rewrite** with a 910-line
`agent.py`, its own `workers.py`/`handoff.py`/`check.py`, `manifest.yaml`, and **127
passing tests**), and two already-contained branches (`festive-johnson`, `lucid-kare`).
The user asked for "the perfect agent template." A council of five specialists analyzed
the actual branch contents.

## Decision

**Base = `main`'s `core/` + `project/` architecture. Merge `tender-feistel`. Do NOT
merge v3.0 wholesale — harvest its assets onto the core.**

Council consensus was near-unanimous:

1. **Keep the core/project split** (ADR-0002-binding). v3.0's flat-root rewrite
   reverses it, branched *before* main's hardening, and would delete `core/`,
   `project/`, and `platform/`. Rejected as a base.
2. **Merge `tender-feistel`** — it is a well-behaved superset of `main`; only two
   trivial conflicts (`core/governance.py`, `project/manifest.json`). **Done** in this
   cycle.
3. **Harvest from v3.0 (cherry-pick/port, not merge):** the 127-test suite, the
   `check.py` manifest validator, `deploy.sh`/`deploy.ps1`, and the
   least-privilege **worker** + allowlisted **handoff** *concepts* re-homed as
   `core/workers.py` / `core/handoff.py`. Plus the friendlier German onboarding UX.
4. **Drop from v3.0:** the 910-line `agent.py`, `setup_wizard.py`, flat `skills/` and
   `agents/`, `manifest.yaml`, and the duplicate `EINRICHTEN.bat`/`STARTEN.bat`.
5. **Canonical choices** (dedup): JSON manifest at `project/manifest.json`;
   `project/skills/<kebab>/SKILL.md` (+ `references/`); `project/agents/<role>/AGENT.md`
   with frontmatter; `agent_cli.py` as the single setup wizard; `SETUP.bat`/`START.bat`.
6. **Security correction (see [ADR-0006](ADR-0006-fail-closed-autonomy-default.md)):**
   the full-autonomy default merged earlier was fail-open; restored to
   **fail-closed-by-default** during conflict resolution.

## Consequences

- (+) One coherent template on a hardened, ADR-aligned core; no lost `platform/` docs.
- (+) v3.0's best engineering (tests, validator, least-privilege workers, deploy) is
  preserved as the harvest plan, not discarded.
- (+) Duplicate capabilities collapse to one canonical implementation each.
- (−) The v3.0 harvest is real work (est. M / 1–2 focused days): tests are coupled to
  v3.0's flat modules and pre-hardening `brain.py`; `test_agent.py` must be rewritten
  against `core/`. Tracked in [NEXT_STEPS](../../NEXT_STEPS.md).
- (−) v3.0 remains an unmerged branch until the harvest lands; must not be force-merged.

## Alternatives

- **Merge v3.0 as the trunk** — rejected: reverses ADR-0002, drops hardening + docs,
  monolithic 910-line agent violates the file-cohesion standard.
- **Discard v3.0 entirely** — rejected: loses the single best test suite and the
  least-privilege/handoff safety ideas across all branches.
- **Keep both architectures** — rejected: two runtimes, two manifests, permanent
  confusion for pack authors.

## Revisit when

The v3.0 harvest is complete and the ported worker/handoff modules prove the core's
orchestration interfaces need widening — then widen the interfaces (per ADR-0002's
revisit clause), don't reintroduce the flat layout.
