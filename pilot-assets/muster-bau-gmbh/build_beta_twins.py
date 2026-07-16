#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut die PROSA-ZWILLINGE der `projekt-beta`-Korpus-Belege fuer "Muster Bau GmbH".

Kontext (Vorab-Kohaerenz-Audit + Struktur-/Prosa-Zwillinge, s. README):
Die 3 Pilot-Szenarien ziehen zusammen 12 Quelldokumente heran. Nach dem
Materialkosten-Zyklus (2026-07-15) waren 6/12 gestaged (Controlling-.xlsx,
Rechnung-CSV, Rahmenvertrag-CSV, Q1-Bericht, 2 E-Mails) und damit das PRIMAERE
Szenario `materialkosten` vollstaendig. Dieses Skript staged die VIER Belege des
ZWEITEN Pilot-Szenarios `projekt-beta` (2 Prosa + 2 Beleg-mit-Positionstabelle):

  * projekt-beta-status        -> projekt-beta-status_zwilling.txt   (Projektbericht)
  * eskalation-beta-elektronik -> eskalation-beta-elektronik_zwilling.txt (E-Mail)
  * nachtrag-nordwind-beta     -> nachtrag-nordwind-beta_zwilling.txt (Nachtragsangebot + Positionen)
  * auftrag-nordwind-beta      -> auftrag-nordwind-beta_zwilling.txt  (Auftragsbestaetigung + Positionen)

Damit ist `projekt-beta` als ZWEITES der 3 Pilot-Szenarien VOLLSTAENDIG als
Zwilling abgedeckt. Korpus-Abdeckung gesamt: 6/12 -> 10/12. Es verbleiben nur die
2 `vorstand-summary`-eigenen Prosa-Belege (Vorstandsprotokoll + ESG-Bericht;
`projekt-alpha-status` wird ebenfalls von vorstand-summary herangezogen).

FREEZE-GRENZE: Dieser Ordner liegt AUSSERHALB prototype/. Das Erzeugen der
Zwillinge (die nicht-gated Pipeline-Haelfte, Schritte 1+2) beruehrt prototype/
NICHT. Erst das Laden in prototype/data.js (Schritt 3) ist bis Gate B->C gesperrt.

PERSONEN-REGEL (Gap 2 des Audits): Die internen Meridian-Personen der Quelldocs
werden durch die synthetischen Namen aus pilot.config.js (COMPANY.people) ersetzt;
externe Gegenparteien bleiben. In diesem Batch:
  * CFO  Dr. Katharina Vogel  -> Petra Hollmann   (config.people.cfo)
  * CEO  Markus Brandt        -> Andreas Moser     (config.people.ceo)
  * Projektleitung Beta  Markus Feldmann -> Tobias Lindner  (KEINE Config-Rolle, s.u.)
Externe Gegenparteien BLEIBEN (kein Meridian-Leak):
  * Nordwind Logistik AG  (Kunde/Gegenpartei)
  * ElektroSys GmbH       (Zulieferer der Steuerungselektronik)

FRICTION (verschaerft, in README dokumentiert): Der `materialkosten`-Batch fand
eine 7. Persona "Projektleitung Alpha" (Sabine Reinhardt -> Sandra Bergmann) ohne
Config-Rolle. Dieser Batch fuegt eine ACHTE hinzu: "Projektleitung Beta" (Markus
Feldmann -> Tobias Lindner). Es gibt also MEHRERE Projektleitungen (Alpha, Beta) —
eine EINZELNE `projectLead`-Rolle in pilot.config.js reicht nicht. Empfehlung fuer
Schritt 3: entweder eine Liste `projectLeads` oder projekt-scoped Eintraege
(`projectLeadAlpha`/`projectLeadBeta`). Nachnamen bewusst kollisionsfrei zu den
Config-Nachnamen (Moser/Hollmann/Baumgartner/Kessler/Reinhardt/Weiss/Bergmann).

