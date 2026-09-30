---
name: bmd-workflow
description: Bereitet BMD-NTCS-Arbeitsschritte, Buchungsimporte, Auswertungen und Checklisten sicher vor und verlangt Preview sowie Freigabe vor Seiteneffekten.
metadata:
  version: "0.1.0"
  product: BMD NTCS
---

# BMD workflow

BMD NTCS ist der Zielkontext, aber diese Skill-Datei ist keine vollständige Herstellerdokumentation.
Verwende nur die in der Umgebung freigegebenen BMD-Adapter, Exportformate und Handbücher. Erfinde
keine Menüpunkte, Konten, Parameter oder API-Endpunkte.

## Sicherer Ablauf

1. Mandant, BMD-Version, Modul, Wirtschaftsjahr, Datenquelle und Berechtigung feststellen.
2. Mit einer Kopie oder Vorschau arbeiten. Importdateien gegen das lokale BMD-Schnittstellenhandbuch
   und das erwartete Format validieren.
3. Anzahl Zeilen, Debet/Kredit-Summen, Steuerwerte, Perioden, Belegreferenzen und Duplikate prüfen.
4. Einen strukturierten Bericht oder Importentwurf ablegen und dem tax-reviewer vorlegen.
5. Verbuchung, Stammdatenänderung, Fristenaktion, Signatur oder Übermittlung erst nach expliziter
   Autorisierung und erfolgreichem Review ausführen. Ergebnis danach erneut aus BMD auslesen.

Wenn der Adapter fehlt, bleibt der Schritt `blocked` oder liefert nur einen Bedienplan. BMDs eigene
Lern-/Automatisierungsfunktionen dürfen nicht als steuerliche Freigabe interpretiert werden.

