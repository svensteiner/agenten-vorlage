# CHANGELOG — Kundendemonstrations-Prototyp

Alle sichtbaren Änderungen am Demo-Prototyp. Neueste zuerst.

## Zyklus 13 — 2026-07-08 — Zweite E-Mail (interne Weiterleitung) → Entscheidungskette quer durch Postfächer ✉→✉

**Von der einzelnen E-Mail zum belegten E-Mail-Thread.** Zyklus 12 brachte das E-Mail-Skin und die
auslösende Lieferanten-E-Mail. Jetzt zeigt die Demo, wie AI Studio eine **Entscheidungskette über
zwei Postfächer** rekonstruiert: Lieferant → Einkauf → CFO → Vorstandsbeschluss.

### Neu (rein additiv in `data.js` — kein Code-Umbau, Skin existiert bereits)
- **Neues Dokument `email-weiterleitung-materialbudget`** (Typ **„E-Mail"**, Modul Finanzen):
  **WG-Weiterleitung** der Donau-Preis-E-Mail von **Thomas Krüger (Einkauf)** an **Dr. Katharina
  Vogel (CFO)**, Cc Projektleitung Alpha, vom 13.02.2026. Enthält die **Bewertung des Einkaufs**:
  ~640 t Jahresbedarf × +120 €/t → **rund 0,9 Mio. € Mehrbedarf** für Projekt Alpha, plus die
  **Empfehlung**, das Mehrbudget als Vorstands-Beschlussvorlage einzubringen und Ferro Nord zu
  beschleunigen. **Zitat-Verlauf** = die Original-Donau-E-Mail (Andreas Huber) → sichtbarer Thread.
- **Verzahnt mit der bestehenden Story:** die 0,9 Mio. € stammen genau aus dem
  **Vorstandsbeschluss TOP 2** (`vorstandsprotokoll-2026-03`) — die Weiterleitung ist die
  **Herkunft dieser Zahl**. Kein neuer Wert, sondern der fehlende Beleg der Entscheidungskette.
- **In zwei Szenarien eingewoben:**
  - „**Warum sind die Materialkosten gestiegen?**" — E-Mail als **3. Quelle** (81 %), in „Verwandte
    Dokumente" und als zusätzlicher Reasoning-Schritt (Einkauf → CFO, 0,9 Mio. €).
  - „**Fasse Projekt Alpha zusammen.**" — E-Mail als Quelle für die **Herkunft des Mehrbudgets**
    (Reasoning: Lieferanten-E-Mail → Weiterleitung an CFO → Vorstandsbeschluss).
- Bestehende Dokumente, Skins und der Antwortpfad **unverändert**.

### Verifikation (deterministisch via Node-VM gegen `data.js`)
- **21 Dokumente** (war 20), davon **2 E-Mails** (`email-preisanpassung-donau`,
  `email-weiterleitung-materialbudget`), **11 Szenarien**.
- **0 kaputte Referenzen** über alle `sources` / `related` / `withheld` / `MODULE_SUGGESTIONS`.
- Neue E-Mail nutzt das identische Feldschema (`from`/`to`/`cc`/`subject`/`sent`/`attachment`/
  `quoted`) → `buildPaper()`-`cat==="email"`-Zweig rendert Postfach-Kopf + Zitat automatisch.

## Zyklus 12 — 2026-07-08 — E-Mail-Skin im Viewer + Lieferanten-E-Mail als Beleg der Materialkosten-Story ✉

**„Wissen steckt in E-Mails" ist jetzt im Bild.** Die Mission-Story nennt E-Mails ausdrücklich als
Ort, an dem Firmenwissen gefangen ist — im Viewer gab es dafür kein eigenes Skin. Dieser Zyklus
schließt die Lücke mit einem authentischen Postfach-Look **und** verankert die E-Mail als
auslösenden Beleg der stärksten bestehenden Story (Materialkostenanstieg).

### Neu (rein additiv in `data.js` / `app.js` / `styles.css`)
- **Neues Dokument `email-preisanpassung-donau`** (Typ **„E-Mail"**, Modul Finanzen): die
  Original-Ankündigung von **Stahlwerk Donau** über die 15-%-Preisanpassung auf Baustahl S355 zum
  01.03.2026 — 800 € → 920 € (**+15 %** = Preisgleitklausel §6 des Rahmenvertrags RV-2023-014).
  Cc an die CFO, **Anhang-Chip** „Preisliste_2026_Stahlwerk-Donau.pdf · 148 KB", **Zitat-Verlauf**
  der vorherigen Einkaufs-Anfrage.
- **E-Mail-Skin** `DOC_SKINS["E-Mail"] = { cat: "email" }`: Postfach-Kopf mit Avatar-Initialen
  (Verlauf Cyan→Indigo), **Von/An/Cc/Betreff/Gesendet**-Zeilen (Betreff fett), Anhang-Chip und
  zitiertem Verlauf (linker Balken). Neue Helfer `buildMailHead()` / `buildQuoted()` / `mailRow()`;
  `buildPaper()` verzweigt für `cat === "email"`. **✉-Icon** für E-Mail-Karten in der Bibliothek.
- **In die Materialkosten-Story eingewoben:** E-Mail als **2. Quelle** (88 %) der Antwort „Warum
  sind die Materialkosten gestiegen?", in „Verwandte Dokumente" und als zusätzlicher Reasoning-
  Schritt → **klickbar in der Geführten Demo**, Skin erscheint automatisch im Video.
- Bestehende Skins, Dokumente und der Antwortpfad **unverändert**.

### Verifikation (im Browser, DOM/CSS-basiert)
- Finanzen-Bibliothek: E-Mail-Karte mit **✉-Icon** + Typ „E-Mail" (5 Karten gesamt).
- Viewer: `paper paper-email`, Postfach-Kopf mit Initialen **„AH"**, 5 Zeilen (Betreff `font-weight
  700`), Anhang-Chip „Preisliste_2026_Stahlwerk-Donau.pdf / 148 KB", **2 Highlights**, Zitat-Verlauf
  mit **3 Zeilen**.
- Datenintegrität: **0 kaputte Referenzen** über alle Szenarien, 20 Dokumente; Materialkosten-Quelle
  + Verwandte + Reasoning enthalten die E-Mail. Keine Konsolenfehler.
- *Layout-Maße im Headless-Preview nicht messbar (0×0-Viewport, bekannte Harness-Grenze); CSS parst
  und greift, spiegelt das bewährte `.lh`-Briefkopf-Flexmuster.*

---

## Zyklus 11 — 2026-07-08 — Bewegungs-Politur: gestaffelter Block-Reveal + Modulwechsel-Fade ✨

**Die Demo läuft jetzt flüssig — die Antwort baut sich souverän auf, statt zu springen.** Inhaltlich
war die Story komplett; die härteste verbleibende Kante war das etwas sprunghafte Ein-/Umblenden.
Diese reine Wahrnehmungs-Politur hebt die gefühlte Produktreife auf „fertig" — ohne inhaltliches
Risiko.

### Neu (rein additiv in `styles.css` + kleiner Helfer in `app.js`)
- **Gestaffelter Block-Reveal:** die strukturierten Blöcke unter jeder Antwort
  (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) blenden **nacheinander** ein
  (neue Keyframe `block-rise`, Fade + 9 px Slide-up, ~0,42 s). `revealBlocks()` vergibt je Block
  eine additive Verzögerung **+55 ms** über die CSS-Variable `--rev-delay` — die Antwort „wächst"
  von oben nach unten.
- **Sanfter Modulwechsel:** der neu gerenderte Panel-Inhalt (`.wrap`) blendet dezent ein (neue
  Keyframe `view-in`, Fade + 7 px Slide-up, ~0,32 s) beim Wechsel Wissen ↔ Finanzen/Audit/HR/
  Verträge/Berichte/Einstellungen. Feuert nur beim View-Render; die Chat-Antworten behalten ihre
  eigene `.msg`-`rise`-Animation.
- **Fail-safe:** `prefers-reduced-motion: reduce` deaktiviert **beide** Effekte sauber
  (`revealBlocks()` steigt früh aus, CSS setzt `animation: none`). Startopazität liegt nur im
  Keyframe → ohne Animation bleiben alle Blöcke voll sichtbar (opacity 1), **kein Risiko
  unsichtbarer Inhalte**.
- `data.js` und der bestehende Antwortpfad **unverändert**.

### Verifikation (deterministisch im Browser)
- Normalbrowser (no-preference): `.block.reveal` → `animationName: block-rise`, `--rev-delay:110ms`
  → aufgelöst als `animation-delay: 0,11 s` (Stagger greift).
- Reduzierte Bewegung (Preview-Umgebung): `animationName: none` bei `opacity: 1` — sichere
  Fallback-Darstellung ohne unsichtbare Blöcke.
- Alle drei neuen CSS-Regeln (`view-in`, `block-rise`, `.block.reveal`) im geladenen Stylesheet
  bestätigt. (Streaming-Vollpfad im Headless-Preview durch Timer-Throttling zu langsam für Live-
  Beobachtung → mechanisch/deterministisch geprüft.)

## Zyklus 10 — 2026-07-08 — Handlungs-Abschluss: „An Vorstand senden" / „Als Briefing exportieren" ✉

**Die Demo schließt jetzt die Nutzer-Story „Frage → belegte Antwort → weiterreichbares Ergebnis".**
Bisher endete jede Antwort informativ, aber ohne den Moment, den ein Entscheider als Nächstes
denkt: „und dann?". Neu erscheint unter jeder belegten Antwort ein Aktions-Block **„↗ Ergebnis
weiterreichen"** mit zwei Buttons — der letzte fehlende Baustein und ein starker Video-Schluss.

### Neu (rein additiv in `app.js` / `styles.css`)
- **Primär-Button „✉ An Vorstand senden"** und Sekundär-Button **„⤓ Als Briefing exportieren"**
  im Antwortkopf-Fuß (nach den Folgefragen). Klick zeigt eine kurze Vorbereitungs-Phase
  („Briefing wird zusammengestellt…" / „PDF wird erzeugt…", Spinner ~0,8 s) und morpht dann in
  eine **grüne Erfolgs-Bestätigung** mit ✓-Badge:
  - Senden: „**Briefing an den Vorstand gesendet** · Empfänger: Vorstand · Meridian Industrie
    GmbH · soeben · Ref. BRF-2026-XXXX".
  - Export: „**Briefing als PDF exportiert** · meridian-briefing-2026-XXXX.pdf · <Datum>".
- **Deterministische Briefing-Nummer** (`briefingNumber()`, Hash aus Antwortinhalt + Konfidenz) —
  im Video reproduzierbar, konsistent mit dem Tempo-Signal aus Zyklus 8 (keine Zufallszahl).
- **Fail-safe/ehrlich:** Der Aktions-Block erscheint **nur bei belegten Antworten** (mind. eine
  Quelle) — ein leerer „kein Treffer"-Fallback bietet kein Briefing an. Rein UI: **keine echten
  Mails/Exporte**, nur eine überzeugende Bestätigung.
- **Politur:** Pop-Animation der Bestätigung, `prefers-reduced-motion` respektiert (Animation aus,
  Vorbereitungs-Delay 0). `data.js` und der bestehende Antwortpfad unverändert.

### Verifikation (live im Browser, text-basiert)
- Aktions-Block rendert an korrekter Position (nach „➜ Folgefragen"), beide Buttons vorhanden,
  Primär-Button in Marken-Indigo (#4f46e5) mit weißer Schrift.
- Klick „An Vorstand senden" → Spinner-Phase → grüne Bestätigung (Ref. BRF-2026-5602, Empfänger-
  Zeile korrekt). Export-Zweig symmetrisch. Keine Konsolenfehler.
- (Screenshot-Capture im Harness weiterhin instabil → DOM/CSS-basiert verifiziert.)

## Zyklus 9 — 2026-07-08 — Ressort-Breite: HR-Onboarding & Lieferanten-/Klumpenrisiko 🧭

**Zwei neue, glaubwürdige Szenarien holen zwei zusätzliche Entscheider-Ressorts ins Publikum.**
Die Demo deckte bisher Finanzen, Audit, Verträge, Berichte/ESG und Governance ab. Jetzt kommen
**HR-Onboarding** („Was muss ein neuer Mitarbeiter am ersten Tag erledigen?") und
**Beschaffungs-/Risikoanalyse** („Wie abhängig sind wir von unserem größten Lieferanten?") dazu —
zwei Fragen, bei denen HR-Leitung und CFO/Einkauf sofort „das ist genau mein Problem" denken.
Die „Geführte Demo" nimmt beide **automatisch** auf (jetzt 11 Szenarien).

### Neu (rein additiv in `data.js` — kein Code-Umbau)
- **Szenario „Onboarding, erster Tag"** (Modul HR): Antwort als Schritt-für-Schritt-Checkliste
  (Empfang, Werksausweis, IT-Zugänge, **Pflicht-Sicherheitsunterweisung**, Pflichtdokumente,
  Pate). Quellen: neue **Onboarding-Checkliste** (98 %) + Querverweis **Reiserichtlinie 2026**
  (68 %). Konfidenz 96 %.
- **Szenario „Lieferanten-/Klumpenrisiko"** (Modul Finanzen): Antwort mit **Konzentrations-
  Tabelle** (Stahlwerk Donau AG 23,9 % · Siemens 11,6 % · Robotik Bayern 8,2 %) und der
  kritischen **Single-Source-Warnung** für Baustahl S355; Gegenmaßnahme Ferro Nord (Vorstands-
  beschluss). Quellen: neue **Lieferanten-Risikoanalyse 2026** (97 %) + Vorstandsprotokoll (80 %)
  + Rahmenvertrag (72 %). Konfidenz 94 %.
- **Neues Doc `onboarding-checkliste-2026`** (Typ „Checkliste", HR) — 8 Absätze, 4 Highlights.
- **Neues Doc `lieferanten-risikoanalyse-2026`** (Typ „Risikobericht", Finanzen) — mit
  `lineItems`-Tabelle „Top-Lieferanten nach Einkaufsvolumen 2025" (5 Positionen, Anteile).
- **Wiring:** Hero-Vorschläge 6 → 8, Modul HR (2) und Finanzen (3) ergänzt.

### Konsistenz (bewusst mit bestehender Story verzahnt)
- Größter Lieferant = **Stahlwerk Donau AG** (bereits Materialkosten-/Rechnungs-Story); Zweit-
  quelle **Ferro Nord** = derselbe Vorstandsbeschluss wie im Governance-/Strategie-Szenario.
- Einkaufsvolumen 268 Mio. € plausibel zum Umsatz 612 Mio. €; Donau 64 Mio. € = 23,9 %.

### Funktioniert (live im Browser verifiziert, throttle-immun text-basiert)
- Datenintegrität: 11 Szenarien, 8 Hero-Kacheln, **0 kaputte Quell-/Related-Referenzen**.
- Beide Hero-Kacheln erscheinen; Antwortkopf mit Tempo-Signal „2,3 s" + Konfidenz 94 % rendert.
- Finale Antwort-HTML deterministisch geparst: Lieferanten-Tabelle mit Kopf
  `[Lieferant · Volumen 2025 · Anteil]` + 3 Datenzeilen; Onboarding als Liste. Alle Quell-/
  Related-IDs lösen auf echte Dokumenttitel auf (Viewer-Links funktionieren). Keine Konsolenfehler.
- Hinweis: Live-Streaming-Endzustand im Hintergrund-Tab durch Timer-Throttling (`setTimeout`)
  nicht abfilmbar — Verifikation daher über finalen Render-Pfad, identisch zu den 8 bewährten
  Szenarien.

## Zyklus 8 — 2026-07-08 — Video-Politur: „Beantwortet in X,X s"-Signal + Zahlen-Hochzählen ⚡

**Die Demo fühlt sich jetzt schnell und „live" an — die letzte Politur fürs Verkaufsvideo.**
Jede Antwort trägt im Kopf ein **Tempo-Signal „⚡ Beantwortet in 1,9 s"**, das direkt beim
Erscheinen von 0 hochzählt, und die **Kernzahlen im Antworttext** (18,4 %, 87.584 €, -30,0 % …)
**zählen dezent hoch**, sobald die Antwort fertig getippt ist. Das erzeugt genau den Eindruck
von Geschwindigkeit und Souveränität, der in einem CEO/CFO-Video zählt — ohne den Antwortpfad
umzubauen.

### Neu (rein additiv in `app.js` / `styles.css`)
- **Tempo-Signal im Antwortkopf** (`.speed` „⚡ Beantwortet in <b>X,X s</b>") links vom
  Konfidenz-Meter. Wert ist **deterministisch** aus Antwortumfang (Quellen, Textlänge, Tabelle)
  im schnell wirkenden Fenster **1,2–2,6 s** → im Video reproduzierbar, keine Zufallszahl.
- **Count-up der Kernzahlen:** neue `animateCounts()` scannt die **fett gesetzten** Zahlen und
  zählt sie per `requestAnimationFrame` (easeOutCubic, ~760 ms) hoch. `parseGermanNumber()`
  erkennt deutsche Formate (Dezimalkomma, Tausenderpunkt, Einheit % € t „Mio. €" GWh …).
- **Sicher gegen Fehl-Animation:** verlangt Dezimalkomma **oder** Einheit → **Jahre (2026),
  Datumsangaben (28.02.2026), PO-Nummern (PO-2026-0512)** bleiben unangetastet. `tabular-nums`
  während des Zählens verhindert Breiten-Zittern; `prefers-reduced-motion` → Endwerte sofort.

### Funktioniert (live im Browser verifiziert, text-basiert)
- Tempo-Signal rendert und zählt auf „1,9 s" (Materialkosten-Szenario).
- Parser exakt gegen alle realen fett-Zahlen geprüft: alle Kernwerte animieren, alle
  Jahre/Datum/PO-Nummern korrekt ausgeschlossen; German-Format (87.584, 18,4, -30,0) korrekt.
- Count-up-Mechanismus auf realem Antwort-Fragment: Zwischenframe → korrekter Endwert im DOM.
- Keine Konsolenfehler. (Screenshot-Capture im Harness weiter instabil → text-basiert verifiziert.)

## Zyklus 7 — 2026-07-08 — Vertrauens-Story: gesperrtes Dokument + „für Sie nicht freigegeben" 🔒

**Die Demo zeigt jetzt sichtbar, dass Berechtigungen respektiert werden — das große fehlende
Wow-Thema für skeptische Entscheider.** Zwei bewusst **gesperrte Dokumente** (M&A-
Akquisitionsvorlage „Projekt Nordstern", Vorstandsvergütung 2026) erscheinen im Modul Berichte
**ausgegraut mit Schloss** und „Kein Zugriff — Vorstand". Ein neues 9. Szenario „Was hat der
Vorstand für die Wachstumsstrategie beschlossen?" beantwortet nur die **freigegebenen**
Beschlüsse und zeigt darunter das Governance-Signal **„2 weitere Treffer für Sie nicht
freigegeben"**. Das beantwortet die CFO/Compliance-Frage „Sieht jeder alles?" in Sekunden und
differenziert AI Studio von „ChatGPT auf unseren Dateien".

### Neu (rein additiv in `data.js` / `app.js` / `styles.css`)
- **2 gesperrte Dokumente** (`locked: true`, `lockedRole`, `classification`, **kein `body`**) —
  Inhalt bleibt strukturell unsichtbar, nicht nur ausgeblendet.
- **Bibliothek:** gesperrte Karte gestrichelt/ausgegraut, Schloss-Icon, rotes
  „🔒 Kein Zugriff — <Rolle>". Klick öffnet statt Inhalt eine **„Zugriff verweigert"-Ansicht**
  im Viewer (Klassifizierung, Freigabe-Rolle, Eigentümer; Inhalt verborgen).
- **Neues 9. Szenario** `strategie-ausblick` mit optionalem `answer.withheld`-Feld →
  neuer Antwort-Block `appendWithheld()`: „N weitere Treffer für Sie nicht freigegeben",
  Klassifizierungs-Tag, Erklärsatz und **anklickbare gesperrte Treffer** (öffnen die
  Zugriff-verweigert-Ansicht).
- **„Geführte Demo"** deckt automatisch alle 9 Szenarien ab (Zähler dynamisch aus `SCENARIOS`).

### Funktioniert (live im Browser verifiziert, text-basiert)
- 2 gesperrte Karten im Modul Berichte, korrekte Rollen-Labels.
- Klick auf gesperrtes Dokument → „Zugriff verweigert", **kein Inhalt** geleakt; Meta zeigt
  Klassifizierung/Freigabe/Eigentümer.
- Strategie-Szenario als Hero-Vorschlag vorhanden; Antwortpfad unverändert.
- Withheld-Block wird nach den Quellen eingeblendet (identisches Muster wie `appendSources`).

## Zyklus 6 — 2026-07-08 — Onboarding-Overlay beim ersten Start 👋

**Der erste Video-Eindruck ist jetzt geführt statt leer.** Beim ersten Laden erscheint ein
leichtgewichtiges Coachmark oben rechts, dessen Pfeil exakt auf den „▶ Geführte Demo"-Button
zeigt — der Button pulsiert dazu dezent. Headline in einem Satz („Fragen Sie alles über Ihr
Unternehmenswissen") plus ein Primär-Button, der das Overlay schließt **und die Vorführung
sofort startet**: ein starker Opener fürs Verkaufsvideo (ein Klick → alles läuft automatisch).

### Neu (rein additiv in `index.html` / `styles.css` / `app.js`)
- **Onboarding-Coachmark** (`#onboard`) — abgedunkelter Backdrop + Karte mit Spark-Icon,
  Headline, Erklärtext und zwei Aktionen: **„▶ Geführte Demo starten"** (schließt + startet
  `startDemo()`) und **„Selbst erkunden"** (schließt nur).
- **Pfeil zielt auf den Button** (Offset 270 px = Buttonmitte 298 px vom rechten Rand −
  Kartenrand 28 px), im Browser auf ±10 px verifiziert. Der Demo-Button erhält währenddessen
  die Klasse `.hi` und **pulsiert**.
- **Nur einmal:** `localStorage`-Flag `aistudio.onboarded.v1` (try/catch → unter `file://`
  ohne Storage läuft es sauber weiter, erscheint dann bei jedem Laden).
- **Schließen** per Skip-Button, Klick auf den Backdrop oder **Esc**.
- **`prefers-reduced-motion`** respektiert (keine Animationen für empfindliche Nutzer).

### Funktioniert (live im Browser verifiziert, text-basiert)
- Overlay sichtbar beim ersten Laden, Pfeil auf ±10 px am Button, Button pulsiert.
- Skip setzt das Flag → nach Reload erscheint das Overlay **nicht** mehr.
- Primär-CTA schließt das Overlay und startet die Geführte Demo (Fortschritt „1 / 8",
  Composer gesperrt, Frage wird getippt).
- Keine Konsolenfehler. `data.js` und der Antwortpfad blieben unverändert.

## Zyklus 5 — 2026-07-07 — ESG/CO₂-Szenario: Breite über Finanzen hinaus 🌱

**Die Demo spricht jetzt auch Vorstands-/Aufsichtsratssprache.** Ein neues 8. Szenario
„Wie hat sich unser CO₂-Fußabdruck entwickelt — sind wir auf ESG-Kurs?" hebt die Demo von
„Buchhaltungs-Trick" auf **Nachhaltigkeit & Governance**. Die Antwort zeigt einen echten
**CO₂-Reduktionspfad als Tabelle** (2020 → 2025 → Ziel 2030) und legt die Lücke zum
linearen Zielpfad **ehrlich offen** (-12 % ist vs. -15 % Pfad) statt sie zu beschönigen —
genau der glaubwürdige, entscheidungsreife Ton, der einen CEO/CFO überzeugt.

### Neu (rein additiv in `data.js`, kein Code-Umbau)
- **Neues Szenario `esg-co2`** (Modul Berichte) — Antwort mit **Trend-Tabelle**
  (Jahr · CO₂ Scope 1+2 · ggü. 2020), erneuerbarem Stromanteil, benannter Ziel-Lücke und
  Handlungshebeln bis 2030; Konfidenz 92 %, 3 Quellen (97/93/76 %), 4 Nachvollziehbarkeits-
  schritte, 2 Folgefragen.
- **Neues Belegdokument `energie-emissionsbericht-2025`** („Energie- & Emissionskennzahlen
  2025", Typ Kennzahlenbericht) — CO₂-Trend 2020–2025, Zielwert 2030 (32.760 t / -30 %),
  Stromverbrauch/Energieintensität, Reduktionshebel. Rendert im Viewer als `paper-bericht`.
- **`esg-bericht-2025` vertieft** — von 2 auf 6 Absätze: Scope-1/2-Aufteilung
  (12.400 t / 28.800 t), erneuerbarer Anteil 68 % (Vorjahr 61 %), Zielpfad-Bewertung,
  Soziales & Governance (Unfallquote, Frauenanteil Führung, Lieferanten-Kodex).
- **Zahlenkonsistenz geprüft:** 41.200 t (2025) = -12,0 % ggü. Basis 46.800 t (2020);
  Ziel 2030 = 46.800 × 0,70 = 32.760 t; verbleibend 8.440 t. Über alle 3 Quellen identisch.
- **Wiring:** `esg-co2` in Hero-Vorschlägen (`wissen`) und im Modul `berichte`. Die
  „Geführte Demo" nimmt das 8. Szenario **automatisch** auf (7 → 8).

### Funktioniert (live im Browser verifiziert, text-basiert)
- Frage → gestreamte Antwort mit **5-zeiliger Trend-Tabelle**, alle 4 Blöcke
  (Nachvollziehbarkeit · Quellen 3 · Verwandte Dokumente 3 · Folgefragen 2), Konfidenz 92 %.
- Quellen-Relevanzen 97 / 93 / 76 %; alle Quellen & verwandten Dokumente lösen auf.
- Klick auf Quelle „Energie- & Emissionskennzahlen 2025" → Viewer öffnet `paper-bericht`
  mit 3 hervorgehobenen KPI-Absätzen. Keine Konsolenfehler.
- (Screenshot-Capture im Harness weiterhin instabil → DOM/CSS-Prüfung wie in Zyklus 4.)

## Zyklus 4 — 2026-07-07 — Rechnungs-Positionstabelle im Beleg-Skin 🧾

**Belege zeigen jetzt eine echte Positionszeilen-Tabelle statt Fließtext.** Rechnung,
Bestellung und Wareneingang öffnen im Viewer mit einer prüfungsechten Buchungstabelle
(Pos. · Bezeichnung · Menge · Einzelpreis · Summe) samt Netto/USt/Brutto-Fußzeile. Das
ist der stärkste **„das ist echte Buchhaltung"-Moment** für einen CFO im Video: der
**Drei-Wege-Abgleich** (Szenario 3) zeigt jetzt sichtbar übereinstimmende Positionen und
Beträge über alle drei Belege.

### Neu
- **`buildLineItems()`** in `app.js` (+ `footRow`) — rendert eine `.li-table` nur für die
  `beleg`-Kategorie, wenn `doc.lineItems` gesetzt ist. Netto/USt/Brutto-Fußzeilen sind
  **optional** (nur gerendert, wenn im Datensatz vorhanden). Alle Werte HTML-escaped.
- **`.li-table`-Styling** in `styles.css` — rechtsbündige, tabellarische Zahlen
  (`tabular-nums`), Ober-/Unterlinien, hervorgehobene Brutto-Endsumme.
- **Optionales `doc.lineItems`-Feld** in `data.js` für die 3 Belege — Fallback = bisheriger
  Fließtext, wenn nicht gesetzt (bestehende Dokumente unverändert).
  - Rechnung 2026-1843: 80,000 t Baustahl S355 · 920,00 € · Netto 73.600 € · USt 19 %
    13.984 € · **Brutto 87.584 €**.
  - Bestellung PO-2026-0512: identische Position · nur Netto 73.600 €.
  - Wareneingang WE-2026-0778: identische Position · Einzelpreis „—" · Summe „vollständig",
    keine Betrags-Fußzeile.
- **Korrektur:** Rechnungs-Snippet-Brutto von falsch „84.640 €" auf konsistente
  **„87.584 €"** (= 73.600 € × 1,19) gesetzt — die Tabelle hätte die Abweichung sichtbar
  gemacht.

### Funktioniert (live im Browser verifiziert)
- Rechnung → Positionszeile + Fußzeile Netto/USt 19 %/Brutto; Brutto-Endsumme fett (800),
  rechtsbündig, dunkel. Header-Labels korrekt uppercase/faint.
- Bestellung → identische Position, nur **Netto**-Fußzeile (keine USt/Brutto).
- Wareneingang → identische Position, **keine** Betrags-Fußzeile.
- Mengen (80,000 t) und Netto (73.600 €) stimmen über alle drei Belege überein → Abgleich schlüssig.

## Zyklus 3 — 2026-07-07 — „Geführte Demo" (hands-free Auto-Play) ▶

**Ein Klick spielt die komplette Demo selbst ab.** Ein prominenter Play-Button in der
Topbar tippt jede der 7 Beispielfragen sichtbar in den Composer, lässt die Antwort
streamen, pausiert kurz und geht zur nächsten — vollständig ohne Bedienung. Perfekt für
die **Videoaufnahme** (keine Mausbewegungen/Tippfehler im Bild) und für einen
**Messestand-/Empfangs-Loop**, der Kunden ohne Bediener überzeugt.

### Neu
- **Play-Button „Geführte Demo"** in der Topbar (`#demoBtn` in `index.html`, `.demo-btn`
  in `styles.css`) — Markenfarbe, wird im Lauf zu „⏹ Demo stoppen".
- **Fortschritts-Indikator** „Szenario n / 7" (`#demoProgress`) direkt im Button.
- **Auto-Play-Orchestrierung** (`startDemo`/`stopDemo`/`typeIntoComposer` in `app.js`):
  Chat wird frisch am Hero gestartet, Frage wird Zeichen für Zeichen „getippt", dann läuft
  der bestehende `ask()`-Flow, danach eine Lesepause. Jederzeit per Klick stoppbar
  (Token-Mechanik lässt die laufende Schleife sauber aussteigen).
- Composer ist während der Demo gesperrt (readonly) und manuelles Senden ist geblockt,
  damit sich nichts überlagert.
- **Rein additiv** — keine Änderung an `data.js` und am bestehenden `ask()`-Antwortpfad.

### Funktioniert (live im Browser verifiziert)
- Start → Button „⏹ Demo stoppen", Fortschritt „1 / 7", Composer gesperrt.
- Frage tippt sich sichtbar in den Composer, danach streamt die bestehende Antwort.
- Stopp → voller Reset (Button „▶ Geführte Demo", Fortschritt aus, Composer wieder frei).

## Zyklus 2 — 2026-07-07 — Dokument-Skins im Viewer 📄

**Der Dokumentenviewer zeigt jetzt echte Dokumente statt Textabsätzen.** Jede Quelle
wird als Papierblatt auf einem Schreibtisch dargestellt — der stärkste Vertrauens-Trigger
für nicht-technische Entscheider: „Das System öffnet mein tatsächliches Dokument."

### Neu
- **Papier-Darstellung pro Dokumenttyp** (`buildPaper` in `app.js`, `.paper*` in `styles.css`):
  - **Briefkopf** mit Logo-Initialen, Aussteller und Referenzblock (Typ · Titel · Datum).
    Bei Eingangsrechnungen ist der Aussteller korrekt der **Lieferant** (z. B. „Stahlwerk Donau AG").
  - **Belege** (Rechnung/Bestellung/Wareneingang) erhalten einen rotierten **Stempel**
    (EINGANG · GENEHMIGT · GEPRÜFT).
  - **Verträge** erhalten eine **Ort/Datum-Zeile + zwei Unterschriftszeilen** (beide Parteien).
  - **Prüfnachweise** (Feuerbeschau) erhalten einen grünen **BESTANDEN**-Stempel.
  - **Klausel-Marken** (§9, Teil B §5, TOP 1) werden im Fließtext hervorgehoben.
  - Die **gelben Highlights liegen jetzt IM Dokument-Layout** statt in einer Textliste.
- Rein CSS/HTML, datengetrieben aus `doc.type` — **keine Änderung an `data.js` nötig**,
  neue Dokumente bekommen ihr Skin automatisch.

### Funktioniert (live im Browser verifiziert)
- Rechnung 2026-1843 → `paper-beleg`, Lieferant-Briefkopf, EINGANG-Stempel, 3 Highlights im Blatt.
- Rahmenvertrag → `paper-vertrag`, §9-Klauselmarke, Unterschriftszeilen (Meridian · Dr. Elena Wagner).
- Feuerbeschau → `paper-nachweis`, grüner BESTANDEN-Stempel (rotiert).
- Quartalsbericht → sauberer Briefkopf-Fallback (`paper-bericht`).

## Zyklus 1 — 2026-07-07 — Prototyp-Bootstrap 🎉

**Der Kunden-Demo-Prototyp existiert jetzt.** (Zuvor: 31 Zyklen ausschließlich
`platform/`-Architektur-Dokumentation — nicht Teil dieser Mission.)

### Neu
- **`prototype/`** — self-contained, buildfreie Enterprise-Web-App (Vanilla-JS, `file://`-fähig).
  - `index.html` — App-Rahmen: Seitenleiste (7 Module), Chat, Composer, Dokumentenviewer.
  - `styles.css` — Enterprise-Design (Stripe/Linear/Notion-Anmutung), responsiv.
  - `data.js` — fiktive **„Meridian Industrie GmbH"** + **15 Dokumente** + **7 Szenarien**.
  - `app.js` — Chat-Logik: gestreamte Antworten, Retrieval-Schritte, Quellen-Rendering,
    Dokumentenviewer, Modul-/Bibliotheks-Ansichten, ehrlicher Fallback bei freien Fragen.
  - `README.md` — Start- und Demo-Anleitung.
- **Handover-Dateien** im Wurzelverzeichnis: `NEXT_STEPS.md`, `PROGRESS.md`, `CHANGELOG.md`,
  `IDEAS.md`, `VIDEO_SCRIPT.md`, `VIDEO_SCENES.md`, `OPEN_ITEMS.md`, `FUTURE_BACKLOG.md`.

### Funktioniert (live im Browser getestet)
- Frage stellen → gestreamte Antwort mit Konfidenz-Meter.
- Antwort enthält: Nachvollziehbarkeit, Quellen (Zitat + Relevanz %), verwandte Dokumente, Folgefragen.
- Klick auf Quelle/verwandtes Dokument → Dokumentenviewer mit Metadaten + hervorgehobenen Belegstellen.
- Modulwechsel zeigt gefilterte Dokumentenbibliothek + Vorschlagsfragen.

### Bewusst nicht angefasst
- `platform/` (Architektur-Doku) und `core/` (Agenten-Runtime) — geschütztes IP, unverändert.
