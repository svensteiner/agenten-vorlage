# Pilot vorführen — Muster Bau GmbH

> **Für Sven. Vorführbereit seit 2026-08-17.** Doppelklick auf **`PILOT_ZEIGEN.bat`**,
> der Browser öffnet sich, die Demo läuft. Nichts zu installieren, nichts zu konfigurieren,
> keine Internetverbindung nötig.
>
> **Was hier läuft, ist keine Attrappe:** dieselbe Anwendung, die ein Pilotkunde bekommt —
> nur mit einem synthetischen Kunden bespielt. Der Umbau auf einen echten Interessenten ist
> **ein Wort in einer Datei** (§5).

---

## 1 · Starten

| Schritt | Was passiert |
|---|---|
| Doppelklick auf `PILOT_ZEIGEN.bat` | Ein schwarzes Fenster geht auf und bleibt offen — **nicht schließen**, das ist der Server. |
| Nach ~1 Sekunde | Der Browser öffnet `http://127.0.0.1:8777` mit der Demo. |
| Beenden | Das schwarze Fenster schließen (oder Strg+C). |

**Wenn der Browser nicht von selbst aufgeht:** im schwarzen Fenster steht die Adresse —
manuell in den Browser tippen. Ist Port 8777 belegt (ein zweites Demo-Fenster läuft noch),
weicht der Starter automatisch auf 8778, 8779 … aus und nennt die tatsächliche Adresse.

**Vor dem Kundentermin, einmal:** Fenster auf 1920×1080 oder Vollbild (F11), Browser-Zoom auf
100 % (Strg+0), und ein Probelauf der geführten Demo — damit im Termin nichts zum ersten Mal passiert.

---

## 2 · Was der Kunde sieht

**Die Firma:** Muster Bau GmbH, Hoch- & Tiefbau Region Süd, Augsburg · Werkhof Kempten,
gegründet 1998, 180 Mitarbeitende, 48 Mio. € Umsatz 2025.

**Alles daran ist erfunden** — Firma, Personen, Dokumente, Zahlen. Das ist der Punkt, nicht
die Einschränkung: Es beweist das 48-Stunden-Versprechen aus dem
[One-Pager](PILOT_ONE_PAGER.md), ohne dass der Interessent ein einziges eigenes Dokument
herausgeben muss.

**Der Bestand:** 29 Dokumente (Rechnungen, Verträge, Protokolle, Berichte, E-Mails),
17 Szenarien insgesamt — davon 3 in der geführten Vorführung plus das Finale.

---

## 3 · Der Ablauf (20 Minuten)

Die geführte Demo läuft **hands-free** in dieser Reihenfolge. Die drei ersten Szenarien
stammen aus der Pilot-Konfiguration, das Finale hängt die Anwendung immer selbst an.

| # | Frage auf dem Schirm | Worauf Sven zeigt |
|---|---|---|
| 1 | „Warum sind die Materialkosten gestiegen?" | Die Antwort **mit Quellen und Konfidenzwert**. Auf einen Beleg klicken — der Pfad ist sichtbar (`SharePoint › …`). Satz dazu: *„Jede Zahl hier hat eine Herkunft, die Sie anklicken können."* |
| 2 | „Wie steht Projekt Beta?" | Dass die Antwort **mehrere Dokumente zusammenzieht** — nicht ein Suchtreffer, sondern ein Sachstand. |
| 3 | „Erstelle eine Zusammenfassung für den Vorstand." | Der Moment für kaufmännische Leitungen: **die Fleißarbeit fällt weg**, die Belege bleiben. |
| 4 | „Kann ich einen weiteren Agenten dazubuchen?" | **Das Finale — und der einzige Verkaufsmoment.** Hier steht das Abo-Modell auf dem Schirm. Nicht überreden, nur zeigen und schweigen. |

**Die drei Bedienelemente:** `▶ Geführte Demo` (läuft von allein), `⟲ Zurücksetzen`
(vor dem nächsten Termin), und das Eingabefeld — dort kann der Kunde **selbst tippen**.

