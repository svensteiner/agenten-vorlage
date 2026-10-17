# Abnahme der Agentenvorlagen

Ziel: Die Agenten sollen einen Auftrag mit passenden Skills selbst planen,
ausführen, prüfen und bei behebbaren Fehlern nacharbeiten. Die Bewertung gilt
für die direkte eigene Nutzung von Coding- und Marketingagenten; die spätere
Mietplattform ist ein eigener Auftrag. Eine Prozentzahl allein beweist diese
Fähigkeiten nicht. Der Gesamtabschluss ist noch nicht nachgewiesen.

| Anforderung | Nachweis / verbleibende Lücke |
|---|---|
| Austauschbare Rollen, Skills und Firmenbindung | Generierte Pakete und Katalogprüfungen im Release-Gate; keine ausführbaren Skill-Plugins |
| Wahl des nächsten Schritts aus Beobachtungen | Engine und Backend-Vertrag; Offline-Demo ist lediglich eine Fixture |
| Werkzeuge tatsächlich ausführen | Host-Executor und API-Adapter; Live-Nachweis muss Modell, Aufgabe und Lauf identifizieren |
| Nach einem verfrühten Abschluss selbst nacharbeiten | Neue Engine-Tests: fehlende Evidenz nachholen, unabhängiges Review nachholen, wiederholte Ablehnung begrenzen |
| Änderungen unabhängig prüfen | Review-Gate; jede mögliche Änderung entwertet das frühere Review |
| Keine unbekannten Seiteneffekte wiederholen | Persistiertes `in_flight`, Bindung und bewusste Wiederaufnahme; bestehende Resume-Tests bleiben verbindlich |
| Anbieter wechseln und Ressourcen begrenzen | Explizite API-/Codex-Adapter, Zeit-, Schritt- und Fehlerbudgets; Provider-Fixtures sind keine Live-Abnahme |
| Ziele vollständig erfüllen statt nur Erfolg melden | Belegter Abschlussbericht und Review sind Mindestbedingungen; fachliche Abnahmekriterien müssen zusätzlich am tatsächlichen Ergebnis geprüft werden |
| Einen realen Coding-Auftrag unbeaufsichtigt erledigen | Kleine bisherige Live-Fixtures reichen nicht für beliebige Projekte; repräsentative Projektaufgaben und Regressionstests fehlen als umfassender Nachweis |
| Marketinginhalte belastbar verbessern | Die bisherige Blindabnahme ist gescheitert; echte neue Ausgabequalität und unveränderte Veröffentlichungsschutzmechanismen müssen noch nachgewiesen werden |
| Mit einem anderen Skill eine andere Fachrolle ausüben | Paketkomposition vorhanden; erfolgreiche Coding-Aufgaben belegen keine steuerliche oder andere fachliche Richtigkeit |

## Nachweise vom 17.10.2026

Ein frischer, operatorseitig vorbereiteter Coding-Lauf mit Budgetkontext schloss
einen begrenzten Bausteinauftrag ohne Zwischenhilfe ab: vier Schritte, keine
Fehler, drei Schreibbelege, 79 frische Tests und separates Review. Geschuetzte
Dateien, Paket und Runtime blieben unveraendert. Das ist ein Einzelnachweis,
keine Vollprojekt- oder Qualitaetsfreigabe. [Hashgebundener Lauf](evidence/execution-profiles-20261017/budget-unassisted-trial.json).

### Prompt-/Persona-Integration: native Reparatur belegt, Ergebnisqualitaet offen

`fa3edbfab7b94739b8c5c94d9d58b497` endete nach eigener Nachbesserung mit Review,
aber sieben spaetere Host-Gegenproben widerlegten die technische Abnahme.
Ein getrennter Folgeauftrag nutzte diese Gegenbeispiele; nach eigener Unicode-
Nachbesserung und frischer Review bestaetigte der Host 99 gezielte Tests.
Die volle Regression bestand im echten Git-Worktree mit 4.485 Tests. Die folgende
echte Modellabnahme scheiterte: beide Varianten 0/6 nutzbare Posts, 36 Antworten
am Markdown-Bold-Filter verworfen; Kosten 0,044962 USD. Keine Uebernahme.
[Kompletter gescheiterter Vergleich](evidence/source-draft-quality-20261017/README.md). Keine Host-Codehilfe innerhalb der
Laeufe; der Folgeauftrag ist wegen seiner Host-Gegenbeispiele assistiert markiert.
[Rohbelege und eingefrorene Quell-/Testsnapshots](evidence/source-draft-coding-20261017/README.md).

