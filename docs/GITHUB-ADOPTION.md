# GitHub adoption research

Research date: 2026-10-01. This is a bounded architecture and licensing review, not a
recommendation to copy a repository or add a dependency. Claims marked **evidence** come
from the linked repository at the observed revision; **assessment** is our interpretation.

## Decision

Keep AgentKit’s Python engine, agent-pack format, review gate, workspace binding, and
checkpoint/resume model. Do not import code, runtime services, or skills from these projects.
The useful adoption target is a small set of interface patterns: a thin chat client, explicit
action/approval events, reconnectable job status, and adapter contracts. These can be added
behind the existing Cockpit/Backend boundaries and tested with fixtures. No project reviewed
provides a drop-in replacement for the current bounded local runner.

## Open-Dots (requested reference)

Source: [repository](https://github.com/Anil-matcha/Open-Dots), [README](https://github.com/Anil-matcha/Open-Dots/blob/main/README.md),
[MIT license](https://github.com/Anil-matcha/Open-Dots/blob/main/LICENSE).

**Evidence.** The repository showed 105 commits at the observed revision and declares the
MIT license. Its README labels the project “Prototype / active development” and documents
assistants, streaming chat, persistent conversations and a model adapter. The current server
uses the Responses API and explicitly does not use Chat Completions. Browser access uses an
owner token. A deny-by-default action gateway creates approval and audit records. Integrations
are deliberately narrow: a Composio-backed GitHub issue connector and `/search` through the
You.com MCP. Optional computer providers include fake, Docker and remote runtimes; the README
explicitly says this computer path is not hardened for hostile-web use.

**Assessment.** This is the best design reference for the existing Cockpit because its
boundaries resemble ours: UI → HTTP events → local run state → governed tools. Adopt the
concept of user-visible approval/audit records and provider-independent action contracts only
as contracts in AgentKit. AgentKit/Cockpit already matches the deny-by-default approval model
and strengthens it with persistent exact-action identity, stale-review invalidation,
`in_flight`/unknown-outcome handling and company/workspace binding. Preserve those semantics
and dynamic observation-driven planning. Do not adopt its computer runtime as a security
boundary; its own README warns against hostile-web use. No Open-Dots code was copied.

## LibreChat

Source: [repository](https://github.com/LibreChat-AI/LibreChat), [README](https://raw.githubusercontent.com/LibreChat-AI/LibreChat/main/README.md),
[MIT license](https://github.com/LibreChat-AI/LibreChat/blob/main/LICENSE).

**Evidence.** The README advertises custom and local model endpoints, agents, MCP, reusable
`SKILL.md` bundles, subagents, attached workspaces, trace viewing, sandboxed code execution,
OpenTelemetry/Langfuse, resumable streams with Redis for horizontal scaling, and multi-user
authentication/admin controls. The repository is MIT licensed. It also labels attached
workspaces highly experimental and points users to changelogs for breaking changes.

**Assessment.** LibreChat is a useful checklist for future host capabilities, especially
stable event types, trace inspection, and reconnect/resume behavior. It is too broad to embed
in this template: adopting its service topology would duplicate Paperclip, the AgentKit
engine, and our portable skill packaging. The minimal local action is to define a versioned
Cockpit status/event response that can later support reconnects; Redis, multi-user auth, and
trace infrastructure remain host-level work.

## assistant-ui

Source: [repository](https://github.com/assistant-ui/assistant-ui), [README](https://raw.githubusercontent.com/assistant-ui/assistant-ui/main/README.md),
[MIT license](https://raw.githubusercontent.com/assistant-ui/assistant-ui/main/LICENSE).

**Evidence.** assistant-ui is a TypeScript/React library rather than an agent server. Its
README exposes composable thread/message/composer primitives, streaming, retries,
attachments, markdown, accessibility, generative UI for tool calls and inline human
approvals, typed runtimes, and adapters for Vercel AI SDK, LangGraph, AG-UI/A2A, and custom
data streams. The package and repository state MIT licensing; managed persistence and
telemetry are offered separately as Assistant Cloud.

**Assessment.** It could replace or inform the Cockpit’s presentation layer if the project
later moves to a React build. It cannot replace AgentKit’s Python orchestration, filesystem
locks, review gate, or checkpoint semantics. Before considering adoption, prototype one
read-only status view against the current HTTP API and measure bundle/build cost; do not add
it to the template merely for visual polish.

## Open WebUI (comparison)

Source: [repository](https://github.com/open-webui/open-webui), [license](https://github.com/open-webui/open-webui/blob/main/LICENSE),
[license history/notice](https://github.com/open-webui/open-webui/blob/main/LICENSE_NOTICE).

**Evidence.** The current repository notice says licensing varies by contribution history:
older material is MIT/BSD-3-Clause, while newer material is under the Open WebUI License.
The current license adds a material restriction against removing or altering Open WebUI
branding except for stated small-user, permission, or enterprise-license cases, and requires
a contributor license agreement for newer contributions.

**Assessment.** Open WebUI is valuable as a product-scale self-hosted UI reference, but its
mixed historical licensing and branding condition make code adoption and white-label use a
poor fit for this portable company template. Treat it as product research only; no source or
dependency is recommended.

## Minimal follow-up backlog

1. Specify a small Cockpit event/status contract (`queued`, `running`, `blocked`, `error`,
   `completed`) with run identity and last checkpoint, preserving current resume rules.
2. Add approval/audit display fields only when the engine already emits them; never infer
   approval from UI state. Add fixture tests for refresh/reconnect and unknown outcomes.
3. If a React migration becomes justified, run a separate assistant-ui proof of concept
   against that contract. Record its exact package version and license before adoption.

No live model, production deployment, hostile-web sandbox, or external checkout was tested in
this research. The recommendations are repository/documentation based and remain subject to
implementation review.

## Open-Dots refresh: exact current comparison

Checked again on 2026-10-01 at Open-Dots revision
`5abe1b3d65d5176af936ed92de1b731634d2bcb5` (2026-10-01 07:03:56 UTC) against the
[current Open-Dots README](https://github.com/Anil-matcha/Open-Dots/blob/main/README.md),
its [action gateway](https://github.com/Anil-matcha/Open-Dots/blob/main/server/app/services/action_gateway.py)
and the repository history. The observed revision had 105 commits and an MIT license. The
README still labels the product “Prototype / active development”. Its implemented product
surface includes assistants, streaming chat, persistent conversations and a model adapter;
inference uses the Responses API, with no Chat Completions path. Owner-token authentication
protects the browser session.

Tooling stays explicit and narrow. The action gateway denies unknown actions by default and
records approval/audit state. The documented connectors are a Composio GitHub issue flow and
`/search` through the You.com MCP. Computer execution is optional through fake, Docker or
remote providers, and the project explicitly does not claim hardening for hostile-web use.
It does not present arbitrary connector discovery or that computer runtime as a general
security boundary.

The three highest actionable gaps relative to this repository are:

1. **Dynamic workflow and delegation.** Open-Dots describes an assistant persona selecting
   governed actions, but its public architecture does not describe an observation-driven
   `delegate`/`finish`/`blocked` loop, role catalog, skill selection, or reviewer handoff.
   AgentKit already implements those backend decisions and re-plans after worker reports and
   failed reviews. Reusable idea: keep Open-Dots’ explicit registered-action boundary (unknown
   actions rejected) while exposing action observations as ordinary planner context. This is
   **inspired by** Open-Dots; no gateway code was copied. The current AgentKit approval
   receipts already match its deny-by-default shape and add persistent exact-action,
   stale-approval and unknown-outcome checks.

2. **Durable interruption and resume semantics.** Open-Dots documents SQLite persistence and
   SSE chat streaming, but does not claim an `in_flight` marker, unknown-side-effect outcome,
   or a resume protocol for an interrupted tool/model call. AgentKit persists atomic `.runs`
   checkpoints, binds resume to company/agent/workspace/backend, and requires new evidence
   before retrying an unknown outcome. Reusable idea: carry Open-Dots’ audit/request identity
   into future Cockpit event payloads, without weakening AgentKit’s existing resume rules.

3. **Evidence-based completion.** Open-Dots has approval prompts and audit events, but its
   README does not describe a separate read-only reviewer that invalidates a prior review after
   edits. AgentKit’s `dirty`/review gate and structured artifact checks provide that missing
   quality transition. Reusable idea: display Open-Dots-style action risk, preview, and audit
   identifiers in the UI, while completion remains controlled by AgentKit evidence and review.

These are comparison findings, not imported implementation. The existing approval semantics
already match or strengthen the useful Open-Dots pattern; the adoption decision remains to
preserve the AgentKit runtime and add compatible fields/contracts only when needed. No
Open-Dots source, dependency, skill or runtime was copied, and its MIT license/attribution is
therefore not being relied upon for implementation.

The only Open-Dots change after the previously reviewed revision
`e8cf82b18dfc81bbdae4c47342229ae780b9e627` updates two README video links. It changes no
runtime, security or product contract, so no implementation was imported for that delta.

## Open pull-request audit in this repository (1 October 2026)

[PR #3](https://github.com/svensteiner/agenten-vorlage/pull/3) was inspected rather than
merged blindly. It targets the historical `9b11c5c` product architecture, is currently a
draft with merge conflicts and a failed CI check, and changes a separate `product/` runtime
that the current AgentKit/Cockpit release replaced. Its useful operational themes—bounded
resources, metrics, encrypted backups, restore drills, egress policy and production-safe
proxy defaults—remain acceptance requirements for the current public adapter. Its source is
not cherry-picked because doing so would reintroduce the obsolete runtime and bypass the
current company/workspace binding, approval receipts and unknown-outcome semantics.

## Document extraction adopted (30 September 2026)

[py-pdf/pypdf](https://github.com/py-pdf/pypdf) and
[tiran/defusedxml](https://github.com/tiran/defusedxml) are now package dependencies,
tested at 6.19.0 and 0.7.1 respectively. License references are in
`THIRD_PARTY_NOTICES.md`. No upstream source files were vendored.

The [pypdf extraction guidance](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
documents the distinction between embedded text and scanned images, and the memory
cost of decompressed content streams. The integration therefore limits document size,
PDF pages/content streams, extracted text and subprocess execution time. It rejects
image-only PDFs instead of implying OCR. OOXML processing reads bounded ZIP members
with defusedxml, never executes formulas or extracts archive paths onto disk.

## Local image OCR decision (30 September 2026)

[RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR) was examined as an Apache-2.0
OCR integration. Its documented setup adds an inference runtime and bundled or
selected models. For the current Windows-local release we use the already installed
[Windows.Media.Ocr API](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine)
through a bounded subprocess instead. No RapidOCR source, package or model was copied.
The host probe confirmed German and English recognizers; qualification uses synthetic
image fixtures and must be kept separate from live LLM answer quality.
