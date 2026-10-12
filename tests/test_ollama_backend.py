import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.ollama_backend import OllamaBackend
from agentkit.api_backend import ApiBackend
from agentkit.cli import parser
from agentkit.contracts import ContractError


class OllamaBackendTests(unittest.TestCase):
    def test_bounded_reads_large_files_without_silent_truncation(self):
        backend = OllamaBackend(base_url='http://192.168.0.101:11434/v1')
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary,'large.py')
            path.write_text('x' * 100 + '\n',encoding='utf-8')
            path.write_text(path.read_text() * 3000,encoding='utf-8')
            result=json.loads(backend._run_tool('read_file',{'path':'large.py','start_line':101,'max_lines':200}, {'workspace':temporary},5))
            self.assertLessEqual(len(result['content']),12000)
            self.assertTrue(result['truncated'])
            self.assertEqual(result['end_line']+1,result['next_line'])
            self.assertEqual(3000,result['total_lines'])
            matches=json.loads(backend._run_tool('search_file',{'path':'large.py','text':'xxx'},{'workspace':temporary},5))
            self.assertEqual(20,len(matches['matches']))
            self.assertTrue(matches['truncated'])
            self.assertEqual(3000,matches['total_matches'])
            past_end=json.loads(backend._run_tool('read_file',{'path':'large.py','start_line':3001},{'workspace':temporary},5))
            self.assertEqual('start_line_out_of_range',past_end['error'])
            invalid=json.loads(backend._run_tool('read_file',{'path':'large.py','start_line':True},{'workspace':temporary},5))
            self.assertEqual('invalid_read_range',invalid['error'])
    def test_private_endpoint_without_credentials_and_binding(self):
        with patch.dict('os.environ', {'AGENTKIT_API_KEY': 'cloud-secret', 'AGENTKIT_OLLAMA_BASE_URL': 'http://192.168.0.101:11434/v1'}):
            backend = OllamaBackend()
        self.assertEqual('ollama', backend.api_key)
        self.assertEqual('qwen3-coder-next:latest', backend.model)
        self.assertEqual('http://192.168.0.101:11434/v1', backend.base_url)
        self.assertNotEqual(backend.name, OllamaBackend(base_url='http://192.168.0.102:11434/v1').name)
        self.assertIn('inspect_git', backend.allowed_tools)
        self.assertEqual('ollama', parser().parse_args(['run','--agent','fixture','--backend','ollama','--task','fixture']).backend)

    def test_public_or_ambiguous_endpoints_are_rejected(self):
        for endpoint in ['http://8.8.8.8:11434/v1','http://asus:11434/v1', 'http://192.168.0.101/v1',
                         'http://user:password@192.168.0.101:11434/v1', 'http://192.168.0.101:11434/v1?key=x',
                         'http://169.254.169.254:11434/v1','http://192.168.0.101:11434/v1#x']:
            with self.subTest(endpoint=endpoint), self.assertRaises(ContractError):
                OllamaBackend(base_url=endpoint)
        with self.assertRaises(ContractError):
            ApiBackend('fixture',api_key='fixture',base_url='http://192.168.0.101:11434/v1')

    def test_worker_report_without_actual_tool_observation_is_rejected(self):
        backend = OllamaBackend(base_url='http://192.168.0.101:11434/v1')
        with patch.object(ApiBackend, '_chat', return_value={'content':'{"status":"success"}'}):
            with self.assertRaisesRegex(ContractError, 'without actual tool observations'):
                backend._chat([{'role':'user','content':'Fix the file'}], 5,
                              tools=backend.available_tool_specs('workspace-write'))
            result = backend._chat([{'role':'tool','content':'actual host result','tool_call_id':'fixture'}], 5,
                                   tools=backend.available_tool_specs('workspace-write'))
        self.assertIn('content', result)

    def test_report_format_repair_does_not_repeat_tool_execution(self):
        backend = OllamaBackend(base_url='http://192.168.0.101:11434/v1')
        report = {'status':'success','summary':'Read actual file','artifacts':['app.py'],
                  'evidence':['file contains fixture'],'next_actions':[]}
        call = {'id':'read-1','type':'function','function':{'name':'read_file','arguments':'{"path":"app.py"}'}}
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary,'app.py').write_text('fixture',encoding='utf-8')
            with patch.object(backend,'_chat',side_effect=[{'tool_calls':[call]}, {'content':'Done.'},
                                                          {'content':json.dumps(report)}]) as chat, \
                    patch.object(backend,'_run_tool',wraps=backend._run_tool) as run:
                result = backend._call('Read file','report',{'workspace':temporary,'sandbox':'read-only'},10)
            self.assertEqual(report,result)
            run.assert_called_once()
            self.assertIsNone(chat.call_args.kwargs['tools'])

    def test_oversized_report_repair_is_rejected_before_another_request(self):
        backend = OllamaBackend(base_url='http://192.168.0.101:11434/v1')
        call = {'id':'read-1','type':'function','function':{'name':'read_file','arguments':'{"path":"app.py"}'}}
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary,'app.py').write_text('fixture',encoding='utf-8')
            with patch.object(backend,'_chat',side_effect=[{'tool_calls':[call]},
                    {'content':'x' * (backend.max_message_chars + 1)}]) as chat:
                with self.assertRaises(ContractError):
                    backend._call('Read file','report',{'workspace':temporary,'sandbox':'read-only'},10)
            self.assertEqual(2,chat.call_count)
