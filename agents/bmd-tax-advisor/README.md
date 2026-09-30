# BMD Tax Advisor für AI_Studioxyz

Dieser Agent ist die erste fachliche Ausarbeitung für einen österreichischen
Steuerberatungsmitarbeiter mit BMD-NTCS-Zielkontext. Er kann Fälle strukturieren, Quellen
recherchieren, Buchungs- und Importvorschläge vorbereiten, Prüfberichte erzeugen und
Korrekturen kontrolliert als Lernkandidaten dokumentieren.

Der Ordner enthält noch keinen echten BMD-Zugang und keinen proprietären BMD-Adapter. Ohne
einen ausdrücklich konfigurierten Adapter bleibt ein BMD-Schritt bei Preview, validierter
Importvorlage oder Bedienplan. Der Agent führt keine Buchung, Stammdatenänderung,
FinanzOnline-Übermittlung, Zahlung oder Mandantenkommunikation selbstständig aus.

## Rollen und Skills

- `tax-advisor`: Sachverhalt, österreichische Primärquellen, Beleg- und Buchungsvorschlag
- `bmd-operator`: BMD-Preview, Import-/Exportvertrag und technische Plausibilisierung
- `tax-reviewer`: unabhängiges Review mit Vier-Augen-Gate
- `researcher`: Quellen und lokale Unterlagen mit Standdatum untersuchen
- `austrian-tax-research`, `bookkeeping-review`, `bmd-workflow`, `learning-log` und
  `tax-review`: fachliche Regeln, die im Agentenpaket portabel kopiert sind

„Lernen“ ist absichtlich review-gesteuert. Neue Fälle landen als redigierte Kandidaten unter
`workspace/knowledge/candidates/`; erst ein zuständiger Reviewer darf eine Notiz nach
`workspace/knowledge/approved/` übernehmen. Diese Notizen sind Arbeitshilfen und müssen bei
zeitabhängigem Recht gegen die aktuelle Primärquelle geprüft werden.

## Lokale Prüfung

Aus dem Vorlagenordner:

```powershell
python -m agentkit validate --agent agents\bmd-tax-advisor
python -m agentkit inspect --agent agents\bmd-tax-advisor
python -m agentkit run --agent agents\bmd-tax-advisor --backend demo --task "Kontrollierten BMD-Lernworkflow demonstrieren"
```

Die Demo schreibt nur `workspace/demo-result.md` und demonstriert Rollenrouting,
Nacharbeit und Review. Sie ist kein BMD-End-to-End-Test. Für einen echten Lauf muss ein
autorisierter Adapter die Schnittstelle in [references/bmd-adapter-contract.md](references/bmd-adapter-contract.md)
implementieren und die Daten in einem isolierten Arbeitsbereich bereitstellen.

## Quellen und Anpassung

Die vorgesehenen offiziellen Einstiegspunkte stehen in
[references/official-sources.md](references/official-sources.md). Produktdokumentation
beschreibt den BMD-Arbeitsablauf, ist aber keine österreichische Rechtsgrundlage. Ergänze
mandats- und bürospezifische Regeln nur als redigierte, reviewte Skills oder Wissensnotizen;
ändere `SOUL.md`, `WORKFLOW.md` und `agent.json` sichtbar und versioniert.
