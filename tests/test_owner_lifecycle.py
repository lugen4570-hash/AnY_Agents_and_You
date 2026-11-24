"""Regression coverage for owner window lifecycle and multi-tab close behavior."""
import threading
import time
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge.owner_lifecycle import OwnerLifecycle

class OwnerLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.stopped=threading.Event()
        self.life=OwnerLifecycle(self.stopped.set,grace=.12,expiry=.25,interval=.01)
        self.a='a'*32;self.b='b'*32
    def test_last_tab_close_stops_service(self):
        self.life.update(self.a,'open');self.life.update(self.a,'close')
        self.assertTrue(self.stopped.wait(1))
    def test_closing_one_of_two_tabs_does_not_stop_service(self):
        self.life.update(self.a,'open');self.life.update(self.b,'open');self.life.update(self.a,'close')
        self.assertFalse(self.stopped.wait(.16));self.life.update(self.b,'close');self.assertTrue(self.stopped.wait(1))
    def test_reload_registers_new_tab_within_grace(self):
        self.life.update(self.a,'open');self.life.update(self.a,'close');time.sleep(.04);self.life.update(self.b,'open')
        self.assertFalse(self.stopped.wait(.15));self.life.update(self.b,'close');self.assertTrue(self.stopped.wait(1))
    def test_late_close_from_old_document_does_not_close_reloaded_tab(self):
        old='c'*32;new='d'*32
        self.life.update(self.a,'open',old);self.life.update(self.a,'open',new);self.life.update(self.a,'ping',old);self.life.update(self.a,'close',old)
        self.assertFalse(self.stopped.wait(.15));self.life.update(self.a,'close',new);self.assertTrue(self.stopped.wait(1))
    def test_abandoned_tab_expires(self):
        self.life.update(self.a,'open');self.assertTrue(self.stopped.wait(1))
    def test_startup_lease_stops_if_open_never_arrives(self):
        self.life.arm(.08)
        self.assertTrue(self.stopped.wait(1))
    def test_open_cancels_startup_lease(self):
        self.life.arm(.08)
        time.sleep(.02)
        self.life.update(self.a,'open','i'*32)
        self.assertFalse(self.stopped.wait(.14))
        self.life.update(self.a,'close','i'*32)
        self.assertTrue(self.stopped.wait(1))
    def test_invalid_and_unknown_close_do_not_stop(self):
        with self.assertRaises(ValueError):self.life.update('bad','open')
        self.life.update(self.a,'open');self.life.update(self.b,'close');self.assertFalse(self.stopped.wait(.15))
        self.life.update(self.a,'close');self.assertTrue(self.stopped.wait(1))
    def test_active_work_defers_shutdown_until_idle(self):
        busy=[True]
        stopped=threading.Event()
        life=OwnerLifecycle(stopped.set,grace=.08,expiry=.25,interval=.01,is_busy=lambda:busy[0])
        life.update(self.a,'open');life.update(self.a,'close')
        self.assertFalse(stopped.wait(.2))
        busy[0]=False
        self.assertTrue(stopped.wait(1))
class LifecycleSwitch(unittest.TestCase):
    def test_matrix(self):
        from bridge.web import owner_lifecycle_enabled
        self.assertTrue(owner_lifecycle_enabled({}))
        self.assertTrue(owner_lifecycle_enabled({'ROUNDTABLE_OWNER_LIFECYCLE':'1'}))
        self.assertFalse(owner_lifecycle_enabled({'ROUNDTABLE_NO_BROWSER':'1'}))
        self.assertTrue(owner_lifecycle_enabled({'ROUNDTABLE_NO_BROWSER':'1','ROUNDTABLE_OWNER_LIFECYCLE':'1'}))

