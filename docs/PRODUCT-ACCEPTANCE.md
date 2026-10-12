# Produktabnahme: AI-Arbeitsraum nach Open-Dots-Vorbild

Das aktive Ziel ist **100 Prozent innerhalb des ausdrücklich abgegrenzten Produktscopes**. Dieser Katalog
präzisiert den Umfang anhand des Nutzerauftrags und des referenzierten Produkts. Er ist
keine nachträgliche Reduzierung auf die bereits vorhandenen AgentKit-Funktionen.

Quelle für den Vergleich: https://github.com/Anil-matcha/Open-Dots (103 beobachtete
Commits, MIT, README und Implementierungsgrenzen am 30.09.2026; Details in
[GITHUB-ADOPTION.md](GITHUB-ADOPTION.md)).
Open-Dots beschreibt einen lokal betriebenen Arbeitsraum mit Assistenten, Chat, Werkzeugen,
Freigaben, Connectoren und optionaler Computerlaufzeit. Ein Mehrbenutzer-SaaS, mobile Clients
und ein globaler Scheduler sind keine bestehenden Referenzfunktionen. Dieses Repository hat
zusätzlich einen getrennt bewerteten Single-Tenant-Mehrbenutzer-Release-Candidate; dessen
installationsabhängige Go-live-Gates stehen in [PRODUCT-READINESS.md](PRODUCT-READINESS.md).

## Lokaler Single-Owner-MVP: Bereiche und Nachweise

| Bereich | Status | Abnahme | Aktueller Nachweis / Grenze |
|---|---|---|---|
| Assistenten | Vollständig | Anlegen, dauerhaft auswählen, Profile/Vorgaben und Modellbindung | Pack-/HTTP-Tests und Browser-Erstellung; Archivieren/Wiederherstellen; revisionsgesichertes Bearbeiten mit Entwurfsschutz und eingefrorenen Auftragsvorgaben |
| Gesprächsverlauf | Vollständig | Mehrere echte Nachrichten mit vorherigem Antwortkontext; Reload/Neustart ohne Verlust | Reale zweistufige Luna-Kontextabnahme mit `ORBIT-731`; Browser-/Vertragstests für Reload, Neustart und Reservierungs-Recovery |
| Modellbetrieb | Vollständig | Reales Lesen, Schreiben, Tests und unabhängiges Review mit Grenzen | gpt-5.6-luna/low: bytegleicher Schreibworkflow, unabhängiges Review, gehärteter Abbruch/Resume und begrenzter Artefaktexport bestanden |
| Ausführung | Vollständig | Dynamische Rollenwahl, sichtbare Schritte, Review-Repair und Recovery | Reale Repository-Prüfung, Test-/Feedback-Recovery und GitHub-Connector-Analyse bestanden; der GitHub-Lauf zeigte Review-Fehler, begrenztes Feedback, Nacharbeit und abschließenden Reviewer-Erfolg |
| Freigaben | Vollständig | Risikoreiche Aktionen pausieren; konkrete Aktion genehmigen/ablehnen | DeepSeek/Demo sowie Codex-Host-Gateway: exakte Datei-/Testfreigaben, Neustart, Ablehnung, stale/unknown outcome, Digest-/Continuation-Bindung und laufweiter no-replay-Schutz geprüft; echte Codex-Abnahme mit gpt-5.6-luna/CLI 0.159.2 und exaktem Git-Diff |
| Dateien | Vollständig | Begrenzte Anhänge, Ergebnisdownloads und nachvollziehbarer Dateikontext | UTF-8/PDF/DOCX/XLSX/PPTX sowie lokale PNG/JPEG-OCR, Originaldownloads und Codex-Artefaktexport geprüft; visuelle Bildanalyse und Scan-PDF-OCR sind Erweiterungen |
| Connectoren | Vollständig | Ein schmaler, einwilligungsgebundener Connector mit Integrität und Retry | Öffentliche GitHub-Textvorschau und expliziter Import mit Blob-/Attachment-Hash; echter Open-Dots-Abruf und Luna-Analyse bestanden. Authentifizierte und breite Schreibconnectoren sind Erweiterungen |
| Computeraufgaben | Optional, keine Gutschrift | Optionaler isolierter Browser mit sichtbaren Aktionen und Freigaben | Nicht Bestandteil des Nenners; eine hostile-web-gehärtete Computer-Sandbox ist nicht implementiert |
| Persistenz/Wiederaufnahme | Vollständig | Prozessabbruch, unbekannter Ausgang, stabile IDs, Cold-Restore | Gehärteter Luna-Lauf terminierte den Kindprozess, persistierte `checkpoint_kind=planner`, verweigerte Resume ohne Ack und schloss nach Ack mit unverändertem Workspace ab |
| Geheimnisse/Zugriff | Vollständig | Schlüssel nicht in Browser/Log/Testprozess; Herkunftsschutz; lokale Speicherung | Subprozessfilter, Origin/Host und CSP-Hashes; Windows-DPAPI mit Browser-Speichern/Reload/Entfernen und Manipulationstest |
| Bedienung | Vollständig | Einrichten, arbeiten, Fehler erkennen und fortsetzen; responsive und tastaturbedienbar | Vier Hauptseiten responsive; 29/29 sichtbare interaktive Elemente benannt, Fokusführung, 62 Kontrastfälle und Reflow geprüft; sechs isolierte Chromium-E2E-Journeys laufen reproduzierbar |
| Auslieferung | Vollständig | Reproduzierbare Installation, Release-Gate, Recovery-Anleitung und reale Anwendungsabnahme | Saubere Windows-/Python-3.12-Installation; 376 Tests, 80 % Line-/Branch-Coverage, Ruff, Bandit ohne mittlere/hohe Befunde, Dependency-Audit ohne bekannte Schwachstellen, zehn Workflow-Szenarien und 20/20 Offline-Release-Checks; reale Luna-Aufgaben dokumentiert |

