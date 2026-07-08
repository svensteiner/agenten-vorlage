# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 10 — **Handlungs-Abschluss: „An Vorstand senden" / „Als Briefing
  exportieren"** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-08.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 70 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**Sanfte Übergänge (Fade/Slide) für Modulwechsel und einblendende Antwortblöcke.** Inhalt, Tiefe,
Vertrauen, Tempo, Ressort-Breite **und** der Handlungs-Abschluss stehen jetzt. Der stärkste
verbleibende Video-Hebel ist reine **Bewegungs-Politur**: Modulwechsel und das Erscheinen der
strukturierten Blöcke (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) wirken
aktuell etwas „hart". Ein dezenter, gestaffelter **Fade-/Slide-in** (je Block ~40–60 ms versetzt,
`prefers-reduced-motion` respektiert) lässt die Antwort **souverän aufbauen** statt springen — im
Video der Unterschied zwischen „Prototyp" und „fertiges Produkt". Rein additiv in `styles.css`
(ggf. minimale Klassen-Vergabe in `app.js`); `data.js` und der Antwortpfad unverändert.

*Warum diese?* Die Erzählung ist inhaltlich **komplett** (Frage → belegte Antwort → weiterreichbares
Ergebnis). Was bleibt, ist Feinschliff der Wahrnehmung: flüssige Bewegung erhöht das gefühlte
Qualitätsniveau ohne inhaltliches Risiko — genau der letzte 5 %-Politur-Schritt für die Kamera.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md)
(weitere Beleg-Skins z. B. E-Mail/Memo, ein weiteres Ressort z. B. IT/Datenschutz).

---

## CEO-Review (Ende Zyklus 10)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Story ist jetzt **rund**: Frage →
  belegte Antwort → sichtbares **Arbeitsergebnis** („An Vorstand senden"). Kein „und dann?" bleibt
  offen.
- *Erzeugt es Aufregung?* — Ja: der grüne „✓ Briefing an den Vorstand gesendet"-Moment ist ein
  starker, konkreter **Schlussframe** fürs Video — aus Auskunft wird Handlung in einem Klick.
- *Versteht ein CFO/CEO den Nutzen?* — Ja, sofort: „Ich frage, bekomme eine belegte Antwort und
  reiche sie mit einem Klick an den Vorstand weiter." Kein Wort über Technik.
- *Schwächste Stelle → nächster Zyklus:* **Bewegungs-Politur.** Inhaltlich ist die Demo komplett;
  die härteste verbleibende Kante ist das etwas sprunghafte Ein-/Umblenden — sanfte Übergänge
  heben die gefühlte Produktreife auf „fertig".
