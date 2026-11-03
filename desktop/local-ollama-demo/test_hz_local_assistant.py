"""Integration tests against a simulated loopback API and simulated Ollama."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hz_local_assistant as h

class Handler(BaseHTTPRequestHandler):
    notes = []
    token = 'read-secret'
    write_token = 'write-secret'
    model_requests = 0
    def log_message(self, *args):
        pass
    def do_POST(self):
        size = int(self.headers.get('Content-Length', 0))
        req = json.loads(self.rfile.read(size))
        code, body = 200, {}
        if self.path == '/api/generate':
            type(self).model_requests += 1
            body = {'response': 'The appointment is on Thursday [1].'}
        elif self.headers.get('Authorization') not in ('Bearer '+self.token, 'Bearer '+self.write_token):
            code, body = 401, {'error': 'Unauthorized'}
        elif self.path == '/v1/search':
            body = {'results': [x for x in self.notes if 'appointment' in req['query'].lower()]}
        elif self.path == '/v1/remember':
            if self.headers.get('Authorization') != 'Bearer '+self.write_token:
                code, body = 403, {'error': 'Read-only token'}
            else:
                item = {'id': str(len(self.notes)+1), 'title': req['title'],
                        'content': req['content'], 'score': .89, 'source': 'local-api'}
                self.notes.append(item)
                code, body = 201, {'id': item['id']}
        else:
            code, body = 404, {'error': 'not found'}
        encoded = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class LocalClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.notes = []
        Handler.model_requests = 0
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    def setUp(self):
        Handler.notes = []
        Handler.model_requests = 0

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=3)

    def test_permission_read_and_write(self):
        read = h.HingeZeroClient(self.http.server_port, 'read-secret')
        self.assertEqual(read.search('appointment'), [])
        with self.assertRaisesRegex(h.LocalServiceError, 'Read-only'):
            read.remember('Meeting', 'Appointment Thursday')
        write = h.HingeZeroClient(self.http.server_port, 'write-secret')
        self.assertEqual(write.remember('Meeting','Appointment Thursday'), '1')
        self.assertEqual(read.search('appointment')[0]['title'], 'Meeting')

    def test_write_confirmation_and_success(self):
        output=[]
        answers=iter(['Note', 'Appointment Thursday', 'YES'])
        status=h.run(['remember','--port',str(self.http.server_port)],input_fn=lambda _:next(answers), password_fn=lambda _:'write-secret', output=output.append)
        self.assertEqual(status,0)
        self.assertTrue(output[-1].startswith('Saved to HingeZero vault: record ID'))
        self.assertEqual(len(Handler.notes),1)

    def test_ollama_local_generate_and_citation(self):
        old_port=h.OLLAMA_PORT
        h.OLLAMA_PORT=self.http.server_port
        try:
            result=h.ask_local_ollama('When?', [{'id': 4, 'title': 'Appointment', 'content':'Thursday at 14:00', 'source':'local-api'}])
            self.assertIn('Thursday [1]', result)
            self.assertEqual(Handler.model_requests, 1)
        finally:
            h.OLLAMA_PORT=old_port

    def test_unauthorized(self):
        wrong = h.HingeZeroClient(self.http.server_port, 'wrong-secret')
        with self.assertRaisesRegex(h.LocalServiceError, 'invalid or expired'):
            wrong.search('appointment')

    def test_empty_evidence_abstains_without_model_call(self):
        old = Handler.model_requests
        self.assertIn('INSUFFICIENT EVIDENCE', h.ask_local_ollama('question', []))
        self.assertEqual(old, Handler.model_requests)

    def test_bad_model_name_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid Ollama model'):
            h.ask_local_ollama('question', [{'id':1,'title':'Test','content':'safe', 'source':'local'}], 'http://malicious.test')

    def test_strict_localhost_and_size(self):
        with self.assertRaises(ValueError):
            h.HingeZeroClient(0, 'token')
        with self.assertRaises(ValueError):
            h.HingeZeroClient(65536, 'token')
        with self.assertRaises(ValueError):
            h.HingeZeroClient(self.http.server_port,'token').search('a'*2001)
        with self.assertRaises(ValueError):
            h.HingeZeroClient(self.http.server_port,'token').remember('x','a'*12001)

    def test_save_requires_explicit_confirmation(self):
        output=[]
        answers=iter(['Test note', 'Contents', 'no'])
        ret=h.run(['remember','--port',str(self.http.server_port)], input_fn=lambda _:next(answers),
                  password_fn=lambda _: 'write-secret', output=output.append)
        self.assertEqual(ret,0)
        self.assertIn('Save cancelled',output[-1])

    def test_search_no_hit_does_not_invoke_ollama(self):
        output=[]
        old=Handler.model_requests
        ret=h.run(['ask','--port',str(self.http.server_port)], input_fn=lambda _: 'completely unrelated',
                  password_fn=lambda _: 'read-secret',output=output.append)
        self.assertEqual(ret,0)
        self.assertEqual(old,Handler.model_requests)
        self.assertIn('INSUFFICIENT EVIDENCE',output[-1])

if __name__=='__main__':
    unittest.main()
