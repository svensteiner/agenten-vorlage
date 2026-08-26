# CHANGELOG — Kundendemonstrations-Prototyp

Alle sichtbaren Änderungen am Demo-Prototyp. Neueste zuerst.

## Produktlaufzeit 1.4.14 — 2026-08-26 — Restore-Kopien begrenzen

`restore.sh` legt Vor-Restore-Kopien 0600/0700 an und behält nur die letzten drei
(Datenbank und `uploads.before-restore-*`). Housekeeping räumt ältere Reste auf —
sonst bleiben Mandantendateien nach einem Restore unbegrenzt auf der Platte.

## Produktlaufzeit 1.4.13 — 2026-08-26 — Bootstrap-Passwort unter data/, kein Demo-PREV

`install.sh` schreibt den Erstmandant nach `data/bootstrap.env` (600), nicht nach `.env`.
Der Prozess liest die Datei, legt den Mandanten an und löscht sie — systemd darf `data/`
schreiben, `.env` nicht. Überzählige Bootstrap-Variablen werden auch dann entfernt,
wenn schon ein Mandant existiert (Neustart lädt sie sonst erneut). `--password-file`
muss 600 oder 400 sein. `AISTUDIO_SECRET_PREV` mit Demo-Wert oder unter 24 Zeichen
wird in Produktion ignoriert. WAL/SHM der SQLite-Datei werden 0600.

## Produktlaufzeit 1.4.12 — 2026-08-26 — Secret-Rotation, Install ohne argv-Passwort

Sitzungstokens akzeptieren optional das vorige HMAC-Geheimnis (`AISTUDIO_SECRET_PREV`),
damit ein Secret-Wechsel nicht alle Anmeldungen sofort ungültig macht.
`install.sh` liest das Bootstrap-Passwort aus `--password-file` oder
`AISTUDIO_BOOTSTRAP_PASSWORD`; `--password` bleibt, warnt aber (Prozessliste).

## Produktlaufzeit 1.4.11 — 2026-08-26 — Audit ohne Fragen, systemd nur data/

Fragen und Auftrags-Texte stehen nicht mehr im Audit-Log (nur Zeichenlänge).
systemd schreibt nur noch `data/` (nicht den Quellbaum); zusätzlich
`CapabilityBoundingSet=` und `LimitCORE=0`.

## Produktlaufzeit 1.4.10 — 2026-08-26 — Bootstrap-Passwort, Metriken, Backup-Alter

Nach erfolgreichem Erstmandant entfernt der Prozess `AISTUDIO_BOOTSTRAP_*` aus
der Umgebung und aus `.env` — das Admin-Passwort bleibt nicht auf der Platte.
`/api/metrics` ist in Produktion ohne Token 401 (`AISTUDIO_METRICS_TOKEN`, Install
legt eines an). `/api/ready` und Metriken melden das Alter der letzten Sicherung
(`backup_age_hours`, `backup_ok`; optional `AISTUDIO_READY_REQUIRE_BACKUP`).
Housekeeping ruft `PRAGMA optimize` auf.

## Produktlaufzeit 1.4.9 — 2026-08-26 — Schutzschalter, Speicherlimit, Sitzungsruhe

Nach wiederholten Modell-Ausfällen bleiben Antworten extractiv (`AISTUDIO_LLM_BREAKER_FAILS` /
`AISTUDIO_LLM_BREAKER_SECONDS`, Standard 5 / 300 s) — der Worker wartet nicht weiter auf
eine tote API. Uploads sind je Mandant begrenzt (`AISTUDIO_ORG_UPLOAD_MB`, Standard 200).
Ungenutzte Sitzungen laufen nach `AISTUDIO_SESSION_IDLE` aus (Install: 4 Stunden).
Produktion blendet `/openapi.json` aus. Optional `AISTUDIO_ALLOWED_HOSTS` prüft den
Host-Header. systemd: `MemoryMax=512M`.

## Produktlaufzeit 1.4.8 — 2026-08-26 — LLM-Tageskontingent

Cloud-Aufrufe sind zusätzlich pro Kalendertag begrenzt (`AISTUDIO_LLM_PER_USER_DAY` /
`AISTUDIO_LLM_PER_ORG_DAY`, Standard 200/800) und in SQLite persistiert — ein
Neustart setzt das Tagesbudget nicht zurück. Bei Ausschöpfung weiter extractiv.

## Produktlaufzeit 1.4.7 — 2026-08-26 — Backup-Verschlüsselung, Compose localhost

Sicherungen sind 0600, das Backup-Verzeichnis 0700. Mit `AISTUDIO_BACKUP_PASS`
schreibt `backup.sh` AES-256 (openssl, pbkdf2) und lässt kein Klartext liegen.
Compose veröffentlicht Port 8123 nur auf 127.0.0.1.

## Produktlaufzeit 1.4.6 — 2026-08-26 — nginx, systemd, Metriken-Token

nginx-HTTP-Conf startet ohne Zertifikat; TLS liegt in `nginx-aistudio.tls.conf`.
Login am Proxy ist rate-begrenzt. `install.sh --systemd` schreibt Einheiten für
dieses Checkout. 429 mit `Retry-After`. `/api/metrics` optional mit Token,
Prometheus-Text über `?format=prom`.

## Produktlaufzeit 1.4.5 — 2026-08-26 — Housekeeping, Metriken, Uploads

Housekeeping läuft periodisch im Prozess (nicht nur beim Start), WAL-Checkpoint,
verwaiste Upload-Dateien werden entfernt. Löschen eines Dokuments löscht die
Datei. `/api/metrics` (Größen und Zähler, keine Mandantentexte). Backup bricht
ab unter 100 MB frei. `data/` und die SQLite-Datei werden auf 0700/0600 gesetzt.

## Produktlaufzeit 1.4.4 — 2026-08-26 — Rate-Limiter, Restore, Compose-Prod

Rate-Limiter vergisst idle Keys (kein unbegrenztes Wachstum). Restore prüft
die Quelle vor dem Überschreiben, legt bei Fehler den vorherigen Stand zurück
und spielt Uploads aus dem Schwesterarchiv wieder ein. `backup.sh` sichert
`uploads/` mit. `docker-compose.prod.yml` ohne Demo-Seed, Secret Pflicht.
Image enthält `sqlite3` (WAL-sichere Sicherung). nginx leitet HTTP nach HTTPS.
Install setzt `data/` auf 0700. `/api/health` nennt in Produktion keine
Mandanten-/Dokumentzahlen.

## Produktlaufzeit 1.4.3 — 2026-08-26 — Image und Dateiauslieferung

`.dockerignore` lässt `.env`, Tests und `platform/` draußen. Statische Dateien nur
mit erlaubter Endung, keine Hidden Files. Uploads ohne Pfadanteile, ohne NUL.
Compose: read-only Root, `cap_drop: ALL`. nginx verweigert `/.…`.

## Produktlaufzeit 1.4.2 — 2026-08-26 — Fehler, Logs, Aufräumen

Unhandled Errors in Produktion ohne Stacktrace, `request_id` in API-Fehlern,
JSON-Access-Log in Produktion, `/api/live` ohne Datenbank, Housekeeping
(abgelaufene Sitzungen, alte Audit-/Auftragszeilen), härterer Backup-Timer,
Install mit 12-Stunden-Sitzung.

## Produktlaufzeit 1.4.1 — 2026-08-26 — Produktionshärtung

CSP, COOP/CORP, LLM-Kontingent (extractiver Fallback statt 429), Audit ohne Prompt,
systemd-Härtung, nginx HSTS, Backup mit `integrity_check`, Install-Default
`AISTUDIO_LLM_EGRESS=in_boundary`. `/api/ready` meldet freien Speicher.

## Produktlaufzeit 1.4.0 — 2026-08-26 — Modell-Schicht, Daten bleiben auf der Instanz

**Sprachmodell hinter einem Tor, nicht als Direktaufruf.** Additiv `product/llm.py`
(`core/` und `platform/` unangetastet, kein `brain.py` mehr im Produktpfad):
- Standard `AISTUDIO_LLM_EGRESS=in_boundary`: Cloud-APIs werden verweigert, Antworten extractiv lokal.
- Opt-in erste Stufe: OpenAI mit `AISTUDIO_LLM_EGRESS=cloud` — nur ACL-gefilterte Kurzauszüge, nie die Wissensbasis.
- Später derselbe Vertrag auf `AISTUDIO_LLM_PROVIDER=decentral` + lokale `AISTUDIO_LLM_BASE_URL`.
- Prompts werden nicht geloggt. `/api/health` zeigt Provider/Modell ohne Schlüssel.
- Antwortkarte: Badge „formuliert“ / „aus Belegen“. Betrieb zeigt die Schicht.

## Produktionslaufzeit — 2026-08-25 — Mandant anlegen, Sitzungen, Rollen, Betrieb

**AI Studio als Werkzeug auf der eigenen Infrastruktur**, soweit ohne SSO/Zahlungsanbieter möglich.
Additiv in `product/` (+ Login/Einstellungen im Prototype):
- **Mandant anlegen** (Admin, leere Wissensbasis), Nutzerrollen admin/cfo/board/member.
- Sitzungen mit JTI, Logout widerruft, Passwortwechsel, Anmeldesperre, Rate-Limits, Security-Header.
- Produktion startet nicht mit Demo-Secret; `/docs` aus; Demo-Seed per Env abschaltbar.
- Betrieb in Einstellungen: Upload, Nutzer, Mandant, Audit, DSGVO-Export. Flotte nur Admin/CFO.
- Interne Rechnungsentwürfe, `/api/ready`, systemd-Einheit.

## Produktlaufzeit — 2026-08-24 — Mandant, Wissensbasis, Miete, Aufträge

**Die Mietplattform läuft als Produkt**, nicht nur als Demo-UI. Additive Schicht `product/`
(`core/` und `platform/` unangetastet):
- FastAPI auf Port 8123, SQLite + FTS5, Demo-Mandant Meridian (29 Dokumente, 8 Agenten).
- Anmeldung (CFO / Vorstand), belegte Antworten, fail-closed bei gesperrten Akten.
- Flotte mieten/pausieren/kündigen serverseitig, Abrechnung, Agent-Jobs über `core.orchestrator`.
- Prototype erkennt `/api/health`: Live-Login + Live-Ask/Fleet; ohne Server unveränderte Offline-Demo.
- Start: `./scripts/run_product.sh` · Docker: `docker compose up --build`.

## Mietplattform „Team" — 2026-08-24 — Digitale Mitarbeiter mieten, steuern, abrechnen

**Die Agenten-Miete ist jetzt eine eigene Plattform**, nicht nur der Money-Shot am Demo-Ende.
Additiv in `prototype/` (bestehende Demo, Guided-Tour und Money-Shot bleiben):
- **Neues Modul `Team`** in der Seitenleiste (Gruppe Betrieb, neben Einstellungen): vier Karten
  **Ihr Team · Marktplatz · Abrechnung · Aufträge**.
- **`AGENT_CATALOG` in `data.js`** — 8 digitale Mitarbeiter (Auskunft inklusive, Reporting 400 €
  empfohlen, Rechnung 600 €, Vertrag 500 €, plus Liquidität 450 €, Compliance 550 €, Einkauf 500 €,
  ESG 450 €), mit SLA, Skills, Werkzeugen und Demo-Lieferungen. Money-Shot-Karten tragen dieselben `id`s.
- **Flotte:** mieten (Bestätigungsdialog), pausieren, kündigen (Zwei-Klick), persistiert in
  `localStorage` (`aistudio.fleet.v1`). Reset setzt auf den Auskunfts-Agenten zurück.
- **Abrechnung:** Positionszeilen, Summe, nächste Lastschrift, Preis-Pfad. Pausierte Agenten
  werden nicht berechnet.
- **Aufträge:** gemietete Agenten liefern Monatsabschluss, Rechnungsprüflauf, Fristenradar usw.
  aus denselben Meridian-Zahlen.
- Money-Shot **schreibt in die Flotte** (Reporting-Agent nach Auto-Buchung im Team sichtbar);
  **`answerCard()`** schließt den Replay-Bug nach Modulwechsel.

## Phase B (Wartepunkt) — 2026-07-21 — Voll-Korpus-Kohärenz-Audit (12/12) + Config-Kommentar korrigiert, blockiert auf Sven — kein `prototype/`-Eingriff

**Erster Voll-Korpus-Kohärenz-Audit** — jetzt möglich, weil die 12 Zwilling-Körper seit 2026-07-17 vollständig
sind; ein neuer Winkel statt eines identischen Re-Verifikations-Ticks (Churn). Deterministisch (`grep`) **alle 12
Zwillinge** gegen den Draft `pilot.config.js` geprüft:
- **0 Meridian-Leak** über alle 12 Körper — Firma, Domain **und** alle Quell-Personennamen (Krüger/Vogel/Wagner/
  Brandt/Feldmann/Lang/Sabine Reinhardt) → **0 Treffer**.
- **7 von 9 synth. Config-Namen** erscheinen in ≥1 Zwilling (Moser · Hollmann · Kessler · Reinhardt · Bergmann ·
  Falk · Lindner).
- **⚠ Neu-Fund:** `hr` (Baumgartner) & `audit` (Weiß) erscheinen in **0** Zwillingen — **korrekt & erwartet**: die
  3 gewählten Pilot-Szenarien (materialkosten · projekt-beta · vorstand-summary) referenzieren **keine** HR-/Audit-
  Persona → das sind **ungenutzte** Korpus-Mapping-Einträge (harmlos; `applyPilotChrome` nutzt `people` nur fürs
  Korpus-Ersetzen). **Schritt-3-Hinweis:** nicht nach HR-/Audit-Belegen suchen — es gibt keine.
- **Config-Kommentar korrigiert** (nur `pilot-assets/`, **nicht** `prototype/`): die überholte Notiz „hr/audit + 2
  restliche vorstand-Belege folgen in Schritt 3" ersetzt — die vorstand-Zwillinge sind seit 2026-07-17 gestaged; die
  Realität (hr/audit ungenutzt) ist jetzt im Draft dokumentiert. `node --check` (config + prototype) grün, `git`:
  nur `pilot.config.js`. Ein Audit-/Doku-Brick hebt kein Gate → **Gate B→C wartet weiter allein auf Sven.**

## Phase B (Wartepunkt) — 2026-07-20 — Live-Browser-Verifikationstick (grün), blockiert auf Sven — keine Prototyp-/Feature-Änderung

