# AI Studio — Kundendemonstrations-Prototyp

Eine schöne, schnelle Enterprise-Demo, die zeigt, wie AI Studio das im Unternehmen
verstreute Wissen (Verträge, Rechnungen, Berichte, Richtlinien) sofort nutzbar macht.
Gebaut für die **Verkaufsvideo-Aufnahme** und Live-Vorführungen.

> **Alle Daten sind frei erfunden** (fiktive „Meridian Industrie GmbH"). Keine echten Kundendaten.

## Starten

Kein Build, kein Server, keine Installation nötig:

1. `prototype/index.html` per Doppelklick im Browser öffnen — **fertig.**

Falls der Browser lokale Skripte über `file://` blockiert, alternativ mit
Mini-Server starten und `http://127.0.0.1:8123` öffnen:

```bash
cd prototype
python -m http.server 8123
```

## Was die Demo zeigt

- **Geführte Demo (▶ oben rechts)** — spielt alle 8 Szenarien **hands-free** nacheinander
  ab: die Frage tippt sich selbst in den Composer, die Antwort streamt, kurze Lesepause,
  dann das nächste Szenario (Fortschritt „n / 8", jederzeit stoppbar). Ideal für die
  Videoaufnahme und einen Messestand-Loop. *(Tab beim Aufnehmen im Vordergrund halten.)*
- **Chat als Zentrum** — Frage in natürlicher Sprache, gestreamte Antwort.
- **Jede Antwort belegt** — Antwort · Nachvollziehbarkeit · Quellen (mit Zitat & Relevanz) ·
  Konfidenz · verwandte Dokumente · Folgefragen.
- **Dokumentenviewer mit echten Dokument-Skins** — Klick auf eine Quelle öffnet das
  Dokument als **Papierblatt**: Briefkopf, Beleg-Stempel (EINGANG/GEPRÜFT/BESTANDEN),
  Vertrags-Unterschriftszeilen — mit hervorgehobenen Belegstellen im Layout und
  Metadaten (Pfad, Autor, Datum, Typ). Das Skin richtet sich automatisch nach `doc.type`.
- **Module** — Wissen, Finanzen, Audit, HR, Verträge, Berichte, Einstellungen.

## Beste Demo-Reihenfolge (8 Szenarien)

1. „Wo finde ich die aktuelle Reiserichtlinie?" — sofortige, präzise Richtlinien-Antwort.
2. „Warum sind die Materialkosten gestiegen?" — verknüpft Bericht ↔ Vertrag ↔ Rechnung.
3. „Zeig mir die Belege zu Rechnung 2026-1843." — Drei-Wege-Abgleich, prüfungssicher.
4. „Fasse Projekt Alpha zusammen." — Projektstatus über mehrere Quellen.
5. „Finde alle Verträge mit automatischer Verlängerung." — Tabelle mit Kündigungsfristen ⚠.
6. „Erstelle eine Zusammenfassung für den Vorstand." — bereichsübergreifendes Briefing.
7. „Wo ist die Brandschutzdokumentation für Werk 2?" — Richtlinie + behördlicher Nachweis.
8. „Wie hat sich unser CO₂-Fußabdruck entwickelt — sind wir auf ESG-Kurs?" — CO₂-Trend-Tabelle
   (2020→2025→Ziel 2030) mit ehrlicher Lücken-Offenlegung; Nachhaltigkeit & Governance.

Das komplette Drehbuch steht in [`../VIDEO_SCRIPT.md`](../VIDEO_SCRIPT.md).

## Dateien

| Datei | Zweck |
|-------|-------|
| `index.html` | App-Rahmen (Seitenleiste, Chat, Composer, Viewer). |
| `styles.css` | Enterprise-Design (Stripe/Linear/Notion-Anmutung). |
| `data.js`    | Demo-Firma, Dokumente & Szenarien — **einzige Quelle der Wahrheit**. |
| `app.js`     | Interaktionslogik (Streaming, Quellen, Viewer). Reines Vanilla-JS. |

**Neues Szenario/Dokument hinzufügen:** nur `data.js` erweitern (`DOCS`, `SCENARIOS`).
Kein Code in `app.js` nötig.

## Verhältnis zum übrigen Repository

Dieser Prototyp ist **additiv**. Er verändert `platform/` (Architektur-Doku) und
`core/` (Agenten-Runtime) **nicht** — beides bleibt geschützt. Der Prototyp ist die
Kundensicht auf die Idee; die Plattform-Doku ist das technische Fundament dahinter.
