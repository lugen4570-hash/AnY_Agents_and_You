import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DirectModelTests(unittest.TestCase):
    def test_configure_verify_and_reply_with_compatible_service(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            result = subprocess.run(
                [sys.executable, '-c', SCRIPT], cwd=Path(__file__).resolve().parents[1],
                env=dict(os.environ, ROUNDTABLE_LOG_DIR=root), capture_output=True,
                text=True, encoding='utf-8', errors='replace', timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


SCRIPT = r'''
import json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bridge import access, direct_model, registry, room as R, web

key = 'test-only-model-key'
seen = []

class FakeProvider(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        seen.append((self.path, self.headers.get('Authorization'), body))
        if self.path.startswith('/redirect'):
            self.send_response(307)
            self.send_header('Location', '/other/v1/chat/completions')
            self.end_headers()
            return
        if self.headers.get('Authorization') != 'Bearer ' + key:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'example provider error must not be shown')
            return
        body = json.dumps({'choices': [{'message': {'content': 'example reply'}}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

provider = ThreadingHTTPServer(('127.0.0.1', 0), FakeProvider)
app = web.ExclusiveServer(('127.0.0.1', 0), web.Handler)
for server in (provider, app):
    threading.Thread(target=server.serve_forever, daemon=True).start()

def post(path, params):
    req = Request('http://127.0.0.1:%d%s' % (app.server_port, path), json.dumps(params).encode(),
                  {'X-RT-Token': web.RT_TOKEN, 'Content-Type': 'application/json'})
    try:
        res = urlopen(req, timeout=12)
    except HTTPError as exc:
        res = exc
    with res:
        return res.code, json.load(res)

assert direct_model.endpoint('https://provider.example') == 'https://provider.example/v1/chat/completions'
provider_url = 'http://127.0.0.1:%d' % provider.server_port
spec = {'id': 'direct-test', 'label': 'Direct test', 'driver': 'http', 'http_protocol': 'openai_chat',
        'endpoint': provider_url + '/v1', 'token': key, 'default': ['vendor-model', '']}
code, added = post('/api/agents/add', {'spec': spec})
assert code == 200, added
agent = next(agent for agent in added['agents'] if agent['id'] == spec['id'])
assert agent['http_protocol'] == 'openai_chat' and key not in json.dumps(added), added
config = Path(os.environ['ROUNDTABLE_LOG_DIR']) / 'agents.d' / 'direct-test.json'
if os.name == 'nt':
    assert key not in config.read_text(encoding='utf-8')
else:
    assert config.stat().st_mode & 0o077 == 0
registry.load()
assert registry.get(spec['id'])['token'] == key
code, verified = post('/api/contacts/check', {'id': spec['id']})
assert code == 200 and verified['connection']['state'] == 'ready', verified
assert seen[0][0] == '/v1/chat/completions'
assert seen[0][1] == 'Bearer ' + key and seen[0][2]['model'] == 'vendor-model'

folder = Path(os.environ['ROUNDTABLE_LOG_DIR']) / 'private-project-name'
folder.mkdir()
room = R.rooms.create('API model room', '', str(folder), participants=[spec['id']],
                      permissions={spec['id']: {'work': True, 'board': True, 'files': True, 'trigger': True}})
room.set_mode('work')
room.system_note('private runtime status')
assert not any(access.permissions(room, spec['id'])[p] for p in ('work','board','files','trigger'))
assert post('/api/r/' + quote(room.id) + '/send', {'text':'first direct room message'})[0] == 200
deadline = time.monotonic() + 8
while room.busy_for():
    assert time.monotonic() < deadline, 'model never replied'
    time.sleep(.02)
assert room.messages[-1]['text'] == 'example reply', room.messages
room_call = seen[-1][2]
assert set(room_call) == {'model', 'messages'}
content = room_call['messages'][0]['content']
assert 'first direct room message' in content and 'private-project-name' not in content and 'private runtime status' not in content

for bad in ({'token':'wrong-key'}, {'endpoint':provider_url + '/redirect'}):
    retry_spec = dict(spec, **bad)
    assert post('/api/agents/add', {'spec':retry_spec})[0] == 200
    count = len(seen)
    code, rejected = post('/api/contacts/check', {'id':spec['id']})
    assert code == 200 and rejected['connection']['state'] == 'failed', rejected
    assert len(seen) == count + 1 and key not in json.dumps(rejected) and 'example provider error' not in json.dumps(rejected)
assert post('/api/agents/add', {'spec':dict(spec, endpoint='http://service.example/v1')})[0] == 400

for server in (provider, app):
    server.shutdown()
    server.server_close()
'''


if __name__ == '__main__':
    unittest.main()
