# SCENARIO_LIBRARY — Pilot-Szenarienbibliothek

> **Phase C (Pilot-Kit) · erste Deliverable.** Ziel: Nach einem 30-Minuten-Audit-Call mit einer echten
> KMU in **Minuten** die drei passenden Demo-Szenarien auswählen, die den Schmerz *dieses* Kunden treffen.
> Alle 17 bestehenden Szenarien des Prototyps sind hier nach **Schmerz** und **Branche** verschlagwortet.
>
> **Diese Datei ändert den Prototyp nicht** — sie ist reine Übergabe (Feature-Freeze aus Phase B gewahrt).
> Grundlage: `prototype/data.js` (17 Szenarien · 29 Dokumente), deterministisch ausgelesen am 2026-07-09.
> Verwandte Phase-C-Dateien (folgen): `PILOT_CONFIG`, `PILOT_ONE_PAGER.md`, `PILOT_KIT.md`.

---

## So wählst du (3 Schritte, < 5 Minuten)

1. **Schmerz hören.** Im Audit-Call notieren, worüber der CFO/Head of Finance klagt
   („Rechnungen prüfen frisst Zeit", „keiner findet die Verträge", „Monatsabschluss zieht sich").
2. **2–3 Schmerz-Tags matchen.** In der Tabelle unten die Zeilen mit passendem 🔖-Tag markieren.
3. **Genau 3 auswählen** — eine gute Mischung ist **1× Kostentransparenz + 1× Prüfung/Compliance +
   1× Projekt/Reporting**. Der **Money-Shot** (`agent-dazubuchen`) hängt sich als Finale automatisch an,
   er wird **nicht** mitgezählt.

> **Faustregel für die Reihenfolge:** leicht verständlicher Einstieg → belegter „Aha"-Moment →
> Reporting/Portfolio → **Money-Shot**. Deckt sich mit der kuratierten `DEMO_ORDER` der Geführten Demo.

---

## Schmerz-Kategorien (🔖-Tags)

| Tag | Schmerz beim Kunden | O-Ton im Audit-Call |
|-----|---------------------|---------------------|
| **KOSTEN** | Kostenanstieg unerklärt, Zahlen ohne Herkunft | „Warum ist das teurer geworden?" |
| **RECHNUNGSPRÜFUNG** | Belegprüfung/Drei-Wege-Abgleich frisst Zeit | „Wir prüfen Rechnungen noch von Hand." |
| **VERTRÄGE** | Fristen/Verlängerungen/Klauseln unübersichtlich | „Keiner weiß, welcher Vertrag wann ausläuft." |
| **MONATSABSCHLUSS** | Reporting/Vorstandsunterlagen manuell zusammengesucht | „Der Abschluss zieht sich jeden Monat." |
| **PROJEKTE** | Kein Überblick über Stand/Budget/Termin der Vorhaben | „Wo stehen meine Projekte gerade?" |
| **LIQUIDITÄT/RISIKO** | Klumpen-/Lieferantenrisiko, Abhängigkeiten | „Wie abhängig sind wir von dem einen Lieferanten?" |
| **COMPLIANCE** | Audit/DSGVO/Brandschutz — Nachweise verstreut | „Beim Audit suchen wir tagelang Unterlagen." |
| **WISSENSVERLUST** | Wissen steckt in Ordnern/Postfächern/Köpfen | „Das weiß nur die eine Kollegin." |
| **ESG/GOVERNANCE** | ESG-Kennzahlen, Vorstandsbeschlüsse nicht greifbar | „Für den ESG-Report sammeln wir alles neu." |
| **⭐ MONEY-SHOT** | — (Upsell, kein Schmerz) | Finale: „Agenten dazubuchen wie Mitarbeiter." |

---

## Alle 17 Szenarien — verschlagwortet

> `Konf.` = Konfidenz laut `data.js` · `Belege` = Anzahl Quellen der Antwort · `Modul` = Ressort im Prototyp.
> Branchen-Fit: **∀** = branchenübergreifend · sonst die Branchen, für die das Szenario am glaubwürdigsten wirkt.

| # | Frage (Szenario-ID) | Modul | Konf. | Belege | 🔖 Schmerz-Tag | Branchen-Fit |
|--:|---------------------|-------|:----:|:-----:|----------------|--------------|
| 1 | Wo finde ich die aktuelle Reiserichtlinie? (`reiserichtlinie`) | HR | 98 | 1 | WISSENSVERLUST | ∀ |
| 2 | Warum sind die Materialkosten gestiegen? (`materialkosten`) | Finanzen | 94 | 5 | **KOSTEN** | Fertigung · Bau · Handel |
| 3 | Wie kam das Mehrbudget von 0,9 Mio. € zustande? (`budget-herkunft`) | Finanzen | 95 | 3 | KOSTEN · COMPLIANCE | Fertigung · Bau |
| 4 | Zeig mir die Belege zu Rechnung 2026-1843. (`beleg-rechnung`) | Audit | 97 | 3 | **RECHNUNGSPRÜFUNG** | ∀ (bes. Handel · Fertigung) |
| 5 | Wie haben wir die mangelhafte Stahllieferung reklamiert? (`reklamation-stahl`) | Audit | 95 | 3 | RECHNUNGSPRÜFUNG · COMPLIANCE | Fertigung · Bau · Großhandel |
| 6 | Fasse Projekt Alpha zusammen. (`projekt-alpha`) | Berichte | 93 | 3 | **PROJEKTE** | Fertigung · Bau · Anlagenbau |
| 7 | Wie steht Projekt Beta? (`projekt-beta`) | Berichte | 91 | 4 | PROJEKTE | Fertigung · Bau · Logistik |
| 8 | Welche Projekte laufen aktuell? (`projekt-portfolio`) | Berichte | 94 | 3 | PROJEKTE · MONATSABSCHLUSS | Fertigung · Bau · Dienstleistung |
| 9 | Finde alle Verträge mit automatischer Verlängerung. (`vertraege-verlaengerung`) | Verträge | 96 | 3 | **VERTRÄGE** | ∀ |
| 10 | Erstelle eine Zusammenfassung für den Vorstand. (`vorstand-summary`) | Berichte | 91 | 4 | **MONATSABSCHLUSS** | ∀ |
| 11 | Wo ist die Brandschutzdokumentation für Werk 2? (`brandschutz`) | Audit | 95 | 2 | COMPLIANCE · WISSENSVERLUST | Fertigung · Bau · Logistik |
| 12 | Sind wir DSGVO-konform — letztes Datenschutz-Audit? (`datenschutz-audit`) | Audit | 93 | 2 | **COMPLIANCE** | ∀ |
| 13 | Wie hat sich unser CO₂-Fußabdruck entwickelt? (`esg-co2`) | Berichte | 92 | 3 | **ESG/GOVERNANCE** | Fertigung · Handel · Logistik |
| 14 | Was hat der Vorstand zur Wachstumsstrategie beschlossen? (`strategie-ausblick`) | Berichte | 88 | 1 | ESG/GOVERNANCE · WISSENSVERLUST | ∀ |
| 15 | Was muss ein neuer Mitarbeiter am ersten Tag erledigen? (`onboarding-tag1`) | HR | 96 | 2 | WISSENSVERLUST | ∀ |
| 16 | Wie abhängig sind wir vom größten Lieferanten? (`lieferanten-risiko`) | Finanzen | 94 | 3 | **LIQUIDITÄT/RISIKO** | Fertigung · Handel · Großhandel |
| 17 | Kann ich einen weiteren Agenten dazubuchen? (`agent-dazubuchen`) | Berichte | — | 0 | ⭐ **MONEY-SHOT** | ∀ (immer Finale) |

---

## Fertige 3er-Auswahlen nach Branche (Startvorlagen)

> Jede Zeile ist ein **erprobter Startsatz** für einen Pilot. Der Money-Shot (`agent-dazubuchen`) kommt
> immer als Finale dazu — er steht in den Sätzen daher nicht extra. Bei Bedarf einzelne Szenarien tauschen.

| Branche des Pilotkunden | Szenario 1 (Einstieg) | Szenario 2 (Aha) | Szenario 3 (Reporting) |
|-------------------------|-----------------------|------------------|------------------------|
| **Fertigung / Industrie** | `materialkosten` (KOSTEN) | `beleg-rechnung` (RECHNUNGSPRÜFUNG) | `projekt-portfolio` (PROJEKTE) |
| **Bau / Anlagenbau** | `materialkosten` (KOSTEN) | `projekt-beta` (PROJEKTE, Terminrisiko) | `vorstand-summary` (MONATSABSCHLUSS) |
| **Handel / Großhandel** | `beleg-rechnung` (RECHNUNGSPRÜFUNG) | `lieferanten-risiko` (LIQUIDITÄT/RISIKO) | `vorstand-summary` (MONATSABSCHLUSS) |
| **Logistik** | `beleg-rechnung` (RECHNUNGSPRÜFUNG) | `projekt-beta` (PROJEKTE) | `datenschutz-audit` (COMPLIANCE) |
| **Dienstleistung / Kanzlei** | `vertraege-verlaengerung` (VERTRÄGE) | `datenschutz-audit` (COMPLIANCE) | `vorstand-summary` (MONATSABSCHLUSS) |
| **Querschnitt (unsicher)** | `reiserichtlinie` (WISSENSVERLUST) | `beleg-rechnung` (RECHNUNGSPRÜFUNG) | `projekt-portfolio` (PROJEKTE) |

---

## Auswahl-Spickzettel (auf einer Karte)

1. **Schmerz #1 des CFO** → passendes 🔖-Tag → Szenario als **Einstieg**.
2. **Ein belegter Prüf-/Compliance-Moment** (`beleg-rechnung`, `reklamation-stahl`, `datenschutz-audit`)
   → als **Aha** (zeigt Quellen + Konfidenz + Nachvollziehbarkeit).
3. **Ein Reporting-/Portfolio-Moment** (`projekt-portfolio`, `vorstand-summary`) → als **Abschluss vor dem Money-Shot**.
4. **Money-Shot** hängt automatisch an — nichts weiter zu tun.

> **Wichtig für Phase C:** Für den echten Pilot werden Firmenname, Dokumenttypen und Zahlen über `PILOT_CONFIG`
> und die **synthetische Datenpipeline** (`synthetic-data-creator`) auf den Kunden umgebrandet — **kein einziges
> echtes Kundendokument**. Diese Bibliothek liefert nur die **Szenario-Auswahl**; das Umbranden folgt separat.
