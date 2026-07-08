# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 17 — **Globale Live-Suche (Command-Palette)**: „🔍 Alles durchsuchen" in
  der Sidebar (+ Strg/⌘ + K) öffnet ein Modal, das live über alle 23 Dokumente filtert (Titel/Typ/
  Snippet/Autor/Modul) — der „Was steckt alles drin?"-Moment (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-08.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 81 %** (siehe [PROGRESS.md](PROGRESS.md)).

---

## ⚠ Wichtiger Kontext für den nächsten Zyklus

Das Repository hatte vor dieser Mission **31 Zyklen** ausschließlich `platform/`-
**Architektur-Dokumentation** produziert — genau die Themen, die die Prototyp-Mission
unter „DO NOT WORK ON" listet (Enterprise-Architektur, Security, Skalierung, Connector-/
Agenten-Framework). Der eigentliche **Kunden-Demo-Prototyp existierte nicht**.

**Regeln ab jetzt:**
- `platform/` und `core/` sind **geschütztes IP** → nicht verändern, nicht umbauen.
  (Die `platform/NEXT_STEPS.md` ist die Übergabe *jenes* Tracks und bleibt eingefroren.)
- Alle Prototyp-Arbeit passiert **additiv** in [`prototype/`](prototype/) + diesen
  Handover-Dateien im Repo-Wurzelverzeichnis.
- Jeden Zyklus **genau EINE** sichtbare Verbesserung am Prototyp.

---

## Was in Zyklus 17 gebaut wurde

**Globale Live-Suche über den gesamten Wissensspeicher (Command-Palette) — der lang offene
„Was steckt alles drin?"-Moment.** Die Demo hatte Breite (13 Szenarien, 23 Dokumente über 6 Ressorts),
aber der Betrachter *fühlte* die schiere **Menge** des erschlossenen Wissens noch nicht. Neu:
- **Sidebar-Auslöser „🔍 Alles durchsuchen"** (mit sichtbarem `Strg K`-Kürzel) direkt unter dem Logo;
  **Strg/⌘ + K** öffnet/schließt die Suche von überall, **Esc** schließt, Klick auf den Backdrop schließt.
