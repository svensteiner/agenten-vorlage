---
name: learning-log
description: Dokumentiert geprüfte Fälle, Korrekturen und wiederverwendbare Arbeitsregeln für kontrolliertes Lernen ohne stille Rechts- oder Kontierungsänderungen.
metadata:
  version: "0.1.0"
  safety: reviewed-only
---

# Controlled learning log

Lernen bedeutet hier: wiederkehrende Beobachtungen als Kandidaten dokumentieren, anschließend
durch einen tax-reviewer prüfen lassen und erst danach als `approved` abrufbar machen. Eine
Kandidaten-Notiz verändert weder Steuerrecht noch BMD-Parameter automatisch.

## Kandidatenschema

Jede Notiz enthält: `id`, Erstellungsdatum, anonymisierten Sachverhalt, erkannte Ursache,
Korrektur, betroffene BMD-Version/Module, Quellen mit Standdatum, Gültigkeitsbereich,
Konfidenz, Autor, Reviewer und Status `candidate|approved|rejected|superseded`.

Keine Namen, Steuernummern, IBANs, Zugangsdaten, vollständigen Belege oder unnötige
Mandantendaten speichern. Verweise auf lokale Fallartefakte statt Kopien. Ein Approved-Eintrag
ist nur eine Arbeitshilfe: bei zeitabhängigem Recht die Primärquelle erneut prüfen.

Bei widersprüchlichen Lernnotizen die ältere Regel nicht still überschreiben; beide markieren,
den Konflikt an den tax-reviewer eskalieren und bis zur Entscheidung die sicherere Variante wählen.

