---
schema: agent-status/v1
agent_id: programming-agent
company: AI_Studioxyz
profile: developer
status: production
last_updated: "2026-09-17"
---

# Programming Agent — aktueller Status

## Aktueller Auftrag

Der Agent ist die erste wiederverwendbare Programmierausarbeitung der Agenten-Vorlage.
Er wählt dynamisch zwischen Recherche, Implementierung, Debugging und Review und arbeitet
in einem separat übergebenen Git-Workspace.

## Letzter bestätigter Stand

- Rollen und Skills sind unter `roles/` und `.agents/skills/` registriert.
- Der Demo-Lauf demonstriert Nacharbeit nach einem fehlgeschlagenen Review.
- Der DeepSeek-Adapter unterstützt robuste JSON-/Python-Literal-Toolargumente, CP1252-Fallback,
  gezielte `edit_file`-Änderungen, bevorzugt bei `src`-Workspaces den lokalen Importpfad und
  verweigert blindes Überschreiben großer Dateien. Das produktive Tool-Budget beträgt 48 Aufrufe.
- Das Cockpit persistiert Aufträge lokal, listet die Run-Historie und kann blockierte Läufe mit
  Feedback und Interruption-Bestätigung fortsetzen.
- Letzte Vorlage-Verifikation: `python -m unittest discover -q` → 43 bestanden; Ruff,
  Kompilierung und `agentkit validate` → bestanden.
- Validierung:
  `python -m agentkit validate --agent agents\programming-agent`
- Demo:
  `python -m agentkit run --agent agents\programming-agent --backend demo --task "Zeige den dynamischen Programmier-Workflow"`

## Nächste Aktion

Bei einem echten Auftrag zuerst `STATUS.md` im Ziel-Workspace lesen und die Akzeptanzkriterien
bestätigen, dann den kleinsten implementierbaren Schritt mit gezieltem Edit ausführen, testen
und durch die separate read-only Reviewer-Rolle prüfen. Nach jeder Unterbrechung zuerst den Zustand prüfen; nie blind wiederholen.

## Offene Blocker

Kein konkretes Repository ist diesem Agenten dauerhaft zugeordnet. Ohne `--workspace` ist
`workspace/` nur ein Scratch-Bereich. Ein externer Pseudokrat-Test wurde als negativer
Harness-Test beendet; der Checkout wurde auf den Ausgangszustand zurückgesetzt.

## Grenzen

Keine Deployments, Veröffentlichungen, externen Nachrichten oder irreversiblen Änderungen
ohne ausdrückliche Freigabe. Status nach jedem Lauf aktualisieren.

## Einstieg

`STATUS.md` → `AGENTS.md` → `SOUL.md` → `WORKFLOW.md` → `agent.json` → relevante Rolle/Skills.

