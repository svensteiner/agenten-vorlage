"""Runtime helpers for queues, state, and heartbeat data."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import Any


@dataclass
class RuntimeState:
    active: bool = True
    last_heartbeat: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_heartbeat(self, agent_name: str) -> Path:
        state = RuntimeState(
            active=True,
            last_heartbeat=datetime.now().isoformat(),
            metadata={"agent_name": agent_name},
        )
        path = self.root / "heartbeat.json"
        path.write_text(json.dumps(state.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
