# Dateianhänge im Arbeitsdialog

In `/chat` Dateien auswählen, Namen prüfen und **Senden** drücken. Erst dann werden
die Dateien lokal hochgeladen und mit der Nachricht an den ausgewählten Backendlauf
übergeben. Ein Klick auf den Dateinamen im Verlauf lädt die unveränderten Originalbytes.

## Unterstützter Umfang

- UTF-8, optional mit BOM: `.txt`, `.md`, `.csv`, `.json`, `.yaml`, `.yml`, `.log`,
  `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`, `.sql`, `.xml`, `.toml`.
- PDF mit eingebettetem Text, DOCX-Absätze/Tabellen, XLSX-Zellen und PPTX-Folientext.
  Formeln werden als Text samt vorhandenem Cachewert gelesen, niemals berechnet.
- PNG/JPEG mit lokaler Windows-OCR: nur erkannter Text, keine visuelle Bildanalyse.
  Einzelbilder bis 4096 Pixel je Seite und insgesamt 8 Millionen Pixel; keine Animationen.
- Höchstens 32 KiB Originalbytes pro Textdatei, 2 MiB pro Dokument oder Bild, fünf Anhänge
  und insgesamt 2 MiB pro Nachricht in der Oberfläche; 20 Dateien und 8 MiB pro Dialog.
- PDF: maximal 100 Seiten. Dokumenttext: maximal 48.000 Zeichen je Datei.
- Anhänge einschließlich früherer Nachrichten zählen zum expliziten Kontextlimit.
  Zu große Nachrichten werden vor dem Start abgewiesen; Inhalte werden nicht still gekürzt.
- OCR gescannter PDFs, andere Bildformate, alte binäre Office-Formate, Makros und
  verschlüsselte Dokumente werden nicht unterstützt. Office-Dateien mit externen Beziehungen werden abgewiesen.
  Formatierung, Grafiken, Kommentare und andere Nebenbestandteile werden nicht vollständig
  abgebildet. PDF-Lesereihenfolge ist keine Garantie für das visuelle Seitenlayout.

Dateien sind Referenzdaten. Sie werden nicht in den ausführbaren Workspace kopiert,
nicht importiert und nicht als Code gestartet. Das Modell erhält Text und Metadaten
mit einem ausdrücklichen Hinweis, dass Dateiinhalte keine neue Handlungsbefugnis erteilen.
HTML und Quelltexte werden beim Download als Anhang mit `nosniff` ausgeliefert.

Die Dokumentextraktion läuft in einem separaten Prozess mit acht Sekunden Zeitlimit
und gefilterter Umgebung ohne Provider-Schlüssel. Archive werden ausschließlich im
Speicher gelesen: maximal 256 Einträge, 4 MiB je entpacktem Eintrag und 8 MiB insgesamt.
XML-DTDs und Entities sind gesperrt. PDF-Dekompression und Seiten-Contentstreams sind
begrenzt. Dies ist keine Betriebssystem-Sandbox für beliebige feindliche Dokumente.

## Lokale Bild-Texterkennung

PNG/JPEG werden beim ausdrücklichen Senden lokal mit der installierten Windows-OCR
verarbeitet. Es werden keine Bilder an einen OCR-Dienst geschickt und keine Modelle
nachgeladen. Deutsch wird verwendet, wenn installiert; andernfalls eine verfügbare
installierte englische OCR-Sprache (en-US). Fehlt eine passende Windows-OCR, wird der Upload
abgewiesen. Andere Betriebssysteme sind für diese Funktion nicht qualifiziert.

Die Oberfläche kennzeichnet den Anhang als OCR-Text mit der verwendeten Sprache.
Erkennungsfehler sind möglich; insbesondere Zahlen, Tabellen, Handschrift und
Lesereihenfolge benötigen eine Prüfung anhand des herunterladbaren Originals.
Ein Bild ohne erkannten Text wird abgewiesen. Das Modell erhält ausschließlich
erkannten Text und Metadaten; Bildinhalte werden nicht visuell interpretiert.

Der OCR-Prozess erhält maximal zwölf Sekunden und dieselbe gefilterte Umgebung
wie die Dokumentextraktion. Bildabmessungen werden vor der Bitmap-Dekodierung
begrenzt. Die Windows-Bilddecoder sind keine Sandbox für beliebige feindliche Dateien.
Erkannter Text, Methode und Sprache bleiben mit dem Original gespeichert;
Wiederholung, Neustart und Download führen keine erneute OCR aus.

## Speicherung und Wiederholung

`cockpit/.runs/attachments/<dialog-id>/<datei-id>.json` enthält Originalbytes,
extrahierten Text, SHA-256 und die Bindung an Dialog, Company, Agent und Workspace. Die lokale
Speicherung ist nicht verschlüsselt und gehört zum zugriffsgeschützten Studio-Backup.
Eine Dateiauswahl allein löst keinen Modellaufruf aus.

