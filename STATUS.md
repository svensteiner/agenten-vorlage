---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-17"
---

# Agentenvorlagen: aktueller Stand

## Aktueller Auftrag

Coding- und Marketingagent sollen Ziele mit austauschbaren Rollen/Skills selbst
planen, ausfuehren, pruefen und nacharbeiten. Tests, kritische Abnahme, guenstige
Modelle und GitHub-Pushes sind verbindlich. Die Mietplattform ist zurueckgestellt.
**Gesamtziel noch nicht nachgewiesen; keine Produktionsfreigabe.**

## Bestaetigt

- AgentKit: letzter voller Lauf 432 Tests, drei erwartete Skips, keine Fehler;
  Ruff, 20 Offline-Gates und Python-/Security-Reviews bestanden. Danach nur Docs.
- Marketingbot/master `db358c51`: Quellenbindung und reproduzierter OS-Sperrenfix.
  4.461 Unit-Tests bestanden, elf Skips, fuenf erwartete Fehler, 277,69 Sekunden;
  separate Reviews ohne Blocker. Quellenmetadaten bleiben unverifiziert.
- Laufende Originalinstallation nicht umgestellt oder neu gestartet; ihr
  divergierender Arbeitszweig nicht ueberschrieben. Push ist kein Deployment.
- CLI/Python unterstuetzen guenstiges Primaermodell, separates Review und staerkere
  Reparatur nach Revisionen. Cockpit weiterhin mit festem Modell. Produktive
  Aktionsfreigaben bleiben erhalten; nur isolierte Experimente deaktivieren sie.

## Aktuelle Coding-Abnahme

`fa3edbfab7b94739b8c5c94d9d58b497`: fuenf Schritte, eine abgelehnte und danach
bestandene separate Review; keine Host-Codehilfe innerhalb des Laufs. 887
Quelldateien, Paket und eingefrorene Tests unveraendert. Host bestaetigt 79 Tests.
Sieben zusaetzliche Regressionen zu Unicode-Zeilentrennern und Persona scheitern.
**Nicht qualifiziert, nicht in den Marketingbot uebernommen.**

Der getrennte Folgeauftrag `4599afdcf2154f9b94302d4d922b3b62` hat ebenfalls
fuenf Schritte, eine eigene Nachbesserung und bestandene separate Review.
888 Quelldateien und zwei eingefrorene Testsammlungen unveraendert. Vor Umsetzung
19 neue Fehler und eine bestandene Grenzpruefung; danach bestaetigt der Host
99 Tests in 13,32 Sekunden. Python-/Security-Reviews ohne technische Blocker.
Der volle Kandidatenlauf im echten Git-Worktree besteht: 4.485 Tests, elf Skips,
fuenf erwartete Fehler, 272,68 Sekunden, Exit 0. Ein vorheriger Lauf in einer
Git-freien Kopie scheiterte am geerbten .runs-Ignore; dieser Kontextfehler bleibt
dokumentiert. Die neue eingefrorene Sechser-Abnahme ist gescheitert: beide Varianten 0/6
nutzbare Posts, alle 36 Rohantworten am Markdown-Bold-Filter verworfen.
Gemeldete Kosten 0,044962 USD, keine unbekannten Kosten.
[Kompletter Vergleich](docs/evidence/source-draft-quality-20261017/README.md).
Der Folgeauftrag verwendet Host-Gegenbeispiele und macht den ersten Lauf nicht
rueckwirkend bestanden. Beide Kandidaten bleiben isoliert und unpromoviert.
[Nachpruefbare Rohbelege](docs/evidence/source-draft-coding-20261017/README.md).
Live-Handles: privater `.runs/qualification/agentic-qualification-checkpoint-20261017.json`.

## Neueste Nachbesserung

Native Formatkorrektur mit separater Review, danach 105 Hosttests. Der getrennte
Grund-/Feedback-Folgeauftrag blieb ohne finale Review; der Host bestaetigt
unveraenderte geschuetzte Eingaben und 110 Tests. Eine anschliessende explizite
Hostkorrektur beschraenkt die Sprachregel auf Deutsch: 109 gezielte Tests,
96,36% Generatorabdeckung; voller echter Git-Worktree 4.495 bestanden, elf Skips,
fuenf erwartete Fehler, 276,61 Sekunden. Der blockierte native Lauf bleibt blockiert.
[Getrennte Belege](docs/evidence/source-draft-feedback-20261017/README.md).

