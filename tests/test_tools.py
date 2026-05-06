import json
import tempfile
import unittest
from pathlib import Path

from core.context import ContextBuilder
from core.planner import Planner
from tools.file_tool import FileTool
from tools.message_bus import MessageBus


class FileToolPathTests(unittest.TestCase):
    def test_rejects_sibling_path_with_same_prefix(self):
        tool = FileTool()

        with self.assertRaises(ValueError):
            tool._safe_path("../agenten-vorlage-escape/secret.txt")

    def test_rejects_blocked_file_names(self):
        tool = FileTool()

        with self.assertRaises(ValueError):
            tool._safe_path(".env")


class MessageBusOrderingTests(unittest.TestCase):
    def test_receive_sorts_by_priority_then_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus_file = Path(tmp) / "message_bus.json"
            bus_file.write_text(
                json.dumps(
                    [
                        {
                            "id": "old-normal",
                            "from": "sender",
                            "to": "agent",
                            "type": "note",
                            "content": "old",
                            "priority": "normal",
                            "timestamp": "2026-05-06T08:00:00",
                            "read": False,
                        },
                        {
                            "id": "new-normal",
                            "from": "sender",
                            "to": "agent",
                            "type": "note",
                            "content": "new",
                            "priority": "normal",
                            "timestamp": "2026-05-06T09:00:00",
                            "read": False,
                        },
                        {
                            "id": "urgent",
                            "from": "sender",
                            "to": "agent",
                            "type": "note",
                            "content": "urgent",
                            "priority": "urgent",
                            "timestamp": "2026-05-06T07:00:00",
                            "read": False,
                        },
                    ]
                ),
                encoding="utf-8",
            )

            messages = MessageBus("agent", bus_file=bus_file).receive()

        self.assertEqual([msg["id"] for msg in messages], ["urgent", "new-normal", "old-normal"])


class PlannerToolGuessTests(unittest.TestCase):
    def test_file_tool_guess_preserves_path_case(self):
        context = ContextBuilder(Path(__file__).resolve().parents[1]).build()
        plan = Planner().draft("lies README.md", project=context, tools={"file": FileTool()})
        file_inputs = [step.input for step in plan.steps if step.tool == "file"]

        self.assertEqual(file_inputs, ["read:README.md"])


if __name__ == "__main__":
    unittest.main()
