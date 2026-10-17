# Source-first coding qualification - 17 October 2026

The candidate separates persona from drafting policy and carries source text as
unverified JSON data through the existing Marketingbot generator. Provider calls,
three-attempt budget, cleanup and publication checks are unchanged.

The first native run completed after one rejected review and automatic repair,
but seven later host counterexamples exposed Unicode line splitting and persona
interpolation. It failed host qualification despite 79 passing targeted tests.

A separate follow-up used those host counterexamples. Its independent reviewer
found another nonprintable-Unicode validation gap; the planner requested repair
and a fresh review. Host tests then confirmed 99 passing checks in 13.32 seconds.
Python and security reviews found no remaining high/critical blocker. Neither run
received host code edits while executing; the follow-up is explicitly marked
assisted because its task uses host counterexamples from the first run.

Raw execution records retain passed=false. See host-validation.json for the later
host checks and SHA-256 links. The snapshots are inert text, not runtime imports.
The original baseline is Marketingbot commit db358c51; candidate bytes remain
separate and have not been promoted to master or the running installation.

Full regression on this candidate and actual text-quality acceptance are pending.
The old fixed-nine quality gate remains failed; a new six-case synthetic study
cannot replace it. Mock tests and prompt rules do not prove model truth, resistance
to every prompt injection, X reach, production readiness or general autonomy.
A misleading pre-existing verified-observation docstring must be corrected before
promotion. Native Codex costs were not reported.
