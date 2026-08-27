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
export AISTUDIO_METRICS_TOKEN='ein-langes-zufaelliges-metrik-token-min-16'
export AISTUDIO_ALLOW_DEMO_SEED=false
export AISTUDIO_CORS_ORIGINS=https://studio.example.com
./scripts/run_product.sh
```

Ohne `AISTUDIO_HOST` bindet die Instanz **127.0.0.1** (lokal und Produktion). Docker setzt `0.0.0.0` nur im Container und verlangt dann ein eigenes Secret, nicht den Demo-Wert. Der Host-Port bleibt 127.0.0.1. `AISTUDIO_CORS_ORIGINS=*` gilt in Produktion nicht.

Ohne gültiges `AISTUDIO_SECRET` oder `AISTUDIO_METRICS_TOKEN` startet der Prozess nicht. OpenAPI (`/docs` und `/openapi.json`) ist in Produktion aus. Ersteinrichtung: `./scripts/install.sh --org "Firma GmbH" --email admin@firma.example --password-file ./pass.txt` (`data/` wird 0700; `--systemd` legt den Systembenutzer `aistudio` an und schreibt Einheiten — nicht root; Demo-Secret oder unter 24 Zeichen bricht `--systemd` ab, sonst Crash-Loop). Secret-Wechsel: neues `AISTUDIO_SECRET`, altes in `AISTUDIO_SECRET_PREV`, nach Ablauf der Sitzungen `PREV` entfernen. Reverse-Proxy: `scripts/nginx-aistudio.conf` (HTTP ohne Zertifikat) bzw. `scripts/nginx-aistudio.tls.conf` nach certbot (`AISTUDIO_TRUST_PROXY=true`, `AISTUDIO_PROXY_IPS=127.0.0.1,::1` bei Host-nginx auf Loopback, hinter Docker die Bridge-Gateway-IP statt `172.16.0.0/12`, `AISTUDIO_ALLOWED_HOSTS` um den öffentlichen Namen ergänzen; `/api/` 20/s, Login/Register 10/Minute, 32 parallele Verbindungen pro IP). Docker: `docker compose up --build` mit Secret in der Umgebung, Root-Dateisystem read-only, RAM 512 MB (Backup-Profil 256 MB, ohne Extra-Swap), Port nur auf 127.0.0.1 (`.dockerignore` hält `.env` und `backup.env` draußen). Produktion: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build` (`AISTUDIO_SECRET` und `AISTUDIO_METRICS_TOKEN` Pflicht, kein Demo-Seed). Docker-Sicherung: `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup run --rm backup` (openssl im Image; Passwort auf Volume `aistudio-backup-secret`, nicht im Produkt-Container). Sicherung/Restore: `./scripts/backup.sh` und `./scripts/restore.sh` (SQLite plus `uploads/`; `install.sh` schreibt `AISTUDIO_BACKUP_PASS` nach `backup.env` neben `.env`, nicht in die Produkt-`.env` und nicht nach `data/`; Restore braucht denselben Wert). Qualität lokal (gleicher Stand wie CI): `./scripts/check.sh`.

In Produktion ist **Mandant anlegen** standardmäßig aus. Der erste Mandant kommt über `data/bootstrap.env` (`AISTUDIO_BOOTSTRAP_*`, von `install.sh` geschrieben) oder kurz `AISTUDIO_ALLOW_REGISTER=true`.

### Was die Instanz kann

