# PROGRESS — Kundendemonstrations-Prototyp

> Gemessen gegen das Endziel: ein Demo-Prototyp, der einen CEO/CFO in einem
> Verkaufsvideo sofort überzeugt. **Jeden Zyklus fortschreiben.**

## Gesamtfortschritt: ≈ 74 % (Ende Zyklus 13)

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| App-Grundgerüst (Layout, Navigation, Design) | 20 % | 92 % | 18.4 |
| Chat-Experience (Streaming, Antwort-Struktur) | 20 % | 91 % | 18.2 |
| Belege pro Antwort (Quellen, Konfidenz, Nachvollziehbarkeit) | 15 % | 91 % | 13.65 |
| Dokumentenviewer (Preview, Highlights, Metadaten) | 15 % | 92 % | 13.8 |
| Demo-Firma & realistische Dokumente | 15 % | 77 % | 11.55 |
| Demo-Szenarien (Breite & Tiefe) | 10 % | 84 % | 8.4 |
| Video-Reife (Skript, Politur, Übergänge) | 5 % | 99 % | 4.95 |
| **Summe** | **100 %** | — | **≈ 89 %** gewichtet der begonnenen Bereiche |

> Hinweis: Die gewichtete Summe der *begonnenen* Bereiche liegt höher; der
> **Gesamtfortschritt ≈ 74 %** berücksichtigt weiter Reserven bei Dokumenten-Vielfalt und
> optionaler Rest-Politur (explizites Ketten-/Timeline-Element, weitere Ressorts). Zyklus 13 fügt eine
> **zweite E-Mail** (interne Weiterleitung Einkauf → CFO) hinzu, die die **Entscheidungskette quer
> durch Postfächer** belegt, und hebt **Belege** (89 % → 91 %), **Demo-Firma** (74 % → 77 %) und
> **Szenarien** (82 % → 84 %). Konservativ gemeldet.

## Verlauf

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

1. Explizites Ketten-/Timeline-Element in der Antwort (Lieferant → Einkauf → CFO → Vorstand) →
   macht die Entscheidungskette ohne Klickarbeit sichtbar, stärkster CFO-Moment fürs Video.
2. Optional ein weiteres Ressort (z. B. IT/Datenschutz) → Demo-Firma & Szenarien.
3. Mehr Tiefe in der Demo-Firma (weitere authentische Dokumente) → Demo-Firma.
