---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-17"
---

# Agentenvorlagen: aktueller Stand

## Aktueller Nachweis: private Reviewer-Schnittstelle

Die [neue private Reviewer-Schnittstelle](docs/evidence/execution-profiles-20261017/private-review-observations.json) erlaubt ausschliesslich Host-Leseaktionen und Berichte; native Shell, Aenderungen und Testphasen bleiben fuer diese Rolle gesperrt. 672 Gesamttests bestehen mit sieben Skips, ohne Fehler und unveraenderten Quell-/Schemaeingaben. 37 Offline-Pruefungen, separates Review und ein echter Sol-Lesetest bestehen. Alle sieben Jobs der CI 39043783201 bestehen am Runtime-Commit f46a97b. Der [frische Coding-Auftrag V7](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v7-started.json) ist [ohne Abnahme beendet](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v7-terminal.json): RED bestanden, zwei Produktionsedits, gezielte Tests fehlgeschlagen. Nach Testnacharbeit sperrte der veraltete RED-Nachweis auch die Wiederherstellung des Produktions-Ausgangsstands. Fuenf Schritte, drei Fehler, keine fremde Codehilfe, keine Aenderung ausserhalb der drei erlaubten Dateien. Volltest und finales Review fehlen; keine Uebernahme. Keine Abnahme der Marketingqualitaet oder des Gesamtziels.

## Vorheriger Nachweis: V6 beendet (keine Abnahme)

Der echte Sol-Lauf V6 ist [blockiert beendet](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v6-terminal.json): vier Schritte, zwei begrenzte Leseabbrueche und zwei geaenderte Testdateien. Die erste Testphase wurde vor Ausfuehrung abgelehnt, weil die Vorbereitung den Launcher-Hash statt des Host-Runner-Hashs gebunden hatte. Der Runtime-Runner blieb unveraendert; seine Integritaetspruefung hat korrekt gestoppt. Keine Produktionsaenderung, kein frischer Volltest und keine Marketingqualifikation. Der Lauf bleibt unveraendert und wird nicht wiederholt.


**Gesamtziel nicht nachgewiesen; keine Produktionsfreigabe.** Coding- und
Marketingagent sollen Ziele mit austauschbaren Skills planen, ausfuehren,
pruefen und nacharbeiten. Die Mietplattform ist zurueckgestellt.

Der Original-Marketingbot bleibt unveraendert. Isolierte Cockpit-Abnahmen
verwenden Port 8766; die Laufprotokolle belegen ihren jeweiligen Betriebsstand.

Die [privaten lokalen Docker-Testphasen](docs/LOCAL-PHASE-TESTS.md) sind nur
operatorseitig ueber Python verfuegbar. Der aktuelle
[technische Stand](docs/evidence/execution-profiles-20261017/snapshot-link-safety.json)
besteht 656 Gesamttests mit sieben Skips, ohne Fehler und mit 80,37 %
kombinierter Coverage (83,15 % Statements, 73,45 % Branches) sowie 34
Offline-Releasepruefungen. Bekannte verfruehte Vorschlaege erhalten begrenzte
Korrekturbeobachtungen; unbekannte Ausgaenge bleiben gesperrt.

Ein separat validierter [Containerlauf](docs/evidence/execution-profiles-20261017/private-local-phase-technical.json)
erfasst 4.729 Testfaelle in 321 Dateien; alle 698 Host- und Scratch-Eingaben
blieben unveraendert, der Container wurde entfernt. Fruehere unbekannte
Diagnoselaeufe und fehlgeschlagene CI-Laeufe bleiben erhalten. Die Windows-CI
deckte einen echten Symlink-Fehler im gemeinsamen Datei-Leser sowie weitere
hostabhaengige Fixtures auf. Die Korrekturen sind unabhaengig und lokal
geprueft; alle sieben Jobs der CI 39038388607 sind gruen, einschliesslich
der ausgefuehrten Link-Regressionen unter Windows 3.11 und 3.12.
Der echte [Korrekturlauf V4](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v4-terminal.json)
ist dagegen nicht abgenommen: vier blockierte Luna-Schritte, keine
Host-Aktion, keine Dateiaenderung und keine Testphase. Die Worker suchten
Host-Aktionen als native Werkzeuge statt JSON-Vorschlaege zurueckzugeben.
Laufzeit, Quelldateien und Schreibgrenzen blieben unveraendert. Die
Werkzeugschnittstelle und Marketingqualitaet bleiben offen.

