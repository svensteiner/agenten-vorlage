# Lokale Agentenmiete

Die Mietstrecke ist **kein Stripe-/Zahlungsflow**. Listenpreise werden im Ledger
gespeichert (`spent_eur` bleibt `"0"`, bis Abrechnung existiert). Getrennt von der
kostenfreien Controlling-Demo (0 EUR, synthetische Daten).

## Portal starten

```powershell
python order_portal.py
```

Standard: `http://127.0.0.1:8765`

Daten:

- Demo-Auftraege: `work/order-portal/instances`
- Miet-Ledger und Instanzen: `work/order-portal/rentals`

Im Browser: Abschnitt **Agenten mieten** - Katalog, Mieten, aktive Mieten,
Oeffnen, Onboarding, Kuendigen. Offline auf 127.0.0.1, ohne Anmeldung.

Nach einer provisionierten Miete (controlling, reporting) erscheint **Oeffnen**.
Der Button oeffnet das Cockpit der Instanz in einem neuen Tab. Das Cockpit
zeigt Anzeigename, SOUL/Preset und vorhandene Dateien aus `instance_path`
(fail-closed, kein Path-Traversal).

Fuer den Controlling-Agenten gibt es zwei Einstiege, im Portal **und** im
geoeffneten Cockpit:

1. **Excel hochladen** - XLSX wird bytegleich nach `inbox/actuals/` kopiert
   (Formeln unangetastet). Fehlt das Konten-Mapping, wird die Vorlage aus dem
   Preset `kmu-controlling` nach `project/pilot/account-mapping.json` gelegt.
2. **Mit Muster starten** - legt Mapping, Starter-Konten, Starter-Bericht und
   einen Forecast in die Instanz. Zusaetzlich existiert `imports/actuals/` als
   lokaler CSV-Drop-Ordner (kein Bank-Live-Import).

Ledger-only-Agenten (rechnungen, vertraege) zeigen **Pack folgt** und haben
keinen Oeffnen-Button.

## API (lokal, CSRF wie die Demo)

Zuerst Session-Token holen:

```powershell
curl http://127.0.0.1:8765/api/session
curl http://127.0.0.1:8765/api/agents
```

Mieten (Header `Origin` und `X-CSRF-Token` aus `/api/session`):

```powershell
curl -X POST http://127.0.0.1:8765/api/rentals `
  -H "Content-Type: application/json" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "X-CSRF-Token: TOKEN" `
  -d '{"company_name":"Muster Demo GmbH","agent_id":"controlling","idempotency_key":"rent-001"}'
```

Aktive Mieten listen, Instanz sehen, onboarden, oeffnen und kuendigen:

```powershell
curl "http://127.0.0.1:8765/api/rentals?company_name=Muster%20Demo%20GmbH"
curl "http://127.0.0.1:8765/api/rentals/rnt_.../instance?company_name=Muster%20Demo%20GmbH"
curl -X POST http://127.0.0.1:8765/api/rentals/rnt_.../onboard `
  -H "Content-Type: application/json" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "X-CSRF-Token: TOKEN" `
  -d '{"company_name":"Muster Demo GmbH","mode":"starter","idempotency_key":"onboard-001"}'
curl "http://127.0.0.1:8765/api/rentals/rnt_.../open?company_name=Muster%20Demo%20GmbH"
curl -X POST http://127.0.0.1:8765/api/rentals/rnt_.../cancel `
  -H "Content-Type: application/json" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "X-CSRF-Token: TOKEN" `
  -d '{"tenant_id":"TENANT","idempotency_key":"cancel-001"}'
```

Excel-Onboarding sendet `mode=excel`, `filename` (nur `*.xlsx`, kein Pfad) und
`content_base64`. Der Server kopiert die Bytes unveraendert.

`GET /open` ist fail-closed und braucht denselben Mandanten (`tenant_id` oder
`company_name`). Erfolg: 302 auf das Cockpit. Browser folgen der Weiterleitung
(neuer Tab). `curl` ohne `-L` zeigt nur den `Location`-Header.

## Was wird wirklich provisioniert?

| Agent | Listenpreis | Provisionierung | Oeffnen | Onboarding |
|-------|-------------|-----------------|---------|------------|
| controlling | 400 EUR | ja, Preset `kmu-controlling` | ja, sieht Instanz | Excel oder Muster |
| reporting | 400 EUR | ja, minimale Instanz ohne Controlling-Preset | ja, sieht Instanz | nein |
| rechnungen | 600 EUR | nein (Ledger-only) | nein | nein |
| vertraege | 500 EUR | nein (Ledger-only) | nein | nein |

**Rechnungen / Vertraege bewusst offen:** Im Repo gibt es keine provisionierbaren
Presets/Tools fuer diese Agenten (`platform/packs/finance` und `legal` sind
SPI-Dokumente, kein Instanz-Pack). Es wird **nicht** fake-provisioniert.
Status bleibt "Pack folgt", bis ein echtes Pack analog Reporting existiert.

Die Demo-Route `/api/demo-orders*` bleibt unveraendert (nur 0 EUR, synthetisch).

## Instanz oeffnen (Fail-closed)

Nur **active + provisioned + passender Mandant**. Der gespeicherte
`instance_path` muss genau `{tenant}/{agent}` unter dem Miet-Root sein;
`..`, absolute Pfade und Links werden abgelehnt.

| Fall | HTTP |
|------|------|
| Provisionierte aktive Miete | 302 auf `/api/rentals/{id}/cockpit/{tenant}/` |
| Instanz-Snapshot | 200 JSON (`/instance`) |
| Gekuendigt | 409 |
| Ledger-only (Pack folgt) | 409 |
| Falscher Mandant / unbekannte ID | 404 |
| Path-Escape in `instance_path` | 409 |
| Onboarding fuer Reporting/Ledger-only | 400 / 409 |
| Excel-Name mit `..` oder Fremdpfad | 400 |

Das Cockpit kommt aus `prototype/` (index.html, app.js, data.js, styles.css)
plus einem generierten `pilot.config.js` mit Anzeigename, Preset/SOUL,
Artefakten und Onboarding-Status der Miete. `serve_pilot.py` und die
0-EUR-Demo bleiben unangetastet.

## Dateien in der Controlling-Instanz nach Onboarding

| Ziel | Quelle |
|------|--------|
| `project/pilot/account-mapping.json` | Preset-Beispiel (unverändert, wenn schon da) |
| `inbox/actuals/*.xlsx` | hochgeladene Excel-Datei, Byte-Kopie |
| `inbox/actuals/starter-konten.csv` | Musterkonten |
| `inbox/forecast/starter-forecast.csv` | Muster-Forecast |
| `artifacts/starter-bericht.md` | Starter-Bericht |
| `imports/actuals/` | lokaler CSV-Drop (kein Bank-Live) |
