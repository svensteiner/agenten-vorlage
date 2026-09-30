import base64
import http.client
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from cockpit.attachments import Attachments
from cockpit.conversations import Conversations
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler


def docx_bytes(text='Dokument-4711: Grüße 世界', padding=0):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')
        if padding:
            archive.writestr('padding.txt', b'0' * padding)
    return buffer.getvalue()


class DocumentAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Attachments(self.root)
        self.binding = {'conversation_id': 'a' * 32, 'company': 'Company', 'agent': 'agent', 'workspace': 'workspace'}

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, data, rid='b' * 32):
        return {'request_id': rid, 'name': 'reference.docx', 'content_base64': base64.b64encode(data).decode()}

    def test_real_subprocess_unicode_restart_original_download_and_no_reparse(self):
        data = docx_bytes()
        item = self.store.put(self.binding, self.payload(data))
        restored = Attachments(self.root)
        with patch('cockpit.attachments._process_result', side_effect=AssertionError('must not reparse')):
            self.assertIn('Grüße 世界', restored.read(self.binding, item['id'])['text'])
            self.assertEqual((data, 'reference.docx'), restored.download(self.binding, item['id']))
            self.assertEqual(item, restored.put(self.binding, self.payload(data)))
        record_path = restored._path(self.binding['conversation_id'], item['id'])
        record = json.loads(record_path.read_text(encoding='utf-8'))
        record['text'] = 'changed'
        record_path.write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaises(ContractError):
            restored.read(self.binding, item['id'])

    def test_timeout_and_invalid_document_leave_no_record_and_strip_secrets(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'synthetic-secret', 'OPENAI_API_KEY': 'synthetic-other'}):
            with patch('cockpit.attachments._process_result', side_effect=subprocess.TimeoutExpired('fixture', 8)) as process:
                with self.assertRaises(ContractError):
                    self.store.put(self.binding, self.payload(docx_bytes()))
                self.assertNotIn('DEEPSEEK_API_KEY', process.call_args.kwargs['env'])
                self.assertNotIn('OPENAI_API_KEY', process.call_args.kwargs['env'])
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(b'not-a-document'))
        self.assertEqual([], list(self.store.directory.rglob('*.json')))
        self.assertTrue(self.store.put(self.binding, self.payload(docx_bytes()))['id'])

    def test_document_limits_and_quota_retry(self):
        with self.assertRaises(ContractError):
            self.store.put(self.binding, self.payload(b'0' * (2 * 1024 * 1024 + 1)))
        data = docx_bytes()
        with patch('cockpit.attachments._MAX_TOTAL_BYTES', len(data)):
            item = self.store.put(self.binding, self.payload(data))
            self.assertEqual(item, self.store.put(self.binding, self.payload(data)))
            with self.assertRaises(ContractError):
                self.store.put(self.binding, self.payload(data, 'c' * 32))

    def test_http_document_context_and_download_with_large_upload(self):
        agent = create(self.root / 'agents' / 'assistant', 'developer', 'assistant', 'Company')
        manager = JobManager(self.root)
        dialogs = Conversations(manager)
        conversation = dialogs.create({'request_id': '1' * 32, 'agent': str(agent), 'backend': 'demo',
                                      'workspace': str(agent / 'workspace'), 'title': 'Documents'})
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        data = docx_bytes(padding=80_000)
        body = json.dumps(self.payload(data)).encode()
        headers = {'Content-Type': 'application/json'}
        try:
            with urlopen(Request(base + f'/api/conversations/{conversation["id"]}/attachments', body, headers), timeout=12) as response:
                item = json.load(response)
            dialogs.send(conversation['id'], {'request_id': '2' * 32, 'content': 'Use this document', 'attachment_ids': [item['id']]})
            job = manager.get('2' * 32)
            job.thread.join(10)
            self.assertEqual('completed', job.status)
            self.assertIn('Dokument-4711: Grüße 世界', job.result['task'])
            self.assertFalse((agent / 'workspace' / 'reference.docx').exists())
            with urlopen(base + f'/api/conversations/{conversation["id"]}/attachments/{item["id"]}', timeout=3) as response:
                self.assertEqual(data, response.read())
                self.assertIn('attachment;', response.headers['Content-Disposition'])
            # Verify rejection from the declared size before the body is read.
            # Sending the already-rejected body races Windows' TCP close/reset.
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                connection.putrequest('POST', '/api/jobs')
                connection.putheader('Content-Type', 'application/json')
                connection.putheader('Content-Length', str(len(body)))
                connection.endheaders()
                response = connection.getresponse()
                self.assertEqual(400, response.status)
                self.assertIn('too large', json.loads(response.read())['error'])
            finally:
                connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
            for job in manager.recent():
                if job.thread:
                    job.thread.join(10)


if __name__ == '__main__':
    unittest.main()
