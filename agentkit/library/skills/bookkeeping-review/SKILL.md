---
name: bookkeeping-review
description: Prüft österreichische Buchungs- und Belegvorschläge auf Zeitraum, Kontierung, Steuerkennzeichen, Summen, Belegkette und Abstimmungsbedarf.
metadata:
  version: "0.1.0"
---

# Bookkeeping review

Prüfe jede Zeile gegen Beleg, Mandant, Buchungsperiode, Konto/Gegenkonto, Betrag, Währung,
Umsatzsteuerkennzeichen, Vorsteuerabzug, Kostenstelle, Zahlungsstatus und Beleglink. Gleiche
Debitoren/Kreditoren, Bank, Kassa, USt-Konten und offene Posten mit den gelieferten Summen ab.

Markiere fehlende Pflichtfelder, ungewöhnliche Kontierungen, Periodenabgrenzungen, private oder
gemischte Aufwendungen, Reverse-Charge-/Auslandsfälle und Differenzen. Keine Kontierung aus einem
ähnlichen Fall blind übernehmen. Ein plausibler Buchungssatz ist kein Nachweis der steuerlichen
Zulässigkeit; verweise bei Rechtsfragen auf `austrian-tax-research`.

Ausgabe: geprüfte Vorschlagsdatei oder Checkliste, Differenzliste, Quellen/Annahmen und konkrete
Rückfragen. Keine echte Verbuchung ohne gesonderte Freigabe.

