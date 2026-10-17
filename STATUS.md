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

## Quellenpruefung: API-Protokoll und semantischer Gegenbeweis

Die getrennten v3/v4-Diagnosen mit echtem Haiku verbessern das API-Format.
V4 repariert die falsche Zahlungs-/Automatikbehauptung ueber ein explizites,
streng dekodiertes JSON-Textfeld. Trotzdem keine Abnahme: Das als gueltig
bezeichnete Kontrollbeispiel behauptet exklusive Controller-Zustaendigkeit,
obwohl die Quelle nur dessen Zustimmung verlangt. V3 und v4 akzeptieren diese
Verstaerkung. Die separate kritische Pruefung wertet das als False-Accept.
Vier Aufrufe je Studie kosten gemeldet 0,006434 und 0,006625 USD; keine unbekannten
Ausgaenge. Parser und fruehere fehlgeschlagene Abnahmen bleiben unveraendert.
[Rohantworten, Dekodierung und semantischer Audit](docs/evidence/source-faithfulness-typed-protocol-20261017/README.md).

Zusaetzlicher echter Integrationsfehler gefunden: Der zentrale Responder haengt
an Quellenpruefung/Reparatur einen widersprechenden Nur-Tweet-Zusatz an. Zwei
neue Regressionen waren rot; die enge Ausnahme fuer diese expliziten Tasktypen
besteht 134 gezielte Tests und den Kandidaten-Vollauf mit 4.605 Tests, elf Skips,
fuenf erwarteten Fehlern,273,93 Sekunden. Die saubere Uebernahme nur dieses
kleinen Adapterfixes besteht separat 4.464 Tests auf originalem master, elf Skips,
fuenf erwartete Fehler,286,32 Sekunden, Exit 0. Der Zwei-Dateien-Fix ist auf
Marketingbot/master b2b0c7e2 gepusht; der unqualifizierte Quellenchecker ist
nicht enthalten. [Getrennte Quell-/Test-/Commitbelege](docs/evidence/source-review-wrapper-20261017/README.md).

Der groessere strukturierte API-Kandidat bleibt isoliert. Sicherheitsreview
fand und korrigierte Fehlerbody-Logging sowie ungueltige Unicode-Surrogate.
Die ebenfalls nachgewiesene OpenRouter-only-Erreichbarkeitsluecke ohne
OpenAI-Schluessel ist im isolierten Kandidaten korrigiert; explizite Mock-/
Local-Konfigurationen bleiben ohne Remotezugriff. Die tatsaechlich erfolgreiche
Providerroute wird erfasst; OpenRouter-Fehlerlogs enthalten keine Antwort-/
Exception-Texte. 91 gezielte Tests bestanden. Der folgende Vollauf besteht
4.640 Tests und scheitert an einer alten Testannahme: Ein gemockter Generator
belegt keine OpenAI-Transportherkunft. Nur diese Assertion wurde auf unknown
korrigiert; separate Review ohne Blocker und 80 relevante Tests bestanden.
Der neue Vollauf besteht: 4.641 Tests, elf Skips, fuenf erwartete Fehler,
42 Warnungen, 295,53 Sekunden, Exit 0. Zwoelf ueberwachte Dateien bleiben
bytegleich. [Getrennte Fehl-/Erfolgsbelege](docs/evidence/source-typed-central-20261017/README.md).
Gewoehnliche erfolgreiche Antworttexte werden
weiterhin teilweise geloggt; keine allgemeine Datenschutzfreigabe. Keine
Promotion dieses Kandidaten.

## Isolierte Selbsttests: Hostvorpruefung bestanden

