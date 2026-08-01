# KMU order-to-report E2E construction plan

## Objective

Deliver one demonstrable, zero-cost local journey:

`Controlling-Agent bestellen -> Instanz provisionieren -> synthetische Daten laden
-> deterministischen Lauf starten -> verifizierten Bericht öffnen`.

This is a local sales/pilot workflow, not a payment system, customer account,
contract, or production multi-tenancy evidence.

## Non-negotiable invariants

- Synthetic packaged data only; no caller-provided file paths.
- Cost budget is exactly EUR 0. No LLM, Azure, network, connector, email, publish,
  booking, or other non-loopback external action is reachable.
- Instance identity, preset snapshot, and seeded demo inputs are immutable after
  publication. `state/` and `artifacts/` are controlled mutable areas.
- A local instance is a path-contained namespace under one OS principal. It is not
  an authorization boundary or production tenant-isolation evidence.
- Reuse the existing `kmu-controlling` preset, deterministic report tool, signed
  acceptance evidence, and tenant-bound instance validation.
- Every mutation is tenant-scoped, serialized, crash-consistent, idempotent by
  operation ID, and fail-closed.
- The portal binds to localhost by default and is labelled as a free local demo.
- The portal never accepts artifact paths. It serves only fixed, bounded report
  bytes resolved from service-owned order state.

## Dependency graph

```text
Step 0 contracts and tooling
   -> Step 1 public instance factory
      -> Step 2 operation-id report persistence
         -> Step 3 order service
            -> Step 4 hardened local portal
               -> Step 5 browser E2E and release gate
```

## Step 0 - Contracts, threat boundary, inventory, and test tooling

Tasks:

- Pin the exact demo source/destination/size/SHA-256 inventory.
- Define statuses and idempotency: same key + same canonical request replays;
  same key + different request conflicts; different run keys are distinct.
- Define the `deterministic_local_demo` profile. Generic model-backed execution is
  not part of this order path.
- Declare Ruff, mypy, Playwright, pytest, and CI browser dependencies.
- Write import-boundary, path/traversal, non-loopback egress, concurrency, and
  honest-copy tests before implementation.

Exit: collection succeeds and each expected red test maps to one missing contract.

## Step 1 - Extract a public, race-safe instance factory

Context: `agent_cli.py` already provisions immutable preset instances and
`ControllingReportTool` already produces verified local artifacts.

Tasks:

- Move UI-neutral instance creation/validation/preset overlay into
  `core/instance_factory.py`; both CLI and order service depend on it.
- Never import `agent_cli`, `agent`, or `brain` from `core`.
- Lock outside the not-yet-existing target, provision into a same-volume sibling,
  validate, and publish with a directory rename.
- Preserve existing CLI behaviour and reject/quarantine partial publication safely.

Verification:

```powershell
python -m pytest -q tests/test_instance_factory.py tests/test_agent_cli.py --no-cov
```

Exit: concurrent create tests publish exactly one complete instance and no `core`
module imports a top-level UI/runtime module.

## Step 2 - Idempotent report operations and verified report reader

Tasks:

- Carry a caller-owned `operation_id` into report persistence.
- Deduplicate under the existing acceptance lock before allocating a run.
- Recover correctly around ledger/head/latest publication boundaries.
- Add a fixed, bounded reader that verifies the signed artifact bundle and returns
  already-opened HTML bytes without a verify-then-reopen race.

Exit: replaying one operation never increments the acceptance count; three distinct
operation IDs produce exactly three signed runs; tamper and crash tests fail closed.

## Step 3 - Local durable order service

Files:

- New `core/local_kmu_orders.py`

Tasks:

- Implement create/status/run/artifacts as a UI-neutral service with stable JSON
  contracts.
- Persist tenant-local state and idempotency records using atomic writes and stable
  cross-process lock files.
- Provision through the existing preset factory, verify pinned demo hashes, then
  copy only the approved XLSX and mapping to their allowed instance locations.
- Dispatch `ControllingReportTool` directly with deterministic child operation IDs.
- One verification action runs three explicit slots and reaches signed 3/3
  acceptance. A retry replays the committed result.
- Expose report content only through the verified-byte reader.

Rollback: disable/remove the order service; the extracted factory and operation-ID
support remain backward-compatible infrastructure.

Exit: service tests pass, including two-tenant denial, zero-cost, no-model,
no-egress, concurrent create, replay, and failure paths.

## Step 4 - Hardened local customer portal

Files:

- New `order_portal.py`
- New `order-portal/index.html`, `app.js`, and `styles.css`
- Browser/API tests

Tasks:

- Show one clear product card and a zero-euro demo order form.
- POST order, display provisioning result, run the deterministic agent, and open
  the actual generated HTML management report.
- Use semantic labels and stable `data-testid` selectors.
- Bind to `127.0.0.1` with random-port support; validate client, Host, Origin, and
  CSRF token for mutations.
- Reject transfer encoding, unsafe/conflicting lengths, oversized bodies,
  unsupported content types, encoded traversal, and unknown routes.
- Use fixed static/report routes, restrictive CSP, `nosniff`, `no-store`, and no CORS.
- Render all customer text with `textContent`.

Rollback: remove the portal; the service journey remains independently testable.

Exit: API/security tests pass and the report route returns only a valid accepted
report for the opaque order ID.

## Step 5 - Browser E2E and release gate

Tasks:

- Document the command and the honest boundary: synthetic/local, no payment,
  no production tenant attestation.
- Add Linux browser CI and Windows concurrency/locking CI.
- Run focused tests, lint/type checks, the full suite, and repository validation.
- Run code, Python, security, and E2E reviews; fix all blockers.
- Inspect staged files for secrets and missing dependencies; commit and push one
  coherent green package.

Verification:

```powershell
python tools/check.py
python -m ruff check core/instance_factory.py core/local_kmu_orders.py order_portal.py agent_cli.py tests
python -m mypy --follow-imports=skip core/instance_factory.py core/local_kmu_orders.py order_portal.py
python -m pytest -q
```

Exit: the journey is repeatable offline, costs EUR 0, makes no external action,
and ends at a real verified report.