### Formatkorrektur: nativer Reparaturlauf, weitere Review-Luecken offen

Der native Lauf `c9a5a44b102c454a8c0917d8135cee3d` bestand nach eigener
Testnachweis-Nacharbeit und frischer unabhaengiger Review. Der Host bestaetigt
105 gezielte Tests mit 96,23% Generatorabdeckung; 790 geschuetzte Eingaben
unveraendert, keine Host-Codehilfe innerhalb des Laufs. Weitere Review findet
unpassendes generisches Feedback bei semantischen Ablehnungen und fehlende
Fehlerzaehlung bei verworfenen Formatantworten. Der getrennte Folgeauftrag endete wegen nicht ausreichend sichtbarer Pruefbelege
ohne finale Review. Hostpruefungen bestaetigen 110 Tests und geschuetzte Eingaben;
eine anschliessende, explizite Hostkorrektur der Sprachregel besteht 109 Tests.
Die unterschiedlichen Testumfaenge sind [getrennt dokumentiert](evidence/source-draft-feedback-20261017/README.md).
Keine Promotion. Der abschliessende echte Git-Worktree besteht 4.495 Tests;
der folgende Modelltest liefert sechs technisch akzeptierte Entwuerfe, scheitert
aber an Laenge und unbelegten fachlichen Aussagen. Die getrennte Nachpruefung senkt den
Notenmittelwert von0,75 auf0,4167/5; fuenf harte Fehlerbefunde bleiben.
[Erstnoten, Pruefung und Korrekturen](evidence/source-draft-repair-screen-20261017/README.md). Keine Qualitaetsfreigabe.
[Unveraenderte Lauf-/Quell-/Testbelege](evidence/source-draft-format-20261017/README.md).

### Reale Quellenbindung: integriert, autonomer Coding-Auftrag nicht bestanden

Marketingbot-Commit `3ccb2e7e` auf `master` erhaelt den ausgewaehlten
ObservationBank-Datensatz bis zu Publikations- und Lernmetadaten. Die Quelle
bleibt ausdruecklich unverifiziert; Hashes pruefen Konsistenz und Textbindung,
nicht Wahrheit oder Freigabe. Keine zusaetzlichen Modellaufrufe und keine
Aenderungen an Kontosperren, Versand, Budgets oder Ergebnisberechtigung.

Der echte Coding-Lauf `b666a676170b4ff9acca97334f589bc3` endete nach drei
Revisionen ohne finales Review. Der Reviewer fand eine flache Kopie; das
staerkere Reparaturmodell behob sie. Danach blieb ein Windows-Langpfadfehler
im Testlauf. Unabhaengige Hostpruefungen fanden drei weitere Regressionen:
fehlende Scrape-Rueckgabe, zweiten Draw nach Record-API-Fehler und fehlenden
Typimport. Drei neue Tests scheiterten vor den getrennten Hostkorrekturen;
danach bestanden 99 gezielte Tests und separate Python-/Security-Reviews.
879 geschuetzte Quelldateien und eingefrorene Tests blieben unveraendert.
Der autonome Auftrag gilt weiterhin als nicht bestanden.

