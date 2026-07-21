"""Workers — Permission-scoped sub-agents (Least-Privilege-Prinzip).

Jeder Worker hat eine klar definierte Rolle mit eingeschränktem Tool-Zugriff:

  reader  → nur lesen  (file_read, web_search)
  compute → nur rechnen (keine externen Tools)
  writer  → nur schreiben (file_write, notify)

Genau ein Worker hat Write-Zugriff. Das verhindert unerwünschte
Seiteneffekte und macht den Datenfluss nachvollziehbar.

Verwendung:
    from workers import WorkerRegistry, load_registry

    registry = load_registry()
    allowed, reason = registry.check_permission("reader", "file_write")
    # → (False, "Worker 'reader' hat keinen Zugriff auf 'file_write'")

    scoped_tools = registry.filter_tools("reader", all_tools)
    # → nur file_read + web_search
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("workers")

# Aliases: Tool-Operationen → kanonischer Tool-Name
# file_read und file_write sind beide das "file"-Tool, aber Workers
# bekommen nur die jeweils erlaubte Operation.
_TOOL_ALIASES: dict[str, str] = {
    "file_read": "file",
    "file_write": "file",
    "file_list": "file",
}


@dataclass(frozen=True)
class Worker:
    name: str
    description: str
    allowed_tools: tuple[str, ...]
    trust_level: str  # low | medium | high

    def can_use(self, tool_name: str) -> bool:
        """Prüft ob dieses Worker-Tool verwenden darf."""
        if tool_name in self.allowed_tools:
            return True
        # Vorwärts-Alias: file_read → file
        canonical = _TOOL_ALIASES.get(tool_name)
        if canonical and canonical in self.allowed_tools:
            return True
        # Rückwärts-Alias: "file" erlaubt wenn file_read/file_write in allowed_tools
        for allowed in self.allowed_tools:
            if _TOOL_ALIASES.get(allowed) == tool_name:
                return True
        return False


class WorkerRegistry:
    """Lädt Worker-Definitionen aus manifest.yaml und erzwingt Berechtigungen."""

    def __init__(self, manifest: dict) -> None:
        self._workers: dict[str, Worker] = {}
        for name, cfg in manifest.get("workers", {}).items():
            self._workers[name] = Worker(
                name=name,
                description=cfg.get("description", ""),
                allowed_tools=tuple(cfg.get("tools", [])),
                trust_level=cfg.get("trust_level", "medium"),
            )
        logger.debug("WorkerRegistry: %d Worker geladen — %s", len(self._workers), list(self._workers))

    def get(self, name: str) -> Optional[Worker]:
        return self._workers.get(name)

    def names(self) -> list[str]:
        return list(self._workers.keys())

    def check_permission(self, worker_name: str, tool_name: str) -> tuple[bool, str]:
        """Prüft ob worker_name das tool_name verwenden darf.

        Returns:
            (True, "")          wenn erlaubt
            (False, Grund)      wenn blockiert
        """
        worker = self._workers.get(worker_name)
        if worker is None:
            return True, ""
        if worker.can_use(tool_name):
            return True, ""
        return False, (
            f"Worker '{worker_name}' hat keinen Zugriff auf '{tool_name}'. "
            f"Erlaubt: {list(worker.allowed_tools)}"
        )

    def filter_tools(self, worker_name: str, available_tools: dict) -> dict:
        """Gibt nur die für worker_name erlaubten Tools zurück.

        Für file-Tool: read-only Worker bekommen eine eingeschränkte Version
        (nur read/list), write-only Worker nur write.
        """
        worker = self._workers.get(worker_name)
        if worker is None:
            return available_tools

        filtered: dict = {}
        for tool_name, tool in available_tools.items():
            if worker.can_use(tool_name):
                if tool_name == "file":
                    filtered[tool_name] = _ScopedFileTool(tool, worker.allowed_tools)
                else:
                    filtered[tool_name] = tool

        return filtered

    def summary(self) -> dict:
        return {
            name: {
                "tools": list(w.allowed_tools),
                "trust": w.trust_level,
                "description": w.description,
            }
            for name, w in self._workers.items()
        }


class _ScopedFileTool:
    """Wrapper der file_tool auf erlaubte Operationen einschränkt."""

    def __init__(self, original, allowed_tools: tuple[str, ...]) -> None:
        self._orig = original
        self._can_read = "file_read" in allowed_tools or "file_list" in allowed_tools
        self._can_write = "file_write" in allowed_tools
        self.name = original.name

    def safe_run(self, input_str: str) -> str:
        op = input_str.split(":")[0].strip().lower()
        if op in ("read", "list") and not self._can_read:
            return "FEHLER: Dieser Worker hat keinen Lesezugriff auf das Dateisystem."
        if op in ("write", "append") and not self._can_write:
            return "FEHLER: Dieser Worker hat keinen Schreibzugriff auf das Dateisystem."
        return self._orig.safe_run(input_str)


def load_registry(manifest: Optional[dict] = None) -> WorkerRegistry:
    """Erstellt WorkerRegistry aus manifest oder leerer Config."""
    return WorkerRegistry(manifest or {})
