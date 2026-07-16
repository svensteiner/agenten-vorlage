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

## Vorab-Kohärenz-Audit Schicht A ↔ Schicht B (2026-07-10)

Bisher waren beide Hälften **je für sich** verifiziert (Config gegen `data.js`; Zwilling gegen openpyxl).
Neu: die beiden Hälften **gegeneinander** und gegen das, was die Config **verspricht**, geprüft — der Winkel,
der die gated §8-Übertragung sonst kalt getroffen hätte. Deterministisch (Node-VM gegen `data.js` +
openpyxl gegen beide `.xlsx`). **Drei nicht-blockierende Kohärenz-Lücken** — vorab protokolliert, damit
Schritt 3 nach Gate B→C nicht live entdeckt, sondern abgehakt wird:

1. **Korpus-Abdeckung: 1 Zwilling ⇄ 12 Quelldokumente.** Die 3 Pilot-Szenarien ziehen zusammen **12
   verschiedene** Belege heran (verifiziert):
   - `materialkosten` (5): `q1-bericht-2026`, `email-preisanpassung-donau`, `email-weiterleitung-materialbudget`, `rahmenvertrag-stahlwerk-donau`, `rechnung-2026-1843`
   - `projekt-beta` (4): `projekt-beta-status`, `eskalation-beta-elektronik`, `nachtrag-nordwind-beta`, `auftrag-nordwind-beta`
   - `vorstand-summary` (4, `q1-bericht-2026` geteilt): `projekt-alpha-status`, `vorstandsprotokoll-2026-03`, `esg-bericht-2025`

   Der bereits erzeugte Zwilling (`…_testdaten.xlsx`) deckt semantisch **nur die Zahlen von
   `materialkosten`** ab (Monatsabschluss/Materialkosten) — er ersetzt **keinen** dieser 12 Dokumentkörper.
   **Für Schritt 3 zu erzeugen:** synthetische Zwillinge (bzw. redaktionelle Umschriften) für **alle 12**
   (Rechnung · 2 E-Mails · Rahmenvertrag · Q1-Bericht · 2 Projektberichte · Eskalations-Mail · Nachtrag ·
   Auftragsbestätigung · Vorstandsprotokoll · ESG-Bericht). Der Controlling-`.xlsx` ist **1 von 12** — der
   klickbare Netto/USt/Brutto-Beleg für den Materialkosten-Beat.

2. **Personen-Versprechen unerfüllt (bis Schritt 3).** `pilot.config.js` deklariert **6** synthetische
   Personen und sagt, sie „tauchen im synthetischen Korpus (Schicht B) auf". **Sie tauchen aktuell nirgends
   auf:** im Zwilling-`.xlsx` **0** (nur Firmenname + Kostenarten), in `data.js` **0** Treffer. Umgekehrt
   tragen die 12 Quelldokumente heute die **Meridian**-Namen (z. B. CFO Dr. Katharina Vogel, Einkauf Thomas
   Krüger). **Schritt 3 muss die 6 synthetischen Namen aktiv in die 12 Zwillinge einsetzen**, sonst zeigt die
   Muster-Bau-Demo Meridian-Personen — genau der Leak, den die Pipeline verhindern soll. (Config-Kommentar
   entsprechend von „tauchen … auf" auf „**sollen** … auftauchen (via Schritt 3)" ehrlich gestellt.)

3. **§8-Eingabeliste läuft dem Staging voraus.** [PILOT_KIT.md](../../PILOT_KIT.md) §8 nennt als synthetische
   Eingaben u. a. „Eingangsrechnungen (CSV), Rahmenverträge (CSV)" — die sind **noch nicht gestaged** (dieser
   Ordner enthält nur den Controlling-`.xlsx`). Kein Widerspruch, nur eine **Reihenfolge-Notiz:** die CSV-
   Zwillinge (für `rechnung-2026-1843`, `rahmenvertrag-stahlwerk-donau`) entstehen erst im gated Schritt 3.

**Keine dieser Lücken ist blockierend** — alle drei liegen jenseits der Freeze-Grenze (Schritt 3 berührt
`prototype/`). Ergebnis des Audits: eine **konkrete 12-Dokument-Checkliste** + die Personen-Ersetzungs-Regel
stehen für die gated §8-Übertragung bereit, statt live entdeckt zu werden. `prototype/` unverändert;
Live-Daten unverändert (**29 Docs · 17 Szenarien**).

## Struktur-Zwillinge gestaged: Korpus-Abdeckung 1/12 → 3/12 (2026-07-14)