> **Der stärkste Moment ist nicht Punkt 4, sondern der Augenblick, in dem der Kunde selbst
> tippt.** Wer im Audit-Call Frage F8 beantwortet hat („Welche Frage tippen Sie als Erstes
> ein?"), bekommt hier seine eigene Frage zurück — deshalb wird sie im
> [Leitfaden](business/drafts/2026-08-07_audit-call-leitfaden.md) wörtlich mitgeschrieben.

---

## 4 · Die vier Einwände — und was auf dem Schirm die Antwort ist

Die Antworten stehen ausführlich im [Audit-Call-Leitfaden §6](business/drafts/2026-08-07_audit-call-leitfaden.md).
Hier nur, **worauf man dabei zeigt**:

| Einwand | Was zeigen |
|---|---|
| „Verlassen unsere Daten das Haus?" | Das schwarze Fenster: `127.0.0.1`. Es läuft auf **diesem** Rechner, ohne Internet. Das ist keine Behauptung, das ist sichtbar. |
| „Erfindet die KI Antworten?" | Auf einen Beleg klicken. Quelle, Pfad, Konfidenzwert. |
| „Sieht dann jeder alles?" | Das Governance-Szenario zeigt „für Sie nicht freigegeben" **statt** Inhalt. |
| „Wer nutzt das schon?" | Nichts zeigen. Ehrlich antworten (Leitfaden §6). **Keine Kundennamen erfinden** — es gibt keine. |

---

## 5 · Auf einen echten Interessenten umbauen

Alles Kundenspezifische steht in **einer** Datei: [`prototype/pilot.config.js`](prototype/pilot.config.js).

1. **Firmenkarte** (`company`): Name, Tagline, Glyph, Akzentfarbe, die vier Fakten.
2. **Die 3 Szenarien** (`scenarios`): aus der [SCENARIO_LIBRARY.md](SCENARIO_LIBRARY.md) nach
   dem Schmerz wählen, den der Kunde im Audit-Call genannt hat. Das Finale wird automatisch angehängt.
3. **Namen und Orte** (`corpusReplace`): Personen und Standorte des Vorkunden auf die des
   neuen Piloten mappen.

**Danach zwingend:**

```bash
node scripts/verify_pilot.js
```

Der Lauf muss **„vorführbereit"** melden. Er prüft unter anderem, dass **kein Name des
Vorkunden** übrig ist — inklusive der umlautlosen Schreibweisen, die in Dateipfaden stehen.
Genau dort steckte am 2026-08-17 der letzte Rest (`…_Logistik_Nuernberg.pdf`), und genau so
ein Rest ist die Sorte Detail, die im Termin auffällt.

> **Zwei Regeln beim Umbau:**
> **(a) Zu jedem Quellnamen mit Umlaut gehört die ASCII-Variante** — Pfade schreiben `ue`, nicht `ü`.
> **(b) Jeder Ort, der in einem Beleg vorkommt, muss in der Firmenkarte stehen.** Sonst nennt
> ein Dokument einen Standort, den die Firma laut eigener Karte nicht hat.

**Zurück auf die Standarddemo:** in `pilot.config.js` `active: true` → `active: false`.
Sonst nichts. Der Prüflauf bestätigt auch diese Richtung.

---

## 6 · Was diese Demo **nicht** kann

- **Sie ist noch nie vor einem Kunden gelaufen.** Null Vorführungen. Alles unten Beschriebene
  ist geprüft, aber nicht erprobt.
- **Sie beantwortet nur, was vorbereitet ist.** Tippt der Kunde eine Frage außerhalb der
  17 Szenarien, kommt keine kluge Antwort. *Umgang damit: die Frage mitschreiben und sagen,
  dass genau das der Inhalt seiner eigenen 48-Stunden-Demo wäre — das ist der Verkauf, nicht die Panne.*
- **Kein Rechtekonzept, nur dessen Darstellung.** Das Governance-Szenario **zeigt** eine
  Sperre. Ein echtes Berechtigungssystem ist Teil der Foundation, nicht des Piloten.
- **Kein Video.** Die Aufnahme ist weiterhin offen ([NEXT_STEPS.md](NEXT_STEPS.md)) — in
  automatisierten Läufen lässt sich der Bildschirm nicht abfilmen. Diese Anleitung ersetzt
  das Video für den Fall „Sven zeigt es selbst"; für „läuft ohne Sven" braucht es weiterhin eine Aufnahme.
- **Der Prüflauf prüft Daten, keine Optik.** Layout, Konsolenfehler und das Abspielen der
  geführten Demo sieht nur, wer sie im Browser laufen lässt. Deshalb der Probelauf in §1.
