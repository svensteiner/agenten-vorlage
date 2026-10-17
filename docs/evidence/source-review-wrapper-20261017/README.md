# Preserve source-task prompts through the central responder

The central freeform adapter appended the ordinary German tweet-only/220-character instruction even when an explicit source-faithfulness task requested review JSON or a repair preserving its original language and stricter length. Two exact-prompt regression cases failed before the fix; a third control confirms ordinary tweet tasks retain their wrapper.

The fix excludes only editorial and the two explicit source-faithfulness task types from that legacy wrapper. No provider, credential, budget, posting, review or source-parser rule changes. A separate read-only review found no blocker.

The larger isolated source candidate passed 4,605 unit tests,11 skips and5 expected failures in273.93seconds. Because its semantic acceptance is still failed, a clean worktree was created at original Marketingbot/master db358c51. Only the central responder's small exclusion and its test file were copied. The new source qualifier was absent. That independently tested subset passed all4,464 unit tests,11 skips and5 expected failures in286.32seconds, exit0, source hashes unchanged. Both snapshots and logs are retained separately.

Only this two-file fix was pushed to [Marketingbot/master b2b0c7e2](https://github.com/svensteiner/marketingbot/commit/b2b0c7e2). The live original installation was not modified or restarted. The unqualified source checker, typed API prototype and other isolated content changes were not included. A GitHub push is not a deployment or general agentic acceptance. See the separate typed-protocol evidence for the unresolved semantic false acceptance.

The hash manifest covers raw captures, not this editorial README. Validation hashes describe the tested checkout bytes; the committed patch is captured separately.
