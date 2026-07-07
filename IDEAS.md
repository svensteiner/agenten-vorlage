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
- **Sanfte Zahlen-Animation** — Konfidenz-Meter und Relevanz-% zählen hoch (Politur). *(Nächster Zyklus.)*
- **„Antwort in X s"-Signal** im Antwortkopf — Tempo/Souveränität fürs Video. *(Nächster Zyklus.)*

## Mehr Substanz
- 2–3 weitere Szenarien: HR-Onboarding-Frage, Lieferanten-Risiko, Investitions-/Cashflow-Frage.
- Pro Dokument ein Miniatur-Thumbnail in der Bibliothek (SVG-Icon je Typ).
- Eine „Diese Antwort exportieren"-Schaltfläche (kopiert Antwort + Quellen).
- Zeitstempel/„Antwort in 1,2 s" als kleines Performance-Signal.

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
