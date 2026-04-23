# Agent Onboarding

This document is the starting point for creating a new automation agent from this template.

The idea is simple:

1. ask the right questions
2. collect prompts and answers
3. turn the answers into `SOUL.md`, config, workflows, policies, and tools
4. launch the agent with a project-specific identity

## Purpose

Use this onboarding flow whenever we create a new project pack.
It keeps the start simple for beginners and still leaves room for precise details later.

## Simple Start

The default wizard asks only the essentials:

- What is the project called?
- What should the agent do?
- Who is it for?
- Which tools or files does it need?
- What does success look like?
- What starts the workflow?
- What needs approval?

This is enough to create a good first version of the agent.

## Optional Detail

If you want a sharper project pack, the wizard can ask more questions after that:

- What is the agent's role?
- Which language should it use?
- How should it sound?
- What should it always know?
- What must it never decide alone?
- How should it retry after errors?
- What should it remember?

This section becomes the core of `project/SOUL.md`.

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

Ask me the minimum set of beginner-friendly questions needed to define:
- the project name
- what the agent should do
- who it is for
- which tools it needs
- what success looks like
- what needs approval
- what it should remember

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

For more detail, use:

```bash
python agent_cli.py setup --full
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
