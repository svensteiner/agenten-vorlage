import json
import unittest
from unittest.mock import MagicMock, patch

from agentkit.anthropic_backend import AnthropicBackend
from agentkit.contracts import ContractError


class AnthropicBackendTests(unittest.TestCase):
    def backend(self):
        return AnthropicBackend("fixture-model", api_key="fixture-key")

    def test_native_tool_round_trip_and_headers(self):
        messages = [{"role": "system", "content": "fixture system"},
                    {"role": "user", "content": "read files"},
                    {"role": "assistant", "content": "", "tool_calls": [
                        {"id": "one", "function": {"name": "read_file", "arguments": '{"path":"a"}'}},
                        {"id": "two", "function": {"name": "read_file", "arguments": '{"path":"b"}'}},
                    ]},
                    {"role": "tool", "tool_call_id": "one", "content": "a content"},
                    {"role": "tool", "tool_call_id": "two", "content": "b content"}]
        envelope = {"stop_reason": "tool_use", "content": [
            {"type": "text", "text": "inspect"},
            {"type": "tool_use", "id": "three", "name": "read_file", "input": {"path": "c"}},
        ]}
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(envelope).encode()
        backend = self.backend()
        with patch("agentkit.anthropic_backend.urllib.request.build_opener", return_value=opener):
            result = backend._chat(messages, 5, tools=backend.available_tool_specs("read-only"))
        request = opener.open.call_args.args[0]
        self.assertEqual("https://api.anthropic.com/v1/messages", request.full_url)
        self.assertEqual("fixture-key", request.get_header("X-api-key"))
        self.assertIsNone(request.get_header("Authorization"))
        payload = json.loads(request.data)
        self.assertEqual("fixture system", payload["system"])
        self.assertEqual(2, len(payload["messages"][-1]["content"]))
        self.assertEqual("tool_result", payload["messages"][-1]["content"][0]["type"])
        self.assertIn("input_schema", payload["tools"][0])
        self.assertEqual("read_file", result["tool_calls"][0]["function"]["name"])
        self.assertEqual({"path": "c"}, json.loads(result["tool_calls"][0]["function"]["arguments"]))

    def test_truncated_or_unknown_blocks_cannot_produce_actions(self):
        for envelope in ({"stop_reason": "max_tokens", "content": []},
                         {"stop_reason": "tool_use", "content": [{"type": "text", "text": "mismatch"}]},
                         {"stop_reason": "end_turn", "content": [{"type": "tool_use", "id": "x", "name": "read_file", "input": {}}]},
                         {"content": [{"type": "unknown"}]},
                         {"content": [{"type": "tool_use", "id": "x", "name": "write_file", "input": []}]}):
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(envelope).encode()
            with self.subTest(envelope=envelope), \
                 patch("agentkit.anthropic_backend.urllib.request.build_opener", return_value=opener), \
                 self.assertRaises(ContractError):
                self.backend()._chat([{"role": "user", "content": "fixture"}], 5)
