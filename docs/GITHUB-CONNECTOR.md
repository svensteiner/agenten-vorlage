# GitHub-Dateien als Dialogreferenz

Im Arbeitsdialog kann eine einzelne UTF-8-Textdatei aus einem öffentlichen GitHub-
Repository geladen werden. Eigentümer, Repository, Dateipfad und Branch/Tag/Commit
werden getrennt angegeben. Branches mit Schrägstrichen sind möglich. Die Aktion
„Vorschau von GitHub laden“ übermittelt diese Angaben an GitHub; Gesprächsinhalte
und lokale Dateien werden dabei nicht übertragen.

Nach Prüfung der Vorschau übernimmt „Als Anhang übernehmen“ einen unveränderlichen
Text-Snapshot in den Nachrichtenentwurf. Erst „Senden“ gibt ihn als Referenz an den
gewählten Ausführungsablauf weiter. Die Vorschau alleine startet keinen Modelllauf.
Abbrechen oder Wechseln des Dialogs verwirft eine noch nicht übernommene Vorschau.

Der Snapshot enthält die angegebene Quelle, den Ref und den geprüften Git-Blob-SHA
zusammen mit dem gelesenen Text. Er ist daher eine abgeleitete Referenzdatei, keine
bytegleiche Kopie der GitHub-Datei. Der Hash identifiziert den gelesenen Inhalt; ein
Branchname kann sich später ändern. Für einen dauerhaft adressierbaren Stand kann
ein Commit als Ref angegeben werden. Wiederholungen des Anhang-Uploads verwenden
dieselben gespeicherten Bytes und dieselbe Anfragen-ID statt GitHub erneut zu lesen.

## Netzwerk- und Inhaltsgrenzen

- Nur `https://api.github.com`, ausschließlich lesende Inhaltsanfragen; keine
  Weiterleitungen oder vom Server gelieferten Download-URLs.
- Keine Tokens, Cookies oder übernommenen Proxy-Zugangsdaten. Private Repositories,
  OAuth und Schreibaktionen sind nicht implementiert. Bestehende Provider-Schlüssel
  werden nicht an GitHub gesendet.
- Höchstens 24.000 Bytes Quelltext und 32 KiB fertiger Snapshot. Binärdateien,
  Verzeichnisse, Submodule, ungültiges UTF-8 und NUL-Bytes werden abgelehnt.
- Begrenzte Antwortgröße, zwei gleichzeitige Anfragen und Netzwerk-Timeout;
  keine automatische Wiederholung bei Fehlern oder Rate Limits.
- Quelltext und Markdown bleiben Referenzdaten und werden nicht ausgeführt oder
  als HTML gerendert. Bestehende Anhangs-, Dialog- und Kontextgrenzen gelten weiterhin.

Die Integration folgt der offiziellen [GitHub Contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content).
GitHub erlaubt diese Leseanfragen für öffentliche Ressourcen ohne Authentifizierung.
Es wird kein fremder Connector-Code übernommen. Der Connector gewährt keine
Lizenzrechte an eingelesenen Inhalten; Herkunft bleibt im Snapshot erhalten.

## Abnahme am 30.09.2026

Der echte Abruf von `Anil-matcha/Open-Dots`, `README.md`, Ref `main` bestand mit Blob
`987cc9ed798712f2d21cbeef9035df4b539aeb26`; Snapshotgröße 11.127 Bytes. Im Browser wurde
derselbe Weg über Vorschau, Übernahme und Versand durchlaufen. Der Quellen-Hash kam
im Ausführungskontext an; die Demo wurde nach zwei konkreten Datei-Freigaben mit
Review abgeschlossen. Verlauf und Download blieben nach Reload erhalten. Eine
Eingabeänderung verwarf die alte Vorschau; `../LICENSE` wurde abgelehnt.

Elf gezielte Tests prüfen Connector und HTTP-/Anhangsfluss, einschließlich Redirect-
Verbot, fehlender Auth-/Proxy-Übernahme, Größen-/Text-/Hash-Grenzen, Freigabe der
Anfrageslots nach Fehlern, Origin-Schutz und unveränderlichem Wiederholungsinhalt.
Der Gesamtlauf bestand mit 154 Tests. Nachweise liegen in `.runs/qualification/`
als `github-live-preview.json`, `github-browser-result.json` und
`unittest-github-connector.log`. GitHub wurde real abgefragt; die Modellausführung
war ausschließlich die deterministische Demo.
