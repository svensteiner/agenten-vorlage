# Konkrete Aktionsfreigaben

DeepSeek pausiert im Cockpit vor `write_file`, `edit_file` und `run_pytest`.
Die Auftragsansicht zeigt Werkzeug und vollständige Argumente. **Aktion freigeben**
führt genau diese gespeicherte Aktion aus; **Aktion ablehnen** beendet den Schritt
blockiert. Ein Dialog verweist auf diese Auftragsansicht und nimmt bis zur Klärung
keine weitere Nachricht an. Die Offline-Demo demonstriert zwei getrennte Dateifreigaben.

## Garantien und Grenzen

- Vorschlag und Modellfortsetzung werden vor der Aktion dauerhaft gespeichert.
- Freigaben sind an Run, Agent, Company, Workspace, Backend und Modell gebunden.
- Eine Dateiprüfsumme bindet die Freigabe an den beobachteten Workspace. Änderungen
  verhindern die Ausführung; ein veralteter Vorschlag kann weiterhin abgelehnt werden.
- Die unterstützte Prüfsumme umfasst höchstens 512 Einträge und 8 MiB Dateiinhalte.
  Größere, verlinkte oder nicht lesbare Workspaces werden ausdrücklich abgewiesen.
  `.git`, `.runs` und interne Sperrdateien werden ausgenommen. Dies ersetzt keine
  OS-Isolation und verhindert keine gleichzeitigen Änderungen durch fremde Prozesse.
- Ein wiederholter HTTP-Klick führt eine verbrauchte Freigabe nicht erneut aus.
  Nach einem Absturz vor Dispatch kann derselbe unverbrauchte Vorschlag erneut
  ausdrücklich bestätigt werden. Es gibt keinen automatischen Neustart.
- Nach Beginn einer Aktion bleibt bei unklarem Ausgang `in_flight` erhalten.
  Wiederaufnahme benötigt Prüfung, Feedback und Unterbrechungsbestätigung. Die alte
  Werkzeugfortsetzung wird verworfen; der Planer erhält die neue Evidenz.
- Gebündelte Werkzeugaufrufe behalten ihre Reihenfolge. Spätere Dateiaktionen benötigen
  eigene Freigaben; vorherige Werkzeuge werden beim Fortsetzen nicht wiederholt.
- Freigaben ersetzen keine Reviews: mögliche Schreibschritte entwerten frühere Reviews.

**Codex:** Der aktuelle CLI-Adapter kann einzelne Werkzeuge nicht abfangen. Er bietet
diese Freigaben deshalb nicht an; `--require-approvals` wird mit diesem Backend
abgewiesen. Die bestehende CLI-Sandbox und Rollenrechte gelten weiterhin.

**DeepSeek:** Die Freigabe eines Tests genehmigt die angezeigte Testausführung,
nicht jedes Betriebssystemereignis innerhalb des Tests. Testprogramme bleiben
vertrauenswürdiger lokaler Code. Netzwerk-, Connector- und Browseraktionen sind
damit noch nicht implementiert oder freigegeben.

## CLI

```powershell
python -m agentkit run --agent generated\mein-cto --backend demo `
  --require-approvals --task "Freigaben demonstrieren"
python -m agentkit resume --agent generated\mein-cto --backend demo `
  --run-dir generated\mein-cto\.runs\RUN_ID `
  --approval-id APPROVAL_ID --approval-decision approve
```

Die IDs stammen aus der Ausgabe des pausierten Laufs. Für Ablehnung `reject`
verwenden. Die gespeicherte Freigabepflicht bleibt nach Neustart bestehen, auch wenn
`--require-approvals` beim Fortsetzen nicht erneut angegeben wird.

## Nachweise

`tests/test_action_approvals.py` prüft Engine und DeepSeek-Adapter mit simulierten
Modellantworten, darunter tatsächliche lokale Dateiänderungen, Werkzeugbatches,
Budgetgrenzen und unbekannte Ausgänge. `tests/test_cockpit_approvals.py` prüft HTTP,
Herkunftsschutz, doppelte Entscheidungen, Neustart, veraltete Vorschläge und Dialogbindung.
`scripts/verify_release.py` prüft zusätzlich beide Demo-Freigaben bis zum Abschluss.
Das sind Offline-/Vertragsnachweise; eine reale DeepSeek-Modellabnahme steht noch aus.

Browser-Abnahme am 30.09.2026: Job `3c0486eaf51d4292b87931de49285d38` zeigte beide
vollständigen Schreibvorschläge. Zwischen den Freigaben wurde der Server neu gestartet;
die zweite Freigabe-ID blieb erhalten. Danach: `completed`, zwei auditierte Freigaben,
`reviewed: true` und tatsächliche Datei mit `ACCEPTED`. Kein Modell wurde dafür aufgerufen.
