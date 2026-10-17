# Hostgebundene Selbsttests: lokale Implementierungsabnahme

Der neue CLI/Python-Weg erlaubt dem Coding-Agenten die Aktion
run_isolated_tests mit leerem Argumentobjekt. Ein externer Hostmanifest bindet
Image/Dependency-Lock, Test- und Supportdateien samt Hashes, erwartete Testzahl
und den genauen Quellsnapshot. Das Modell kann keine Dockerparameter oder
Teiltests waehlen. Freigaben bleiben bei require_approvals aktiv; eine bewusst
autonome Konfiguration kann die begrenzten Tests ohne Einzelfreigabe ausfuehren.
Legacy run_pytest bleibt unter strikter Policy gesperrt. Jeder Versuch wird
vor Start dauerhaft reserviert; frische Testevidenz und separates Review sind
Abschlussbedingungen. Die Kopiergrenze nutzt gepruefte Dateihandles.

## Nachweise und erhaltene Fehlschlaege

* Finaler vollstaendiger Lauf mit Coverage: 507 Testfaelle, 503 bestanden,
  vier Skips, keine Fehler, Exit 0. Monitored Python-/Schemaquellen und Tests
  blieben bytegleich. Kombinierte Zeilen-/Branch-Abdeckung 80,6264 Prozent,
  im Textreport auf 81 Prozent gerundet; --fail-under=80 besteht.
* Erster Vollauf: 506 Faelle, vier Fehler im alten Codex-Freigabeablauf,
  vier Skips. Ursache: nicht serialisierbare neue Host-Callbacks im bisherigen
  Modellkontext. Der korrigierte gemeinsame Filter und bedingte Callback-
  Einrichtung bestehen den neuen Vollauf. Fehlerlog bleibt erhalten.
* Zwei Datei-Austausch-Regressionen waren zuerst rot. Die unabhaengige
  Sicherheitsnachpruefung bestaetigt die Korrektur ohne verbleibenden Blocker
  im geprueften Quellstand. Der erste kritische Audit bleibt erhalten.
* Echte Docker-Gegenproben: Quellimport und hostile conftest mit verweigertem
  Netzwerk/Workspace-Schreiben; begrenzte Ausgabe mit Abbruch; abgekoppelter
  PID1-Zeitwaechter beendet den Container (Exit 124); Bereinigung bestaetigt.
* Alle 23 Runner-Tests bestehen zudem unter Linux/POSIX im Container.
  Das ist eine Komponentensuite, keine zweite volle Projektsuite.
* Ruff besteht. Der reine Checkout hat 16 Offline-Release-Gates; die kanonische
  lokale Kopie besteht 20, einschliesslich vier dort erzeugter Operatorpakete.

Die 15 geaenderten Implementierungs-/Test-/Dokumentationsdateien wurden bytegleich
in die kanonische Kopie uebertragen. Unveraenderte Baseline-Dateien koennen
zwischen den lokalen Checkouts nur in LF/CRLF-Zeilenenden differieren; die
normalisierte Gleichheit aller ueberwachten Dateien ist separat geprueft. Der
Patch ist eine Git-Textdarstellung; die Rohdatei-Hashes beziehen sich auf den
getesteten lokalen Arbeitsstand und koennen durch Checkout-Zeilenenden von
Git-Blobs abweichen. Die JSON-/Logbelege werden bytegetreu archiviert.

## Grenzen

Noch kein echter Modell-Coding-Auftrag mit dem neuen Testwerkzeug abgenommen.
Kein Beweis gegen Kernel-/Dockerfehler oder eine manipulierte Testsuite.
Host, Transport und gepinntes Image bleiben vertrauenswuerdig; das Image muss
selbst frei von Zugangsdaten sein. Das Cockpit bietet diese Policy noch nicht
an. Die Marketing-Quellenpruefung hat weiterhin einen nachgewiesenen
semantischen False-Accept; keine Produktions-/Gesamtfreigabe. Der laufende
Originalbot wurde nicht umgestellt oder neu gestartet.

[Verwendung und Hostvertrag](../../ISOLATED-TEST-EXECUTION.md).
