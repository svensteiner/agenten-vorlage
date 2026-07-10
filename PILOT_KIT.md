# PILOT_KIT — der wiederholbare 48-Stunden-Pilot-Prozess

> **Phase C · Deliverable 5 von 5** (AI STUDIO — PILOT SPRINT MODE v2) — das **Master-Runbook**, das die
> vier vorbereitenden Bricks zu **einem** durchgehenden Ablauf zusammenfasst: vom 30-Minuten-Audit-Call bis
> zur eigenen, belegten Kundendemo binnen 48 Stunden.
>
> **Stand: Playbook-Portion fertig, End-to-End-Probelauf ausstehend.** Der dokumentierte Prozess steht
> vollständig bereit. Der **tatsächliche Probelauf „Muster Bau GmbH"** führt Schritte aus, die `prototype/`
> berühren (Eintrag in `data.js`, `pilot.config.js`) → er wird **erst nach Gate B→C** (Svens Video-Aufnahme
> + Freigabe) ausgeführt und dann in §8 dieser Datei protokolliert. **Diese Datei selbst ändert `prototype/`
> nicht** (Feature-Freeze gewahrt).

**Die vier Bausteine, die dieses Runbook orchestriert:**

| # | Baustein | Rolle im 48-h-Ablauf |
|--:|----------|----------------------|
| 1 | [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) | Das **Angebot**, das den Pilot verkauft (Preis-Pfad, 48-h-Versprechen). Wird im Audit-Call gezeigt. |
| 2 | [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) | Die **Szenario-Auswahl** — nach dem Call in Minuten 3 passende von 17 Szenarien wählen. |
| 3 | [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) | Die **Datenpipeline** — Kunden-Dateistruktur rein → synthetischer Zwilling (Formeln intakt) raus. |
| 4 | [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) | Der **Umbranding-Mechanismus** — eine `pilot.config.js` setzt Name/Logo/Branche/3 Szenarien. |

---

## 1. Das Versprechen, das dieses Runbook einlöst

> **„Nach einem 30-Minuten-Audit-Call sieht der Kunde binnen 48 h seine eigene Demo — sein Firmenname,
> seine Branche, seine drei Schmerz-Szenarien — mit 100 % synthetischen Daten. Wir brauchen kein einziges
> echtes Dokument von ihm."**

Das ist die Vertriebs-Waffe: **Pilot ohne Risiko.** Damit dieses Versprechen in **Stunden statt Tagen**
wiederholbar wird, ist ein Pilot kein Programmierprojekt, sondern **zwei Datei-Operationen** auf der
bestehenden Meridian-Demo:

- **Schicht A — Chrome umbranden:** eine kleine `pilot.config.js` (Name, Tagline, Logo-Glyph, Fakten,
  Branche, 3 Szenario-IDs).
- **Schicht B — Korpus tauschen:** die synthetischen Zwillings-Dokumente in `data.js` (statt der ~55
  Meridian-Namensvorkommen; siehe [PILOT_CONFIG_SPEC.md §2](PILOT_CONFIG_SPEC.md)).

Der Money-Shot `agent-dazubuchen` (Agenten dazubuchen wie Mitarbeiter) bleibt **unberührt** und hängt sich
automatisch als Finale an — er verkauft das Abo in jedem Pilot gleich.

---

## 2. Der Ablauf auf einen Blick

