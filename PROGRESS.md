# PROGRESS — Kundendemonstrations-Prototyp

> Gemessen gegen das Endziel: ein Demo-Prototyp, der einen CEO/CFO in einem
> Verkaufsvideo sofort überzeugt. **Jeden Zyklus fortschreiben.**

## Mission: AI STUDIO — PILOT SPRINT (v2) · **Phase B (Video) — Kern-Deliverables fertig, wartet auf Sven**

> **Phase B — Videoproduktion:** Alle drei Kern-Deliverables sind vorhanden —
> [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md), [VIDEO_SCENES.md](VIDEO_SCENES.md) und
> [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md) (narrensichere Aufnahme-Anleitung); dazu die
> **optionale** Untertiteldatei [VIDEO_SUBTITLES.de.srt](VIDEO_SUBTITLES.de.srt). **Gate B→C wartet
> allein auf Svens Aufnahme + Freigabe.** Bis dahin nur ändern, was Sven anmerkt.
>
> **Parallel (freeze-konforme Phase-C-Vorbereitung, kein Eingriff in `prototype/`):** **alle 5 reinen
> Doku-Bricks fertig** — [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) + [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md)
> + [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) + [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md)
> + neu [PILOT_KIT.md](PILOT_KIT.md) (48-h-Master-Runbook, das die vier Bricks zu **einem** Prozess
> zusammenfügt). **Die reinen Doku-Bricks sind damit vollständig abgeschlossen** — die restlichen
> Phase-C-Schritte (PILOT_CONFIG-Implementierung, End-to-End-Probelauf) berühren `prototype/` und warten
> auf Gate B→C.

> Seit 2026-07-08 gilt [MISSION_PILOT_SPRINT.md](MISSION_PILOT_SPRINT.md): drei Phasen bis zur
> Ziellinie — **A) Demo-Freeze → B) Video → C) Pilot-Kit**. **Phase A ist abgeschlossen
> (Gate A→B bestanden).** Phase-A-Checkliste — **alle 6 Kästchen erfüllt**:
> ✅ Money-Shot „Agenten dazubuchen" (Finale) · ✅ Deutsch durchgängig · ✅ belegte Antworten/
> Konfidenz/Kette (1920×1080) · ✅ Geführte Demo ≤ 4 min (kuratierte 6er-Kern-Auswahl, „n / 6") ·
> ✅ Ein-Klick Demo-Reset. **Nächste Phase: Videoproduktion** — VIDEO_SCRIPT / VIDEO_SCENES /
> RECORDING_CHECKLIST (siehe [NEXT_STEPS.md](NEXT_STEPS.md)).

## Prototyp-Baufortschritt: ≈ 92 % (Phase B — Video-Deliverables fertig, wartet auf Aufnahme)

> **2026-07-19 · Multi-`projectLeads`-Friction gelöst (freeze-konform, kein Eingriff in `prototype/`):** Statt
> eines identischen Re-Verifikations-Ticks (Churn) die seit ~4 Zyklen offene Friction konkret behoben — Draft
> `pilot.config.js` (in `pilot-assets/`) trägt jetzt `company.projectLeads` projekt-scoped (`alpha:[Bergmann,Falk]`
> · `beta:[Lindner]`), Alpha-Doppel-Lead faithful, nicht eingeebnet; `legal ≠ projectLead Reinhardt` klargestellt.
> De-riskt den gated Schritt-3-Wiring. Verifiziert: `node --check` (config + prototype) grün, Config-Werte rein
> synthetisch, **29 Docs · 17 Szenarien** unverändert, Baum clean. Nächster Fortschritt **gated auf Sven**.
>
> **2026-07-18 · Verifikations-Tick (grün):** Kein offener freeze-konformer Brick mehr (Zwillinge 12/12, 3/3
> Szenarien). Verifiziert: 0 Meridian-Leak (12 Dateien), `node --check` grün, 17 Szenarien unverändert, Baum
> clean. Nächster Fortschritt ist **gated auf Sven** (Aufnahme/Freigabe) — bis dahin nur, was Sven anmerkt.

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| App-Grundgerüst (Layout, Navigation, Design) | 20 % | 95 % | 19.0 |
| Chat-Experience (Streaming, Antwort-Struktur) | 20 % | 95 % | 19.0 |
| Belege pro Antwort (Quellen, Konfidenz, Nachvollziehbarkeit) | 15 % | 96 % | 14.4 |
| Dokumentenviewer (Preview, Highlights, Metadaten) | 15 % | 95 % | 14.25 |
| Demo-Firma & realistische Dokumente | 15 % | 93 % | 13.95 |
| Demo-Szenarien (Breite & Tiefe) | 10 % | 94 % | 9.4 |
| Video-Reife (Skript, Politur, Übergänge) | 5 % | 100 % | 5.0 |
| **Summe** | **100 %** | — | **≈ 95 %** gewichtet der begonnenen Bereiche |

> Hinweis: Die gewichtete Summe der *begonnenen* Bereiche liegt höher; der
> **Gesamtfortschritt ≈ 89 %** berücksichtigt weiter Reserven bei optionaler Rest-Tiefe (Kunden-
> Beauftragungsbeleg). Zyklus 24 schließt die **Bewegungs-Politur** (Konfidenz-/Relevanz-Balken laufen
> mit hoch) und hebt **Chat-Experience** (93 % → 95 %). Konservativ gemeldet.

## Verlauf

- **Phase C (Vorbereitung) · 3 Prosa-Zwillinge gestaged, `vorstand-summary` vollständig → ALLE 3 Pilot-Szenarien komplett (2026-07-17) ≈ 92 %** —
  Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C). Statt Re-Verifikation (Churn) die
  12-Dok-Checkliste **abgeschlossen**: nach `materialkosten` (5/5) und `projekt-beta` (4/4) jetzt die **3
  verbleibenden Belege des dritten Pilot-Szenarios `vorstand-summary`** (Projekt-Alpha-Status · Vorstands-
  protokoll · ESG-Bericht) als identitäts-bereinigte `.txt`-Zwillinge gestaged (nicht-gated Schritte 1+2).
  Damit sind **alle 3 Pilot-Szenarien** als Zwilling komplett. Neuer Generator `build_vorstand_twins.py`
  (additiv, mit Self-Check). **⚠ Accounting-Korrektur (CEO-Review):** die 3 Szenarien ziehen **12 Dokument-
  körper** heran; „10/12" zählte den Controlling-`.xlsx` versehentlich als Körper mit — er ist ein **Zahlen-
  Overlay ZUSÄTZLICH** zu den 12 (ersetzt keinen Körper). Wahr waren **9/12 Körper**; dieser Zyklus staged die
  3 fehlenden → **12/12 Körper** (`.xlsx` bleibt Overlay). **Personen-Regel angewandt & verifiziert:** Brandt →
  Moser (CEO), Ing. Petra Lang → **Nadine Falk** (Projektleitung Alpha); *Nachhaltigkeitsteam* (Team) bleibt;
  extern *Ferro Nord* bleibt; Self-Check + unabhängiger grep: **0 Meridian-Leak** (Firma · Personen).
  **Friction verschärft:** die Quelle nennt für „Projektleitung Alpha" **zwei** Namen (Sabine Reinhardt →
  Bergmann **und** Petra Lang → Falk) — Inkonsistenz im Meridian-Korpus, faithful auf zwei distinkte synth.
  Namen gemappt (nicht eingeebnet), für Schritt 3 protokolliert → bestätigt Empfehlung **Liste `projectLeads`**.
  Zahlen bewusst nicht perturbiert (verbatim in Szenario-Zitaten → an Schritt 3 gekoppelt). `prototype/`
  unverändert; `node --check` grün; **29 Docs · 17 Szenarien** unverändert. Ein Vorbereitungs-Brick hebt kein
  Gate → **Gate B→C wartet weiter nur auf Sven.** Es verbleibt **kein** Korpus-Körper mehr — nur die
  `prototype/`-berührenden gated Schritte (data.js-Übertragung + Config-Wiring inkl. `projectLeads`).

- **Phase C (Vorbereitung) · 4 Prosa-Zwillinge gestaged, `projekt-beta` vollständig (2026-07-16) ≈ 92 %** —
  Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C). Statt Re-Verifikation (Churn) die
  12-Dok-Checkliste weiter abgearbeitet: nach `materialkosten` (5/5, Vorzyklus) jetzt die **4 Belege des
  zweiten Pilot-Szenarios `projekt-beta`** (Status · Eskalation · Nachtrag · Auftrag) als identitäts-bereinigte
  `.txt`-Zwillinge gestaged (nicht-gated Schritte 1+2). Damit ist `projekt-beta` als **zweites** der 3 Pilot-
  Szenarien **komplett** (4/4); **Korpus-Abdeckung 6/12 → 10/12**. Neuer Generator `build_beta_twins.py`
  (additiv, mit Self-Check). **Personen-Regel angewandt & verifiziert:** Vogel → Hollmann (CFO), Brandt → Moser
  (CEO), Feldmann → Lindner (Projektleitung Beta), `meridian-industrie.example → muster-bau.example`; extern
  (*Nordwind Logistik AG* / *ElektroSys GmbH*) bleibt; Self-Check + unabhängiger grep: **0 Meridian-Leak**
  (Firma · Personen · Domain). **Friction verschärft:** eine **zweite** Projektleitung (Beta) ohne Config-Rolle
  → mehrere Projektleitungen → Schritt-3-Empfehlung von einzelner `projectLead`-Rolle auf **Liste `projectLeads`**
  angehoben. Zahlen bewusst nicht perturbiert (verbatim in Szenario-Zitaten → an Schritt 3 gekoppelt).
  `prototype/` unverändert; `node --check` grün; **29 Docs · 17 Szenarien** unverändert. Ein Vorbereitungs-Brick
  hebt kein Gate → **Gate B→C wartet weiter nur auf Sven.**
