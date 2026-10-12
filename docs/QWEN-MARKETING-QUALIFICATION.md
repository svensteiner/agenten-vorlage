# Reale Qwen-Abnahme am Marketingbot, 12.10.2026

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

Schutzpruefung: 502 Original-Quelldateien hashgeprueft unveraendert; Bot und
Scheduler weiterhin aktiv. In der Kopie entstanden testbedingte Diagnoseartefakte,
aber keine Qwen-Quellcodeaenderung. Der kuratierte Testbaseline umfasste 81 bestandene
Tests. Der breitere Unit-Baseline hatte schon vorher 23 Fehler, 3860 bestandene
Tests, 11 Skips und 5 erwartete Fehler; er war keine vollstaendig gruene Abnahme.

Verbesserte Laufzeit: begrenzte Zeilenreads/Literalsuche, weiterhin endliche
Workspace-Bindung sowie optionale begrenzte Werkzeugdiagnose ohne Quelltexte.
Diagnose-I/O kann erfolgreiche Aktionen nicht verdecken. Die unabhaengig gepruefte
Laufzeit besteht 404 Tests mit drei Skips und 19 Offline-Abnahmepruefungen. Diese
Laufzeitnachweise beweisen keine autonome Marketingverbesserung durch Qwen.
