# Pilot-Probelauf „Muster Bau GmbH" — Schritte 1+2 real ausgeführt

> **Phase C (Vorbereitung) · freeze-konform** (AI STUDIO — PILOT SPRINT MODE v2).
> Dieser Ordner liegt **außerhalb `prototype/`** — der Prototyp bleibt eingefroren (Gate B→C wartet auf Sven).
> Verwandt: [../../SYNTHETIC_DATA_PIPELINE.md](../../SYNTHETIC_DATA_PIPELINE.md) · [../../PILOT_KIT.md](../../PILOT_KIT.md)

## Wozu dieser Ordner

Die [SYNTHETIC_DATA_PIPELINE.md](../../SYNTHETIC_DATA_PIPELINE.md) beschrieb den Pilot-Workflow
**„Kunden-Dateistruktur rein → synthetischer Zwilling raus (Formeln intakt)"** — bislang aber nur als
**hypothetische** Beispieltabelle. Die Tool-Aufrufe waren nie gegen eine echte Bau-Controlling-Struktur
ausgeführt. Genau das war die größte unbewiesene Annahme im gesamten Phase-C-Plan.

**Dieser Ordner führt die Schritte 1 + 2 tatsächlich aus** (die *nicht*-gated Hälfte der Pipeline — Schritt 3,
das Laden in `prototype/data.js`, berührt `prototype/` und bleibt bis Gate B→C gesperrt). Ergebnis: die
dokumentierte Pipeline ist jetzt **ausgeführt und verifiziert**, nicht mehr nur beschrieben.

## Dateien

