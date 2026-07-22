# Erster KMU-Controlling-Pilot

Dieser Ordner ist das betriebsfertige, kundennamensfreie Pilot-Pack. Er ersetzt weder Buchhaltung noch fachliche Freigabe.

**Produktionshinweis:** Die fachliche Pilot-Ampel allein ist keine Freigabe für
reale Mandantendaten. Vor Produktion ist der
[Storage-Sicherheitsvertrag](../../../docs/adr/ADR-0001-kmu-pilot-storage-security-contract.md)
auf dem Zielsystem nachzuweisen. Zwingend sind je Tenant eine eigene
eingeschränkte Service-Identität und ein eigener
Prozess-/Container-/VM-/Namespace-/Volume-Scope ohne Mount oder Zugriff auf
fremde Tenant-Volumes. ACLs und Anwendungs-Preflights sind nur zusätzliche
Härtung. Der P1 bleibt bis zu aktueller, signierter Produktions-Evidenz offen;
die grüne CLI-Ampel ist notwendig, aber allein nicht hinreichend.

Für den ersten Pitch und Trockenlauf enthält `demo/` einen vollständig
fiktiven Referenzfall mit Saldenliste, freigegebenem Mapping und geprüften
Sollwerten. So lässt sich die technische Kette vor Kundendaten reproduzierbar
zeigen; die Anleitung steht in `demo/README.md`.

## In fünf Schritten

1. Lege mindestens eine Saldenliste oder BWA gemäß `data-contract.json` unter `inbox/`, `data/` oder `imports/` ab; empfohlen ist der Unterordner `actuals/`.
2. Kopiere `account-mapping.example.json` nach `account-mapping.json`, passe Spalten, Gruppen, Vorzeichen, `report_metadata` und `source_globs` an und validiere die Arbeitskopie gegen `account-mapping.schema.json`. `source_globs` dürfen nur relativ unter `inbox/`, `data/` oder `imports/` liegen und müssen genau eine primäre Ist-Datei treffen. Der Loop startet erst, wenn `account-mapping.json` vorhanden ist.
3. Prüfe Zeitraum, dreistelligen Währungscode, die feste Vorzeichenkonvention und die in `row_identifier` benannte eindeutige Quellspalte.
4. Starte die Instanz mit `agent_cli.py run --instance <pfad> --loop`.
5. Öffne `artifacts/latest-controlling-report.html` und prüfe den Entwurf fachlich. Der Pilot besitzt bewusst keine Funktion zum externen Versenden.

Budget und Offene-Posten-Liste sind optional. Fehlende optionale Daten werden als Einschränkung genannt; fehlende Pflichtdaten stoppen die betroffene Auswertung. Maßgeblich sind `30-day-runbook.md` und `acceptance-criteria.json`.

Vorzeichen sind explizit: `normalisierter Wert = Quellwert × multiplier`. Im Beispiel erhöht Umsatz mit `+1` das Ergebnis; Material, Personal, Abschreibung und Finanzergebnis mindern es mit `-1`. Diese Multiplikatoren sind vor jedem Pilot fachlich gegen die Vorzeichen der Quelldatei zu prüfen. EBITDA schließt die Gruppe `depreciation` aus; EGT schließt `depreciation` und `financial` ein.

Jedes kontenähnliche Datenkonto mit Zahlen muss genau eine Gruppe treffen. Bewusst ausgeschlossene Konten erhalten eine eigene, überschneidungsfreie Gruppe mit `"ignored": true`; sie dürfen nicht einfach ungemappt bleiben. Das Beispiel `ignored_example` ist nur ein Platzhalter und muss fachlich ersetzt oder entfernt werden.

Monat und Vormonat sind für jedes numerische Konto Pflicht. Für alle GuV-Gruppen, die in EBITDA, EBIT, EGT/EBT, Abschreibung, Betriebsergebnis oder Jahresergebnis eingehen, sind auch YTD und YTD-Vorjahr Pflicht. Bilanzgruppen dürfen leere YTD-Felder enthalten. Leere Zellen werden nie als Null geschätzt; ein Vertragsfehler endet mit `FEHLER`.

## Erwartete Ausgabe

- Status: `success`, `warning` oder `error`
- Kurzfazit und priorisierte Abweichungen
- Quellen, Zeitraum und Rechenweg für jede Zahl
- Offene Daten- oder Mapping-Fragen
- Direkt lesbarer Bericht: `artifacts/latest-controlling-report.html`
- Maschinenbericht: `artifacts/latest-controlling-report.json`
- Automatischer Abnahmenachweis: `artifacts/acceptance-evidence.json`
- Nächste Schritte; keine externe Sendefunktion im Pilot

Nach drei Läufen mit identischer Eingabe, identischem Mapping und identischen
KPI-Ergebnissen wechselt der lokale Abnahmenachweis auf `passed`, sofern auch
Quellenbezug, Laufzeit und Aktionssicherheit bestanden sind. Jeder Lauf erhält
eine fortlaufende Nummer, eine eigene ID und eine lokal HMAC-verkettete Signatur.
Das signierte, append-only Laufbuch und sein separat signierter Head liegen im
ignorierten Instanzordner `state/`; `artifacts/acceptance-evidence.json` ist nur
die lesbare Ableitung daraus. Veränderte Einträge, abgeschnittene Historien und
zurückgespielte Artefaktstände stoppen die Abnahme sichtbar. Der lokale Nachweis
ist manipulationsanzeigend, aber kein externer, unveränderlicher Prüfungsdienst.
