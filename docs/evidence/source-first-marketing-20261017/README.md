# Begrenzter Source-first-Nachweis

Alle Quellbriefs und Posts sind synthetische Offline-Testdaten, keine verifizierten
Kundenfaelle oder zur Veroeffentlichung freigegebene Posts.

`execution.json` dokumentiert den frischen Lauf `a66058b400bb4abeb6b4576bc84331c2`:
vier guenstige Entwurfsbatches, separates staerkeres Review, guenstige Reparatur,
erneute Ablehnung, automatische staerkere Reparatur nach zwei Revisionen, finales
Review und Abschluss. Zehn Schritte, zwei Fehlerberichte, keine Host-Reparaturhilfe;
Quellen und Agentenpaket blieben unveraendert. Aktionsfreigaben waren nur in diesem
isolierten Experiment deaktiviert; CLI und Cockpit behalten ihre Freigabepflicht.
Die leere Ausgabedatei und ihr Ordner wurden vom Host vorab angelegt.

Ein vorausgehender Versuch stoppte bereits am ersten Worker wegen eines vom
Windows-Sandboxkonto erzeugten, fuer den Host unzugaenglichen Unterordners.
Dieser Lauf wurde nicht wiederholt oder als Erfolg gezaehlt. Der korrigierte
read-only-Pruef-/Exportweg wurde an dessen echtem 1.958-Byte-Artefakt getestet.
Der erfolgreiche zweite Versuch besitzt einen neuen Workspace und Checkpoint.

Die Hostpruefung verlangt alle zwoelf Quellenidentitaeten, striktes JSON ohne
doppelte Schluessel, unterschiedliche nichtleere Texte mit maximal 190 Zeichen
und exakte Quellenzitate. Das ist keine semantische Wahrheitspruefung.

Der unabhaengige Grader erhielt nur `blind-packet.json`, mit zufaelligen Seiten
und Reihenfolge. `comparison-map.json` wurde erst nach der Bewertung fuer die
Auswertung verwendet und wird hier zur Nachpruefbarkeit offengelegt. Die Rohdaten
in `posts.json`, `source-briefs.json` und `blind-grades.json` bleiben erhalten;
`verdict.json` bindet Ausgabe, Bewertungsunterlagen und Noten per SHA-256.

| Vergleich | Neue Texte bevorzugt | Harte neue Fehler | Mittlerer Score-Abstand |
|---|---:|---:|---:|
| Alter Stand | 8/9 | 0 | +0,1333 |
| Bisherige Promptfassung | 9/9 | 0 | +0,2444 |

Beide Kontrollarme haben selbst 8/9 harte Fehler, etwa Ueberlaenge oder unbelegte
Behauptungen. Die Praeferenz ist deshalb kein Beweis breiter Qualitaetsueberlegenheit.
Die drei erstmals in diesem Lauf verwendeten Quellenbriefs erhalten im Mittel
3,8/5 ohne harte Fehler. Diese Daten sind nach ihrer Offenlegung kein frischer
Holdout fuer spaetere Versuche.

**Gesamte Textqualitaetsabnahme nicht bestanden:** Beide Abstaende unterschreiten
die vorher bestehende Grenze von +0,5. Die neun festen Faelle sind Entwicklungsevidenz.
Nur ein Blindgrader, kleine synthetische Stichprobe, keine gemessene X-Wirkung,
keine normale Marketingbot-Integration und keine Produktionsfreigabe. Native
Codex-Kosten wurden nicht vom Provider ausgewiesen.
