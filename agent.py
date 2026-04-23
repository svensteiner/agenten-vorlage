"""Core runner for the reusable automation-agent template.

This file is now the thin compatibility layer around the reusable core.
The heavy lifting lives in `core/` and the project pack under `project/`.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from core.orchestrator import AgentOrchestrator
from memory import Memory
from tools.message_bus import MessageBus

load_dotenv(Path(__file__).parent / ".env")

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "project" / "config.json"
TASKS_PATH = ROOT / "tasks.json"
LOG_DIR = ROOT / "logs"
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

TOOLS: dict = {}
ORCHESTRATOR = AgentOrchestrator(ROOT)


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "project_name": "automation-project",
        "agent_name": "automation-agent",
        "loop_interval_minutes": 60,
    }


def _load_tools() -> None:
    """Auto-load BaseTool subclasses from tools/."""
    import importlib
    import inspect

    from tools.base_tool import BaseTool

    skip = {"base_tool", "message_bus", "__init__"}
    tools_dir = ROOT / "tools"
    for path in tools_dir.glob("[!_]*.py"):
        if path.stem in skip:
            continue
        try:
            mod = importlib.import_module(f"tools.{path.stem}")
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, BaseTool) and cls is not BaseTool and cls.name != "base_tool":
                    inst = cls()
                    TOOLS.setdefault(inst.name, inst)
        except Exception as exc:
            logger.warning("Tool discovery (%s): %s", path.stem, exc)


def _read_tasks() -> list[dict]:
    if not TASKS_PATH.exists():
        return []
    try:
        return json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read tasks.json: %s", exc)
        return []


def _write_tasks(tasks: list[dict]) -> None:
    TASKS_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_task_status(task_id: str, status: str, extra: dict | None = None) -> None:
    tasks = _read_tasks()
    if not tasks:
        return
    for task in tasks:
        if task.get("id") == task_id:
            task["status"] = status
            if extra:
                task.update(extra)
            break
    _write_tasks(tasks)


def _pending_tasks() -> list[dict]:
    return [task for task in _read_tasks() if task.get("status") == "pending"]


def _show_status() -> None:
    cfg = _load_config()
    ctx = ORCHESTRATOR.context_builder.build()
    mem = Memory()

    print(f"\n=== Core Status [{ctx.project_name}] ===")
    print(f"Project root: {ctx.project_root}")
    print(f"Agent name: {cfg.get('agent_name')}")
    print(f"Manifest workflow: {ctx.manifest.get('workflow', {}).get('name', '(keine)')}")
    print(f"Workflows: {list(ctx.workflows.keys()) or '(keine)'}")
    print(f"Policies: {list(ctx.policies.keys()) or '(keine)'}")
    print(f"Knowledge: {list(ctx.knowledge.keys()) or '(keine)'}")
    print(f"Subagents: {list(ctx.subagents.keys()) or '(keine)'}")
    print(f"Loaded tools: {list(TOOLS.keys()) or '(keine)'}")

    print("\n=== Legacy Memory ===")
    summary = mem.summary()
    if not summary:
        print("  (keine Einträge)")
    for key, info in summary.items():
        print(f"  {key}: {info['total']} gesamt, {info['today']} heute, letzter: {info['last']}")


def _run_single(task_text: str) -> None:
    logger.info("Core run: %s", task_text[:120])
    result = ORCHESTRATOR.run(task_text, tools=TOOLS)
    print(f"\n=== Core Run [{result.context.project_name if result.context else 'project'}] ===")
    print(f"Task: {result.task}")
    print(f"Success: {result.success}")
    if result.plan:
        print(f"Workflow hint: {result.plan.workflow_hint or '(keine)'}")
        print(f"Steps: {[step.action for step in result.plan.steps]}")
    if result.metadata.get("outputs"):
        print("Outputs:")
        for line in result.metadata["outputs"]:
            print(f"- {line}")


def _run_queue() -> None:
    tasks = _pending_tasks()
    if not tasks:
        logger.info("Keine Tasks — Agent ist idle.")
        return

    for task in tasks:
        task_id = task.get("id", "?")
        task_text = task.get("task", str(task))
        _update_task_status(task_id, "in_progress")
        try:
            result = ORCHESTRATOR.run(task_text, tools=TOOLS)
            _update_task_status(
                task_id,
                "done" if result.success else "failed",
                extra={
                    "result": {
                        "task": result.task,
                        "success": result.success,
                        "project": result.context.project_name if result.context else None,
                        "workflow_hint": result.plan.workflow_hint if result.plan else None,
                        "outputs": result.metadata.get("outputs", []),
                    }
                },
            )
            if result.success:
                logger.info("Task erledigt: %s", task_id)
            else:
                logger.warning("Task fehlgeschlagen: %s", task_id)
        except Exception as exc:
            _update_task_status(task_id, "failed", extra={"error": str(exc)})
            logger.error("Task %s failed: %s", task_id, exc, exc_info=True)


def _messages() -> None:
    cfg = _load_config()
    bus = MessageBus(agent_name=cfg.get("agent_name", "automation-agent"))
    msgs = bus.receive(unread_only=False)
    print(f"\n=== Bus-Nachrichten für [{cfg.get('agent_name')}] ===")
    if not msgs:
        print("  Keine Nachrichten.")
        return
    for msg in msgs[-10:]:
        status = "📬" if not msg.get("read") else "✓"
        print(f"  {status} [{msg['priority']}] Von {msg['from']}: {msg['type']} — {str(msg['content'])[:60]}")


def _loop(interval_minutes: int | None = None) -> None:
    cfg = _load_config()
    interval = interval_minutes or cfg.get("loop_interval_minutes", 60)
    running = [True]

    def handle_stop(sig, frame):
        logger.info("Signal empfangen — stoppe nach diesem Zyklus...")
        running[0] = False

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    logger.info("Dauerbetrieb gestartet — Zyklus alle %s Minuten", interval)
    while running[0]:
        ORCHESTRATOR.runtime.write_heartbeat(cfg.get("agent_name", "automation-agent"))
        try:
            _run_queue()
        except Exception as exc:
            logger.error("Fehler im Zyklus: %s", exc, exc_info=True)

        if running[0]:
            logger.info("Nächster Zyklus in %s Minuten...", interval)
            time.sleep(interval * 60)

    logger.info("Agent gestoppt.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Core runner for the automation-agent template")
    parser.add_argument("--loop", action="store_true", help="Dauerbetrieb")
    parser.add_argument("--task", type=str, help="Spezifischer Task")
    parser.add_argument("--status", action="store_true", help="Status anzeigen")
    parser.add_argument("--messages", action="store_true", help="Bus-Nachrichten anzeigen")
    parser.add_argument("--interval", type=int, help="Loop-Intervall in Minuten")
    parser.add_argument("--dry-run", action="store_true", help="Kompatibilitätsflag")
    args = parser.parse_args()

    _load_tools()

    if args.status:
        _show_status()
        return

    if args.messages:
        _messages()
        return

    if args.task:
        _run_single(args.task)
        return

    if args.loop:
        _loop(interval_minutes=args.interval)
        return

    _run_queue()


if __name__ == "__main__":
    main()
