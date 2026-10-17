# Echter zentraler Marketing-API-Weg: Protokoll belegt, Semantik gescheitert

V2 fuehrt die beiden vorher festgelegten synthetischen Faelle ueber den echten
zentralen LLMResponder.generate_freeform aus. Der Diagnoseadapter validiert den
bereits vom Produktionskandidaten erzeugten Request und veraendert dessen
Payload nicht. OpenRouter/Haiku liefert drei Reviews und eine Reparatur:
vier physische Aufrufe, vier TaskBudget-Attempts, 0,006543 USD gemeldete Kosten,
keine unbekannten Ausgaenge oder Kosten. Die lokale Reservierung ist 0,20 USD;
es existiert keine vom Anbieter erzwungene Kostengrenze. Status diagnostic_complete.
Kein Live-X-Versand, keine Aktivierung oder Promotion des Kandidaten.

## Kritischer Befund

Der korrekte Kontrollentwurf erscheint quellentreu. Der reparierte falsche
Entwurf entfernt zwar bezahlt/automatisch und bewahrt den unbekannten
Zahlungsstatus. Aus der Quelle 'A controller must approve release' wird aber
'Freigabe erfordert Kontrolle': Der menschliche Akteur und dessen notwendige
Zustimmung fehlen. Der abschliessende Reviewer akzeptiert dies und meldet die
Kontrolle als bewahrt. Die unabhaengige Pruefung wertet das als False-Accept.
Das Weglassen von matched ist ebenfalls im Audit erfasst.

**Semantische Abnahme fehlgeschlagen.** Vier technische Erfolgsantworten und
diagnostic_complete sind keine fachliche Freigabe. Die frueheren v3/v4-Befunde
bleiben verbindlich. Diese bekannten synthetischen Faelle sind kein neuer
Blindtest und keine Messung besserer Marketingqualitaet.

## Erhaltener Fehlversuch und Tests

V1 stoppt vor HTTP mit AttributeError: Der Diagnosehelfer erwartet budget.halted,
die echte TaskBudget-Klasse bietet exhausted. Null Requests, null Attempt,
null Reservierung/Kosten. Seine Dateien/Resultate bleiben unveraendert und
sind im neuen V2-Helper extern gepinnt. V2 korrigiert dies als separaten Versuch.
Die zehn Offline-Tests enthalten jetzt den gesamten run()-Pfad mit echtem
TaskBudget und Responder sowie ausschliesslich gemocktem physischen Transport.
Die in diesem Offline-Log sichtbaren vier Requests/0,004 USD sind Testdaten,
keine echten Anbieteraufrufe. V1 hatte acht Offline-Tests bestanden; deren
begrenzter Umfang hatte den aeusseren Loop-Fehler nicht erfasst.

Helper, Offline-Tests/-Logs, Prepared-/Result-/Reviewbelege, echte Live-Logs
und unabhaengiger semantischer Audit liegen bei. Requestheader/Schluessel
werden nicht persistiert; rohe Antwortinhalte sind ausschliesslich die festen
synthetischen Daten. Volltest- und Quellbindung siehe
[isolierten Kandidaten](../source-typed-central-20261017/README.md).
