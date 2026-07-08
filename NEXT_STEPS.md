# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 8 — **Video-Politur: „Beantwortet in X,X s"-Signal +
  Zahlen-Hochzählen** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-08.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 64 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**Zwei neue Szenarien + passende Dokumente (HR-Onboarding & Lieferanten-Risiko).** Die Demo ist
jetzt breit, tief, geführt **und** poliert (Tempo-Signal, Count-up). Der schwächste
Fortschrittsbereich ist jetzt **Demo-Firma & Szenarien-Breite** (62 % / 74 %). Der stärkste
Hebel: **1–2 neue, glaubwürdige Szenarien**, die zusätzliche Entscheider-Ressorts abdecken —
z. B. **HR-Onboarding** („Was muss ein neuer Mitarbeiter am ersten Tag erledigen?") und
**Lieferanten-/Klumpen-Risiko** („Wie abhängig sind wir von unserem größten Lieferanten?").
Beide brauchen je 1–2 neue Dokumente in `data.js` (z. B. Onboarding-Checkliste, Lieferanten-
Übersicht) plus einen Szenario-Eintrag mit Antwort/Quellen/Konfidenz — die „Geführte Demo"
nimmt sie **automatisch** auf. Rein additiv in `data.js`, kein Code-Umbau.

*Warum diese?* Alle Wow-Mechaniken (Nutzen, Quellen, Tiefe, Vertrauen, Tempo) stehen. Was den
Gesamtfortschritt jetzt am meisten hebt, ist **inhaltliche Breite** — mehr Ressorts = mehr
Entscheider im Publikum, die „das ist genau mein Problem" denken. Risikoarm, weil datengetrieben.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md)
(Export-/„An Vorstand senden"-Button, sanfte Übergänge).

---

## CEO-Review (Ende Zyklus 8)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo wirkt jetzt auch **schnell**:
  „⚡ Beantwortet in 1,9 s" und hochzählende Kernzahlen geben ihr das „live & souverän"-Gefühl,
  das ein Verkaufsvideo trägt.
- *Erzeugt es Aufregung?* — Ja: Zahlen, die beim Erscheinen hochzählen, lesen sich wie ein
  Live-System, nicht wie eine statische Folie — subtil, aber wirkungsvoll im Bewegtbild.
- *Versteht ein CFO/CEO den Nutzen?* — Ja, unverändert stark: Antwort + Quellen + Konfidenz +
  jetzt sichtbares Tempo, alles ohne ein Wort über Technik.
- *Schwächste Stelle → nächster Zyklus:* **Inhaltliche Breite.** Mechanik und Politur sind rund;
  am meisten fehlt noch Ressort-Breite (HR-Onboarding, Lieferanten-Risiko) für noch mehr
  Entscheider-Resonanz.
