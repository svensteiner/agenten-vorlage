# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 1 — **Prototyp erstmals aufgesetzt** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-07.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 35 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**Bebilderte Dokument-Previews im Viewer** (statt reinem Text). Derzeit zeigt der
Viewer Text-Absätze mit gelben Highlights. Für den „Wow"-Effekt eines CFO sollte er
wie ein **echtes Dokument** aussehen: ein PDF-/Brief-/Rechnungs-Layout (Briefkopf,
Tabellenraster für die Rechnung, Unterschriftszeile im Vertrag) mit dem gelben
Highlight *im Dokument-Layout*. Rein CSS/HTML, keine echten PDFs — als „Dokumenten-
Skin" pro `type` in `prototype/app.js`/`styles.css`.

*Warum diese?* Der Sprung von „Chatbot mit Textschnipseln" zu „das System öffnet mein
tatsächliches Dokument und zeigt mir die Stelle" ist der stärkste Einzel-Vertrauens-
Trigger für nicht-technische Entscheider — genau die Zielgruppe des Videos.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md).

---

## CEO-Review (Ende Zyklus 1)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja**, der Kern-Flow ist überzeugend.
- *Erzeugt es Aufregung?* — Ja: die Belege + Konfidenz + Viewer wirken „enterprise-echt".
- *Versteht ein CFO den Nutzen?* — Ja, Szenario 2/3/5 sind direkt CFO-relevant.
- *Schwächste Stelle → nächster Zyklus:* der Viewer zeigt Text, nicht ein *echtes*
  Dokument-Layout. Das ist der nächste Hebel (oben).
