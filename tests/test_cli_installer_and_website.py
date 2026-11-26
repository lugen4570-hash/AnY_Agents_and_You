"""Verify CLI bootstrap scripts, macOS DMG packaging config, and download page wiring."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('any_cli_installer', ROOT / 'website' / 'install-cli.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class CliInstallerAndWebsiteTests(unittest.TestCase):
    def test_shell_scripts_use_lf_line_endings(self):
        for rel in ('packaging/build_macos.sh', 'website/install-cli.sh'):
            raw = (ROOT / rel).read_bytes()
            self.assertNotIn(b'\r', raw, f'{rel} must use LF line endings')

    def test_powershell_installer_parses_without_syntax_errors(self):
        ps1 = ROOT / 'website' / 'install-cli.ps1'
        script = (
            "$tokens=$null; $errors=$null; "
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{ps1}', [ref]$tokens, [ref]$errors); "
            "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
        )
        res = subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_download_page_exposes_dmg_and_curl_irm_commands(self):
        html = (ROOT / 'website' / 'download.html').read_text(encoding='utf-8')
        self.assertIn('downloads/AnY-macOS-arm64.dmg', html)
        self.assertIn('downloads/AnY-macOS-x86_64.dmg', html)
        self.assertIn('install-cli.sh', html)
        self.assertIn('install-cli.ps1', html)
        self.assertIn('data-platform="cmd"', html)
        self.assertIn('data-cmd-command=', html)
        self.assertIn('powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://lugen4570-hash.github.io/AnY_Agents_and_You/install-cli.ps1 | iex"', html)
        self.assertIn('data-install-guide', html)
        self.assertIn('data-wechat-banner', html)

    def test_install_cli_print_launcher_writes_launcher_and_handles_uv_fallback(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tar:
            payload = b'[project]\nname="ai-bridge-room"\nversion="0.0.1"\n'
            info = tarfile.TarInfo('AnY-CLI/pyproject.toml')
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        bundle = buf.getvalue()
        commit = 'a' * 40
        manifest = json.dumps({'commit': commit, 'sha256': hashlib.sha256(bundle).hexdigest(), 'size': len(bundle)}).encode()

        def fake_download(path, _limit):
            if path == 'cli/current.json':
                return manifest
            if path == f'cli/any-cli-{commit}.tar.gz':
                return bundle
            raise AssertionError(path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'cli'

            def fake_run(cmd, **kwargs):
                self.assertIs(kwargs.get('stdout'), INSTALLER.sys.stderr)
                if cmd[1:3] == ['-m', 'venv']:
                    raise subprocess.CalledProcessError(1, cmd)
                if Path(cmd[0]).name.startswith('uv') and cmd[1] == 'venv':
                    interp = INSTALLER.python_in(Path(cmd[-1]).parent)
                    interp.parent.mkdir(parents=True, exist_ok=True)
                    interp.write_text('stub', encoding='utf-8')
                return subprocess.CompletedProcess(cmd, 0)

            stdout = io.StringIO()
            with patch.object(INSTALLER, 'download', side_effect=fake_download), \
                 patch.object(INSTALLER, '_find_uv', return_value='uv'), \
                 patch.object(INSTALLER.subprocess, 'run', side_effect=fake_run), \
                 patch.dict(INSTALLER.os.environ, {'ANY_CLI_INSTALL_DIR': str(root)}), \
                 patch('sys.stdout', stdout):
                rc = INSTALLER.main(['--print-launcher'])
            self.assertEqual(rc, 0)
            launcher = Path(stdout.getvalue().strip())
            self.assertTrue(launcher.is_file())
            self.assertEqual(launcher.parent, root.resolve())
            self.assertIn('-I -X utf8 -m bridge.cli', launcher.read_text(encoding='utf-8'))

    def test_shell_installer_requires_working_venv_and_pip(self):
        script = (ROOT / 'website' / 'install-cli.sh').read_text(encoding='utf-8')
        self.assertIn('import sys, venv, ensurepip', script)
        self.assertIn('-m venv "$probe_dir"', script)
        self.assertIn('-m pip --version', script)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows cmd.exe check')
    def test_cmd_install_command_executes_via_cmd_exe(self):
        html = (ROOT / 'website' / 'download.html').read_text(encoding='utf-8')
        match = re.search(r"data-cmd-command='([^']+)'", html)
        self.assertIsNotNone(match)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Write-Output 'cmd-bridge-ok'")

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            cmd = match.group(1).replace(
                'https://lugen4570-hash.github.io/AnY_Agents_and_You/install-cli.ps1',
                f'http://127.0.0.1:{server.server_port}/install-cli.ps1',
            )
            res = subprocess.run(f'cmd.exe /c {cmd}', capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
            self.assertIn('cmd-bridge-ok', res.stdout)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
