---
name: dynamic-workflow
description: Select roles and skills dynamically for a multi-step assignment, replan from observed results, and hand off bounded work with acceptance evidence.
---

# Dynamic workflow

Start with the user's outcome and the available role/skill catalog in agent.json. Choose
the smallest next action that closes a known gap. Do not preassign every possible phase.

For a handoff, include the objective, owned files, required artifact, acceptance evidence,
remaining limits and the relevant earlier findings. Prefer one owner for a shared artifact.
Use parallel workers only for independent outcomes in isolated workspaces. Otherwise keep
execution sequential. Workers return results to the coordinator, without recursive spawning.

After every result, choose: continue, select a different skill, repair, verify, finish,
or ask for the missing input. A failed review routes back to the relevant implementation
skill. Another code edit requires fresh review. For read-only research, do not add a coding
or testing phase just because those roles exist.

Stop repeated attempts that provide no new evidence. Report the failing operation,
observed cause, smallest recovery action and who can unblock it. Completion includes
the deliverable, fresh evidence and explicit limitations. Native harness budgets and
permissions must be configured by the host; this instruction is not a security boundary.

