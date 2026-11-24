# -*- coding: utf-8 -*-
"""Windowed builds have no console: keep stdio usable and package as GUI."""
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_roundtable():
    spec = importlib.util.spec_from_file_location("roundtable_headless_test", ROOT / "roundtable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stdio(unittest.TestCase):
    def test_keeps_existing_streams(self):
        module = load_roundtable()
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            module.ensure_stdio()
            self.assertIs(sys.stdout, out)
            self.assertIs(sys.stderr, err)

    def test_without_console_writes_to_log(self):
        module = load_roundtable()
        original_out, original_err = sys.stdout, sys.stderr
        stream = None
        with tempfile.TemporaryDirectory() as tmp:
            try:
                with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None), \
                        patch.object(module, "_attach_console", return_value=False), \
                        patch.dict(os.environ, {"ROUNDTABLE_LOG_DIR": tmp}):
                    module.ensure_stdio()
                    stream = sys.stdout
                    self.assertIsNotNone(stream)
                    self.assertIs(stream, sys.stderr)
                    stream.write("windowed line\n")
                    stream.flush()
                log = Path(tmp) / "any.log"
                self.assertTrue(log.exists())
                self.assertIn("windowed line", log.read_text(encoding="utf-8"))
            finally:
                if stream is not None:
                    stream.close()
                sys.stdout, sys.stderr = original_out, original_err


class Packaging(unittest.TestCase):
    def test_windows_build_is_windowed(self):
        build = (ROOT / "build_exe.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("--windowed", build)
        self.assertIn("--onefile", build)
        self.assertIn("--onedir", build)
        self.assertIn("AnYCore", build)
        for spec in ("AnY.spec", "AnYCore.spec", "AIBridge.spec"):
            spec_path = ROOT / spec
            if spec_path.is_file():
                text = spec_path.read_text(encoding="utf-8")
                self.assertRegex(text, r"console\s*=\s*False", spec)

    def test_source_launcher_is_headless(self):
        starter = (ROOT / "start.bat").read_text(encoding="utf-8-sig").lower()
        self.assertIn("pythonw", starter)
        self.assertNotIn("pause", starter)


class DesktopPackaging(unittest.TestCase):
    def test_optional_dependency_and_build_script(self):
        import json, tomllib
        from bridge.version import VERSION
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["dependencies"], [])
        self.assertIn("pywebview>=5.3", config["project"]["optional-dependencies"]["desktop"])
        self.assertEqual(config["project"]["version"], VERSION)
        build = (ROOT / "build_desktop.ps1").read_text(encoding="utf-8-sig")
        for token in ("cargo build --release", "desktop_tauri", "any-desktop.exe", "sign_exe.ps1"):
            self.assertIn(token, build)
        conf = json.loads((ROOT / "desktop_tauri" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
        self.assertEqual(conf["version"], VERSION)
        self.assertFalse(conf["app"]["withGlobalTauri"])
        cap = json.loads((ROOT / "desktop_tauri" / "src-tauri" / "capabilities" / "main.json").read_text(encoding="utf-8"))
        self.assertEqual(cap["windows"], ["main"])
        self.assertEqual(cap["permissions"], ["allow-any-choose-workdir", "allow-any-choose-agent-file"])
        self.assertFalse(cap["local"])
        self.assertEqual(cap["remote"]["urls"], [])  # exact port is granted at runtime

    def test_release_includes_desktop_zip_and_readme(self):
        readme = (ROOT / "packaging" / "desktop-readme.txt").read_text(encoding="utf-8")
        for token in ("AnY.exe", "AnYCore.exe", "_internal", "同一个文件夹", "WebView2", "浏览器"):
            self.assertIn(token, readme)
        release = (ROOT / "packaging" / "build_release.py").read_text(encoding="utf-8")
        for token in ("AnY-Desktop-", "AnYCore.exe", "_internal", "desktop-readme.txt"):
            self.assertIn(token, release)
        member = (ROOT / "packaging" / "connect-member.bat").read_text(encoding="utf-8-sig")
        self.assertLess(member.index("AnYCore.exe"), member.index("AnY.exe"))

    def test_desktop_installer_cleans_internal_and_preserves_data(self):
        from bridge.version import VERSION
        iss = (ROOT / "packaging" / "any-desktop.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define MyAppVersion "{VERSION}"', iss)
        self.assertIn(f'#define OutputName "AnY-Setup-{VERSION}-test"', iss)
        self.assertIn(f'#define OutputName "AnY-Setup-{VERSION}"', iss)
        self.assertIn(r'Source: "..\dist\AnYCore\AnYCore.exe"; DestDir: "{app}"; DestName: "AnYCore.exe"', iss)
        self.assertIn(r'Source: "..\dist\AnYCore\_internal\*"; DestDir: "{app}\_internal"', iss)
        self.assertIn('[InstallDelete]', iss)
        self.assertIn('[UninstallDelete]', iss)
        self.assertIn(r'Type: filesandordirs; Name: "{app}\_internal"', iss)
        self.assertIn('PrepareToInstall', iss)
        self.assertIn('HasWebView2Runtime', iss)
        self.assertNotIn(r'{app}\data', iss)

    def test_build_release_packs_onedir_desktop_and_onefile_portable(self):
        import shutil, subprocess, zipfile, tomllib
        version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            for folder in ("bridge", "docs", "examples", "packaging", "static"):
                shutil.copytree(ROOT / folder, stage / folder)
            for file in ("pyproject.toml", "LICENSE"):
                shutil.copy2(ROOT / file, stage / file)
            if not (stage / "static" / "member-connector.zip").is_file():
                (stage / "static" / "member-connector.zip").write_bytes(b"member")
            dist = stage / "dist"
            (dist / "AnYCore" / "_internal" / "static").mkdir(parents=True)
            (dist / "AnY.exe").write_bytes(b"portable-onefile")
            (dist / "AnYDesktop.exe").write_bytes(b"desktop-shell")
            (dist / "AnYCore" / "AnYCore.exe").write_bytes(b"core-onedir")
            (dist / "AnYCore" / "_internal" / "python312.dll").write_bytes(b"pydll")
            (dist / "AnYCore" / "_internal" / "static" / "app.js").write_bytes(b"js")
            env = dict(os.environ, ANY_REQUIRE_SIGNATURE="0")
            res = subprocess.run([sys.executable, str(stage / "packaging" / "build_release.py")],
                                 cwd=stage, env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            with zipfile.ZipFile(dist / f"AnY-{version}-win64.zip") as portable_zip:
                self.assertIn("AnY.exe", portable_zip.namelist())
                self.assertEqual(portable_zip.read("AnY.exe"), b"portable-onefile")
                self.assertFalse(any(n.startswith("_internal/") for n in portable_zip.namelist()))
            with zipfile.ZipFile(dist / f"AnY-Desktop-{version}-win64.zip") as desktop_zip:
                names = set(desktop_zip.namelist())
                self.assertIn("AnY.exe", names)
                self.assertIn("AnYCore.exe", names)
                self.assertIn("_internal/python312.dll", names)
                self.assertIn("_internal/static/app.js", names)
                self.assertEqual(desktop_zip.read("AnY.exe"), b"desktop-shell")
                self.assertEqual(desktop_zip.read("AnYCore.exe"), b"core-onedir")


if __name__ == "__main__":
    unittest.main()
