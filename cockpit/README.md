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

Lokale Operatoren können optional eine Hostdatei mit vorab gebundenen Ausführungsprofilen
angeben. Der Browser sieht nur passende Profil-IDs und sichere Zusammenfassungen; die
konkreten Schreib- und Testregeln bleiben im Serverprozess:

```powershell
python cockpit\server.py --execution-profiles C:\host\cockpit-profiles.json
# oder
.\Start-AI-Studio.ps1 -ExecutionProfiles C:\host\cockpit-profiles.json
```

Die Datei ist versioniertes JSON mit `{"version":1,"profiles":[...]}`. Jeder Eintrag
enthält genau `id`, `label`, `agent`, `workspace`, `backend`, `write_paths`,
`test_manifest` und `host_autonomous`. Agent, Workspace und Backend müssen registriert
sein; Testmanifeste liegen außerhalb des gebundenen Workspace. Ein autonomes Profil
benötigt sowohl eine genaue Schreibdateiliste als auch eine feste isolierte Testsuite.
Manuelle Profile können eine oder beide Policies binden. Ohne Profil bleiben die bisherigen Freigaben aktiv. Profile sind im
öffentlichen Mehrbenutzermodus nicht verfügbar.

Für einen echten DeepSeek-Lauf muss `DEEPSEEK_API_KEY` bereits in der lokalen
Umgebung gesetzt sein. Der Browser erhält den Schlüssel nie.

## Sicherheitsgrenzen des Prototyps

- Der Server bindet standardmäßig nur an `127.0.0.1`.
- Agenten dürfen nur aus `agents/` und `generated/` geladen werden.
- Aufträge laufen asynchron und liefern eine Job-ID zum Polling.
- Job-Metadaten und Ergebnisse werden atomar unter `cockpit/.runs/` gespeichert; nach einem
  Server-Neustart können blockierte Läufe mit Feedback und Interruption-Bestätigung fortgesetzt werden.
- Der Workspace muss ein bereits vorhandener Ordner sein.
- Dateianhaenge verwenden begrenzte Upload-Endpunkte; eine freie Shell- oder
  Deployment-Oberflaeche gibt es im Cockpit nicht.
- Hostprofile sind unveränderlich geladen und an Agent, Workspace, Backend und Policy-Hashes
  gebunden. Fortsetzen mit geändertem Profil wird vor Worker-Reservierung abgewiesen.
- Autonome Profile überspringen nur einzelne Freigaben für ihre Host-Allowlist. Sie binden
  immer eine feste Testsuite; Abschluss erfordert deren aktuellen erfolgreichen Hostbeleg
  sowie ein frisches Review. Auch manuelle Profile mit Testsuite behalten diese Gates.

## Betriebsgrenze

Der Server ist für lokale Operatoren gedacht und bindet standardmäßig ausschließlich an
`127.0.0.1`. Für Mehrbenutzerbetrieb, Authentifizierung und externe Orchestrierung braucht
es einen vorgeschalteten Dienst; Paperclip kann später Aufgabenbesitz liefern, während
AgentKit die review-gesteuerte Ausführung bleibt.
