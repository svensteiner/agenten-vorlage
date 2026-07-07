# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 3 — **„Geführte Demo" (hands-free Auto-Play)** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-07.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 48 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**Rechnungs-Positionstabelle im Beleg-Skin** — Belege haben jetzt Briefkopf + Stempel;
als nächste Vertiefung bekommt der Viewer für Rechnung/Bestellung/Wareneingang eine echte
**Positionszeilen-Tabelle** (Pos. · Bezeichnung · Menge · Einzelpreis · Summe · USt) mit
Zwischensumme/USt/Endbetrag. Umsetzung datengetrieben über ein optionales
**`doc.lineItems`-Feld in `data.js`** (Fallback = bisheriger Fließtext, wenn nicht gesetzt),
gerendert in `buildPaper()` nur für die `beleg`-Kategorie.

*Warum diese?* Sie macht den **Drei-Wege-Abgleich (Szenario 3)** für einen CFO endgültig
prüfungsecht: Rechnung ↔ Bestellung ↔ Wareneingang zeigen dann übereinstimmende Positionen
und Beträge — der stärkste „das ist echte Buchhaltung"-Moment im Video. Baut auf dem
vorhandenen Beleg-Skin auf und bleibt rein additiv.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md)
(Onboarding-Overlay, weitere Szenarien, Politur).

---

## CEO-Review (Ende Zyklus 3)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Mit der „Geführten Demo" läuft die
  komplette Story auf Knopfdruck durch — ideal für Video und Messestand.
- *Erzeugt es Aufregung?* — Ja: das automatische Tippen der Fragen + streamende Antworten
  wirken wie ein echter Assistent, der selbst arbeitet.
- *Versteht ein CFO den Nutzen?* — Ja, weil die 7 Szenarien in kuratierter Reihenfolge
  ohne Ablenkung nacheinander laufen (Reiserichtlinie → Materialkosten → Beleg-Abgleich …).
- *Schwächste Stelle → nächster Zyklus:* die Belege wirken noch textlastig. Eine echte
  **Positionstabelle** (oben) hebt die Prüf-Glaubwürdigkeit für Finanz-Entscheider am meisten.
