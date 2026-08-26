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

Ohne gültiges `AISTUDIO_SECRET` startet der Prozess nicht. OpenAPI (`/docs`) ist in Produktion aus. Ersteinrichtung: `./scripts/install.sh --org "Firma GmbH" --email admin@firma.example --password '…'`. systemd: `scripts/aistudio.service`, tägliche Sicherung: `scripts/aistudio-backup.timer`. Reverse-Proxy: `scripts/nginx-aistudio.conf` (`AISTUDIO_TRUST_PROXY=true`). Docker: `docker compose up --build` mit Secret in der Umgebung, Root-Dateisystem read-only. Sicherung/Restore: `./scripts/backup.sh` und `./scripts/restore.sh`. Qualität lokal (gleicher Stand wie CI): `./scripts/check.sh`.

In Produktion ist **Mandant anlegen** standardmäßig aus. Der erste Mandant kommt über `AISTUDIO_BOOTSTRAP_*` (oder kurz `AISTUDIO_ALLOW_REGISTER=true`).

### Was die Instanz kann

- Mandant registrieren, Nutzer mit Rollen (admin / cfo / board / member), Nutzer deaktivieren, Passwort setzen
- Sitzungen mit Widerruf (Logout, Passwortwechsel, andere Geräte, Deaktivieren)
- Anmeldesperre nach Fehlversuchen, Rate-Limits, Access-Log, Security-Header, Größenlimit
- Private Wissensbasis (FTS5), Upload, Löschen, DSGVO-Export
- Agenten mieten (Admin/CFO), interne Rechnungsentwürfe, Aufträge über `core.orchestrator`
- **Modell-Schicht** (`product/llm.py`): einziges Tor nach außen. Die Wissensbasis bleibt auf der Instanz. Standard `AISTUDIO_LLM_EGRESS=in_boundary` (extractiv oder lokales Modell). Erste Stufe: OpenAI mit `AISTUDIO_LLM_EGRESS=cloud` — dann gehen nur freigegebene Kurzauszüge, nie der Bestand. Später derselbe Vertrag auf `AISTUDIO_LLM_PROVIDER=decentral` + `AISTUDIO_LLM_BASE_URL`.
- Audit-Log, Auftragsliste, `/api/ready` (Datenbank + beschreibbares Datenverzeichnis), `/api/live` (Prozess ohne DB)
- Housekeeping beim Start: abgelaufene Sitzungen, Audit nach `AISTUDIO_AUDIT_RETENTION_DAYS`, Aufträge nach `AISTUDIO_JOB_RETENTION_DAYS`
- Erstmandant per `AISTUDIO_BOOTSTRAP_*`, wenn die Datenbank leer ist

### Sprachmodell

`product/` spricht nicht mit `brain.py` und nicht direkt mit einem Vendor-SDK. Alle Formulierungen laufen über `product/llm.py`.

| Variable | Wirkung |
|---|---|
| `AISTUDIO_LLM_EGRESS=in_boundary` | **Standard.** Cloud-APIs werden verweigert. Antworten bleiben auf der Instanz (extractiv oder lokales OpenAI-kompatibles Modell). |
| `AISTUDIO_LLM_EGRESS=cloud` | OpenAI/Anthropic dürfen **Kurzauszüge** der Treffer sehen — nicht die Wissensbasis. |
| `AISTUDIO_LLM_PROVIDER=openai` | Erste Produktstufe, Chat Completions. |
| `AISTUDIO_LLM_PROVIDER=decentral` | Später: lokale Instanz, `AISTUDIO_LLM_BASE_URL` z. B. `http://127.0.0.1:11434/v1`. |

Prompts werden nicht geloggt. `/api/health` zeigt `llm` ohne Schlüssel. Cloud-Aufrufe sind pro Nutzer/Mandant kontingentiert (`AISTUDIO_LLM_PER_USER` / `AISTUDIO_LLM_PER_ORG`); bei Ausschöpfung bleibt die Antwort extractiv auf der Instanz.

### Bewusst nicht in dieser Version

Echte SEPA-/Kartenlastschrift, SSO/SAML, SharePoint- oder SAP-Connector. Dafür die produktive Mandanten-Laufzeit auf der eigenen Infrastruktur.

`file://` und `?demo=1` bleiben die bisherige Offline-Verkaufsdemo.
