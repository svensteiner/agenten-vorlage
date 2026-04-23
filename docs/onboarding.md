# Agent Onboarding

This document is the starting point for creating a new automation agent from this template.

The idea is simple:

1. ask the right questions
2. collect prompts and answers
3. turn the answers into `SOUL.md`, config, workflows, policies, and tools
4. launch the agent with a project-specific identity

## Purpose

Use this onboarding flow whenever we create a new project pack.
It helps us avoid random prompt sprawl and forces us to define the agent clearly before implementation.

## Step 1: Define the project

Ask these first:

- What is the project called?
- What problem does the agent solve?
- Who is the owner or primary user?
- What does success look like?
- What should the agent never do?

## Step 2: Define the agent identity

Ask these next:

- What is the agent's role?
- Which company, team, or customer does it belong to?
- What language should it use?
- Should it sound formal, direct, friendly, or technical?
- What knowledge should it always assume?

This section becomes the core of `project/SOUL.md`.

## Step 3: Define the workflow

Ask:

- What are the recurring tasks?
- In what order should the agent do them?
- Which steps are mandatory?
- Which steps are optional?
- When should it stop and ask a human?

This section becomes `project/workflows/`.

## Step 4: Define the tools

Ask:

- Which systems does the agent need to access?
- Which files should it read or write?
- Which API integrations are needed?
- Which actions are safe to automate?
- Which actions need explicit confirmation?

This section becomes `project/tools/` and `project/policies/`.

## Step 5: Define the memory

Ask:

- What should the agent remember across runs?
- What should be written to project memory?
- Which facts change often?
- Which facts are stable?

This section becomes `project/memory/` and the memory-related parts of `config.json`.

## Step 6: Define quality and safety

Ask:

- What counts as a good result?
- What is the minimum quality threshold?
- What should be retried automatically?
- What should always be escalated?
- What actions are destructive or expensive?

This section becomes `project/policies/`, `project/config.json`, and governance rules.

## Output mapping

| Onboarding answer | Target file |
| --- | --- |
| Project name | `project/config.json` |
| Agent identity | `project/SOUL.md` |
| Operating rules | `project/AGENTS.md` |
| Recurring task flows | `project/workflows/*.md` |
| Tool list | `project/tools/*.py` |
| Approval rules | `project/policies/*.md` |
| Domain facts | `project/knowledge/*.md` |
| Persistent learnings | `project/memory/*.md` |

## Suggested interview script

Use this exact prompt flow when onboarding a new project:

```text
I want to create a new automation agent.

Ask me the minimum set of questions needed to define:
- the project name
- the agent identity
- the target workflow
- the required tools
- the approval rules
- the quality threshold
- the memory the agent should keep

After I answer, summarize the project as:
1. agent identity
2. workflows
3. tools
4. policies
5. memory
6. open questions
7. recommended next implementation steps

If you want the repository to generate a new project pack after the interview, run:

```bash
python agent_cli.py setup
```
```

## Recommended artifact

After the interview, create a short project brief in markdown and use it to generate:

- `project/SOUL.md`
- `project/config.json`
- `project/workflows/example_automation.md`
- `project/tools/`
- `project/policies/`
- `project/knowledge/`

## Guiding principle

The onboarding should make the agent feel like a productized system, not a one-off prompt.