Der folgende volle Marketingbot-Testlauf meldete 4.451 bestanden und neun
Fehler: acht schon in der Baseline plus einen intermittierenden
Mehrprozess-Kontosperrentest. Fuer die acht Baselinefehler wurden veraltete
Gatekeeper-/DOM-Testobjekte, eine alte Source-Assertion und eine durch Commit
`a72fb508` ueberholte Mengenpolicy nachgewiesen. Nur Tests wurden angepasst;
67 gezielte Tests bestanden. Der folgende volle Vergleich bestand mit 4.460
Tests, elf Skips und fuenf erwarteten Fehlern (279,07 Sekunden). Testkorrekturen
sind unter `4e6125a4` auf Marketingbot/master. Der Mehrprozess-Test bestand zwar
15/15 Wiederholungen, doch eine gezielte Windows-Gegenprobe belegte danach eine
Race: Ein Initialisierungsschreiben vor dem Byte-Lock trifft die bereits gesperrte,
temporaer leere Datei und erhaelt PermissionError. Der neue separate Prozess-
Regressionstest war zuerst rot; nach minimalem Entfernen des ungeschuetzten
Schreibens bestehen 119 gezielte Tests. Python-/Security-Review ohne Blocker;
abschliessender voller Lauf bestanden: 4.461 Tests, elf Skips, fuenf erwartete
Fehler, 277,69 Sekunden. Fix/Regression auf Marketingbot/master unter `db358c51`.
Keine Produktionsfreigabe und kein Nachweis allgemeiner Agentic-Zuverlaessigkeit.

Die normale Entwurfsqualitaet und ein unbeaufsichtigt bestandener realer
Projektauftrag bleiben erforderlich. Die laufende Originalinstallation wurde
nicht umgestellt oder neu gestartet.

### Source-first: echter autonomer Review-/Reparaturablauf, Qualitaetsgate noch offen

Der erste native Versuch `7e8c31a6315547d4a794589fcf88a8ce` stoppte nach einem
Schreibschritt an einer Windows-Pfadberechtigung. Sein unbekannter `in_flight`-
Ausgang wurde nicht automatisch wiederholt. Die generische Artefaktpruefung und
der Download verwenden bei echten Codex-Zugriffsfehlern jetzt dieselbe kanonische
Pfadpolicy im offiziellen read-only, netzwerkfreien Sandboxkonto. Kein ACL-Bypass.
Der echte Export der ersten Batchdatei lieferte 1.958 gepruefte Bytes.
432 Tests, drei erwartete Skips, keine Fehler; 20 Offline-Gates, Ruff und
unabhaengige Python-/Security-Reviews bestanden am abschliessenden Stand.

Ein frischer zweiter Workspace mit leerer vorab angelegter Ausgabedatei pruefte
das echte X-Agentenpaket: neun feste Faelle und drei neue synthetische Quellen.
`a66058b400bb4abeb6b4576bc84331c2` erreichte ohne Host-Reparaturhilfe in zehn
Schritten den Abschluss. Vier guenstige Entwurfsbatches, ablehnendes separates
Review, guenstige Reparatur, erneute Ablehnung, automatische staerkere Reparatur
nach zwei Revisionen und abschliessendes Review. Quellen und Agentenpaket blieben
unveraendert; die Hostpruefung bestaetigte alle zwoelf Identitaeten, striktes JSON,
maximal 190 Zeichen, unterschiedliche Texte und exakte Quellenzitate.
Die Aktionsfreigaben waren nur in diesem isolierten Experiment deaktiviert.
Das belegt den konkreten autonomen Ablauf, keine allgemeine Erfolgsquote.

Ein unabhaengiger Grader sah ausschliesslich 18 zufaellig angeordnete A/B-Paare
und drei Einzeltexte. Die Zuordnung blieb bis zur Auswertung getrennt.
Ein zweiter Pruefer rechnete spaeter die Auswertung und SHA-Verknuepfungen nach:

| Vergleich | Neue Texte bevorzugt | Harte neue Fehler | Mittlerer Score-Abstand |
|---|---:|---:|---:|
| Alter Stand | 8/9 | 0 | +0,1333 |
| Bisherige Promptfassung | 9/9 | 0 | +0,2444 |

