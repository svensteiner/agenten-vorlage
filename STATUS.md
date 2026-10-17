---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-17"
---

# Agentenvorlagen: aktueller Stand

**Gesamtziel nicht nachgewiesen; keine Produktionsfreigabe.** Coding- und
Marketingagent sollen Ziele mit austauschbaren Skills planen, ausfuehren,
pruefen und nacharbeiten. Die Mietplattform ist zurueckgestellt.

Der Original-Marketingbot bleibt unveraendert. Isolierte Cockpit-Abnahmen
verwenden Port 8766; die Laufprotokolle belegen ihren jeweiligen Betriebsstand.

## Belegt und offen

| Bereich | Nachweis und Grenze |
|---|---|
| Reale Coding-Aufgabe | [Nativer Sol-Lauf](docs/evidence/host-observations-20261017/native-task-sol-attempt.json): erlaubte Quelle geaendert, zwei 79-Test-Laeufe, separates Review, unabhaengige Nachpruefung. Gilt fuer einen extrahierten Marketingbot-Baustein. |
| Echter Cockpit-Lauf | [UI-Profillauf](docs/evidence/execution-profiles-20261017/real-ui-profile-trial.json): 79 Tests und Review, aber keine eigene Quellaenderung. Modellberichte schreiben einen vorhandenen Diff falsch dem neuen Lauf zu. |
| Inhaltspruefung Haiku | [v7, alle zwoelf Faelle](docs/evidence/host-observations-20261017/semantic-v7-complete-accounting.json): vier akzeptiert, vier abgelehnt, vier Protokollfehler. Blindpruefung beanstandet zwei der vier akzeptierten Texte; ein weiterer bleibt mehrdeutig. Keine Freigabe. |
| Modell-Gegenprobe Sonnet | [v8, unvollstaendig](docs/evidence/host-observations-20261017/semantic-v8-model-partial.json): vier akzeptiert, ein Fehler, sieben ungeprueft. Zwei akzeptierte Texte nicht vollstaendig gestuetzt; drei Mehrdeutigkeitsbefunde ueberlappen diese Bewertungen. Kein frischer Holdout oder Qualitaetsgewinn belegt. |
| Letzter gepruefter Technikstand | Commit `2321d7b`: 561 Tests bestanden, vier Skips, 24 Offline-Releasepruefungen, 81 % Coverage mit Branch-Messung; alle sieben CI-Jobs im Lauf `39012516342` erfolgreich. Gilt nicht automatisch fuer spaetere Aenderungen. |
| Aenderungsnachweise | Host erfasst Ausgangshashes und abgeschlossene Schreibaktionen getrennt. Nicht zuordenbare Aenderungen und fehlende Nachweise bleiben explizit unbekannt; separate Anzeige in Auftrag und Dialog. Unabhaengige Reviews abgeschlossen; kombinierte technische Pruefung: 554 bestanden, vier Skips, 81 % Coverage mit Branch-Messung und 21 Offline-Releasepruefungen. [Quellhashes und Grenzen](docs/evidence/host-observations-20261017/provenance-technical-qualification.json). [Echte Gegenproben](docs/evidence/execution-profiles-20261017/paired-provenance-trial.json): A meldet korrekt null eigene Schreibaktionen; B hat drei eigene Schreibbelege, frische 79 Tests und Review. B benoetigte nach Zeitabbruch eine operatorgestuetzte Wiederaufnahme; kein unbeaufsichtigter Gesamterfolg. |
| Budgetsteuerung | Hostbudget und aktuelles Aufruflimit werden sichtbar; Vorbereitungskosten werden vor dem Dispatch abgezogen. Unabhaengig geprueft: 561 Tests bestanden, vier Skips, 81 % Coverage mit Branch-Messung, 24 Releasepruefungen. [Quellhashes und Grenzen](docs/evidence/host-observations-20261017/execution-budget-qualification.json). Alle sieben CI-Jobs erfolgreich. [Frischer Coding-Lauf](docs/evidence/execution-profiles-20261017/budget-unassisted-trial.json): vier Schritte, keine Fehler oder Operatorhilfe, 79 Tests und separates Review; unabhaengig nachgeprueft. Gilt nur fuer den begrenzten Bausteinauftrag. |

Richtige Ablehnung eines unbelegten Entwurfs ist von erfolgloser Reparatur zu
trennen. Fehler und ungepruefte Faelle bleiben im Nenner. Kleine synthetische
Stichproben und unterschiedliche Grader belegen keine allgemeine Zuverlaessigkeit.

Historische Fehlversuche bleiben in der [Agentic-Abnahme](docs/AGENTIC-ACCEPTANCE.md),
den verlinkten Nachweisen und dem
[vorherigen ausfuehrlichen Status](https://github.com/svensteiner/agenten-vorlage/blob/0f4f244/STATUS.md)
erhalten. Keine Promotion der gescheiterten Inhaltsvarianten in den laufenden Bot.

## Verwendung

Nach technischer Freigabe startet `Start-Coding-Agent.ps1 -Workspace <isolierter Checkout>`
den Coding-Einstieg. Optional bindet `-ExecutionProfiles <Hostregistry>` genaue
Schreibdateien und eine gepinnte Testsuite. Autonome Profile verlangen frische
Hosttests und ein separates Review; ohne Profil bleiben Einzelfreigaben aktiv.
Die Registry und das Testimage werden nicht automatisch eingerichtet.
[Hostgebundene Ausfuehrung](docs/ISOLATED-TEST-EXECUTION.md).

Das vorbereitete lokale Profil ist auf einen extrahierten Baustein beschraenkt.
Es ist weder eine vollstaendige Marketingbot-Integration noch eine X-Freigabe.

## Naechste verbindliche Abnahme

1. Vollstaendige frische Marketing-Baseline und deren Testumgebung abnehmen.
2. Zeichenlimit im echten Generierungspfad angleichen und neue Regressionen pruefen.
3. Nutzbare, interessante und quellentreue Marketingausgaben unabhaengig nachweisen.
4. Vollstaendige isolierte Marketingbot-Integration testen; erst danach begrenzt uebernehmen.
