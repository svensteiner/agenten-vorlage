# Skills

Skills sind abgeschlossene, wiederverwendbare Aufgaben-Playbooks.

## Konzept

Ein Skill ist kleiner als ein Agent, aber größer als ein Tool:
- Ein **Tool** führt eine einzelne Aktion aus (Datei lesen, API-Call)
- Ein **Skill** beschreibt, wie eine fachliche Teilaufgabe Schritt für Schritt erledigt wird
- Ein **Agent** orchestriert mehrere Skills für eine vollständige Aufgabe

## Struktur

```
skills/
  <skill-name>/
    SKILL.md          ← Beschreibung, Workflow, Output-Spezifikation
    references/       ← Backing-Material (optional)
      workflow.md     ← Detaillierte Schritt-für-Schritt-Anleitung
      best-practices.md
      [weitere Referenzen]
```

## SKILL.md Aufbau

```markdown
---
name: skill-name
description: Einzeiler wann dieser Skill benutzt wird
triggers: ["keyword1", "keyword2"]   # wann wird der Skill automatisch gewählt?
output: "was dieser Skill produziert"
---

# Skill-Name

[Kurzbeschreibung was der Skill macht]

## Wann benutzen

[Trigger-Situationen]

## Workflow

1. Schritt 1
2. Schritt 2
...

## Output-Spezifikation

[Format, Dateiname, Mindestanforderungen]

## Qualitäts-Checkliste

- [ ] Anforderung 1
- [ ] Anforderung 2
```

## Skills im Planner

Der Planner lädt alle SKILL.md Dateien und wählt den passenden Skill
anhand der `triggers`-Keywords aus dem Task-Text aus.

Skills werden in `manifest.json` unter `skills` deklariert:

```json
{
  "skills": ["skill-name-1", "skill-name-2"]
}
```
