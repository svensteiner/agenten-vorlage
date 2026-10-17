# Strict host write policy: canonical validation

The canonical candidate ran 459 unittest cases in 209.059 seconds: 455 passed, four skipped, exit 0. Source hashes before and after are identical in full-unittest.json. Ruff passed; the offline release runner passed all 20 gates. These are fixture, integration and offline checks, not a real-model qualification of the new policy.

The separately reviewed implementation rejects planner scope expansion, path aliases and hard links, changed policy on resume, and unbound routed endpoints. Project execution is denied under this policy. It assumes trusted host callbacks and no concurrent hostile host process; it is not an OS sandbox. CLI and cockpit do not automatically enable it. See ../../WRITE-POLICY.md.

An earlier isolated implementation run failed one public-server test; its exception details were not retained. That test passed alone and subsequent full isolated and canonical runs passed. The earlier cause remains unknown; no flaky-test diagnosis is established.