Die drei neuen Quellenbriefs erhalten im Mittel 3,8/5 ohne harte Fehler.
**Die gesamte Textqualitaetsabnahme bleibt negativ:** Beide festen Vergleiche
verfehlen die vorbestehende +0,5-Grenze. Beide Kontrollarme haben selbst 8/9 harte
Fehler; die Praeferenzen sind kein breiter Ueberlegenheitsnachweis. Ein Grader,
kleine synthetische Stichprobe, keine X-Outcomes und keine normale Bot-Integration.
Nach Offenlegung sind diese drei Quellen kein frischer Holdout mehr. Native
Codex-Kosten wurden nicht ausgewiesen. Rohbelege und Nachpruefbarkeit:
[Source-first-Nachweis](evidence/source-first-marketing-20261017/README.md).

### Redaktion und Bestaetigungspruefung getrennt: Abnahme weiterhin negativ

V4 entfernte die kuenstliche Wortzahl und trennte Redaktionsauftrag von finaler
Faktenpruefung. Sie lieferte 7/9 technisch akzeptierte Texte (17 Haiku-Aufrufe,
0,036265 USD), bestand aber keine fachliche Abnahme. Das Code-/Promptreview fand
eine zu breite Erlaubnis fuer als Fragen oder Vorschlaege markierte Empfehlungen.
Die Ausgaben bestaetigten die Gefahr: ein Text stellte infrage, ob menschliche
Pruefung sinnvoll bleibe. Diese Variante wurde nicht uebernommen.

V5 verlangt ausdruecklich, dass Bedingungen und Begruendungen jeder Empfehlung
aus zitierter Evidenz folgen und vorgegebene menschliche Pruefungen erhalten
bleiben. Keine blockierenden Promptreview-Befunde; die bestehenden 72 Tests
bestanden. Der vollstaendige feste Providervergleich lieferte jedoch nur 4/9
akzeptierte Texte (17 Aufrufe, 0,039550 USD). Fuenf fehlende Texte verletzen bereits
die vorab festgelegte Null-Fehler-Grenze. Deshalb keine weitere Blindbewertung,
kein Holdout-Erfolgsnachweis und keine normale Bot-Integration. Quellen und
Output-Guard blieben in beiden Vergleichen per Hash gebunden und unveraendert;
keine Requests mit unbekannten Kosten. Native Codex-Kosten sind nicht enthalten.

Die portable `content-draft`-Anleitung und die Rollen `content-editor`/`verifier`
uebernehmen die engeren Quellen- und Kontrollregeln. Die Anleitung verbessert
den Arbeitsvertrag, beweist aber keinen Modell- oder Reichweitenerfolg. Die
Komponentenstrategie braucht einen quellenbasierten Neuentwurf statt weiteres
Polieren von Drafts mit bereits unbelegten Behauptungen. Private Belege:
`refiner-quality-fixed9-v4-20261017.json`, `refiner-quality-fixed9-v5-20261017.json`
und `refiner-editor-split-tests-20261017.log` unter `.runs/qualification/`.

### Weitere Reparatur und echter Providervergleich

Der neue begrenzte Coding-Auftrag `46c643d7a43b4cf592e93ca95b3495e5` bestand
zunaechst 62 Tests, scheiterte aber zu Recht an der unabhaengigen Review: Ein
linker Bereichsoperand konnte ausgetauscht werden. Eine zweite Gegenpruefung
fand ausgelassene Ziffern-Identifier am Stringende. Nach drei Fehlerberichten
stoppte die Engine am Fehlerbudget. Der Host vereinfachte danach den Parser
und ergaenzte Regressionen. Mit protokollierter Host-Hilfe wurde derselbe Lauf
ohne Erhoehung seiner Zeit-/Schrittgrenzen fortgesetzt: sieben Schritte,
`completed`, `reviewed: true`, 538 geschuetzte Dateien und die reparierte Quelle
im letzten Abschnitt unveraendert. Die separate Reviewerrolle bestaetigte den
aktuellen Quellstand im vereinbarten Umfang. Das ist ein assistierter, begrenzter Abschluss,
kein unassistierter Projektnachweis. Quell-SHA256 dieses Abschlusses:
`1ec5c6944ed0679245f638388ef446e0ef4bb06cd3ca04e2c8095457ee7b48e6`.

