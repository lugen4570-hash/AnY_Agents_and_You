"""Platform Abstraction Layer (bridge.pal) unit tests and common alias parity."""
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class PalTests(unittest.TestCase):
    def test_subprocess_kwargs_per_platform(self):
        from bridge.pal import _posix, _win32

        self.assertEqual(_posix.subprocess_kwargs(), {})
        win_kwargs = _win32.subprocess_kwargs()
        expected = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        self.assertEqual(win_kwargs, {"creationflags": expected})

    def test_shell_join_win32_and_posix(self):
        from bridge.pal import _posix, _win32

        argv = ["C:\\Program Files\\claude.exe", "--say", "it's ok"]
        self.assertEqual(
            _win32.shell_join(argv),
            "& 'C:\\Program Files\\claude.exe' '--say' 'it''s ok'",
        )
        self.assertEqual(_posix.shell_join(["/usr/bin/claude", "--say", "it's ok"]),
                         shlex.join(["/usr/bin/claude", "--say", "it's ok"]))

    def test_cli_shell_command_and_codex_args(self):
        from bridge.pal import _posix, _win32

        self.assertEqual(
            _win32.cli_shell_command(r"C:\py\python.exe", r"C:\app\hook_codex.py"),
            '& "C:/py/python.exe" "C:/app/hook_codex.py"',
        )
        self.assertEqual(
            _posix.cli_shell_command("/usr/bin/python3", "/opt/bridge/hook_codex.py"),
            "/usr/bin/python3 /opt/bridge/hook_codex.py",
        )
        self.assertEqual(_win32.codex_platform_args(), ["-c", 'windows.sandbox="unelevated"'])
        self.assertEqual(_posix.codex_platform_args(), [])

    def test_resolve_cmd_unpacks_cmd_shim_and_exe(self):
        from bridge.pal import _posix, _win32

        with tempfile.TemporaryDirectory() as tmp:
            shim_js = Path(tmp) / "codex.cmd"
            node = Path(tmp) / "node.exe"
            js = Path(tmp) / "node_modules" / "codex.js"
            js.parent.mkdir(parents=True)
            node.write_bytes(b"")
            js.write_text("", encoding="utf-8")
            shim_js.write_text('"%dp0%\\node_modules\\codex.js" %*\n', encoding="utf-8")
            with patch.object(_win32, "find_command_path", return_value=str(shim_js)):
                self.assertEqual(_win32.resolve_command("codex"), [str(node), str(js)])

            shim_exe = Path(tmp) / "claude.cmd"
            real_exe = Path(tmp) / "claude.exe"
            real_exe.write_bytes(b"")
            shim_exe.write_text('"%dp0%\\claude.exe" %*\n', encoding="utf-8")
            with patch.object(_win32, "find_command_path", return_value=str(shim_exe)):
                self.assertEqual(_win32.resolve_command("claude"), [str(real_exe)])

            with patch.object(_posix, "find_command_path", return_value="/usr/local/bin/claude"):
                self.assertEqual(_posix.resolve_command("claude"), ["/usr/local/bin/claude"])

    def test_resolve_cmd_unpacks_extensionless_cjs_ps1_and_quoted_paths(self):
        from bridge.pal import _shared, _win32

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node.exe"
            node.write_bytes(b"")

            # Extensionless node wrapper script (e.g. grok.cmd -> bin/grok)
            extless_dir = root / "node_modules" / "@xai" / "grok" / "bin"
            extless_dir.mkdir(parents=True)
            extless_script = extless_dir / "grok"
            extless_script.write_text("#!/usr/bin/env node\nconsole.log('ok');\n", encoding="utf-8")
            grok_cmd = root / "grok.cmd"
            grok_cmd.write_text('"%_prog%" "%dp0%\\node_modules\\@xai\\grok\\bin\\grok" %*\n', encoding="utf-8")
            with patch.object(_win32, "find_command_path", return_value=str(grok_cmd)):
                self.assertEqual(_win32.resolve_command("grok"), [str(node), str(extless_script)])

            # .cjs dispatcher (e.g. qodercn.cmd -> dispatcher.cjs)
            cjs_dir = root / "node_modules" / "@qodercn-ai" / "bundle"
            cjs_dir.mkdir(parents=True)
            cjs_script = cjs_dir / "qodercn-npm-dispatcher.cjs"
            cjs_script.write_text("console.log('ok');\n", encoding="utf-8")
            qoder_cmd = root / "qodercn.cmd"
            qoder_cmd.write_text('"%_prog%" "%dp0%\\node_modules\\@qodercn-ai\\bundle\\qodercn-npm-dispatcher.cjs" %*\n', encoding="utf-8")
            with patch.object(_win32, "find_command_path", return_value=str(qoder_cmd)):
                self.assertEqual(_win32.resolve_command("qodercn"), [str(node), str(cjs_script)])

            # Cursor agent.cmd -> cursor-agent.ps1 -> versions/<latest>/node.exe + index.js
            cursor_dir = root / "cursor"
            v_old = cursor_dir / "versions" / "2026.10.01-aaaa111"
            v_new = cursor_dir / "versions" / "2026.11.11-b912975"
            v_old.mkdir(parents=True)
            v_new.mkdir(parents=True)
            for ver_dir in (v_old, v_new):
                (ver_dir / "node.exe").write_bytes(b"")
                (ver_dir / "index.js").write_text("", encoding="utf-8")
            ps1 = cursor_dir / "cursor-agent.ps1"
            ps1.write_text("# wrapper\n", encoding="utf-8")
            agent_cmd = cursor_dir / "agent.cmd"
            agent_cmd.write_text(
                'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\\cursor-agent.ps1" %*\n',
                encoding="utf-8",
            )
            with patch.object(_win32, "find_command_path", return_value=str(agent_cmd)):
                self.assertEqual(
                    _win32.resolve_command("agent"),
                    [str(v_new / "node.exe"), str(v_new / "index.js")],
                )

            # Surrounding quotes around executable paths are stripped cleanly.
            found = _shared.find_command_with_dirs(f'"{grok_cmd}"', lambda _h: [])
            self.assertEqual(found, str(grok_cmd))

    def test_read_npm_prefix_dirs_picks_up_npmrc_and_env(self):
        from bridge.pal import _win32

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            custom_npm = Path(tmp) / "custom_npm"
            env_npm = Path(tmp) / "env_npm"
            custom_npm.mkdir()
            env_npm.mkdir()
            (home / ".npmrc").write_text(f"prefix={custom_npm}\ncache=D:\\npm\\cache\n", encoding="utf-8")
            with patch.dict(os.environ, {"NPM_CONFIG_PREFIX": str(env_npm), "APPDATA": str(home)}, clear=False):
                dirs = _win32._read_npm_prefix_dirs(str(home))
            self.assertIn(str(env_npm), dirs)
            self.assertIn(str(custom_npm), dirs)

    def test_installed_app_names_caching_and_posix_empty(self):
        from bridge.pal import _posix, _win32

        self.assertEqual(_posix.installed_app_names(), frozenset())

        class FakeKey:
            def __init__(self, subkeys=(), value=None):
                self._subkeys = subkeys
                self._value = value

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        fake_winreg = types.SimpleNamespace(
            HKEY_CURRENT_USER=1,
            HKEY_LOCAL_MACHINE=2,
            OpenKey=lambda root, sub: FakeKey(["app1"]) if "Uninstall" in sub else FakeKey(value="Cursor App"),
            QueryInfoKey=lambda key: (len(key._subkeys),),
            EnumKey=lambda key, idx: key._subkeys[idx],
            QueryValueEx=lambda key, name: (key._value, 1),
        )
        _win32._APP_NAMES.update(at=0.0, names=frozenset())
        with patch.dict(sys.modules, {"winreg": fake_winreg}):
            names = _win32.installed_app_names(ttl=30.0)
            self.assertIn("cursor app", names)

    def test_start_menu_and_shortcut_resolution(self):
        from bridge.pal import _posix, _win32

        self.assertEqual(_posix.start_menu_dirs(), [])
        self.assertEqual(_posix.resolve_shortcut_target("foo.lnk", 1, 10), "")

        with tempfile.TemporaryDirectory() as tmp:
            programs = Path(tmp) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            programs.mkdir(parents=True)
            with patch.dict(os.environ, {"APPDATA": tmp, "ProgramData": ""}, clear=False):
                self.assertEqual(_win32.start_menu_dirs(), [str(programs)])

            _win32._shortcut_targets.clear()
            done = types.SimpleNamespace(returncode=0, stdout=b"D:\\Apps\\Cursor.exe\n")
            with patch.object(_win32.subprocess, "run", return_value=done) as run_mock:
                target = _win32.resolve_shortcut_target("C:\\Menu\\Cursor.lnk", 123, 456)
                cached = _win32.resolve_shortcut_target("C:\\Menu\\Cursor.lnk", 123, 456)
            self.assertEqual(target, "D:\\Apps\\Cursor.exe")
            self.assertEqual(cached, "D:\\Apps\\Cursor.exe")
            run_mock.assert_called_once()

    def test_kill_process_tree_falls_back_to_kill(self):
        from bridge.pal import _posix, _win32

        proc = Mock()
        proc.pid = 4321
        with patch.object(_win32.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)) as run_mock:
            _win32.kill_process_tree(proc)
        run_mock.assert_called_once()
        self.assertEqual(run_mock.call_args.args[0], ["taskkill", "/F", "/T", "/PID", "4321"])
        proc.kill.assert_not_called()

        proc2 = Mock()
        proc2.pid = 999
        with patch.object(_win32.subprocess, "run", side_effect=OSError("no taskkill")):
            _win32.kill_process_tree(proc2)
        proc2.kill.assert_called_once()

        proc3 = Mock()
        _posix.kill_process_tree(proc3)
        proc3.kill.assert_called_once()

    def test_kill_process_tree_falls_back_when_taskkill_returns_failure(self):
        from bridge.pal import _win32

        proc = Mock()
        proc.pid = 4321
        with patch.object(_win32.subprocess, "run", return_value=types.SimpleNamespace(returncode=1)):
            _win32.kill_process_tree(proc)
        proc.kill.assert_called_once()

    def test_exclusive_socket_options(self):
        from bridge.pal import _posix, _win32

        self.assertTrue(_posix.socket_reuse_allowed())
        self.assertFalse(_win32.socket_reuse_allowed())

        sock = Mock()
        _posix.apply_exclusive_socket(sock)
        sock.setsockopt.assert_not_called()

        with patch.object(socket, "SO_EXCLUSIVEADDRUSE", 999, create=True):
            _win32.apply_exclusive_socket(sock)
        sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, 999, 1)

    def test_can_install_and_launch_hidden_powershell(self):
        from bridge.pal import _posix, _win32

        self.assertFalse(_posix.can_install_desktop_update(True, "/tmp/AnYCore"))
        with self.assertRaises(OSError):
            _posix.launch_hidden_powershell("abc", {})

        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "AnYCore.exe"
            gui = Path(tmp) / "AnY.exe"
            core.write_bytes(b"")
            self.assertFalse(_win32.can_install_desktop_update(True, str(core)))
            gui.write_bytes(b"")
            self.assertTrue(_win32.can_install_desktop_update(True, str(core)))
            self.assertFalse(_win32.can_install_desktop_update(False, str(core)))

    def test_common_aliases_match_pal(self):
        from bridge import common, pal

        self.assertEqual(common.NO_WINDOW, pal.subprocess_kwargs())
        proc = Mock()
        with patch.object(pal, "kill_process_tree") as mocked:
            common.kill_tree(proc)
        mocked.assert_called_once_with(proc)

    def test_member_package_bundles_pal(self):
        import zipfile

        from bridge import member_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = Path(__file__).resolve().parents[1]
            for rel in ("bridge", "packaging", "LICENSE"):
                src = repo / rel
                dst = root / rel
                if src.is_dir():
                    import shutil
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    dst.write_bytes(src.read_bytes())
            (root / "static").mkdir(exist_ok=True)
            out = member_package.build(root)
            with zipfile.ZipFile(out) as zf:
                names = set(zf.namelist())
            self.assertIn("bridge/pal/__init__.py", names)
            self.assertIn("bridge/pal/_win32.py", names)
            self.assertIn("bridge/pal/_posix.py", names)
            self.assertIn("bridge/pal/_shared.py", names)


if __name__ == "__main__":
    unittest.main()
