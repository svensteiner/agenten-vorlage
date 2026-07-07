# OPEN_ITEMS — priorisierte Aufgabenliste (Prototyp)

> Eine Liste, absteigend nach Wirkung auf die Kundendemonstration. Der nächste
> Zyklus nimmt das **oberste offene** Item. Erledigtes nach unten verschieben.

## Offen (nach Priorität)

1. **[P1] „Guided Demo"-Modus** — ein Play-Button, der die 7 Szenarien automatisch
   nacheinander abspielt (Frage tippen → Antwort → kurze Pause → nächstes). Perfekt für
   eine hands-free Videoaufnahme oder einen Messestand-Loop. → nächster Wow-Hebel.
2. **[P2] Onboarding-Overlay** beim ersten Start (ein Satz + Pfeil auf den Composer).
3. **[P2] Rechnungs-Positionstabelle** — Belege haben jetzt Briefkopf + Stempel; als
   Vertiefung eine echte **Positionszeilen-Tabelle** (Menge · Einzelpreis · Summe · USt)
   für Rechnung/Bestellung. Optionales `doc.lineItems`-Feld in `data.js`, Fallback = Text.
4. **[P3] 2–3 zusätzliche Szenarien** (HR-Onboarding, ESG/CO₂, Lieferanten-Risiko) +
   passende Dokumente in `data.js`.
5. **[P3] Vertrauens-Story sichtbar machen** — ein „gesperrtes" Dokument + Badge
   „Nur berechtigte Dokumente" prominenter.
6. **[P4] Politur** — Zahlen-Hochzähl-Animation (Konfidenz/Relevanz), sanftere Übergänge,
   „Antwort in X s"-Signal.
7. **[P4] Export-Button** für eine Antwort inkl. Quellen.

## Erledigt

- **[Zyklus 2] Dokument-Skins im Viewer** — Papierblatt + Briefkopf pro `doc.type`,
  Beleg-/Prüf-Stempel, Vertrags-Unterschriftszeilen, Klausel-Marken, Highlights im Layout.
- **[Zyklus 1] Prototyp-Grundgerüst** — App-Rahmen, Chat-Streaming, Belege/Quellen/
  Konfidenz, Dokumentenviewer, Demo-Firma + 15 Dokumente + 7 Szenarien, live getestet.

## Bewusst NICHT offen (gehört nicht in diese Mission)
- Echte Backend-Anbindung, echtes RAG/Embeddings, Auth, Skalierung, Framework-Arbeit.
  → alles in [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md). Der Prototyp bleibt eine
  self-contained Frontend-Demo.
