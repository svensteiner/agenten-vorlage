# Live-Qualifizierung am 30.09.2026

Der korrigierte Codex-Adapter ist für einen realen isolierten Schreibworkflow mit
Test, unabhängigem Review, sicherem Ergebnisexport und gehärteter Wiederaufnahme
qualifiziert. Drei getrennte reale Aufgaben decken Repository-Audit,
Test-/Feedback-Recovery sowie GitHub-Connector-Analyse mit Review-Repair-Recovery ab.
Die technischen Schreib-/Dialog-Szenarien verwendeten synthetische Dateien; die drei
repräsentativen Läufe nutzten echten Projekt-, Test- beziehungsweise Connector-Kontext.
Keine echten Provider-Schlüssel wurden in Nachweisen gespeichert.

## Sichere Diagnose bei blockiertem Provider-Lauf

Wenn ein Live-Lauf mit `status=blocked` endet, schreibt `scripts/live_smoke.py`
nur eine begrenzte Diagnoseklasse in den sanitisierten Nachweis:
`provider_authentication` (HTTP 401/403 oder Authentifizierungsfehler),
`provider_http` (andere HTTP-Fehler), `provider_network` (Netzwerk-/Timeout-
Fehler), `contract` (ungültige strukturierte Providerantwort) oder
`workflow_blocked` (fachliche Blockade ohne Providerursache). Der Summary-Text
wird nur im Speicher geprüft, vorher begrenzt und um erkennbare Schlüssel sowie
Bearer-Werte bereinigt. Rohe Providerantworten und Zugangsdaten werden nicht
gespeichert.

## Nachweise

| Prüfung | Ergebnis | Lokaler Nachweis |
|---|---|---|
| Vollständiger Schreibworkflow, gpt-5.6-luna/low, elevated | Bestanden: drei Schritte, Developer und unabhängiger Reviewer, lokale Python-Byteprüfung, Quelle unverändert, Marker `STUDIO-FACT-4729`, bytegleiches Artefakt, 101,61 s | `.runs/qualification/codex-luna-artifact-export-qualified.json` |
| Zweistufiger realer Dialog, gpt-5.6-luna | Bestanden: zwei abgeschlossene Turns im isolierten Workspace; `ORBIT-731` im ersten Turn aus Datei gelesen und im zweiten nur aus Dialogkontext wiedergegeben; keine Dateiänderung | `.runs/qualification/codex-luna-conversation-context.json` |
| Repräsentativer realer Repository-Audit, gpt-5.6-luna | Bestanden: echter Repo-Kontext read-only; Researcher→Reviewer; drei Schritte/93,0 s; reviewed=true, dirty=false; drei Risiken plus konkrete Prüfaktionen | `.runs/qualification/codex-luna-repository-audit.json` |
| Reale Test-/Feedback-Recovery, gpt-5.6-luna | Bestanden: exakter 19-Test-Befehl, Exit 0/OK; drei kumulative Fehler, ein Feedback, acht Schritte/541,391 s; Reviewer read-only ohne erneute Testausführung | `.runs/qualification/codex-luna-test-recovery.json` |
| Reale GitHub-Connector-/Open-Dots-Analyse, gpt-5.6-luna/low | Bestanden: öffentlicher Blob plus unveränderlicher Anhang; neun Schritte/352,141 s; drei Review-Fehler, begrenztes Feedback-Recovery, finaler Reviewer success; fünf Fähigkeiten, drei priorisierte Lücken | `.runs/qualification/codex-luna-github-connector-analysis.json` |
| Gehärtete Unterbrechung/Wiederaufnahme, gpt-5.6-luna | Bestanden: Kindprozess beendet; Planner-Checkpoint; Resume ohne Ack verweigert, nach Ack abgeschlossen; Marker in Summary/Workerreport; Workspace unverändert; drei Schritte/31,515 s | `.runs/qualification/codex-luna-live-resume-hardened.json` |
| Sicherer Codex-Artefaktexport | Offizieller App-Server, read-only, Netzwerk deaktiviert; gemeldeter Workspace-Pfad, 2-MB-Grenze, Länge und SHA-256 geprüft | `agentkit/codex_artifacts.py`, `tests/test_codex_artifact_export.py` |
| Codex-Aktionsfreigaben, gpt-5.6-luna, CLI 0.159.2 | Bestanden: genau ein genehmigter `write_file` und `run_pytest`, `awaiting_approval` vor Mutation, unabhängiges Review, exakter Hash und Git-Diff nur für `app.py`, Digest-/Continuation-Bindung und laufweiter no-replay-Schutz; separater Reject-Lauf ohne Mutation; 158,140 s von 600 s Budget | `docs/evidence/codex-luna-action-approvals.json` |