Ein echter Docker-Test unter WSL besteht zehn Container- und zwoelf Hostchecks:
kein Netzwerk, nichtprivilegierter Benutzer, schreibgeschuetzte Root-/Testdatei,
keine Capabilities, kein Docker-Socket, feste Ressourcen und ein per Digest
gebundenes Python-Image. Die geschuetzte Hostdatei bleibt unveraendert;
Containerbereinigung bestaetigt. Separate Sicherheitspruefung ohne Blocker.
Noch kein AgentKit-Testwerkzeug, keine Projektabhaengigkeiten und kein echter
Coding-Abschluss darin. run_pytest bleibt unter WritePolicy gesperrt.
[Belege und verbleibender Integrationsvertrag](docs/evidence/docker-isolation-probe-20261017/README.md).

## Zentraler echter API-Nachtest

Der zentrale Responder-Kandidat fuehrt nach einer separat korrigierten
Diagnoseharness-Panne vier echte Haiku/OpenRouter-Aufrufe aus: drei Reviews,
eine Reparatur, gemeldet 0,006543 USD, keine unbekannten Ausgaenge. Die
API-/Schema-/Dekodierintegration funktioniert. Die unabhaengige Inhaltspruefung
findet jedoch erneut einen False-Accept: erforderliche Controller-Zustimmung
wird zur allgemeinen Kontrolle abgeschwaecht und vom Reviewer akzeptiert.
Keine semantische Abnahme oder Promotion. Der vorherige Harness-Fehlversuch
mit null Aufrufen/Kosten ist separat erhalten.
[Rohbelege, Ganzablauf-Tests und kritischer Audit](docs/evidence/source-central-live-20261017/README.md).

## CLI-Dateifreigabe

`run` und `resume` bieten jetzt wiederholtes `--allow-write DATEI` und explizites
`--autonomous-writes`. Ohne Liste keine autonome Freigabe; gespeicherte
Aktionsfreigaben bleiben bestehen, geaenderte/fehlende Listen sperren Resume.
Acht CLI-Tests bestanden; voller kanonischer Lauf: 463 Tests inklusive vier
Skips, 233,760 Sekunden, Exit 0, getestete Quellen unveraendert. Ruff und alle 20
Offline-Gates bestanden; separate Codepruefung ohne Blocker. Keine neue echte
Modellabnahme der CLI, Cockpit-Anbindung noch offen.
[Testbelege und Grenzen](docs/evidence/cli-write-policy-20261017/README.md).

GitHub CI deckte danach zwei testinterne Abhaengigkeiten von einer installierten
Codex-CLI auf Linux auf. Beide Fehler sind lokal mit deaktivierter CLI-Suche
reproduziert. Nur die Command-Discovery-Fixtures wurden korrigiert, die echten
Policy-Pruefungen bleiben aktiv. Beide Faelle bestehen ohne CLI. GitHub-Lauf 38995751553 fuer 5995f54 ist
abgeschlossen und gruen: alle sieben Jobs, darunter Linux/Windows mit Python
3.11/3.12 sowie Browser-, Paket- und Deploymentpruefungen. Die Linux-3.11-Pruefung
meldet 463 Tests inklusive 21 Skips und 80% kombinierte Zeilen-/Branch-Abdeckung.
[Externe Lauf-/Jobbelege](docs/evidence/cli-write-policy-20261017/github-run.json).

## Aktuelle Verifikation der Schreibgrenze

Die separat reviewte strikte WritePolicy ist im Hauptprojekt uebernommen.
Ruff und alle 20 Offline-Release-Gates bestehen. Der volle kanonische Lauf
umfasst 459 Tests: 455 bestanden, vier Skips, 209,059 Sekunden, Exit 0;
die getesteten Quelldateien blieben unveraendert. Ein echter begrenzter Luna-Modelllauf ist beendet: erlaubte Aenderung und
separate Review, geschuetzter Dateihash unveraendert. Die LF-only-Byteassertion
scheitert an CRLF; die Git-Diff-Evidenz des Reviewers hat keine eigene
Fixture-Baseline. Kein nachgewiesener verbotener Schreibversuch und keine
allgemeine Coding-Abnahme. [Rohresultat und Hostaudit](docs/evidence/write-policy-live-20261017/README.md). [Testbelege](docs/evidence/write-policy-20261017/README.md).
[API, Verwendung und Grenzen](docs/WRITE-POLICY.md).

