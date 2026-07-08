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
- ✅ **„Antwort in X s"-Signal + Zahlen-Count-up** — *erledigt in Zyklus 8*: „⚡ Beantwortet in
  1,9 s" im Antwortkopf (zählt hoch) + fett gesetzte Kernzahlen zählen hoch (`animateCounts()`,
  sicher gegen Jahre/Datum/PO-Nummern). Tempo/Souveränität fürs Video.
- ✅ **Handlungs-Abschluss „An Vorstand senden" / „Als Briefing exportieren"** — *erledigt in
  Zyklus 10*: Aktions-Block „↗ Ergebnis weiterreichen" unter jeder belegten Antwort; Klick →
  Spinner → grüne Erfolgs-Bestätigung mit ✓-Badge + deterministischer Briefing-Nummer. Reine UI.
- ✅ **Sanfte, gestaffelte Übergänge** beim Einblenden der Antwortblöcke + Modulwechsel —
  *erledigt in Zyklus 11*: gestaffelter Block-Reveal (`block-rise`, +55 ms je Block via
  `--rev-delay`) + Modulwechsel-Fade (`view-in` auf `.wrap`), `prefers-reduced-motion` deaktiviert
  beide sauber (opacity 1). Rein additiv.
- ✅ **E-Mail-Skin im Viewer** — *erledigt in Zyklus 12*: neues Dokument
  `email-preisanpassung-donau` (Original-Ankündigung der Donau-Preisanpassung) im echten Postfach-
  Look — Von/An/Cc/Betreff/Gesendet-Kopf mit Avatar, Anhang-Chip, Zitat-Verlauf (`DOC_SKINS["E-Mail"]`,
  `buildMailHead()`/`buildQuoted()`). Als 2. Quelle in die Materialkosten-Story eingewoben. Belegt
  die Kern-Erzählung „Wissen steckt in E-Mails".
- ✅ **Zweite E-Mail (interne Weiterleitung Einkauf → CFO)** — *erledigt in Zyklus 13*: neues
  Dokument `email-weiterleitung-materialbudget` (WG der Donau-Preis-E-Mail, Krüger → Dr. Vogel,
  Cc Projektleitung Alpha) mit Bewertung 0,9 Mio. € Mehrbedarf + Empfehlung Vorstands-Beschlussvorlage;
  Zitat-Verlauf = Original-Donau-E-Mail (Thread). Belegt die **Entscheidungskette quer durch
  Postfächer** (Lieferant → Einkauf → CFO → Vorstand). Rein additiv in `data.js`.
- ✅ **Explizites Ketten-/Timeline-Element in der Antwort** — *erledigt in Zyklus 14*: neues Szenario
  `budget-herkunft` + Feld `answer.chain` und Renderer `appendChain()` (analog `appendWithheld()`):
  vertikale Timeline Lieferant → Einkauf → CFO → Vorstand, je Datum/Akteur/Label und anklickbarem
  Beleg, letzter Schritt hervorgehoben. Als erster Block unter der Antwort. Der stärkste CFO-Moment
  ist jetzt ohne Klickarbeit im Bild.
- ✅ **Timeline im Dokumentenviewer** — *erledigt in Zyklus 15*: Ketten-Navigator
  „⛓ Entscheidungskette · Schritt n von 3" mit Vor/Zurück + anklickbarem Stepper, erscheint
  automatisch bei den drei Ketten-Belegen. Kette entdoppelt zu `const DECISION_CHAIN` (einzige
  Quelle für Chat-Block **und** Viewer). Rein additiv.
- ✅ **DSGVO-/Datenschutz-Szenario (neues Ressort)** — *erledigt in Zyklus 16*: Szenario
  `datenschutz-audit` (Modul Audit, 93 %) mit Status-Tabelle (Art. 30/32/28/Betroffenenrechte/72-h-
  Meldeprozess, je ✓ / ⚠ 1 offen) + ehrlicher Auflagen-Offenlegung; zwei neue Dokumente
  (Datenschutz-Audit 2025 mit BESTANDEN-Stempel, Verzeichnis von Verarbeitungstätigkeiten Art. 30).
  Rein additiv in `data.js`. Öffnet ein Vorstands-relevantes Compliance-Ressort.
- ✅ **Globale Live-Suche (Command-Palette)** — *erledigt in Zyklus 17*: Sidebar-Auslöser
  „🔍 Alles durchsuchen" (+ Strg/⌘ + K) öffnet ein zentriertes Modal, das beim Tippen live über alle
  23 Dokumente filtert (Titel/Typ/Snippet/Autor/Modul); leeres Feld = komplettes Inventar, Live-Zähler
  „X von 23", Suchbegriff gelb markiert, ↑/↓+Enter-Navigation, Klick öffnet den Beleg im Viewer.
  Gesperrte Docs erscheinen ohne Inhalts-Leak. Rein additiv. Macht die schiere Menge des Wissens
  sichtbar.
