# SYNTHETIC_DATA_PIPELINE — vom Kunden-Ordner zum belegten Pilot-Demo

> **Phase C · Deliverable 3 von 5** (AI STUDIO — PILOT SPRINT MODE v2).
> Reine Handover-/Prozessdatei. **`prototype/` wird nicht verändert** (Feature-Freeze gewahrt).
> Verwandte Dateien: [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) · [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) ·
> [MISSION_PILOT_SPRINT.md](MISSION_PILOT_SPRINT.md).

## Wozu diese Datei

Das Pilot-Versprechen lautet: **„Wir brauchen kein einziges echtes Dokument von Ihnen."**
Nach einem 30-Minuten-Audit-Call zeigen wir dem Kunden binnen 48 h **seine eigene Demo** —
mit seinem Firmennamen, seinen Dokumenttypen, seinen Schmerz-Szenarien — auf **100 % synthetischen
Daten**, deren **Formeln weiter rechnen** (ein CFO klickt in die Zahlen hinein).

Diese Datei dokumentiert genau **einen** wiederholbaren Weg dorthin:

> **Kunden-Dateistruktur rein → synthetischer Zwilling raus (Formeln intakt) → in den Prototyp geladen.**

Das dafür genutzte Werkzeug existiert bereits und ist getestet — es wird **wiederverwendet**, nicht neu gebaut.

---

## Das Werkzeug (Reuse, nicht neu bauen)

**`C:\Users\botrunner\projects\synthetic-data-creator`** — eigenes, lokales Tool, **43/43 Tests grün**
(`python -m unittest test_synth`, verifiziert 2026-07-09: 43 `test_`-Funktionen in `test_synth.py`).

Was es kann (aus dessen `README.md` / `ANLEITUNG.md`):

| Fähigkeit | Bedeutung für den Pilot |
|---|---|
| **Personenbezug ersetzen** (Name, E-Mail, Adresse, Telefon) | Keine echten Personen in der Demo — DSGVO-sicher, verschickbar. |
| **Zahlen/Beträge/Datum/Ja-Nein sinnvoll erhalten** | Summen, Quoten und Auswertungen stimmen weiter — die Demo wirkt echt. |
| **Mehrblatt-Excel mit Formelerhalt** (auch blattübergreifend `=Annahmen!B5`) | Ein DCF-/Kalkulationsmodell rechnet nach dem Klonen unverändert weiter. |
| **Gelb-Konvention** (`FFF2CC`-Eingabezellen werden gezielt ersetzt) | Chirurgischer Eingriff: nur Eingaben synthetisch, Formeln/Labels unangetastet. |
| **CSV/JSON/XLSX/PDF** per Rechtsklick oder CLI | Deckt die üblichen SME-Formate ab (Controlling-Excel, Stammdaten-CSV, Rechnungs-PDF). |
| **Rückweg „Echtdaten einsetzen"** | Modell auf synthetischer Kopie bauen, später echte Werte zellgenau zurückspielen. |
| **100 % lokal** | Kein Upload, keine Cloud — passt zum „nichts verlässt das Haus"-Versprechen. |

**Betriebsmodi:**
- **Endkunde / kein Python:** ZIP entpacken → `INSTALLIEREN.bat` → **Rechtsklick auf Datei → „Testdaten erzeugen"**.
- **Entwicklung (unser Weg):** Python 3.10+, `pip install openpyxl pdfplumber fpdf2`, dann `python synth.py …`.

Wichtige CLI-Aufrufe (aus dem Tool-README):
```bash
python synth.py --from kunden.xlsx            # Mehrblatt-Excel klonen (Formeln bleiben)
python synth.py --from kunden.csv --rows 500  # CSV/JSON mit eigener Zeilenzahl
python synth.py name email age --rows 100 -o test.csv   # ganz ohne Vorlage
python synth.py --from kunden.xlsx --seed 42  # reproduzierbar (gleiche Demo bei jeder Erzeugung)
python synth.py --list                        # alle Feldtypen
```
Feldtypen u. a.: `id, name, email, phone, city, street, zip, company, job, date, price, int, float, bool, text`.

> **Tipp Reproduzierbarkeit:** Für Pilot-Demos immer `--seed` setzen. So erzeugt eine zweite Ausführung
> exakt dieselben synthetischen Werte — die Demo bleibt zwischen Take und Kundentermin identisch.

---

## Der Pilot-Workflow (4 Schritte, ~2–4 h Handarbeit)

### Schritt 0 — Beim Audit-Call einsammeln (kein Dokument nötig)

Wir brauchen **keine echten Dateien**, nur die **Form**:
- **Firmenname, Branche, Logo** (Logo optional, sonst Platzhalter).
- **Welche Dokumenttypen** liegen wo (Ordner? Postfach? ERP-Export?): z. B. „Controlling-Excel je Monat",
  „Eingangsrechnungen als PDF", „Rahmenverträge als Word/PDF", „Projektstatus als Excel".
