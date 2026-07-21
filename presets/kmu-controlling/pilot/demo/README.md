# Sofort-Demo: erster KMU-Pilot

Die Dateien in diesem Ordner bilden den fiktiven, reproduzierbaren Referenzfall
für den ersten Pilottermin. Es werden keine Echtdaten verwendet.

## Demo in einer erzeugten Instanz starten

1. Erzeuge die isolierte Instanz:
   `py agent_cli.py create --tenant demo-kmu --agent controlling --preset kmu-controlling`
2. Kopiere `Saldenliste_Muster_Juni2026.xlsx` nach
   `inbox/actuals/Saldenliste_Muster_Juni2026.xlsx`.
3. Kopiere `account-mapping.json` nach
   `project/pilot/account-mapping.json`.
4. Starte denselben Entwurf dreimal, um die reproduzierbare Abnahme zu belegen:
   `py agent_cli.py run --instance instances/demo-kmu/controlling --task "Erstelle den belegten Monatsreport"`.
5. Öffne `instances/demo-kmu/controlling/artifacts/latest-controlling-report.html`.
   Beim dritten identischen Lauf zeigt die Konsole `Pilot acceptance: passed (3/3 repeatable runs)`.
6. Starte danach bei Bedarf den adaptiven 60-Minuten-Betrieb:
   `py agent_cli.py run --instance instances/demo-kmu/controlling --loop`.

Die Sollwerte für die Abnahme stehen in `expected-results.json`.
Die geprüften Laufbelege stehen in `artifacts/acceptance-evidence.json`; der
maschinenlesbare Bericht liegt in `artifacts/latest-controlling-report.json`.

Das Demo-Mapping enthält den vollständigen Berichtskontext: ISO-Zeitraum,
Währung `EUR`, feste Vorzeichenkonvention und `Konto` als eindeutige
Zeilen-ID. Diese Metadaten erscheinen unverändert im lokalen Rechenbericht.
Monat/Vormonat sind je Zahlenkonto vollständig; YTD/YTD-Vorjahr sind für alle
GuV-Gruppen vollständig, während Bilanzgruppen dort leer sein dürfen.

Das Mapping gilt bewusst nur für diese Demo-Datei. Bei einem Kunden werden
Zeitraum, Währung, Zeilen-ID, Spalten, Kontengruppen, Vorzeichen und
Materialitätsgrenze fachlich neu
freigegeben. Der Agent darf ein unvollständiges oder mehrdeutiges Mapping nicht
durch Schätzungen ersetzen.
