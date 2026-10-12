# Reale Qwen-Abnahme am Marketingbot, 12.10.2026

**Ergebnis: autonomer Projektauftrag nicht bestanden.** Kein Nachweis besserer Posts.

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
