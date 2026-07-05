"""Gemeinsame Test-Fixtures für die Agenten-Vorlage."""
import json
import pytest
from pathlib import Path


MINIMAL_MANIFEST = {
    "name": "Test-Agent",
    "description": "Agent für Tests",
    "model": {
        "fast": "claude-haiku-4-5-20251001",
        "smart": "claude-sonnet-4-6",
    },
    "workers": {
        "reader": {
            "description": "Liest Daten",
            "tools": ["file_read", "web_search"],
            "trust_level": "low",
        },
        "compute": {
            "description": "Verarbeitet Daten",
            "tools": [],
            "trust_level": "medium",
        },
        "writer": {
            "description": "Schreibt Ergebnisse",
            "tools": ["file_write", "notify"],
            "trust_level": "high",
        },
    },
    "skills": [],
    "callable_agents": [
        {"name": "reader", "file": "agents/reader.md"},
        {"name": "writer", "file": "agents/writer.md"},
    ],
    "governance": {
        "require_approval_for": ["delete", "overwrite"],
        "cooldowns": {
            "notify": {"minutes": 30, "max_per_day": 10},
            "web_search": {"minutes": 5, "max_per_day": 50},
        },
    },
    "handoffs": {
        "allowlist": ["reader", "compute", "writer"],
        "max_payload_chars": 2000,
    },
}


@pytest.fixture
def manifest() -> dict:
    return {**MINIMAL_MANIFEST}


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Temporäres Root-Verzeichnis mit minimaler Struktur."""
    (tmp_path / "agents").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "SOUL.md").write_text("# Test Agent\nDu bist ein Test-Agent.", encoding="utf-8")
    (tmp_path / "config.json").write_text(
        json.dumps({"agent_name": "test", "loop_interval_minutes": 60}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def mock_tool():
    """Einfaches Mock-Tool das immer 'MOCK_RESULT' zurückgibt."""
    class MockTool:
        name = "mock_tool"
        def safe_run(self, input_str: str) -> str:
            return f"MOCK_RESULT:{input_str}"
    return MockTool()


@pytest.fixture
def mock_write_tool():
    """Mock-Tool das Schreibvorgänge simuliert."""
    class MockWriteTool:
        name = "file"
        calls: list = []
        def safe_run(self, input_str: str) -> str:
            self.calls.append(input_str)
            return f"OK:{input_str[:30]}"
    return MockWriteTool()
