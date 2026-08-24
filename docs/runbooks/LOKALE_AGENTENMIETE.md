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

Im Browser: Abschnitt **Agenten mieten** — Katalog, Mieten, aktive Mieten, Kuendigen.
Offline auf 127.0.0.1, ohne Anmeldung.

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

Aktive Mieten listen und kuendigen:

```powershell
curl "http://127.0.0.1:8765/api/rentals?company_name=Muster%20Demo%20GmbH"
curl -X POST http://127.0.0.1:8765/api/rentals/rnt_.../cancel `
  -H "Content-Type: application/json" `
  -H "Origin: http://127.0.0.1:8765" `
  -H "X-CSRF-Token: TOKEN" `
  -d '{"tenant_id":"TENANT","idempotency_key":"cancel-001"}'
```

## Was wird wirklich provisioniert?

| Agent | Listenpreis | Provisionierung |
|-------|-------------|-----------------|
| controlling | 400 EUR | ja, Preset `kmu-controlling` |
| reporting | 400 EUR | ja, minimale Instanz ohne Controlling-Preset |
| rechnungen | 600 EUR | nein (Ledger-only, Pack folgt) |
| vertraege | 500 EUR | nein (Ledger-only, Pack folgt) |

Die Demo-Route `/api/demo-orders*` bleibt unveraendert (nur 0 EUR, synthetisch).