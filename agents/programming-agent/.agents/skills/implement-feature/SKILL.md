---
name: implement-feature
description: Implement a bounded software feature in an existing repository, with acceptance examples, targeted tests and a reviewable diff.
---

# Implement a feature

Read the affected code and repository instructions. Identify the smallest path from the
request to an observable behavior. Reuse existing components and dependencies where they
fit. For changed behavior, specify an acceptance example and a meaningful test before
implementation. Avoid tests that merely repeat constant values or implementation details.

Implement within the assigned files. Keep public contracts and callers synchronized.
Run the affected checks and inspect the diff for unrelated edits. Record command,
exit status and the behavior actually checked. Hand off changed paths, limitations and
acceptance evidence. Do not describe a build or test as passing if it was not run.

