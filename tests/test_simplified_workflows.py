"""Quiet Agent inputs and one-step contact removal, using isolated data only."""
import copy
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_contacts_access import DATA, R, access, agents, call, common, registry


class SimplifiedWorkflows(unittest.TestCase):
    def setUp(self):
        self.pid = 'cleanup-agent'
        registry.save_agent({'id': self.pid, 'driver': 'external', 'enabled': True})
        self.key = access.credential(self.pid)
        self.a = R.rooms.create('delete contact a', '', DATA, participants=[self.pid, 'claude'])
        self.b = R.rooms.create('delete contact b', '', DATA, participants=[self.pid])

    def test_delete_detaches_loaded_unloaded_archived_and_trashed_rooms(self):
        self.a.add_message(self.pid, 'keep historical reply')
        R.set_archived(self.b.id, True)
        R.rooms.unload(self.b.id)
        trash = R.rooms.create('contact in trash', '', DATA, participants=[self.pid])
        self.assertTrue(R.trash_meeting(trash.id)[0])
        code, result = call('/api/agents/remove', {'id': self.pid}, owner=True)
        self.assertEqual(code, 200, result)
        self.assertIsNone(registry.get(self.pid))
        self.assertIsNone(access.identify(self.key))
        self.assertNotIn(self.pid, self.a.ais)
        self.assertEqual(self.a.messages[-1]['text'], 'keep historical reply')
        for base in (common.MEET_DIR, common.TRASH_DIR):
            for row in R.scan(base):
                meta = common.read_json(os.path.join(base, row['id'], 'meeting.json'))
                self.assertNotIn(self.pid, meta.get('participants', []))

    def test_busy_target_refuses_without_partial_detach(self):
        self.a.state['running'].append(self.pid)
        try:
            self.assertEqual(call('/api/agents/remove', {'id': self.pid}, owner=True)[0], 409)
            self.assertIn(self.pid, self.a.ais)
            self.assertIn(self.pid, self.b.ais)
            self.assertEqual(access.identify(self.key), self.pid)
        finally:
            self.a.state['running'].clear()

    def test_other_agent_running_does_not_prevent_contact_removal(self):
        self.a.state['running'].append('claude')
        try:
            self.assertEqual(call('/api/agents/remove', {'id': self.pid}, owner=True)[0], 200)
            self.assertEqual(self.a.state['running'], ['claude'])
            self.assertEqual(self.a.ais, ['claude'])
        finally:
            self.a.state['running'].clear()

    def test_failed_metadata_write_rolls_back_and_preserves_contact(self):
        original = R.write_json
        calls = 0

        def fail_once(path, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('fixture disk failure')
            return original(path, value)

        before = copy.deepcopy(self.a.meta)
        with patch.object(R, 'write_json', side_effect=fail_once):
            self.assertEqual(call('/api/agents/remove', {'id': self.pid}, owner=True)[0], 500)
        self.assertEqual(self.a.meta, before)
        self.assertEqual(common.read_json(os.path.join(self.a.dir, 'meeting.json')), before)
        self.assertIsNotNone(registry.get(self.pid))
        self.assertEqual(access.identify(self.key), self.pid)

    def test_claude_rules_are_system_instructions_not_chat_text(self):
        prompt = self.a.build_prompt('claude')[0]
        self.assertNotIn('本会话授予你的权限', prompt)
        self.assertNotIn(common.BRIDGE_RULES, prompt)
        cmd = agents.build_cmd('claude', 'discuss', None, ['claude'], room=self.a)
        self.assertIn('--append-system-prompt', cmd)
        self.assertIn('false 表示禁止', cmd[cmd.index('--append-system-prompt') + 1])
        self.assertNotIn('还没写目标', prompt)

    def test_cleanup_does_not_hold_room_and_credential_locks(self):
        from bridge import members

        def cleanup(pid):
            completed = threading.Event()

            def concurrent_reader():
                R.rooms.listing()
                access.identify(self.key)
                completed.set()

            reader = threading.Thread(target=concurrent_reader, daemon=True)
            reader.start()
            self.assertTrue(completed.wait(2), 'cleanup must not block concurrent room/credential readers')
            reader.join()

        with patch.object(members.broker, 'stop_standby', side_effect=cleanup):
            self.assertEqual(call('/api/agents/remove', {'id':self.pid}, owner=True)[0], 200)

    def test_deleting_contact_keeps_other_contact_credentials(self):
        registry.save_agent({'id':'keep-agent','driver':'external','enabled':True})
        other_key = access.credential('keep-agent')
        self.assertEqual(call('/api/agents/remove', {'id':self.pid}, owner=True)[0], 200)
        self.assertEqual(access.identify(other_key), 'keep-agent')

    def test_codex_start_and_resume_receive_developer_instructions(self):
        class Captured(Exception):
            pass

        for sid, method in [(None, 'thread/start'), ('existing', 'thread/resume')]:
            server = agents.CodexServer()
            with patch.object(server, 'ensure'), patch.object(server, 'request', side_effect=Captured) as request:
                with self.assertRaises(Captured):
                    server.run_turn(sid, 'hello', [], 'discuss', '', '', [], {}, instructions='private rules')
            self.assertEqual(request.call_args.args[0], method)
            self.assertEqual(request.call_args.args[1]['developerInstructions'], 'private rules')

    def test_generic_stateless_prompt_uses_short_rules(self):
        registry.save_agent({'id':'short-cli', 'driver':'cli', 'bin':[sys.executable], 'context':'full'})
        room = R.rooms.create('short prompt', '', DATA, participants=['short-cli'])
        room.add_message('你', 'hello')
        prompt = room.build_prompt('short-cli')[0]
        self.assertIn('hello', prompt)
        self.assertIn('讨论模式，只读', prompt)
        self.assertNotIn(common.BRIDGE_RULES, prompt)
        self.assertLess(len(prompt), 400)

    def test_unchanged_stateful_rules_are_not_repeated(self):
        registry.save_agent({'id':'short-cli', 'driver':'cli', 'bin':[sys.executable], 'context':'delta'})
        room = R.rooms.create('delta prompt', '', DATA, participants=['short-cli'])
        room.meta['short-cli_session'] = 'native-session'
        room.meta['instruction_seen'] = {'short-cli':room.instruction_signature('short-cli')}
        prompt = room.build_prompt('short-cli')[0]
        self.assertNotIn('【合拍】', prompt)
        room.meta['permissions'] = {'short-cli':{'post':False}}
        self.assertIn('【合拍】', room.build_prompt('short-cli')[0])


if __name__ == '__main__':
    unittest.main()
