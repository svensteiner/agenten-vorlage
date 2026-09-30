# Produktabnahme: AI-Arbeitsraum nach Open-Dots-Vorbild

Das aktive Ziel bleibt **über 90 Prozent produktiv und durchgetestet**. Dieser Katalog
präzisiert den Umfang anhand des Nutzerauftrags und des referenzierten Produkts. Er ist
keine nachträgliche Reduzierung auf die bereits vorhandenen AgentKit-Funktionen.

Quelle für den Vergleich: https://github.com/Anil-matcha/Open-Dots (103 beobachtete
Commits, MIT, README und Implementierungsgrenzen am 30.09.2026; Details in
[GITHUB-ADOPTION.md](GITHUB-ADOPTION.md)).
Open-Dots beschreibt einen lokal betriebenen Arbeitsraum mit Assistenten, Chat, Werkzeugen,
Freigaben, Connectoren und optionaler Computerlaufzeit. Ein Mehrbenutzer-SaaS, mobile Clients
und ein globaler Scheduler sind keine bestehenden Referenzfunktionen; sie bleiben mögliche
Erweiterungen. Öffentliche Bereitstellung wird durch das aktuelle Produkt nicht freigegeben.

## Lokaler Single-Owner-MVP: Bereiche und Nachweise

| Bereich | Status | Abnahme | Aktueller Nachweis / Grenze |
|---|---|---|---|
| Assistenten | Vollständig | Anlegen, dauerhaft auswählen, Profile/Vorgaben und Modellbindung | Pack-/HTTP-Tests und Browser-Erstellung; Archivieren/Wiederherstellen; revisionsgesichertes Bearbeiten mit Entwurfsschutz und eingefrorenen Auftragsvorgaben |
| Gesprächsverlauf | Vollständig | Mehrere echte Nachrichten mit vorherigem Antwortkontext; Reload/Neustart ohne Verlust | Reale zweistufige Luna-Kontextabnahme mit `ORBIT-731`; Browser-/Vertragstests für Reload, Neustart und Reservierungs-Recovery |
| Modellbetrieb | Vollständig | Reales Lesen, Schreiben, Tests und unabhängiges Review mit Grenzen | gpt-5.6-luna/low: bytegleicher Schreibworkflow, unabhängiges Review, gehärteter Abbruch/Resume und begrenzter Artefaktexport bestanden |
| Ausführung | Vollständig | Dynamische Rollenwahl, sichtbare Schritte, Review-Repair und Recovery | Reale Repository-Prüfung, Test-/Feedback-Recovery und GitHub-Connector-Analyse bestanden; der GitHub-Lauf zeigte Review-Fehler, begrenztes Feedback, Nacharbeit und abschließenden Reviewer-Erfolg |
| Freigaben | **Teilweise** | Risikoreiche Aktionen pausieren; konkrete Aktion genehmigen/ablehnen | DeepSeek/Demo: exakte Datei-/Testfreigaben, Neustart, Ablehnung, stale und unknown outcome geprüft. Die Codex CLI bietet keine live per-tool interception; diese sichtbare Backend-Grenze ist kein belegter Bypass |
| Dateien | Vollständig | Begrenzte Anhänge, Ergebnisdownloads und nachvollziehbarer Dateikontext | UTF-8/PDF/DOCX/XLSX/PPTX sowie lokale PNG/JPEG-OCR, Originaldownloads und Codex-Artefaktexport geprüft; visuelle Bildanalyse und Scan-PDF-OCR sind Erweiterungen |
| Connectoren | Vollständig | Ein schmaler, einwilligungsgebundener Connector mit Integrität und Retry | Öffentliche GitHub-Textvorschau und expliziter Import mit Blob-/Attachment-Hash; echter Open-Dots-Abruf und Luna-Analyse bestanden. Authentifizierte und breite Schreibconnectoren sind Erweiterungen |
| Computeraufgaben | Optional, keine Gutschrift | Optionaler isolierter Browser mit sichtbaren Aktionen und Freigaben | Nicht Bestandteil des Nenners; eine hostile-web-gehärtete Computer-Sandbox ist nicht implementiert |
| Persistenz/Wiederaufnahme | Vollständig | Prozessabbruch, unbekannter Ausgang, stabile IDs, Cold-Restore | Gehärteter Luna-Lauf terminierte den Kindprozess, persistierte `checkpoint_kind=planner`, verweigerte Resume ohne Ack und schloss nach Ack mit unverändertem Workspace ab |
| Geheimnisse/Zugriff | Vollständig | Schlüssel nicht in Browser/Log/Testprozess; Herkunftsschutz; lokale Speicherung | Subprozessfilter, Origin/Host und CSP-Hashes; Windows-DPAPI mit Browser-Speichern/Reload/Entfernen und Manipulationstest |
| Bedienung | Vollständig | Einrichten, arbeiten, Fehler erkennen und fortsetzen; responsive und tastaturbedienbar | Vier Hauptseiten responsive; 29/29 sichtbare interaktive Elemente benannt, Fokusführung, 62 Kontrastfälle und Reflow ohne Seitenüberlauf geprüft |
| Auslieferung | Vollständig | Reproduzierbare Installation, Release-Gate, Recovery-Anleitung und reale Anwendungsabnahme | Saubere Windows-/Python-3.12-Installation; 204 Tests, Ruff, zehn Workflow-Szenarien und 19/19 Offline-Release-Checks; drei getrennte reale Luna-Aufgaben dokumentiert |

## Bewertungsregel

Ein Bereich zählt erst als abgenommen, wenn seine Abnahme vollständig durch aktuelle
Ausführung belegt ist. Tests bloßer Hilfsfunktionen ersetzen keinen kompletten Nutzerablauf.
Fixture-, Browser- und Live-Modellnachweise werden getrennt ausgewiesen. Fehlende Evidenz
zählt nicht als bestanden. Ein kritischer Fehler bei Geheimnissen, Freigaben, Datenverlust
oder doppelten Seiteneffekten verhindert die Produktionsfreigabe unabhängig von einer Quote.

Der Zielstatus wird nicht aus der Zahl grüner Unittests abgeleitet. Computeraufgaben
sind optional, stehen außerhalb des Nenners und erhalten keine Gutschrift. Von den
elf verbindlichen Bereichen sind zehn vollständig abgenommen; **10 / 11 = 90,9 %**.
Die Freigabe gilt damit für den abgegrenzten **lokalen Single-Owner-MVP**. Die fehlende
Codex-per-tool-Interception bleibt die einzige verbindliche Teil-Lücke. Sie ist
ausdrücklich ausgewiesen und wird nicht als vorhandene Freigabe oder Sandbox-Bypass
dargestellt.

Diese Freigabe gilt nicht für Mehrbenutzerbetrieb oder öffentliche Bereitstellung.
Authentifizierte beziehungsweise breite Schreibconnectoren, visuelle Bildanalyse,
OCR gescannter PDFs, mobile Clients und eine hostile-web-gehärtete Computer-Sandbox
sind Erweiterungen außerhalb dieses MVP-Umfangs.
