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

Im Browser: Abschnitt **Agenten mieten** — Katalog, Mieten, aktive Mieten,
Oeffnen, Kuendigen. Offline auf 127.0.0.1, ohne Anmeldung.

Nach einer provisionierten Miete (controlling, reporting) erscheint **Oeffnen**.
Der Button oeffnet das Cockpit der Instanz in einem neuen Tab (dieselbe
Prototype-UI wie `scripts/serve_pilot.py`, ausgeliefert vom Portal unter
`/api/rentals/{id}/cockpit/{tenant}/`). Ledger-only-Agenten (rechnungen,
vertraege) zeigen **Pack folgt** und haben keinen Oeffnen-Button.

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

Aktive Mieten listen, oeffnen und kuendigen:

```powershell
curl "http://127.0.0.1:8765/api/rentals?company_name=Muster%20Demo%20GmbH"
curl "http://127.0.0.1:8765/api/rentals/rnt_.../open?company_name=Muster%20Demo%20GmbH"
curl -X POST http://127.0.0.1:8765/api/rentals/rnt_.../cancel `
  -H "Content-Type: application/json" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "X-CSRF-Token: TOKEN" `
  -d '{"tenant_id":"TENANT","idempotency_key":"cancel-001"}'
```

`GET /open` ist fail-closed und braucht denselben Mandanten (`tenant_id` oder
`company_name`). Erfolg: 302 auf das Cockpit. Browser folgen der Weiterleitung
(neuer Tab). `curl` ohne `-L` zeigt nur den `Location`-Header.

## Was wird wirklich provisioniert?

| Agent | Listenpreis | Provisionierung | Oeffnen |
|-------|-------------|-----------------|---------|
| controlling | 400 EUR | ja, Preset `kmu-controlling` | ja |
| reporting | 400 EUR | ja, minimale Instanz ohne Controlling-Preset | ja |
| rechnungen | 600 EUR | nein (Ledger-only, Pack folgt) | nein |
| vertraege | 500 EUR | nein (Ledger-only, Pack folgt) | nein |

Die Demo-Route `/api/demo-orders*` bleibt unveraendert (nur 0 EUR, synthetisch).

## Instanz oeffnen (Fail-closed)

Nur **active + provisioned + passender Mandant**. Der gespeicherte
`instance_path` muss genau `{tenant}/{agent}` unter dem Miet-Root sein;
`..`, absolute Pfade und Links werden abgelehnt.

| Fall | HTTP |
|------|------|
| Provisionierte aktive Miete | 302 auf `/api/rentals/{id}/cockpit/{tenant}/` |
| Gekuendigt | 409 |
| Ledger-only (Pack folgt) | 409 |
| Falscher Mandant / unbekannte ID | 404 |
| Path-Escape in `instance_path` | 409 |

Das Cockpit kommt aus `prototype/` (index.html, app.js, data.js, styles.css)
plus einem generierten `pilot.config.js` mit dem Anzeigenamen der Miete.
`serve_pilot.py` und die 0-EUR-Demo bleiben unangetastet.
