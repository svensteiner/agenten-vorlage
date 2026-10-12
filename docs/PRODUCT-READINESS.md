# AI Studio: Produkt- und Betriebsreife

Stand: 01.10.2026. Produktziel: ein AI-Arbeitsraum nach dem Bedienvorbild von
[Open-Dots](https://github.com/Anil-matcha/Open-Dots), auf dem vorhandenen AgentKit-Kern.
Der klar begrenzte lokale Single-Owner-MVP erreicht **11 von 11 verbindlichen
Bereichen = 100 % innerhalb seines Produktscopes**. Computeraufgaben sind optional,
stehen außerhalb des Nenners und erhalten keine Gutschrift. Codex-Freigaben verwenden
read-only Vorschläge und einen Allowlist-Host-Executor; native per-tool interception
der Codex CLI wird nicht behauptet.

Für öffentlichen Betrieb existiert jetzt ein eigener, lokal geprüfter
**Single-Tenant-Mehrbenutzer-Release-Candidate**. Seine Quellcode-Gates sind erfüllt;
die konkrete Internetinstallation bleibt bis zu den unten genannten externen
Abnahmen ein **No-Go**. Die beiden Bewertungen werden nicht zu einer scheinpräzisen
Gesamtprozentzahl vermischt.

## Öffentlicher Release-Candidate

| Quellcode-Gate | Stand |
|---|---|
| OIDC-Proxy-Vertrauensgrenze, exakter HTTPS-Host | implementiert und vertraglich getestet |
| Sitzungsgebundenes CSRF und exakter Origin | implementiert und HTTP-getestet |
| Rollen und Cross-User-/Cross-Tenant-Isolation | implementiert und HTTP-getestet |
| Opake getrennte Agenten-, Workspace- und State-Wurzeln | implementiert; Symlink-/Traversal-Tests |
| Rate-, Job-, Runtime- und Speichergrenzen | implementiert; Unit-/Vertragstests |
| Sicherer Public-Tool-Scope ohne Codex/Test/Fremdcode | implementiert und fail-closed getestet |
| Pfad-/Continuation-Redaktion und HMAC-Auditkette | implementiert; Manipulationstest |
| Gehärtete TLS/OIDC/Container-Vorlage | statisch geprüft; Images müssen per Digest gesetzt werden |

Diese 8/8-Aussage bedeutet nur, dass der definierte Quellcode-Scope implementiert und
lokal nachgewiesen ist. Sie ist keine Ausfallwahrscheinlichkeit, kein Pentest und keine
Freigabe einer unbekannten Infrastruktur.

Vor öffentlichem Go-live braucht **jede konkrete Installation** folgende Evidenz:

1. realer OIDC-Login mit Domain-/Gruppenpolicy, Logout und Session-Rotation;
2. reale DNS-/TLS-Kette sowie verifizierte Forwarded-Header am Proxy;
3. verschlüsseltes Backup plus Restore-Probe des persistenten Volumes und der Secrets;
4. repräsentativer Last-/Soak-Test mit beobachteten CPU-, RAM-, Queue- und Volume-Grenzen,
   einer erzwungenen Volume-/Projektquote und Alarmierung vor freiem Speicherende;
5. unabhängiger Security-/Penetrationstest einschließlich IDOR, CSRF, Header-Spoofing und Uploads;
6. Monitoring/Alarmierung sowie ein getesteter Rollback auf ein unveränderliches Image;
7. bei aktiviertem DeepSeek ein echter, budgetierter Provider-Smoke ohne Secret-/Pfadleck.

Bis diese sieben externen Gates für das Zielsystem belegt sind, lautet die ehrliche
Produktionsentscheidung: **bereit zum Staging, noch nicht für offenen Internetverkehr freigegeben**.

## Implementiert und geprüft

| Fähigkeit | Nachweis |
|---|---|
| Eigene Assistenten mit Profil und Vorgaben | Persistente Packs; HTTP-/Manager-Tests; Browser-Erstellung, reversible Archivverwaltung und revisionsgesichertes Bearbeiten der Vorgaben |
| Workspace, Backend und Modell wählen | Verfügbarkeitsanzeige ohne Schlüssel im Browser |
| Aufträge und Folgeaufträge | Dauerhafter Verlauf; Kontext des letzten abgeschlossenen Auftrags; Company-/Workspace-Bindung |
| Wiederaufnahme | Gehärteter realer Luna-Lauf: Kindprozess beendet, `checkpoint_kind=planner`, Resume ohne Ack verweigert, nach Ack abgeschlossen, Marker in Summary und Workerreport, Workspace unverändert; nur `.agentkit.lock` intern ausgenommen |
| Sichere Wiederholung von Startanfragen | Browser-request_id; persistente serverseitige Deduplizierung auch nach Neustart |
| Nachvollziehbare Arbeit | Live-Checkpoint, Rollen, Evidenz, fehlgeschlagenes Review und Korrektur sichtbar |
| Ergebnisse herunterladen | Nur vom Auftrag gemeldete Dateien innerhalb seines Workspace; maximal 2 MB; Codex-Fallback read-only, netzwerkfrei, längen- und SHA-256-geprüft |
| Lokaler Zugriff | Loopback, Host-/Origin-Prüfung, JSON-only POST, Größenlimits, vier aktive Aufträge |
| Begrenzte Werkzeuge | Read-only-Reviewer dürfen weder schreiben noch Tests starten; Tool-/Zeitlimits |
| Prozess- und Zustandsgrenzen | Prozessbaum-Abbruch, gefilterte Testumgebung, Workspace-Sperre, Resume-Pfadbindung |
| Dauerhafte Dialoge | Vollständiger sichtbarer Kontext; zwei Schritte, Reload, Reservierungs-Recovery im Browser; nach Server-Neustart per API und Browser wiederhergestellt; echter zweistufiger Luna-Dialog übernahm `ORBIT-731` im zweiten Turn ausschließlich aus dem vorherigen Antwortkontext |
| Konkrete Aktionsfreigaben | DeepSeek/Demo und Codex-Host-Gateway: exakte Aktionen, Neustart, Ablehnung, stale/unknown outcome, Digest-/Continuation-Bindung und laufweiter no-replay-Schutz geprüft; echte Codex-Abnahme mit gpt-5.6-luna/CLI 0.159.2, genau zwei Freigaben und exaktem Git-Diff nur für `app.py` |
| Text- und Dokumentanhänge | UTF-8/PDF/DOCX/XLSX/PPTX; Browser-Dateiauswahl bis 2 MiB, Kontextübergabe, Originaldownload; Bindungs-, Integritäts- und Retry-Tests |
| PNG-/JPEG-Texterkennung | Native Windows-OCR, deutsche Unicode-Fixture; Originalbytes, Dialogkontext, Neustart, Fehler-Recovery und Browser geprüft; keine visuelle Bildanalyse |
| Lokale Provider-Einrichtung | Windows CurrentUser-DPAPI; synthetische Schlüssel, Manipulationstest, Browser-Speichern/Reload/Entfernen |
| Wiederherstellung einer Sicherung | Cold-Restore an denselben absoluten Pfad; Dialog, Anhang und wartende Freigabe erhalten; Provider ausgeschlossen, kein automatischer Dispatch |
| Installation | Frische Windows-/Python-3.12-Umgebung, reguläres Wheel, isolierter CLI-Demostart und Launcher/HTTP-Demo samt Neustart; INSTALLATION-QUALIFICATION.md |
| Öffentliche GitHub-Dateien | Echter Open-Dots-README-Abruf mit Blob-/Attachment-Hash; Browser-Vorschau/Import und realer Luna-Workflow mit Review-Repair-Recovery bestanden; keine Authentifizierung oder Schreibaktion |
| Repräsentative reale Aufgaben | Drei getrennte Luna-Nachweise: read-only-Repository-Audit, echte 19-Test-/Feedback-Recovery und GitHub-Connector-Analyse mit finalem Reviewer-Erfolg |
| Bedienung und Accessibility | Responsive Browserabnahme; 29/29 sichtbare interaktive Elemente benannt, Tastaturfokus und Dialog-Fokusführung geprüft, 62 sichtbare Textfälle mit bestandenem WCAG-Kontrast; sechs isolierte Chromium-Journeys prüfen lokale und öffentliche Nutzerabläufe einschließlich 390-Pixel-Reflow und Launcher-Voreinstellungen; keine formale Screenreader-Zertifizierung |
| Reproduzierbare Offline-Abnahme | 376 Tests in 209,230 s mit Branch-Coverage-Instrumentierung, OK, drei erwartete Windows-Symlink-Skips; 80 % kombinierte Line-/Branch-Coverage; Ruff und Bandit ohne mittlere/hohe Befunde; Dependency-Audit ohne bekannte Schwachstellen; zehn Workflow-Trace-Szenarien; 20/20 Offline-Release-Checks mit --windows-ocr (`offline_only=true`, `model_tested=false`); Live-Luna-Nachweise separat |

Die Browser-Abnahme erstellte `generated/studio-smoke`, startete eine Demo und prüfte
Erstellen → Review fehlgeschlagen → Korrektur → Review bestanden → Abschluss.
Der Server wurde neu gestartet, um den gespeicherten Verlauf erneut zu öffnen.
Die fünf Playwright-Journeys laufen gegen isolierte temporäre Serverzustände und
prüfen Navigation, zugängliche Namen, mobilen Reflow, Archivieren/Wiederherstellen,
zweistufige Demo-Freigaben, fehlgeschlagenes Review, Reparatur, Download, Reload sowie
Authentifizierung und Trennung zweier öffentlicher Nutzersitzungen.
CI erzeugt Trace und Screenshot als Workflow-Artefakte. Der Public-Deployment-Job baut
zusätzlich das Public-Image, prüft dessen Dependency-Scope, interpoliert Compose und startet
den Public-Server als Nonroot-Prozess bis zur Readiness. Echte WinRT-OCR bleibt
wegen unzuverlässiger Initialisierung auf Hosted-Runnern im separaten lokalen
`verify_release.py --windows-ocr`-Gate.

## Backend-Nachweise

- **Demo:** vollständiger Offline-Ablauf, echte Dateien und HTTP-/Browserbedienung.
  Deterministische Fixture, kein Modell und keine beliebige Aufgabenlösung.
- **DeepSeek:** API-/Tool-Verträge und lokale Subprozesse geprüft. Ein begrenzter
  Live-Smoke am 01.10.2026 erreichte den offiziellen Endpoint, wurde jedoch vor jeder
  Modellantwort mit HTTP 401 abgewiesen. Damit bleibt `model_tested=false`; es ist kein
  gültiger DeepSeek-Zugang konfiguriert. Der sanitisierten Nachweis enthält nur
  `blocked_category=provider_authentication`, keine Providerantwort oder Zugangsdaten.
- **Codex:** Adapterverträge und echte Timeout-/Exitcode-Prozesse geprüft. Der Adapter
  isoliert globale CLI-Einstellungen mit `--ignore-user-config` und passt das
  Anbieterschema an. Authentifizierung bleibt erhalten; globale Konfiguration unverändert.
  Standard ist explizit `gpt-5.6-luna` mit niedrigem Reasoning, ohne Fast-Tier-Override.
  Der aktuelle reale Schreiblauf in der offiziellen elevated-Windows-Sandbox bestand
  in 101,61 Sekunden: drei Schritte, Developer plus unabhängiger Reviewer, lokale
  Python-Prüfungen, unveränderte Quelle, exakter Marker `STUDIO-FACT-4729` und
  bytegleiches Ergebnisartefakt. Ein direkter Host-Read war für sandbox-eigene Dateien
  nicht möglich; der qualifizierte Download nutzt deshalb den offiziellen Codex-App-Server
  read-only und ohne Netzwerk, begrenzt auf das gemeldete Workspace-Artefakt mit
  Größen-, Längen- und SHA-256-Prüfung. Nachweis:
  `.runs/qualification/codex-luna-artifact-export-qualified.json`.
  Ein zusätzlicher realer Computer-Use-Dialog `Luna Kontext-Abnahme 2` bestand zwei
  abgeschlossene Turns im isolierten Workspace. Der erste Turn las `CONTEXT.txt` und
  antwortete mit `ORBIT-731`; der zweite wiederholte den Marker nur aus dem vorherigen
  Dialogkontext, ohne die Datei erneut zu lesen oder Dateien zu ändern. Nachweis:
  `.runs/qualification/codex-luna-conversation-context.json`.
  Eine repräsentative reale Repository-Prüfung las `STATUS.md`,
  `docs/PRODUCT-ACCEPTANCE.md` und `docs/PRODUCT-READINESS.md` read-only. Researcher
  und unabhängiger Reviewer schlossen drei Schritte in 93,0 Sekunden ab;
  `reviewed=true`, `dirty=false`, drei Risiken und konkrete Prüfaktionen sind belegt.
  Der sanitisierten Evidenz fehlen absichtlich rohe Modellausgaben. Nachweis:
  `.runs/qualification/codex-luna-repository-audit.json`, Run
  `5243dfd6db934f87961b5dd2e6079e48`.
  Die reale Test-/Recovery-Aufgabe führte exakt
  `python -m unittest -v tests.test_action_approvals tests.test_conversations` aus:
  19 Tests, Exit 0, `OK`. Nach drei kumulativen Fehlern und einem Feedback endete
  sie nach acht Schritten/541,391 Sekunden abgeschlossen. Der finale Reviewer blieb
  read-only und führte den temporär schreibenden Befehl nicht erneut aus. Nachweis:
  `.runs/qualification/codex-luna-test-recovery.json`.
  Der reale GitHub-Connector-Lauf importierte öffentlich
  `Anil-matcha/Open-Dots/README.md@main`, Blob
  `430a85dfd698ca150cd6b9a8d8cc37c639dc493b`, Attachment-SHA-256
  `6210e1fe567259c9f9b4313935017a9fe1f5ad69f0f8764f3c7ae9b6bc3da994`.
  Luna/low lief über den Adapterstandard: neun Schritte/352,141 Sekunden, drei
  kumulative Review-Fehler, ein begrenztes Feedback-Recovery, fünf Fähigkeiten,
  drei priorisierte Lücken, finaler Reviewer `success`, `reviewed=true`,
  `dirty=false`. Keine rohen Modelltexte wurden gespeichert. Dieser Lauf belegt
  dynamisches Review-Repair-Recovery. Nachweis:
  `.runs/qualification/codex-luna-github-connector-analysis.json`.
  Der gehärtete Resume-Lauf terminierte den Kindprozess, persistierte
  `checkpoint_kind=planner`, verweigerte Resume ohne Ack, setzte nach Ack fort und
  bestätigte den Marker in Summary und Workerreport. Der Workspace blieb bis auf die
  interne Ausnahme `.agentkit.lock` unverändert; drei Schritte/31,515 Sekunden.
  Nachweis: `.runs/qualification/codex-luna-live-resume-hardened.json`.
  Ein historischer Lese-Smoke mit tatsächlichem Dateizugriff bestand am 30.09.2026
  in 42,672 Sekunden (`.runs/qualification/codex-isolated-read.json`).
  Frühere Lese-Smokes waren blockiert: Dateizugriff in der Windows-Sandbox
  verweigert bzw. Planner-Timeout nach 45 Sekunden. Historische JSON-Nachweise liegen unter
  `.runs/qualification/codex-gpt55-read*.json`. Im ersten Nachweis ist `source_unchanged`
  wegen einer inzwischen korrigierten CRLF-Prüfung falsch negativ; kein Nachweis einer Modelländerung.
  `scripts/live_smoke.py` fordert ein explizites Modell und `--live`; keine stillen Kosten.
  Lokales Vorhandensein von Credentials wird getrennt von erfolgreichem Live-Zugriff ausgewiesen.
  Die korrigierte Konfigurationsisolation übernimmt jetzt ausschließlich die vorhandene
  Windows-Sandbox-Auswahl. Frühere gpt-5.5-/Luna-Fehler bleiben als historische
  Diagnosen dokumentiert; sie beschreiben nicht den aktuellen qualifizierten Stand.
  [Nachweise und Diagnosegrenzen](LIVE-QUALIFICATION.md).

## Freigabeumfang und verbleibende Grenze

Der lokale Single-Owner-MVP ist mit **11/11 = 100 %** der verbindlichen Bereiche
freigegeben. Die Codex-Freigabe verwendet read-only Vorschläge und einen lokalen
Allowlist-Host-Executor. Native per-tool interception der Codex CLI wird ausdrücklich
nicht behauptet. Die Abnahme gilt für einen vertrauenswürdigen lokalen Single-User-
Workspace; freigegebene Tests sind vertrauenswürdiger lokaler Code.

Diese Prozentzahl bewertet ausschließlich, ob jeder vereinbarte MVP-Bereich einen
Abnahmenachweis besitzt. Sie ist keine Fehlerwahrscheinlichkeit und keine Code-Coverage;
die aktuell gemessene kombinierte Line-/Branch-Coverage beträgt 80 %.

Die lokale Produktfreigabe ist keine OS-Isolation, keine hostile-web-Computer-Sandbox
und keine Garantie fachlicher Modellwahrheit. Der getrennte Public-Adapter ist nur für
den oben beschriebenen Text-/Datei-Scope freigegeben; seine konkrete Bereitstellung
benötigt die sieben externen Go-live-Nachweise.
Alte pending approvals vor dem Digest-/Host-Gateway-Upgrade werden fail-closed
verworfen und müssen neu geplant werden.

Außerhalb dieses MVP liegen authentifizierte beziehungsweise breite
Schreibconnectoren, visuelle Bildanalyse, OCR gescannter PDFs, horizontaler
Mehrmandantenbetrieb, öffentliche Fremdcodeausführung und eine hostile-web-gehärtete
Computer-Sandbox. Computeraufgaben sind optional, werden nicht als erfüllt behauptet
und zählen nicht zur Quote.
Einzelne Folgeaufträge erhalten den letzten Auftrag und dessen Zusammenfassung. Die neue
Dialogansicht erhält dagegen den vollständigen sichtbaren Verlauf innerhalb expliziter
Kontextgrenzen. Das Review-Gate prüft Berichte und Artefakte, keine fachliche Wahrheit.
DeepSeek-Dateiänderungen und Testausführungen erhalten konkrete Freigaben; Grenzen
und Nachweise stehen in [ACTION-APPROVALS.md](ACTION-APPROVALS.md).

Der verbindliche Produktumfang bleibt in [PRODUCT-ACCEPTANCE.md](PRODUCT-ACCEPTANCE.md)
festgehalten; diese Offline-Abnahme ersetzt die dort offenen Produktbereiche nicht.

Die gefilterte Subprozessumgebung verhindert das beiläufige Vererben von Server-Secrets;
sie ersetzt keine OS-Isolation. Codex erhält seine explizit nötige Authentifizierung
(`OPENAI_API_KEY`, `CODEX_HOME`). Vertrauenswürdige lokale Workspaces bleiben Voraussetzung.

## Historische Freigabeentscheidung nach OCR-Abnahme

Am 30.09.2026 erneut ohne Modellaufruf geprüft: Der laufende Server hat keinen
konfigurierten DeepSeek-Zugang (weder gespeicherter Schlüssel noch Umgebung).
Codex bleibt bei CLI 0.130.0 und derselben Windows-Sandbox-Auswahl; vorhandene
Authentifizierungsdateien beweisen keinen funktionierenden Worker-Dateizugriff.
Der letzte tatsächliche Schreib-Smoke endete mit Access-denied und ohne Review.
Docker und Podman sind weiterhin nicht als Laufzeit verfügbar. Sanitisiertes
Prüfergebnis: `.runs/qualification/current-release-blockers.json`.

Zu diesem historischen Stand blieb die Gesamtfreigabe aus. Der damals nächste
entscheidende Nachweis erforderte einen funktionsfähigen Modellanbieter oder die
belegte Reparatur der Host-Sandbox. Schreiben, Test, Review und Artefaktexport sind
inzwischen qualifiziert. Die gehärtete Wiederaufnahme, der Repository-Audit, die
Test-/Feedback-Recovery und der GitHub-Connector-Workflow bestanden anschließend.
Weitere Fixture-Tests oder eine höhere Zahl kleiner Funktionen ersetzen dieses Gate
nicht. Authentifizierte Connectoren und die optionale isolierte Computerlaufzeit
bleiben separate offene Produktbereiche; sie werden nicht als abgeschlossen gezählt.

## Aktueller Reparaturstand

Codex CLI wurde auf 0.159.2 aktualisiert. gpt-5.6-luna/low ist der neue
Standard. Nach nutzerbestätigter offizieller elevated-Sandbox-Einrichtung bestand
der reale Workflow Schreiben, lokale Python-Prüfung, unabhängiges Review und
bytegleichen Artefaktexport in drei Schritten und 101,61 Sekunden. Der Export liest
das bereits gemeldete Artefakt über den offiziellen Codex-App-Server read-only und
netzwerkfrei; Pfad, 2-MB-Grenze, Länge und SHA-256 werden geprüft. Weder ACLs noch
Sandboxregeln wurden abgeschwächt.
Die repräsentative read-only-Repository-Prüfung mit Researcher und unabhängigem
Reviewer bestand ebenfalls in drei Schritten und 93,0 Sekunden. Sie ergänzt die
synthetischen Backend-Nachweise. Test-Recovery und GitHub-Connector-Analyse ergänzen
zwei weitere reale Aufgaben; der GitHub-Lauf belegt dynamisches Review-Repair-Recovery.
Der gehärtete Resume-Lauf bestand mit tatsächlicher Kindprozessbeendigung und
unverändertem Workspace.
Der zusätzlich gefundene Checkpoint-Konflikt unter Windows wurde reproduziert
und behoben. Die aktuelle vollständige Testsuite lief mit 376 Tests in
209,230 Sekunden mit Branch-Coverage-Instrumentierung durch (OK, drei erwartete
Windows-Symlink-Skips); Ruff, zehn
Workflow-Trace-Szenarien sowie 20/20 Offline-Release-Checks mit echter lokaler
Windows-OCR bestanden.
Die neue grafische Workflow-Spur wurde mit Computer Use inklusive zwei Freigaben,
Neustart, Nacharbeit, Review, Download und mobiler Ansicht abgenommen.
Aktuelle Evidenz: [LIVE-QUALIFICATION.md](LIVE-QUALIFICATION.md).
