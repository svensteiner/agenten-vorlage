# OPEN_ITEMS — priorisierte Aufgabenliste (Prototyp)

> **MISSION-WECHSEL:** Seit 2026-07-08 gilt **AI STUDIO — PILOT SPRINT MODE (v2)**
> ([MISSION_PILOT_SPRINT.md](MISSION_PILOT_SPRINT.md)). Feature-Freeze in **Phase A**:
> keine neuen Szenarien/Module/Dokumente außer den Punkten der Phase-A-Checkliste.
> Der nächste Zyklus nimmt das **oberste offene** Item. Erledigtes nach unten.

## Offen (Phase B — Videoproduktion, nach Priorität)

> ✅ **Phase A abgeschlossen (Gate A→B bestanden).** Feature-Freeze bleibt in Kraft — keine neuen
> Prototyp-Features; nur noch das Verkaufsvideo produktionsreif machen. Ideen → [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md).
>
> **Alle drei Kern-Deliverables (Skript · Shotlist · Checkliste) fertig.** Gate B→C wartet nur noch auf
> **Svens Aufnahme + Freigabe** — bis dahin nur ändern, was Sven anmerkt.

1. **[B-Wartet] Svens Aufnahme + Freigabe** (Gate B→C) — aufnehmen mit [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md), freigeben. **Reiner Wartepunkt** — alle Aufnahme-Dateien sind faktentreu und aufnahmebereit. Bis Svens „OK" nur ändern, was er anmerkt.

> **Freeze-konforme Phase-C-Vorbereitung parallel begonnen** (kein Eingriff in `prototype/`): reine
> Dokumentations-Bricks, die nicht von der Video-Freigabe abhängen. Nächste Kandidaten (Reihenfolge):
> **PILOT_ONE_PAGER.md** (Angebotsdokument, reine Doku) → **Synthetische Datenpipeline dokumentieren**
> (Reuse `synthetic-data-creator`) → **PILOT_CONFIG** (Achtung: berührt `prototype/` → erst **nach**
> Gate B→C bauen) → **End-to-End-Probelauf „Muster Bau GmbH"**. Details siehe [NEXT_STEPS.md](NEXT_STEPS.md).

## Erledigt

- **[Phase C — Vorbereitung] SCENARIO_LIBRARY.md (Pilot-Szenarienbibliothek)** — alle **17 Szenarien** aus
  `data.js` nach **Schmerz** (KOSTEN · RECHNUNGSPRÜFUNG · VERTRÄGE · MONATSABSCHLUSS · PROJEKTE · LIQUIDITÄT/
  RISIKO · COMPLIANCE · WISSENSVERLUST · ESG/GOVERNANCE) und **Branche** verschlagwortet — mit Modul,
  Konfidenz, Belegzahl; dazu **fertige 3er-Startvorlagen** je Branche + Auswahl-Spickzettel und der Money-Shot
  als markiertes Finale. Reine Handover-Datei, **`prototype/` unverändert** (Feature-Freeze gewahrt).
  Verifiziert: `node --check` (app.js + data.js) ok, `git status` zeigt nur die neue `.md`. Erste Phase-C-
  Brick — hebt kein Gate (Gate B→C wartet weiter auf Sven), macht aber den 48-h-Pilot-Prozess konkret.

- **[Phase B] Skript & Shotlist auf die reale Demo angeglichen (Faktenkorrektur)** — die Video-Handover-
  Dateien nannten veraltete Zahlen: **Dokumentenzahl 27/28 → 29** (Such-Beat/Palette-Zähler in
  `VIDEO_SCRIPT.md` Szene 0b + `VIDEO_SCENES.md` Szene 0a/B-Roll; „10 von 27" → „10 von 29") und die
  Geführte Demo als **„alle 16 Szenarien / n / 16" → „kuratierte 6er-Kern-Auswahl / n / 6"** (endet auf
  dem Money-Shot). Klarstellungs-Hinweis ergänzt (Szenen = manuelle Langfassung; Geführte Demo = 6
  Kern-Momente; verbindlich bleibt `RECORDING_CHECKLIST.md`). Nur `.md`, `prototype/` unverändert.
  Verifiziert (Node-VM: 29 Docs, 17 Szenarien, „stahl"=10, DEMO_ORDER=6/Money-Shot-letzt; `grep`: keine
  16/27/28-Reste mehr).