**Recording-Readiness erstmals wieder real im Browser belegt** (nicht nur `node --check`), freeze-konform, `prototype/`
unangetastet. Weil **kein** freeze-konformer Vorbereitungs-Brick mehr offen ist und ein weiterer reiner Daten-Tick
Churn wäre, diesen Zyklus die Video-Auflösung live geprüft — die letzten Zyklen fielen am *throttled* Streaming-/
Screenshot-Pfad auf DOM/Daten zurück.
- **Live geladen** über statischen Server (`launch.json` „prototype", Port 8777) bei **1920×1080**: **0 Konsolenfehler**
  beim Laden **und** nach Klick auf die Demo-Buttons; Titel „AI Studio — Meridian Industrie GmbH"; voller Interaktivbaum
  (Suche/Strg+K · **▶ Geführte Demo** · **⟲ Zurücksetzen** · Composer/Senden) vorhanden; App sauber IIFE-gekapselt.
- **Server-Logs:** `data.js` · `styles.css` · `app.js` je **HTTP 200**; einziger 404 = `favicon.ico` — kosmetisch, im
  Screen-Recording unsichtbar → **bewusst nicht** angefasst (Feature-Freeze + „nur ändern, was Sven anmerkt").
- **Deterministischer Invarianten-Check** (VM-Sandbox, Scratchpad): **29 Docs · 17 Szenarien · DEMO_ORDER→6 Szenarien ·
  Money-Shot letzt · 0 kaputte Beleg-Referenzen · Money-Shot mit 4 Agenten-Karten**.
- **Bekannte Limitierung:** Das *Streaming der Geführten Demo* wird im Automations-Harness gedrosselt (async setTimeout-
  Sequenz spielt dort nicht sichtbar durch) — **kein** Demo-Defekt; Sven nimmt in einem echten Browser auf, wo es abspielt.
- Hebt **kein** Gate → **Gate B→C wartet weiter allein auf Sven.** `git`-Baum clean; `prototype/` unverändert.

## Phase C (Vorbereitung) — 2026-07-19 — Multi-`projectLeads`-Friction im Draft-`pilot.config.js` gelöst (kein Eingriff in prototype/)

**Statt eines identischen Re-Verifikations-Ticks (Churn) die eine seit ~4 Zyklen offene Friction konkret behoben** —
freeze-konform, nur `pilot-assets/`, `prototype/` unangetastet. Der Korpus trägt **mehrere** Projektleitungen
(Alpha: zwei Namen — Meridian-Inkonsistenz, faithful gemappt; Beta: einer), für die eine **einzelne** `projectLead`-
Rolle nicht reicht. Der Draft `pilot.config.js` trug das bislang nur als Kommentar-Friction. Jetzt umgesetzt:
- **Neu `company.projectLeads`** (projekt-scoped): `alpha: ["Sandra Bergmann", "Nadine Falk"]`, `beta: ["Tobias Lindner"]` —
  alle Namen bereits in den Zwillingen gesetzt & verifiziert (Alpha-Doppel-Lead nicht eingeebnet).
- **`legal`-Kommentar** klargestellt: *Dr. Stefan Reinhardt* (Recht) ≠ projectLead *Reinhardt* (bewusst getrennt, Kollision vermieden).
- Friction-Kommentar von „⚠ offen" auf „✅ gelöst" umgestellt; Wiring (Konsum) bleibt **gated auf Gate B→C** (berührt prototype/).
- **Verifiziert:** `node --check` (config) grün; strukturell `alpha`/`beta`-Arrays korrekt, `scenarios: 3`, `active: true`;
  Config-**Werte** rein synthetisch (0 Meridian-Leak in Daten); `node --check` prototype/app.js+data.js grün; **29 Docs · 17 Szenarien** unverändert; `prototype/` unberührt. **Gate B→C wartet weiter allein auf Sven.**

## Phase B (Wartepunkt) — 2026-07-18 — Verifikations-Tick (grün), blockiert auf Sven — keine Prototyp-/Feature-Änderung

**Reiner Re-Verifikations-Zyklus, kein Eingriff in `prototype/` (Feature-Freeze gewahrt).** Es ist **kein**
freeze-konformer Vorbereitungs-Brick mehr offen (Korpus-Zwillinge 12/12, alle 3 Pilot-Szenarien komplett);
alle verbleibenden Schritte (Schritt-3-Übertragung + PILOT_CONFIG-Wiring) sind **gated auf Gate B→C = Svens
Aufnahme + Freigabe**. Statt neuen Umfangs (Freeze-Verstoß) oder Doku-Churn: Zustand deterministisch verifiziert.
- **0 Meridian-Leak** über alle 12 Zwilling-Dateien (Firma · Personen · Domain — unabhängiger `grep`, Exit 1).
- **Synth. Namen present** in allen 12 Zwilling-Dateien (Muster Bau · Moser · Hollmann · Kessler · Lindner · Falk · Bergmann).
- **`node --check`** (prototype/app.js + prototype/data.js) grün; **Live-Daten unverändert** (17 Szenarien in data.js).
- `git status` sauber (Arbeitsbaum clean). **Gate B→C wartet weiterhin allein auf Sven.**

## Phase C (Vorbereitung) — 2026-07-17 — 3 Prosa-Zwillinge gestaged, `vorstand-summary` vollständig → ALLE 3 Pilot-Szenarien komplett, Körper-Abdeckung 9/12 → 12/12 (kein Eingriff in prototype/)

**Drittes und letztes Pilot-Szenario vollständig als Zwilling, freeze-konform.** Phase B bleibt auf **Svens
Aufnahme + Freigabe** blockiert (Gate B→C). Nach `materialkosten` (5/5) und `projekt-beta` (4/4) staged dieser
Zyklus die **3 verbleibenden Belege des dritten Pilot-Szenarios `vorstand-summary`** als identitäts-bereinigte
Text-Zwillinge (nicht-gated Pipeline-Hälfte, Schritte 1+2 — Laden in `data.js` bleibt Schritt 3/gated). Damit
sind **alle 3 Pilot-Szenarien** als Zwilling komplett; die Korpus-Zwilling-Vorbereitung ist abgeschlossen.

### Gebaut (nur `pilot-assets/muster-bau-gmbh/` — `prototype/` unverändert)
- **`build_vorstand_twins.py`** — reproduzierbarer Generator **mit Self-Check** (Anker-Zahlen erhalten · kein
  Meridian-Leak · synth. Namen present · externe Gegenpartei behalten). Additiv neben den 3 Vorgänger-Generatoren.
- **`projekt-alpha-status_zwilling.txt`** — Projektbericht (neue Fertigungslinie Werk 2, Budget 24 Mio. €, 62 % im Zeitplan, 14,1 Mio. € verausgabt, Inbetriebnahme Q4 2026).
- **`vorstandsprotokoll-2026-03_zwilling.txt`** — Sitzungsprotokoll 28.03.2026 (TOP1 Zweitlieferant Ferro Nord, TOP2 Mehrbudget 0,9 Mio. € Projekt Alpha, TOP3 ESG-Ziel 30 % CO₂ bis 2030).
- **`esg-bericht-2025_zwilling.txt`** — Nachhaltigkeitsbericht CSRD/ESRS (CO₂ 41.200 t, −12 % ggü. 2020, Scope 1/2 12.400/28.800 t, 68 % Grünstrom, Zielpfad −30 % bis 2030).
- **README** fortgeschrieben (Vorstand-Zwillinge, CEO/Alpha-Lead-Ersetzung, **Accounting-Korrektur**, Alpha-Doppel-Lead-Friction).

### Verifiziert (deterministisch, Self-Check + unabhängiger grep)
- **Körper-Abdeckung 9/12 → 12/12**; Szenario `vorstand-summary` **3/3** Belege gestaged → **alle 3 Szenarien komplett**.
- **⚠ Accounting korrigiert:** die 3 Szenarien ziehen **12 Dokumentkörper** heran; „10/12" zählte den Controlling-`.xlsx`
  fälschlich als Körper — er ist ein **Zahlen-Overlay ZUSÄTZLICH** zu den 12. Wahr waren 9/12; jetzt 12/12 Körper.
- **Personen-/Rollen-Regel:** Brandt → Moser (CEO), Ing. Petra Lang → **Nadine Falk** (Projektleitung Alpha);
  *Nachhaltigkeitsteam* (Team) bleibt; extern *Ferro Nord* bleibt. **0 Meridian-Leak** (Firma · Personen).
- **Friction:** Quelle nennt für „Projektleitung Alpha" **zwei** Namen (Reinhardt → Bergmann · Lang → Falk) —
  Korpus-Inkonsistenz, faithful auf zwei distinkte synth. Namen gemappt → bestätigt Empfehlung Liste `projectLeads`.
- `node --check` (app.js + data.js) grün; **29 Docs · 17 Szenarien** unverändert; nur 4 neue Dateien in `pilot-assets/`.

## Phase C (Vorbereitung) — 2026-07-16 — 4 Prosa-Zwillinge gestaged, `projekt-beta` vollständig, Korpus-Abdeckung 6/12 → 10/12 (kein Eingriff in prototype/)

**Zweites Pilot-Szenario vollständig als Zwilling, freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Nach `materialkosten` (5/5) staged dieser Zyklus die **4 Belege des zweiten
Pilot-Szenarios `projekt-beta`** als identitäts-bereinigte Text-Zwillinge (nicht-gated Pipeline-Hälfte,
Schritte 1+2 — Laden in `data.js` bleibt Schritt 3/gated). Damit ist `projekt-beta` als **zweites** der 3
Pilot-Szenarien **komplett** abgedeckt (4/4: Status · Eskalation · Nachtrag · Auftrag).

### Gebaut (nur `pilot-assets/muster-bau-gmbh/` — `prototype/` unverändert)
- **`build_beta_twins.py`** — reproduzierbarer Generator **mit Self-Check** (Anker-Zahlen erhalten · kein
  Meridian-Leak · synth. Namen present · externe Gegenparteien behalten). Additiv neben den 2 Vorgänger-Generatoren.
- **`projekt-beta-status_zwilling.txt`** — Projektbericht (Budget 8,6 Mio. €, 48 %/3 Wo. Verzug, Pönale max. 0,43 Mio. €, Q4 2026).
- **`eskalation-beta-elektronik_zwilling.txt`** — Eskalations-E-Mail Projektleitung → CFO (Cc CEO), 6-Wochen-Verzug ElektroSys, zitierter Verlauf.
- **`nachtrag-nordwind-beta_zwilling.txt`** — Nachtragsangebot NA-2026-0037 + Positionen (250k+110k+40k = 400.000 € netto / 476.000 € brutto).
- **`auftrag-nordwind-beta_zwilling.txt`** — Auftragsbestätigung NW-BEST-2026-0091 (Nordwind beauftragt verbindlich, 400.000 € netto / 476.000 € brutto).
- **README + `pilot.config.js`-Kommentar** fortgeschrieben (Beta-Zwillinge, CEO/CFO-Ersetzung, verschärfte projectLead-Friction).

### Verifiziert (deterministisch, Self-Check + unabhängiger grep)
- **Korpus-Abdeckung 6/12 → 10/12**; Szenario `projekt-beta` **4/4** Belege gestaged.
- **Personen-Regel:** Vogel → Hollmann (CFO), Brandt → Moser (CEO), Feldmann → Lindner (Projektleitung Beta),
  interne Domain `meridian-industrie.example → muster-bau.example`; extern (*Nordwind Logistik AG* / *ElektroSys GmbH*)
  bleibt. **0 Meridian-Leak** (Firma · Personen · Domain), unabhängiger grep bestätigt.
- **Friction verschärft:** eine **zweite** Projektleitung (Beta) ohne Config-Rolle → mehrere Projektleitungen
  → Schritt-3-Empfehlung von einzelner `projectLead`-Rolle auf **Liste `projectLeads`** angehoben.
- Anker-Zahlen je Datei erhalten (Zahlen bewusst **nicht** perturbiert — verbatim in Szenario-Zitaten).
- `git status`: nur 5 neue/geänderte Dateien in `pilot-assets/`; `node --check` (app.js + data.js) grün;
  **29 Docs · 17 Szenarien** unverändert.

## Phase C (Vorbereitung) — 2026-07-15 — 3 Prosa-Zwillinge gestaged, `materialkosten` vollständig, Korpus-Abdeckung 3/12 → 6/12 (kein Eingriff in prototype/)

**Erstes Pilot-Szenario vollständig als Zwilling, freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Nach den 2 Struktur-Zwillingen (2026-07-14) staged dieser Zyklus die **3
Prosa-Belege des primären Pilot-Szenarios `materialkosten`** (1 Finanzbericht + 2 E-Mails) als identitäts-
bereinigte Text-Zwillinge (nicht-gated Pipeline-Hälfte, Schritte 1+2 — Laden in `data.js` bleibt Schritt 3/gated).
Damit ist `materialkosten` als **erstes** der 3 Pilot-Szenarien **komplett** abgedeckt (5/5 Belege: Q1-Bericht
+ 2 E-Mails [neu] + Rechnung + Rahmenvertrag [CSV, Vorzyklus]).

### Gebaut (nur `pilot-assets/muster-bau-gmbh/` — `prototype/` unverändert)
- **`build_prose_twins.py`** — reproduzierbarer Generator **mit Self-Check** (Anker-Zahlen erhalten · kein
  Meridian-Leak · synth. Namen present · externe Gegenpartei behalten). Additiv neben `build_corpus_twins.py`.
- **`q1-bericht-2026_zwilling.txt`** — Quartalsbericht (Materialkosten +18,4 %, Stahl 780 → 920 €/t, §6, Ferro Nord).
- **`email-preisanpassung-donau_zwilling.txt`** — Lieferanten-E-Mail (15-%-Preisanpassung, 920 €, zitierter Verlauf).
- **`email-weiterleitung-materialbudget_zwilling.txt`** — interne Weiterleitung Einkauf → CFO (0,9 Mio. € Mehrbedarf).
- **README + `pilot.config.js`-Kommentar** fortgeschrieben (Prosa-Zwillinge, E-Mail-Domain-Regel, projectLead-Friction).

### Verifiziert (deterministisch, Self-Check + unabhängiger grep)
- **Korpus-Abdeckung 3/12 → 6/12**; Szenario `materialkosten` **5/5** Belege gestaged.
- **Personen-Regel:** Krüger → Kessler (Einkauf), Vogel → Hollmann (CFO), interne Domain
  `meridian-industrie.example → muster-bau.example`; extern (*Andreas Huber* / *Stahlwerk Donau AG* / *Ferro Nord*)
  bleibt. **0 Meridian-Leak** (Firma · Personen · Domain), unabhängiger grep bestätigt.
- **Neue Friction dokumentiert:** 7. Persona *Projektleitung Alpha* ohne Config-Rolle → ad hoc auf
  *Sandra Bergmann* gemappt; Schritt-3-Empfehlung: `projectLead` in `pilot.config.js` ergänzen.
- Anker-Zahlen je Datei erhalten (Zahlen bewusst **nicht** perturbiert — verbatim in Szenario-Zitaten).
- `git status`: nur 4 neue Dateien in `pilot-assets/`; `node --check` (app.js + data.js) grün; **29 Docs ·
  17 Szenarien** unverändert.

## Phase C (Vorbereitung) — 2026-07-14 — 2 Struktur-Zwillinge gestaged, Korpus-Abdeckung 1/12 → 3/12 (kein Eingriff in prototype/)

**Checkliste abarbeiten statt re-verifizieren, freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Der Kohärenz-Audit (2026-07-10) legte die 12-Dokument-Checkliste an; nur
**1 von 12** war als Zwilling gestaged. Dieser Zyklus staged die **2 strukturierten/tabellarischen** Belege
(die nicht-gated Pipeline-Hälfte, Schritte 1+2 — Laden in `data.js` bleibt Schritt 3/gated).

### Gebaut (nur `pilot-assets/muster-bau-gmbh/` — `prototype/` unverändert)
- **`build_corpus_twins.py`** — reproduzierbarer Generator **mit Self-Check** (Formelkette exakt + kein
  Meridian-Leak); wendet die Personen-Ersetzungs-Regel deterministisch an.
- **`rechnung-2026-1843_zwilling.csv`** — Positionstabelle mit **lebender Formelkette** netto = Menge × EP ·
  USt = netto × 19 % · brutto = netto + USt (`73.600 → 13.984 → 87.584 €`).
- **`rahmenvertrag-stahlwerk-donau_zwilling.csv`** — Klausel-Tabelle §9 Laufzeit · §6 Preisgleitklausel ·
  §12 Gewährleistung, identitäts-bereinigt.
- **README + `pilot.config.js`-Kommentar** fortgeschrieben: Personen-Zusage in den Struktur-Zwillingen erfüllt.

### Verifiziert (deterministisch, Self-Check)
- **Korpus-Abdeckung 1/12 → 3/12** (die drei tabellarischen Belege).
- **Personen-Regel (Audit-Gap 2) erstmals angewandt:** Krüger → Kessler (Einkauf), Wagner → Reinhardt (Recht),
  Meridian Industrie GmbH → Muster Bau GmbH; externer Lieferant *Stahlwerk Donau AG* bleibt. **0 Meridian-Leak**,
  alle 3 synth. Namen present.
- **Formelkette exakt:** brutto = netto × 1,19 bestätigt. Zahlen bewusst **nicht** perturbiert (verbatim in 2
  Szenario-Zitaten → ±10 %-Synthese an Schritt 3 gekoppelt, sonst neue Kohärenz-Lücke).
- `git status`: nur 3 neue Dateien in `pilot-assets/`; `node --check` (app.js + data.js) grün; **29 Docs ·
  17 Szenarien** unverändert.

**Kein Gate gehoben** (Vorbereitungs-Brick). Verbleibt gated: **9 Prosa-Belege** (redaktionelle Umschriften) +
Config-Wiring + Schritt-3-Übertragung in `data.js`. **Gate B→C wartet weiter nur auf Sven.**

## Phase C (Vorbereitung) — 2026-07-10 — Vorab-Kohärenz-Audit Schicht A ↔ B „Muster Bau GmbH" (kein Eingriff in prototype/)

**Neuer Prüf-Winkel statt Churn, freeze-konform.** Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert
(Gate B→C). Die zwei bereits gestageten Probelauf-Hälften (Schicht A `pilot.config.js` + Schicht B synth.
Zwilling) waren bisher **je isoliert** verifiziert; erstmals **gegeneinander** und gegen die Config-Versprechen
geprüft (deterministisch: Node-VM gegen `data.js` + openpyxl gegen beide `.xlsx`). Ziel: die gated §8-Übertragung
startet **warm** statt kalt.

### Gebaut (reine Doku/Config in `pilot-assets/` + Handover — `prototype/` unverändert)
- **README → „Vorab-Kohärenz-Audit Schicht A ↔ B"** + **§8-Notiz in [PILOT_KIT.md](PILOT_KIT.md)**: drei
  nicht-blockierende Kohärenz-Lücken protokolliert mit **verifizierter 12-Dokument-Checkliste** für Schritt 3.
- **Ehrlichkeits-Fix in `pilot.config.js`:** der Personen-Kommentar von „tauchen im Korpus auf" auf „**sollen**
  via Schritt 3 auftauchen (heute in 0 Artefakten)" gestellt.

### Verifiziert (deterministisch)
- **(1) Korpus-Abdeckung:** die 3 Pilot-Szenarien ziehen zusammen **12 verschiedene** Belege heran (aufgelistet);
  der Zwilling-`.xlsx` deckt nur die Materialkosten-Zahlen ab → **1 von 12**, die übrigen 11 sind gated (Schritt 3).
- **(2) Personen-Regel:** die 6 synth. Config-Personen erscheinen in **0** Artefakten (Zwilling 0, `data.js` 0);
  die 12 Quelldocs tragen heute die **Meridian**-Namen → Schritt 3 muss 1:1 ersetzen, sonst Meridian-Leak.
- **(3) §8-Eingaben:** die genannten Rechnungs-/Vertrags-CSV-Zwillinge sind **noch nicht gestaged** (Schritt 3).
- **`prototype/` unverändert** (`git status`: nur `README.md` + `pilot.config.js` + `PILOT_KIT.md`), `node --check`
  (app.js + data.js) grün, Live-Daten unverändert (**29 Docs · 17 Szenarien**). Ein Audit-Brick hebt kein Gate →
  **Gate B→C wartet weiter nur auf Sven.**

## Phase C (Vorbereitung) — 2026-07-09 — Pilot-Config (Schicht A) für „Muster Bau GmbH" real geschrieben (kein Eingriff in prototype/)

**Nächster Schritt des End-to-End-Probelaufs, freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Nachdem die Vorzyklen die Pipeline-Schritte 1+2 (synthetischer Korpus,
Schicht B) real ausgeführt haben, ist jetzt die **Schicht-A-Konfiguration** aus [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) §4
für denselben Probelauf-Kunden **konkret geschrieben** statt nur spezifiziert — neue Datei
[`pilot-assets/muster-bau-gmbh/pilot.config.js`](pilot-assets/muster-bau-gmbh/pilot.config.js), **außerhalb
`prototype/`** (nicht verdrahtet → Feature-Freeze gewahrt; das Wiring bleibt bis Gate B→C gated).

### Gebaut
- **`pilot.config.js`** — vollständige `window.PILOT_CONFIG` für **Muster Bau GmbH** (Hoch- & Tiefbau):
  Firmenname, Tagline, Logo-Glyph `▲`, Akzent, 4 synthetische Fakten, 6 synthetische Personennamen, Branche
  `bau`, `corpus`-Zeiger — **alle Werte 100 % synthetisch** (kein echter Name/kein Logo-Bild).
- **3 Schmerz-Szenarien = die verifizierte Bau-Startvorlage** aus [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md):
  `materialkosten` · `projekt-beta` · `vorstand-summary` (Money-Shot `agent-dazubuchen` bewusst **nicht**
  in der Liste → bleibt automatisch Demo-Finale).

### Verifiziert (deterministisch, Node-VM gegen die Live-`data.js`)
- **Faktenkorrektur belegt:** die Beispiel-IDs der Spec (`rechnungspruefung-donau`, `liquiditaet-90-tage`)
  **existieren nicht** in `data.js` — die real gewählten 3 IDs **existieren alle** (gegen `SCENARIOS` geprüft).
- Schema erfüllt: `active:true`, genau **3** Szenarien, `people`-Keys **deckungsgleich** mit `COMPANY.people`
  (audit/ceo/cfo/hr/legal/procurement), `logoGlyph` = 1 Glyph, 4 Fakten.
- **Kein Meridian-Leak** (kein „Meridian", keine echten Meridian-Personennamen im Config), Firmenname weicht ab.
- Live-Daten unverändert: **29 Dokumente · 17 Szenarien**; **`prototype/` unverändert** (`git status`: nur die
  neue `pilot.config.js`); `node --check` (config + app.js + data.js) grün.
- Ein Vorbereitungs-Brick hebt **kein** blockiertes Gate → **Gate B→C wartet weiter nur auf Sven.**

## Phase C (Vorbereitung) — 2026-07-09 — Pilot-Datenpipeline real ausgeführt (Muster Bau GmbH, Schritte 1+2, kein Eingriff in prototype/)

**Erstmals echte Ausführung statt Doku.** Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert
(Gate B→C). Statt eines 6. identischen Re-Verifikations-Zyklus (Churn) die größte unbewiesene Annahme des
Phase-C-Plans getilgt: Die [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) beschrieb den Workflow
„Kunden-Struktur rein → synthetischer Zwilling raus (Formeln intakt)" bislang nur **hypothetisch**. Jetzt sind
die **Schritte 1 + 2 tatsächlich ausgeführt** (die *nicht*-gated Hälfte; Schritt 3 = Laden in `data.js` bleibt
gated) — neuer Ordner [`pilot-assets/muster-bau-gmbh/`](pilot-assets/muster-bau-gmbh/README.md), **außerhalb
`prototype/`**.

### Gebaut & ausgeführt
- **`build_input.py`** — baut reproduzierbar eine fiktive **Muster-Bau-Controlling-Mappe** (2 Blätter:
  Annahmen + Monatsabschluss Mai) mit Gelb-Konvention (`FFF2CC`) auf echten Eingaben und **3 blattüber-
  greifenden Formeln** (`=Annahmen!B…`).
- **Synthetischer Zwilling** via `synthetic-data-creator` (`python synth.py --from … --seed 42`, Reuse,
  43/43 Tests grün) erzeugt.

### Verifiziert (deterministisch, openpyxl)
- **12/12 Formeln bit-genau erhalten**, inkl. der 3 blattübergreifenden (`E12=E11*Annahmen!B5/100` usw.).
- **Chirurgisch:** 12/14 gelbe Eingaben synthetisiert; **gesetzliche USt-Konstante 19 % unangetastet**
  (bewusst nicht gelb); Labels/Einheiten/Blätter unverändert.
- **Modell rechnet weiter:** Formelkette aus den synthetischen Werten nachgerechnet → Netto **284.266,41 €**,
  Brutto **338.277,03 €**, Probe **Brutto = Netto × 1,19** bestätigt, plausible Größenordnung.
- **Lernpunkt für echte Pilots:** feste/gesetzliche Konstanten *nicht* gelb markieren (sonst perturbiert die
  ±10 %-Heuristik) — im Log demonstriert. Keine blockierende Friction.
- **`prototype/` unverändert** (`git status`: nur `pilot-assets/` neu); `node --check` (app.js + data.js) grün.

Ein Vorbereitungs-Brick hebt kein blockiertes Gate → **Gate B→C wartet weiter nur auf Sven.** Die Pipeline ist
jetzt **ausgeführt & bewiesen**, nicht mehr nur beschrieben — der 48-h-Pilot ist damit spürbar de-risked.

## Phase B — 2026-07-09 — Link-Integrität der Handover-Suite verifiziert (frischer Prüf-Winkel, kein Eingriff)

**Reiner Verifikations-Zyklus, neue Dimension.** Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert
(Gate B→C); die vorziehbaren Phase-C-Doku-Bricks sind erschöpft (alle 5 fertig), jede weitere Phase-C-Arbeit
berührt `prototype/` und ist gated. Statt Doc-Zähl-/Konsistenz-Prüfungen ein weiteres Mal zu wiederholen
(Churn), diesmal die **interne Link-Integrität der gesamten Handover-Suite** geprüft — ein bisher nicht
abgedeckter Winkel: brechende Querverweise machen ein Verkaufs-/Aufnahme-Kit für einen Nicht-Techniker
unbrauchbar.

### Verifiziert (deterministisch, Node)
- **Interne Markdown-Links: 133 geprüft, 0 kaputt** über *alle* Wurzel-`.md` (VIDEO_*, RECORDING_CHECKLIST,
  PILOT_*, SCENARIO_LIBRARY, SYNTHETIC_DATA_PIPELINE, NEXT_STEPS, PROGRESS, OPEN_ITEMS u. a.). Jeder relative
  Datei-Link (Anker/`http(s)`/`mailto` ausgenommen) zeigt auf eine existierende Datei.
- **Live-Daten unverändert:** `data.js` = **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte
  Referenzen** (Quellen/Verwandte/Withheld/Chain); `DECISION_CHAIN` = **3 Schritte**.
- **Aufnahme-Pfad intakt:** `DEMO_ORDER` = **6 IDs** (alle existieren) mit `agent-dazubuchen` als **Finale**;
  `matchDocs("stahl")` = **10**, `matchDocs("")` = **29** (Palette-Zähler stimmt).
- `node --check` (app.js + data.js) grün; **`git status` sauber, `prototype/` unverändert** (Feature-Freeze
  gewahrt). **Keine Regression — die Demo ist unverändert aufnahmebereit.** Kein gehobenes Gate.
  **Gate B→C wartet weiter nur auf Sven.**

## Phase B — 2026-07-09 — Aufnahme-Bereitschaft verhaltens-verifiziert (Palette-Suche real nachgestellt, kein Eingriff)

**Reiner Verifikations-Zyklus, tieferer Winkel.** Phase B bleibt auf **Svens Aufnahme + Freigabe**
blockiert (Gate B→C); die vorziehbaren Phase-C-Doku-Bricks sind erschöpft (alle 5 fertig), jede weitere
Phase-C-Arbeit berührt `prototype/` und ist gated. Statt die Zähl-Prüfung ein drittes Mal identisch zu
wiederholen (Churn), diesmal die **tatsächliche Such-Verhaltensweise** verifiziert, die ein CFO on-camera
auslöst: nicht ein Ganz-Objekt-Scan, sondern die reale `matchDocs()`-Feldmenge
(`title · type · snippet · author · module`) exakt nachgestellt.

### Verifiziert (deterministisch, Node-VM gegen `data.js` + `app.js`-Logik nachgestellt)
- **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte Referenzen** (Quellen/Verwandte/
  Withheld) — unverändert.
- **Command-Palette real nachgestellt:** die `matchDocs()`-Feldmenge exakt repliziert →
  `matchDocs("stahl")` = **10 Treffer**, `matchDocs("")` = **29** (volles Inventar). Ein naiver
  Ganz-Objekt-Scan liefert 12 — der Palette-Zähler auf der Leinwand ist aber **10** (belegt, dass die
  im Skript/Checkliste genannte „10" die *sichtbare* Zahl ist, nicht die Rohzahl).
- **Demo-Steuerung aus `app.js` aufgelöst:** `MONEY_SHOT_ID = "agent-dazubuchen"` (existiert in `data.js`),
  `DEMO_ORDER` = **6 IDs** mit dem Money-Shot als **Finale**; `DECISION_CHAIN` = **3 Schritte**
  (Donau 12.02. → Einkauf→CFO 13.02. → Vorstand März).
- **Keine veralteten Zähl-Reste** (16/27/28) in VIDEO_SCRIPT / VIDEO_SCENES / RECORDING_CHECKLIST (`grep`).
- `node --check` (app.js + data.js) grün; **`git status` sauber, `prototype/` unverändert** (Feature-Freeze
  gewahrt). **Keine Regression — die Demo ist unverändert aufnahmebereit.** Kein gehobenes Gate.
  **Gate B→C wartet weiter nur auf Sven.**

## Phase B — 2026-07-09 — Pilot-Kit-Konsistenz-Audit (Doku ↔ Live-Daten, kein Eingriff)

**Reiner Verifikations-Zyklus, neuer Prüf-Winkel.** Phase B bleibt auf **Svens Aufnahme + Freigabe**
blockiert (Gate B→C); die vorziehbaren Phase-C-Doku-Bricks sind erschöpft, jede weitere Phase-C-Arbeit
berührt `prototype/` und ist gated. Statt die reine „Aufnahme-Bereitschaft" ein zweites Mal identisch zu
prüfen (Churn), diesmal ein **anderer Winkel**: die Phase-C-Verkaufs-/Handover-Dokumente (das
„Verkaufs-Werkzeug") **gegen die Live-Daten** abgeglichen — genau die Klasse Drift, die zuvor die
27/28 → 29-Dokumentenzahl in den Video-Dateien aufdeckte.

### Verifiziert (deterministisch, Node-VM gegen `data.js` + `grep` der Doku)
- **Zahlen deckungsgleich:** `data.js` liefert **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt ·
  DECISION_CHAIN = 3 Schritte** — exakt die in SCENARIO_LIBRARY / PILOT_KIT / SYNTHETIC_DATA_PIPELINE
  zitierten Zahlen.
- **Szenario-Abdeckung vollständig:** alle **17** Szenario-IDs aus `data.js` sind in
  [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) referenziert — **0 fehlend**.
- **Agenten-Preise stimmen:** [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) nennt **Reporting 400 € ·
  Vertrags 500 € · Rechnungs 600 €** — bit-genau die `answer.agents`-Preise des Money-Shots
  `agent-dazubuchen`; Auskunfts-Agent „inklusive/aktiv", Reporting „empfohlen".
- **Preis-Pfad konsistent:** **Audit 149 € → Foundation ab 5.000 € → Agent-Abo ab 400 €/Monat** identisch
  in One-Pager und [PILOT_KIT.md](PILOT_KIT.md); Money-Shot `agent-dazubuchen` = `DEMO_ORDER`-Finale.
- `node --check` (app.js + data.js) grün; **`git status` sauber vor dem Schreiben, `prototype/`
  unverändert** (Feature-Freeze gewahrt). **Zero Drift** — das Pilot-Kit ist als Verkaufs-Werkzeug in sich
  stimmig und deckungsgleich mit der Demo. Kein gehobenes Gate. **Gate B→C wartet weiter nur auf Sven.**

## Phase B — 2026-07-09 — Aufnahme-Bereitschaft re-verifiziert (Wartepunkt, kein Eingriff)

**Reiner Verifikations-Zyklus.** Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C);
die vorziehbaren Phase-C-Doku-Bricks sind erschöpft (alle 5 fertig), die restlichen Schritte berühren
`prototype/` und sind bis Gate B→C gated. Statt zu churnen die einzig freeze-konforme Handlung: bestätigen,
dass die Demo unverändert aufnahmebereit ist.

### Verifiziert (deterministisch, Node-VM gegen `data.js`)
- **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte Referenzen** (Quellen/Verwandte/
  Withheld/Entscheidungskette) — unverändert gegenüber der letzten Messung.
- **`DEMO_ORDER` = 6 IDs**, alle als Szenarien vorhanden, **Money-Shot `agent-dazubuchen` als Finale**;
  „stahl"-Suche = **10 Treffer**; `DECISION_CHAIN` = 3 Schritte.
- `node --check` (app.js + data.js) grün; `grep`: **keine** veralteten Zähl-Reste (16/27/28) in
  VIDEO_SCRIPT / VIDEO_SCENES / RECORDING_CHECKLIST.
- **`git status` sauber, `prototype/` unverändert** (Feature-Freeze gewahrt). Kein gehobenes Gate — reiner
  Regressionsschutz für das noch aufzunehmende Video. **Gate B→C wartet weiter nur auf Sven.**

## Phase C (Vorbereitung) — 2026-07-09 — PILOT_KIT.md (48-h-Master-Runbook, Playbook-Portion)

**Capstone-Deliverable der Phase C (5 von 5), freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Die vier vorbereitenden Bricks werden jetzt zu **einem** durchgehenden
Ablauf zusammengefügt — reine `.md`, **kein Eingriff in `prototype/`**.

### Neu: `PILOT_KIT.md`
- **Master-Runbook**, das [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) (Angebot), [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)
  (3 Szenarien), [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) (Datenpipeline) und
  [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) (Umbranding) zu **einem** 48-h-Prozess orchestriert.
- **Ablauf T+0 → T+48** als Diagramm: Audit-Call → 3 Szenarien wählen → synth. Zwilling erzeugen →
  Schicht A (`pilot.config.js`) + Schicht B (`data.js`-Korpus) → deterministisch verifizieren → Übergabe.
- **Kopierbare Master-Checkliste** (ein Pilot = eine Kopie), **Zeit-Budget** (~2–4 h Netto-Handaufwand),
  **Definition of Done** und ein **Probelauf-Protokoll „Muster Bau GmbH"** als klar markierter Platzhalter.
- **Freeze-Grenze ausdrücklich:** die `prototype/`-berührenden Schritte (Schritt 3 + Config-Wiring) und der
  **tatsächliche Probelauf** warten auf **Gate B→C**; hier steht nur der **dokumentierte Prozess** bereit.
- **Reine Handover-Datei, `prototype/` unverändert:** `git status` zeigt nur die neue `.md`, `node --check`
  (app.js + data.js) grün, alle internen Querverweise lösen auf.

## Phase C (Vorbereitung) — 2026-07-09 — PILOT_CONFIG_SPEC.md (Umbranding-Mechanismus spezifiziert)

**Design-Portion der Phase-C-Deliverable 1, freeze-konform.** Phase B bleibt auf **Svens Aufnahme +
Freigabe** blockiert (Gate B→C). Statt eines weiteren identischen Re-Verifikations-Zyklus die
**Design-Portion** der nächsten Brick vorgezogen — reine `.md`, **kein Eingriff in `prototype/`**.

### Neu: `PILOT_CONFIG_SPEC.md`
- **Kernaufschluss (grounded durch Lesen von `prototype/`):** Der Firmenname „Meridian Industrie GmbH"
  steht **~55-mal** in `data.js`-Dokumentkörpern → naives „Name im Config ändern" schlägt nicht durch.
- **Auflösung — zwei Schichten:** **A) Shell/Chrome** per neuer `pilot.config.js`, die das `COMPANY`-Objekt
  überschreibt (Shell liest es heute schon fast überall: `renderCompanyCard`, Hero, Briefing-Fußzeile,
  `#searchCompany`); **B) Dokumentenkorpus wholesale ersetzt** durch den synthetischen Zwilling
  (`SYNTHETIC_DATA_PIPELINE.md`), nicht per Suchen-Ersetzen.
- **Config-Schema** (`company`/`industry`/**genau 3** `scenarios`/optional `accent`+`corpus`), additiver
  **Wiring-Plan** (Script-Tag + `Object.assign`-Guard + `applyPilotChrome()`), **Token-Konvention**
  `{{COMPANY}}` gegen künftige Hartkodierung, **48-h-Ablaufdiagramm** und **Abnahme-Kriterien**.
- **Regressionsschutz fürs Video:** `active:false`/fehlende Datei → **bit-identische** Meridian-Demo.
- **Reine Design-Datei, `prototype/` unverändert** (Feature-Freeze gewahrt): `git status` nur die neue
  `.md`, `prototype/` 0 geänderte Dateien, `node --check` (app.js + data.js) ok. Die **Implementierung**
  berührt `prototype/` → **erst nach Gate B→C**.

## Phase C (Vorbereitung) — 2026-07-09 — SYNTHETIC_DATA_PIPELINE.md (Datenpipeline dokumentiert)

**Dritte Phase-C-Deliverable, freeze-konform.** Phase B bleibt auf **Svens Aufnahme + Freigabe**
blockiert (Gate B→C). Die nächste `prototype/`-freie Doku-Brick nach Plan: der **Workflow für
synthetische Pilot-Daten** — reine Prozessdatei, **kein Eingriff in `prototype/`**.

### Neu: `SYNTHETIC_DATA_PIPELINE.md`
- Dokumentiert **einen wiederholbaren Weg**: **Kunden-Dateistruktur rein → synthetischer Zwilling
  raus (Formeln intakt) → in `prototype/data.js` geladen** — passend zum 48-h-Pilot-Versprechen
  („kein einziges echtes Dokument nötig").
- **Reuse statt Neubau:** nutzt das bestehende Tool `C:\Users\botrunner\projects\synthetic-data-creator`
  (**43/43 Tests** verifiziert), inkl. Mehrblatt-Excel mit **Formelerhalt** (auch blattübergreifend),
  Gelb-Konvention (`FFF2CC`-Eingabezellen), CSV/JSON/XLSX/PDF, `--seed` für reproduzierbare Demos.
- **4-Schritt-Prozess** (Audit-Call → Eingabe formen → `python synth.py --from …` → Eintrag in `DOCS`/
  `lineItems` → deterministisch verifizieren) + Ablaufdiagramm + Beispieltabelle „Muster Bau GmbH".
- **Freeze-Grenze klar markiert:** Schritt 3 (Eintrag in `data.js`) und PILOT_CONFIG berühren
  `prototype/` → **erst nach Gate B→C**. **Verifikation:** `git status` sauber, `node --check`
  (app.js + data.js) ok, `prototype/` unverändert, Tool-Tests 43/43. (Phase-C-Deliverable 3 von 5.)

## Phase C (Vorbereitung) — 2026-07-09 — PILOT_ONE_PAGER.md (Angebotsdokument)

**Zweite Phase-C-Deliverable, freeze-konform.** Phase B bleibt auf **Svens Aufnahme + Freigabe**
blockiert (Gate B→C). Statt zu churnen die nächste `prototype/`-freie Doku-Brick nach Plan:
das **Angebotsdokument** für den Audit-Call — reine Vertriebsdatei, **kein Eingriff in `prototype/`**.

### Neu: `PILOT_ONE_PAGER.md`
- Ein-Seiten-Angebot in **CFO-Sprache** (kein Technik-Jargon): das 48-h-Versprechen („Ihre eigene
  Demo, kein echtes Dokument nötig"), **was der Kunde nach 48 h sieht** (Name/Logo, 3 Schmerz-
  Szenarien, belegte Antworten, Money-Shot) und der **Preis-Pfad** als Tabelle: Audit **149 €** →
  Wissensbasis **ab 5.000 €** → Agent-Abo **ab 400 €/Monat**.
- **Agenten-Preisvergleich** (Auskunft inkl. · Reporting ab 400 € · Vertrag ab 500 € · Rechnung ab
  600 €) + „digitale Mitarbeiter statt Recruiting"-Argument; **Einwand-Antworten** (Daten bleiben im
  Haus · keine erfundenen Antworten · Berechtigungen bleiben · Einstieg nur 149 €); klarer CTA.
- Preise/Agenten deckungsgleich mit dem Money-Shot des Prototyps (`agent-dazubuchen`) und der
  [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md). **Verifikation:** `git status` zeigt **nur** die neue
  `.md`; `node --check` (app.js + data.js) ok, `prototype/` unverändert. **Gate B→C wartet weiter
  nur auf Svens Aufnahme + Freigabe.**

## Phase C (Vorbereitung) — 2026-07-09 — SCENARIO_LIBRARY.md (Pilot-Szenarienbibliothek)

**Erste Phase-C-Deliverable, freeze-konform gestartet.** Phase B bleibt auf **Svens Aufnahme + Freigabe**
blockiert (Gate B→C); ein dritter identischer Re-Verifikations-Zyklus wäre reines Churnen. Stattdessen die
niedrigst-riskante Phase-C-Aufgabe vorgezogen: die **Szenarienbibliothek** — reine Dokumentation aus
`data.js`, **kein Eingriff in `prototype/`** (Feature-Freeze gewahrt), kein neues Feature.

### Neu: `SCENARIO_LIBRARY.md`
- Alle **17 bestehenden Szenarien** nach **Schmerz** (KOSTEN · RECHNUNGSPRÜFUNG · VERTRÄGE ·
  MONATSABSCHLUSS · PROJEKTE · LIQUIDITÄT/RISIKO · COMPLIANCE · WISSENSVERLUST · ESG/GOVERNANCE) und
  **Branche** verschlagwortet, mit Modul, Konfidenz und Belegzahl (deterministisch aus `data.js` gelesen).
- **Fertige 3er-Startvorlagen** je Branche (Fertigung · Bau · Handel · Logistik · Dienstleistung ·
  Querschnitt) + Auswahl-Spickzettel → nach einem 30-Min-Audit-Call in Minuten 3 passende Szenarien wählbar.
- Der **Money-Shot** (`agent-dazubuchen`) ist als automatisches Finale markiert (nicht mitgezählt).
- **Verifikation:** `node --check` (app.js + data.js) ok; `git status` zeigt **nur** die neue `.md`,
  `prototype/` unverändert. **Gate B→C wartet weiter nur auf Svens Aufnahme + Freigabe.**

## Phase B — 2026-07-09 — Aufnahme-Bereitschaft re-verifiziert (Wartepunkt, keine Änderung)

**Reiner Verifikations-Zyklus.** Phase B ist blockiert auf **Svens Aufnahme + Freigabe** (Gate B→C); der
Feature-Freeze verbietet neue Arbeit. Die einzige freeze-konforme Handlung ist, die Voraussetzung des
Blockers zu sichern: **dass die Demo unverändert aufnahmebereit ist.** Bestätigt — keine Regression.

### Verifikation (keine Dateiänderung im `prototype/`)
- `node --check` für `app.js` **und** `data.js`: syntaktisch fehlerfrei.
- Ground-Truth deterministisch (Node-VM gegen `data.js` + `DEMO_ORDER` aus `app.js`): **29 Dokumente**,
  **17 Szenarien**, **3 E-Mails**, **2 gesperrt**, **0 kaputte Referenzen** (sources/related/withheld/
  chain/DECISION_CHAIN); `DEMO_ORDER` = **6** IDs, **keine fehlt**, **Money-Shot als Finale**; „stahl"-
  Suche = **10 Treffer**.
- `grep` über die Video-Handover-Dateien: **keine** veralteten Zähl-Referenzen (16/27/28) mehr.
- **Ergebnis:** Alle Werte stimmen mit Skript, Shotlist und Checkliste überein → Sven kann ohne
  Abweichung zwischen Datei und Bildschirm aufnehmen.

## Phase B — 2026-07-09 — Skript & Shotlist auf die reale Demo angeglichen (Faktenkorrektur)

**Die Video-Handover-Dateien nannten Zahlen, die nicht mehr zum Prototyp passen** — ein nicht-technischer
Aufnehmer hätte sie für einen Fehler gehalten. Gegen die Live-Daten geprüft und korrigiert (nur `.md`,
`prototype/` unverändert, Feature-Freeze gewahrt).

### Korrigiert
- **Dokumentenzahl 27/28 → 29** (Such-Beat/Command-Palette-Zähler) in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)
  (Szene 0b) und [VIDEO_SCENES.md](VIDEO_SCENES.md) (Szene 0a + B-Roll + „Globale Suche"); „10 von 27" →
  „10 von 29". (Der „stahl"→**10 Treffer** war bereits korrekt.)
- **Geführte Demo: „alle 16 Szenarien / n / 16" → „kuratierte 6er-Kern-Auswahl / n / 6"** (endet auf dem
  Money-Shot, < 4 Min) — die seit Phase-A-Abschluss reale `DEMO_ORDER`. In den Aufnahme-Hinweisen beider
  Dateien richtiggestellt.
- **Klarstellungs-Hinweis** ergänzt (beide Dateien): die Szene-für-Szene-Abfolge ist die **manuelle
  Langfassung**; die Geführte Demo deckt davon 6 Kern-Momente automatisch ab. Verbindliche Aufnahme-
  Anleitung bleibt [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md).

### Verifikation
- Ground-Truth deterministisch (Node-VM gegen `data.js`): **29 Dokumente**, **17 Szenarien**, „stahl"-
  Suche = **10 Treffer**; `DEMO_ORDER` = **6** IDs mit dem Money-Shot als Finale. Anschließend `grep`:
  **keine** veralteten Zähl-Referenzen (16/27/28) mehr in Skript oder Shotlist.

## Phase B — 2026-07-08 — `VIDEO_SUBTITLES.de.srt` (optionale, aber wertvolle Deliverable)

**Die in der Phase-B-Checkliste als „optional, aber wertvoll" genannte Untertiteldatei ist erstellt** —
eine fertige deutsche SRT aus dem Sprechertext von [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). Damit sind alle
Phase-B-Deliverables (Skript · Shotlist · Checkliste · **Untertitel**) vorhanden; das Gate B→C wartet
weiterhin allein auf **Svens Aufnahme + Freigabe**.

### Neu
- **`VIDEO_SUBTITLES.de.srt`** — **47 Cues**, deutsch, direkt aus den `Sprecher`-Zeilen des Skripts
  abgeleitet (je 1–2 Zeilen, alle ≤ 55 Zeichen). Monotone Zeitleiste ~0:00–4:22, entspricht der
  **manuellen Langfassung** aller Szenen (inkl. optionaler Ressort-Beats 5b). Standardformat, in jedes
  Schnittprogramm/Player einlesbar.

### Verzahnung / Reuse
- **Reine Handover-Datei** — kein Prototyp-Code berührt (`prototype/` unverändert, Feature-Freeze gewahrt).
  Kurze Verweis-Sektion „Untertitel (SRT)" in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) ergänzt (Fundort +
  Hinweis: Timings sind Richtwerte, beim finalen Schnitt angleichen; nicht gefilmte Cues entfernen).

### Verifikation
- SRT deterministisch geparst (Node): **47 Cues**, Indizes lückenlos aufsteigend 1–47, alle Timecodes
  wohlgeformt, **keine Überlappung** (Start ≥ vorheriges Ende), Ende > Start je Cue, **kein Cue > 2 Zeilen**,
  **keine Zeile > 55 Zeichen**. Letztes Cue endet 00:04:21,500.

## Phase B — 2026-07-08 — `RECORDING_CHECKLIST.md` (letzte Kern-Deliverable der Videoproduktion)

**Die dritte und letzte Phase-B-Kern-Deliverable ist erstellt** — eine narrensichere Aufnahme-Checkliste,
mit der eine **nicht-technische Person** das Verkaufsvideo ohne Vorwissen aufnehmen kann. Damit sind alle
drei Phase-B-Deliverables (Skript · Shotlist · Checkliste) vorhanden; das Gate B→C wartet nur noch auf
**Svens Aufnahme + Freigabe**.

### Neu
- **`RECORDING_CHECKLIST.md`** — Schritt-für-Schritt, ausdrücklich für Nicht-Techniker:
  Browser-Setup (Chrome, Vollbild, 100 % Zoom, **„Bewegung reduzieren" AUS**), das **Reset-Ritual vor
  jedem Take** (Inkognito für das Onboarding-Intro, „⟲ Zurücksetzen"), der **schnellste Weg über die
  Geführte Demo** (6 Kern-Szenen, „n / 6", endet auf dem Money-Shot, < 4 Min), Nachvertonung des
  Sprechertexts, eine **Fehler→Behebung-Tabelle** mit Retake-Regel, die optionale manuelle Langfassung
  (alle 17 Szenarien) und ein **Kurz-Spickzettel** zum an-den-Monitor-Kleben.
- Bewusst gegen die **reale** Geführte Demo geschrieben (6 kuratierte Szenen, 29 Dokumente, Such-Beat
  tippt „stahl") — nicht gegen die ältere 16-Szenen-Beschreibung in Skript/Shotlist (die die
  ausführliche **manuelle** Fassung abbilden).

### Verzahnung / Reuse
- **Reine Handover-Datei** — kein Prototyp-Code berührt (`prototype/` unverändert, Feature-Freeze gewahrt).
  Verweist auf [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) (Sprechertext) und [VIDEO_SCENES.md](VIDEO_SCENES.md)
  (Detail-Shotlist für die manuelle Langfassung).

### Verifikation
- Ground-Truth deterministisch gegen `prototype/` geprüft (Node-VM): **29 Dokumente**, **17 Szenarien**,
  2 gesperrt, 3 E-Mails; `DEMO_ORDER` = 6 IDs (materialkosten → beleg-rechnung → budget-herkunft →
  projekt-portfolio → strategie-ausblick → **agent-dazubuchen** als Finale); Reset-Button `#resetBtn`
  („⟲ Zurücksetzen") in `index.html`; Onboarding-Flag `aistudio.onboarded.v1`; Such-Beat-Begriff „stahl".
  Alle Zahlen/Bezeichnungen der Checkliste entsprechen dem laufenden Prototyp.

## Phase A — 2026-07-08 — Geführte Demo kuratiert (≤ 4 min) + Ein-Klick „Zurücksetzen" ✅ PHASE A ABGESCHLOSSEN

**Die letzten beiden Phase-A-Kästchen — Timing-Gate und wiederholbarer Startzustand — sind erledigt.**
Damit ist der Demo-Freeze (Phase A) komplett; die Mission geht auf **Phase B — Videoproduktion** über.

### Neu
- **Kuratierte Kern-Reihenfolge der Geführten Demo** (`DEMO_ORDER` + `demoScenarios()` in `app.js`): Die
  hands-free-Vorführung spielt jetzt eine **straffe 6er-Auswahl** statt aller 17 Szenarien — ein klarer
  Story-Bogen fürs Verkaufsvideo, der **immer mit dem Money-Shot endet**:
  1. **Materialkosten** (94 %) — belegte Antwort · Quellen · Konfidenz · E-Mail aus dem Postfach
  2. **Belege zu Rechnung 2026-1843** (97 %) — Drei-Wege-Abgleich · prüfungsechte Rechnungsprüfung
  3. **Herkunft Mehrbudget 0,9 Mio. €** (95 %) — Entscheidungskette als sichtbarer Beleg-Pfad
  4. **Welche Projekte laufen aktuell?** (94 %) — Ampel Alpha + Beta · Breite + ehrliche Risiko-Kennzeichnung
  5. **Wachstumsstrategie** (88 %) — Governance: „weitere Treffer für Sie nicht freigegeben"
  6. **Agenten dazubuchen** — **MONEY-SHOT** · Finale · verkauft das Abo
  Fail-safe: unbekannte/doppelte IDs werden übersprungen, der Money-Shot steht garantiert am Ende, leere
  Kuratierung fällt sicher auf die volle Liste zurück. Alle 17 Szenarien bleiben per Kachel/Frage/Suche
  erreichbar — nur die *hands-free*-Reihenfolge ist kuratiert. Fortschritt zeigt jetzt „n / 6".
- **Ein-Klick „Zurücksetzen"** (Topbar-Button `#resetBtn` + `resetDemo()` in `app.js`): bringt die App in
  den **sauberen Startzustand** für wiederholbare Video-Takes — laufende Demo sauber stoppen, Verlauf
  leeren, Viewer/Palette schließen, zurück auf den Hero. Sekundär-Stil (Reuse der Marken-Tokens).

### Verzahnung / Reuse
- **Rein additiv:** `DEMO_ORDER`/`demoScenarios()`/`wireReset()`/`resetDemo()` in `app.js`, `.reset-btn`
  in `styles.css`, ein Button in `index.html`. **Kein neues Szenario/Dokument/Modul** (Feature-Freeze
  eingehalten); `data.js` unverändert. Reuse von `stopDemo()`/`resetDemoUi()`/`closeViewer()`/
  `closeSearch()`/`selectModule()`.

### Verifikation
- `node --check app.js` ok; Node-VM gegen `data.js`: alle 6 kuratierten IDs existieren, Money-Shot ist
  **letztes** Element (17 Szenarien gesamt). Live im Browser (DOM gegen reale Daten): Reset-Button
  rendert („⟲ Zurücksetzen", Pill, `--ink-soft`); Klick nach einer Frage → Hero zurück, 0 User-Bubbles,
  0 Antworten, 14 Vorschläge, Viewer zu, Composer entsperrt; Geführte Demo zeigt **„1 / 6"**; Reset
  **mitten in der Demo** stoppt sauber (running=false, Fortschritt verborgen, Hero zurück, Input
  entsperrt); **keine Konsolenfehler**. (Screenshot-Capture harness-instabil — bekannte Grenze; daher
  DOM/CSS-basiert verifiziert.)

### Gate A → B
**PHASE_A_COMPLETE.** Alle sechs Checklisten-Kästchen erfüllt: hands-free Geführte Demo ohne
Konsolenfehler · Answer/Quellen/Konfidenz/Kette rendern (1920×1080) · Ein-Klick Demo-Reset · Timing
(6 Szenarien ≈ ≤ 2 min, je ≤ 25 s) · Finale = Money-Shot · durchgängig Deutsch. **Nächste Phase:
Videoproduktion** (VIDEO_SCRIPT / VIDEO_SCENES / RECORDING_CHECKLIST).

## Phase A — 2026-07-08 — Money-Shot „Agenten dazubuchen" (Demo-Finale) 🤝

**Mission-Wechsel auf AI STUDIO — PILOT SPRINT (v2); Phase A (Demo-Freeze).** Das größte Phase-A-Loch war
der **Verkaufsmoment des Abos**: der Moment, in dem der Kunde sieht, wie er **einen weiteren Agenten
dazubucht — wie einen neuen Mitarbeiter**. Jetzt schließt die Geführte Demo genau damit.

### Neu
- **Abschluss-Szenario `agent-dazubuchen`** (letztes in `SCENARIOS` → automatisch **letzte Szene** der
  Geführten Demo): „Kann ich einen weiteren Agenten dazubuchen?" Die Wissensbasis steht — jetzt mietet
  der Kunde **digitale Mitarbeiter** obendrauf.
- **Agenten-Marktplatz** (`answer.agents` + Renderer `appendAgents()`): 4 Karten — **Auskunfts-Agent**
  (inklusive/aktiv), **Reporting-Agent 400 €/Monat (empfohlen)**, **Rechnungs-Agent 600 €**,
  **Vertrags-Agent 500 €**; je „＋ Dazubuchen"-Button → kurze Einrichtung → grüne **„✓ Aktiviert · Teil
  Ihres Teams"**-Bestätigung. Preis-Pfad-Fußzeile: Audit 149 € → Wissensbasis ab 5.000 € → Agent ab
  400 €/Monat.
- **Hands-free-Payoff:** In der Geführten Demo **bucht sich der empfohlene Agent selbst** (token-
  gesichert); die Schluss-Pause der Demo wächst 1600 → 3400 ms, damit die „Aktiviert"-Bestätigung
  sichtbar stehen bleibt.
- **Beauftragung Nordwind** (`auftrag-nordwind-beta`, Typ „Auftragsbestätigung", BEAUFTRAGT-Stempel):
  Nordwind beauftragt den Nachtrag schriftlich → Betas **+0,4 Mio. €** sind jetzt **beidseitig** belegt
  (Angebot + Auftrag; 4. Quelle in `projekt-beta`). *(Rest-WIP aus dem alten Modus, hier abgeschlossen.)*

### Verzahnung / Reuse
- **Rein additiv:** neuer `answer.agents`-Block + `appendAgents()`/`bookAgent()`/`scheduleAutoBook()` in
  `app.js`, `.block.agents`-Stile in `styles.css`, Szenario + Doc in `data.js`. Antwortkopf zeigt für die
  **Buchungsansicht kein Konfidenz-Meter** (`hasConf`-Guard in `streamAnswer()`) — außerhalb des Money-
  Shots unverändert. Bestehender Antwortpfad, Skins und alle Szenarien unangetastet.

### Verifiziert
- `node --check` ok; Node-VM gegen `data.js`: **29 Docs, 17 Szenarien, 0 kaputte Referenzen**, Money-Shot
  ist die letzte Szene (4 Agenten: 1 empfohlen, 1 aktiv). Live (DOM/CSS gegen reale Daten @1920×1080):
  4 Karten, 3 Buchen-Buttons + Aktiv/Empfohlen-Badge, **Grid 2-spaltig (377 px)**, Buchen-Button Marken-
  Indigo, gebuchte Karte grün, Antwortkopf **ohne** Konfidenz-Meter, **keine Konsolenfehler**. (Streaming-/
  Screenshot-Pfad im Headless-Harness gedrosselt → DOM/CSS/Daten-basiert verifiziert, wie in den Vorzyklen.)

## Zyklus 24 — 2026-07-08 — Konfidenz-/Relevanz-Balken laufen mit hoch 📈

**Die Antwort „springt" nicht mehr — sie wächst.** Beim Einblenden zählten Tempo-Signal und Kernzahlen
schon hoch, aber der **Balken** des Konfidenz-Meters sprang sofort auf seinen Endwert. Jetzt läuft er —
passend zum Zahlen-Count-up — sichtbar hoch; die Konfidenz-Zahl im Kopf zählt zusätzlich mit. Die letzte
sichtbare Bewegungs-Kante im Antwortkopf, geschlossen.

### Neu
- **Konfidenz-Balken hochlaufend:** beim Einblenden einer Antwort läuft der Meter-Balken in ~**760 ms**
  (easeOutCubic) von **0 auf den Zielwert** statt hart zu springen. Die **Konfidenz-Zahl** im Kopf zählt
  über den bestehenden `countUp()` synchron mit hoch.
- **Relevanz-Balken im Popover:** die drei Balken der Konfidenz-Herleitung laufen beim **ersten** Öffnen
  des Popovers (Hover/Focus) einmalig hoch (640 ms); danach bleiben sie stehen.

### Verzahnung / Reuse
- **Rein additiv:** neuer Helfer `animateBar(fill, dur)` (analog `animateCounts()`/`countUp()`) +
  `wireConfPopBars(card)` in `app.js`, drei Zeilen Wiring in `streamAnswer()`, ein `will-change: width`-
  Hinweis auf `.conf-bar i, .cp-bar i` in `styles.css`. Kein neues Dokument, kein Datenpfad-Umbau;
  `data.js`/`index.html` unverändert. Bestehende Zähl-Animationen unberührt.
- **Barrierefrei:** `prefers-reduced-motion` **oder** Zielwert ≤ 0 → sofort auf den Endwert (kein
  Sprung-Artefakt, keine Leer-Animation).

### Verifikation
- `node --check app.js` ok, Wiring-Checks bestanden. Live (DOM gegen reale Daten): Konfidenz-Kopf **94 %**
  (Zahl + Balken finit, kein NaN), Popover-`mouseenter` → **3 cp-Balken** finit (75/96/92 %), **keine
  Konsolenfehler**. Reduced-motion-Pfad (headless meldet `reduce`) setzt korrekt **sofort** den Endwert;
  Motion-Ramp startet nachweislich bei 0 (Zwischenwert 0,04 % am Frame-Start). Vollanimation im Headless-
  Preview rAF-gedrosselt, Screenshot-Capture instabil — bekannte Harness-Grenzen, daher DOM/Daten-basiert.

## Zyklus 23 — 2026-07-08 — Nachtragsangebot an Nordwind: Betas letzte Zahl wird belegt 🧾

**Der Kunden-Änderungswunsch (+0,4 Mio. €) ist jetzt ein Original-Beleg, keine Behauptung mehr.** Nach
Zyklus 22 war Betas Breite rund (Portfolio-Überblick als Klammer), aber die **+0,4 Mio. €** für die
zusätzliche Prüfstation waren die einzige Beta-Zahl **ohne** Belegdokument. Neu ist der kaufmännische
Nachweis, *wie* Meridian den Scope-Change beim Kunden geltend macht — derselbe lückenlose Beleg-Anspruch,
den Alpha (Entscheidungskette) und der Reklamations-Vorgang bereits erfüllen.

### Neu
- **Dokument `nachtrag-nordwind-beta`** (Typ **„Nachtragsangebot"**, Modul Berichte): Nachtragsangebot
  **NA-2026-0037** von Meridian an die **Nordwind Logistik AG**, Bezug Rahmenauftrag NW-2025-0442.
  Positionstabelle (Reuse des Beleg-Skins mit `lineItems`): zusätzliche **Prüfstation** 250.000 € +
  **Engineering/SPS-Integration** 110.000 € + **erweiterte FAT** 40.000 € = **400.000 € netto**, USt 19 %
  76.000 €, **Angebotssumme brutto 476.000 €**. Aussteller = **Meridian** (kein extIssuer); neutraler
  **NACHTRAG**-Stempel (Ton `ink`, bestehend). Datum 27.03.2026 (nach Change-Request 18.03., vor
  Statusbericht 31.03.) → chronologisch konsistent.
- **In `projekt-beta` eingewoben:** als **3. Quelle** (82 %) plus neuer Reasoning-Schritt („Kunden-
  Änderungswunsch (+0,4 Mio. €) über das Nachtragsangebot an Nordwind kaufmännisch belegt"), in `related`
  ergänzt und neue Folgefrage **„Zeig mir den Nachtrag an Nordwind."** → in der Geführten Demo klickbar.

### Verzahnung / Reuse
- **Fast reiner `data.js`-Additiv-Schritt.** Zwei winzige, rückwärtskompatible Ergänzungen in `app.js`:
  ein neuer `DOC_SKINS["Nachtragsangebot"]`-Eintrag und ein optionales `lineItems.grossLabel`
  (Fallback „Rechnungsbetrag brutto") — damit die Fußzeile korrekt **„Angebotssumme brutto"** statt
  „Rechnungsbetrag" liest. Kein Umbau, keine bestehenden Belege/Skins verändert.

### Verifikation
- Deterministisch (Node-VM gegen `data.js`): **28 Docs** (war 27), **16 Szenarien**, **3 E-Mails**,
  **0 kaputte Referenzen**; alle **3** Beta-Quell-Zitate wortgleich im Body; Relevanzen 0–100;
  **Arithmetik** geprüft (250 + 110 + 40 = 400 netto; +19 % 76 = **476** brutto). Live im Browser (DOM
  gegen reale Daten): Suche „nachtrag" findet den Beleg (▤), Klick öffnet **`paper-beleg`**, Aussteller
  **Meridian Industrie GmbH**, **NACHTRAG**-Stempel, 3 Positionszeilen + Netto/USt/**Angebotssumme
  brutto**; Beta-Szenario trägt die neue Quelle; **keine Konsolenfehler**. (Screenshot-Capture im Harness
  instabil — bekannte Grenze; daher DOM/Daten-basiert verifiziert.)

## Zyklus 22 — 2026-07-08 — Projekt-Portfolio: die Parallelität auf einen Blick 📊

**„Welche Projekte laufen aktuell?" — beide Projekte in einer Ampel-Übersicht.** Nach Zyklus 21 trug die
Demo zwei gleichwertig belegte Projekte (Alpha im Zeitplan, Beta verzögert), aber die Parallelität war
nur über zwei getrennte Fragen erlebbar. Neu ist die **Vogelperspektive**: ein Portfolio-Szenario, das
Alpha **und** Beta in **einer** Tabelle gegenüberstellt — der „mein ganzes Portfolio auf einen Blick"-
Moment für einen CEO/CFO.

### Neu
- **Szenario `projekt-portfolio`** (Modul Berichte, Konfidenz 94 %): „Welche Projekte laufen aktuell?" —
  Antwort mit **Ampel-Übersichtstabelle** (Projekt · Fortschritt · Budget · Termin · Status): **Alpha**
  62 % · 24,0 Mio. € · Q4 2026 · **✓ im Zeitplan**; **Beta** 48 % · 8,6 Mio. € · Q4 2026 · **⚠ 3 Wo.
  Verzug**. Portfolio-Volumen aggregiert **32,6 Mio. €** (18,8 verausgabt); ehrlicher Schluss **„1 von 2
  Projekten termingefährdet — offen gekennzeichnet, nicht beschönigt."**
- **Quellen = beide Statusberichte** (`projekt-alpha-status` 96 %, `projekt-beta-status` 96 %) plus
  Vorstandsprotokoll (74 %) → der Konfidenz-Tooltip zeigt „3 Quellen · höchste Relevanz 96 % ·
  Übereinstimmung hoch". `related` verlinkt beide Statusberichte + Eskalation + Protokoll.

### Verzahnung / Reuse
- **Rein additiv in `data.js`** — kein Code-Umbau: Reuse der bestehenden `<table>`-Antwortstruktur und der
  **bereits vorhandenen** Statusberichte als Quellen. Als **erstes** Berichte-Modul-Tile und neu im Hero
  (13 Tiles). In der Geführten Demo läuft Portfolio **direkt nach** Alpha + Beta → „im Zeitplan" und
  „unter Terminrisiko" werden erst einzeln, dann in **einer Übersicht** gezeigt (16 Szenarien).

### Verifikation
- Deterministisch (Node-VM gegen `data.js`): **27 Docs**, **16 Szenarien** (war 15), **0 kaputte
  Referenzen**, alle 3 Quell-Zitate **wortgleich** im jeweiligen Body, Relevanzen gültig; Matcher routet
  „Welche Projekte laufen aktuell?" → `projekt-portfolio` **ohne Kollision** (Alpha/Beta lösen weiter
  korrekt auf). Live im Browser: Hero-Tile + erstes Berichte-Tile vorhanden, Klick löst das Szenario auf,
  Konfidenz-Kopf **94 %** + Herleitungs-Tooltip (3 Quellen, höchste Relevanz 96 %, Übereinstimmung hoch),
  alle Tabellenzellen (Alpha ✓ / Beta ⚠) + Portfolio-Volumen **32,6 Mio. €** im DOM, **keine
  Konsolenfehler**. (Voll-Streaming-HTML-Swap im Headless-Preview timer-gedrosselt — bekannte
  Harness-Grenze; daher DOM/Daten-basiert verifiziert.)

## Zyklus 21 — 2026-07-08 — Projekt Beta: die Demo-Firma trägt mehrere parallele Vorhaben 🏗️

**Ein zweites Projekt neben „Alpha" — bewusst unter Terminrisiko, ehrlich gekennzeichnet.** Der
schwächste verbleibende Fortschrittsbereich war **Demo-Firma & realistische Dokumente**. Die Demo zeigte
mit Alpha nur *eine* Vorzeige-Story (im Zeitplan). Neu ist **Projekt Beta** — eine kundenspezifische
Anlage für die *Nordwind Logistik AG*, die **verzögert** ist. Damit beweist die Demo, dass die Firma
mehrere parallele Projekte trägt, und dass AI Studio Risiken **offen kennzeichnet** statt zu beschönigen.

### Neu
- **Szenario `projekt-beta`** (Modul Berichte, Konfidenz 90 %): „Wie steht Projekt Beta?" — Antwort mit
  **Ampel-Statustabelle** (Fortschritt 48 % ⚠ verzögert · Budget 8,6 Mio. € im Rahmen · Liefertermin
  Q4 2026 ⚠ 3 Wo. Verzug), Ursachen (Lieferverzug Steuerungselektronik + Kunden-Change-Request),
  Pönale-Risiko (0,5 %/Woche, gedeckelt 5 % = max. 0,43 Mio. €) und Gegenmaßnahmen. Schließt mit dem
  **Kontrast zu Alpha** („im Zeitplan") — Risiko wird offen benannt.
- **Doc `projekt-beta-status`** (Projektbericht → `paper-bericht`, 6 Highlights): Statusbericht per
  31.03.2026, parallele Momentaufnahme zu Alpha (gleiches Berichtsdatum).
- **Doc `eskalation-beta-elektronik`** (E-Mail → `paper-email`, 3. E-Mail der Demo): Eskalation der
  Projektleitung Beta an die CFO (Cc CEO) zum Lieferverzug, mit zitiertem Verlauf der Zulieferer-
  Meldung (ElektroSys). Reuse des bestehenden E-Mail-Skins — kein Code-Umbau.
- **Wiring:** Hero (Modul Wissen) 11 → **12 Kacheln**, Modul Berichte 5 → 6, Geführte Demo 14 → **15
  Szenarien** (Beta läuft direkt nach Alpha → „im Zeitplan" gefolgt von „unter Terminrisiko").

### Verifikation
- **Deterministisch** (Node-VM gegen `data.js`): **27 Dokumente** (war 25), **15 Szenarien** (war 14),
  **3 E-Mails** (war 2), **2 gesperrt** (unverändert), **0 kaputte Referenzen** über alle
  `sources`/`related`/`withheld`/`chain`/`MODULE_SUGGESTIONS`; beide Quell-Zitate liegen wortgleich im
  Dokument-Body; alle Relevanzwerte 0–100.
- **Live im Browser** (DOM gegen reale Daten): Beta-Hero-Kachel vorhanden; Klick löst das Szenario auf →
  Konfidenz-Meter **90 %** + Herleitungs-Tooltip; Ampel-Tabelle korrekt (Kopf + 3 Zeilen), Alpha-Kontrast
  im Text; Suche „beta" findet beide Docs (▤ Status, ✉ E-Mail); Eskalations-Mail öffnet als
  **`paper-email`** mit 5 Kopfzeilen (Von/An/Cc/Betreff/Gesendet) + zitiertem Verlauf; Statusbericht
  öffnet als **`paper-bericht`** mit 6 Highlights; **keine Konsolenfehler**. (Voll-Streaming-Pfad im
  Headless-Preview timer-gedrosselt — bekannte Harness-Grenze; daher DOM/Daten-basiert verifiziert.)

## Zyklus 20 — 2026-07-08 — Konfidenz-Herleitung: das Meter erklärt sich selbst 🔍

**Die Konfidenzzahl im Antwortkopf ist jetzt erklärbar.** Der letzte Skeptiker-Einwand eines CFOs zielt
auf die Konfidenzzahl selbst („woher weiß das System das?"). Neu: hovert der Cursor das Konfidenz-Meter
(oder erreicht es per Tab), öffnet sich ein Popover, das die Zahl **aus den Quellen herleitet** —
Anzahl der Quellen, höchste Relevanz und Grad der Übereinstimmung. Rein datengetrieben aus dem
bestehenden `answer.sources`-Array; keine neuen Datenfelder.

### Neu
- **Konfidenz-Tooltip** am Meter (`.conf-pop`): drei Faktoren mit Mini-Balken — **Quellen herangezogen**
  (Anzahl), **Höchste Relevanz** (Top-Quelle in %), **Übereinstimmung der Belege** (qualitativ
  *einzeln / teilweise / hoch* mit Unterzeile „X von N Belegen ≥ 80 % Relevanz"). Titel „So ergibt sich
  die **Konfidenz X %**", Fußzeile *„Keine Behauptung — eine Ableitung aus konkreten Quellen."*
- **Ehrlich, nicht beschönigt:** `projekt-alpha` (3 Quellen, nur 1 ≥ 80 %) → „teilweise";
  `reiserichtlinie` (1 Quelle) → „einzeln"; `materialkosten` (5 Quellen) → „hoch".
- **Zugänglich:** Meter ist `tabindex="0"` + `aria-label`; Popover öffnet per `:focus-within` (Tastatur),
  nicht nur per Maus. `prefers-reduced-motion` → keine Transition.

### Geändert
- `app.js`: neue `buildConfPop(answer)`; Kopf-Markup in `streamAnswer()` trägt jetzt `conf has-pop` +
  `tabindex` + optionalen ⓘ-Marker, wenn Quellen vorhanden sind.
- `styles.css`: `.conf-pop`-Block (Popover, Pfeil, Faktor-Zeilen, Mini-Balken) hinter den vorhandenen
  `.conf-bar`-Regeln.
- `data.js` und `index.html` unverändert; bestehender Antwortpfad, Skins und Dokumente unangetastet.

### Verifikation
- Deterministisch (Node-VM gegen `data.js`): **14 Szenarien mit Quellen** erhalten den Tooltip,
  **0 ungültige Relevanzwerte**, Labels korrekt über alle Fälle.
- Live im Browser (DOM/CSS gegen reale Daten): Kopf `conf has-pop` + `tabindex="0"`, Popover-Inhalt
  korrekt hergeleitet (Reiserichtlinie 1 Quelle · Top 98 % · „einzeln"), Mini-Balken 25/98/55 % passend,
  Popover per `:focus-within` sichtbar (opacity 1), **keine Konsolenfehler**. (Screenshot-Capture im
  Harness instabil, `:focus-within`-Icon-Tint headless unzuverlässig — bekannte Grenzen.)

## Zyklus 19 — 2026-07-08 — Reklamations-Vorgang: mangelhafte Stahllieferung → Gutschrift 🧾

**Ein neuer, authentischer Beleg-Vorgang zeigt, dass auch die Ausnahme lückenlos dokumentiert ist —
und das Geld zurückkam.** Der schwächste Fortschrittsbereich war **Demo-Firma & realistische Dokumente
(81 %)**. Neu ist ein vollständiger Qualitäts-/Reklamationsvorgang, bewusst mit der bestehenden
Stahl-/Donau-Story verzahnt (separate Folgelieferung, keine Kollision mit dem sauberen Drei-Wege-
Abgleich): eine Teillieferung Baustahl S355 war mangelhaft, wurde form- und fristgerecht gerügt und
per Gutschrift erstattet. Rein additiv in `data.js`; zwei neue Beleg-Skins in `app.js`, ein
Stempel-Ton in `styles.css`.

### Neu
- **Szenario `reklamation-stahl`** (Modul Audit, Konfidenz 95 %): „Wie haben wir die mangelhafte
  Stahllieferung reklamiert?" Antwort: 12 t (von 60 t) fielen bei der Wareneingangsprüfung durch eine
  **Maßabweichung EN 10029** + Walzhautfehler auf → **§377-HGB-Rüge** (fristgerecht, 2. Tag) →
  **Gutschrift über 11.040 € netto (13.137,60 € brutto)**. Kernbotschaft: *Mangel erkannt, fristgerecht
  gerügt, Geld zurück.*
- **Dokument `maengelruege-mr-2026-0091`** (Typ **„Mängelrüge"**, Modul Audit): formale Rüge Meridian →
  Stahlwerk Donau, §377 HGB + Gewährleistungsklausel §12 Rahmenvertrag, 3 Highlights. Neues Beleg-Skin
  mit rotem **MÄNGELRÜGE**-Stempel.
- **Dokument `gutschrift-gs-2026-0203`** (Typ **„Gutschrift"**, Modul Finanzen): Gutschrift Stahlwerk
  Donau → Meridian mit **Positionstabelle** (12 t × 920 € = 11.040 € netto · USt 19 % 2.097,60 € ·
  brutto 13.137,60 €), grüner **GUTSCHRIFT**-Stempel, Aussteller = Lieferant.
- **§12 Gewährleistung** als neue Klausel im **Rahmenvertrag Stahlwerk Donau** ergänzt → die Zitate der
  Mängelrüge/Gutschrift lösen jetzt auf eine sichtbare Vertragsklausel auf.
- Verdrahtung: neuer Stempel-Ton `.stamp-warn` (Rot #b91c1c) in `styles.css`; DOC_SKINS „Mängelrüge"
  (beleg, warn-Stempel) + „Gutschrift" (beleg, extIssuer, ok-Stempel) in `app.js`. Hero (Wissen)
  10 → **11 Kacheln**; Modul-Vorschläge Audit + Finanzen erweitert; Geführte Demo 13 → **14 Szenarien**.

### Verifikation
- **Deterministisch (Node-VM gegen `data.js`):** **25 Dokumente** (war 23), **14 Szenarien** (war 13),
  2 E-Mails, 2 gesperrt, **0 kaputte Referenzen** über alle `sources`/`related`/`withheld`/`chain`/
  `MODULE_SUGGESTIONS`; Hero 11 Kacheln. Arithmetik geprüft: 12 × 920 = 11.040; +19 % = 13.137,60 €.
- **Live im Browser (DOM gegen reale Daten):** Suche findet beide Belege mit korrektem Modul-Tag;
  **Gutschrift** öffnet als `paper-beleg`, Aussteller „Stahlwerk Donau AG", GUTSCHRIFT-Stempel (grün),
  Positionstabelle Netto/USt/Brutto korrekt, 3 Highlights; **Mängelrüge** öffnet als `paper-beleg`,
  Aussteller „Meridian Industrie GmbH", MÄNGELRÜGE-Stempel in **Rot (rgb 185,28,28)**, 3 Highlights;
  Szenario-Kopf rendert mit **95 % Konfidenz**. **Keine Konsolenfehler.** (Voll-Streaming-Pfad im
  Headless-Preview timer-gedrosselt, Screenshot-Capture instabil — bekannte Harness-Grenzen; daher
  DOM/Daten-basiert verifiziert.)

## Zyklus 18 — 2026-07-08 — Such-Beat als Opener der Geführten Demo 🎬

**Die Command-Palette wird jetzt hands-free vorgeführt.** Zyklus 17 baute die globale Suche, sie lief
aber nur bei manueller Auslösung. Jetzt eröffnet die **„▶ Geführte Demo"** mit einem automatischen
Such-Beat: bevor die erste Frage getippt wird, öffnet die Palette selbsttätig, tippt sichtbar
**„stahl"**, zeigt **8 Treffer quer über Finanzen + Audit**, öffnet kurz einen Beleg und schließt
wieder — *dann* startet die Frage-Sequenz. Die schiere **Menge** des erschlossenen Wissens ist damit
das erste Bild des Videos. Rein additiv in `app.js`; `data.js`/`styles.css`/`index.html` unverändert.

### Neu
- **`demoSearchBeat(token)`** in `app.js`: öffnet die Palette inline (die manuelle `openSearch()` bleibt
  während der Demo bewusst gesperrt), tippt „stahl" Zeichen-für-Zeichen mit Live-Filter, zeigt die
  Treffer, öffnet den ersten **freigegebenen** Beleg im Viewer (gesperrte übergangen → kein „Zugriff
  verweigert" als Opener), schließt Viewer + Palette. Ein Aufruf in `startDemo()` vor der Szenario-Schleife.
- **Fail-safe Teardown:** `resetDemoUi()` schließt jetzt zusätzlich Viewer und Palette → Stoppen
  **mitten im Beat** hinterlässt keinen offenen Zustand. Voll token-gesteuert (sauberer Abbruch an jedem
  Schritt); `prefers-reduced-motion` → sofortiges Tippen + kurze Pausen.

### Verifikation (Browser-DOM, live gegen reale Daten)
- Beat läuft automatisch: Palette öffnet mit **„23 Dokumente im Wissensspeicher"**, „stahl" wird
  getippt → **8 von 23**, Module quer (Finanzen · Audit · Verträge), `<mark>`-Highlight vorhanden;
  Viewer öffnet auf „Quartalsbericht Q1 2026" und schließt wieder; danach **Fortschritt „1 / 13"**,
  Composer gesperrt — nahtloser Übergang in die Frage-Sequenz. **Keine Konsolenfehler.**
- Stopp mitten im Beat: Palette + Viewer geschlossen, Demo-Button zurückgesetzt, Composer wieder
  editierbar. (Screenshot-Capture im Harness instabil — DOM-basiert verifiziert.)

## Zyklus 17 — 2026-07-08 — Globale Live-Suche (Command-Palette) 🔍

**Der „Was steckt alles drin?"-Moment.** Ein Sidebar-Auslöser „🔍 Alles durchsuchen" (+ Strg/⌘ + K)
öffnet ein zentriertes Modal, das beim Tippen live über **alle 23 Dokumente** filtert. Rein additiv in
`index.html`/`styles.css`/`app.js`; `data.js` und der Antwortpfad unverändert.

### Neu
- **Sidebar-Auslöser „🔍 Alles durchsuchen"** unter dem Logo (mit `Strg K`-Kürzel-Badge); **Strg/⌘ + K**
  öffnet/schließt von überall, **Esc** und Backdrop-Klick schließen.
- **Command-Palette-Modal** (Notion/Linear-Anmutung): Autofocus-Suchfeld, Live-Zähler, scrollbare
  Trefferliste. **Leeres Feld = komplettes Inventar** („23 Dokumente im Wissensspeicher"); Tippen filtert
  **live** über Titel/Typ/Snippet/Autor/Modul (Zähler „X von 23 für ‚…'").
- **Treffer-Zeilen** mit Icon (✉ bei E-Mail), **Modul-Tag + Typ**, einzeiligem Snippet und **gelb
  markiertem Suchbegriff** (`<mark>` via sicherer `hlMatch()`). ↑/↓ + **Enter** öffnen den markierten
  Treffer, Klick öffnet den Beleg im bestehenden Viewer.
- **Governance konsistent:** gesperrte Dokumente erscheinen (mit „🔒 Kein Zugriff"), öffnen aber die
  „Zugriff verweigert"-Ansicht ohne Inhalts-Leak. Während der Geführten Demo ist der Auslöser inaktiv.

### Verifikation (deterministisch via Node-VM + Browser-DOM/CSS)
- **23 Dokumente**; Filter exakt: ""→23, „stahl"→8, „vertrag"→4, „dsgvo"→2, „donau"→6, kein-Treffer→0;
  **0 Feld-Fehler**, 2 gesperrte Docs.
- Live: Auslöser + Strg+K öffnen/schließen, 23 Zeilen bei leerem Feld + korrekter Zähler, `<mark>`-
  Highlight, ↓+Enter öffnet Viewer (Titel korrekt), gesperrter Treffer → `paper-locked` ohne Leak,
  eine „stahl"-Suche zeigt Treffer aus Finanzen **und** Audit; **keine Konsolenfehler**.
  `prefers-reduced-motion` respektiert. (Screenshot-Capture im Harness instabil — DOM/CSS-basiert
  verifiziert.)

## Zyklus 16 — 2026-07-08 — DSGVO-/Datenschutz-Szenario (neues Entscheider-Ressort) 🛡

**Die Demo öffnet ein neues Entscheider-Ressort: Datenschutz/Compliance.** Bisher finanzlastig, deckt
sie jetzt auch DSGVO ab — ein Thema, das jeden CEO/CFO betrifft. Rein additiv in `data.js`, bestehende
Tabellen- und Skin-Renderer wiederverwendet.

### Neu
- **Szenario `datenschutz-audit`** (Modul Audit, Konfidenz 93 %): „Sind wir DSGVO-konform — wann war
  das letzte Datenschutz-Audit?" Antwort mit **Status-Tabelle** über 5 Prüffelder (Art. 30 VVT,
  Art. 32 TOM, Art. 28 Auftragsverarbeitung, Betroffenenrechte/Löschkonzept, 72-h-Meldeprozess), je
  Status ✓ / ⚠ 1 offen. **Ehrlich:** zwei offene Auflagen mit Frist 31.03.2026, „kein akutes
  Bußgeldrisiko".
- **Dokument `datenschutz-audit-2025`** (Typ „Prüfnachweis" → grüner **BESTANDEN**-Stempel im Viewer):
  jährliches DSGVO-Audit vom 20.11.2025, externe Datenschutzbeauftragte Dr. Julia Sander, 8 Absätze /
  6 Highlights.
- **Dokument `verarbeitungsverzeichnis-2026`** (Typ „Verzeichnis" → Fallback Bericht-Skin
  `paper-bericht`): Verzeichnis nach Art. 30 DSGVO, 34 Verarbeitungstätigkeiten mit Rechtsgrundlage
  und Löschfrist.
- **Verdrahtung:** Szenario nach `brandschutz` einsortiert (zwei Audit-/Compliance-Beats in Folge in
  der Geführten Demo); Hero (Wissen) 9 → 10 Kacheln, `audit`-Vorschläge 2 → 3. Jetzt **13 Szenarien**.

### Verifikation (deterministisch via Node-VM + Browser-DOM/CSS)
- **23 Dokumente** (war 21), **2 E-Mails**, **13 Szenarien** (war 12), **1 chain**, **0 kaputte
  Referenzen** über alle `sources`/`related`/`withheld`/`chain`/`MODULE_SUGGESTIONS`.
- Live: DSGVO-Hero-Kachel vorhanden (10 Kacheln), beide neue Karten im Audit-Modul, Datenschutz-Audit
  öffnet als `paper-nachweis` mit BESTANDEN-Stempel + 6 Highlights, VVT als `paper-bericht` + 3
  Highlights, kein Ketten-Navigator bei den Nicht-Ketten-Docs, **keine Konsolenfehler**. (Voll-
  Streaming-Pfad timer-gedrosselt, Screenshot-Capture instabil — bekannte Harness-Grenzen; DOM/CSS-
  basiert verifiziert.)

## Zyklus 15 — 2026-07-08 — Ketten-Navigator im Dokumentenviewer („Schritt n von 3") ⛓

**Die Entscheidungskette ist jetzt auch beim Lesen der Einzelbelege navigierbar (Option B aus
Zyklus 14).** Öffnete man bisher einen der drei Ketten-Belege im Viewer, verlor man den Kontext
„wo im Beleg-Pfad bin ich?". Jetzt zeigt der Viewer oben einen kompakten Navigator und man klickt
sich durch die ganze Kette, ohne ihn zu verlassen.

### Neu
- **Ketten-Navigator im Viewer** (`buildChainNav()` in `app.js`): erscheint automatisch, sobald eines
  der drei Ketten-Dokumente geöffnet wird (Lieferanten-E-Mail → interne Weiterleitung → Vorstands-
  protokoll). Zeigt **„⛓ Entscheidungskette · Schritt n von 3"**, einen **horizontalen Stepper** mit
  Datum + Akteur je Schritt (aktueller Schritt gefüllt in Marken-Farbe, erledigte markiert) und eine
  Fußzeile **„← Voriger Beleg / Nächster Beleg →"** plus das Label des aktuellen Schritts. Stepper-
  Punkte **und** Vor/Zurück-Buttons öffnen direkt den jeweiligen Beleg.
- **`chainStepIndex()`** ordnet ein Dokument seiner Position in der Kette zu (−1 = nicht Teil) → der
  Navigator erscheint **nur** bei den drei Ketten-Dokumenten; jeder andere Beleg öffnet unverändert.
  Prev am 1. / Next am letzten Schritt deaktiviert.
- **Kette entdoppelt:** neue **`const DECISION_CHAIN`** (`data.js`) ist jetzt **einzige Quelle der
  Wahrheit** — der Chat-Block (`answer.chain` in `budget-herkunft`) **und** der Viewer-Navigator lesen
  dieselbe Definition; garantiert synchron, keine doppelte Datenpflege.
- **Navigator-CSS** (`styles.css`): `.vchain`/`.vc-track`/`.vc-step`/`.vc-dot`/`.vc-nav` …, bindet an
  die Marken-Tokens (`--brand`, `--brand-soft`, `--brand-ink`). Bestehende Skins, Dokumente und der
  Antwortpfad **unverändert**.

### Verifikation (deterministisch via Node-VM + Browser-DOM/CSS)
- **21 Dokumente**, **2 E-Mails**, **12 Szenarien**, **1 chain**, `budget-herkunft.chain ===
  DECISION_CHAIN`, **0 kaputte Referenzen** über `sources`/`related`/`withheld`/`chain`/
  `MODULE_SUGGESTIONS` + die 3 `DECISION_CHAIN`-`docId`s.
- Navigator live gegen die realen Daten geprüft: auf allen 3 Belegen mit korrektem „Schritt n/3"-
  Zähler; **Vor/Zurück und Stepper-Punkt-Klick** wechseln das Dokument korrekt (Titel/Zähler/erledigt-
  Status stimmen); Prev am 1. und Next am letzten Schritt deaktiviert; **kein** Strip bei einem Nicht-
  Ketten-Dokument (Quartalsbericht); aktueller Punkt bindet an `--brand`/`--brand-soft`; keine
  Konsolenfehler. (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM/CSS-basiert.)

---

## Zyklus 14 — 2026-07-08 — Entscheidungskette als sichtbarer „Beleg-Pfad" im Chat ⛓

**Vom Daten-Beleg zum sichtbaren Element.** Zyklus 12/13 legten die Daten der Entscheidungskette
(zwei E-Mails → CFO → Vorstand); der Betrachter musste sie aber über Quellen-Chips selbst
zusammensetzen. Jetzt zeigt die Antwort die **Herkunfts-Kette als eigene vertikale Timeline** —
Lieferant → Einkauf → CFO → Vorstand, jeder Schritt mit anklickbarem Originalbeleg.

### Neu
- **Neues Szenario `budget-herkunft`** (Modul Finanzen, Konfidenz 95 %): „**Wie kam das Mehrbudget von
  0,9 Mio. € für Projekt Alpha zustande?**" — knapper Antworttext plus der neue Ketten-Block. Als
  Hero-Kachel (8 → 9) und in „Geführte Demo" (automatisch, jetzt **12 Szenarien**).
- **Neues optionales Feld `answer.chain`** (`data.js`) + **Renderer `appendChain()`** (`app.js`),
  analog zum bestehenden `appendWithheld()`-Muster: vertikale **Timeline mit 3 Schritten**, je
  **Datum-Badge**, **Akteur** („Einkauf → CFO"), **Label**, Beschreibung und **anklickbarem Beleg**
  (öffnet das Originaldokument im Viewer). Letzter Schritt (Vorstandsbeschluss) als `strong`
  hervorgehoben (gefüllter Punkt), Verbindungslinie läuft durch die Punkte und endet am letzten Schritt.
- **Timeline-CSS** (`styles.css`): `.chain-line`/`.chain-step`/`.cs-dot`/`.cs-date`/`.cs-src` …,
  bindet an die Marken-Tokens (`--brand`, `--brand-soft`, `--brand-ink`). Als **erster** strukturierter
  Block unter der Antwort → maximale Wirkung; wird vom bestehenden gestaffelten Block-Reveal mitanimiert.
- **Zahlen konsistent mit der Story:** 640 t × 120 €/t ≈ 0,9 Mio. € = beschlossenes Mehrbudget
  (Vorstandsprotokoll). Bestehende Szenarien, Dokumente und der Antwortpfad **unverändert**.

### Verifikation (deterministisch via Node-VM + Browser-DOM/CSS)
- **21 Dokumente**, **2 E-Mails**, **12 Szenarien**, **1 Szenario mit `chain`**, **0 kaputte
  Referenzen** über `sources`/`related`/`withheld`/`chain`/`MODULE_SUGGESTIONS`.
- Chain-Markup + CSS live gegen die realen Szenariodaten gerendert: 3 Schritte, alle **anklickbar**,
  1 `strong`; Punkte-Rahmen/Datum-Badge/Beleg-Link binden korrekt an die Marken-Tokens,
  Verbindungslinie 2 px und am letzten Schritt beendet; **keine Konsolenfehler**.
- (Voll-Streaming-Pfad im Headless-Preview timer-gedrosselt, Screenshot-Capture instabil — bekannte
  Harness-Grenzen; daher DOM/CSS-basiert verifiziert.)

## Zyklus 13 — 2026-07-08 — Zweite E-Mail (interne Weiterleitung) → Entscheidungskette quer durch Postfächer ✉→✉

**Von der einzelnen E-Mail zum belegten E-Mail-Thread.** Zyklus 12 brachte das E-Mail-Skin und die
auslösende Lieferanten-E-Mail. Jetzt zeigt die Demo, wie AI Studio eine **Entscheidungskette über
zwei Postfächer** rekonstruiert: Lieferant → Einkauf → CFO → Vorstandsbeschluss.

### Neu (rein additiv in `data.js` — kein Code-Umbau, Skin existiert bereits)
- **Neues Dokument `email-weiterleitung-materialbudget`** (Typ **„E-Mail"**, Modul Finanzen):
  **WG-Weiterleitung** der Donau-Preis-E-Mail von **Thomas Krüger (Einkauf)** an **Dr. Katharina
  Vogel (CFO)**, Cc Projektleitung Alpha, vom 13.02.2026. Enthält die **Bewertung des Einkaufs**:
  ~640 t Jahresbedarf × +120 €/t → **rund 0,9 Mio. € Mehrbedarf** für Projekt Alpha, plus die
  **Empfehlung**, das Mehrbudget als Vorstands-Beschlussvorlage einzubringen und Ferro Nord zu
  beschleunigen. **Zitat-Verlauf** = die Original-Donau-E-Mail (Andreas Huber) → sichtbarer Thread.
- **Verzahnt mit der bestehenden Story:** die 0,9 Mio. € stammen genau aus dem
  **Vorstandsbeschluss TOP 2** (`vorstandsprotokoll-2026-03`) — die Weiterleitung ist die
  **Herkunft dieser Zahl**. Kein neuer Wert, sondern der fehlende Beleg der Entscheidungskette.
- **In zwei Szenarien eingewoben:**
  - „**Warum sind die Materialkosten gestiegen?**" — E-Mail als **3. Quelle** (81 %), in „Verwandte
    Dokumente" und als zusätzlicher Reasoning-Schritt (Einkauf → CFO, 0,9 Mio. €).
  - „**Fasse Projekt Alpha zusammen.**" — E-Mail als Quelle für die **Herkunft des Mehrbudgets**
    (Reasoning: Lieferanten-E-Mail → Weiterleitung an CFO → Vorstandsbeschluss).
- Bestehende Dokumente, Skins und der Antwortpfad **unverändert**.

### Verifikation (deterministisch via Node-VM gegen `data.js`)
- **21 Dokumente** (war 20), davon **2 E-Mails** (`email-preisanpassung-donau`,
  `email-weiterleitung-materialbudget`), **11 Szenarien**.
- **0 kaputte Referenzen** über alle `sources` / `related` / `withheld` / `MODULE_SUGGESTIONS`.
- Neue E-Mail nutzt das identische Feldschema (`from`/`to`/`cc`/`subject`/`sent`/`attachment`/
  `quoted`) → `buildPaper()`-`cat==="email"`-Zweig rendert Postfach-Kopf + Zitat automatisch.

## Zyklus 12 — 2026-07-08 — E-Mail-Skin im Viewer + Lieferanten-E-Mail als Beleg der Materialkosten-Story ✉

**„Wissen steckt in E-Mails" ist jetzt im Bild.** Die Mission-Story nennt E-Mails ausdrücklich als
Ort, an dem Firmenwissen gefangen ist — im Viewer gab es dafür kein eigenes Skin. Dieser Zyklus
schließt die Lücke mit einem authentischen Postfach-Look **und** verankert die E-Mail als
auslösenden Beleg der stärksten bestehenden Story (Materialkostenanstieg).

### Neu (rein additiv in `data.js` / `app.js` / `styles.css`)
- **Neues Dokument `email-preisanpassung-donau`** (Typ **„E-Mail"**, Modul Finanzen): die
  Original-Ankündigung von **Stahlwerk Donau** über die 15-%-Preisanpassung auf Baustahl S355 zum
  01.03.2026 — 800 € → 920 € (**+15 %** = Preisgleitklausel §6 des Rahmenvertrags RV-2023-014).
  Cc an die CFO, **Anhang-Chip** „Preisliste_2026_Stahlwerk-Donau.pdf · 148 KB", **Zitat-Verlauf**
  der vorherigen Einkaufs-Anfrage.
- **E-Mail-Skin** `DOC_SKINS["E-Mail"] = { cat: "email" }`: Postfach-Kopf mit Avatar-Initialen
  (Verlauf Cyan→Indigo), **Von/An/Cc/Betreff/Gesendet**-Zeilen (Betreff fett), Anhang-Chip und
  zitiertem Verlauf (linker Balken). Neue Helfer `buildMailHead()` / `buildQuoted()` / `mailRow()`;
  `buildPaper()` verzweigt für `cat === "email"`. **✉-Icon** für E-Mail-Karten in der Bibliothek.
- **In die Materialkosten-Story eingewoben:** E-Mail als **2. Quelle** (88 %) der Antwort „Warum
  sind die Materialkosten gestiegen?", in „Verwandte Dokumente" und als zusätzlicher Reasoning-
  Schritt → **klickbar in der Geführten Demo**, Skin erscheint automatisch im Video.
- Bestehende Skins, Dokumente und der Antwortpfad **unverändert**.

### Verifikation (im Browser, DOM/CSS-basiert)
- Finanzen-Bibliothek: E-Mail-Karte mit **✉-Icon** + Typ „E-Mail" (5 Karten gesamt).
- Viewer: `paper paper-email`, Postfach-Kopf mit Initialen **„AH"**, 5 Zeilen (Betreff `font-weight
  700`), Anhang-Chip „Preisliste_2026_Stahlwerk-Donau.pdf / 148 KB", **2 Highlights**, Zitat-Verlauf
  mit **3 Zeilen**.
- Datenintegrität: **0 kaputte Referenzen** über alle Szenarien, 20 Dokumente; Materialkosten-Quelle
  + Verwandte + Reasoning enthalten die E-Mail. Keine Konsolenfehler.
- *Layout-Maße im Headless-Preview nicht messbar (0×0-Viewport, bekannte Harness-Grenze); CSS parst
  und greift, spiegelt das bewährte `.lh`-Briefkopf-Flexmuster.*

---

## Zyklus 11 — 2026-07-08 — Bewegungs-Politur: gestaffelter Block-Reveal + Modulwechsel-Fade ✨

**Die Demo läuft jetzt flüssig — die Antwort baut sich souverän auf, statt zu springen.** Inhaltlich
war die Story komplett; die härteste verbleibende Kante war das etwas sprunghafte Ein-/Umblenden.
Diese reine Wahrnehmungs-Politur hebt die gefühlte Produktreife auf „fertig" — ohne inhaltliches
Risiko.

### Neu (rein additiv in `styles.css` + kleiner Helfer in `app.js`)
- **Gestaffelter Block-Reveal:** die strukturierten Blöcke unter jeder Antwort
  (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) blenden **nacheinander** ein
  (neue Keyframe `block-rise`, Fade + 9 px Slide-up, ~0,42 s). `revealBlocks()` vergibt je Block
  eine additive Verzögerung **+55 ms** über die CSS-Variable `--rev-delay` — die Antwort „wächst"
  von oben nach unten.
- **Sanfter Modulwechsel:** der neu gerenderte Panel-Inhalt (`.wrap`) blendet dezent ein (neue
  Keyframe `view-in`, Fade + 7 px Slide-up, ~0,32 s) beim Wechsel Wissen ↔ Finanzen/Audit/HR/
  Verträge/Berichte/Einstellungen. Feuert nur beim View-Render; die Chat-Antworten behalten ihre
  eigene `.msg`-`rise`-Animation.
- **Fail-safe:** `prefers-reduced-motion: reduce` deaktiviert **beide** Effekte sauber
  (`revealBlocks()` steigt früh aus, CSS setzt `animation: none`). Startopazität liegt nur im
  Keyframe → ohne Animation bleiben alle Blöcke voll sichtbar (opacity 1), **kein Risiko
  unsichtbarer Inhalte**.
- `data.js` und der bestehende Antwortpfad **unverändert**.

### Verifikation (deterministisch im Browser)
- Normalbrowser (no-preference): `.block.reveal` → `animationName: block-rise`, `--rev-delay:110ms`
  → aufgelöst als `animation-delay: 0,11 s` (Stagger greift).
- Reduzierte Bewegung (Preview-Umgebung): `animationName: none` bei `opacity: 1` — sichere
  Fallback-Darstellung ohne unsichtbare Blöcke.
- Alle drei neuen CSS-Regeln (`view-in`, `block-rise`, `.block.reveal`) im geladenen Stylesheet
  bestätigt. (Streaming-Vollpfad im Headless-Preview durch Timer-Throttling zu langsam für Live-
  Beobachtung → mechanisch/deterministisch geprüft.)

## Zyklus 10 — 2026-07-08 — Handlungs-Abschluss: „An Vorstand senden" / „Als Briefing exportieren" ✉

**Die Demo schließt jetzt die Nutzer-Story „Frage → belegte Antwort → weiterreichbares Ergebnis".**
Bisher endete jede Antwort informativ, aber ohne den Moment, den ein Entscheider als Nächstes
denkt: „und dann?". Neu erscheint unter jeder belegten Antwort ein Aktions-Block **„↗ Ergebnis
weiterreichen"** mit zwei Buttons — der letzte fehlende Baustein und ein starker Video-Schluss.

### Neu (rein additiv in `app.js` / `styles.css`)
- **Primär-Button „✉ An Vorstand senden"** und Sekundär-Button **„⤓ Als Briefing exportieren"**
  im Antwortkopf-Fuß (nach den Folgefragen). Klick zeigt eine kurze Vorbereitungs-Phase
  („Briefing wird zusammengestellt…" / „PDF wird erzeugt…", Spinner ~0,8 s) und morpht dann in
  eine **grüne Erfolgs-Bestätigung** mit ✓-Badge:
  - Senden: „**Briefing an den Vorstand gesendet** · Empfänger: Vorstand · Meridian Industrie
    GmbH · soeben · Ref. BRF-2026-XXXX".
  - Export: „**Briefing als PDF exportiert** · meridian-briefing-2026-XXXX.pdf · <Datum>".
- **Deterministische Briefing-Nummer** (`briefingNumber()`, Hash aus Antwortinhalt + Konfidenz) —
  im Video reproduzierbar, konsistent mit dem Tempo-Signal aus Zyklus 8 (keine Zufallszahl).
- **Fail-safe/ehrlich:** Der Aktions-Block erscheint **nur bei belegten Antworten** (mind. eine
  Quelle) — ein leerer „kein Treffer"-Fallback bietet kein Briefing an. Rein UI: **keine echten
  Mails/Exporte**, nur eine überzeugende Bestätigung.
- **Politur:** Pop-Animation der Bestätigung, `prefers-reduced-motion` respektiert (Animation aus,
  Vorbereitungs-Delay 0). `data.js` und der bestehende Antwortpfad unverändert.

### Verifikation (live im Browser, text-basiert)
- Aktions-Block rendert an korrekter Position (nach „➜ Folgefragen"), beide Buttons vorhanden,
  Primär-Button in Marken-Indigo (#4f46e5) mit weißer Schrift.
- Klick „An Vorstand senden" → Spinner-Phase → grüne Bestätigung (Ref. BRF-2026-5602, Empfänger-
  Zeile korrekt). Export-Zweig symmetrisch. Keine Konsolenfehler.
- (Screenshot-Capture im Harness weiterhin instabil → DOM/CSS-basiert verifiziert.)

## Zyklus 9 — 2026-07-08 — Ressort-Breite: HR-Onboarding & Lieferanten-/Klumpenrisiko 🧭

**Zwei neue, glaubwürdige Szenarien holen zwei zusätzliche Entscheider-Ressorts ins Publikum.**
Die Demo deckte bisher Finanzen, Audit, Verträge, Berichte/ESG und Governance ab. Jetzt kommen
**HR-Onboarding** („Was muss ein neuer Mitarbeiter am ersten Tag erledigen?") und
**Beschaffungs-/Risikoanalyse** („Wie abhängig sind wir von unserem größten Lieferanten?") dazu —
zwei Fragen, bei denen HR-Leitung und CFO/Einkauf sofort „das ist genau mein Problem" denken.
Die „Geführte Demo" nimmt beide **automatisch** auf (jetzt 11 Szenarien).

### Neu (rein additiv in `data.js` — kein Code-Umbau)
- **Szenario „Onboarding, erster Tag"** (Modul HR): Antwort als Schritt-für-Schritt-Checkliste
  (Empfang, Werksausweis, IT-Zugänge, **Pflicht-Sicherheitsunterweisung**, Pflichtdokumente,
  Pate). Quellen: neue **Onboarding-Checkliste** (98 %) + Querverweis **Reiserichtlinie 2026**
  (68 %). Konfidenz 96 %.
- **Szenario „Lieferanten-/Klumpenrisiko"** (Modul Finanzen): Antwort mit **Konzentrations-
  Tabelle** (Stahlwerk Donau AG 23,9 % · Siemens 11,6 % · Robotik Bayern 8,2 %) und der
  kritischen **Single-Source-Warnung** für Baustahl S355; Gegenmaßnahme Ferro Nord (Vorstands-
  beschluss). Quellen: neue **Lieferanten-Risikoanalyse 2026** (97 %) + Vorstandsprotokoll (80 %)
  + Rahmenvertrag (72 %). Konfidenz 94 %.
- **Neues Doc `onboarding-checkliste-2026`** (Typ „Checkliste", HR) — 8 Absätze, 4 Highlights.
- **Neues Doc `lieferanten-risikoanalyse-2026`** (Typ „Risikobericht", Finanzen) — mit
  `lineItems`-Tabelle „Top-Lieferanten nach Einkaufsvolumen 2025" (5 Positionen, Anteile).
- **Wiring:** Hero-Vorschläge 6 → 8, Modul HR (2) und Finanzen (3) ergänzt.

### Konsistenz (bewusst mit bestehender Story verzahnt)
- Größter Lieferant = **Stahlwerk Donau AG** (bereits Materialkosten-/Rechnungs-Story); Zweit-
  quelle **Ferro Nord** = derselbe Vorstandsbeschluss wie im Governance-/Strategie-Szenario.
- Einkaufsvolumen 268 Mio. € plausibel zum Umsatz 612 Mio. €; Donau 64 Mio. € = 23,9 %.

### Funktioniert (live im Browser verifiziert, throttle-immun text-basiert)
- Datenintegrität: 11 Szenarien, 8 Hero-Kacheln, **0 kaputte Quell-/Related-Referenzen**.
- Beide Hero-Kacheln erscheinen; Antwortkopf mit Tempo-Signal „2,3 s" + Konfidenz 94 % rendert.
- Finale Antwort-HTML deterministisch geparst: Lieferanten-Tabelle mit Kopf
  `[Lieferant · Volumen 2025 · Anteil]` + 3 Datenzeilen; Onboarding als Liste. Alle Quell-/
  Related-IDs lösen auf echte Dokumenttitel auf (Viewer-Links funktionieren). Keine Konsolenfehler.
- Hinweis: Live-Streaming-Endzustand im Hintergrund-Tab durch Timer-Throttling (`setTimeout`)
  nicht abfilmbar — Verifikation daher über finalen Render-Pfad, identisch zu den 8 bewährten
  Szenarien.

## Zyklus 8 — 2026-07-08 — Video-Politur: „Beantwortet in X,X s"-Signal + Zahlen-Hochzählen ⚡

**Die Demo fühlt sich jetzt schnell und „live" an — die letzte Politur fürs Verkaufsvideo.**
Jede Antwort trägt im Kopf ein **Tempo-Signal „⚡ Beantwortet in 1,9 s"**, das direkt beim
Erscheinen von 0 hochzählt, und die **Kernzahlen im Antworttext** (18,4 %, 87.584 €, -30,0 % …)
**zählen dezent hoch**, sobald die Antwort fertig getippt ist. Das erzeugt genau den Eindruck
von Geschwindigkeit und Souveränität, der in einem CEO/CFO-Video zählt — ohne den Antwortpfad
umzubauen.

### Neu (rein additiv in `app.js` / `styles.css`)
- **Tempo-Signal im Antwortkopf** (`.speed` „⚡ Beantwortet in <b>X,X s</b>") links vom
  Konfidenz-Meter. Wert ist **deterministisch** aus Antwortumfang (Quellen, Textlänge, Tabelle)
  im schnell wirkenden Fenster **1,2–2,6 s** → im Video reproduzierbar, keine Zufallszahl.
- **Count-up der Kernzahlen:** neue `animateCounts()` scannt die **fett gesetzten** Zahlen und
  zählt sie per `requestAnimationFrame` (easeOutCubic, ~760 ms) hoch. `parseGermanNumber()`
  erkennt deutsche Formate (Dezimalkomma, Tausenderpunkt, Einheit % € t „Mio. €" GWh …).
- **Sicher gegen Fehl-Animation:** verlangt Dezimalkomma **oder** Einheit → **Jahre (2026),
  Datumsangaben (28.02.2026), PO-Nummern (PO-2026-0512)** bleiben unangetastet. `tabular-nums`
  während des Zählens verhindert Breiten-Zittern; `prefers-reduced-motion` → Endwerte sofort.

### Funktioniert (live im Browser verifiziert, text-basiert)
- Tempo-Signal rendert und zählt auf „1,9 s" (Materialkosten-Szenario).
- Parser exakt gegen alle realen fett-Zahlen geprüft: alle Kernwerte animieren, alle
  Jahre/Datum/PO-Nummern korrekt ausgeschlossen; German-Format (87.584, 18,4, -30,0) korrekt.
- Count-up-Mechanismus auf realem Antwort-Fragment: Zwischenframe → korrekter Endwert im DOM.
- Keine Konsolenfehler. (Screenshot-Capture im Harness weiter instabil → text-basiert verifiziert.)

## Zyklus 7 — 2026-07-08 — Vertrauens-Story: gesperrtes Dokument + „für Sie nicht freigegeben" 🔒

**Die Demo zeigt jetzt sichtbar, dass Berechtigungen respektiert werden — das große fehlende
Wow-Thema für skeptische Entscheider.** Zwei bewusst **gesperrte Dokumente** (M&A-
Akquisitionsvorlage „Projekt Nordstern", Vorstandsvergütung 2026) erscheinen im Modul Berichte
**ausgegraut mit Schloss** und „Kein Zugriff — Vorstand". Ein neues 9. Szenario „Was hat der
Vorstand für die Wachstumsstrategie beschlossen?" beantwortet nur die **freigegebenen**
Beschlüsse und zeigt darunter das Governance-Signal **„2 weitere Treffer für Sie nicht
freigegeben"**. Das beantwortet die CFO/Compliance-Frage „Sieht jeder alles?" in Sekunden und
differenziert AI Studio von „ChatGPT auf unseren Dateien".

### Neu (rein additiv in `data.js` / `app.js` / `styles.css`)
- **2 gesperrte Dokumente** (`locked: true`, `lockedRole`, `classification`, **kein `body`**) —
  Inhalt bleibt strukturell unsichtbar, nicht nur ausgeblendet.
- **Bibliothek:** gesperrte Karte gestrichelt/ausgegraut, Schloss-Icon, rotes
  „🔒 Kein Zugriff — <Rolle>". Klick öffnet statt Inhalt eine **„Zugriff verweigert"-Ansicht**
  im Viewer (Klassifizierung, Freigabe-Rolle, Eigentümer; Inhalt verborgen).
- **Neues 9. Szenario** `strategie-ausblick` mit optionalem `answer.withheld`-Feld →
  neuer Antwort-Block `appendWithheld()`: „N weitere Treffer für Sie nicht freigegeben",
  Klassifizierungs-Tag, Erklärsatz und **anklickbare gesperrte Treffer** (öffnen die
  Zugriff-verweigert-Ansicht).
- **„Geführte Demo"** deckt automatisch alle 9 Szenarien ab (Zähler dynamisch aus `SCENARIOS`).

### Funktioniert (live im Browser verifiziert, text-basiert)
- 2 gesperrte Karten im Modul Berichte, korrekte Rollen-Labels.
- Klick auf gesperrtes Dokument → „Zugriff verweigert", **kein Inhalt** geleakt; Meta zeigt
  Klassifizierung/Freigabe/Eigentümer.
- Strategie-Szenario als Hero-Vorschlag vorhanden; Antwortpfad unverändert.
- Withheld-Block wird nach den Quellen eingeblendet (identisches Muster wie `appendSources`).

## Zyklus 6 — 2026-07-08 — Onboarding-Overlay beim ersten Start 👋

**Der erste Video-Eindruck ist jetzt geführt statt leer.** Beim ersten Laden erscheint ein
leichtgewichtiges Coachmark oben rechts, dessen Pfeil exakt auf den „▶ Geführte Demo"-Button
zeigt — der Button pulsiert dazu dezent. Headline in einem Satz („Fragen Sie alles über Ihr
Unternehmenswissen") plus ein Primär-Button, der das Overlay schließt **und die Vorführung
sofort startet**: ein starker Opener fürs Verkaufsvideo (ein Klick → alles läuft automatisch).

### Neu (rein additiv in `index.html` / `styles.css` / `app.js`)
- **Onboarding-Coachmark** (`#onboard`) — abgedunkelter Backdrop + Karte mit Spark-Icon,
  Headline, Erklärtext und zwei Aktionen: **„▶ Geführte Demo starten"** (schließt + startet
  `startDemo()`) und **„Selbst erkunden"** (schließt nur).
- **Pfeil zielt auf den Button** (Offset 270 px = Buttonmitte 298 px vom rechten Rand −
  Kartenrand 28 px), im Browser auf ±10 px verifiziert. Der Demo-Button erhält währenddessen
  die Klasse `.hi` und **pulsiert**.
- **Nur einmal:** `localStorage`-Flag `aistudio.onboarded.v1` (try/catch → unter `file://`
  ohne Storage läuft es sauber weiter, erscheint dann bei jedem Laden).
- **Schließen** per Skip-Button, Klick auf den Backdrop oder **Esc**.
- **`prefers-reduced-motion`** respektiert (keine Animationen für empfindliche Nutzer).

### Funktioniert (live im Browser verifiziert, text-basiert)
- Overlay sichtbar beim ersten Laden, Pfeil auf ±10 px am Button, Button pulsiert.
- Skip setzt das Flag → nach Reload erscheint das Overlay **nicht** mehr.
- Primär-CTA schließt das Overlay und startet die Geführte Demo (Fortschritt „1 / 8",
  Composer gesperrt, Frage wird getippt).
- Keine Konsolenfehler. `data.js` und der Antwortpfad blieben unverändert.

## Zyklus 5 — 2026-07-07 — ESG/CO₂-Szenario: Breite über Finanzen hinaus 🌱

**Die Demo spricht jetzt auch Vorstands-/Aufsichtsratssprache.** Ein neues 8. Szenario
„Wie hat sich unser CO₂-Fußabdruck entwickelt — sind wir auf ESG-Kurs?" hebt die Demo von
„Buchhaltungs-Trick" auf **Nachhaltigkeit & Governance**. Die Antwort zeigt einen echten
**CO₂-Reduktionspfad als Tabelle** (2020 → 2025 → Ziel 2030) und legt die Lücke zum
linearen Zielpfad **ehrlich offen** (-12 % ist vs. -15 % Pfad) statt sie zu beschönigen —
genau der glaubwürdige, entscheidungsreife Ton, der einen CEO/CFO überzeugt.

### Neu (rein additiv in `data.js`, kein Code-Umbau)
- **Neues Szenario `esg-co2`** (Modul Berichte) — Antwort mit **Trend-Tabelle**
  (Jahr · CO₂ Scope 1+2 · ggü. 2020), erneuerbarem Stromanteil, benannter Ziel-Lücke und
  Handlungshebeln bis 2030; Konfidenz 92 %, 3 Quellen (97/93/76 %), 4 Nachvollziehbarkeits-
  schritte, 2 Folgefragen.
- **Neues Belegdokument `energie-emissionsbericht-2025`** („Energie- & Emissionskennzahlen
  2025", Typ Kennzahlenbericht) — CO₂-Trend 2020–2025, Zielwert 2030 (32.760 t / -30 %),
  Stromverbrauch/Energieintensität, Reduktionshebel. Rendert im Viewer als `paper-bericht`.
- **`esg-bericht-2025` vertieft** — von 2 auf 6 Absätze: Scope-1/2-Aufteilung
  (12.400 t / 28.800 t), erneuerbarer Anteil 68 % (Vorjahr 61 %), Zielpfad-Bewertung,
  Soziales & Governance (Unfallquote, Frauenanteil Führung, Lieferanten-Kodex).
- **Zahlenkonsistenz geprüft:** 41.200 t (2025) = -12,0 % ggü. Basis 46.800 t (2020);
  Ziel 2030 = 46.800 × 0,70 = 32.760 t; verbleibend 8.440 t. Über alle 3 Quellen identisch.
- **Wiring:** `esg-co2` in Hero-Vorschlägen (`wissen`) und im Modul `berichte`. Die
  „Geführte Demo" nimmt das 8. Szenario **automatisch** auf (7 → 8).

### Funktioniert (live im Browser verifiziert, text-basiert)
- Frage → gestreamte Antwort mit **5-zeiliger Trend-Tabelle**, alle 4 Blöcke
  (Nachvollziehbarkeit · Quellen 3 · Verwandte Dokumente 3 · Folgefragen 2), Konfidenz 92 %.
- Quellen-Relevanzen 97 / 93 / 76 %; alle Quellen & verwandten Dokumente lösen auf.
- Klick auf Quelle „Energie- & Emissionskennzahlen 2025" → Viewer öffnet `paper-bericht`
  mit 3 hervorgehobenen KPI-Absätzen. Keine Konsolenfehler.
- (Screenshot-Capture im Harness weiterhin instabil → DOM/CSS-Prüfung wie in Zyklus 4.)

## Zyklus 4 — 2026-07-07 — Rechnungs-Positionstabelle im Beleg-Skin 🧾

**Belege zeigen jetzt eine echte Positionszeilen-Tabelle statt Fließtext.** Rechnung,
Bestellung und Wareneingang öffnen im Viewer mit einer prüfungsechten Buchungstabelle
(Pos. · Bezeichnung · Menge · Einzelpreis · Summe) samt Netto/USt/Brutto-Fußzeile. Das
ist der stärkste **„das ist echte Buchhaltung"-Moment** für einen CFO im Video: der
**Drei-Wege-Abgleich** (Szenario 3) zeigt jetzt sichtbar übereinstimmende Positionen und
Beträge über alle drei Belege.

### Neu
- **`buildLineItems()`** in `app.js` (+ `footRow`) — rendert eine `.li-table` nur für die
  `beleg`-Kategorie, wenn `doc.lineItems` gesetzt ist. Netto/USt/Brutto-Fußzeilen sind
  **optional** (nur gerendert, wenn im Datensatz vorhanden). Alle Werte HTML-escaped.
- **`.li-table`-Styling** in `styles.css` — rechtsbündige, tabellarische Zahlen
  (`tabular-nums`), Ober-/Unterlinien, hervorgehobene Brutto-Endsumme.
- **Optionales `doc.lineItems`-Feld** in `data.js` für die 3 Belege — Fallback = bisheriger
  Fließtext, wenn nicht gesetzt (bestehende Dokumente unverändert).
  - Rechnung 2026-1843: 80,000 t Baustahl S355 · 920,00 € · Netto 73.600 € · USt 19 %
    13.984 € · **Brutto 87.584 €**.
  - Bestellung PO-2026-0512: identische Position · nur Netto 73.600 €.
  - Wareneingang WE-2026-0778: identische Position · Einzelpreis „—" · Summe „vollständig",
    keine Betrags-Fußzeile.
- **Korrektur:** Rechnungs-Snippet-Brutto von falsch „84.640 €" auf konsistente
  **„87.584 €"** (= 73.600 € × 1,19) gesetzt — die Tabelle hätte die Abweichung sichtbar
  gemacht.

### Funktioniert (live im Browser verifiziert)
- Rechnung → Positionszeile + Fußzeile Netto/USt 19 %/Brutto; Brutto-Endsumme fett (800),
  rechtsbündig, dunkel. Header-Labels korrekt uppercase/faint.
- Bestellung → identische Position, nur **Netto**-Fußzeile (keine USt/Brutto).
- Wareneingang → identische Position, **keine** Betrags-Fußzeile.
- Mengen (80,000 t) und Netto (73.600 €) stimmen über alle drei Belege überein → Abgleich schlüssig.

## Zyklus 3 — 2026-07-07 — „Geführte Demo" (hands-free Auto-Play) ▶

**Ein Klick spielt die komplette Demo selbst ab.** Ein prominenter Play-Button in der
Topbar tippt jede der 7 Beispielfragen sichtbar in den Composer, lässt die Antwort
streamen, pausiert kurz und geht zur nächsten — vollständig ohne Bedienung. Perfekt für
die **Videoaufnahme** (keine Mausbewegungen/Tippfehler im Bild) und für einen
**Messestand-/Empfangs-Loop**, der Kunden ohne Bediener überzeugt.

### Neu
- **Play-Button „Geführte Demo"** in der Topbar (`#demoBtn` in `index.html`, `.demo-btn`
  in `styles.css`) — Markenfarbe, wird im Lauf zu „⏹ Demo stoppen".
- **Fortschritts-Indikator** „Szenario n / 7" (`#demoProgress`) direkt im Button.
- **Auto-Play-Orchestrierung** (`startDemo`/`stopDemo`/`typeIntoComposer` in `app.js`):
  Chat wird frisch am Hero gestartet, Frage wird Zeichen für Zeichen „getippt", dann läuft
  der bestehende `ask()`-Flow, danach eine Lesepause. Jederzeit per Klick stoppbar
  (Token-Mechanik lässt die laufende Schleife sauber aussteigen).
- Composer ist während der Demo gesperrt (readonly) und manuelles Senden ist geblockt,
  damit sich nichts überlagert.
- **Rein additiv** — keine Änderung an `data.js` und am bestehenden `ask()`-Antwortpfad.

### Funktioniert (live im Browser verifiziert)
- Start → Button „⏹ Demo stoppen", Fortschritt „1 / 7", Composer gesperrt.
- Frage tippt sich sichtbar in den Composer, danach streamt die bestehende Antwort.
- Stopp → voller Reset (Button „▶ Geführte Demo", Fortschritt aus, Composer wieder frei).

## Zyklus 2 — 2026-07-07 — Dokument-Skins im Viewer 📄

**Der Dokumentenviewer zeigt jetzt echte Dokumente statt Textabsätzen.** Jede Quelle
wird als Papierblatt auf einem Schreibtisch dargestellt — der stärkste Vertrauens-Trigger
für nicht-technische Entscheider: „Das System öffnet mein tatsächliches Dokument."

### Neu
- **Papier-Darstellung pro Dokumenttyp** (`buildPaper` in `app.js`, `.paper*` in `styles.css`):
  - **Briefkopf** mit Logo-Initialen, Aussteller und Referenzblock (Typ · Titel · Datum).
    Bei Eingangsrechnungen ist der Aussteller korrekt der **Lieferant** (z. B. „Stahlwerk Donau AG").
  - **Belege** (Rechnung/Bestellung/Wareneingang) erhalten einen rotierten **Stempel**
    (EINGANG · GENEHMIGT · GEPRÜFT).
  - **Verträge** erhalten eine **Ort/Datum-Zeile + zwei Unterschriftszeilen** (beide Parteien).
  - **Prüfnachweise** (Feuerbeschau) erhalten einen grünen **BESTANDEN**-Stempel.
  - **Klausel-Marken** (§9, Teil B §5, TOP 1) werden im Fließtext hervorgehoben.
  - Die **gelben Highlights liegen jetzt IM Dokument-Layout** statt in einer Textliste.
- Rein CSS/HTML, datengetrieben aus `doc.type` — **keine Änderung an `data.js` nötig**,
  neue Dokumente bekommen ihr Skin automatisch.

### Funktioniert (live im Browser verifiziert)
- Rechnung 2026-1843 → `paper-beleg`, Lieferant-Briefkopf, EINGANG-Stempel, 3 Highlights im Blatt.
- Rahmenvertrag → `paper-vertrag`, §9-Klauselmarke, Unterschriftszeilen (Meridian · Dr. Elena Wagner).
- Feuerbeschau → `paper-nachweis`, grüner BESTANDEN-Stempel (rotiert).
- Quartalsbericht → sauberer Briefkopf-Fallback (`paper-bericht`).

## Zyklus 1 — 2026-07-07 — Prototyp-Bootstrap 🎉

**Der Kunden-Demo-Prototyp existiert jetzt.** (Zuvor: 31 Zyklen ausschließlich
`platform/`-Architektur-Dokumentation — nicht Teil dieser Mission.)

### Neu
- **`prototype/`** — self-contained, buildfreie Enterprise-Web-App (Vanilla-JS, `file://`-fähig).
  - `index.html` — App-Rahmen: Seitenleiste (7 Module), Chat, Composer, Dokumentenviewer.
  - `styles.css` — Enterprise-Design (Stripe/Linear/Notion-Anmutung), responsiv.
  - `data.js` — fiktive **„Meridian Industrie GmbH"** + **15 Dokumente** + **7 Szenarien**.
  - `app.js` — Chat-Logik: gestreamte Antworten, Retrieval-Schritte, Quellen-Rendering,
    Dokumentenviewer, Modul-/Bibliotheks-Ansichten, ehrlicher Fallback bei freien Fragen.
  - `README.md` — Start- und Demo-Anleitung.
- **Handover-Dateien** im Wurzelverzeichnis: `NEXT_STEPS.md`, `PROGRESS.md`, `CHANGELOG.md`,
  `IDEAS.md`, `VIDEO_SCRIPT.md`, `VIDEO_SCENES.md`, `OPEN_ITEMS.md`, `FUTURE_BACKLOG.md`.

### Funktioniert (live im Browser getestet)
- Frage stellen → gestreamte Antwort mit Konfidenz-Meter.
- Antwort enthält: Nachvollziehbarkeit, Quellen (Zitat + Relevanz %), verwandte Dokumente, Folgefragen.
- Klick auf Quelle/verwandtes Dokument → Dokumentenviewer mit Metadaten + hervorgehobenen Belegstellen.
- Modulwechsel zeigt gefilterte Dokumentenbibliothek + Vorschlagsfragen.

### Bewusst nicht angefasst
- `platform/` (Architektur-Doku) und `core/` (Agenten-Runtime) — geschütztes IP, unverändert.
