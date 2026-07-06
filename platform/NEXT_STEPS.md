# NEXT_STEPS — Continuous Architecture State

> **Read this file first, every cycle.** It is the mandatory hand-off between
> execution cycles. Update it at the end of every cycle. Never restart from scratch.

- **Current cycle:** 26 (**Coding cycle — finished the orchestrator re-host + locked the coverage floor; the engineering track is now COMPLETE.** Executed the [reconciliation plan](engineering/00-core-reconciliation-plan.md)'s last two work packages. **WP-A4:** [`core/orchestrator.py`](../core/orchestrator.py)'s `run()` loop is re-expressed against the [`ExecutionBackend`](../core/execution.py) port — each plan step's *execution* is routed `start_run → schedule_step → await_steps` through the default `InProcessExecutionBackend`, never a direct `dispatcher.dispatch(...)` call, with **behaviour parity** (the 131 prior tests pass unchanged + a dedicated spy/parity test). `RunSpec` consolidated to one definition (execution plane, re-exported from orchestrator). This realizes ADR-0019's "same primitives re-hosted" in code: the decision plane (governance/tool-scope/handoff/verifier) stays in the loop, only the *when/whether/retry* of a step moved behind the port — no new decision method (the port-purity grep-invariant still holds). **WP-C1:** the legacy LLM-path modules (`verifier` 25→97 %, `subagents` 28→94 %, `planner` 54→89 %, `governance` 66→96 %, `dispatcher` 74→100 %) were backfilled with **mocked-model** tests (monkeypatched `brain.complete`/`brain.evaluate`, deterministic regardless of env/API keys), lifting **whole-`core` coverage 75 % → 92.9 %**; [`pytest.ini`](../pytest.ini) now enforces `--cov=core --cov-fail-under=80` and a new [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs `check.py` + the gated suite on push/PR. **131 → 193 tests green (+62), `check.py` exit 0, ruff clean.** No ADR (discharges the last of ADR-0019). The engineering-track [Definition of Done](engineering/00-core-reconciliation-plan.md#8-definition-of-done) is **fully met** — see the [Cycle-26 implementation report](engineering/02-cycle-26-implementation-report.md). **Remaining: tuning inputs only** (distributed `ExecutionBackend` adapter sizing → Deployment §7; onboarding-UX polish → §6 Cycle 2c.4) — no open architecture question, no blocking engineering item. **Superseded — Cycle 25:** (**Coding cycle — *executed* the `platform/`→`core/` reconciliation plan (TDD).** The first cycle that ships *code*, not docs. It closes the Cycle-24 audit's load-bearing finding: **[`core/orchestrator.py`](../core/orchestrator.py) now calls both [`WorkerRegistry`](../core/workers.py) and [`HandoffRouter`](../core/handoff.py) in the run loop** — the tool-scope (O3/O5) and handoff (O4) gates went from *coded-and-tested-but-inert* to **enforced at runtime, covered by negative tests**. Shipped **Front A** (WP-A1 tool-scope wiring → `tool_scope_blocked`; WP-A2 handoff wiring → `handoff_refused`; WP-A5 governance-order hardening — a *deterministic* destructive/irreversible hard-block class evaluated **before** the `autonomy_level: max` shortcut, ADR-0006 made structural; WP-A3 the [`ExecutionBackend`](../core/execution.py) Protocol **with no decision method** + default `InProcessExecutionBackend` + port-purity grep-invariant test; G4 run identity `RunSpec(tenant, request_id)`) and **all of Front B** — the `core/packs/` loader ([bundle](../core/packs/bundle.py)→[validators](../core/packs/validators.py)+[ledger](../core/packs/ledger.py)→[dryrun](../core/packs/dryrun.py)→[loader](../core/packs/loader.py) atomic COMMIT→[activation](../core/packs/activation.py) fail-closed unload). **The marquee acceptance test passes: `test_pack_validate.py::test_floor_loosening_bundle_fails_validate` — a floor-loosening bundle is rejected by *code* (`rejected_by == "§3 tighten-only validator"`), not review** ([ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)'s headline proven in CI). **62 → 131 tests green (+69), `tools/check.py` exit 0**; coverage 80–100 % on all built/changed modules. **No ADR** (discharges ADR-0017 + ADR-0019). Wrote the [Cycle-25 implementation report](engineering/01-cycle-25-implementation-report.md). **Remaining (Cycle 26):** WP-A4 (re-express `run()` against the port — mechanical, the port + `RunSpec` exist) + WP-C1 (CI `--cov=core --cov-fail-under=80` gate, after backfilling the legacy LLM-path modules). **Superseded — Cycle 24:** (**Engineering-track bridge — the `platform/`→`core/` reconciliation *plan*.** Every open architecture question (Q#1–Q#7) is closed and the platform surface is complete, so the highest-leverage move is no longer a *decision* but the **build order** for the one remaining weighted gap: code-reconciliation. Wrote the new **[engineering/](engineering/README.md)** concern folder + **[engineering/00-core-reconciliation-plan.md](engineering/00-core-reconciliation-plan.md)** — a coding-cycle brief that discharges the two fully-specified but unbuilt targets, [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md) (pack-load loader) and [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) (orchestrator re-host), into a sequenced TDD work plan grounded in a **ground-truth audit of `core/`**. The audit surfaced the load-bearing fact the docs alone could not: **[`core/orchestrator.py`](../core/orchestrator.py) today imports and calls neither [`WorkerRegistry`](../core/workers.py) nor [`HandoffRouter`](../core/handoff.py)** — both are fully built and unit-tested (62 tests green) but **structurally inert in the run loop**, i.e. the tool-scope (O3/O5) and handoff (O4) gates are coded-and-tested yet never enforced. The plan makes wiring those two inert gates live the highest-leverage/lowest-risk first move (WP-A1/A2), before the heavier port-extraction (`ExecutionBackend`, WP-A3/A4) and the pack-load loader (`core/packs/`, WP-B1–B4, whose marquee acceptance test is *a floor-loosening bundle fails VALIDATE by code, not review* — ADR-0017's headline proven in CI). A gap ledger (G1–G8) maps each ADR requirement to its code reality; a test matrix turns each ADR falsifiability check into a named `pytest`. Adds **no ADR** (introduces no cross-component decision — it *discharges* two). This is the first instance of a reusable *engineering-bridge* doc pattern (audit → gap ledger → target design → sequenced WPs). Net progress: the coding cycle is now de-risked and fully specified end-to-end; code implementation (Cycle 25) is the next step. **Superseded — Cycle 23:** Agent orchestration posture — resolves open Q#6, the *last open architecture question*.** With Q#3 closed (Cycle 22), the only remaining doc-track item was Q#6: *extend the existing `core/` planner/verifier into the distributed orchestrator, or adopt an agent framework?* Resolved: **extend `core/` — the orchestration *logic and choke points stay ours and in-boundary* — and adopt a commodity durable-execution substrate for the distributed plumbing only, behind a narrow `ExecutionBackend` port; do NOT adopt a framework that owns planning, tool-calling, routing, or the answer gate.** The load-bearing reason: the platform's five choke points (one [verifier answer gate](architecture/adr/ADR-0014-api-contract-surface.md), the [permission filter](architecture/adr/ADR-0004-permission-faithful-retrieval.md), the [Model Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md), the [governance gate](architecture/adr/ADR-0012-governance-audit-and-cost.md), per-agent tool-scope) all live *inside* the plan→act loop — and a general agent framework's defining feature is that it **owns that loop and calls tools itself**, i.e. it is a *competing* choke point that would scatter exactly what five cycles consolidated. The template's [`AgentOrchestrator`](../core/orchestrator.py) *already is* the loop (Planner→Governance→Dispatcher→Subagents→Verifier) with multi-agent primitives already present — the [`HandoffRouter`](../core/handoff.py) (allowlisted, schema-validated agent→agent transfer) + the [`WorkerRegistry`](../core/workers.py) (per-agent tool scope); the distributed orchestrator is these primitives **re-hosted** onto the queue-backed topology, exactly as [ADR-0002](architecture/adr/ADR-0002-reuse-existing-template-core.md) foresaw ("concepts transfer, implementation re-hosts") and named in its own "Revisit when". **Two planes:** a *decision plane* (ours, in-boundary — carries O1–O5) + an *execution plane* (adopted commodity durable execution behind the `ExecutionBackend` port, which has **no decision method** — the [`VectorIndex`](storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)/[Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md) "commodity behind a port" bargain reused a third time). **Multi-agent is bounded, not emergent** — a run is a bounded DAG over a *pack-declared, allowlisted* agent graph, installed by the [pack-load SPI](packs/01-pack-load-spi.md) as validated config (one additive validator), so a new domain's multi-agent flow is a pack, not an orchestrator change. Net **horizontal change = none, all additive**: the same five gates in the same order, re-hosted; no new safety predicate, no new choke point, lock-in bounded to one adapter. Wrote [orchestration/00-agent-orchestration.md](orchestration/00-agent-orchestration.md) + [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) + the `orchestration/` folder. **All open architecture questions are now closed** — only the **engineering track** (`core/` code-reconciliation: implement the pack-load SPI + the orchestrator loop) remains.)
- **Superseded current-cycle note (Cycle 22):** (**Model hosting & serving posture — resolves open Q#3.** With the platform surface complete (10 packs Seeded, pack-load SPI designed), the highest-leverage architecture-doc move is closing one of the two remaining open questions. Q#3 asked *where models physically run* — in-boundary OSS vs. contractually-private managed, per tenant tier. Resolved as a **dual-track serving fabric behind the [Model Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md)**: **Track A** (in-boundary self-hosted open-weight models on reserved GPUs — privacy/residency *by physical construction*) + **Track B** (contractually-private managed endpoints over private networking, zero-retention/no-train terms — capability/elastic), with the track selected **per `(tenant tier × data class)`** by the *existing* label→trust matrix. **Isolated tier → Track A only; Standard tier → Track B default with a `confidential`/`pii` floor lifting to the highest-trust track.** Hosting posture becomes a **closed registry enum** (`in_boundary_oss` / `managed_private` / `managed_private_dedicated`) with mandatory data-handling terms — the one open field of [Governance §8](governance/00-governance-and-audit.md#8-g6--model-governance)'s approved-model registry. **Routing is fail-closed:** a `pii` request whose track is down degrades within-or-above its trust floor, never spills to a cheaper track. Net **horizontal change = none, all additive** — two data values (the enum + the per-tier map) + one boundary condition behind the Gateway indirection ADR-0003 already built; no new hot-path component, no new predicate, read plane untouched. Wrote [models/00-model-hosting-and-serving.md](models/00-model-hosting-and-serving.md) + [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md); closes a real doc gap — model *serving* was referenced by ADR-0003/Governance §8/Deployment §7 but had no home. Only Q#6 (orchestrator posture) + the `core/` code-reconciliation remain open.)
- **Superseded current-cycle note (Cycle 21):** (**Runtime pack-load SPI** — the *engineering form* of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md), which named this ADR in its own "Revisit when". The doc contract was fixed (a pack = six additive sections, tighten-only, §0 ledger); this cycle designs *how a pack is loaded at runtime* — a **validating, transactional, fail-closed loader** (RESOLVE → VALIDATE → DRY-RUN → COMMIT-atomic → ACTIVATE-scoped) whose defining property is that a **floor-loosening pack is structurally rejected by the loader, not merely by review**. The safety gate is six validators, each checking a section `⊆` its horizontal extension point; the loader is **safe by construction** because its only verbs are subset-installs into fail-closed extension points (the `VectorIndex` port has no unfiltered method to bind; the label schema is a closed grammar; the matrix composes most-restrictive-wins). A pack loads with **no code deploy** (validated data + a route flip); a pack claiming any horizontal change fails the machine-checked §0 ledger and routes to a human ADR gate. Wrote [packs/01-pack-load-spi.md](packs/01-pack-load-spi.md) + [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md); the SPI's own §0-equivalent ledger is *"none, all additive"* — it writes only into stores that already exist. This is the prerequisite for the `core/` code-reconciliation and the first `platform/`→`core/` mechanism to implement.)
- **Superseded current-cycle note (Cycle 20):** (Domain Pack #10 — Reporting: the first *aggregation* falsifiability test and **the pack that completes the domain-pack surface** — a report is a *derived artifact* reusing DocIntel's inherit-source-ACL rule + SAP BW/Finance fidelity; the sharp new corner is *arithmetic inference* (a total reconstructing a masked row via small-cell/differencing), disarmed **by construction** via the existing **filter-then-aggregate** order, not a disclosure-control engine; cross-source rollup = **intersection, never union**; unresolvable-contributor aggregate = quarantine; 5th pack with empty §2 + §3; held with net zero horizontal change — the 10th consecutive all-additive ledger)
- **Last updated:** 2026-07-06 (Cycle 26)
- **Documentation root:** `platform/` — the single source of truth.
- **Gesamtfortschritt:** **≈ 98 %** (Ende Zyklus 26) — siehe §0.1. **Nach jeder Session melden.**

---

## 0.1 Fortschritt (Gesamtstand, gewichtet)

> Gemessen gegen das Endziel: Doku ausreichend, damit ein Team die komplette Plattform
> ohne zusätzliche Architektur-Vorgabe implementieren kann. **Jeden Zyklus fortschreiben.**

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| Vision & Prinzipien | 10 % | 100 % | 10.0 |
| Security-Architektur (inkl. **Model-Hosting-Posture Z22** — in-boundary vs. contractually-private, fail-closed Routing; **Orchestrierungs-Choke-Points Z23** — die fünf Gates bleiben in-boundary im *Decision-Plane*; **Z25 — die O3/O4/O5-Gates + der deterministische Hard-Block sind jetzt *im Code erzwungen* + negativ-getestet, nicht mehr nur spezifiziert**) | 10 % | 94 % | 9.4 |
| Permissions Deep Dive (Z3) | 12 % | 90 % | 10.8 |
| RAG Deep Dive (Z4) | 12 % | 85 % | 10.2 |
| Storage & Tenancy (Z5) | 10 % | 90 % | 9.0 |
| Workers & Connectors (Z6) | 10 % | 90 % | 9.0 |
| Metadata / Katalog / Lineage (Z8) | 6 % | 90 % | 5.4 |
| Governance / Audit / Kosten (Z7) | 8 % | 85 % | 6.8 |
| API-Surface & Verträge (Z9) | 5 % | 90 % | 4.5 |
| Deployment / Topologie / DR (Z10) | 7 % | 90 % | 6.3 |
| Domänen-Pack-Specs (Finance/HR/Legal/Audit/KM/SAP/SharePoint/Email/DocIntel/Reporting) — **alle 10 seeded, Fläche vollständig** + **Pack-Load-SPI designed (Z21)** | 6 % | 100 % | 6.0 |
| Code-Reconciliation (`core/`-Umsetzung) — **Z26 hat die letzten zwei WPs ausgeführt: WP-A4 (der `run()`-Loop ist gegen den [`ExecutionBackend`](../core/execution.py)-Port re-expressed — `start_run→schedule_step→await_steps`, Behaviour-Parity, `RunSpec` konsolidiert) + WP-C1 (die Legacy-LLM-Pfad-Module mit Mock-Modell-Tests backfilled → Whole-`core`-Coverage 75 %→92,9 %; `pytest.ini` erzwingt `--cov=core --cov-fail-under=80`; neue `.github/workflows/ci.yml`). 131→193 Tests grün, `check.py` exit 0, ruff clean. Die [Definition of Done](engineering/00-core-reconciliation-plan.md#8-definition-of-done) ist vollständig erfüllt — der Engineering-Track ist KOMPLETT.** | 4 % | 100 % | 4.0 |
| **Summe** | **100 %** | — | **≈ 98 %** |

**Verlauf:** Z1 ≈ 18 % · Z2/2b ≈ 24 % · Z3 ≈ 33 % · Z4 ≈ 40 % · Z5 ≈ 49 % · Z6 ≈ 58 % · Z7 ≈ 65 % · Z8 ≈ 71 % · Z9 ≈ 76 % · Z10 ≈ 82 % · Z11 ≈ 84 % · Z12 ≈ 85 % · Z13 ≈ 86 % · Z14 ≈ 87 % · Z15 ≈ 88 % · Z16 ≈ 89 % · Z17 ≈ 90 % · Z18 ≈ 91 % · Z19 ≈ 92 % · Z20 ≈ 93 % · Z21 ≈ 94 % · Z22 ≈ 95 % · Z23 ≈ 96 % · Z24 ≈ 96,5 % · Z25 ≈ 97,5 % · **Z26 ≈ 98 %** (Coding-Cycle — die letzten zwei WPs des Reconciliation-Plans ausgeführt: **WP-A4** — der [`run()`](../core/orchestrator.py)-Loop ist gegen den [`ExecutionBackend`](../core/execution.py)-Port re-expressed (`start_run→schedule_step→await_steps` über den Default-`InProcessExecutionBackend`, statt direktem `dispatcher.dispatch`), mit **Behaviour-Parity** (die 131 vorherigen Tests unverändert grün + ein dedizierter Spy/Parity-Test); `RunSpec` auf eine Definition konsolidiert. Realisiert ADR-0019's „dieselben Primitiven re-hosted" im Code: die Decision-Plane bleibt im Loop, nur das *wann/ob/Retry* eines Steps wanderte hinter den Port — keine neue Entscheidungs-Methode (die Port-Purity-Grep-Invariante hält). **WP-C1** — die Legacy-LLM-Pfad-Module mit Mock-Modell-Tests (monkeypatched `brain.complete`/`brain.evaluate`) backfilled → **Whole-`core`-Coverage 75 %→92,9 %**; `pytest.ini` erzwingt `--cov=core --cov-fail-under=80`; neue `.github/workflows/ci.yml` läuft `check.py` + die gate-gesicherte Suite. **131→193 Tests grün, `check.py` exit 0, ruff clean.** Kein ADR. Die [Definition of Done](engineering/00-core-reconciliation-plan.md#8-definition-of-done) ist vollständig erfüllt — **der Engineering-Track ist KOMPLETT**; verbleibend sind nur Tuning-Inputs, keine offene Architektur- oder blockierende Engineering-Frage.) · Vorheriger Meilenstein — **Z25 ≈ 97,5 %** (Coding-Cycle — der Z24-Plan *ausgeführt* (TDD): die inerten Gates O3/O4/O5 sind im [`run()`](../core/orchestrator.py)-Loop verdrahtet + negativ-getestet (`tool_scope_blocked`/`handoff_refused`); WP-A5 macht den *deterministischen* Hard-Block vor dem `autonomy_level:max`-Shortcut strukturell (ADR-0006); der [`ExecutionBackend`](../core/execution.py)-Port **ohne Entscheidungs-Methode** + `InProcessExecutionBackend` + Port-Purity-Test existieren; und der vollständige [`core/packs/`](../core/packs/)-Loader ist gebaut — **Marquee-Test `test_floor_loosening_bundle_fails_validate` grün** (ADR-0017 im CI bewiesen). **62→131 Tests grün, `check.py` exit 0**, Coverage 80–100 % auf allen gebauten Modulen. Kein ADR (entlädt ADR-0017 + ADR-0019). Offen: WP-A4 (Loop gegen den Port) + WP-C1 (CI-Coverage-Gate).) · Vorheriger Meilenstein — **Z24 ≈ 96,5 %** (Engineering-Track-Bridge — der `platform/`→`core/`-Reconciliation-*Plan*. Alle Architektur-Fragen sind geschlossen, also ist der höchste Hebel keine Entscheidung mehr, sondern die **Build-Order** für die einzige verbleibende gewichtete Lücke. Neuer Ordner **[engineering/](engineering/00-core-reconciliation-plan.md)** — ein Coding-Cycle-Brief, der die zwei vollspezifizierten, aber ungebauten Ziele ([ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md) Pack-Load-Loader + [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) Orchestrator-Re-Host) in einen sequenzierten TDD-Plan überführt, gegründet auf ein **Ground-Truth-Audit von `core/`**. Das Audit förderte die tragende Tatsache zutage, die die Docs allein nicht zeigten: **[`core/orchestrator.py`](../core/orchestrator.py) ruft heute weder [`WorkerRegistry`](../core/workers.py) noch [`HandoffRouter`](../core/handoff.py) auf** — beide sind gebaut + unit-getestet (62 Tests grün), aber **strukturell inert im Run-Loop**; die Tool-Scope- (O3/O5) und Handoff-Gates (O4) sind also codiert-und-getestet, doch nie erzwungen. Der Plan macht das Verdrahten dieser zwei inerten Gates zum höchst-hebligen/niedrigst-riskanten ersten Schritt (WP-A1/A2), vor Port-Extraktion (`ExecutionBackend`) und Pack-Load-Loader (`core/packs/`, dessen Marquee-Akzeptanztest lautet: *ein bodenlockerndes Bundle scheitert an VALIDATE per Code, nicht per Review* — ADR-0017's Schlagzeile im CI bewiesen). Gap-Ledger G1–G8 + Test-Matrix (jeder ADR-Falsifizierbarkeits-Check → ein benannter `pytest`). **Kein neues ADR** (keine Cross-Component-Entscheidung — es *entlädt* zwei). Erstes Beispiel eines wiederverwendbaren *Engineering-Bridge*-Muster (Audit → Gap-Ledger → Target-Design → sequenzierte WPs). Code-Implementierung = Zyklus 25.) · Vorheriger Meilenstein — **Z23 ≈ 96 %** (Agent-Orchestrierung / Orchestrator-Posture — die Auflösung von **Q#6**, der **letzten offenen Architektur-Frage**: *das bestehende `core/`-Planner/Verifier zum verteilten Orchestrator erweitern oder ein Framework adoptieren?* Antwort: **`core/` erweitern** — die Orchestrierungs-*Logik und die Choke-Points bleiben unser und in-boundary* — und für die *verteilte Klempnerei allein* (durable State, Retries, Timer, Fan-out) ein Commodity-Substrat hinter einem schmalen `ExecutionBackend`-Port adoptieren; **kein** Framework, das den Plan→Act-Loop, das Tool-Calling, das Routing oder das Antwort-Gate besitzt. Der tragende Grund: die fünf Choke-Points der Plattform (ein [Verifier-Antwort-Gate](architecture/adr/ADR-0014-api-contract-surface.md), der [Permission-Filter](architecture/adr/ADR-0004-permission-faithful-retrieval.md), das [Model Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md), das [Governance-Gate](architecture/adr/ADR-0012-governance-audit-and-cost.md), der Per-Agent-Tool-Scope) leben *innerhalb* des Loops — und das Kernmerkmal eines Agent-Frameworks ist, dass es **genau diesen Loop besitzt und selbst Tools aufruft**, also ein *konkurrierender* Choke-Point wäre, der zerstreut, was fünf Zyklen konsolidiert haben. Der Template-[`AgentOrchestrator`](../core/orchestrator.py) *ist bereits* der Loop, mit den Multi-Agent-Primitiven schon vorhanden — dem [`HandoffRouter`](../core/handoff.py) (allowlisted, schema-validierter Agent→Agent-Transfer) + der [`WorkerRegistry`](../core/workers.py) (Per-Agent-Tool-Scope); der verteilte Orchestrator ist diese Primitiven **auf die queue-basierte Topologie re-hosted**, genau wie [ADR-0002](architecture/adr/ADR-0002-reuse-existing-template-core.md) es vorsah („Konzepte transferieren, Implementierung re-hosted") und in seinem eigenen „Revisit when" benannte. **Zwei Planes:** *Decision-Plane* (unser, in-boundary — trägt O1–O5) + *Execution-Plane* (adoptierte Commodity-Durable-Execution hinter dem `ExecutionBackend`-Port, der **keine Entscheidungs-Methode** hat — die [`VectorIndex`](storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)/Gateway-Bargain „Commodity hinter einem Port" zum dritten Mal wiederverwendet). **Multi-Agent ist bounded, nicht emergent** — ein Run ist ein bounded DAG über einen *pack-deklarierten, allowlisted* Agent-Graphen, per [Pack-Load-SPI](packs/01-pack-load-spi.md) als validierte Config installiert (ein additiver Validator), also ist der Multi-Agent-Flow einer neuen Domäne ein Pack, keine Orchestrator-Änderung. Netto **horizontale Änderung = keine, rein additiv**: dieselben fünf Gates in derselben Reihenfolge, re-hosted; kein neues Sicherheits-Prädikat, kein neuer Choke-Point, Lock-in auf einen Adapter begrenzt. [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md). **Alle offenen Architektur-Fragen sind jetzt geschlossen** — nur der **Engineering-Track** (`core/`-Code-Reconciliation: Pack-Load-SPI + Orchestrator-Loop implementieren) verbleibt.) · Vorheriger Meilenstein — **Z22 ≈ 95 %** (Model-Hosting-Posture — die Auflösung von **Q#3**, einer der letzten zwei offenen Architektur-Fragen: *wo* Modelle physisch laufen. Antwort: **Dual-Track-Serving-Fabric hinter dem [Model Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md)** — **Track A** (in-boundary self-hosted OSS auf reservierten GPUs; Privatheit/Residenz *durch physische Konstruktion*) + **Track B** (contractually-private Managed Endpoints über Private Networking, Zero-Retention/No-Train) — Track-Wahl **pro `(Tenant-Tier × Datenklasse)`** über die *bestehende* Label→Trust-Matrix. Isolated → nur Track A; Standard → Track B Default mit `confidential`/`pii`-Boden auf den höchst-vertrauten Track. Hosting-Posture wird ein **geschlossenes Registry-Enum** mit Pflicht-Datenverarbeitungs-Terms; Routing ist **fail-closed** (kein stiller Fallback auf einen niedriger-vertrauten Track). Netto **horizontale Änderung = keine, rein additiv** — zwei Datenwerte + eine Randbedingung hinter der Gateway-Indirektion, die ADR-0003 bereits gebaut hat; kein neuer Hot-Path, kein neues Prädikat, Read-Plane unberührt. „Schwer zu *entscheiden*, trivial zu *verdrahten*" — das Gütezeichen der frühen ADR-0003-Entscheidung. Schließt zugleich eine echte Doku-Lücke: Model-*Serving* hatte bislang kein eigenes Verzeichnis. [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md)) (Pack-Load-SPI — der **Übergang von der Papier- zur Laufzeit-Fähigkeit**: der *validierende, transaktionale, fail-closed* Loader, der die sechs Pack-Sektionen in ihre horizontalen Erweiterungspunkte installiert und **jeden bodenlockernden Pack strukturell ablehnt** — nicht per Review, sondern per Konstruktion, weil die einzigen Verben des Loaders Subset-Installationen in fail-closed-Erweiterungspunkte sind. Kein neuer Hot-Path; das §0-Äquivalent-Ledger des SPI selbst ist *"none, all additive"*. Erstes konkretes `platform/`→`core/`-Umsetzungsziel; [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)) · Verlauf-Fortsetzung: **Z20 ≈ 93 %** (Reporting-Pack — n=10, der **letzte** Pack; die **Domänen-Pack-Fläche ist damit vollständig**. Der **erste *Aggregat*-Test**: ein Report-Wert ist selten eine Quellzeile, sondern ein **Rollup** über viele Zeilen mit *heterogenen* ACLs. Der scharfe neue Fehlermodus, den kein früherer Pack hatte, ist **arithmetische Inferenz** — eine Summe kann eine maskierte Zeile *rekonstruieren* (Small-Cell/Differencing: eine Gehaltssumme über *eine* Person **ist** deren Gehalt). Kernbefund: entschärft **durch Konstruktion, nicht durch eine Disclosure-Control-Engine** — die Plattform **filtert Zeilen *vor* dem Aggregieren** ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)), also ist jedes ausgelieferte Total eine Funktion von Zeilen, die der Aufrufer ohnehin einzeln lesen dürfte → ein Total verrät nie etwas Neues. *filter-then-aggregate*, nie *aggregate-then-filter* — Letzteres ist die Naht, durch die Aggregation leckt, und dieser Codepfad **existiert nicht**. Ein **vor-materialisierter** Report trägt die **eigene Quell-ACL** ([SAP Band-A](packs/sap/00-sap-pack.md)); ein **quellen-übergreifender** Rollup trägt die **Schnittmenge** (most-restrictive, DocIntel-Merge — nie die Vereinigung); ein Aggregat über einen *nicht auflösbaren* Beitragssatz wird **quarantänisiert**. **5. Pack mit leerem §2 + §3** (ein Report *präsentiert* die Policy der reitenden Domäne, besitzt keine eigene). §2/§3 leer, §4 vollständig geerbt (jede beitragende Domäne — eine Kachel aus Finance-Ledger + HR-Headcount ist SOX *und* Art. 9). Kein neues ADR (Worked Instance von [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). Der **eine benannte zukünftige ADR**: ein Total über Zeilen *ausliefern*, die der Aufrufer nicht einzeln lesen darf (statistische Disclosure Control / Differential Privacy) — heute bewusst außerhalb des Scopes, quarantänisiert. **Verbleibend: keine Packs mehr** — der Engineering-Track (runtime pack-load SPI, Code-Reconciliation) und die offenen Q#3/Q#6 sind der einzige verbleibende Weg)) (Document-Intelligence-Pack — n=9; der **erste *derived-content*-Test** und das erste nicht-leere §2 seit Legal. Kernbefund: die Plattform *fabriziert* nie eine Autorisierungs-Tatsache — ein abgeleitetes Artefakt **erbt** die ACL des Quell-Items über die [Lineage](metadata/00-catalog-and-lineage.md) (Mehrfachquellen-Merge = **Schnittmenge/Split/Quarantäne, nie Vereinigung**), und ein *abgeleitetes* Label darf nur **verschärfen**, ist **fail-closed** bei geringer Klassifikator-Konfidenz und wird provenienz-gestempelt (`label_source: derived`). Ein falsches Ableiten kostet **Verfügbarkeit, nie Sicherheit** — weil ein Label nur Fähigkeit *subtrahiert* und die ACL, nicht das Label, das primäre Tor ist. Die einzige Metadata-Berührung (`LineageNode.kind` für einen sekundären abgeleiteten Index) ist das *additive* Knoten-Typ-Wachstum, das [Metadata §9](metadata/00-catalog-and-lineage.md) bereits genau für diesen Fall benannt hat — **kein Vertragsbruch**. Der eine harte Fall (ein abgeleitetes Sub-Item, dessen korrekte ACL enger und unauflösbar ist) reitet auf dem bestehenden `approximate → deny + quarantine`-Pfad. Verbleibend: der concept-shaped **Reporting**-Pack + die runtime pack-load SPI (Engineering-Track)) (Email-Pack — n=8; der **dritte und *letzte* source-shaped Pack** und der *einfachste* aller Quellen: die ACL einer Nachricht ist ihr **Postfach-Eigentümer + Delegierte**, nie ihr Transport-Publikum. Der *transport-vs-storage*-Falsifizierbarkeitstest: wird je eine Transport-Tatsache (To/Cc/Bcc, Verteiler-Mitgliedschaft, ein weitergeleiteter Thread) still zu einem Lese-Grant auf die archivierte Kopie? **Nein** — jedes Konstrukt → `allow`/`deny`/Quarantäne, das Publikum wird als *Inhalt* (Header) erfasst, nie als Grant. **Vierter Pack mit leerem §2 + §3**; **kein Band C, keine Sharing-Link-Fläche** → die kürzeste §1-Matrix. Konsolidiert die 3× ad-hoc behauptete Email-Fidelity (HR/Legal/Audit) in eine kanonische §1. **Die Source-Pack-Fläche ist damit vollständig** — verbleibend: die concept-shaped Packs Document Intelligence/Reporting + die runtime pack-load SPI (Engineering-Track)) (SharePoint-Pack — n=7; der **zweite *source-shaped* Pack und SAPs *Spiegelbild***: SAPs Risiko war *zu viel quarantänisieren* (keine Dokument-ACL); SharePoints Risiko ist das gefährlichere Gegenteil — ein **stiller *Über*-Grant**. Der *inverse* Falsifizierbarkeitstest: passt jedes SharePoint-Sharing-Konstrukt (gebrochene Vererbung, Sharing-Links, **"Anyone"-Links, Gäste, dynamische Gruppen, MIP-Labels**) in `allow`/`deny`/geflaggter-Grant/Quarantäne — *ohne* je stillschweigend Zugriff zu erweitern und *ohne* neue Prinzipal-Kategorie oder neues Prädikat? **"Anyone"-Link → flag-and-fail-closed, nie stiller Public-Grant.** **Dritter Pack mit leerem §2 + §3**; **kein Band C** (ACL ist item-level → strukturell kürzer als SAP). Konsolidiert die bisher 5× ad-hoc behauptete SharePoint-Fidelity in **eine kanonische §1**. Email bleibt der letzte Source-Pack (noch kürzer — keine Sharing-Link-Fläche)).

---

## 0. How to run a cycle (process reminder)

1. Read every Markdown file under `platform/` (start with this file).
2. Do the **highest-priority open item** in §6 — not everything.
3. Create/extend Markdown docs (each answers Why / How / Trade-offs / Alternatives /
   Future scalability). Prefer **extending** existing docs over duplicating.
4. If a decision shapes >1 component, add an ADR under
   `architecture/adr/` and link it.
5. Update this file: move items Completed, add new risks/questions, re-prioritize.

---

## 1. Completed work

### Cycle 26 (2026-07-06) — Coding cycle: **finished the orchestrator re-host + locked the coverage floor — engineering track COMPLETE**
- Executed the [reconciliation plan](engineering/00-core-reconciliation-plan.md)'s **last two work packages**;
  the engineering-track [Definition of Done](engineering/00-core-reconciliation-plan.md#8-definition-of-done)
  is now **fully met.** Wrote the [Cycle-26 implementation report](engineering/02-cycle-26-implementation-report.md).
  **No ADR** (discharges the last of [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)).
- **WP-A4 (G4) — `run()` re-expressed against the `ExecutionBackend` port.** Each plan step's *execution* is
  routed through the default [`InProcessExecutionBackend`](../core/execution.py) via
  `start_run → schedule_step → await_steps`, instead of a direct `self.dispatcher.dispatch(...)` call. A new
  `_dispatch_activity` helper performs the dispatch and boxes the full `DispatchResult` in
  `StepResult.metadata["dispatch"]`, so the loop recovers the exact object it had pre-port — **behaviour parity.**
  `RunSpec` was consolidated to a single definition in [`core/execution.py`](../core/execution.py) and
  re-exported from [`core/orchestrator.py`](../core/orchestrator.py) (`from core.orchestrator import RunSpec`
  still works). *Falsifiability check — does re-hosting change any observable output? **No:*** the 131 prior
  tests pass **unchanged**, and `test_orchestrator_execution.py` asserts a spying backend yields the same
  `success`/`outputs`/`dispatch_count`/`run_id` as the default **and** that the port is actually driven (parity
  is not achieved by bypassing it). Realizes ADR-0019's "same primitives re-hosted": the decision plane stays
  in the loop, only the *when/whether/retry* of a step moved behind a port that still has **no decision method.**
- **WP-C1 — coverage floor locked in CI.** Backfilled the legacy LLM-path modules with **mocked-model** tests
  (monkeypatched `brain.complete`/`brain.evaluate`, deterministic regardless of env/API keys):
  `test_dispatcher.py` (6), `test_governance.py` (16), `test_verifier.py` (9), `test_planner.py` (15),
  `test_subagents.py` (12), `test_orchestrator_execution.py` (6, incl. 2 parity regressions). Per-module coverage: `verifier` 25→97 %,
  `subagents` 28→94 %, `planner` 54→89 %, `governance` 66→96 %, `dispatcher` 74→100 % — **whole-`core`
  75 % → 92.9 %.** [`pytest.ini`](../pytest.ini) now enforces `--cov=core --cov-report=term-missing
  --cov-fail-under=80`; a new [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs `tools/check.py`
  (non-strict — the template's `autonomy_level: max` is an intentional WARN, not an error) + the gated suite on
  every push/PR.
- **Parity hardening (adversarial code review, pre-merge).** The first WP-A4 draft was **not** fully
  parity-preserving on the production path — an in-review finding, now fixed. The `ExecutionBackend` caches
  step results by `(run_id, step_id)` as a deliberate replay feature; combined with the Cycle-25 default that
  derived `request_id` from the *task text*, a **long-lived orchestrator** ([`agent.py`](../agent.py) holds one
  singleton) running the same task twice reused the same `run_id` and **replayed the first run's cached result,
  silently skipping side-effecting re-execution.** Fixed: an omitted `request_id` now defaults to a **fresh
  unique id per invocation** (`uuid4`) — each `run()` is a distinct request. A second, narrower fix disambiguates
  the execution key on a per-run **sequence number** so two plan steps sharing an id can't collide. Both are
  covered by new regressions (`test_each_run_gets_a_distinct_identity`,
  `test_repeated_task_on_same_orchestrator_reexecutes_side_effects` — asserts the tool runs twice,
  `test_duplicate_plan_step_ids_do_not_collide_in_backend`); the Cycle-25 test that pinned the deterministic
  `request_id` (which had encoded the defect) was corrected to assert per-invocation uniqueness.
- **Quality gates:** **131 → 193 tests green (+62)**, `tools/check.py` exit 0, ruff clean (`core/` + `tests/`;
  also fixed two pre-existing unused-import lints). The tree was never broken.
- **Directly strengthens (no new risk owned):** turns the ADR-0019 "commodity behind a port" claim into
  *running code with a parity proof*, and makes the whole-`core` 80 % floor a **machine-enforced CI gate**
  rather than a per-module aspiration — hardening confidence in the Security posture's now-in-code gates.
- ✅ **Nothing handed forward on the engineering track** — it is complete. Remaining items are pure tuning
  inputs: the distributed `ExecutionBackend` adapter (Temporal-class, out-of-`core/` by design; sizing →
  [Deployment §7](deployment/00-deployment-topology.md)) and onboarding-UX polish (§6 Cycle 2c.4).

### Cycle 25 (2026-07-06) — Coding cycle: **executed** the `core/` reconciliation plan (TDD)
- The **first cycle that ships code, not docs.** Followed the
  [reconciliation plan](engineering/00-core-reconciliation-plan.md) work-package order and closed the
  Cycle-24 audit's load-bearing finding: **[`core/orchestrator.py`](../core/orchestrator.py) now calls both
  [`WorkerRegistry`](../core/workers.py) and [`HandoffRouter`](../core/handoff.py) in the run loop.** The
  tool-scope (O3/O5) and handoff (O4) gates went from *coded-and-tested-but-inert* to **enforced at runtime,
  covered by negative tests.** Wrote the [Cycle-25 implementation report](engineering/01-cycle-25-implementation-report.md).
- **Front A (orchestrator re-host):**
  - **WP-A1 (G1)** — tool-scope gate wired into `run()`: the acting worker's `WorkerRegistry` scope is
    enforced *in the loop* (`_acting_worker` + pre-dispatch `check_permission` + `filter_tools`); an
    out-of-scope tool returns `status: tool_scope_blocked`. (`test_orchestrator_tool_scope.py`, 5 tests.)
  - **WP-A2 (G2)** — handoff gate wired in: a handoff in a step's output is validated (allowlist + payload
    bound) **before** control could transfer; invalid → `status: handoff_refused`.
    (`test_orchestrator_handoff.py`, 4 tests.)
  - **WP-A5 (G5)** — governance-order hardening in [`core/governance.py`](../core/governance.py): a
    **deterministic** destructive/irreversible hard-block class is evaluated **before** the
    `autonomy_level: max` shortcut, unconditional unless an explicit `hard_block_on_high_risk: false` opt-out.
    ADR-0006 "escalation is a deterministic policy decision, not an LLM `needs_human` flag" made structural.
    (`test_governance_order.py`, 7 tests.) *Behavior change:* a destructive task now hard-blocks even under
    the template's default `autonomy_level: max` (the intended fail-closed posture).
  - **WP-A3 (G3)** — [`core/execution.py`](../core/execution.py): the `ExecutionBackend` **Protocol with no
    decision method** + default `InProcessExecutionBackend`; a port-purity grep-invariant is a test
    (`test_execution_port.py`, 8 tests). **G4** — run identity: `run()` accepts `tenant`/`request_id` and
    synthesizes a `RunSpec` keyed `(tenant_id, request_id)` when absent (CLI path unbroken).
- **Front B (pack-load loader `core/packs/`) — complete:** [`bundle.py`](../core/packs/bundle.py) (RESOLVE:
  signed, content-addressed, data-only) → [`validators.py`](../core/packs/validators.py) (six validators, one
  tighten-only invariant) + [`ledger.py`](../core/packs/ledger.py) (§0 machine-check → human-ADR route) →
  [`dryrun.py`](../core/packs/dryrun.py) → [`loader.py`](../core/packs/loader.py) (atomic COMMIT; partial
  install unrepresentable) → [`activation.py`](../core/packs/activation.py) (tenant-scoped, `pack_version`
  pinning, **fail-closed unload**). **The marquee acceptance test passes:
  `test_pack_validate.py::test_floor_loosening_bundle_fails_validate` — a floor-loosening bundle is rejected by
  code (`rejected_by == "§3 tighten-only validator"`), not review** — [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)'s
  headline proven in CI. Plus atomicity (mid-VALIDATE/mid-COMMIT failure installs zero sections) and
  fail-closed unload. (`test_pack_{bundle,validate,atomic,activation}.py`, 40 tests.)
- **Quality gates:** **62 → 131 tests green (+69)**, `tools/check.py` exit 0; coverage 80–100 % on all
  built/changed modules (`core/packs/*` 96–100 %, `core/execution.py` 96 %, `core/orchestrator.py` 80 %). Every
  work package kept the full suite green — **the tree was never broken.** **No ADR** (discharges ADR-0017 +
  ADR-0019). New files lint-clean (ruff).
- **Directly strengthens (no new risk owned):** hardens the **Security-Architektur** posture — the O3/O4/O5
  gates and the ADR-0006 hard block are now *enforced in code and negative-tested*, not merely specified — and
  makes ADR-0017's tighten-only claim a **named CI test** rather than a review convention.
- ⏳ **Handed to Cycle 26:** **WP-A4** — re-express `run()` against the `InProcessExecutionBackend` (behaviour
  parity; the port + `RunSpec` already exist, so it is a mechanical seam swap). **WP-C1** — add the
  `--cov=core --cov-fail-under=80` gate to `pytest.ini`/CI (GitHub Actions), after backfilling coverage on the
  legacy `planner`/`brain`/`subagents` LLM paths (mocked-model tests) so the whole-`core` floor holds.

### Cycle 24 (2026-07-06) — Engineering-track bridge: the `platform/`→`core/` reconciliation **plan**
- Wrote the new **[engineering/](engineering/README.md)** concern folder +
  **[engineering/00-core-reconciliation-plan.md](engineering/00-core-reconciliation-plan.md)** — the
  **engineering projection** of the architecture. With every architecture question (Q#1–Q#7) closed and
  the 12-surface platform complete, the highest-leverage move is no longer a *decision* but the **build
  order** for the sole remaining weighted gap (code-reconciliation, §0.1). This doc discharges the two
  fully-specified-but-unbuilt targets into a sequenced, test-first plan grounded in the real `core/` code.
  **No ADR** — it introduces no cross-component decision; it *discharges* [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)
  and [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md).
- **The load-bearing finding (a ground-truth `core/` audit, not derivable from the docs):**
  **[`core/orchestrator.py`](../core/orchestrator.py) imports and calls neither
  [`WorkerRegistry`](../core/workers.py) nor [`HandoffRouter`](../core/handoff.py).** Both are fully built,
  configured, and unit-tested (62 tests green) but **structurally inert in the run loop** — so the platform's
  tool-scope gate (O3/O5) and handoff gate (O4) are *coded-and-tested yet never enforced at runtime*. This is
  the concrete meaning of ADR-0019's "re-host the primitives" and the still-open
  [Cycle 2c](#-cycle-2c-open--parallel-engineering-track-not-the-architecture-doc-path) item, made precise.
- **The plan's spine:**
  - **§1 ground truth** — maps the five choke points onto the actual `run()` loop (governance + verifier are
    live; tool-scope + handoff are inert; the permission filter is out of the template's toy-loop scope).
  - **§2 gap ledger (G1–G8)** — each ADR requirement vs. its code reality, sorted into two independent build
    fronts: **Front A** (orchestrator re-host — wire the inert gates, then lift onto the port) and **Front B**
    (the `core/packs/` loader).
  - **§3 Target A** — *wire before you distribute*: WP-A1/A2 make `WorkerRegistry`/`HandoffRouter` live
    (highest-leverage, zero new dependency), WP-A5 hardens governance order (hard-block before the autonomy
    shortcut — ADR-0006), then WP-A3/A4 introduce the `ExecutionBackend` Protocol (**no decision method**, a
    CI grep-invariant) with a default in-process adapter proving behaviour parity.
  - **§4 Target B** — the six-module `core/packs/` loader (RESOLVE→VALIDATE→DRY-RUN→COMMIT→ACTIVATE); six
    validators = one *tighten-only* invariant; the **marquee acceptance test** is
    `test_floor_loosening_bundle_fails_validate` — ADR-0017's "structurally rejected by the loader, not by
    review" **proven in CI**, plus atomicity (partial install unrepresentable) and fail-closed unload.
  - **§5 sequenced WPs** (A1→A2→A5→B1→B2→B3→A3→A4→B4→C1), **§6 test matrix** (each ADR falsifiability check →
    a named `pytest`), **§8 definition-of-done** (gate on `--cov=core --cov-fail-under=80`; never push a broken tree).
- **Directly strengthens (no new risk owned):** turns two ratified-but-inert gates into a scheduled,
  test-covered wiring (hardens the Security posture — the O3/O4/O5 gates become *enforced*, not merely
  *specified*), and makes ADR-0017's tighten-only claim a named CI test rather than a review convention.
- **Pattern seeded:** the *engineering-bridge* doc shape (audit → gap ledger → target design → sequenced TDD
  WPs) is the reusable template for every future `platform/`→`core/` reconciliation.
- ⏳ **Handed to Cycle 25 (the coding cycle):** execute the WPs in order, TDD, keeping the tree green. The
  architecture-doc track has **no open item** — only tuning inputs (substrate/GPU-pool sizing → Deployment §7;
  Track-B + handoff-edge hardening → Security) remain as pure-doc refinements.

### Cycle 23 (2026-07-06) — Agent orchestration posture: **resolves open Q#6 — the last open architecture question**
- Wrote **[orchestration/00-agent-orchestration.md](orchestration/00-agent-orchestration.md)** +
  **[ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)** + the **`orchestration/`
  concern folder** ([README](orchestration/README.md)) — closing **open Q#6**, the **last open architecture
  question** on the platform surface. With Q#3 closed (Cycle 22), Q#6 was the only remaining doc-track item:
  *extend the existing `core/` planner/verifier into the distributed orchestrator, or adopt a framework?*
- **The headline: extend `core/` — the orchestration *logic and choke points stay ours and in-boundary* —
  and adopt commodity durable execution behind an `ExecutionBackend` port for the distributed plumbing only;
  consistent with every cycle since ADR-0016, net horizontal change = none, all additive.**
  - **The load-bearing reason (§1 "the load-bearing observation").** The platform's five choke points —
    one [verifier answer gate](architecture/adr/ADR-0014-api-contract-surface.md), the
    [permission filter](architecture/adr/ADR-0004-permission-faithful-retrieval.md), the
    [Model Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md), the
    [governance gate](architecture/adr/ADR-0012-governance-audit-and-cost.md), and per-agent tool-scope —
    all live **inside** the plan→act loop. A general agent framework's defining feature is that it **owns
    that loop and calls tools itself** — i.e. it is a *competing* choke point that would scatter exactly what
    five cycles consolidated. Owning the ~200-line loop is the price of keeping the gates un-bypassable.
  - **Two planes, cleanly split.** A **decision plane** (ours, in-boundary — what to do next, whether it is
    allowed, whether the result is good enough, who may hand off to whom; carries safety invariants O1–O5) +
    an **execution plane** (adopted commodity durable execution — state/retries/timers/fan-out/resume —
    behind an `ExecutionBackend` port that has **no decision method**: it cannot plan, pick a tool, call a
    model, or emit an answer, exactly as the [`VectorIndex` port has no unfiltered-search method](storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)).
  - **We already have the multi-agent primitives, fail-closed.** The template's [`AgentOrchestrator`](../core/orchestrator.py)
    *is* the loop (Planner→Governance→Dispatcher→Subagents→Verifier); the [`HandoffRouter`](../core/handoff.py)
    is allowlisted + schema-validated agent→agent control transfer; the [`WorkerRegistry`](../core/workers.py)
    is per-agent tool-scope. The distributed orchestrator is these **re-hosted** onto the queue-backed
    topology — the *predicates* (allowlist, schema, tool-scope, verifier threshold, governance risk) are
    unchanged, so **no new safety predicate** is introduced.
  - **Multi-agent is bounded, not emergent.** A run is a bounded DAG over a **pack-declared, allowlisted**
    agent graph (auditability + fail-closed + blast-radius), installed by the [pack-load SPI](packs/01-pack-load-spi.md)
    as validated config (one additive validator: agent-graph ⊆ allowlisted-targets). A new domain's
    multi-agent flow is a **pack, not an orchestrator change** — the founding bet applied to orchestration.
- **The orchestration falsifiability check** (mirroring the pack/SPI rules): *can a sub-agent emit an answer
  without the single verifier gate, or call a tool outside its `WorkerRegistry` scope, or hand off to an
  unlisted target?* — **no to all three, structurally.** That "no" is the proof the extension is additive.
- **Why nothing horizontal changed:** the distributed orchestrator enforces the *same* five gates in the
  *same* order as the in-process loop; distribution changes *where* a step runs, never *whether* it passes a
  gate. No new choke point (the existing ones stay single), no new hot-path lock-in (the only adopted
  component is the `ExecutionBackend`, confined to one adapter — the `VectorIndex`/Gateway pattern reused a
  **third** time), and multi-agent workflows are pack-declared config. **This is the payoff of
  [ADR-0002](architecture/adr/ADR-0002-reuse-existing-template-core.md)** — "concepts transfer, implementation
  re-hosts," written Cycle 1, discharged here; hard to *decide* (a fashionable framework is tempting), trivial
  to *wire* (the primitives already exist).
- **This is a cross-component decision → [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)**
  (it constrains security/api/governance/packs/deployment at once). Updated indexes: ADR index (0019 added),
  `platform/README.md` domain map (new `orchestration/` row, Q#6 resolved), open-questions §3 (Q#6 → DECIDED).
- **Directly strengthens (no new risk owned):** hardens the **Security-Architektur** posture (the five gates
  are now specified to remain in-boundary in the decision plane, not delegated to a framework) and R7
  (orchestration lock-in bounded to one `ExecutionBackend` adapter — the model/vector analogue). Adds an
  **orchestration conformance/eval class** (no sub-agent answers without the verifier gate; no out-of-scope
  tool call; no unlisted handoff) — the orchestration analogue of the permission-negative conformance class.
- ⏳ **Handed to later cycles:** the **`core/` implementation** — re-host `AgentOrchestrator` onto the
  `ExecutionBackend` port, alongside the [pack-load SPI](packs/01-pack-load-spi.md) implementation (the **two**
  first `platform/`→`core/` reconciliation targets, both now fully specified). Substrate **sizing** per tier →
  [Deployment](deployment/00-deployment-topology.md); handoff-edge hardening (intra-boundary trust edge) →
  [Security](security/00-security-architecture.md). **All open architecture questions (Q#1–Q#7) are now
  closed** — only the engineering track remains.

### Cycle 22 (2026-07-06) — Model hosting & serving posture: **resolves open Q#3**
- Wrote **[models/00-model-hosting-and-serving.md](models/00-model-hosting-and-serving.md)** +
  **[ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md)** — closing **open Q#3**
  (model hosting), one of only two remaining open architecture questions, and creating the **`models/`
  concern folder** (a real doc gap: model *serving* was cited by [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md),
  [Governance §8](governance/00-governance-and-audit.md#8-g6--model-governance), and
  [Deployment §7](deployment/00-deployment-topology.md) but never had a home). With the pack surface
  complete, this was the **highest-leverage pure-architecture-doc move.**
- **The headline: a dual-track serving fabric, routed per `(tenant tier × data class)` behind the Model
  Gateway — and, consistent with every cycle since ADR-0016, net horizontal change = none, all additive.**
  - **Track A — in-boundary self-hosted OSS:** open-weight models on **reserved GPUs inside the trust
    boundary**. Privacy and residency hold **by construction** (no endpoint to egress to) — the posture
    for the **Isolated tier** and for `confidential`/`pii` on any tenant. Cost: reserved-GPU fixed spend
    + model-ops burden + a possible frontier-capability gap.
  - **Track B — contractually-private managed endpoint:** a managed service over **private networking**
    under **zero-retention / no-training** terms (`managed_private_dedicated` for single-tenant). Frontier
    capability + elastic; privacy by **contract + network isolation**, not physical possession. The default
    for **Standard**-tier `public`/`internal` bulk.
  - **Routing = the existing label→trust matrix, tighten-only.** Isolated → **Track A only**; Standard →
    **Track B default with a `confidential`/`pii` floor** lifting to the highest-trust track. A tenant may
    pin stricter, never route a sensitive class down (the [admin-can-only-tighten](architecture/adr/ADR-0014-api-contract-surface.md)
    rule applied to model routing).
- **Q#3 was literally the open `hosting_posture` field of [Governance §8](governance/00-governance-and-audit.md#8-g6--model-governance)'s
  approved-model registry.** It is now a **closed enum** — `in_boundary_oss` / `managed_private` /
  `managed_private_dedicated` — and a `managed_private*` entry **must** carry its data-handling terms
  (DPA / retention=0 / training=none / sub-processors) or the eval gate refuses promotion. This turns
  "contractually private" from a verbal assurance into a **recorded, auditable, eval-gated fact.**
- **Fail-closed routing (the safety crux).** If the required track is unavailable, the request degrades
  *within-or-above* its trust floor, is queued, or is denied — it **never** spills to a lower-trust track.
  A `pii` prompt whose Track A pool is saturated does **not** fall back to Track B. This is the
  model-serving projection of the platform-wide invariant: *capability/availability may degrade; the trust
  floor may not* ([Governance §7.3](governance/00-governance-and-audit.md), R5).
- **Why nothing horizontal changed:** the two tracks are *serving endpoints behind the existing Gateway*;
  the registry, the label matrix, and the routing policy already exist. The cycle fixes **two data values**
  (the enum + the per-tier×class map) and **one boundary condition** (fail-closed fallback). Callers are
  unchanged — they request a logical role and never learn which track answered (M2). The read/ACL plane is
  untouched (the filter runs *before* any model sees content, [ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)):
  a mis-hosted model can, at worst, cost capability or (if fail-closed were broken) reach *a vendor under
  contract*, never widen a user's read access. **"Both, by tier" is expressible as pure policy only because
  [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md) built the Gateway indirection first —
  hard to *decide*, trivial to *wire*; the sign of a good earlier decision.**
- **This is a cross-component decision → [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md)**
  (it constrains Governance/Security/Deployment/Data at once). Updated indexes: ADR index (0018 added),
  Governance §8 (hosting-posture field resolved + routing-map link), `platform/README.md` domain map (new
  `models/` row, Q#3 resolved).
- **Directly strengthens (no new risk owned):** hardens the **Security-Architektur** posture (in-boundary
  vs. contractually-private is now specified, not deferred) and R7 (Track B vendor lock-in bounded to one
  Gateway adapter — the model analogue of the `VectorIndex` port). Adds a **model-routing conformance/eval
  class** (no `pii` fixture ever routes to a `managed_private` posture) — the routing analogue of the
  permission-negative conformance class.
- ⏳ **Handed to later cycles:** **empirical sizing → [Deployment §7](deployment/00-deployment-topology.md)**
  (Track A reserved-GPU pool sizing as a reserved-capacity class alongside reserved-P0; Track B endpoint
  pricing/region routing → the D4 pricing manifest) and **network-boundary hardening → [Security](security/00-security-architecture.md)**
  (Track B PrivateLink/VPC-peering + zero-egress verification; Track A GPU-pool tenant isolation). Only
  **Q#6** (orchestrator posture — extend `core/` vs. adopt) and the **`core/` code-reconciliation** (Cycle 22
  SPI-implementation candidate / Cycle 2c engineering track) remain open.

### Cycle 21 (2026-07-06) — Runtime pack-load SPI: the engineering form of ADR-0016
- Wrote **[packs/01-pack-load-spi.md](packs/01-pack-load-spi.md)** + **[ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)** —
  the **first cycle off the domain-pack track and onto the engineering track.** With the
  [domain-pack surface complete](packs/README.md) (Cycle 20), the highest-leverage move is the piece that
  turns ten *proven paper packs* into a *runtime capability*: the **code mechanism that loads a pack**.
  [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) fixed *what a pack is allowed to be* and
  **named this ADR in its own "Revisit when"**; this cycle discharges it.
- **The headline: the loader is a safety gate, and its defining property is that a floor-loosening pack is
  *structurally rejected by the loader*, not merely by review.** The SPI's own falsifiability check (mirroring
  the pack falsifiability rule) — *can a pack load with no code deploy, and is a floor-loosening pack rejected
  structurally?* — resolves **yes to both**:
  - **The pack artifact is a signed, versioned, content-addressed bundle** (not the Markdown spec) carrying the
    machine-readable projection of the six sections — **data + declarative config only, no read-path code.** A
    pack *references* an already-built, independently conformance-gated Connector; it never ships one (new
    connector code is a platform PR through the connector gate, keeping "load a pack" down to "install validated
    config," never "run untrusted code on the retrieval path").
  - **The load lifecycle is a staged, transactional pipeline** — RESOLVE → VALIDATE → DRY-RUN → COMMIT(atomic)
    → ACTIVATE(tenant-scoped) — mirroring the [ingestion DAG](workers/00-ingestion-architecture.md). **All six
    sections commit in one transaction or none do:** partial installation is the one state that could
    transiently loosen a floor, so it is made unrepresentable.
  - **VALIDATE is six validators, one invariant.** Each section is checked `⊆` its extension point (§1 fixtures
    against the [conformance suite](permissions/00-authorization-model.md#11-the-permission-conformance-test-the-production-gate);
    §2 values against the [closed label grammar](metadata/00-catalog-and-lineage.md#4-the-classification--label-schema-m3);
    §3 deltas against the [label→action matrix](governance/00-governance-and-audit.md#41-the-labelaction-matrix-the-ratified-default-tenants-may-tighten-never-loosen),
    tighten-only; §4/§5/§6 similarly). The composite invariant is [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)
    §2 made executable: **an accepted pack can only subtract capability.**
  - **Safe by construction, not by decision:** the loader's only verbs are subset-installs into fail-closed
    extension points — the [`VectorIndex` port has no unfiltered method](storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)
    to bind, the label schema is a closed grammar (unregistered value → DLQ), the matrix composes
    most-restrictive-wins (a widening delta is a no-op or a rejected write). The gate is the belt; the closed
    extension points are the suspenders.
- **The §0 ledger is machine-checked.** A pack loads on the standard path only if its manifest ledger equals
  `"none, all additive."` A pack claiming a horizontal change (the falsifiability rule firing) is routed to a
  **human ADR gate** — refused until a horizontal ADR raises the floor it needs. This turns ADR-0016's
  falsifiability rule from a review convention into an **enforced control-flow branch**.
- **Versioning/hot-load/rollback:** per-tenant-pinnable `pack_version` (reusing the
  [model-version pinning pattern](governance/00-governance-and-audit.md#8-g6--model-governance)) + an SPI
  `schema_version` gated by `min_platform_schema`; a pack loads with **no code deploy** (validated data + a
  route flip); rollback = a route-flip to the additive prior version; **fail-closed unload** (a live label
  blocks its own removal). Every load is a signed, **audited governance event**.
- **No new hot-path component** — the SPI is a control-plane loader writing only into stores that already
  exist (label schema, policy store, conformance corpus, catalog); the DRY-RUN plan runs in **CI as a release
  veto**, reusing the [deployment safety-gate pattern](deployment/00-deployment-topology.md). **Runtime
  consumers are unchanged** — retrieval/verifier/canary see only a larger closed vocabulary + a stricter
  matrix, both already handled totally. That invisibility is the proof the SPI is additive. The SPI's own
  §0-equivalent ledger is therefore *"none, all additive."*
- **This is a cross-component decision → [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)** (it
  constrains permissions/metadata/governance/api/workers/storage at once, exactly as ADR-0016 did): the loader
  is the *specification* ADR-0016 §"Revisit when" anticipated. Updated indexes: ADR index (0017 added),
  `packs/README.md` (new "From paper contract to running capability" section), `platform/README.md` domain map
  (packs → **load SPI designed (Cycle 21)**).
- **Directly strengthens (no new risk owned):** hardens R1 (the §1 fixture validator makes an over-permissive
  `map_acl` a *load-time* CI failure, not just a canary catch), R4 (activation is tenant-scoped; a pack cannot
  cross tenants), and turns the [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) tighten-only rule
  from a reviewable claim into an executable, fail-closed gate.
- ⏳ **Handed to later cycles:** the **`core/` implementation** of the loader (this doc is its specification —
  the first concrete `platform/`→`core/` reconciliation target, [NEXT_STEPS §6 Cycle 2c](NEXT_STEPS.md)); open
  **Q#3** (model hosting — the SPI's §5 eval gate consumes whatever the approved-model registry holds,
  orthogonal) and **Q#6** (agent framework — the SPI fixes how domain content plugs in independent of the
  orchestrator choice) remain the only open engineering decisions. A **pack marketplace / external publishers**
  is the named future extension (the signed content-addressed bundle already is the distributable shape).

### Cycle 20 (2026-07-06) — Domain Pack #10 (Reporting): the first *aggregation* test — **the pack that completes the domain-pack surface**
- Wrote **[packs/reporting/00-reporting-pack.md](packs/reporting/00-reporting-pack.md)** — the **tenth
  and *last* pack** and the most inheritance-heavy of all: a dashboard tile / BI extract / report row is a
  **derived artifact over source tables**, so it reuses [DocIntel's](packs/document-intelligence/00-document-intelligence-pack.md)
  *derived-artifact-inherits-source-ACL* rule **verbatim** and [SAP's](packs/sap/00-sap-pack.md) BW/BI +
  [Finance's](packs/finance/00-finance-pack.md) fidelity for its sources. It was saved for last because it
  introduces **exactly one concept eleven prior packs never stressed — the *aggregate***: a report cell is
  rarely one source row but a **rollup** (sum/count/avg) over *many* rows the caller may only *partially* access.
- **The headline (§0 ledger + the dedicated "Aggregation" analysis): net horizontal change = none, all
  additive — the falsifiability rule was armed against an *arithmetic-inference leak* and did NOT fire.**
  Reporting's failure mode is unique among packs: not an ACL-widening but **arithmetic reconstruction** — a
  total over *one* masked row **is** that row; a difference of two aggregates leaks the delta (the classic
  small-cell / differencing / statistical-disclosure problem). The concept most likely to force a new hot-path
  mechanism (k-anonymity / suppression / differential privacy) resolved **by construction, not by an engine**:
  - **Query-time aggregate → filter-then-aggregate.** The [query-time ACL filter](permissions/00-authorization-model.md#4-query-time-enforcement)
    runs **before** the aggregation stage ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)),
    so every served total is a function of rows the caller **could have retrieved individually** — it reveals
    nothing a row-by-row read wouldn't. The one seam through which aggregation leaks — *aggregate-then-filter* —
    **is not a code path the platform has.** Differencing is therefore harmless: every aggregate a caller can
    obtain is built from rows they can each read.
  - **Pre-materialized report → Band-A mirror.** A BW query result / Power BI dataset / published dashboard
    is an **Item that already carries the source's own ACL** on that materialized artifact — the
    [SAP Band-A materialized-extract case](packs/sap/00-sap-pack.md), generalized. The platform mirrors it,
    never recomputes it.
  - **Cross-source rollup → intersection, never union.** A tile joining D1`{A,B}` + D2`{B,C}` is visible only
    to `{B}` — DocIntel's multi-source merge rule reused verbatim; a union would show A a value depending on a
    row A can't read.
  - **Unresolvable-contributor aggregate → quarantine.** An aggregate over a BW analysis authorization the
    connector can't enumerate to a principal set rides the *existing* `approximate → deny + quarantine` hatch
    (the **fourth sighting** — SAP field-auth / Legal computed-privilege / DocIntel redaction-cell).
- **The reusable articulation (the "aggregation discipline," stated once, in the pack):** *the platform
  aggregates only over rows the caller may already read (filter-then-aggregate), mirrors — never recomputes —
  a source-materialized total's ACL (Band-A), and a cross-source rollup carries the intersection of its
  contributing ACLs (never the union); an unresolvable contributor is quarantined.* So the worst a
  misconfigured Reporting pipeline can do is over-mask a tile or quarantine a rollup (**availability**), never
  reconstruct a masked row (**safety**) — fail-closed applied to *aggregation*. Reaffirms
  [ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)/[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)/[ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)
  → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **5th pack with empty §2 + §3** (after KM/SAP/SharePoint/Email) — a report **presents** the riding domain's
  policy, owns none (a report-owns-policy claim is the SAP category error). §2/§3 empty; the one composition
  behavior (a report resolves to the **most-restrictive** label + tier among contributing rows) is the
  inherited mixed-ACL invariant, not a new delta. **§4 fully inherited from *every* contributing domain** (a
  Finance+HR dashboard tile is **both** SOX- and Art.9-relevant) + the reused Finance numeric-grounding bar as
  the SOX evidence that a figure traces to its ledger source.
- **Consolidation / DRY win:** Reporting adds **no** SAP/SharePoint/Finance fidelity — it cites them verbatim;
  its only new content is the aggregation discipline + the arithmetic-inference eval class. Conformance
  fixtures weighted toward the aggregation failure modes (filter-then-aggregate pos/neg, small-cell/differencing
  non-leak, cross-source intersection-not-union, pre-materialized ACL mirror, unresolvable-contributor
  quarantine, aggregate-erasure completeness, cross-tenant). Eval headline is the aggregation analogue:
  **filter-then-aggregate negatives + small-cell non-leak + cross-source intersection** (0 arithmetic leaks) +
  numeric grounding (SOX).
- Updated indexes: `packs/README.md` (Reporting → **Seeded**, 1st aggregation test / **surface complete**;
  closing note now reads "domain-pack surface complete (Cycle 20)"), `platform/README.md` domain map
  (packs → **Domain-pack surface complete (Cycle 20)**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=10** and to its **first aggregation
  corner**; hardens R4 (cross-source rollups never aggregate across tenant *or* source boundaries,
  checked-and-empty; arithmetic-inference non-leak checked-and-empty), R1 (unresolvable-contributor
  quarantine), and makes GDPR erasure reach PII *inside an aggregate* (the lineage forward-walk
  tombstones/recomputes every aggregate that consumed an erased row — provable, not asserted).
- ⏳ **Handed to later cycles:** **the pack backlog is now empty — the domain-pack surface is complete.** The
  only remaining tracks are the **engineering track** (runtime pack-load SPI, `core/` code-reconciliation,
  Cycle 2c) and the two open engineering questions (**Q#3** model hosting, **Q#6** agent framework). The one
  future case that *would* force a horizontal ADR is named: a tenant requiring the platform to *serve* an
  aggregate over rows the caller can't individually read (statistical disclosure control / differential
  privacy) — deliberately out of scope, quarantined today.

### Cycle 19 (2026-07-06) — Domain Pack #9 (Document Intelligence): the first *derived-content* falsifiability test
- Wrote **[packs/document-intelligence/00-document-intelligence-pack.md](packs/document-intelligence/00-document-intelligence-pack.md)** —
  the **ninth pack**, the **first *concept-shaped* pack since KM** (Cycle 15), and the **first non-empty
  §2 since Legal** (Cycle 13). The eight prior packs all shared an unstated assumption: every artifact's
  ACL and label was **read from a source of record**. DocIntel is the first pack where the platform
  **manufactures the content itself** — OCR text, extracted tables/entities/forms, and a classification
  a classifier *infers* (a `pii_class` no source declared). That raises the one question the
  [falsifiability rule](packs/README.md#the-falsifiability-rule) exists to catch: *when the platform
  manufactures an artifact, where does its **ACL** come from, and can a **derived label** be trusted
  like a source-declared one?*
- **The headline (§0 ledger + the dedicated "Derived content" analysis): net horizontal change = none,
  all additive — the falsifiability rule was armed against a *manufactured authorization fact* and did
  NOT fire, because the platform never manufactures one; it inherits and tightens.** The two concepts
  most likely to force a horizontal primitive resolved cleanly:
  - **Derived *ACL* — inherited, never computed.** A derived artifact (OCR text = a `parsed_artifact`;
    an extracted table = a table-row chunk) is a **lineage descendant** of its `source_item`; the chunk
    projection denormalizes the *source Item's* ACL arrays. So the OCR of a `{client,counsel}` contract
    carries exactly `{client,counsel}` — the platform never invents a broader (or any) ACL. A
    **multi-source** derived node (an entity merging spans from D1/D2) takes the **intersection**
    (most-restrictive-wins) / splits / quarantines — **never the union** (the mixed-ACL invariant
    applied to a *manufactured* node). A derived sub-Item whose correct ACL is *narrower-and-unresolvable*
    (a redaction / PII-cell) rides the *existing* `approximate → deny + quarantine` hatch — the
    **third sighting** of the SAP-field-auth / Legal-computed-privilege path.
  - **Derived *label* — registered, tighten-only, fail-closed, provenance-stamped.** A classifier that
    infers `pii_class:health` is the first label the *platform* assigns rather than the *source* declares.
    It resolves additively: the value is **registered** (§2 non-empty — DocIntel *owns* this vocabulary);
    it may only **tighten** (add a mask, never remove/downgrade a label); a **low-confidence** output
    **fails closed** (resolves to the *more* restrictive outcome); and it is stamped `label_source: derived`
    + classifier id + version. A *wrong* inference **cannot leak**: under-labeling only fails to *add* an
    extra mask (a label only *subtracts* capability per [Permissions §7](permissions/00-authorization-model.md);
    the **ACL** — not the label — is the primary gate), and over-labeling is an *availability* cost (the
    fail-closed-preferred direction, the KM trade re-applied).
- **The reusable articulation (the "derivation discipline," stated once, in the pack):** *a
  platform-derived artifact may only ever **inherit or tighten** authorization, never widen it, in either
  plane — the ACL inherits (or intersects to) the source Item's and never unions; the label only adds a
  mask and never removes/downgrades one, failing closed on uncertainty.* This is the DocIntel analogue of
  Legal's "waiver = ACL edit, label stays" discipline. So the worst a misconfigured DocIntel pipeline can
  do is over-mask/over-quarantine (availability), never over-expose (safety) — fail-closed applied to
  *derivation*. Reaffirms [ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)/[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)/[ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)
  → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **First non-empty §2 since Legal, for a *new* reason:** the source packs' §2 was empty because a source
  carries no policy of its own; DocIntel's §2 is non-empty because it **owns a derived-classification
  vocabulary** — the labels a classifier *assigns*. The novel element is the **`label_source: derived`
  provenance stamp** (kept in the *same* dimension so enforcement is identical — never a `derived_sensitivity`
  fork that could someday be treated more loosely), not a new label value. Registered `restricted:extracted`;
  §3 tightens it (a derived artifact is **never** placed more openly than its source).
- **The one Metadata touch is additive, not a contract change.** OCR/extraction are ordinary **parse-stage**
  outputs (`parsed_as`, no new node). A *secondary* derived index (an entity/KG store) would be a new
  `LineageNode.kind` + `relation` — but that is the additive node-kind growth **[Metadata §9](metadata/00-catalog-and-lineage.md)
  already named for exactly this case** ("new derived artifact type = a new `LineageNode.kind` + `relation`");
  the graph was designed to grow node kinds, exactly as Legal was the first pack to exercise the *label*
  extension point beyond Finance. §4 fully inherited (GDPR for inferred/incidental PII + **EU AI Act**
  automated-classification transparency, satisfied by the existing model-version audit field + the
  provenance stamp + the *riding domain's* regime, since a DocIntel pipeline inherits its source's
  compliance envelope).
- **Consolidation / DRY win:** OCR/Doc-Intelligence was already a *named* RAG chunking content type
  ([RAG §2.1](rag/00-retrieval-pipeline.md)) and the "OCR layout" parser was the deferred sub-question of
  open Q#4 — this pack makes derived-content authorization **one canonical §1**. Conformance fixtures
  weighted toward the derived-authorization failure modes (ACL inheritance pos/neg, multi-source
  merge=intersection-not-union, derived-label fail-closed, redaction sub-Item quarantine, erasure reaches
  every derived artifact, cross-tenant). Eval headline is the derived-content analogue: **ACL-inheritance
  negatives + merge correctness + derived-classification fail-closed** (0 widenings) + OCR-noise robustness.
- Updated indexes: `packs/README.md` (Document Intelligence → **Seeded**, 1st derived-content test),
  `platform/README.md` domain map (packs → **… + Document Intelligence seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=9** and to its **first derived-content
  corner**; hardens R1 (a derived sub-Item's unresolvable ACL is a *checked-and-quarantined* case), R4
  (multi-source merge never unions across source boundaries, checked-and-empty), and makes GDPR erasure
  reach *derived* PII (the lineage forward-walk tombstones every derived node — provable, not asserted).
- ⏳ **Handed to later cycles:** only **Reporting** remains on the pack backlog (concept-shaped; reuses SAP
  BW/Finance fidelity + DocIntel's derived-artifact-inherits-source-ACL rule verbatim). With the pack
  surface all but complete, the **runtime pack-load SPI** (open Q#6-adjacent) becomes the primary remaining
  track. The one future case that *would* force a horizontal ADR is named: a derivation whose narrowing ACL
  the platform is *trusted to compute-and-enforce as a grant* on the shared path (an automated redaction as
  a grant, not a mirror) — deliberately out of scope, quarantined today.

### Cycle 18 (2026-07-06) — Domain Pack #8 (Email/Exchange): the third & *last* source-shaped pack — the *transport-vs-storage* test
- Wrote **[packs/email/00-email-pack.md](packs/email/00-email-pack.md)** — the **eighth pack**, the
  **third and last source-shaped** one, and the **simplest of all sources**. SAP was the *hardest*
  (no document ACL → quarantine story); SharePoint the easiest *document* source (rich ACL, but a
  sharing-link over-grant trap); Email is simpler still — a message's ACL is just its **mailbox owner
  + explicit delegates**, with **no sharing-link surface at all**. It is now the **canonical Email
  `map_acl` reference** that HR/Legal/Audit cite instead of re-deriving (all three already read email).
- **The headline (§0 ledger + the "transport-vs-storage" analysis): net horizontal change = none, all
  additive — the falsifiability rule was armed against a *transport-to-storage widening* and did NOT
  fire.** The one trap unique to messaging is conflating a message's **transport-time audience** with a
  **storage-time read grant**. Every Exchange construct sorts into `allow` / `deny` / quarantine, and
  the audience is captured as **content, never a grant**:
  - **The archived copy's ACL = the mailbox it lives in, not the message's To/Cc/Bcc audience** — a
    message in Alice's mailbox is granted to Alice + her delegates, *not* to everyone on the recipient
    line ([Permissions §5.3](permissions/00-authorization-model.md#53-email--exchange), verbatim).
  - **Per-message thread ACLs → the mixed-ACL invariant** — each message keeps its own ACL; a
    forwarded/quoted thread does not retroactively grant earlier recipients. The Item = one message;
    [RAG §2.2](rag/00-retrieval-pipeline.md)'s per-email-message chunker already enforces it.
  - **Delegate / Full-Access / shared-mailbox → explicit `allow`s** (Band-A `exact`, ordinary
    principal-set expansion); **Send-As / Send-on-Behalf → no read grant** (write rights; platform is
    read-only); a dynamic-group-governed delegate set → the *existing* [SAP Band-B](packs/sap/00-sap-pack.md)
    resolve-or-quarantine path.
  - **Distribution-list membership → NOT a read grant on the archive** (the email analogue of
    SharePoint's "anyone"-link trap) — membership is a *transport* delivery fact; the canonical model
    refuses to derive a storage grant from it.
  - **Mailbox perms not fully readable → quarantine** (`acl_confidence = exact` only when the delegate
    set was fully read — the one hard floor).
- **The reusable articulation (stated once, in the pack):** *the archived copy's ACL is the mailbox it
  lives in, never the message's transport audience; a recipient set (To/Cc/Bcc, a distribution list, a
  forwarded thread) is captured as **content**, never promoted to a **grant** — so no transport fact
  ever silently widens storage access.* Reaffirms [ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)/[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)
  → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **Fourth pack with empty §2 + §3** (after KM, SAP, SharePoint) — a source-shaped pack carries no
  policy of its own; a message has no native label vocabulary (an Exchange hold/sensitivity tag is
  *carried*, not *owned*). §4 fully inherited (GDPR/privilege/SOX-PCAOB/ISO) + one source-specific
  evidence binding (mailbox + internetMessageId + Graph change-key). **Shortest §1 matrix of any pack**
  — **no Band-C** (message is the ACL-carrying Item) *and* **no sharing-link surface**.
- **Consolidation / DRY win:** Email fidelity was asserted **3× ad hoc** (HR/Legal/Audit); this pack
  makes it **one canonical §1**. Conformance fixtures weighted toward the transport-vs-storage over-grant
  mode (DL non-grant, thread-audience non-widening, To/Cc/Bcc non-grant, delegate pos/neg, shared-mailbox
  correctness, Band-B freshness, not-fully-read quarantine, cross-tenant, revocation). Eval headline is
  the source-shaped analogue: **transport-vs-storage over-grant negatives (0 silent over-grants)** + the
  [KM](packs/km/00-km-pack.md) over-refusal/recall lens retained.
- Updated indexes: `packs/README.md` (Email → **Seeded**, 3rd & last source-shaped pack), `platform/README.md`
  domain map (packs → **… + Email seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=8** and closes the **source-pack
  surface**; hardens R4 (transport-audience non-widening + cross-tenant mailbox isolation now checked-and-empty),
  R1 (not-fully-read quarantine), and re-exercises the Band-B (dynamic delegate-set) freshness path.
- ⏳ **Handed to later cycles:** the **source-pack surface is now complete** (Finance/HR/Legal/Audit/KM
  concept-shaped + SAP/SharePoint/Email source-shaped). Remaining packs — **Document Intelligence** and
  **Reporting** — are *concept-shaped reuse*; the **runtime pack-load SPI** (open Q#6-adjacent) is now the
  primary remaining track. The one future case that would force a horizontal Permissions ADR is named:
  an Exchange construct mappable to none of `allow`/`deny`/quarantine without deriving a storage grant
  from a transport fact (none found).

### Cycle 17 (2026-07-06) — Domain Pack #7 (SharePoint): the second *source-shaped* pack — SAP's mirror, the *inverse* (over-grant) test
- Wrote **[packs/sharepoint/00-sharepoint-pack.md](packs/sharepoint/00-sharepoint-pack.md)** — the
  **seventh pack** and the **second source-shaped** one, deliberately chosen as SAP's *mirror image*.
  [SAP](packs/sap/00-sap-pack.md) was the **hardest** source (no document ACL → whole story was
  *quarantine*); SharePoint is the **easiest** (rich item-level ACL → almost everything `exact`). That
  flips the falsifiability question and the feared failure: SAP's risk was **quarantining too much** (an
  availability cost); SharePoint's is the **opposite and more dangerous** — a **silent *over*-grant** (a
  safety leak, R4/R1).
- **The headline (§0 ledger + the dedicated "over-grant" analysis): net horizontal change = none, all
  additive — the falsifiability rule was armed against a *widening* and did NOT fire.** Every SharePoint
  sharing construct maps to one of four outcomes — `allow` / `deny` / **flagged-grant** / quarantine —
  none of which silently widens access, and none of which needs a new principal category or a new
  predicate:
  - **Broken inheritance → the *effective* item ACL, not the library's** (a removal = a `deny`,
    deny-wins). SharePoint's ACL lives *at* the Item, so **there is no Band-C (sub-Item) case at all** —
    the structural reason this pack is shorter than SAP.
  - **Sharing links:** specific-people → explicit `allow`s; org-wide → a real all-org grant; **"anyone"
    / anonymous links → a *flagged* grant (`sharing:anonymous`) that fail-closes by default — never a
    silent public grant** (the [§5.1 rule](permissions/00-authorization-model.md#51-sharepoint--onedrive-m365)
    enforced verbatim). The one construct that *looks* like it needs a "public" predicate is handled by
    **flag-and-fail-closed** → no anonymous/public predicate, no new principal category.
  - **External/guest (`#EXT#`) principals → ordinary tenant-namespaced CPIs** (a guest of tenant A is a
    principal *of tenant A* — R4 unaffected).
  - **Azure AD dynamic groups → resolve-or-quarantine**, the **same Band-B mechanism SAP defined**,
    reused verbatim (pre-resolve + `list_principal_changes`, else quarantine).
  - **Permissions not fully readable → quarantine** (`acl_confidence = exact` only when item perms were
    fully read — the one hard floor).
- **The reusable articulation (stated once, in the pack):** *a fidelity-friendly source's risk is the
  inverse of a fidelity-poor one's — not under-serving via quarantine but over-serving via a silent
  widening; the defense is to map every sharing construct to an explicit grant, a deny, a **flagged**
  grant, or a quarantine — the four outcomes are exhaustive, so no construct escapes into a silent
  public grant.* Reaffirms [ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)/[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)
  → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **Third pack with empty §2 + §3** (after KM and SAP) — for SAP's reason: **a source-shaped pack
  carries no policy of its own.** Nuance vs. SAP: SharePoint *carries* MIP sensitivity labels into
  `labels.sensitivity`, but the label **values** are owned by the riding domain — SharePoint is a label
  **carrier/mapper**, not a label **owner** (SAP carries no native label at all). §4 fully inherited
  (SOX/GDPR/privilege/ISO) + one source-specific evidence binding (site/library + item objectId +
  Graph version + the `sharing:anonymous` flag).
- **Consolidation / DRY win:** SharePoint fidelity was asserted **5× ad hoc** (Finance/HR/Legal/Audit/KM);
  this pack makes it **one canonical §1** they all cite. Conformance fixtures weighted toward the
  over-grant failure mode (broken-inheritance negative, "anyone"-link non-widening, guest isolation,
  dynamic-group freshness, not-fully-read quarantine, open-mode positive, revocation). Eval headline is
  the source-shaped analogue: **over-grant negatives (0 silent over-grants)** + the [KM](packs/km/00-km-pack.md)
  over-refusal/recall lens retained.
- Updated indexes: `packs/README.md` (SharePoint → **Seeded**, 2nd source-shaped / SAP's mirror; Email →
  last source pack), `platform/README.md` domain map (packs → **… + SharePoint seeded**).
- **Also committed the Cycle-16 SAP pack** (it was authored but left untracked by the prior auto-save).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=7** and to its **first over-grant
  corner**; hardens R4 (guest isolation + no-silent-widening are now checked-and-empty), R1 (not-fully-read
  quarantine), and re-exercises the Band-B (dynamic-group) freshness path from the document side.
- ⏳ **Handed to later cycles:** **Email** (Cycle 18) is the **last source pack** — per-message ACL +
  delegates + shared mailboxes (already exercised via HR/Legal/Audit), shorter still (no sharing-link
  surface); after that the domain-pack surface is essentially complete and the **runtime pack-load SPI**
  (open Q#6-adjacent) becomes the primary remaining track. The one future case that would force a
  horizontal Permissions ADR is named explicitly: a SharePoint sharing construct mappable to none of the
  four outcomes without silently widening access (none found).

### Cycle 16 (2026-07-06) — Domain Pack #6 (SAP): the first *source-shaped* pack + the canonical `map_acl` reference
- Wrote **[packs/sap/00-sap-pack.md](packs/sap/00-sap-pack.md)** — the **sixth pack** and the
  first that is *source-shaped* rather than *concept-shaped*. Finance/HR/Legal/Audit/KM each
  stressed a **policy** corner; SAP introduces **no new policy concept at all** — its entire
  content is **connector `map_acl` fidelity** for the one source with **no document ACL**. It is
  now the **canonical SAP `map_acl` reference** that Finance/HR/Audit cite instead of re-deriving,
  and it **resolves the sub-question open Q#2 deferred**: *the exact `map_acl` fidelity achievable
  per SAP module* (see §3 below).
- **The headline (§0 ledger + the "three-band fidelity model" analysis): net horizontal change =
  none, all additive — a *different kind* of falsifiability test, and it held.** The five concept
  packs asked "does a new *policy* concept fit?"; SAP asks **"does the hardest source's *entire*
  authorization model — every module — fit the `map_acl` fidelity contract, with no case that is
  neither `exact` nor quarantinable?"** Every SAP construct sorts into exactly one of three bands:
  - **Band A — org-level & role authorization → `exact`:** company code / cost center / plant /
    purchasing org / sales org expressible as `role:*` + `orgunit:*` principal set-membership
    (FI/CO, MM, SD; the case Finance proved and HR/Audit reused).
  - **Band B — structural / dynamic authorization → resolve-or-quarantine:** HCM structural
    authorizations (PD/OM org-tree evaluation paths), `P_ORGINCON` context solution, dynamic
    groups. **B1** = pre-evaluate to a principal set kept fresh by `list_principal_changes`
    (the *same mechanism HR's computed manager-hierarchy already rode*) → `exact` within SLA;
    **B2** = not stably resolvable → `approximate → deny + quarantine` (or OBO).
  - **Band C — field / row / cell-level → quarantine:** FI field-level auth, infotype subfield
    masking, BW analysis authorizations (characteristic-value/cell-level) — sub-Item, not a
    document grant → `approximate → deny + quarantine` (Finance's salary-line fixture path).
    *Exception:* a materialized extract carrying its own row ACL is an ordinary Band-A item.
- **Why there is no fourth case (the falsifiability payoff):** "resolvable to a principal set" and
  "quarantinable" are **jointly exhaustive** — anything not Band A/B1 is sub-`exact`, and everything
  sub-`exact` is denied-and-quarantined by construction (the `VectorIndex` port has no unfiltered
  method; the persist stage routes sub-`exact` to quarantine). **There is no representable state in
  which an unresolvable SAP authorization is served.** The three bands are *presentations* of the
  existing two-outcome gate (`exact` served / sub-`exact` quarantined), **not a new confidence
  level** — so no new predicate, no horizontal ADR. Reaffirms
  [ADR-0008 §5.2](architecture/adr/ADR-0008-canonical-principal-acl-model.md) + the §9 quarantine
  hatch → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **Second pack with empty §2 + §3** (after KM), but for a **structurally different reason**: KM's
  tables were empty because the low-restriction defaults were already calibrated; SAP's are empty
  because **a source-shaped pack carries no policy of its own** — classification/tighten belong to
  the *domain* riding on it (Finance's `restricted:mnpi`, HR's `pii_class:health`, Audit's
  `restricted:audit_workpaper`). A source claiming policy would be a category error. §4 is **fully
  inherited** (SOX from Finance-on-SAP, GDPR from HR-on-HCM, PCAOB from Audit-on-GRC) + one
  source-specific evidence binding (SAP table/module + `CDPOS` change-doc number + version).
- **Module-by-module fidelity matrix (§1)** covers FI/CO, MM, SD, HCM/SuccessFactors, BW/BI, GRC —
  each row assigned a band + max `acl_confidence`. Conformance fixtures span all three bands
  (Band-A pos/neg, Band-C quarantine, Band-B1 freshness, Band-B2 quarantine, revocation,
  cross-tenant). Eval headline is the source-shaped analogue: **fidelity-band routing correctness**
  (0 Band-C/B2 items served) + permission negatives. Promoted the **SAP table-serialization parser**
  (named in Finance §5) to the canonical SAP parser.
- **GRC/SoD inherited verbatim** from [Audit's plane-boundary analysis](packs/audit/00-audit-pack.md):
  SoD *prevention* is out of the read plane; SoD read-exclusions = pre-resolved per-principal `deny`
  (Band A, deny-wins); SoD *detection* = ordinary permission-gated retrieval. Adds nothing.
- **Consolidation / DRY win:** SAP fidelity was asserted **3× ad hoc** (Finance/HR/Audit); this pack
  makes it **one canonical §1** they all cite.
- Updated indexes: `packs/README.md` (SAP → **Seeded**, 1st source-shaped pack; SharePoint/Email →
  shorter fidelity-reuse backlog), `platform/README.md` domain map (packs → **Finance + HR + Legal +
  Audit + KM + SAP seeded**).
- **Resolved the deferred sub-question of open Q#2** — see §3.
- **Directly strengthens (no new risk owned):** pushes the bet to **n=6** and to its **first
  source-shaped corner**; hardens R1 (the three-band model makes "neither resolvable nor
  quarantinable" a *checked and empty* set across all SAP modules); re-exercises R3 (Band-B1
  structural-auth freshness), R4 (cross-tenant), and the quarantine hatch end to end.
- ⏳ **Handed to later cycles:** **SharePoint** and **Email** source packs are now near-pure,
  *shorter* fidelity reuse (both *have* document ACLs → no dominant Band-C story; both modes already
  exercised); the runtime **pack-load SPI** (open Q#6-adjacent) is still the engineering track; open
  Q#3 (model hosting) still feeds each pack's eval-tuned model choice. The one future case that would
  force a horizontal Permissions ADR is now **named explicitly**: an SAP module exposing an
  authorization construct that is *neither* resolvable to a principal set *nor* sub-Item-quarantinable
  (none found across FI/CO, MM, SD, HCM, BW, GRC).

### Cycle 15 (2026-07-06) — Domain Pack #5 (KM): the first *inverse* falsifiability test — over-refusal
- Wrote **[packs/km/00-km-pack.md](packs/km/00-km-pack.md)** — the **fifth pack**, and the first to
  stress the platform from the **opposite** direction. Finance/HR/Legal/Audit all asked *"does the
  platform correctly **refuse**?"* (over-sharing = safety bug). KM inverts it: broad `internal`, low
  restriction, high recall over Confluence/SharePoint/wikis/portals — the feared failure is
  ***over-refuse*** (an **availability** bug: accessible open content left *unfound* or *needlessly
  masked*).
- **The headline (§0 ledger + the dedicated "Over-refusal" analysis): net horizontal change = none,
  all additive — and, uniquely, additive with *empty §2 and §3*. The falsifiability rule was armed
  against a *loosening* (not a tightening) and did NOT fire.** The pack most tempted to loosen a floor
  to buy recall needed to loosen **nothing**:
  - **Over-refusal is a *tuning/eval* problem *upstream* of the filter and verifier — never a
    floor-loosening problem.** A KM answer is wrongly empty for exactly two reasons: (1) content was
    accessible but *not retrieved* (a recall miss — fixed by the *existing* levers on the
    already-permitted set: query expansion [RAG §4.3], hybrid/rerank/MMR tuning [RAG §5], wiki dedup
    [RAG §6], a KM-eval-tuned model); or (2) content was *not accessible* and the empty answer is
    *correct* (the safety floor working). Neither requires seeing more than the caller may.
  - **Three floor-loosening temptations, each rejected *and* shown unnecessary:** widen the default
    label (`internal`→`public`) — buys **zero** recall (`internal` is already retrievable internally)
    and breaks fail-closed classification; relax the verifier grounding bar — targets the wrong stage
    and converts an availability bug into a **grounding/R2 leak**; add an unfiltered "list mode" —
    structurally impossible (`VectorIndex` port has no unfiltered method) *and* unnecessary (browse =
    the filter-parity catalog read).
- **The reusable articulation (stated once, in the pack):** *recall is bought **upstream of** the
  filter and verifier, on the set the caller may already see; safety is enforced **at and after** the
  filter — the two never trade, so improving one never regresses the other.* Reaffirms
  ADR-0004/ADR-0009 → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **First pack to register ZERO new vocabulary (§2 empty) and apply ZERO tighten deltas (§3 empty),
  and it loosens nothing either** — the empty tables *are* the deliverable: direct evidence that the
  **low-restriction end of the lattice was already complete** and correctly calibrated. Also the
  **lightest compliance footprint** of any pack (ISO 27001/SOC 2 + incidental-PII GDPR, both inherited).
- **Sources:** Confluence (space + page restrictions), SharePoint/OneDrive wikis+portals (reuses
  Finance/HR/Legal fidelity verbatim), internal portals/intranet, Git-hosted wikis. Fidelity-friendly,
  but the fail-closed rule is **not waived** for it (an unresolvable page restriction is still
  quarantined; unlabeled → `internal` never `public`). Supplied conformance fixtures with a deliberate
  *both-ways* emphasis — an **open-content positive** (a space-member *can* read an `internal` page:
  the pack must not over-restrict) **and** the usual restricted-page/computed-restriction/cross-tenant
  negatives (safety floor unchanged). Eval set inverts the headline to **recall / over-refusal
  false-negative** while *retaining* the permission-negative class — proving the gate can chase recall
  without trading away safety (the SoD-detection recall class Audit first surfaced, now the primary bar).
- **No new ADR this cycle** — KM is a *worked instance* of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md);
  the pack instead **documents the floor from the open side** (a tenant demanding "skip the filter" is
  refused) and names the future pack that *would* force an ADR: a *transparency-mode* pack that
  surfaces content beyond strict entitlement (deliberately out of scope, now documented).
- Updated indexes: `packs/README.md` (KM → **Seeded**, 1st inverse test), `platform/README.md` domain
  map (packs → **Finance + HR + Legal + Audit + KM seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=5** and to its **first inverse
  (over-refusal) corner**; proves the fail-closed defaults don't suppress legitimate recall; re-exercises
  the SharePoint connector fidelity in *open* mode (complementing the restricted-mode exercise);
  re-validates R2 from the other side (a lowered grounding bar as an *anti*-pattern is now documented).
- ⏳ **Handed to later cycles:** the **source-shaped** packs (SAP / SharePoint / Email) are now pure
  connector-fidelity reuse (both restricted- and open-mode SharePoint paths exercised); the runtime
  **pack-load SPI** (open Q#6-adjacent) is still the engineering track; open Q#3 (model hosting) still
  feeds each pack's eval-tuned model choice.

### Cycle 14 (2026-07-06) — Domain Pack #4 (Audit): the first *combinatorial*-concept falsifiability test
- Wrote **[packs/audit/00-audit-pack.md](packs/audit/00-audit-pack.md)** — the **fourth pack**,
  chosen as the **highest-leverage / lowest-effort** slot: it inherits almost everything already
  built (**Finance's SOX row + SAP fidelity verbatim**; **Legal's `matter:<id>` hold + append-only
  evidence**) and introduces **exactly one concept to stress: segregation-of-duties (SoD)** — the
  first *combinatorial* constraint any pack has raised (every prior restriction was *unary*: a
  property of one (principal, item) pair; SoD is *relational* — "the preparer of entry E may not be
  its approver").
- **The headline (§0 ledger + the dedicated "Segregation-of-duties" analysis): net horizontal change
  = none, all additive — the falsifiability rule was armed and did NOT fire, but for a *sharper*
  reason than Legal's.** Legal's waiver held by *composing* two existing mechanisms; Audit's SoD
  holds because of a **plane boundary**. SoD is one word for two controls in two planes:
  - **SoD as *prevention* (write plane) — out of the platform's plane.** "Preparer may not post" is
    a constraint on *executing a transaction*, enforced in the source system of record (SAP GRC /
    the ERP). The platform is a **read-only, permission-faithful knowledge platform**
    ([ADR-0001](architecture/adr/ADR-0001-platform-shape-private-rag.md)/[ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md));
    it **never posts/approves/executes** — so **there is no SoD action for it to gate.** Not a gap;
    out of plane.
  - **SoD as it *projects onto read access* — a per-principal `deny`, pre-resolved by the source.**
    An independence/SoD *read*-exclusion is structurally identical to Legal's **ethical wall**: the
    source resolves the relation into a principal set, the connector `map_acl`s it into a `deny`
    grant, deny-wins evaluates first. *Additive.*
  - **SoD as *detection* (read plane) — an ordinary permission-gated retrieval.** "Which users both
    prepared and approved?" is a **read** over the audit trail; the combinatorial join lives **in
    the query and the source data, never in the access predicate.** The verifier grounds it in cited
    trail rows. *Additive — exactly what a permission-faithful RAG platform is for.*
- **The reusable articulation (stated once, in the pack):** *the platform enforces
  **who-may-read**, never **who-may-act**. Any action-phrased control — SoD, four-eyes,
  maker-checker, dual-authorization — is enforced in the source; the platform mirrors the **read**
  restriction it produces (a `deny`) and **retrieves over** the **evidence** it leaves (the trail).
  Detection in scope; prevention of an action out of plane.* This **reaffirms** ADR-0001/0004 rather
  than extending them → **no new ADR** (correct per [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
- **Where it could have broken:** trying to make the *access predicate itself* compute the relation
  live. Covered by two *existing* hatches: pre-resolved → unary `deny`; computed-and-unresolvable →
  the *existing* `approximate → deny + quarantine` path (identical to SAP field-level auth / Legal
  computed-privilege). No third case exists → no horizontal gap.
- **Sources:** GRC/audit-management (AuditBoard/Workiva/SAP GRC), SAP/ERP (reuses Finance fidelity +
  field-level-auth quarantine verbatim), DMS/SharePoint (reuses Legal/Finance), the platform's **own
  S7 append-only trail** (the reflexive case), email. Registered **`restricted:audit_workpaper`**
  (pre-issuance masking + egress block); reused `matter:<id>` for PCAOB AS 1215 7-yr retention holds.
  Supplied conformance fixtures (SoD read-exclusion deny-wins, pre-issuance pos/neg, computed-SoD
  quarantine, hold-vs-erasure, cross-tenant) and an eval set whose headline classes are
  **pre-issuance permission negatives** and — a deliberate first — **SoD-conflict *detection*
  recall** (missing a real conflict is an audit failure), the first sighting of the *over-refusal*
  failure mode KM will make its headline.
- **No new ADR this cycle** — Audit is a *worked instance* of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md);
  the pack instead **documents the plane boundary** as the explicit reason no transaction-control ADR
  was needed (and names the future pack that *would* need one: an action-taking pack).
- Updated indexes: `packs/README.md` (Audit → **Seeded**, 1st combinatorial test), `platform/README.md`
  domain map (packs → **Finance + HR + Legal + Audit seeded**).
- **Directly strengthens (no new risk owned):** pushes the bet to **n=4** and to its **first
  combinatorial concept**; hardens the SOX/evidence story (Finance's row, now reused + reflexive:
  the platform's own SOC 2 evidence is the trail Audit queries); re-exercises R1 (computed-SoD
  quarantine), R4 (cross-tenant), and the `legal_hold > erasure > retention` precedence under PCAOB
  retention; makes the **read-plane-mirror scope boundary** an explicit, cited statement.
- ⏳ **Handed to later cycles:** **KM** is next as the deliberate *inverse* stress (broad `internal`,
  high recall, low restriction — does the pipeline *over*-refuse on open content?); the runtime
  **pack-load SPI** (open Q#6-adjacent) is still the engineering track; a future **action-taking**
  pack would be the one case forcing a horizontal transaction-control ADR (deliberately out of scope,
  now documented).

### Cycle 13 (2026-07-06) — Domain Pack #3 (Legal): the first genuine novel-concept falsifiability test
- Wrote **[packs/legal/00-legal-pack.md](packs/legal/00-legal-pack.md)** — the **third pack**, chosen
  because it is *near-mechanical in five of six sections* (reuses HR's `matter:<id>`/hold shape +
  Finance's DMS/SharePoint fidelity) **while introducing the one concept the platform had never
  stress-tested: attorney-client privilege as a retrieval gate.** Unlike HR (a *different shape* of
  known mechanism), Legal is the first pack that could have **falsified** the bet with a genuinely
  new primitive. It did not.
- **The headline (§0 ledger + the dedicated "Privilege & waiver" analysis): net horizontal change =
  none, all additive — the falsifiability rule was armed and did NOT fire.** The concept most likely
  to force a horizontal primitive — **privilege *waiver*, per matter, per recipient** — resolved to
  the *composition of two mechanisms the platform already has*, by separating **what** from **who**:
  - **What** (the restriction) = a `restricted:privileged` label — a §2 registered value + §3 tighten
    delta, structurally identical to Finance's `restricted:mnpi`.
  - **Who** (the cleared set) = the **item ACL** — the existing per-item `allow` set.
  - **Waiver** = a **narrowing grant edit on the item ACL**, propagated by the *existing*
    change-driven re-sync ([Workers §5](workers/00-ingestion-architecture.md)); **never** a label
    removal (which would over-waive to *everyone* — the trap). "Per recipient" is exactly what an ACL
    *is*, so the **static label→action matrix never encodes recipient-specific policy → no horizontal
    gap.** Recorded as **one pack-local discipline** (waiver = ACL edit, label stays), not a mechanism.
- **Ethical walls (information barriers) = the *existing* deny-wins clause**
  ([Permissions §3.1](permissions/00-authorization-model.md#31-precedence-deny-always-wins)): a
  conflicted attorney is a `deny` grant on the matter's items; deny already evaluates first, before
  any allow. Deliberately **not** modeled as a label (that would lose deny semantics) — kept in the ACL.
- **The one thing the platform must *refuse*:** it does **not compute** subject-matter waiver (a legal
  determination); it **mirrors** counsel's decision as reflected in the source ACL. A DMS exposing
  privilege only as a *computed* rule takes the *existing* `approximate → deny + quarantine` path —
  identical to SAP field-level auth. Refusing to *infer* privilege is what keeps the platform a
  faithful ACL mirror rather than a legal-reasoning engine that could leak on a wrong inference.
- **Sources:** DMS (iManage/NetDocuments — rich per-document ACL + walls, so Legal is *fidelity-friendly*
  unlike SAP), SharePoint, privileged email, matter/practice-management stores; **clause-level chunking**
  reuses RAG's structure-aware seam. Registered `restricted:privileged` + `restricted:work_product`
  (independently waivable → two labels); reused `matter:<id>` verbatim. Supplied conformance fixtures
  (ethical-wall deny-wins, privilege pos/neg, **waiver-as-grant-edit that does not over-share and keeps
  the label**, hold-vs-erasure, cross-tenant) and an eval set whose headline classes are **privilege
  negatives**, **waiver correctness**, and **ethical-wall enforcement**.
- **No new ADR this cycle** — [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) already
  ratifies the pack contract; Legal is a *worked instance* of it. (A pack that *had* forced per-recipient
  matrix policy would have needed a horizontal Governance ADR — that section instead documents *why the
  gap does not exist*.)
- Updated indexes: `packs/README.md` pack table (Legal → **Seeded**, 1st novel-concept test),
  `platform/README.md` domain map (packs → **Finance + HR + Legal seeded**).
- **Directly strengthens (no new risk owned):** turns "even a genuinely new restriction type = pack,
  not redesign" from an *untested* claim into a *tested* one (n=3, first novel concept); binds a new
  audit dimension (**the waiver decision itself is an audited ACL-change event**); re-exercises R1
  (computed-privilege quarantine), R3 (waiver propagation within the freshness SLA), R4 (cross-tenant),
  and the `legal_hold > erasure > retention` precedence under e-discovery preservation.
- ⏳ **Handed to later cycles:** **Audit** is now almost entirely inherited (Finance SOX row +
  segregation-of-duties as another `deny`-grant + append-only evidence + Legal's `matter:<id>` hold),
  then **KM** as the deliberate *inverse* stress (broad `internal`, high recall — does the pipeline
  *over*-refuse on open content?). The runtime **pack-load SPI** (open Q#6-adjacent) is still the
  engineering track.

### Cycle 12 (2026-07-06) — Domain Pack #2 (HR): the second, structurally-different data point
- Wrote **[packs/hr/00-hr-pack.md](packs/hr/00-hr-pack.md)** — the **second pack**, chosen to
  stress a **different corner** than Finance so the bet is tested for *reusability*, not just
  *possibility*. One pack proves the mechanism exists; a second, structurally-different pack is
  the first evidence the [skeleton](packs/README.md) *generalizes*.
- **The headline (§0 ledger): net horizontal change = none, all additive — the skeleton
  generalized from n=1 to n=2 cleanly.** The case most likely to force a new primitive —
  **employee-self-scoped ACLs** ("a subject may see *only their own* record") — resolved to the
  **degenerate case of the existing set-membership predicate**: a one-element `allow` set = the
  owner's CPI, and the subject's own CPI is *already* one of their effective principals
  ([Permissions §4.1](permissions/00-authorization-model.md)). No "owner-of" concept was added.
- **Computed manager-hierarchy visibility** ("manager sees reports N levels down", dynamic
  security groups) that is *not* expressible as static set-membership rides the **existing §9
  quarantine / §10 OBO escape hatch** — the *same one Finance used for SAP field-level auth*.
  The R1 confidence gate held against a second, different ABAC shape.
- **Special-category data:** registered `pii_class:health` (GDPR Art. 9 — already the Metadata
  schema's named example), `pii_class:employment`, and `restricted:works_council`; **tightened**
  the label matrix with a **manager-visibility carve-out** (health data masked even from a
  subordinate's own line manager by default) — a *tighten*, never a grant.
- **GDPR as the *primary* regime (Finance leaned SOX):** exercised the reflexive **self-DSAR**
  (employee is both subject and caller — the existing DSAR job, unchanged) and the
  **`legal_hold > erasure > retention`** precedence under real conflict (an erasure request is
  *partially* honored — HR content erased, statutorily-retained payroll held — provable by
  lineage traversal).
- **Sources:** Workday + SAP-HCM/SuccessFactors (**reuses Finance's SAP connector fidelity work
  verbatim**), SharePoint (HR policy library, broadly `internal`, high recall), grievance email.
  Supplied self-scope + health-masking + erasure/retention conformance fixtures and an eval set
  whose headline classes are **self-scope permission negatives** and **health-field masking**.
- **No new ADR this cycle** — [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)
  already ratifies the pack contract; HR is a *worked instance* of it, exactly as Finance was.
  (A new pack that *did* force a horizontal change would have needed one — HR did not.)
- Updated indexes: `packs/README.md` pack table (HR → **Seeded**), `platform/README.md` domain
  map (packs → **Finance + HR seeded**).
- **Directly strengthens (no new risk owned):** turns "new domain = pack, not redesign" from a
  claim backed by *one* example into one backed by **two structurally-different examples**;
  re-exercises R1 (a second ABAC shape quarantined), R4 (cross-tenant + self-scope blast radius),
  and the erasure/legal-hold precedence end to end.
- ⏳ **Handed to later cycles:** Legal / Audit / KM / SAP / SharePoint / Email packs stay
  fill-in-the-blank (Legal reuses HR's `matter:*`/grievance-hold shape; Audit reuses Finance's
  SOX row); the runtime **pack-load SPI** (open Q#6-adjacent) is still the engineering track.

### Cycle 11 (2026-07-06) — Domain Pack #1 (Finance) + the reusable pack-spec skeleton
- Opened the **`packs/`** folder — the first *vertical* surface, after all ten horizontals were
  Seeded (Cycle 10). Its purpose is to **prove the founding bet** (*"new domain = pack, not
  redesign"*), asserted ten times and until now proven zero times.
- Wrote **[packs/README.md](packs/README.md)** — the **reusable six-part pack-spec skeleton**
  (every future pack is fill-in-the-blank): (1) sources + `map_acl` fidelity + conformance
  fixtures; (2) classification-registry values; (3) label→action *tighten* deltas; (4)
  compliance-map rows; (5) retrieval/answer eval set + parsers; (6) optional additive API `pack`
  hint. Each section plugs into **one already-built horizontal extension point** — the author
  fills blanks, never designs mechanism. Added the mandatory **§0 horizontal-change ledger** and
  the **falsifiability rule** (if a pack *can't* fit, that's a real horizontal gap → a horizontal
  ADR, never a pack-local hack).
- Wrote **[packs/finance/00-finance-pack.md](packs/finance/00-finance-pack.md)** — the **reference
  pack**, deliberately the hardest (SAP has *no document ACL*; Finance data is simultaneously
  `confidential` + PII + legally held; SOX makes the audit trail contractual; numbers must be
  grounded-or-refused). Its **§0 ledger records ZERO horizontal changes** across all ten surfaces —
  the bet held against the worst case. Concretely: SAP `map_acl` fidelity target + 4 conformance
  fixtures (incl. `approximate→deny+quarantine` for field-level auth, and revocation-within-SLA);
  registered `restricted:mnpi`/`restricted:supervisory` + `pii_class:financial`/`tax`; tighten-only
  label deltas (MNPI → Isolated model pool + egress block); inherited SOX/GDPR/ISO compliance rows
  with evidence bindings; SAP-table/ledger/Excel parsers + a numeric-grounding / refuse-over-guess /
  permission-negatives eval set; the additive `pack:"finance"` hint (identity still governs).
- Recorded **[ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)** — ratifies the pack
  contract as a genuinely cross-component decision (it constrains all ten horizontal surfaces at
  once): **a pack is additive data + policy, tighten-only, six sections, with a mandatory
  horizontal-change ledger.** The worst a misconfigured pack can do is over-restrict (availability
  bug), never over-expose (safety bug) — fail-closed applied to extensibility.
- Updated indexes: ADR index, `platform/README.md` domain map (added `packs/` → **Finance seeded**).
- **Directly strengthens (no new risk owned):** turns the founding bet from a slogan into a
  **reviewable, blockable contract** (a non-additive §0 ledger row is a PR-visible event);
  exercises and validates R1 (SAP quarantine), R5 (Isolated-tier cost trade), and the
  audit-as-evidence promise end to end.
- ⏳ **Handed to later cycles:** HR / Legal / Audit / KM / SAP / SharePoint / Email packs are now
  fill-in-the-blank against the Finance template; the runtime **pack-load SPI** (how a pack is
  *loaded* at runtime) is deferred to the engineering track (open Q#6); open Q#3 (model hosting)
  still feeds each pack's eval-tuned model choice.

### Cycle 10 (2026-07-06) — Deployment: topology, environments, CI/CD & DR/BCP
- Wrote **[deployment/00-deployment-topology.md](deployment/00-deployment-topology.md)** — the
  **physical projection** of the whole platform and the **last un-seeded surface**. Introduces
  **no new logical component and no new guarantee**; it makes the existing ones affordable,
  operable, and survivable, and is the single place the **empirical sizing/tuning numbers** queued
  by Cycles 5–9 land. Collected those obligations as **D1–D8**, each tracing to its upstream source.
- **Physical projection:** the [three planes](architecture/01-platform-overview.md) map onto three
  substrates by dominant scaling axis — **edge+query** (stateless, latency-SLO autoscale),
  **ingestion** (stateless workers, scaled on **queue lag** not CPU), **data** (the only stateful
  substrate, hence the only backup/DR owner). Fail independently, blast radius stays separate.
- **Reference topology per tier (D1):** **Shared** (dense multi-tenant pool + two-control isolation)
  vs. **Isolated** (dedicated pool/cluster + per-tenant DEK/BYOK, quarantine hatch), mirroring the
  [Storage isolation tiers](storage/00-storage-architecture.md) one-to-one. **Graduation** =
  blue/green re-index through the `VectorIndex` port (no source re-hit) + a `tenant→placement`
  route flip — a data migration, not a redesign.
- **CI/CD as a safety gate (D7):** the [permission-conformance suite](permissions/00-authorization-model.md)
  is the **un-overridable release veto** (any over-permissive `map_acl` → hard fail, ships in
  quarantine never open); the [eval-before-promotion](governance/00-governance-and-audit.md) battery
  gates model changes; progressive delivery (staging → canary → prod) with the connector canary live;
  policy/allowlist/topology **as code**. **Real tenant data never leaves prod** — staging is
  synthetic but **ACL-shaped** so the gate stays meaningful.
- **SLA-capacity sizing (D2/D3):** **P0 revocation capacity is reserved, never autoscaled** (reacting
  to a revocation backlog is already a breach); P1/P2 autoscale on queue lag; relay-poll cadence set
  **below the SLA budget** — the freshness SLA is really an SLA on cache-TTL+invalidation, which
  query-time principal precedence backstops. Broker: managed queue + Postgres outbox (Shared),
  partitioned log (Isolated). **Safety is provisioned, bulk is elastic.**
- **Cost/residency (D4):** prices + envelope sizes live in a **versioned manifest** promoted through
  the pipeline (a price change is a reviewable commit into the unchanged degradation ladder); the
  safety invariant is inherited verbatim (no envelope/scale-down relaxes a permission). **Region is a
  routing fact** (`tenant→placement`), never a contract change; **data never crosses its residency class.**
- **Metadata ops (D5):** catalog partitioned by `tenant_id`; cold-lineage archival keeps tombstone/
  erasure walkability; a scheduled **lineage-integrity-check** asserts the [Metadata §7](metadata/00-catalog-and-lineage.md)
  invariants (no orphan / version monotonicity / label⊆registry / **no cross-tenant edge, R4**),
  violation → governance incident + write-quarantine.
- **DR/BCP (D8) → [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md):**
  **active-passive per residency region** (no active-active writes → **never** a window where two
  regions disagree on a revocation); **ACL-first, fail-closed recovery** (SoT→object→vector-rebuild→
  cache; permissions recover before content is queryable); **vectors rebuilt, not backed up**
  (a restored snapshot could disagree with recovered ACLs; the object-artifact rebuild is
  consistency-safe); tiered RPO/RTO (Shared ≤15 min/≤4 h, Isolated ≤5 min/≤1 h). The failover safety
  rule reuses query-time principal precedence — a failover cannot resurrect a revoked grant.
- Recorded **[ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md)**.
- Updated indexes: ADR index, `deployment/README.md` (stub → real), `platform/README.md` domain map
  (deployment → **Seeded**).
- **Directly strengthens (no new risk owned):** **closes the residual/"empirical" half of R3, R5, R8**
  (SLA-capacity sizing, prices/envelopes, autoscaling tuning now have a home) and **operationalizes R4**
  (partition pruning + the scheduled cross-tenant-edge integrity check). **All eight core platform
  surfaces are now Seeded — §5 is fully closed.**
- ⏳ **Handed to later cycles:** per-domain **pack specs** (Finance/HR/Legal — proves the "new domain =
  deployment of data+policy, not a topology change" bet end to end); open Q#3 (model-hosting posture per
  tier) feeds the concrete instance/model manifest; open Q#6 (agent framework) and the `core/`
  reconciliation remain the engineering track.

### Cycle 9 (2026-07-06) — API: external surface, contracts & versioning
- Wrote **[api/00-api-surface.md](api/00-api-surface.md)** — the platform's **outward
  contract** and the **last major un-seeded surface**. It is a *contract, not a new component*:
  the outward face of the [API Gateway](architecture/01-platform-overview.md) (Plane 1) and the
  [Governance policy store](governance/00-governance-and-audit.md). Discharges the client-facing
  needs three cycles queued (Governance → budgets/DSAR/audit-export; Metadata → catalog/lineage/
  DSAR-status; RAG+Permissions → the query endpoint that carries the subject token).
- **Five resource groups:** Query & Answer · Catalog & Lineage · Governance & Admin · Privacy &
  Audit (DSAR/erasure/export) · Ingestion ops, plus a shared async **Jobs** surface. Aligned to
  caller + owning plane/policy.
- **Six design tenets** = the outward projection of the platform principles: identity in the token
  not the URL/body; fail-closed at the edge; one envelope; heavy work is a job; idempotent writes;
  versioned & deprecable.
- **Query/answer contract:** sync `POST /v1/answers` + streaming `/v1/answers:stream`, **one
  verifier gate for both** (streamed `final` event emitted only after the verifier passes — streaming
  is never a grounding bypass). "No permitted data" is a **`200` success**
  (`grounding:"no_accessible_information"`), never an error — so absence of access can't leak as (or
  be faked as) an error. Citations expose the canonical `resource_id`+`source_item_version` from
  [Metadata §3](metadata/00-catalog-and-lineage.md).
- **Token → subject at the edge:** IdP bearer token → `{tenant, subject, effective principals,
  delegation}`; tenancy **derived from the token, never a URL segment** (impersonation
  unrepresentable). OBO via **token exchange** (actor + subject; retrieval runs under the subject).
  A **client-credentials** token has no end-user principals → a service account **structurally cannot**
  read user-restricted knowledge — kills the "index-everything under a service account" anti-pattern
  at the API layer.
- **One response envelope** `{ok,data,error,meta}` with **typed error enums**, leak-free messages,
  and `meta.request_id` == the audit correlation id; hidden resources return `not_found`, never a
  message confirming existence.
- **Admin API can only tighten:** thin self-auditing CRUD over the Governance policy store; a write
  that would loosen a platform floor (widen a label, disable the ACL filter, throttle a P0 revocation,
  raise a budget above ceiling, pin an un-evaluated model) → `422 policy_blocked`. Successor to the
  local [ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md) `control_panel.py`.
- **Privacy group** (DSAR/erasure/audit-export) = **jobs**; erasure status returns the
  [Metadata lineage-tombstone](metadata/00-catalog-and-lineage.md) evidence — completeness is
  **proven by a traversal**, `legal_hold` blocks with `422`. **Filter parity** on catalog/lineage
  reads (identical predicate to retrieval; no unfiltered "list mode" side-channel).
- **Versioning:** URL-major (`/v1/`), additive-by-default (clients must ignore unknown fields),
  breaking → new major + `Deprecation`/`Sunset` + per-version usage reporting. **A new domain pack
  is not a version event.**
- Recorded **[ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md)**.
- Updated indexes: ADR index, `api/README.md` (stub → real), `platform/README.md` domain map
  (api → **Seeded**).
- **Directly strengthens (no new risk owned):** the A1/A6 obligations — permission-faithful retrieval
  ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)) enforced once at audited
  choke points instead of re-argued per endpoint; budget/rate limits couple to
  [Governance §7.3](governance/00-governance-and-audit.md) and **throttle cost, never safety** (R5).
- ⏳ **Handed to downstream cycles:** concrete gateway/broker/topology + per-region residency routing +
  rate-limit sizing + streaming transport ops → [Deployment](deployment/); each domain pack's optional
  `pack` hint + any pack-specific endpoints ride the additive rule (no contract change).

### Cycle 8 (2026-07-06) — Metadata: catalog, lineage & classification schema
- Wrote **[metadata/00-catalog-and-lineage.md](metadata/00-catalog-and-lineage.md)** — the
  **connective-tissue schema**. Five prior cycles referred to the same nouns (`resource_id`,
  `source_item_version`, `labels`, `embed_model`, "lineage tombstone", "catalog row") but **no
  document owned their definitions**; this cycle canonicalizes them so the four consumers
  (Storage holds, Workers emits, RAG/citation + Governance/evidence read) share **one contract
  instead of four component-local shapes**. Adds **no new store** (metadata lives in the
  relational source of truth, [Storage §4.2](storage/00-storage-architecture.md)) and **no
  hot-path component** (lineage is a byproduct of the persist write already done).
- **Canonical catalog:** four-level hierarchy **Document → Item → Chunk → Version**, keyed on
  `resource_id` + `source_item_version`. The **Item** level is defined as the finest source unit
  carrying *one* ACL — that is where [RAG §2.2](rag/00-retrieval-pipeline.md)'s mixed-ACL
  invariant lives (per-message emails, per-sheet workbooks). `resource_id` = the platform-wide
  join key; `source_item_version` = the coherence key; `superseded_by` = version history
  (Principle 8). A denormalized chunk projection (labels, ACL arrays, `embed_model`,
  `section_path`) keeps retrieval + citation single-store reads.
- **Closed classification vocabulary** (M3): `sensitivity ∈ {public,internal,confidential,
  restricted:<class>}`, `pii ∈ {true,false}+pii_class:<type>`, `legal_hold ∈ {true,false}+
  matter:<id>`. **An unregistered label is a write-boundary schema violation → DLQ, never
  stored** — this is what makes the [Governance §4](governance/00-governance-and-audit.md) matrix
  *total* (every label a chunk can carry has a defined action). Unlabeled defaults to `internal`,
  never `public` (fail-closed classification).
- **Explicit lineage graph** (M2) `source→raw→parsed→chunk→vector`, emitted at persist carrying
  the ingestion `job_trace_id`, **traversable both directions**: forward = erasure-completeness +
  re-embed; backward = audit/citation evidence. The `re_embedded_from` edge is itself the proof a
  re-embed was source-independent ([Workers §6](workers/00-ingestion-architecture.md)).
- **Content-free erasure/legal-hold tombstone** (M4) — the concrete shape of
  [Storage §9](storage/00-storage-architecture.md)'s "lineage tombstone" + the
  [Governance §5](governance/00-governance-and-audit.md) legal balance (`legal_hold > erasure >
  retention`; audit retained, content erased). "No silent orphans" becomes a **provable graph
  walk**, not an assertion.
- **Metadata as the audit-evidence base** (M5): every Governance promise resolves to a catalog
  column or a lineage traversal addressable by the `resource_id`/`job_trace_id` an audit event
  already carries — [Governance §6.3](governance/00-governance-and-audit.md)'s "can the log prove
  it?" is answered by a query, not a reconstruction. Hence metadata lives transactionally with the
  ACL of record, not in a lagging analytics copy.
- **Anti-drift discipline** (M6): a `schema_version` + write-boundary validation (violation → DLQ,
  same mechanism as a malformed `map_acl`) + additive-with-migration evolution — a shared change
  can't become a silent cross-component break. Integrity invariants: every chunk has a live
  lineage path or a tombstone; version monotonicity; label ⊆ registry; no cross-tenant edge (R4).
- Recorded **[ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md)**.
- Updated indexes: ADR index, `metadata/README.md` (stub → real), `platform/README.md` domain map
  (metadata → **Seeded**).
- **Directly strengthens (no new risk owned):** R1 (quarantine now auditable via `acl_confidence`
  in the catalog + orphan check), R3 (re-sync is addressable because identifiers are canonical),
  and makes Governance's erasure/retention/label promises **provable** (the evidence is a
  traversal). Closes the **last un-seeded cross-cutting store concern** (§5).
- ⏳ **Handed to downstream cycles:** the catalog-browse / lineage / DSAR-status client surface →
  [API](api/); catalog partitioning + cold-lineage archival + the lineage-integrity-check schedule
  → [Deployment](deployment/); each domain pack registers its `restricted:<class>` /
  `pii_class:<type>` values in the classification registry ([Metadata §4.1](metadata/00-catalog-and-lineage.md)).

### Cycle 7 (2026-07-06) — Governance, audit & cost
- Wrote **[governance/00-governance-and-audit.md](governance/00-governance-and-audit.md)** —
  the **policy plane**. Governance owns *policy, not mechanism*: it adds **no hot-path runtime
  component**, only a versioned (itself-audited) policy store + a reporting/metering surface over
  the existing [audit store](storage/00-storage-architecture.md); every enforcement point already
  exists (Model Gateway, retrieval filter/redactor, worker scheduler). Closes the three
  ratifications the upstream cycles queued (G1–G3) plus audit usage (G4), cost/R5 (G5), model
  governance (G6), and compliance mapping (G7).
- **Ratified freshness SLA (closes open Q#7):** contractual per-tier numbers — principal change
  **≤5 min** (Standard) / **≤2 min** (Isolated); restrictive resource-ACL **≤15 / ≤5 min**;
  widening ≤60 / ≤15 min; public best-effort. A breach = alarm **+** recorded governance incident
  (contractual reporting event for Isolated). Made affordable by the fact that query-time principal
  precedence ([Storage §7](storage/00-storage-architecture.md)) already closes offboarding
  independent of the re-tag — the tight number is really an SLA on cache-TTL+invalidation.
- **Ratified label→action policy:** platform-owned default matrix (`public`/`internal`/
  `confidential`/`pii`/`legal_hold`/`restricted:<class>`) mapping each label to retrieval / prompt /
  routing / egress, composing **most-restrictive-wins**; tenants may **tighten, never loosen**;
  labels can only subtract capability ([Permissions §7](permissions/00-authorization-model.md)
  invariant preserved).
- **Ratified retention / erasure / legal-hold:** per-store schedule (audit ≥1 yr hot / ≥7 yr cold;
  raw object 90 d→archival; DLQ 30 d; cache 5–15 min); right-to-erasure as an SLA-bound DSAR
  workflow using [Storage §9](storage/00-storage-architecture.md) propagation, **erasure recorded as
  an audit event**, **audit trail itself exempt**; precedence **legal-hold > erasure > retention**.
- **Cost model & R5 (design-mitigated):** every cost-bearing event carries `tenant_id`; per-tenant→
  pack→workload attribution; budget envelopes degrade **capability before safety** (80–100 % →
  cheaper tier + defer P2 + tighten cache; 100 % → block new P2, queue P1, alert). **A budget cap
  can never relax a permission, skip the ACL filter, or throttle a P0 revocation** — fail-closed on
  spend.
- **Audit-as-evidence:** *a promise the audit log can't evidence is not a governable promise* —
  the SLA, labels, erasure, and budgets are each proven by their event type; audit read access is
  role-gated + itself audited; hash-chain verified on schedule.
- **Model governance:** approved-model registry + **eval-before-promotion** gate (grounding, refusal
  calibration, jailbreak resistance, pack task accuracy) + per-tenant version pinning/rollback + model
  version in every retrieval audit event. **Compliance map** binds existing controls to GDPR / SOX /
  ISO 27001-SOC 2 / sector per domain, each cell evidence-backed.
- Recorded **[ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)**.
- Updated indexes: ADR index, `governance/README.md` (stub → real), `platform/README.md` domain
  map (governance → **Seeded**).
- **Directly de-risks:** R5 (cost → metering + attribution + budget envelopes + safety-preserving
  degradation ladder); **closes the SLA-number half of R3** and the label-policy dependency.
- **Closed open question #7** (freshness SLA — ratified) — see §3.
- ⏳ **Handed to downstream cycles:** actual prices / budget-envelope sizes / per-tier SLA capacity
  sizing / data residency → [Deployment](deployment/); classification schema the label policy
  consumes → [Metadata](metadata/); the client-facing surface for budgets / DSAR / audit export →
  [API](api/). Open Q#3 (model hosting) feeds the approved-model registry when decided.

### Cycle 6 (2026-07-05) — Ingestion workers & connectors
- Wrote **[workers/00-ingestion-architecture.md](workers/00-ingestion-architecture.md)** — the
  write-plane engine. Turns the Cycle 3–5 write-side obligations (W1 idempotent version-keyed
  writes, W2 ACL-denorm coherence, W3 change-driven re-sync, W4 source-independent re-embed,
  W5 mixed-ACL invariant at write time, W6 least-privilege per-tenant execution, W7 backpressure)
  into a selected shape: a **staged DAG** (fetch → parse → map_acl → chunk → embed → persist),
  each stage reading/writing a durable artifact so failures resume without re-hitting the source.
- Wrote **[workers/01-connector-framework.md](workers/01-connector-framework.md)** — the
  source-specific boundary: a **six-method `Connector` port** (`list_items`, `fetch`, `map_acl`,
  `subscribe_changes`, `list_principal_changes`, `capabilities`); per-source `map_acl` duties
  (R1 implementation); versioning + fault isolation (R6); and the **permission-conformance suite
  as the production gate** ([Permissions §11](permissions/00-authorization-model.md)) running in
  CI **and** a production canary that **auto-quarantines** a source on drift.
- **Key decisions:** (a) **at-least-once delivery + idempotent version-keyed writes** — refuse
  exactly-once, make replays/outbox-double-delivery harmless; (b) **strict priority classes with
  fairness guards** (P0 revocation/security ≤5/≤15 min · P1 content delta · P2 backfill/re-embed/
  reconciliation) so a backfill can **never** starve a revocation (**R8 core**); (c) the
  [Storage §7](storage/00-storage-architecture.md) coherence relay = **transactional outbox** at
  the dedicated-engine tier (pgvector tier stays same-transaction); (d) re-embed/re-chunk =
  **blue/green P2 jobs reading the parsed object artifact, never the source**
  ([Storage §8](storage/00-storage-architecture.md)); (e) **least privilege split** — the
  read-source credential and the write-ACL credential live in different worker pools; (f) under
  load the plane **drops recall before it drops a revocation** (fail-closed on the write path).
- Recorded **[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md)**.
- Updated indexes: ADR index, `workers/README.md` (stub → real), `platform/README.md` domain
  map (workers → **Seeded**).
- **Directly de-risks:** R8 (backlog → freshness: priority + fairness + lag alarms, made
  *observable*), R6 (connector fragility: independent versioning + schema-validated boundary +
  conformance canary), R3 write-half (change-driven content/ACL re-sync + P0 principal re-sync).
- **Strengthened open question #7** (freshness SLA): the priority-class model now *implements*
  the proposed ≤5/≤15 min targets and the relay-lag/queue-lag alarms that enforce them — still
  **pending [Governance](governance/) ratification** of the actual numbers.
- ⏳ **Handed to downstream cycles:** freshness-SLA ratification (Q#7) + per-tenant ingest cost +
  DLQ/retention policy → [Governance](governance/) (Cycle 7); concrete broker choice per tier +
  worker autoscaling topology + secret provisioning → [Deployment](deployment/); lineage schema
  emitted by the persist stage → [Metadata](metadata/).

### Cycle 5 (2026-07-05) — Storage & tenancy deep dive
- Wrote **[storage/00-storage-architecture.md](storage/00-storage-architecture.md)** — the
  data-plane payoff. Turns the Cycle 3+4 hard requirements (S1 set-overlap filtering,
  S2 hybrid-under-one-filter, S3 versioned upsert/delete, S4 isolation-by-construction,
  S5 in-boundary+BYOK, S6 rich metadata, S7 append-only audit) into a selected topology:
  the **five-store data plane** (object / vector+keyword / relational-source-of-truth /
  cache / append-only audit), each assigned by scaling axis, consistency, and blast radius.
- **Resolved open question #1 (FINAL):** vector layer = **pgvector-in-Postgres as default**
  (co-locates vector + `text[]` ACL arrays w/ GIN `&&` + `tsvector` full-text + metadata in
  one transaction → both hybrid halves share one filter, ACL denormalization is drift-free),
  **graduating** per-tenant to Qdrant / Elasticsearch on *measured* thresholds. Confirms &
  finalizes [ADR-0009 §6](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)'s
  provisional lean. Introduced the **`VectorIndex` port with no unfiltered-search method** —
  filter-during-retrieval ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md))
  becomes *structurally* impossible to bypass, and vector lock-in (R7) is bounded to one adapter.
- **Resolved open question #5 (FINAL):** **a tenant = one customer organization** (isolation
  & governance boundary); departments/domains are ACL/`visibility` scopes and packs *within*
  a tenant — aligns the storage isolation primitive with the CPI identity namespace.
- Specified **two isolation tiers** per store (Shared: namespace/schema/prefix + RLS +
  unconditional `tenant_id`, two independent controls; Isolated: dedicated cluster/DB/bucket +
  BYOK), **envelope encryption w/ per-tenant DEKs + crypto-erasure**, the
  **ACL-denormalization coherence** rules (same-transaction at pgvector tier; transactional
  outbox at dedicated-engine tier; query-time principal precedence covers the residual gap),
  **re-embed migrations** (blue/green from the parsed object-store artifact — no source re-hit),
  and **right-to-erasure** propagation across all five stores (audit retained as event).
- Recorded **[ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)**.
- Updated indexes: ADR index, `storage/README.md` (stub → real), `platform/README.md`
  domain map (storage → **Seeded**).
- **Directly de-risks:** R4 (cross-tenant → namespace **and** predicate, two controls;
  per-tenant DEK), R5 (cost → pgvector-default + object tiering + quantization levers),
  R7 (vector lock-in → `VectorIndex` port, one adapter per engine).
- ⏳ **Handed to downstream cycles:** the **transactional-outbox relay** + **re-embed/re-sync
  jobs** → [Workers](workers/) (Cycle 6, must honor the §7 coherence bound and the freshness
  SLA); **retention + legal-hold tombstone + per-tenant cost metering + erasure ratification**
  → [Governance](governance/) (Cycle 7); **per-tier topology, graduation thresholds, backup/DR**
  → [Deployment](deployment/); **catalog + lineage schema** detail → [Metadata](metadata/).

### Cycle 4 (2026-07-05) — RAG retrieval pipeline deep dive
- Wrote **[rag/00-retrieval-pipeline.md](rag/00-retrieval-pipeline.md)** — the query-plane
  payoff. Specifies **structure-aware chunking** (heading/clause/table-row/per-email-message,
  with the **mixed-ACL invariant**: a chunk never spans two items with different ACLs),
  **universal embedding space + per-domain normalization** (not per-domain models;
  versioned re-embed on model upgrade), **hybrid search** (dense + BM25, RRF fusion) with
  the **permission predicate pushed into *both* engines** (consumed from Permissions §6,
  not re-specified), **cross-encoder reranking** (+ MMR, degradable latency dial), **context
  assembly** (dedup / budget / cite-tag / label redaction) with the **prompt-injection (R2)
  data-boundary defense**, the **verifier contract** (grounding / citation validity /
  no-context honesty / guardrails / label compliance — refuse-over-guess), a latency budget,
  and a **provisional vector-store position** (open Q#1).
- Recorded **[ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)** —
  hybrid permission-filtered retrieval + structure-aware chunking. Obeys ADR-0004, pushes
  the ADR-0008 predicate into search, mediated by ADR-0003 gateway.
- Updated indexes: ADR index, `rag/README.md` (stub → real), `platform/README.md` domain
  map (rag → **Seeded**).
- **Directly de-risks:** R2 (prompt injection → retrieved-text-as-data boundary + verifier
  backstop). Design mitigation now documented, not just named.
- **Answered open questions:** #4 (chunking & embedding strategy — **decided**:
  structure-aware chunking + universal space + per-domain normalization).
- **Provisionally answered:** #1 (vector store — pgvector for small tenants graduating to a
  dedicated engine; **Storage/Cycle 5 owns the final call**).
- ⏳ **Handed to downstream cycles:** vector + keyword indexes must support efficient
  **set-overlap filtering** on principal arrays and **hybrid search under one metadata
  filter** (hard selection criteria → Storage); chunk parsers per content-type + embedding
  jobs + re-embed migration → Workers; audit-trail fields (principals, chunk IDs, rerank
  scores, verifier verdict) → Governance.

### Cycle 3 (2026-07-05) — Permissions & Identity deep dive
- Wrote **[permissions/00-authorization-model.md](permissions/00-authorization-model.md)** —
  the platform's hardest correctness guarantee. Defines the **canonical four-noun model**
  (Subject / Principal / Grant / Resource), the **Canonical Principal Identifier**
  (`tenant:source:type:stable-id`, keyed on non-reusable source ids), the **single
  decision predicate** (tenant → confidence=`exact` → deny-wins → require-allow),
  query-time **effective-principal resolution** via an identity graph (nested-group
  expansion + explicit cross-source links), **filter-during-retrieval** mechanics,
  per-source ACL mapping (SharePoint / SAP / Email / file share), **sensitivity labels as
  a second independent gate**, the **freshness** strategy (query-time precedence + short
  revocable TTL + change-driven re-sync), the **unmappable-source quarantine doctrine**,
  delegated/OBO access, and the **permission-conformance test suite** (the production gate).
- Recorded **[ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)** —
  normalize every source ACL into one canonical model (the *how* behind ADR-0004's *what*).
  Owns risks R1, R3, R4.
- Updated indexes: ADR index, `permissions/README.md` (stub → real), `platform/README.md`
  domain map (permissions → **Seeded**).
- **Directly de-risks:** R1 (mismatch → conformance suite + confidence-gated deny),
  R3 (staleness → query-time precedence + SLA), R4 (cross-tenant → tenant-namespaced CPIs).
- **Provisionally answered open questions:** #2 (permission normalization model — decided),
  #7 (freshness SLA — proposed: principals ≤5 min, restricted resource ACLs ≤15 min,
  pending Governance ratification).
- ⏳ **Handed to downstream cycles:** vector store must support efficient **set-overlap
  filtering** on principal arrays (hard requirement → Storage, open question #1); label
  policy + SLA ratification → Governance; change-driven re-sync → Workers.

### Cycle 2b (2026-07-05) — v3.0 harvest + client settings UI
- **Client settings UI** ([ADR-0007](architecture/adr/ADR-0007-client-configuration-surface.md)):
  `control_panel.py` + `EINSTELLUNGEN.bat` — browser page (stdlib only) to set autonomy,
  models, limits **and manage connectors** (`connectors.yaml` allowlist) with validation;
  syncs `config.json` + `project/manifest.json`. End-to-end tested.
- **Harvested v3.0 assets onto the core** ([ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md)):
  `core/workers.py` (least-privilege WorkerRegistry), `core/handoff.py` (allowlisted
  router), `tools/check.py` (project-pack validator, CI exit codes),
  `scripts/deploy.{sh,ps1}`, `pytest.ini`, `requirements-dev.txt`. Added `workers`/
  `handoffs` config to `project/manifest.json`.
- **Tests:** 62 green (23 workers + 24 handoff + 11 check + 4 tools).
- ⏳ **Still staged (not done):** wiring `WorkerRegistry`/`HandoffRouter` INTO
  `core/orchestrator` at runtime; rewriting v3.0's `test_agent.py` against `core/`;
  retargeting `test_brain`/`test_governance`; coverage gate `--cov=core --cov-fail-under=80`;
  deeper governance hardening (high-risk block before autonomy shortcut, per ADR-0006).

### Cycle 2 (2026-07-05) — Branch consolidation (design council)
- Convened a **5-member design council** (Enterprise Architect, Senior Engineer,
  Security & Governance, QA & Test, Redundancy & Consistency) to reconcile 4 divergent
  template branches into "the perfect agent template."
- **Decision → [ADR-0005](architecture/adr/ADR-0005-template-consolidation-council.md):**
  keep `core/`+`project/` as base, **merged `tender-feistel`** (skills, connectors,
  steering examples, leaf-write governance, financial-services patterns), and defined a
  **harvest plan** for the v3.0 (`kind-keller`) fork instead of merging it wholesale.
- **Security fix → [ADR-0006](architecture/adr/ADR-0006-fail-closed-autonomy-default.md):**
  reverted the fail-open full-autonomy default to **fail-closed-by-default**
  (`core/governance.py._approval_required` now defaults True; autonomy is explicit opt-in
  via `autonomy_level: "max"`).
- Merge landed on `main`, core modules import clean, existing tests pass.
- ⏳ **Not yet merged:** the v3.0 asset harvest (see §6 Cycle 2b) and the other
  contained branches are superseded.

### Cycle 1 (2026-07-05) — Foundation
- Established `platform/` as the documentation root with a per-concern folder layout
  (architecture, security, rag, permissions, storage, metadata, workers, api,
  deployment, governance) and a navigation index (`platform/README.md`).
- **[Vision & Principles](architecture/00-vision-and-principles.md)** — mission,
  target domains, 8 non-negotiable principles, honest trade-offs, non-goals.
- **[Platform Overview](architecture/01-platform-overview.md)** — C4 context +
  container diagrams, the **three-plane model** (Query / Ingestion / Data + cross-
  cutting), request and ingestion lifecycles as sequence diagrams.
- **[Security Architecture](security/00-security-architecture.md)** — trust boundary,
  identity/authz, multi-tenant isolation tiers, data protection, STRIDE + OWASP-LLM
  threat model, fail-closed doctrine.
- **[ADR log](architecture/adr/)** — ADR-0001 (private RAG shape), ADR-0002 (reuse
  template core as tenancy seed), ADR-0003 (model gateway), ADR-0004 (permission-
  faithful retrieval).

---

## 2. Architecture decisions (accepted so far)

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| ADR-0001 | Privately-hosted, permission-aware RAG | Fresh, auditable, per-user-filterable knowledge in-boundary |
| ADR-0002 | Reuse template core/project split as tenancy seed | Continuity; domain-agnostic core already proven |
| ADR-0003 | All inference via a Model Gateway | One choke point for governance, cost, vendor independence |
| ADR-0004 | Enforce end-user permissions at query time | Safe for Finance/HR/Legal/Audit; fail closed |
| ADR-0008 | Normalize every source ACL into one canonical principal model | One filterable predicate; new source = connector + conformance test, not a redesign |
| ADR-0009 | Hybrid permission-filtered retrieval + structure-aware chunking | Exact-token + semantic recall; safety stays one index predicate; new domain = parser, not a pipeline change |
| ADR-0010 | Five-store data plane; pgvector-default vector layer (graduate on measured need) behind a filter-only `VectorIndex` port; tenant = customer org | Meets every S1–S7 requirement; ACL stays a single-store `WHERE`; unfiltered search is unrepresentable; lock-in bounded to one adapter |
| ADR-0011 | Ingestion = staged-DAG workers; at-least-once + idempotent version-keyed writes; priority classes (P0 revoke > P1 delta > P2 backfill); outbox coherence relay; conformance-gated connector contract | Resumable/scalable/contained ingestion; backlog can't starve a revocation (R8); new source = connector + suite, not redesign; write path fail-closed |
| ADR-0012 | Governance = policy plane (no hot-path component); ratified per-tier freshness SLA + label→action matrix + retention/erasure; audit-as-evidence; per-tenant budgets that degrade capability-before-safety; eval-gated model registry; per-domain compliance map | Promises become contractual & provable; cost control (R5) can never regress into a safety leak; new domain inherits a control map, not a redesign |
| ADR-0013 | Canonical metadata: four-level catalog (Doc→Item→Chunk→Version) + explicit bidirectional lineage graph + closed classification vocabulary + content-free erasure tombstone; held in the relational SoT, no new store; versioned + write-boundary-validated | Four consumers share one contract not four shapes; the Governance label matrix becomes total; erasure-completeness & audit-evidence become provable queries; new domain/artifact type = additive registration, not a schema redesign |
| ADR-0014 | API contract: token-bound identity (tenancy never in URL) + OBO via token exchange; dual sync/streaming answer under one verifier gate; "no access" is a 200; one typed-error envelope; heavy work = jobs; admin-can-only-tighten; filter-parity reads; URL-major additive versioning | Permission-faithful retrieval enforced once at audited choke points not re-argued per endpoint; impersonation/cross-tenant unrepresentable on the wire; budgets throttle cost not safety; new pack = additive, not a version event |
| ADR-0015 | Deployment DR: active-passive per residency region (no active-active writes); ACL-first fail-closed recovery (SoT→object→vector-rebuild→cache); vectors rebuilt not backed up; tiered RPO/RTO; reserved (not autoscaled) P0 capacity | No cross-region window disagrees on a revocation; the platform recovers fail-closed (permissions before content); a restore can't resurrect a vector snapshot that disagrees with recovered ACLs; the revocation SLA is provisioned in advance |
| ADR-0016 | Domain pack contract: a pack is additive data + policy, **tighten-only**, exactly six sections, with a mandatory §0 horizontal-change ledger + a falsifiability rule (can't-fit → horizontal ADR, never a pack-local hack) | Makes "new domain = pack, not redesign" a reviewable/blockable contract not a slogan; a misconfigured pack can only over-restrict (availability), never over-expose (safety); Finance (reference pack) proved zero horizontal changes against the hardest domain |
| ADR-0017 | Runtime pack-load SPI: a validating, transactional, fail-closed loader (RESOLVE→VALIDATE→DRY-RUN→COMMIT-atomic→ACTIVATE-scoped) installing the six sections into their horizontal extension points; signed data-only bundle (connector referenced, never shipped); machine-checked §0 ledger; per-tenant `pack_version` pinning; no code deploy | Makes ADR-0016's tighten-only rule **executable** — a floor-loosening pack is *structurally* rejected by the loader, not by review; the worst a bad/malicious pack does is fail to load (availability), never loosen a floor (safety); the first `platform/`→`core/` reconciliation target |
| ADR-0018 | Model hosting & serving posture: a dual-track serving fabric (Track A in-boundary self-hosted OSS / Track B contractually-private managed endpoints) routed per `(tenant tier × data class)` by the label→trust matrix behind the Model Gateway; closed `hosting_posture` registry enum + mandatory data-handling terms; fail-closed track-fallback | Closes open Q#3 with the honest *both-by-tier* answer, expressible as pure policy because ADR-0003 built the Gateway indirection first; the trust floor may never degrade (a `pii` request never spills to a cheaper track); no new hot-path component, read plane untouched — additive |
| ADR-0019 | Agent orchestration posture: extend `core/`'s planner/dispatcher/verifier/governance loop into the distributed multi-agent orchestrator (the choke points stay ours and in-boundary — the *decision plane*); adopt commodity durable execution behind an `ExecutionBackend` port (the *execution plane*, no decision method) for distributed plumbing only; bounded pack-declared allowlisted agent graphs; never a framework that owns the loop | Closes open Q#6; the five gates all live *inside* the loop, so a framework that owns the loop is a competing choke point — extending `core/` keeps them un-bypassable; the same five gates re-hosted (no new predicate), lock-in bounded to one adapter (the Gateway/`VectorIndex` bargain, 3rd use), multi-agent flow = pack not redesign — additive |

---

## 3. Open questions (need a decision in an upcoming cycle)

1. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Vector store choice~~ — **pgvector-in-Postgres is the default** (co-locates vector +
   `text[]` ACL arrays w/ GIN `&&` + `tsvector` + metadata in one transactional store),
   **graduating per-tenant** to Qdrant / Elasticsearch on *measured* thresholds (chunk count,
   QPS/SLA, keyword dominance, isolation mandate). All engines sit behind a **`VectorIndex`
   port that has no unfiltered-search method**. See [Storage §3](storage/00-storage-architecture.md).
   Remaining sub-question deferred to [Workers](workers/): the transactional-outbox relay
   that keeps the denormalized chunk-ACL coherent at the dedicated-engine tier.
2. ✅ **DECIDED (Cycle 3, [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md)); sub-question RESOLVED (Cycle 16).**
   ~~Permission normalization model~~ — canonical four-noun model + CPI, normalize at
   ingestion, enforce one predicate at query time. **The deferred sub-question — *exact
   `map_acl` fidelity achievable per SAP module* — is resolved by the
   [SAP pack §1 three-band fidelity matrix](packs/sap/00-sap-pack.md):** FI/CO, MM, SD org-level
   → **Band A `exact`**; HCM structural authorizations → **Band B** (resolve-to-principal-set +
   re-sync, else quarantine); FI field-level / infotype subfield / BW analysis authorizations →
   **Band C** quarantine. The bands are jointly exhaustive — no SAP construct is neither
   resolvable nor quarantinable, so no new confidence level / predicate was needed.
3. ✅ **DECIDED (Cycle 22, [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md)).**
   ~~Model hosting~~ — a **dual-track serving fabric behind the Model Gateway**: **Track A**
   (in-boundary self-hosted OSS on reserved GPUs — privacy/residency by physical construction) +
   **Track B** (contractually-private managed endpoints over private networking, zero-retention/no-train),
   **routed per `(tenant tier × data class)`** by the existing label→trust matrix (**Isolated → Track A
   only; Standard → Track B default with a `confidential`/`pii` floor to the highest-trust track**).
   Hosting posture is now a **closed registry enum** (`in_boundary_oss`/`managed_private`/
   `managed_private_dedicated`) with mandatory data-handling terms; routing is **fail-closed** (no silent
   fallback to a lower-trust track). See [Models §2–§4](models/00-model-hosting-and-serving.md). Net
   horizontal change = none (two data values + one boundary condition behind ADR-0003). Empirical GPU-pool
   sizing / managed-endpoint pricing handed to [Deployment §7](deployment/00-deployment-topology.md);
   network-boundary hardening handed to [Security](security/00-security-architecture.md).
4. ✅ **DECIDED (Cycle 4, [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md)).**
   ~~Chunking & embedding strategy~~ — **structure-aware chunking** (heading/clause/table-row/
   per-email-message; mixed-ACL invariant) + **universal embedding space with per-domain
   text normalization** (not per-domain models) + versioned re-embed on model upgrade. See
   [RAG §2–§3](rag/00-retrieval-pipeline.md). Remaining sub-question deferred to Workers:
   the exact per-content-type parser fidelity (OCR layout, SAP table serialization).
5. ✅ **DECIDED (Cycle 5, [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md)).**
   ~~Tenancy granularity~~ — **a tenant = one customer organization** (isolation & governance
   boundary owning its data, identity namespace, policies, cost envelope). Departments and
   domains are ACL/`visibility` scopes and packs *within* a tenant, not separate tenants —
   this keeps the CPI identity namespace and nested-group resolution intact. See
   [Storage §5](storage/00-storage-architecture.md).
6. ✅ **DECIDED (Cycle 23, [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)).**
   ~~Agent framework~~ — **extend the existing `core/` planner/verifier into the distributed
   orchestrator; do NOT adopt a framework that owns the plan→act loop, tool-calling, routing, or the
   answer gate.** The decision plane (planner/governance/dispatcher/verifier/handoff/tool-scope) stays
   ours and in-boundary because the platform's five choke points all live *inside* the loop; the
   distributed *execution* plane (durable state/retries/timers/fan-out) is adopted commodity behind an
   `ExecutionBackend` port with **no decision method** (the [`VectorIndex`](storage/00-storage-architecture.md#34-the-abstraction-that-prevents-lock-in-r7)/[Gateway](architecture/adr/ADR-0003-model-gateway-indirection.md)
   "commodity behind a port" bargain, reused a 3rd time). Multi-agent is a **bounded DAG over a
   pack-declared allowlisted agent graph** ([`HandoffRouter`](../core/handoff.py) +
   [`WorkerRegistry`](../core/workers.py) re-hosted), installed by the [pack-load SPI](packs/01-pack-load-spi.md)
   as validated config. See [Orchestration §2–§6](orchestration/00-agent-orchestration.md). Net horizontal
   change = none — the same five gates re-hosted, no new predicate/choke-point, lock-in bounded to one
   adapter. This discharges [ADR-0002](architecture/adr/ADR-0002-reuse-existing-template-core.md)'s
   "Revisit when." Remaining: the **`core/` implementation** (engineering track) + substrate sizing →
   [Deployment](deployment/00-deployment-topology.md), handoff-edge hardening → [Security](security/00-security-architecture.md).
7. ✅ **DECIDED (Cycle 7, [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md)).**
   ~~Freshness SLA~~ — **ratified as contractual per-tier numbers**
   ([Governance §3](governance/00-governance-and-audit.md)): principal change ≤5 min
   (Standard) / ≤2 min (Isolated); restrictive resource-ACL ≤15 / ≤5 min; widening ≤60 / ≤15 min;
   public best-effort. A breach is an alarm **and** a recorded governance incident (contractual
   reporting event for Isolated tenants). Workers already *implements and measures* these
   ([workers §4.2, §10](workers/00-ingestion-architecture.md)); Governance fixed the promise +
   consequences. Remaining sub-question deferred to [Deployment](deployment/): the
   reserved-P0-capacity / relay-poll-frequency **sizing** that meets each ratified number at cost
   (a tuning knob, not a redesign).

---

## 4. Technical risks (tracked)

| # | Risk | Severity | Mitigation direction |
|---|------|----------|----------------------|
| R1 | **Permission-model mismatch** — source ACLs can't be faithfully normalized → leak | **Critical** | ✅ *Design mitigated (Cycle 3):* canonical model + `acl_confidence` gate (approximate→deny) + per-connector conformance suite + quarantine tier. Residual: correct **implementation** of each connector's `map_acl`. |
| R2 | **Prompt injection via retrieved content** | **Critical** | ✅ *Design mitigated (Cycle 4, [RAG §6.1, §7](rag/00-retrieval-pipeline.md)):* retrieved text delivered inside a data boundary (not instructions), retrieved content cannot alter tool/routing/citation policy, verifier enforces grounding + guardrails as the backstop. Residual: implementation hardening of the verifier + red-team corpus. |
| R3 | **Stale permissions** — user loses access but index still serves it | High | ✅ *Design mitigated (Cycles 3+6):* query-time principal precedence ([Permissions §8](permissions/00-authorization-model.md)) closes offboarding regardless of chunk lag; the write half — **change-driven content/ACL re-sync at P0/P1** + the **outbox relay bounded by the freshness SLA** ([workers §5, §7](workers/00-ingestion-architecture.md)) — closes the resource-re-tag case; relay/queue lag is alarmed (§10). Residual: SLA number ratification (Q#7). |
| R4 | **Cross-tenant leakage** via a filtering bug | High | ✅ *Design mitigated (Cycle 5, [Storage §5.2](storage/00-storage-architecture.md)):* Shared tier uses **two independent controls** (per-tenant namespace/schema **and** an unconditional `tenant_id` predicate); Isolated tier = dedicated cluster/DB/bucket + per-tenant DEK; the `VectorIndex` port takes a `tenant` on every call (cross-tenant query unrepresentable). Residual: correct namespace provisioning per tenant. |
| R5 | **Cost blow-up** — inference + storage at 10× data/tenants | High | ✅ *Design mitigated (Cycle 7, [Governance §7](governance/00-governance-and-audit.md)):* per-tenant **metering + attribution** (every cost event carries `tenant_id`, assembled tenant→pack→workload), **budget envelopes**, and a **graceful-degradation ladder** that degrades *capability before safety* (cheaper model tier + defer P2 + tighten cache; then block new P2, queue P1) — **a budget cap can never relax a permission, skip the ACL filter, or throttle a P0 revocation**. Upstream levers (model tiering [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md), quantization/tiering [Storage §10](storage/00-storage-architecture.md), embed batching [Workers §4.3](workers/00-ingestion-architecture.md)) now have an owner that pulls them. Residual: actual **prices + envelope sizes** per tier ([Deployment](deployment/), empirical). |
| R6 | **Connector fragility** — source API changes break ingestion/permissions | Medium | ✅ *Design mitigated (Cycle 6, [connector §3, §5](workers/01-connector-framework.md)):* independently-versioned connectors + a **schema-validated** return boundary (malformed ACL → DLQ, never the store) + the **conformance suite as a production canary** that **auto-quarantines** a source on semantic drift. Residual: implementation of each connector's change-detection. |
| R7 | **Vendor lock-in** at model or vector layer | Medium | ✅ *Design mitigated (Cycle 5, [Storage §3.4](storage/00-storage-architecture.md)):* the **`VectorIndex` port** confines each engine to one adapter; a tenant migration is a re-index through the port, not a pipeline rewrite (the vector-layer analogue of the Model Gateway). Models already covered by [ADR-0003](architecture/adr/ADR-0003-model-gateway-indirection.md). |
| R8 | **Ingestion backlog** starves freshness | Medium | ✅ *Design mitigated (Cycle 6, [workers §4, §10](workers/00-ingestion-architecture.md)):* **strict priority classes** (P0 revoke > P1 delta > P2 backfill) with **fairness guards** so a backfill can't starve a revocation; bounded-lease backpressure; per-tenant weighted-fair scheduling; **queue-lag alarms** make a looming SLA breach loud, not silent. Residual: autoscaling tuning ([Deployment](deployment/)). |

---

## 5. Documentation gaps (folders still empty / thin)

- ✅ `rag/` — retrieval pipeline (chunking, hybrid search, reranking, grounding, verifier). **Seeded (Cycle 4).**
- ✅ `permissions/` — canonical ACL model + per-source mapping. **Seeded (Cycle 3).**
- ✅ `storage/` — five-store data plane, pgvector-default vector layer + `VectorIndex` port, tenancy definition, isolation tiers, encryption/BYOK, coherence, migrations, erasure. **Seeded (Cycle 5).** Resolved open Q#1 (final) + Q#5 (final); mitigated R4/R5/R7 by design.
- ✅ `workers/` — staged-DAG ingestion, `IngestionTask` queue + idempotent version-keyed writes, priority classes (R8), outbox coherence relay, re-embed migrations, change-driven re-sync, DLQ, least-privilege posture, connector contract + conformance gate. **Seeded (Cycle 6).** Mitigated R8/R6/R3-write by design; strengthened Q#7.
- ✅ `metadata/` — canonical four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification/label vocabulary, content-free erasure tombstone, metadata-as-audit-evidence, schema versioning/validation. **Seeded (Cycle 8).** Closed the last un-seeded cross-cutting store concern; made Governance's label matrix total and its erasure/audit promises provable.
- ✅ `api/` — external surface: five resource groups, token-bound identity + OBO, query/answer + streaming contract (one verifier gate), one typed-error envelope, async-job pattern, admin-can-only-tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major versioning. **Seeded (Cycle 9).** Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued; enforced permission-faithfulness once at the edge.
- ✅ `deployment/` — physical projection: per-tier reference topology + graduation, environments,
  safety-gated CI/CD (conformance suite as un-overridable release veto), reserved-P0 SLA-capacity
  sizing, cost-envelope/residency routing, catalog partitioning + cold-lineage archival + integrity
  checks, gateway/rate-limit/streaming ops, and **ACL-first active-passive DR/BCP** with per-store
  backup/restore. **Seeded (Cycle 10).** Discharged the sizing/tuning inputs Cycles 5–9 queued;
  closed the residual/empirical half of R3/R5/R8 and operationalized R4.

- ✅ `models/` — dual-track model hosting & serving (in-boundary OSS vs. contractually-private managed),
  per-`(tenant tier × data class)` routing behind the Model Gateway, closed `hosting_posture` registry enum,
  fail-closed track-fallback. **Seeded (Cycle 22).** Resolved open Q#3.
- ✅ `orchestration/` — agent orchestration posture: extend `core/`'s planner/verifier loop into the
  distributed multi-agent orchestrator (choke points stay ours — the decision plane); commodity durable
  execution behind an `ExecutionBackend` port (the execution plane, no decision method); bounded pack-declared
  allowlisted agent graphs; the same five gates re-hosted. **Seeded (Cycle 23).** Resolved open Q#6.
- ✅ `engineering/` — the `platform/`→`core/` reconciliation track: ground-truth `core/` audit + gap ledger
  (G1–G8) + sequenced TDD build plan discharging [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)
  (pack-load loader) and [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md) (orchestrator
  re-host). **Seeded (Cycle 24).** Surfaced that `core/orchestrator.py` calls neither `WorkerRegistry` nor
  `HandoffRouter` (inert gates) → made wiring them the first WP. No new architectural gap; this is the
  *implementation* bridge, not a new surface.

**→ All core platform surfaces (architecture, security, permissions, rag, storage, workers, metadata, api,
governance, deployment, models, orchestration) are now Seeded, and every open architecture question (Q#1–Q#7)
is closed. §5 is fully closed.** The remaining work is purely the **engineering track**: the `platform/`→`core/`
code reconciliation (implement the pack-load SPI + the orchestrator loop) + empirical sizing/hardening inputs.
- ✅ `governance/` — policy plane: ratified freshness SLA + label→action matrix + retention/erasure, audit usage (retention/access/evidence), per-tenant cost model & budgets (R5), model governance, compliance map. **Seeded (Cycle 7).** Closed open Q#7; mitigated R5 by design.

---

## 6. Priority list & recommended implementation order

Ordered by **architectural leverage** (unblocks the most, de-risks the most).

### ✅ Cycle 2b (DONE — see §1): harvested deploy scripts, `tools/check.py`,
`core/workers.py`, `core/handoff.py`, tests (62 green), and shipped the client settings
UI with connector management. Remaining harvest work moved to Cycle 2c below.

### ✅ Cycle 2c (DONE — discharged by Cycles 25–26; see §1):
**Wire the harvested modules into the runtime + finish tests.** Code work on the `core/`
template, independent of the platform architecture docs.
1. ✅ **DONE (Cycle 25)** — `WorkerRegistry` + `HandoffRouter` are wired into
   `core/orchestrator.run` (tool-scope + handoff enforced in the loop, negative-tested).
2. ✅ **DONE (Cycle 26, WP-C1)** — legacy LLM-path modules backfilled with mocked-model
   tests (whole-`core` 75 %→92.9 %); `pytest.ini` + `.github/workflows/ci.yml` enforce
   `--cov=core --cov-fail-under=80`.
3. ✅ **DONE (Cycle 25, WP-A5)** — the high-risk hard block runs *before* the autonomy
   shortcut; escalation is a deterministic keyword policy, not an LLM `needs_human` flag.
4. ⏸ **Open (only non-reconciliation item left)** — onboarding UX polish (fold kind's
   plain-German prompts + self-test into `agent_cli.py`; `.bat` robustness); then delete the
   superseded `kind-keller` branch.
**Do NOT push a broken tree — gate on tests green.**

### ✅ Cycle 3 (DONE — see §1): **Permissions & Identity deep dive**
Wrote `permissions/00-authorization-model.md` + [ADR-0008](architecture/adr/ADR-0008-canonical-principal-acl-model.md).
Canonical model, query-time enforcement, freshness, conformance suite. Mitigates R1/R3/R4
by design; decided open question #2; provisional answer to #7.

### ✅ Cycle 4 (DONE — see §1): **RAG pipeline deep dive**
Wrote `rag/00-retrieval-pipeline.md` + [ADR-0009](architecture/adr/ADR-0009-hybrid-retrieval-and-chunking.md).
Structure-aware chunking, universal embedding space, hybrid search consuming the permission
filter, reranking, grounding/citation, verifier contract. Decided open question #4; mitigated
R2 by design; provisional answer to #1.

### ✅ Cycle 5 (DONE — see §1): **Storage & tenancy deep dive**
Wrote `storage/00-storage-architecture.md` + [ADR-0010](architecture/adr/ADR-0010-storage-topology-and-tenancy.md).
Five-store data plane, pgvector-default vector layer behind a filter-only `VectorIndex` port,
tenant = customer org, isolation tiers, encryption/BYOK, ACL-denormalization coherence,
re-embed migrations, erasure. Resolved open questions 1 (final) and 5 (final); mitigated
R4/R5/R7 by design.

### ✅ Cycle 6 (DONE — see §1): **Ingestion workers & connectors**
Wrote `workers/00-ingestion-architecture.md` + `workers/01-connector-framework.md` +
[ADR-0011](architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).
Staged-DAG pipeline, idempotent version-keyed writes, priority classes + fairness (R8),
outbox coherence relay ([Storage §7](storage/00-storage-architecture.md)), re-embed
migrations, change-driven re-sync, DLQ, least-privilege posture, six-method connector
contract, conformance gate + canary. Mitigated R8/R6/R3-write by design; strengthened Q#7.

### ✅ Cycle 7 (DONE — see §1): **Governance, audit & cost**
Wrote `governance/00-governance-and-audit.md` + [ADR-0012](architecture/adr/ADR-0012-governance-audit-and-cost.md).
Policy plane (no hot-path component): ratified freshness SLA per tier (closed Q#7), label→action
matrix, retention/erasure/legal-hold; audit-as-evidence (retention/access/hash-chain); per-tenant
cost model + budgets that degrade capability-before-safety (mitigated R5 by design); eval-gated
model registry; per-domain compliance map. Handed Deployment the prices/envelopes/SLA-capacity
sizing, Metadata the classification schema, and API the budget/DSAR/audit-export surface.

### ✅ Cycle 8 (DONE — see §1): **Metadata — catalog, lineage & classification schema**
Wrote `metadata/00-catalog-and-lineage.md` + [ADR-0013](architecture/adr/ADR-0013-canonical-metadata-lineage-schema.md).
Four-level catalog (Doc→Item→Chunk→Version), bidirectional lineage graph, closed classification
vocabulary (makes the Governance matrix total), content-free erasure tombstone, metadata-as-audit-
evidence, schema versioning/validation. Held in the relational SoT — no new store, no hot-path
component. Closed the last un-seeded cross-cutting store concern; strengthened R1/R3 and made
Governance's erasure/retention/label promises provable. A cross-component schema decision *did*
emerge → ADR-0013.

### ✅ Cycle 9 (DONE — see §1): **API — external surface, contracts & versioning**
Wrote `api/00-api-surface.md` + [ADR-0014](architecture/adr/ADR-0014-api-contract-surface.md).
Five resource groups, token-bound identity + OBO (tenancy never in the URL), dual sync/streaming
query contract under one verifier gate, one typed-error envelope, async-job pattern, admin-can-only-
tighten policy CRUD, DSAR/erasure/audit-export, filter-parity catalog/lineage, URL-major additive
versioning. Discharged the client-facing surfaces Governance/Metadata/RAG/Permissions queued;
enforced permission-faithful retrieval once at the edge (a contract-shape decision was cross-component
→ ADR-0014).

### ✅ Cycle 10 (DONE — see §1): **Deployment — topology, environments, CI/CD, DR/BCP**
Wrote `deployment/00-deployment-topology.md` + [ADR-0015](architecture/adr/ADR-0015-deployment-dr-and-regional-topology.md).
Physical projection of the three planes; per-tier topology + graduation; safety-gated CI/CD
(conformance suite as release veto); reserved-P0 SLA-capacity sizing; cost-envelope/residency
routing; catalog partitioning + cold-lineage archival + integrity checks; gateway/streaming ops;
**ACL-first active-passive DR** with per-store backup/restore (a cross-component DR decision → ADR-0015).
Discharged the sizing/tuning inputs Cycles 5–9 queued; **closed §5 — all core surfaces Seeded.**

### ✅ Cycle 11 (DONE — see §1): **Domain Pack #1 — Finance + the pack-spec skeleton**
Wrote `packs/README.md` (the reusable six-part skeleton + §0 ledger + falsifiability rule),
`packs/finance/00-finance-pack.md` (the reference pack), and
[ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) (the pack contract).
Finance's §0 horizontal-change ledger records **zero** horizontal changes against the hardest
domain — the founding bet held. HR/Legal/Audit/KM/SAP/SharePoint/Email packs are now
fill-in-the-blank against the Finance template.

### ✅ Cycle 12 (DONE — see §1): **Domain Pack #2 — HR**
Wrote `packs/hr/00-hr-pack.md` against the [pack skeleton](packs/README.md). No new ADR (HR is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md), like Finance).
**§0 ledger = none, all additive — the skeleton generalized from n=1 to n=2 cleanly.** The hardest
case (employee-self-scoped ACLs) resolved to the *degenerate* set-membership predicate (owner CPI is
already an effective principal); computed manager-hierarchy rules reused the §9/§10 escape hatch.
Registered `pii_class:health`/`employment`/`restricted:works_council`; tightened the matrix with a
manager-visibility carve-out; exercised the reflexive self-DSAR and `legal_hold > erasure > retention`.

### ✅ Cycle 13 (DONE — see §1): **Domain Pack #3 — Legal (privilege, ethical walls & holds)**
Wrote `packs/legal/00-legal-pack.md` against the [skeleton](packs/README.md). No new ADR (Legal is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First genuine
novel-concept falsifiability test since Finance — the rule was armed and did NOT fire.** Privilege
*waiver* resolved additively by separating **what** (`restricted:privileged` label) from **who** (item
ACL): waiver = a *narrowing ACL grant edit* propagated by the existing re-sync, **never** a label
removal; "per recipient" is what an ACL already is, so the static label→action matrix needs no
recipient policy. Ethical walls = the existing deny-wins clause. Registered `restricted:privileged` +
`restricted:work_product`; reused `matter:<id>`. The platform *mirrors* privilege (computed/unresolvable
privilege → `approximate → deny + quarantine`), never *computes* waiver.

### ✅ Cycle 14 (DONE — see §1): **Domain Pack #4 — Audit (mostly inherited) + segregation-of-duties**
Wrote `packs/audit/00-audit-pack.md` against the [skeleton](packs/README.md). No new ADR (Audit is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First
*combinatorial*-concept falsifiability test — the rule was armed and did NOT fire, but for a sharper
reason than Legal's:** SoD *prevention* is a write/transaction control **out of the platform's plane**
(read-plane mirror — the platform never posts/approves/executes); SoD *read*-exclusion = the existing
deny-wins clause (a unary `deny`, pre-resolved by the source, identical to Legal's ethical wall); SoD
*detection* ("who both prepared and approved?") = an ordinary permission-gated retrieval whose
combinatorial join lives in the query + source data, never in the access predicate. Registered
`restricted:audit_workpaper`; inherited Finance's SOX row + SAP fidelity + Legal's `matter:<id>` hold +
the S7 append-only trail verbatim. Documented the **read-plane-mirror scope boundary** as the explicit
reason no transaction-control ADR was needed (and named the future *action-taking* pack that would).

### ✅ Cycle 15 (DONE — see §1): **Domain Pack #5 — Knowledge Management (the inverse stress)**
Wrote `packs/km/00-km-pack.md` against the [skeleton](packs/README.md). No new ADR (KM is a worked
instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First *inverse*
(over-refusal) falsifiability test — the rule was armed against a *loosening* and did NOT fire.**
Over-refusal resolved as a *tuning/eval* problem **upstream** of the filter and verifier (query
expansion, rerank/MMR, dedup, KM-eval-tuned model on the *already-permitted* set), **never** a
floor-loosening one — all three temptations (widen default label, relax grounding bar, unfiltered list
mode) rejected *and* shown unnecessary. **First pack with empty §2 + §3** (zero new vocabulary, zero
tighten, zero loosen) — the empty tables *are* the proof the low-restriction defaults are already
calibrated. Eval headline inverted to **recall / over-refusal** while retaining the permission-negative
class (recall chased without trading away safety).

### ✅ Cycle 16 (DONE — see §1): **Domain Pack #6 — SAP (the first source-shaped pack)**
Wrote `packs/sap/00-sap-pack.md` against the [skeleton](packs/README.md). No new ADR (SAP is a worked
instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md); the three-band model is a
consolidation of [ADR-0008 §5.2](architecture/adr/ADR-0008-canonical-principal-acl-model.md) + the §9
quarantine hatch, not a new decision). **First *source-shaped* falsifiability test — held.** The
module-by-module fidelity matrix (FI/CO, MM, SD, HCM, BW, GRC) sorts every SAP authorization construct
into **Band A** (`exact`), **Band B** (structural/dynamic: resolve-or-quarantine) or **Band C**
(field/row/cell: quarantine) — jointly exhaustive, so no construct is neither resolvable nor
quarantinable → no new confidence level/predicate. **2nd pack with empty §2 + §3** (a source carries no
policy of its own; §4 fully inherited). Resolved open Q#2's deferred per-module sub-question; consolidated
the 3× ad-hoc SAP fidelity into one canonical §1.

### ✅ Cycle 17 (DONE — see §1): **Domain Pack #7 — SharePoint (source-shaped, SAP's mirror)**
Wrote `packs/sharepoint/00-sharepoint-pack.md` against the [skeleton](packs/README.md). No new ADR
(SharePoint is a worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
**Second source-shaped pack and SAP's mirror — the *inverse* (over-grant) falsifiability test, held.**
Every sharing construct maps to `allow` / `deny` / **flagged-grant** (`sharing:anonymous` → fail-closed,
never silent public) / quarantine — no new principal category, no new predicate. **No Band-C** (ACL is
item-level). 3rd pack with empty §2 + §3 (source carries no policy; MIP labels *carried* not *owned*).
Consolidated the 5× ad-hoc SharePoint fidelity into one canonical §1; committed the untracked Cycle-16
SAP pack alongside.

### ✅ Cycle 18 (DONE — see §1): **Domain Pack #8 — Email / Exchange (the last source pack)**
Wrote `packs/email/00-email-pack.md` against the [skeleton](packs/README.md). No new ADR (Email is a
worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **Third & last
source-shaped pack, the simplest of all sources — the *transport-vs-storage* falsifiability test, held.**
A message's ACL is its **mailbox owner + delegates**, never its transport audience; every construct
(mailbox owner, delegate, shared mailbox, Send-As→no-read, per-message thread ACL, **DL membership→no
grant**, To/Cc/Bcc→content-not-ACL) maps to `allow`/`deny`/quarantine — no new principal category, no new
predicate. **4th pack with empty §2 + §3**; **shortest §1 matrix** (no Band-C, no sharing-link surface).
Consolidated the 3× ad-hoc Email fidelity (HR/Legal/Audit) into one canonical §1. **The source-pack surface
is now complete.**

### ✅ Cycle 19 (DONE — see §1): **Domain Pack #9 — Document Intelligence (the derived-content test)**
Wrote `packs/document-intelligence/00-document-intelligence-pack.md` against the [skeleton](packs/README.md).
No new ADR (DocIntel is a worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)).
**First *derived-content* falsifiability test — the rule was armed against a *manufactured authorization
fact* and did NOT fire.** A platform-derived artifact **never carries an ACL of its own** — it *inherits*
the source Item's via lineage (multi-source merge = **intersection/split/quarantine, never union**); a
*derived* label may only **tighten**, is **fail-closed** on low classifier confidence, and is
provenance-stamped (`label_source: derived`). A wrong derivation costs *availability, never safety* (a label
only subtracts capability; the ACL is the primary gate). **First non-empty §2 since Legal** (owns a
derived-classification vocabulary; the novel element is the provenance stamp, kept in the same dimension so
enforcement is identical). The one Metadata touch (`LineageNode.kind` for a secondary derived index) is the
additive node-kind growth [Metadata §9](metadata/00-catalog-and-lineage.md) already named — not a contract
change; unresolvable narrowing sub-Items ride the existing `approximate → deny + quarantine` hatch (3rd sighting).

### ✅ Cycle 20 (DONE — see §1): **Domain Pack #10 — Reporting (the aggregation test) — surface complete**
Wrote `packs/reporting/00-reporting-pack.md` against the [skeleton](packs/README.md). No new ADR (Reporting is
a worked instance of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)). **First *aggregation*
falsifiability test — the rule was armed against an *arithmetic-inference leak* (a total reconstructing a
masked row via small-cell/differencing) and did NOT fire.** Disarmed **by construction, not by a
disclosure-control engine**: query-time aggregates are **filter-then-aggregate** ([ADR-0004](architecture/adr/ADR-0004-permission-faithful-retrieval.md)),
so a served total is always a function of rows the caller could read individually (the *aggregate-then-filter*
leak path does not exist); a pre-materialized report is a **Band-A** source-ACL mirror; a cross-source rollup
carries the **intersection** (never union, DocIntel merge reused); an unresolvable-contributor aggregate is
quarantined (4th sighting of the hatch). **5th pack with empty §2 + §3** (a report presents the riding domain's
policy, owns none); §4 inherited from *every* contributing domain. **The domain-pack surface is now complete —
all 10 planned packs Seeded, every one with an all-additive §0 ledger.**

### ✅ Cycle 21 (DONE — see §1): **Runtime pack-load SPI (design)**
Wrote `packs/01-pack-load-spi.md` + [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md).
The **engineering form of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md)** (named in its own
"Revisit when"): a **validating, transactional, fail-closed loader** (RESOLVE→VALIDATE→DRY-RUN→COMMIT-atomic→
ACTIVATE-scoped) that installs the six pack sections into their horizontal extension points from a **signed
data-only bundle** (connector *referenced*, never shipped). VALIDATE = six validators, each checking a section
`⊆` its extension point → the tighten-only rule becomes **executable**; the loader is **safe by construction**
(its only verbs are subset-installs into fail-closed extension points). Machine-checked §0 ledger routes a
horizontal-change pack to a human ADR gate. **No code deploy** to load a pack; per-tenant `pack_version`
pinning; fail-closed unload. The SPI's own §0-equivalent ledger is *"none, all additive"* — no new hot-path
component. The SPI's falsifiability check (*no-code-deploy load? floor-loosening pack structurally rejected?*)
resolves **yes to both**. Cross-component → ADR-0017; first concrete `platform/`→`core/` reconciliation target.

### ✅ Cycle 22 (DONE — see §1): **Model hosting & serving posture — resolved open Q#3**
Wrote `models/00-model-hosting-and-serving.md` + [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md).
Dual-track serving fabric (Track A in-boundary OSS / Track B contractually-private managed) routed per
`(tenant tier × data class)` behind the Model Gateway; closed `hosting_posture` registry enum + mandatory
data-handling terms; fail-closed track-fallback. Net horizontal change = none, all additive. Closed a real
doc gap (model serving had no home folder); resolved open Q#3. Handed empirical sizing/pricing to Deployment
§7 and network-boundary hardening to Security.

### ✅ Cycle 23 (DONE — see §1): **Agent orchestration posture — resolved open Q#6 (the last open architecture question)**
Wrote `orchestration/00-agent-orchestration.md` + [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)
+ the `orchestration/` folder. **Extend `core/`'s planner/verifier loop into the distributed orchestrator**
(the five choke points stay ours and in-boundary — the *decision plane*); adopt commodity durable execution
behind an `ExecutionBackend` port (the *execution plane*, no decision method) for distributed plumbing only;
**never a framework that owns the loop**. Bounded pack-declared allowlisted agent graphs; the same five gates
re-hosted onto the queue-backed topology → net horizontal change = none, all additive. **All open architecture
questions Q#1–Q#7 are now closed.**

### ✅ Cycle 24 (DONE — see §1): **Engineering-track bridge — the `core/` reconciliation plan**
Wrote [engineering/00-core-reconciliation-plan.md](engineering/00-core-reconciliation-plan.md) + the
`engineering/` folder. Ground-truth `core/` audit (surfaced: `orchestrator.py` calls neither
`WorkerRegistry` nor `HandoffRouter` — inert gates), gap ledger G1–G8, two target designs, sequenced TDD
work-package list (A1→A2→A5→B1→B2→B3→A3→A4→B4→C1), test matrix, definition-of-done. No new ADR (discharges
ADR-0017 + ADR-0019). This is the build order the coding cycle below executes.

### ✅ Cycle 25 (DONE — see §1): **Executed the `core/` reconciliation — coding cycle (TDD)**
Wired the inert gates live (WP-A1 tool-scope → `tool_scope_blocked`; WP-A2 handoff → `handoff_refused`),
hardened governance order (WP-A5, deterministic hard-block before the autonomy shortcut), added the
[`ExecutionBackend`](../core/execution.py) port + `InProcessExecutionBackend` + purity test (WP-A3) and run
identity (G4), and built the **complete** [`core/packs/`](../core/packs/) loader (WP-B1–B4). **Marquee test
`test_floor_loosening_bundle_fails_validate` passes.** 62→131 tests green, `check.py` exit 0, coverage
80–100 % on built modules. No ADR. See the [implementation report](engineering/01-cycle-25-implementation-report.md).

### ✅ Cycle 26 (DONE — see §1): **Finished the orchestrator re-host + locked the coverage floor**
Executed the [reconciliation plan](engineering/00-core-reconciliation-plan.md)'s last two work packages —
the engineering-track [definition-of-done](engineering/00-core-reconciliation-plan.md#8-definition-of-done)
is now **fully met.** **WP-A4:** `run()` re-expressed against the [`ExecutionBackend`](../core/execution.py)
port (`start_run→schedule_step→await_steps` via the default in-process adapter), behaviour parity; `RunSpec`
consolidated. An adversarial code review caught a run-identity collision (task-derived `request_id` +
long-lived orchestrator → cache replay skipping side effects) — fixed to a **fresh unique id per invocation** +
per-run step-sequence keys, both regression-tested. **WP-C1:** legacy LLM-path modules backfilled with
mocked-model tests (whole-`core` 75 %→92.9 %); `pytest.ini` + `.github/workflows/ci.yml` enforce
`--cov=core --cov-fail-under=80`. **131→193 tests green, `check.py` exit 0, ruff clean.** No ADR. See the
[Cycle-26 implementation report](engineering/02-cycle-26-implementation-report.md).

### ▶ Cycle 27 (do next): **Tuning-input refinements — no open architecture or blocking engineering item**
The architecture surface is complete (Q#1–Q#7 closed) **and** the engineering track is complete. Remaining work
is pure refinement — pick the highest-leverage:
1. **Distributed `ExecutionBackend` adapter (design note) + substrate sizing.** The port + in-process adapter
   exist; a Temporal-class adapter is out-of-`core/` by design. Document its sizing per tenant tier as a
   reserved-capacity class → [Deployment §7](deployment/00-deployment-topology.md).
2. **Track-B network-boundary hardening + handoff-edge (intra-boundary trust edge) hardening** →
   [Security](security/00-security-architecture.md).
3. **Onboarding UX polish** (§6 Cycle 2c.4) — the last non-reconciliation code item.
4. *(optional)* A **new domain pack** (Procurement/Manufacturing/CRM) as a fill-in-the-blank exercise of the
   [pack skeleton](packs/README.md) + the now-built [loader](../core/packs/) — proves the "new domain = a pack,
   not a redesign" bet end-to-end (paper spec → runtime load). Not required; the bet is already proven on paper.
**Do NOT push a broken tree — gate on tests green.** None of these is an open question; each is a refinement.

### Later (backlog)
- **The pack backlog is empty** — all ten planned packs (Finance/HR/Legal/Audit/KM/DocIntel concept-shaped +
  SAP/SharePoint/Email source-shaped + Reporting aggregation) are Seeded. A **new** domain (Procurement,
  Manufacturing, CRM) is now a fill-in-the-blank pack against the [skeleton](packs/README.md), inheriting the
  Finance §0-ledger discipline — not a redesign. No further pack is *required* to prove the bet.
- ✅ **Runtime pack-load SPI — *designed* (Cycle 21, [ADR-0017](architecture/adr/ADR-0017-runtime-pack-load-spi.md)):**
  the engineering form of [ADR-0016](architecture/adr/ADR-0016-domain-pack-contract.md) — a validating,
  fail-closed loader ([packs/01-pack-load-spi.md](packs/01-pack-load-spi.md)). **Remaining: the `core/`
  *implementation* of it** (Cycle 22 candidate; the doc is its specification).
- **Cycle 2c engineering track** (still open) — wire `WorkerRegistry`/`HandoffRouter` into the
  runtime, finish the test port + coverage gate, deeper governance hardening (see §6 Cycle 2c).
- Reconcile `platform/` architecture with the existing `core/` code (ADR-0002 implementation path).
- ✅ **Resolved open Q#3** (model hosting — Cycle 22, [ADR-0018](architecture/adr/ADR-0018-model-hosting-and-serving-posture.md)):
  dual-track serving fabric routed per `(tenant tier × data class)` behind the Gateway. **Remaining: the
  empirical GPU-pool sizing / managed-endpoint pricing** ([Deployment §7](deployment/00-deployment-topology.md))
  and **Track-B network-boundary hardening** ([Security](security/00-security-architecture.md)) — tuning
  inputs, not redesigns.
- ✅ **Resolved open Q#6** (agent framework — Cycle 23, [ADR-0019](architecture/adr/ADR-0019-agent-orchestration-posture.md)):
  extend `core/`'s planner/verifier into the distributed orchestrator (choke points stay ours); adopt durable
  execution behind an `ExecutionBackend` port; bounded pack-declared agent graphs; never a framework that owns
  the loop. **This was the last open architecture question — Q#1–Q#7 are all closed.** Remaining: the `core/`
  *implementation* of the orchestrator loop (engineering track) + substrate sizing (Deployment) and
  handoff-edge hardening (Security) — tuning inputs, not redesigns.

---

## 7. Consistency checklist (run before ending each cycle)

- [ ] New docs answer Why / How / Trade-offs / Alternatives / Future scalability.
- [ ] New cross-component decisions captured as an ADR and linked.
- [ ] No duplicated content; extended existing docs where possible.
- [ ] `platform/README.md` domain-map statuses updated.
- [ ] This file's §1, §3, §4, §6 updated.
