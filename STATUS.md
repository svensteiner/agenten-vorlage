---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-12"
---

# AI Studio — Projektstatus

## Aktueller Auftrag

Zwei Agenten fuer die direkte eigene Nutzung fertigstellen: zuerst den Marketingbot als
messbaren X-Wachstumsagenten, danach den Coding-Agenten. Beide bleiben Zusammensetzungen aus
derselben AgentKit-Laufzeit, austauschbaren Rollen und Skills; der vorhandene BMD-/Steueragent
belegt denselben Baukasten fuer Buchhaltung. Die Miet-/Mehrnutzerplattform ist bewusst
zurueckgestellt.

## Letzter bestätigter Stand

- Reale Coding-Abnahme am 12.10.2026: Luna reparierte `unique_ordered` in einem
  isolierten Projekt, drei unveraenderte Tests bestanden und die separate read-only
  Rolle pruefte das Artefakt. Run `1f030bb10e4b45d2a7ed50d870bd7676` abgeschlossen.
  Ein vorheriger Live-Lauf deckte widerspruechliche Inspektions-/Vorschlagsrechte auf;
  der Adapter-Prompt ist korrigiert. LF-Vorschlaege fuer einheitliche CRLF-Dateien
  funktionieren jetzt ohne Aenderung der Zeilenenden; mehrdeutige Edits bleiben gesperrt.
  Der erfolgreiche Lauf benoetigte Feedback bei gemischten Zeilenenden; daraus folgt
  kein Nachweis unbeaufsichtigter Bearbeitung beliebiger Repositories.
- Wiederholungsabnahme `7f459565f22340b3abb71860087feacb`: Luna waehlt ohne
  Korrekturfeedback direkt einen newline-freien Edit, besteht drei Tests, aktualisiert
  STATUS.md, arbeitet einen Review-Befund selbst nach und besteht das erneute Review.
  Fuenf Schritte, Testdatei bytegenau unveraendert. Die fehlende Git-Baseline bleibt
  im Modellbericht sichtbar; unveraenderte Tests wurden separat durch den Host geprueft.
  Der bestehende Live-Smoke akzeptiert jetzt auch gezielte Edits, aber nur bei exakt
  erwarteten Ergebnisbytes. Ein CI-Flake im Ein-Sekunden-Budgettest wird mit einer
  kontrollierten Uhr und exakter Restzeitpruefung beseitigt.

- `x-growth-agent` bildet Strategie, Research, Content, Verifikation, Operator-Grenze und
  Reporting des bestehenden Marketingbots als portables AgentKit-Paket ab. Live-X-Aktionen
  verbleiben in der bestehenden Marketingbot-Pipeline.
- `Start-Marketing-Agent.ps1` erzeugt einen kuratierten, credential-bereinigten Snapshot
  der Marketingbot-Messdaten. `Start-Coding-Agent.ps1` nutzt einen explizit gewaehlten
  Entwicklungs-Workspace. Beide oeffnen AI Studio mit Codex und editierbarem Startauftrag.
- Ein aktueller echter Codex-Luna-Schreibworkflow bestand am 12.10.2026 mit dynamischer
  Planung, zwei erfolgreichen Rollenberichten, separatem read-only Review und bytegenau
  verifiziertem Artefakt. Die Offline-Demo bleibt nur eine deterministische Test-Fixture.

- Öffentlicher Release-Candidate: OIDC-Proxy-Vertrauensgrenze, exakter HTTPS-Origin,
  sitzungsgebundenes CSRF, Rollen (`viewer`, `member`, `reviewer`, `tenant_admin`),
  Nutzer-/Tenant-Rate-Limits, tenantweites Worker-Budget, Gesamt-Nutzerspeichergrenzen
  mit einem atomaren Writer für Bytes, Dateien und Verzeichnisse sowie generische
  Fehlerantworten.
- Jeder authentifizierte Nutzer erhält opake, HMAC-abgeleitete Verzeichnisse mit
  getrennten Agenten-Snapshots, Workspaces und Zuständen. API und UI verwenden nur
  Ressourcen-IDs; Cross-User- und Cross-Tenant-Zugriffe liefern 404.
