# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

- **Mission:** einen herausragenden Kunden-Demo-Prototyp bauen (für ein Verkaufsvideo).
  Höchste Priorität. Visuelle Qualität, Kundennutzen, „Wow"-Effekt.
- **Letzter Zyklus:** Zyklus 6 — **Onboarding-Overlay beim ersten Start** (siehe unten).
- **Zuletzt aktualisiert:** 2026-07-08.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Gesamtfortschritt Prototyp:** **≈ 58 %** (siehe [PROGRESS.md](PROGRESS.md)).

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

**Vertrauens-Story sichtbar machen: ein „gesperrtes" Dokument + prominenteres Berechtigungs-
Signal.** Die Demo ist jetzt breit, tief und geführt — die stärkste ungenutzte Karte ist die
**Permission-faithful-Kernidee** („Sie sehen nur, was Sie dürfen"). Nächster Zyklus: ein bewusst
**gesperrtes Dokument** in der Bibliothek (Schloss-Icon, ausgegraut, „Kein Zugriff — Vorstand")
plus, in einer Antwort, eine sichtbare Zeile **„2 weitere Treffer für Sie nicht freigegeben"**.
Das macht Datenschutz/Governance in Sekunden greifbar — genau die CFO/Compliance-Frage
„Sieht jeder alles?". Rein additiv (neues `locked`-Flag in `data.js` + Rendering in
Bibliothek/Antwort), kein Umbau des Antwortpfads.

*Warum diese?* Sie hebt **Vertrauen/Governance** — das einzige große Wow-Thema, das die Demo
noch nicht zeigt — und differenziert AI Studio von „ChatGPT auf unseren Dateien". Kleiner,
risikoarmer Eingriff mit starker Wirkung auf skeptische Entscheider.

**Danach (Priorität absteigend):** siehe [OPEN_ITEMS.md](OPEN_ITEMS.md)
(weitere Szenarien HR/Lieferanten-Risiko, Politur/Zahlen-Animationen, Export-Button).

---

## CEO-Review (Ende Zyklus 6)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Der Einstieg ist jetzt geführt: ein
  Zuschauer versteht in der ersten Sekunde, was er tun kann, und ein Klick startet die volle
  Vorführung.
- *Erzeugt es Aufregung?* — Ja: „Ein Klick → das System spielt sich selbst vor" ist ein
  starker Video-Opener; der pulsierende Button mit Pfeil führt das Auge sofort.
- *Versteht ein CFO/CEO den Nutzen?* — Ja: Headline + Geführte Demo beantworten „Was bringt
  mir das?" ohne dass jemand die Bedienung erklären muss.
- *Schwächste Stelle → nächster Zyklus:* **Vertrauen/Governance ist noch unsichtbar.** Die
  Demo zeigt nicht, dass Berechtigungen respektiert werden. Ein **gesperrtes Dokument + „für
  Sie nicht freigegeben"-Signal** (oben) ist der größte verbleibende Wow-Hebel für skeptische
  Entscheider.
