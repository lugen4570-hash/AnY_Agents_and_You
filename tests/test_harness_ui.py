"""Regression tests for M2/M3 Harness UI: layout hooks, theme/lang, target-aware model chip, slash skills, and extension rules."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node is required for frontend UI unit tests')
class HarnessUiTests(unittest.TestCase):
    def run_node(self, script):
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_index_html_has_harness_ui_mounts(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        for marker in (
            'href="/static/harness-ui.css"',
            'src="/static/harness-ui.js"',
            'id="openSettingsBtn"',
            'id="sideToggleBtn"',
            'id="sideTabs"',
            'data-side-tab="agents"',
            'data-side-tab="board"',
            'data-side-tab="output"',
            'id="sideAgentsPane"',
            'id="composerBar"',
            'id="composerModeBtn"',
            'id="composerModelBtn"',
            'id="composerExtBtn"',
            'id="composerPopover"',
            'id="slashMenu"',
            'class="sr-file-input"',
        ):
            self.assertIn(marker, html, f'Missing marker {marker} in index.html')
        self.assertNotIn('id="toolBox"', html)
        self.assertNotIn('data-inline-tools', (ROOT / 'static' / 'harness-ui.js').read_text(encoding='utf-8'))

    def test_agent_settings_fold_unconfigured_presets(self):
        self.run_node(r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const settings=fs.readFileSync('static/agent-settings.js','utf8');
const harness=fs.readFileSync('static/harness-ui.js','utf8');
const contacts=[
  {id:'codex',driver:'codex',enabled:true},
  {id:'uninstalled',driver:'cli',enabled:false},
  {id:'desktop',driver:'external',enabled:true},
  {id:'paired',driver:'external',enabled:true},
  {id:'manual',driver:'cli',enabled:false,user:true},
  {id:'configured',driver:'cli',enabled:false,configured:true},
  {id:'alice',kind:'user',driver:'external',enabled:true}
];
const ctx=vm.createContext({CONTACTS:contacts,agCat:{connections:{paired:{has_key:true}}},esc:String});
vm.runInContext(settings.slice(settings.indexOf('function groupAgentSettings'),settings.indexOf('async function openAgentManager')),ctx);
vm.runInContext(harness.slice(harness.indexOf('function renderAgentsTab'),harness.indexOf('function renderExtensionsContent')),ctx);
const html=ctx.renderAgentsTab(), [visible,folded]=html.split('<details');
for(const id of ['codex','paired','manual','configured'])assert.ok(visible.includes('data-settings-agent="'+id+'"'));
for(const id of ['uninstalled','desktop']){
  assert.ok(!visible.includes('data-settings-agent="'+id+'"'));
  assert.ok(folded.includes('data-settings-agent="'+id+'"'));
}
assert.ok(!html.includes('@alice'));
''')

    def test_codex_cli_plus_antigravity_desktop_model_chip_and_slash_skills(self):
        self.run_node(r'''
const assert = require('assert/strict');
const h = require('./static/harness-ui.js');

const state = {
  meeting: 'm1',
  mode: 'discuss',
  participants: ['codex', 'antigravity'],
  agents: [
    { id: 'codex', label: 'Codex', kind: 'ai' },
    { id: 'antigravity', label: 'Antigravity', kind: 'ai' },
  ],
  execution: {
    codex: { endpoint: 'cli' },
    antigravity: { endpoint: 'desktop' },
  },
  ais: {
    codex: {
      model: { label: 'gpt-5.4 · high', model: 'gpt-5.4', effort: 'high', apply_status: 'pending' },
    },
    antigravity: {
      model: { apply_status: 'read_only', model_supported: false, observed: { model: 'gemini-3-pro' } },
    },
  },
};

// 1. Broadcast (no @) shows Models (2)
const broadcast = h.buildModelChipState('hello team', state, state.agents);
assert.equal(broadcast.readonly, false);
assert.equal(broadcast.pending, true);
assert.match(broadcast.label, /2/);

// 2. Explicit @codex shows Codex model + pending state
const toCodex = h.buildModelChipState('@codex please check', state, state.agents);
assert.equal(toCodex.readonly, false);
assert.equal(toCodex.pending, true);
assert.equal(toCodex.label, 'Codex · gpt-5.4 · high');

// 3. Explicit @antigravity (desktop) shows read-only reported model
const toAgy = h.buildModelChipState('@antigravity review this', state, state.agents);
assert.equal(toAgy.readonly, true);
assert.equal(toAgy.label, 'Antigravity · gemini-3-pro');

// 4. Desktop with no reported model falls back to "由桌面端管理"
const stateNoObs = JSON.parse(JSON.stringify(state));
stateNoObs.ais.antigravity.model.observed = null;
const toAgyUnknown = h.buildModelChipState('@antigravity hi', stateNoObs, state.agents);
assert.equal(toAgyUnknown.readonly, true);
assert.match(toAgyUnknown.label, /由桌面端管理/);

// 5. Slash skills: @codex /deb -> lists Codex enabled skills only
const toolsByAi = {
  codex: {
    skills: [
      { name: 'systematic-debugging', desc: 'debug root cause', on: true },
      { name: 'disabled-skill', desc: 'off', on: false },
    ],
  },
};
const codexSlash = h.filterSlashSkills('@codex /deb', 11, state, toolsByAi, state.agents);
assert.equal(codexSlash.desktopOnly, false);
assert.equal(codexSlash.items.length, 1);
assert.equal(codexSlash.items[0].name, 'systematic-debugging');

// 6. Slash skills: @antigravity / -> desktop notice, no fake skills
const agySlash = h.filterSlashSkills('@antigravity /', 14, state, toolsByAi, state.agents);
assert.equal(agySlash.desktopOnly, true);
assert.equal(agySlash.items.length, 0);
assert.match(agySlash.notice, /技能由原软件管理/);

// 7. Slash skills: broadcast / -> lists codex skill + desktop note; selecting prepends @codex
const broadcastSlash = h.filterSlashSkills('/sys', 4, state, toolsByAi, state.agents);
assert.equal(broadcastSlash.items.length, 1);
assert.deepEqual(broadcastSlash.items[0].agentIds, ['codex']);
assert.match(broadcastSlash.notice, /Antigravity/);
const picked = h.applySlashSelection('/sys', broadcastSlash.slash, broadcastSlash.items[0], broadcastSlash.target);
assert.equal(picked.text, '@codex /systematic-debugging ');
assert.deepEqual(picked.recipientIds, ['codex']);

// 8. Explicit recipient is preserved when selecting a skill
const explicitPicked = h.applySlashSelection('@codex /deb', codexSlash.slash, codexSlash.items[0], codexSlash.target);
assert.equal(explicitPicked.text, '@codex /systematic-debugging ');
assert.deepEqual(explicitPicked.recipientIds, ['codex']);

// 9. Work mode with codex work:false flags blockedWorkTargets
const workState = Object.assign({}, state, {
  mode: 'work',
  permissions: { codex: { work: false }, antigravity: { work: true } },
});
assert.deepEqual(h.blockedWorkTargets(workState, h.resolveComposerTarget('@codex hi', workState)), ['codex']);
assert.deepEqual(h.blockedWorkTargets(workState, h.resolveComposerTarget('@antigravity hi', workState)), []);

// 10. Built-in slash commands (/compact, /skills) filter & parse cleanly
const cmdAll = h.filterSlashCommands('/', 1, state, state.agents);
assert.deepEqual(cmdAll.items.map(i => i.name), ['compact', 'skills']);
const cmdComp = h.filterSlashCommands('/com', 4, state, state.agents);
assert.deepEqual(cmdComp.items.map(i => i.name), ['compact']);
assert.deepEqual(h.parseComposerSlashCommand('/compact', state), { command: 'compact', targetIds: [], explicitTarget: false, error: '' });
assert.deepEqual(h.parseComposerSlashCommand('@codex /compact', state), { command: 'compact', targetIds: ['codex'], explicitTarget: true, error: '' });
assert.deepEqual(h.parseComposerSlashCommand('/compact codex', state), { command: 'compact', targetIds: ['codex'], explicitTarget: true, error: '' });
assert.deepEqual(h.parseComposerSlashCommand('/skills codex', state), { command: 'skills', targetIds: ['codex'], explicitTarget: true, error: '' });
assert.equal(h.parseComposerSlashCommand('/systematic-debugging check', state), null);
''')

    def test_extensions_badges_tristate_and_import_validation(self):
        self.run_node(r'''
const assert = require('assert/strict');
const h = require('./static/harness-ui.js');

// default_on omitted => unknown (no default on/off badge)
const unknown = h.classifyExtensionBadges({ id: 'a', scope: 'user' });
assert.equal(unknown.some(b => /默认/.test(b.label)), false);

// default_on === false => 默认关闭
const off = h.classifyExtensionBadges({ id: 'b', scope: 'project', default_on: false });
assert.ok(off.some(b => b.label === '默认关闭'));
assert.ok(off.some(b => b.label === '项目'));

// host_managed => 由原软件管理
const host = h.classifyExtensionBadges({ id: 'c', scope: 'host', tags: ['host_managed'], default_on: false });
assert.ok(host.some(b => b.label === '由原软件管理'));
assert.equal(host.some(b => b.label === '默认关闭'), false);

// user scope omits project_id
const userImp = h.validateImportPayload({ agent_id: 'codex', scope: 'user', project_id: 'p1', source_path: 'D:\\skills\\demo' });
assert.equal(userImp.ok, true);
assert.equal('project_id' in userImp.payload, false);

// project scope requires project_id
const badProj = h.validateImportPayload({ agent_id: 'codex', scope: 'project', project_id: '', source_path: 'D:\\skills\\demo' });
assert.equal(badProj.ok, false);
const okProj = h.validateImportPayload({ agent_id: 'codex', scope: 'project', project_id: 'p1', source_path: 'D:\\skills\\demo' });
assert.equal(okProj.ok, true);
assert.equal(okProj.payload.project_id, 'p1');
''')

    def test_theme_and_language_resolution(self):
        self.run_node(r'''
const assert = require('assert/strict');
const h = require('./static/harness-ui.js');
assert.equal(h.applyTheme('dark'), 'dark');
assert.equal(h.applyTheme('light'), 'light');
assert.equal(h.applyTheme('system'), 'system');
assert.equal(h.resolveLang('en'), 'en');
assert.equal(h.resolveLang('zh-CN'), 'zh-CN');
''')

    def test_native_permission_update_notice_and_work_mode_warning(self):
        import os, sys, tempfile

        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROUNDTABLE_DATA=tmp)
            script = r'''
import os, tempfile
from bridge import room as R

with tempfile.TemporaryDirectory() as wd:
    r = R.rooms.create('codex perm sync', '', wd, participants=['codex'])
    r.meta['codex_session'] = 'thread-1'
    r.meta.setdefault('permissions', {})['codex'] = {
        'read': True, 'post': True, 'trigger': True, 'board': False, 'files': False, 'work': False,
    }
    r.meta['instruction_seen'] = {'codex': r.instruction_signature('codex', 'discuss')}
    ok, msg = r.set_mode('work')
    assert ok, msg
    assert r.messages[-1]['text'] == '切到干活模式', r.messages[-1]['text']
    assert r.member_mode('codex') == 'discuss'

    ok, msg = r.set_members(['codex'], {'codex': {'work': True}})
    assert ok, msg
    assert r.messages[-1]['text'] == '已允许干活：codex'
    r.add_message('你', '@codex 开始改代码')
    prompt, _, _, _ = r.build_prompt('codex', r.member_mode('codex'))
    assert '【合拍模式与权限已更新】' in prompt, prompt
    assert '"work": true' in prompt, prompt
    assert '干活模式' in prompt, prompt
'''
            result = subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
