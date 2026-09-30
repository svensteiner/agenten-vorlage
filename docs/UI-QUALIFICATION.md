# Prüfung schmaler und großer Ansichten

Am 30.09.2026 mit dem echten lokalen Server und Browser geprüft. Es wurde kein
Geräteemulator als Nachweis für native mobile Betriebssysteme verwendet.

| Ansicht | 390 × 844 | 1440 × 1000 |
|---|---|---|
| Aufträge | Navigation, horizontale Listen, kein Seitenüberlauf; Erstellformular vollständig bedienbar, Abbrechen geprüft | Kein Seitenüberlauf |
| Dialog | Bestehender Verlauf, Anhangslink, Composer und Verwaltungsnavigation erreichbar | Verlauf, Composer und GitHub-Felder visuell geprüft |
| Provider | Navigation, Status und Formularbereich ohne Seitenüberlauf | Kein Seitenüberlauf |
| Assistentenverwaltung | Geladene Liste mit langen Pfaden und Aktionsbuttons ohne Seitenüberlauf | Geladene Liste ohne Seitenüberlauf |

Zusätzlich wurde der Dialog bei 320 × 740 geprüft: zweispaltige GitHub-Eingaben,
Dateiauswahl und Vorschau-/Senden-Bereich bleiben innerhalb der Seitenbreite.
Der Tastaturfokus war beim Wechsel zwischen GitHub-Feldern sichtbar.
Die temporäre Browsergrößen-Vorgabe wurde nach der Prüfung zurückgesetzt.

Zwei Fehler wurden dabei behoben:

- Unter 760 Pixeln blendete der Dialog den gesamten Navigationsfooter aus. Dadurch
  waren Aufträge, Provider und Assistentenverwaltung nicht über die Oberfläche
  erreichbar. Der Footer bleibt jetzt sichtbar; seine Links besitzen mindestens
  44 Pixel Höhe.
- Im breiten GitHub-Formular stand die Pfad-Beschriftung neben dem Eingabefeld,
  während andere Beschriftungen darüber lagen. Alle vier Labels verwenden jetzt
  dieselbe vertikale Anordnung.

Dies ist eine gezielte Responsive-/Bedienungsabnahme, kein vollständiges
Barrierefreiheitszertifikat. Die folgende Computer-Use-Prüfung ergänzt Kontrast,
Tastatur und Reflow; eine formale Screenreader-Zertifizierung und weitere
Browser-/Betriebssystemkombinationen bleiben offen.

## Accessibility- und Reflow-Prüfung

Computer Use prüfte am 30.09.2026 den laufenden lokalen Server:

- Alle 29 sichtbaren interaktiven Elemente der geprüften Ansichten besaßen einen
  zugänglichen Namen.
- Der Tastaturpfad zeigte einen nachvollziehbaren sichtbaren Fokus.
- Der native Assistenten-Dialog setzte den initialen Fokus, schloss mit Escape und
  gab den Fokus an den auslösenden Button zurück.
- 62 sichtbare Textfälle bestanden die berechnete WCAG-Kontrastprüfung.
- Bei einer halbierten Layoutbreite von 588 CSS-Pixeln blieb der Seiten-Reflow ohne
  horizontalen Überlauf.

Diese Messungen ergänzen die 320-/390-/1440-Pixel-Abnahme. Sie sind kein formaler
Test mit einem Screenreader und keine Zertifizierung aller Browser-, Betriebssystem-
oder Zoomkombinationen.

## Assistenten-Vorgaben bearbeiten

Separater lokaler Fixture-Server, ohne Modellaufruf, am 30.09.2026 geprüft:

- Unicode-Vorgaben speichern und nach Seiten-Reload unverändert laden.
- Zwei gleichzeitig geöffnete Editoren: veraltetes Speichern wird abgelehnt;
  der Entwurf bleibt erhalten. Bewusstes Neuladen übernimmt die aktuelle Revision.
- Serverausfall während Speichern: kein Erfolg behauptet, Entwurf bleibt erhalten,
  Speichern gesperrt. Nach Server-Neustart aktiviert ein Listen-Reload das Speichern
  nicht erneut; erst das bewusste Neuladen der Vorgaben löst den unklaren Zustand.
- Der Editor erhält nach dem Laden sichtbaren Tastaturfokus.
- Bei 390 × 844 bleiben Text, Revisionshash und alle drei Aktionen erreichbar.
  Ein Überlauf durch den langen Hash wurde durch gezielten Textumbruch behoben;
  kein globales Verbergen von horizontalem Überlauf. Gemessen: Seitenbreite 375
  innerhalb eines Viewports von 390 Pixeln mit vertikaler Scrollbar.

Das Offline-Release-Gate prüft zusätzlich zwei konkrete Freigaben nach Änderung
der Vorgaben und Server-Neustart: der alte Auftrag verwendet seinen gespeicherten
Core, ein neuer Auftrag die neuen Vorgaben. Dies ist ein Demo-/Vertragsnachweis,
keine Live-Modellqualifikation.

## PNG-/JPEG-Anhänge

Am 30.09.2026: echter PNG-Dateidialog, lokale OCR-Kennzeichnung mit Sprache,
Übernahme in den Auftragskontext, beide Demo-Freigaben und Abschluss geprüft.
Nach echtem Server-Neustart blieb der Downloadlink sichtbar; Browserdownload
ausgelöst und Originalbytes zusätzlich per HTTP verglichen. Ein leeres PNG
wurde ohne neuen Auftrag abgewiesen; Entfernen und Reload behielten die Korrektur.
Native PNG-/JPEG- und deutsche Unicode-OCR zusätzlich in automatisierten Tests;
keine Live-LLM-Abnahme. Einzelheiten und IDs: ATTACHMENTS.md.

## Sichtbare dynamische Workflow-Spur

Die Auftragsansicht projiziert protokollierte Entscheidungen, Berichte,
`in_flight` und wartende Freigaben in eine navigierbare Ablaufspur. Sie stellt
keinen festen Ablaufplan dar. Ungeklärte Ausgänge bleiben ausdrücklich ungeklärt;
ein erfolgreicher Gesamtstatus macht fehlende Einzelberichte nicht erfolgreich.
Demo-Läufe sind gekennzeichnet. Bewegung ist auf laufende Schritte begrenzt und
respektiert `prefers-reduced-motion`.

Computer-Use-Abnahme am 30.09.2026: Job
`27ed9d492e7a4b89821ba8d1c814e556`, Run
`3129f1b95e274a9b80e721ba1ed1415f`. Erste Dateiaktion freigegeben, fehlgeschlagenes
Review gesehen, Server vor zweiter Freigabe neu gestartet. Gleiche Freigabe-ID
`9f479ca749e144a9be8b2249f7542643` wiederhergestellt, Korrektur freigegeben,
frisches Review und Abschluss bestätigt. Download im Browser ausgelöst;
zusätzliche HTTP-Prüfung: 200, Attachment, erwartete Datei mit ACCEPTED.

Bei 320 × 800: Dokumentbreite 305, Ablaufspur 231 Pixel mit internem Scrollbereich
580 Pixel; kein Seitenüberlauf. Bei 1440 × 900: Dokumentbreite 1425, Ablaufspur
722 Pixel ohne eigenen Überlauf. Nachweislink mit Enter aktiviert und Ziel
`#timeline-step-1` sichtbar. Zehn Zustandsfälle über
`node scripts/test_workflow_trace.cjs` geprüft; unabhängiges Code-Review bestanden.