Der Audit oben legte die 12-Dokument-Checkliste an; **nur 1 von 12** war als Zwilling gestaged (die
Controlling-`.xlsx`). Dieser Zyklus staged die **beiden strukturierten/tabellarischen** Belege — genau die,
bei denen „klickbare Zahlen" für einen CFO zählen — als CSV-Zwillinge (die **nicht-gated** Pipeline-Hälfte,
Schritte 1+2; das Laden in `data.js` bleibt Schritt 3 / gated):

| Zwilling | Quelle | Was der Zwilling trägt |
|---|---|---|
| `rechnung-2026-1843_zwilling.csv` | `rechnung-2026-1843` | Positionstabelle **mit lebender Formelkette** netto = Menge × EP · USt = netto × 19 % · brutto = netto + USt (`73.600 → 13.984 → 87.584 €`) |
| `rahmenvertrag-stahlwerk-donau_zwilling.csv` | `rahmenvertrag-stahlwerk-donau` | Klausel-Tabelle §9 Laufzeit · §6 Preisgleitklausel · §12 Gewährleistung, identitäts-bereinigt |
| `build_corpus_twins.py` | — | reproduzierbarer Generator **mit Self-Check** (Formelkette exakt + kein Meridian-Leak) |

**Personen-Regel (Gap 2) erstmals konkret angewandt & verifiziert:** die internen Meridian-Personen der
Quelldocs sind 1:1 durch die synthetischen `pilot.config.js`-Namen ersetzt — **Thomas Krüger → Jürgen Kessler**
(Einkauf), **Dr. Elena Wagner → Dr. Stefan Reinhardt** (Recht), **Meridian Industrie GmbH → Muster Bau GmbH**;
der **externe** Lieferant *Stahlwerk Donau AG* bleibt (Gegenpartei, keine Meridian-Identität). Der Self-Check
bestätigt deterministisch: **0 Meridian-Leak**, alle drei synthetischen Namen present. Damit ist die vom Audit
als „unerfüllt" markierte Personen-Zusage in den strukturierten Zwillingen **erfüllt** (vorher: 0 Artefakte).

**Zahlen bewusst nicht perturbiert:** die Rechnungswerte stehen verbatim in zwei Szenario-Zitaten in `data.js`
(`materialkosten`, `rechnungspruefung`); eine Abweichung im Zwilling öffnete eine **neue** Kohärenz-Lücke. Die
optionale ±10 %-Synthese ist daher an Schritt 3 gekoppelt (Korpus **und** Szenario-Zitate zusammen umschreiben).
Der Zwilling trägt stattdessen die **Formelkette explizit** — klickbar & nachrechenbar.

**Verbleibt für Schritt 3 (gated):** die **9 Prosa-Belege** (2 E-Mails, Q1-/2 Projekt-/ESG-Bericht,
Eskalations-Mail, Nachtrag, Auftragsbestätigung, Vorstandsprotokoll) = redaktionelle Umschriften direkt in
`data.js`. Struktur-Abdeckung jetzt **3/12**; `prototype/` unverändert; Live-Daten unverändert (29 Docs · 17 Szenarien).

## Prosa-Zwillinge des Materialkosten-Szenarios gestaged: Abdeckung 3/12 → 6/12 (2026-07-15)

Die Struktur-Zwillinge deckten die tabellarischen Belege. Dieser Zyklus staged die **drei Prosa-Belege des
primären Pilot-Szenarios `materialkosten`** (1 Finanzbericht + 2 E-Mails) als identitäts-bereinigte
Text-Zwillinge — die **nicht-gated** Pipeline-Hälfte (Schritte 1+2; das Laden in `data.js` bleibt Schritt 3 /
gated). Damit ist `materialkosten` als **erstes** der 3 Pilot-Szenarien **vollständig** als Zwilling abgedeckt:

| Zwilling | Quelle | Was der Zwilling trägt |
|---|---|---|
| `q1-bericht-2026_zwilling.txt` | `q1-bericht-2026` | Quartalsbericht: Materialkostenanstieg **18,4 %**, Stahlpreis 780 → **920 €/t**, Donau-Preisanpassung 15 % (§6), Ferro-Nord-Gegenmaßnahme, Marge 34,1 → 31,6 % |
| `email-preisanpassung-donau_zwilling.txt` | `email-preisanpassung-donau` | Lieferanten-E-Mail: 15-%-Preisanpassung über §6, neuer Tonnenpreis **920 €**, inkl. zitiertem Verlauf |
| `email-weiterleitung-materialbudget_zwilling.txt` | `email-weiterleitung-materialbudget` | Interne Weiterleitung Einkauf → CFO: **0,9 Mio. €** Mehrbedarf, Vorstandsvorlage, Zweitlieferant |
| `build_prose_twins.py` | — | reproduzierbarer Generator **mit Self-Check** (Anker-Zahlen erhalten · kein Meridian-Leak · synth. Namen present · externe Gegenpartei behalten) |

