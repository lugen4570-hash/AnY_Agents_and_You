import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RoomWorkFeedbackTests(unittest.TestCase):
    def test_room_failure_diff_and_safe_retry(self):
        script = r'''
import json
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from bridge import acp, registry, room as R, web, workspace as ws
from bridge.guard import guard

wd = Path(sys.argv[1])
wd.mkdir()
ws.git(['init', '-q'], wd)
target = wd / 'work.txt'
target.write_bytes(b'committed\n')
ws.git(['add', 'work.txt'], wd)
ws.git(['commit', '-qm', 'test'], wd)
before = b'user unsaved change\n'
target.write_bytes(before)
pid = 'feedback-test'
registry.save_agent({'id': pid, 'driver': 'cli', 'bin': [sys.executable]})
room = R.rooms.create('Feedback tests', '', str(wd), participants=[pid], permissions={pid: {'work': True}})
room.set_mode('work')
srv = web.ExclusiveServer(('127.0.0.1', 0), web.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:%d' % srv.server_port

def post(action, data):
    request = Request(base + '/api/r/' + room.id + '/' + action, json.dumps(data).encode(),
                      {'Content-Type': 'application/json', 'X-RT-Token': web.RT_TOKEN})
    try:
        response = urlopen(request, timeout=8)
    except HTTPError as error:
        response = error
    with response:
        return response.code, json.load(response)

def idle():
    end = time.monotonic() + 8
    while room.busy_for():
        assert time.monotonic() < end, 'job never finished'
        time.sleep(.01)
    # The turn releases its transient claims as it finishes.
    while guard.listing():
        assert time.monotonic() < end, 'claims never released'
        time.sleep(.01)

seen = []
def fake(ai, prompt, sid, images, mode, room):
    seen.append((ai, target.read_bytes()))
    if len(seen) == 1:
        target.write_bytes(b'user unsaved change\nagent edit\n')
        return False, 'timed out', None, [{'op': 'edit', 'path': str(target)}]
    if len(seen) == 2:
        return True, 'worked after retry', None, []
    return False, 'tool did not report changes', None, []

with patch.object(R, 'ai_caller', fake):
    assert post('send', {'text': 'run this'})[0] == 200
    idle()
    status = room.api_state()['ais'][pid]
    failure = room.messages[status['failure']]
    assert room.messages[failure['source_message']]['text'] == 'run this', failure
    details = failure['failure']
    assert details['changes'] == 'recorded' and details['undo_possible'], details
    step = details['step']
    assert post('step/diff', {'step': step, 'path': '../outside'})[0] == 404
    assert post('undo/preview', {'step': step})[0] == 200
    assert post('turn/retry/preview', {'id': failure['id']})[0] == 200

    target.write_bytes(b'later unrelated edit\n')
    ws.git(['gc', '--prune=now'], wd)
    code, preview = post('step/diff', {'step': step, 'path': 'work.txt'})
    assert code == 200 and '+agent edit' in preview['diff'], preview
    assert 'later unrelated edit' not in preview['diff'], preview
    assert post('turn/retry', {'id': failure['id'], 'action': 'undo'})[0] == 409
    assert target.read_bytes() == b'later unrelated edit\n'

    target.write_bytes(b'user unsaved change\nagent edit\n')
    guard.claim(('other-room', 'other-ai'), [str(target)])
    assert post('turn/retry/preview', {'id': failure['id']})[0] == 409
    assert post('turn/retry', {'id': failure['id'], 'action': 'undo'})[0] == 409
    guard.release(('other-room', 'other-ai'))
    assert post('turn/retry', {'id': failure['id'], 'action': 'undo'})[0] == 200
    idle()
    assert seen == [(pid, before), (pid, before)], seen
    assert room.api_state()['ais'][pid]['failure'] is None
    assert post('turn/retry', {'id': failure['id'], 'action': 'continue'})[0] == 409
    assert post('send', {'text': 'run again'})[0] == 200
    idle()
    unknown = room.messages[room.api_state()['ais'][pid]['failure']]
    assert unknown['failure']['changes'] == 'unknown' and not unknown['failure']['undo_possible'], unknown
    assert post('turn/retry', {'id': unknown['id'], 'action': 'undo'})[0] == 409
    assert ws.git(['diff', '--cached', '--name-only'], wd) == b''

client = object.__new__(acp.AcpProcess)
client.active_room, client.active_mode, client.pid, client.active_edits = room, 'work', pid, []
permission = {'toolCall': {'kind': 'execute', 'title': 'Run a check'}, 'options': [
    {'optionId': 'permanent', 'kind': 'allow_always'}, {'optionId': 'once', 'kind': 'allow_once'},
    {'optionId': 'reject', 'kind': 'reject_once'},
]}
choices = []
def approval_fake(ai, prompt, sid, images, mode, room):
    choices.append(client._on_permission(permission)['outcome']['optionId'])
    return True, 'done', None, []

with patch.object(R, 'ai_caller', approval_fake):
    for decision, result in [('deny', 'reject'), ('allow', 'once')]:
        assert post('send', {'text': 'request permission'})[0] == 200
        end = time.monotonic() + 8
        while not (waiting := room.api_state()['ais'][pid]['approval']):
            assert time.monotonic() < end, 'approval not published'
            time.sleep(.03)
        assert waiting['title'] == 'Run a check'
        assert post('turn/approval', {'id': 'unrelated', 'decision': 'allow'})[0] == 409
        assert post('turn/approval', {'id': waiting['id'], 'decision': decision})[0] == 200
        idle()
        assert choices[-1] == result and room.api_state()['ais'][pid]['approval'] is None
        assert post('turn/approval', {'id': waiting['id'], 'decision': 'allow'})[0] == 409
    assert client.active_edits == [{'op': 'command'}]
srv.shutdown()
srv.server_close()
'''
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
            result = subprocess.run(
                [sys.executable, '-c', script, str(Path(root) / 'workspace')],
                cwd=Path(__file__).resolve().parents[1],
                env=dict(os.environ, ROUNDTABLE_LOG_DIR=str(Path(root) / 'data'), ROUNDTABLE_DETACHED_CLI='0'),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=35,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