- **Phase C (Vorbereitung) · 3 Prosa-Zwillinge gestaged, `materialkosten` vollständig (2026-07-15) ≈ 92 %** —
  Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C). Statt Re-Verifikation (Churn) die vom
  Kohärenz-Audit angelegte **12-Dok-Checkliste weiter abgearbeitet**: nach den 2 Struktur-Zwillingen jetzt die
  **3 Prosa-Belege des primären Pilot-Szenarios `materialkosten`** (Q1-Bericht + 2 E-Mails) als identitäts-
  bereinigte `.txt`-Zwillinge gestaged (nicht-gated Schritte 1+2). Damit ist `materialkosten` als **erstes** der
  3 Pilot-Szenarien **komplett** abgedeckt (5/5 Belege); **Korpus-Abdeckung 3/12 → 6/12**. Neuer Generator
  `build_prose_twins.py` (additiv, mit Self-Check). **Personen-Regel + E-Mail-Domain angewandt & verifiziert:**
  Krüger → Kessler, Vogel → Hollmann, `meridian-industrie.example → muster-bau.example`; extern (*Andreas Huber* /
  *Stahlwerk Donau AG* / *Ferro Nord*) bleibt; Self-Check + unabhängiger grep: **0 Meridian-Leak** (Firma ·
  Personen · Domain). **Neue Friction dokumentiert:** 7. Persona *Projektleitung Alpha* ohne Config-Rolle → ad hoc
  auf *Sandra Bergmann* gemappt, Schritt-3-Empfehlung `projectLead` in `pilot.config.js`. Zahlen bewusst nicht
  perturbiert (verbatim in Szenario-Zitaten → an Schritt 3 gekoppelt). `prototype/` unverändert; `node --check`
  grün; **29 Docs · 17 Szenarien** unverändert. Ein Vorbereitungs-Brick hebt kein Gate → **Gate B→C wartet weiter
  nur auf Sven.**
- **Phase C (Vorbereitung) · 2 Struktur-Zwillinge gestaged (2026-07-14) ≈ 92 %** — Phase B bleibt auf
  **Svens Aufnahme + Freigabe** blockiert (Gate B→C). Statt Re-Verifikation (Churn) die vom Kohärenz-Audit
  angelegte **12-Dok-Checkliste konkret abgearbeitet**: die 2 strukturierten Korpus-Belege als synthetische
  CSV-Zwillinge gestaged (nicht-gated Schritte 1+2) — `rechnung-2026-1843_zwilling.csv` (lebende Formelkette
  `73.600 → 13.984 → 87.584 €`) + `rahmenvertrag-stahlwerk-donau_zwilling.csv` (Klausel-Tabelle §9/§6/§12) +
  `build_corpus_twins.py` (Generator mit Self-Check). **Korpus-Abdeckung 1/12 → 3/12.** **Audit-Gap 2
  (Personen-Regel) erstmals angewandt & verifiziert:** Meridian-intern → `pilot.config.js`-Namen (Krüger →
  Kessler, Wagner → Reinhardt, Meridian → Muster Bau), extern (Stahlwerk Donau) bleibt; Self-Check: 0
  Meridian-Leak. Zahlen bewusst nicht perturbiert (verbatim in Szenario-Zitaten → ±10 % an Schritt 3 gekoppelt).
  `prototype/` unverändert; `node --check` grün; 29 Docs · 17 Szenarien. **Gate B→C wartet weiter nur auf Sven.**
- **Phase C (Vorbereitung) · Vorab-Kohärenz-Audit Schicht A ↔ B (2026-07-10) ≈ 92 %** — Phase B bleibt auf
  **Svens Aufnahme + Freigabe** blockiert (Gate B→C); statt einer identischen Re-Verifikation (Churn) ein
  **neuer Winkel**: die zwei bereits gestageten Probelauf-Hälften für „Muster Bau GmbH" (Schicht A `pilot.config.js`
  + Schicht B synth. Zwilling), bisher **je isoliert** verifiziert, erstmals **gegeneinander** und gegen die
  Config-Versprechen geprüft (deterministisch: Node-VM gegen `data.js` + openpyxl gegen beide `.xlsx`). **Drei
  nicht-blockierende Kohärenz-Lücken** vorab protokolliert (README → „Vorab-Kohärenz-Audit" + [PILOT_KIT.md](PILOT_KIT.md)
  §8-Notiz): **(1)** die 3 Szenarien ziehen **12 verschiedene** Belege heran → der Zwilling-`.xlsx` ist **1 von
  12** (verifizierte Schritt-3-Checkliste); **(2)** die 6 synth. Config-Personen erscheinen in **0** Artefakten
  (Zwilling 0, `data.js` 0), die 12 Quelldocs tragen heute die **Meridian**-Namen → Schritt 3 muss sie 1:1
  ersetzen (Config-Kommentar von „tauchen auf" ehrlich auf „**sollen** via Schritt 3" gestellt); **(3)** die
  §8-Rechnungs-/Vertrags-CSV-Zwillinge sind **noch nicht gestaged**. Alle drei Lücken liegen **jenseits der
  Freeze-Grenze** (Schritt 3 berührt `prototype/`). **`prototype/` unverändert** (`git status`: nur `README.md`
  + `pilot.config.js` + `PILOT_KIT.md`), `node --check` grün, Live-Daten unverändert (**29 Docs · 17 Szenarien**).
  Ein Audit-Brick hebt kein blockiertes Gate → Fortschritt bleibt **≈ 92 %**; die gated Schritt-3-Übertragung
  startet jetzt **warm** (12-Dok-Checkliste + Personen-Regel). **Gate B→C wartet weiter nur auf Sven.**

- **Phase C (Vorbereitung) · Pilot-Config Schicht A real geschrieben (2026-07-09) ≈ 92 %** — Phase B bleibt
  auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C). Nachdem die Vorzyklen die Pipeline **Schicht B**
  (synthetischer Korpus, Schritte 1+2) real ausgeführt haben, jetzt die **Schicht A** (Umbranding-Config) für
  denselben Probelauf-Kunden konkret geschrieben statt nur spezifiziert: neue Datei
  [`pilot-assets/muster-bau-gmbh/pilot.config.js`](pilot-assets/muster-bau-gmbh/pilot.config.js) — vollständige
  `window.PILOT_CONFIG` nach [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) §4 für **Muster Bau GmbH** (Name,
  Tagline, Glyph `▲`, Akzent, 4 synth. Fakten, 6 synth. Personennamen, Branche `bau`, `corpus`-Zeiger), **3
  Schmerz-Szenarien = die verifizierte Bau-Startvorlage** aus [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)
  (`materialkosten` · `projekt-beta` · `vorstand-summary`; Money-Shot bleibt Finale). **Alle Werte 100 %
  synthetisch.** Damit sind **beide freeze-konformen Hälften des Probelaufs** ausgeführt — Daten (Schicht B) *und*
  Chrome (Schicht A). Verifiziert (deterministisch, Node-VM gegen die Live-`data.js`): Schema erfüllt (genau 3
  Szenarien, `people`-Keys deckungsgleich mit `COMPANY.people`), **alle 3 Szenario-IDs existieren** in `SCENARIOS`
  — und eine **Faktenkorrektur** belegt: die *Beispiel*-IDs der Spec (`rechnungspruefung-donau`,
  `liquiditaet-90-tage`) existieren **nicht**, die real gewählten IDs schon; **kein Meridian-Leak**; Live-Daten
  unverändert (**29 Docs · 17 Szenarien**). **`prototype/` unverändert** (`git status`: nur die neue
  `pilot.config.js`; nicht verdrahtet → Wiring gated bis Gate B→C), `node --check` (config + app.js + data.js)
  grün. Ein Vorbereitungs-Brick hebt kein blockiertes Gate → Fortschritt bleibt **≈ 92 %**; der 48-h-Pilot ist
  jetzt für „Muster Bau GmbH" **beidseitig** (Config + Korpus) ausgeführt & bewiesen. **Gate B→C wartet weiter
  nur auf Sven.**

- **Phase C (Vorbereitung) · Pilot-Datenpipeline real ausgeführt (2026-07-09) ≈ 92 %** — statt eines 6.
  identischen Re-Verifikations-Zyklus (Churn) die größte **unbewiesene** Annahme des Phase-C-Plans getilgt:
  die [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) beschrieb den Workflow „Kunden-Struktur rein →
  synthetischer Zwilling raus (Formeln intakt)" bislang nur **hypothetisch** (§Beispiel-Tabelle). Jetzt sind
  die **Schritte 1 + 2 tatsächlich ausgeführt** — die *nicht*-gated Hälfte der Pipeline (Schritt 3 = Laden in
  `data.js` bleibt gated). Neuer Ordner [`pilot-assets/muster-bau-gmbh/`](pilot-assets/muster-bau-gmbh/README.md),
  **außerhalb `prototype/`**: `build_input.py` baut reproduzierbar eine fiktive mehrblättrige Bau-Controlling-
  Mappe (Annahmen + Monatsabschluss Mai) mit Gelb-Konvention `FFF2CC` und **3 blattübergreifenden Formeln**;
  der `synthetic-data-creator` (Reuse, `python synth.py --from … --seed 42`, 43/43 Tests grün) erzeugt den
  synthetischen Zwilling. **Verifiziert (deterministisch, openpyxl):** **12/12 Formeln bit-genau erhalten**
  (inkl. blattübergreifend `=Annahmen!B5/100` u. a.); **gesetzliche USt-Konstante 19 % unangetastet** (bewusst
  nicht gelb); **12/14 gelbe Eingaben synthetisiert**; Labels/Einheiten/Blätter unverändert; Modell rechnet
  weiter (Formelkette aus den synth. Werten nachgerechnet: Netto **284.266,41 €**, Brutto **338.277,03 €**,
  Probe **Brutto = Netto × 1,19** bestätigt). **Lernpunkt:** feste/gesetzliche Konstanten *nicht* gelb
  markieren, sonst perturbiert die ±10 %-Heuristik — keine blockierende Friction. **`prototype/` unverändert**
  (`git status`: nur `pilot-assets/` neu), `node --check` (app.js + data.js) grün. Ein Vorbereitungs-Brick
  hebt kein blockiertes Gate → Fortschritt bleibt ≈ 92 %; die Pipeline ist jetzt **ausgeführt & bewiesen**
  (nicht mehr nur beschrieben), der 48-h-Pilot spürbar de-risked. **Gate B→C wartet weiter nur auf Sven.**

