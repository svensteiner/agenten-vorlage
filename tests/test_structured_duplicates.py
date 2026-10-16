import json
import unittest
from agentkit.backends import DeepSeekBackend

class DuplicateJSONTests(unittest.TestCase):
    def test_tool_arguments_reject_duplicates_without_literal_fallback(self):
        for raw in ('{"path":"a","path":"b"}',
                    '{"outer":{"x":1,"x":2}}',
                    '{"items":[{"x":1,"x":2}]}',
                    "{'path': 'a', 'path': 'b'}",
                    "{'outer': {'x': 1, 'x': 2}}"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                DeepSeekBackend._parse_tool_arguments(raw)

    def test_valid_python_literal_arguments_remain_supported(self):
        self.assertEqual(
            {'path': 'a', 'items': [{'x': True}, {'x': None}]},
            DeepSeekBackend._parse_tool_arguments(
                "{'path': 'a', 'items': [{'x': True}, {'x': None}]}"),
        )

    def test_rejects_duplicates_at_every_depth_and_in_wrappers(self):
        samples = ['{"action":"delegate","action":"finish"}',
                   '{"outer":{"x":1,"x":2}}',
                   '{"items":[{"x":1,"x":2}]}',
                   '{"approved":true,"approved":true}',
                   '{"pa\\u0074h":"a","path":"b"}']
        for raw in samples:
            for content in (raw, '```json\n'+raw+'\n```', 'Before '+raw+' after'):
                with self.subTest(content=content), self.assertRaises(json.JSONDecodeError):
                    DeepSeekBackend._parse_structured_content(content)
                with self.subTest(tool_content=content), self.assertRaises(json.JSONDecodeError):
                    DeepSeekBackend._parse_tool_arguments(content)

    def test_existing_valid_wrappers_remain_supported(self):
        raw = '{"path":"README.md","items":[{"x":1},{"x":2}]}'
        for content in (raw, '```json\n'+raw+'\n```', 'Before '+raw+' after'):
            with self.subTest(content=content):
                self.assertEqual(json.loads(raw), DeepSeekBackend._parse_structured_content(content))

    def test_duplicate_looking_text_values_are_not_keys(self):
        value = {"text": '"x":1,"x":2', "same": 2, "other": 2}
        self.assertEqual(value, DeepSeekBackend._parse_structured_content(json.dumps(value)))
