# AI Studio — Produktlaufzeit

Mandantenfähige Schicht **über** `core/` und den Verkaufsprototyp. `core/` und `platform/` bleiben unangetastet.

## Start (Entwicklung / Demo)

```bash
pip install -r requirements.txt
./scripts/run_product.sh
```

Browser: [http://127.0.0.1:8123](http://127.0.0.1:8123)

Demo-Anmeldung (fiktive Meridian Industrie GmbH), nur wenn `AISTUDIO_ALLOW_DEMO_SEED` nicht aus ist:

| Rolle | E-Mail | Passwort |
|---|---|---|
| CFO | `katharina.vogel@meridian.example` | `Meridian2026!` |
| Vorstand | `markus.brandt@meridian.example` | `Meridian2026!` |

Eigener Mandant: auf dem Login-Dialog **Mandant anlegen** (Admin, leere Wissensbasis, Auskunfts-Agent inklusive).

## Produktion

```bash
export AISTUDIO_ENV=production
export AISTUDIO_SECRET='ein-langes-zufaelliges-geheimnis-min-24'
export AISTUDIO_ALLOW_DEMO_SEED=false
export AISTUDIO_CORS_ORIGINS=https://studio.example.com
./scripts/run_product.sh
```

Ohne gültiges `AISTUDIO_SECRET` startet der Prozess nicht. OpenAPI (`/docs`) ist in Produktion aus. systemd-Einheit: `scripts/aistudio.service`. Reverse-Proxy-Beispiel: `scripts/nginx-aistudio.conf` (dann `AISTUDIO_TRUST_PROXY=true`). Docker: `docker compose up --build` mit Secret in der Umgebung. Sicherung: `./scripts/backup.sh`.

### Was die Instanz kann

- Mandant registrieren, Nutzer mit Rollen (admin / cfo / board / member), Nutzer deaktivieren
- Sitzungen mit Widerruf (Logout, Passwortwechsel, andere Geräte, Deaktivieren)
- Anmeldesperre nach Fehlversuchen, Rate-Limits, Access-Log, Security-Header
- Private Wissensbasis (FTS5), Upload, Löschen, DSGVO-Export
- Agenten mieten (Admin/CFO), interne Rechnungsentwürfe, Aufträge über `core.orchestrator`
- Audit-Log, `/api/ready`

### Bewusst nicht in dieser Version

Echte SEPA-/Kartenlastschrift, SSO/SAML, SharePoint- oder SAP-Connector. Dafür die produktive Mandanten-Laufzeit auf der eigenen Infrastruktur.

`file://` und `?demo=1` bleiben die bisherige Offline-Verkaufsdemo.