Die anschliessende [private Aktionsanweisung](docs/evidence/execution-profiles-20261017/private-action-interface.json)
nennt die Host-Aktionen explizit und enthaelt schema-gueltige Beispiele.
658 Gesamttests (sieben Skips, keine Fehler) und 35 Offline-Pruefungen
bestehen. Im echten, gegen Aenderungen gesperrten Lesetest scheitert Luna
weiterhin; Sol liest die Datei ueber den Host und berichtet korrekt.
Das qualifiziert nur die Leseaktion. Der naechste vollstaendige Korrekturlauf
V5 ist vorbereitet, noch nicht gestartet. CI 39039620098 scheiterte unter
Windows 3.12: Ein oeffentlicher Job konnte seinen Checkpoint wegen
WinError 5 nicht atomar ersetzen. Der Quota-Writer umgeht bisher die
bereits vorhandene begrenzte Windows-Wiederholung des Standard-Checkpoints.
Die [Speicherkorrektur](docs/evidence/execution-profiles-20261017/quota-checkpoint-sharing.json)
verwendet die vorhandene begrenzte Windows-Wiederholung auch im Quota-Writer.
662 Windows-Gesamttests (sieben Skips, keine Fehler), ein echter Windows-
Handle-Test und 35 Offline-Pruefungen bestehen. Eine nachtraegliche reine
Testkorrektur verhindert globale Betriebssystemsimulation; die elf Quotentests
bestehen danach unter Windows und Linux. Alle sieben Jobs der finalen
CI 39040477529 sind gruen; beide Quotentests liefen in allen vier
Betriebssystem-/Python-Kombinationen erfolgreich.
Der [frische Sol-Lauf V5](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v5-started.json)
ist [ohne Abnahme beendet](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v5-terminal.json):
eine belegte Testaenderung, danach Kontextlimit beim Lesen, keine Testphase
und keine Produktionsaenderung. Der Worker bleibt in_flight gespeichert;
der Lauf wird nicht wiederholt. Eine vorangehende reine Startpruefung hatte eine falsche
Snapshot-Kennung vor jedem Modellaufruf abgelehnt. Die korrigierte Bindung
und die zusaetzliche Vorpruefung bestehen 20 Guard-Tests und separates Review.
Die eigentliche Codekorrektur und Marketingqualitaet sind noch nicht abgenommen.
Die [Folgekorrektur](docs/evidence/execution-profiles-20261017/observation-budget-recovery.json)
gibt bekannte reine Lesebudget-Stopps als Host-Nacharbeit
an den Planer zurueck. Limits und Sperren fuer unklare Ausgaenge bleiben
unveraendert. Beide betroffenen Testmodule bestehen unabhaengig mit 100 Tests;
668 Gesamttests (sieben Skips, keine Fehler), 36 Offline-Pruefungen und alle
sieben Jobs der CI 39041971315 sind bestanden. Der neue
[Sol-Auftrag V6](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-v6-started.json)
ist mit frischem Originalsnapshot und 20 Guard-Tests gestartet. Seine
eigentliche autonome Codekorrektur ist noch nicht abgenommen.

Der neue [native RSS-Auftrag](docs/evidence/execution-profiles-20261017/marketing-native-rss-terminal.json)
ist mit eigenstaendiger Review-Nacharbeit abgeschlossen: 231 gezielte und
4.702 vollstaendige Tests bestanden. Die unabhaengige Nachpruefung findet
keinen Codeblocker und bestaetigt die finalen Quell-/Testhashes. Die autonome
Wiederanlaufabnahme bleibt unvollstaendig: Vor dem zweiten Gesamttest ist
keine Prozessbereinigungspruefung fuer den zuvor unbekannten Timeout belegt.
Der spaetere erfolgreiche Test ersetzt diesen unbekannten Ausgang nicht.

