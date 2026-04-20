# 🤖 Agent Vorlage

**Wiederverwendbares Template für autonome KI-Agenten.**

Jeder Agent den wir für Kunden bauen, basiert auf dieser Vorlage.
Einmal verstehen — überall einsetzen.

---

## Was ist ein Agent?

Ein Agent ist ein KI-System das **autonom** Aufgaben erledigt:

```
Observe → Think → Act → Reflect → (wiederholen)
```

Kein manuelles Eingreifen. Kein Copy-Paste von ChatGPT.
Der Agent läuft, lernt, verbessert sich.

---

## Struktur

```
agent-vorlage/
├── SOUL.md              ← Wer ist der Agent? Was weiß er?
├── agent.py             ← Haupt-Loop (Observe→Think→[Challenge]→Act→Reflect)
├── brain.py             ← LLM-Intelligenz (think/act/reflect/evaluate/challenge)
├── memory.py            ← Persistenter Speicher (JSON)
├── governance.py        ← Action-Cooldowns + Tageslimits
├── tools/
│   ├── base_tool.py     ← Basisklasse (alle Tools erben davon)
│   ├── notify.py        ← Telegram + Slack Benachrichtigungen
│   ├── file_tool.py     ← Lesen/Schreiben von Dateien
│   ├── web_search.py    ← Web-Suche (Beispiel)
│   └── message_bus.py   ← Agent-zu-Agent Kommunikation
├── config.json          ← Einstellungen (Modell, Schwellenwerte)
├── .env                 ← API Keys (nicht ins Git!)
├── .env.example         ← Vorlage für .env
├── tasks.json           ← Runtime: Task-Queue (nicht ins Git!)
├── tasks.json.example   ← Schema-Vorlage für tasks.json
├── state/               ← Auto-erstellt: Memory + Governance
└── logs/                ← Auto-erstellt: Log-Dateien
```

### Die 3 Schichten

```
┌──────────────────────────────────────┐
│  SOUL.md                             │  ← Was der Agent weiß und wie er denkt
│  (Identität + Domain-Wissen)         │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  brain.py                            │  ← LLM-Intelligenz
│  think() → act() → reflect()         │     OpenAI / Anthropic
│  evaluate()                          │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│  agent.py + tools/                   │  ← Ausführung + Fähigkeiten
│  Observe → Think → Act → Reflect     │
│  Memory, Loop, Logging               │
└──────────────────────────────────────┘
```

---

## Schnellstart (5 Minuten)

### 1. Setup

```bash
# Repo klonen
git clone https://github.com/[user]/agent-vorlage
cd agent-vorlage

# Dependencies installieren
pip install -r requirements.txt

# .env anlegen
cp .env.example .env
# → OPENAI_API_KEY eintragen
```

### 2. SOUL.md anpassen

Öffne `SOUL.md` und fülle aus:
- Wer ist der Agent? (Rolle, Unternehmen)
- Was weiß er? (Domain-Wissen)
- Was darf er alleine? (Autonome Entscheidungen)
- Was ist "gut genug"? (Qualitätsstandards)

### 3. Starten

```bash
python agent.py --task "Mache XYZ"    # Einmaliger Task
python agent.py --loop                 # Dauerbetrieb
python agent.py --dry-run             # Vorschau
python agent.py --status              # Memory anzeigen
```

Oder auf Windows:
```
START.bat           ← Einmaliger Lauf
DAUERLAUF.bat       ← Kontinuierlich
```

---

## Eigene Tools hinzufügen

```python
# tools/mein_tool.py
from tools.base_tool import BaseTool

class MeinTool(BaseTool):
    name = "mein_tool"
    description = "Macht XYZ — wird vom Brain automatisch ausgewählt"

    def run(self, input: str) -> str:
        # Eigene Logik
        return "Ergebnis"
```

Fertig. Der Agent lädt alle Tools aus `tools/` **automatisch** — keine manuelle Registrierung nötig.

---

## Brain-Funktionen

```python
import brain

# Aufgabe verstehen + planen
plan = brain.think("Erstelle einen LinkedIn Post über KI-Trends")
# → {"plan": [...], "tool": "linkedin_poster", "tool_input": "..."}

# Ergebnis bewerten
result = brain.act(plan, tool_result="Post erstellt")
# → {"success": True, "next_action": "done"}

# Aus Ergebnis lernen
learning = brain.reflect("Post erstellt", "500 Impressionen", "1000 Impressionen erwartet")
# → {"insight": "Posts morgens performen besser"}

# Qualität prüfen
score = brain.evaluate("Post-Text hier...", content_type="linkedin_post")
# → {"score": 8, "passes": True, "feedback": [...]}
```

---

## Memory-Nutzung

```python
from memory import Memory
mem = Memory()

# Aktion speichern
mem.save("actions", {"type": "post", "platform": "linkedin", "success": True})

# Heute schon gemacht?
if mem.done_today("actions", type="post", platform="linkedin"):
    print("Heute schon gepostet — überspringe")

# Letzten 10 Learnings laden
learnings = mem.load("learnings", limit=10)

# Metriken loggen
mem.log_metric("engagement_rate", 4.2, unit="%")
avg = mem.avg_metric("engagement_rate", days=7)
```

---

## Für Kunden deployen

### Was der Kunde bekommt

1. **Angepasste SOUL.md** — Domänen-Wissen des Kunden
2. **Konfiguriertes agent.py** — Aufgaben die der Agent erledigt
3. **Custom Tools** — API-Verbindungen zum Kunden-System
4. **Windows-freundlich** — START.bat, DAUERLAUF.bat
5. **Transparente Logs** — Was der Agent wann gemacht hat

### Pricing-Idee

| Paket | Was | Preis |
|-------|-----|-------|
| Starter Agent | 1 Aufgabentyp, 1 Tool, Setup | ab 1.500 € |
| Business Agent | 3-5 Aufgaben, 3 Tools, Memory | ab 3.500 € |
| Autonome Company | Multi-Agent-System (CMO+CTO+...) | ab 8.000 € |
| Wartung | Monatliches Monitoring + Updates | 299 €/Mo |

---

## Technologie

- **Python 3.11+**
- **LLM:** OpenAI GPT-4o-mini (Standard) oder Anthropic Claude
- **Persistenz:** JSON-Dateien (kein DB-Setup nötig)
- **Deployment:** Windows Task Scheduler / Linux Cron / Docker

---

## Lizenz

Intern — AI_Studioxyz. Nicht öffentlich teilen ohne Genehmigung.
