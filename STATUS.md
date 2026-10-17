---
schema: agent-status/v1
project: agenten-vorlage
status: active
last_updated: "2026-10-17"
---

# Agentenvorlagen: aktueller Stand

Coding- und Marketingagent sollen Ziele mit austauschbaren Rollen/Skills selbst
planen, ausfuehren, pruefen und nacharbeiten. Tests, kritische Abnahme, guenstige
Modelle und GitHub-Pushes sind verbindlich. Die Mietplattform ist zurueckgestellt.
**Gesamtziel noch nicht nachgewiesen; keine Produktionsfreigabe.**


Aktueller Nachweis: Ein neuer echter Coding-Lauf mit angefordertem gpt-6-sol
schliesst den extrahierten Marketingbot-Auftrag in drei Schritten ohne Fehler ab.
Er berichtet Hostbeobachtungen, aendert nur die freigegebene Quelldatei, besteht die
vollstaendige gepinnte Suite zweimal mit je 79 Tests und erhaelt ein separates
read-only Review. Alle Schutzdateien und die Runtime bleiben unveraendert.
Die unabhaengige Nachpruefung bestaetigt den finalen Diff, alle Schutzbindungen
und den frischen 79-Test-Nachweis nach dem letzten Edit. Persistierte Telemetrie
fuer die berichteten Leseaufrufe fehlt. Die neue semantische Pruefung,
Marketing-Vollintegration und Produktionsabnahme bleiben offen.
[Originalnachweise und Grenzen](docs/evidence/host-observations-20261017/native-task-sol-attempt.json).
Auch GitHub-Lauf 39006656908 auf main 11fabf9 ist vollstaendig erfolgreich.

## Jetzt implementiert

Die CLI/Python-API hat eine unveraenderliche genaue Schreibdateiliste:
--allow-write plus bewusstes --autonomous-writes. Resume kann Rechte und
bestehende Freigabepflichten nicht ausweiten. [Vertrag](docs/WRITE-POLICY.md).

Neu: --test-policy FILE aktiviert run_isolated_tests ohne Modellargumente.
Ein externer Hostmanifest pinnt Image/Lock, gesamte Test-/Supportdateien,
Quellsnapshot und Testzahl. Docker laeuft ohne Netzwerk, mit schreibgeschuetztem
Snapshot/Root, nichtprivilegiert, mit Ressourcen-/Zeit-/Ausgabelimits. Jeder
Versuch wird vor Start checkpointed; ein unbekannter Lauf wird nicht automatisch
wiederholt. Weitere Aenderungen entwerten den Passnachweis; aktueller Hostpass
und unabhaengiges Review sind fuer Abschluss erforderlich. Legacy run_pytest
bleibt unter strikter Policy gesperrt. Das lokale Cockpit kann diese Policies ueber feste Host-Ausfuehrungsprofile binden.
[Verwendung](docs/ISOLATED-TEST-EXECUTION.md).

## Aktuelle technische Abnahme

Nach dem lokalen Vollauf fand GitHub drei neue Fixtures mit Abhaengigkeit von
installierter Codex-CLI und Windows-Sandbox-Konfiguration. Der CLI-Fixture-Fix
und eine eng begruendete Bandit-Markierung fuer die Container-Tmpfs-Pruefung sind
auf main 2786d99. Linux, Browser, Paket und Deployment bestehen dort; Windows
3.11 scheiterte an der fehlenden lokalen Sandbox-Konfiguration im Testaufbau.
Der separat gepruefte Folgefix ist auf main 2c71d7e: 18 Integrationstests bestehen
auch mit absichtlich fehlender Konfiguration. GitHub-Lauf 39001481693 besteht
vollstaendig: Linux und Windows jeweils Python 3.11/3.12, Browser, Paket und
Deployment. Dies ist eine technische CI-Abnahme, keine fachliche Freigabe.

Der echte Coding-Lauf 5e0b73e35b284bada8f4cc44884a637c aenderte nur die erlaubte
Quelldatei des extrahierten Marketingbot-Bausteins. Alle sechs geschuetzten
Test-/Hilfsdateien sind bytegleich. Nach Timeout und kontrollierter Wiederaufnahme
forderte der Agent zweimal selbst die gepinnte Container-Suite an: jeweils
79 bestanden, keine Skips/Fehler, Cleanup bestaetigt. Ein separates Review fand
die fehlende Reparaturanweisung; der Agent ergaenzte sie und testete erneut.
Der Lauf endete dennoch blocked (8 Schritte, 4 Fehlberichte): native read-only
Shell-Aufrufe lieferten wiederholt keine sichtbaren Quellen-/Diff-Inhalte, daher
kein finales Review. Ein Worker behauptete zwischenzeitlich faelschlich einen
leeren Diff. Kein autonomer Gesamterfolg und keine fachliche Abnahme; naechster
Runtime-Schritt ist eine verlaessliche hostgebundene Lese-/Inspektionsmoeglichkeit.

