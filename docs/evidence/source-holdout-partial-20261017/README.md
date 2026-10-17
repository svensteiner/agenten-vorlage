# Teilweise semantische Modellpruefung: keine Gesamtfreigabe

Der vorab unabhaengig gepruefte v5-Helfer verwendete den tatsaechlichen zentralen
Marketingbot-Responder und den eingefrorenen Coding-Kandidaten. Sechs Offline-
Tests bestanden vor dem echten Lauf. Der laufende Originalbot blieb unberuehrt.

Zehn physische Haiku/OpenRouter-Aufrufe kosteten zusammen 0,015775 USD; keine
unbekannten Ausgaenge oder Kosten. Der Lauf stoppte nach fuenf von zwoelf Faellen:
drei technisch akzeptiert, einer abgelehnt, einer Fehler; sieben nicht ausgefuehrt.
Die lokale Reservierung war keine beim Provider erzwungene Kostengrenze.

Ein unabhaengiger Pruefer ohne Erwartungslabels fand die drei akzeptierten Texte
quellentreu und nutzbar. Das ist ein Teilergebnis, kein bestandenes Gesamtgate:
kleine synthetische Stichprobe, ein Pruefer, sieben ungetestete Faelle, keine
X-Ergebnisse. Die bisherigen False Accepts bleiben dokumentierte Gegenbeispiele.

Beim Fehler speicherte der Helfer weder den Qualifier-Grund noch die rohe Review-
Antwort. Eine konkrete Parserursache ist aus diesem Beleg nicht ableitbar.
Es gab keine automatische Wiederholung und keine Uebernahme in den Originalbot.

[Aggregierte Originalmessungen und SHA-256-Bindungen](summary.json).
Rohresultat, Falltexte, Blindzuordnung und Erwartungslabels bleiben privat, damit
die laufende Implementierungsarbeit nicht die zurueckgehaltenen Faelle erhaelt.

## Neuer Diagnoselauf v6: Ursache belegt, Gesamtpruefung weiter offen

Eine separat gepruefte Diagnose-Ergaenzung bestand fuenf Offline-Tests und pinnt
auch deren Quelldatei. Sie veraendert weder den zentralen Request noch den
Qualifier. Neue einmalige Artefakte erhalten private Modellantworten und echte
Fehlercodes; der v5-Fehlversuch bleibt unveraendert.

V6 stoppte nach 15 Anfragen fuer 0,024394 USD, ohne unbekannte Ausgaenge oder
Kosten: sechs accepted, ein error, fuenf nicht ausgefuehrt. Ein unabhaengiger
Blindpruefer ohne Erwartungslabels bewertet alle sechs akzeptierten Texte als
quellentreu und nutzbar. Die genaue Fehler-Replaypruefung belegt ein vom Modell
nicht abgedecktes letztes Satzzeichen; die strenge Abdeckungspruefung lehnt
korrekt ab. Keine Parserlockerung und keine automatische Wiederholung.

Beide Laeufe verwenden denselben Korpus und denselben Qualifier-Kandidaten.
Die Teilergebnisse duerfen nicht zu unabhaengigen Stichproben addiert oder als
Qualitaetsverbesserung ausgegeben werden. Zwoelfteilige Abnahme weiter unvollstaendig.
[V6-Messungen und Bindungen](v6-summary.json).