- Mandant registrieren, Nutzer mit Rollen (admin / cfo / board / member), Nutzer deaktivieren, Passwort setzen
- Sitzungen mit Widerruf (Logout, Passwortwechsel, andere Geräte, Deaktivieren)
- Anmeldesperre nach Fehlversuchen, Rate-Limits (Health/Ready 180/Minute pro IP — Docker-HEALTHCHECK alle 30s und Lastbalancer 1/s bleiben grün; Live 300; Metriken 60 vor dem Token; Suche wie Ask 120/Minute je Nutzer; Dokumentliste und Einzelabruf, Aufträge, Audit und `/api/me` 60), Access-Log (ohne Live/Ready 2xx), Security-Header ohne `Server:`, Größenlimit (Upload höchstens 8 MB, Request 10 MB; nginx-Muster `client_max_body_size 10m`), Mandanten-Speicherlimit
- Private Wissensbasis (FTS5), Upload, Löschen, DSGVO-Export; je Mandant Speicherlimit und höchstens 500 Dokumente (`AISTUDIO_ORG_MAX_DOCS`); Liste ohne Dokumentkörper (`GET /api/docs/{id}` im Viewer); Export kapt Aufträge/Audit (Kennzeichen `truncated`)
- Agenten mieten (Admin/CFO), interne Rechnungsentwürfe, Aufträge über `core.orchestrator`
- **Modell-Schicht** (`product/llm.py`): einziges Tor nach außen. Die Wissensbasis bleibt auf der Instanz. Standard `AISTUDIO_LLM_EGRESS=in_boundary` (extractiv oder lokales Modell). Erste Stufe: OpenAI mit `AISTUDIO_LLM_EGRESS=cloud` — dann gehen nur freigegebene Kurzauszüge, nie der Bestand. Später derselbe Vertrag auf `AISTUDIO_LLM_PROVIDER=decentral` + `AISTUDIO_LLM_BASE_URL`. Nach wiederholten Ausfällen Schutzschalter (extractiv, ohne weiteres Warten).
- Audit-Log (ohne Fragen/Auftragstexte, nur Länge), Auftragsliste, `/api/health` (Produktion: Prozess + `allow_register`, ohne DB), `/api/ready` (`SELECT 1` + beschreibbares Verzeichnis; Sicherungslage in Produktion nicht öffentlich; Schema nicht bei jeder Sonde), `/api/live` (Prozess ohne DB), `/api/metrics` (Größen/Zähler; in Produktion `AISTUDIO_METRICS_TOKEN` Pflicht, `?format=prom`)
- Housekeeping beim Start und alle `AISTUDIO_HOUSEKEEPING_HOURS` Stunden (Standard 24): abgelaufene Sitzungen, Audit, Aufträge, WAL-Checkpoint (übersprungen, solange `data/.backup.lock` gehalten wird), verwaiste Uploads, Vor-Restore-Kopien (letzte 3). Cron: `./scripts/housekeeping.sh`. Restore bricht ab, solange der Produktprozess läuft (`data/aistudio.pid`; `AISTUDIO_RESTORE_FORCE=1` überschreibt bewusst) oder eine Sicherung läuft (`data/.backup.lock`). Ein zweiter Produktprozess auf demselben `data/` wird beim Start abgelehnt (`data/aistudio.lock`). `backup.sh` braucht `sqlite3` (kein `cp` der WAL) und lässt nur eine Sicherung gleichzeitig zu.
- Erstmandant per `data/bootstrap.env` bzw. `AISTUDIO_BOOTSTRAP_*`, wenn die Datenbank leer ist. Nach Erfolg löscht der Prozess die Datei und entfernt die Variablen aus der Umgebung (und aus `.env`, falls sie dort noch stehen). systemd schreibt nur `data/` — deshalb liegt das Bootstrap-Passwort nicht mehr in `.env`.
- Sitzungsruhe (`AISTUDIO_SESSION_IDLE`; `last_seen` höchstens einmal pro Minute, nicht bei jedem GET), Host-Allowlist (`AISTUDIO_ALLOWED_HOSTS`; in Produktion immer an, `*` ist Loopback statt alles). Bind ohne `AISTUDIO_HOST` auf 127.0.0.1. Demo-Secret auf `0.0.0.0`/`::` wird verweigert. Docker an `0.0.0.0` mit nur Loopback in `AISTUDIO_PROXY_IPS` warnt, weil X-Forwarded-For dann nicht greift. `install.sh` auf bestehender `.env` trägt fehlende Keys nach (Bind, Allowlist, Metrik-Token, Proxy, Egress), ohne Werte zu überschreiben.

### Sprachmodell

`product/` spricht nicht mit `brain.py` und nicht direkt mit einem Vendor-SDK. Alle Formulierungen laufen über `product/llm.py`.

| Variable | Wirkung |
|---|---|
| `AISTUDIO_LLM_EGRESS=in_boundary` | **Standard.** Cloud-APIs werden verweigert. Antworten bleiben auf der Instanz (extractiv oder lokales OpenAI-kompatibles Modell). |
| `AISTUDIO_LLM_EGRESS=cloud` | OpenAI/Anthropic dürfen **Kurzauszüge** der Treffer sehen — nicht die Wissensbasis. |
| `AISTUDIO_LLM_PROVIDER=openai` | Erste Produktstufe, Chat Completions. |
| `AISTUDIO_LLM_PROVIDER=decentral` | Später: lokale Instanz, `AISTUDIO_LLM_BASE_URL` z. B. `http://127.0.0.1:11434/v1`. |

Prompts werden nicht geloggt. Entwicklung: `/api/health` zeigt `llm` ohne Schlüssel. Produktion: dieselbe Lage nach Login auf `/api/me` und auf `/api/metrics`. Cloud-Aufrufe sind pro Nutzer/Mandant kontingentiert (`AISTUDIO_LLM_PER_USER` / `AISTUDIO_LLM_PER_ORG` pro Minute, `AISTUDIO_LLM_PER_USER_DAY` / `AISTUDIO_LLM_PER_ORG_DAY` pro Kalendertag, persistiert); bei Ausschöpfung bleibt die Antwort extractiv auf der Instanz. Nach `AISTUDIO_LLM_BREAKER_FAILS` Ausfällen (Standard 5) bleibt der Ausgang `AISTUDIO_LLM_BREAKER_SECONDS` Sekunden (Standard 300) geschlossen. Timeout höchstens 60s. `in_boundary` ignoriert `HTTP_PROXY` (Auszüge bleiben auf der Instanz); Cloud darf den Proxy nutzen. Basis-URL nur http/https.

### Bewusst nicht in dieser Version

Echte SEPA-/Kartenlastschrift, SSO/SAML, SharePoint- oder SAP-Connector. Dafür die produktive Mandanten-Laufzeit auf der eigenen Infrastruktur.

`file://` und `?demo=1` bleiben die bisherige Offline-Verkaufsdemo.
