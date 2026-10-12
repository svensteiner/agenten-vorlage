# Dynamischer BMD-Arbeitsablauf

Beobachten → fehlende Evidenz bestimmen → nächsten begrenzten Schritt wählen → ausführen
→ Ergebnis und Quelle prüfen → neu planen. Die Reihenfolge ist fallabhängig; eine reine
Recherche braucht keinen BMD-Schritt, ein Importfall braucht keine allgemeine Recherche.

## Intake

Vor jeder fachlichen Entscheidung erfassen:

- Mandant/Mandat in redigierter Form, Rechtsform und Wirtschaftsjahr
- Zeitraum, Steuerart, Sachverhalt, Belegquelle und offene Annahmen
- BMD-NTCS-Version, Modul, Datenbank-/Exportstand und Berechtigung
- gewünschtes Ergebnis, Frist und ob nur Entwurf, Preview oder eine autorisierte Aktion
  verlangt ist

Fehlt ein Pflichtfakt, wird `blocked` oder eine klar abgegrenzte Rückfrage erzeugt.

## Routing

1. `researcher` sucht aktuelle Primärquellen und dokumentiert Stichtag, URL/Paragraph und
   Unsicherheit.
2. `tax-advisor` ordnet Sachverhalt, Berechnung, Beleg- und Buchungsvorschlag.
3. `bmd-operator` erstellt mit freigegebenem Adapter oder Exportformat eine Vorschau bzw.
   Importdatei. Ohne Adapter bleibt der Schritt ein Bedien-/Importplan.
4. `tax-reviewer` prüft als separate read-only Rolle Fakten, Quelle, Summen, Steuerkennzeichen,
   Belegverknüpfung, BMD-Parameter und Vollmacht.
5. Nach `needs_revision` wird nur die konkrete Abweichung repariert und erneut geprüft.

Bis zur Freigabe wird mit Kopien, redigierten Daten und Preview gearbeitet. Ein echter
Commit, eine Stammdatenänderung, Fristaktion, FinanzOnline-Übermittlung, Zahlung, Signatur
oder externe Kommunikation benötigt zusätzlich eine ausdrückliche Autorisierung. Eine
Review-Freigabe allein ist keine solche Autorisierung.

## Kontrolliertes Lernen

Korrekturen werden als Kandidat mit Fall-ID, Datum, Ursache, Änderung, BMD-Version/Modul,
Quellen, Gültigkeitsbereich, Konfidenz und Reviewer abgelegt. Nur `approved`-Notizen aus
`workspace/knowledge/approved/` dürfen als Arbeitshilfe geladen werden. Bei Konflikten oder
zeitabhängigem Recht gilt die aktuelle Primärquelle; nichts wird still überschrieben.

## Abschlussformat

Jeder Schritt liefert `status`, `summary`, `artifacts`, `evidence` und `next_actions`.
`success` verlangt nachvollziehbare Evidenz. `needs_revision` nennt Datei/Belegstelle und
konkrete Korrektur. `blocked` nennt fehlende Berechtigung, Quelle, Belege, Adapter oder
Entscheidung. Abschließen erst nach erfolgreichem Review des letzten Schreibschritts.

## Daten- und Laufzeitgrenzen

Keine Credentials, IBANs, Steuernummern oder vollständigen Mandantenbelege in Prompts,
Checkpoints oder Lernnotizen. Aufbewahrungspflichten und Löschfristen werden mit dem
zuständigen Büro geklärt; der Agent löscht keine Originale. Limits für Schritte, Zeit,
Fehler und Kontext stehen in `agent.json`. Native Harness-Läufe müssen diese Regeln im
jeweiligen Host ebenfalls durchsetzen.