- **Phase B · Link-Integrität der Handover-Suite verifiziert (2026-07-09) ≈ 92 %** — reiner Verifikations-
  Zyklus mit **neuer Dimension**: statt Doc-Zähl-/Konsistenz-Prüfungen zu wiederholen (Churn), diesmal die
  **interne Markdown-Link-Integrität aller Wurzel-`.md`** geprüft — ein bisher nicht abgedeckter Winkel:
  brechende Querverweise machen ein Aufnahme-/Verkaufs-Kit für Nicht-Techniker unbrauchbar. **133 interne
  Links geprüft, 0 kaputt** (jeder relative Datei-Link → existierende Datei; Anker/`http(s)`/`mailto`
  ausgenommen). Live-Daten unverändert (Node-VM gegen `data.js`): **29 Docs · 17 Szenarien · 3 E-Mails ·
  2 gesperrt · 0 kaputte Referenzen · DECISION_CHAIN 3 Schritte**; Aufnahme-Pfad intakt: `DEMO_ORDER` =
  **6 IDs** (alle vorhanden) mit **Money-Shot `agent-dazubuchen` als Finale**, `matchDocs("stahl")` = **10**,
  `matchDocs("")` = **29**. `node --check` (app.js + data.js) grün, `git status` sauber, **`prototype/`
  unverändert** (Feature-Freeze gewahrt). **Keine Regression — die Demo ist unverändert aufnahmebereit.**
  Ein Verifikations-Pass hebt kein blockiertes Gate → Fortschritt bleibt ≈ 92 %. **Gate B→C wartet weiter
  nur auf Sven.**

- **Phase B · Aufnahme-Bereitschaft verhaltens-verifiziert (2026-07-09) ≈ 92 %** — reiner Verifikations-
  Zyklus mit **tieferem Winkel**: statt die Zähl-Prüfung ein drittes Mal identisch zu wiederholen (Churn),
  die **reale Command-Palette-Suche nachgestellt** — die `matchDocs()`-Feldmenge
  (`title · type · snippet · author · module`) exakt repliziert: `matchDocs("stahl")` = **10 Treffer**
  (ein naiver Ganz-Objekt-Scan liefert 12 → belegt, dass die im Skript/Checkliste genannte „10" die
  *sichtbare* Palette-Zahl ist, nicht die Rohzahl), `matchDocs("")` = **29** (volles Inventar). Zusätzlich
  die Demo-Steuerung aus `app.js` aufgelöst: `MONEY_SHOT_ID = "agent-dazubuchen"` (existiert in `data.js`),
  `DEMO_ORDER` = **6 IDs** mit dem Money-Shot als **Finale**, `DECISION_CHAIN` = **3 Schritte**. Node-VM
  gegen `data.js`: **29 Docs · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte Referenzen**; `grep`: keine
  16/27/28-Reste in den Video-Dateien; `node --check` (app.js + data.js) grün, `git status` sauber,
  **`prototype/` unverändert** (Feature-Freeze gewahrt). **Keine Regression — die Demo ist unverändert
  aufnahmebereit.** Ein Verifikations-Pass hebt kein blockiertes Gate → Fortschritt bleibt ≈ 92 %.
  **Gate B→C wartet weiter nur auf Sven.**

- **Phase B · Pilot-Kit-Konsistenz-Audit (2026-07-09) ≈ 92 %** — reiner Verifikations-Zyklus mit **neuem
  Prüf-Winkel**: statt die „Aufnahme-Bereitschaft" identisch zu wiederholen (Churn), die fünf Phase-C-
  Verkaufs-/Handover-Dokumente (das „Verkaufs-Werkzeug") **gegen die Live-Daten** abgeglichen — dieselbe
  Drift-Klasse, die zuvor 27/28 → 29 in den Video-Dateien aufdeckte. **Zero Drift:** `data.js` = **29 Docs ·
  17 Szenarien · 3 E-Mails · 2 gesperrt · DECISION_CHAIN 3 Schritte** deckungsgleich mit SCENARIO_LIBRARY /
  PILOT_KIT / SYNTHETIC_DATA_PIPELINE; **alle 17 Szenario-IDs** in SCENARIO_LIBRARY referenziert (0 fehlend);
  Agenten-Preise im [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) (Reporting 400 · Vertrags 500 · Rechnungs 600 €)
  bit-genau die `agent-dazubuchen`-Preise; Preis-Pfad **149 € → 5.000 € → 400 €/Mon.** identisch in One-Pager
  und PILOT_KIT; Money-Shot = `DEMO_ORDER`-Finale. `node --check` grün, `git status` sauber, **`prototype/`
  unverändert** (Feature-Freeze gewahrt). Ein Verifikations-Pass hebt kein blockiertes Gate → Fortschritt
  bleibt ≈ 92 %. Das Pilot-Kit ist als Verkaufs-Werkzeug stimmig. **Gate B→C wartet weiter nur auf Sven.**

- **Phase B · Aufnahme-Bereitschaft erneut re-verifiziert (2026-07-09) ≈ 92 %** — reiner Verifikations-
  Zyklus: Phase B bleibt auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C), die vorziehbaren Phase-C-
  Doku-Bricks sind erschöpft (alle 5 fertig), die restlichen Schritte berühren `prototype/` (bis Gate B→C
  gated). Statt zu churnen die einzig freeze-konforme Handlung: bestätigen, dass die Demo unverändert
  aufnahmebereit ist. `node --check` (app.js + data.js) ok; Ground-Truth deterministisch (Node-VM):
  **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte Referenzen**, `DEMO_ORDER` = 6 IDs
  (alle vorhanden) mit **Money-Shot `agent-dazubuchen` als Finale**, „stahl" = **10 Treffer**,
  `DECISION_CHAIN` = 3 Schritte; `grep`: keine 16/27/28-Reste in den Video-Dateien; `git status` sauber.
  **Keine Regression, `prototype/` unverändert.** Ein Verifikations-Pass hebt kein blockiertes Gate →
  Fortschritt bleibt ≈ 92 %. **Gate B→C wartet weiter nur auf Sven.**

- **Phase C (Vorbereitung) · PILOT_KIT.md (2026-07-09) ≈ 92 %** — Phase B bleibt auf **Svens Aufnahme +
  Freigabe** blockiert (Gate B→C). Statt eines weiteren identischen Re-Verifikations-Zyklus die **letzte
  freeze-konforme Phase-C-Brick** gebaut: [PILOT_KIT.md](PILOT_KIT.md) — das **Master-Runbook**, das die
  vier vorbereitenden Bricks ([PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) · [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)
  · [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) · [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md))
  zu **einem** durchgehenden 48-h-Prozess zusammenfügt. Enthält ein Ablaufdiagramm **T+0 → T+48**
  (Audit-Call → 3 Szenarien → synth. Zwilling → Schicht A `pilot.config.js` + Schicht B `data.js`-Korpus →
  deterministisch verifizieren → Übergabe + Preis-Pfad), ein Schritt-für-Schritt-Runbook, eine **kopierbare
  Master-Checkliste** (ein Pilot = eine Kopie), ein **Zeit-Budget** (~2–4 h Netto-Handaufwand vs. 48-h-
  Kundenversprechen), eine **Definition of Done** und ein **markiertes Platzhalter-Protokoll „Muster Bau
  GmbH"** (§8) für den späteren End-to-End-Probelauf. **Reine Handover-/Playbook-Datei — kein Eingriff in
  `prototype/`** (Feature-Freeze gewahrt): `git status` zeigt nur die neue `.md`, `node --check` (app.js +
  data.js) grün, alle internen Querverweise lösen auf. Die `prototype/`-berührenden Schritte (Schritt 3 +
  Config-Wiring) und der **tatsächliche Probelauf** → **erst nach Gate B→C**. Ein Doku-Brick hebt kein
  blockiertes Gate → Fortschritt bleibt **≈ 92 %**; damit sind **alle 5 Phase-C-Doku-Bricks abgeschlossen**
  und der 48-h-Pilot-Prozess ist als **ein** einheitliches Runbook verkaufbar. **Gate B→C wartet weiter nur
  auf Sven.** (Phase-C-Deliverable 5 von 5 — Playbook-Portion.)

