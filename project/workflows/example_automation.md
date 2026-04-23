# Example Workflow

## Trigger

The agent receives a domain task from a queue, webhook, or manual run.

## Steps

1. Read the task and project rules.
2. Draft a plan.
3. Check governance and approval gates.
4. Execute the allowed tool chain.
5. Verify the result.
6. Store the outcome in project memory.

## Escalation

- Stop if the task is destructive.
- Stop if the required data is missing.
- Stop if verification fails twice.
