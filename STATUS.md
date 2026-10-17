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
bleibt unter strikter Policy gesperrt. Das Cockpit bietet diese Policy noch nicht.
[Verwendung](docs/ISOLATED-TEST-EXECUTION.md).

## Aktuelle technische Abnahme

Nach dem lokalen Vollauf fand GitHub drei neue Fixtures mit Abhaengigkeit von
installierter Codex-CLI und Windows-Sandbox-Konfiguration. Der CLI-Fixture-Fix
und eine eng begruendete Bandit-Markierung fuer die Container-Tmpfs-Pruefung sind
auf main 2786d99. Linux, Browser, Paket und Deployment bestehen dort; Windows
3.11 scheiterte an der fehlenden lokalen Sandbox-Konfiguration im Testaufbau.
Der separat gepruefte Folgefix ist auf main 2c71d7e: 18 Integrationstests bestehen
auch mit absichtlich fehlender Konfiguration. GitHub-Abnahme dieses Stands offen.

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
