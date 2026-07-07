# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 2 — **Dokument-Skins im Viewer** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-07.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 42 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**„Guided Demo"-Modus** — ein prominenter **Play-Button** (z. B. in der Topbar oder auf
dem Hero), der die 7 Szenarien **automatisch nacheinander abspielt**: Frage wird in den
Composer „getippt", Antwort streamt, kurze Pause, dann das nächste Szenario. Mit
Pause/Stop und einem dezenten Fortschritts-Indikator (z. B. „Szenario 3 / 7").

*Warum diese?* Damit läuft die komplette Demo **hands-free** — ideal für die Video-
Aufnahme (keine sichtbaren Mausbewegungen/Tippfehler) **und** für einen Messestand- bzw.
Empfangs-Loop, der Kunden ohne Bediener überzeugt. Baut vollständig auf dem vorhandenen
`ask()`-Flow in `prototype/app.js` auf (nur Orchestrierung + ein Button) und verändert die
bestehende Logik nicht.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md).

---

## CEO-Review (Ende Zyklus 2)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja**, deutlich stärker: der Viewer
  öffnet jetzt sichtbar „echte" Rechnungen/Verträge mit Stempel und Unterschrift.
- *Erzeugt es Aufregung?* — Ja: der EINGANG-Stempel und die Unterschriftszeilen sind ein
  spürbarer „das ist mein echtes Dokument"-Moment.
- *Versteht ein CFO den Nutzen?* — Ja, der Drei-Wege-Abgleich (Szenario 3) wirkt mit den
  Belegskins nun wie eine echte Prüfungsakte.
- *Schwächste Stelle → nächster Zyklus:* die Demo braucht noch Bedienung. Ein
  hands-free „Guided Demo"-Modus (oben) hebt die Video-/Messe-Reife am meisten.