**Personen-Regel angewandt & verifiziert:** interne Meridian-Personen 1:1 durch synthetische Namen ersetzt —
**Thomas Krüger → Jürgen Kessler** (Einkauf), **Dr. Katharina Vogel → Petra Hollmann** (CFO), plus die
interne **E-Mail-Domain** `meridian-industrie.example → muster-bau.example`; externe Gegenparteien
(*Andreas Huber* / *Stahlwerk Donau AG*, Zweitlieferant *Ferro Nord*) bleiben. Self-Check deterministisch:
**0 Meridian-Leak** (Firma, Personen, Domain), alle synth. Namen present, Anker-Zahlen je Datei erhalten.

**Neue Friction (für Schritt 3 / Config):** Der Weiterleitungs-Beleg trägt eine **7. interne Persona** —
*Sabine Reinhardt (Projektleitung Alpha)* —, für die `pilot.config.js` (6 Rollen: ceo/cfo/hr/procurement/
legal/audit) **keine Rolle** hat. Im Zwilling auf einen synthetischen Projektleitungs-Namen gemappt
(*Sandra Bergmann*; Nachname bewusst **≠** Reinhardt, um Kollision mit legal *Dr. Stefan Reinhardt* zu
vermeiden). **Empfehlung Schritt 3:** `pilot.config.js` um eine `projectLead`-Rolle erweitern, damit die
Persona aus der einen Config-Quelle stammt statt ad hoc erzeugt zu werden.

**Zahlen bewusst nicht perturbiert** (gleiche Kopplung wie bei den Struktur-Zwillingen: die Werte stehen
verbatim in Szenario-Antwort-Zitaten in `data.js` → ±10 %-Synthese an Schritt 3 gekoppelt).

**Verbleibt für Schritt 3 (gated):** die **6 restlichen Prosa-Belege** (2 Projektberichte · Eskalations-Mail ·
Nachtrag · Auftragsbestätigung · Vorstandsprotokoll · ESG-Bericht) = redaktionelle Umschriften direkt in
`data.js`. Abdeckung jetzt **6/12**; `prototype/` unverändert; Live-Daten unverändert (29 Docs · 17 Szenarien).

## Prosa-Zwillinge des Projekt-Beta-Szenarios gestaged: Abdeckung 6/12 → 10/12 (2026-07-16)

Nach `materialkosten` (vollständig) staged dieser Zyklus die **vier Belege des zweiten Pilot-Szenarios
`projekt-beta`** als identitäts-bereinigte Zwillinge — die **nicht-gated** Pipeline-Hälfte (Schritte 1+2;
das Laden in `data.js` bleibt Schritt 3 / gated). Damit ist `projekt-beta` als **zweites** der 3 Pilot-
Szenarien **vollständig** als Zwilling abgedeckt:

| Zwilling | Quelle | Was der Zwilling trägt |
|---|---|---|
| `projekt-beta-status_zwilling.txt` | `projekt-beta-status` | Projektbericht: Budget **8,6 Mio. €**, **48 %** / 3 Wo. Verzug, Elektronik-Lieferverzug, Change-Request +0,4 Mio. €, Pönale max. **0,43 Mio. €**, Liefertermin **Q4 2026** |
| `eskalation-beta-elektronik_zwilling.txt` | `eskalation-beta-elektronik` | Eskalations-E-Mail Projektleitung → CFO (Cc CEO): 6-Wochen-Verzug ElektroSys, Pönale-Risiko, Antrag Zweitquelle, inkl. zitiertem Zulieferer-Verlauf |
| `nachtrag-nordwind-beta_zwilling.txt` | `nachtrag-nordwind-beta` | Nachtragsangebot NA-2026-0037 + Positionstabelle (250k + 110k + 40k = **400.000 € netto** / USt 76.000 € / **476.000 € brutto**) |
| `auftrag-nordwind-beta_zwilling.txt` | `auftrag-nordwind-beta` | Auftragsbestätigung NW-BEST-2026-0091 (Nordwind beauftragt Nachtrag verbindlich, **400.000 € netto / 476.000 € brutto**) |
| `build_beta_twins.py` | — | reproduzierbarer Generator **mit Self-Check** (Anker-Zahlen erhalten · kein Meridian-Leak · synth. Namen present · externe Gegenparteien behalten) |

