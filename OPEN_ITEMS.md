# OPEN_ITEMS — priorisierte Aufgabenliste (Prototyp)

> Eine Liste, absteigend nach Wirkung auf die Kundendemonstration. Der nächste
> Zyklus nimmt das **oberste offene** Item. Erledigtes nach unten verschieben.

## Offen (nach Priorität)

1. **[P1] ESG/CO₂-Szenario** — der `Nachhaltigkeitsbericht` existiert, wird aber von keinem
   Szenario genutzt. Neues Szenario „CO₂-Fußabdruck/ESG-Kurs?" in `data.js` (Antwort ·
   Nachvollziehbarkeit · Quellen aus ESG-Bericht + 1 Kennzahlen-Doc · Konfidenz ·
   Folgefragen). → beweist **Breite** über Finanz/Audit hinaus, adressiert Vorstands-/
   Aufsichtsratsthemen. Die „Geführte Demo" nimmt es automatisch auf.
2. **[P2] Onboarding-Overlay** beim ersten Start (ein Satz + Pfeil auf den Composer bzw.
   auf den „Geführte Demo"-Button).
3. **[P3] Weitere Szenarien** (HR-Onboarding, Lieferanten-Risiko) + passende Dokumente in
   `data.js`. (Die „Geführte Demo" nimmt neue Szenarien automatisch auf.)
4. **[P3] Vertrauens-Story sichtbar machen** — ein „gesperrtes" Dokument + Badge
   „Nur berechtigte Dokumente" prominenter.
5. **[P4] Politur** — Zahlen-Hochzähl-Animation (Konfidenz/Relevanz), sanftere Übergänge,
   „Antwort in X s"-Signal.
6. **[P4] Export-Button** für eine Antwort inkl. Quellen.

## Erledigt

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
