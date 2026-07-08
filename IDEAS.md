# IDEAS — Prototyp-Verbesserungen

> Ideen, die die **Kundendemonstration** besser machen. Priorisierung steuert
> [OPEN_ITEMS.md](OPEN_ITEMS.md). Alles, was Enterprise-Architektur/Skalierung/
> Framework betrifft, gehört in [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md), nicht hierher.

## Hohe Wirkung fürs Video
- ✅ **Dokument-Skins im Viewer** — *erledigt in Zyklus 2*: Briefkopf, Beleg-/Prüf-Stempel,
  Vertrags-Unterschriftszeilen, Klausel-Marken, Highlights im Layout.
- ✅ **„Guided Demo"-Modus** — *erledigt in Zyklus 3*: Play-Button in der Topbar spielt alle
  7 Szenarien hands-free ab (Frage tippen → Antwort → Lesepause), Fortschritt „n / 7", stoppbar.
- ✅ **Rechnungs-Positionstabelle** — *erledigt in Zyklus 4*: echte Positionszeilen (Menge ·
  Einzelpreis · Summe) + Netto/USt/Brutto-Fußzeile für Rechnung/Bestellung/Wareneingang;
  optionales `doc.lineItems`-Feld, Fallback = Text. Drei-Wege-Abgleich prüfungsecht.
- ✅ **ESG/CO₂-Szenario** — *erledigt in Zyklus 5*: 8. Szenario mit CO₂-Trend-Tabelle
  (2020→2025→Ziel 2030) und ehrlicher Lücken-Offenlegung; neues Doc „Energie- &
  Emissionskennzahlen 2025"; ESG-Bericht vertieft. Breite über Finanz/Audit hinaus.
- ✅ **Onboarding-Overlay** beim ersten Start — *erledigt in Zyklus 6*: Coachmark oben rechts,
  Pfeil auf den pulsierenden „Geführte Demo"-Button, Primär-CTA startet die Demo direkt; nur
  einmal (localStorage), Esc/Backdrop/Skip schließen.
- ✅ **Vertrauens-Story** — *erledigt in Zyklus 7*: 2 gesperrte Dokumente (Schloss, ausgegraut,
  „Kein Zugriff") + „Zugriff verweigert"-Ansicht; neues 9. Szenario mit „2 weitere Treffer für
  Sie nicht freigegeben"-Signal (`appendWithheld()`).
- ✅ **„Antwort in X s"-Signal + Zahlen-Count-up** — *erledigt in Zyklus 8*: „⚡ Beantwortet in
  1,9 s" im Antwortkopf (zählt hoch) + fett gesetzte Kernzahlen zählen hoch (`animateCounts()`,
  sicher gegen Jahre/Datum/PO-Nummern). Tempo/Souveränität fürs Video.
- ✅ **Handlungs-Abschluss „An Vorstand senden" / „Als Briefing exportieren"** — *erledigt in
  Zyklus 10*: Aktions-Block „↗ Ergebnis weiterreichen" unter jeder belegten Antwort; Klick →
  Spinner → grüne Erfolgs-Bestätigung mit ✓-Badge + deterministischer Briefing-Nummer. Reine UI.
- **Konfidenz-/Relevanz-Meter mit-animieren** — die Prozent-Balken (Konfidenz, Relevanz je
  Quelle) beim Einblenden von 0 hochlaufen lassen, passend zum Zahlen-Count-up. *(Optional.)*
- **Sanfte, gestaffelte Übergänge** beim Einblenden der Antwortblöcke + Modulwechsel (Fade/Slide,
  ~40–60 ms versetzt, `prefers-reduced-motion`) → nächstes oberstes Item.

## Mehr Substanz
- ✅ **HR-Onboarding & Lieferanten-/Klumpenrisiko** — *erledigt in Zyklus 9*: zwei neue Szenarien +
  Dokumente (Onboarding-Checkliste, Lieferanten-Risikoanalyse mit Konzentrations-Tabelle),
  verzahnt mit der Stahl-/Ferro-Nord-Story. „Geführte Demo" 9 → 11.
- Weiteres Szenario: Investitions-/Cashflow-Frage; optional ein IT-/Datenschutz-Ressort.
- Pro Dokument ein Miniatur-Thumbnail in der Bibliothek (SVG-Icon je Typ).
- ✅ **„Diese Antwort exportieren / An Vorstand senden"** — *erledigt in Zyklus 10* (Handlungs-
  Abschluss der Story, reine UI-Bestätigung).
- ✅ Zeitstempel/„Antwort in X s" — *erledigt in Zyklus 8* (Tempo-Signal im Antwortkopf).

## Vertrauen sichtbar machen
- ✅ Ein bewusst „gesperrtes" Dokument + „für Sie nicht freigegeben"-Signal — *erledigt in
  Zyklus 7* (Story: „ich sehe nur, was ich darf").
- Badge „Nur Dokumente, für die Sie berechtigt sind" auch bei den anderen Antworten sichtbarer
  platzieren (aktuell nur im Governance-Szenario prominent).
- Nutzer-Umschalter „Als Sachbearbeiter / als Vorstand ansehen" — dieselbe Frage, andere
  Freigaben: der gesperrte Treffer wird für den Vorstand sichtbar. Sehr starker Live-Demo-Moment.

## Nice-to-have
- Umschalter Sprache DE/EN für internationale Kunden.
- Dark-Mode (nicht fürs Video, aber für Live-Demos in dunklen Räumen).
- Firmen-Rebranding per einer Konfig-Zeile (Name/Logo/Farbe) für kundenspezifische Demos.