ZAHLEN-KONVENTION (bewusst, s. Struktur-/Prosa-Zwillinge-Log): Zahlen werden NICHT
perturbiert — exakt diese Werte stehen in den `projekt-beta`-Szenario-Antwort-
Zitaten in data.js verbatim (Status 48 %, Naehtragswert 400.000 €/476.000 € brutto,
Beauftragung). Die optionale +/-10%-Synthese ist an Schritt 3 gekoppelt (Korpus UND
Szenario-Zitate zusammen umschreiben).

    python build_beta_twins.py     # schreibt die vier *_zwilling.txt + self-check
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Identitaets-Ersetzung: Meridian-intern -> Muster-Bau-synthetisch ------------
# Reihenfolge zaehlt: laengste/spezifischste Muster zuerst (Voll-Name vor Nachname,
# Anrede-Sonderfaelle vor Nachname-Fallback). KEIN Vornamen-Fallback ("Markus"
# waere zweideutig: Markus Feldmann UND Markus Brandt) — nur eindeutige Voll-Namen
# und eindeutige Nachname-Fallbacks.
REPLACEMENTS: list[tuple[str, str]] = [
    # Firmenname + interne E-Mail-Domain
    ("Meridian Industrie GmbH", "Muster Bau GmbH"),
    ("meridian-industrie.example", "muster-bau.example"),
    # CFO: Dr. Katharina Vogel -> Petra Hollmann (kein Doktortitel -> "Frau ...")
    ("Dr. Katharina Vogel", "Petra Hollmann"),
    ("Frau Dr. Vogel", "Frau Hollmann"),
    ("Katharina Vogel", "Petra Hollmann"),
    ("k.vogel@", "p.hollmann@"),
    # CEO: Markus Brandt -> Andreas Moser (config.people.ceo)
    ("Markus Brandt", "Andreas Moser"),
    # Projektleitung Beta: Markus Feldmann -> Tobias Lindner (KEINE Config-Rolle)
    ("Markus Feldmann", "Tobias Lindner"),
    ("Herrn Feldmann", "Herrn Lindner"),
    ("Herr Feldmann", "Herr Lindner"),
    ("m.feldmann@", "t.lindner@"),
    # Nachname-Fallbacks (nur wo eindeutig eine Person gemeint ist):
    ("Feldmann", "Lindner"),
    ("Vogel", "Hollmann"),
]

# Externe Identitaeten, die bewusst BLEIBEN (kein Meridian-Leak):
EXTERNAL_KEEP = (
    "Nordwind Logistik AG",
    "ElektroSys",
)

# Meridian-Marker, die nach der Ersetzung NIRGENDS mehr auftauchen duerfen:
LEAK_MARKERS = (
    "Meridian",
    "meridian-industrie",
    "Katharina Vogel",
    "Markus Brandt",
    "Markus Feldmann",
    "Feldmann",
    "m.feldmann@",
    "k.vogel@",
)


def sub(text: str) -> str:
    """Wendet die Identitaets-Ersetzungen der Reihe nach an."""
    out = text
    for src, dst in REPLACEMENTS:
        out = out.replace(src, dst)
    return out


# --- Quell-Texte (verbatim aus prototype/data.js, VOR Ersetzung) -----------------
# Jeder Zwilling wird aus dem Original-Body (body[].t / from/to/cc/subject/quoted /
# lineItems) von data.js abgeleitet und dann durch sub() identitaets-bereinigt.
# Zahlen bleiben unangetastet (s. ZAHLEN-KONVENTION).

STATUS_SRC = """\
PROJEKTBERICHT — Projekt Beta, Statusbericht
Autor: Projektleitung Beta (Ing. Markus Feldmann) · Datum: 2026-03-31
Ablage: Fileserver > Projekte > Beta > Statusbericht_2026-03.docx

Projekt Beta — kundenspezifische, automatisierte Verpackungs- und Palettierlinie
für die Nordwind Logistik AG (Engineering München, Endmontage Werk 2 Ingolstadt).

Auftragswert / Budget: 8,6 Mio. €. Ziel: schlüsselfertige Übergabe der Anlage
inklusive Werksabnahme (FAT) beim Kunden.

Status per 31.03.2026: 48 % abgeschlossen, rund 3 Wochen in Verzug. Bislang
4,7 Mio. € verausgabt.

Ursachen der Verzögerung: (1) Lieferverzug der Steuerungselektronik — der
Zulieferer ElektroSys hat den Termin um 6 Wochen verschoben. (2) Kunden-
Änderungswunsch: eine zusätzliche Prüfstation (Scope-Change, +0,4 Mio. €).

Terminrisiko: Der ursprüngliche Liefertermin Q3 2026 wurde auf Q4 2026 verschoben
(Werksabnahme November 2026). Bei weiterer Verzögerung greift die vertragliche
Pönale von 0,5 % des Auftragswerts je angefangene Verzugswoche, gedeckelt bei 5 %
(max. 0,43 Mio. €).

Gegenmaßnahmen: Zweitquelle für die Steuerungselektronik qualifiziert; der Change
Request wird kaufmännisch beim Kunden geltend gemacht; wöchentliches Eskalations-
Jour-fixe mit CFO und Vorstand.
"""