- Öffentliche Ausführung ist bewusst auf `demo` und optional serververwaltetes
  DeepSeek mit `list_files`, `read_file`, `write_file` und `edit_file` begrenzt.
  Codex, `run_pytest`, beliebiger Fremdcode, lokale Hostpfade sowie Dokument-/Bildparser
  sind im öffentlichen Modus gesperrt; Anhänge sind begrenzte Textdateien.
- HMAC-verkettetes, größenbegrenztes Audit wird beim Start vollständig verifiziert;
  fehlender Log-, lokaler oder Volume-Initialisierungsmarker lässt den Start scheitern.
  Der Container-Stack
  veröffentlicht nur den TLS-Proxy, verlangt unveränderliche Image-Digests für Basis-
  und Proxy-Images und startet die App read-only, ohne Privilegien oder Docker-Socket.
- Der Quellstand und die HTTP-Verträge sind lokal geprüft. Eine reale Internetfreigabe
  bleibt bis zur Abnahme der konkreten OIDC-/TLS-Konfiguration, Backups, Lastgrenzen,
  DeepSeek-Verbindung (falls aktiviert) und eines unabhängigen Security-/Pentests offen.
  Details: `docs/PUBLIC-DEPLOYMENT.md` und `docs/PRODUCT-READINESS.md`.

- AI Studio: Assistenten anlegen, Profil/Vorgaben, Backend/Modell, Workspace, Auftragsverlauf.
- Assistenten-Vorgaben bearbeiten: revisionsgesichertes SOUL.md, atomisches Speichern,
  UTF-8-Grenzen, Konflikt-/Verbindungsfehler mit Entwurfsschutz. Neue Aufträge und spätere
  Dialognachrichten übernehmen Änderungen; laufende Jobs/Freigaben behalten ihren Core.
  Browser und Offline-Neustart-/Freigabeablauf geprüft; beschädigte/alte offene Zustände
  verhindern rückwirkende Änderungen. Nachweis: docs/ASSISTANT-MANAGEMENT.md.
- Dauerhafte Dialoge unter /chat übernehmen alle bisherigen sichtbaren Antworten und Nachrichten.
- Reale zweistufige Codex/Luna-Kontextabnahme im isolierten Workspace bestanden:
  erster Turn las `CONTEXT.txt` und antwortete `ORBIT-731`; der zweite Turn übernahm
  den Marker ausschließlich aus dem sichtbaren Dialogkontext, ohne erneuten Dateizugriff
  oder Dateiänderung. Beide Jobs abgeschlossen; Nachweis:
  `.runs/qualification/codex-luna-conversation-context.json`.
- Nachrichten werden vor Dispatch reserviert; unterbrochene Starts lassen sich mit derselben ID wiederholen.
- Live-Schritte, Review-Evidenz, Artefakt-Downloads und kontrollierte Wiederaufnahme.
- Run-ID vor Dispatch persistiert; request_id verhindert doppelte Starts bei wiederholten Anfragen.
- Loopback-/Origin-Schutz, sichere DOM-Ausgabe, maximal vier aktive Aufträge und Server-Sperre.
- DeepSeek erzwingt Read-only, Toolbudget und Deadline. Tests laufen ohne Server-Secrets
  in der Umgebung; Prozessbäume werden bei Timeout beendet.
- Ein begrenzter DeepSeek-Live-Smoke am 01.10.2026 erreichte den offiziellen Endpoint,
  wurde aber vor jeder Modellantwort mit HTTP 401 abgewiesen. Der Nachweis lautet daher
  weiterhin `model_tested=false`; das abgelehnte Test-Credential wurde nach der Prüfung
  aus dem lokalen Secret-Pfad entfernt und nie in Git oder Nachweisen gespeichert.
  `live_smoke.py` weist solche Fälle jetzt ausschließlich als bereinigte Kategorie
  `provider_authentication` aus.
