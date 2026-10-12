import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.approvals import workspace_fingerprint
from agentkit.contracts import ContractError


class ApprovalWorkspaceSizeTests(unittest.TestCase):
    def test_real_source_project_over_512_files_is_fully_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(600):
                (root / f'module_{index}.py').write_text('pass\n', encoding='utf-8')
            before = workspace_fingerprint(root)
            (root / 'module_599.py').write_text('changed = True\n', encoding='utf-8')
            self.assertNotEqual(before, workspace_fingerprint(root))

    def test_item_budget_remains_finite(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch('agentkit.approvals.os.walk', return_value=[(temporary, [], [f'f{i}' for i in range(4097)])]):
                with self.assertRaisesRegex(ContractError, 'too large'):
                    workspace_fingerprint(Path(temporary))

    def test_byte_budget_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'oversized').write_bytes(b'x' * (8 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(ContractError, 'too large'):
                workspace_fingerprint(root)