## Bewertungsregel

Ein Bereich zählt erst als abgenommen, wenn seine Abnahme vollständig durch aktuelle
Ausführung belegt ist. Tests bloßer Hilfsfunktionen ersetzen keinen kompletten Nutzerablauf.
Fixture-, Browser- und Live-Modellnachweise werden getrennt ausgewiesen. Fehlende Evidenz
zählt nicht als bestanden. Ein kritischer Fehler bei Geheimnissen, Freigaben, Datenverlust
oder doppelten Seiteneffekten verhindert die Produktionsfreigabe unabhängig von einer Quote.

Der Zielstatus wird nicht aus der Zahl grüner Unittests abgeleitet. Computeraufgaben
sind optional, stehen außerhalb des Nenners und erhalten keine Gutschrift. Von den
elf verbindlichen Bereiche sind vollständig abgenommen; **11 / 11 = 100 %** innerhalb
des abgegrenzten **lokalen Single-Owner-MVP**. Die Codex-Abnahme gilt für read-only
Vorschläge plus Allowlist-Host-Executor. Sie behauptet keine native per-tool
interception der Codex CLI.

Die 11/11-Quote ist eine binäre Abdeckung des vereinbarten Funktionsumfangs, keine
statistische Zuverlässigkeits- oder Code-Coverage-Aussage. Die aktuelle kombinierte
Line-/Branch-Coverage beträgt 80 %. GitHub Actions führt die Plattform-, Package-,
Browser- und Public-Container-Gates aus. Echte Windows-OCR bleibt wegen der WinRT-
Initialisierung auf Hosted-Runnern ein separat protokolliertes lokales Release-Gate.

Die 11/11-Freigabe bewertet weiterhin nur den lokalen Single-Owner-MVP. Für den
Single-Tenant-Mehrbenutzerbetrieb gilt der separate Public-Release-Candidate mit sieben
externen Zielsystem-Gates. Authentifizierte beziehungsweise breite Schreibconnectoren,
visuelle Bildanalyse, OCR gescannter PDFs, mobile Clients und eine hostile-web-gehärtete
Computer-Sandbox bleiben Erweiterungen außerhalb dieses MVP-Umfangs.
