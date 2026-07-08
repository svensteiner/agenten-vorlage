# PROGRESS — Kundendemonstrations-Prototyp

> Gemessen gegen das Endziel: ein Demo-Prototyp, der einen CEO/CFO in einem
> Verkaufsvideo sofort überzeugt. **Jeden Zyklus fortschreiben.**

## Gesamtfortschritt: ≈ 67 % (Ende Zyklus 9)

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| App-Grundgerüst (Layout, Navigation, Design) | 20 % | 92 % | 18.4 |
| Chat-Experience (Streaming, Antwort-Struktur) | 20 % | 86 % | 17.2 |
| Belege pro Antwort (Quellen, Konfidenz, Nachvollziehbarkeit) | 15 % | 88 % | 13.2 |
| Dokumentenviewer (Preview, Highlights, Metadaten) | 15 % | 89 % | 13.35 |
| Demo-Firma & realistische Dokumente | 15 % | 70 % | 10.5 |
| Demo-Szenarien (Breite & Tiefe) | 10 % | 82 % | 8.2 |
| Video-Reife (Skript, Politur, Übergänge) | 5 % | 94 % | 4.7 |
| **Summe** | **100 %** | — | **≈ 86 %** gewichtet der begonnenen Bereiche |

> Hinweis: Die gewichtete Summe der *begonnenen* Bereiche liegt höher; der
> **Gesamtfortschritt ≈ 67 %** berücksichtigt weiter Reserven bei Dokumenten-Vielfalt und dem
> Handlungs-Abschluss (Export). Zyklus 9 hebt vor allem **Demo-Szenarien** (74 % → 82 %, zwei
> neue Ressorts) und **Demo-Firma** (62 % → 70 %, zwei neue Dokumente). Konservativ gemeldet.

## Verlauf

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

1. Export-/„An Vorstand senden"-Aktion pro Antwort (Handlungs-Abschluss der Story) → Chat-Experience
   & Video-Reife.
2. Sanfte Übergänge + weitere Beleg-Skins → Viewer/Video-Reife.
3. Optional ein weiteres Ressort (z. B. IT/Datenschutz) → Demo-Firma & Szenarien.
