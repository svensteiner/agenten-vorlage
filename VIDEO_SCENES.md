# VIDEO_SCENES — Aufnahme-Shotlist

> Konkrete Klick-/Kamera-Abfolge zur Aufnahme des Videos aus
> [`prototype/index.html`](prototype/index.html). Ergänzt [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

> **Schnellster Weg zur Aufnahme:** Statt manuell zu klicken kann der **▶-Button
> „Geführte Demo"** (oben rechts) die gesamte Abfolge unten hands-free abspielen — Frage
> tippt sich selbst, Antwort streamt, Fortschritt „n / 8". Sprecher nur drüberlegen. Tab
> dabei im Vordergrund halten (Hintergrund-Tabs drosseln Tipp-/Streaming-Tempo).

| # | Dauer | Aktion in der App | Kamera / Fokus |
|---|-------|-------------------|----------------|
| 0 | 0:20 | App im Vollbild öffnen (**Storage vorher leeren** → **Onboarding-Coachmark** erscheint mit Pfeil auf den pulsierenden Demo-Button). Klick auf **„▶ Geführte Demo starten"** — Overlay schließt & die Demo läuft ab hier automatisch | Kurz auf das Coachmark (Satz + Pfeil) halten, dann langsamer Einzoom auf Überschrift & Vorschlagskarten |
| 1 | 0:25 | Klick auf Karte *Reiserichtlinie* | Antwort-Streaming zeigen; kurz auf Konfidenz 98 % halten |
| 2 | 0:30 | Composer: *„Warum sind die Materialkosten gestiegen?"* eintippen, Enter | Auf Nachvollziehbarkeit-Schritte & 3 Quellen schwenken |
| 3 | 0:30 | *„Zeig mir die Belege zu Rechnung 2026-1843."* → Quelle *Rechnung 2026-1843* anklicken | Viewer öffnet von rechts als **echtes Rechnungs-Dokument** (Lieferanten-Briefkopf, rotierter **EINGANG-Stempel**); auf die **Positionstabelle** zoomen — Menge 80 t · 920 € · **Netto/USt/Brutto** — dann zusätzlich *Bestellung* & *Wareneingang* öffnen: gleiche Position & Beträge = **Drei-Wege-Abgleich** |
| 4 | 0:25 | Viewer schließen (✕) → *„Finde alle Verträge mit automatischer Verlängerung."* | Auf die Tabelle mit ⚠-Frist zoomen |
| 5 | 0:30 | *„Wie hat sich unser CO₂-Fußabdruck entwickelt — sind wir auf ESG-Kurs?"* | Auf die **CO₂-Trend-Tabelle** (2020 → 2025 → Ziel 2030) und das **Fazit** halten; Quelle *Energie- & Emissionskennzahlen 2025* kurz öffnen |
| 6 | 0:20 | *„Erstelle eine Zusammenfassung für den Vorstand."* | Ganze Antwort im Bild; langsam nach unten scrollen (Finanzen + ESG in einem Briefing) |
| 7 | 0:05 | (Standbild) Seitenleiste + Logo | Fade-out |

## Alternative B-Roll (optional)
- Modul **Verträge** öffnen → Dokumentenbibliothek als Raster zeigen (Breite des Wissens).
- Modul **Einstellungen** → „Datenquellen" (SharePoint, SAP, Fileserver … ● verbunden)
  — untermauert „Ihr Unternehmen besitzt die Daten bereits".
- Modul **Audit** → *Feuerbeschau-Protokoll Werk 2* öffnen → grüner **BESTANDEN-Stempel**
  auf dem behördlichen Nachweis (starkes „prüfungssicher"-Signal).
- Modul **Verträge** → *Rahmenvertrag Stahlwerk Donau* öffnen → **Unterschriftszeilen**
  beider Parteien am Blattende (wirkt wie ein echter Vertrag).

## Technisch
- 1920×1080, 60 fps, System-Cursor sichtbar lassen.
- Heller Modus (Standard). Kein Dark Mode für das Video.
- Zwischen Szenen Seite neu laden (F5) für saubere Hero-Ansicht.
- Onboarding-Coachmark erscheint nur beim ersten Laden (`localStorage`-Flag
  `aistudio.onboarded.v1`). Fürs Intro Storage leeren oder Inkognito-Fenster nutzen.
- Ton: ruhige Sprecherstimme, dezenter Corporate-Underscore.
