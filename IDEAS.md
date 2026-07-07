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
- **ESG/CO₂-Szenario** — vorhandenen `Nachhaltigkeitsbericht` in ein Szenario einbinden,
  zeigt Breite über Finanz/Audit hinaus. *(Nächster Zyklus.)*
- **Onboarding-Overlay** beim ersten Start — ein Satz + Pfeil auf das Eingabefeld.
- **Sanfte Zahlen-Animation** — Konfidenz-Meter und Relevanz-% zählen hoch (Politur).

## Mehr Substanz
- 2–3 weitere Szenarien: HR-Onboarding-Frage, ESG/CO₂-Frage, Lieferanten-Risiko.
- Pro Dokument ein Miniatur-Thumbnail in der Bibliothek (SVG-Icon je Typ).
- Eine „Diese Antwort exportieren"-Schaltfläche (kopiert Antwort + Quellen).
- Zeitstempel/„Antwort in 1,2 s" als kleines Performance-Signal.

## Vertrauen sichtbar machen
- Badge „Nur Dokumente, für die Sie berechtigt sind" bei Antworten sichtbarer platzieren
  (knüpft an die Permission-faithful-Kernidee der Plattform an).
- Ein bewusst „gesperrtes" Dokument, das ein anderer Nutzer sähe — zeigt, dass Rechte
  respektiert werden (Story: „ich sehe nur, was ich darf").

## Nice-to-have
- Umschalter Sprache DE/EN für internationale Kunden.
- Dark-Mode (nicht fürs Video, aber für Live-Demos in dunklen Räumen).
- Firmen-Rebranding per einer Konfig-Zeile (Name/Logo/Farbe) für kundenspezifische Demos.
