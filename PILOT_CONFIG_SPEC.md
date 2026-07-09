# PILOT_CONFIG — Spezifikation (Umbranding-Mechanismus)

> **Phase C · Deliverable 1 (Design-Portion).** Reine Handover-/Design-Datei — **kein Eingriff in
> `prototype/`**. Beschreibt, *wie* eine einzige Konfigurationsdatei den gesamten Prototyp auf einen
> Pilotkunden umbrandet. Die **Implementierung berührt `prototype/`** und wird daher erst **nach
> Gate B→C** ausgeführt (Feature-Freeze in Phase B gewahrt). Diese Spec macht die Umsetzung dann zu
> einer 30-Minuten-Mechanik statt einer Suche-Ersetze-Odyssee.

Verwandte Bricks: [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) (Dokumentenkorpus erzeugen) ·
[SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) (welche 3 Szenarien) · [PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md)
(das Angebot, das dieses 48-h-Versprechen verkauft).

---

## 1. Das Versprechen, das diese Datei einlöst

> „Nach dem 30-Minuten-Audit-Call sieht der Kunde binnen 48 h **seine eigene** Demo — sein Firmenname,
> seine Branche, seine drei Schmerz-Szenarien — mit 100 % synthetischen Daten."

Damit das wiederholbar in Stunden statt Tagen geht, darf ein Pilot **keine** Code-Jagd durch 1.100 Zeilen
`data.js` bedeuten. Er ist ein **Datei-Tausch**: eine `pilot.config.js` + ein synthetischer Korpus.

---

## 2. Der entscheidende Denkfehler, den diese Spec vermeidet

Der Firmenname „Meridian Industrie GmbH" steht **~55-mal** in `prototype/data.js` — in **Dokument-
körpern** (Rechnungen, Verträge, E-Mails), nicht nur an einer Stelle. Ein naives „Firmenname im Config
ändern" würde also **nicht** durchschlagen; ein globales Suchen-Ersetzen wäre fehleranfällig (Personen,
Aussteller, Domains, Belegnummern hängen dran).

**Auflösung — zwei getrennte Schichten:**

| Schicht | Was | Wie sie beim Piloten ausgetauscht wird |
|---|---|---|
| **A · Shell / Chrome** | Firmenname im Kopf, Logo-Glyph, Tagline, Fakten-Karte, Branche, Akzentfarbe, die 3 gezeigten Szenarien | **`pilot.config.js`** überschreibt das `COMPANY`-Objekt + wenige Shell-Werte. Klein, deterministisch. |
| **B · Dokumentenkorpus** | Rechnungen, Verträge, Berichte, E-Mails (die ~55 Namensvorkommen) | **Nicht** per Suchen-Ersetzen — der Meridian-Korpus wird **wholesale ersetzt** durch den synthetischen Zwilling aus [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md). Die 55 Vorkommen verschwinden mit dem alten Korpus. |

Der Pilot ist damit: **Config tauschen (Schicht A)** + **Korpus tauschen (Schicht B)**. `PILOT_CONFIG` ist
Schicht A und der Zeiger darauf, *welchen* Korpus/Szenariensatz Schicht B lädt.

---

## 3. Reale Verankerung im heutigen Code (Ist-Zustand)

Belegt durch Lesen von `prototype/` (nichts geändert):

- `data.js:9–26` — `const COMPANY = { name, tagline, facts[], people{} }`. Einzige Chrome-Quelle.
- `index.html:6` — `<title>AI Studio — Meridian Industrie GmbH</title>` (hartkodiert).
- `index.html:14` — Logo-Glyph `✦`; `index.html:16` — Produktname „AI Studio" (bleibt, ist **unser**
  Produkt, nicht der Kunde).
- `app.js:285 renderCompanyCard()` — liest `COMPANY.name` + `COMPANY.facts`.
- `app.js:331` Hero-Intro, `app.js:706` Briefing-Fußzeile, `app.js:913` Bibliothekskopf,
  `app.js:1185 #searchCompany` — alle lesen `COMPANY.name`/`COMPANY.tagline`.

**Gut:** Die Shell liest bereits **fast alles** aus `COMPANY`. Nur der `<title>` und der Logo-Glyph sind
hartkodiert. Das macht Schicht A klein.

---

## 4. Schema — `pilot.config.js`

Eine Datei, an **einer** Stelle geladen (vor `data.js` in `index.html`). Fehlt sie → Prototyp läuft
unverändert als Meridian-Demo (abwärtskompatibel).

```js
// pilot.config.js — pro Pilot EINE Datei. 100 % synthetisch. Kein echter Kundenname/Logo.
window.PILOT_CONFIG = {
  active: true,                       // false → Standard-Meridian-Demo
  company: {
    name:    "Muster Bau GmbH",       // ersetzt COMPANY.name überall in der Shell
    tagline: "Hoch- & Tiefbau · Region Süd",
    logoGlyph: "▲",                   // 1 Zeichen (Emoji/Unicode); ersetzt ✦ im Kopf + Onboarding
    accent:  "#1f6feb",              // optional: CSS --accent; weglassen = Marken-Indigo behalten
    facts: [                          // 3–4 Kennzahlen für die Firmenkarte (synthetisch!)
      { label: "Gegründet",     value: "1998" },
      { label: "Mitarbeitende", value: "180" },
      { label: "Standorte",     value: "Augsburg · Werkhof Kempten" },
      { label: "Umsatz 2025",   value: "48 Mio. €" },
    ],
    people: {                         // Namen, die in synthetischen Dokumenten auftauchen
      ceo: "…", cfo: "…", procurement: "…", hr: "…", legal: "…", audit: "…",
    },
  },
  industry: "bau",                    // steuert Szenario-Vorauswahl (siehe SCENARIO_LIBRARY.md)
  scenarios: [                        // GENAU 3 Schmerz-Szenarien + Money-Shot bleibt Finale
    "materialkosten",                 // IDs aus data.js / SCENARIO_LIBRARY.md
    "rechnungspruefung-donau",
    "liquiditaet-90-tage",
  ],
  // corpus: "muster-bau"             // optional: Ordner-/Datei-Zeiger auf synth. Korpus (Schicht B)
};
```

