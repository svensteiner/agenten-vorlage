"""Persistent reversible assistant organization settings."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from agentkit.contracts import ContractError
from agentkit.storage import save


class AssistantSettings:
    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / "assistant-settings" / "archive.json"
        self._lock = threading.RLock()

    def _read(self) -> dict[str, bool]:
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                raw_text = stream.read(512_001)
            if len(raw_text) > 512_000:
                raise ContractError("Assistant archive state is too large.")
            raw = json.loads(raw_text)
            if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw.get("version") != 1 or not isinstance(raw.get("agents"), dict):
                raise ContractError("Assistant archive state is invalid.")
            agents = raw["agents"]
            if len(agents) > 10_000 or any(not isinstance(k, str) or not Path(k).is_absolute() or not isinstance(v, bool) for k, v in agents.items()):
                raise ContractError("Assistant archive state is invalid.")
            return dict(agents)
        except FileNotFoundError:
            return {}
        except ContractError:
            raise
        except (OSError, ValueError, TypeError, UnicodeError) as exc:
            raise ContractError("Assistant archive state is invalid.") from exc

    def archived(self, agent_path: Path) -> bool:
        with self._lock:
            return self._read().get(str(agent_path.resolve()), False)

    def set_archived(self, agent_path: Path, archived: bool) -> bool:
        if not isinstance(archived, bool):
            raise ContractError("archived must be boolean.")
        canonical = str(agent_path.resolve())
        with self._lock:
            values = self._read()
            values[canonical] = archived
            document = {"version": 1, "agents": values}
            if len(values) > 10_000 or len(json.dumps(document, ensure_ascii=False, indent=2) + "\n") > 512_000:
                raise ContractError("Assistant archive state is too large.")
            save(self.path, document)
            return archived
