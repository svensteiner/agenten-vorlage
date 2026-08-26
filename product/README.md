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

Ohne gültiges `AISTUDIO_SECRET` startet der Prozess nicht. OpenAPI (`/docs` und `/openapi.json`) ist in Produktion aus. Ersteinrichtung: `./scripts/install.sh --org "Firma GmbH" --email admin@firma.example --password '…'` (`data/` wird 0700; `--systemd` schreibt Einheiten für dieses Verzeichnis). Reverse-Proxy: `scripts/nginx-aistudio.conf` (HTTP ohne Zertifikat) bzw. `scripts/nginx-aistudio.tls.conf` nach certbot (`AISTUDIO_TRUST_PROXY=true`, `AISTUDIO_ALLOWED_HOSTS` um den öffentlichen Namen ergänzen). Docker: `docker compose up --build` mit Secret in der Umgebung, Root-Dateisystem read-only, Port nur auf 127.0.0.1. Produktion: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build` (`AISTUDIO_SECRET` Pflicht, kein Demo-Seed). Sicherung/Restore: `./scripts/backup.sh` und `./scripts/restore.sh` (SQLite plus `uploads/`; optional `AISTUDIO_BACKUP_PASS` für AES-256). Qualität lokal (gleicher Stand wie CI): `./scripts/check.sh`.

In Produktion ist **Mandant anlegen** standardmäßig aus. Der erste Mandant kommt über `AISTUDIO_BOOTSTRAP_*` (oder kurz `AISTUDIO_ALLOW_REGISTER=true`).

### Was die Instanz kann

- Mandant registrieren, Nutzer mit Rollen (admin / cfo / board / member), Nutzer deaktivieren, Passwort setzen
- Sitzungen mit Widerruf (Logout, Passwortwechsel, andere Geräte, Deaktivieren)
- Anmeldesperre nach Fehlversuchen, Rate-Limits, Access-Log, Security-Header, Größenlimit, Mandanten-Speicherlimit
- Private Wissensbasis (FTS5), Upload, Löschen, DSGVO-Export
- Agenten mieten (Admin/CFO), interne Rechnungsentwürfe, Aufträge über `core.orchestrator`
- **Modell-Schicht** (`product/llm.py`): einziges Tor nach außen. Die Wissensbasis bleibt auf der Instanz. Standard `AISTUDIO_LLM_EGRESS=in_boundary` (extractiv oder lokales Modell). Erste Stufe: OpenAI mit `AISTUDIO_LLM_EGRESS=cloud` — dann gehen nur freigegebene Kurzauszüge, nie der Bestand. Später derselbe Vertrag auf `AISTUDIO_LLM_PROVIDER=decentral` + `AISTUDIO_LLM_BASE_URL`. Nach wiederholten Ausfällen Schutzschalter (extractiv, ohne weiteres Warten).
- Audit-Log, Auftragsliste, `/api/ready` (Datenbank + beschreibbares Datenverzeichnis, Alter der letzten Sicherung), `/api/live` (Prozess ohne DB), `/api/metrics` (Größen/Zähler; in Produktion `AISTUDIO_METRICS_TOKEN` Pflicht, `?format=prom`)
- Housekeeping beim Start und alle `AISTUDIO_HOUSEKEEPING_HOURS` Stunden (Standard 24): abgelaufene Sitzungen, Audit, Aufträge, WAL-Checkpoint, verwaiste Uploads. Cron: `./scripts/housekeeping.sh`.
- Erstmandant per `AISTUDIO_BOOTSTRAP_*`, wenn die Datenbank leer ist. Nach Erfolg entfernt der Prozess diese Variablen aus `.env`.
- Sitzungsruhe (`AISTUDIO_SESSION_IDLE`), optional Host-Allowlist (`AISTUDIO_ALLOWED_HOSTS`)

### Sprachmodell

`product/` spricht nicht mit `brain.py` und nicht direkt mit einem Vendor-SDK. Alle Formulierungen laufen über `product/llm.py`.

| Variable | Wirkung |
|---|---|
| `AISTUDIO_LLM_EGRESS=in_boundary` | **Standard.** Cloud-APIs werden verweigert. Antworten bleiben auf der Instanz (extractiv oder lokales OpenAI-kompatibles Modell). |
| `AISTUDIO_LLM_EGRESS=cloud` | OpenAI/Anthropic dürfen **Kurzauszüge** der Treffer sehen — nicht die Wissensbasis. |
| `AISTUDIO_LLM_PROVIDER=openai` | Erste Produktstufe, Chat Completions. |
| `AISTUDIO_LLM_PROVIDER=decentral` | Später: lokale Instanz, `AISTUDIO_LLM_BASE_URL` z. B. `http://127.0.0.1:11434/v1`. |

Prompts werden nicht geloggt. `/api/health` zeigt `llm` ohne Schlüssel. Cloud-Aufrufe sind pro Nutzer/Mandant kontingentiert (`AISTUDIO_LLM_PER_USER` / `AISTUDIO_LLM_PER_ORG` pro Minute, `AISTUDIO_LLM_PER_USER_DAY` / `AISTUDIO_LLM_PER_ORG_DAY` pro Kalendertag, persistiert); bei Ausschöpfung bleibt die Antwort extractiv auf der Instanz. Nach `AISTUDIO_LLM_BREAKER_FAILS` Ausfällen (Standard 5) bleibt der Ausgang `AISTUDIO_LLM_BREAKER_SECONDS` Sekunden (Standard 300) geschlossen.

### Bewusst nicht in dieser Version

Echte SEPA-/Kartenlastschrift, SSO/SAML, SharePoint- oder SAP-Connector. Dafür die produktive Mandanten-Laufzeit auf der eigenen Infrastruktur.

`file://` und `?demo=1` bleiben die bisherige Offline-Verkaufsdemo.
