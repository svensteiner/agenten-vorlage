#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut die STRUKTUR-ZWILLINGE der Pilot-Korpus-Belege fuer "Muster Bau GmbH".

Kontext (Vorab-Kohaerenz-Audit, s. README §"Vorab-Kohaerenz-Audit"):
Die 3 Pilot-Szenarien ziehen zusammen 12 Quelldokumente heran. Bisher war nur
1 von 12 als synthetischer Zwilling gestaged (die Controlling-Mappe .xlsx fuer
den Materialkosten-Beat). Dieses Skript stellt die beiden STRUKTURIERTEN Belege
(tabellarisch, "klickbare" Zahlen -> CFO-relevant) als CSV-Zwillinge bereit:

  * rechnung-2026-1843        -> rechnung-2026-1843_zwilling.csv      (Eingangsrechnung)
  * rahmenvertrag-stahlwerk-donau -> rahmenvertrag-stahlwerk-donau_zwilling.csv (Klausel-Tabelle)

Damit steigt die Korpus-Abdeckung von 1/12 auf 3/12 (die drei tabellarisch/
formelhaltigen Belege). Die uebrigen 9 sind Prosa (E-Mails, Berichte, Protokolle)
= redaktionelle Umschriften und gehoeren in den gated Schritt 3 (Text in data.js).

FREEZE-GRENZE: Dieser Ordner liegt AUSSERHALB prototype/. Das Erzeugen der
Zwillinge (die nicht-gated Pipeline-Haelfte, Schritte 1+2) beruehrt prototype/
NICHT. Erst das Laden in prototype/data.js (Schritt 3) ist bis Gate B->C gesperrt.

PERSONEN-REGEL (Gap 2 des Audits, hier erstmals konkret angewandt & verifiziert):
Die internen Meridian-Personen der Quelldocs werden 1:1 durch die synthetischen
Namen aus pilot.config.js (COMPANY.people) ersetzt; der externe Lieferant
(Stahlwerk Donau AG, dessen Vertriebler Andreas Huber) bleibt — externe
Gegenpartei, keine Meridian-Identitaet. So leakt der Zwilling KEINE Meridian-Namen.

ZAHLEN-KONVENTION (bewusst, s. Friction-Log unten):
Die Rechnungs-Zahlen (80 t x 920 EUR/t = 73.600 netto ...) werden NICHT perturbiert,
weil exakt diese Werte in zwei Szenario-Antwort-Zitaten in data.js verbatim stehen
(materialkosten, rechnungspruefung). Eine ploetzliche Abweichung wuerde eine NEUE
Kohaerenz-Luecke oeffnen. Die optionale +/-10%-Synthese wird daher an Schritt 3
gekoppelt (Korpus UND Szenario-Zitate zusammen umschreiben). Der Zwilling traegt
stattdessen die FORMELKETTE explizit -> ein CFO, der klickt, sieht netto=Menge x EP,
USt=netto x 19%, brutto=netto+USt, alles nachrechenbar.

    python build_corpus_twins.py     # schreibt die zwei *_zwilling.csv + self-check
