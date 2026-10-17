# Lokale Ausfuehrungsprofile: gemeinsame Abnahme

Der Host bindet Profil-ID, Agent, Workspace, Backend, genaue Schreibdateien und
Testmanifest. Der Browser waehlt nur die ID. Autonomes Schreiben verlangt sowohl
Schreibpolicy als auch eine gepinnte Testsuite; aktueller Hostpass und separates
Review bleiben Abschlussbedingungen. Profile sind im oeffentlichen Modus gesperrt.

Die [Quell- und Logbindung](summary.json) dokumentiert den gemeinsamen Vollauf:
540 Faelle, 536 bestanden, vier Skips, acht ausgefuehrte Browser-Tests,
80-Prozent-Coverage-Grenze bestanden, Ruff und Bandit ohne Befund sowie 16
Release-Gates. Alle 104 ueberwachten Quelldateien blieben unveraendert.
Die Browserreise prueft Auswahl, gespeicherte Konversation, wiederhergestellten
Entwurf sowie verschwundenes Profil mit sichtbarer Warnung und ohne Absenden.

Die UI-Pruefung verwendet eine lokale Fixture, keinen echten Modellauftrag und
keinen Dockerlauf. Die [separate native Leseprobe](../host-observations-20261017/native-read-probe.json)
belegt genau eine Host-Leseaktion und die korrekte Folgeantwort. Der
[fehlgeschlagene Coding-Auftrag](../host-observations-20261017/native-task-attempt.json)
bleibt ein Fehlversuch. Gesamtauftrag, Marketingqualitaet und Produktionsreife
sind weiterhin offen.
