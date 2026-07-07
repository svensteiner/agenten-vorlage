# CHANGELOG — Kundendemonstrations-Prototyp

Alle sichtbaren Änderungen am Demo-Prototyp. Neueste zuerst.

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