Die spaetere Fassung ergaenzt einen expliziten Providervertrag und erkennt genau
eine vollstaendige aeussere JSON-Codeblockhuelle. Der erste neue Huellentestlauf
scheiterte vor der Parseraenderung in zwei Faellen und bestand vier negative
Kontrollen. Prosa vor/nach JSON, mehrere Bloecke und doppelte Schluessel bleiben
verboten; alle inneren Schema-/Zitat-/Bestaetigungs-/Laengengrenzen bleiben aktiv.
72 aktuelle Modultests bestanden; die Aenderung wurde separat unabhaengig geprueft.
Der abschliessende Hostlauf bestand mit 238 ausgewaehlten Tests in 17,17 Sekunden
und 96 % Modul-Line-Coverage. Das ist keine vollstaendige Bot-Gesamtsuite.
Der native Abschluss der aelteren Quelle ist kein Reviewnachweis fuer spaetere
Prompt- oder Parseraenderungen.

**Grenze:** Ganze Zahlenfolgen und Operatoren werden syntaktisch geprueft.
Zahlenmenge oder exakte Zitatpraesenz beweisen nicht, welcher Aussage eine Zahl
zugeordnet ist. Diese Semantik muss der Reviewerdurchgang bewerten; auch dessen
Zustimmung ist keine Wahrheitsgarantie.

Der feste Vergleich verwendet alle neun bereits vorhandenen Kandidaten,
dieselben drei Quellbriefs und jeweils hoechstens zwei Revieweraufrufe. Es
werden keine erfolgreichen Faelle nachtraeglich ausgewaehlt und keine fehlenden
Ausgaben aus dem Nenner entfernt. Quelle, Output-Guard und Korpus sind vor dem
Modellaufruf per SHA256 gebunden und danach erneut geprueft. Es gab keine
Veroeffentlichung oder Originalbot-Aenderung.

| Variante | Akzeptierte Ausgaben | API-Requests | Gemeldete USD |
|---|---:|---:|---:|
| V1 | 0/9 | 9 | 0,019194 |
| V2, expliziter Roh-JSON-Prompt | 0/9 | 9 | 0,018747 |
| V3, Providerhuelle und kuerzere Einzelpunkte | 6/9 | 18 | 0,031386 |

Eine gesonderte Einzelfalldiagnose verbrauchte einen Request und 0,002154 USD.
Zusammen 37 Requests und 0,071481 USD, keine unbekannten Kosten. Das sind nur
die gemeldeten Haiku-Kosten, nicht die nativen Codex-Aufrufe. Reservierungen
bleiben lokale Schaetzungen statt Provider-Ausgabensperren.

**Blinde Gegenpruefung: nicht bestanden.** Ein separater Reviewer erhielt nur
18 zufaellig angeordnete A/B-Paare mit Evidenz und der bisherigen Fuenf-Dimensionen-
Rubrik. Der Zuordnungsschluessel wurde ihm nicht gegeben. Alle neun Faelle wurden
sowohl gegen den alten Stand als auch gegen die bisherigen Kandidaten geprueft:

| Vergleich | V3 bevorzugt | Harte V3-Fehler | Mittlerer Score-Abstand |
|---|---:|---:|---:|
| Alter Stand | 5/9 | 3/9 | -0,911 |
| Bisherige Kandidaten | 6/9 | 3/9 | -0,978 |

Die drei fehlenden Ausgaben gelten als harte Fehler. Fuer die sechs vorhandenen
Texte meldete der Reviewer keine harten Inhaltsfehler, aber schwache Eigenstaendigkeit
und wenig nichttriviale Einsicht. Die vorab bestehende Abnahme verlangt null harte
Fehler, mindestens 7/9 Praeferenzen und mindestens +0,5 Score-Abstand: nicht erreicht.
Die iterative feste Kohorte ist Entwicklungsevidenz, kein frischer Holdout und
kein Nachweis fuer reale X-Reichweite oder Produktionsreife.

Private Belege: `refiner-context-agent-20261017.json`,
`refiner-context-reviewed-20261017.json`, `refiner-context-v2-red-20261017.log`,
`refiner-envelope-red-20261017.log`, `refiner-v3-frozen72-20261017.log`,
`refiner-quality-fixed9[-v2|-v3]-20261017.json`,
`refiner-quality-v3-blind-grades-20261017.json`,
`refiner-quality-v3-verdict-20261017.json` unter `.runs/qualification/`.

