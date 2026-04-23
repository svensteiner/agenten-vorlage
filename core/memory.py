"""Core memory abstraction for reusable automations."""

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class MemoryStore:
    root: Path
    namespace: str = "core"
    state: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def load(self, key: str) -> list[dict[str, Any]]:
        path = self.root / self.namespace / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def save(self, key: str, value: dict[str, Any]) -> None:
        path = self.root / self.namespace / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        current = self.load(key)
        current.append(value)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
