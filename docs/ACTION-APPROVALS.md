# Konkrete Aktionsfreigaben

DeepSeek und Codex pausieren im Cockpit und in der öffentlichen CLI vor `write_file`, `edit_file` und `run_pytest`.
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
- Erfolgreiche Aktionen werden mit ihrem nachfolgenden Workspace-Fingerprint im Lauf
  gespeichert. Eine getrennte, dateisystemkanonische Replay-Identität vereinheitlicht
  unter Windows Groß-/Kleinschreibung und vorhandene 8.3-Aliase, ohne das sichtbare
  Freigabemanifest zu verändern. Dieselbe Aktion wird ohne beobachtete
  Workspace-Änderung auch in einer späteren Worker-Delegation nicht erneut angeboten.
- Nach Beginn einer Aktion bleibt bei unklarem Ausgang `in_flight` erhalten.
  Wiederaufnahme benötigt Prüfung, Feedback und Unterbrechungsbestätigung. Die alte
  Werkzeugfortsetzung wird verworfen; der Planer erhält die neue Evidenz.
- Gebündelte Werkzeugaufrufe behalten ihre Reihenfolge. Spätere Dateiaktionen benötigen
  eigene Freigaben; vorherige Werkzeuge werden beim Fortsetzen nicht wiederholt.
- Freigaben ersetzen keine Reviews: mögliche Schreibschritte entwerten frühere Reviews.

**Codex:** Die CLI bietet keine native per-tool interception. Für den expliziten
Freigabemodus läuft Codex read-only und liefert genau einen strukturierten Vorschlag.
Ein lokaler Allowlist-Host-Executor führt erst nach exakter Bestätigung `write_file`,
`edit_file` oder `run_pytest` aus. Manifest-Digest, Run, Agent, Company, Workspace,
Backend und Modell werden gebunden; abweichende Fortsetzungen werden verworfen. Das
ist eine Host-Gateway-Semantik, keine behauptete native Codex-CLI-Abfangbarkeit.
Interne VCS-/Runtime-/Cache-Pfade, Windows-Gerätenamen und Alternate Data Streams sind
gesperrt. Pytest läuft ohne Bytecode- und pytest-Cache-Mutation.

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

Die reale Codex-Abnahme steht in `docs/evidence/codex-luna-action-approvals.json`.
Mit gpt-5.6-luna und Codex CLI 0.159.2 wurden genau ein genehmigter `write_file`- und
ein `run_pytest`-Schritt, unabhängiges Review, exakter Artefakt-Hash und Git-Diff nur
für `app.py`, Digest-/Continuation-Bindung und laufweiter no-replay-Schutz belegt. Ein
zweiter echter Lauf lehnte `write_file` ab und blieb ohne Workspace-Mutation. Die
Gesamtdauer betrug 158,140 Sekunden bei einem Budget von 600 Sekunden. Das
Nachweisdokument ist sanitisiert.

Reale Browser-Abnahme am 30.09.2026: Eine wartende Codex-`write_file`-Freigabe blieb
über einen Server-Neustart mit identischer ID und identischem Manifest erhalten. Nach
getrennter `run_pytest`-Freigabe folgten `completed`, `reviewed: true` und `1 passed`.
Der sanitierte Computer-Use-Nachweis steht in
`docs/evidence/codex-cockpit-approval.json`.

Alte offene Freigaben vor dieser Host-Gateway-Erweiterung werden fail-closed behandelt
und müssen verworfen und neu geplant werden.
