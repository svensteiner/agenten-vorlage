# Working on this template

This repository creates portable company-agent packs and a bounded reference workflow.
Read STATUS.md, then README.md and docs/ARCHITECTURE.md before changing the runtime.

- Keep role instructions, skill guidance and executable runtime separate.
- Keep the dynamic planner observation-driven; no domain keyword router in the engine.
- Do not modify the external AI-Company checkout as part of routine template work.
- Preserve company/workspace binding, unknown-outcome handling and review invalidation.
- Do not auto-import executable code from skill directories or auto-update vendored skills.
- Update tests for changed state transitions, resume semantics and subprocess behavior.
- Run `python -m unittest discover -v`; validate generated packs and the offline demo.
- Document whether a backend was tested with a real model or only via fixtures/contracts.
- Preserve source licenses and UPSTREAM.json on copied resources.