ESKALATION_SRC = """\
E-MAIL — Eskalation Projekt Beta — Lieferverzug Elektronik, Pönale-Risiko & Antrag Zweitquelle
Von:      Markus Feldmann · Projektleitung Beta, Meridian Industrie GmbH <m.feldmann@meridian-industrie.example>
An:       Dr. Katharina Vogel · CFO, Meridian Industrie GmbH <k.vogel@meridian-industrie.example>
Cc:       Markus Brandt · CEO, Meridian Industrie GmbH
Gesendet: 24.03.2026, 17:22

Sehr geehrte Frau Dr. Vogel,

Eskalation Projekt Beta — Terminrisiko Kundenanlage Nordwind Logistik.

Lieferverzug der Steuerungselektronik: Der Zulieferer ElektroSys hat den
Liefertermin um sechs Wochen verschoben. Dadurch droht eine Vertragsstrafe
(Pönale) gegenüber der Nordwind Logistik AG.

Auswirkung: Der Liefertermin verschiebt sich von Q3 auf Q4 2026 (Werksabnahme
November). Die Pönale beträgt 0,5 % des Auftragswerts je Verzugswoche, gedeckelt
bei 5 % — bei 8,6 Mio. € Auftragswert also bis zu 0,43 Mio. €.

Antrag: Freigabe einer bereits qualifizierten Zweitquelle für die
Steuerungselektronik, um den Verzug zu begrenzen. Der parallele Kunden-
Änderungswunsch (zusätzliche Prüfstation, +0,4 Mio. €) wird als Change Request
kaufmännisch geltend gemacht.

Ich schlage ein wöchentliches Eskalations-Jour-fixe bis zur Werksabnahme vor und
berichte den Fortschritt direkt an den Vorstand.

Mit freundlichen Grüßen
Markus Feldmann — Projektleitung Beta, Meridian Industrie GmbH

--- Zitierter Verlauf ---
Von: Vertrieb, ElektroSys GmbH, 20.03.2026, 11:05
  Sehr geehrter Herr Feldmann,
  leider müssen wir Ihnen mitteilen, dass sich die Auslieferung der
  Steuerungselektronik (Charge B-4471) aufgrund eines Engpasses bei Halbleiter-
  Bauteilen um rund sechs Wochen verzögert.
  Mit freundlichen Grüßen, Vertrieb ElektroSys GmbH
"""

NACHTRAG_SRC = """\
NACHTRAGSANGEBOT NA-2026-0037 — Zusätzliche Prüfstation
Aussteller: Vertrieb Sondermaschinen (Meridian Industrie GmbH) · Datum: 2026-03-27
Ablage: SAP > SD > Angebote > 2026 > NA_2026-0037_Nordwind.pdf

Nachtragsangebot NA-2026-0037 — Meridian Industrie GmbH an Nordwind Logistik AG.

Bezug: Rahmenauftrag NW-2025-0442 (Projekt Beta — automatisierte Verpackungs- und
Palettierlinie) sowie Ihr Änderungswunsch vom 18.03.2026.

Gegenstand: Integration einer zusätzlichen Prüfstation (Kamera-Inspektion zur
Qualitätskontrolle) in die vereinbarte Linie — ein Scope-Change gegenüber dem
ursprünglichen Auftragsumfang.

Nachtragswert: 400.000 € netto (476.000 € brutto). Der Betrag deckt Hardware/
Sensorik, Engineering und SPS-Integration sowie die erweiterte Werksabnahme (FAT) ab.

Termin: Der Änderungswunsch verschiebt den Liefertermin um rund 3 Wochen auf
Q4 2026; die zusätzliche Prüfstation wird in die laufende Endmontage eingeplant.
Die Pönale-Klausel des Hauptvertrags bleibt vom genehmigten Scope-Change unberührt.

Gültigkeit: Dieses Nachtragsangebot ist bis 15.04.2026 verbindlich. Mit
schriftlicher Beauftragung wird der Nachtragswert Bestandteil des Auftragswerts.

--- Positionen (Nachtragsangebot NA-2026-0037) ---
Bezug: Rahmenauftrag NW-2025-0442 · Änderungswunsch Nordwind Logistik AG vom 18.03.2026
Pos. 1  Zusätzliche Prüfstation — Kamera-Inspektion inkl. Sensorik und Hardware
        Menge: 1 Stk. · Einzelpreis: 250.000,00 € · Summe: 250.000,00 €
Pos. 2  Engineering, SPS-Integration und Anpassung der Anlagensteuerung
        Menge: pauschal · Einzelpreis: 110.000,00 € · Summe: 110.000,00 €
Pos. 3  Erweiterte Werksabnahme (FAT) und Dokumentation
        Menge: pauschal · Einzelpreis: 40.000,00 € · Summe: 40.000,00 €
        Nettosumme:              400.000,00 €
        USt 19 %:                 76.000,00 €
        Angebotssumme brutto:    476.000,00 €
"""

