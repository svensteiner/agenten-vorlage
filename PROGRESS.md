# PROGRESS — Kundendemonstrations-Prototyp

> Gemessen gegen das Endziel: ein Demo-Prototyp, der einen CEO/CFO in einem
> Verkaufsvideo sofort überzeugt. **Jeden Zyklus fortschreiben.**

## Gesamtfortschritt: ≈ 86 % (Ende Zyklus 21)

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| App-Grundgerüst (Layout, Navigation, Design) | 20 % | 95 % | 19.0 |
| Chat-Experience (Streaming, Antwort-Struktur) | 20 % | 93 % | 18.6 |
| Belege pro Antwort (Quellen, Konfidenz, Nachvollziehbarkeit) | 15 % | 96 % | 14.4 |
| Dokumentenviewer (Preview, Highlights, Metadaten) | 15 % | 95 % | 14.25 |
| Demo-Firma & realistische Dokumente | 15 % | 90 % | 13.5 |
| Demo-Szenarien (Breite & Tiefe) | 10 % | 93 % | 9.3 |
| Video-Reife (Skript, Politur, Übergänge) | 5 % | 100 % | 5.0 |
| **Summe** | **100 %** | — | **≈ 94 %** gewichtet der begonnenen Bereiche |

> Hinweis: Die gewichtete Summe der *begonnenen* Bereiche liegt höher; der
> **Gesamtfortschritt ≈ 86 %** berücksichtigt weiter Reserven bei Dokumenten-Vielfalt und
> optionaler Rest-Politur. Zyklus 21 fügt ein **zweites, ehrlich verzögertes Projekt (Beta)**
> hinzu und hebt **Demo-Firma** (86 % → 90 %) und **Szenarien** (92 % → 93 %).
> Konservativ gemeldet.

## Verlauf

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

## Was den Fortschritt als Nächstes hebt

1. **Konfidenz visuell erklären** — ein Tooltip/Hover am Konfidenz-Meter, der zeigt, *woraus* sich die
   Zahl speist (Quellenanzahl, höchste Relevanz, Übereinstimmung); macht die „belastbaren Belege"-Story
   noch greifbarer für skeptische CFOs. Klein, rein additiv (`app.js`/`styles.css`). **Jetzt stärkster
   Hebel**, da Demo-Firma mit Zyklus 19 auf 86 % gehoben ist.
2. **Mehr Tiefe in der Demo-Firma** (weitere authentische Dokumente) → z. B. ein zweites Projekt
   (neben Alpha), das eine Frage wie „Wie steht Projekt Beta?" belegt — hebt Demo-Firma **und**
   Szenarien-Breite.
3. Optional: die Entscheidungskette (`DECISION_CHAIN`) auch an die **Materialkosten-Antwort** hängen
   — Tiefe statt Breite; Video-Reihenfolge beachten (Kette erschiene zweimal, s. NEXT_STEPS).
