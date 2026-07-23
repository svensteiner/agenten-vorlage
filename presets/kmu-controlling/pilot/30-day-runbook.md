# 30-Tage-Runbook

## Produktions-Abnahmeblocker: Storage und Mandantentrennung

Vor Verwendung mit realen Mandantendaten muss der
[Storage-Sicherheitsvertrag](../../../docs/adr/ADR-0001-kmu-pilot-storage-security-contract.md)
auf dem produktionsgleichen Zielsystem nachgewiesen sein. Der P1 bleibt offen,
solange je Tenant eine eigene eingeschränkte Service-Identität, ein eigener
Prozess-/Container-/VM-/Namespace-/Volume-Scope ohne Zugriff auf fremde
Tenant-Volumes und aktuelle Produktions-Evidenz fehlen. ACLs sind zusätzliche
Härtung; mehrere Mandanten unter demselben OS-Principal sind nicht unterstützt.

Ein erfolgreicher Pfad-/Symlink-Preflight ist nur Defense-in-depth und hebt den
Blocker nicht auf. Jeder Mandant darf nur seine eigenen `inbox/`, `data/` und
`imports/` beschreiben und Eingaben anderer Tenants weder lesen, auflisten,
schreiben, löschen noch umbenennen. Ehemals außerhalb von `inbox/`, `data/` oder
`imports/` tenant-writable Instanzbäume sind vor der Abnahme offline unter
einer servicekontrollierten Parentkette neu zu provisionieren.

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
- Prüfen, dass jeder Lauf denselben `approval_policy_hash` mit aktivem
  Freigabe-Gate, den Begriffen `external communication`, `send`, `publish` und
  keinen externen Tool-Fähigkeiten belegt.

## Tage 15–21: Fachliche Abnahme

- Abweichungen mit Buchhaltung oder Controlling nachvollziehen.
- Keine Budget- oder OP-Dateien für diesen Pilotlauf bereitstellen oder im
  Bericht erwarten: Der aktuelle Pilot liest und analysiert sie auch bei
  Vorliegen nicht. Budgetabweichung und Forderungsalterung müssen sichtbar als
  nicht verfügbar / nicht verarbeitet erscheinen. Eine zukünftige Aktivierung
  erfordert einen separat versionierten und fachlich reconcilierten Umfang.
- Freigabeprozess mit einem nicht versendeten Testentwurf durchführen.

## Tage 22–27: Betriebsprobe

- Stündlichen Loop überwachen: neue Datei, geänderte Datei, Leerlauf und Fehlerfall testen.
- Täglich `py agent_cli.py status --instance <pfad>` prüfen und Ampel, Fehlerzähler sowie nächsten Betreiber-Schritt dokumentieren.
- Prüfen, dass Leerlauf keine Analyse startet und Fehlergrenze den Loop sicher einfriert.
- Die Testmatrix des Storage-Sicherheitsvertrags mit zwei synthetischen Tenants
  ausführen. Insbesondere im eigenen Input einen Link bzw. unter Windows eine
  Junction auf den fremden Scope anlegen und belegen, dass der eigene Dienst
  fail-closed ablehnt und keinerlei Cross-Scope-I/O verursacht.
- Den manuellen Nachweis außerhalb der Tenant-Volumes ablegen: Zeitstempel und
  Gültigkeit, Deployment-/Image-/ACL-/Volume-Fingerprints, Soll-/Ist-Ergebnisse
  sowie Sign-off von Plattformbetrieb und Security erfassen.
- Offene Punkte, Verantwortliche und Termin dokumentieren.

## Tage 28–30: Entscheidung

- Den Produktionsnachweis gemäß Storage-Sicherheitsvertrag prüfen und als
  Abnahmebeleg referenzieren; veraltete oder unvollständige Evidenz hält den P1
  offen und die Entscheidung lautet `gestoppt`.
- Die Pilot-Ampel muss `GRÜN – pilotbereit` zeigen.
- Festhalten, dass die grüne CLI-Ampel notwendig, aber ohne aktuellen
  Produktionsnachweis nicht hinreichend ist.
- Automatischen Nachweis in `artifacts/acceptance-evidence.json` gegen `acceptance-criteria.json` prüfen.
- Ergebnis als bestanden, nachzubessern oder gestoppt festhalten.
- Nur bei bestandener Abnahme den nächsten Datenzeitraum oder weitere KPIs freigeben.