"""
from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Personen-Ersetzungs-Regel: Meridian-intern -> Muster-Bau-synthetisch --------
# Quelle der synthetischen Namen: pilot.config.js -> company.people
PEOPLE_MAP = {
    "Meridian Industrie GmbH": "Muster Bau GmbH",
    "Thomas Krüger": "Jürgen Kessler",         # Einkauf / procurement
    "Dr. Elena Wagner": "Dr. Stefan Reinhardt",          # Recht / legal
    "Dr. Katharina Vogel": "Petra Hollmann",             # CFO / cfo
}
# Externe Gegenparteien, die bewusst BLEIBEN (kein Meridian-Leak):
EXTERNAL_KEEP = ("Stahlwerk Donau AG", "Andreas Huber")

VAT_RATE = 19  # gesetzliche Konstante -> nicht synthetisieren (Lernpunkt README)


def apply_people(text: str) -> str:
    """Ersetzt jede interne Meridian-Person durch ihren synthetischen Zwilling."""
    out = text
    for meridian, synth in PEOPLE_MAP.items():
        out = out.replace(meridian, synth)
    return out


# --- Zwilling 1: Eingangsrechnung (formelhaltige Positionstabelle) ----------------
def build_invoice_twin() -> tuple[str, list[list[str]]]:
    buyer = apply_people("Meridian Industrie GmbH")  # -> Muster Bau GmbH
    supplier = "Stahlwerk Donau AG"                  # extern, bleibt
    # PO-2026-0512 wurde laut Quell-PO vom Einkaufsleiter freigegeben (data.js) ->
    # traegt die synthetische Einkaufs-Person (procurement) in den Rechnungs-Zwilling.
    procurement = apply_people("Thomas Krüger")      # -> Jürgen Kessler

    # Positionen (Menge/Einzelpreis fix -> kohaerent mit Szenario-Zitaten in data.js)
    positions = [
        # pos, beschreibung, menge_t, einzelpreis_eur
        ("1", "Baustahl S355, Warmband - Materialzeugnis 3.1 (EN 10204)", 80.0, 920.00),
    ]

    rows: list[list[str]] = []
    rows.append(["Rechnung Nr.", "2026-1843"])
    rows.append(["Lieferant", supplier])
    rows.append(["Rechnungsempfänger", buyer])
    rows.append(["Bestellbezug", "PO-2026-0512"])
    rows.append(["Bestellverantwortung Einkauf", procurement])
    rows.append(["Lieferung", "20.03.2026, Werkhof Kempten"])  # Muster-Bau-Standort
    rows.append(["Zahlungsziel", "30 Tage netto, 2 % Skonto bei Zahlung < 14 Tage"])
    rows.append([])
    rows.append(["Pos", "Beschreibung", "Menge (t)", "Einzelpreis (EUR/t)", "Summe netto (EUR)"])

    net = 0.0
    for pos, desc, qty, unit in positions:
        line = qty * unit
        net += line
        rows.append([pos, desc, f"{qty:,.3f}", f"{unit:,.2f}", f"{line:,.2f}"])

    vat = net * VAT_RATE / 100.0
    gross = net + vat
    rows.append([])
    rows.append(["", "", "", "Summe netto (EUR)", f"{net:,.2f}"])
    rows.append(["", "", "", f"USt {VAT_RATE} % (EUR)", f"{vat:,.2f}"])
    rows.append(["", "", "", "Rechnungsbetrag brutto (EUR)", f"{gross:,.2f}"])

    return "rechnung-2026-1843_zwilling.csv", rows, (net, vat, gross)


# --- Zwilling 2: Rahmenvertrag (Klausel-Tabelle, identitaets-bereinigt) -----------
def build_contract_twin() -> tuple[str, list[list[str]]]:
    party_a = apply_people("Meridian Industrie GmbH")  # -> Muster Bau GmbH
    party_b = "Stahlwerk Donau AG"                     # extern, bleibt
    legal = apply_people("Dr. Elena Wagner")           # -> Dr. Stefan Reinhardt

    rows: list[list[str]] = []
    rows.append(["Rahmenvertrag Nr.", "RV-2023-014"])
    rows.append(["Partei A (Besteller)", party_a])
    rows.append(["Partei B (Lieferant)", party_b])
    rows.append(["Vertragsverantwortung Recht", legal])
    rows.append(["Gegenstand", "Liefervertrag Baustahl S355"])
    rows.append([])
    rows.append(["Paragraph", "Titel", "Kerninhalt"])
    rows.append([
        "§9", "Laufzeit",
        "Laufzeit bis 31.05.2026; automatische Verlängerung um je 12 Monate, "
        "sofern nicht 3 Monate vor Ablauf schriftlich gekündigt.",
    ])
    rows.append([
        "§6", "Preisgleitklausel",
        "Preisanpassung zulässig bei Rohstoff-/Energiekostensteigerung > 10 %.",
    ])
    rows.append([
        "§12", "Gewährleistung",
        "Werkstoff-/Maßtoleranzen EN 10029; Mängelrüge unverzüglich nach "
        "Wareneingangsprüfung (§377 HGB); Nachlieferung oder Gutschrift.",
    ])
    rows.append([])
    rows.append(["Nächste Kündigungsfrist", "28.02.2026"])
    rows.append(["Bei Nichtkündigung", "Verlängerung bis 31.05.2027"])
    return "rahmenvertrag-stahlwerk-donau_zwilling.csv", rows, None


def write_csv(name: str, rows: list[list[str]]) -> str:
    path = os.path.join(HERE, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        for r in rows:
            writer.writerow(r)
    return path


def main() -> int:
    inv_name, inv_rows, inv_totals = build_invoice_twin()
    con_name, con_rows, _ = build_contract_twin()

    inv_path = write_csv(inv_name, inv_rows)
    con_path = write_csv(con_name, con_rows)

    # --- Self-Check 1: Formelkette der Rechnung -----------------------------------
    net, vat, gross = inv_totals
    exp_net, exp_vat, exp_gross = 73600.00, 13984.00, 87584.00
    ok_chain = (
        abs(net - exp_net) < 0.005
        and abs(vat - exp_vat) < 0.005
        and abs(gross - exp_gross) < 0.005
        and abs(gross - net * 1.19) < 0.005
    )

    # --- Self-Check 2: kein Meridian-Leak in beiden Zwillingen --------------------
    blob = "\n".join(
        ";".join(c for c in row) for row in (inv_rows + con_rows)
    )
    leaked = [m for m in PEOPLE_MAP if m != "Meridian Industrie GmbH" and m in blob]
    leaked_company = "Meridian" in blob
    synth_present = all(
        s in blob for s in ("Muster Bau GmbH", "Jürgen Kessler", "Dr. Stefan Reinhardt")
    )
    ext_kept = all(e in blob for e in EXTERNAL_KEEP if e != "Andreas Huber")

    print("Geschrieben:")
    print("  ", inv_path)
    print("  ", con_path)
    print()
    print(f"Rechnung Formelkette: netto {net:,.2f} -> USt {vat:,.2f} -> brutto {gross:,.2f}")
    print(f"  brutto = netto x 1,19 ? {'JA' if abs(gross-net*1.19)<0.005 else 'NEIN'}")
    print(f"  Formelkette exakt (73.600 / 13.984 / 87.584): {'OK' if ok_chain else 'FEHLER'}")
    print(f"Kein Meridian-Personen-Leak: {'OK' if not leaked else 'FEHLER ' + str(leaked)}")
    print(f"Kein 'Meridian'-Firmenleak:  {'OK' if not leaked_company else 'FEHLER'}")
    print(f"Synth. Namen vorhanden:      {'OK' if synth_present else 'FEHLER'}")
    print(f"Externe Gegenpartei behalten: {'OK' if ext_kept else 'FEHLER'}")

    all_ok = ok_chain and not leaked and not leaked_company and synth_present and ext_kept
    print()
    print("GESAMT:", "OK" if all_ok else "FEHLER")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