```
                          ┌──────────────────────────────────────────────┐
   T+0h   AUDIT-CALL ─────┤ One-Pager zeigen · Schmerz + Struktur einsammeln
   (30 min)               └──────────────────────────────────────────────┘
                                     │  Firmenname · Branche · 3 Schmerzpunkte
                                     │  Dokumenttypen + Ablageorte  (KEIN echtes Dokument)
                                     ▼
   T+2h    [1] SZENARIEN WÄHLEN ....  SCENARIO_LIBRARY.md  → genau 3 IDs (+ Money-Shot-Finale)
                                     ▼
   T+4h    [2] DATEN ERZEUGEN .....   SYNTHETIC_DATA_PIPELINE.md
                                     │  python synth.py --from <struktur> --seed 42
                                     │  Personen erfunden · Zahlen plausibel · Formeln intakt
                                     ▼
   T+24h   [3a] SCHICHT A ..........  pilot.config.js schreiben        (PILOT_CONFIG_SPEC §4)
           [3b] SCHICHT B ..........  synth. Zwilling → data.js DOCS[] (Datenübertrag, kein app.js-Umbau)
                                     ▼
   T+40h   [4] VERIFIZIEREN .......   node --check · 0 kaputte Refs · Arithmetik · live im Browser
                                     ▼
   T+48h   KUNDE SIEHT SEINE DEMO ─►  eigener Name/Logo · 3 Szenarien belegt · Money-Shot
                                     ▼
           NÄCHSTER SCHRITT .......   One-Pager Preis-Pfad: Audit 149 € → Foundation ab 5.000 €
                                                                     → Agent-Abo ab 400 €/Monat
```

> Die Stundenmarken sind **Puffer-Richtwerte** (der reine Handaufwand liegt bei ~2–4 h, siehe §6). Die
> 48 h sind das **Kundenversprechen**, nicht die Netto-Arbeitszeit.

---

## 3. Voraussetzungen (einmalig einrichten)

- **Prototyp lauffähig:** [`prototype/`](prototype/) per Doppelklick auf `index.html` (buildfrei).
- **Datenwerkzeug einsatzbereit:** `C:\Users\botrunner\projects\synthetic-data-creator`
  (**43/43 Tests grün**), Python 3.10+, `pip install openpyxl pdfplumber fpdf2` — Details in
  [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md).
- **Node** (nur zur Verifikation: `node --check`, Node-VM-Zählung).
- **Das Angebot griffbereit:** [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) für den Call.
- **Grundregel:** alles synthetisch. **Nie** ein echter Kundenname, **nie** ein echtes Logo-Bild
  (Glyph statt Bilddatei = kein Rechte-/Asset-Risiko).

---

## 4. Das Runbook — Schritt für Schritt

### Schritt 0 · Audit-Call (30 min) — einsammeln, nicht sammeln lassen

Ziel: eine **Struktur-Skizze**, kein einziges echtes Dokument.

- [ ] [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) zeigen — Versprechen + Preis-Pfad in 90 s.
- [ ] **Firmenname, Branche, grobe Kennzahlen** (Umsatz, Mitarbeitende, Standorte) — nur als
      Plausibilitäts-Rahmen für synthetische Werte.
- [ ] **Dokumenttypen + Ablageorte** notieren: „Controlling-Excel je Monat", „Eingangsrechnungen als PDF",
      „Rahmenverträge als Word", „Projektstatus als Excel" — inkl. *wo* sie liegen (Ordner/Postfach/ERP),
      denn der `path` jedes Belegs zitiert später diese Ablage.
- [ ] **Die drei größten Schmerzpunkte** in O-Ton mitschreiben (für das 🔖-Tag-Matching).

### Schritt 1 · Genau 3 Szenarien wählen (< 5 min) — [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)

- [ ] Schmerz-O-Töne → 🔖-Tags matchen (KOSTEN · RECHNUNGSPRÜFUNG · VERTRÄGE · MONATSABSCHLUSS · PROJEKTE ·
      LIQUIDITÄT/RISIKO · COMPLIANCE · WISSENSVERLUST · ESG/GOVERNANCE).
