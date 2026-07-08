# OPEN_ITEMS — priorisierte Aufgabenliste (Prototyp)

> Eine Liste, absteigend nach Wirkung auf die Kundendemonstration. Der nächste
> Zyklus nimmt das **oberste offene** Item. Erledigtes nach unten verschieben.

## Offen (nach Priorität)

1. **[P4] Export-/„An Vorstand senden"-Aktion** pro Antwort inkl. Quellen (Handlungs-Abschluss der
   Story; reine UI-Bestätigung/Toast, keine echte Mail). → oberstes Item für den nächsten Zyklus.
2. **[P4] Sanfte Übergänge** zwischen Modulwechseln/Antwortblöcken (Fade/Slide) — optionale
   Rest-Politur.
3. **[P5] Optional ein weiteres Ressort** (z. B. IT/Datenschutz) + 1 Dokument in `data.js`.

## Erledigt

- **[Zyklus 9] Ressort-Breite — HR-Onboarding & Lieferanten-/Klumpenrisiko** — zwei neue Szenarien
  + Dokumente (`onboarding-checkliste-2026`, `lieferanten-risikoanalyse-2026`). Onboarding-
  Checkliste-Antwort (Konfidenz 96 %) und Lieferanten-Konzentrations-Tabelle (Donau 23,9 % +
  Single-Source-Warnung, Konfidenz 94 %), verzahnt mit der Stahl-/Ferro-Nord-Story. Rein additiv in
  `data.js`; Hero 6 → 8, „Geführte Demo" 9 → 11. Live verifiziert (0 kaputte Referenzen).

- **[Zyklus 8] Video-Politur — Tempo/Souveränität** — „⚡ Beantwortet in X,X s"-Signal im
  Antwortkopf (zählt hoch, deterministisch 1,2–2,6 s) + dezentes Hochzählen der fett gesetzten
  Kernzahlen (`animateCounts()`/`parseGermanNumber()`, easeOutCubic). Sicher gegen
  Jahre/Datum/PO-Nummern; `prefers-reduced-motion` respektiert. Rein additiv. Live verifiziert.

- **[Zyklus 7] Vertrauens-Story** — 2 gesperrte Dokumente (M&A-Akquisitionsvorlage,
  Vorstandsvergütung) ausgegraut mit Schloss + „Kein Zugriff — <Rolle>" in der Bibliothek;
  Klick öffnet „Zugriff verweigert" statt Inhalt (kein Leak). Neues 9. Szenario
  „Wachstumsstrategie" mit Governance-Signal „2 weitere Treffer für Sie nicht freigegeben"
  (neuer `appendWithheld()`-Block, anklickbare gesperrte Treffer). Rein additiv. Live verifiziert.

- **[Zyklus 6] Onboarding-Overlay** beim ersten Start — leichtgewichtiges Coachmark oben
  rechts, Pfeil auf den pulsierenden „Geführte Demo"-Button, ein Satz + Primär-CTA, der das
  Overlay schließt und die Demo direkt startet. Nur einmal (localStorage), Esc/Backdrop/Skip
  schließen, `prefers-reduced-motion` respektiert. Rein additiv. Live verifiziert.

- **[Zyklus 5] ESG/CO₂-Szenario** — neues 8. Szenario „CO₂-Fußabdruck/ESG-Kurs?" mit
  Trend-Tabelle (2020→2025→Ziel 2030) und ehrlicher Lücken-Offenlegung; neues Doc
  „Energie- & Emissionskennzahlen 2025"; `esg-bericht-2025` von 2 auf 6 Absätze vertieft.
  Rein additiv in `data.js`; „Geführte Demo" 7 → 8 Szenarien. Live verifiziert.

- **[Zyklus 4] Rechnungs-Positionstabelle** — echte Buchungstabelle (Pos./Bezeichnung/Menge/
  Einzelpreis/Summe) + optionale Netto/USt/Brutto-Fußzeile für Rechnung/Bestellung/Waren-
  eingang, datengetrieben über optionales `doc.lineItems` (Fallback = Text). Prüfungsechter
  Drei-Wege-Abgleich; alle 3 Belege live verifiziert.
- **[Zyklus 3] „Geführte Demo" (hands-free Auto-Play)** — Play-Button in der Topbar spielt
  alle 7 Szenarien automatisch ab (Frage tippen → `ask()` → Lesepause → nächstes),
  Fortschritt „n / 7", jederzeit stoppbar, Composer während der Demo gesperrt.
- **[Zyklus 2] Dokument-Skins im Viewer** — Papierblatt + Briefkopf pro `doc.type`,
  Beleg-/Prüf-Stempel, Vertrags-Unterschriftszeilen, Klausel-Marken, Highlights im Layout.
- **[Zyklus 1] Prototyp-Grundgerüst** — App-Rahmen, Chat-Streaming, Belege/Quellen/
  Konfidenz, Dokumentenviewer, Demo-Firma + 15 Dokumente + 7 Szenarien, live getestet.

## Bewusst NICHT offen (gehört nicht in diese Mission)
- Echte Backend-Anbindung, echtes RAG/Embeddings, Auth, Skalierung, Framework-Arbeit.
  → alles in [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md). Der Prototyp bleibt eine
  self-contained Frontend-Demo.
