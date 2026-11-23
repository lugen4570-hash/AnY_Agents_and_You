import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

import test_contacts_access as support
from bridge import updater


class Updates(unittest.TestCase):
    def test_macos_uses_separate_manifest_and_downloads_verified_zip(self):
        archive = 'Cojam-99.0.0-macOS-Python.zip'
        manifest = self.manifest(b'macos archive')
        manifest['url'] = updater.DOWNLOAD_ROOT + archive
        with self.assertRaises(ValueError):
            updater.parse_manifest(manifest)
        with self.assertRaises(ValueError):
            updater.parse_manifest(self.manifest(), macos=True)
        with patch.object(updater.sys, 'platform', 'darwin'), \
             patch.object(updater, 'STATE', {'state': 'idle'}), patch.object(updater, 'RELEASE', None), \
             patch.object(updater, '_open', side_effect=[io.BytesIO(json.dumps(manifest).encode()), io.BytesIO(b'macos archive')]) as request, \
             tempfile.TemporaryDirectory() as tmp:
            result = updater.check()
            self.assertEqual(result['state'], 'available')
            self.assertTrue(result['macos'])
            self.assertFalse(result['can_install'])
            request.assert_called_once_with(updater.MACOS_MANIFEST)
            updater._download(updater.RELEASE, tmp)
            self.assertEqual(updater.status()['state'], 'downloaded')
            self.assertEqual(Path(tmp, archive).read_bytes(), b'macos archive')

    def manifest(self, payload=b'installer'):
        return {'app':'Cojam', 'version':'99.0.0',
                'url':'https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/Cojam-Setup-99.0.0.exe',
                'sha256':hashlib.sha256(payload).hexdigest(), 'size':len(payload)}

    def test_rejects_untrusted_urls_and_bad_manifest(self):
        for url in ['http://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/Cojam-Setup-99.0.0.exe',
                    'https://evil.test/Cojam/downloads/Cojam-Setup-99.0.0.exe',
                    'https://jun-genyan.github.io/Cojam/downloads/Cojam-Setup-99.0.0.exe',
                    'https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/../Cojam-Setup-99.0.0.exe',
                    'https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/Cojam-Setup-99.0.0.exe?x=y']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                updater.parse_manifest(dict(self.manifest(),url=url))
        with self.assertRaises(ValueError):
            updater.parse_manifest(dict(self.manifest(), sha256='bad'))

    def test_new_account_is_the_only_trusted_update_origin(self):
        self.assertEqual(updater.MANIFEST, 'https://lugen4570-hash.github.io/AnY_Agents_and_You/update.json')
        self.assertEqual(updater.DOWNLOAD_ROOT, 'https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/')
        self.assertEqual(updater.parse_manifest(self.manifest())['url'], self.manifest()['url'])

    def test_generated_manifest_matches_the_trusted_account(self):
        script = Path(__file__).resolve().parents[1] / 'packaging' / 'make_update_manifest.py'
        spec = importlib.util.spec_from_file_location('cojam_manifest_generator', script)
        self.assertIsNotNone(spec)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'dist').mkdir()
            (root / 'website').mkdir()
            (root / 'pyproject.toml').write_text('[project]\nversion = "99.0.0"\n', encoding='utf-8')
            (root / 'dist' / 'Cojam-Setup-99.0.0.exe').write_bytes(b'installer')
            with patch.object(generator, 'ROOT', root), patch.object(sys, 'argv', ['make_update_manifest.py']):
                generator.main()
            import json
            generated = json.loads((root / 'website' / 'update.json').read_text(encoding='utf-8'))
            self.assertEqual(updater.parse_manifest(generated)['url'], self.manifest()['url'])
            self.assertEqual(generated['sha256'], self.manifest()['sha256'])

    def test_verified_download_never_runs_and_never_overwrites(self):
        release=updater.parse_manifest(self.manifest())
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp,'Cojam-Setup-99.0.0.exe');old.write_bytes(b'old')
            with patch.object(updater,'_open',return_value=io.BytesIO(b'installer')):
                updater._download(release,tmp)
            result=updater.status()
            self.assertEqual(result['state'],'downloaded')
            self.assertEqual(old.read_bytes(),b'old')
            self.assertEqual(Path(result['path']).read_bytes(),b'installer')
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_corrupt_download_is_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater,'_open',return_value=io.BytesIO(b'corrupt!!')):
            updater._download(updater.parse_manifest(self.manifest()),tmp)
            self.assertEqual(updater.status()['state'],'error')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_only_authenticated_local_owner_can_start_download(self):
        self.assertEqual(support.call('/api/update/download', {})[0],403)
        self.assertEqual(support.call('/api/update/download', {}, owner=True,
                                      headers={'X-Forwarded-For':'10.0.0.2'})[0],403)
        with patch.object(updater,'start_download',return_value={'state':'downloading'}):
            self.assertEqual(support.call('/api/update/download', {}, owner=True)[0],200)

    def test_install_revalidates_and_targets_current_desktop_directory(self):
        payload=b'verified-installer'
        release=updater.parse_manifest(self.manifest(payload))
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp,'My Cojam');folder.mkdir()
            core=folder/'CojamCore.exe';core.write_bytes(b'core')
            (folder/'Cojam.exe').write_bytes(b'shell')
            installer=Path(tmp,'Cojam-Setup-99.0.0.exe');installer.write_bytes(payload)
            old_state=dict(updater.STATE);old_release=updater.RELEASE
            self.addCleanup(lambda: (updater.STATE.clear(),updater.STATE.update(old_state),setattr(updater,'RELEASE',old_release)))
            updater.STATE.update(state='downloaded',path=str(installer));updater.RELEASE=release
            with patch.object(updater.sys,'platform','win32'), patch.object(updater.sys,'frozen',True,create=True), \
                 patch.object(updater.sys,'executable',str(core)), patch.object(updater.subprocess,'Popen') as launch, \
                 patch.object(updater,'_watch_install'):
                self.assertEqual(updater.start_install(lambda: True)['state'],'installing')
                args=launch.call_args.args[0]
                self.assertIn('-EncodedCommand',args)
                env=launch.call_args.kwargs['env']
                self.assertEqual(Path(env['COJAM_UPDATE_DIRECTORY']),folder.resolve())
                self.assertEqual(env['COJAM_UPDATE_INSTALLER'],str(installer))
                self.assertIn('/NOFORCECLOSEAPPLICATIONS',updater._INSTALL_HELPER)
                self.assertIn('Start-Process -FilePath $shellPath',updater._INSTALL_HELPER)
                updater.STATE['state']='downloaded';installer.write_bytes(b'altered-installer!')
                with self.assertRaisesRegex(ValueError,'更改|校验'):
                    updater.start_install(lambda: True)
                self.assertEqual(launch.call_count,1)
                installer.write_bytes(payload)
                updater.STATE['state']='downloaded'
                with self.assertRaisesRegex(ValueError,'安全退出'):
                    updater.start_install(lambda: False)
                launch.return_value.terminate.assert_called_once()
                self.assertEqual(updater.STATE['state'],'downloaded')

    def test_install_requires_local_owner_and_idle(self):
        self.assertEqual(support.call('/api/update/install', {})[0],403)
        self.assertEqual(support.call('/api/update/install', {}, owner=True,
                                      headers={'X-Forwarded-For':'10.0.0.2'})[0],403)
        with patch('bridge.web.R.rooms.listing',return_value=[{'running':['codex']}]), \
             patch.object(updater,'start_install') as launch:
            self.assertEqual(support.call('/api/update/install', {}, owner=True)[0],409)
            launch.assert_not_called()

    def test_automatic_install_waits_if_tasks_are_running(self):
        release=updater.parse_manifest(self.manifest())
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(updater,'_open',return_value=io.BytesIO(b'installer')), \
             patch.object(updater,'start_install') as launch:
            updater._download(release,tmp,auto_install=True,busy=lambda:True)
            result=updater.status()
            self.assertEqual(result['state'],'downloaded')
            self.assertIn('运行',result['error'])
            self.assertTrue(Path(result['path']).is_file())
            launch.assert_not_called()

    def test_install_failure_is_available_for_retry(self):
        from unittest.mock import Mock
        old=dict(updater.STATE)
        self.addCleanup(lambda: (updater.STATE.clear(),updater.STATE.update(old)))
        updater.STATE.update(state='installing',error='')
        updater._watch_install(Mock(wait=Mock(return_value=1)))
        self.assertEqual(updater.status()['state'],'downloaded')
        self.assertIn('安装未完成',updater.status()['error'])

    def test_update_shutdown_does_not_stop_busy_rooms(self):
        from bridge import web
        from unittest.mock import Mock
        with patch.object(web.R.rooms,'listing',return_value=[{'running':['codex']}]), \
             patch.object(web,'stop_application') as stop:
            self.assertFalse(web.stop_idle_for_update(Mock()))
            stop.assert_not_called()

    def test_parallel_range_download_retries_and_verifies(self):
        import threading
        payload = b'0123456789abcdef' * (128 * 1024)  # 2 MiB >= RANGE_THRESHOLD
        release = updater.parse_manifest(self.manifest(payload))
        attempts: dict[int, int] = {}
        attempt_lock = threading.Lock()

        class _RangeResp(io.BytesIO):
            def __init__(self, body: bytes, start: int, end: int, total: int):
                super().__init__(body)
                self.status = 206
                self.headers = {'Content-Range': f'bytes {start}-{end}/{total}'}

        def fake_open(url, headers=None):
            self.assertEqual(url, release['url'])
            header = (headers or {}).get('Range', '')
            self.assertTrue(header.startswith('bytes='))
            start_s, end_s = header[len('bytes='):].split('-')
            start, end = int(start_s), int(end_s)
            with attempt_lock:
                attempts[end] = attempts.get(end, 0) + 1
                hit = attempts[end]
            body = payload[start:end + 1]
            # Simulate a dropped connection mid-slice on the first attempt of slice 2.
            if start > 0 and hit == 1 and len(body) > 1024:
                body = body[:1024]
            return _RangeResp(body, start, end, len(payload))

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(updater, '_open', side_effect=fake_open), \
             patch.object(updater.time, 'sleep'):
            updater._download(release, tmp)
            result = updater.status()
            self.assertEqual(result['state'], 'downloaded')
            self.assertEqual(Path(result['path']).read_bytes(), payload)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_large_download_falls_back_when_server_returns_200(self):
        payload = b'single-stream-' * (96 * 1024)
        release = updater.parse_manifest(self.manifest(payload))

        class _FullResp(io.BytesIO):
            status = 200
            headers = {}

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(updater, '_open', return_value=_FullResp(payload)) as opener:
            updater._download(release, tmp)
            self.assertEqual(opener.call_count, 1)
            result = updater.status()
            self.assertEqual(result['state'], 'downloaded')
            self.assertEqual(Path(result['path']).read_bytes(), payload)


if __name__ == '__main__':
    unittest.main()