Der neueste Marketingbot-Kandidat besteht 4.602 Unit-Tests, elf Skips und fuenf
erwartete Fehler. Die Promptkorrektur fuer die Quellenpruefung ist im echten
zweiten Protokollnachtest dennoch gescheitert: zwei Reviewantworten in Codebloecken,
beide streng verworfen, keine verwertbaren Endtexte. Kein Qualitaetsnachweis und
keine Promotion in den laufenden Bot. Der naechste Ansatz muss die API-Ausgabeform
verbindlich steuern; die fehlgeschlagenen Abnahmen bleiben bestehen.

Der folgende Test mit eigener Git-Baseline und festen LF-Bytes scheitert im
normalen Engine-Workflow am Worker-Zeitlimit (75 Sekunden): erlaubte Aenderung
korrekt, aber keine finale Review. Im getrennten direkten Backend-Negativtest
werden zwei echte protected.txt-Schreibvorschlaege durch die Hostpolicy
abgelehnt; die Dateien bleiben gegenueber dem Zustand nach dem Engine-Lauf
unveraendert. Nur dieser Grenztest ist bestanden, keine allgemeine
Coding-Abnahme. [Rohbelege und kritische Bewertung](docs/evidence/write-policy-live-v2-20261017/README.md).

## Bestaetigt

- AgentKit: letzter voller kanonischer Lauf 463 Tests inklusive vier Skips,
  keine Fehler; Ruff und 20 Offline-Gates bestanden. Die strikte Schreibpolicy
  wurde separat reviewt. Danach nur Dokumentation und isolierte Diagnostik.
- Marketingbot/master `b2b0c7e2`: Quellenbindung, OS-Sperrenfix und unveraenderte
  Weitergabe expliziter Quellenpruefungs-/Reparaturprompts. Der saubere Stand
  besteht 4.464 Unit-Tests, elf Skips,fuenf erwartete Fehler, 286,32 Sekunden;
  separate Review ohne Blocker. Quellenmetadaten bleiben unverifiziert.
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

## Echte Quellenpruefung: neue Sechser-Abnahme gescheitert

Nach4.597 bestandenen Unit-Tests liefert der eingefrorene echte Modellvergleich
0/6 akzeptierte neue Posts,11 Anfragen,0,015246USD gemeldete Kosten und keine
unbekannten Kosten/Ausgaenge. Beide verblindeten Pruefungen: alle12Arme0Punkte,
sechs Gleichstaende,Delta0. Fehlende Ausgaben bleiben im Nenner. Keine Promotion.
Rohantworten des Reviewers fehlen im Beleg; die genaue Protokollfehlerursache ist
noch unbewiesen. Ein getrennter Diagnosetrace mit zwei neuen synthetischen Entwuerfen bestaetigt
Markdown-Zaun/Erklaerung und fehlende Satzzeichenabdeckung in diesen Antworten:
zwei Requests,0,004088USD,beide invalid_response. Promptkorrektur in Arbeit;
Parser bleibt streng. Kein Wiederholen der Abnahme.
[Neue Diagnose mit Rohantworten](docs/evidence/source-faithfulness-protocol-trace-20261017/README.md). [Rohbelege, Blindnoten und Grenzen](docs/evidence/source-faithfulness-paired-screen-20261017/README.md).

## Offene Abnahme

1. Fruehere Generatorreparatur: volle Unit-Regression4.495 bestanden. Neue
   Quellenintegration: erster voller Unit-Lauf4.591 bestanden/sechs alte
   Experiment-Fixturefehler; nach expliziter Host-Fixtureanpassung zweiter Lauf
   4.597 bestanden,elf Skips,fuenf xfailed,291,04s. Native Bereichsabnahme bleibt gescheitert. Uebernahme bleibt von Umfangsschutz, Textqualitaet und Betrieb abhaengig.
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
