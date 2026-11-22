"""End-to-end tests for Detached CLI Job Runner & Startup Dialogue Collector."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DetachedJobsTests(unittest.TestCase):
    def _run_isolated(self, script: str):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROUNDTABLE_DATA=tmp, ROUNDTABLE_DETACHED_CLI='1')
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=35,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cli_job_survives_cojam_shutdown_and_collects_on_reopen(self):
        self._run_isolated(r'''
import os, sys, tempfile, time
from pathlib import Path
from bridge import detached_jobs, registry, room as R
from bridge.common import read_json

with tempfile.TemporaryDirectory() as wd:
    # Register a fast local CLI agent that sleeps 1.2s then prints a reply
    worker_py = Path(wd) / 'fake_cli.py'
    worker_py.write_text(
        'import sys, time\n'
        'time.sleep(1.2)\n'
        'print("DETACHED_OK_FROM_CLI")\n',
        encoding='utf-8',
    )
    registry.save_agent({
        'id': 'detached-cli',
        'label': 'Detached CLI',
        'driver': 'cli',
        'bin': [sys.executable],
        'args': {'base': [str(worker_py)], 'new': [], 'resume': [], 'read': [], 'work': []},
        'prompt': 'stdin',
    })

    r = R.rooms.create('detached room', '', wd, participants=['detached-cli'])
    assert detached_jobs.should_detach(r, 'detached-cli', R.ai_caller)

    # Spawn detached job directly as run_job would
    r.add_message('你', '@detached-cli do work')
    prompt, upto, ver, imgs = r.build_prompt('detached-cli', 'discuss')
    job_path = detached_jobs.spawn_job(
        r, 'detached-cli', prompt, None, imgs, 'discuss',
        upto=upto, ver=ver, pre_tree=None, t0=time.time(),
    )

    # Simulate Cojam shutting down immediately while the CLI job is still running
    detached_jobs.begin_shutdown()
    state, _ = detached_jobs.wait_for_job(job_path)
    assert state == 'detached', f'Expected detached on shutdown, got {state}'

    # Worker must STILL finish on its own while Cojam is "closed"
    deadline = time.time() + 10
    while time.time() < deadline:
        d = read_json(job_path) or {}
        if d.get('status') == 'done':
            break
        time.sleep(0.15)
    d = read_json(job_path) or {}
    assert d.get('status') == 'done', d
    assert d['result']['ok'] is True, d['result']
    assert 'DETACHED_OK_FROM_CLI' in d['result']['text'], d['result']

    # Simulate Cojam reopening: collect_for_room collects the reply exactly once
    detached_jobs.reset_shutdown()
    n1 = detached_jobs.collect_for_room(r)
    assert n1 == 1, n1
    assert any(m['speaker'] == 'detached-cli' and 'DETACHED_OK_FROM_CLI' in m['text'] for m in r.messages), r.messages

    # Second collection must be a no-op (idempotent)
    n2 = detached_jobs.collect_for_room(r)
    assert n2 == 0, n2
''')

    def test_explicit_stop_cancels_detached_job(self):
        self._run_isolated(r'''
import os, sys, tempfile, time
from pathlib import Path
from bridge import detached_jobs, registry, room as R
from bridge.common import read_json

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as wd:
    worker_py = Path(wd) / 'slow_cli.py'
    worker_py.write_text('import time\ntime.sleep(30)\nprint("SHOULD_NOT_FINISH")\n', encoding='utf-8')
    registry.save_agent({
        'id': 'slow-cli',
        'label': 'Slow CLI',
        'driver': 'cli',
        'bin': [sys.executable],
        'args': {'base': [str(worker_py)], 'new': [], 'resume': [], 'read': [], 'work': []},
        'prompt': 'stdin',
    })

    r = R.rooms.create('cancel room', '', wd, participants=['slow-cli'])
    job_path = detached_jobs.spawn_job(
        r, 'slow-cli', 'hi', None, [], 'discuss',
        upto=0, ver=1, pre_tree=None, t0=time.time(),
    )
    time.sleep(0.5)
    killed = detached_jobs.cancel_jobs(r, ['slow-cli'])
    assert killed == 1
    d = read_json(job_path) or {}
    assert d.get('status') == 'cancelled'
    deadline = time.time() + 5
    while time.time() < deadline and detached_jobs.pid_alive(int(d.get('pid') or 0)):
        time.sleep(0.1)
    assert not detached_jobs.pid_alive(int(d.get('pid') or 0))
    r.close()
''')

    def test_detached_job_handles_hex_model_revision(self):
        self._run_isolated(r'''
import sys, tempfile, time
from pathlib import Path
from bridge import detached_jobs, model_catalog, registry, room as R
from bridge.common import read_json

with tempfile.TemporaryDirectory() as wd:
    worker_py = Path(wd) / 'hex_rev_cli.py'
    worker_py.write_text('print("HEX_REVISION_REPLY_OK")\n', encoding='utf-8')
    registry.save_agent({
        'id': 'detached-cli',
        'label': 'Detached CLI',
        'driver': 'cli',
        'bin': [sys.executable],
        'args': {'base': [str(worker_py)], 'new': [], 'resume': [], 'read': [], 'work': []},
        'prompt': 'stdin',
    })

    r = R.rooms.create('hex revision room', '', wd, participants=['detached-cli'])
    r.add_message('你', '@detached-cli test hex revision')
    prompt, upto, ver, imgs = r.build_prompt('detached-cli', 'discuss')
    rev = model_catalog.request_id(r, 'detached-cli')
    assert isinstance(rev, str) and len(rev) == 24
    int(rev, 16)
    job_path = detached_jobs.spawn_job(
        r, 'detached-cli', prompt, None, imgs, 'discuss',
        upto=upto, ver=ver, pre_tree=None, t0=time.time(), model_revision=rev,
    )

    deadline = time.time() + 10
    while time.time() < deadline:
        d = read_json(job_path) or {}
        if d.get('status') == 'done':
            break
        time.sleep(0.1)
    d = read_json(job_path) or {}
    assert d.get('status') == 'done', d
    assert d.get('model_revision') == rev, d
    detached_jobs.apply_job_result(r, job_path, d)
    assert any(m['speaker'] == 'detached-cli' and 'HEX_REVISION_REPLY_OK' in m['text'] for m in r.messages), r.messages
    assert not any(m['speaker'] == '系统' and '内部错误' in m.get('text', '') for m in r.messages), r.messages
    r.close()
''')


if __name__ == '__main__':
    unittest.main()