Der [versionierte Quellenbeleg-Adapter](docs/SOURCE-EVIDENCE-V2.md) wurde im
[isolierten Coding-Lauf](docs/evidence/execution-profiles-20261017/marketing-evidence-native-v2-terminal.json)
implementiert, aber nicht abgenommen. Der Lauf stoppte nach zwei Schritten am
CLI-Ausgabelimit; der ausstehende Worker-Ausgang bleibt unbekannt und wird
nicht automatisch wiederholt. Der abgeschlossene Gesamttest meldete 4.714
Erfolge, einen Fehler, elf Skips und fuenf erwartete Fehlschlaege. Eine danach
geaenderte Test-Fixture ist noch ungeprueft. Unabhaengig bestaetigt sind zwei
Codeblocker: nicht fortlaufende Beleg-IDs bei Quellen ueber 512 Zeichen und
von Anthropic nicht unterstuetzte Array-Grenzen im rohen Transportschema.
Der separate [AgentKit-Fix fuer Codex-Fortschrittsausgaben](docs/evidence/execution-profiles-20261017/codex-console-capture-technical.json)
ist offline und unabhaengig geprueft: 570 Gesamttests ausgefuehrt, vier
uebersprungen, keine Fehler; 31 Releasepruefungen bestanden. Strukturierte
Ergebnisdateien und allgemeine Prozessausgaben bleiben begrenzt. Das
qualifiziert weder den gestoppten Worker nachtraeglich noch echte Modelllaeufe.
Numerische Beleg-IDs ersetzen kopierte Zitate, beweisen aber keine semantisch
richtige Belegwahl. Keine Implementierungs-, Inhalts- oder Produktionsfreigabe.

Der [frische Korrekturauftrag](docs/evidence/execution-profiles-20261017/marketing-evidence-correction-terminal.json)
stoppte nach dem ersten Entwickleraufruf an der Artefaktpruefung des Berichts.
Nur zwei Testdateien wurden geaendert, kein Produktionscode. Vier neue Tests
schlugen fehl; drei ValueError-Ausgaenge erfuellten den geforderten Assertion-
RED-Nachweis nicht. Runtime, Launcher und Paket blieben unveraendert. Der
Bericht wurde vor seiner Speicherung abgelehnt; der Checkpoint bleibt
unbekannt und wird nicht wiederholt. Der [eng begrenzte Berichtspfad](docs/evidence/execution-profiles-20261017/completed-report-rejection-technical.json)
ist nun offline und unabhaengig geprueft: 29 gezielte Tests, 584 Gesamttests
mit vier Skips und ohne Fehler sowie 32 Releasepruefungen. Die getrennt
gepruefte Workflow-Anzeige besteht 13 gezaehlte Szenarien. Nur ein normal
zurueckgegebener, abgelehnter Codex-Bericht wird zur Planerbeobachtung; unsichere
Backend-Ausgaenge bleiben gesperrt. Die neue Runtime muss sich im naechsten
echten Coding-Lauf noch bewaehren.

Die [frische RSS-Abnahme](docs/evidence/execution-profiles-20261017/marketing-rss-v16-prospective.json)
ist unabhaengig auf Quellen und sichtbare Goldlabels geprueft, aber noch ohne
Modelllauf. Die [Reparaturdiagnose](docs/evidence/execution-profiles-20261017/marketing-v16-diagnostic-tooling.json)
besteht 67 Offline-Tests; ihre Integration mit dem neuen v2-Kandidaten ist
noch offen. Die [separate v2-Diagnose](docs/evidence/execution-profiles-20261017/marketing-v16-evidence-v2-tooling.json)
besteht 70 Offline-Tests und ein unabhaengiges Review. Sie reicht das tatsaechliche
Anfrageschema unveraendert weiter. Kurze Quellen durchlaufen den simulierten
zweistufigen HTTP-Pfad; lange Quellen zeigen noch den bekannten Kandidatenfehler.
Der korrigierte Kandidat und echte Modellqualitaet sind damit nicht abgenommen.
Die Diagnose veraendert keine Modellantwort oder Freigabe.

## Belegt und offen