Die portable Reviewer-Rolle fordert diese Trennung von Fixtures, Providerverhalten
und fachlichen Ergebnissen nun ausdruecklich. 20 strukturelle Offline-Gates
bestanden; sie pruefen keinen Provider und kein Modell.

### Planergrenze und vorausgegangene Projektfortsetzung

Der native Codex-Planer erwartet jetzt ausdruecklich kein Dispatch-Werkzeug:
er gibt `action: delegate` als JSON zurueck und der Host startet die Rolle.
Native Unteragenten sind fuer beide Verträge deaktiviert, das Shell-Werkzeug
nur fuer den Planer. Die Worker-Sandbox und die Review-Grenze bleiben erhalten.
Zwei Regressionstests pruefen CLI-Flags und den Delegationsvertrag; der neue
Delegationstest scheiterte vor der Promptkorrektur und bestand danach.
Das unabhaengige Python-Review fand keine schweren Befunde; Ruff und alle
20 Offline-Release-Gates bestanden. Der abschliessende Gesamtlauf fuehrte 410 Tests aus,
drei wurden uebersprungen, keine Fehler (221,908 Sekunden).

Die echte Fortsetzung `ea94e2f6e5c146228ea67889c085f912` delegierte danach
selbst an Developer (`gpt-6-luna`) und Reviewer (`gpt-6.1-sol`). Der Reviewer
belegte zunaechst die quadratische Regex-Suche, dann wiederholtes String-Slicing.
Der Planer veranlasste beide Reparaturen und neue Tests. Ein unabhaengiger
Hostlauf am Zwischenstand bestand mit 219 Tests und 96 % Modul-Line-Coverage.
Nach der letzten Reparatur endete der Lauf am kumulativen Schrittlimit 16,
ohne erneute Review: `reviewed: false`, `passed: false`. Alle 537 geschuetzten
Dateien blieben unveraendert. Vorangegangenes Host-Feedback und erhoehte
Schrittbudgets sind Teil der Historie; dies ist kein unassistierter Gesamterfolg.

Zusaetzliche Gegenproben lassen getrennte Zahlenoperatoren wie `− 25` gegen
die Evidenz `25` weiterhin passieren. Ein gruener 53-Faelle-Testlauf beweist
daher keine umfassende Faktensicherheit. Modulabnahme, echte Verbesserung der
Marketingentwuerfe und Integration bleiben offen; der Originalbot wurde durch
diese Arbeiten nicht veraendert oder gestartet.

Private Belege unter `.runs/qualification/`:
`refiner-json-delegation-resume-20261017.json`,
`refiner-host219-20261017.log`, `refiner-extra-adversarial-20261017.json`,
`agentic-json-delegation-gates-20261017.log`.

## Nachweise vom 16.10.2026

### Größerer Auftrag und adversariale Gegenprüfung

Der erste größere Codex-Auftrag blockierte schon im Planer: Die read-only
Koordinator-Sitzung wurde fälschlich als fehlendes Schreibrecht aller Rollen
interpretiert. Der Planer-Prompt stellt jetzt klar, dass der Host schreibberechtigte
Worker separat startet. Eine echte begrenzte Planer-Gegenprobe delegierte an die
Entwicklerrolle und ließ ihre Dateien unverändert. Sie prüft ausschließlich
Delegation, keinen abgeschlossenen Projektauftrag. Die dazugehörige Laufzeit
bestand 408 Tests mit drei Skips, 20 Offline-Gates und unabhängiges Review.

Danach schrieb der direkte API-Adapter mit `anthropic/claude-haiku-4.5` ein neues
Fakten-/Längenprüfmodul in der isolierten Marketingbot-Kopie. Der Host erlaubte
Schreibwerkzeuge ausschließlich für dieses Modul und das Testwerkzeug nur für
die eingefrorene Testdatei. Alle 537 geschützten Dateien blieben unverändert.
Der Lauf endete nach 15 Requests vor seinem Abschlussbericht an der lokalen
Reservierungsschätzung. Die gemeldeten Gesamtkosten betragen 0,379454 USD; alle
15 Requests haben Kostenmetadaten. Die Schätzung ist keine Provider-Ausgabensperre.

