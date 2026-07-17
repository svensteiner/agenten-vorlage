#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut die PROSA-ZWILLINGE der `vorstand-summary`-Korpus-Belege fuer "Muster Bau GmbH".

Kontext (Vorab-Kohaerenz-Audit + Struktur-/Prosa-Zwillinge, s. README):
Die 3 Pilot-Szenarien ziehen zusammen 12 QUELL-DOKUMENTKOERPER heran. Nach dem
Materialkosten-Zyklus (5 Koerper) und dem Projekt-Beta-Zyklus (4 Koerper) waren
9 der 12 Koerper gestaged. (Der Controlling-`.xlsx` ist ein ZAHLEN-OVERLAY
ZUSAETZLICH zu den 12 Koerpern — kein Ersatz eines Koerpers; das fruehere
"10/12" zaehlte ihn versehentlich als 12. Slot mit. Wahr war 9/12 Koerper.)

Dieses Skript staged die DREI verbleibenden Koerper des DRITTEN Pilot-Szenarios
`vorstand-summary` und macht damit `vorstand-summary` — und die Korpus-Abdeckung
insgesamt (12/12 Koerper) — vollstaendig:

  * projekt-alpha-status       -> projekt-alpha-status_zwilling.txt   (Projektbericht)
  * vorstandsprotokoll-2026-03 -> vorstandsprotokoll-2026-03_zwilling.txt (Sitzungsprotokoll)
  * esg-bericht-2025           -> esg-bericht-2025_zwilling.txt       (Nachhaltigkeitsbericht)

Damit sind ALLE 3 Pilot-Szenarien (materialkosten · projekt-beta · vorstand-
summary) als Zwilling vollstaendig. Korpus-Koerper-Abdeckung: 9/12 -> 12/12.

FREEZE-GRENZE: Dieser Ordner liegt AUSSERHALB prototype/. Das Erzeugen der
Zwillinge (die nicht-gated Pipeline-Haelfte, Schritte 1+2) beruehrt prototype/
NICHT. Erst das Laden in prototype/data.js (Schritt 3) ist bis Gate B->C gesperrt.

PERSONEN-REGEL (Gap 2 des Audits): Die internen Meridian-Personen der Quelldocs
werden durch die synthetischen Namen aus pilot.config.js (COMPANY.people) ersetzt;
externe Gegenparteien bleiben. In diesem Batch:
  * CEO  Markus Brandt  -> Andreas Moser  (config.people.ceo)
  * Projektleitung Alpha (Ing. Petra Lang) -> Nadine Falk  (KEINE Config-Rolle, s.u.)
Externe Gegenpartei BLEIBT (kein Meridian-Leak):
  * Ferro Nord  (im Vorstandsprotokoll beschlossener Zweitlieferant)
Rollen-Bezeichner ohne Personennamen bleiben unveraendert:
  * "Nachhaltigkeitsteam" (Autor des ESG-Berichts) — ein Team, keine Person.

FRICTION (verschaerft, in README dokumentiert): Der `materialkosten`-Batch fand
eine Persona "Projektleitung Alpha" (Sabine Reinhardt -> Sandra Bergmann, Cc der
Weiterleitungs-Mail). Die QUELLE nennt fuer DIESELBE Rolle im Alpha-Statusbericht
einen ZWEITEN Namen: "Ing. Petra Lang". Das ist eine Inkonsistenz im Meridian-
Ausgangskorpus (zwei Namen fuer "Projektleitung Alpha"). Faithful behandelt:
beide bleiben als eigenstaendige Personen erhalten und werden auf JE einen
distinkten synthetischen Namen gemappt (Sandra Bergmann bzw. Nadine Falk) — die
Inkonsistenz wird NICHT stillschweigend eingeebnet, sondern fuer Schritt 3
protokolliert. Zusammen mit Projektleitung Beta (Tobias Lindner) bestaetigt das
erneut: eine EINZELNE `projectLead`-Rolle reicht nicht -> Empfehlung Liste
`projectLeads` (bzw. projekt-scoped Eintraege). Nachname "Falk" bewusst
kollisionsfrei zu den Config-Nachnamen (Moser/Hollmann/Baumgartner/Kessler/
Reinhardt/Weiss) sowie zu Bergmann/Lindner; Vorname "Nadine" bewusst kollisions-
frei zu "Petra" (= Config-CFO Petra Hollmann).