- Resume ist an Agentenverzeichnis, Run-ID, Company, Workspace und Backend gebunden.
- Aktuelle vollständige Testsuite: 376 Tests in 209,230 Sekunden mit
  Branch-Coverage-Instrumentierung, Status OK;
  drei Windows-Symlink-Tests wurden mangels Berechtigung erwartbar übersprungen.
  Sechs isolierte Chromium-Journeys prüfen lokale und öffentliche Navigation,
  Accessibility/Reflow, Nutzertrennung, Assistentenarchivierung sowie Demo-Freigaben,
  Review-Recovery, Download und Reload.
  Gemessene kombinierte Line-/Branch-Coverage: 80 %; diese Zahl ist ein
  Regressionssignal und keine Produktreifequote. Ruff, Bandit ohne mittlere/hohe
  Befunde, isolierter Audit der Public-Dependency-Locks ohne bekannte CVEs, zehn
  Workflow-Trace-Szenarien und
  20/20 Offline-Release-Checks mit
  `--windows-ocr` bestanden (`offline_only=true`, `model_tested=false`); reale
  Luna-Nachweise sind separat dokumentiert.
- Der reproduzierbare Browserlauf fand einen 26-Pixel-Überlauf eines langen
  Workspace-Pfads im 390-Pixel-Dialog und belegt die Korrektur. DeepSeek akzeptiert
  nur HTTPS-Basis-URLs ohne eingebettete Zugangsdaten, Query oder Fragment und folgt
  keinen Redirects; Bearer-Zugangsdaten bleiben an den konfigurierten Provider gebunden.
- GitHub Actions erzwingt Ruff, einen Coverage-Floor, Python-3.11/3.12-
  Plattformtests, Workflow-Trace, Bandit ab mittlerer Schwere, Dependency-Audit,
  Wheel-Neuinstallation, Chromium-E2E sowie Build und Nonroot-Start des Public-Images.
  Die zwei echten WinRT-OCR-Fixtures bleiben wegen unzuverlässiger Initialisierung auf
  Hosted-Runnern im expliziten lokalen Gate `verify_release.py --windows-ocr`; der
  plattformunabhängige OCR-Vertrag läuft weiterhin in CI.
- Navigierbare Workflow-Spur aus echten Checkpoints: Freigaben, Nacharbeit,
  laufende Schritte, ungeklärte Ausgänge und Abschluss. Zehn Zustandsfälle geprüft;
  Computer Use: Demo mit zwei Freigaben, Neustart, Korrektur, Review und Download;
  320-/1440-Pixel-Abnahme. Details: docs/UI-QUALIFICATION.md.
- Responsive-Abnahme: vier Hauptseiten bei 390/1440 Pixeln, Dialog zusätzlich bei
  320 Pixeln; ausgeblendete mobile Dialognavigation und uneinheitliche GitHub-Labels
  korrigiert. Computer Use bestätigte außerdem Namen für 29/29 sichtbare interaktive
  Elemente, Tastaturfokus, Fokusführung des nativen Assistenten-Dialogs, Escape mit
  Fokusrückgabe, 62 bestandene Kontrastfälle und Reflow bei 588 CSS-Pixeln ohne
  horizontalen Seitenüberlauf. Keine formale Screenreader-Zertifizierung;
  Details: docs/UI-QUALIFICATION.md.
- Öffentlicher GitHub-Dateiconnector: explizite Vorschau, geprüfter Blob-SHA,
  unveränderlicher Quellen-Snapshot als Dialoganhang, feste API-/Größen-/Netzwerkgrenzen.
  Echter Open-Dots-README-Abruf und Browser-Import bis Demoabschluss, Reload und
  Download geprüft; private/OAuth-/Schreib-Connectoren bleiben offen.