- **[Phase B — optional] SRT-Untertitel** — `VIDEO_SUBTITLES.de.srt` erstellt: 47 Cues, deutsch, aus den
  `Sprecher`-Zeilen von `VIDEO_SCRIPT.md` abgeleitet (1–2 Zeilen je Cue, ≤ 55 Zeichen), Zeitleiste
  ~0:00–4:22 (manuelle Langfassung, inkl. optionaler 5b-Beats). Verweis-Sektion in `VIDEO_SCRIPT.md`
  ergänzt (Timings = Richtwerte, beim Schnitt angleichen). Reine Handover-Datei, `prototype/` unverändert.
  Deterministisch geparst (47 Cues, Indizes lückenlos, keine Überlappung, kein Cue > 2 Zeilen).

- **[Phase B] Video-Deliverables** — `VIDEO_SCRIPT.md` (Sprechertext), `VIDEO_SCENES.md` (Shotlist) und
  neu **`RECORDING_CHECKLIST.md`**: narrensichere Aufnahme-Anleitung für Nicht-Techniker (Browser-Setup,
  Reset-Ritual, Geführte Demo = 6 Kern-Szenen „n / 6" bis Money-Shot < 4 Min, Fehler→Behebung-Tabelle,
  Kurz-Spickzettel). Reine Handover-Dateien, `prototype/` unverändert; gegen die reale Demo verifiziert
  (29 Docs, 17 Szenarien, DEMO_ORDER = 6 IDs, Money-Shot letzt).

- **[Phase A — Abschluss] Geführte Demo kuratiert (≤ 4 min) + Ein-Klick „Zurücksetzen"** — die letzten
  beiden Phase-A-Kästchen: `DEMO_ORDER` + `demoScenarios()` spielen hands-free eine straffe **6er-Kern-
  Auswahl** (Materialkosten → Rechnungsprüfung → Entscheidungskette → Portfolio → Governance → Money-Shot),
  endet garantiert mit dem Money-Shot, Fortschritt „n / 6"; alle 17 bleiben per Kachel/Frage/Suche
  erreichbar. Topbar-Button „⟲ Zurücksetzen" (`resetDemo()`): Demo stoppen, Verlauf leeren, Viewer/Palette
  zu, zurück auf den Hero. Rein additiv (`app.js`/`styles.css`/`index.html`), `data.js` unverändert.
  Verifiziert (`node --check`, Node-VM 6 IDs/Money-Shot-letzt, live DOM „1 / 6" + Reset räumt sauber, keine
  Konsolenfehler). **→ Gate A→B bestanden, PHASE_A_COMPLETE.**

- **[Phase A] Money-Shot „Agenten dazubuchen" (Demo-Finale)** — neues Abschluss-Szenario
  `agent-dazubuchen` (letztes in `SCENARIOS` → automatisch **letzte** Szene der Geführten Demo): Die
  Wissensbasis steht, jetzt mietet der Kunde **digitale Mitarbeiter** obendrauf. `answer.agents`-Block +
  Renderer `appendAgents()`: 4 Agenten-Karten (Auskunfts-Agent *inklusive/aktiv*, **Reporting-Agent
  400 € empfohlen**, Rechnungs-Agent 600 €, Vertrags-Agent 500 €), „＋ Dazubuchen"-Button → grüne
  „✓ Aktiviert"-Bestätigung; Preis-Pfad-Fußzeile (Audit 149 € → Wissensbasis ab 5.000 € → Agent ab
  400 €/Monat). In der Geführten Demo **bucht sich der empfohlene Agent hands-free selbst** (token-
  gesichert; Schluss-Pause 1600 → 3400 ms). Antwortkopf ohne Konfidenz-Meter (Buchungsansicht, keine
  Quellen; `hasConf`-Guard in `streamAnswer()`). Rein additiv in `data.js`/`app.js`/`styles.css`.
  Verifiziert: `node --check` ok, Node-VM (29 Docs, 17 Szenarien, 0 kaputte Refs, Money-Shot letzt);
  live (DOM/CSS gegen reale Daten): 4 Karten korrekt, 3 Buchen-Buttons + 1 Aktiv-Badge + 1 Empfohlen-
  Badge, Grid 2-spaltig (377 px) bei 1920×1080, Buchen-Button Marken-Indigo, gebuchte Karte grün, Kopf
  **ohne** Konfidenz-Meter, keine Konsolenfehler. (Streaming-/Screenshot-Pfad harness-throttled — daher
  DOM/CSS/Daten-basiert, wie in den Vorzyklen.)