- **Phase C (Vorbereitung) · PILOT_CONFIG_SPEC.md (2026-07-09) ≈ 92 %** — Phase B bleibt auf **Svens
  Aufnahme + Freigabe** blockiert (Gate B→C). Statt eines weiteren identischen Re-Verifikations-Zyklus die
  **Design-Portion der nächsten Phase-C-Brick** vorgezogen: [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) —
  Spezifikation des Umbranding-Mechanismus. Grounded durch Lesen von `prototype/` (nichts geändert):
  Firmenname „Meridian Industrie GmbH" steht **~55-mal** in `data.js`-Dokumentkörpern → Umbranding ist
  **zwei Schichten**: **A) Shell/Chrome** per neuer `pilot.config.js`, die das `COMPANY`-Objekt überschreibt
  (die Shell liest heute schon fast alles daraus — `renderCompanyCard`, Hero, Briefing, `#searchCompany`);
  **B) Dokumentenkorpus wholesale ersetzt** durch den synthetischen Zwilling ([SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md)),
  nicht per Suchen-Ersetzen. Enthält Config-Schema (`company`/`industry`/genau 3 `scenarios`/optional
  `accent`+`corpus`), additiven Wiring-Plan (Script-Tag + Guard + `applyPilotChrome()`), Token-Konvention
  `{{COMPANY}}` gegen künftige Hartkodierung, 48-h-Ablauf-Diagramm und Abnahme-Kriterien — u. a. `active:false`
  → **bit-identische Meridian-Demo** (Regressionsschutz für das noch aufzunehmende Video). **Reine
  Handover-/Design-Datei — kein Eingriff in `prototype/`** (Feature-Freeze gewahrt): `git status` zeigt nur
  die neue `.md`, `node --check` (app.js + data.js) ok, `prototype/` 0 geänderte Dateien. Die
  **Implementierung** berührt `prototype/` → **erst nach Gate B→C**. Ein Design-Brick hebt kein blockiertes
  Gate → Fortschritt bleibt **≈ 92 %**. (Phase-C-Deliverable 1 — Design-Portion; Deliverable 4 von 5 der
  vorziehbaren Doku-Bricks.)

- **Phase C (Vorbereitung) · SYNTHETIC_DATA_PIPELINE.md (2026-07-09) ≈ 92 %** — Phase B bleibt auf **Svens
  Aufnahme + Freigabe** blockiert (Gate B→C). Wie im Handover angekündigt die **dritte freeze-konforme
  Phase-C-Brick** gebaut: [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) — dokumentiert den
  wiederholbaren Pilot-Workflow **Kunden-Dateistruktur rein → synthetischer Zwilling raus (Formeln intakt)
  → in `prototype/data.js` geladen**. Nutzt das **bestehende** Tool `synthetic-data-creator`
  (`C:\Users\botrunner\projects\synthetic-data-creator`, **43/43 Tests** verifiziert) statt Neubau: Mehrblatt-
  Excel mit Formelerhalt (auch blattübergreifend), Gelb-Konvention `FFF2CC`, CSV/JSON/XLSX/PDF, `--seed` für
  reproduzierbare Demos. Enthält 4-Schritt-Prozess (Audit-Call → Eingabe formen → `python synth.py --from …`
  → Eintrag in `DOCS`/`lineItems` → deterministisch verifizieren), Ablaufdiagramm, Beispieltabelle
  „Muster Bau GmbH" und eine klar markierte **Freeze-Grenze** (Eintrag in `data.js` + PILOT_CONFIG berühren
  `prototype/` → erst nach Gate B→C). **Reine Handover-Datei — kein Eingriff in `prototype/`** (Feature-Freeze
  gewahrt). Verifiziert: `git status` vor dem Schreiben sauber, `node --check` (app.js + data.js) ok,
  `prototype/` unverändert, Tool-Tests 43/43. Ein Doku-Brick hebt kein blockiertes Gate → Fortschritt bleibt
  **≈ 92 %**; damit sind die **reinen** Phase-C-Doku-Bricks abgeschlossen — die restlichen Schritte warten
  auf Gate B→C. (Phase-C-Deliverable 3 von 5.)