- Reale GitHub-Connector-/Open-Dots-Aufgabe bestanden: öffentlicher Abruf von
  `Anil-matcha/Open-Dots`, `README.md@main`, Blob
  `430a85dfd698ca150cd6b9a8d8cc37c639dc493b`, Attachment-SHA-256
  `6210e1fe567259c9f9b4313935017a9fe1f5ad69f0f8764f3c7ae9b6bc3da994`.
  Luna/low über Adapterstandard; neun Schritte in 352,141 Sekunden, drei kumulative
  Review-Fehler, begrenztes Feedback-Recovery, finaler Reviewer erfolgreich,
  `reviewed=true`, `dirty=false`, fünf Fähigkeiten und drei priorisierte Lücken.
  Keine rohen Modelltexte gespeichert. Der Lauf belegt dynamisches
  Review-Repair-Recovery mit einem echten Connector-Snapshot.
- Assistenten unter /assistants archivieren/wiederherstellen: persistente Auswahl,
  unveränderte Packs, bestehende Dialoge/Anhänge/Freigaben weiter nutzbar. Browser:
  Archivieren, Reload, leere Neuauswahl, Wiederherstellen und Verbindungsfehler mit
  bewusstem Neuladen nach Server-Neustart geprüft.
- Saubere Windows-/Python-3.12-Installation geprüft: reguläres Wheel, isolierter
  CLI-Demostart, Launcher, HTTP-Demo und Neustart. CLI-Konstruktorfehler und fehlende
  pytest-Laufzeitabhängigkeit dabei gefunden und behoben; docs/INSTALLATION-QUALIFICATION.md.
- Cold-Restore am selben absoluten Pfad geprüft: Dialog, Originalanhang, Artefakt,
  abgeschlossener Job und wartende Freigabe; Provider-Verzeichnis ausgeschlossen,
  kein automatischer Dispatch, ausdrückliche Freigaben führen zum Demo-Abschluss.
- PNG-/JPEG-Anhänge mit lokaler Windows-OCR (Deutsch, sonst Englisch): echte
  synthetische PNG/JPEG- und Umlauterkennung, Originaldownload, Kontextübergabe,
  Neustart und Demo-Freigaben geprüft. Keine Bildanalyse und keine OCR für Scan-PDFs.
- PDF-/DOCX-/XLSX-/PPTX-Textanhänge mit begrenzter Subprozess-Extraktion,
  unveränderten Downloads, Seiten-/Archiv-/Textgrenzen und Unicode-Kontext geprüft.
- Browser: DOCX mit genau 2 MiB, Entwurfs-Recovery, Upload/Download und Demo-Abschluss;
  PDF-Textkontext und Ablehnung leerer PDFs samt Entfernen/Reload geprüft.
- Historischer Codex-Leseablauf mit gpt-5.5 bestand vor der Sandbox-Korrektur
  (42,672 Sekunden); dies ist keine Live-Freigabe des korrigierten Adapters.
- Codex-Adapter isoliert globale CLI-Konfiguration, behält Authentifizierung und
  Rollen-Sandbox; expliziter Standard gpt-5.6-luna/low ohne Fast-Tier-Override.
- Reale Codex-Live-Qualifizierung mit gpt-5.6-luna/low und elevated-Sandbox
  bestanden: drei Schritte, Developer plus separate read-only Reviewer-Rolle, lokale
  Python-Byteprüfung, exakter Marker `STUDIO-FACT-4729` und bytegleich exportiertes
  Ergebnisartefakt in 101,61 Sekunden. Der Export nutzt den offiziellen App-Server
  read-only, ohne Netzwerk, mit Größen- und SHA-256-Prüfung.
- Repräsentative reale Repository-Prüfung mit Computer Use und gpt-5.6-luna bestanden:
  echter Repository-Kontext read-only, `STATUS.md`, `docs/PRODUCT-ACCEPTANCE.md` und
  `docs/PRODUCT-READINESS.md`, Researcher gefolgt von separater read-only Reviewer-Rolle,
  drei Schritte in 93,0 Sekunden, `reviewed=true`, `dirty=false`. Ergebnis enthält
  drei Risiken und konkrete Prüfaktionen; sanitisiertes Evidenzartefakt:
  `.runs/qualification/codex-luna-repository-audit.json` (Run
  `5243dfd6db934f87961b5dd2e6079e48`).
