# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 21 — **Projekt Beta**: ein zweites, bewusst *verzögertes* Projekt neben
  Alpha (kundenspezifische Anlage für die Nordwind Logistik AG). Beweist, dass die Demo-Firma mehrere
  parallele Vorhaben trägt — und dass AI Studio Risiken **offen** kennzeichnet (Ampel-Status) statt zu
  beschönigen. Neues Szenario + 2 Belege (Statusbericht + Eskalations-E-Mail), rein additiv in `data.js`.
- **Zuletzt aktualisiert:** 2026-07-08.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 86 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

## Was in Zyklus 21 gebaut wurde

**Projekt Beta — die Demo-Firma trägt jetzt mehrere parallele Vorhaben, ehrlich inklusive Risiko.** Der
schwächste Fortschrittsbereich war **Demo-Firma & realistische Dokumente (86 %)**. Bisher zeigte die Demo
mit Alpha nur *eine* Vorzeige-Story (im Zeitplan). Ein skeptischer CFO fragt als Nächstes: *„Ist das nur
diese eine schöne Geschichte, oder trägt es meinen ganzen Betrieb?"* Neu:
- **Szenario `projekt-beta`** (Modul Berichte, Konfidenz 90 %): „Wie steht Projekt Beta?" — eine
  kundenspezifische, automatisierte Verpackungs-/Palettierlinie für die **Nordwind Logistik AG**
  (Engineering München, Endmontage Werk 2). Antwort mit **Ampel-Statustabelle**: Fortschritt **48 %
  ⚠ verzögert**, Budget **8,6 Mio. €** (4,7 verausgabt) im Rahmen, Liefertermin **Q4 2026 ⚠ 3 Wo.
  Verzug** (verschoben von Q3). Ursachen: **Lieferverzug der Steuerungselektronik** (Zulieferer 6 Wochen
  zu spät) + **Kunden-Change-Request** (zusätzliche Prüfstation, +0,4 Mio. €). Risiko: **Pönale** 0,5 %
  je Verzugswoche, gedeckelt bei 5 % (max. 0,43 Mio. €). Gegenmaßnahmen: Zweitquelle Elektronik
  qualifiziert, Change Request kaufmännisch geltend gemacht, wöchentliche Eskalation. Schließt mit dem
  **offenen Kontrast zu Alpha** („im Zeitplan") — *AI Studio kennzeichnet das Risiko, statt es zu
  beschönigen.*
- **Zwei neue Belege** (Modul Berichte):
  - **`projekt-beta-status`** (Typ „Projektbericht" → `paper-bericht`, 6 Highlights): Statusbericht per
    **31.03.2026** — dasselbe Berichtsdatum wie Alpha, also eine echte parallele Momentaufnahme.
  - **`eskalation-beta-elektronik`** (Typ „E-Mail" → `paper-email`, **3. E-Mail der Demo**): Eskalation
    der Projektleitung Beta (Ing. Markus Feldmann) an die **CFO** (Cc **CEO**) zum Lieferverzug + Pönale-
    Risiko + Antrag Zweitquelle; **zitierter Verlauf** = die Zulieferer-Meldung (ElektroSys, Halbleiter-
    Engpass). Nutzt das **bestehende E-Mail-Skin** aus Zyklus 12 — kein Code-Umbau.
- **Bewusst mit der bestehenden Story verzahnt, ohne Kollision:** Betas „Zweitquelle Elektronik"-Motiv
  spiegelt Alphas „Zweitlieferant Ferro Nord"-Thema (Lieferketten-Risiko als roter Faden). `related`
  verlinkt zu `projekt-alpha-status` → der „mehrere Projekte"-Eindruck entsteht direkt beim Lesen.
- **Rein additiv in `data.js`** — kein Code-Umbau (beide Skins rendern das identische Feldschema
  automatisch). Hero (Modul Wissen) 11 → **12 Kacheln**, Berichte 5 → 6, Geführte Demo 14 → **15
  Szenarien** (Beta läuft direkt nach Alpha → „im Zeitplan" gefolgt von „unter Terminrisiko" — ein
  starker Kontrast im Video).
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **27 Dokumente** (war 25), **15
  Szenarien**, **3 E-Mails**, **2 gesperrt** (unverändert), **0 kaputte Referenzen**; beide Quell-Zitate
  liegen wortgleich im Body; alle Relevanzwerte 0–100. Live im Browser (DOM gegen reale Daten):
  Beta-Hero-Kachel vorhanden; Klick löst das Szenario auf → Konfidenz-Meter **90 %** + Herleitungs-
  Tooltip; **Ampel-Tabelle** korrekt (Kopf + 3 Zeilen: 48 %/verzögert, 8,6 Mio. €, Q4 2026), Alpha-
  Kontrast im Text; Suche „beta" findet **beide** Docs (▤ Status, ✉ E-Mail); Eskalations-Mail öffnet
  als **`paper-email`** mit 5 Kopfzeilen (Von/An/Cc/Betreff/Gesendet) + zitiertem Verlauf; Statusbericht
  öffnet als **`paper-bericht`** mit 6 Highlights; **keine Konsolenfehler**. (Voll-Streaming-Pfad im
  Headless-Preview timer-gedrosselt — bekannte Harness-Grenze; daher DOM/Daten-basiert verifiziert.)

## Was in Zyklus 20 gebaut wurde

**Konfidenz-Herleitung — die Prozentzahl im Antwortkopf ist jetzt erklärbar.** Der letzte Skeptiker-
Einwand eines CFOs zielt auf die **Konfidenzzahl selbst** („woher weiß das System das?"). Neu: hovert der
Cursor das Konfidenz-Meter, öffnet sich ein kleines Popover direkt darunter, das die Zahl **aus den
Quellen herleitet**:
- **Drei datengetriebene Faktoren**, je mit Mini-Balken: **Quellen herangezogen** (Anzahl, skaliert auf
  bis zu 4 = voll), **Höchste Relevanz** (Top-Quelle in %), **Übereinstimmung der Belege** — qualitativ
  **einzeln / teilweise / hoch** mit ehrlicher Unterzeile „X von N Belegen ≥ 80 % Relevanz". Titel „So
  ergibt sich die **Konfidenz X %**", Fußzeile *„Keine Behauptung — eine Ableitung aus konkreten Quellen."*
- **Rein datengetrieben** aus dem bestehenden `answer.sources`-Array — **keine neuen Datenfelder**. Ohne
  Quellen (Fallback-Antwort) erscheint **kein** Tooltip. Ehrlich statt beschönigt: `projekt-alpha` (3
  Quellen, aber nur 1 ≥ 80 %) zeigt korrekt **„teilweise"**, `reiserichtlinie` (1 Quelle) **„einzeln"**.
- **Zugänglich:** das Meter ist `tabindex="0"` + `aria-label`; das Popover öffnet auch per Tastatur
  (`:focus-within`), nicht nur per Maus. `prefers-reduced-motion` → keine Transition.
- **Rein additiv:** neue `buildConfPop(answer)` + erweitertes Kopf-Markup in `app.js`, `.conf-pop`-Block
  in `styles.css`; `data.js`/`index.html` unverändert. Bestehender Antwortpfad, Skins und alle Dokumente
  unangetastet. Deterministisch verifiziert (Node-VM gegen `data.js`): **14 Szenarien mit Quellen** (alle
  erhalten den Tooltip), **0 ungültige Relevanzwerte**, Labels korrekt über alle Fälle. Live im Browser
  gegen reale Daten geprüft: Kopf trägt `conf has-pop` + `tabindex="0"`, Popover-Inhalt korrekt hergeleitet
  (Reiserichtlinie 1 Quelle · Top 98 % · „einzeln"), Mini-Balken **25/98/55 %** passend, Popover per
  `:focus-within` sichtbar (opacity 1), **keine Konsolenfehler**. (Screenshot-Capture im Harness instabil,
  `:focus-within`-Tint headless unzuverlässig — bekannte Grenzen; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 19 gebaut wurde

**Reklamations-Vorgang — auch die Ausnahme ist lückenlos belegt, und das Geld kam zurück.** Der
schwächste Fortschrittsbereich war **Demo-Firma & realistische Dokumente (81 %)**. Bisher zeigte die
Demo nur den *sauberen* Beleg-Pfad (Drei-Wege-Abgleich ohne Abweichung). Neu ist der *Ausnahme*-Pfad —
ein vollständiger Qualitäts-/Reklamationsvorgang, bewusst mit der Donau-Story verzahnt:
- **Neues Szenario `reklamation-stahl`** (Modul Audit, Konfidenz 95 %): „Wie haben wir die mangelhafte
  Stahllieferung reklamiert?" Antwort in drei belegten Schritten — **Erkannt** (12 t von 60 t fallen bei
  der Wareneingangsprüfung durch eine **Maßabweichung EN 10029** + Walzhautfehler), **Gerügt**
  (form-/fristgerecht nach **§377 HGB**, Rüge am 2. Tag, Gewährleistungsklausel §12), **Erstattet**
  (Gutschrift **11.040 € netto / 13.137,60 € brutto**). Kernbotschaft: *Mangel erkannt, fristgerecht
  gerügt, Geld zurück.*
- **Zwei neue Dokumente:**
  - **`maengelruege-mr-2026-0091`** (Typ **„Mängelrüge"**, Modul Audit): formale Rüge Meridian →
    Stahlwerk Donau, Bezug Bestellung PO-2026-0684. Neues Beleg-Skin mit rotem **MÄNGELRÜGE**-Stempel,
    Aussteller = Meridian, 3 Highlights (Mangel, §377-HGB-Rüge, Forderung Nachlieferung/Gutschrift).
  - **`gutschrift-gs-2026-0203`** (Typ **„Gutschrift"**, Modul Finanzen): Gutschrift Stahlwerk Donau →
    Meridian mit **Positionstabelle** (12 t × 920 € = 11.040 € netto · USt 19 % 2.097,60 € · brutto
    13.137,60 €), grüner **GUTSCHRIFT**-Stempel, Aussteller = Lieferant (extIssuer).
- **Verzahnt, ohne Kollision:** separate Folgelieferung (PO-2026-0684) — der bestehende saubere
  Drei-Wege-Abgleich (PO-2026-0512 / Rechnung 2026-1843 / WE-2026-0778, 80 t, keine Abweichung) bleibt
  unangetastet. **Rahmenvertrag** um **§12 Gewährleistung** ergänzt → die Zitate von Mängelrüge und
  Gutschrift lösen jetzt auf eine sichtbare Vertragsklausel auf.
- **Rein additiv:** `data.js` (2 Docs + Szenario + §12 + Wiring), `app.js` (2 DOC_SKINS: „Mängelrüge"
  beleg/warn-Stempel, „Gutschrift" beleg/extIssuer/ok-Stempel), `styles.css` (ein Stempel-Ton
  `.stamp-warn`, Rot #b91c1c). Bestehende Skins/Belege/Antwortpfad unverändert. Hero 10 → **11**
  Kacheln, Geführte Demo 13 → **14 Szenarien**; Modul-Vorschläge Audit + Finanzen erweitert.
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **25 Dokumente** (war 23), **14
  Szenarien**, 2 E-Mails, 2 gesperrt, **0 kaputte Referenzen**, Hero 11; Arithmetik geprüft
  (12 × 920 = 11.040; +19 % = 13.137,60 €). Live im Browser (DOM gegen reale Daten): Suche findet beide
  Belege mit korrektem Modul-Tag; **Gutschrift** öffnet `paper-beleg`, Aussteller „Stahlwerk Donau AG",
  GUTSCHRIFT-Stempel grün, Positionstabelle Netto/USt/Brutto korrekt, 3 Highlights; **Mängelrüge**
  öffnet `paper-beleg`, Aussteller „Meridian Industrie GmbH", MÄNGELRÜGE-Stempel **rot (rgb 185,28,28)**,
  3 Highlights; Szenario-Kopf rendert mit **95 % Konfidenz**; **keine Konsolenfehler**. (Voll-Streaming-
  Pfad im Headless-Preview timer-gedrosselt, Screenshot-Capture instabil — bekannte Harness-Grenzen;
  daher DOM/Daten-basiert verifiziert.)

## Was in Zyklus 18 gebaut wurde

**Such-Beat als automatischer Opener der Geführten Demo — die Command-Palette wird jetzt hands-free
vorgeführt.** Zyklus 17 baute den Such-**Mechanismus**; sein Wert entfaltete sich im Video aber nur,
wenn der Betrachter Strg+K selbst drückte. Jetzt eröffnet die „▶ Geführte Demo" mit einem 6–8-Sekunden-
Such-Beat, *bevor* die erste Frage getippt wird:
- **Neue `demoSearchBeat(token)`** (nur `app.js`): öffnet die Palette **inline** — die manuelle
  `openSearch()` bleibt während der Demo bewusst gesperrt, daher öffnet der Beat den Overlay direkt
  (`search.open`, `hidden=false`, `renderSearchResults("")`, Fokus). Zeigt kurz **„23 Dokumente im
  Wissensspeicher"**, tippt dann **„stahl"** Zeichen-für-Zeichen (je Keystroke `renderSearchResults`) →
  **8 von 23** Treffer quer über **Finanzen · Audit · Verträge** mit gelbem `<mark>`-Highlight.
- **Öffnet einen Beleg:** wählt den ersten **freigegebenen** Treffer (`findIndex(d => !d.locked)`) —
  gesperrte werden übersprungen, damit als Opener **kein** „Zugriff verweigert" erscheint — setzt die
  Auswahl (`setSel`) und öffnet ihn im bestehenden Viewer (`openViewer`), Lesepause, `closeViewer`,
  `closeSearch`; *dann* läuft die bestehende Szenario-Schleife weiter.
- **Verdrahtung:** ein Aufruf in `startDemo()` nach dem Frisch-Start und **vor** der Schleife, in
  `token`-Guards eingefasst. **Fail-safe:** `resetDemoUi()` schließt jetzt zusätzlich `closeViewer()` +
  `closeSearch()` → wird die Demo **mitten im Beat** gestoppt, bleibt kein Overlay/Viewer offen. Voll
  token-gesteuert (Abbruch an jedem Schritt); `prefers-reduced-motion` → sofortiges Tippen + kurze Pausen.
- **Rein additiv** in `app.js`; `data.js`/`styles.css`/`index.html` unverändert (Reuse von
  `renderSearchResults()`/`setSel()`/`openViewer()`/`closeViewer()`/`closeSearch()`/`reducedMotion()`).
  Live im Browser gegen die realen Daten verifiziert: Beat läuft automatisch (Palette → „stahl" → 8/23,
  Module Finanzen/Audit/Verträge, `<mark>` vorhanden), Viewer öffnet auf „Quartalsbericht Q1 2026" und
  schließt wieder, danach **Fortschritt „1 / 13"** + Composer gesperrt (nahtloser Übergang); Stopp mitten
  im Beat räumt Palette + Viewer sauber ab und reaktiviert den Composer; **keine Konsolenfehler**.
  (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM-basiert verifiziert.)

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

**Ein „Portfolio"-Überblick als Landing-/Antwort-Moment: „Welche Projekte laufen aktuell?"** Nach Zyklus
21 trägt die Demo zwei gleichwertig belegte Projekte (Alpha im Zeitplan, Beta verzögert). Der stärkste
nächste additive Schritt macht diese **Parallelität sofort sichtbar**: ein neues Szenario **„Welche
Projekte laufen aktuell?"** (Modul Berichte), das beide Projekte in **einer Ampel-Übersichtstabelle**
gegenüberstellt (Projekt · Fortschritt · Budget · Termin · Status), mit Quellen auf **beide**
Statusberichte. Das ist der „mein ganzes Portfolio auf einen Blick"-Moment für einen CEO/CFO — und die
natürliche Klammer über Alpha + Beta. Rein additiv in `data.js` (Reuse der `<table>`-Antwortstruktur +
bestehender Statusberichte als Quellen); Wiring in Hero + Modul Berichte. Hebt **Szenarien-Breite** und
verzahnt die zwei Projekte zu einer Geschichte.

*Warum?* Die Demo hat jetzt Breite (15 Szenarien, 27 Dokumente über 6 Ressorts), Tiefe (saubere **und**
Ausnahme-Belegpfade), erklärte Belegbarkeit (Konfidenz-Tooltip) **und** mehrere parallele Projekte. Was
noch fehlt, ist der **eine Blick, der die Parallelität zeigt** — statt sie nur über zwei getrennte Fragen
erlebbar zu machen. Eine Portfolio-Übersicht liefert genau diese Vogelperspektive.

**Alternative (Tiefe):** ein drittes Ressort-Dokument für Beta (z. B. der **Change-Request/Angebots-
Nachtrag** an Nordwind über +0,4 Mio. €) — macht den kaufmännischen Umgang mit dem Kunden-Änderungswunsch
belegbar. Nur falls Portfolio-Übersicht zu ähnlich zum bestehenden `vorstand-summary` wirkt.

**Nicht dupliziert (bewusst):** Beta **nicht** zusätzlich ins Vorstandsprotokoll oder in die
`DECISION_CHAIN` einweben — das würde die in Zyklus 15 sorgfältig entdoppelte Alpha-Kette verwässern.
Beta steht als eigenständiger, sauber belegter Vorgang neben Alpha.

---

## CEO-Review (Ende Zyklus 21)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo zeigt nicht mehr nur eine perfekte
  Geschichte (Alpha, im Zeitplan), sondern ein **zweites, reales Projekt (Beta) unter Terminrisiko** —
  mit Ampel-Status, Pönale-Risiko und Gegenmaßnahmen, jeder Punkt belegt. In der Geführten Demo folgt
  „im Zeitplan" direkt auf „unter Terminrisiko" — ein glaubwürdiger Kontrast.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„das System zeigt mir auch das Projekt, das gerade
  schwierig läuft — und verschweigt das Risiko nicht."* Genau dieses **ehrliche** Verhalten schafft
  Vertrauen; eine Demo, in der alles grün ist, wirkt unglaubwürdig.
- *Schwächste Stelle → nächster Zyklus:* die **Parallelität der Projekte** ist noch über zwei getrennte
  Fragen verteilt — ein Portfolio-Überblick („Welche Projekte laufen aktuell?") macht sie auf einen
  Blick sichtbar. Siehe oben.

## CEO-Review (Ende Zyklus 20)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo beweist Belege pro Antwort nicht mehr
  nur (Quellen, Relevanz, Konfidenzzahl) — sie **erklärt** die Konfidenzzahl jetzt am Meter: hovert der
  Cursor, zeigt ein Popover *„3 Quellen · höchste Relevanz 97 % · Übereinstimmung hoch"*. Die 95 % sind
  sichtbar keine Behauptung, sondern eine Ableitung.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: der häufigste Skeptiker-Reflex („woher weiß das System
  das?") wird in einer Sekunde entkräftet, ohne dass jemand eine Formel erklären muss. Und es bleibt
  **ehrlich** — bei nur teilweiser Beleglage sagt der Tooltip „teilweise", nicht „hoch".
- *Schwächste Stelle → nächster Zyklus:* Breite der Demo-Firma — ein **zweites Projekt (Beta)** neben
  Alpha, gleichwertig belegt. Siehe oben.

## CEO-Review (Ende Zyklus 19)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Neben dem Wow-Opener (Such-Beat) zeigt die Demo
  jetzt einen Vorgang, der jeden CFO/Auditor überzeugt: eine **mangelhafte Stahllieferung** wurde
  erkannt, **fristgerecht nach §377 HGB gerügt** und per **Gutschrift (11.040 € netto) erstattet** —
  jeder Schritt mit Originalbeleg. Die Demo beweist damit nicht nur den *sauberen* Pfad
  (Drei-Wege-Abgleich), sondern auch, dass die **Ausnahme** lückenlos dokumentiert ist.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„auch als etwas schiefging, haben wir es sauber
  dokumentiert und das Geld kam zurück"*. Das ist Governance und Prüfungssicherheit in einem Satz.
- *Schwächste Stelle → nächster Zyklus:* Breite und Tiefe stehen; der letzte Hebel ist **Politur der
  Belegbarkeit** — ein Konfidenz-Tooltip, der die Prozentzahl aus den Quellen herleitet. Siehe oben.

## CEO-Review (Ende Zyklus 18)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Geführte Demo eröffnet jetzt mit einem
  Wow-Bild: die Command-Palette öffnet sich von selbst, tippt „stahl" und sammelt in Millisekunden
  **8 Treffer quer durch Finanzen und Audit** — bevor überhaupt die erste Frage läuft. Ein Klick, und
  das ganze Video läuft hands-free.
- *Erzeugt es Aufregung?* — Ja: Der Betrachter sieht als **Erstes** die schiere Menge des erschlossenen
  Wissens („23 Dokumente im Wissensspeicher") und wie ein einziges Stichwort quer durchs Haus greift.
  Genau das „mein Unternehmen besitzt das alles bereits"-Gefühl, am stärksten möglichen Ort platziert.
- *Versteht ein CFO/CEO den Nutzen?* — Ja: erst *„so viel liegt schon da"*, dann *„und ich kann es
  einfach fragen"*. Der Such-Beat und die Frage-Sequenz erzählen zusammen eine geschlossene Geschichte.
- *Schwächste Stelle → nächster Zyklus:* Mechanik, Politur und Choreografie sind rund; der letzte Hebel
  ist **inhaltliche Dichte** — ein weiterer authentischer, quervernetzter Beleg-Vorgang (Demo-Firma 81 %).
  Siehe oben.
