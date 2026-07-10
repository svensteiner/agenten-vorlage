# NEXT_STEPS — Kundendemonstrations-Prototyp

> **Zuerst diese Datei lesen, jeden Zyklus.** Verbindliche Übergabe für die
> **Prototyp-Mission** (AI STUDIO – PROTOTYPE DEVELOPMENT MODE). Am Ende jedes
> Zyklus fortschreiben. **Nie neu beginnen — immer erweitern.**

> ⚠ **MISSION-WECHSEL (2026-07-08):** Es gilt jetzt **AI STUDIO — PILOT SPRINT MODE (v2)**
> ([MISSION_PILOT_SPRINT.md](MISSION_PILOT_SPRINT.md)) — drei Phasen bis zur Ziellinie:
> **A) Demo-Freeze → B) Video → C) Pilot-Kit**. **Feature-Freeze in Phase A:** keine neuen
> Szenarien/Module/Dokumente außer den Phase-A-Checklistenpunkten; neue Ideen →
> [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md). Wir sind in **Phase A**. (Die alte „PROTOTYPE
> DEVELOPMENT MODE"-Zeile oben ist historisch; die Zyklus-Historie unten bleibt gültig.)

## ► Nächster Zyklus (Phase B — Videoproduktion: **Kern-Deliverables fertig, wartet auf Sven**)

> ✅ **PHASE A ABGESCHLOSSEN (Gate A→B bestanden, 2026-07-08).** Alle 6 Checklisten-Kästchen erfüllt.
> **Feature-Freeze bleibt in Kraft** — keine neuen Prototyp-Features, nur noch das Verkaufsvideo
> produktionsreif machen. Neue Ideen → [FUTURE_BACKLOG.md](FUTURE_BACKLOG.md).

**Phase-B-Deliverables sind vollständig — inkl. der optionalen:** [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)
(Sprechertext), [VIDEO_SCENES.md](VIDEO_SCENES.md) (Shotlist), [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md)
(narrensichere Aufnahme-Anleitung) und neu [VIDEO_SUBTITLES.de.srt](VIDEO_SUBTITLES.de.srt) (deutsche
Untertitel, 47 Cues). **Sven kann jetzt aufnehmen.**

**Gate-Item = reiner Wartepunkt: Svens Aufnahme + Freigabe (Gate B→C).** Bis Svens „OK" am Prototyp/Video
**nur** ändern, was er anmerkt — nichts anderes. Alle Aufnahme-Dateien sind faktentreu und aufnahmebereit.

**Parallel begonnen (freeze-konforme Phase-C-Vorbereitung):** Weil Phase B seit mehreren Zyklen allein auf
Sven wartet und ein weiterer identischer Re-Verifikations-Zyklus reines Churnen wäre, werden die niedrigst-
riskanten Phase-C-Bricks vorgezogen — **reine Doku, kein Eingriff in `prototype/`** (Feature-Freeze gewahrt).
Bereits fertig: **[SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)** (17 Szenarien nach Schmerz + Branche, 3er-
Startvorlagen), **[PILOT_ONE_PAGER.md](PILOT_ONE_PAGER.md)** (Angebotsdokument: 48-h-Versprechen · Preis-Pfad
Audit 149 € → Wissensbasis ab 5.000 € → Agent-Abo ab 400 €/Monat · Einwand-Antworten · CTA) und **neu
[SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md)** (Workflow **Kunden-Dateistruktur rein →
synthetischer Zwilling mit intakten Formeln raus → in `data.js` geladen**, Reuse `synthetic-data-creator`
43/43 Tests, 4-Schritt-Prozess + Ablaufdiagramm). Das hebt **kein** Gate — Gate B→C wartet weiter nur auf
Sven —, macht aber den 48-h-Pilot-Prozess konkret verkaufbar.

**► Nächster Zyklus, wenn weiter keine Sven-Rückmeldung vorliegt:** **alle 5 reinen Phase-C-Doku-Bricks
sind abgeschlossen** (Szenarienbibliothek · One-Pager · Datenpipeline · PILOT_CONFIG-Spec · **neu
PILOT_KIT.md** = 48-h-Master-Runbook). Es gibt **keine freeze-konforme Doku-Brick mehr** — die
verbleibenden Bricks **berühren `prototype/`** und dürfen daher **erst nach Gate B→C** ausgeführt werden:
1. **PILOT_CONFIG (Implementierung)** — das in [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md) spezifizierte
   Wiring (`pilot.config.js` + Guard in `data.js` + `applyPilotChrome()` in `app.js`). ⚠ berührt
   `prototype/` → **erst nach Gate B→C**. Design ist fertig → dann 30-Min-Mechanik.
2. **End-to-End-Probelauf „Muster Bau GmbH"** — führt PILOT_CONFIG-Spec +
   [SYNTHETIC_DATA_PIPELINE.md](SYNTHETIC_DATA_PIPELINE.md) real aus; Protokoll in [PILOT_KIT.md](PILOT_KIT.md) §8;
   danach `MISSION_COMPLETE`. Sobald 1 steht.

> **Konsequenz:** Ohne Sven-Rückmeldung ist der nächste Zyklus ein reiner **Wartepunkt** (aufnahmebereit
> re-verifizieren statt churnen) — die vorziehbare Doku ist erschöpft, jede weitere Phase-C-Arbeit ist
> gated. Kommt eine Anmerkung von Sven → **die hat Vorrang** vor allem anderen.

**Diesen Zyklus gebaut (2026-07-10, freeze-konform, kein Eingriff in `prototype/`):** ein **Vorab-Kohärenz-
Audit Schicht A ↔ Schicht B** für „Muster Bau GmbH". Die beiden gestageten Probelauf-Hälften (Config +
synth. Zwilling) waren bisher **je für sich** verifiziert; erstmals gegeneinander **und** gegen das, was die
Config verspricht, geprüft (deterministisch: Node-VM gegen `data.js` + openpyxl gegen beide `.xlsx`) — der
Winkel, der die gated §8-Übertragung sonst kalt getroffen hätte. **Drei nicht-blockierende Kohärenz-Lücken
vorab protokolliert** (in [`pilot-assets/muster-bau-gmbh/README.md`](pilot-assets/muster-bau-gmbh/README.md)
→ „Vorab-Kohärenz-Audit" und als §8-Notiz in [PILOT_KIT.md](PILOT_KIT.md)): **(1) Korpus-Checkliste** — die 3
Pilot-Szenarien ziehen zusammen **12 verschiedene** Belege heran (verifiziert aufgelistet); der erzeugte
Zwilling-`.xlsx` deckt nur die Materialkosten-Zahlen ab und ist damit **1 von 12** → die übrigen 11 sind im
gated Schritt 3 zu erzeugen/umzuschreiben. **(2) Personen-Regel** — die Config deklariert 6 synthetische
Personen als „im Korpus vorhanden", sie erscheinen aber in **0** Artefakten (Zwilling 0, `data.js` 0), während
die 12 Quelldocs heute die **Meridian**-Namen tragen → Schritt 3 muss die 6 Namen 1:1 einsetzen, sonst leakt
die Demo Meridian; der Config-Kommentar wurde von „tauchen auf" ehrlich auf „**sollen** via Schritt 3
auftauchen" gestellt. **(3) §8-Eingaben** — die dort genannten Rechnungs-/Vertrags-CSV-Zwillinge sind **noch
nicht gestaged** (entstehen erst in Schritt 3). Ergebnis: eine **konkrete 12-Dokument-Checkliste + Personen-
Ersetzungs-Regel** stehen für die gated Übertragung bereit, statt live entdeckt zu werden. `git status`: nur
`README.md` + `pilot.config.js` + `PILOT_KIT.md`; `node --check` (app.js + data.js) grün; Live-Daten
unverändert (**29 Docs · 17 Szenarien**). Ein Vorbereitungs-/Audit-Brick hebt kein Gate → **Gate B→C wartet
weiter nur auf Sven.**

**Zyklus davor gebaut (freeze-konform, kein Eingriff in `prototype/`):** die **Pilot-Config Schicht A für
„Muster Bau GmbH" real geschrieben** statt nur spezifiziert. Neue Datei
[`pilot-assets/muster-bau-gmbh/pilot.config.js`](pilot-assets/muster-bau-gmbh/pilot.config.js) (außerhalb
`prototype/`, **nicht** verdrahtet): vollständige `window.PILOT_CONFIG` nach [PILOT_CONFIG_SPEC.md](PILOT_CONFIG_SPEC.md)
§4 — Name, Tagline, Glyph `▲`, Akzent, 4 synthetische Fakten, 6 synthetische Personennamen, Branche `bau`,
`corpus`-Zeiger; **3 Schmerz-Szenarien = die verifizierte Bau-Startvorlage** aus [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md)
(`materialkosten` · `projekt-beta` · `vorstand-summary`), Money-Shot `agent-dazubuchen` bewusst **nicht** in
der Liste → bleibt Demo-Finale. **Alle Werte 100 % synthetisch** (kein Meridian-Leak, kein Logo-Bild). Damit
sind **beide freeze-konformen Hälften des Probelaufs** ausgeführt — Korpus (Schicht B, Vorzyklus) *und* Config
(Schicht A). **Verifiziert** (Node-VM gegen die Live-`data.js`): Schema erfüllt (genau 3 Szenarien, `people`-Keys
deckungsgleich mit `COMPANY.people`), **alle 3 IDs existieren** — und eine **Faktenkorrektur**: die
*Beispiel*-IDs der Spec (`rechnungspruefung-donau`, `liquiditaet-90-tage`) existieren **nicht** in `data.js`,
die real gewählten schon; Live-Daten unverändert (29 Docs · 17 Szenarien). `git status`: nur die neue
`pilot.config.js`; `node --check` (config + app.js + data.js) grün. Das Wiring (Script-Tag + `COMPANY`-Guard +
`applyPilotChrome()`) berührt `prototype/` und bleibt **gated bis Gate B→C**.

**Zyklus davor gebaut (freeze-konform, kein Eingriff in `prototype/`):** die **Pilot-Datenpipeline erstmals
real ausgeführt** statt nur dokumentiert. Neuer Ordner [`pilot-assets/muster-bau-gmbh/`](pilot-assets/muster-bau-gmbh/README.md)
(außerhalb `prototype/`): `build_input.py` baut reproduzierbar eine fiktive mehrblättrige Bau-Controlling-Mappe
mit Gelb-Konvention + 3 blattübergreifenden Formeln; der `synthetic-data-creator` (Reuse, 43/43 Tests) erzeugt
mit `--seed 42` den synthetischen Zwilling. **Verifiziert (openpyxl):** 12/12 Formeln bit-genau erhalten (inkl.
blattübergreifend), gesetzliche USt-Konstante 19 % unangetastet, 12/14 gelbe Eingaben synthetisiert, Modell
rechnet weiter (Netto 284.266,41 € → Brutto 338.277,03 €, Brutto = Netto × 1,19). Das tilgt die größte
**unbewiesene** Annahme des Phase-C-Plans (die §Beispiel-Tabelle der Pipeline war bislang hypothetisch) — die
Schritte 1+2 sind jetzt **ausgeführt & bewiesen**, nur Schritt 3 (Laden in `data.js`) bleibt gated. **Lernpunkt
im Log:** feste/gesetzliche Konstanten *nicht* gelb markieren. `git status`: nur `pilot-assets/` neu;
`node --check` (app.js + data.js) grün.

> **Korrektur zur Freeze-Grenze:** Die frühere Aussage „keine freeze-konforme Arbeit mehr möglich" galt nur für
> *Doku*-Bricks. Die **Ausführung** der nicht-gated Pipeline-Hälfte (Schritte 1+2 = synthetischen Zwilling
> erzeugen, ohne `prototype/` zu berühren) war weiterhin möglich und ist nun erledigt. **Jetzt** ist die
> vorziehbare Phase-C-Arbeit erschöpft: das verbleibende Schritt 3 (`data.js`) + PILOT_CONFIG + der End-to-End-
> Probelauf am Prototyp berühren alle `prototype/` und sind bis Gate B→C gated. Der `pilot-assets/`-Input steht
> als **verifizierter** Ausgangspunkt für den späteren Probelauf bereit (Protokoll → PILOT_KIT.md §8).

Details: [OPEN_ITEMS.md](OPEN_ITEMS.md).

> **Link-Integrität der Handover-Suite am 2026-07-09 verifiziert (freeze-konform, neuer Prüf-Winkel, kein
> Eingriff):** statt Doc-Zähl-/Konsistenz-Prüfungen erneut zu wiederholen (Churn), diesmal die **interne
> Markdown-Link-Integrität aller Wurzel-`.md`** geprüft — ein bisher nicht abgedeckter Winkel: brechende
> Querverweise machen ein Aufnahme-/Verkaufs-Kit für Nicht-Techniker unbrauchbar. **133 interne Links
> geprüft, 0 kaputt** (jeder relative Datei-Link zeigt auf eine existierende Datei; Anker/`http(s)`/`mailto`
> ausgenommen). Live-Daten unverändert: **29 Docs · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0 kaputte
> Referenzen · Chain 3**; Aufnahme-Pfad intakt: `DEMO_ORDER` = 6 IDs mit Money-Shot `agent-dazubuchen` als
> Finale, `matchDocs("stahl")` = 10, `matchDocs("")` = 29. `node --check` grün, `git status` sauber,
> `prototype/` unverändert. **Keine Regression — die Demo ist unverändert aufnahmebereit.** Ein
> Verifikations-Pass hebt kein blockiertes Gate → **Gate B→C wartet weiter nur auf Sven.**
>
> **Aufnahme-Bereitschaft am 2026-07-09 verhaltens-verifiziert (freeze-konformer Verifikations-Zyklus, neuer
> tieferer Winkel, keine Änderung im `prototype/`):** statt die Zähl-Prüfung identisch zu wiederholen (Churn)
> diesmal die **reale Palette-Suche nachgestellt** — die `matchDocs()`-Feldmenge (`title · type · snippet ·
> author · module`) exakt repliziert: `matchDocs("stahl")` = **10** (ein naiver Ganz-Objekt-Scan liefert 12 →
> belegt, dass die im Skript/Checkliste genannte „10" die *sichtbare* Palette-Zahl ist), `matchDocs("")` =
> **29**. Dazu die Demo-Steuerung aus `app.js` aufgelöst: `MONEY_SHOT_ID = "agent-dazubuchen"` (existiert),
> `DEMO_ORDER` = 6 IDs mit dem Money-Shot als **Finale**, `DECISION_CHAIN` = 3 Schritte; `node --check`
> (app.js + data.js) ok; Node-VM gegen `data.js` — **29 Docs · 17 Szenarien · 3 E-Mails · 2 gesperrt · 0
> kaputte Referenzen**; `grep`: keine veralteten Zähl-Reste (16/27/28) in den Video-Dateien; `git status`
> sauber. **Keine Regression — die Demo ist unverändert aufnahmebereit.** Der nächste automatische Zyklus
> bleibt ohne Svens Rückmeldung ein Wartepunkt (nicht churnen); mit seinen Anmerkungen → gezielt umsetzen. Die
> vorziehbare Phase-C-Doku ist erschöpft (alle 5 Bricks fertig); jede weitere Phase-C-Arbeit berührt
> `prototype/` und ist bis Gate B→C gated.
>
> **Pilot-Kit-Konsistenz-Audit am 2026-07-09 (neuer Prüf-Winkel, kein Eingriff):** die fünf Phase-C-Verkaufs-/
> Handover-Dokumente **gegen die Live-Daten** abgeglichen (Doku ↔ `data.js`, dieselbe Drift-Klasse wie 27/28 →
> 29 früher). **Zero Drift:** 29 Docs · 17 Szenarien · 3 E-Mails · 2 gesperrt · DECISION_CHAIN 3 Schritte
> deckungsgleich; **alle 17 Szenario-IDs** in SCENARIO_LIBRARY referenziert (0 fehlend); Agenten-Preise
> (Reporting 400 · Vertrags 500 · Rechnungs 600 €) + Preis-Pfad (149 € → 5.000 € → 400 €/Mon.) bit-genau zu
> `agent-dazubuchen` und One-Pager/PILOT_KIT. Das Pilot-Kit ist als Verkaufs-Werkzeug stimmig, `prototype/`
> unverändert. Ein Verifikations-Pass hebt kein Gate → **Gate B→C wartet weiter nur auf Sven.**

## Was in diesem Zyklus gebaut wurde (Skript/Shotlist-Faktenkorrektur)

**Die Video-Handover-Dateien auf den realen Prototyp angeglichen.** Skript und Shotlist nannten Zahlen, die
seit dem Phase-A-Abschluss nicht mehr stimmen — ein nicht-technischer Aufnehmer hätte die Abweichung zwischen
Datei und Bildschirm für einen eigenen Fehler gehalten. Gegen die Live-Daten (`data.js`/`app.js`) geprüft und
korrigiert:
- **Dokumentenzahl 27/28 → 29** — Such-Beat/Command-Palette-Zähler in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)
  (Szene 0b) und [VIDEO_SCENES.md](VIDEO_SCENES.md) (Szene 0a + B-Roll + „Globale Suche"); „10 von 27" →
  „10 von 29". Der „stahl"→**10 Treffer** war bereits korrekt.
- **Geführte Demo „alle 16 Szenarien / n / 16" → „kuratierte 6er-Kern-Auswahl / n / 6"** (endet auf dem
  Money-Shot, < 4 Min) — die seit Phase-A-Abschluss reale `DEMO_ORDER`. In den Aufnahme-Hinweisen beider
  Dateien richtiggestellt.
- **Klarstellungs-Hinweis** ergänzt (beide Dateien): die Szene-für-Szene-Abfolge ist die **manuelle
  Langfassung**; die Geführte Demo deckt davon 6 Kern-Momente automatisch ab. Verbindlich bleibt
  [RECORDING_CHECKLIST.md](RECORDING_CHECKLIST.md).
- **Nur `.md` — `prototype/` unverändert (Feature-Freeze gewahrt).** Verifikation: Node-VM gegen `data.js`
  (29 Docs, 17 Szenarien, „stahl" = 10, `DEMO_ORDER` = 6/Money-Shot-letzt); `grep`: keine 16/27/28-Reste mehr.

## Was im Zyklus davor gebaut wurde (VIDEO_SUBTITLES.de.srt)

**Die optionale, aber wertvolle Phase-B-Deliverable: eine fertige deutsche Untertiteldatei.** Skript,
Shotlist und Checkliste standen; die Phase-B-Checkliste nennt zusätzlich „optional, aber wertvoll: SRT-
Untertitel aus dem Skript". Neu:
- **`VIDEO_SUBTITLES.de.srt`** — **47 Cues**, direkt aus den `Sprecher`-Zeilen von `VIDEO_SCRIPT.md`
  abgeleitet (je 1–2 Zeilen, alle ≤ 55 Zeichen), monotone Zeitleiste **~0:00–4:22** (manuelle Langfassung
  aller Szenen inkl. optionaler Ressort-Beats 5b). Standard-SRT — in jedes Schnittprogramm/Player einlesbar.
- **Verweis-Sektion „Untertitel (SRT)" in `VIDEO_SCRIPT.md`** ergänzt: Fundort + Hinweis, dass die Timings
  **Richtwerte** sind (beim finalen Schnitt an die reale Sprechergeschwindigkeit angleichen; wird nur die
  kuratierte 6er-Kern-Demo gefilmt, die nicht gefilmten Cues — v. a. 5b, Cues 34–39 — entfernen).
- **Reine Handover-Datei**, `prototype/` unverändert (Feature-Freeze gewahrt). Verifikation deterministisch
  (Node-Parser): 47 Cues, Indizes lückenlos 1–47, alle Timecodes wohlgeformt, **keine Überlappung**, Ende >
  Start je Cue, kein Cue > 2 Zeilen, keine Zeile > 55 Zeichen. Letztes Cue endet 00:04:21,500.

## Was zwei Zyklen davor gebaut wurde (RECORDING_CHECKLIST.md)

**Die letzte Phase-B-Kern-Deliverable — eine Aufnahme-Checkliste, an der eine nicht-technische Person nicht
scheitern kann.** Skript und Shotlist existierten bereits; es fehlte die Anleitung, die einen Laien sicher
durch einen sauberen Take führt. Neu:
- **Browser-Setup narrensicher:** Chrome/Vollbild/100 % Zoom, **„Bewegung reduzieren" AUS** (die wichtigste
  Einstellung — sonst springen Zahlen/Balken statt hochzulaufen), Aufnahme-Tab im Vordergrund.
- **Reset-Ritual vor jedem Take:** Inkognito-Fenster fürs Onboarding-Intro (`aistudio.onboarded.v1`),
  „⟲ Zurücksetzen" für saubere Wiederholungen — Merksatz „Recorder an → Zurücksetzen → Demo starten".
- **Schnellster Weg = Geführte Demo:** 6 Kern-Szenen (Fortschritt „n / 6"), endet garantiert auf dem
  **Money-Shot**, < 4 Min, hands-free — als Tabelle mit „was der CFO je Szene sieht".
- **Fehler→Behebung-Tabelle** mit Retake-Regel + **Kurz-Spickzettel** zum Ankleben; optionale manuelle
  Langfassung (alle 17 Szenarien via [VIDEO_SCENES.md](VIDEO_SCENES.md)).
- **Gegen die reale Demo geschrieben** (6 kuratierte Szenen, 29 Dokumente, Such-Beat „stahl") — nicht
  gegen die ältere 16-Szenen-Beschreibung in Skript/Shotlist (die die manuelle Langfassung abbilden).
- **Reine Handover-Datei**, `prototype/` unverändert (Feature-Freeze gewahrt). Verifikation: Ground-Truth
  deterministisch (Node-VM) — 29 Docs, 17 Szenarien, `DEMO_ORDER` = 6 IDs mit `agent-dazubuchen` als
  Finale, Reset-Button `#resetBtn`, Onboarding-Flag `aistudio.onboarded.v1`.

- **Ziel Phase B:** Sven kann das Video in **< 30 min** selbst aufnehmen — mit der Geführten Demo, dem
  Skript und der Aufnahme-Checkliste. Gate B→C: Sven nimmt auf und **gibt das Video frei**.
- **Aufnahme-Setup steht bereit:** Geführte Demo = **kuratierte 6er-Kern-Auswahl** (Materialkosten →
  Rechnungsprüfung → Entscheidungskette → Projekt-Portfolio → Governance → **Money-Shot**), Fortschritt
  „n / 6", ≤ 4 min; **Ein-Klick „Zurücksetzen"** in der Topbar für saubere, wiederholbare Takes.
- **Letzter Zyklus (Phase-A-Abschluss):** Geführte Demo auf die kuratierte 6er-Reihenfolge
  (`DEMO_ORDER` + `demoScenarios()`) gekürzt (endet garantiert mit dem Money-Shot; alle 17 bleiben per
  Kachel/Frage/Suche erreichbar) **und** Ein-Klick „Zurücksetzen" (`resetDemo()` + Topbar-Button) für
  wiederholbare Video-Takes. Rein additiv in `app.js`/`styles.css`/`index.html`, `data.js` unverändert
  (kein neues Szenario/Dokument — Feature-Freeze gewahrt). Verifiziert: `node --check` ok, Node-VM (6 IDs
  existieren, Money-Shot letzt, 17 gesamt); live (DOM): Reset räumt Chat/Viewer/Palette → Hero zurück,
  Geführte Demo „1 / 6", Reset mitten in der Demo stoppt sauber, keine Konsolenfehler.
- **Vorletzter Zyklus:** **Phase A — Money-Shot „Agenten dazubuchen"** (Demo-Finale, verkauft das Abo):
  Abschluss-Szenario `agent-dazubuchen` mit Agenten-Marktplatz (`answer.agents`/`appendAgents()`), in der
  Geführten Demo bucht sich der empfohlene Agent hands-free selbst; Antwortkopf ohne Konfidenz-Meter.
- **Vorheriger Zyklus:** Zyklus 24 — **Konfidenz-/Relevanz-Balken laufen mit hoch** (Bewegungs-Politur):
  der Meter-Balken läuft beim Einblenden in ~760 ms (easeOutCubic) von 0 auf den Zielwert statt zu
  springen; Zahl zählt synchron; Popover-Relevanz-Balken laufen einmalig hoch. Rein additiv
  (`animateBar()`/`wireConfPopBars()`).
- **Zuletzt aktualisiert:** 2026-07-10.
- **Prototyp liegt in:** [`prototype/`](prototype/) — per Doppelklick auf `index.html` startbar.
- **Prototyp-Baufortschritt:** **≈ 92 %**; **Phase A abgeschlossen**, Mission jetzt in **Phase B (Video)** (siehe [PROGRESS.md](PROGRESS.md)).

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

## Was in Zyklus 24 gebaut wurde

**Konfidenz-/Relevanz-Balken laufen mit hoch — die letzte fehlende Bewegungs-Politur.** Nach Zyklus 23
waren Breite *und* Belegtiefe rund; der von NEXT_STEPS selbst als „die EINE wichtigste Verbesserung"
markierte Rest war reine **Video-Feinpolitur**: Beim Einblenden einer Antwort zählte die Konfidenz-Zahl
zwar hoch, aber der **Balken** des Konfidenz-Meters (und die Relevanz-Balken der Quellen) sprangen sofort
auf ihren Endwert — im Video sichtbar als „Springen" statt „Wachsen". Neu:
- **Helfer `animateBar(fill, dur)`** (nur `app.js`, analog `animateCounts()`/`countUp()`): liest die
  Zielbreite aus dem inline gesetzten `style.width`, setzt sie auf `0%` und läuft per
  `requestAnimationFrame` **easeOutCubic** in ~**760 ms** auf den Zielwert hoch. `prefers-reduced-motion`
  **oder** Zielwert ≤ 0 → sofort auf den Endwert (kein Sprung-Artefakt, keine leere Animation).
- **Im Antwortkopf verdrahtet:** in `streamAnswer()` läuft der Konfidenz-Balken (`\.conf-bar i`) beim
  Einblenden mit hoch; zusätzlich zählt die **Konfidenz-Zahl** im Kopf (`.conf-meter > b`) über den
  bestehenden `countUp()` mit — Zahl und Balken bewegen sich synchron („passend zum Zahlen-Count-up").
- **Relevanz-Balken im Popover:** neuer `wireConfPopBars(card)` lässt die drei `cp-bar`-Balken der
  Konfidenz-Herleitung beim **ersten** Öffnen des Popovers (Hover/Focus) einmalig hochlaufen (640 ms);
  danach bleiben sie stehen. Nur bei Antworten mit Quellen (Popover vorhanden) verdrahtet.
- **Rein additiv:** `app.js` (`animateBar()` + `wireConfPopBars()` + drei Zeilen in `streamAnswer()`) und
  `styles.css` (ein `will-change: width`-Hinweis auf `.conf-bar i, .cp-bar i` für flüssige Compositor-
  Animation). **Kein neues Dokument, kein Datenpfad-Umbau**; `data.js`/`index.html` unverändert. Bestehende
  Zähl-Animationen (Tempo, Kernzahlen) unberührt.
- **Verifikation:** `node --check app.js` ok; Wiring-Checks bestanden. Live im Browser gegen reale Daten
  (DOM): Klick „Welche Projekte laufen aktuell?" → Konfidenz-Kopf **94 %** (Zahl + Balken 94 %), Balken-
  Endwert **finit** (kein NaN); Popover per `mouseenter` geöffnet → **3 cp-Balken** mit finiten Breiten
  (75/96/92 %); **keine Konsolenfehler**. Reduced-motion-Pfad (headless meldet `reduce`) setzt korrekt
  **sofort** den Endwert — verifiziert (94 % ohne Ramp). Der Motion-Pfad wurde durch `matchMedia`-Override
  angestoßen und zeigte einen echten Zwischenwert **0,04 %** am Frame-Start (Ramp beginnt bei 0) — die
  Vollanimation ist im Headless-Preview timer-/rAF-gedrosselt (bekannte Harness-Grenze; Screenshot-Capture
  ebenfalls instabil), daher DOM/Daten-basiert verifiziert.

## Was in Zyklus 23 gebaut wurde

**Nachtragsangebot an Nordwind — Betas letzte unbelegte Zahl wird ein Original-Beleg.** Nach Zyklus 22
war die Breite rund; die schwächste Stelle blieb **Demo-Firma & Dokumente (90 %)**: Beta nannte in
Statusbericht, Eskalation und Portfolio den **Kunden-Änderungswunsch (+0,4 Mio. €)**, aber der
kaufmännische **Beleg** dazu fehlte — die einzige Beta-Zahl ohne Dokument. Neu:
- **Dokument `nachtrag-nordwind-beta`** (Typ „Nachtragsangebot", Modul Berichte): Nachtragsangebot
  **NA-2026-0037** von Meridian an die **Nordwind Logistik AG** (Bezug Rahmenauftrag NW-2025-0442,
  Änderungswunsch vom 18.03.2026). **Positionstabelle** (Reuse des Beleg-Skins mit `lineItems`):
  Prüfstation 250.000 € + Engineering/SPS-Integration 110.000 € + erweiterte FAT 40.000 € =
  **400.000 € netto**, USt 19 % 76.000 €, **Angebotssumme brutto 476.000 €**. Aussteller = **Meridian**
  (kein extIssuer — Meridian bietet dem Kunden an); **NACHTRAG**-Stempel (Ton `ink`). Datum 27.03.2026
  liegt sauber zwischen Change-Request (18.03.) und Statusbericht (31.03.).
- **In `projekt-beta` eingewoben:** als **3. Quelle** (82 %, Zitat wortgleich im Body), neuer
  Reasoning-Schritt, in `related` ergänzt, neue Folgefrage **„Zeig mir den Nachtrag an Nordwind."** →
  in der Geführten Demo klickbar. Belegt exakt die „+0,4 Mio. €", die der Statustext bereits nannte.
- **Bewusst NICHT** in die `DECISION_CHAIN` eingewoben (die bleibt Alphas entdoppelte Kette). Beta bleibt
  ein eigenständiger, sauber belegter Vorgang.
- **Fast reiner `data.js`-Additiv-Schritt.** Zwei winzige rückwärtskompatible `app.js`-Ergänzungen:
  neuer `DOC_SKINS["Nachtragsangebot"]`-Eintrag + optionales `lineItems.grossLabel` (Fallback
  „Rechnungsbetrag brutto") → Fußzeile liest korrekt „Angebotssumme brutto". Keine bestehenden Belege,
  Skins oder der Antwortpfad verändert.
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **28 Docs** (war 27), **16 Szenarien**,
  **3 E-Mails**, **0 kaputte Referenzen**; alle **3** Beta-Quell-Zitate wortgleich im Body, Relevanzen
  0–100; Arithmetik geprüft (250 + 110 + 40 = 400 netto; +19 % = 476 brutto). Live im Browser (DOM gegen
  reale Daten): Suche „nachtrag" → 1 Treffer (▤); Klick öffnet **`paper-beleg`**, Aussteller **Meridian
  Industrie GmbH**, **NACHTRAG**-Stempel, 3 Positionszeilen + Netto 400.000 / USt 19 % 76.000 /
  **Angebotssumme brutto 476.000**; Beta-Szenario führt `nachtrag-nordwind-beta` in Quellen + Verwandten;
  **keine Konsolenfehler**. (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM/Daten-
  basiert verifiziert.)

## Was in Zyklus 22 gebaut wurde

**Projekt-Portfolio-Überblick — die Parallelität der Projekte auf einen Blick.** Nach Zyklus 21 trug die
Demo zwei gleichwertig belegte Projekte (Alpha im Zeitplan, Beta verzögert), aber die Parallelität war nur
über zwei *getrennte* Fragen erlebbar. Ein CEO/CFO will die **Vogelperspektive**: „Was läuft gerade — und
wo brennt es?" Neu:
- **Szenario `projekt-portfolio`** (Modul Berichte, Konfidenz 94 %): „Welche Projekte laufen aktuell?" —
  Antwort mit **Ampel-Übersichtstabelle** (Projekt · Fortschritt · Budget · Termin · Status): **Alpha**
  62 % · 24,0 Mio. € · Q4 2026 · **✓ im Zeitplan**; **Beta** 48 % · 8,6 Mio. € · Q4 2026 · **⚠ 3 Wo.
  Verzug**. Darunter zwei Erläuterungspunkte (Alpha: Materialbudget genehmigt; Beta: Terminrisiko +
  Gegenmaßnahmen) und ein **aggregiertes Portfolio-Volumen 32,6 Mio. €** (18,8 verausgabt). Ehrlicher
  Schluss: **„1 von 2 Projekten termingefährdet — offen gekennzeichnet, nicht beschönigt."**
- **Quellen = die beiden bestehenden Statusberichte** (`projekt-alpha-status` 96 %, `projekt-beta-status`
  96 %) plus Vorstandsprotokoll (74 %) → der Konfidenz-Tooltip aus Zyklus 20 zeigt automatisch „3 Quellen ·
  höchste Relevanz 96 % · Übereinstimmung hoch". `related` verlinkt beide Statusberichte + Eskalation +
  Protokoll. **Kein neues Dokument** — bewusst Reuse: der Überblick aggregiert, was schon belegt ist.
- **Rein additiv in `data.js`** — kein Code-Umbau (Reuse der bestehenden `<table>`-Antwortstruktur). Als
  **erstes** Berichte-Modul-Tile einsortiert und neu im Hero (12 → **13** Tiles). In der Geführten Demo
  läuft Portfolio **direkt nach** Alpha + Beta (15 → **16** Szenarien) → „im Zeitplan" und „unter
  Terminrisiko" werden erst einzeln, dann in **einer Übersicht** gezeigt — eine starke Klammer im Video.
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **27 Docs**, **16 Szenarien** (war 15),
  **0 kaputte Referenzen**, alle 3 Quell-Zitate **wortgleich** im jeweiligen Body, Relevanzen 0–100;
  Matcher routet „Welche Projekte laufen aktuell?" → `projekt-portfolio` **ohne Kollision** (Alpha/Beta
  lösen weiter korrekt auf; „Zeig mir das Projektportfolio" → portfolio). Live im Browser (DOM gegen reale
  Daten): Hero-Tile + **erstes** Berichte-Tile vorhanden; Klick löst das Szenario auf → Konfidenz-Kopf
  **94 %** + Herleitungs-Tooltip (3 Quellen · höchste Relevanz 96 % · Übereinstimmung hoch); alle
  Tabellenzellen (Alpha 62 %/24,0 Mio./Q4 2026/✓; Beta 48 %/8,6 Mio./Q4 2026/⚠) + Portfolio-Volumen
  **32,6 Mio. €** im DOM; **keine Konsolenfehler**. (Voll-Streaming-HTML-Swap im Headless-Preview
  timer-gedrosselt — bekannte Harness-Grenze; daher DOM/Daten-basiert verifiziert.)

## Was in Zyklus 21 gebaut wurde

**Projekt Beta — die Demo-Firma trägt jetzt mehrere parallele Vorhaben, ehrlich inklusive Risiko.** Der
schwächste Fortschrittsbereich war **Demo-Firma & realistische Dokumente (86 %)**. Bisher zeigte die Demo
mit Alpha nur *eine* Vorzeige-Story (im Zeitplan). Ein skeptischer CFO fragt als Nächstes: *„Ist das nur
diese eine schöne Geschichte, oder trägt es meinen ganzen Betrieb?"* Neu:
- **Szenario `projekt-beta`** (Modul Berichte, Konfidenz 90 %): „Wie steht Projekt Beta?" — eine
  kundenspezifische, automatisierte Verpackungs-/Palettierlinie für die **Nordwind Logistik AG**
  (Engineering München, Endmontage Werk 2). Antwort mit **Ampel-Statustabelle**: Fortschritt **48 %
  ⚠ verzögert**, Budget **8,6 Mio. €** (4,7 verausgabt) im Rahmen, Liefertermin **Q4 2026 ⚠ 3 Wo.
  Verzug** (verschoben von Q3). Ursachen: **Lieferverzug der Steuerungselektronik** (Zulieferer 6 Wochen
  zu spät) + **Kunden-Change-Request** (zusätzliche Prüfstation, +0,4 Mio. €). Risiko: **Pönale** 0,5 %
  je Verzugswoche, gedeckelt bei 5 % (max. 0,43 Mio. €). Gegenmaßnahmen: Zweitquelle Elektronik
  qualifiziert, Change Request kaufmännisch geltend gemacht, wöchentliche Eskalation. Schließt mit dem
  **offenen Kontrast zu Alpha** („im Zeitplan") — *AI Studio kennzeichnet das Risiko, statt es zu
  beschönigen.*
- **Zwei neue Belege** (Modul Berichte):
  - **`projekt-beta-status`** (Typ „Projektbericht" → `paper-bericht`, 6 Highlights): Statusbericht per
    **31.03.2026** — dasselbe Berichtsdatum wie Alpha, also eine echte parallele Momentaufnahme.
  - **`eskalation-beta-elektronik`** (Typ „E-Mail" → `paper-email`, **3. E-Mail der Demo**): Eskalation
    der Projektleitung Beta (Ing. Markus Feldmann) an die **CFO** (Cc **CEO**) zum Lieferverzug + Pönale-
    Risiko + Antrag Zweitquelle; **zitierter Verlauf** = die Zulieferer-Meldung (ElektroSys, Halbleiter-
    Engpass). Nutzt das **bestehende E-Mail-Skin** aus Zyklus 12 — kein Code-Umbau.
- **Bewusst mit der bestehenden Story verzahnt, ohne Kollision:** Betas „Zweitquelle Elektronik"-Motiv
  spiegelt Alphas „Zweitlieferant Ferro Nord"-Thema (Lieferketten-Risiko als roter Faden). `related`
  verlinkt zu `projekt-alpha-status` → der „mehrere Projekte"-Eindruck entsteht direkt beim Lesen.
- **Rein additiv in `data.js`** — kein Code-Umbau (beide Skins rendern das identische Feldschema
  automatisch). Hero (Modul Wissen) 11 → **12 Kacheln**, Berichte 5 → 6, Geführte Demo 14 → **15
  Szenarien** (Beta läuft direkt nach Alpha → „im Zeitplan" gefolgt von „unter Terminrisiko" — ein
  starker Kontrast im Video).
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **27 Dokumente** (war 25), **15
  Szenarien**, **3 E-Mails**, **2 gesperrt** (unverändert), **0 kaputte Referenzen**; beide Quell-Zitate
  liegen wortgleich im Body; alle Relevanzwerte 0–100. Live im Browser (DOM gegen reale Daten):
  Beta-Hero-Kachel vorhanden; Klick löst das Szenario auf → Konfidenz-Meter **90 %** + Herleitungs-
  Tooltip; **Ampel-Tabelle** korrekt (Kopf + 3 Zeilen: 48 %/verzögert, 8,6 Mio. €, Q4 2026), Alpha-
  Kontrast im Text; Suche „beta" findet **beide** Docs (▤ Status, ✉ E-Mail); Eskalations-Mail öffnet
  als **`paper-email`** mit 5 Kopfzeilen (Von/An/Cc/Betreff/Gesendet) + zitiertem Verlauf; Statusbericht
  öffnet als **`paper-bericht`** mit 6 Highlights; **keine Konsolenfehler**. (Voll-Streaming-Pfad im
  Headless-Preview timer-gedrosselt — bekannte Harness-Grenze; daher DOM/Daten-basiert verifiziert.)

## Was in Zyklus 20 gebaut wurde

**Konfidenz-Herleitung — die Prozentzahl im Antwortkopf ist jetzt erklärbar.** Der letzte Skeptiker-
Einwand eines CFOs zielt auf die **Konfidenzzahl selbst** („woher weiß das System das?"). Neu: hovert der
Cursor das Konfidenz-Meter, öffnet sich ein kleines Popover direkt darunter, das die Zahl **aus den
Quellen herleitet**:
- **Drei datengetriebene Faktoren**, je mit Mini-Balken: **Quellen herangezogen** (Anzahl, skaliert auf
  bis zu 4 = voll), **Höchste Relevanz** (Top-Quelle in %), **Übereinstimmung der Belege** — qualitativ
  **einzeln / teilweise / hoch** mit ehrlicher Unterzeile „X von N Belegen ≥ 80 % Relevanz". Titel „So
  ergibt sich die **Konfidenz X %**", Fußzeile *„Keine Behauptung — eine Ableitung aus konkreten Quellen."*
- **Rein datengetrieben** aus dem bestehenden `answer.sources`-Array — **keine neuen Datenfelder**. Ohne
  Quellen (Fallback-Antwort) erscheint **kein** Tooltip. Ehrlich statt beschönigt: `projekt-alpha` (3
  Quellen, aber nur 1 ≥ 80 %) zeigt korrekt **„teilweise"**, `reiserichtlinie` (1 Quelle) **„einzeln"**.
- **Zugänglich:** das Meter ist `tabindex="0"` + `aria-label`; das Popover öffnet auch per Tastatur
  (`:focus-within`), nicht nur per Maus. `prefers-reduced-motion` → keine Transition.
- **Rein additiv:** neue `buildConfPop(answer)` + erweitertes Kopf-Markup in `app.js`, `.conf-pop`-Block
  in `styles.css`; `data.js`/`index.html` unverändert. Bestehender Antwortpfad, Skins und alle Dokumente
  unangetastet. Deterministisch verifiziert (Node-VM gegen `data.js`): **14 Szenarien mit Quellen** (alle
  erhalten den Tooltip), **0 ungültige Relevanzwerte**, Labels korrekt über alle Fälle. Live im Browser
  gegen reale Daten geprüft: Kopf trägt `conf has-pop` + `tabindex="0"`, Popover-Inhalt korrekt hergeleitet
  (Reiserichtlinie 1 Quelle · Top 98 % · „einzeln"), Mini-Balken **25/98/55 %** passend, Popover per
  `:focus-within` sichtbar (opacity 1), **keine Konsolenfehler**. (Screenshot-Capture im Harness instabil,
  `:focus-within`-Tint headless unzuverlässig — bekannte Grenzen; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 19 gebaut wurde

**Reklamations-Vorgang — auch die Ausnahme ist lückenlos belegt, und das Geld kam zurück.** Der
schwächste Fortschrittsbereich war **Demo-Firma & realistische Dokumente (81 %)**. Bisher zeigte die
Demo nur den *sauberen* Beleg-Pfad (Drei-Wege-Abgleich ohne Abweichung). Neu ist der *Ausnahme*-Pfad —
ein vollständiger Qualitäts-/Reklamationsvorgang, bewusst mit der Donau-Story verzahnt:
- **Neues Szenario `reklamation-stahl`** (Modul Audit, Konfidenz 95 %): „Wie haben wir die mangelhafte
  Stahllieferung reklamiert?" Antwort in drei belegten Schritten — **Erkannt** (12 t von 60 t fallen bei
  der Wareneingangsprüfung durch eine **Maßabweichung EN 10029** + Walzhautfehler), **Gerügt**
  (form-/fristgerecht nach **§377 HGB**, Rüge am 2. Tag, Gewährleistungsklausel §12), **Erstattet**
  (Gutschrift **11.040 € netto / 13.137,60 € brutto**). Kernbotschaft: *Mangel erkannt, fristgerecht
  gerügt, Geld zurück.*
- **Zwei neue Dokumente:**
  - **`maengelruege-mr-2026-0091`** (Typ **„Mängelrüge"**, Modul Audit): formale Rüge Meridian →
    Stahlwerk Donau, Bezug Bestellung PO-2026-0684. Neues Beleg-Skin mit rotem **MÄNGELRÜGE**-Stempel,
    Aussteller = Meridian, 3 Highlights (Mangel, §377-HGB-Rüge, Forderung Nachlieferung/Gutschrift).
  - **`gutschrift-gs-2026-0203`** (Typ **„Gutschrift"**, Modul Finanzen): Gutschrift Stahlwerk Donau →
    Meridian mit **Positionstabelle** (12 t × 920 € = 11.040 € netto · USt 19 % 2.097,60 € · brutto
    13.137,60 €), grüner **GUTSCHRIFT**-Stempel, Aussteller = Lieferant (extIssuer).
- **Verzahnt, ohne Kollision:** separate Folgelieferung (PO-2026-0684) — der bestehende saubere
  Drei-Wege-Abgleich (PO-2026-0512 / Rechnung 2026-1843 / WE-2026-0778, 80 t, keine Abweichung) bleibt
  unangetastet. **Rahmenvertrag** um **§12 Gewährleistung** ergänzt → die Zitate von Mängelrüge und
  Gutschrift lösen jetzt auf eine sichtbare Vertragsklausel auf.
- **Rein additiv:** `data.js` (2 Docs + Szenario + §12 + Wiring), `app.js` (2 DOC_SKINS: „Mängelrüge"
  beleg/warn-Stempel, „Gutschrift" beleg/extIssuer/ok-Stempel), `styles.css` (ein Stempel-Ton
  `.stamp-warn`, Rot #b91c1c). Bestehende Skins/Belege/Antwortpfad unverändert. Hero 10 → **11**
  Kacheln, Geführte Demo 13 → **14 Szenarien**; Modul-Vorschläge Audit + Finanzen erweitert.
- **Verifikation:** deterministisch (Node-VM gegen `data.js`) **25 Dokumente** (war 23), **14
  Szenarien**, 2 E-Mails, 2 gesperrt, **0 kaputte Referenzen**, Hero 11; Arithmetik geprüft
  (12 × 920 = 11.040; +19 % = 13.137,60 €). Live im Browser (DOM gegen reale Daten): Suche findet beide
  Belege mit korrektem Modul-Tag; **Gutschrift** öffnet `paper-beleg`, Aussteller „Stahlwerk Donau AG",
  GUTSCHRIFT-Stempel grün, Positionstabelle Netto/USt/Brutto korrekt, 3 Highlights; **Mängelrüge**
  öffnet `paper-beleg`, Aussteller „Meridian Industrie GmbH", MÄNGELRÜGE-Stempel **rot (rgb 185,28,28)**,
  3 Highlights; Szenario-Kopf rendert mit **95 % Konfidenz**; **keine Konsolenfehler**. (Voll-Streaming-
  Pfad im Headless-Preview timer-gedrosselt, Screenshot-Capture instabil — bekannte Harness-Grenzen;
  daher DOM/Daten-basiert verifiziert.)

## Was in Zyklus 18 gebaut wurde

**Such-Beat als automatischer Opener der Geführten Demo — die Command-Palette wird jetzt hands-free
vorgeführt.** Zyklus 17 baute den Such-**Mechanismus**; sein Wert entfaltete sich im Video aber nur,
wenn der Betrachter Strg+K selbst drückte. Jetzt eröffnet die „▶ Geführte Demo" mit einem 6–8-Sekunden-
Such-Beat, *bevor* die erste Frage getippt wird:
- **Neue `demoSearchBeat(token)`** (nur `app.js`): öffnet die Palette **inline** — die manuelle
  `openSearch()` bleibt während der Demo bewusst gesperrt, daher öffnet der Beat den Overlay direkt
  (`search.open`, `hidden=false`, `renderSearchResults("")`, Fokus). Zeigt kurz **„23 Dokumente im
  Wissensspeicher"**, tippt dann **„stahl"** Zeichen-für-Zeichen (je Keystroke `renderSearchResults`) →
  **8 von 23** Treffer quer über **Finanzen · Audit · Verträge** mit gelbem `<mark>`-Highlight.
- **Öffnet einen Beleg:** wählt den ersten **freigegebenen** Treffer (`findIndex(d => !d.locked)`) —
  gesperrte werden übersprungen, damit als Opener **kein** „Zugriff verweigert" erscheint — setzt die
  Auswahl (`setSel`) und öffnet ihn im bestehenden Viewer (`openViewer`), Lesepause, `closeViewer`,
  `closeSearch`; *dann* läuft die bestehende Szenario-Schleife weiter.
- **Verdrahtung:** ein Aufruf in `startDemo()` nach dem Frisch-Start und **vor** der Schleife, in
  `token`-Guards eingefasst. **Fail-safe:** `resetDemoUi()` schließt jetzt zusätzlich `closeViewer()` +
  `closeSearch()` → wird die Demo **mitten im Beat** gestoppt, bleibt kein Overlay/Viewer offen. Voll
  token-gesteuert (Abbruch an jedem Schritt); `prefers-reduced-motion` → sofortiges Tippen + kurze Pausen.
- **Rein additiv** in `app.js`; `data.js`/`styles.css`/`index.html` unverändert (Reuse von
  `renderSearchResults()`/`setSel()`/`openViewer()`/`closeViewer()`/`closeSearch()`/`reducedMotion()`).
  Live im Browser gegen die realen Daten verifiziert: Beat läuft automatisch (Palette → „stahl" → 8/23,
  Module Finanzen/Audit/Verträge, `<mark>` vorhanden), Viewer öffnet auf „Quartalsbericht Q1 2026" und
  schließt wieder, danach **Fortschritt „1 / 13"** + Composer gesperrt (nahtloser Übergang); Stopp mitten
  im Beat räumt Palette + Viewer sauber ab und reaktiviert den Composer; **keine Konsolenfehler**.
  (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM-basiert verifiziert.)

## Was in Zyklus 17 gebaut wurde

**Globale Live-Suche über den gesamten Wissensspeicher (Command-Palette) — der lang offene
„Was steckt alles drin?"-Moment.** Die Demo hatte Breite (13 Szenarien, 23 Dokumente über 6 Ressorts),
aber der Betrachter *fühlte* die schiere **Menge** des erschlossenen Wissens noch nicht. Neu:
- **Sidebar-Auslöser „🔍 Alles durchsuchen"** (mit sichtbarem `Strg K`-Kürzel) direkt unter dem Logo;
  **Strg/⌘ + K** öffnet/schließt die Suche von überall, **Esc** schließt, Klick auf den Backdrop schließt.
- **Zentriertes Command-Palette-Modal** (Notion/Linear/Stripe-Anmutung): großes Suchfeld mit Autofocus,
  Live-Zähler und scrollbare Trefferliste. **Leeres Feld = komplettes Inventar** („23 Dokumente im
  Wissensspeicher — tippen zum Filtern"); beim Tippen filtert es **live** über
  **Titel/Typ/Snippet/Autor/Modul aller Dokumente** (Zähler „X von 23 für ‚…'").
- **Treffer-Zeilen** mit Datei-Icon (✉ für E-Mail), **Modul-Tag + Typ** rechts, Snippet einzeilig,
  und **gelb hervorgehobenem Suchbegriff** (`<mark>`, über eine sichere escape-dann-markieren-Helferin
  `hlMatch()`). **Tastatur:** ↑/↓ bewegt die Auswahl, **Enter** öffnet den markierten Treffer; Maus-Hover
  markiert ebenfalls. Klick/Enter schließt die Suche und öffnet den Beleg im **bestehenden Viewer**.
- **Governance bleibt konsistent:** gesperrte Dokumente erscheinen als Treffer (mit „🔒 Kein Zugriff"),
  öffnen aber die **„Zugriff verweigert"-Ansicht** (`paper-locked`, kein Inhalts-Leak). Während der
  Geführten Demo ist der Auslöser bewusst inaktiv (`if (demo.running) return`), damit nichts kollidiert.
- **Cross-Modul belegt:** eine „stahl"-Suche liefert Treffer aus **Finanzen und Audit** — sichtbar wird,
  dass ein Begriff quer durchs ganze Haus greift.
- **Rein additiv:** `index.html` (Auslöser + Overlay-Markup), `styles.css` (`.search-trigger`,
  `.search-ov`/`.search-panel`/`.sp-*`, reduced-motion-Guard) und `app.js` (`wireSearch()`/`openSearch()`/
  `closeSearch()`/`matchDocs()`/`renderSearchResults()`/`hlMatch()` u. a.); `data.js` und der Antwortpfad
  unverändert. Deterministisch verifiziert (Node-VM gegen `data.js`): **23 Dokumente**, Filter exakt
  (""→23, „stahl"→8, „vertrag"→4, „dsgvo"→2, „donau"→6, kein-Treffer→0), **0 Feld-Fehler**, 2 gesperrte
  Docs. Live im Browser gegen die realen Daten geprüft: Auslöser **und** Strg+K öffnen/schließen, 23
  Zeilen bei leerem Feld + korrekter Zähler, `<mark>`-Highlight vorhanden, ↓+Enter öffnet den Viewer
  (Titel „Bestellung PO-2026-0512" korrekt), gesperrter Treffer öffnet `paper-locked` ohne Leak, **keine
  Konsolenfehler**. (Screenshot-Capture im Harness instabil — bekannte Grenze; daher DOM/CSS-basiert
  verifiziert.)

## Was in Zyklus 16 gebaut wurde

**DSGVO-/Datenschutz-Szenario — die Demo öffnet ein neues Entscheider-Ressort (Compliance/Datenschutz).**
Die Demo war bisher finanzlastig; die schwächsten Fortschrittsbereiche waren **Demo-Firma & Dokumente**
und **Szenarien-Breite**. Zyklus 16 hebt beide mit einem Thema, das jeden CEO/CFO betrifft — rein
additiv in `data.js`, kein Code-Umbau (bestehende Tabellen- und Skin-Renderer wiederverwendet):
- **Neues Szenario `datenschutz-audit`** (Modul Audit, Konfidenz 93 %): „Sind wir DSGVO-konform — wann
  war das letzte Datenschutz-Audit?" Antwort mit **Status-Tabelle** (5 Prüffelder: Art. 30 VVT,
  Art. 32 TOM, Art. 28 Auftragsverarbeitung, Betroffenenrechte/Löschkonzept, 72-h-Meldeprozess), je
  Status **✓** / **⚠ 1 offen**. **Ehrlich statt beschönigt:** zwei offene Auflagen (AV-Vertrag
  Cloud-Backup, Löschkonzept Bewerberdaten) mit klarer Frist **31.03.2026**, „kein akutes Bußgeldrisiko".
- **Zwei neue Dokumente** (Modul Audit):
  - **`datenschutz-audit-2025`** (Typ „Prüfnachweis" → grüner **BESTANDEN**-Stempel im Viewer): das
    jährliche DSGVO-Audit vom 20.11.2025, externe Datenschutzbeauftragte **Dr. Julia Sander**,
    8 Absätze / 6 Highlights (Ergebnis, VVT, TOM, beide Auflagen, Meldeprozess, 0 meldepflichtige
    Vorfälle 2025).
  - **`verarbeitungsverzeichnis-2026`** (Typ „Verzeichnis" → sauberer Fallback aufs Bericht-Skin,
    `paper-bericht`): Verzeichnis nach **Art. 30 DSGVO**, 34 Verarbeitungstätigkeiten, Rechtsgrundlagen
    und Löschfristen (Beschäftigten-/Bewerberdaten).
- **Verdrahtung:** Szenario nach `brandschutz` einsortiert → in der Geführten Demo laufen die beiden
  Audit-/Compliance-Beats direkt hintereinander (jetzt **13 Szenarien**). Hero (Modul Wissen) 9 → **10
  Kacheln**, `audit`-Modul-Vorschläge 2 → 3.
- **Rein additiv** in `data.js`; `app.js`/`styles.css`/`index.html` unverändert. Deterministisch
  verifiziert (Node-VM gegen `data.js`): **23 Dokumente** (war 21), **2 E-Mails**, **13 Szenarien**
  (war 12), **1 chain**, **0 kaputte Referenzen** über alle `sources`/`related`/`withheld`/`chain`/
  `MODULE_SUGGESTIONS`. Live im Browser gegen die realen Daten geprüft: DSGVO-Hero-Kachel vorhanden
  (10 Kacheln), beide neue Karten im Audit-Modul, Datenschutz-Audit öffnet als `paper-nachweis` mit
  **BESTANDEN**-Stempel + 6 Highlights, VVT öffnet als `paper-bericht` mit 3 Highlights, kein
  Ketten-Navigator bei den Nicht-Ketten-Docs, **keine Konsolenfehler**. (Voll-Streaming-Pfad der
  Antwort im Headless-Preview timer-gedrosselt, Screenshot-Capture im Harness instabil — bekannte
  Grenzen; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 15 gebaut wurde

**Ketten-Navigator im Dokumentenviewer — die Entscheidungskette ist jetzt auch beim Lesen der
Einzelbelege navigierbar (Option B aus Zyklus 14).** Zyklus 14 zeigte die Kette als Timeline im Chat;
öffnete man aber einen der drei Belege im Viewer, verlor man den Kontext „wo im Beleg-Pfad bin ich?".
Neu:
- **Kompakter Navigator oben im Viewer** — erscheint automatisch, sobald eines der drei Ketten-
  Dokumente geöffnet wird (Lieferanten-E-Mail → interne Weiterleitung → Vorstandsprotokoll). Zeigt
  **„⛓ Entscheidungskette · Schritt n von 3"**, einen **horizontalen Stepper** mit Datum + Akteur je
  Schritt (aktueller Schritt gefüllt in Marken-Farbe, erledigte Schritte markiert) und eine Fußzeile
  **„← Voriger Beleg / Nächster Beleg →"** plus das Label des aktuellen Schritts. Die Stepper-Punkte
  **und** die Vor/Zurück-Buttons öffnen direkt den jeweiligen Beleg — man klickt sich durch die ganze
  Kette, ohne den Viewer zu verlassen.
- **Fail-safe/ehrlich:** Der Navigator erscheint **nur** bei den drei Ketten-Dokumenten (per
  `chainStepIndex()`); jeder andere Beleg (Quartalsbericht etc.) öffnet unverändert ohne Strip.
  Erster Schritt → „Voriger" deaktiviert, letzter Schritt → „Nächster" deaktiviert (`.disabled`,
  `pointer-events:none`).
- **Kette entdoppelt — eine Quelle der Wahrheit:** die Ketten-Definition liegt jetzt als
  **`const DECISION_CHAIN`** in `data.js` und wird sowohl vom Chat-Block (`answer.chain` in
  `budget-herkunft`) **als auch** vom Viewer-Navigator gelesen. Chat-Timeline und Viewer-Stepper
  bleiben damit garantiert synchron; keine doppelten Datenpflege-Stellen mehr.
- **Rein additiv** in `data.js` (Extraktion + Referenz, kein Inhaltswechsel), `app.js`
  (`chainStepIndex()`/`buildChainNav()`, ein Aufruf in `openViewer()`) und `styles.css`
  (`.vchain`-Block). Bestehende Skins, Dokumente und der Antwortpfad unverändert. Deterministisch
  verifiziert (Node-VM gegen `data.js`): **21 Dokumente**, **2 E-Mails**, **12 Szenarien**, **1 chain**,
  `budget-herkunft.chain === DECISION_CHAIN`, **0 kaputte Referenzen**. Live im Browser gegen die
  realen Daten geprüft: Navigator auf allen 3 Belegen mit korrektem „Schritt n/3"-Zähler, Vor/Zurück
  **und** Stepper-Punkt-Klick wechseln das Dokument korrekt (Titel/Zähler/erledigt-Status stimmen),
  Prev am 1. Schritt und Next am letzten deaktiviert, **kein** Strip bei Nicht-Ketten-Dokumenten,
  aktueller Punkt bindet an `--brand`/`--brand-soft`, keine Konsolenfehler. (Screenshot-Capture im
  Harness instabil — bekannte Grenze; daher DOM/CSS-basiert verifiziert.)

## Was in Zyklus 14 gebaut wurde

**Entscheidungskette als sichtbarer „Beleg-Pfad" im Chat — der stärkste CFO-Moment ist jetzt ohne
Klickarbeit im Bild.** Zyklus 12/13 legten die Daten (zwei E-Mails → CFO → Vorstand); der Betrachter
musste die Kette aber selbst über Quellen-Chips zusammensetzen. Jetzt zeigt die Antwort die
**Herkunfts-Kette als eigenes visuelles Element** — eine kompakte vertikale Timeline:
- **Neues Szenario `budget-herkunft`** (Modul Finanzen, Konfidenz 95 %): „Wie kam das Mehrbudget von
  0,9 Mio. € für Projekt Alpha zustande?" Antwort mit knappem Text **plus** dem neuen Ketten-Block.
- **Neues optionales Feld `answer.chain`** + Renderer **`appendChain()`** (analog zu `appendWithheld()`):
  vertikale Timeline mit **3 Schritten** — je **Datum-Badge**, **Akteur** (z. B. „Einkauf → CFO"),
  **Label**, Beschreibung und **anklickbarem Beleg** (öffnet das Originaldokument im Viewer). Der letzte
  Schritt (Vorstandsbeschluss) ist als `strong` hervorgehoben (gefüllter Punkt, Marken-Farbe).
  Verbindungslinie läuft durch die Punkte und endet sauber am letzten Schritt.
- **Die drei Schritte sind die echten Belege:** Lieferanten-E-Mail (12.02.) → interne Weiterleitung
  Einkauf→CFO mit Bewertung 0,9 Mio. € (13.02.) → Vorstandsbeschluss (März 2026). Alle Zahlen
  konsistent mit der bestehenden Story (640 t × 120 €/t ≈ 0,9 Mio. € = beschlossenes Mehrbudget).
- **Als erster strukturierter Block** unter der Antwort platziert (vor Nachvollziehbarkeit/Quellen) →
  maximale Wirkung; wird vom bestehenden gestaffelten Block-Reveal automatisch mitanimiert.
- **Rein additiv** in `data.js` / `app.js` / `styles.css`; bestehender Antwortpfad und alle Dokumente
  unverändert. Hero 8 → **9 Kacheln**, „Geführte Demo" nimmt das Szenario automatisch auf (jetzt
  **12 Szenarien**). Deterministisch verifiziert (Node-VM gegen `data.js`): **21 Dokumente**, **2
  E-Mails**, **12 Szenarien**, **1 Szenario mit `chain`**, **0 kaputte Referenzen** über alle
  `sources`/`related`/`withheld`/`chain`/`MODULE_SUGGESTIONS`. Chain-Markup + CSS live im Browser gegen
  die realen Szenariodaten geprüft: 3 Schritte, alle anklickbar, 1 `strong`, Punkte/Datum-Badges/
  Beleg-Links binden korrekt an die Marken-Tokens (--brand/--brand-soft/--brand-ink), Verbindungslinie
  2 px und am letzten Schritt beendet; keine Konsolenfehler. (Voll-Streaming-Pfad im Headless-Preview
  timer-gedrosselt, Screenshot-Capture im Harness instabil — bekannte Grenzen; daher DOM/CSS-basiert
  verifiziert.)

## Was in Zyklus 13 gebaut wurde

**Zweite E-Mail (interne Weiterleitung) — die Entscheidungskette quer durch Postfächer ist jetzt
belegt.** Zyklus 12 setzte das E-Mail-Skin und die auslösende Lieferanten-E-Mail; eine einzelne
E-Mail riss die Kern-Erzählung aber nur an. Jetzt zeigt die Demo den **Thread über zwei Nachrichten**
und verbindet **E-Mail → CFO → Vorstandsbeschluss**:
- **Neues Dokument `email-weiterleitung-materialbudget`** (Typ **„E-Mail"**, Modul Finanzen): die
  **WG-Weiterleitung** der Donau-Preis-E-Mail von **Thomas Krüger (Einkauf)** an **Dr. Katharina
  Vogel (CFO)** (Cc Projektleitung Alpha), 13.02.2026. Kernaussage im Highlight: **~640 t
  Jahresbedarf × +120 €/t → rund 0,9 Mio. € Mehrbedarf** für Projekt Alpha; **Empfehlung**,
  das Mehrbudget als Vorstands-Beschlussvorlage einzubringen und Ferro Nord zu beschleunigen.
  **Zitat-Verlauf** = die Original-Donau-E-Mail → sichtbarer Zwei-Nachrichten-Thread.
- **Verzahnt mit der bestehenden Story (kein neuer Wert):** die 0,9 Mio. € stammen exakt aus dem
  **Vorstandsbeschluss TOP 2** (`vorstandsprotokoll-2026-03`). Die Weiterleitung ist die
  **Herkunft dieser Zahl** — der bisher fehlende Beleg, *warum* der Vorstand das Mehrbudget genehmigt
  hat.
- **In zwei Szenarien eingewoben:** „Warum sind die Materialkosten gestiegen?" (E-Mail als **3.
  Quelle**, 81 %, + Verwandte + Reasoning-Schritt Einkauf → CFO) und „Fasse Projekt Alpha zusammen"
  (E-Mail als Quelle für die Herkunft des Mehrbudgets, neuer Reasoning-Schritt zur Entscheidungskette).
  Beide sind Teil der Geführten Demo → das Skin und der Thread erscheinen automatisch im Video.
- **Rein additiv in `data.js`** — kein Code-Umbau (E-Mail-Skin aus Zyklus 12 rendert das identische
  Feldschema automatisch). Deterministisch verifiziert (Node-VM gegen `data.js`): **21 Dokumente**
  (war 20), **2 E-Mails**, **11 Szenarien**, **0 kaputte Referenzen** über alle `sources`/`related`/
  `withheld`/`MODULE_SUGGESTIONS`.

## Was in Zyklus 12 gebaut wurde

**E-Mail-Skin im Dokumentenviewer — „Wissen steckt in E-Mails" ist jetzt im Bild sichtbar.**
Die Mission-Story nennt E-Mails ausdrücklich als Ort, an dem Firmenwissen gefangen ist; im Viewer
gab es dafür bisher kein eigenes Skin. Neu:
- **Neues Dokument `email-preisanpassung-donau`** (Typ **„E-Mail"**, Modul Finanzen): die
  **Original-Ankündigung von Stahlwerk Donau** über die 15-%-Preisanpassung auf Baustahl S355 zum
  01.03.2026 — der **auslösende Beleg** hinter dem Materialkostenanstieg. Bewusst mit der bestehenden
  Story verzahnt: 800 € → 920 € (**+15 %** = die vertragliche Preisgleitklausel §6 aus dem
  Rahmenvertrag RV-2023-014; die +17,9 % im Q1-Bericht sind der Jahresvergleich). CC an die CFO,
  **Anhang-Chip** „Preisliste_2026_Stahlwerk-Donau.pdf · 148 KB", **Zitat-Verlauf** der vorherigen
  Anfrage des Einkaufs (Thomas Krüger).
- **E-Mail-Skin** (`DOC_SKINS["E-Mail"] = { cat: "email" }`): Postfach-Kopf mit **Avatar-Initialen**
  (Verlauf Cyan→Indigo), **Von/An/Cc/Betreff/Gesendet**-Zeilen (Betreff fett via `.mr.sub`),
  Anhang-Chip und zitiertem Verlauf (`.mail-quote`, linker Balken). Neue Helfer in `app.js`:
  `buildMailHead()`, `buildQuoted()`, `mailRow()`; `buildPaper()` verzweigt für `cat === "email"`
  (Postfach-Kopf statt Briefkopf, Betreff ersetzt die generische Überschrift). In der Bibliothek
  trägt die E-Mail-Karte ein **✉-Icon** statt ▤.
- **In die Materialkosten-Story eingewoben:** die E-Mail ist jetzt **2. Quelle** (88 %) der Antwort
  „Warum sind die Materialkosten gestiegen?" (nach dem Q1-Bericht), steht in „Verwandte Dokumente"
  und ist als zusätzlicher Reasoning-Schritt genannt („Auslösende Lieferanten-E-Mail … im
  Einkaufs-Postfach identifiziert"). Dadurch **klickbar in der Geführten Demo** → das E-Mail-Skin
  erscheint automatisch im Video.
- **Rein additiv** in `data.js` / `app.js` / `styles.css`; bestehende Skins, Dokumente und der
  Antwortpfad unverändert. Verifiziert: E-Mail-Karte mit ✉ + Typ „E-Mail" in Finanzen, Viewer öffnet
  `paper-email` mit korrektem Kopf (Initialen „AH", 5 Zeilen, Betreff fett), Anhang-Chip
  (148 KB), 2 Highlights, Zitat mit 3 Zeilen; **0 kaputte Referenzen** (20 Dokumente), keine
  Konsolenfehler. (Layout-Maße im Headless-Preview nicht messbar — 0×0-Viewport, bekannte
  Harness-Grenze; CSS parst/greift, spiegelt das bewährte `.lh`-Briefkopf-Flexmuster.)

## Was in Zyklus 11 gebaut wurde

**Bewegungs-Politur — die Antwort baut sich souverän auf, statt zu springen.** Inhaltlich war die
Demo komplett; die härteste verbleibende Kante war das etwas sprunghafte Ein-/Umblenden. Jetzt:
- **Gestaffelter Block-Reveal:** die strukturierten Blöcke unter jeder Antwort
  (Nachvollziehbarkeit → Quellen → Verwandte → Folgefragen → Aktionen) blenden **nacheinander**
  ein (neue Keyframe `block-rise`, Fade + 9 px Slide-up, ~0,42 s). `revealBlocks()` in `app.js`
  vergibt je Block eine additive Verzögerung **+55 ms** über die CSS-Variable `--rev-delay` — die
  Antwort „wächst" von oben nach unten statt komplett auf einmal zu erscheinen.
- **Sanfter Modulwechsel:** der neu gerenderte Panel-Inhalt (`.wrap`) blendet dezent ein
  (Keyframe `view-in`, Fade + 7 px Slide-up, ~0,32 s) — beim Wechsel Wissen ↔ Finanzen/Audit/HR/
  Verträge/Berichte/Einstellungen ein weiches Überblenden statt hartem Umschalten. Feuert nur beim
  View-Render; die Chat-Antworten behalten ihre eigene `.msg`-`rise`-Animation.
- **Ehrlich/fail-safe:** `prefers-reduced-motion: reduce` deaktiviert **beide** Effekte sauber —
  `revealBlocks()` steigt früh aus (kein `.reveal`-Klassen-Anhang) und die CSS-Regeln setzen
  `animation: none`. Da die Startopazität nur **im Keyframe** liegt, bleiben alle Blöcke ohne
  Animation voll sichtbar (opacity 1) — **kein Risiko unsichtbarer Inhalte**.
- **Rein additiv:** `styles.css` (zwei Keyframes + `.answer .block.reveal` / `.wrap`-Regel, je mit
  reduced-motion-Guard) und ein kleiner `revealBlocks()`-Helfer in `app.js`; `data.js` und der
  Antwortpfad unverändert. Deterministisch im Browser verifiziert: im Normalbrowser `block-rise`
  mit exaktem Delay (`--rev-delay:110ms` → `animation-delay: 0,11 s`); unter reduzierter Bewegung
  `animationName: none` bei opacity 1. (Streaming-Vollpfad im Headless-Preview durch Timer-
  Throttling zu langsam für Live-Beobachtung → mechanisch/deterministisch geprüft.)

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

**Kunden-Beauftragungsbeleg — den Nachtrag an Nordwind zu einem echten Zwei-Schritt-Vorgang schließen.**
Nach Zyklus 24 ist die **Bewegungs-Politur vollständig** (Zahlen *und* Balken laufen hoch; Blöcke blenden
gestaffelt ein). Der stärkste verbleibende Tiefen-Schritt: Beta hat mit `nachtrag-nordwind-beta` das
**Angebot** über 476.000 € brutto (Meridian → Nordwind), aber die **Kunden-Seite** fehlt noch — ein kurzer
**Beauftragungs-/Bestätigungsbeleg** (Nordwind bestätigt NA-2026-0037 schriftlich, z. B. „Bestellung/
Freigabe zum Nachtrag") würde den Vorgang zu einem sauberen **Angebot → Auftrag**-Paar schließen und die
+0,4 Mio. € beidseitig belegen. Reuse des bestehenden `paper-email`- **oder** `paper-beleg`-Skins (Typ
„Auftragsbestätigung"), Aussteller = **Nordwind** (extIssuer), als **4. Quelle** ins `projekt-beta`-
Szenario. Rein additiv in `data.js`; höchstens ein `DOC_SKINS`-Eintrag in `app.js`.

*Warum?* Die Bewegung ist jetzt rund, die Breite steht (16 Szenarien, 28 Dokumente über 6 Ressorts). Der
größte Rest-Grenznutzen liegt darin, den **einen offenen kaufmännischen Loop** (Angebot ohne sichtbare
Annahme) zu schließen — genau die Nachweis-Vollständigkeit, die ein CFO im Video honoriert („nicht nur
angeboten, sondern beauftragt").

**Alternative (Politur):** die **Balken-Ramp im Video real sichtbar machen** — im Headless-Preview ist die
Vollanimation rAF-gedrosselt; in einem echten Browser läuft sie. Kein Code-Bedarf, nur ein Hinweis fürs
Aufnahme-Setup (echten Chrome ohne reduced-motion nutzen). In VIDEO_SCENES.md notiert.

**Nicht dupliziert (bewusst):** Beta bleibt **außerhalb** der `DECISION_CHAIN` (Alphas entdoppelte Kette).

---

## CEO-Review (Ende Zyklus 24)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Antwort „wächst" jetzt souverän auf: das
  Tempo-Signal, die Kernzahlen, die Konfidenz-Zahl **und** ihr Balken laufen synchron hoch, die Blöcke
  blenden gestaffelt ein. Im Video wirkt das System nicht mehr wie ein Sprung ins fertige Ergebnis, sondern
  wie ein Assistent, der die Antwort in Echtzeit belegt.
- *Versteht ein CFO den Nutzen?* — Der Nutzen war schon da; dieser Zyklus poliert die **Wahrnehmung**: ein
  live hochlaufendes Konfidenz-Meter liest sich als „das System *rechnet* seine Sicherheit aus", nicht als
  vorgefertigte Zahl. Kleiner Hebel, aber genau die Kante, die ein Verkaufsvideo professionell macht.
- *Schwächste Stelle → nächster Zyklus:* inhaltlich der eine offene kaufmännische Loop — Betas Nachtrag ist
  **angeboten**, aber die **Kunden-Beauftragung** fehlt noch als Beleg. Siehe oben.

## CEO-Review (Ende Zyklus 23)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Beta zeigt jetzt nicht nur ehrlich ein Risiko,
  sondern belegt **jede** genannte Zahl mit einem Original: Statusbericht, Eskalations-E-Mail und jetzt das
  **Nachtragsangebot über 476.000 € brutto** an den Kunden. Die „+0,4 Mio. €" sind keine Behauptung mehr,
  sondern ein anklickbarer Beleg mit Positionstabelle.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„selbst der Änderungswunsch im schwierigen Projekt ist
  kaufmännisch sauber dokumentiert — ich sehe, wie wir das beim Kunden geltend machen."* Genau die
  Prüfungs- und Nachweis-Sicherheit, die Alpha und der Reklamations-Vorgang bereits vormachen.
- *Schwächste Stelle → nächster Zyklus:* rein visuell — das Konfidenz-/Relevanz-Meter springt beim
  Einblenden noch, statt hochzulaufen. Balken-Animation als letzte Politur. Siehe oben.

## CEO-Review (Ende Zyklus 22)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo zeigt jetzt nicht nur zwei Projekte
  einzeln, sondern **beide auf einen Blick** in einer Ampel-Übersicht: Alpha ✓ im Zeitplan, Beta ⚠ unter
  Terminrisiko, Portfolio-Volumen 32,6 Mio. € — die Vogelperspektive, die ein CEO/CFO zuerst sehen will.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„eine Frage, und ich sehe mein ganzes Projektportfolio —
  inklusive dem, das gerade schwierig läuft."* Der ehrliche Schluss („1 von 2 termingefährdet, offen
  gekennzeichnet") macht die Übersicht glaubwürdig statt beschönigt.
- *Schwächste Stelle → nächster Zyklus:* Betas Change-Request (+0,4 Mio. €) ist die letzte **unbelegte**
  Beta-Zahl — ein Nachtragsbeleg an Nordwind schließt die Lücke. Siehe oben.

## CEO-Review (Ende Zyklus 21)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo zeigt nicht mehr nur eine perfekte
  Geschichte (Alpha, im Zeitplan), sondern ein **zweites, reales Projekt (Beta) unter Terminrisiko** —
  mit Ampel-Status, Pönale-Risiko und Gegenmaßnahmen, jeder Punkt belegt. In der Geführten Demo folgt
  „im Zeitplan" direkt auf „unter Terminrisiko" — ein glaubwürdiger Kontrast.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„das System zeigt mir auch das Projekt, das gerade
  schwierig läuft — und verschweigt das Risiko nicht."* Genau dieses **ehrliche** Verhalten schafft
  Vertrauen; eine Demo, in der alles grün ist, wirkt unglaubwürdig.
- *Schwächste Stelle → nächster Zyklus:* die **Parallelität der Projekte** ist noch über zwei getrennte
  Fragen verteilt — ein Portfolio-Überblick („Welche Projekte laufen aktuell?") macht sie auf einen
  Blick sichtbar. Siehe oben.

## CEO-Review (Ende Zyklus 20)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Demo beweist Belege pro Antwort nicht mehr
  nur (Quellen, Relevanz, Konfidenzzahl) — sie **erklärt** die Konfidenzzahl jetzt am Meter: hovert der
  Cursor, zeigt ein Popover *„3 Quellen · höchste Relevanz 97 % · Übereinstimmung hoch"*. Die 95 % sind
  sichtbar keine Behauptung, sondern eine Ableitung.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: der häufigste Skeptiker-Reflex („woher weiß das System
  das?") wird in einer Sekunde entkräftet, ohne dass jemand eine Formel erklären muss. Und es bleibt
  **ehrlich** — bei nur teilweiser Beleglage sagt der Tooltip „teilweise", nicht „hoch".
- *Schwächste Stelle → nächster Zyklus:* Breite der Demo-Firma — ein **zweites Projekt (Beta)** neben
  Alpha, gleichwertig belegt. Siehe oben.

## CEO-Review (Ende Zyklus 19)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Neben dem Wow-Opener (Such-Beat) zeigt die Demo
  jetzt einen Vorgang, der jeden CFO/Auditor überzeugt: eine **mangelhafte Stahllieferung** wurde
  erkannt, **fristgerecht nach §377 HGB gerügt** und per **Gutschrift (11.040 € netto) erstattet** —
  jeder Schritt mit Originalbeleg. Die Demo beweist damit nicht nur den *sauberen* Pfad
  (Drei-Wege-Abgleich), sondern auch, dass die **Ausnahme** lückenlos dokumentiert ist.
- *Versteht ein CFO den Nutzen?* — Ja, sofort: *„auch als etwas schiefging, haben wir es sauber
  dokumentiert und das Geld kam zurück"*. Das ist Governance und Prüfungssicherheit in einem Satz.
- *Schwächste Stelle → nächster Zyklus:* Breite und Tiefe stehen; der letzte Hebel ist **Politur der
  Belegbarkeit** — ein Konfidenz-Tooltip, der die Prozentzahl aus den Quellen herleitet. Siehe oben.

## CEO-Review (Ende Zyklus 18)

- *Würde ich das morgen einem Kunden zeigen?* — **Ja.** Die Geführte Demo eröffnet jetzt mit einem
  Wow-Bild: die Command-Palette öffnet sich von selbst, tippt „stahl" und sammelt in Millisekunden
  **8 Treffer quer durch Finanzen und Audit** — bevor überhaupt die erste Frage läuft. Ein Klick, und
  das ganze Video läuft hands-free.
- *Erzeugt es Aufregung?* — Ja: Der Betrachter sieht als **Erstes** die schiere Menge des erschlossenen
  Wissens („23 Dokumente im Wissensspeicher") und wie ein einziges Stichwort quer durchs Haus greift.
  Genau das „mein Unternehmen besitzt das alles bereits"-Gefühl, am stärksten möglichen Ort platziert.
- *Versteht ein CFO/CEO den Nutzen?* — Ja: erst *„so viel liegt schon da"*, dann *„und ich kann es
  einfach fragen"*. Der Such-Beat und die Frage-Sequenz erzählen zusammen eine geschlossene Geschichte.
- *Schwächste Stelle → nächster Zyklus:* Mechanik, Politur und Choreografie sind rund; der letzte Hebel
  ist **inhaltliche Dichte** — ein weiterer authentischer, quervernetzter Beleg-Vorgang (Demo-Firma 81 %).
  Siehe oben.
