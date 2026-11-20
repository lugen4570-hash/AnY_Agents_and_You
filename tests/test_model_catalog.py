"""Indexes reflect endpoint capabilities and never equate saved preferences with applied settings."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import test_contacts_access as support
from bridge import agent_settings, agents, model_catalog, registry, room as R


class ModelCatalog(unittest.TestCase):
    def setUp(self):
        model_catalog.CACHE.clear()
        path=Path(support.DATA,'agent_settings.json')
        if path.exists():path.unlink()
        registry.load()
        agent_settings.save('codex',{'bin':[sys.executable]},agent_settings.view('codex')['revision'])
        self.r=R.rooms.create('indexed models','',support.DATA,participants=['codex'])
        self.addCleanup(R.rooms.unload,self.r.id)

    def test_codex_refresh_pages_preserves_empty_efforts_and_source(self):
        server=Mock()
        server.request.side_effect=[{'data':[{'model':'indexed-fast','supportedReasoningEfforts':[]}],'nextCursor':'next'},
                                    {'data':[{'model':'indexed-reasoning','supportedReasoningEfforts':[{'reasoningEffort':'high'}]}]}]
        with patch.object(agents,'codex_launch',return_value=(['fake'],{})),patch.object(agents,'CodexServer',return_value=server):
            result=model_catalog.refresh(self.r,'codex')
        self.assertIn('indexed-fast',result['models'])
        self.assertEqual(result['efforts_by_model']['indexed-fast'],[])
        self.assertEqual(result['efforts_by_model']['indexed-reasoning'],['high'])
        self.assertEqual(result['source'],'Codex model/list')
        self.assertFalse(self.r.set_models('codex','indexed-fast','high')[0])
        self.assertTrue(self.r.set_models('codex','indexed-reasoning','high')[0])
        server.stop.assert_called_once()

    def test_refresh_failure_retains_index_with_stale_marker(self):
        key=model_catalog._key('codex')
        model_catalog.CACHE[key]={'models':['kept-model'],'efforts_by_model':{'kept-model':['low']},'source':'previous','checked_at':1}
        with patch.object(agents,'codex_launch',side_effect=RuntimeError('offline')):
            result=model_catalog.refresh(self.r,'codex')
        self.assertIn('kept-model',result['models'])
        self.assertTrue(result['stale']);self.assertIn('offline',result['error'])

    def test_last_index_survives_backend_cache_restart(self):
        server=Mock()
        server.request.return_value={'data':[{'model':'persisted-model','supportedReasoningEfforts':[]}]}
        with patch.object(agents,'codex_launch',return_value=(['fake'],{})),patch.object(agents,'CodexServer',return_value=server):
            model_catalog.refresh(self.r,'codex')
        model_catalog.CACHE.clear()
        self.assertIn('persisted-model',model_catalog.capabilities(self.r,'codex')['models'])

    def test_busy_refresh_does_not_start_a_process(self):
        self.r.state['running'].append('codex')
        try:
            with patch.object(agents,'CodexServer') as server:
                with self.assertRaisesRegex(ValueError,'正在运行'):
                    model_catalog.refresh(self.r,'codex')
            server.assert_not_called()
        finally:self.r.state['running'].clear()

    def test_saved_requested_settings_wait_for_actual_acceptance(self):
        self.assertTrue(self.r.set_models('codex','test-model','high')[0])
        state=self.r.model_info('codex')
        self.assertEqual(state['apply_status'],'pending');self.assertIsNone(state['accepted'])
        revision=model_catalog.request_id(self.r,'codex')
        model_catalog.accepted(self.r,'codex',revision,'fake protocol acknowledgement')
        state=self.r.model_info('codex')
        self.assertEqual(state['apply_status'],'applied')
        self.assertEqual(state['accepted']['model'],'test-model')
        self.assertIsNone(state['observed'])
        self.r.set_models('codex','different-model','low')
        model_catalog.accepted(self.r,'codex',revision,'stale acknowledgement')
        self.assertEqual(self.r.model_info('codex')['apply_status'],'pending')

    def test_config_rejection_is_reported_as_failure(self):
        self.r.set_models('codex','test-model','high')
        revision=model_catalog.request_id(self.r,'codex')
        model_catalog.result(self.r,'codex',revision,False,'unsupported model: test-model','')
        state=self.r.model_info('codex')
        self.assertEqual(state['apply_status'],'failed')
        self.assertIn('unsupported',state['apply_error'])

    def test_acp_index_comes_from_real_declared_config_options(self):
        from bridge import acp
        registry.save_agent({'id':'index-acp','driver':'acp','bin':[sys.executable],'args':{'acp':['fake']}})
        self.r.set_members(['codex','index-acp'],{'codex':{},'index-acp':{}})
        process=Mock()
        process.config_options=[{'id':'model-choice','category':'model','options':[{'name':'group','options':[{'value':'vendor/model'}]}]},
                                {'id':'thinking','category':'thought_level','options':[{'value':'low'},{'value':'high'}]}]
        with patch.object(acp,'AcpProcess',return_value=process):
            result=model_catalog.refresh(self.r,'index-acp')
        self.assertTrue(result['model_supported']);self.assertTrue(result['effort_supported'])
        self.assertIn('vendor/model',result['models'])
        self.assertEqual(result['efforts_by_model']['vendor/model'],['low','high'])
        self.assertTrue(self.r.set_models('index-acp','vendor/model','high')[0])
        process.close.assert_called_once()

    def test_index_routes_require_owner_authentication(self):
        path='/api/r/'+support.quote(self.r.id)+'/models/catalog?ai=codex'
        self.assertEqual(support.call(path)[0],403)
        self.assertEqual(support.call(path,owner=True)[0],200)

    def test_antigravity_and_cursor_collapse_effort_variants(self):
        import tempfile
        from types import SimpleNamespace
        agy_out = '\n'.join([
            'Available models:',
            'gemini-4-argon-medium',
            'gemini-4-argon-high',
            'gemini-4-argon-low',
            'gemini-4-hydrogen-high',
            'gemini-4-hydrogen-xhigh',
            'gemini-4-hydrogen-medium',
            'gemini-4-hydrogen-low',
            'gemini-pro-orchestrator-g1-pro - Orchestrator (Argon)',
            'gemini-3.8-flash-high',
            'gemini-3.8-flash-medium',
            'gemini-3.8-flash-low',
            'claude-opus-5-5-low',
            'claude-opus-5-5-medium',
            'claude-opus-5-5-high',
            'claude-sonnet-5-5-low',
            'claude-sonnet-5-5-medium',
            'claude-sonnet-5-5-high',
            'gpt-oss-120b-medium',
        ])
        cur_out = '\n'.join([
            'gpt-5.5-low - GPT 5.5',
            'gpt-5.5-medium',
            'gpt-5.5-high',
            'gpt-5.5-extra-high',
            'gpt-5.5-fast-low',
            'gpt-5.5-fast-high',
            'claude-4.6-sonnet-medium',
        ])
        with tempfile.TemporaryDirectory() as tmp:
            presets = Path(__file__).resolve().parents[1] / 'bridge' / 'presets'
            with patch.object(agents, 'CURSOR_HOME', Path(tmp)), \
                 patch.object(registry, 'find_executable', return_value='C:/mock/tool.exe'), \
                 patch.object(model_catalog, '_run_probe', side_effect=[
                     SimpleNamespace(returncode=0, stdout=agy_out),
                     SimpleNamespace(returncode=0, stdout=cur_out),
                 ]):
                for name in ('antigravity', 'cursor'):
                    ok, msg = registry.save_agent(json.loads((presets / f'{name}.json').read_text(encoding='utf-8')))
                    self.assertTrue(ok, msg)
                ok, msg = self.r.set_members(['codex', 'antigravity', 'cursor'], {'codex': {}, 'antigravity': {}, 'cursor': {}})
                self.assertTrue(ok, msg)
                model_catalog.CACHE.clear()
                agy = model_catalog.refresh(self.r, 'antigravity')
                cur = model_catalog.refresh(self.r, 'cursor')
        self.assertEqual(agy['models'], [
            'gemini-4-argon',
            'gemini-4-hydrogen',
            'gemini-pro-orchestrator-g1-pro',
            'gemini-3.8-flash',
            'claude-opus-5-5',
            'claude-sonnet-5-5',
            'gpt-oss-120b-medium',
        ])
        self.assertEqual(agy['efforts_by_model']['gemini-pro-orchestrator-g1-pro'], [])
        self.assertEqual(agy['efforts_by_model']['gpt-oss-120b-medium'], [])
        self.assertEqual(agy['efforts_by_model']['gemini-4-hydrogen'], ['low', 'medium', 'high', 'xhigh'])
        for mid in ('gemini-4-argon', 'gemini-3.8-flash', 'claude-opus-5-5', 'claude-sonnet-5-5'):
            self.assertEqual(agy['efforts_by_model'][mid], ['low', 'medium', 'high'])
        self.assertEqual(agy['model_labels'].get('gemini-pro-orchestrator-g1-pro'), 'Orchestrator (Argon)')
        self.assertEqual(cur['models'], ['gpt-5.5', 'gpt-5.5-fast', 'claude-4.6-sonnet-medium'])
        self.assertEqual(cur['efforts_by_model']['gpt-5.5'], ['low', 'medium', 'high', 'xhigh'])
        self.assertEqual(cur['efforts_by_model']['gpt-5.5-fast'], ['low', 'high'])
        self.assertEqual(cur['efforts_by_model']['claude-4.6-sonnet-medium'], [])

    def test_opencode_grok_qoder_real_catalog_indexing(self):
        import tempfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oc_dir = root / 'opencode'
            oc_dir.mkdir()
            (oc_dir / 'opencode.jsonc').write_text(
                '{\n'
                '  // OpenCode config with URL string and trailing comma\n'
                '  "$schema": "https://opencode.ai/config.json",\n'
                '  "model": "zhipu/glm-5.3",\n'
                '  "provider": {\n'
                '    "zhipu": {\n'
                '      "models": {\n'
                '        "glm-5.3": {"name": "GLM-5.3"},\n'
                '        "glm-5.3-flash": {},\n'
                '      },\n'
                '    },\n'
                '  },\n'
                '}\n',
                encoding='utf-8',
            )
            grok_dir = root / 'grok'
            grok_dir.mkdir()
            (grok_dir / 'models_cache.json').write_text(json.dumps({
                'models': {
                    'grok-4.7': {'id': 'grok-4.7', 'name': 'Grok 4.7', 'reasoning_efforts': ['low', 'medium', 'high', 'xhigh']},
                }
            }), encoding='utf-8')
            presets = Path(__file__).resolve().parents[1] / 'bridge' / 'presets'
            with patch.object(agents, 'OPENCODE_CONFIG_DIR', oc_dir), \
                 patch.object(agents, 'GROK_HOME', grok_dir), \
                 patch.object(registry, 'find_executable', return_value='C:/mock/tool.exe'), \
                 patch.object(model_catalog, '_run_probe', side_effect=[
                     SimpleNamespace(returncode=0, stdout='opencode/gpt-5-nano\nzhipu/glm-5.3\nzhipu/glm-5.3-flash\n'),
                     SimpleNamespace(returncode=0, stdout='You are not authenticated.\n* grok-4.7 (default)\n'),
                     SimpleNamespace(returncode=3, stdout='MODEL\nAuto\nFast\nQwen4-Max\n'),
                 ]):
                for name in ('opencode', 'grok', 'qodercli'):
                    ok, msg = registry.save_agent(json.loads((presets / f'{name}.json').read_text(encoding='utf-8')))
                    self.assertTrue(ok, msg)
                ok, msg = self.r.set_members(['codex', 'opencode', 'grok', 'qodercli'], {'codex': {}, 'opencode': {}, 'grok': {}, 'qodercli': {}})
                self.assertTrue(ok, msg)
                model_catalog.CACHE.clear()
                oc = model_catalog.refresh(self.r, 'opencode')
                gr = model_catalog.refresh(self.r, 'grok')
                qd = model_catalog.refresh(self.r, 'qodercli')
        self.assertEqual(oc['models'], ['zhipu/glm-5.3', 'zhipu/glm-5.3-flash'])
        self.assertNotIn('opencode/gpt-5-nano', oc['models'])
        self.assertEqual(gr['models'], ['grok-4.7'])
        self.assertEqual(gr['efforts_by_model']['grok-4.7'], ['low', 'medium', 'high', 'xhigh'])
        self.assertEqual(qd['models'], ['Auto', 'Fast', 'Qwen4-Max'])
        self.assertNotIn('MODEL', qd['models'])

    def test_cli_model_and_effort_resolution_for_antigravity_and_cursor(self):
        from bridge import drivers
        agy_spec = {'id': 'antigravity', 'driver': 'antigravity', 'args': {'model': ['--model', '{model}'], 'effort': ['--effort', '{effort}']}}
        self.assertEqual(drivers._resolve_cli_model_effort('antigravity', 'agy.exe', agy_spec, 'gemini-4-argon-high', 'low'), ('gemini-4-argon', 'low'))
        self.assertEqual(drivers._resolve_cli_model_effort('antigravity', 'agy.exe', agy_spec, 'gemini-pro-orchestrator-g1-pro', 'high'), ('gemini-pro-orchestrator-g1-pro', ''))
        self.assertEqual(drivers._resolve_cli_model_effort('antigravity', 'agy.exe', agy_spec, 'gpt-oss-120b-medium', 'low'), ('gpt-oss-120b-medium', ''))
        cur_spec = {'id': 'cursor', 'driver': 'cursor', 'args': {'model': ['--model', '{model}'], 'effort': []}}
        self.assertEqual(drivers._resolve_cli_model_effort('cursor', 'cursor-agent.exe', cur_spec, 'gpt-5.5', 'xhigh'), ('gpt-5.5-extra-high', ''))
        self.assertEqual(drivers._resolve_cli_model_effort('cursor', 'cursor-agent.exe', cur_spec, 'gpt-5.5-fast', 'high'), ('gpt-5.5-high-fast', ''))

    def test_idle_agent_model_switch_and_refresh_not_blocked_by_other_busy_agent(self):
        ok, msg = self.r.set_members(['claude', 'codex'], {'claude': {}, 'codex': {}})
        self.assertTrue(ok, msg)
        server = Mock()
        server.request.return_value = {'data': [{'model': 'idle-model', 'supportedReasoningEfforts': [{'reasoningEffort': 'high'}]}]}
        self.r.state['running'].append('claude')
        try:
            ok, msg, _ = self.r.set_models('claude', 'other', '')
            self.assertFalse(ok)
            self.assertIn('claude', msg)
            with patch.object(agents, 'CodexServer', return_value=server), \
                 patch.object(agents, 'codex_launch', return_value=(['codex'], {})):
                refreshed = model_catalog.refresh(self.r, 'codex')
            self.assertEqual(refreshed['models'], ['idle-model'])
            ok, msg, changed = self.r.set_models('codex', 'idle-model', 'high')
            self.assertTrue(ok, msg)
            self.assertTrue(changed)
        finally:
            self.r.state['running'].clear()

    def test_readable_model_label_prefers_catalog_label_including_effort_variant(self):
        self.assertEqual(
            model_catalog.display_model_name('gemini-4-hydrogen-xhigh', {'gemini-4-hydrogen': 'Gemini 4 Hydrogen'}),
            'Gemini 4 Hydrogen',
        )
        self.assertEqual(
            model_catalog.display_model_name('gpt-oss-120b-medium', {'gpt-oss-120b-medium': 'GPT-OSS 120B (Medium)'}),
            'GPT-OSS 120B (Medium)',
        )
        with patch.object(
            model_catalog,
            'capabilities',
            return_value={
                'model_supported': True,
                'effort_supported': True,
                'models': ['gemini-4-hydrogen'],
                'efforts_by_model': {'gemini-4-hydrogen': ['high', 'xhigh']},
                'model_labels': {'gemini-4-hydrogen': 'Gemini 4 Hydrogen'},
                'observed': {'model': 'gemini-4-hydrogen-xhigh', 'effort': 'xhigh'},
                'source': 'CLI 模型查询',
                'checked_at': 1.0,
                'stale': False,
                'error': '',
            },
        ):
            info = self.r.model_info('codex')
        self.assertEqual(info['label'], 'Gemini 4 Hydrogen · xhigh')


if __name__=='__main__':unittest.main()
