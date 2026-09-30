# AgentKit Cockpit

Lokale Chat-Oberfläche zum Starten und Überwachen von AgentKit-Aufträgen.
Die Oberfläche enthält keine zweite Agentenlogik: Die Ausführung und alle Review-Gates
bleiben in `agentkit.Engine`.

## Start

Aus dem Vorlagenordner:

```powershell
python cockpit\server.py
```

Danach `http://127.0.0.1:8765` öffnen.

Für einen echten DeepSeek-Lauf muss `DEEPSEEK_API_KEY` bereits in der lokalen
Umgebung gesetzt sein. Der Browser erhält den Schlüssel nie.

## Sicherheitsgrenzen des Prototyps

- Der Server bindet standardmäßig nur an `127.0.0.1`.
- Agenten dürfen nur aus `agents/` und `generated/` geladen werden.
- Aufträge laufen asynchron und liefern eine Job-ID zum Polling.
- Job-Metadaten und Ergebnisse werden atomar unter `cockpit/.runs/` gespeichert; nach einem
  Server-Neustart können blockierte Läufe mit Feedback und Interruption-Bestätigung fortgesetzt werden.
- Der Workspace muss ein bereits vorhandener Ordner sein.
- Es gibt keine Datei-Upload-, Shell- oder Deployment-Oberfläche im Cockpit.

## Betriebsgrenze

Der Server ist für lokale Operatoren gedacht und bindet standardmäßig ausschließlich an
`127.0.0.1`. Für Mehrbenutzerbetrieb, Authentifizierung und externe Orchestrierung braucht
es einen vorgeschalteten Dienst; Paperclip kann später Aufgabenbesitz liefern, während
AgentKit die review-gesteuerte Ausführung bleibt.
