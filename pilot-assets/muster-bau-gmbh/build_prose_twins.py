#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut die PROSA-ZWILLINGE der Pilot-Korpus-Belege fuer "Muster Bau GmbH".

Kontext (Vorab-Kohaerenz-Audit + Struktur-Zwillinge, s. README):
Die 3 Pilot-Szenarien ziehen zusammen 12 Quelldokumente heran. Nach dem
Struktur-Zwillinge-Zyklus (2026-07-14) waren 3/12 gestaged (die tabellarischen
Belege: Controlling-.xlsx, Rechnung-CSV, Rahmenvertrag-CSV). Dieses Skript staged
die drei PROSA-Belege des Materialkosten-Szenarios (Text: 1 Bericht + 2 E-Mails):

  * q1-bericht-2026                  -> q1-bericht-2026_zwilling.txt
  * email-preisanpassung-donau       -> email-preisanpassung-donau_zwilling.txt
  * email-weiterleitung-materialbudget -> email-weiterleitung-materialbudget_zwilling.txt

Damit ist das PRIMAERE Pilot-Szenario `materialkosten` VOLLSTAENDIG als Zwilling
abgedeckt (5/5: q1-bericht + 2 E-Mails [hier] + Rechnung + Rahmenvertrag [CSV,
Vorzyklus]). Korpus-Abdeckung gesamt: 3/12 -> 6/12.

FREEZE-GRENZE: Dieser Ordner liegt AUSSERHALB prototype/. Das Erzeugen der
Zwillinge (die nicht-gated Pipeline-Haelfte, Schritte 1+2) beruehrt prototype/
NICHT. Erst das Laden in prototype/data.js (Schritt 3) ist bis Gate B->C gesperrt.

PERSONEN-REGEL (Gap 2 des Audits): Die internen Meridian-Personen der Quelldocs
werden durch die synthetischen Namen aus pilot.config.js (COMPANY.people) ersetzt;
externe Gegenparteien (Stahlwerk Donau AG / Andreas Huber; Zweitlieferant Ferro
Nord) bleiben. Zusaetzlich: interne E-Mail-DOMAIN wird ersetzt (meridian-industrie
.example -> muster-bau.example), sonst leakt die Absenderzeile.

NEUE FRICTION (in README dokumentiert): Der Quell-Korpus enthaelt eine 7. interne
Persona — "Sabine Reinhardt (Projektleitung Alpha)" —, fuer die pilot.config.js
(6 Rollen: ceo/cfo/hr/procurement/legal/audit) KEINE Rolle hat. Sie wird hier auf
einen synthetischen Projektleitungs-Namen gemappt (Nachname bewusst != Reinhardt,
um Kollision mit legal "Dr. Stefan Reinhardt" zu vermeiden). Schritt 3 sollte
pilot.config.js um eine `projectLead`-Rolle erweitern.

ZAHLEN-KONVENTION (bewusst, s. Struktur-Zwillinge-Log): Zahlen werden NICHT
perturbiert — exakt diese Werte stehen in Szenario-Antwort-Zitaten in data.js
verbatim. Die optionale +/-10%-Synthese ist an Schritt 3 gekoppelt (Korpus UND
Szenario-Zitate zusammen umschreiben).

    python build_prose_twins.py     # schreibt die drei *_zwilling.txt + self-check
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Identitaets-Ersetzung: Meridian-intern -> Muster-Bau-synthetisch ------------
# Reihenfolge zaehlt: laengste/spezifischste Muster zuerst (Voll-Name vor Nachname,
# Anrede-Sonderfaelle vor Nachname-Fallback).
# Quelle der synthetischen Namen: pilot.config.js -> company.people (+ 1 synth.
# Projektleitung, s. NEUE FRICTION oben).
REPLACEMENTS: list[tuple[str, str]] = [
    # Firmenname + interne E-Mail-Domain
    ("Meridian Industrie GmbH", "Muster Bau GmbH"),
    ("meridian-industrie.example", "muster-bau.example"),
    # CFO: Dr. Katharina Vogel -> Petra Hollmann (kein Doktortitel -> "Frau ..." )
    ("Dr. Katharina Vogel", "Petra Hollmann"),
    ("Frau Dr. Vogel", "Frau Hollmann"),
    ("Katharina Vogel", "Petra Hollmann"),
    ("k.vogel@", "p.hollmann@"),
    # Einkauf: Thomas Krueger -> Juergen Kessler
    ("Thomas Krüger", "Jürgen Kessler"),
    ("Herrn Krüger", "Herrn Kessler"),
    ("Herr Krüger", "Herr Kessler"),
    ("t.krueger@", "j.kessler@"),
    # 7. Persona ohne Config-Rolle: Sabine Reinhardt (Projektleitung Alpha)
    # -> synth. Name; Nachname != Reinhardt (Kollision mit legal Dr. Stefan Reinhardt)
    ("Sabine Reinhardt", "Sandra Bergmann"),
    # Nachname-Fallbacks (nur wo eindeutig eine Person gemeint ist; NICHT "Reinhardt"
    # wegen Kollision — "Sabine Reinhardt" ist oben bereits vollstaendig ersetzt).
    ("Krüger", "Kessler"),
    ("Vogel", "Hollmann"),
]