### Historische Nachweise und Fehlversuche

Die folgenden Einträge dokumentieren die Entwicklung vor der bestandenen
Live-Qualifizierung; sie beschreiben nicht den aktuellen Freigabestand.

| Prüfung | Historisches Ergebnis | Lokaler Nachweis |
|---|---|---|
| Windows-Sandbox ohne Modell, read-only | Testmarker gelesen; auch mit gefilterter Adapterumgebung | `.runs/qualification/sandbox_probe.py` |
| Einzelner strukturierter Modellaufruf mit isolierter Konfiguration | Tatsächlicher Dateizugriff, exakter Marker, 11,74 s | `.runs/qualification/isolated-read-evidence.json` |
| Vollständiger Research-Workflow, gpt-5.5 | Abgeschlossen, zwei Planerentscheidungen, Quelle unverändert, Marker im Abschluss; 42,672 s | `.runs/qualification/codex-isolated-read.json` |
| Schreibworkflow im Repository | Worker-Timeout nach 45 s; kein Ergebnisartefakt | `.runs/qualification/codex-isolated-write.json` |
| Native Sandbox mit Workspace-Schreibprofil, ohne Modell | Synthetische RESULT.txt geschrieben und gelesen | Terminalnachweis dieser Abnahme |
| Schreibworkflow außerhalb des Repositories, 90 s je Aufruf/300 s gesamt | Nach 87,36 s blockiert: Worker melden Copy-Item und Python-Prüfung als durch Policy abgewiesen; kein Ergebnisartefakt | `.runs/qualification/codex-isolated-write-clean-workspace.json` |

Der Offline-Befehl `codex debug prompt-input` bestätigte, dass ein Testworkspace
innerhalb dieses Repositories dessen AGENTS.md einschließlich vollständiger
Unittest-Anforderung erbt. Das erklärt zusätzlichen Kontext, beweist aber nicht die
Ursache der Policy-Ablehnung. `scripts/live_smoke.py` verwendet deshalb jetzt einen
eigenen temporären Ordner außerhalb dieses Repositories. Aufruf- und Gesamtlaufzeit
sind explizit und begrenzt konfigurierbar. Kein stiller Neustart eines fehlgeschlagenen Laufs.

## Adapteränderung

Der aktuelle Adapter nutzt `--ignore-user-config`; lokale Authentifizierung wird weiter
genutzt. Die notwendige Windows-Sandbox-Auswahl wird seit der unten dokumentierten
Korrektur als einzelner validierter Wert übernommen; sonstige globale CLI-Einstellungen
werden nicht geladen. Der Adapter setzt das Modell
(Standard `gpt-5.6-luna`), niedriges Reasoning, Rollen-Sandbox, `approval_policy=never` und
das Netzwerkverbot für Workspace-Schreibaufrufe explizit. Der frühere automatische
Fast-Tier-Override entfällt. Die originale Konfiguration wurde nicht geändert.