| Datei | Was |
|---|---|
| `build_input.py` | Baut die fiktive **Muster-Eingabedatei** (Schritt 1) reproduzierbar: mehrblättriges Bau-Controlling mit Gelb-Konvention (`FFF2CC`) auf echten Eingaben und blattübergreifenden Formeln (`=Annahmen!B5`). |
| `muster-bau-controlling_vorlage.xlsx` | Die erzeugte Eingabe („Kunden-Dateistruktur rein"). 2 Blätter: **Annahmen** + **Monatsabschluss Mai**. |
| `muster-bau-controlling_vorlage_testdaten.xlsx` | Der **synthetische Zwilling** (Schritt 2), erzeugt vom `synthetic-data-creator` mit `--seed 42`. |
| `pilot.config.js` | Die **Schicht-A-Konfiguration** (Umbranding) für denselben Probelauf-Kunden — vollständige `window.PILOT_CONFIG` nach [../../PILOT_CONFIG_SPEC.md](../../PILOT_CONFIG_SPEC.md) §4. 100 % synthetisch; **nicht in `prototype/` verdrahtet** (Wiring gated bis Gate B→C). Die 3 Szenarien sind gegen `data.js` verifiziert. |

## Ausgeführte Befehle (2026-07-09)

```bash
# Schritt 1 — Eingabe formen (fiktiv, kein echtes Kundendokument)
cd pilot-assets/muster-bau-gmbh
python build_input.py                       # -> muster-bau-controlling_vorlage.xlsx

# Schritt 2 — synthetischen Zwilling erzeugen (Reuse des bestehenden Tools, 43/43 Tests)
cd C:\Users\botrunner\projects\synthetic-data-creator
python synth.py --from <…>/muster-bau-controlling_vorlage.xlsx --seed 42 \
       -o <…>/muster-bau-controlling_vorlage_testdaten.xlsx
```

## Verifikationsergebnis (deterministisch, openpyxl)

**Formelerhalt — 12/12 Formeln bit-genau erhalten**, inklusive der 3 blattübergreifenden:

| Zelle | Formel (Original = Zwilling) |
|---|---|
| `Monatsabschluss Mai!E4…E9` | `=B4*D4` … `=B9*D9` (Positionssummen) |
| `E11` | `=SUM(E4:E9)` (Direktkosten netto) |
| `E12` | `=E11*Annahmen!B5/100` (Gemeinkostenumlage, **blattübergreifend**) |
| `E13` | `=E11*Annahmen!B6/100` (Materialaufschlag, **blattübergreifend**) |
| `E14` | `=E11+E12+E13` (Netto gesamt) |
| `E15` | `=E14*Annahmen!B4/100` (USt, **blattübergreifend** auf Konstante) |
| `E16` | `=E14+E15` (Bruttosumme) |

**Chirurgische Synthese — nur echte Eingaben ersetzt:**
- **12 von 14 gelben Eingabezellen** synthetisiert (Mengen/Einzelpreise/%-Annahmen; 2 unverändert:
  eine Pauschal-Menge `1` bleibt `1`, ein Einzelpreis fiel per Zufall auf denselben Wert — beides korrekt).
- **Gesetzliche Konstante USt = 19 % blieb unangetastet** (bewusst *nicht* gelb markiert — s. Lernpunkt).
- **Labels, Einheiten (`m3`, `t`, `h`), Blattnamen** unverändert.

**Modell rechnet weiter (Formelkette aus den synthetischen Eingaben nachgerechnet):**
- Direktkosten netto **237.409 €** → Netto gesamt **284.266,41 €** → Bruttosumme **338.277,03 €**.
- Probe **Brutto = Netto × 1,19 bestätigt**; Größenordnung plausibel (mittleres Bauprojekt).
- Ein CFO, der in `E16` klickt, sieht eine **lebende `=…`-Formel**, keinen hart kodierten Wert.

## Lernpunkte für echte Pilots (Friction-Log — keine blockierende Friction)

1. **Gesetzliche/feste Konstanten NICHT gelb markieren.** USt-Satz, feste Stundenverrechnungssätze etc.
   gehören in *nicht*-gelbe Zellen, sonst perturbiert sie die ±10 %-Heuristik (im Probelauf demonstriert:
   USt blieb 19 %, weil bewusst nicht gelb; die gelbe %-Annahme `8,5` wurde zu `8,737`). **Regel:** gelb =
   nur, was synthetisiert werden *soll*.
2. **Kleine Ganzzahlen (z. B. Pauschal-Menge `1`) bleiben stabil** — für „1 × Pauschalposten" ist das genau
   richtig, kein Bug.
3. **openpyxl rechnet Formeln nicht neu.** Der Formel-Check prüft die **Formel-Präsenz** (Zelle trägt `=…`);
   die *Werte* rechnet Excel/LibreOffice beim Öffnen neu. Für den deterministischen CI-Check die Formelkette
   wie hier in Code nachrechnen ODER die XLSX einmal in LibreOffice öffnen (`--convert-to`).
4. **`--seed` immer setzen** → zweite Ausführung liefert bit-identische Werte; die Demo bleibt zwischen
   Take und Kundentermin stabil.

## Schicht A — Config geschrieben (2026-07-09)

Nachdem Schritte 1+2 die **Schicht B** (synthetischer Korpus) real erzeugt haben, ist jetzt die **Schicht A**
(Umbranding-Config) für denselben Kunden konkret geschrieben: `pilot.config.js`. Damit sind **beide
freeze-konformen Hälften des Probelaufs** ausgeführt — Schicht B (Daten) *und* Schicht A (Chrome).
Deterministisch verifiziert (Node-VM gegen die Live-`data.js`):

- **Schema erfüllt:** `active:true`, `company` mit name/tagline/logoGlyph/facts/people, genau **3** Szenarien,
  `corpus`-Zeiger. `people`-Keys **deckungsgleich** mit `COMPANY.people`; `logoGlyph` = 1 Glyph; 4 Fakten.
- **3 Szenarien existieren** in `data.js` (`materialkosten` · `projekt-beta` · `vorstand-summary` = die
  Bau-Startvorlage aus SCENARIO_LIBRARY); Money-Shot `agent-dazubuchen` **nicht** in der Liste (bleibt Finale).
- **Faktenkorrektur:** die Beispiel-IDs der Spec (`rechnungspruefung-donau`, `liquiditaet-90-tage`) existieren
  **nicht** — die real gewählten IDs sind gegen `SCENARIOS` geprüft.
- **Kein Meridian-Leak**, alle Werte synthetisch; Firmenname weicht ab. `node --check` grün.

## Was noch fehlt (gated bis Gate B→C)

**Schritt 3** — die synthetischen Zahlen redaktionell in `prototype/data.js` als `DOCS`/`lineItems`
übertragen — **und das Config-Wiring** (Script-Tag + `COMPANY`-Guard + `applyPilotChrome()`, s.
PILOT_CONFIG_SPEC §5) berühren `prototype/` und sind **bis zu Svens Video-Freigabe gesperrt**. Dieser Ordner
liefert den **verifizierten Input** (Korpus **und** Config); die eigentliche Übertragung + der
End-to-End-Probelauf am Prototyp werden in [PILOT_KIT.md](../../PILOT_KIT.md) §8 protokolliert, sobald das
Gate offen ist.

---

*Erstellt 2026-07-09 · Phase C (Vorbereitung) · Schritte 1+2 real ausgeführt · `prototype/` unverändert.*