# Externe Identitaeten, die bewusst BLEIBEN (kein Meridian-Leak):
EXTERNAL_KEEP = (
    "Stahlwerk Donau AG",
    "Andreas Huber",
    "a.huber@stahlwerk-donau.example",
    "Ferro Nord",
)

# Meridian-Marker, die nach der Ersetzung NIRGENDS mehr auftauchen duerfen:
LEAK_MARKERS = (
    "Meridian",
    "meridian-industrie",
    "Katharina Vogel",
    "Thomas Krüger",
    "Sabine Reinhardt",
    "t.krueger@",
    "k.vogel@",
)


def sub(text: str) -> str:
    """Wendet die Identitaets-Ersetzungen der Reihe nach an."""
    out = text
    for src, dst in REPLACEMENTS:
        out = out.replace(src, dst)
    return out


# --- Quell-Texte (verbatim aus prototype/data.js, VOR Ersetzung) -----------------
# Jeder Zwilling wird aus dem Original-Body von data.js abgeleitet und dann durch
# sub() identitaets-bereinigt. Zahlen bleiben unangetastet (s. ZAHLEN-KONVENTION).

Q1_SRC = """\
QUARTALSBERICHT Q1 2026 — Meridian Industrie GmbH, Bereich Controlling
Autor: Dr. Katharina Vogel (CFO) · Datum: 2026-04-10
Ablage: Fileserver > Controlling > 2026 > Quartalsbericht_Q1_2026.xlsx

Die Materialkosten stiegen im Q1 2026 um 18,4 % gegenüber Q1 2025
(von 41,2 Mio. € auf 48,8 Mio. €).

Haupttreiber ist der Stahleinkauf: Der Tonnenpreis für Baustahl S355 stieg
von 780 € auf 920 € (+17,9 %), bedingt durch Energiekosten und Lieferengpässe.

Der Lieferant Stahlwerk Donau AG hat zum 01.03.2026 eine Preisanpassung von
15 % durchgesetzt (Rahmenvertrag RV-2023-014, Preisgleitklausel §6).

Gegenmaßnahme: Der Einkauf verhandelt einen Zweitlieferanten (Ferro Nord) zur
Reduktion der Abhängigkeit. Erwartete Entlastung ab Q3 2026.

Rohertragsmarge sank folglich von 34,1 % auf 31,6 %. Umsatz stabil bei 158 Mio. €.
"""

MAIL1_SRC = """\
E-MAIL — Preisanpassung Baustahl S355 zum 01.03.2026 — Rahmenvertrag RV-2023-014
Von:      Andreas Huber · Stahlwerk Donau AG <a.huber@stahlwerk-donau.example>
An:       Thomas Krüger · Einkauf, Meridian Industrie GmbH <t.krueger@meridian-industrie.example>
Cc:       Dr. Katharina Vogel (CFO) · Meridian Industrie GmbH
Gesendet: 12.02.2026, 09:14
Anhang:   Preisliste_2026_Stahlwerk-Donau.pdf (148 KB)

Sehr geehrter Herr Krüger,

aufgrund der anhaltend hohen Energie- und Rohstoffkosten passen wir gemäß der
Preisgleitklausel (§6 des Rahmenvertrags RV-2023-014) den Tonnenpreis für
Baustahl S355 zum 01.03.2026 um 15 % an.

Der neue Tonnenpreis beträgt damit 920 € (bisher 800 €). Die vollständige
angepasste Preisliste finden Sie im Anhang.

Grundlage ist der Anstieg unserer Energiekosten um mehr als 10 % im zweiten
Halbjahr 2025. Bereits bestätigte Bestellungen bleiben von der Anpassung unberührt.

Für Rückfragen stehe ich Ihnen gern zur Verfügung.

Mit freundlichen Grüßen
Andreas Huber — Vertrieb Großkunden, Stahlwerk Donau AG

--- Zitierter Verlauf ---
Von: Thomas Krüger (Einkauf, Meridian Industrie GmbH), 10.02.2026, 16:40
  Sehr geehrter Herr Huber,
  wir haben Ihre Vorankündigung einer möglichen Preisanpassung erhalten. Bitte
  teilen Sie uns die konkrete Höhe und den Wirkungszeitpunkt schriftlich mit,
  damit wir die Auswirkung auf Projekt Alpha und das Materialbudget bewerten können.
  Mit freundlichen Grüßen, Thomas Krüger
"""

