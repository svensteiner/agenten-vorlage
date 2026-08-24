# Controlling Eval

ADK-inspired golden set for the KMU controlling preset: question or tool
payload -> expected artifact keys, sourced totals, evidence hashes.
This is our pattern, not a Google ADK dependency and not ADK source.

## Run

    python -m pytest tests/test_controlling_eval.py -q --tb=short

Offline and deterministic. The harness provisions a temp instance like
the KMU acceptance e2e, copies the demo xlsx plus account-mapping.json,
and runs ControllingReportTool / ControllingComputeTool. No LLM network.
KPI numbers come only from presets/kmu-controlling/pilot/demo/expected-results.json.
Negative cases (empty inbox, missing source) must fail closed: no fabricated totals.