- **3 Schmerz-Szenarien** aus der [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) auswählen
  (z. B. Bau → Materialkosten · Nachträge · Zahlungsstatus).
- **Grobe Kennzahlen-Bänder** (Umsatzgröße, Projektvolumina, Mitarbeiterzahl) — nur als Plausibilitäts-Rahmen.

> Ergebnis: eine **Struktur-Skizze**, kein einziges echtes Dokument. Das ist der Kern des Risiko-frei-Versprechens.

### Schritt 1 — Eingabe formen: „Kunden-Dateistruktur rein"

Zwei Wege, je nachdem, was der Kunde beim Call bereitstellt:

- **A) Kunde gibt eine (echte oder leere) Struktur-Datei mit** — z. B. sein Controlling-Excel-Template
  ohne die sensiblen Zahlen, oder mit echten Zahlen (wird ja gleich synthetisiert):
  → direkt in Schritt 2 als `--from`-Eingabe.
- **B) Kunde gibt nichts Digitales mit** (Normalfall) — wir bauen aus der Struktur-Skizze selbst eine
  **Muster-Eingabedatei**: ein Excel/CSV mit den genannten Spalten/Blättern und ein paar Beispielzeilen.
  Für Excel-Modelle die **Eingabezellen hellgelb** (`FFF2CC`) einfärben (Gelb-Konvention) → das Tool
  ersetzt später gezielt nur diese.

**Regel (aus der Tool-Anleitung):** Logik und Daten trennen — Werte in (gelbe) Eingabezellen, nie ein
fester Wert direkt in einer Formel; Eingabezeilen nicht verschieben. Dann bleibt der Formelerhalt zellgenau.

### Schritt 2 — Synthetischen Zwilling erzeugen: „synthetischer Zwilling raus"

```bash
cd C:\Users\botrunner\projects\synthetic-data-creator
python synth.py --from <kunden_struktur>.xlsx --seed 42     # Excel: alle Blätter + Formeln bleiben
python synth.py --from <stammdaten>.csv --rows 300 --seed 42  # CSV: Personendaten erfunden, Zahlen plausibel
```
Ergebnis: daneben liegt z. B. `<name>_testdaten.xlsx` / `_testdaten.csv`:
- Namen/E-Mails/Adressen **erfunden**,
- Beträge/Mengen/Datum **plausibel erhalten**,
- **Formeln und Zusatzblätter unverändert** → das Modell rechnet weiter.

**Kurz-Check (Formeln leben noch):** die synthetische XLSX in Excel/LibreOffice öffnen, in eine
Summen-/Ergebniszelle klicken — es steht eine `=…`-Formel drin, kein hart kodierter Wert.
(Diagramme/Pivots können in seltenen Fällen verloren gehen — dann meldet das Tool das.)

### Schritt 3 — In den Prototyp laden: „geladen in den Prototyp"

Der Prototyp rendert **ausschließlich** aus **`prototype/data.js`** — der einzigen Quelle der Wahrheit
(`DOCS` = Dokumentenbibliothek, `SCENARIOS` = Fragen/Antworten, `COMPANY`/`MODULES` = Rahmen).
Es gibt **keinen Datei-Upload**: die synthetischen Werte werden **redaktionell in `data.js` übertragen**.

Konkret je Kunden-Dokument einen Eintrag in `DOCS` anlegen (Feldschema aus den bestehenden Belegen kopieren):
- `title, type, module, path, author, date, snippet` — Metadaten (der `path` zitiert die Kunden-Ablage,
  z. B. `„SharePoint › Controlling › 2026 › Monatsabschluss_Mai.xlsx"`),
- `body[]` — die Absätze/Highlights, die im Viewer erscheinen (`highlight:true` hebt Belegstellen hervor),
- optional **`lineItems`** — eine echte Positionstabelle (Pos./Bezeichnung/Menge/Einzelpreis/Summe +
  Netto/USt/Brutto-Fußzeile). **Genau hier fließen die synthetischen Excel-Zahlen ein**, damit die
  Beträge im Beleg-Skin aufaddieren wie im Original.