Uploads haben stabile Anfrage-IDs. Derselbe Upload kann nach einem Verbindungsfehler
ohne Duplikat wiederholt werden; veränderter Inhalt unter derselben ID wird abgewiesen.
Nachrichten binden ihre Anhangsliste in dieselbe Idempotenzprüfung ein. Nach einem
unterbrochenen Start werden Nachricht und ursprüngliche Anhänge ausdrücklich zur
Wiederholung vorbereitet. Es gibt keinen automatischen Neustart.

Gespeicherte Anhänge bleiben unverändert. „Entfernen“ vor dem Senden entfernt die
Referenz aus dem Nachrichtenentwurf; bereits hochgeladene Dateien bleiben im lokalen
Dialogbestand und zählen weiterhin zum Dialoglimit.

## Abnahme

`tests/test_attachments.py` und `tests/test_conversation_attachments.py` prüfen
Originalbytes, Integrität, parallele Wiederholungen, Quoten, Kontextgrenzen,
Company-/Dialogbindung, Herkunftsschutz, Downloadheader und unterbrochene Starts.
Das Release-Skript prüft Kontextübergabe und Download nach Rekonstruktion des Servers.
`tests/test_document_extract.py` und `tests/test_document_attachments.py` ergänzen
echte synthetische PDF-/Office-Fixtures, Seiten-/Text-/Archivgrenzen, Formeltexte,
Folienreihenfolge, DTD-/Relationship-Schutz, Subprozessfehler und Unicode-Kontext.

Browser-Abnahme am 30.09.2026: Dialog `66e039aa5c364d04aa781b71980cd12b`, Job
`daf6eab85cb64c69831e59bf9df2bc49`. Eine echte Dateiauswahl wurde hochgeladen,
als Link angezeigt, im Ausführungskontext nachgewiesen und heruntergeladen.
Nach Reload blieb der Anhang sichtbar. Der Demo-Lauf endete mit bestandenem Review.
Eine Datei über 32 KiB einschließlich BOM und eine Datei mit NUL-Byte wurden bereits
im Browser abgewiesen. Dies ist eine Offline-Abnahme, keine Prüfung der Modellantwortqualität.
Zusätzlich wurde ein zu großer Gesamtkontext abgewiesen. Ein danach entfernter,
bereits hochgeladener Anhang blieb auch nach Reload aus dem Entwurf entfernt.

Dokument-Abnahme am 30.09.2026: Dialog `8e2c195420cd4139b5b2a4624558be10`,
Job `d59631120cd14a7f8869e79a6dbc152b`. Eine synthetische DOCX mit exakt 2 MiB
blieb nach einem abgewiesenen Start und Reload im Entwurf, wurde danach hochgeladen,
im Ausführungskontext nachgewiesen und über den Browser heruntergeladen. Die Demo
schloss mit Review ab. PDF-Dialog `9d6b87221c994add873d89b7d9bb8ae8` prüfte die
Ablehnung eines PDFs ohne Text, das Entfernen dieses Anhangs und Erhalt der Änderung
nach Serverneustart/Reload; die gültige PDF erreichte anschließend den Auftragskontext.
Vollständiger Prüflauf: 137 Tests; Dokument-Fokus nach den letzten kleinen Korrekturen:
14 Tests; Ruff und 17 Offline-Release-Prüfungen bestanden. Ein früherer paralleler
Volltest meldete einmal einen Demo-HTTP-Fehler; der isolierte Wiederholungstest und
der anschließende vollständige Lauf bestanden. Die Testdiagnose gibt jetzt auch den
Jobfehler aus. Diese Evidenz umfasst keine Live-Modellantworten.

Bild-Abnahme am 30.09.2026: Dialog `c0a432e0280f4c9a8dc5a72a3fea9053`,
Job `f4153be62d24441e8834194dd6d6172d` im isolierten Testserver. PNG über echte
Dateiauswahl gesendet, Kennzeichnung `OCR-Text (de-DE)`, erkannter Marker im
Auftragskontext, zwei ausdrückliche Demo-Freigaben und bestandenes Review.
Nach Server-Neustart blieb der Anhang im Dialog sichtbar; Browserdownload ausgelöst
und Originalbytes zusätzlich per HTTP bytegleich geprüft. PNG und JPEG sowie
`Grüße für Österreich` wurden durch die echte installierte OCR verarbeitet.
Ein anfänglicher Integrationsfehler während der Umsetzung wurde behoben; die
damalige vollständige Abnahme bestand mit einem Windows-Symlink-Skip; Ruff und
19 Checks mit
`python scripts/verify_release.py --windows-ocr`. Ohne diesen expliziten Schalter
bleibt das plattformübergreifende Release-Gate bei 18 Checks; der OCR-Nachweis darf
dann nicht daraus abgeleitet werden. Keine Live-LLM-Qualifikation.

Ein leeres PNG wurde im Browser abgewiesen, ohne einen weiteren Job zu erzeugen.
Der Entwurf blieb erhalten; nach Entfernen des Bilds und Reload blieb es entfernt.