507 Unit-/Integrationstestfaelle im vollstaendigen Coverage-Lauf: 503 bestanden,
vier Skips, keine Fehler, Exit 0; ueberwachte Quellen unveraendert. Kombinierte
Zeilen-/Branch-Abdeckung 80,6264 Prozent (Report gerundet 81 Prozent).
Ruff und alle 20 lokalen Offline-Gates bestehen; im reinen Git-Checkout sind
es 16, die lokale Kopie hat vier zusaetzliche generierte Operatorpakete.
Zusaetzlich 23 Runner-Tests unter Linux sowie echte Docker-Gegenproben fuer
Netzwerk-/Schreibschutz, Ausgabelimit, unabhaengiges PID1-Zeitlimit und Cleanup.
Separates Code-/Sicherheitsreview ohne verbleibenden Blocker im geprueften Stand.
Der vorherige Vollauf mit vier Codex-Regressionen und die zuerst roten
Datei-Austausch-Tests bleiben dokumentiert.
[Quellenbindung, Rohlogs, kritische Audits und Grenzen](docs/evidence/isolated-test-execution-20261017/README.md).

## Marketingbot: fachliche Abnahme weiterhin gescheitert

Der separat vorab gepruefte zwoelfteilige semantische Holdout v5 stoppte nach
zehn echten zentralen Haiku/OpenRouter-Aufrufen: 0,015775 USD bekannte Kosten,
keine unbekannten Ausgaenge oder Nutzungsdaten. Fuenf Faelle wurden bearbeitet
(drei technisch accepted, einer rejected, einer error), sieben blieben ungetestet.
Der Helfer speicherte beim Fehler weder den Grund noch die rohe Review-Antwort;
eine konkrete Parserursache ist damit nicht belegt. Keine automatische Wiederholung.
Accepted ist keine fachliche Wertung. Eine unabhaengige Blindpruefung ohne
Erwartungslabels bewertet die drei akzeptierten Texte als quellentreu und nutzbar;
kein False Accept unter diesen drei. Fehlerfall und sieben ungetestete Faelle
bleiben offen; die zwoelfteilige Gesamtpruefung ist nicht bestanden.
[Aggregierte Messungen und Grenzen](docs/evidence/source-holdout-partial-20261017/README.md).

V6 ergaenzt nur die Diagnose (fuenf Offline-Tests, separates Code-/Security-Review),
nicht den Qualifier. Neuer Lauf: 15 Anfragen, 0,024394 USD, sechs accepted,
ein error, fuenf ungetestet, keine unbekannten Ausgaenge/Kosten. Blindpruefung:
sechs akzeptierte Texte quellentreu/nutzbar. Die erhaltene rohe Review belegt
ein nicht abgedecktes letztes Satzzeichen; der Parser lehnt korrekt ab.
Gleicher Kandidat/Korpus: keine unabhaengigen Stichproben und kein bestandener
Gesamtvergleich. Naechste fachliche Arbeit muss die Protokolltreue verbessern,
ohne Abdeckungsregeln zu lockern; kein blindes Wiederholen des gleichen Stands.

Der Host-Lesepfad wurde nach den gefundenen Git-Pfad-Lecks, Filterluecken und
Austausch-Races korrigiert und unabhaengig geprueft. Der erste unterbrochene
Vollauf bleibt ein Fehlversuch. Der neue Vollauf nach der nullable-Schemakorrektur
besteht 528 Faelle (524 bestanden, vier Skips), 80,4805 Prozent kombinierte
Abdeckung, Ruff, Bandit und 16 Release-Gates. Windows und Linux bestehen jeweils
73 fokussierte Tests (Windows ein Skip). Eine echte native Schema-Probe liefert
eine validierte Antwort: ein Adapteraufruf, keine ausgefuehrten Aktionen. Dies
belegt noch keinen autonomen Gesamtauftrag; der fruehere blockierte Lauf bleibt
verbindlich. [Nachweise und Grenzen](docs/evidence/host-observations-20261017/README.md).

