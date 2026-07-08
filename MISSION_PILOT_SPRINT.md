# AI STUDIO — PILOT SPRINT MODE (v2)
## Supersedes: PROTOTYPE DEVELOPMENT MODE · Owner: Sven Steiner · 2026-07-08

## IMPORTANT — PROTECT THE REPOSITORY
The existing repository is the result of many hours of work. Treat it as valuable intellectual property.
Never start over. Never redesign. Never replace large parts of the code. Never perform large refactorings.
Always extend the existing solution. Always reuse existing components first.
`platform/` and `core/` are protected IP — do not modify.
All work happens additively in `prototype/` and the handover files.

---

# YOUR MISSION — THREE PHASES, ONE FINISH LINE

The mission is NOT "make the demo better forever."
The mission ends when:
1. A sales video has been recorded and approved by Sven, AND
2. The Pilot Kit has been tested end-to-end once with a fictional customer.

Business context (this is what the demo sells):
AI Studio installs a **private knowledge base on the customer's own infrastructure** (continuously fed from folders, mailboxes, systems — nothing leaves the house) and rents **AI agents on top, per month, like employees** (from €400/month per agent). Entry: Data Audit €149 → Foundation from €5,000 → Agents by subscription. Target customer: CFO / Head of Finance of an SME.

At the START of every execution, determine the current phase from the gate checklists below. Work ONLY on the current phase.

---

# PHASE A — DEMO FREEZE (max. 3 more cycles)

**FEATURE FREEZE IS IN EFFECT.** No new scenarios. No new modules. No new documents. New ideas go to FUTURE_BACKLOG.md — always.

Only work on this exit checklist:
- [ ] Guided demo ("Geführte Demo") plays all scenarios hands-free, start to finish, zero visual glitches, zero console errors
- [ ] Every scenario answer renders: Answer, Sources, Confidence, Chain/Timeline where applicable — correctly on 1920×1080 (video resolution)
- [ ] One-click **Demo Reset** returns the app to a clean start state (required for repeatable video takes)
- [ ] Timing: each scenario ≤ 25 seconds in guided mode; total guided demo ≤ 4 minutes
- [ ] The FINAL scenario is the money shot: the "add another agent" moment — showing how the customer books an additional agent (Reporting-Agent, Rechnungs-Agent) on top of the knowledge base. This scene sells the subscription.
- [ ] German language throughout the UI and scenarios (target audience: DACH CFOs)

**Gate A→B:** every box checked. Then write `PHASE_A_COMPLETE` in PROGRESS.md and move on. Do not add "one more nice thing."

---

# PHASE B — VIDEO PRODUCTION (target: 1–2 cycles)

Goal: Sven can record the video **himself in under 30 minutes** using the guided demo.

Deliverables:
- [ ] VIDEO_SCRIPT.md finalized: 90–120 seconds, German, CFO language (no RAG/embeddings/LLM jargon). Story arc: pain ("Ihr Wissen steckt in Ordnern und Postfächern") → demo moments → money shot ("Agenten dazubuchen wie Mitarbeiter") → call to action ("Daten-Audit, 149 €")
- [ ] VIDEO_SCENES.md: scene-by-scene shot list mapped to guided-demo timestamps, with exact on-screen moments and voiceover text per scene
- [ ] RECORDING_CHECKLIST.md: resolution, browser zoom, demo reset, which scenario order, retake instructions — so a non-technical person cannot fail
- [ ] Optional but valuable: subtitle file (SRT) generated from the script

**Gate B→C:** Sven records and approves the video. Until his approval arrives, fix only what he flags — nothing else.

---

# PHASE C — PILOT KIT (the real goal: a paying pilot customer)

Goal: After a 30-minute audit call with a real SME, we can show them **their own demo within 48 hours** — populated with their company name, their document types, their pain scenarios — using **100% synthetic data**.

This is the sales weapon: *"Pilot ohne Risiko — wir brauchen kein einziges echtes Dokument von Ihnen."*

Deliverables:
- [ ] PILOT_CONFIG: one config file (company name, logo, industry, 3 pain scenarios chosen from a scenario library) rebrands the entire prototype — no code changes needed
- [ ] SYNTHETIC DATA PIPELINE: reuse the existing tool at `C:\Users\botrunner\projects\synthetic-data-creator` (tested 43/43) to generate customer-shaped Excel/CSV demo data with intact formulas. Document the workflow: customer file structure in → synthetic twin out → loaded into prototype
- [ ] SCENARIO LIBRARY: the existing 9+ scenarios tagged by industry/pain (Monatsabschluss, Liquidität, Rechnungsprüfung, Verträge, Wissensverlust), so 3 fitting ones can be picked per pilot in minutes
- [ ] PILOT_ONE_PAGER.md: the offer document — pilot scope, what the customer sees after 48h, price path (Audit €149 → Foundation ab €5.000 → Agent-Abo ab €400/Monat)
- [ ] END-TO-END REHEARSAL: run the full pilot process once for a fictional customer ("Muster Bau GmbH") and log every friction point; fix only blocking friction

**Mission complete:** rehearsal done, PILOT_KIT.md documents the repeatable 48h process. Write `MISSION_COMPLETE` in PROGRESS.md and stop.

---

# THINK LIKE A CUSTOMER
The customer knows nothing about AI and does not care about RAG, embeddings, vector databases, agents, LLMs.
The customer wants: "My company already owns all the information I need — this finally makes it usable, and I can book digital employees on top."
Every feature must answer: "How does this make my work easier?"

# SYNTHETIC DATA — HARD RULE
All data in demo and pilots is synthetic. Never real customer data, never real names of real companies.
Prefer generating Excel assets via the synthetic-data-creator so formulas keep working — a CFO WILL click into the numbers.

# DEVELOPMENT LOOP (every execution)
1. Read NEXT_STEPS.md, PROGRESS.md and the current phase checklist above
2. Determine the phase from the gates — do not work outside it
3. Select exactly ONE item from the current phase checklist (highest impact first)
4. Implement it
5. Review your own work critically — run the guided demo after every change
6. Update: NEXT_STEPS.md, PROGRESS.md, CHANGELOG.md, OPEN_ITEMS.md (+ phase-specific files)
7. RULE: OPEN_ITEMS.md must be shorter or equal after every cycle — never longer. New ideas → FUTURE_BACKLOG.md

# CEO REVIEW (end of every execution)
Ask, in this order:
1. Could Sven record the video TODAY? If yes and Phase A boxes are done → move to Phase B, say so explicitly in NEXT_STEPS.md
2. Could a pilot customer see their own demo within 48h? If yes → Phase C progress is real
3. Would a CFO understand within 90 seconds what he pays €5,000 + €400/month for?
If any answer is no, the single most important fix goes to the top of NEXT_STEPS.md.

# DO NOT WORK ON
Large architecture redesign, enterprise security, production scaling, performance optimisation, connector framework, agent framework, skill library, platform architecture, new prototype features outside the current phase checklist.
Ideas in those areas → FUTURE_BACKLOG.md, then continue with the phase checklist.

Stay focused. Protect the repository. Get to the pilot.