class LifecycleHeadless(unittest.TestCase):
    def test_headless_backend_exits_after_last_tab(self):
        import json,os,re,socket,subprocess,tempfile,urllib.request
        root=Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,ROUNDTABLE_PORT=str(port),ROUNDTABLE_NO_BROWSER='1',
                     ROUNDTABLE_OWNER_LIFECYCLE='1',ROUNDTABLE_LOG_DIR=tmp,PYTHONIOENCODING='utf-8')
            proc=subprocess.Popen([sys.executable,str(root/'roundtable.py')],cwd=root,env=env,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                base='http://127.0.0.1:%d'%port
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                info=None
                for _ in range(100):
                    try:
                        with opener.open(base+'/api/server/info',timeout=.2) as response:
                            info=json.loads(response.read())
                        break
                    except OSError:time.sleep(.05)
                self.assertIsNotNone(info,'backend did not start')
                with opener.open(base+'/',timeout=2) as response:
                    token=re.search(r'name="rt-token" content="([^"]+)"',response.read().decode('utf-8')).group(1)
                body={'tab':'t'*32,'instance':'i'*32}
                for action in ('open','close'):
                    request=urllib.request.Request(base+'/api/ui/session',
                        data=json.dumps(dict(body,action=action)).encode(),
                        headers={'Content-Type':'application/json','X-RT-Token':token})
                    with opener.open(request,timeout=2) as response:
                        self.assertEqual(response.status,200)
                self.assertEqual(proc.wait(timeout=15),0)
            finally:
                if proc.poll() is None:
                    proc.terminate();proc.wait(timeout=5)

    def test_headless_backend_exits_after_last_tab_even_with_active_detached_worker(self):
        import json,os,re,socket,subprocess,tempfile,urllib.request
        from bridge import detached_jobs
        root=Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            pid_file=Path(tmp)/'worker.pid'
            worker_py=Path(tmp)/'slow_worker.py'
            worker_py.write_text(
                f"import os, pathlib, time\npathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()), encoding='utf-8')\ntime.sleep(30)\n",
                encoding='utf-8',
            )
            env=dict(os.environ,ROUNDTABLE_PORT=str(port),ROUNDTABLE_NO_BROWSER='1',
                     ROUNDTABLE_OWNER_LIFECYCLE='1',ROUNDTABLE_DETACHED_CLI='1',
                     ROUNDTABLE_LOG_DIR=tmp,PYTHONIOENCODING='utf-8')
            proc=subprocess.Popen([sys.executable,str(root/'roundtable.py')],cwd=root,env=env,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            worker_pid=0
            try:
                base='http://127.0.0.1:%d'%port
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for _ in range(100):
                    try:
                        with opener.open(base+'/api/server/info',timeout=.2) as response:
                            if response.status==200:break
                    except OSError:time.sleep(.05)
                with opener.open(base+'/',timeout=2) as response:
                    token=re.search(r'name="rt-token" content="([^"]+)"',response.read().decode('utf-8')).group(1)
                def post(path,payload):
                    req=urllib.request.Request(base+path,data=json.dumps(payload).encode(),
                        headers={'Content-Type':'application/json','X-RT-Token':token})
                    with opener.open(req,timeout=20) as resp:
                        return json.loads(resp.read())
                post('/api/ui/session',{'tab':'t'*32,'instance':'i'*32,'action':'open'})
                post('/api/agents/add',{'spec':{
                    'id':'slow-worker','label':'Slow Worker','driver':'cli',
                    'bin':[sys.executable],'args':{'base':[str(worker_py)]},'prompt':'stdin',
                }})
                rid=post('/api/rooms/new',{'title':'busy-close','workdir':tmp,'participants':['slow-worker']})['id']
                post(f'/api/r/{rid}/send',{'text':'@slow-worker run'})
                for _ in range(100):
                    if pid_file.is_file():
                        worker_pid=int(pid_file.read_text(encoding='utf-8').strip())
                        break
                    time.sleep(.05)
                self.assertTrue(worker_pid>0 and detached_jobs.pid_alive(worker_pid),'detached worker did not start')
                post('/api/ui/session',{'tab':'t'*32,'instance':'i'*32,'action':'close'})
                self.assertEqual(proc.wait(timeout=8),0)
                deadline=time.monotonic()+5
                while detached_jobs.pid_alive(worker_pid) and time.monotonic()<deadline:
                    time.sleep(.05)
                self.assertFalse(detached_jobs.pid_alive(worker_pid),'AnY left child detached worker alive')
            finally:
                if proc.poll() is None:
                    proc.terminate();proc.wait(timeout=5)
                if worker_pid and detached_jobs.pid_alive(worker_pid):
                    detached_jobs.kill_pid_tree(worker_pid)

if __name__=='__main__':unittest.main()