ZAHLEN-KONVENTION (bewusst, s. Struktur-/Prosa-Zwillinge-Log): Zahlen werden NICHT
perturbiert — exakt diese Werte stehen in den `vorstand-summary`/`esg-co2`/
`strategie-ausblick`-Szenario-Antwort-Zitaten in data.js verbatim (0,9 Mio. €,
30 % CO2 bis 2030, 41.200 t, 62 %, 24 Mio. €). Die optionale +/-10%-Synthese ist
an Schritt 3 gekoppelt (Korpus UND Szenario-Zitate zusammen umschreiben).

    python build_vorstand_twins.py     # schreibt die drei *_zwilling.txt + self-check
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Identitaets-Ersetzung: Meridian-intern -> Muster-Bau-synthetisch ------------
# Reihenfolge zaehlt: laengste/spezifischste Muster zuerst. KEIN bare "Lang"-
# Fallback (waere als Substring in generischem Deutsch riskant) — nur der
# eindeutige Voll-Name "Petra Lang". "Petra" allein wird NICHT ersetzt (es kommt
# in diesen drei Belegen nur als Vorname von "Petra Lang" vor).
REPLACEMENTS: list[tuple[str, str]] = [
    # Firmenname + interne E-Mail-Domain (Domain defensiv; in diesen Belegen nicht vorhanden)
    ("Meridian Industrie GmbH", "Muster Bau GmbH"),
    ("meridian-industrie.example", "muster-bau.example"),
    # CEO: Markus Brandt -> Andreas Moser (config.people.ceo)
    ("Markus Brandt", "Andreas Moser"),
    # Projektleitung Alpha: Ing. Petra Lang -> Nadine Falk (KEINE Config-Rolle)
    ("Petra Lang", "Nadine Falk"),
]

# Externe Identitaeten, die bewusst BLEIBEN (kein Meridian-Leak):
EXTERNAL_KEEP = (
    "Ferro Nord",
)

# Meridian-Marker, die nach der Ersetzung NIRGENDS mehr auftauchen duerfen:
LEAK_MARKERS = (
    "Meridian",
    "meridian-industrie",
    "Markus Brandt",
    "Petra Lang",
)


def sub(text: str) -> str:
    """Wendet die Identitaets-Ersetzungen der Reihe nach an."""
    out = text
    for src, dst in REPLACEMENTS:
        out = out.replace(src, dst)
    return out


# --- Quell-Texte (verbatim aus prototype/data.js, VOR Ersetzung) -----------------
# Jeder Zwilling wird aus dem Original-Body (body[].t) von data.js abgeleitet; der
# Kopf (Titel/Typ/Autor/Datum/Ablage) wird aus den Metadaten rekonstruiert (wie bei
# den projekt-beta-Zwillingen). Zahlen bleiben unangetastet (s. ZAHLEN-KONVENTION).

ALPHA_SRC = """\
PROJEKTBERICHT — Projekt Alpha, Statusbericht
Autor: Projektleitung Alpha (Ing. Petra Lang) · Datum: 2026-03-31
Ablage: Fileserver > Projekte > Alpha > Statusbericht_2026-03.docx

Projekt Alpha — Aufbau einer neuen automatisierten Fertigungslinie in Werk 2
Ingolstadt.

Ziel: Kapazitätserhöhung um 35 % bei Getriebekomponenten. Gesamtbudget: 24 Mio. €.

Status per 31.03.2026: 62 % abgeschlossen, im Zeitplan. Bislang 14,1 Mio. €
verausgabt.

Risiken: Stahlpreisanstieg belastet das Materialbudget (+0,9 Mio. € erwartet,
siehe Q1-Bericht). Liefertermin Robotik-Zellen um 3 Wochen verschoben.

Meilenstein: Geplante Inbetriebnahme Q4 2026. Abnahmetests ab Oktober.
"""

VORSTANDSPROTOKOLL_SRC = """\
VORSTANDSPROTOKOLL — Sitzungsprotokoll März 2026
Autor: Markus Brandt (CEO) · Datum: 2026-03-28
Ablage: SharePoint > Vorstand > Protokolle > Protokoll_2026-03.pdf

Vorstandssitzung Meridian Industrie GmbH, 28.03.2026.

TOP 1: Materialkosten. Der Vorstand beschließt die Aufnahme von Ferro Nord als
Zweitlieferant zur Reduktion der Stahlpreis-Abhängigkeit.

TOP 2: Projekt Alpha bleibt im Zeitplan; Vorstand genehmigt Mehrbudget von
0,9 Mio. € für Materialpreissteigerung.

TOP 3: ESG-Ziel bekräftigt — 30 % CO₂-Reduktion bis 2030 gegenüber 2020.
"""