- ✅ **Such-Beat als Opener der Geführten Demo** — *erledigt in Zyklus 18*: `startDemo()` ruft vor der
  Szenario-Schleife `demoSearchBeat(token)` — die Command-Palette öffnet automatisch („23 Dokumente"),
  tippt sichtbar „stahl" → 8 Treffer quer über Finanzen+Audit (`<mark>`), öffnet kurz einen freigegebenen
  Beleg im Viewer, schließt Palette+Viewer, *dann* die Frage-Sequenz. `resetDemoUi()` fail-safe. Macht die
  Menge des Wissens zum ersten Bild des Videos. Rein additiv in `app.js`.
- ✅ **Reklamations-/Mängel-Vorgang (Donau-Stahllieferung)** — *erledigt in Zyklus 19*: Szenario
  `reklamation-stahl` (Audit, 95 %) „Wie haben wir die mangelhafte Stahllieferung reklamiert?" +
  zwei Belege — `maengelruege-mr-2026-0091` (Typ „Mängelrüge", roter MÄNGELRÜGE-Stempel, §377 HGB,
  EN 10029) und `gutschrift-gs-2026-0203` (Typ „Gutschrift", Positionstabelle, 11.040 € netto /
  13.137,60 € brutto, grüner GUTSCHRIFT-Stempel). §12 Gewährleistung im Rahmenvertrag ergänzt. Zeigt
  den *Ausnahme*-Belegpfad als Gegenpol zum sauberen Drei-Wege-Abgleich. Rein additiv. Hero 10 → 11,
  Demo 13 → 14.
- ✅ **Konfidenz-Tooltip am Meter** — *erledigt in Zyklus 20*: Hover/Focus am Konfidenz-Meter öffnet ein
  Popover, das die Zahl aus den Quellen herleitet (Quellen herangezogen · höchste Relevanz ·
  Übereinstimmung einzeln/teilweise/hoch, je Mini-Balken; Fußzeile „Keine Behauptung — eine Ableitung aus
  konkreten Quellen."). Datengetrieben aus `answer.sources`, tastatur-erreichbar. Rein additiv in
  `app.js` (`buildConfPop()`) + `styles.css`.
- ✅ **Zweites Projekt „Beta"** — *erledigt in Zyklus 21*: Szenario `projekt-beta` (Berichte, 90 %) „Wie
  steht Projekt Beta?" — kundenspezifische Anlage für die Nordwind Logistik AG, bewusst **verzögert**
  (Ampel-Statustabelle, Pönale-Risiko, Gegenmaßnahmen, offener Kontrast zu Alpha „im Zeitplan"). Zwei
  neue Belege: `projekt-beta-status` (Projektbericht) + `eskalation-beta-elektronik` (E-Mail, zitierter
  Zulieferer-Verlauf) — beide über bestehende Skins, kein Code-Umbau. Rein additiv in `data.js`. Beweist,
  dass die Demo-Firma mehrere parallele Vorhaben trägt — und Risiken ehrlich kennzeichnet.
- ✅ **Projekt-Portfolio-Überblick** — *erledigt in Zyklus 22*: Szenario `projekt-portfolio` (Berichte,
  94 %) „Welche Projekte laufen aktuell?" stellt Alpha + Beta in **einer** Ampel-Übersichtstabelle
  gegenüber (Projekt · Fortschritt · Budget · Termin · Status), Portfolio-Volumen 32,6 Mio. €, ehrlicher
  Schluss „1 von 2 termingefährdet". Quellen = **beide bestehenden Statusberichte** (je 96 %) +
  Vorstandsprotokoll. Reuse `<table>`-Struktur, kein neues Dokument, kein Code-Umbau. Der „ganzes
  Portfolio auf einen Blick"-Moment; in der Geführten Demo direkt nach Alpha + Beta.
- **Drittes Beta-Dokument (Change-Request an Nordwind)** — Angebotsnachtrag über den Kunden-
  Änderungswunsch (+0,4 Mio. €, zusätzliche Prüfstation) mit `lineItems`; Reuse Beleg-Skin, in
  `projekt-beta` als Quelle einweben. Schließt Betas letzte unbelegte Zahl. *(Nächster Zyklus — Tiefe.)*
- **Kette an weitere Antworten hängen** — den `answer.chain`-Baustein (= `DECISION_CHAIN`) auch an die
  Materialkosten-Antwort (Einstiegs-Beat) anfügen, kein neuer Code. Video-Reihenfolge beachten
  (Kette erschiene zweimal). *(Tiefe-Option.)*
- **Konfidenz-/Relevanz-Meter mit-animieren** — die Prozent-Balken (Konfidenz, Relevanz je
  Quelle) beim Einblenden von 0 hochlaufen lassen, passend zum Zahlen-Count-up. *(Optional,
  nächste Feinpolitur.)*

## Mehr Substanz
- ✅ **HR-Onboarding & Lieferanten-/Klumpenrisiko** — *erledigt in Zyklus 9*: zwei neue Szenarien +
  Dokumente (Onboarding-Checkliste, Lieferanten-Risikoanalyse mit Konzentrations-Tabelle),
  verzahnt mit der Stahl-/Ferro-Nord-Story. „Geführte Demo" 9 → 11.
- ✅ **Zweite E-Mail (interne Weiterleitung an die CFO)** — *erledigt in Zyklus 13*: Thread über
  zwei Nachrichten, verbindet E-Mail → Vorstandsbeschluss (Entscheidungskette quer durch Postfächer).
- Weiteres Szenario: Investitions-/Cashflow-Frage; optional ein IT-/Datenschutz-Ressort.
- Pro Dokument ein Miniatur-Thumbnail in der Bibliothek (SVG-Icon je Typ).
- ✅ **„Diese Antwort exportieren / An Vorstand senden"** — *erledigt in Zyklus 10* (Handlungs-
  Abschluss der Story, reine UI-Bestätigung).
- ✅ Zeitstempel/„Antwort in X s" — *erledigt in Zyklus 8* (Tempo-Signal im Antwortkopf).

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
