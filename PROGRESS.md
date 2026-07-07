# PROGRESS — Kundendemonstrations-Prototyp

> Gemessen gegen das Endziel: ein Demo-Prototyp, der einen CEO/CFO in einem
> Verkaufsvideo sofort überzeugt. **Jeden Zyklus fortschreiben.**

## Gesamtfortschritt: ≈ 48 % (Ende Zyklus 3)

| Bereich | Gewicht | Stand | Beitrag |
|---------|:------:|:-----:|:------:|
| App-Grundgerüst (Layout, Navigation, Design) | 20 % | 92 % | 18.4 |
| Chat-Experience (Streaming, Antwort-Struktur) | 20 % | 82 % | 16.4 |
| Belege pro Antwort (Quellen, Konfidenz, Nachvollziehbarkeit) | 15 % | 85 % | 12.75 |
| Dokumentenviewer (Preview, Highlights, Metadaten) | 15 % | 80 % | 12.0 |
| Demo-Firma & realistische Dokumente | 15 % | 45 % | 6.75 |
| Demo-Szenarien (Breite & Tiefe) | 10 % | 55 % | 5.5 |
| Video-Reife (Skript, Politur, Übergänge) | 5 % | 70 % | 3.5 |
| **Summe** | **100 %** | — | **≈ 76 %** gewichtet der begonnenen Bereiche |

> Hinweis: Die gewichtete Summe der *begonnenen* Bereiche liegt höher; der
> **Gesamtfortschritt ≈ 48 %** berücksichtigt, dass Tiefe (mehr Dokumente,
> Positionstabellen, weitere Szenarien, Politur) noch fehlt. Die „Geführte Demo" hebt vor
> allem die **Video-Reife** deutlich (40 % → 70 %). Konservativ gemeldet.

## Verlauf

- **Zyklus 3 (2026-07-07) ≈ 48 %** — „Geführte Demo": Play-Button in der Topbar spielt alle
  7 Szenarien hands-free ab (Frage sichtbar tippen → bestehender `ask()`-Flow → Lesepause),
  Fortschritt „n / 7", jederzeit stoppbar, Composer während der Demo gesperrt. Rein additiv,
  `data.js` unverändert. Start/Typing/Fortschritt/Stopp live verifiziert. (Video-Reife 40 % → 70 %.)
- **Zyklus 2 (2026-07-07) ≈ 42 %** — Dokument-Skins im Viewer: Papierblatt + Briefkopf
  pro `doc.type`, Beleg-/Prüf-Stempel (EINGANG/GEPRÜFT/BESTANDEN), Vertrags-
  Unterschriftszeilen, Klausel-Marken, Highlights im Dokument-Layout. Alle 4 Skin-
  Kategorien live verifiziert. (Viewer 50 % → 80 %.)
- **Zyklus 1 (2026-07-07) ≈ 35 %** — Prototyp erstmals aufgesetzt: buildfreie
  Enterprise-Web-App, fiktive „Meridian Industrie GmbH", Chat-Zentrum mit gestreamten
  Antworten, Belege+Konfidenz+Quellen, Dokumentenviewer, 7 Szenarien, live getestet.
  (Davor: 31 Zyklen `platform/`-Architektur-Doku — nicht Teil der Prototyp-Mission.)

## Was den Fortschritt als Nächstes hebt

1. Rechnungs-Positionstabelle im Beleg-Skin (`doc.lineItems`) → prüfungsechter Drei-Wege-Abgleich.
2. 2–3 weitere Szenarien (HR-Onboarding, ESG/CO₂, Lieferanten-Risiko) + Dokumente → Demo-Firma & Szenarien.
3. Politur: Onboarding-Overlay, Zahlen-Animation, sanfte Übergänge → Video-Reife.