ESG_SRC = """\
ESG-BERICHT 2025 — Nachhaltigkeitsbericht
Autor: Nachhaltigkeitsteam · Datum: 2026-02-20
Ablage: SharePoint > Vorstand > ESG > ESG_Bericht_2025.pdf

ESG-Bericht 2025 der Meridian Industrie GmbH nach CSRD/ESRS.

CO₂-Emissionen 2025: 41.200 t (Scope 1+2), -12 % ggü. Basisjahr 2020.
Ziel: -30 % bis 2030.

Scope 1 (eigene Anlagen und Fuhrpark): 12.400 t. Scope 2 (Strombezug): 28.800 t.

Anteil erneuerbarer Energie am Strombezug: 68 % (Vorjahr 61 %). Photovoltaik
Werk 2 seit Q3 2025 aktiv (4,2 GWh/Jahr).

Zielpfad: Ein linearer Reduktionspfad läge 2025 bei rund -15 %; mit -12 % liegen
wir leicht dahinter, holen aber durch PV-Ausbau und Grünstrom auf.

Soziales & Governance: Arbeitsunfallquote -18 %, Frauenanteil in Führung 27 %,
Lieferanten-Kodex von 94 % der A-Lieferanten unterzeichnet.
"""

TWINS: list[tuple[str, str]] = [
    ("projekt-alpha-status_zwilling.txt", ALPHA_SRC),
    ("vorstandsprotokoll-2026-03_zwilling.txt", VORSTANDSPROTOKOLL_SRC),
    ("esg-bericht-2025_zwilling.txt", ESG_SRC),
]

# Anker-Zahlen/-Kennungen, die nach der Ersetzung verbatim erhalten sein MUESSEN:
NUMBER_ANCHORS: dict[str, tuple[str, ...]] = {
    "projekt-alpha-status_zwilling.txt": ("24 Mio. €", "62 %", "14,1 Mio. €", "35 %", "+0,9 Mio. €", "Q4 2026"),
    "vorstandsprotokoll-2026-03_zwilling.txt": ("0,9 Mio. €", "30 %", "2030", "28.03.2026"),
    "esg-bericht-2025_zwilling.txt": ("41.200 t", "-12 %", "-30 %", "68 %", "12.400 t", "28.800 t"),
}


def main() -> int:
    written: list[str] = []
    all_ok = True
    combined = ""

    for name, src in TWINS:
        twin = sub(src)
        path = os.path.join(HERE, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(twin)
        written.append(path)
        combined += "\n" + twin

        # Self-Check pro Datei: Anker-Zahlen erhalten
        anchors = NUMBER_ANCHORS[name]
        missing = [a for a in anchors if a not in twin]
        if missing:
            all_ok = False
            print(f"FEHLER [{name}] fehlende Anker-Zahlen: {missing}")

    # --- Self-Check global: kein Meridian-Leak -----------------------------------
    leaked = [m for m in LEAK_MARKERS if m in combined]
    if leaked:
        all_ok = False

    # --- Self-Check global: synthetische Namen present ---------------------------
    synth_present = all(
        s in combined
        for s in (
            "Muster Bau GmbH",
            "Andreas Moser",
            "Nadine Falk",
        )
    )
    if not synth_present:
        all_ok = False

    # --- Self-Check global: externe Gegenpartei behalten -------------------------
    ext_kept = all(e in combined for e in EXTERNAL_KEEP)
    if not ext_kept:
        all_ok = False

    print("Geschrieben:")
    for p in written:
        print("  ", p)
    print()
    print(f"Kein Meridian-Leak:             {'OK' if not leaked else 'FEHLER ' + str(leaked)}")
    print(f"Synth. Namen vorhanden:         {'OK' if synth_present else 'FEHLER'}")
    print(f"Externe Gegenpartei behalten:   {'OK' if ext_kept else 'FEHLER'}")
    print(f"Anker-Zahlen je Datei erhalten: {'OK' if all_ok or leaked or not synth_present or not ext_kept else 'FEHLER'}")
    print()
    print("GESAMT:", "OK" if all_ok else "FEHLER")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