**Harte Regeln:**
- `scenarios` = **genau 3** IDs (der Money-Shot `agent-dazubuchen` wird vom Umbranding **nicht** angefasst
  und bleibt automatisch das Demo-Finale — das verkauft das Abo).
- Alle Werte **synthetisch**. Nie echter Kundenname, nie echtes Logo (Glyph statt Bilddatei = kein
  Marken-/Rechte-Risiko, kein Asset-Handling).
- `active:false` oder Datei fehlt → **unveränderte** Meridian-Demo (die aufnahmebereite Video-Basis
  bleibt intakt).

---

## 5. Wiring (zu implementieren **nach** Gate B→C)

Rein additiv, ~1 kleine Funktion + 1 Script-Tag. Kein Umbau bestehender Renderer.

1. **`index.html`** — `<script src="pilot.config.js"></script>` **vor** `data.js`. (Neue optionale Datei;
   fehlt sie, lädt der Browser sie nicht → Standard-Demo.)
2. **`data.js`** — nach der `COMPANY`-Definition ein Guard:
   ```js
   if (window.PILOT_CONFIG?.active) {
     Object.assign(COMPANY, window.PILOT_CONFIG.company); // Shell übernimmt Kundennamen
   }
   ```
   Damit schlagen `renderCompanyCard`, Hero, Briefing-Fußzeile, `#searchCompany` **automatisch** durch —
   sie lesen bereits `COMPANY.name` (siehe §3).
3. **`app.js`** — eine `applyPilotChrome()`-Funktion beim Init:
   - `document.title` und `#searchCompany` aus `COMPANY.name` setzen (Titel ist heute hartkodiert).
   - Logo-Glyph `.logo`/`.ob-spark` auf `logoGlyph` setzen, falls vorhanden.
   - `accent` → `document.documentElement.style.setProperty('--accent', …)`, falls vorhanden.
   - Szenario-Vorauswahl: `DEMO_ORDER` aus `PILOT_CONFIG.scenarios` + Money-Shot-Finale bilden
     (Fallback = heutige kuratierte 6er-Reihenfolge, wenn kein Config).
4. **Schicht B (Korpus)** — separat über [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md): der
   synthetische Zwilling ersetzt die `DOCS`/`lineItems`-Einträge. `PILOT_CONFIG.corpus` ist nur der Zeiger.

**Token-Konvention für neue synthetische Dokumente (verhindert künftige Hartkodierung):** synthetische
Korpora sollen `{{COMPANY}}` statt eines Klarnamens schreiben; ein einmaliger Ersetzungs-Pass beim Laden
setzt `COMPANY.name` ein. So bleibt Schicht B umbrandbar, ohne die 55-Vorkommen-Falle zu wiederholen.

---

## 6. 48-h-Pilot-Ablauf (wo PILOT_CONFIG sitzt)

```
Audit-Call (30 min)
   └─ Firmenname · Branche · 3 Schmerzpunkte + Kunden-Dateistruktur erfragen
        │
        ▼
[Schicht A] pilot.config.js schreiben ......................  ~20 min  (§4)
        │      Name/Tagline/Glyph/Fakten/Branche/3 Szenario-IDs
        ▼
[Schicht B] synthetischen Zwilling erzeugen ...............  siehe SYNTHETIC_DATA_PIPELINE.md
        │      synth.py --from <Struktur> --seed …  → DOCS/lineItems
        ▼
Szenarien wählen ..........................................  SCENARIO_LIBRARY.md (3 zur Branche)
        │
        ▼
Deterministisch verifizieren ..............................  node --check · Docs/Szenarien/0 kaputte Refs
        │
        ▼
Kunde sieht seine Demo  ◀── < 48 h nach dem Call
```

---

## 7. Abnahme-Kriterien der (späteren) Implementierung

- [ ] `active:false`/fehlende Datei → **bit-identische** Meridian-Demo (Regressionsschutz fürs Video).
- [ ] `active:true` → Kundenname erscheint in: Titel-Tab, Firmenkarte, Hero-Intro, Bibliothekskopf,
      Briefing-Fußzeile, Such-Fußzeile — **ohne** ein einziges verbliebenes „Meridian" in der Shell.
- [ ] Money-Shot `agent-dazubuchen` bleibt Demo-Finale (unberührt vom Umbranding).
- [ ] `node --check` grün; Node-VM zählt Docs/Szenarien; **0 kaputte Referenzen**.
- [ ] Kein echter Kundenname/kein Logo-Bild im Repo (nur synthetische Config + Glyph).

---

## 8. Freeze-Grenze (ausdrücklich)

Diese Datei ist **Design/Doku** — sie ändert `prototype/` nicht und hebt **kein** Gate. Das eigentliche
Wiring (§5) berührt `index.html`/`data.js`/`app.js` und ist daher **erst nach Gate B→C** auszuführen.
Bis Svens Video-Freigabe gilt: am Prototyp **nur** ändern, was Sven anmerkt.
