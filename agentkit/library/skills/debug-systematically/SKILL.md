---
name: debug-systematically
description: Diagnose a reproducible defect or failed check, test one causal hypothesis at a time, and verify a minimal repair.
---

# Debug systematically

Capture the actual failing input and error. Trace the failing value to its source and
compare against a working case. Form a causal hypothesis and use the smallest check
that can falsify it. Repair the cause, then rerun the original reproduction and affected
regression checks. Do not stack speculative fixes on an unexplained symptom.

When an attempt fails, preserve the observation for the coordinator. Change the hypothesis
or investigation method before another attempt. Stop when the configured failure budget
is reached or the next useful evidence needs unavailable access.

