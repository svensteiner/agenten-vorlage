# Reale Qwen-Abnahme am Marketingbot

## Aktueller Stand, 13.10.2026

Die Blindbewertung der normalen X-Generierung erfüllt die vereinbarten
Freigabekriterien nicht. Pro Modellpfad wurden 18 Ausgaben als neun Paare aus
drei identischen Belegbriefings und drei Wiederholungen verglichen. Die
Zeichenlängen wurden mit Python-Unicode-Zählung nachgeprüft; diese Prüfung änderte
die Bewertungen nicht.

| Modellpfad | Kandidat bevorzugt | Kandidaten-Hard-Fails | Mittlerer Vorsprung über fünf Dimensionen | Kosten |
|---|---:|---:|---:|---:|
| Lokales Qwen 30B | 4/9 | 9 | +0,156 | lokal |
| OpenRouter Haiku 4.5 | 5/9 | 6 | +0,489 | rund 0,078 USD |

Freigabe erfordert null Kandidaten-Hard-Fails, mindestens 7/9 Präferenzen und
mindestens +0,5 mittleren Vorsprung. Beide Modellpfade verfehlen die Kriterien.
Der Haiku-Kandidat liegt auch beim Mittelwert knapp unter der Grenze. Die
Bewertungen gelten nur für diese Beispiele. Sie belegen keine Impressions,
Replies, Engagement oder Reichweite auf X.

Qwen hat eine Persona-Änderung und vier passende Tests in einer privaten
Qualifikationskopie erstellt. Beim ersten privaten Kandidaten bestanden 138 von
140 Tests. Zwei beanstandeten fehlende Persona- und Formulierungsanker:
Wingsurfer/Sportler sowie „Fehlt diese Zuständigkeit“ und „Kein erzwungenes
Entweder-oder“. Diese Fassung wurde nachgebessert; der unabhängig geprüfte
reparierte Prompt besteht nun alle 140 Schutztests. Die separat gemeldeten
Baseline-Zahlen von 3 Fehlschlägen und 1 Erfolg stammen aus einem anderen
Vergleich. Nichts davon wurde in den Original-Bot übernommen.

Drei kontrollierte Vorher-/Nachher-Prompt-Captures mit identischen
Belegbriefings, Stimmen und Formaten sind erfasst. Tatsächliche Modell-Ausgaben
wurden noch nicht verglichen. Es gab keine Übernahme in den Original-Bot, keinen
Neustart und keine Veröffentlichung. Die Arbeit erfolgte mit
Operatorunterstützung; ein autonomer Marketingzyklus ist nicht nachgewiesen.

Letzter gemeldeter Laufzeitstand: 405 Tests bestanden, drei Skips und 19
Offline-Gates bestanden. Ein frischer Hashcheck verglich die 502 Einträge des
bestehenden Manifests `.runs/qualification/qwen-marketing-baseline.json` mit den
manifestierten Quelldateien im Originalprojekt: 502 Treffer, null Abweichungen,
fehlende oder abgelehnte Pfade. Es wurden keine Zugangsdaten oder Profile
geprüft. Der Check attestiert nur die gelisteten Dateien, nicht sonstige Dateien
oder Prozesszustände. Der Scheduler wurde zuletzt schlafend gemeldet, nächster
Lauf 12:20 Uhr (Europe/Vienna); daraus folgt keine Aussage über einen früheren
Child-Prozess oder eine PID.

**Ergebnis: autonome Marketingverbesserung nicht nachgewiesen; Live-Freigabe nicht bestanden.**

## Historischer Stand bis 12.10.2026

**Ergebnis: autonomer Projektauftrag nicht bestanden.** Kein Nachweis besserer Posts.

## Fortgesetzte reale Umsetzung und Gegenpruefung

Ein separater Aider-0.86.2-Ausfuehrungsweg mit demselben lokalen Qwen-Modell
hat inzwischen echte Edits und automatische Testlaeufe in der isolierten Kopie
erzeugt. Daraus folgt weiterhin keine akzeptierte Marketingverbesserung:

- Erste Fassung: 15 Tests gruen. Alle neun neuen Tests bestanden jedoch auch
  gegen unveraenderten Baseline-Code. Ein Qualitaets-Negativtest wurde sogar
  verlaengert, damit er nur an einer alten Laengenregel scheitert. Abgelehnt.
- Zweite Fassung: zunaechst eine harte Nomen- und Erstwortpruefung. Eigene
  Gegenproben verwarfen gute Angebote/Vertraege und unterschiedliche Posts mit
  gleichem Anfangsartikel, liessen generische Kapital/Prozesse-Floskeln aber
  wegen Teilstrings durch. Qwen entfernte die Erstwortpruefung spaeter selbst;
  die verbleibende Wortliste und drei rote Tests blieben Abnahmeblocker.