**Kritischer Befund:** Die erste Implementierung bestand 32 unabhängige Hosttests
mit 92 % Line-Coverage, akzeptierte aber unter anderem sofort genehmigte Neufassungen
ohne zweite Bestätigung und doppelte JSON-Schlüssel. Vorzeichen und Zahlengruppen
konnten ihre Bedeutung verlieren. Eine Exception-Klasse konnte Informationen im
Fehlergrund offenlegen. Das unabhängige Sicherheitsreview bestätigte diese Befunde.
Die erweiterten 41 Tests scheitern gegen die erhaltene erste Implementierung in
11 Fällen und bestehen in 30 Fällen. Das ist ein negativer Nachweis und keine
Freigabe des Moduls. Nacharbeit und anschließendes Host-Review bleiben erforderlich.

Belege: `cloud-refiner-result-20261016.json`, `api-refiner-result-20261016.json`,
`api-refiner-provider-20261016.json`, `api-refiner-host-v1-20261016.log`,
`refiner-v2-preserved-baseline-20261016.log`,
`planner-role-boundary-live-20261016.json` unter `.runs/qualification/`.

### Vorausgegangene kleinere Abnahme

- Die drei neuen Verhaltenstests scheiterten vor der Engine-Änderung und bestanden
  danach. Zusammen mit den bisherigen Engine-Tests bestanden 62 Tests.
- Die gesamte Testsuite führte mit Coverage 408 Tests aus und maß für die Engine
  92 % kombinierte Line-/Branch-Coverage. Ein intermittierender Browser-Test war
  fehlerhaft; das ist ausdrücklich kein vollständig grüner Gesamtlauf.
- Der Browser-Test wartete vor seiner zweiten Freigabe noch nicht auf eine neue
  Freigabe-ID. Nach Korrektur bestanden beide öffentlichen Browser-Tests. Es
  wurden keine Produktfreigaben automatisiert oder Prüfungen übersprungen.
- 20 Offline-Release-Gates bestanden, einschließlich generierter Pakete und Demo.
- Echter Modellpfad: `codex`, Modell `gpt-6-luna`, isolierter temporärer Workspace,
  höchstens 300 Sekunden und 90 Sekunden pro Aufruf. Der erfolgreiche Lauf
  benötigte 59,484 Sekunden, vier Schritte und zwei Berichte; ein separates Review
  bestand. Der Host bestätigte identische Eingabe-/Ergebnisbytes über den
  read-only Sandbox-Export und eine unveränderte Eingabe.
- Zwei vorausgehende Modellversuche wurden nicht als Erfolge gezählt. Im zweiten
  meldete das Modell, es könne einen weiteren Reviewer nicht starten. Die
  Rollenbeschreibung stellt nun klar, dass die aktuelle Reviewer-Instanz bereits
  vom Host unabhängig dispatcht wird und die Prüfung selbst durchführen soll.

Die Belege liegen privat unter `.runs/qualification/agentic-*20261016*`.
Diese Prüfung belegt den konkreten Dateiauftrag und die geänderte Fehlerbehandlung,
keinen unbeaufsichtigten Erfolg für beliebige Projekte und keine verbesserte
Marketingqualität. Der endgültige Gesamtlauf nach der Browser-Testkorrektur
bestand: **408 Tests ausgeführt, drei übersprungen, keine Fehler**, in
220,472 Sekunden. Der vorherige fehlgeschlagene Lauf bleibt als Beleg erhalten.
Das unabhängige Review und Ruff fanden keine blockierenden Befunde.

### Modellrouting und begrenzter nativer Coding-Nachweis, 17.10.