MAIL2_SRC = """\
E-MAIL — WG: Preisanpassung Baustahl S355 — Auswirkung auf Projekt Alpha (+0,9 Mio. €)
Von:      Thomas Krüger · Einkauf, Meridian Industrie GmbH <t.krueger@meridian-industrie.example>
An:       Dr. Katharina Vogel · CFO, Meridian Industrie GmbH <k.vogel@meridian-industrie.example>
Cc:       Sabine Reinhardt · Projektleitung Alpha, Meridian Industrie GmbH
Gesendet: 13.02.2026, 08:05
Anhang:   Preisliste_2026_Stahlwerk-Donau.pdf (148 KB)

Sehr geehrte Frau Dr. Vogel,

wie besprochen leite ich Ihnen die schriftliche Preisanpassung von Stahlwerk
Donau weiter (siehe unten). Die 15-%-Anhebung ist über die Preisgleitklausel §6
vertraglich gedeckt — ein Widerspruch ist nicht durchsetzbar.

Auswirkung auf das Materialbudget: Bei einem geplanten Jahresbedarf von rund
640 t Baustahl S355 für Projekt Alpha steigt der Einkaufswert um 120 €/t — das
entspricht einem Mehrbedarf von rund 0,9 Mio. € für 2026.

Empfehlung: Aufnahme in die nächste Vorstandssitzung als Beschlussvorlage
(Mehrbudget 0,9 Mio. €) sowie Beschleunigung der Qualifizierung des
Zweitlieferanten Ferro Nord, um die Single-Source-Abhängigkeit ab Q3 2026 zu
reduzieren.

Für die Sitzungsvorlage stelle ich Ihnen gern die Mengengerüste und die Rechnung
2026-1843 als Referenz bereit.

Mit freundlichen Grüßen
Thomas Krüger — Einkaufsleiter, Meridian Industrie GmbH

--- Zitierter Verlauf ---
Von: Andreas Huber (Vertrieb, Stahlwerk Donau AG), 12.02.2026, 09:14
  Sehr geehrter Herr Krüger,
  aufgrund der anhaltend hohen Energie- und Rohstoffkosten passen wir gemäß der
  Preisgleitklausel (§6 des Rahmenvertrags RV-2023-014) den Tonnenpreis für
  Baustahl S355 zum 01.03.2026 um 15 % an. Der neue Tonnenpreis beträgt 920 €
  (bisher 800 €).
  Mit freundlichen Grüßen, Andreas Huber — Stahlwerk Donau AG
"""

TWINS: list[tuple[str, str]] = [
    ("q1-bericht-2026_zwilling.txt", Q1_SRC),
    ("email-preisanpassung-donau_zwilling.txt", MAIL1_SRC),
    ("email-weiterleitung-materialbudget_zwilling.txt", MAIL2_SRC),
]

# Anker-Zahlen, die nach der Ersetzung verbatim erhalten sein MUESSEN (pro Datei):
NUMBER_ANCHORS: dict[str, tuple[str, ...]] = {
    "q1-bericht-2026_zwilling.txt": ("18,4 %", "48,8 Mio. €", "920 €", "RV-2023-014"),
    "email-preisanpassung-donau_zwilling.txt": ("920 €", "15 %", "§6"),
    "email-weiterleitung-materialbudget_zwilling.txt": ("0,9 Mio. €", "640 t", "920"),
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
            "Jürgen Kessler",
            "Petra Hollmann",
            "Sandra Bergmann",
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
    print(f"Kein Meridian-Leak:            {'OK' if not leaked else 'FEHLER ' + str(leaked)}")
    print(f"Synth. Namen vorhanden:        {'OK' if synth_present else 'FEHLER'}")
    print(f"Externe Gegenparteien behalten: {'OK' if ext_kept else 'FEHLER'}")
    print(f"Anker-Zahlen je Datei erhalten: {'OK' if all_ok or leaked or not synth_present or not ext_kept else 'FEHLER'}")
    print()
    print("GESAMT:", "OK" if all_ok else "FEHLER")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