- **[Phase A / vorm. P4] Kunden-Beauftragung NA-2026-0037** — neues Dokument `auftrag-nordwind-beta`
  (Typ „Auftragsbestätigung", extIssuer, BEAUFTRAGT-Stempel): Nordwind beauftragt den Nachtrag
  schriftlich (Bestellung NW-BEST-2026-0091, 400.000 € netto / 476.000 € brutto), Termin Q4 2026
  akzeptiert, Pönale für den Scope-Change ausgesetzt. Als **4. Quelle** (80 %) + Reasoning-Schritt +
  Folgefrage in `projekt-beta`; die +0,4 Mio. € sind jetzt **beidseitig** belegt (Angebot + Auftrag).
  Reuse `paper-beleg`/`lineItems`; ein `DOC_SKINS`-Eintrag in `app.js`. (War Rest-WIP aus dem alten
  Modus, mit diesem Zyklus abgeschlossen & verifiziert.)
- **[Zyklus 24] Konfidenz-/Relevanz-Balken laufen mit hoch** — der Meter-Balken läuft beim Einblenden in
  ~760 ms (easeOutCubic) von 0 auf den Zielwert statt zu springen; die Konfidenz-Zahl im Kopf zählt
  synchron mit; die drei Popover-Relevanz-Balken laufen beim ersten Öffnen einmalig hoch (640 ms). Neuer
  Helfer `animateBar()` + `wireConfPopBars()` in `app.js` (analog `animateCounts()`), ein `will-change`-
  Hinweis in `styles.css`. `prefers-reduced-motion`/Zielwert ≤ 0 → sofort. Rein additiv; `data.js`/
  `index.html` unverändert. Verifiziert: `node --check` ok, live (DOM) Konfidenz-Kopf 94 % (Zahl + Balken
  finit), Popover 3 Balken finit (75/96/92 %), keine Konsolenfehler; reduced-motion setzt sofort, Motion-
  Ramp startet nachweislich bei 0.

- **[Zyklus 23] Nachtragsangebot an Nordwind (Betas letzte unbelegte Zahl)** — neues Dokument
  `nachtrag-nordwind-beta` (Typ „Nachtragsangebot", Berichte): NA-2026-0037 von Meridian an die Nordwind
  Logistik AG mit `lineItems` (Prüfstation 250k + Engineering/SPS 110k + FAT 40k = 400.000 € netto /
  76.000 € USt / **476.000 € brutto**), NACHTRAG-Stempel, Aussteller Meridian — Reuse des Beleg-Skins.
  In `projekt-beta` als 3. Quelle (82 %) + Reasoning + Verwandte + Folgefrage eingewoben; belegt exakt die
  „+0,4 Mio. €". Fast reiner `data.js`-Additiv; zwei winzige `app.js`-Ergänzungen (`DOC_SKINS`-Eintrag +
  optionales `grossLabel`). Deterministisch (28 Docs, 16 Szenarien, 0 kaputte Refs, Zitate wortgleich,
  Arithmetik korrekt) + live verifiziert (Suche findet Beleg, `paper-beleg` mit Meridian/NACHTRAG/3
  Positionen/Angebotssumme brutto, keine Konsolenfehler).
- **[Zyklus 22] Projekt-Portfolio-Überblick** — neues Szenario `projekt-portfolio` (Berichte, 94 %)
  „Welche Projekte laufen aktuell?" stellt Alpha **und** Beta in **einer** Ampel-Übersichtstabelle
  gegenüber (Projekt · Fortschritt · Budget · Termin · Status): Alpha 62 %/24,0 Mio./✓ im Zeitplan, Beta
  48 %/8,6 Mio./⚠ 3 Wo. Verzug; Portfolio-Volumen 32,6 Mio. €, ehrlicher Schluss „1 von 2 termingefährdet".
  Quellen = **beide bestehenden Statusberichte** (je 96 %) + Vorstandsprotokoll (74 %). Rein additiv in
  `data.js` (Reuse `<table>`-Struktur + vorhandene Belege), kein neues Dokument, kein Code-Umbau. Hero
  12 → 13, Berichte 6 → 7 (Portfolio zuerst), Demo 15 → 16. Deterministisch (27 Docs, 16 Szenarien, 0
  kaputte Refs, Zitate wortgleich, Matcher kollisionsfrei) + live verifiziert (Hero-/Berichte-Tile, Klick
  → 94 % + Tooltip, alle Tabellenzellen + 32,6 Mio. € im DOM, keine Konsolenfehler).
- **[Zyklus 21] Zweites Projekt „Beta"** — neues Szenario `projekt-beta` (Berichte, 90 %) „Wie steht
  Projekt Beta?" mit Ampel-Statustabelle (Fortschritt 48 % ⚠ verzögert · Budget 8,6 Mio. € · Liefertermin
  Q4 2026 ⚠), Ursachen (Lieferverzug Elektronik + Kunden-Change-Request), Pönale-Risiko und
  Gegenmaßnahmen, offener Kontrast zu Alpha. Zwei neue Belege: `projekt-beta-status` (Projektbericht,
  6 Highlights) + `eskalation-beta-elektronik` (E-Mail, 3. Demo-Mail, zitierter Zulieferer-Verlauf) —
  beide über bestehende Skins, kein Code-Umbau. Rein additiv in `data.js`; Hero 11 → 12, Berichte 5 → 6,
  Geführte Demo 14 → 15. Deterministisch (27 Docs, 15 Szenarien, 3 Mails, 0 kaputte Refs) + live
  verifiziert (Beta-Kachel/Klick → 90 % + Tooltip, Ampel korrekt, Suche findet beide, `paper-email` +
  `paper-bericht` korrekt, keine Konsolenfehler).