Der kleine zentrale Prompt-Wrapper-Fix ist auf Marketingbot/master b2b0c7e2:
saubere Uebernahme separat mit 4.464 Tests bestanden. Der groessere strukturierte
API-/Quellenchecker-Kandidat ist weiterhin isoliert und nicht promoviert.
Sein Vollauf besteht 4.641 Tests; ein echter zentraler Haiku/OpenRouter-Test
belegt vier physische Aufrufe fuer 0,006543 USD, keine unbekannten Ausgaenge.
Die reparierte Antwort schwaecht jedoch erforderliche Controller-Zustimmung zu
allgemeiner Kontrolle ab; der Reviewer akzeptiert das faelschlich. Auch der
fruehere Exklusivitaets-False-Accept bleibt verbindlich. Technisch gueltige
Modellantworten sind kein Nachweis semantischer Richtigkeit oder besserer Posts.
[API-Rohdaten und semantischer Audit](docs/evidence/source-central-live-20261017/README.md).

## Naechste verbindliche Abnahmen

1. Echter Coding-Auftrag mit strikter Schreibgrenze, eigenem isoliertem
   Test-/Reparaturablauf und separatem Review; geschuetzte Dateien unveraendert.
2. Quellenreview-/Reparaturfehler korrigieren und neue unabhaengige fachliche
   Abnahme bestehen; alte Fehlversuche nicht umetikettieren.
3. Bessere Marketingausgaben an realen Quellfaellen belegen; erst danach
   entsprechende Kandidaten in den Marketingbot uebernehmen.
4. Die lokale Bedienoberflaeche an die bewiesenen Host-Policies anbinden.

Fruehere kleine Modell-Fixtures, erfolgreiche Unit-Tests oder technische
Protokolltests beweisen keinen allgemeinen autonomen Projektabschluss.
Die vollstaendige Abnahmeliste und historische Gegenbeweise stehen in
[AGENTIC-ACCEPTANCE.md](docs/AGENTIC-ACCEPTANCE.md); ihre Fehlschlaege bleiben offen.
Der laufende Original-Marketingbot wurde nicht umgestellt oder neu gestartet.

## CI-Nachtrag: Hostbeobachtungs-Fixture

GitHub-Lauf 39004612791 auf c26855d scheiterte unter Linux an 21 neuen Tests,
deren Fixture eine lokal installierte Codex-CLI voraussetzte. Die lokale
Vollabnahme widerlegt diese CI-Luecke nicht. Der eng gepruefte Testfix mockt nur
CLI-/Windows-Konfigurationssuche beim Konstruktor; Runtime und Assertions bleiben
unveraendert. Alle 21 Faelle bestehen auf Windows sowie Linux ohne Codex im PATH.
Der neue GitHub-Lauf muss die plattformuebergreifende Abnahme noch bestaetigen.

## Echter Hostbeobachtungs-Auftrag: Protokolluebergabe weiter offen

Lauf 947156d972c94e88b188c477c60de28d endete blocked: vier Schritte, vier
Fehlberichte, keine Quellaenderung und keine Tests. Das Modell behandelte die
Host-Aktionsnamen als fehlende native CLI-Werkzeuge. Die geplanten Hostaktionen
wurden nicht angefordert. Die Nachpruefung bestaetigt sechs geschuetzte Dateien
und die Quelle unveraendert; der Runner meldet ausserdem die vom Engine-Host
erzeugte .agentkit.lock als unerlaubte Workspace-Aenderung. Sein originaler
Fehlerstatus bleibt erhalten. Der anschliessend korrigierte Protokollprompt
muss einen echten Lese-/Folgeantworttest und danach einen neuen Gesamtauftrag
bestehen. Kein Replay des ausgeschöpften Laufs und keine Produktionsfreigabe.
[Pruefsummen und Grenzen](docs/evidence/host-observations-20261017/native-task-attempt.json).

## Gemeinsame Abnahme: lokale Profile und Protokollkorrektur

Der neue Vollauf besteht 540 Faelle (536 bestanden, vier Skips), darunter acht
Browser-Tests. Alle 104 ueberwachten Quellen bleiben unveraendert; kombinierte
Abdeckung 80.6094 Prozent. Ruff, Bandit und 16 Release-Gates bestehen.
Eine echte native Leseprobe liefert mit zwei Adapteraufrufen und einer Hostaktion
die zufaellige Testmarkierung korrekt zurueck; Datei und Runtime unveraendert.
Damit ist die Lese-/Folgeantwortuebergabe nach der Protokollkorrektur belegt.
Der blockierte Coding-Gesamtauftrag bleibt gescheitert; ein neuer vollstaendiger
Auftrag und die fachliche Marketing-Abnahme sind weiterhin erforderlich.
[Gemeinsame Nachweise und Grenzen](docs/evidence/execution-profiles-20261017/README.md).

## Python-3.11-Nachtrag zu Junction-Regressionen

