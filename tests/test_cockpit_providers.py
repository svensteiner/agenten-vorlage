import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


class ProviderHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = JobManager(state_dir=Path(self.temp.name))
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.manager))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, payload=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = Request(self.base + '/api/providers/deepseek',
                          data=json.dumps(payload).encode() if payload is not None else None,
                          headers=headers)
        return urlopen(request, timeout=3)

    def test_save_clear_and_status_never_echo_secret(self):
        secret = 'synthetic-provider-test-only'
        status = {'configured': True, 'source': 'stored', 'storage_available': True}
        with patch.object(self.manager.providers, 'save') as save, \
                patch.object(self.manager.providers, 'clear') as clear, \
                patch.object(self.manager.providers, 'status', return_value=status):
            with self.request({'action': 'save', 'api_key': secret}) as response:
                raw = response.read().decode()
                self.assertNotIn(secret, raw)
                self.assertEqual(status, json.loads(raw))
            save.assert_called_once_with(secret)
            with self.request({'action': 'clear'}) as response:
                self.assertEqual(200, response.status)
            clear.assert_called_once_with()

    def test_cross_origin_cannot_write_or_read(self):
        with patch.object(self.manager.providers, 'save') as save:
            for payload in (None, {'action': 'save', 'api_key': 'synthetic'}):
                with self.assertRaises(HTTPError) as error:
                    self.request(payload, 'https://foreign.example')
                self.assertEqual(403, error.exception.code)
            save.assert_not_called()

    def test_invalid_payload_and_storage_errors_are_redacted(self):
        secret = 'synthetic-never-in-response'
        with patch.object(self.manager.providers, 'save', side_effect=ContractError(secret)):
            for payload in ({'action': 'save', 'api_key': secret},
                            {'action': 'save', 'api_key': secret, 'extra': True}):
                with self.assertRaises(HTTPError) as error:
                    self.request(payload)
                self.assertEqual(400, error.exception.code)
                self.assertNotIn(secret, error.exception.read().decode())
        with patch.object(self.manager.providers, 'status', side_effect=ContractError(secret)):
            with self.request() as response:
                raw = response.read().decode()
                self.assertNotIn(secret, raw)
                self.assertFalse(json.loads(raw)['configured'])

    def test_saved_key_injected_without_persisting_and_fixed_endpoint(self):
        root = Path(self.temp.name) / 'project'
        agent = create(root / 'agents' / 'test', 'developer', 'test', 'Company')
        manager = JobManager(root)
        secret = 'synthetic-injection-only'
        with patch.object(manager.providers, 'api_key', return_value=secret), \
                patch('cockpit.server.DeepSeekBackend') as backend, \
                patch('cockpit.server.Engine') as engine:
            engine.return_value.run.return_value = {'status': 'completed'}
            job = manager.start({'agent': str(agent), 'workspace': str(agent / 'workspace'),
                                 'backend': 'deepseek', 'task': 'Fixture only'})
            job.thread.join(5)
            self.assertEqual('completed', job.status)
            backend.assert_called_once_with(None, api_key=secret, base_url='https://api.deepseek.com')
            self.assertNotIn(secret, manager._job_file(job.job_id).read_text())
            self.assertTrue(engine.call_args.kwargs['require_approvals'])


if __name__ == '__main__':
    unittest.main()
