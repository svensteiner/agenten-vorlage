---
name: example-skill
description: Erstellt eine strukturierte Analyse zu einem vorgegebenen Thema. Benutze diesen Skill wenn der User eine Analyse, einen Report oder eine Auswertung anfordert.
triggers: ["analyse", "auswertung", "report", "zusammenfassung", "untersuche", "analyze", "review"]
output: "Strukturierter Markdown-Report mit Zusammenfassung, Befunden und Empfehlungen"
---

# Example Skill — Strukturierte Analyse

Dieser Skill ist ein Starter-Template. Kopiere diesen Ordner, benenne ihn um
und passe SKILL.md auf deine fachliche Aufgabe an.

## Wann benutzen

Benutze diesen Skill wenn der Task eine strukturierte Analyse, Auswertung
oder einen Report verlangt — nicht für einfache Lookups oder reine Datenabrufe.

## Workflow

1. **Scope klären.** Bestätige Thema, Zeitraum und gewünschten Output-Typ.
2. **Daten sammeln.** Nutze die verfügbaren Tools (web_search, file, MCP-Connectors).
3. **Analyse durchführen.** Strukturiere die Befunde nach Relevanz.
4. **Report erstellen.** Formatiere als Markdown mit klaren Abschnitten.
5. **Qualitäts-Check.** Prüfe gegen die Checkliste unten.

Detaillierter Ablauf: siehe [references/workflow.md](references/workflow.md)

## Output-Spezifikation

**Dateiname:** `[thema]_analyse_[datum].md`

**Mindest-Struktur:**
- Executive Summary (3–5 Sätze)
- Befunde (gegliedert nach Themenblöcken)
- Empfehlungen (priorisiert)
- Quellen (mit Links)

## Guardrails

- Jede Zahl muss eine Quelle haben. Wenn keine Quelle verfügbar: `[UNBELEGT]` markieren.
- Keine externen Dienste kontaktieren, die nicht in `connectors.yaml` deklariert sind.
- Vor der Ausgabe: Qualitäts-Check durchführen.

## Qualitäts-Checkliste

- [ ] Executive Summary vorhanden
- [ ] Alle Zahlen mit Quelle belegt
- [ ] Empfehlungen priorisiert (Hoch / Mittel / Niedrig)
- [ ] Kein `[UNBELEGT]` in kritischen Abschnitten
- [ ] Quellen-Abschnitt vollständig

## Ressourcen

- [references/workflow.md](references/workflow.md) — Detaillierter Schritt-für-Schritt-Ablauf
- [references/best-practices.md](references/best-practices.md) — Qualitätsstandards und häufige Fehler