AUFTRAG_SRC = """\
AUFTRAGSBESTÄTIGUNG — Nachtrag NA-2026-0037 beauftragt
Aussteller: Einkauf / Projektleitung (Nordwind Logistik AG) · Datum: 2026-04-03
Ablage: SAP > SD > Aufträge > 2026 > AB_Nordwind_NA-2026-0037.pdf

Auftragsbestätigung / Beauftragung — Nordwind Logistik AG an Meridian Industrie GmbH.

Bezug: Ihr Nachtragsangebot NA-2026-0037 vom 27.03.2026 zum Rahmenauftrag
NW-2025-0442 (Projekt Beta — automatisierte Verpackungs- und Palettierlinie).

Hiermit beauftragen wir den Nachtrag verbindlich: die zusätzliche Prüfstation
(Kamera-Inspektion) wird zum angebotenen Preis von
400.000 € netto (476.000 € brutto) freigegeben.

Unsere Bestellnummer: NW-BEST-2026-0091. Mit dieser Beauftragung wird der
Nachtragswert Bestandteil des Auftragswerts gemäß Ihrem Angebot.

Termin: Die daraus folgende Verschiebung des Liefertermins um rund 3 Wochen auf
Q4 2026 wird ausdrücklich akzeptiert; die Pönale-Klausel des Hauptvertrags bleibt
für den genehmigten Scope-Change ausgesetzt.

Freigabe: Projektleitung und Einkauf Nordwind Logistik AG, 03.04.2026. Die
Rechnungsstellung erfolgt nach erfolgreicher erweiterter Werksabnahme (FAT).

--- Positionen (Beauftragung NW-BEST-2026-0091) ---
Bezug: Nachtragsangebot NA-2026-0037 · Rahmenauftrag NW-2025-0442
Pos. 1  Nachtrag NA-2026-0037 — zusätzliche Prüfstation (Kamera-Inspektion) inkl.
        Engineering, SPS-Integration und erweiterter FAT
        Menge: 1 Pauschale · Einzelpreis: 400.000,00 € · Summe: 400.000,00 €
        Nettosumme:                        400.000,00 €
        USt 19 %:                           76.000,00 €
        Beauftragter Nachtragswert brutto: 476.000,00 €
"""

TWINS: list[tuple[str, str]] = [
    ("projekt-beta-status_zwilling.txt", STATUS_SRC),
    ("eskalation-beta-elektronik_zwilling.txt", ESKALATION_SRC),
    ("nachtrag-nordwind-beta_zwilling.txt", NACHTRAG_SRC),
    ("auftrag-nordwind-beta_zwilling.txt", AUFTRAG_SRC),
]

# Anker-Zahlen/-Kennungen, die nach der Ersetzung verbatim erhalten sein MUESSEN:
NUMBER_ANCHORS: dict[str, tuple[str, ...]] = {
    "projekt-beta-status_zwilling.txt": ("8,6 Mio. €", "48 %", "3 Wochen", "0,43 Mio. €", "Q4 2026"),
    "eskalation-beta-elektronik_zwilling.txt": ("sechs Wochen", "0,43 Mio. €", "0,5 %", "+0,4 Mio. €"),
    "nachtrag-nordwind-beta_zwilling.txt": ("400.000 € netto", "476.000 € brutto", "NA-2026-0037", "76.000,00 €"),
    "auftrag-nordwind-beta_zwilling.txt": ("400.000 € netto", "476.000 € brutto", "NW-BEST-2026-0091", "NA-2026-0037"),
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
            "Tobias Lindner",
            "Petra Hollmann",
            "Andreas Moser",
            "muster-bau.example",
        )
    )
    if not synth_present:
        all_ok = False

    # --- Self-Check global: externe Gegenparteien behalten -----------------------
    ext_kept = all(e in combined for e in EXTERNAL_KEEP)
    if not ext_kept:
        all_ok = False

    print("Geschrieben:")
    for p in written:
        print("  ", p)
    print()
    print(f"Kein Meridian-Leak:             {'OK' if not leaked else 'FEHLER ' + str(leaked)}")
    print(f"Synth. Namen vorhanden:         {'OK' if synth_present else 'FEHLER'}")
    print(f"Externe Gegenparteien behalten: {'OK' if ext_kept else 'FEHLER'}")
    print(f"Anker-Zahlen je Datei erhalten: {'OK' if all_ok or leaked or not synth_present or not ext_kept else 'FEHLER'}")
    print()
    print("GESAMT:", "OK" if all_ok else "FEHLER")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
