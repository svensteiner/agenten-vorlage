# Private lokale Testphasen (in Entwicklung)

Diese Ausfuehrungsart ist noch nicht fuer Produktionsauftraege qualifiziert.
Sie ist getrennt vom oeffentlichen, unveraenderlichen Docker-Testprofil v1.
Es gibt noch keinen oeffentlichen API- oder Cockpit-Loader fuer diese Policy.

Der Operator bindet einen isolierten Workspace, genaue Schreibdateien,
Produktions-Ausgangshashes, Testverzeichnisse und Testdateien, ein Image und
den Host-Starter an eine unveraenderliche Policy. Codex darf nur Host-Aktionen
vorschlagen. Native Shell-Ausfuehrung bleibt dabei deaktiviert.

Der Host erzwingt folgende Bedingungen:

- `red` weist die benannten Assertion-Fehler am unveraenderten Produktionsstand nach.
- Produktionsaenderungen benoetigen diesen Nachweis mit unveraenderten Testdateien.
- `targeted` prueft die festgelegten Tests am aktuellen Quellstand.
- `full` benoetigt einen erfolgreichen gezielten Test desselben Quellstands und
  fuehrt die gesamte festgelegte Testsuite aus.
- Abschluss benoetigt einen aktuellen erfolgreichen Gesamttest und unabhaengiges Review.

Versuche werden vor der Ausfuehrung dauerhaft reserviert. Ein unbekannter Ausgang
sperrt weitere Versuche; er darf nicht automatisch wiederholt werden. Ein bereits
bekannter Versuch derselben Phase und desselben Quellstands wird vor einer neuen
Reservierung abgelehnt. Gespeicherte Nachweise muessen auch bei Wiederaufnahme
die Reihenfolge und die Quellbindungen erfuellen.

## Aussagekraft der Nachweise

Container-Konfiguration, Ein-/Ausgangshashes, Prozessausgang und Bereinigung sind
Host-Beobachtungen. Einzelne Testergebnisse werden dagegen von pytest gemeldet.
Ein Hash ueber einen Bericht authentifiziert nicht dessen inhaltliche Wahrheit.
Ausgefuehrter Python-Code kann innerhalb seines Testprozesses Verhalten und
Testausgaben beeinflussen. Deshalb ersetzen gruene Tests weder die unabhaengige
Pruefung geaenderter Tests noch aufgabenbezogene Akzeptanzpruefungen.

Die Trennung von Supervisor und Testprozess verhindert, dass normale Testimporte
direkt die Python-Variablen des Supervisors ueberschreiben. Sie ist kein Nachweis,
dass boesartiger Testcode seine eigenen Ergebnisberichte nicht faelschen kann.
Die Container-Grenze schuetzt den Host; ihre Wirksamkeit und die Aussagekraft
der Tests sind getrennt zu pruefen.

## Bisherige praktische Pruefung

Die [Linux-Kompatibilitaetspruefung](evidence/execution-profiles-20261017/marketing-linux-fixture-portability.json)
hat die vollstaendige Marketingbot-Unit-Suite mit 4.714 Erfolgen, zwoelf Skips
und fuenf erwarteten Fehlschlaegen ausgefuehrt. Vier unabhaengig gepruefte
Fixture-Korrekturen simulieren Windows nur im jeweils getesteten Modul.
Produktionscode und laufender Marketingbot wurden nicht geaendert.

Ein kleiner Engine-Lauf hat RED, eine Host-Quellaenderung, gezielte Tests und
Gesamttests in echten Docker-Containern durchlaufen. Die Modellantworten und
das Review waren dabei vorgegeben; das belegt die technische Verbindung,
keine autonome Loesung durch ein echtes Modell.

Die anschliessende vollstaendige Marketingbot-Suite hat einen fehlenden
Programmeinstiegsschutz im pytest-Kindprozess aufgedeckt: Multiprocessing
startete beim Reimport weitere Testsuiten. Dieser Diagnoselauf wurde gezielt
beendet und bleibt unbekannt. Der korrigierte Starter verwendet einen
`__main__`-Schutz. Ein frischer Lauf erreichte die pytest-Zusammenfassung mit
4.714 Erfolgen, zwoelf Skips und fuenf erwarteten Fehlschlaegen; sein
strukturierter Ergebnisbericht war fuer den Host jedoch nicht lesbar. Auch
dieser Lauf bleibt unbekannt und wird nicht wiederholt. Die Container wurden
entfernt, und die 698 Workspace-Eingaben blieben unveraendert.

Separat reproduziert wurde eine stille Kuerzung der allgemeinen
Prozessausgabe: 1,1 MB stdout wurden bei erfolgreichem Prozessende als nur
1,0 MB zurueckgegeben. Die unabhaengig gepruefte Korrektur liest beide Streams
vollstaendig innerhalb der unveraenderten gemeinsamen 2-MB-Grenze. Gezielte
Tests pruefen grosse Einzelstreams und die Ablehnung zu grosser gemeinsamer
Ausgaben. Der frische Gesamtlauf liefert nun einen validierten Host-Bericht:
4.729 erfasste Testfaelle in 321 Dateien, davon 4.714 bestanden, zehn
uebersprungen und fuenf erwartete Fehlschlaege. Zwei weitere Skips betreffen
die Modulsammlung. Echte Multiprocessing-Tests liefen innerhalb des
geschuetzten pytest-Kindprozesses erfolgreich. Alle 698 Host- und
Scratch-Eingaben blieben unveraendert; der Container ist nachweislich entfernt.

Der gepruefte AgentKit-Stand besteht 643 Gesamttests mit fuenf Skips und ohne
Fehler sowie 34 Offline-Releasepruefungen. Die Zahl der Releasepruefungen
enthaelt die zu diesem Zeitpunkt vorhandenen generierten Pakete.
[Quellbindungen, Ergebnisse und Grenzen](evidence/execution-profiles-20261017/private-local-phase-technical.json).

Der [Folgestand](evidence/execution-profiles-20261017/private-local-phase-recovery-technical.json)
besteht 651 Tests mit fuenf Skips, ohne Fehler und mit 80 % Branch-Coverage.
Bekannte verfruehte Phasen- oder Produktionsschreibvorschlaege werden vor
Seiteneffekten als begrenzte Korrekturbeobachtung an den Worker gegeben.
Allgemeine Fehler, unbekannte Ausgaenge und Fehler nach einer Reservierung
bleiben gesperrt. Vorhandene Korrektur- und Historienbudgets gelten weiter.

Exakte, hostseitig gebundene Test-IDs duerfen bis zu 16.384 Zeichen enthalten;
die Manifestgrenze von 200.000 Bytes und die Anzahlgrenzen bleiben erhalten.
Damit ist auch ein bestehender parametrisierter Fall mit 8.284 Zeichen ohne
Verkleinerung der gezielten Suite waehlbar. Das oeffentliche v1-Profil bleibt
unveraendert. Ein echter autonomer Coding-Auftrag und die Marketingqualitaet
sind weiterhin nicht abgenommen.
