"""Agent — Autonomer Haupt-Loop.

Der Agent läuft in einem Observe → Think → Act → Reflect Zyklus.
Er nutzt Brain für Intelligenz, Tools für Fähigkeiten, Memory für Persistenz.

Verwendung:
    python agent.py                    # Einmal ausführen
    python agent.py --loop             # Dauerbetrieb (alle X Minuten)
    python agent.py --task "Aufgabe"   # Spezifische Aufgabe
    python agent.py --dry-run          # Vorschau ohne Ausführung
    python agent.py --status           # Memory-Zusammenfassung

Anpassen:
    1. SOUL.md mit Agenten-Wissen füllen
    2. TOOLS mit eigenen Tools bestücken
    3. get_tasks() an eigene Task-Quelle anpassen
    4. run_task() Tool-Logik einbauen
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import brain
from memory import Memory

load_dotenv(Path(__file__).parent / ".env")

# ── Logging ───────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Agent] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_DIR / "agent.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent")

# ── Konfiguration ─────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "loop_interval_minutes": 60,
        "max_retries": 2,
        "quality_threshold": 7,
        "dry_run": False,
    }

# ── Tool-Registry ─────────────────────────────────────────────────────────
# Eigene Tools hier registrieren:
# from tools.web_search import WebSearchTool
# TOOLS["web_search"] = WebSearchTool()

TOOLS: dict = {}

# ── Task-Quelle ───────────────────────────────────────────────────────────

def get_tasks() -> list[dict]:
    """Holt die nächsten Aufgaben.

    Anpassen für eigene Task-Quelle:
    - Queue-Datei lesen
    - API aufrufen
    - Eigene Logik implementieren
    """
    # ── ANPASSEN: Hier eigene Task-Logik implementieren ──────────────────

    # Beispiel 1: Tasks aus Datei
    tasks_file = Path(__file__).parent / "tasks.json"
    if tasks_file.exists():
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        return [t for t in tasks if t.get("status") == "pending"]

    # Beispiel 2: Default-Task wenn nichts da ist
    return [{"id": "default", "task": "Status-Check ausführen und Memory zusammenfassen"}]


def mark_done(task: dict) -> None:
    """Markiert einen Task als erledigt."""
    tasks_file = Path(__file__).parent / "tasks.json"
    if not tasks_file.exists():
        return
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    for t in tasks:
        if t.get("id") == task.get("id"):
            t["status"] = "done"
            t["completed_at"] = datetime.now().isoformat()
    tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Kern-Loop: Observe → Think → Act → Reflect ───────────────────────────

def run_task(task: dict, mem: Memory, dry_run: bool = False) -> dict:
    """Führt einen einzelnen Task durch den vollen Agenten-Zyklus.

    Returns: {"success": bool, "result": str, "learning": dict}
    """
    task_text = task.get("task", str(task))
    task_id = task.get("id", "?")
    cfg = load_config()
    max_retries = cfg.get("max_retries", 2)

    logger.info(f"─── Task [{task_id}]: {task_text[:80]}")

    # ── 1. OBSERVE: Kontext sammeln ────────────────────────────────────
    context_parts = []
    recent_actions = mem.load("actions", limit=5)
    if recent_actions:
        context_parts.append(f"Letzte Aktionen: {json.dumps(recent_actions[-3:], ensure_ascii=False)}")
    recent_learnings = mem.load("learnings", limit=5)
    if recent_learnings:
        context_parts.append(f"Learnings: {[l.get('insight', '') for l in recent_learnings[-3:]]}")
    context = "\n".join(context_parts)

    # ── 2. THINK: Plan erstellen ───────────────────────────────────────
    logger.info("  → Think: Plan erstellen...")
    plan = brain.think(task_text, context)
    logger.info(f"  → Plan: {plan.get('plan', [])[:2]}")
    logger.info(f"  → Tool: {plan.get('tool', 'keins')}")

    if plan.get("needs_human"):
        logger.warning(f"  → Eskalation: Mensch benötigt für: {task_text}")
        mem.save("escalations", {"task": task_text, "reason": plan.get("reasoning")})
        return {"success": False, "result": "Eskalation", "learning": {}}

    if dry_run:
        logger.info(f"  [DRY RUN] Würde ausführen: {json.dumps(plan, ensure_ascii=False)[:200]}")
        return {"success": True, "result": "dry-run", "learning": {}}

    # ── 3. ACT: Ausführen ────────────────────────────────────────────
    tool_name = plan.get("tool")
    tool_input = plan.get("tool_input", task_text)
    tool_result = ""

    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"  → Retry {attempt}/{max_retries}...")
            time.sleep(2 ** attempt)  # Exponential backoff

        if tool_name and tool_name in TOOLS:
            logger.info(f"  → Tool ausführen: {tool_name}")
            tool_result = TOOLS[tool_name].safe_run(tool_input)
        else:
            # ── ANPASSEN: Eigene Ausführungslogik hier ───────────────
            logger.info(f"  → Direkte Ausführung (kein Tool)")
            tool_result = f"Task '{task_text}' verarbeitet."
            # Hier echte Logik implementieren

        # Ergebnis bewerten
        act_result = brain.act(plan, tool_result)
        logger.info(f"  → Ergebnis: {act_result.get('next_action')} | {act_result.get('summary', '')[:100]}")

        if act_result.get("success"):
            break
        if act_result.get("next_action") == "escalate":
            logger.warning("  → Eskalation nach Fehler")
            break

    # ── 4. REFLECT: Lernen ────────────────────────────────────────────
    learning = brain.reflect(
        action_taken=f"Task: {task_text}, Tool: {tool_name}",
        result=act_result.get("summary", tool_result),
        expected="Erfolgreiche Ausführung",
    )
    logger.info(f"  → Learning: {learning.get('insight', '')[:100]}")

    # ── 5. Persistieren ──────────────────────────────────────────────
    success = act_result.get("success", False)

    mem.save("actions", {
        "task": task_text,
        "task_id": task_id,
        "tool": tool_name,
        "success": success,
        "summary": act_result.get("summary", ""),
    })

    if learning.get("insight"):
        mem.save("learnings", {
            "insight": learning["insight"],
            "source": task_id,
            "improve": learning.get("improve_next_time"),
        })

    return {
        "success": success,
        "result": act_result.get("output") or act_result.get("summary", ""),
        "learning": learning,
    }


# ── Haupt-Entrypoint ──────────────────────────────────────────────────────

def run_once(task_text: str = None, dry_run: bool = False) -> None:
    """Führt einen einzelnen Zyklus aus."""
    mem = Memory()
    cfg = load_config()

    if task_text:
        tasks = [{"id": "cli", "task": task_text}]
    else:
        tasks = get_tasks()

    if not tasks:
        logger.info("Keine Tasks im Queue.")
        return

    logger.info(f"Agent startet — {len(tasks)} Task(s) gefunden")

    for task in tasks:
        result = run_task(task, mem, dry_run=dry_run or cfg.get("dry_run", False))
        if result["success"]:
            mark_done(task)
            logger.info(f"✅ Task erledigt: {task.get('id', '?')}")
        else:
            logger.warning(f"⚠️ Task fehlgeschlagen: {task.get('id', '?')}")


def run_loop(interval_minutes: int = None) -> None:
    """Dauerbetrieb: läuft alle X Minuten."""
    cfg = load_config()
    interval = interval_minutes or cfg.get("loop_interval_minutes", 60)

    # Graceful Shutdown
    running = [True]
    def handle_stop(sig, frame):
        logger.info("Signal empfangen — stoppe nach diesem Zyklus...")
        running[0] = False

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    logger.info(f"Dauerbetrieb gestartet — Zyklus alle {interval} Minuten")

    while running[0]:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Fehler im Zyklus: {e}", exc_info=True)

        if running[0]:
            logger.info(f"Nächster Zyklus in {interval} Minuten...")
            time.sleep(interval * 60)

    logger.info("Agent gestoppt.")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Autonomer Agent")
    parser.add_argument("--loop", action="store_true", help="Dauerbetrieb")
    parser.add_argument("--task", type=str, help="Spezifischer Task")
    parser.add_argument("--dry-run", action="store_true", help="Vorschau ohne Ausführung")
    parser.add_argument("--status", action="store_true", help="Memory-Status anzeigen")
    parser.add_argument("--interval", type=int, help="Loop-Intervall in Minuten")
    args = parser.parse_args()

    if args.status:
        mem = Memory()
        summary = mem.summary()
        print("\n=== Agent Memory Status ===")
        for key, info in summary.items():
            print(f"  {key}: {info['total']} gesamt, {info['today']} heute, letzter: {info['last']}")
        return

    if args.loop:
        run_loop(interval_minutes=args.interval)
    else:
        run_once(task_text=args.task, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
