# Hostbeobachtungen: technische Abnahme

Die Hostwerkzeuge liefern begrenzte Datei-, Verzeichnis- und Git-Beobachtungen.
Der Host sperrt bekannte Zugangsdatenpfade und behandelt die Ergebnisse als
unvertrauenswuerdige Daten. [Vertrag und Grenzen](../../HOST-OBSERVATIONS.md).

Die [Zusammenfassung](summary.json) bindet Quellen und private Rohlogs per SHA-256.
Windows und Linux bestehen jeweils 73 fokussierte Tests; Windows ueberspringt
einen Fall. Ruff, Bandit ab mittlerer Schwere und 16 Release-Gates bestehen.
Der neue Vollauf besteht 528 Faelle: 524 bestanden, vier Skips, keine Fehler.
Kombinierte Zeilen-/Branch-Abdeckung: 80.4805 Prozent; die 80-Prozent-Grenze besteht.

Eine echte native Probe mit gpt-6-luna lieferte eine hostvalidierte Antwort im
korrigierten Schema: ein Adapteraufruf, keine ausgefuehrten Agentenaktionen.
Physische Anbieteranfragen und Kosten sind nicht bekannt. Diese Probe belegt
keinen autonomen Coding-Auftrag, keine Marketingqualitaet und keine Produktionsreife.

Fruehere Fehlversuche bleiben erhalten. Die zuerst entdeckten Git-Pfad-Lecks,
Filterluecken und Austausch-Races wurden mit eigenen Regressionen korrigiert.
Der vorzeitig unterbrochene erste Vollauf zaehlt nicht als bestanden; ebenso
bleiben die rote POSIX-Testfixture und die fehlgeschlagene erste Schema-Probe
getrennte historische Befunde. Der laufende Original-Marketingbot bleibt unberuehrt.
