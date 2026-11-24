"""Tests for collapsible desktop sidebar, real ctx extraction, model parity, and all-agent compaction."""
from pathlib import Path
import io
import json
import shutil
import subprocess
import threading
import time
import unittest
from unittest.mock import patch

import test_contacts_access as support  # noqa: F401 - isolates test data directory
from bridge import access, acp, agents, drivers, members, model_catalog, registry, room as R


class _DummyResp(io.BytesIO):
    def __init__(self, body: bytes, ctype: str = 'application/json'):
        super().__init__(body)
        self.headers = {'Content-Type': ctype}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def _load_preset(root: Path, name: str) -> dict:
    raw = json.loads((root / 'bridge' / 'presets' / f'{name}.json').read_text(encoding='utf-8'))
    return registry._norm(raw)


class SidebarCollapseTests(unittest.TestCase):
    def test_css_and_html_include_desktop_collapse_rules(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / 'index.html').read_text(encoding='utf-8')
        css = (root / 'static' / 'workspace.css').read_text(encoding='utf-8')
        studio = (root / 'static' / 'studio.css').read_text(encoding='utf-8')
        self.assertIn('id="navClose"', html)
        self.assertNotIn('id="navClose" aria-label="收起侧栏" title="收起侧栏">×<', html)
        self.assertIn('id="navToggle"', html)
        self.assertIn('body.nav-collapsed', css)
        self.assertIn('body.nav-collapsed #rooms', css)
        self.assertIn('translateX(-104%)', css)
        self.assertIn('position:fixed;left:0', css)
        self.assertIn('body.nav-collapsed #navToggle', css)
        self.assertIn('body.nav-collapsed #rooms', studio)
        self.assertIn('column-gap:0', studio)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to test sidebar JS')
    def test_desktop_sidebar_collapse_persists_and_toggles(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const ws = fs.readFileSync('static/workspace.js', 'utf8');
const part = ws.slice(ws.indexOf("const NAV_COLLAPSE_KEY='any_nav_collapsed';"));
assert.ok(part.includes('setNavCollapsed'), 'nav collapse helpers must exist in workspace.js');
const makeClassList = () => {
  const set = new Set();
  return {
    add: (...ks) => ks.forEach(k => set.add(k)),
    remove: (...ks) => ks.forEach(k => set.delete(k)),
    toggle: (k, force) => {
      if (force === undefined) force = !set.has(k);
      if (force) set.add(k); else set.delete(k);
      return force;
    },
    contains: k => set.has(k),
  };
};
const bodyClassList = makeClassList();
const modalClassList = makeClassList();
const makeEl = extra => ({
  onclick: null,
  attributes: {},
  classList: makeClassList(),
  setAttribute(k, v) { this.attributes[k] = v; },
  addEventListener() {},
  focus() {},
  select() {},
  ...extra,
});
const els = {
  rooms: makeEl({inert: false}),
  navToggle: makeEl(),
  navClose: makeEl(),
  navShade: makeEl(),
  roomList: makeEl(),
  navSearch: makeEl({value: ''}),
  modal: makeEl({classList: modalClassList}),
};
const store = new Map([['any_nav_collapsed', '1']]);
let keydownHandler = null;
const kbd = {textContent: ''};
const ctx = vm.createContext({
  document: {
    body: {classList: bodyClassList},
    getElementById: id => els[id] || makeEl(),
    addEventListener: (ev, fn) => { if (ev === 'keydown') keydownHandler = fn; },
    querySelector: sel => sel === '.nav-search kbd' ? kbd : null,
  },
  window: {innerWidth: 1200},
  matchMedia: q => ({matches: ctx.window.innerWidth >= 850}),
  navigator: {platform: 'Win32'},
  localStorage: {
    getItem: k => store.has(k) ? store.get(k) : null,
    setItem: (k, v) => store.set(k, String(v)),
  },
  drawRooms: () => {},
});
vm.runInContext(part, ctx);
assert.equal(bodyClassList.contains('nav-collapsed'), true, 'restores collapsed sidebar on desktop');
assert.equal(els.rooms.inert, true);
assert.equal(els.navToggle.attributes['aria-expanded'], 'false');
els.navToggle.onclick();
assert.equal(bodyClassList.contains('nav-collapsed'), false);
assert.equal(els.rooms.inert, false);
assert.equal(store.get('any_nav_collapsed'), '0');
assert.equal(els.navToggle.attributes['aria-expanded'], 'true');
els.navClose.onclick();
assert.equal(bodyClassList.contains('nav-collapsed'), true);
assert.equal(els.rooms.inert, true);
assert.equal(store.get('any_nav_collapsed'), '1');
keydownHandler({ctrlKey: true, key: 'k', preventDefault(){}});
assert.equal(bodyClassList.contains('nav-collapsed'), false, 'Ctrl+K expands collapsed desktop sidebar');
ctx.window.innerWidth = 640;
els.navToggle.onclick();
assert.equal(bodyClassList.contains('nav-open'), true);
els.navClose.onclick();
assert.equal(bodyClassList.contains('nav-open'), false);
'''
        result = subprocess.run(['node', '-e', script], cwd=root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ContextUsageExtractionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.rooms = []
        self.registered = []

    def tearDown(self):
        for r in self.rooms:
            R.rooms.unload(r.id)
        for aid in self.registered:
            registry.remove_agent(aid)

    def _new_room(self, participants):
        r = R.rooms.create('ctx test', '', support.DATA, participants=participants)
        self.rooms.append(r)
        return r

    def _add_agent(self, raw):
        registry.save_agent(raw)
        self.registered.append(raw['id'])

    def test_cli_ndjson_json_and_text_real_token_extraction(self):
        # 1) OpenCode NDJSON usage
        opencode_spec = _load_preset(self.root, 'opencode')
        res = {}
        ndjson = '\n'.join([
            json.dumps({'type': 'text', 'sessionID': 'ses_oc1', 'part': {'text': 'hello'}}),
            json.dumps({'type': 'step_finish', 'sessionID': 'ses_oc1',
                        'part': {'tokens': {'input': 800, 'output': 150, 'cache': {'read': 250, 'write': 50}}}}),
        ])
        text, sess = drivers._parse(opencode_spec, ndjson, res)
        self.assertEqual(text, 'hello')
        self.assertEqual(sess, 'ses_oc1')
        self.assertEqual(res.get('ctx_used'), 1250)

        # 2) Antigravity / Claude-like NDJSON with modelUsage contextWindow
        agy_spec = _load_preset(self.root, 'antigravity')
        res2 = {}
        ndjson2 = '\n'.join([
            json.dumps({'type': 'assistant', 'session_id': 'ses_agy',
                        'message': {'usage': {'input_tokens': 1000, 'cache_read_input_tokens': 500, 'output_tokens': 200},
                                    'content': [{'type': 'text', 'text': 'hi'}]}}),
            json.dumps({'type': 'result', 'session_id': 'ses_agy', 'result': 'hi',
                        'modelUsage': {'m': {'inputTokens': 1000, 'cacheReadInputTokens': 500, 'contextWindow': 200000}}}),
        ])
        drivers._parse(agy_spec, ndjson2, res2)
        self.assertEqual(res2.get('ctx_used'), 1700)
        self.assertEqual(res2.get('ctx_win'), 200000)

        # 3) Gemini JSON stats
        gem_spec = _load_preset(self.root, 'gemini')
        res3 = {}
        gem_json = json.dumps({
            'response': 'gemini reply',
            'stats': {'models': {'gemini-2.5-pro': {'tokens': {'prompt': 3000, 'candidates': 400, 'total': 3400, 'cached': 500}}}},
        })
        t3, _ = drivers._parse(gem_spec, gem_json, res3)
        self.assertEqual(t3, 'gemini reply')
        self.assertEqual(res3.get('ctx_used'), 3400)

        # 4) Plain text CLI returns no token info -> never estimates
        aider_spec = _load_preset(self.root, 'aider')
        res4 = {}
        t4, _ = drivers._parse(aider_spec, 'plain stdout reply without tokens', res4)
        self.assertEqual(t4, 'plain stdout reply without tokens')
        self.assertEqual(res4, {})

    def test_http_extracts_real_usage_and_ignores_missing(self):
        spec = {'id': 'myhttp', 'driver': 'http', 'endpoint': 'http://127.0.0.1:9999/chat', 'default': ['', '']}
        r = self._new_room(['claude'])
        with patch('urllib.request.urlopen', return_value=_DummyResp(json.dumps({
            'text': 'ok', 'session': 'hs1', 'usage': {'input_tokens': 1200, 'output_tokens': 300}, 'context_window': 128000,
        }).encode())):
            ok, text, sess, _ = drivers.call_http('claude', spec, 'hi', None, (), 'discuss', r)
        self.assertTrue(ok)
        self.assertEqual(text, 'ok')
        self.assertEqual(sess, 'hs1')
        self.assertEqual(r.last_ctx['claude']['used'], 1500)
        self.assertEqual(r.last_ctx['claude']['window'], 128000)

        # Without usage: does not fabricate or overwrite with estimation
        r2 = self._new_room(['claude'])
        with patch('urllib.request.urlopen', return_value=_DummyResp(json.dumps({'text': 'no usage'}).encode())):
            ok, _, _, _ = drivers.call_http('claude', spec, 'hi', None, (), 'discuss', r2)
        self.assertTrue(ok)
        self.assertNotIn('claude', r2.last_ctx)

    def test_acp_extracts_usage_update_and_auto_caches_config_options(self):
        self._add_agent({
            'id': 'myacp', 'label': 'MyACP', 'driver': 'acp', 'bin': ['python'],
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        r = self._new_room(['claude'])
        proc = object.__new__(acp.AcpProcess)
        proc.pid = 'myacp'
        proc.cwd = r.workdir()
        proc.lock = threading.RLock()
        proc.last_used = 0
        proc.active_room = r
        proc.active_mode = 'discuss'
        proc.active_edits = []
        proc.session_id = 'acp-s1'
        proc.applied = None
        proc.config_options = []
        proc.request_caps = {'loadSession': False}

        def fake_request(method, params, timeout=60, on_note=None):
            if method == 'session/new':
                return {
                    'sessionId': 'acp-s1',
                    'configOptions': [
                        {'id': 'model', 'category': 'model', 'options': [{'value': 'm-alpha'}, {'value': 'm-beta'}]},
                        {'id': 'effort', 'category': 'thought_level', 'options': [{'value': 'low'}, {'value': 'high'}]},
                    ],
                }
            if method == 'session/set_config_option':
                return {}
            if method == 'session/prompt':
                on_note({'method': 'session/update', 'params': {'update': {'sessionUpdate': 'usage_update', 'used': 4200, 'size': 200000}}})
                on_note({'method': 'session/update', 'params': {'update': {'sessionUpdate': 'agent_message_chunk', 'content': {'text': 'acp ok'}}}})
                return {'stopReason': 'end_turn'}
            return {}

        proc.request = fake_request
        reply, sid, _ = proc.prompt('hello', [], 'discuss', r)
        self.assertEqual(reply, 'acp ok')
        self.assertEqual(sid, 'acp-s1')
        self.assertEqual(r.last_ctx['myacp']['used'], 4200)
        self.assertEqual(r.last_ctx['myacp']['window'], 200000)
        cap = model_catalog.capabilities(r, 'myacp')
        self.assertTrue(cap['model_supported'])
        self.assertEqual(cap['models'], ['m-alpha', 'm-beta'])
        self.assertTrue(cap['effort_supported'])

    def test_external_member_reports_real_ctx(self):
        self._add_agent({
            'id': 'ext1', 'label': 'Ext1', 'driver': 'external',
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        broker = members.Broker()
        r = self._new_room(['claude'])
        self.assertEqual(r.set_participants(['ext1']), (True, ''))
        key = access.credential('ext1')
        with patch.object(members, 'broker', broker):
            broker.register('ext1', key, {'worker': 'w1', 'workdir': r.workdir(), 'allow_work': False})
            out = {}
            t = threading.Thread(target=lambda: out.setdefault('res', broker.call('ext1', 'hi', None, 'discuss', r)))
            t.start()
            deadline = time.time() + 5
            task = None
            while time.time() < deadline:
                poll = broker.receive('ext1', key, {'worker': 'w1', 'timeout': 0})
                if poll.get('task'):
                    task = poll['task']
                    break
                time.sleep(0.05)
            self.assertIsNotNone(task, f"ext task missing, out={out}")
            broker.complete('ext1', key, {
                'task': task['id'], 'worker': 'w1', 'lease': task['lease'],
                'ok': True, 'text': 'ext reply', 'session': 'es1',
                'usage': {'prompt_tokens': 900, 'completion_tokens': 100}, 'context_window': 64000,
            })
            t.join(timeout=5)
        self.assertEqual(out['res'], (True, 'ext reply', 'es1', []))
        self.assertEqual(r.last_ctx['ext1']['used'], 1000)
        self.assertEqual(r.last_ctx['ext1']['window'], 64000)


class ModelParityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.registered = []

    def tearDown(self):
        for aid in self.registered:
            registry.remove_agent(aid)

    def _add_agent(self, raw):
        registry.save_agent(raw)
        self.registered.append(raw['id'])

    def test_remote_drivers_and_aider_preset_support_model_settings(self):
        aider_raw = json.loads((self.root / 'bridge' / 'presets' / 'aider.json').read_text(encoding='utf-8'))
        aider_raw['enabled'] = True
        aider_raw['bin'] = ['python']
        self._add_agent(aider_raw)
        aider_cap = agents.model_capabilities('aider')
        self.assertTrue(aider_cap['model_supported'])

        self._add_agent({
            'id': 'r_http', 'label': 'RHTTP', 'driver': 'http', 'endpoint': 'http://127.0.0.1:9999/h',
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        self._add_agent({
            'id': 'r_ext', 'label': 'REXT', 'driver': 'external',
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        for aid in ('r_http', 'r_ext'):
            cap = agents.model_capabilities(aid)
            self.assertTrue(cap['model_supported'], aid)
            self.assertTrue(cap['effort_supported'], aid)
            self.assertEqual(cap['efforts_by_model'][''], ['low', 'medium', 'high'])

    def test_parse_cli_models_filters_noise(self):
        raw = '\x1b[32mAvailable models:\x1b[0m\nopenai/gpt-5\nanthropic/claude-sonnet-4-5 - default\n--- divider ---\n'
        self.assertEqual(model_catalog._parse_cli_models(raw), ['openai/gpt-5', 'anthropic/claude-sonnet-4-5'])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to test model-settings refresh UI')
    def test_model_refresh_rerenders_controls_when_model_becomes_supported(self):
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const ms = fs.readFileSync('static/model-settings.js', 'utf8');
let info = {model_supported: false, effort_supported: false, models: [], efforts: [], efforts_by_model: {}, model: '', effort: '', default_model: '', default_effort: '', label: '未设置'};
let currentMarkup = '';
const mounted = {};
function makeFakeBox() {
  return {
    parentNode: {id: 'modalBody'},
    set outerHTML(html) {
      currentMarkup = html;
      mounted.box = makeFakeBox();
      mounted.mModelChoice = {value: '', disabled: false, onchange: null};
      mounted.mModel = {value: '', disabled: false, oninput: null};
      mounted.mCustomModel = {hidden: true};
      mounted.mEffort = {value: '', disabled: false, innerHTML: '', onchange: null};
      mounted.mEffortHint = {textContent: ''};
      mounted.mSave = {disabled: true, onclick: null};
      mounted.mReset = {disabled: false, onclick: null};
      mounted.mHint = {textContent: ''};
      mounted.mCurrent = {textContent: ''};
      mounted.mApplyStatus = {textContent: ''};
      mounted.mCatalogStatus = {textContent: ''};
      mounted.mRefreshCatalog = {disabled: false, onclick: null};
    },
  };
}
mounted.box = makeFakeBox();
mounted.mRefreshCatalog = {disabled: false, onclick: null};
mounted.mCatalogStatus = {textContent: ''};
const ctx = vm.createContext({
  RID: 'r1',
  S: {ais: {myacp: {model: info}}},
  api: k => '/api/r/r1/' + k,
  esc: s => String(s),
  post: async () => [true, {model: {model_supported: true, effort_supported: true, models: ['m-new'], efforts_by_model: {'': ['low', 'high'], 'm-new': ['low', 'high']}, source: 'ACP 会话声明'}}],
  loadState: async () => {},
  document: {
    getElementById: id => id === 'modelSettings' ? mounted.box : mounted[id],
  },
});
vm.runInContext(ms, ctx);
currentMarkup = ctx.modelSettingsMarkup(info, false);
assert.doesNotMatch(currentMarkup, /id="mModelChoice"/);
ctx.bindModelSettings('myacp', info, false);
(async () => {
  await mounted.mRefreshCatalog.onclick();
  assert.match(currentMarkup, /id="mModelChoice"/);
  assert.match(currentMarkup, /m-new/);
  assert.equal(typeof mounted.mModelChoice.onchange, 'function');
  assert.equal(typeof mounted.mSave.onclick, 'function');
})().catch(e => { console.error(e); process.exitCode = 1; });
'''
        result = subprocess.run(['node', '-e', script], cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class AllAgentCompactionTests(unittest.TestCase):
    def setUp(self):
        self.rooms = []
        self.registered = []
        self.orig_caller = R.ai_caller
        self.orig_compact = R.ai_native_compact

    def tearDown(self):
        R.ai_caller = self.orig_caller
        R.ai_native_compact = self.orig_compact
        for r in self.rooms:
            R.rooms.unload(r.id)
        for aid in self.registered:
            registry.remove_agent(aid)

    def _add_agent(self, raw):
        registry.save_agent(raw)
        self.registered.append(raw['id'])

    def test_full_context_agent_compacts_via_checkpoint_and_reuses_summary(self):
        self._add_agent({
            'id': 'fullcli', 'label': 'FullCLI', 'driver': 'cli', 'bin': ['python'],
            'context': 'full', 'args': {'new': ['-c', 'print(1)', '{prompt}']},
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        r = R.rooms.create('full compact', 'finish v1', support.DATA, participants=['claude'])
        self.rooms.append(r)
        self.assertEqual(r.set_participants(['fullcli']), (True, ''))
        r.add_message('你', '第一条需求')
        r.add_message('fullcli', '明白第一条')
        st0 = r.api_state()['ais']['fullcli']
        self.assertTrue(st0['can_compact'])

        calls = []

        def fake_caller(ai, prompt, sid, images, mode, room):
            calls.append((ai, prompt, sid))
            room.note_ctx(ai, {'ctx_used': 512, 'ctx_win': 1000000})
            return True, '要点：确定了第一条需求。', None, []

        R.ai_caller = fake_caller
        R.ai_native_compact = lambda ai, sid, room=None: False
        msg = r.compact_one('fullcli')
        self.assertIn('摘要检查点', msg)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0][2])
        self.assertEqual(r.meta['compact_checkpoints']['fullcli']['summary'], '要点：确定了第一条需求。')
        self.assertEqual(r.meta['ctx']['fullcli']['used'], 512)
        self.assertEqual(r.meta['ctx']['fullcli']['window'], 1000000)

        self.assertFalse(r.api_state()['ais']['fullcli']['can_compact'])
        r.add_message('你', '第二条新指令')
        self.assertTrue(r.api_state()['ais']['fullcli']['can_compact'])
        prompt, _, _, _ = r.build_prompt('fullcli')
        self.assertIn('此前会议摘要：\n要点：确定了第一条需求。', prompt)
        self.assertIn('第二条新指令', prompt)
        self.assertNotIn('[你] 第一条需求', prompt)

    def test_stateless_http_fallback_to_checkpoint_when_no_new_sid(self):
        self._add_agent({
            'id': 'h1', 'label': 'HTTP1', 'driver': 'http', 'endpoint': 'http://127.0.0.1:9999/h',
            'context': 'delta', 'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        r = R.rooms.create('http compact', 'goal', support.DATA, participants=['claude'])
        self.rooms.append(r)
        self.assertEqual(r.set_participants(['h1']), (True, ''))
        r.meta['h1_session'] = 'old-http-sid'
        r.add_message('你', '讨论 A')
        seq = [
            (True, '摘要内容 A', 'old-http-sid', []),
            (True, '收到', None, []),
        ]
        R.ai_caller = lambda *args: seq.pop(0)
        R.ai_native_compact = lambda ai, sid, room=None: False
        res = r.compact_one('h1')
        self.assertIn('摘要检查点', res)
        self.assertIsNone(r.meta.get('h1_session'))
        self.assertEqual(r.meta['old_sessions']['h1'], ['old-http-sid'])
        self.assertEqual(r.meta['compact_checkpoints']['h1']['summary'], '摘要内容 A')

    def test_acp_compacts_via_summary_and_new_session_and_user_skips(self):
        self._add_agent({
            'id': 'acp_c', 'label': 'ACPC', 'driver': 'acp', 'bin': ['python'],
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        self._add_agent({
            'id': 'alice', 'label': 'Alice', 'driver': 'external', 'kind': 'user',
            'models': [], 'efforts': [], 'default': ['', ''], 'caps': {}, 'enabled': True,
        })
        r = R.rooms.create('acp compact', 'ship parity', support.DATA, participants=['claude'])
        self.rooms.append(r)
        self.assertEqual(r.set_participants(['acp_c', 'alice']), (True, ''))
        r.meta['acp_c_session'] = 'acp-s1'
        r.add_message('你', '同步需求')
        self.assertTrue(r.api_state()['ais']['acp_c']['can_compact'])
        self.assertFalse(r.api_state()['ais']['alice']['can_compact'])
        self.assertIn('人工联系人', r.compact_one('alice'))

        seen = []

        def fake_caller(ai, prompt, sid, images, mode, room):
            seen.append((ai, prompt, sid))
            if len(seen) == 1:
                return True, 'ACP 阶段摘要', 'acp-s1', []
            return True, '收到', 'acp-s2', []

        R.ai_caller = fake_caller
        R.ai_native_compact = lambda ai, sid, room=None: False
        msg = r.compact_one('acp_c')
        self.assertIn('续接（摘要 + 新会话）', msg)
        self.assertEqual(r.meta['acp_c_session'], 'acp-s2')
        self.assertEqual(r.meta['old_sessions']['acp_c'], ['acp-s1'])
        self.assertEqual(seen[0][2], 'acp-s1')
        self.assertIsNone(seen[1][2])
        self.assertIn('【AnY】你是 @acp_c', seen[1][1])
        self.assertIn('ACP 阶段摘要', seen[1][1])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to test openAi modal')
    def test_open_ai_modal_excludes_compact_and_session_tools(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const appMeeting = fs.readFileSync('static/app-meeting.js', 'utf8');
const start = appMeeting.indexOf('function openAi(');
const end = appMeeting.indexOf("\ndocument.getElementById('bList')", start);
const part = appMeeting.slice(start, end);
let modalHtml = '';
const els = {aClose: {}};
const ctx = vm.createContext({
  S: {
    participants: ['gemini'],
    running: [],
    queued: 0,
    execution: {gemini: {endpoint: 'cli'}},
    ais: {
      gemini: {
        session: false,
        handed_off: false,
        busy: false,
        compacting: false,
        can_compact: true,
        compact_at: '',
        handoff: false,
        caps: {tools: true},
        model: {models: ['gemini-2.5-pro'], model: '', effort: ''},
        ctx: {used: 3400, window: 1000000},
      },
    },
  },
  CONTACTS: [{id: 'gemini', label: 'Gemini', driver: 'cli'}],
  agentMeta: id => ({id, driver: 'cli'}),
  esc: s => String(s),
  fmtK: n => String(n),
  modelSettingsMarkup: () => '<div id="modelSettings"></div>',
  executionSettingsMarkup: () => '<div></div>',
  showModal: html => { modalHtml = html; },
  hideModal: () => {},
  bindModelSettings: () => {},
  bindExecutionSettings: () => {},
  loadTools: () => { throw new Error('openAi must not render or load tools'); },
  api: k => k,
  post: async () => [true, {}],
  loadState: async () => {},
  poll: () => {},
  confirm: () => true,
  document: {getElementById: id => els[id] || {}},
});
vm.runInContext(part, ctx);
ctx.openAi('gemini');
assert.doesNotMatch(modalHtml, /压缩上下文/);
assert.doesNotMatch(modalHtml, /id="aCompact"/);
assert.doesNotMatch(modalHtml, /id="toolsBox"/);
assert.doesNotMatch(modalHtml, /会话与终端/);
assert.match(modalHtml, /id="modelSettings"/);
assert.match(modalHtml, /id="aClose"/);
'''
        result = subprocess.run(['node', '-e', script], cwd=root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class MemberPermissionsAndStatusSeparationTests(unittest.TestCase):
    def test_single_meeting_entry_and_composer_model_controls(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('id="sideToggleBtn"'), 1)
        self.assertNotIn('id="caps"', html)
        self.assertNotIn('id="menu"', html)
        side = html[html.index('<aside id="side"'):html.index('</aside>')]
        for action in ('bRename', 'bAgents', 'bWrap'):
            self.assertIn(f'id="{action}"', side)
        self.assertGreater(html.index('id="composerModelBtn"'), html.index('<footer>'))

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to test openAgents bulk permissions')
    def test_consolidated_permissions_and_one_click_bulk_toggle(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const ws = fs.readFileSync('static/workspace.js', 'utf8');
const permsPart = ws.slice(ws.indexOf('const PERM_LABELS='), ws.indexOf('let contactsRequestSequence='));
const openAgentsStart = ws.indexOf('function memberPermissionRow(');
const openAgentsEnd = ws.indexOf("document.getElementById('contactsAdd')", openAgentsStart);
const openAgentsPart = ws.slice(openAgentsStart, openAgentsEnd);

const makeClassList = () => {
  const set = new Set();
  return {
    toggle: (k, force) => { if (force === undefined) force = !set.has(k); if (force) set.add(k); else set.delete(k); return force; },
    contains: k => set.has(k),
  };
};
function parseOpenAgents(html) {
  const rows = [];
  const rowRe = /<section class="member-row" data-member="([^"]+)" data-permissions="([^"]*)">([\s\S]*?)<\/section>/g;
  let m;
  while ((m = rowRe.exec(html))) {
    const id = m[1], initialPermissions = m[2].replace(/&quot;/g, '"'), inner = m[3];
    const memberCheck = {checked: /data-member-check[^>]* checked/.test(inner), onchange: null};
    const perms = {};
    for (const g of ['chat', 'collab', 'work']) {
      const reg = new RegExp('data-perm-group="' + g + '"([^>]*)>');
      const pm = inner.match(reg);
      perms[g] = {checked: !!(pm && /checked/.test(pm[1])), disabled: false, dataset: {permGroup: g}, onchange: null};
    }
    rows.push({
      dataset: {member: id, permissions: initialPermissions},
      memberCheck,
      perms,
      querySelector: sel => sel === '[data-member-check]' ? memberCheck : perms[sel.match(/data-perm-group="([^"]+)"/)[1]],
      querySelectorAll: sel => sel === '[data-perm-group]' ? Object.values(perms) : [],
    });
  }
  const bulk = {};
  for (const g of ['chat', 'collab', 'work']) {
    bulk[g] = {dataset: {permAll: g}, disabled: false, textContent: '', attrs: {}, classList: makeClassList(), setAttribute(k, v){ this.attrs[k] = v; }, onclick: null};
  }
  const mMembersAll = {disabled: false, textContent: '', attrs: {}, classList: makeClassList(), setAttribute(k, v){ this.attrs[k] = v; }, onclick: null};
  const mClose = {onclick: null}, mSave = {onclick: null};
  return {rows, bulk, mMembersAll, mClose, mSave};
}

let dom = null, posted = null;
const mbox = {
  querySelectorAll: sel => {
    if (sel === '[data-member]') return dom.rows;
    if (sel === '[data-perm-all]') return Object.values(dom.bulk);
    return [];
  },
  querySelector: sel => {
    const gm = sel.match(/^\[data-perm-all="([^"]+)"\]$/);
    return gm ? dom.bulk[gm[1]] : null;
  },
};
const ctx = vm.createContext({
  RID: 'r1',
  contactMode: 'global',
  CONTACTS: [
    {id: 'claude', label: 'Claude', enabled: true},
    {id: 'codex', label: 'Codex', enabled: true},
    {id: 'gemini', label: 'Gemini', enabled: true},
  ],
  S: {
    participants: ['claude', 'codex'],
    permissions: {
      claude: {read: true, post: true, trigger: true, board: false, files: false, work: false},
      codex: {read: true, post: true, trigger: true, board: true, files: false, work: false},
    },
  },
  mbox,
  esc: s => String(s).replace(/"/g, '&quot;'),
  refreshContacts: async () => {},
  showModal: html => { dom = parseOpenAgents(html); },
  hideModal: () => {},
  post: async (url, body) => { posted = {url, body}; return [true, {}]; },
  loadState: async () => {},
  alert: msg => { throw new Error(msg); },
  document: {
    getElementById: id => id === 'mMembersAll' ? dom.mMembersAll : id === 'mClose' ? dom.mClose : id === 'mSave' ? dom.mSave : null,
  },
});
vm.runInContext(permsPart + '\n' + openAgentsPart, ctx);
(async () => {
  await ctx.openAgents();
  assert.equal(vm.runInContext('PERM_GROUPS.length', ctx), 3);
  // Only 3 permission checkboxes per member (no fragmented 6 checkboxes)
  assert.equal(dom.rows[0].querySelectorAll('[data-perm-group]').length, 3);
  assert.equal(dom.rows[2].perms.chat.disabled, true, 'uninvited gemini starts disabled');
  assert.equal(dom.bulk.chat.classList.contains('on'), true, 'chat starts on for all invited');
  assert.equal(dom.bulk.work.classList.contains('on'), false, 'work starts off');
  await dom.mSave.onclick();
  assert.equal(posted.body.permissions.codex.board, true);
  assert.equal(posted.body.permissions.codex.files, false, 'untouched grouped settings retain individual permissions');

  // One click turns work ON for all invited members (claude + codex), leaving uninvited gemini untouched/disabled
  dom.bulk.work.onclick();
  assert.equal(dom.rows[0].perms.work.checked, true);
  assert.equal(dom.rows[1].perms.work.checked, true);
  assert.equal(dom.bulk.work.classList.contains('on'), true);

  // Second click turns work OFF for all invited members
  dom.bulk.work.onclick();
  assert.equal(dom.rows[0].perms.work.checked, false);
  assert.equal(dom.rows[1].perms.work.checked, false);
  assert.equal(dom.bulk.work.classList.contains('on'), false);

  // One click invites all members, then bulk toggles collab ON for everyone
  dom.mMembersAll.onclick();
  assert.equal(dom.rows[2].memberCheck.checked, true);
  assert.equal(dom.rows[2].perms.chat.disabled, false);
  dom.bulk.collab.onclick();
  for (const row of dom.rows) assert.equal(row.perms.collab.checked, true);

  await dom.mSave.onclick();
  assert.equal(posted.url, '/api/r/r1/members');
  assert.deepEqual(JSON.parse(JSON.stringify(posted.body.participants)), ['claude', 'codex', 'gemini']);
  assert.equal(posted.body.permissions.codex.files, true, 'explicit bulk enable grants both permissions');
  assert.deepEqual(JSON.parse(JSON.stringify(posted.body.permissions.gemini)), {
    read: true, post: true, trigger: true, board: true, files: true, work: false,
  });
})().catch(e => { console.error(e); process.exitCode = 1; });
'''
        result = subprocess.run(['node', '-e', script], cwd=root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
