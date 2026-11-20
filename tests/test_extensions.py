"""Tests for M1 /api/extensions backend: discovery, refresh, safe open-folder, and local skill import."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExtensionsBackendTests(unittest.TestCase):
    def _run_isolated(self, script: str):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROUNDTABLE_DATA=tmp, CODEX_HOME=os.path.join(tmp, 'codex_home'))
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_list_import_conflict_and_open_folder_security(self):
        self._run_isolated(r'''
import os, tempfile
from pathlib import Path
from bridge import extensions, projects

with tempfile.TemporaryDirectory() as proj_dir, tempfile.TemporaryDirectory() as src_parent:
    # Create a project
    proj = projects.create('DemoProj', proj_dir)

    # Create a valid local skill folder to import
    src_skill = Path(src_parent) / 'my-cool-skill'
    src_skill.mkdir()
    (src_skill / 'SKILL.md').write_text('---\nname: my-cool-skill\ndescription: Helps debug things\n---\nBody', encoding='utf-8')

    # 1. Without project_id: only user/host roots, no project root
    res0 = extensions.list_extensions('', local_host=True)
    root_ids0 = [r['id'] for r in res0['skill_roots']]
    assert 'codex:user' in root_ids0
    assert not any(r['scope'] == 'project' for r in res0['skill_roots'])

    # 2. With project_id: includes project root with can_import=True
    res1 = extensions.list_extensions(proj['id'], local_host=True)
    proj_roots = [r for r in res1['skill_roots'] if r['scope'] == 'project']
    assert len(proj_roots) == 1
    assert proj_roots[0]['can_import'] is True
    assert proj_roots[0]['can_open'] is True

    # 3. Remote device sees can_import=False and can_open=False, and cannot import/open
    res_remote = extensions.list_extensions(proj['id'], local_host=False)
    assert all(not r['can_import'] and not r['can_open'] for r in res_remote['skill_roots'])
    try:
        extensions.import_skill(agent_id='codex', scope='user', source_path=str(src_skill), local_host=False)
        raise AssertionError('Expected 403 for remote import')
    except extensions.ExtensionError as e:
        assert e.code == 403

    # 4. Import into user scope succeeds and appears in subsequent list_extensions(refresh=True)
    imp = extensions.import_skill(agent_id='codex', scope='user', source_path=str(src_skill), local_host=True)
    assert imp['item']['name'] == 'my-cool-skill'
    assert imp['item']['scope'] == 'user'
    assert imp['item']['description'] == 'Helps debug things'

    res2 = extensions.list_extensions('', refresh=True, local_host=True)
    names = [i['name'] for i in res2['items'] if i['kind'] == 'skill']
    assert 'my-cool-skill' in names

    # 5. Duplicate name returns 409 with conflict_name and preserves original file
    orig_md = Path(imp['item']['source']) / 'SKILL.md'
    orig_md.write_text('ORIGINAL', encoding='utf-8')
    try:
        extensions.import_skill(agent_id='codex', scope='user', source_path=str(src_skill), local_host=True)
        raise AssertionError('Expected 409 conflict')
    except extensions.ExtensionError as e:
        assert e.code == 409
        assert e.conflict_name == 'my-cool-skill'
    assert orig_md.read_text(encoding='utf-8') == 'ORIGINAL'

    # 6. Project scope requires project_id, and works when provided
    try:
        extensions.import_skill(agent_id='codex', scope='project', project_id='', source_path=str(src_skill), local_host=True)
        raise AssertionError('Expected 400 without project_id')
    except extensions.ExtensionError as e:
        assert e.code == 400

    imp_proj = extensions.import_skill(agent_id='codex', scope='project', project_id=proj['id'], source_path=str(src_skill), local_host=True)
    assert imp_proj['item']['scope'] == 'project'
    assert Path(imp_proj['item']['source'], 'SKILL.md').is_file()

    # 7. Non-codex (e.g. antigravity) rejected for local import
    try:
        extensions.import_skill(agent_id='antigravity', scope='user', source_path=str(src_skill), local_host=True)
        raise AssertionError('Expected 400 for antigravity import')
    except extensions.ExtensionError as e:
        assert e.code == 400

    # 8. open_folder only accepts listed root_ids and never arbitrary paths
    opened = []
    out = extensions.open_folder('codex:user', local_host=True, opener=opened.append)
    assert out['ok'] is True and len(opened) == 1
    try:
        extensions.open_folder('C:\\Windows', local_host=True, opener=opened.append)
        raise AssertionError('Expected 404 for arbitrary path')
    except extensions.ExtensionError as e:
        assert e.code == 404
''')

    def test_http_endpoints_end_to_end(self):
        self._run_isolated(r'''
import http.client, json, os, tempfile, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from bridge import web, projects

srv = ThreadingHTTPServer(('127.0.0.1', 0), web.Handler)
port = srv.server_address[1]
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()

def req(method, path, body=None, token=web.RT_TOKEN):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    headers = {'X-RT-Token': token} if token else {}
    payload = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        payload = json.dumps(body).encode('utf-8')
    conn.request(method, path, body=payload, headers=headers)
    r = conn.getresponse()
    raw = r.read().decode('utf-8')
    conn.close()
    return r.status, json.loads(raw) if raw else {}

try:
    # Unauthenticated rejected
    st, _ = req('GET', '/api/extensions', token='')
    assert st == 403

    # List works
    st, data = req('GET', '/api/extensions?refresh=1')
    assert st == 200
    assert 'items' in data and 'skill_roots' in data

    # Import + 409 conflict over HTTP
    with tempfile.TemporaryDirectory() as src_parent:
        src_skill = Path(src_parent) / 'http-skill'
        src_skill.mkdir()
        (src_skill / 'SKILL.md').write_text('---\ndescription: HTTP test skill\n---\n', encoding='utf-8')

        st, res = req('POST', '/api/extensions/import-skill', {
            'agent_id': 'codex', 'scope': 'user', 'source_path': str(src_skill),
        })
        assert st == 200, (st, res)
        assert res['item']['name'] == 'http-skill'

        st, res2 = req('POST', '/api/extensions/import-skill', {
            'agent_id': 'codex', 'scope': 'user', 'source_path': str(src_skill),
        })
        assert st == 409, (st, res2)
        assert res2['conflict_name'] == 'http-skill'

    # Arbitrary open-folder rejected with 404
    st, _ = req('POST', '/api/extensions/open-folder', {'root_id': 'evil:root'})
    assert st == 404
finally:
    srv.shutdown()
    srv.server_close()
''')


if __name__ == '__main__':
    unittest.main()
