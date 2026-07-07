# CHANGELOG — Kundendemonstrations-Prototyp

Alle sichtbaren Änderungen am Demo-Prototyp. Neueste zuerst.

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