- Gehärtete Codex-Unterbrechungs-/Resume-Abnahme bestanden: Kindprozess tatsächlich
  beendet, dauerhafter `checkpoint_kind=planner`, Resume ohne Ack mit `ContractError`
  verweigert, nach Ack in drei Schritten abgeschlossen; Marker in Summary und
  Workerbericht, Workspace unverändert, 31,515 Sekunden. Nur `.agentkit.lock` war
  als interner Laufzeitpfad ausgenommen.
- Reale Test-/Recovery-Aufgabe bestanden: exakt
  `python -m unittest -v tests.test_action_approvals tests.test_conversations`,
  19 Tests, Exit 0, `OK`; nach drei kumulativen Fehlern und einem Feedback in acht
  Schritten/541,391 Sekunden abgeschlossen. Der Reviewer blieb read-only und führte
  den temporär schreibenden Testbefehl nicht erneut aus.
- Windows-Sandbox-Auswahl wird gezielt aus der vorhandenen Konfiguration übernommen:
  Der Quellcode von CLI 0.130.0 bestätigt die vorherige automatische Read-only-
  Rückstufung bei fehlender Auswahl. Fehlende/ungültige Auswahl stoppt vor Modellkosten.
- Provider-Einstellungen unter /settings: DeepSeek-Schlüssel mit Windows CurrentUser-DPAPI
  verschlüsselt; keine Schlüssel in Status-/Job-APIs. Browser-Speichern/Reload/Entfernen,
  echte DPAPI-Entschlüsselung in separatem Prozess und Manipulationsschutz geprüft.
- Textanhänge in Dialogen: Upload, persistente Bindung, Kontextübergabe, Download,
  Größen-/Kontextgrenzen und sichere Wiederholung geprüft. Keine Ausführung hochgeladener Dateien.
- Browser: reale Dateiauswahl, Versand, Verlauf, Reload, Download sowie BOM-/NUL-Grenzfälle geprüft.
- Konkrete Datei-/Testfreigaben für DeepSeek, zwei Datei-Freigaben in der Demo:
  persistente Vorschläge, Ablehnen, veraltete Freigaben, Deduplizierung und sichere Wiederaufnahme geprüft.
- Browser-Freigaben: reale Codex-Dateiaktion, Server-Neustart bei wartender Freigabe,
  danach getrennte Testfreigabe, bestandenes Review und Abschluss bestätigt. Sanitierter
  Computer-Use-Nachweis: `docs/evidence/codex-cockpit-approval.json`.
- Codex-Freigaben laufen als read-only strukturierte Vorschläge mit lokalem Allowlist-
  Host-Executor; native per-tool interception der Codex CLI wird nicht behauptet.
  Echter gpt-5.6-luna-Lauf mit CLI 0.159.2 bestand genau eine `write_file`- und eine
  `run_pytest`-Genehmigung, separates read-only Review, exakten Git-Diff nur für `app.py`,
  Digest-/Continuation-Bindung und laufweiten no-replay-Schutz; ein separater
  Reject-Lauf blieb ohne Workspace-Mutation. Nachweis:
  `docs/evidence/codex-luna-action-approvals.json`.
- Browser: zwei Dialogschritte, Reload und Wiederholung einer unterbrochenen Reservierung geprüft;
  beide Dialoge nach echtem Server-Neustart wiederhergestellt.
- Browser: Assistent erstellt und Demo mit fehlgeschlagenem Review, Korrektur und Abschluss geprüft.
- GitHub-Referenzen und Lizenzentscheidungen in docs/GITHUB-ADOPTION.md dokumentiert.
- Windows-Start über Start-AI-Studio.ps1; Betrieb/Backup in docs/OPERATIONS.md.

## Abgeschlossene Live-Reparatur

- Codex CLI auf 0.159.2 aktualisiert; echter strukturierter Luna-Aufruf erfolgreich.
- Nutzer hat die offizielle Windows-Sandbox-Einrichtung bestätigt. Die globale
  Auswahl ist jetzt elevated; modellfreie Schreib- und Read-only-Prüfungen bestanden.