**Personen-Regel angewandt & verifiziert:** interne Meridian-Personen 1:1 durch synthetische Namen ersetzt —
**Dr. Katharina Vogel → Petra Hollmann** (CFO, `config.people.cfo`), **Markus Brandt → Andreas Moser**
(CEO, `config.people.ceo`), **Markus Feldmann → Tobias Lindner** (Projektleitung Beta, s. Friction), plus die
interne **E-Mail-Domain** `meridian-industrie.example → muster-bau.example`; **externe** Gegenparteien
(*Nordwind Logistik AG* als Kunde, *ElektroSys GmbH* als Zulieferer) bleiben. Self-Check **und** unabhängiger
`grep`: **0 Meridian-Leak** (Firma · Personen · Domain), alle synth. Namen present, Anker-Zahlen je Datei erhalten.

**Friction verschärft (für Schritt 3 / Config):** Der `materialkosten`-Batch fand eine 7. Persona
*Projektleitung Alpha* (Sabine Reinhardt → Sandra Bergmann) ohne Config-Rolle. Dieser Batch fügt eine **achte**
hinzu: *Projektleitung Beta* (Markus Feldmann → Tobias Lindner). Es gibt also **mehrere** Projektleitungen
(Alpha, Beta) → eine **einzelne** `projectLead`-Rolle in `pilot.config.js` reicht nicht. **Empfehlung Schritt 3:**
entweder eine Liste `projectLeads` oder projekt-scoped Einträge (`projectLeadAlpha` / `projectLeadBeta`).
Nachnamen bewusst kollisionsfrei zu den Config-Nachnamen (Moser/Hollmann/Baumgartner/Kessler/Reinhardt/Weiß/Bergmann).

**Zahlen bewusst nicht perturbiert** (gleiche Kopplung wie zuvor: die Werte stehen verbatim in den
`projekt-beta`-Szenario-Antwort-Zitaten in `data.js` → ±10 %-Synthese an Schritt 3 gekoppelt).

**Verbleibt für Schritt 3 (gated):** die **2 restlichen Prosa-Belege des `vorstand-summary`-Szenarios**
(Vorstandsprotokoll · ESG-Bericht; `projekt-alpha-status` wird dort ebenfalls herangezogen). Abdeckung jetzt
**10/12**; `prototype/` unverändert; Live-Daten unverändert (29 Docs · 17 Szenarien).

## Was noch fehlt (gated bis Gate B→C)

**Schritt 3** — die synthetischen Zahlen redaktionell in `prototype/data.js` als `DOCS`/`lineItems`
übertragen — **und das Config-Wiring** (Script-Tag + `COMPANY`-Guard + `applyPilotChrome()`, s.
PILOT_CONFIG_SPEC §5) berühren `prototype/` und sind **bis zu Svens Video-Freigabe gesperrt**. Dieser Ordner
liefert den **verifizierten Input** (Korpus **und** Config); die eigentliche Übertragung + der
End-to-End-Probelauf am Prototyp werden in [PILOT_KIT.md](../../PILOT_KIT.md) §8 protokolliert, sobald das
Gate offen ist.

---

*Erstellt 2026-07-09 · Phase C (Vorbereitung) · Schritte 1+2 real ausgeführt · `prototype/` unverändert.*
*Ergänzt 2026-07-10 · Vorab-Kohärenz-Audit Schicht A ↔ B (12-Dok-Checkliste + Personen-Regel).*
*Ergänzt 2026-07-14 · 2 Struktur-Zwillinge gestaged (Rechnung + Rahmenvertrag), Korpus-Abdeckung 1/12 → 3/12, Personen-Regel verifiziert.*
*Ergänzt 2026-07-15 · 3 Prosa-Zwillinge gestaged (Q1-Bericht + 2 E-Mails → `materialkosten` vollständig), Abdeckung 3/12 → 6/12, E-Mail-Domain-Regel + projectLead-Friction dokumentiert.*
*Ergänzt 2026-07-16 · 4 Prosa-Zwillinge gestaged (`projekt-beta` vollständig: Status + Eskalation + Nachtrag + Auftrag), Abdeckung 6/12 → 10/12, CEO/CFO-Ersetzung + 2. projectLead (Beta) → Config-Empfehlung `projectLeads`-Liste.*
