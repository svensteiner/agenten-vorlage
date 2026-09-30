---
schema: agent-status/v1
agent_id: "{{AGENT_ID}}"
company: "{{COMPANY}}"
profile: "{{PROFILE}}"
status: ready
last_updated: "YYYY-MM-DD"
---

# Agent-Status

Diese Datei ist der erste Einstiegspunkt für jede neue LLM-Session. Sie beschreibt den
letzten belastbaren Stand, den nächsten begrenzten Schritt und offene Blocker. Nach jedem
relevanten Lauf muss sie aktualisiert werden; Vermutungen gehören in `Offene Blocker`.

## Aktueller Auftrag

- Ziel: `<ein messbares Ziel>`
- Verantwortlicher: `<Mensch oder System>`
- Arbeitsbereich: `workspace/` oder der explizit übergebene Workspace
- Status: `ready | active | blocked | paused | completed`

## Letzter bestätigter Stand

- Datum: `<YYYY-MM-DD>`
- Erledigt: `<konkretes Ergebnis>`
- Nachweis: `<Test, Datei, Report oder Kommando>`

## Nächste Aktion

1. `<kleinster sinnvoller nächster Schritt>`
2. `<Akzeptanzkriterium>`

## Offene Blocker

- Keine bekannten Blocker. `<Oder konkrete fehlende Eingabe mit Besitzer>`

## Grenzen und Freigaben

- Keine Veröffentlichung, kein Deployment, keine externe Nachricht und keine irreversible
  Änderung ohne ausdrückliche Freigabe.
- Rollen, Skills und Review-Regeln aus `agent.json` sind verbindlich.
- Lies für den Einstieg danach `AGENTS.md`, `SOUL.md`, `WORKFLOW.md` und nur die relevanten
  Rollen-/Skill-Dateien.

## Übergabe an die nächste LLM

Nicht erledigte Punkte fortsetzen, vorhandene Artefakte zuerst prüfen und nach jeder
Änderung den Nachweis aktualisieren. Keine Fertigmeldung ohne frische Verifikation.
