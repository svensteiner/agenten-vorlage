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

Der Original-Marketingbot bleibt unveraendert. Das eigens gestartete lokale
Cockpit auf Port 8766 ist fuer die Korrektur der Aenderungsnachweise gestoppt.

## Belegt und offen

| Bereich | Nachweis und Grenze |
|---|---|
| Reale Coding-Aufgabe | [Nativer Sol-Lauf](docs/evidence/host-observations-20261017/native-task-sol-attempt.json): erlaubte Quelle geaendert, zwei 79-Test-Laeufe, separates Review, unabhaengige Nachpruefung. Gilt fuer einen extrahierten Marketingbot-Baustein. |
| Echter Cockpit-Lauf | [UI-Profillauf](docs/evidence/execution-profiles-20261017/real-ui-profile-trial.json): 79 Tests und Review, aber keine eigene Quellaenderung. Modellberichte schreiben einen vorhandenen Diff falsch dem neuen Lauf zu. |
| Inhaltspruefung Haiku | [v7, alle zwoelf Faelle](docs/evidence/host-observations-20261017/semantic-v7-complete-accounting.json): vier akzeptiert, vier abgelehnt, vier Protokollfehler. Blindpruefung beanstandet zwei der vier akzeptierten Texte; ein weiterer bleibt mehrdeutig. Keine Freigabe. |
| Modell-Gegenprobe Sonnet | [v8, unvollstaendig](docs/evidence/host-observations-20261017/semantic-v8-model-partial.json): vier akzeptiert, ein Fehler, sieben ungeprueft. Zwei akzeptierte Texte nicht vollstaendig gestuetzt; drei Mehrdeutigkeitsbefunde ueberlappen diese Bewertungen. Kein frischer Holdout oder Qualitaetsgewinn belegt. |
| Letzter freigegebener Technikstand | Commit `80667ce`: 537 Tests bestanden, vier Skips, 20 Offline-Releasepruefungen bestanden; GitHub-Lauf `39007748612` erfolgreich. Deckt die aktuellen uncommitted Aenderungen nicht ab. |
| Aktuelle Korrektur | Host erfasst Ausgangshashes und abgeschlossene Schreibaktionen getrennt. Nicht zuordenbare Aenderungen und fehlende Nachweise bleiben explizit unbekannt; separate Anzeige in Auftrag und Dialog. Unabhaengige Reviews abgeschlossen; kombinierte technische Pruefung: 554 bestanden, vier Skips, 81 % Coverage mit Branch-Messung und 21 Offline-Releasepruefungen. [Quellhashes und Grenzen](docs/evidence/host-observations-20261017/provenance-technical-qualification.json). Echte Modell-Gegenproben stehen aus. |

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

1. Technische Pruefung bestanden; geprueften Stand sichern und GitHub-CI bestaetigen.
2. Herkunftsnachweise mit echtem Modell an vorhandenen und neuen Aenderungen pruefen.
3. Nutzbare, interessante und quellentreue Marketingausgaben unabhaengig nachweisen.
4. Vollstaendige isolierte Marketingbot-Integration testen; erst danach begrenzt uebernehmen.