- **Zentriertes Command-Palette-Modal** (Notion/Linear/Stripe-Anmutung): großes Suchfeld mit Autofocus,
  Live-Zähler und scrollbare Trefferliste. **Leeres Feld = komplettes Inventar** („23 Dokumente im
  Wissensspeicher — tippen zum Filtern"); beim Tippen filtert es **live** über
  **Titel/Typ/Snippet/Autor/Modul aller Dokumente** (Zähler „X von 23 für ‚…'").
- **Treffer-Zeilen** mit Datei-Icon (✉ für E-Mail), **Modul-Tag + Typ** rechts, Snippet einzeilig,
  und **gelb hervorgehobenem Suchbegriff** (`<mark>`, über eine sichere escape-dann-markieren-Helferin
  `hlMatch()`). **Tastatur:** ↑/↓ bewegt die Auswahl, **Enter** öffnet den markierten Treffer; Maus-Hover
  markiert ebenfalls. Klick/Enter schließt die Suche und öffnet den Beleg im **bestehenden Viewer**.
- **Governance bleibt konsistent:** gesperrte Dokumente erscheinen als Treffer (mit „🔒 Kein Zugriff"),
  öffnen aber die **„Zugriff verweigert"-Ansicht** (`paper-locked`, kein Inhalts-Leak). Während der
  Geführten Demo ist der Auslöser bewusst inaktiv (`if (demo.running) return`), damit nichts kollidiert.
- **Cross-Modul belegt:** eine „stahl"-Suche liefert Treffer aus **Finanzen und Audit** — sichtbar wird,
  dass ein Begriff quer durchs ganze Haus greift.
- **Rein additiv:** `index.html` (Auslöser + Overlay-Markup), `styles.css` (`.search-trigger`,
  `.search-ov`/`.search-panel`/`.sp-*`, reduced-motion-Guard) und `app.js` (`wireSearch()`/`openSearch()`/
  `closeSearch()`/`matchDocs()`/`renderSearchResults()`/`hlMatch()` u. a.); `data.js` und der Antwortpfad
  unverändert. Deterministisch verifiziert (Node-VM gegen `data.js`): **23 Dokumente**, Filter exakt
  (""→23, „stahl"→8, „vertrag"→4, „dsgvo"→2, „donau"→6, kein-Treffer→0), **0 Feld-Fehler**, 2 gesperrte
  Docs. Live im Browser gegen die realen Daten geprüft: Auslöser **und** Strg+K öffnen/schließen, 23
  Zeilen bei leerem Feld + korrekter Zähler, `<mark>`-Highlight vorhanden, ↓+Enter öffnet den Viewer
  (Titel „Bestellung PO-2026-0512" korrekt), gesperrter Treffer öffnet `paper-locked` ohne Leak, **keine
  Konsolenfehler**. (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM/CSS-basiert
  verifiziert.)

## Was in Zyklus 16 gebaut wurde

**DSGVO-/Datenschutz-Szenario — die Demo öffnet ein neues Entscheider-Ressort (Compliance/Datenschutz).**
Die Demo war bisher finanzlastig; die schwächsten Fortschrittsbereiche waren **Demo-Firma & Dokumente**
und **Szenarien-Breite**. Zyklus 16 hebt beide mit einem Thema, das jeden CEO/CFO betrifft — rein
additiv in `data.js`, kein Code-Umbau (bestehende Tabellen- und Skin-Renderer wiederverwendet):
- **Neues Szenario `datenschutz-audit`** (Modul Audit, Konfidenz 93 %): „Sind wir DSGVO-konform — wann
  war das letzte Datenschutz-Audit?" Antwort mit **Status-Tabelle** (5 Prüffelder: Art. 30 VVT,
  Art. 32 TOM, Art. 28 Auftragsverarbeitung, Betroffenenrechte/Löschkonzept, 72-h-Meldeprozess), je
  Status **✓** / **⚠ 1 offen**. **Ehrlich statt beschönigt:** zwei offene Auflagen (AV-Vertrag
  Cloud-Backup, Löschkonzept Bewerberdaten) mit klarer Frist **31.03.2026**, „kein akutes Bußgeldrisiko".
- **Zwei neue Dokumente** (Modul Audit):
  - **`datenschutz-audit-2025`** (Typ „Prüfnachweis" → grüner **BESTANDEN**-Stempel im Viewer): das
    jährliche DSGVO-Audit vom 20.11.2025, externe Datenschutzbeauftragte **Dr. Julia Sander**,
    8 Absätze / 6 Highlights (Ergebnis, VVT, TOM, beide Auflagen, Meldeprozess, 0 meldepflichtige
    Vorfälle 2025).
  - **`verarbeitungsverzeichnis-2026`** (Typ „Verzeichnis" → sauberer Fallback aufs Bericht-Skin,
    `paper-bericht`): Verzeichnis nach **Art. 30 DSGVO**, 34 Verarbeitungstätigkeiten, Rechtsgrundlagen
    und Löschfristen (Beschäftigten-/Bewerberdaten).
- **Verdrahtung:** Szenario nach `brandschutz` einsortiert → in der Geführten Demo laufen die beiden
  Audit-/Compliance-Beats direkt hintereinander (jetzt **13 Szenarien**). Hero (Modul Wissen) 9 → **10
  Kacheln**, `audit`-Modul-Vorschläge 2 → 3.
- **Rein additiv** in `data.js`; `app.js`/`styles.css`/`index.html` unverändert. Deterministisch
  verifiziert (Node-VM gegen `data.js`): **23 Dokumente** (war 21), **2 E-Mails**, **13 Szenarien**
  (war 12), **1 chain**, **0 kaputte Referenzen** über alle `sources`/`related`/`withheld`/`chain`/
  `MODULE_SUGGESTIONS`. Live im Browser gegen die realen Daten geprüft: DSGVO-Hero-Kachel vorhanden
  (10 Kacheln), beide neue Karten im Audit-Modul, Datenschutz-Audit öffnet als `paper-nachweis` mit
  **BESTANDEN**-Stempel + 6 Highlights, VVT öffnet als `paper-bericht` mit 3 Highlights, kein
  Ketten-Navigator bei den Nicht-Ketten-Docs, **keine Konsolenfehler**. (Voll-Streaming-Pfad der
  Antwort im Headless-Preview timer-gedrosselt, Screenshot-Capture im Harness instabil — bekannte
  Grenzen; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 15 gebaut wurde

**Ketten-Navigator im Dokumentenviewer — die Entscheidungskette ist jetzt auch beim Lesen der
Einzelbelege navigierbar (Option B aus Zyklus 14).** Zyklus 14 zeigte die Kette als Timeline im Chat;
öffnete man aber einen der drei Belege im Viewer, verlor man den Kontext „wo im Beleg-Pfad bin ich?".
Neu:
- **Kompakter Navigator oben im Viewer** — erscheint automatisch, sobald eines der drei Ketten-
  Dokumente geöffnet wird (Lieferanten-E-Mail → interne Weiterleitung → Vorstandsprotokoll). Zeigt
  **„⛓ Entscheidungskette · Schritt n von 3"**, einen **horizontalen Stepper** mit Datum + Akteur je
  Schritt (aktueller Schritt gefüllt in Marken-Farbe, erledigte Schritte markiert) und eine Fußzeile
  **„← Voriger Beleg / Nächster Beleg →"** plus das Label des aktuellen Schritts. Die Stepper-Punkte
  **und** die Vor/Zurück-Buttons öffnen direkt den jeweiligen Beleg — man klickt sich durch die ganze
  Kette, ohne den Viewer zu verlassen.
- **Fail-safe/ehrlich:** Der Navigator erscheint **nur** bei den drei Ketten-Dokumenten (per
  `chainStepIndex()`); jeder andere Beleg (Quartalsbericht etc.) öffnet unverändert ohne Strip.
  Erster Schritt → „Voriger" deaktiviert, letzter Schritt → „Nächster" deaktiviert (`.disabled`,
  `pointer-events:none`).
- **Kette entdoppelt — eine Quelle der Wahrheit:** die Ketten-Definition liegt jetzt als
  **`const DECISION_CHAIN`** in `data.js` und wird sowohl vom Chat-Block (`answer.chain` in
  `budget-herkunft`) **als auch** vom Viewer-Navigator gelesen. Chat-Timeline und Viewer-Stepper
  bleiben damit garantiert synchron; keine doppelten Datenpflege-Stellen mehr.
- **Rein additiv** in `data.js` (Extraktion + Referenz, kein Inhaltswechsel), `app.js`
  (`chainStepIndex()`/`buildChainNav()`, ein Aufruf in `openViewer()`) und `styles.css`
  (`.vchain`-Block). Bestehende Skins, Dokumente und der Antwortpfad unverändert. Deterministisch
  verifiziert (Node-VM gegen `data.js`): **21 Dokumente**, **2 E-Mails**, **12 Szenarien**, **1 chain**,
  `budget-herkunft.chain === DECISION_CHAIN`, **0 kaputte Referenzen**. Live im Browser gegen die
  realen Daten geprüft: Navigator auf allen 3 Belegen mit korrektem „Schritt n/3"-Zähler, Vor/Zurück
  **und** Stepper-Punkt-Klick wechseln das Dokument korrekt (Titel/Zähler/erledigt-Status stimmen),
  Prev am 1. Schritt und Next am letzten deaktiviert, **kein** Strip bei Nicht-Ketten-Dokumenten,
  aktueller Punkt bindet an `--brand`/`--brand-soft`, keine Konsolenfehler. (Screenshot-Capture im
  Harness instabil — bekannte Grenze; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 14 gebaut wurde

**Entscheidungskette als sichtbarer „Beleg-Pfad" im Chat — der stärkste CFO-Moment ist jetzt ohne
Klickarbeit im Bild.** Zyklus 12/13 legten die Daten (zwei E-Mails → CFO → Vorstand); der Betrachter
musste die Kette aber selbst über Quellen-Chips zusammensetzen. Jetzt zeigt die Antwort die
**Herkunfts-Kette als eigenes visuelles Element** — eine kompakte vertikale Timeline:
- **Neues Szenario `budget-herkunft`** (Modul Finanzen, Konfidenz 95 %): „Wie kam das Mehrbudget von
  0,9 Mio. € für Projekt Alpha zustande?" Antwort mit knappem Text **plus** dem neuen Ketten-Block.
- **Neues optionales Feld `answer.chain`** + Renderer **`appendChain()`** (analog zu `appendWithheld()`):
  vertikale Timeline mit **3 Schritten** — je **Datum-Badge**, **Akteur** (z. B. „Einkauf → CFO"),
  **Label**, Beschreibung und **anklickbarem Beleg** (öffnet das Originaldokument im Viewer). Der letzte
  Schritt (Vorstandsbeschluss) ist als `strong` hervorgehoben (gefüllter Punkt, Marken-Farbe).
  Verbindungslinie läuft durch die Punkte und endet sauber am letzten Schritt.
- **Die drei Schritte sind die echten Belege:** Lieferanten-E-Mail (12.02.) → interne Weiterleitung
  Einkauf→CFO mit Bewertung 0,9 Mio. € (13.02.) → Vorstandsbeschluss (März 2026). Alle Zahlen
  konsistent mit der bestehenden Story (640 t × 120 €/t ≈ 0,9 Mio. € = beschlossenes Mehrbudget).
- **Als erster strukturierter Block** unter der Antwort platziert (vor Nachvollziehbarkeit/Quellen) →
  maximale Wirkung; wird vom bestehenden gestaffelten Block-Reveal automatisch mitanimiert.
- **Rein additiv** in `data.js` / `app.js` / `styles.css`; bestehender Antwortpfad und alle Dokumente
  unverändert. Hero 8 → **9 Kacheln**, „Geführte Demo" nimmt das Szenario automatisch auf (jetzt
  **12 Szenarien**). Deterministisch verifiziert (Node-VM gegen `data.js`): **21 Dokumente**, **2
  E-Mails**, **12 Szenarien**, **1 Szenario mit `chain`**, **0 kaputte Referenzen** über alle
  `sources`/`related`/`withheld`/`chain`/`MODULE_SUGGESTIONS`. Chain-Markup + CSS live im Browser gegen
  die realen Szenariodaten geprüft: 3 Schritte, alle anklickbar, 1 `strong`, Punkte/Datum-Badges/
  Beleg-Links binden korrekt an die Marken-Tokens (--brand/--brand-soft/--brand-ink), Verbindungslinie
  2 px und am letzten Schritt beendet; keine Konsolenfehler. (Voll-Streaming-Pfad im Headless-Preview
  timer-gedrosselt, Screenshot-Capture im Harness instabil — bekannte Grenzen; daher DOM/CSS-basiert
  verifiziert.)

## Was in Zyklus 13 gebaut wurde

**Zweite E-Mail (interne Weiterleitung) — die Entscheidungskette quer durch Postfächer ist jetzt
belegt.** Zyklus 12 setzte das E-Mail-Skin und die auslösende Lieferanten-E-Mail; eine einzelne
E-Mail riss die Kern-Erzählung aber nur an. Jetzt zeigt die Demo den **Thread über zwei Nachrichten**
und verbindet **E-Mail → CFO → Vorstandsbeschluss**:
- **Neues Dokument `email-weiterleitung-materialbudget`** (Typ **„E-Mail"**, Modul Finanzen): die
  **WG-Weiterleitung** der Donau-Preis-E-Mail von **Thomas Krüger (Einkauf)** an **Dr. Katharina
  Vogel (CFO)** (Cc Projektleitung Alpha), 13.02.2026. Kernaussage im Highlight: **~640 t
  Jahresbedarf × +120 €/t → rund 0,9 Mio. € Mehrbedarf** für Projekt Alpha; **Empfehlung**,
  das Mehrbudget als Vorstands-Beschlussvorlage einzubringen und Ferro Nord zu beschleunigen.
  **Zitat-Verlauf** = die Original-Donau-E-Mail → sichtbarer Zwei-Nachrichten-Thread.
- **Verzahnt mit der bestehenden Story (kein neuer Wert):** die 0,9 Mio. € stammen exakt aus dem
  **Vorstandsbeschluss TOP 2** (`vorstandsprotokoll-2026-03`). Die Weiterleitung ist die
  **Herkunft dieser Zahl** — der bisher fehlende Beleg, *warum* der Vorstand das Mehrbudget genehmigt
  hat.
- **In zwei Szenarien eingewoben:** „Warum sind die Materialkosten gestiegen?" (E-Mail als **3.
  Quelle**, 81 %, + Verwandte + Reasoning-Schritt Einkauf → CFO) und „Fasse Projekt Alpha zusammen"
  (E-Mail als Quelle für die Herkunft des Mehrbudgets, neuer Reasoning-Schritt zur Entscheidungskette).
  Beide sind Teil der Geführten Demo → das Skin und der Thread erscheinen automatisch im Video.
- **Rein additiv in `data.js`** — kein Code-Umbau (E-Mail-Skin aus Zyklus 12 rendert das identische
  Feldschema automatisch). Deterministisch verifiziert (Node-VM gegen `data.js`): **21 Dokumente**
  (war 20), **2 E-Mails**, **11 Szenarien**, **0 kaputte Referenzen** über alle `sources`/`related`/
  `withheld`/`MODULE_SUGGESTIONS`.

## Was in Zyklus 12 gebaut wurde

**E-Mail-Skin im Dokumentenviewer — „Wissen steckt in E-Mails" ist jetzt im Bild sichtbar.**
Die Mission-Story nennt E-Mails ausdrücklich als Ort, an dem Firmenwissen gefangen ist; im Viewer
gab es dafür bisher kein eigenes Skin. Neu:
- **Neues Dokument `email-preisanpassung-donau`** (Typ **„E-Mail"**, Modul Finanzen): die
  **Original-Ankündigung von Stahlwerk Donau** über die 15-%-Preisanpassung auf Baustahl S355 zum
  01.03.2026 — der **auslösende Beleg** hinter dem Materialkostenanstieg. Bewusst mit der bestehenden
  Story verzahnt: 800 € → 920 € (**+15 %** = die vertragliche Preisgleitklausel §6 aus dem
  Rahmenvertrag RV-2023-014; die +17,9 % im Q1-Bericht sind der Jahresvergleich). CC an die CFO,
  **Anhang-Chip** „Preisliste_2026_Stahlwerk-Donau.pdf · 148 KB", **Zitat-Verlauf** der vorherigen
  Anfrage des Einkaufs (Thomas Krüger).
- **E-Mail-Skin** (`DOC_SKINS["E-Mail"] = { cat: "email" }`): Postfach-Kopf mit **Avatar-Initialen**
  (Verlauf Cyan→Indigo), **Von/An/Cc/Betreff/Gesendet**-Zeilen (Betreff fett via `.mr.sub`),
  Anhang-Chip und zitiertem Verlauf (`.mail-quote`, linker Balken). Neue Helfer in `app.js`:
  `buildMailHead()`, `buildQuoted()`, `mailRow()`; `buildPaper()` verzweigt für `cat === "email"`
  (Postfach-Kopf statt Briefkopf, Betreff ersetzt die generische Überschrift). In der Bibliothek
  trägt die E-Mail-Karte ein **✉-Icon** statt ▤.
- **In die Materialkosten-Story eingewoben:** die E-Mail ist jetzt **2. Quelle** (88 %) der Antwort
  „Warum sind die Materialkosten gestiegen?" (nach dem Q1-Bericht), steht in „Verwandte Dokumente"
  und ist als zusätzlicher Reasoning-Schritt genannt („Auslösende Lieferanten-E-Mail … im
  Einkaufs-Postfach identifiziert"). Dadurch **klickbar in der Geführten Demo** → das E-Mail-Skin
  erscheint automatisch im Video.
- **Rein additiv** in `data.js` / `app.js` / `styles.css`; bestehende Skins, Dokumente und der
  Antwortpfad unverändert. Verifiziert: E-Mail-Karte mit ✉ + Typ „E-Mail" in Finanzen, Viewer öffnet
  `paper-email` mit korrektem Kopf (Initialen „AH", 5 Zeilen, Betreff fett), Anhang-Chip
  (148 KB), 2 Highlights, Zitat mit 3 Zeilen; **0 kaputte Referenzen** (20 Dokumente), keine
  Konsolenfehler. (Layout-Maße im Headless-Preview nicht messbar — 0×0-Viewport, bekannte
  Harness-Grenze; CSS parst/greift, spiegelt das bewährte `.lh`-Briefkopf-Flexmuster.)

## Was in Zyklus 11 gebaut wurde

**Bewegungs-Politur — die Antwort baut sich souverän auf, statt zu springen.** Inhaltlich war die
Demo komplett; die härteste verbleibende Kante war das etwas sprunghafte Ein-/Umblenden. Jetzt:
- **Gestaffelter Block-Reveal:** die strukturierten Blöcke unter jeder Antwort
  (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) blenden **nacheinander**
  ein (neue Keyframe `block-rise`, Fade + 9 px Slide-up, ~0,42 s). `revealBlocks()` in `app.js`
  vergibt je Block eine additive Verzögerung **+55 ms** über die CSS-Variable `--rev-delay` — die
  Antwort „wächst" von oben nach unten statt komplett auf einmal zu erscheinen.
- **Sanfter Modulwechsel:** der neu gerenderte Panel-Inhalt (`.wrap`) blendet dezent ein
  (Keyframe `view-in`, Fade + 7 px Slide-up, ~0,32 s) — beim Wechsel Wissen ↔ Finanzen/Audit/HR/
  Verträge/Berichte/Einstellungen ein weiches Überblenden statt hartem Umschalten. Feuert nur beim
  View-Render; die Chat-Antworten behalten ihre eigene `.msg`-`rise`-Animation.
- **Ehrlich/fail-safe:** `prefers-reduced-motion: reduce` deaktiviert **beide** Effekte sauber —
  `revealBlocks()` steigt früh aus (kein `.reveal`-Klassen-Anhang) und die CSS-Regeln setzen
  `animation: none`. Da die Startopazität nur **im Keyframe** liegt, bleiben alle Blöcke ohne
  Animation voll sichtbar (opacity 1) — **kein Risiko unsichtbarer Inhalte**.
- **Rein additiv:** `styles.css` (zwei Keyframes + `.answer .block.reveal` / `.wrap`-Regel, je mit
  reduced-motion-Guard) und ein kleiner `revealBlocks()`-Helfer in `app.js`; `data.js` und der
  Antwortpfad unverändert. Deterministisch im Browser verifiziert: im Normalbrowser `block-rise`
  mit exaktem Delay (`--rev-delay:110ms` → `animation-delay: 0,11 s`); unter reduzierter Bewegung
  `animationName: none` bei opacity 1. (Streaming-Vollpfad im Headless-Preview durch Timer-
  Throttling zu langsam für Live-Beobachtung → mechanisch/deterministisch geprüft.)

## Was in Zyklus 10 gebaut wurde

**Handlungs-Abschluss pro Antwort — die Story bekommt ihren Schlussmoment.** Bisher endete jede
Antwort informativ, aber ohne den „und dann?"-Moment, den ein Entscheider als Nächstes denkt.
Neu unter jeder **belegten** Antwort (nach den Folgefragen) ein Aktions-Block
**„↗ Ergebnis weiterreichen"**:
- **Primär „✉ An Vorstand senden"** + Sekundär **„⤓ Als Briefing exportieren"**. Klick zeigt eine
  kurze **Vorbereitungs-Phase** (Spinner, „Briefing wird zusammengestellt…" / „PDF wird
  erzeugt…", ~0,8 s) und morpht dann in eine **grüne Erfolgs-Bestätigung** mit ✓-Badge:
  Senden → „Briefing an den Vorstand gesendet · Empfänger: Vorstand · Meridian Industrie GmbH ·
  soeben · Ref. BRF-2026-XXXX"; Export → „Briefing als PDF exportiert · meridian-briefing-2026-
  XXXX.pdf · <Datum>".
- **Deterministische Briefing-Nummer** (`briefingNumber()` = Hash aus Antwortinhalt + Konfidenz) →
  im Video reproduzierbar, konsistent mit dem Tempo-Signal aus Zyklus 8 (keine Zufallszahl).
- **Ehrlich/fail-safe:** Der Block erscheint **nur bei Quellen-belegten Antworten** — ein leerer
  „kein Treffer"-Fallback bietet kein Briefing an. Reine UI: **keine echten Mails/Exporte**, nur
  eine überzeugende Bestätigung. `prefers-reduced-motion` respektiert (Pop-Animation aus,
  Vorbereitungs-Delay 0).
- **Rein additiv** in `app.js` (`appendActions()`/`runAction()`/`briefingNumber()`/`todayGerman()`)
  und `styles.css` (`.block.actions`/`.act`/`.act-done`); `data.js` und der Antwortpfad unverändert.
  Live verifiziert: Block an korrekter Position, beide Buttons, Primär in Marken-Indigo (#4f46e5),
  Klick „An Vorstand senden" → Spinner → grüne Bestätigung (Ref. BRF-2026-5602), keine
  Konsolenfehler. (Screenshot-Capture im Harness instabil → DOM/CSS-basiert verifiziert.)

## Was in Zyklus 9 gebaut wurde

**Ressort-Breite: zwei neue Szenarien + Dokumente (HR-Onboarding & Lieferanten-/Klumpenrisiko).**
Der schwächste Fortschrittsbereich war inhaltliche Breite — jetzt sprechen zwei zusätzliche
Entscheider-Ressorts direkt an:
- **Szenario „Onboarding, erster Tag"** (Modul HR, Konfidenz 96 %): Antwort als Schritt-für-
  Schritt-Checkliste (Empfang, Werksausweis, IT-Zugänge, **Pflicht-Sicherheitsunterweisung**,
  Pflichtdokumente, Pate). Neues Doc **`onboarding-checkliste-2026`** (Typ „Checkliste", 8 Absätze,
  4 Highlights) als Primärquelle (98 %), Querverweis **Reiserichtlinie 2026** (68 %).
- **Szenario „Lieferanten-/Klumpenrisiko"** (Modul Finanzen, Konfidenz 94 %): Antwort mit
  **Konzentrations-Tabelle** (Stahlwerk Donau AG **23,9 %** · Siemens 11,6 % · Robotik Bayern
  8,2 %) und **Single-Source-Warnung** für Baustahl S355; Gegenmaßnahme Ferro Nord. Neues Doc
  **`lieferanten-risikoanalyse-2026`** (Typ „Risikobericht") mit `lineItems`-Tabelle „Top-
  Lieferanten 2025" (5 Positionen, 268 Mio. € Gesamtvolumen). Quellen: Risikoanalyse (97 %) +
  Vorstandsprotokoll (80 %) + Rahmenvertrag (72 %).
- **Bewusst mit der bestehenden Story verzahnt:** größter Lieferant = Stahlwerk Donau (Materialkosten/
  Rechnung), Zweitquelle Ferro Nord = derselbe Vorstandsbeschluss wie im Strategie-/Governance-
  Szenario. Einkaufsvolumen plausibel zum Umsatz 612 Mio. €.
- **Rein additiv in `data.js`** — kein Code-Umbau. Hero-Vorschläge 6 → 8, „Geführte Demo" nimmt
  beide automatisch auf (jetzt **11 Szenarien**). Live verifiziert: 0 kaputte Referenzen, beide
  Hero-Kacheln, Tabelle mit korrektem Kopf + 3 Datenzeilen, alle Quell-Links lösen auf echte
  Dokumente auf, keine Konsolenfehler.

## Was in Zyklus 8 gebaut wurde

**Video-Politur: Tempo-Signal + Zahlen-Hochzählen.** Die letzte fehlende Politur — die Demo
wirkt jetzt fühlbar schnell und „live":
- **„⚡ Beantwortet in X,X s"** im Antwortkopf (links vom Konfidenz-Meter), zählt beim
  Erscheinen von 0 hoch. Wert ist **deterministisch** aus Antwortumfang (Quellen, Textlänge,
  Tabelle) im Fenster **1,2–2,6 s** → im Video reproduzierbar, keine Zufallszahl.
- **Kernzahlen zählen hoch** (18,4 %, 87.584 €, -30,0 % …), sobald die Antwort fertig getippt
  ist. Neue `animateCounts()` scannt die **fett gesetzten** Zahlen; `parseGermanNumber()`
  versteht deutsche Formate (Dezimalkomma, Tausenderpunkt, Einheit % € t „Mio. €" GWh).
- **Sicher:** verlangt Dezimalkomma **oder** Einheit → **Jahre (2026), Datum (28.02.2026),
  PO-Nummern** bleiben unangetastet. `requestAnimationFrame` (easeOutCubic, ~760 ms),
  `tabular-nums` gegen Breiten-Zittern, `prefers-reduced-motion` → Endwerte sofort.
- **Rein additiv** in `app.js` / `styles.css`; `data.js` und der Antwortpfad unverändert.
  Live verifiziert: Tempo-Signal „1,9 s", Parser exakt gegen alle realen fett-Zahlen (alle
  Kernwerte animieren, alle Jahre/Datum/PO ausgeschlossen), Count-up-Mechanismus auf realem
  Fragment (Zwischenframe → korrekter Endwert), keine Konsolenfehler.

## Was in Zyklus 7 gebaut wurde

**Vertrauens-/Governance-Story sichtbar gemacht.** Die Kernidee „Sie sehen nur, was Sie
dürfen" ist jetzt in der Demo greifbar — der größte bisher ungenutzte Wow-Hebel für
skeptische CFO/Compliance-Entscheider:
- **Zwei gesperrte Dokumente** im Modul Berichte (`akquisition-nordstern` „Projekt Nordstern
  — Akquisitionsvorlage", `vorstandsverguetung-2026` „Vorstandsvergütung 2026"). Flag
  `locked: true` + `lockedRole` + `classification`, **bewusst ohne `body`** → der Inhalt
  existiert gar nicht im Client, kann also nicht geleakt werden.
- **Bibliothek:** gesperrte Karte gestrichelt/ausgegraut mit **Schloss** und rotem
  „🔒 Kein Zugriff — <Rolle>". Klick öffnet **keine** Inhalte, sondern eine
  **„Zugriff verweigert"-Ansicht** im Viewer (Klassifizierung, Freigabe-Rolle, Eigentümer).
- **Neues 9. Szenario** „Was hat der Vorstand für die Wachstumsstrategie beschlossen?"
  beantwortet nur die **freigegebenen** Beschlüsse (aus dem Vorstandsprotokoll) und zeigt
  darunter das Governance-Signal **„2 weitere Treffer für Sie nicht freigegeben"** mit
  Klassifizierungs-Tag und **anklickbaren gesperrten Treffern** (öffnen die Zugriff-
  verweigert-Ansicht). Neues optionales Feld `answer.withheld` → Block `appendWithheld()`.
- **Rein additiv** in `data.js` / `app.js` / `styles.css`; bestehender Antwortpfad und alle
  vorhandenen Dokumente unverändert. „Geführte Demo" deckt automatisch 9 Szenarien ab
  (Zähler dynamisch). Live verifiziert: 2 gesperrte Karten, Zugriff-verweigert ohne
  Inhalts-Leak, korrekte Meta, Szenario als Hero-Vorschlag.

## Was in Zyklus 6 gebaut wurde

**Onboarding-Overlay beim ersten Start.** Der erste Video-Eindruck ist jetzt geführt statt
leer. Beim ersten Laden erscheint ein **leichtgewichtiges Coachmark** oben rechts:
- Ein **Pfeil zeigt exakt auf den „▶ Geführte Demo"-Button** (Offset 270 px = Buttonmitte,
  im Browser auf ±10 px verifiziert); der Button **pulsiert** dezent, solange das Overlay
  offen ist.
- **Ein Satz** als Headline („Fragen Sie alles über Ihr Unternehmenswissen") + kurzer
  Erklärtext, der zur Geführten Demo führt.
- **Primär-CTA „▶ Geführte Demo starten"** schließt das Overlay **und startet direkt die
  Vorführung** — ein starker Video-Opener (ein Klick → alles läuft automatisch).
  Sekundär **„Selbst erkunden"** schließt nur; Klick auf den abgedunkelten Hintergrund und
  **Esc** schließen ebenfalls.
- **Erscheint nur einmal** (`localStorage`-Flag `aistudio.onboarded.v1`; try/catch, damit es
  auch unter `file://` ohne Storage sauber weiterläuft — dann eben bei jedem Laden).
- **Rein additiv** in `index.html` / `styles.css` / `app.js` — `data.js` und der Antwortpfad
  unverändert. `prefers-reduced-motion` respektiert. Live verifiziert: Anzeige, Pfeil-
  Ausrichtung, Skip-/Esc-/Backdrop-Schließen, Persistenz über Reload, CTA startet Demo
  (Fortschritt „1 / 8", Composer gesperrt), keine Konsolenfehler.

## Was in Zyklus 5 gebaut wurde

**ESG/CO₂-Szenario — Breite über Finanz/Audit hinaus.** Neues 8. Szenario „Wie hat sich
unser CO₂-Fußabdruck entwickelt — sind wir auf ESG-Kurs?" hebt die Demo auf Vorstands-/
Aufsichtsratsthemen:
- **Antwort mit CO₂-Trend-Tabelle** (2020 46.800 t → 2025 41.200 t / -12 % → Ziel 2030
  32.760 t / -30 %) und **ehrlicher Lücken-Offenlegung** (linearer Pfad läge bei -15 %) statt
  Schönfärberei — glaubwürdig für einen CFO/CEO.
- **Neues Doc `energie-emissionsbericht-2025`** („Energie- & Emissionskennzahlen 2025") als
  belastbare Zweitquelle (Trend, Zielwert, Energieintensität, Hebel).
- **`esg-bericht-2025` von 2 auf 6 Absätze vertieft** (Scope 1/2, erneuerbarer Anteil 68 %,
  Zielpfad, Soziales & Governance).
- **Rein additiv in `data.js`** — kein Code-Umbau. Zahlen über alle 3 Quellen konsistent
  (41.200 t = -12 % ggü. 46.800 t; Ziel = 46.800 × 0,70). Wiring in Hero + Modul Berichte;
  „Geführte Demo" 7 → 8 Szenarien. Live verifiziert (Tabelle, 4 Blöcke, Quellen 97/93/76 %,
  Viewer-Skin + Highlights; keine Konsolenfehler).

## Was in Zyklus 4 gebaut wurde

**Rechnungs-Positionstabelle im Beleg-Skin** — Rechnung/Bestellung/Wareneingang öffnen im
Viewer jetzt mit einer echten **Buchungstabelle** (Pos. · Bezeichnung · Menge · Einzelpreis ·
Summe) statt Fließtext:
- Neue `buildLineItems()`/`footRow()` in `app.js`, `.li-table`-Styling in `styles.css`
  (rechtsbündige `tabular-nums`, hervorgehobene Brutto-Endsumme).
- **Optionales `doc.lineItems`-Feld** in `data.js` für die 3 Belege; Fallback = bisheriger
  Text. Netto/USt/Brutto-Fußzeilen nur, wenn im Datensatz vorhanden.
- **Drei-Wege-Abgleich jetzt prüfungsecht:** identische Menge (80,000 t) und Netto
  (73.600 €) über alle drei Belege; Rechnung mit USt 19 % → **Brutto 87.584 €**, Bestellung
  nur Netto, Wareneingang „vollständig" ohne Betrags-Fußzeile.
- Falsches Snippet-Brutto der Rechnung (84.640 €) auf konsistente **87.584 €** korrigiert.
- **Rein additiv** — bestehende Dokumente ohne `lineItems` bleiben unverändert. Alle drei
  Belege live im Browser verifiziert (DOM + CSS geprüft; Screenshot-Capture im Harness
  aktuell instabil, daher text-basiert verifiziert).

## Was in Zyklus 3 gebaut wurde

**„Geführte Demo" — hands-free Auto-Play** aller 7 Szenarien über einen Play-Button in
der Topbar:
- Ein Klick auf **„▶ Geführte Demo"** startet die Vorführung: Chat wird frisch am Hero
  gestartet, jede Frage wird **sichtbar in den Composer getippt**, danach läuft der
  bestehende `ask()`-Flow (Retrieval-Schritte → gestreamte Antwort → Quellen), danach eine
  kurze **Lesepause**, dann das nächste Szenario.
- **Fortschritt** „Szenario n / 7" direkt im Button; Button wird zu **„⏹ Demo stoppen"**.
- Jederzeit **stoppbar** (saubere Token-Mechanik); Composer ist während der Demo gesperrt.
- **Rein additiv** in `index.html` / `styles.css` / `app.js` — `data.js` und der bestehende
  Antwortpfad blieben unverändert. Start/Typing/Fortschritt/Stopp live im Browser verifiziert.

## Was in Zyklus 2 gebaut wurde

**Dokument-Skins im Viewer** — der Viewer zeigt jede Quelle jetzt als **echtes Papier-
Dokument** statt als Textliste:
- **Briefkopf** (Logo-Initialen · Aussteller · Referenzblock mit Typ/Titel/Datum).
  Eingangsrechnungen tragen korrekt den **Lieferanten** als Aussteller.
- **Belege** → rotierter Stempel (EINGANG/GENEHMIGT/GEPRÜFT), **Verträge** →
  Ort/Datum + zwei **Unterschriftszeilen**, **Prüfnachweise** → grüner **BESTANDEN**-Stempel.
- **Klausel-Marken** (§9, Teil B §5, TOP 1) hervorgehoben; **gelbe Highlights liegen im
  Dokument-Layout**.
- Rein CSS/HTML, datengetrieben aus `doc.type` — neue Dokumente bekommen ihr Skin
  automatisch, **`data.js` blieb unverändert**. Alle 4 Skin-Kategorien live verifiziert.

## Was in Zyklus 1 gebaut wurde

Ein **self-contained, buildfreies Enterprise-Web-App** (Vanilla-JS, `file://`-fähig):
- **Fiktive Demo-Firma „Meridian Industrie GmbH"** (Maschinen-/Anlagenbau, München) —
  15 authentische Dokumente (Reiserichtlinie, Rechnung/Bestellung/Wareneingang,
  Quartalsbericht, 4 Verträge, Projekt Alpha, Vorstandsprotokoll, Brandschutz, ESG …).
- **Chat als Zentrum** — gestreamte Antworten mit sichtbaren Retrieval-Schritten.
- **Jede Antwort belegt:** Antwort · Nachvollziehbarkeit · Quellen (Zitat + Relevanz %) ·
  Konfidenz-Meter · verwandte Dokumente · Folgefragen.
- **Dokumentenviewer** (Slide-over): hervorgehobene Belegstellen + Metadaten.
- **7 Demo-Szenarien** exakt aus der Missions-Vorgabe; freie Fragen fallen auf eine
  ehrliche Stichwortsuche zurück (fail-closed, keine Halluzination).
- **Module:** Wissen, Finanzen, Audit, HR, Verträge, Berichte, Einstellungen.
- **Live im Browser getestet** — Szenario, Streaming, Quellen und Viewer funktionieren.

---

## 🎯 NÄCHSTER ZYKLUS — die EINE wichtigste Verbesserung

**Den Suchmoment in die Geführte Demo einweben — die Command-Palette als eigener Video-Beat.** Die
globale Suche steht (Zyklus 17), läuft aber nur, wenn der Betrachter sie selbst auslöst — in der
hands-free „Geführten Demo" taucht sie noch nicht auf. Der stärkste nächste Schritt ist ein **kurzer
Such-Beat als Opener der Vorführung**: bevor die erste Frage getippt wird, öffnet die Demo automatisch
die Palette, tippt sichtbar z. B. **„stahl"**, zeigt **8 Treffer quer über Finanzen + Audit**, öffnet
kurz einen Beleg und schließt wieder — *dann* startet die Frage-Sequenz. Das macht die schiere **Menge**
des erschlossenen Wissens zum ersten Bild des Videos („mein Unternehmen besitzt das alles bereits").
Reuse: `openSearch()`/`renderSearchResults()`/`openViewer()` sind vorhanden; nötig ist nur eine kleine
Choreografie in `startDemo()` (Palette öffnen, Query tippen, Pause, schließen) hinter dem bestehenden
`token`-Mechanismus. Rein additiv, `data.js` unverändert.

*Warum?* Zyklus 17 hat den Such-**Mechanismus** gebaut; sein Wert entfaltet sich im Video aber erst,
wenn er **ohne Zutun des Betrachters** vorgeführt wird. Ein 6–8-Sekunden-Beat verwandelt ein Feature in
einen Wow-Moment.

**Alternative, falls Tiefe vor Breite:** die Entscheidungskette auch an die **`materialkosten`-Antwort**
hängen (dasselbe `answer.chain` = `DECISION_CHAIN`). Achtung Video-Reihenfolge: dann erschiene die
Kette zweimal in der Geführten Demo (materialkosten direkt vor budget-herkunft) — die beiden Beats
müsste man trennen oder einen aus der Sequenz nehmen. Da `materialkosten` → `budget-herkunft` bereits
die natürliche „warum? → woher genau?"-Abfolge ist, wurde bewusst **nicht** dupliziert.

---

## CEO-Review (Ende Zyklus 17)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Mit Strg+K öffnet sich jetzt eine
  Command-Palette wie in Linear/Notion, die den **gesamten** Wissensspeicher durchsucht. Das signalisiert
  einem Entscheider sofort: „AI Studio kennt *alles* im Haus, nicht nur ein paar kuratierte Fragen."
- *Erzeugt es Aufregung?* — Ja: Das leere Suchfeld zeigt **„23 Dokumente im Wissensspeicher"**, und ein
  einziges Wort („stahl") sammelt in Millisekunden Treffer **quer durch Finanzen und Audit** mit
  hervorgehobenem Suchbegriff. Genau das „endlich nutzbar"-Gefühl, um das sich die ganze Story dreht.
- *Versteht ein CFO/CEO den Nutzen?* — Ja: Man tippt ein Stichwort, sieht sofort *wo überall* es
  vorkommt, klickt und liest den Originalbeleg. Gesperrte Dokumente tauchen zwar auf, bleiben aber
  **verschlossen** — die Vertrauens-Story bleibt intakt.
- *Schwächste Stelle → nächster Zyklus:* Das Feature ist stark, wird aber in der **hands-free
  Vorführung** noch nicht gezeigt. Es als **automatischen Such-Beat in die Geführte Demo** aufzunehmen
  ist der größte verbleibende Wow-Hebel — siehe oben.