CLI/Python unterstuetzen jetzt explizite Primaer-, Reparatur- und Reviewmodelle
innerhalb desselben Providers. Zwei abgeschlossene `needs_revision`-Berichte
aktivieren standardmaessig das Reparaturmodell. Nur ein erfolgreicher Reviewer
mit Evidenz setzt die Episode zurueck; ein Entwicklererfolg allein nicht.
Der Engine-Fixture-Nachweis fuehrt ueber zwei Revisionen, staerkere Reparatur,
separates Review und Abschluss bei unveraenderten Schritt-/Fehlerzaehlern.
Policyaenderungen verwerfen ausstehende Freigaben. Exceptions werden nicht
als Anlass fuer automatische Wiederholung unbekannter Aktionen verwendet.

Der reale isolierte Auftrag `e380a25d382e45acb4da58d1472d1cf6` aenderte nur den
Koerper des strukturierten JSON-Parsers: Primaermodell `gpt-6-luna`, separates
Review `gpt-6.1-sol`, drei Schritte, null Fehler, 80,141 Sekunden. Alle 245
geschuetzten Dateien blieben unveraendert; Hostpruefungen bestaetigten den
Methodenbereich, die eingefrorenen Tests und fuenf erfolgreiche Testmethoden.
Keine Host-Reparaturhilfe waehrend dieses Laufs. Die Eingangsprobleme wurden
vorher durch 15 scheiternde Duplicate-Key-Unterfaelle reproduziert. Es gab
keine Live-Eskalation, weil das Primaermodell den begrenzten Auftrag bestand.
Das Experiment deaktivierte Aktionsfreigaben im isolierten Workspace; die CLI
erhaelt ihre bestehenden Freigaben. Kein Nachweis unbeaufsichtigten allgemeinen
Programmierens oder einer OS-isolierten Ausfuehrung beliebigen Fremdcodes.

Ein anschliessendes unabhaengiges Python-Review fand einen zusaetzlichen Bypass
ueber den Python-Literal-Ersatzparser. Diese weitere Korrektur stammt vom Host,
nicht aus dem obigen Modelllauf. Sie propagiert Duplicate-JSON-Fehler vor beiden
Fallbacks und prueft Python-Literal-Dictionaries rekursiv vor der Auswertung.
Fuenf Unterfaelle scheiterten vor der Korrektur. Anschliessend bestanden die
19 gezielten Routing-/CLI-/Parsertests, Ruff und 20 Offline-Gates. Die negativen
Marketing-Qualitaetsnachweise bleiben davon unberuehrt und offen.
Der abschliessende Gesamtlauf nach dieser Korrektur bestand: 426 Tests,
drei erwartete Symlink-Skips, keine Fehler in 205,529 Sekunden. Python- und
Security-Review fanden keine blockierenden Befunde in den geaenderten Bereichen.

Verbindliche Prüfungen bei Laufzeitänderungen:

```powershell
python -m unittest discover -v
python scripts/verify_release.py
```

Hinzu kommen ein unabhängiges Code-Review und ein ausdrücklich als solcher
gekennzeichneter echter Modelllauf. Dessen Ergebnis ist auf die konkrete Aufgabe
und den verwendeten Anbieter begrenzt. Ein gescheiterter Live-Lauf wird mit seiner
Fehlerkategorie dokumentiert und nicht durch eine Offline-Demo ersetzt.

Für die Produktabnahme bleiben alle Anforderungen dieser Tabelle offen, bis ihre
jeweiligen aktuellen Nachweise geprüft sind. Einzelne grüne Tests erlauben keine
pauschale Aussage „100 Prozent autonom“ oder „produktionsreif“.

## Hostbeobachtungen: technische Abnahme, Gesamtauftrag weiter offen

Der korrigierte Host-Lesepfad besteht 528 Regressionstestfaelle (524 bestanden,
vier Skips), die 80-Prozent-Coverage-Grenze und 16 Release-Gates. Eine native
Schema-Probe bestaetigt die nullable Antwortform; sie fuehrt keine Aktionen aus.
Der blockierte fruehere Coding-Lauf wird dadurch nicht nachtraeglich erfolgreich.
Ein neuer echter Auftrag mit Hostbeobachtungen, gepinnten Tests und separatem
Review ist weiterhin erforderlich. [Quellen und Grenzen](evidence/host-observations-20261017/README.md).