| Bereich | Nachweis und Grenze |
|---|---|
| Kleineres Coding-Modell | [Nativer Luna-Versuch](docs/evidence/execution-profiles-20261017/native-retry-luna-rejected.json): selbststaendige Aenderung in drei Dateien, 176 gezielte und 4.649 vollstaendige Tests bestanden. Engine meldet Abschluss nach separatem Review; unabhaengige Nachpruefung verwirft die Abnahme wegen veraenderter Standardbereinigung und ersetzter Inhaltspruefer im Integrationstest. 693 andere Baseline-Dateien unveraendert; neue Laufzeit-/Testartefakte verhindern eine vollstaendig unveraenderte Workspace-Abnahme. Korrekturauftrag erforderlich. |
| Vollstaendiger Marketingablauf | [v9, gestoppt](docs/evidence/execution-profiles-20261017/marketing-fullpath-v9-stopped.json): null von vier Faellen vollstaendig akzeptiert; sieben abgeschlossene API-Anfragen, zwei Faelle ungeprueft. Ein Fall erschoepft die Generierung mit ueberlangen Entwuerfen; ein weiterer erreicht die Quellenfreigabe, aber keine abgeschlossene Inhaltsaudit-Anfrage. Offline reproduziert: nicht isolierter optionaler TypeSafe-Zugang trifft auf die feste OpenRouter-Endpunktgrenze und stoppt den Testtransport. 18 Offline-Pruefungen bestanden; kein Nachweis echter Ausgabequalitaet. |
| Reale Coding-Aufgabe | [Nativer Sol-Lauf](docs/evidence/host-observations-20261017/native-task-sol-attempt.json): erlaubte Quelle geaendert, zwei 79-Test-Laeufe, separates Review, unabhaengige Nachpruefung. Gilt fuer einen extrahierten Marketingbot-Baustein. |
| Vollstaendiger Coding-Auftrag | [Isolierter Fullprojekt-Lauf](docs/evidence/execution-profiles-20261017/native-full-project-assisted-trial.json): acht Schritte, eigene Implementierung und Review-Nacharbeit; 172 gezielte und 4.645 vollstaendige Tests. Separater Host-Gesamttest und unabhaengiger Hash-Audit bestaetigt. Wegen Teststarter-Reparatur und expliziter Wiederaufnahme insgesamt unterstuetzt; keine unbeaufsichtigte Gesamtabnahme. |
| Echter Cockpit-Lauf | [UI-Profillauf](docs/evidence/execution-profiles-20261017/real-ui-profile-trial.json): 79 Tests und Review, aber keine eigene Quellaenderung. Modellberichte schreiben einen vorhandenen Diff falsch dem neuen Lauf zu. |
| Inhaltspruefung Haiku | [v7, alle zwoelf Faelle](docs/evidence/host-observations-20261017/semantic-v7-complete-accounting.json): vier akzeptiert, vier abgelehnt, vier Protokollfehler. Blindpruefung beanstandet zwei der vier akzeptierten Texte; ein weiterer bleibt mehrdeutig. Keine Freigabe. |
| Modell-Gegenprobe Sonnet | [v8, unvollstaendig](docs/evidence/host-observations-20261017/semantic-v8-model-partial.json): vier akzeptiert, ein Fehler, sieben ungeprueft. Zwei akzeptierte Texte nicht vollstaendig gestuetzt; drei Mehrdeutigkeitsbefunde ueberlappen diese Bewertungen. Kein frischer Holdout oder Qualitaetsgewinn belegt. |
| Letzter separat gepruefter Technikstand | Commit `3a208bd`: 584 Gesamttests ausgefuehrt, vier Skips, keine Fehler; 32 Offline-Releasepruefungen. [GitHub-CI `39032010923`](https://github.com/svensteiner/agenten-vorlage/actions/runs/39032010923) vollstaendig erfolgreich. [Abgeschlossene, abgelehnte Codex-Berichte](docs/evidence/execution-profiles-20261017/completed-report-rejection-technical.json) werden als Beobachtung fuer die Neuplanung erfasst. Kein Nachweis eines echten autonomen Gesamterfolgs. |
| Aenderungsnachweise | Host erfasst Ausgangshashes und abgeschlossene Schreibaktionen getrennt. Nicht zuordenbare Aenderungen und fehlende Nachweise bleiben explizit unbekannt; separate Anzeige in Auftrag und Dialog. Unabhaengige Reviews abgeschlossen; kombinierte technische Pruefung: 554 bestanden, vier Skips, 81 % Coverage mit Branch-Messung und 21 Offline-Releasepruefungen. [Quellhashes und Grenzen](docs/evidence/host-observations-20261017/provenance-technical-qualification.json). [Echte Gegenproben](docs/evidence/execution-profiles-20261017/paired-provenance-trial.json): A meldet korrekt null eigene Schreibaktionen; B hat drei eigene Schreibbelege, frische 79 Tests und Review. B benoetigte nach Zeitabbruch eine operatorgestuetzte Wiederaufnahme; kein unbeaufsichtigter Gesamterfolg. |
| Budgetsteuerung | Hostbudget und aktuelles Aufruflimit werden sichtbar; Vorbereitungskosten werden vor dem Dispatch abgezogen. Unabhaengig geprueft: 561 Tests bestanden, vier Skips, 81 % Coverage mit Branch-Messung, 24 Releasepruefungen. [Quellhashes und Grenzen](docs/evidence/host-observations-20261017/execution-budget-qualification.json). Alle sieben CI-Jobs erfolgreich. [Frischer Coding-Lauf](docs/evidence/execution-profiles-20261017/budget-unassisted-trial.json): vier Schritte, keine Fehler oder Operatorhilfe, 79 Tests und separates Review; unabhaengig nachgeprueft. Gilt nur fuer den begrenzten Bausteinauftrag. |

Richtige Ablehnung eines unbelegten Entwurfs ist von erfolgloser Reparatur zu
trennen. Fehler und ungepruefte Faelle bleiben im Nenner. Kleine synthetische
Stichproben und unterschiedliche Grader belegen keine allgemeine Zuverlaessigkeit.

Historische Fehlversuche bleiben in der [Agentic-Abnahme](docs/AGENTIC-ACCEPTANCE.md),
den verlinkten Nachweisen und dem
[vorherigen ausfuehrlichen Status](https://github.com/svensteiner/agenten-vorlage/blob/0f4f244/STATUS.md)
erhalten. Keine Promotion der gescheiterten Inhaltsvarianten in den laufenden Bot.

## Laufende Verbesserung der News-Generierung

Der isolierte Stilauftrag verwendet Luna fuer Umsetzung und Sol fuer Review/Nacharbeit.
Der erste Aenderungsstand bestand 4.661 Tests (elf Skips, fuenf erwartete
Fehlschlaege), ist aber nicht abgenommen: Ein unabhaengiges Review beanstandet,
dass die widerspruechlichen Original-Tonbefehle weiterhin im Prompt stehen und
die neuen Tests nicht die echten zehn Tonvorgaben pruefen. Der [native Auftrag](docs/evidence/execution-profiles-20261017/native-style-trial-rejected.json)
ist inzwischen mit Engine-Abschluss und internem Review beendet. Die unabhaengige
Endpruefung lehnt auch den finalen Stand ab: Die Legacy-Befehle bleiben erhalten,
und der Test erwartet ihr Verbleiben sogar ausdruecklich. Finale Gesamtsuite:
4.661 bestanden; 693 andere Baseline-Dateien und 84 Ausfuehrungspins unveraendert.
Keine Uebernahme dieser Variante. Eine getrennte Korrektur ersetzt inzwischen
die Tonvorgaben tatsaechlich und prueft alle zehn echten Presets; 197 gezielte
Tests und unabhaengiges Review bestanden. Ihr [Gesamttest](docs/evidence/execution-profiles-20261017/source-grounded-style-correction.json)
ist jetzt gruen: 4.670 bestanden, elf Skips und fuenf erwartete Fehlschlaege.
Der [reviewbare Patch](docs/evidence/execution-profiles-20261017/source-grounded-style.patch)
ist auf die fruehere isolierte Kandidatenbasis bezogen; keine Produktionsuebernahme.
Die nachgelagerte [Acht-Faelle-Pruefung](docs/evidence/execution-profiles-20261017/marketing-two-cohort-v12-terminal.json)
ist ebenfalls beendet und gescheitert: null von acht Endtexten bei 39 abgeschlossenen
Anfragen und 0,062597 USD, keine unbekannten Kosten oder Anfrageausgaenge.
Vier Faelle bestehen die Quellenqualifikation, erhalten vom Auditor AVERAGE
mit Vague/No-hook/Generic und werden vom Gatekeeper abgelehnt. Vier weitere
Faelle erreichen diese Stufe nicht. Beide Gruppen bleiben im Nenner: vier
synthetische KI-Randfaelle und vier datierte Primaerquellen-News. Keine
Produktionsfreigabe; als Naechstes ist die sichere Nacharbeit nach dem
Qualitaetsfeedback zu untersuchen, ohne Pruefschwellen abzusenken.

Die getrennte [v12-Diagnose](docs/evidence/execution-profiles-20261017/marketing-fullpath-v12-offline.json)
besteht 21 Offline-Tests und ein unabhaengiges Review. Sie fixiert Ergebnisdateipfade
vor temporaeren Verzeichniswechseln und zeichnet ausschliesslich feste Kategorien
der tatsaechlichen Auditor-/Gatekeeper-Rueckgaben auf. Kein Modelllauf und kein
Nachweis besserer Inhalte. Rohantworten werden dafuer nicht gespeichert.

Die [Quellenumfang-Pruefung](docs/evidence/execution-profiles-20261017/marketing-source-input-scope.json)
zeigt eine weitere Abnahmegrenze: RSS liefert hoechstens 280 Zeichen aus Titel
und Zusammenfassung und ruft keinen verlinkten Artikel ab. Der lokale
Artikel-Extraktor erzeugt Beobachtungen von hoechstens 200 Zeichen. Die
vorbereiteten v13-Laborfaelle mit 719 bis 928 Zeichen sind daher kein
repraesentativer Nachweis fuer den produktiven RSS-Pfad. Dessen Nutzen muss
mit frischen, tatsaechlich extrahierten Kurzquellen separat nachgewiesen werden.

Die isolierte [Qualitaetsnacharbeit](docs/evidence/execution-profiles-20261017/marketing-quality-revision-technical.json)
besteht jetzt den Gesamttest: 4.698 bestanden, elf Skips, fuenf erwartete
Fehlschlaege. Maximal eine Revision darf nach expliziter abgeschlossener
Qualitaetsablehnung erneut Quellen- und Inhaltspruefungen durchlaufen;
Quellenablehnung oder unbekannte Ergebnisse erlauben keine Wiederholung.
Der [Patch](docs/evidence/execution-profiles-20261017/marketing-quality-revision.patch)
ist reviewbar, aber noch nicht produktiv integriert. Echter Inhaltsnutzen
und der neue Testadapter sind weiterhin nicht abgenommen.

Die frische [RSS-Modellabnahme](docs/evidence/execution-profiles-20261017/marketing-rss-v14-terminal.json)
endet mit null von vier freigegebenen Endtexten: 15 abgeschlossene Anfragen,
0,023430 USD, keine unbekannten Anfrageausgaenge oder Kosten. Ein Fall
erschoepft die Generierung, drei stoppen an der Quellenqualifikation. Kein
Fall erreicht Auditor oder Gatekeeper; die Qualitaetsrevision ist damit im
echten Modelllauf weiterhin nicht belegt. Der [v13-Testadapter](docs/evidence/execution-profiles-20261017/marketing-fullpath-v13-offline.json)
besteht nach verschaerfter Rundenzuordnung 42 Offline-Tests und separates Review.
Die RSS-Eingaben entsprechen exakt dem vorhandenen Extraktor, einschliesslich
des separat festgestellten Zeichencodierungsfehlers. Keine Produktionsfreigabe.

Der separat [korrigierte RSS-Fetcher](docs/evidence/execution-profiles-20261017/marketing-rss-encoding-qualification.json)
erhaelt XML-Bytes und damit deklarierte Zeichencodierung/BOM. Acht neue
Regressionen, 15 gezielte Tests, unabhaengiges Review und der Gesamttest
mit 4.706 bestandenen Tests sind gruen. Die gespeicherte Golem-Gegenprobe
enthaelt keine Ersatzzeichen mehr. Der [Patch](docs/evidence/execution-profiles-20261017/marketing-rss-encoding.patch)
ist eine operatorseitige Korrektur in separater Kopie, keine autonome
Coding-Abnahme und keine produktive Umstellung.

Die neue [v15-Laborabnahme](docs/evidence/execution-profiles-20261017/marketing-rich-v15-terminal.json)
endet ebenfalls mit null von vier Endtexten: 13 abgeschlossene Anfragen,
0,024316 USD und keine unbekannten Ausgaenge/Kosten. Der unabhaengig gepruefte
Diagnoseadapter besteht 54 Offline-Tests und erfasst einen konkreten
`quote_mismatch`: Das Modellzitat kommt nicht exakt in der Beobachtung vor.
Zwei Faelle stoppen mit `repair_failed`, einer erschoepft die Generierung;
kein Fall erreicht Auditor/Gatekeeper. Die vier erstmalig getesteten reichen
Quellen sind Laborfaelle ausserhalb des RSS-Zeichenlimits. Auch dieser
Fehlschlag bleibt erhalten; keine Verbesserung oder Produktionsreife belegt.

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

1. Frische Marketing-Baseline liegt vor: 4.641 bestanden, elf Skips, fuenf erwartete Fehlschlaege; 321 Unit-Testdateien. [Nachweis und Browsergrenzen](docs/evidence/execution-profiles-20261017/marketing-full-baseline.json). Native Fullprojekt-Testumgebung ebenfalls abgenommen; synthetische Konfiguration und Browseradapter bleiben Einschraenkungen.
2. Zeichenlimit im isolierten echten Generierungspfad abgenommen: 4.645 Tests und separates Review; Uebernahme in aktuellen Upstream noch offen.
3. Nutzbare, interessante und quellentreue Marketingausgaben unabhaengig nachweisen.
4. Vollstaendige isolierte Marketingbot-Integration testen; erst danach begrenzt uebernehmen.

Der TypeSafe-Isolationsfehler des v9-Teststarters ist in einer getrennten
v10-Version korrigiert und unabhaengig geprueft: 18 Offline-Tests bestanden,
einschliesslich echtem Komponentenablauf mit synthetischem Zusatzschluessel.
Der anschliessende v10-Modellversuch akzeptierte null von vier Faellen bei
20 abgeschlossenen Anfragen (0,032612 USD). Die Messung ist jedoch verfälscht:
Der Testadapter entfernte Routing-Marker, die zugleich widerspruechliche
Tweet-Anweisungen in Inhaltspruefungen verhindern. Deshalb ist v10 kein
belastbarer alleiniger Nachweis der Produktqualitaet.

Eine getrennte [v11-Korrektur](docs/evidence/execution-profiles-20261017/marketing-fullpath-v11-adapter-correction.json)
erhaelt diese Marker beim Promptbau und aendert nur den nachfolgenden
Anbieterdispatch. 18 Offline-Tests bestanden, einschliesslich echter
Komponenten mit synthetischem HTTP und Pruefung der Audit-/Gate-Nachrichten.
Unabhaengiges Review ohne Blocker abgeschlossen, inklusive Ausnahmefall bei Dispatch.
Der frische [v11-Modelllauf](docs/evidence/execution-profiles-20261017/marketing-fullpath-v11-terminal.json)
ist beendet: null von vier vollstaendigen Ergebnissen, 23 abgeschlossene Anfragen,
0,037289 USD, keine unbekannten Kosten oder Anfrageausgaenge. Drei Faelle
bestehen die Quellenqualifikation, scheitern aber am weiteren Qualitaetsablauf;
ein Fall endet mit Quellenprotokollfehler. Keine Endtexte zur Blindbewertung.
Produktverbesserung und erneute frische Abnahme bleiben erforderlich. Keine Produktionsfreigabe.
