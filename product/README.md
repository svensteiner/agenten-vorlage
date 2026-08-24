# AI Studio — Produktlaufzeit

Mandantenfähige Schicht **über** `core/` und den Verkaufsprototyp. `core/` und `platform/` bleiben unangetastet.

## Start

```bash
pip install -r requirements.txt
./scripts/run_product.sh
```

Browser: [http://127.0.0.1:8123](http://127.0.0.1:8123)

Demo-Anmeldung (fiktive Meridian Industrie GmbH):

| Rolle | E-Mail | Passwort |
|---|---|---|
| CFO | `katharina.vogel@meridian.example` | `Meridian2026!` |
| Vorstand | `markus.brandt@meridian.example` | `Meridian2026!` |

Vorstand sieht gesperrte Akten (z. B. Projekt Nordstern). Der CFO nicht — fail-closed.

Ohne laufenden Server bleibt `prototype/index.html` die bisherige Offline-Demo (`file://` oder `python -m http.server`). `?demo=1` erzwingt den Offline-Modus auch hinter dem Produkt-Server.

## Was live ist

- Anmeldung (PBKDF2, HMAC-Token)
- Private Wissensbasis in SQLite FTS5 (29 Meridian-Dokumente, Upload)
- Belegte Antworten (`POST /api/ask`) — optional LLM, sonst extractiv
- Agenten mieten / pausieren / kündigen, Abrechnung
- Aufträge über `core.orchestrator` plus Wissenssuche
- Audit-Log

Keine echten Zahlungen, kein SSO, keine Connectors nach SharePoint/SAP. Dafür: ein laufendes Mandanten-Produkt, das sich wie die Demo anfühlt.

Docker: `docker compose up --build`.