- [ ] **Genau 3** IDs festlegen — bewährte Mischung: **1× Kosten + 1× Prüfung/Compliance + 1× Reporting**.
      Schnellster Weg: die **fertige 3er-Startvorlage** der Kundenbranche (SCENARIO_LIBRARY §„3er-Auswahlen").
- [ ] Reihenfolge = Einstieg → belegter Aha-Moment → Reporting/Portfolio. Der **Money-Shot** hängt sich
      automatisch als Finale an und wird **nicht** mitgezählt.

> Beispiel Bau: `materialkosten` → `projekt-beta` → `vorstand-summary`. Beispiel Handel:
> `beleg-rechnung` → `lieferanten-risiko` → `vorstand-summary`.

### Schritt 2 · Synthetischen Zwilling erzeugen — [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md)

- [ ] Eingabe **formen**: Muster-Struktur `.xlsx`/`.csv` mit den beim Call genannten Blättern/Spalten;
      Excel-**Eingabezellen hellgelb** (`FFF2CC`) einfärben (Gelb-Konvention).
- [ ] Zwilling **erzeugen** (immer mit `--seed`, damit die Demo reproduzierbar bleibt):
      ```bash
      cd C:\Users\botrunner\projects\synthetic-data-creator
      python synth.py --from <kunden_struktur>.xlsx --seed 42        # Excel: Formeln/Blätter bleiben
      python synth.py --from <stammdaten>.csv --rows 300 --seed 42   # CSV: Personen erfunden, Zahlen plausibel
      ```
- [ ] **Formel-Check:** synthetische XLSX öffnen, in eine Ergebniszelle klicken → dort steht `=…`, kein
      hart kodierter Wert. (Ein CFO klickt in die Zahlen.)

### Schritt 3 · Umbranden — Schicht A + Schicht B  ⚠ *berührt `prototype/` → erst nach Gate B→C*

**3a — Schicht A: `pilot.config.js`** (Schema in [PILOT_CONFIG_SPEC.md §4](PILOT_CONFIG_SPEC.md)):

- [ ] `window.PILOT_CONFIG` mit `active:true`, `company` (name/tagline/logoGlyph/facts/people),
      `industry` und **genau 3** `scenarios`-IDs (aus Schritt 1) anlegen.
- [ ] Optional `accent` (CSS `--accent`) und `corpus`-Zeiger. Alles synthetisch.

**3b — Schicht B: Korpus in `data.js`** ([SYNTHETIC_DATA_PIPELINE.md Schritt 3](SYNTHETIC_DATA_PIPELINE.md)):

- [ ] Je Kunden-Dokument einen `DOCS`-Eintrag anlegen (Feldschema aus den bestehenden Belegen kopieren):
      `title, type, module, path, author, date, snippet, body[]`, optional **`lineItems`** — hier fließen
      die synthetischen Excel-Zahlen ein, damit die Beträge im Beleg-Skin aufaddieren.
- [ ] Token-Konvention beachten: neue synthetische Dokumente schreiben `{{COMPANY}}` statt eines Klarnamens
      ([PILOT_CONFIG_SPEC.md §5](PILOT_CONFIG_SPEC.md)) → kein Wiederholen der 55-Vorkommen-Falle.
- [ ] Die 3 gewählten Szenarien in `SCENARIOS` mit den neuen Belegen verdrahten (Money-Shot bleibt Finale).

> **Reine Daten-/Config-Arbeit, kein `app.js`-Umbau.** Das Wiring der Config (Guard in `data.js`,
> `applyPilotChrome()` in `app.js`) ist **einmalig** nach [PILOT_CONFIG_SPEC.md §5](PILOT_CONFIG_SPEC.md)
> zu implementieren — ebenfalls erst nach Gate B→C.

### Schritt 4 · Verifizieren (deterministisch, wie in jedem Zyklus)

- [ ] `node --check prototype/data.js` (und `app.js`, falls Wiring geändert) — Syntax grün.
- [ ] Node-VM-Zählung: Doc-/Szenarien-Zahl, **0 kaputte Referenzen** über `sources`/`related`/`lineItems`,
      Zitate wortgleich im `body`, Relevanzen 0–100.
- [ ] **Arithmetik der `lineItems`** nachrechnen (Netto = Σ Positionen; Brutto = Netto × 1,19).
- [ ] `active:false`/fehlende Config → **bit-identische** Meridian-Demo (Regressionsschutz fürs Video).
- [ ] Live im Browser: Kundenname in Titel/Firmenkarte/Hero/Bibliothek/Briefing/Suche; 3 Szenarien lösen
      belegt auf; Money-Shot als Finale; **keine Konsolenfehler**.

### Schritt 5 · Übergabe an den Kunden + nächster Schritt

- [ ] Demo dem Kunden zeigen/senden (buildfrei, `index.html`).
- [ ] Preis-Pfad aus dem One-Pager anschließen: **Audit 149 € → Wissensbasis ab 5.000 € → Agent-Abo ab
      400 €/Monat**.

---

## 5. Master-Checkliste (kopierbar, ein Pilot = eine Kopie)

```
PILOT: ____________________   Branche: __________   Datum Call: __________

[ ] 0  Audit-Call: Name · Branche · 3 Schmerzpunkte · Dokumenttypen+Ablage  (One-Pager gezeigt)
[ ] 1  3 Szenario-IDs gewählt: __________ / __________ / __________   (+ agent-dazubuchen Finale)
[ ] 2  Muster-Struktur gebaut (Eingaben gelb)  →  synth.py --from … --seed 42  →  Formel-Check ok
[ ] 3a pilot.config.js: active:true · company · industry · genau 3 scenarios          [nach Gate B→C]
[ ] 3b data.js: DOCS[] je Kundendokument (+lineItems) · {{COMPANY}}-Token · 3 Szenarien [nach Gate B→C]
[ ] 4  node --check grün · 0 kaputte Refs · Arithmetik · active:false=Meridian · live ok
[ ] 5  Demo übergeben  ·  Preis-Pfad angeschlossen (149 € → 5.000 € → 400 €/Mon.)
```

---

## 6. Zeit-Budget (Netto-Handaufwand, nicht die 48-h-Wanduhr)

| Schritt | Aufwand | Werkzeug |
|---------|--------:|----------|
| 0 · Audit-Call | 30 min | One-Pager |
| 1 · Szenarien wählen | < 5 min | SCENARIO_LIBRARY (Startvorlage) |
| 2 · Synth. Zwilling | 30–90 min | synthetic-data-creator |
| 3 · Umbranden (A+B) | 60–120 min | pilot.config.js + data.js |
| 4 · Verifizieren | 15–30 min | node --check + Browser |
| **Summe** | **~2–4 h** | — |

Die 48 h sind bewusst großzügig — sie geben Puffer für Rückfragen und lassen die Umsetzung ruhig laufen.

---

## 7. Definition of Done (ein Pilot ist „fertig", wenn …)

- [ ] Kundenname/-branche/-glyph erscheinen in der **gesamten Shell**, **kein** verbliebenes „Meridian".
- [ ] **Genau 3** Schmerz-Szenarien lösen **belegt** auf (Quelle · Konfidenz · Nachvollziehbarkeit).
- [ ] Mindestens ein Beleg mit **funktionierender `lineItems`-Arithmetik** (der CFO-Klick-in-die-Zahl-Moment).
- [ ] **Money-Shot** `agent-dazubuchen` schließt die Demo ab (Abo-Verkauf).
- [ ] `node --check` grün, **0 kaputte Referenzen**, `active:false` ⇒ bit-identische Meridian-Demo.
- [ ] **Kein** echter Kundenname, **kein** Logo-Bild im Repo — 100 % synthetisch.

---

## 8. End-to-End-Probelauf „Muster Bau GmbH" — *Protokoll (nach Gate B→C auszufüllen)*

> Dieser Abschnitt bleibt bis zum Freigabe-Gate ein **Platzhalter**. Sobald Sven das Video freigegeben hat
> (Gate B→C), wird der Prozess aus §4 **einmal vollständig** für einen fiktiven Kunden ausgeführt und hier
> protokolliert — jede Reibung notiert, nur **blockierende** Reibung sofort behoben (so die Mission).

Geplanter Testkunde (aus [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) / [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md)):

- **Firma:** Muster Bau GmbH — Hoch- & Tiefbau, Region Süd (Glyph `▲`, Akzent `#1f6feb`).
- **3 Szenarien (Branche Bau):** `materialkosten` → `projekt-beta` → `vorstand-summary` (+ Money-Shot).
- **Synthetische Eingaben:** Monats-Controlling (mehrblättrig, Formeln), Eingangsrechnungen (CSV),
  Rahmenverträge (CSV) — je `--seed 42`.

> **Vorab-Kohärenz-Audit (2026-07-10, freeze-konform) — startet §8 warm.** Bevor das Gate offen ist, wurden
> die beiden bereits gestageten Probelauf-Hälften (`pilot-assets/muster-bau-gmbh/` — Schicht A Config +
> Schicht B Zwilling) **gegeneinander** geprüft. Drei nicht-blockierende Lücken sind vorab protokolliert (Details:
> [pilot-assets/muster-bau-gmbh/README.md](pilot-assets/muster-bau-gmbh/README.md) → „Vorab-Kohärenz-Audit"):
> (1) **Korpus-Checkliste für Schritt 3:** die 3 Szenarien ziehen **12 verschiedene** Belege heran — der
> gestagete Controlling-`.xlsx` ist **1 von 12**; die übrigen 11 (Rechnung · 2 E-Mails · Rahmenvertrag ·
> Q1-Bericht · 2 Projektberichte · Eskalations-Mail · Nachtrag · Auftragsbestätigung · Vorstandsprotokoll ·
> ESG-Bericht) sind im gated Schritt 3 zu erzeugen/umzuschreiben. (2) **Personen-Regel:** die 6 synthetischen
> Namen der Config müssen dabei die heutigen **Meridian**-Personen 1:1 ersetzen (heute in 0 Artefakten). (3) Die
> oben genannten CSV-Zwillinge sind **noch nicht gestaged** (entstehen in Schritt 3). Die Protokoll-Tabelle
> unten bleibt bis Gate B→C **Platzhalter**.

| Schritt | Ergebnis | Reibung | behoben? |
|---------|----------|---------|----------|
| 0 Audit-Call (simuliert) | _offen_ | | |
| 1 Szenarien | _offen_ | | |
| 2 Synth. Zwilling | _offen_ | | |
| 3 Umbranden A+B | _offen_ | | |
| 4 Verifizieren | _offen_ | | |
| 5 Übergabe | _offen_ | | |

**Mission-Abschluss:** ist dieser Probelauf durchgeführt und protokolliert, ist die Pilot-Sprint-Mission
komplett → `MISSION_COMPLETE` in [PROGRESS.md](PROGRESS.md).

---

## 9. Grenze zum Feature-Freeze (ausdrücklich)

- **Diese Datei = reine Doku/Playbook**, ändert `prototype/` **nicht**. Verifiziert 2026-07-09:
  `git status` sauber vor dem Schreiben, `node --check` (app.js + data.js) grün.
- **Schritt 3 (pilot.config.js + data.js) und das Config-Wiring berühren `prototype/`** → **erst nach
  Gate B→C** (Svens Video-Aufnahme + Freigabe). Bis dahin steht hier nur der **dokumentierte Prozess**
  bereit, nicht seine Ausführung.
- Kommt eine **Anmerkung von Sven** zum Video/Prototyp → sie hat **Vorrang** vor jeder Phase-C-Arbeit.

---

*Erstellt 2026-07-09 · Phase C (Vorbereitung) · Playbook-Portion · reine Handover-Datei · `prototype/` unverändert.*
