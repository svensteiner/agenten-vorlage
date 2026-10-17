# CLI host write policy

The CLI now accepts repeated --allow-write exact relative files and an explicit --autonomous-writes opt-in. Autonomy without a list, conflicting approval modes and noncanonical paths are rejected before provider construction. The default approval requirement for model backends is preserved. Existing stored approvals remain mandatory across resume; a policy change or omission is rejected, including completed runs.

Before implementation, three new tests failed because the CLI did not support these options (raw log retained). Final canonical validation: 463 unittest cases in 233.760 seconds, 459 passed and four skipped, exit 0. The source hash manifest confirms the tested files were unchanged throughout the run. Ruff and all 20 offline release gates passed. Eight CLI tests passed separately, including real subprocess run/resume, policy mismatch and persisted approval requirements. A separate read-only code review found no blocker.

These CLI paths were tested using the offline demo and mocked model constructors. No new real-model CLI qualification is claimed. Earlier real direct-backend denial evidence remains separate, and its paired normal Engine workflow remains failed. Project code execution is still disabled under the strict policy, and the Cockpit has not yet exposed the file list. This is not a production or general agentic acceptance.

## GitHub CI portability correction

GitHub run [38995248475](https://github.com/svensteiner/agenten-vorlage/actions/runs/38995248475) failed two Codex policy unit tests on Linux because their backend constructors required a locally installed Codex executable, despite mocked model calls. Both errors were reproduced locally by forcing CLI discovery unavailable. The fixture now stubs only command discovery during those two constructors. Proposal validation, host enforcement, real file mutations and forbidden-path checks remain active. Both cases then passed with discovery still unavailable; separate review found no blocker. No production runtime code changed. This correction requires a fresh GitHub full-suite result; the earlier full local result above predates it.