- **[Zyklus 20] Konfidenz-Tooltip am Meter** — Hover/Focus am Konfidenz-Meter öffnet ein Popover, das die
  Prozentzahl aus den Quellen herleitet: **Quellen herangezogen · höchste Relevanz · Übereinstimmung der
  Belege** (einzeln/teilweise/hoch, „X von N ≥ 80 %"), je mit Mini-Balken; Fußzeile „Keine Behauptung —
  eine Ableitung aus konkreten Quellen." Rein datengetrieben aus `answer.sources` (keine neuen Felder),
  erscheint nur bei Antworten mit Quellen, tastatur-erreichbar (`tabindex`/`:focus-within`). Rein additiv:
  `buildConfPop()` + Kopf-Markup in `app.js`, `.conf-pop` in `styles.css`. Deterministisch + live
  verifiziert (14 Szenarien mit Quellen erhalten Tooltip, 0 ungültige Relevanz, Popover-Inhalt korrekt
  hergeleitet, Balken 25/98/55 %, keine Konsolenfehler).

- **[Zyklus 19] Reklamations-Vorgang (mangelhafte Stahllieferung → Gutschrift)** — neues Audit-Szenario
  `reklamation-stahl` (95 %) + zwei Belege: `maengelruege-mr-2026-0091` (Typ „Mängelrüge", roter
  MÄNGELRÜGE-Stempel) und `gutschrift-gs-2026-0203` (Typ „Gutschrift", Positionstabelle 11.040 € netto /
  13.137,60 € brutto, grüner GUTSCHRIFT-Stempel). §12 Gewährleistung im Rahmenvertrag ergänzt. Bewusst mit
  der Donau-Story verzahnt (separate Folgelieferung, kein Widerspruch zum sauberen Drei-Wege-Abgleich).
  Rein additiv in `data.js`; 2 DOC_SKINS in `app.js`, Stempel-Ton `.stamp-warn` in `styles.css`. Hero
  10 → 11, Demo 13 → 14 Szenarien. Deterministisch + live verifiziert (25 Docs, 14 Szenarien, 0 kaputte
  Referenzen; beide Belege öffnen mit korrektem Skin/Stempel/Aussteller/Tabelle; keine Konsolenfehler).

- **[Zyklus 18] Such-Beat als Opener der Geführten Demo** — `startDemo()` ruft vor der Szenario-Schleife
  `demoSearchBeat(token)`: Palette öffnet automatisch („23 Dokumente"), tippt „stahl" → 8 Treffer quer
  über Finanzen+Audit (`<mark>`), öffnet kurz einen **freigegebenen** Beleg im Viewer, schließt Palette +
  Viewer, *dann* die Frage-Sequenz. `resetDemoUi()` schließt jetzt zusätzlich Viewer/Palette (fail-safe
  bei Stopp mitten im Beat). Rein additiv in `app.js`. Live verifiziert (Beat läuft automatisch → 8/23 →
  Viewer → Fortschritt „1/13"; Stopp räumt sauber auf; keine Konsolenfehler).

- **[Zyklus 17] Globale Live-Suche (Command-Palette)** — Sidebar-Auslöser „🔍 Alles durchsuchen"
  (+ Strg/⌘ + K) öffnet ein zentriertes Modal, das live über **alle 23 Dokumente** filtert
  (Titel/Typ/Snippet/Autor/Modul); leeres Feld zeigt das komplette Inventar, Live-Zähler „X von 23".
  Treffer mit Modul-Tag + Typ, gelb markiertem Suchbegriff (`<mark>`), ↑/↓+Enter-Navigation, Klick öffnet
  den Beleg im bestehenden Viewer. Gesperrte Docs erscheinen, öffnen aber „Zugriff verweigert" ohne Leak.
  Rein additiv in `index.html`/`styles.css`/`app.js`. Deterministisch + live verifiziert (23 Docs,
  Filter exakt, `<mark>`-Highlight, ↓+Enter öffnet Viewer, gesperrter Treffer ohne Leak, keine
  Konsolenfehler).

- **[Zyklus 16] DSGVO-/Datenschutz-Szenario (neues Entscheider-Ressort)** — neues Szenario
  `datenschutz-audit` (Modul Audit, 93 %) „Sind wir DSGVO-konform?" mit Status-Tabelle (5 Prüffelder,
  je ✓ / ⚠ 1 offen) und ehrlicher Auflagen-Offenlegung (2 offen, Frist 31.03.2026); zwei neue
  Dokumente `datenschutz-audit-2025` (Prüfnachweis → BESTANDEN-Stempel, ext. DSB Dr. Julia Sander) und
  `verarbeitungsverzeichnis-2026` (Art. 30 VVT, 34 Tätigkeiten). Nach `brandschutz` einsortiert;
  Hero 9 → 10, audit-Vorschläge 2 → 3. Rein additiv in `data.js`. Deterministisch + live verifiziert
  (23 Docs, 13 Szenarien, 0 kaputte Referenzen; beide Docs öffnen mit korrektem Skin, keine
  Konsolenfehler).

- **[Zyklus 15] Ketten-Navigator im Dokumentenviewer** — kompakter „⛓ Entscheidungskette · Schritt n
  von 3"-Navigator, der automatisch bei den drei Ketten-Belegen (Lieferanten-E-Mail → Weiterleitung →
  Vorstandsprotokoll) oben im Viewer erscheint: horizontaler Stepper (Datum/Akteur, aktueller Schritt
  in Marken-Farbe, erledigte markiert) + „← Voriger / Nächster Beleg →"; Punkte und Buttons öffnen
  direkt den jeweiligen Beleg. Nur bei Ketten-Dokumenten (`chainStepIndex()`); Prev/Next an den Enden
  deaktiviert. Kette entdoppelt: `const DECISION_CHAIN` als einzige Quelle für Chat-Block **und**
  Viewer. Rein additiv in `data.js`/`app.js`/`styles.css`. Deterministisch + live verifiziert
  (21 Docs, 12 Szenarien, 0 kaputte Referenzen; Navigation korrekt, kein Strip bei Nicht-Ketten-Docs).

- **[Zyklus 14] Entscheidungskette als sichtbarer „Beleg-Pfad"** — neues Szenario `budget-herkunft`
  („Wie kam das Mehrbudget von 0,9 Mio. € zustande?") + neues Feld `answer.chain` und Renderer
  `appendChain()` (analog `appendWithheld()`): vertikale Timeline mit 3 Schritten (Lieferanten-E-Mail
  → Weiterleitung Einkauf→CFO → Vorstandsbeschluss), je Datum-Badge, Akteur, Label, Beschreibung und
  anklickbarem Beleg; letzter Schritt `strong`, Verbindungslinie durch die Punkte. Als erster Block
  unter der Antwort. Rein additiv in `data.js`/`app.js`/`styles.css`; Hero 8 → 9, Geführte Demo
  11 → 12. Deterministisch verifiziert (21 Docs, 12 Szenarien, 1 chain, 0 kaputte Referenzen;
  Markup+CSS live geprüft).

- **[Zyklus 13] Zweite E-Mail (interne Weiterleitung) → Entscheidungskette** — neues Dokument
  `email-weiterleitung-materialbudget` (Typ „E-Mail", Finanzen): WG-Weiterleitung der Donau-Preis-
  E-Mail von Thomas Krüger (Einkauf) an Dr. Katharina Vogel (CFO), Cc Projektleitung Alpha, mit
  Bewertung **0,9 Mio. € Mehrbedarf** für Projekt Alpha + Empfehlung Vorstands-Beschlussvorlage;
  Zitat-Verlauf = Original-Donau-E-Mail (sichtbarer Thread). 0,9 Mio. € = Herkunft der Zahl aus
  Vorstandsbeschluss TOP 2. Eingewoben in „Materialkosten" (3. Quelle, 81 %) und „Projekt Alpha".
  Rein additiv in `data.js`, kein Code-Umbau. Deterministisch verifiziert (21 Docs, 2 E-Mails,
  0 kaputte Referenzen).

- **[Zyklus 12] E-Mail-Skin im Viewer + Lieferanten-E-Mail** — neues Dokument
  `email-preisanpassung-donau` (Typ „E-Mail", Finanzen): Original-Ankündigung der Donau-
  Preisanpassung (15 %, §6 Preisgleitklausel) mit Postfach-Kopf (Avatar-Initialen, Von/An/Cc/
  Betreff/Gesendet), Anhang-Chip (148 KB) und Zitat-Verlauf. `DOC_SKINS["E-Mail"]` +
  `buildMailHead()`/`buildQuoted()`/`mailRow()`; ✉-Icon in der Bibliothek. Als 2. Quelle (88 %) +
  Verwandte + Reasoning in die Materialkosten-Antwort eingewoben → klickbar in der Geführten Demo.
  Rein additiv. Verifiziert (0 kaputte Referenzen, korrekter Kopf/Anhang/Zitat).

- **[Zyklus 11] Bewegungs-Politur — gestaffelter Block-Reveal + Modulwechsel-Fade** — die
  strukturierten Antwortblöcke blenden nacheinander ein (`block-rise`, +55 ms je Block via
  `--rev-delay`); Modulwechsel bekommen einen dezenten Fade-/Slide-in des Panel-Inhalts
  (`view-in` auf `.wrap`). `prefers-reduced-motion` deaktiviert beide Effekte sauber (opacity 1,
  keine unsichtbaren Blöcke). Rein additiv in `styles.css` + `revealBlocks()` in `app.js`.
  Deterministisch verifiziert.

- **[Zyklus 10] Handlungs-Abschluss — „An Vorstand senden" / „Als Briefing exportieren"** —
  Aktions-Block „↗ Ergebnis weiterreichen" unter jeder belegten Antwort; Klick → kurze
  Vorbereitungs-Phase → grüne Erfolgs-Bestätigung mit ✓-Badge, deterministischer Briefing-Nummer
  (BRF-2026-XXXX) und Datei-/Empfänger-Zeile. Erscheint nur bei Quellen-belegten Antworten; reine
  UI (keine echten Mails). Rein additiv in `app.js`/`styles.css`. Live verifiziert.

- **[Zyklus 9] Ressort-Breite — HR-Onboarding & Lieferanten-/Klumpenrisiko** — zwei neue Szenarien
  + Dokumente (`onboarding-checkliste-2026`, `lieferanten-risikoanalyse-2026`). Onboarding-
  Checkliste-Antwort (Konfidenz 96 %) und Lieferanten-Konzentrations-Tabelle (Donau 23,9 % +
  Single-Source-Warnung, Konfidenz 94 %), verzahnt mit der Stahl-/Ferro-Nord-Story. Rein additiv in
  `data.js`; Hero 6 → 8, „Geführte Demo" 9 → 11. Live verifiziert (0 kaputte Referenzen).

- **[Zyklus 8] Video-Politur — Tempo/Souveränität** — „⚡ Beantwortet in X,X s"-Signal im
  Antwortkopf (zählt hoch, deterministisch 1,2–2,6 s) + dezentes Hochzählen der fett gesetzten
  Kernzahlen (`animateCounts()`/`parseGermanNumber()`, easeOutCubic). Sicher gegen
  Jahre/Datum/PO-Nummern; `prefers-reduced-motion` respektiert. Rein additiv. Live verifiziert.

- **[Zyklus 7] Vertrauens-Story** — 2 gesperrte Dokumente (M&A-Akquisitionsvorlage,
  Vorstandsvergütung) ausgegraut mit Schloss + „Kein Zugriff — <Rolle>" in der Bibliothek;
  Klick öffnet „Zugriff verweigert" statt Inhalt (kein Leak). Neues 9. Szenario
  „Wachstumsstrategie" mit Governance-Signal „2 weitere Treffer für Sie nicht freigegeben"
  (neuer `appendWithheld()`-Block, anklickbare gesperrte Treffer). Rein additiv. Live verifiziert.

- **[Zyklus 6] Onboarding-Overlay** beim ersten Start — leichtgewichtiges Coachmark oben
  rechts, Pfeil auf den pulsierenden „Geführte Demo"-Button, ein Satz + Primär-CTA, der das
  Overlay schließt und die Demo direkt startet. Nur einmal (localStorage), Esc/Backdrop/Skip
  schließen, `prefers-reduced-motion` respektiert. Rein additiv. Live verifiziert.

- **[Zyklus 5] ESG/CO₂-Szenario** — neues 8. Szenario „CO₂-Fußabdruck/ESG-Kurs?" mit
  Trend-Tabelle (2020→2025→Ziel 2030) und ehrlicher Lücken-Offenlegung; neues Doc
  „Energie- & Emissionskennzahlen 2025"; `esg-bericht-2025` von 2 auf 6 Absätze vertieft.
  Rein additiv in `data.js`; „Geführte Demo" 7 → 8 Szenarien. Live verifiziert.

- **[Zyklus 4] Rechnungs-Positionstabelle** — echte Buchungstabelle (Pos./Bezeichnung/Menge/
  Einzelpreis/Summe) + optionale Netto/USt/Brutto-Fußzeile für Rechnung/Bestellung/Waren-
  eingang, datengetrieben über optionales `doc.lineItems` (Fallback = Text). Prüfungsechter
  Drei-Wege-Abgleich; alle 3 Belege live verifiziert.
- **[Zyklus 3] „Geführte Demo" (hands-free Auto-Play)** — Play-Button in der Topbar spielt
  alle 7 Szenarien automatisch ab (Frage tippen → `ask()` → Lesepause → nächstes),
  Fortschritt „n / 7", jederzeit stoppbar, Composer während der Demo gesperrt.
- **[Zyklus 2] Dokument-Skins im Viewer** — Papierblatt + Briefkopf pro `doc.type`,
  Beleg-/Prüf-Stempel, Vertrags-Unterschriftszeilen, Klausel-Marken, Highlights im Layout.
- **[Zyklus 1] Prototyp-Grundgerüst** — App-Rahmen, Chat-Streaming, Belege/Quellen/
  Konfidenz, Dokumentenviewer, Demo-Firma + 15 Dokumente + 7 Szenarien, live getestet.

## Bewusst NICHT offen (gehört nicht in diese Mission)
- Echte Backend-Anbindung, echtes RAG/Embeddings, Auth, Skalierung, Framework-Arbeit.
  → alles in [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md). Der Prototyp bleibt eine
  self-contained Frontend-Demo.
