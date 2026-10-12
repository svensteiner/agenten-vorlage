---
name: tax-review
description: Führt eine separate read-only Qualitäts- und Freigabeprüfung für österreichische Steuer- und BMD-Arbeitsergebnisse durch.
metadata:
  version: "0.1.0"
---

# Tax review

Prüfe nicht nur Form, sondern die tatsächliche Beleg- und Quellenlage: Sachverhalt, Stichtag,
Rechtsgrundlage, BMD-Daten, Berechnung, Summen, Annahmen, Vollmacht und offene Risiken.

Ein positives Ergebnis braucht konkrete Evidenz. Bei fehlender oder veralteter Rechtsquelle,
ungeklärtem Mandantenfakt, Importabweichung, möglichem Finanzstraf-/Haftungsrisiko oder
unbekannter BMD-Version `blocked` melden. Bei reparierbarem Fehler `needs_revision` mit
präziser Stelle und Rückfrage. Erst danach darf der Koordinator den nächsten Schritt wählen.

Eine Review-Freigabe autorisiert keine externe Übermittlung oder Zahlung, sofern der Auftrag
dies nicht ausdrücklich umfasst.