> **Wichtig (Feature-Freeze):** Das ist eine **Daten**-Übertragung in `data.js`, kein Code-Umbau in
> `app.js`. Neue Dokumente/Szenarien = **nur `data.js` erweitern** (so der Prototyp-README). Während
> des Freeze bleibt dieser Schritt bewusst **außerhalb** von `prototype/` — er wird erst im
> **End-to-End-Probelauf nach Gate B→C** tatsächlich am Prototyp ausgeführt (siehe „Grenze zum Freeze").

**Umbranding (Name/Logo/Branche):** kommt über **PILOT_CONFIG** (Phase-C-Deliverable, berührt
`prototype/` → **erst nach Gate B→C** bauen). Bis dahin bleibt die Firma die fiktive „Meridian Industrie GmbH".

### Schritt 4 — Verifizieren (deterministisch, wie in jedem Zyklus)

Nach dem Eintragen in `data.js` (im Probelauf):
- `node --check prototype/data.js` — Syntax ok,
- Node-VM-Zählung: Doc-/Szenarien-Zahl, **0 kaputte Referenzen** über `sources`/`related`/`lineItems`,
  Zitate wortgleich im `body`, Relevanzen 0–100,
- **Arithmetik der `lineItems`** nachrechnen (Netto = Σ Positionen; Brutto = Netto × 1,19),
- live im Browser: Beleg öffnet mit korrektem Skin, Konfidenz-Kopf, Positionstabelle addiert korrekt.

---

## Ablaufdiagramm

```
Audit-Call (30 min)
   │  Firmenname · Branche · Dokumenttypen · 3 Schmerz-Szenarien   (KEIN echtes Dokument)
   ▼
[1] Eingabe formen  ──►  Muster-Struktur .xlsx/.csv (Eingabezellen gelb FFF2CC)
   │
   ▼
[2] synthetic-data-creator                python synth.py --from … --seed 42
   │   Personen erfunden · Zahlen plausibel · Formeln/Blätter intakt
   ▼
   <name>_testdaten.xlsx / _testdaten.csv   ◄── Formel-Check: Ergebniszelle trägt =…
   │
   ▼
[3] Übertragen in prototype/data.js       DOCS[…] { title,type,module,path,body[],lineItems }
   │   (reine Daten, kein app.js-Umbau) + 3 Szenarien aus SCENARIO_LIBRARY.md
   ▼
[4] Verifizieren  ──►  node --check · 0 kaputte Refs · Arithmetik · live im Browser
   │
   ▼
Kunde sieht binnen 48 h SEINE eigene, belegte Demo — inkl. Money-Shot „Agenten dazubuchen".
```

---

## Beispiel (Platzhalter für den Probelauf „Muster Bau GmbH")

| Kunden-Dokumenttyp | Eingabe (Schritt 1) | Tool-Aufruf (Schritt 2) | Prototyp-Eintrag (Schritt 3) |
|---|---|---|---|
| Monats-Controlling (Excel, mehrblättrig) | `controlling_vorlage.xlsx`, Eingaben gelb | `--from controlling_vorlage.xlsx --seed 42` | `DOCS["monatsabschluss-mai"]` mit `lineItems` (Kostenarten) |
| Eingangsrechnungen (PDF/CSV) | `rechnungen.csv` (Pos., Menge, Preis) | `--from rechnungen.csv --rows 40 --seed 42` | `DOCS["rechnung-…"]` + Drei-Wege-Abgleich |
| Rahmenverträge (Liste) | `vertraege.csv` (Partner, Laufzeit, Frist) | `--from vertraege.csv --rows 12 --seed 42` | `DOCS["rahmenvertrag-…"]`, Szenario „auto. Verlängerung" |

Der vollständige Probelauf wird in **PILOT_KIT.md** (Phase-C-Deliverable 5) protokolliert.

---

## Grenze zum Feature-Freeze (wichtig)

- **Diese Datei = reine Doku**, ändert `prototype/` **nicht**. Verifiziert 2026-07-09:
  `git status` sauber vor dem Schreiben, `node --check` (app.js + data.js) ok, Tool-Tests 43/43.
- **Schritt 3 (Eintrag in `data.js`) und PILOT_CONFIG berühren `prototype/`** → **erst nach Gate B→C**
  (Svens Video-Aufnahme + Freigabe). Bis dahin bleibt der Prototyp eingefroren; hier steht nur der
  **dokumentierte Prozess** bereit, nicht seine Ausführung.
- Kommt eine **Anmerkung von Sven** zum Video/Prototyp → die hat **Vorrang** vor jeder Phase-C-Doku.

## Nächste Phase-C-Bricks (Reihenfolge)

1. ✅ [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) — 17 Szenarien nach Schmerz/Branche.
2. ✅ [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md) — Angebotsdokument / Preis-Pfad.
3. ✅ **SYNTHETIC_DATA_PIPELINE.md** (diese Datei) — reine Doku, kein `prototype/`-Eingriff.
4. ⏳ **PILOT_CONFIG** — Umbranding-Mechanismus → **erst nach Gate B→C** (berührt `prototype/`).
5. ⏳ **End-to-End-Probelauf „Muster Bau GmbH" + PILOT_KIT.md** — sobald 3 + 4 stehen.

---

*Erstellt 2026-07-09 · Phase C (Vorbereitung) · reine Handover-Datei · `prototype/` unverändert.*