- **Phase C (Vorbereitung) · PILOT_ONE_PAGER.md (2026-07-09) ≈ 92 %** — Phase B bleibt auf **Svens Aufnahme
  + Freigabe** blockiert (Gate B→C). Wie im Handover angekündigt die **nächste freeze-konforme Phase-C-Brick**
  gebaut: [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) — das **Angebotsdokument** für den Audit-Call, in
  CFO-Sprache. Enthält das 48-h-Versprechen („Ihre eigene Demo, kein echtes Dokument nötig"), **was der
  Kunde nach 48 h sieht** (Name/Logo · 3 Schmerz-Szenarien · belegte Antworten · Money-Shot) und den
  **Preis-Pfad** als Tabelle (**Audit 149 € → Wissensbasis ab 5.000 € → Agent-Abo ab 400 €/Monat**), dazu
  Agenten-Preisvergleich, Einwand-Antworten und CTA. Preise/Agenten deckungsgleich mit dem Prototyp-
  Money-Shot (`agent-dazubuchen`) und [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md). **Reine Vertriebsdatei —
  kein Eingriff in `prototype/`** (Feature-Freeze gewahrt). Verifiziert: `git status` zeigt **nur** die neue
  `.md`, `node --check` (app.js + data.js) ok. Ein Doku-Brick hebt kein blockiertes Gate → Fortschritt bleibt
  **≈ 92 %**; damit beantwortet die CEO-Review-Frage 3 („versteht ein CFO in 90 s, wofür er 5.000 € + 400 €/
  Monat zahlt?") jetzt **eine Seite explizit mit Ja**. (Phase-C-Deliverable 2 von 5.)

- **Phase C (Vorbereitung) · SCENARIO_LIBRARY.md (2026-07-09) ≈ 92 %** — Phase B bleibt auf **Svens Aufnahme
  + Freigabe** blockiert (Gate B→C); ein dritter identischer Re-Verifikations-Zyklus wäre reines Churnen.
  Stattdessen — wie im letzten Handover angekündigt („sonst → Phase C") — die **niedrigst-riskante Phase-C-
  Brick** vorgezogen: [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md). Alle **17 Szenarien** aus `data.js` nach
  **Schmerz** (KOSTEN · RECHNUNGSPRÜFUNG · VERTRÄGE · MONATSABSCHLUSS · PROJEKTE · LIQUIDITÄT/RISIKO ·
  COMPLIANCE · WISSENSVERLUST · ESG/GOVERNANCE) und **Branche** verschlagwortet — mit Modul, Konfidenz,
  Belegzahl; dazu **fertige 3er-Startvorlagen** je Branche (Fertigung · Bau · Handel · Logistik ·
  Dienstleistung · Querschnitt) + Auswahl-Spickzettel, Money-Shot als markiertes Finale. So lassen sich nach
  einem 30-Min-Audit-Call in **Minuten** die 3 passenden Szenarien wählen. **Reine Doku aus `data.js` — kein
  Eingriff in `prototype/`** (Feature-Freeze gewahrt), kein neues Feature. Verifiziert: `node --check`
  (app.js + data.js) ok, `git status` zeigt **nur** die neue `.md`. Ein Doku-Brick hebt kein blockiertes Gate
  → Fortschritt bleibt **≈ 92 %**; **Gate B→C wartet weiter nur auf Sven**, aber der 48-h-Pilot-Prozess wird
  konkret. (Phase-C-Deliverable 1 von 5 begonnen.)

- **Phase B · Aufnahme-Bereitschaft re-verifiziert (2026-07-09) ≈ 92 %** — reiner Verifikations-Zyklus:
  Phase B ist auf **Svens Aufnahme + Freigabe** blockiert (Gate B→C), der Feature-Freeze verbietet neue
  Arbeit. Statt zu churnen die einzig freeze-konforme Handlung: **bestätigen, dass die Demo unverändert
  aufnahmebereit ist.** `node --check` (app.js + data.js) ok; Ground-Truth deterministisch (Node-VM):
  **29 Dokumente · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte Referenzen**, `DEMO_ORDER` = 6 IDs
  ohne Lücke mit **Money-Shot als Finale**, „stahl" = **10 Treffer**; `grep`: keine veralteten Zähl-Reste
  (16/27/28) in den Video-Dateien. **Keine Regression, `prototype/` unverändert.** Fortschritt bleibt
  ≈ 92 % (ein Verifikations-Pass hebt kein blockiertes Gate). **Gate B→C wartet weiter nur auf Sven.**

- **Phase B · Skript/Shotlist-Faktenkorrektur (2026-07-09) ≈ 92 %** — die Video-Handover-Dateien nannten
  Zahlen, die nicht mehr zum Prototyp passen (ein nicht-technischer Aufnehmer hätte sie für einen Fehler
  gehalten). Gegen die Live-Daten geprüft und korrigiert: **Dokumentenzahl 27/28 → 29** (Such-Beat/
  Command-Palette-Zähler in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) Szene 0b und [VIDEO_SCENES.md](VIDEO_SCENES.md)
  Szene 0a/B-Roll/Globale-Suche; „10 von 27" → „10 von 29"; der „stahl"→**10 Treffer** war bereits korrekt)
  und die **Geführte Demo „alle 16 Szenarien / n / 16" → „kuratierte 6er-Kern-Auswahl / n / 6"** (endet auf
  dem Money-Shot, < 4 Min — die seit Phase-A-Abschluss reale `DEMO_ORDER`). Zusätzlich in beiden Dateien ein
  **Klarstellungs-Hinweis**: die Szene-für-Szene-Abfolge ist die **manuelle Langfassung**, die Geführte Demo
  deckt davon 6 Kern-Momente automatisch ab; verbindlich bleibt [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md).
  **Nur `.md` — `prototype/` unverändert (Feature-Freeze gewahrt).** Verifikation: Ground-Truth deterministisch
  (Node-VM gegen `data.js`) — 29 Dokumente, 17 Szenarien, „stahl" = 10 Treffer, `DEMO_ORDER` = 6 IDs mit dem
  Money-Shot als Finale; anschließend `grep`: **keine** 16/27/28-Reste mehr in Skript oder Shotlist. Damit
  sind alle Phase-B-Aufnahme-Dateien faktentreu — **Gate B→C wartet weiter nur auf Svens Aufnahme + Freigabe.**
  (Video-Reife bleibt 100 %; Gesamtfortschritt konservativ 92 %.)

- **Phase B · VIDEO_SUBTITLES.de.srt (2026-07-08) ≈ 92 %** — die in der Phase-B-Checkliste als „optional,
  aber wertvoll" genannte **Untertiteldatei** ist erstellt. `VIDEO_SUBTITLES.de.srt`: **47 Cues**, deutsch,
  direkt aus den `Sprecher`-Zeilen von [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) abgeleitet (je 1–2 Zeilen, alle
  ≤ 55 Zeichen), monotone Zeitleiste **~0:00–4:22** (entspricht der manuellen Langfassung aller Szenen inkl.
  optionaler Ressort-Beats 5b). Standard-SRT, in jedes Schnittprogramm/Player einlesbar; kurze Verweis-
  Sektion „Untertitel (SRT)" in `VIDEO_SCRIPT.md` ergänzt (Timings = Richtwerte, beim finalen Schnitt an die
  reale Sprechergeschwindigkeit angleichen; nicht gefilmte Cues entfernen). **Reine Handover-Datei** —
  `prototype/` unverändert (Feature-Freeze gewahrt). Verifikation deterministisch (Node-Parser): 47 Cues,
  Indizes lückenlos 1–47, alle Timecodes wohlgeformt, **keine Überlappung**, Ende > Start je Cue, kein Cue
  > 2 Zeilen, keine Zeile > 55 Zeichen. **Damit sind alle Phase-B-Deliverables (inkl. optionaler) fertig —
  Gate B→C wartet weiter nur auf Svens Aufnahme + Freigabe.** (Video-Reife bleibt 100 %; Gesamtfortschritt
  konservativ 92 %.)

- **Phase B · RECORDING_CHECKLIST.md (2026-07-08) ≈ 92 %** — die **letzte Phase-B-Kern-Deliverable**: eine
  narrensichere Aufnahme-Anleitung, mit der eine **nicht-technische Person** das Verkaufsvideo ohne
  Vorwissen aufnimmt. Browser-Setup (Chrome/Vollbild/100 % Zoom/**„Bewegung reduzieren" AUS**), Reset-
  Ritual vor jedem Take (Inkognito fürs Intro + „⟲ Zurücksetzen"), schnellster Weg über die **Geführte
  Demo** (6 Kern-Szenen, „n / 6", endet auf dem **Money-Shot**, < 4 Min) mit „was-der-CFO-sieht"-Tabelle,
  Nachvertonung, **Fehler→Behebung-Tabelle** + Retake-Regel, optionale manuelle Langfassung (17 Szenarien)
  und ein **Kurz-Spickzettel** zum Ankleben. Reine Handover-Datei — `prototype/` unverändert (Feature-
  Freeze gewahrt); gegen die reale Demo verifiziert (Node-VM: 29 Docs, 17 Szenarien, `DEMO_ORDER` = 6 IDs
  mit Money-Shot als Finale). **Damit sind alle drei Phase-B-Kern-Deliverables fertig — Gate B→C wartet
  nur noch auf Svens Aufnahme + Freigabe.** (Video-Reife bleibt 100 %; Gesamtfortschritt konservativ 92 %.)

- **Phase A · Freeze abgeschlossen (2026-07-08) ≈ 91 % — PHASE_A_COMPLETE** — die letzten beiden
  Phase-A-Kästchen erledigt: **(1) Geführte Demo auf ≤ 4 min kuratiert** — neue `DEMO_ORDER` +
  `demoScenarios()` in `app.js` spielen hands-free eine **straffe 6er-Kern-Auswahl** (Materialkosten →
  Rechnungsprüfung → Entscheidungskette → Projekt-Portfolio → Governance → **Money-Shot**) statt aller 17
  Szenarien; Fortschritt „n / 6", Money-Shot garantiert als Finale, Fail-safe-Rückfall auf die volle
  Liste. Alle 17 bleiben per Kachel/Frage/Suche erreichbar. **(2) Ein-Klick „Zurücksetzen"** (Topbar-
  Button + `resetDemo()`): sauberer Startzustand für wiederholbare Video-Takes (Demo stoppen, Verlauf
  leeren, Viewer/Palette zu, zurück auf den Hero). Rein additiv (`app.js`/`styles.css`/`index.html`);
  **kein neues Szenario/Dokument** (Feature-Freeze gewahrt), `data.js` unverändert. Verifiziert:
  `node --check` ok, Node-VM (6 IDs existieren, Money-Shot letzt, 17 gesamt); live (DOM): Reset rendert +
  räumt Chat/Viewer/Palette (Hero zurück, 14 Vorschläge, Composer entsperrt), Geführte Demo „1 / 6",
  Reset mitten in der Demo stoppt sauber, keine Konsolenfehler. **Gate A→B bestanden → Phase B (Video).**

- **Phase A · Money-Shot (2026-07-08) ≈ 90 %** — **„Agenten dazubuchen" als Demo-Finale** (der
  Verkaufsmoment des Abos, bislang das größte Phase-A-Loch). Neues Abschluss-Szenario
  `agent-dazubuchen` (letztes in `SCENARIOS` → automatisch letzte Szene der Geführten Demo): Die
  Wissensbasis steht — jetzt mietet der Kunde **digitale Mitarbeiter** obendrauf. Neuer `answer.agents`-
  Block + Renderer `appendAgents()`: 4 Agenten-Karten (Auskunfts-Agent inklusive/aktiv, **Reporting-
  Agent 400 € empfohlen**, Rechnungs-Agent 600 €, Vertrags-Agent 500 €), „＋ Dazubuchen" → grüne
  „✓ Aktiviert"-Bestätigung; Preis-Pfad-Fußzeile (Audit 149 € → Wissensbasis ab 5.000 € → Agent ab
  400 €/Monat). In der Geführten Demo **bucht sich der empfohlene Agent hands-free selbst** (token-
  gesichert; letzte Lesepause 1600 → 3400 ms). Antwortkopf ohne Konfidenz-Meter (Buchungsansicht ohne
  Quellen; `hasConf`-Guard in `streamAnswer()`). Zusätzlich der Rest-WIP aus dem alten Modus
  abgeschlossen: `auftrag-nordwind-beta` (Auftragsbestätigung, extIssuer/BEAUFTRAGT) → Betas +0,4 Mio. €
  jetzt **beidseitig** belegt (4. Quelle in `projekt-beta`). Rein additiv in `data.js`/`app.js`/
  `styles.css`. Verifiziert: `node --check` ok, Node-VM (29 Docs, 17 Szenarien, 0 kaputte Refs); live
  (DOM/CSS): 4 Karten, 3 Buchen-Buttons + Aktiv/Empfohlen-Badges, Grid 2-spaltig (377 px) @1920×1080,
  gebuchte Karte grün, Kopf ohne Konfidenz-Meter, keine Konsolenfehler. (Streaming-/Screenshot-Pfad
  harness-throttled → DOM/CSS/Daten-basiert, wie in den Vorzyklen.)

- **Zyklus 24 (2026-07-08) ≈ 89 %** — Konfidenz-/Relevanz-Balken laufen mit hoch (letzte Bewegungs-Politur):
  Beim Einblenden einer Antwort läuft der Balken des Konfidenz-Meters jetzt — passend zum Zahlen-Count-up —
  in ~760 ms (easeOutCubic) von 0 auf den Zielwert, statt hart zu springen; die Konfidenz-Zahl im Kopf
  zählt zusätzlich mit hoch. Die drei Relevanz-Balken der Konfidenz-Herleitung (Popover) laufen beim ersten
  Öffnen einmalig hoch (640 ms). Neuer Helfer `animateBar()` + `wireConfPopBars()` in `app.js` (analog
  `animateCounts()`), drei Zeilen Wiring in `streamAnswer()`, ein `will-change: width`-Hinweis in
  `styles.css`. `prefers-reduced-motion` oder Zielwert ≤ 0 → sofort auf den Endwert. Rein additiv;
  `data.js`/`index.html` unverändert. Verifiziert: `node --check` ok, Wiring-Checks bestanden; live (DOM)
  Konfidenz-Kopf 94 % (Zahl + Balken finit), Popover-mouseenter → 3 cp-Balken finit (75/96/92 %), keine
  Konsolenfehler; reduced-motion setzt korrekt sofort den Endwert, Motion-Ramp startet nachweislich bei 0
  (0,04 % am Frame-Start). (Chat-Experience 93 % → 95 %.)

- **Zyklus 23 (2026-07-08) ≈ 88 %** — Nachtragsangebot an Nordwind: der Kunden-Änderungswunsch von
  Projekt Beta (**+0,4 Mio. €**, zusätzliche Prüfstation) ist jetzt ein Original-Beleg. Neues Dokument
  `nachtrag-nordwind-beta` (Typ „Nachtragsangebot", Modul Berichte): NA-2026-0037 von Meridian an die
  Nordwind Logistik AG, Positionstabelle (Prüfstation 250k + Engineering/SPS 110k + erweiterte FAT 40k =
  **400.000 € netto** / USt 76.000 € / **476.000 € brutto**), NACHTRAG-Stempel, Aussteller Meridian —
  Reuse des Beleg-Skins mit `lineItems`. In `projekt-beta` als 3. Quelle (82 %) + Reasoning-Schritt +
  Verwandte + Folgefrage eingewoben; belegt exakt die vorher nur behaupteten „+0,4 Mio. €". Fast reiner
  `data.js`-Additiv-Schritt; zwei winzige rückwärtskompatible `app.js`-Ergänzungen (`DOC_SKINS`-Eintrag +
  optionales `lineItems.grossLabel` → Fußzeile „Angebotssumme brutto"). Deterministisch verifiziert:
  28 Docs (war 27), 16 Szenarien, 3 E-Mails, 0 kaputte Referenzen, alle 3 Beta-Quell-Zitate wortgleich,
  Arithmetik korrekt (250+110+40=400; +19 %=476); live geprüft (Suche findet den Beleg, Klick öffnet
  `paper-beleg` mit Meridian als Aussteller, NACHTRAG-Stempel, 3 Positionszeilen + Netto/USt/Angebotssumme
  brutto, Beta-Szenario trägt die Quelle, keine Konsolenfehler). (Demo-Firma 90 % → 93 %.)

- **Zyklus 22 (2026-07-08) ≈ 87 %** — Projekt-Portfolio-Überblick: neues Szenario `projekt-portfolio`
  (Modul Berichte, Konfidenz 94 %) „Welche Projekte laufen aktuell?" — stellt **Alpha und Beta in einer
  Ampel-Übersichtstabelle** gegenüber (Projekt · Fortschritt · Budget · Termin · Status): Alpha 62 % ·
  24,0 Mio. € · Q4 2026 · ✓ im Zeitplan; Beta 48 % · 8,6 Mio. € · Q4 2026 · ⚠ 3 Wo. Verzug. Portfolio-
  Volumen 32,6 Mio. € (18,8 verausgabt), ehrlicher Schluss „1 von 2 Projekten termingefährdet". Quellen =
  **beide bestehenden Statusberichte** (je 96 %) + Vorstandsprotokoll (74 %) → Tooltip „3 Quellen · höchste
  Relevanz 96 % · Übereinstimmung hoch". Der „ganzes Portfolio auf einen Blick"-Moment; in der Geführten
  Demo direkt nach Alpha + Beta. Rein additiv in `data.js` (Reuse `<table>`-Struktur + vorhandene Belege),
  kein Code-Umbau. Hero 12 → 13, Berichte 6 → 7 (Portfolio zuerst), Geführte Demo 15 → 16 Szenarien.
  Deterministisch verifiziert: 27 Docs, 16 Szenarien, 0 kaputte Referenzen, Zitate wortgleich, Matcher
  kollisionsfrei; live geprüft (Hero-/Berichte-Tile, Klick → 94 % + Tooltip, alle Tabellenzellen +
  32,6 Mio. € im DOM, keine Konsolenfehler). (Szenarien 93 % → 94 %.)

- **Zyklus 21 (2026-07-08) ≈ 86 %** — Projekt Beta als Breiten-Schritt: neues Szenario `projekt-beta`
  (Modul Berichte, Konfidenz 90 %) „Wie steht Projekt Beta?" — eine kundenspezifische Anlage für die
  Nordwind Logistik AG, bewusst **verzögert**. Antwort mit **Ampel-Statustabelle** (Fortschritt 48 %
  ⚠ · Budget 8,6 Mio. € im Rahmen · Liefertermin Q4 2026 ⚠ 3 Wo. Verzug), Ursachen (Lieferverzug
  Steuerungselektronik + Kunden-Change-Request), Pönale-Risiko (max. 0,43 Mio. €), Gegenmaßnahmen und
  **offenem Kontrast zu Alpha** („im Zeitplan"). Zwei neue Belege: `projekt-beta-status`
  (Projektbericht, `paper-bericht`, 6 Highlights) und `eskalation-beta-elektronik` (E-Mail, `paper-email`,
  3. Demo-E-Mail, zitierter Zulieferer-Verlauf) — beide über den **bestehenden** Skin-Pfad, kein
  Code-Umbau. Rein additiv in `data.js`. Hero 11 → 12, Berichte 5 → 6, Geführte Demo 14 → 15 Szenarien.
  Deterministisch verifiziert: 27 Docs (war 25), 15 Szenarien, 3 E-Mails, 0 kaputte Referenzen, Zitate
  im Body, Relevanzen gültig; live geprüft (Beta-Kachel + Klick → 90 % + Tooltip, Ampel-Tabelle korrekt,
  Suche findet beide Docs, E-Mail öffnet `paper-email` mit 5 Kopfzeilen + Zitat, Status öffnet
  `paper-bericht` mit 6 Highlights, keine Konsolenfehler). (Demo-Firma 86 % → 90 %, Szenarien 92 % → 93 %.)

- **Zyklus 20 (2026-07-08) ≈ 85 %** — Konfidenz-Herleitung als Hover/Focus-Tooltip am Konfidenz-Meter:
  hovert der Cursor die Prozentzahl im Antwortkopf, öffnet sich ein kleines Popover, das zeigt, *woraus*
  sich die Zahl speist — **Quellen herangezogen** (Anzahl), **höchste Relevanz** (Top-Quelle) und **Grad
  der Übereinstimmung der Belege** (einzeln / teilweise / hoch, je „X von N Belegen ≥ 80 % Relevanz"),
  jeweils mit Mini-Balken. Fußzeile: *„Keine Behauptung — eine Ableitung aus konkreten Quellen."*
  Entkräftet den letzten CFO-Einwand („woher weiß das System das?") direkt am Meter. Rein datengetrieben
  aus dem bestehenden `answer.sources`-Array (keine neuen Datenfelder), erscheint nur bei Antworten mit
  Quellen. Rein additiv: `buildConfPop()` + Kopf-Markup in `app.js`, `.conf-pop`-Block in `styles.css`;
  `data.js`/`index.html` unverändert. Deterministisch verifiziert (Node-VM gegen `data.js`): alle **14
  Szenarien** mit Quellen erhalten den Tooltip, **0 ungültige Relevanzwerte**, Labels korrekt (einzeln/
  teilweise/hoch). Live im Browser gegen reale Daten geprüft: Kopf trägt `conf has-pop` + `tabindex`,
  Popover-Inhalt korrekt hergeleitet (Reiserichtlinie: 1 Quelle, Top 98 %, „einzeln"), Mini-Balken
  25/98/55 % passend, Popover erscheint per `:focus-within` (opacity 1, sichtbar), keyboard-erreichbar,
  keine Konsolenfehler. (Screenshot-Capture im Harness instabil — DOM/CSS-basiert verifiziert.)
  (Belege pro Antwort 94 % → 96 %.)

- **Zyklus 19 (2026-07-08) ≈ 84 %** — Reklamations-Vorgang (mangelhafte Stahllieferung → Gutschrift):
  neues Szenario `reklamation-stahl` (Modul Audit, Konfidenz 95 %) „Wie haben wir die mangelhafte
  Stahllieferung reklamiert?" — 12 t (von 60 t) fallen bei der Wareneingangsprüfung durch eine
  **Maßabweichung EN 10029** + Walzhautfehler, **§377-HGB-Rüge** fristgerecht, **Gutschrift 11.040 €
  netto / 13.137,60 € brutto**. Zwei neue Belege: `maengelruege-mr-2026-0091` (Typ „Mängelrüge", roter
  MÄNGELRÜGE-Stempel, Aussteller Meridian) und `gutschrift-gs-2026-0203` (Typ „Gutschrift",
  Positionstabelle, grüner GUTSCHRIFT-Stempel, Aussteller Lieferant). Rahmenvertrag um **§12
  Gewährleistung** ergänzt → Zitate lösen auf sichtbare Klausel auf. Bewusst mit der Donau-Story
  verzahnt (separate Folgelieferung, keine Kollision mit dem sauberen Drei-Wege-Abgleich). Rein additiv
  in `data.js`; 2 Skins in `app.js`, Stempel-Ton `.stamp-warn` in `styles.css`. Hero 10 → 11, Geführte
  Demo 13 → 14 Szenarien. Deterministisch verifiziert: 25 Docs (war 23), 14 Szenarien, 0 kaputte
  Referenzen, Arithmetik korrekt; live geprüft (beide Belege öffnen mit korrektem Skin/Stempel/Aussteller/
  Positionstabelle, Suche findet sie, Szenario-Kopf 95 %, keine Konsolenfehler). (Demo-Firma 81 % → 86 %,
  Szenarien 90 % → 92 %.)

- **Zyklus 18 (2026-07-08) ≈ 82 %** — Such-Beat als Opener der Geführten Demo: die in Zyklus 17
  gebaute globale Suche wird jetzt **hands-free vorgeführt**. `startDemo()` ruft vor der Szenario-
  Schleife `demoSearchBeat(token)` — die Command-Palette öffnet automatisch („23 Dokumente im
  Wissensspeicher"), tippt sichtbar **„stahl"** → **8 Treffer quer über Finanzen + Audit** mit
  `<mark>`-Highlight, öffnet kurz einen **freigegebenen** Beleg im Viewer (gesperrte übergangen → kein
  „Zugriff verweigert" als Opener) und schließt Palette + Viewer, *dann* startet die Frage-Sequenz. Die
  Menge des erschlossenen Wissens ist damit das **erste Bild** des Videos. `resetDemoUi()` schließt
  jetzt zusätzlich Viewer/Palette → Stoppen mitten im Beat hinterlässt keinen offenen Zustand; voll
  token-gesteuert, `prefers-reduced-motion` respektiert. Rein additiv in `app.js`; `data.js`/
  `styles.css`/`index.html` unverändert. Live im Browser gegen reale Daten verifiziert: Beat läuft
  automatisch (Palette → „stahl" → 8/23, Module Finanzen/Audit/Verträge, Viewer „Quartalsbericht Q1
  2026" öffnet+schließt → Fortschritt „1 / 13", Composer gesperrt); Stopp mitten im Beat räumt sauber
  auf; keine Konsolenfehler. (Screenshot-Capture im Harness instabil — DOM-basiert verifiziert.)
  (Video-Reife 99 % → 100 %.)

- **Zyklus 17 (2026-07-08) ≈ 81 %** — Globale Live-Suche (Command-Palette): sichtbarer
  „Was steckt alles drin?"-Moment über den **gesamten** Wissensspeicher. Neuer Sidebar-Auslöser
  **„🔍 Alles durchsuchen"** (+ **Strg/⌘ + K** von überall) öffnet ein zentriertes Modal, das beim
  Tippen **live** über Titel/Typ/Snippet/Autor/Modul **aller 23 Dokumente** filtert; leeres Feld zeigt
  das **komplette Inventar** („23 Dokumente im Wissensspeicher"), Live-Zähler „X von 23". Treffer je
  mit **Modul-Tag + Typ**, Suchbegriff **gelb hervorgehoben** (`<mark>`, sicher escaped),
  Tastatur-Navigation (↑/↓ + Enter öffnet den ersten/markierten Treffer), Klick öffnet den Beleg im
  bestehenden Viewer. **Gesperrte Dokumente** erscheinen als Treffer, öffnen aber die „Zugriff
  verweigert"-Ansicht (kein Inhalts-Leak) → Governance-Story bleibt konsistent. Cross-Modul belegt
  (eine „stahl"-Suche zeigt Treffer aus Finanzen **und** Audit). Reuse: `openViewer()` + Marken-Tokens;
  rein additiv in `index.html`/`styles.css`/`app.js`, `data.js` unverändert. `prefers-reduced-motion`
  respektiert. Deterministisch verifiziert (Node-VM gegen `data.js`): 23 Docs, Filter exakt (""→23,
  „stahl"→8, „vertrag"→4, „dsgvo"→2, „donau"→6, kein-Treffer→0), 0 Feld-Fehler. Live im Browser
  geprüft: Auslöser + Strg+K öffnen/schließen, 23 Zeilen bei leerem Feld, korrekter Zähler, `<mark>`-
  Highlight, ↓+Enter öffnet Viewer (Titel korrekt), gesperrter Treffer → `paper-locked` ohne Leak,
  keine Konsolenfehler. (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM/CSS-
  basiert verifiziert.) (App-Grundgerüst 92 % → 95 %.)

- **Zyklus 16 (2026-07-08) ≈ 79 %** — DSGVO-/Datenschutz-Szenario (neues Entscheider-Ressort): neues
  Szenario `datenschutz-audit` (Modul Audit, Konfidenz 93 %) „Sind wir DSGVO-konform — wann war das
  letzte Datenschutz-Audit?" mit Status-Tabelle (5 Prüffelder Art. 30/32/28/Betroffenenrechte/72-h-
  Meldeprozess, je ✓ / ⚠ 1 offen) und ehrlicher Auflagen-Offenlegung (2 offen, Frist 31.03.2026).
  Zwei neue Dokumente (Modul Audit): `datenschutz-audit-2025` (Typ „Prüfnachweis" → BESTANDEN-Stempel,
  ext. DSB Dr. Julia Sander, 6 Highlights) und `verarbeitungsverzeichnis-2026` (Typ „Verzeichnis" →
  Fallback Bericht-Skin, Art. 30 VVT, 34 Tätigkeiten). Nach `brandschutz` einsortiert → zwei
  Audit-/Compliance-Beats hintereinander in der Geführten Demo; Hero 9 → 10, `audit`-Vorschläge 2 → 3.
  Rein additiv in `data.js`. Deterministisch verifiziert: 23 Docs (war 21), 2 E-Mails, 13 Szenarien
  (war 12), 1 chain, 0 kaputte Referenzen; live geprüft (DSGVO-Hero-Kachel, beide Karten im Audit-
  Modul, Datenschutz-Audit als `paper-nachweis` + BESTANDEN + 6 Highlights, VVT als `paper-bericht`
  + 3 Highlights, keine Konsolenfehler). (Demo-Firma 77 % → 81 %, Szenarien 87 % → 90 %.)

- **Zyklus 15 (2026-07-08) ≈ 78 %** — Ketten-Navigator im Dokumentenviewer (Option B aus Zyklus 14):
  öffnet man einen der drei Ketten-Belege (Lieferanten-E-Mail → Weiterleitung → Vorstandsprotokoll),
  erscheint oben ein kompakter Navigator **„⛓ Entscheidungskette · Schritt n von 3"** — horizontaler
  Stepper mit Datum/Akteur je Schritt (aktueller Schritt in Marken-Farbe, erledigte markiert) +
  Fußzeile „← Voriger Beleg / Nächster Beleg →". Stepper-Punkte **und** Vor/Zurück öffnen direkt den
  jeweiligen Beleg → man blättert durch die ganze Kette, ohne den Viewer zu verlassen. Nur bei den drei
  Ketten-Dokumenten (per `chainStepIndex()`); Prev am 1. / Next am letzten Schritt deaktiviert. Kette
  **entdoppelt**: `const DECISION_CHAIN` in `data.js` ist jetzt einzige Quelle der Wahrheit für Chat-
  Block **und** Viewer-Navigator. Rein additiv in `data.js`/`app.js`/`styles.css`. Deterministisch
  verifiziert: 21 Docs, 2 E-Mails, 12 Szenarien, 1 chain, `budget-herkunft.chain === DECISION_CHAIN`,
  0 kaputte Referenzen; Navigation live gegen reale Daten geprüft (Vor/Zurück + Punkt-Klick wechseln
  korrekt, kein Strip bei Nicht-Ketten-Docs, Marken-Tokens gebunden, keine Konsolenfehler).
  (Viewer 92 % → 95 %, Belege 93 % → 94 %, Szenarien 86 % → 87 %.)

- **Zyklus 14 (2026-07-08) ≈ 76 %** — Entscheidungskette als sichtbarer „Beleg-Pfad": neues Szenario
  `budget-herkunft` („Wie kam das Mehrbudget von 0,9 Mio. € zustande?") + neues optionales Feld
  `answer.chain` und Renderer `appendChain()` (analog `appendWithheld()`). Vertikale Timeline mit 3
  Schritten (Lieferanten-E-Mail 12.02. → Weiterleitung Einkauf→CFO 13.02. → Vorstandsbeschluss März),
  je Datum-Badge, Akteur, Label, Beschreibung und **anklickbarem Beleg** (öffnet Viewer); letzter
  Schritt `strong` hervorgehoben, Verbindungslinie durch die Punkte. Als erster Block unter der
  Antwort → maximale Wirkung, wird vom Block-Reveal mitanimiert. Rein additiv in `data.js`/`app.js`/
  `styles.css`; Hero 8 → 9, Geführte Demo 11 → 12 Szenarien. Deterministisch verifiziert: 21 Docs,
  2 E-Mails, 12 Szenarien, 1 chain, 0 kaputte Referenzen; Chain-Markup+CSS live gegen reale
  Szenariodaten geprüft (Tokens/Linie/Klickbarkeit korrekt), keine Konsolenfehler.
  (Chat 91 % → 93 %, Belege 91 % → 93 %, Szenarien 84 % → 86 %.)
- **Zyklus 13 (2026-07-08) ≈ 74 %** — Zweite E-Mail (interne Weiterleitung): neues Dokument
  `email-weiterleitung-materialbudget` (Typ „E-Mail", Finanzen) — die WG-Weiterleitung der
  Donau-Preis-E-Mail von Thomas Krüger (Einkauf) an Dr. Katharina Vogel (CFO), Cc Projektleitung
  Alpha, mit der Bewertung **0,9 Mio. € Mehrbedarf** für Projekt Alpha und der Empfehlung einer
  Vorstands-Beschlussvorlage; **Zitat-Verlauf** = die Original-Donau-E-Mail (sichtbarer Thread). Die
  0,9 Mio. € stammen exakt aus dem Vorstandsbeschluss TOP 2 → die Weiterleitung ist die **Herkunft
  dieser Zahl**. Eingewoben in „Materialkosten" (3. Quelle, 81 %) und „Projekt Alpha" (Herkunft des
  Mehrbudgets, neuer Reasoning-Schritt). Rein additiv in `data.js`, kein Code-Umbau (E-Mail-Skin
  rendert automatisch). Deterministisch verifiziert: 21 Docs (war 20), 2 E-Mails, 11 Szenarien,
  0 kaputte Referenzen. (Belege 89 % → 91 %, Demo-Firma 74 % → 77 %, Szenarien 82 % → 84 %.)
- **Zyklus 12 (2026-07-08) ≈ 73 %** — E-Mail-Skin im Viewer: neues Dokument
  `email-preisanpassung-donau` (Typ „E-Mail", Finanzen) — die Original-Ankündigung von Stahlwerk
  Donau über die 15-%-Preisanpassung, mit Postfach-Kopf (Avatar-Initialen, Von/An/Cc/Betreff/
  Gesendet), Anhang-Chip (148 KB) und Zitat-Verlauf. `DOC_SKINS["E-Mail"]` + `buildMailHead()`/
  `buildQuoted()`/`mailRow()`; `buildPaper()` verzweigt für `cat==="email"`; ✉-Icon in der
  Bibliothek. Als 2. Quelle (88 %) + Verwandte + Reasoning-Schritt in die Materialkosten-Antwort
  eingewoben → klickbar in der Geführten Demo. Rein additiv in `data.js`/`app.js`/`styles.css`.
  Verifiziert: ✉-Karte in Finanzen, `paper-email` mit korrektem Kopf/Anhang/Zitat, 0 kaputte
  Referenzen (20 Docs), keine Konsolenfehler. (Viewer 89 % → 92 %, Demo-Firma 70 % → 74 %,
  Belege 88 % → 89 %.)
- **Zyklus 11 (2026-07-08) ≈ 71 %** — Bewegungs-Politur: die strukturierten Antwortblöcke
  (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) blenden jetzt **gestaffelt**
  ein (`block-rise`, je Block +55 ms via `--rev-delay`) statt hart zu springen; Modulwechsel
  bekommen einen dezenten **Fade-/Slide-in** des Panel-Inhalts (`view-in` auf `.wrap`). Rein
  additiv in `styles.css` + kleiner `revealBlocks()`-Helfer in `app.js`; Datenpfad unverändert.
  `prefers-reduced-motion` deaktiviert beide Effekte sauber (Blöcke bleiben voll sichtbar, opacity
  1). Deterministisch verifiziert: `block-rise` mit korrektem Delay (0,11 s bei --rev-delay:110ms)
  im Normalbrowser, `none`+opacity 1 unter reduzierter Bewegung. (Video-Reife 96 % → 99 %,
  Chat 90 % → 91 %.)
- **Zyklus 10 (2026-07-08) ≈ 70 %** — Handlungs-Abschluss: Aktions-Block „↗ Ergebnis weiterreichen"
  unter jeder belegten Antwort mit „✉ An Vorstand senden" / „⤓ Als Briefing exportieren". Klick →
  Vorbereitungs-Phase (Spinner) → grüne Erfolgs-Bestätigung mit ✓-Badge, deterministischer
  Briefing-Nummer (BRF-2026-XXXX) und Empfänger-/Datei-Zeile. Nur bei Quellen-belegten Antworten;
  reine UI. Rein additiv in `app.js`/`styles.css`. Live verifiziert (Render, Position, Primär-
  Styling, Klick→Bestätigung, keine Konsolenfehler). Schließt die Story „Frage → belegte Antwort →
  weiterreichbares Ergebnis". (Chat 86 % → 90 %, Video-Reife 94 % → 96 %.)
- **Zyklus 9 (2026-07-08) ≈ 67 %** — Ressort-Breite: zwei neue Szenarien + Dokumente. „Onboarding,
  erster Tag" (HR, Checkliste-Antwort, Konfidenz 96 %) mit neuem Doc `onboarding-checkliste-2026`;
  „Lieferanten-/Klumpenrisiko" (Finanzen, Konzentrations-Tabelle Donau 23,9 % + Single-Source-
  Warnung, Konfidenz 94 %) mit neuem Doc `lieferanten-risikoanalyse-2026` (`lineItems`, 5 Positionen).
  Bewusst mit der Stahl-Story verzahnt (Donau/Ferro Nord). Rein additiv in `data.js`; Hero 6 → 8,
  „Geführte Demo" 9 → 11. Live verifiziert (0 kaputte Referenzen, Tabelle korrekt, Quell-Links lösen
  auf). (Szenarien 74 % → 82 %, Demo-Firma 62 % → 70 %.)
- **Zyklus 8 (2026-07-08) ≈ 64 %** — Video-Politur: „⚡ Beantwortet in X,X s"-Signal im
  Antwortkopf (zählt hoch, deterministisch 1,2–2,6 s) + dezentes Hochzählen der fett gesetzten
  Kernzahlen (`animateCounts()`/`parseGermanNumber()`, easeOutCubic ~760 ms). Sicher gegen
  Jahre/Datum/PO-Nummern; `tabular-nums`, `prefers-reduced-motion` respektiert. Rein additiv in
  `app.js`/`styles.css`. Live verifiziert (Parser exakt gegen reale Zahlen, Mechanismus auf
  realem Fragment). (Video-Reife 86 % → 94 %, Chat 84 % → 86 %.)

- **Zyklus 7 (2026-07-08) ≈ 62 %** — Vertrauens-/Governance-Story: 2 gesperrte Dokumente
  (M&A-Akquisitionsvorlage, Vorstandsvergütung) ausgegraut mit Schloss + „Kein Zugriff" in der
  Bibliothek; Klick öffnet „Zugriff verweigert" statt Inhalt (kein Leak). Neues 9. Szenario
  „Wachstumsstrategie" mit Governance-Signal „2 weitere Treffer für Sie nicht freigegeben"
  (neuer `appendWithheld()`-Block, anklickbare gesperrte Treffer). Rein additiv in
  `data.js`/`app.js`/`styles.css`. Live verifiziert. (Szenarien 68 % → 74 %, Chat 82 % → 84 %.)
- **Zyklus 6 (2026-07-08) ≈ 58 %** — Onboarding-Overlay beim ersten Start: leichtgewichtiges
  Coachmark oben rechts, Pfeil auf den pulsierenden „Geführte Demo"-Button, ein Satz +
  Primär-CTA, der das Overlay schließt und die Demo direkt startet. Nur einmal (localStorage),
  Esc/Backdrop/Skip schließen, `prefers-reduced-motion` respektiert. Rein additiv in
  `index.html`/`styles.css`/`app.js`. Live verifiziert. (Video-Reife 72 % → 86 %.)
- **Zyklus 5 (2026-07-07) ≈ 55 %** — ESG/CO₂-Szenario: neues 8. Szenario „CO₂-Fußabdruck/
  ESG-Kurs?" mit Trend-Tabelle (2020→2025→Ziel 2030) und ehrlicher Lücken-Offenlegung; neues
  Doc „Energie- & Emissionskennzahlen 2025"; `esg-bericht-2025` von 2 auf 6 Absätze vertieft.
  Rein additiv in `data.js`, „Geführte Demo" 7 → 8. Live verifiziert. (Szenarien 58 % → 68 %,
  Demo-Firma 52 % → 58 %.)
- **Zyklus 4 (2026-07-07) ≈ 52 %** — Rechnungs-Positionstabelle im Beleg-Skin: echte
  Buchungstabelle (Pos./Bezeichnung/Menge/Einzelpreis/Summe) + optionale Netto/USt/Brutto-
  Fußzeile für Rechnung/Bestellung/Wareneingang. Datengetrieben über optionales
  `doc.lineItems` (Fallback = Text). Drei-Wege-Abgleich jetzt prüfungsecht (gleiche Menge/
  Beträge über alle 3 Belege). Rein additiv, alle 3 Belege live verifiziert. (Viewer 80 % → 88 %.)
- **Zyklus 3 (2026-07-07) ≈ 48 %** — „Geführte Demo": Play-Button in der Topbar spielt alle
  7 Szenarien hands-free ab (Frage sichtbar tippen → bestehender `ask()`-Flow → Lesepause),
  Fortschritt „n / 7", jederzeit stoppbar, Composer während der Demo gesperrt. Rein additiv,
  `data.js` unverändert. Start/Typing/Fortschritt/Stopp live verifiziert. (Video-Reife 40 % → 70 %.)
- **Zyklus 2 (2026-07-07) ≈ 42 %** — Dokument-Skins im Viewer: Papierblatt + Briefkopf
  pro `doc.type`, Beleg-/Prüf-Stempel (EINGANG/GEPRÜFT/BESTANDEN), Vertrags-
  Unterschriftszeilen, Klausel-Marken, Highlights im Dokument-Layout. Alle 4 Skin-
  Kategorien live verifiziert. (Viewer 50 % → 80 %.)
- **Zyklus 1 (2026-07-07) ≈ 35 %** — Prototyp erstmals aufgesetzt: buildfreie
  Enterprise-Web-App, fiktive „Meridian Industrie GmbH", Chat-Zentrum mit gestreamten
  Antworten, Belege+Konfidenz+Quellen, Dokumentenviewer, 7 Szenarien, live getestet.
  (Davor: 31 Zyklen `platform/`-Architektur-Doku — nicht Teil der Prototyp-Mission.)

## Was den Fortschritt als Nächstes hebt (Phase B — Videoproduktion)

> **Phase A ist abgeschlossen (Feature-Freeze bleibt in Kraft).** Ab jetzt keine neuen Prototyp-Features
> mehr — nur noch das Verkaufsvideo produktionsreif machen. Neue Ideen → [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md).

1. **VIDEO_SCRIPT.md** — 90–120 s, Deutsch, CFO-Sprache (kein RAG/LLM-Jargon). Bogen: Schmerz („Ihr
   Wissen steckt in Ordnern und Postfächern") → Demo-Momente (belegte Antworten · Entscheidungskette ·
   Portfolio-Ampel) → Money-Shot („Agenten dazubuchen wie Mitarbeiter") → CTA („Daten-Audit, 149 €").
2. **VIDEO_SCENES.md** — Szene-für-Szene-Shotlist, gemappt auf die **kuratierte 6er-Reihenfolge** der
   Geführten Demo (Timestamps, On-Screen-Momente, Voiceover je Szene).
3. **RECORDING_CHECKLIST.md** — Auflösung 1920×1080, Browser-Zoom, „Zurücksetzen" vor jedem Take,
   Szenario-Reihenfolge, Retake-Anweisung — so, dass eine nicht-technische Person nicht scheitern kann.
   Optional: SRT-Untertitel aus dem Skript.
