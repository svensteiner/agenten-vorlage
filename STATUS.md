---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-17"
---

# Agentenvorlagen: aktueller Stand

**Gesamtziel nicht abgenommen; keine Produktionsfreigabe.** Coding- und
Marketingagent sollen Ziele mit austauschbaren Skills planen, ausfuehren,
pruefen und nacharbeiten. Die Mietplattform ist zurueckgestellt.
Der laufende Original-Marketingbot bleibt unveraendert; Versuche verwenden
isolierte Kopien. Technische Tests ersetzen keine Inhaltsqualifikation.

## Technisch gepruefter Runtime-Stand

Die [hostseitige Ausgangskopie](docs/evidence/execution-profiles-20261017/retained-baseline-recovery.json)
und private pfadgebundene Ruecksetzung bestehen 702 Gesamttests mit neun Skips
und ohne Fehler; alle erfassten Quell-/Schemaeingaben blieben unveraendert.
38 Offline-Releasepruefungen, separates Review und Windows-Cache-/Legacy-
Resume-Gegenproben bestehen. Alle sieben Jobs der CI 39047216916 sind am
Runtime-Commit 902b809 gruen. Der [frische Coding-Auftrag V8](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v8-started.json)
ist beendet und nicht abgenommen: vier Schritte, zwei Fehler. RED bestand;
ein gezielter Testlauf hatte 242 bestandene und einen fehlgeschlagenen Test.
Nach Testnacharbeit war RED ungueltig. Der Planner stoppte, statt den
vorhandenen Ruecksetzungsweg und einen frischen RED-Lauf zu nutzen.
Volltest und separates Review fehlen. [Terminalnachweis](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v8-terminal.json).
Keine Produktionsfreigabe.

## Vorheriger gepruefter Runtime-Stand

Commit `f46a97b`: [private Reviewer-Schnittstelle](docs/evidence/execution-profiles-20261017/private-review-observations.json).

- 672 Gesamttests, sieben Skips, keine Fehler; erfasste Quell- und Schemaeingaben unveraendert.
- 80,45 % kombinierte Coverage: 83,21 % Statements, 73,55 % Branches.
- 37 Offline-Releasepruefungen bestanden; separates Code- und Vorbereitungsreview.
- Alle sieben Jobs der [CI 39043783201](https://github.com/svensteiner/agenten-vorlage/actions/runs/39043783201) erfolgreich.
- Vier neue Reviewer-Regressionen in allen vier Windows-/Linux-/Python-Kombinationen ausgefuehrt und bestanden.
- Echter Sol-Lesetest: zwei Modellaufrufe, eine Host-Dateibeobachtung, korrekter Bericht, keine Effektanfrage, Workspace unveraendert.

Die private Reviewer-Rolle kann nur Dateien/Git beobachten und berichten;
native Shell, Schreibaktionen und Testphasen bleiben gesperrt. Dieser
Lesetest belegt weder eine vollstaendige Coding-Aufgabe noch allgemeine
Review-Zuverlaessigkeit. [Privates Testprofil](docs/LOCAL-PHASE-TESTS.md).
Die anschliessende Recovery-Korrektur ist noch nicht abgenommen.

## Letzter echter Coding-Auftrag: V7 gescheitert

[V7](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v7-terminal.json)
endete nach fuenf Schritten und drei Fehlern ohne Abnahme. Der Agent schrieb
vier Regressionen; RED bestaetigte die vorgesehenen Assertion-Fehler.
Anschliessend aenderte er die Produktionsdatei. Die gezielten Tests scheiterten;
nach Testnacharbeit war RED veraltet und der Host lehnte auch die
Wiederherstellung des Produktions-Ausgangsstands ab. Volltest und finales
Review fehlen. Drei erlaubte Dateien geaendert, keine fremde Codehilfe,
keine Aenderung ausserhalb der erlaubten Pfade, keine Uebernahme.

Die aktuelle Arbeit behebt zwei konkrete Recovery-Luecken: eine eng
gebundene Wiederherstellung des exakten Produktions-Ausgangsinhalts und
begrenzte, unvertrauenswuerdige Testfehlerdiagnostik fuer das Modell.
V7 bleibt unveraendert; kein Replay oder nachtraegliches Erfolgslabel.
Der [erste Recovery-Kandidat](docs/evidence/execution-profiles-20261017/exact-baseline-recovery-v1-failed.json)
ist ebenfalls nicht abgenommen: 677 Tests, sieben Skips und zwei Fehler in
bestehenden Prompt-Wortlautpruefungen. Zudem fehlten exakte Ausgangsbytes in
spaeteren Worker-Aufrufen. Eine hostseitige, hashgepruefte Ausgangskopie und
eine private Ruecksetzungsaktion sind deshalb implementiert und lokal geprueft;
der frische Modellnachweis steht noch aus.

## Offene Abnahme des Gesamtziels

1. Vollstaendige Coding-Aufgabe ohne Operator-Codehilfe: eigene Aenderungen,
   gueltiges RED, frische gezielte und volle Tests sowie separates Review.
   Die Testkollektion muss die 4.729 urspruenglichen IDs und vier neue
   Regressionen erhalten; die Zahl allein reicht nicht.
2. Nutzbare, interessante und quellentreue Marketingtexte im echten
   Generierungsablauf nachweisen. Die bisherigen Qualitaetsversuche sind
   nicht freigegeben; Fehler und ungepruefte Faelle bleiben im Nenner.
3. Eine neue Qualitaetsmessung an den fertig geprueften Kandidaten binden.
   Die vorbereitete V16-Messung ist noch auf einen aelteren Kandidaten
   gebunden. Vier Faelle, maximal 64 physische Anfragen, lokale
   3-Dollar-Reservierung; kein Anbieter-Billinglimit und kein Best-of.
4. Vollstaendige isolierte Marketingbot-Integration und direkte Nutzung
   ueber den Coding-/Marketing-Einstieg pruefen, erst danach begrenzt uebernehmen.
   API-Auswahl und Skill-Komposition muessen dabei erhalten bleiben.

Kleine erfolgreich abgeschlossene Coding-Aufgaben und synthetische Tests
belegen keine unbeaufsichtigte Gesamtzuverlaessigkeit. Die
[Agentic-Abnahme](docs/AGENTIC-ACCEPTANCE.md) und
[Coding-Abnahme](docs/CODING-AGENT-ACCEPTANCE.md) halten Umfang und Grenzen fest.

## Verwendung

`Start-Coding-Agent.ps1 -Workspace <isolierter Checkout>` startet den
Coding-Einstieg. Optional bindet `-ExecutionProfiles <Hostregistry>` genaue
Schreibdateien und eine gepinnte Testsuite. Ohne Profil bleiben Einzelfreigaben
aktiv; Registry und Testimage werden nicht automatisch eingerichtet.
`Start-Marketing-Agent.ps1` oeffnet den Marketing-Einstieg, keine zweite
Bot-Instanz und keine Live-X-Aktion. [Start und Betriebsarten](README.md),
[hostgebundene Ausfuehrung](docs/ISOLATED-TEST-EXECUTION.md).

## Historische Nachweise

Der [vollstaendige fruehere Status](https://github.com/svensteiner/agenten-vorlage/blob/e554863/STATUS.md)
bleibt mit allen Zwischenstaenden erhalten. Einzelne fehlgeschlagene Laeufe:
[V4](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v4-terminal.json),
[V5](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v5-terminal.json),
[V6](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v6-terminal.json),
[V7](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v7-terminal.json).
Alle Rohbelege bleiben erhalten; fruehere Gruenstaende sind keine aktuelle
Produktionsfreigabe.