Die [offizielle Windows-Dokumentation](https://developers.openai.com/codex/windows)
beschreibt die unterschiedlichen Sandbox-Implementierungen. Die
[Permissions-Dokumentation](https://developers.openai.com/codex/permissions) beschreibt
die nativen Profile für lokale Befehle. Die erfolgreichen lokalen Sandbox-Proben
sind kein Beweis, dass ein vollständiger Modell-Worker dieselben effektiven Rechte
erhält. Es wurde kein Schutz abgeschaltet, keine Execpolicy ignoriert und keine ACL
zur Umgehung der Ablehnung verändert.

## Historischer Zwischenstand vor der Reparatur

Zu diesem damaligen Stand mussten die effektiven CLI-Worker-Rechte geklärt und
Schreiben, Test sowie unabhängiges Review real qualifiziert werden. Diese Punkte sind
inzwischen einschließlich gehärteter Abbruch-/Wiederaufnahme erfüllt. Der folgende
Abschnitt hält die Diagnosehistorie fest.

Eine weitere Offline-Diagnose mit `codex debug prompt-input` am 30.09.2026 nutzte
einen neuen temporären Ordner außerhalb des Repositories und die gefilterte
Adapterumgebung. Explizite Konfigurationswerte `workspace-write`, `never` und
`network_access=false` erschienen korrekt im gerenderten Berechtigungsabschnitt;
der synthetische Workspace war als beschreibbares Verzeichnis aufgeführt.
Die Engine setzt die Rollen-Sandbox vor dem Worker-Aufruf ebenfalls ausdrücklich.
Nachweis: `.runs/qualification/permission-diagnostic-summary.json`.

Dieser Debug-Befehl besitzt keinen dokumentierten `--ignore-user-config`-Schalter.
Er ist daher kein Nachweis der effektiven Rechte des isolierten Exec-Aufrufs und
erklärt die frühere Policy-Ablehnung noch nicht. Der nur für das Rendern erforderliche
Tier-Kompatibilitätswert erzeugte keinen Modellaufruf und wurde nicht in den Adapter
übernommen. Die damals nächste Diagnose musste die Exec-spezifische
Konfigurationsauflösung oder deren Tool-Ablehnungsgrund zeigen; ein weiterer
Schreib-Smoke ohne diese Evidenz wäre nicht aussagekräftig gewesen.

Offline-Nachweise nach Adapteränderung: 137 Unittests, Ruff und 17 Release-Prüfungen
bestanden. Die automatischen Tests prüfen unter anderem, dass Rollen-Sandbox,
strukturierter Ausgabe-Vertrag und Authentifizierungsfilter erhalten bleiben und
globale Einstellungen unverändert sind.

## Historische Ursache der Windows-Schreibblockade

Die Quellcodeprüfung des installierten Tags `rust-v0.130.0` bestätigt eine
Konfigurationslücke: Ohne aktivierte Windows-Sandbox setzt Codex ein angefordertes
`workspace-write` auf `read-only` zurück. Das geschieht ausdrücklich auch bei einer
gesetzten Rollen-Sandbox: [Konfigurationsauflösung, Zeilen 746–757](https://github.com/openai/codex/blob/rust-v0.130.0/codex-rs/config/src/config_toml.rs#L746).
Die beiden historischen Windows-Featureflags sind standardmäßig aus;
[`windows.sandbox` wählt die Implementierung](https://github.com/openai/codex/blob/rust-v0.130.0/codex-rs/core/src/config/mod.rs#L2278).

Die [Befehlspolicy](https://github.com/openai/codex/blob/rust-v0.130.0/codex-rs/core/src/exec_policy.rs#L645)
erlaubt bekannte sichere Lesebefehle vorab. Andere Befehle werden im verwalteten
Windows-Read-only-Profil bei `approval_policy=never` abgewiesen. Das erklärt das
beobachtete Muster aus erfolgreichen Lesebefehlen und abgewiesenem Schreiben/Python.
Die neueren GitHub-Issues waren nur Suchhinweise; diese Diagnose stützt sich auf den
Tag der tatsächlich installierten Version.

Der Adapter übernimmt deshalb die bereits eingerichtete Windows-Sandbox-Auswahl als
einzelnen validierten Wert, während übrige globale Einstellungen isoliert bleiben.
Es gibt keine automatische Auswahl einer schwächeren Implementierung, keinen
Unsandboxed-Fallback und keine Änderung an Benutzerkonfiguration oder Regeln.
Fehlt die Auswahl, erscheint vor dem Modellaufruf ein Einrichtungsfehler.
Ein erfolgreicher Live-Schreib-/Review-Lauf war damit noch nicht nachgewiesen.

## Historische Live-Prüfung nach der ersten Korrektur

Die lokale Konfiguration wählt `unelevated`; genau dieser Wert wird weitergegeben.
Der erste begrenzte Lauf mit dem im lokalen Katalog aufgeführten `gpt-5.6-luna`
brach nach 5,39 Sekunden mit CLI-Exitcode 1 vor jeder Dateiaktion ab. Eine kurze
synthetische Startdiagnose zeigte einen Modellkatalog-Decoderfehler: CLI 0.130.0
kennt dessen Reasoning-Wert `max` nicht. Das beweist eine Inkompatibilität, aber
nicht, dass dies der einzige Startfehler war. Luna war für diese alte CLI-Version
zu diesem Zeitpunkt nicht live qualifiziert. Nachweise: `codex-luna-write-sandbox.json` und
`codex-luna-startup-diagnostic.json` unter `.runs/qualification/`.

Der Vergleichslauf mit dem zuvor funktionierenden `gpt-5.5/low` nutzte dieselbe
korrigierte Sandbox-Auswahl, 60 Sekunden pro Aufruf und höchstens 240 Sekunden.
Er endete nach 77,953 Sekunden blockiert: Der Developer konnte Dateimetadaten
auflisten, aber weder PowerShell noch Python konnten die synthetischen Dateien
lesen (`Access denied`/`PermissionError`). Die Befehle wurden diesmal ausgeführt;
die frühere vorgelagerte Policy-Ablehnung ist durch eine tatsächliche Windows-
Zugriffsverweigerung ersetzt. Quelle unverändert, kein Ergebnisartefakt und kein
bestandener Test oder Review. Nachweis: `.runs/qualification/codex-gpt55-write-sandbox.json`.

Keine ACL, globale Konfiguration, Execpolicy oder Sandbox-Implementierung wurde zur
Umgehung dieser Grenze verändert. Ein erneuter Live-Versuch erforderte zunächst eine
belegte Behebung der Host-Sandbox-Einrichtung. Die historischen Lese-Nachweise
qualifizieren diese neue Adapterkonfiguration nicht.

Nach der Korrektur bestanden 161 Unittests, Ruff und alle 17 Offline-Release-Checks.
Die neuen Verträge prüfen beide erlaubten Windows-Auswahlen, unveränderte Rollenrechte,
Netzwerk-/Approval-Grenzen, fehlende/ungültige Konfiguration vor Modellaufrufen und
Linux/macOS ohne Windows-Konfigurationspflicht. Es handelt sich dabei um simulierte
Plattformverträge, nicht um ausgeführte Linux-/macOS-Installationsprüfungen.

## Reparatur auf ausdrücklichen Nutzerauftrag

Die globale npm-Installation wurde von Codex CLI 0.130.0 auf die offizielle
Version 0.159.2 aktualisiert. Der Modellkatalog wird wieder korrekt gelesen.
Ein tatsächlicher strukturierter Aufruf mit gpt-5.6-luna/low bestand anschließend
in rund sechs Sekunden (`codex-updated-luna-connectivity.json`). Dies beweist
den Modellzugang, noch keine Datei-/Test-/Review-Ausführung.

Ein modellfreier `codex sandbox -P :workspace`-Test reproduzierte unter der
bisherigen unelevated-Einrichtung die Dateilesesperre. Die offiziell bevorzugte
elevated-Einrichtung wurde mit demselben begrenzten Workspace angestoßen; Windows
zeigte den geschützten Administrator-Dialog. Die Diagnose erreichte ihr Zeitlimit,
während die Administratorbestätigung ausstand. Keine ACL wurde manuell geändert,
keine Sandbox abgeschaltet und die globale Sandbox-Auswahl blieb unverändert.
Die Einrichtung ist erst nach Bestätigung und erfolgreichem erneutem Test belegt.

### Historischer Lauf nach bestätigter Einrichtung

Der Nutzer bestätigte den Windows-Dialog. Die offizielle elevated-Sandbox ist
jetzt konfiguriert; die vorherige Konfigurationsdatei wurde gesichert. Modellfreie
Tests bestanden: Schreiben und anschließendes Lesen durch den Host sowie
Read-only-Lesen mit verweigertem Schreiben (`sandbox-confirmed.json` und
`sandbox-readonly-confirmed.json` unter `.runs/qualification`). Keine manuelle
ACL-Erweiterung und kein Sandbox-Bypass wurden eingesetzt.

Der echte gpt-5.6-luna/low-Lauf mit 120 Sekunden Aufruflimit führte Developer,
Python-Bytevergleich und unabhängigen Reviewer aus. Laufzeit: 124,953 Sekunden.
Die Quelle blieb unverändert; der Abschluss enthielt den erwarteten Marker.
Die abschließende Host-Prüfung der erzeugten RESULT.txt scheiterte jedoch mit
PermissionError. Daher ist `codex-luna-repaired-write-120.json` ausdrücklich
`passed: false`; ein Modellbericht ersetzt die fehlende Host-Dateiprüfung nicht.
Der frühere 45-Sekunden-Versuch erreichte sein Zeitlimit.

Die damalige vollständige Testsuite zeigte einen Fehler beim atomaren
Checkpoint-Austausch und übersprang den Windows-Symlink-Test. Die separaten
Workflow-/Freigabe-/Core-Snapshot-Tests bestanden. Der Dateifehler wurde anschließend
untersucht; er war keine belegte dauerhafte Berechtigungsursache.

Der Checkpoint-Fehler wurde anschließend unabhängig vom Modell reproduziert:
intermittierendes WinError 5 beim atomaren Dateiaustausch bei normaler Besitzer-ACL.
Eine Windows-spezifische, begrenzte Wiederholung behebt diesen Speicherkonflikt;
dauerhafte Fehler werden nicht verschluckt. Die damalige vollständige Suite bestand
nach der Korrektur ohne Fehler mit einem Symlink-Skip; Ruff und 19
Offline-Release-Checks bestanden. Die direkte Host-Lesbarkeit des echten
Sandbox-Artefakts war zu diesem Zeitpunkt noch nicht nachgewiesen.

### Modellfreie Eingrenzung des Artefaktfehlers

Der offizielle App-Server (`command/exec`, workspaceWrite, Netzwerk deaktiviert)
reproduziert den Host-Lesefehler auch ohne Modell: neue Sandbox-Dateien sind sowohl
im Repository als auch im temporären Ordner anschließend für den Host unlesbar.
Vorhandene, vom Host angelegte Dateien lassen sich dagegen in-place ändern und
danach lesen. Das ist keine ausreichende Produktlösung: `live_smoke.py` verlangt
weiterhin die Erzeugung einer **neuen** Ergebnisdatei und erzeugt sie nicht vorab.

Ein [Upstream-Fehlerbericht](https://github.com/openai/codex/issues/48721)
beschreibt verwandte Sandbox-Besitzer-/ACL-Probleme und die alternative MXC-Sandbox.
Das aktuelle offizielle Quellschema kennt MXC, die installierte stabile CLI 0.159.2
weist `windows.sandbox="mxc"` jedoch vor Ausführung als unbekannten Wert ab.
Kein Fallback, keine globale Änderung und kein Modellaufruf erfolgten bei diesem
Probeversuch; `.runs/qualification/mxc-probe/mxc-probe-result.json`.

Auch die getrennt installierte offizielle npm-Vorabversion 0.161.0-alpha.4 lehnt
MXC vor Ausführung ab (`mxc-probe/mxc-preview-result.json`). Die globale CLI bleibt
0.159.2; es gab keinen stillen Fallback und keine weiteren Modellkosten.
Die modellfreie Gesamt-Diagnose steht in
`.runs/qualification/sandbox-host-read-diagnosis.json`. Zu diesem Zeitpunkt war
Neudatei-Erzeugung mit anschließendem Download das offene Freigabe-Gate.

## Aktuelle bestandene Live-Qualifizierung

Die Produktlösung ändert keine ACLs und umgeht die Sandbox nicht. Wenn ein vom
Codex-Auftrag gemeldetes neues Artefakt für den Host direkt unlesbar ist, liest es
der offizielle Codex-App-Server innerhalb einer read-only-Sandbox bei deaktiviertem
Netzwerk. Der Export akzeptiert nur relative Pfade innerhalb des gebundenen Workspace,
maximal 2 MB, überträgt begrenzte Blöcke und prüft abschließend Länge und SHA-256.

Der strikte erste Lauf (`codex-luna-artifact-export-final.json`) bestand Schreiben,
Python-Bytevergleich, unabhängiges Review und Artefaktprüfung. Er wurde allein wegen
des fehlenden wörtlichen Markers in der Abschlusszusammenfassung als nicht bestanden
gewertet. Diese Abweichung führte zur Härtung der Qualifikationsanweisung; sie war
kein Datei-, Review- oder Exportfehler.

Der anschließende Lauf `.runs/qualification/codex-luna-artifact-export-qualified.json`
bestand vollständig: `gpt-5.6-luna` mit niedrigem Reasoning, offizielle elevated-
Windows-Sandbox, drei Schritte, Developer und unabhängiger Reviewer, lokale
Python-Prüfungen, unveränderte Quelle, der exakte Marker `STUDIO-FACT-4729` in der
Abschlusszusammenfassung und ein bytegleiches `RESULT.txt`. Das Artefakt wurde über
den read-only/netzwerkfreien Export gelesen und mit SHA-256
`ec305d18bd19e3ab1ccceb74873de7349d66dd45ff2f171819b4aa869adafa61`
bestätigt. Gesamtlaufzeit: 101,61 Sekunden.

Dieser Nachweis schließt das Live-Gate für Schreiben, Test, unabhängiges Review und
Ergebnisexport. Eine pauschale Produktfreigabe über 90 Prozent folgt daraus nicht.

## Reale Dialogkontext-Abnahme

Computer Use erstellte den Dialog `Luna Kontext-Abnahme 2` im isolierten Workspace.
Beide Codex/Luna-Jobs wurden abgeschlossen. Der erste Turn las `CONTEXT.txt` und
antwortete mit `ORBIT-731`. Der zweite Turn erhielt den sichtbaren bisherigen Dialog,
las die Datei nicht erneut, änderte keine Datei und gab `ORBIT-731` korrekt aus dem
vorherigen Antwortkontext wieder. Der persistierte Nachweis
`.runs/qualification/codex-luna-conversation-context.json` enthält die Dialog-ID,
beide Abschlussstatus und die drei Kontextprüfungen. Persistenz- und Reload-Verträge
sind zusätzlich separat durch Fixture-/Browsertests belegt; dieser Live-Nachweis
behauptet keinen Serverneustart zwischen den beiden Modell-Turns.

## Repräsentative reale Repository-Prüfung

Computer Use startete gpt-5.6-luna im echten Repository mit read-only-Auftrag. Run
`5243dfd6db934f87961b5dd2e6079e48` las `STATUS.md`,
`docs/PRODUCT-ACCEPTANCE.md` und `docs/PRODUCT-READINESS.md`. Ein Researcher erstellte
die Prüfung, danach bewertete ein unabhängiger Reviewer. Der Lauf endete nach drei
Schritten und 93,0 Sekunden mit `status=completed`, `reviewed=true`, `dirty=false`
und ohne Fehler. Das Ergebnis enthält drei Risiken und konkrete, ausführbare
Prüfaktionen; `read_only_attested=true`.

Der Nachweis `.runs/qualification/codex-luna-repository-audit.json` ist sanitisiert:
Er speichert Status, Rollen, Pflichtdateien und Ergebnis-Hash, aber keine rohe
Modellausgabe. Dies ist die erste von drei bestandenen repräsentativen realen Aufgaben.

## Reale Test- und Feedback-Recovery

Der Lauf `.runs/qualification/codex-luna-test-recovery.json` führte exakt
`python -m unittest -v tests.test_action_approvals tests.test_conversations` aus.
Alle 19 Tests bestanden mit Exitcode 0 und Ergebnis `OK`. Der dynamische Lauf
akkumulierte drei Fehler, erhielt einmal begrenztes Feedback und schloss nach acht
Schritten in 541,391 Sekunden ab; `failure_budget_recovered=true`.

Der finale Reviewer meldete `success`, blieb read-only und führte den temporär
schreibenden Testbefehl nicht erneut aus. Die sanitisierten Nachweise speichern keine
rohen Modelltexte. Dieser Lauf belegt reale Testausführung, begrenztes Recovery und
die Trennung zwischen schreibendem Testschritt und unabhängigem Review.

## Reale GitHub-Connector- und Open-Dots-Analyse

Der öffentliche Connector lud `Anil-matcha/Open-Dots`, `README.md@main`, mit Blob
`430a85dfd698ca150cd6b9a8d8cc37c639dc493b`. Der unveränderliche Anhang
`github-README.md.txt` hatte SHA-256
`6210e1fe567259c9f9b4313935017a9fe1f5ad69f0f8764f3c7ae9b6bc3da994`.
gpt-5.6-luna/low wurde über den Adapterstandard gewählt.

Der Lauf `.runs/qualification/codex-luna-github-connector-analysis.json` endete nach
neun Schritten und 352,141 Sekunden. Drei kumulative Review-Fehler führten zu einem
begrenzten Feedback-Recovery; danach meldete der finale Reviewer `success`.
`reviewed=true`, `dirty=false`, fünf Fähigkeiten und drei priorisierte Lücken wurden
belegt. Keine rohen Modelltexte wurden gespeichert. Damit ist dynamisches
Review-Repair-Recovery an einem echten Connector-Snapshot live nachgewiesen.

## Gehärtete Unterbrechungs- und Wiederaufnahme-Abnahme

Der autoritative Lauf `.runs/qualification/codex-luna-live-resume-hardened.json`
beendete den aktiven Kindprozess tatsächlich (`child_was_terminated=true`) und
bewahrte einen dauerhaften Checkpoint mit `checkpoint_kind=planner`. Ein Resume ohne
Ack wurde mit `ContractError` verweigert. Nach Ack setzte der Runner denselben Lauf
fort und erreichte nach insgesamt drei Schritten `completed`. Der erwartete Marker
stand sowohl in der Abschlusszusammenfassung als auch im Workerbericht.

Der Workspace blieb bytebezogen unverändert; ausschließlich `.agentkit.lock` war als
interner Laufzeitpfad von dieser Prüfung ausgenommen. Der Lauf dauerte 31,515 Sekunden.
Er ersetzt den früheren Resume-Nachweis und qualifiziert Kindprozessbeendigung,
Bestätigungspflicht, Checkpoint und sichere Fortsetzung gemeinsam.

## Historischer automatisierter Stand der lokalen MVP-Abnahme

`python -m unittest discover -v` führte 240 Tests in 98,121 Sekunden aus: Status
`OK`, ein erwarteter Windows-Symlink-Test wegen fehlender Berechtigung übersprungen.
`python -m ruff check .` bestand. `node scripts/test_workflow_trace.cjs` bestand
zehn Szenarien. `python scripts/verify_release.py --windows-ocr` bestand alle 19
Checks mit `offline_only=true` und `model_tested=false`; die realen Luna-Nachweise
sind deshalb getrennt in dieser Datei dokumentiert.

## Historische Freigabe des lokalen MVP

Für den lokalen Single-Owner-MVP sind elf von elf verbindlichen Bereichen vollständig
abgenommen: **11 / 11 = 100 % innerhalb des lokalen Single-Owner-Produktscopes**.
Diese historische Quote belegt nicht den aktuellen Auftrag zur umfassenden
Agentic-Abnahme von Coding- und Marketingagenten. Dessen offene Anforderungen
und negative Qualitaetsnachweise stehen in `AGENTIC-ACCEPTANCE.md` und `STATUS.md`.
Computeraufgaben sind optional und stehen außerhalb des Nenners. Codex-Freigaben
verwenden read-only Vorschläge plus Allowlist-Host-Executor; native per-tool
interception der Codex CLI wird nicht behauptet.

Die verbleibenden Grenzen sind bewusst außerhalb des Scopes: authentifizierte/breite
Schreibconnectoren, visuelle Bildanalyse, Scan-PDF-OCR, Mehrbenutzer-/Public-Deployment
und hostile-web-gehärtete Computer-Sandbox. Die Freigabe ist keine OS-Isolation und
keine Garantie fachlicher Modellwahrheit; freigegebene Tests sind vertrauenswürdiger
lokaler Code. Alte pending approvals vor dem Host-Gateway-Upgrade werden fail-closed
verworfen und müssen neu geplant werden.
Authentifizierte/breite Schreibconnectoren, visuelle Bildanalyse, Scan-PDF-OCR,
Mehrbenutzer-/Public-Deployment und eine hostile-web-gehärtete Computer-Sandbox
bleiben Erweiterungen außerhalb dieser Freigabe.

## Verschachtelte Windows-Artefakte am 17.10.2026

Der isolierte Source-first-Marketinglauf `7e8c31a6315547d4a794589fcf88a8ce`
stoppte nach seinem ersten Schreibschritt: Ein neu vom Codex-Sandboxkonto angelegter
Unterordner verweigerte dem Host die kanonische Pfadpruefung. Der Checkpoint blieb
mit ungeklaertem `in_flight` erhalten; der Worker wurde nicht erneut ausgefuehrt.

Die Engine kann nun ausschliesslich bei echten Codex-Zugriffsfehlern die identische
`safe_workspace_path`-Pruefung im offiziellen read-only, netzwerkfreien Sandboxkonto
ausfuehren. Der Download behaelt die Liste gemeldeter Artefakte, kanonische
Workspace-/Internal-Pfadpruefung, Groessenbegrenzung und SHA-256-Pruefung bei.
Auch Metadaten und jeder Datenchunk wenden die gemeinsame Pfadpolicy an.
Keine ACL-Aenderung, kein unbeschraenkter Hostprozess und keine Wiederholung
eines unbekannten Schreibausgangs. Das ist keine neue Public-/Fremdcode-Freigabe.

Die isolierte Python-Pruefung braucht nur Standardbibliothek; `jsonschema` wird
erst bei einer tatsaechlichen Schema-Validierung importiert. Der echte Leseexport
der bereits entstandenen ersten Batchdatei lieferte 1.958 gepruefte Bytes. Das
belegt den Leseweg, keinen abgeschlossenen Marketingauftrag. Der erneute
Source-first-Versuch erhaelt einen eigenen Workspace und einen eigenen Lauf.
