---
schema: agent-status/v1
agent_id: bmd-tax-advisor
company: AI_Studioxyz
profile: bmd-tax-advisor
status: ready
last_updated: "2026-09-17"
---

# BMD Tax Advisor — aktueller Status

## Aktueller Auftrag

Österreichische Steuerberatungsfälle im BMD-NTCS-Kontext strukturieren, Primärquellen
recherchieren, Buchungs-/Importvorschläge vorbereiten und Lernkandidaten review-gesteuert
dokumentieren.

## Letzter bestätigter Stand

- Rollen: `tax-advisor`, `bmd-operator`, `tax-reviewer`, `researcher`.
- Review-gesteuertes Lernen mit `workspace/knowledge/candidates/` und `approved/`.
- Kein echter BMD-Adapter und kein Mandantenzugang angeschlossen.
- Validierung:
  `python -m agentkit validate --agent agents\bmd-tax-advisor`
- Demo:
  `python -m agentkit run --agent agents\bmd-tax-advisor --backend demo --task "Kontrollierten BMD-Lernworkflow demonstrieren"`

## Nächste Aktion

Für einen echten Fall zuerst Sachverhalt, Mandant, Stichtag und zulässige Quellen klären.
Danach Vorschlag oder Importvorlage erstellen und durch `tax-reviewer` prüfen lassen.

## Offene Blocker

Der autorisierte BMD-Adapter gemäß `references/bmd-adapter-contract.md` fehlt. Bis dahin
bleiben Buchungen, Stammdatenänderungen, FinanzOnline-Übermittlungen und Zahlungen gesperrt.

## Grenzen

Rechtsstand immer gegen aktuelle offizielle Primärquellen prüfen. Keine selbstständige
Buchung, Übermittlung, Zahlung oder Mandantenkommunikation.

## Einstieg

`STATUS.md` → `AGENTS.md` → `SOUL.md` → `WORKFLOW.md` → `agent.json` → Quellen und relevante Skills.
