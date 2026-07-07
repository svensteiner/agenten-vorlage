# OPEN_ITEMS — priorisierte Aufgabenliste (Prototyp)

> Eine Liste, absteigend nach Wirkung auf die Kundendemonstration. Der nächste
> Zyklus nimmt das **oberste offene** Item. Erledigtes nach unten verschieben.

## Offen (nach Priorität)

1. **[P3] Politur — Tempo/Souveränität fühlbar machen** — „Antwort in X s"-Signal im
   Antwortkopf + dezentes Hochzählen der Kernzahlen (Konfidenz/Relevanz, Beträge, Prozente),
   sanftere Übergänge. → lässt das System im Video schnell und „live" wirken.
2. **[P3] Weitere Szenarien** (HR-Onboarding, Lieferanten-Risiko) + passende Dokumente in
   `data.js`. (Die „Geführte Demo" nimmt neue Szenarien automatisch auf.)
3. **[P4] Export-/„An Vorstand senden"-Button** für eine Antwort inkl. Quellen.

## Erledigt

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
