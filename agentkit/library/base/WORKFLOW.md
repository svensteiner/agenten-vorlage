# Dynamic workflow

Observe → select the next useful action → execute → inspect evidence → replan.
There is no mandatory planner → coder → tester pipeline. A research request may need only
a researcher. A failed review may require a targeted coder step and another review.

For each decision:
1. Identify the remaining gap between the current artifacts and the user's acceptance criteria.
2. Choose a registered role and up to four relevant skills. Use the catalog descriptions first.
3. Give a bounded task, expected artifact, acceptance criteria and relevant previous evidence.
4. Inspect the structured result. A blocked tool may need another method; a real missing input
   should be reported as a specific blocker. Do not repeat the same failed action unchanged.
5. Finish only when the requested outcome is supported by fresh evidence. Code changes need
   review after the most recent write. A later edit invalidates the earlier review.

The local runtime offers delegate, finish and blocked. The planner chooses one action per
iteration. Workers are sequential within one workspace; independent agent instances can run
in separate worktrees/processes. Do not create recursive delegation trees inside a worker.

Limits on decisions, failed steps, call duration and context size live in agent.json.
Hitting a limit yields blocked with a checkpoint. Time/step limits are not monetary budgets;
Paperclip or the model provider must enforce spend limits.

For native DeepSeek Harness, load the dynamic-workflow skill and use the harness's own
tools, subagents and trajectory. The Python runner's hard checks do not apply to native mode.

