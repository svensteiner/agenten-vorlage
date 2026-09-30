---
name: programming-workflow
description: Führt einen Programmierauftrag dynamisch von Repository-Intake über kleine Implementierung und Tests bis zum unabhängigen Review.
metadata:
  version: "0.1.0"
  owner: AI_Studioxyz
---

# Programming workflow

Nutze diese Fähigkeit für Codeänderungen, Bugfixes, Tests und technische Dokumentation im
zugewiesenen Workspace. Sie ergänzt `implement-feature`, `debug-systematically` und
`verification-before-completion`; sie ersetzt keine Repository-Regeln.

## Entscheidungslogik

1. Lies Projektregeln, relevante Dateien, Aufrufer und vorhandene Tests. Formuliere das konkrete
   Abnahmekriterium.
2. Wähle nur den kleinsten nächsten Schritt. Bei fehlender Ursache erst reproduzieren/diagnostizieren;
   bei ausreichender Ursache direkt reparieren; bei einem Review-Fund gezielt nachbessern.
3. Nach jedem Schreibschritt die Änderung gegen das Abnahmekriterium prüfen. Ein früheres Review
   gilt danach nicht mehr als aktuell.
4. Übergib an den read-only Reviewer mit Diff, ausgeführten Befehlen und offenen Risiken. Akzeptiere
   nur ein Review mit konkreter Evidenz.

## Code-Standards

- Öffentliche Verträge, Aufrufer und Fehlermeldungen synchron halten.
- Bestehende Dependencies und Projektmuster bevorzugen; keine unnötige Framework-Schicht ergänzen.
- Eingaben an Grenzen validieren und externe Aufrufe mit Timeout/Fehlerpfad versehen.
- Tests auf beobachtbares Verhalten ausrichten; mindestens einen relevanten Fehlerpfad betrachten.
- Keine Secrets in Code, Fixtures, Logs oder Abschlussberichten.
- Keine Deployments, Veröffentlichungen oder externen Nachrichten aus einem lokalen Coding-Auftrag.

## Bericht

`artifacts` enthält nur existierende relative Dateien im Workspace. `evidence` nennt den exakten
Befehl oder die direkte Inspektion und das Ergebnis. Nicht ausgeführte Checks, Annahmen und Blocker
gehören ausdrücklich in `next_actions` oder den Summary-Text.