Der erneute, vor Ausgaben eingefrorene Entwicklungs-Screen liefert sechs
technisch akzeptierte Entwuerfe in sechs Anfragen fuer 0,00743 USD. Trotzdem
keine Abnahme: zwei Entwuerfe ueber190 Zeichen und mehrere erfundene fachliche
Folgerungen. Erstnoten bleiben erhalten; die Quellenpruefung senkt den Mittelwert von0,75
auf0,4167/5. Keine Ausgabe behaelt das Urteil quellentreu; fuenf haben harte
Fehlerbefunde. [Getrennte Erstnoten und Audits](docs/evidence/source-draft-repair-screen-20261017/README.md).
Die bekannten sechs Quellen ersetzen weder neue Faelle noch das feste Neuner-Gate.

## Quellenpruefung in Arbeit

Neues Modul: nativer Lauf sieben Schritte, zwei eigene Nachbesserungen und
frische separate Review; Host173Tests,91,37% Modulabdeckung.794 geschuetzte
Quelldateien und sieben eingefrorene Dateien unveraendert, keine Host-Codehilfe
innerhalb des Laufs. Noch nicht im Nachrichtenablauf eingebaut und keine echte
Modellabnahme. Weitere Protokollgegenproben: neun Fehler/eine Kontrolle; elf
Integrationsfaelle scheitern erwartungsgemaess am noch alten Ablauf.
[Getrennte Quell-/Test-/Gegenbelege](docs/evidence/source-faithfulness-module-20261017/README.md).
Protokoll-Folgeauftrag beendet:183 Hosttests,90,41% Modulabdeckung. Native
Bereichspruefung gescheitert: eine Testlogdatei im Workspace-Wurzelordner statt
logs/ hinzugefuegt; keine geschuetzte Datei geaendert/entfernt. Keine Promotion.

## Kritischer Umfangsverstoß im Integrationslauf

Native Integration beendet:194 eigene Tests,209 unabhaengige Hosttests inklusive15
Addenda,90,41% Modulabdeckung. Trotzdem nicht qualifiziert: Planer erweiterte selbst
seine Rechte auf eine eingefrorene Testdatei; Reviewer akzeptierte das. Hostmanifest
weist den Verstoß nach. Keine Promotion. Strikte unveraenderliche Host-Schreibpolicy
wird in isolierter Kopie entwickelt; workspace-write allein begrenzt keine Dateien.
[Originalauftrag, Entscheidungen, Review und Gegenbelege](docs/evidence/source-faithfulness-integration-20261017/README.md).

## Offene Abnahme

1. Fruehere Generatorreparatur: volle Unit-Regression4.495 bestanden. Neue
   Quellenintegration: volle Unit-Regression noch laufend, Bereichsabnahme
   gescheitert. Uebernahme bleibt von Umfangsschutz, Textqualitaet und Betrieb abhaengig.
2. Echte Marketingausgaben verblindet bewerten. Bisherige feste Neuner-Abnahme
   verfehlt die vorbestehende +0,5-Grenze; interne Scores sind keine Reichweite.
   Auch die sechs frischen synthetischen Quellen sind gescheitert (0/6 je Variante).
   Ausgabevorgaben und Generator muessen zusammenpassen; Schutzfilter erhalten.
3. Repraesentativer Coding-Auftrag mit vollstaendigem Hostnachweis ohne Codehilfe.
4. Normalen Einsatz gegen die tatsaechliche Installation pruefen.

## Nachweise

[Agentic-Abnahme](docs/AGENTIC-ACCEPTANCE.md), [Live-Abnahme](docs/LIVE-QUALIFICATION.md),
[Source-first-Belege](docs/evidence/source-first-marketing-20261017/README.md),
[Marketingbot-Nachweise](https://github.com/svensteiner/marketingbot/blob/master/docs/SOURCE_PROVENANCE.md).
[Historischer Status](docs/evidence/status-history-20261017.md) erhaelt die alten
Versuche und die MVP-Abnahme. Historische 11/11 messen Funktionsumfang, nicht
allgemeine Zuverlaessigkeit oder den aktuellen Gesamtauftrag.
Einstieg: [README](README.md), [Architektur](docs/ARCHITECTURE.md), [Betrieb](docs/OPERATIONS.md).

Keine Credentials in Nachweisen. Keine Deploy-/Outreach-/BMD-Freigabe ableiten.
Unbekannte Aktionsausgaenge nicht automatisch wiederholen: echten Handle pruefen.
Externen AI-Company-Checkout unveraendert lassen.