- Danach wurde auch die Wortliste entfernt. Ein eigener frischer Pytest-Tempordner
  umging einen globalen Windows-Temp-Zugriffsfehler. Die echte breitere Pruefung
  ergab 69 bestandene und drei fehlgeschlagene Tests; alle bestehenden Tests
  der ausgewaehlten Persona-/Integrations-/Redaktionsgruppen bestanden.

Die Pfadpruefung identifizierte `STANDALONE_X_CONTENT_POLICY` und das Voice-Addon
als direkt in den normalen Standalone-Prompt eingebundene Bausteine. Ob der
optionale Editorial-Pfad im laufenden Prozess aktiviert ist, bleibt unbekannt.
Eine weitere Qwen-Nacharbeit adressiert deshalb auch diesen normalen Pfad.
Echte neue Regressionsnachweise, unabhaengiges Review und reale Modellausgaben
vor/nach der Aenderung sind weiterhin erforderlich. Keine dieser Fassungen wurde
in den laufenden Bot uebernommen; Original-Quellcode blieb unveraendert.

Die folgenden Abschnitte dokumentieren die vorausgegangenen AgentKit-Versuche.

Auftrag: Der lokale Coding-Agent sollte die deutschen X-Posts des bestehenden
Marketingbots konkreter und abwechslungsreicher machen, echte Tests ausfuehren
und ein separates Review bestehen. Er arbeitete mit Qwen3 Coder Next auf dem
ASUS in einer aktuellen, credential-bereinigten Git-Kopie. Der laufende Bot war
kein Schreibziel; es wurden keine X-Aktionen freigegeben.

- Erster breiter Lauf: wiederholte Recherche, Kontext-/Werkzeuggrenzen und eine
  falsche Interpretation des Live-X-Holds; keine Quellcodeaenderung. Behauptete
  Edits und Testzahlen ohne Werkzeuge wurden nicht als Erfolg akzeptiert.
- Zweiter Lauf mit explizitem 65536-Modellkontext: relevante Dateien gelesen,
  wiederholte Anfrageabbrueche; auch nach Eingrenzung keine Produktmutation.
- Kurze Gegenprobe: `run_pytest` fuer `tests/unit/test_editorial_agent.py`
  tatsaechlich ausgefuehrt, **6 bestanden in 1,17 Sekunden**. Anschliessend einen
  neuen Test vorgeschlagen, aber vor dessen Schreiboperation an der
  Laufzeit-Kontextgrenze gestoppt. Keine Produktmutation und kein finales Review.
  Einige vorgeschlagene Negativtests hatten ausserdem zu kurze Texte und koennten
  deshalb vorhandene Laengengrenzen statt der behaupteten Redaktionseigenschaft
  pruefen. Ein solcher Testvorschlag belegt keine Inhaltsverbesserung.

Die Abnahme wurde mit Operatorhilfe wiederholt; selbst ein spaeterer Erfolg
dieser Versuche waere kein Beleg vollkommen unbeaufsichtigter Arbeit.
Werkzeugprotokolle und Checkpoints bleiben lokal unter `.runs/qualification/`.

Ein früherer Schutzcheck meldete 502 unveränderte Original-Quelldateien; Bot und
Scheduler wurden damals als aktiv gemeldet. Der frische Manifestvergleich oben
bestätigt jetzt die 502 gelisteten Quelldateien. Er sagt nichts über den heutigen
Prozessstatus aus. In der Kopie entstanden testbedingte Diagnoseartefakte,
aber keine Qwen-Quellcodeaenderung. Der kuratierte Testbaseline umfasste 81 bestandene
Tests. Der breitere Unit-Baseline hatte schon vorher 23 Fehler, 3860 bestandene
Tests, 11 Skips und 5 erwartete Fehler; er war keine vollstaendig gruene Abnahme.

Damals geprüfte Laufzeit: begrenzte Zeilenreads/Literalsuche, weiterhin endliche
Workspace-Bindung sowie optionale begrenzte Werkzeugdiagnose ohne Quelltexte.
Diagnose-I/O kann erfolgreiche Aktionen nicht verdecken. Die unabhaengig gepruefte
Laufzeit bestand damals 404 Tests mit drei Skips und 19 Offline-Abnahmeprüfungen.
Der aktuelle gemeldete Prüfstand von 405 Tests, drei Skips und 19 Gates steht oben.
Diese Laufzeitnachweise beweisen keine autonome Marketingverbesserung durch Qwen.
