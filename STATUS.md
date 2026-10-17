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

Getrennter Folgeauftrag in `mr-20261017`, gestartet mit
`.runs/qualification/coding_source_draft_hardening_job.py`: 888 geschuetzte
Dateien, zwei eingefrorene Testsammlungen. Vor Umsetzung 19 Fehler und eine
bestandene Grenzpruefung. Dieser Lauf verwendet Host-Gegenbeispiele; das erste
Ergebnis gilt dadurch nicht rueckwirkend als unbeaufsichtigt bestanden.
Live-Handles: privater `.runs/qualification/agentic-qualification-checkpoint-20261017.json`.

## Offene Abnahme

1. Reparatur unabhaengig pruefen; volle Regression vor Uebernahme.
2. Echte Marketingausgaben verblindet bewerten. Bisherige feste Neuner-Abnahme
   verfehlt die vorbestehende +0,5-Grenze; interne Scores sind keine Reichweite.
   Sechs frische synthetische Quellen sind vor Ausgaben eingefroren; sie ersetzen
   die gescheiterte feste Abnahme nicht.
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
