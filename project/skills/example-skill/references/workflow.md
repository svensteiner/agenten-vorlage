# Workflow — Detaillierter Ablauf

## Phase 1: Scope klären (5–10 Min)

Bevor Daten gesammelt werden, muss klar sein was geliefert wird.

**Pflicht-Fragen:**
- Was ist das genaue Thema / die genaue Frage?
- Welcher Zeitraum ist relevant?
- Wer ist die Zielgruppe des Reports?
- Welches Format wird erwartet? (Markdown, DOCX, Slides)

**Stoppregel:** Wenn nach 2 Versuchen die Fragen nicht beantwortbar sind → eskalieren.

## Phase 2: Daten sammeln

**Priorität der Quellen:**
1. Interne Daten aus `project/knowledge/` (höchste Priorität)
2. Deklarierte MCP-Connectors aus `connectors.yaml`
3. Web-Search als letzter Fallback

**Nie:** Daten aus dem Trainings-Wissen ohne Quellenprüfung verwenden.

## Phase 3: Analyse strukturieren

Befunde nach folgendem Schema gliedern:
- **Was ist der Stand?** (Ist-Zustand)
- **Was ist aufgefallen?** (Abweichungen, Trends, Risiken)
- **Was bedeutet das?** (Interpretation)

## Phase 4: Report schreiben

Reihenfolge:
1. Executive Summary zuerst (auch wenn es sich anfühlt, es zuletzt zu schreiben)
2. Befunde gegliedert nach Themenblöcken
3. Empfehlungen mit Priorität
4. Quellen-Abschnitt

## Phase 5: Qualitäts-Check

Vor der Ausgabe die Checkliste aus SKILL.md durchgehen.
Wenn ein Item rot ist → nicht liefern, sondern nachbessern oder eskalieren.
