# Codex-Hostbeobachtungen

AgentKit kann dem Codex-Worker drei begrenzte, schreibgeschuetzte Beobachtungen
bereitstellen: `read_file`, `list_files` und `inspect_git`. Sie laufen im lokalen
AgentKit-Prozess und liefern Ergebnisse fuer den naechsten Modellaufruf. Lesezugriffe
fordern keine Aktionsfreigabe an und veraendern den Workspace nicht.

## Werkzeuge und Grenzen

- `read_file` liest eine einzelne Workspace-Datei. Der Host verwendet standardmaessig
  `start_line=1` und `max_lines=100`; pro Aufruf sind hoechstens 200 Zeilen, 12.000
  Zeichen und Dateien bis 2.000.000 Byte zulaessig. Die Codex-Wire-Schemaform verlangt bei
  jeder Aktion beide Range-Felder: Fuer nicht verwendete Werte sendet das Modell
  `null`; fuer `read_file` darf es positive Integer senden.
- `list_files` listet ein Verzeichnis auf, auch den Workspace-Root. Die Ausgabe ist
  auf 200 Eintraege und 12.000 Zeichen begrenzt. Eine abgeschnittene Liste meldet
  `truncated=true`.
- `inspect_git` gibt den Status und einen begrenzten Textdiff gegen `HEAD` zurueck.
  Es prueft, dass das Workspace-Verzeichnis selbst der Git-Root ist. Die Ausgabe
  ist auf 32 geaenderte Pfade, 12.000 Statuszeichen, 24.000 Diffzeichen und
  Textdateien bis 700.000 Byte pro Blob begrenzt.

Ein `inspect_git`-Ergebnis mit `status=partial`, `filtered_changes_present=true`
oder `truncated=true` ist unvollstaendig und darf nicht als sauberer Workspace
verstanden werden. `status=unavailable` bedeutet, dass Git-Evidenz nicht sicher
ermittelt werden konnte. BinÃ¤re oder nicht-UTF-8-Diffs werden fail-closed als
nicht verfuegbar behandelt.

Pro Worker sind hoechstens 24 Beobachtungsaufrufe und insgesamt 48.000
Beobachtungszeichen verfuegbar. Wiederholte Lesezugriffe liefern den aktuellen
Stand und werden nicht als doppelte Schreibaktionen behandelt.

## Pfad- und Inhaltsgrenzen

Der Host verweigert bekannte Zugangsdatenpfade, etwa `.env`-Dateien, Credential-,
Secret-, Token-, SSH-, Zertifikats- und private-Key-Verzeichnisse sowie gaengige
Schluesseldateinamen und Zertifikats-/Key-Endungen. Interne Laufzeit-, VCS- und
Cachepfade werden ebenfalls aus Verzeichnislisten ausgeblendet. Links, Junctions,
Reparse-Punkte und mehrfach verlinkte Dateien werden nicht als beobachtbare
Quelldateien akzeptiert. POSIX-Verzeichnisse werden ueber verankerte `dirfd`- und
No-follow-Aufrufe gelesen; Windows verwendet geoeffnete Verzeichnishandles und
prueft deren kanonischen Pfad. Git-Diffs vergleichen sicher erfasste Bytes mit
dem Git-Objekt, statt den veraenderlichen Workspace-Pfad erneut durch Git lesen
zu lassen.

Das ist Pfadhygiene, keine allgemeine Erkennung von Geheimnissen im Dateiinhalt.
Eine erlaubte Quelldatei kann weiterhin vertraulichen Text enthalten. Beobachteter
Text und Git-Diffs werden als untrusted input in den folgenden Modellprompt
aufgenommen und dort ausdruecklich als Daten, nicht als Anweisungen, behandelt.
Die Beobachtungsdaten werden nicht in Action-History oder Checkpoints abgelegt;
der ausgewaehlte Modellanbieter erhaelt sie dennoch fuer die Antwort. Diese
Grenzen sind keine allgemeine Betriebssystem-Sandbox oder DLP-Garantie.

## Zusammenspiel mit Codex und Freigaben

Wenn eine hostseitige `WritePolicy` oder `TestExecutionPolicy` aktiv ist, deaktiviert
der Codex-Aufruf das native `shell_tool`; der Worker muss fuer Quellen- und Git-Evidenz
die Hostbeobachtungen verwenden. Ohne diese strikte Policy bleibt das bisherige
No-policy-Aktionsverhalten erhalten; die Beobachtungen stehen als zusaetzlicher
Weg bereit, erzwingen aber keine Aenderung der Legacy-Shell-Konfiguration.

Das JSON-Schema verlangt fuer alle Aktionen dieselben sechs Argumentfelder:
`path`, `content`, `old_text`, `new_text`, `start_line` und `max_lines`. Nicht
verwendete Range-Felder sind im Wire-Format `null`. Der Host entfernt diese
Platzhalter vor Kanonisierung, Freigabe und Replay; dadurch bleiben die bisherigen
kanonischen Aktionsargumente und deren Freigabebindung unveraendert. Ein nicht-null
Range-Wert ist nur bei `read_file` zulaessig. Schreib- und Testfreigaben bleiben
von der Beobachtung getrennt.

## Verifikation und Aussagegrenzen

Die fokussierten Hostbeobachtungs-, Freigabe-, Schreibpolicy- und isolierten
Testintegrationsfaelle bestanden auf Windows und Linux; der Windows-Lauf enthielt
einen uebersprungenen Test. Eine native Codex-Probe bestaetigte lediglich, dass
die aktualisierte strukturierte Antwortschemaform akzeptiert wurde. Sie belegt
keinen echten Datei-Lese-/Schreibauftrag oder die semantische Qualitaet eines
Modellberichts. Der neue Vollauf nach der Schemaaenderung besteht 528 Testfaelle
(524 bestanden, vier Skips) und die 80-Prozent-Coverage-Grenze.
[Quellbindung und Aussagegrenzen](evidence/host-observations-20261017/README.md).
Daraus folgt keine Produktionsfreigabe.