- Der sichere Artefaktexport liest ausschließlich ein bereits vom Auftrag gemeldetes
  Workspace-Artefakt über den offiziellen Codex-App-Server. Die Ausführung ist
  read-only und netzwerkfrei; Pfad, 2-MB-Grenze, Länge und SHA-256 werden geprüft.
- Der abschließende Luna-Lauf bestand Schreiben, Python-Test, separates read-only Review,
  Markerprüfung und bytegleichen Export von `RESULT.txt`. Nachweis:
  `.runs/qualification/codex-luna-artifact-export-qualified.json`.
- Der gehärtete Planner-Abbruch/Resume-Lauf bestand vollständig. Nachweis:
  `.runs/qualification/codex-luna-live-resume-hardened.json`.
- Intermittierender Windows-Fehler beim atomaren Checkpoint-Austausch reproduziert
  und durch begrenzte Wiederholung behoben. Dauerhafte Fehler bleiben sichtbar.
  Aktuelle vollständige Suite: 376 Tests in 209,230 Sekunden mit
  Branch-Coverage-Instrumentierung, OK, drei erwartete
  Symlink-Skips; Ruff, zehn Workflow-Trace-Szenarien und 20/20 Offline-Release-Checks
  inklusive lokaler Windows-OCR bestanden.
  Die historische direkte Host-Lesesperre wird ohne ACL-Änderung oder Sandbox-Bypass
  durch den begrenzten read-only-Export behandelt. Globale CLI unverändert;
  Nachweise: docs/LIVE-QUALIFICATION.md.

## Lokale MVP-Freigabe

Der verbindliche Single-Owner-MVP umfasst elf Bereiche; alle sind vollständig
abgenommen. Computeraufgaben sind optional, stehen außerhalb des Nenners und erhalten
keine Gutschrift. Ergebnis: **11 / 11 = 100 % innerhalb des Produktscopes**.

Diese Quote misst ausschließlich, ob jeder vereinbarte MVP-Bereich einen aktuellen
Abnahmenachweis besitzt. Sie ist keine Fehlerwahrscheinlichkeit und keine Code-Coverage;
die aktuell gemessene kombinierte Line-/Branch-Coverage beträgt 80 %.

Codex besitzt geprüfte exakte Freigabesemantiken über read-only Vorschläge und einen
Allowlist-Host-Executor; das ist keine native per-tool interception. Die Freigabe gilt
für den vertrauenswürdigen lokalen Single-User-Workspace. Freigegebene Tests bleiben
vertrauenswürdiger lokaler Code; es gibt keine OS-Isolation, Public-/Multiuser-Freigabe,
hostile-web-Computer-Sandbox oder Garantie fachlicher Modellwahrheit. Alte pending
approvals vor dem Upgrade werden fail-closed verworfen und neu geplant.

## Erweiterungen außerhalb des lokalen MVP

- Authentifizierte beziehungsweise breite Schreibconnectoren.
- Visuelle Bildanalyse und OCR gescannter PDFs.
- Horizontal skalierter Mehrmandantenbetrieb mit externer Queue/Datenbank.
- Öffentliche Ausführung von Codex, Tests oder anderem Fremdcode; dafür fehlt noch
  ein nachweislich isolierter Worker.
- Eine hostile-web-gehärtete Computer-Sandbox; Computeraufgaben sind optional.

## Grenzen

Freigegebener lokaler Single-Owner-MVP mit 100 % des verbindlichen Umfangs.
Der öffentliche Single-Tenant-Mehrbenutzermodus ist ein lokal geprüfter
Release-Candidate innerhalb des sicheren Text-/Datei-Scope. Er ist keine pauschale
Freigabe einer konkreten Internetinstallation; deren externe Go-live-Gates sind offen.
Historische production-Markierungen einzelner Packs sind keine Produktfreigabe.
Keine Credentials in Statusdateien. Keine Deploy-/Outreach-/BMD-Freigabe ableiten.
Externer AI-Company-Checkout blieb unverändert. Kein Upstream-Code übernommen.

## Einstieg

STATUS.md → README.md → AGENTS.md → docs/ARCHITECTURE.md → docs/PRODUCT-READINESS.md.