Die GitHub-Laeufe 39005635763 und 39005760452 fanden fuenf Windows-3.11-Fehler
in neuen Tests: Path.is_junction existiert dort nicht. Die gepruefte
Testkorrektur erkennt reale Junctions anhand des lstat-Reparse-Tags; keine
Assertions oder Sicherheitsfaelle entfallen, die Runtime bleibt unveraendert.
Alle 21 Faelle bestehen auf Windows Python 3.12 mit entfernter is_junction-API
und echten Junctions. Dies ist eine Kompatibilitaetssimulation; Python 3.11 ist
lokal nicht installiert. Der neue GitHub-Lauf muss die native Abnahme liefern.

## GitHub bestaetigt; voller Agentenauftrag bleibt offen

GitHub-Lauf 39006087460 auf 8911bdb besteht alle sieben Jobs einschliesslich
Windows und Linux mit Python 3.11/3.12, Browser, Paket und Deployment.
Damit ist auch die native Python-3.11-Testkorrektur bestaetigt.

Der neue echte Coding-Lauf 7a9f864b25d84ac684e4e84ef7683154 endet dennoch
blocked: vier Schritte, vier Fehlberichte, keine Tests und kein Review.
Eine Host-edit_file-Aktion aenderte ausschliesslich die erlaubte Quelle;
alle sechs geschuetzten Dateien, Runtime, Agentenpaket und Host-Kontrolldateien
bleiben unveraendert. Die Teilimplementierung bleibt isoliert und wird nicht
promoviert. Weitere Worker meldeten weiter faelschlich fehlende Hostaktionen.
Die erfolgreiche kleine Leseprobe belegt deshalb keinen stabilen Gesamtworkflow.
[Originalstatus und Pruefsummen](docs/evidence/host-observations-20261017/native-task-protocol-attempt.json).
Eine getrennte begrenzte Modellgegenprobe ist der naechste Schritt.

## Neue Inhaltspruefung: keine fachliche Abnahme

Der unabhaengig gepruefte Coding-Kandidat eaa2829 wurde einmalig gegen den neuen,
vorab getrennt beurteilten Zwölf-Faelle-Satz geprueft. Vier HTTP-200-Antworten mit
vollstaendiger Verbrauchs-/Kostentelemetrie kosteten gemeldet 0,006287 US-Dollar.
Ein Fall blieb nach Reparatur abgelehnt; der naechste wurde vom strengen lokalen
Pruefer als invalid_response zurueckgewiesen. Danach stoppte der geerbte Runner
unter dem Status transport_stopped; zehn Faelle wurden nicht ausgefuehrt.
Es gab keinen unbekannten Netzwerkausgang. Kein Replay, keine Regel-Lockerung,
keine semantische Abnahme oder Promotion in den laufenden Marketingbot.
[Ergebnis und Aussagegrenzen](docs/evidence/host-observations-20261017/semantic-v7-partial.json).

## Coding-Einstieg ueber feste Hostprofile

Der Coding-Launcher uebernimmt jetzt optional `-ExecutionProfiles` und reicht die
Registry an AI Studio weiter. Die Regression prueft Profil-/Workspace-Pfade mit
Leerzeichen, den unveraenderten Standardstart und den Rueckgabecode anhand eines
Mock-Startskripts; sie startet keinen Server oder Provider. Separate Code- und
Dokumentationsreviews ohne Blocker. Der vollstaendige unittest-Lauf besteht
541 Faelle (537 bestanden, vier Skips); alle 20 Offline-Releasepruefungen bestehen.
Die Registry und ein projektspezifischer Testmanifest muessen weiterhin hostseitig
vorliegen; der Launcher richtet sie nicht automatisch ein.

## Alle zwoelf Inhaltsfaelle erfasst; fachliche Abnahme gescheitert

Die separat gepruefte Fortsetzung fuehrte nur die zehn zuvor ungeprueften Faelle
aus und uebernahm die ersten beiden samt Verbrauch unveraendert. Insgesamt:
28 abgeschlossene Provideraufrufe, 0,044417 US-Dollar gemeldete Kosten, keine
unbekannten Ausgaenge. Vier Texte akzeptiert, vier abgelehnt, vier Protokollfehler.
Eine unabhaengige Blindpruefung beurteilt zwei der vier akzeptierten Texte als
nicht ausreichend quellentreu; sie beanstandet fehlende Freigabekontrollen und
eine abgeschwaechte Bedingung fuer Freigabe. Einer der zwei als gestuetzt
bewerteten Texte bleibt in der Attribution mehrdeutig. Ein Grader und synthetische
Faelle sind kein breiter Zuverlaessigkeitsnachweis. Richtige Ablehnung eines
unbelegten Entwurfs wird getrennt von erfolgloser Reparatur bewertet.
Keine fachliche Freigabe und keine Promotion in den laufenden Marketingbot.
[Abrechnung, Blindpruefung und Grenzen](docs/evidence/host-observations-20261017/semantic-v7-complete-accounting.json).
