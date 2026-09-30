---
schema: agent-status/v1
component: agentkit-cockpit
status: prototype
last_updated: "2026-09-17"
---

# AgentKit Cockpit — Status

## Aktueller Stand

- Lokale Browser-Oberfläche unter `cockpit/index.html`.
- Python-Server unter `cockpit/server.py`.
- Agentenliste aus `agents/` und `generated/`.
- Demo-, Codex- und DeepSeek-Backend auswählbar.
- Asynchrone Jobs mit Statusabfrage und Ergebnisansicht.

## Letzter Nachweis

Der Server ist standardmäßig an `127.0.0.1:8765` gebunden. Die Engine- und
Backend-Tests der Vorlage bleiben der fachliche Prüfstand; der UI-Smoke-Test
startet einen Demo-Auftrag über HTTP.

## Nächste Aktion

UI mit Paperclip-Aufgaben und AgentKit-Run-Checkpoints verbinden. Danach
Genehmigungen, Live-Events und Worktree-Auswahl ergänzen.

## Offene Grenzen

Noch keine Authentifizierung, kein WebSocket-Streaming und keine mobile Ansicht.
Für den lokalen Einzelplatz-Prototypen ist das absichtlich begrenzt.
