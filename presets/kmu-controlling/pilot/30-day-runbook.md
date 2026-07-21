# 30-Tage-Runbook

## Tage 1–3: Rahmen festlegen

- Pilotverantwortung, Freigebende und einen Monatszeitraum festlegen.
- Datenvertrag prüfen; Saldenliste oder BWA bereitstellen.
- Konten-Mapping kopieren, anpassen und fachlich freigeben.

## Tage 4–7: Trockenlauf

- Struktur, Summen, Vorzeichen, Zeitraum und Währung abstimmen.
- Fehlende oder doppelte Mappings schließen; Materialitätsgrenze dokumentieren.
- Ersten Entwurf erzeugen, ohne externe Weitergabe.

## Tage 8–14: Drei Wiederholungsläufe

- Identische Eingaben dreimal ausführen.
- KPI-Werte, Quellen und Priorisierung vergleichen.
- Laufzeit ab validierter Eingabe bis zum Entwurf messen.
- Prüfen, dass `artifacts/acceptance-evidence.json` drei identische KPI-Hashes belegt.

## Tage 15–21: Fachliche Abnahme

- Abweichungen mit Buchhaltung oder Controlling nachvollziehen.
- Optional Budget und OP-Liste ergänzen; Einschränkungen ohne diese Daten prüfen.
- Freigabeprozess mit einem nicht versendeten Testentwurf durchführen.

## Tage 22–27: Betriebsprobe

- Stündlichen Loop überwachen: neue Datei, geänderte Datei, Leerlauf und Fehlerfall testen.
- Täglich `py agent_cli.py status --instance <pfad>` prüfen und Ampel, Fehlerzähler sowie nächsten Betreiber-Schritt dokumentieren.
- Prüfen, dass Leerlauf keine Analyse startet und Fehlergrenze den Loop sicher einfriert.
- Offene Punkte, Verantwortliche und Termin dokumentieren.

## Tage 28–30: Entscheidung

- Die Pilot-Ampel muss `GRÜN – pilotbereit` zeigen.
- Automatischen Nachweis in `artifacts/acceptance-evidence.json` gegen `acceptance-criteria.json` prüfen.
- Ergebnis als bestanden, nachzubessern oder gestoppt festhalten.
- Nur bei bestandener Abnahme den nächsten Datenzeitraum oder weitere KPIs freigeben.
