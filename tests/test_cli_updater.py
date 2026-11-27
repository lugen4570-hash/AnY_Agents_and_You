"""Tests for separated CLI updater, /update command, CLI manifest, and Desktop separation."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import test_contacts_access as support
from bridge import cli, cli_updater
from bridge.version import CLI_VERSION, VERSION

ROOT = Path(__file__).resolve().parents[1]


def _make_tar_bundle(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel, payload in files.items():
            info = tarfile.TarInfo(rel)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


class CliUpdaterTests(unittest.TestCase):
    def test_parse_manifest_validates_origin_commit_and_version(self):
        bundle = _make_tar_bundle({"AnY-CLI/pyproject.toml": b'[project]\nname="ai-bridge-room"\n'})
        commit = "a" * 40
        sha = hashlib.sha256(bundle).hexdigest()
        manifest = {
            "app": "AnY-CLI",
            "version": "2.9.0",
            "commit": commit,
            "url": f"{cli_updater.DEFAULT_BASE}cli/any-cli-{commit}.tar.gz",
            "sha256": sha,
            "size": len(bundle),
            "notes": "CLI release",
        }
        parsed = cli_updater.parse_manifest(manifest, base=cli_updater.DEFAULT_BASE)
        self.assertEqual(parsed["version"], "2.9.0")
        self.assertEqual(parsed["commit"], commit)

        with self.assertRaises(ValueError):
            cli_updater.parse_manifest({**manifest, "app": "AnY"})
        with self.assertRaises(ValueError):
            cli_updater.parse_manifest({**manifest, "url": "https://evil.example/any.tar.gz"})
        with self.assertRaises(ValueError):
            cli_updater.parse_manifest({**manifest, "sha256": "deadbeef"})
        with self.assertRaises(ValueError):
            cli_updater.parse_manifest({**manifest, "version": "bad-ver"})

    def test_check_uses_cli_version_independently_of_desktop_version(self):
        bundle = _make_tar_bundle({"AnY-CLI/pyproject.toml": b'[project]\nname="ai-bridge-room"\n'})
        commit = "b" * 40
        manifest = {
            "app": "AnY-CLI",
            "version": "99.0.0",
            "commit": commit,
            "url": f"{cli_updater.DEFAULT_BASE}cli/any-cli-{commit}.tar.gz",
            "sha256": hashlib.sha256(bundle).hexdigest(),
            "size": len(bundle),
            "notes": "仅 CLI 端更新",
        }
        with patch.object(cli_updater, "_download_bytes", return_value=json.dumps(manifest).encode("utf-8")):
            res = cli_updater.check(Path(__file__))
        self.assertEqual(res["state"], "available")
        self.assertEqual(res["channel"], "cli")
        self.assertEqual(res["current"], CLI_VERSION)
        self.assertEqual(res["latest"], "99.0.0")
        self.assertEqual(res["mode"], "source")
        self.assertFalse(res["can_install"])

        up_to_date = {**manifest, "version": CLI_VERSION}
        with patch.object(cli_updater, "_download_bytes", return_value=json.dumps(up_to_date).encode("utf-8")):
            res2 = cli_updater.check(Path(__file__))
        self.assertEqual(res2["state"], "current")

    def test_managed_install_switches_launcher_without_touching_running_gen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "AnYCLI"
            old_gen = root / f"release-{'1'*12}-old"
            stale_gen = root / f"release-{'2'*12}-stale"
            for g in (old_gen, stale_gen):
                (g / "AnY-CLI" / "bridge").mkdir(parents=True)
                (g / "venv").mkdir()
                (g / ".complete").write_text("0" * 64, encoding="utf-8")
            fake_pkg_file = old_gen / "AnY-CLI" / "bridge" / "cli_updater.py"
            fake_pkg_file.write_text("# stub", encoding="utf-8")

            bundle = _make_tar_bundle({"AnY-CLI/pyproject.toml": b'[project]\nname="ai-bridge-room"\n'})
            new_commit = "c" * 40
            digest = hashlib.sha256(bundle).hexdigest()
            manifest = {
                "app": "AnY-CLI",
                "version": "99.1.0",
                "commit": new_commit,
                "url": f"{cli_updater.DEFAULT_BASE}cli/any-cli-{new_commit}.tar.gz",
                "sha256": digest,
                "size": len(bundle),
                "notes": "CLI upgrade",
            }

            with patch.object(cli_updater, "_download_bytes", side_effect=[json.dumps(manifest).encode("utf-8"), bundle]):
                checked = cli_updater.check(fake_pkg_file)
                self.assertTrue(checked["can_install"])
                self.assertEqual(checked["state"], "available")

                def fake_setup(r: Path, gen: Path, interp: Path) -> None:
                    self.assertEqual(r, root)
                    interp.parent.mkdir(parents=True, exist_ok=True)
                    interp.write_text("python-stub", encoding="utf-8")

                with patch.object(cli_updater, "_setup_venv", side_effect=fake_setup):
                    installed = cli_updater.install_update(checked["release"], fake_pkg_file)

            self.assertEqual(installed["state"], "installed")
            self.assertEqual(installed["installed"], "99.1.0")
            launcher = Path(installed["launcher"])
            self.assertTrue(launcher.is_file())
            new_gen = Path(installed["generation"])
            self.assertEqual((new_gen / ".complete").read_text(encoding="utf-8"), digest)
            self.assertIn(new_gen.name, launcher.read_text(encoding="utf-8"))
            self.assertTrue(old_gen.is_dir())
            self.assertFalse(stale_gen.exists())

            with self.assertRaises(ValueError):
                cli_updater.install_update(checked["release"], Path(__file__))

    def test_install_rejects_unsafe_tar_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "AnYCLI"
            gen = root / f"release-{'1'*12}-old"
            (gen / "AnY-CLI" / "bridge").mkdir(parents=True)
            (gen / ".complete").write_text("0" * 64, encoding="utf-8")
            fake_pkg_file = gen / "AnY-CLI" / "bridge" / "cli_updater.py"
            fake_pkg_file.write_text("# stub", encoding="utf-8")
            bad_bundle = _make_tar_bundle({"../evil.txt": b"boom"})
            release = {
                "version": "99.0.0",
                "commit": "d" * 40,
                "sha256": hashlib.sha256(bad_bundle).hexdigest(),
                "size": len(bad_bundle),
                "url": f"{cli_updater.DEFAULT_BASE}cli/any-cli-{'d'*40}.tar.gz",
                "notes": "",
            }
            with patch.object(cli_updater, "_download_bytes", return_value=bad_bundle):
                with self.assertRaisesRegex(ValueError, "不安全"):
                    cli_updater.install_update(release, fake_pkg_file)

    def test_cli_update_subcommand_checks_and_prints_json(self):
        out = io.StringIO()
        with patch.object(cli_updater, "check", return_value={
            "state": "current",
            "channel": "cli",
            "current": CLI_VERSION,
            "latest": CLI_VERSION,
            "commit": "e" * 40,
            "sha256": "f" * 64,
            "size": 100,
            "url": "",
            "notes": "",
            "mode": "source",
            "can_install": False,
            "root": str(ROOT),
            "launcher": "",
            "release": None,
            "error": "",
        }), patch("sys.stdout", out):
            rc = cli.main(["update", "--check", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["channel"], "cli")
        self.assertEqual(payload["current"], CLI_VERSION)
        self.assertEqual(payload["state"], "current")

    def test_desktop_update_endpoint_separates_cli_launched_backend(self):
        with patch.dict(os.environ, {"ROUNDTABLE_CLI_MODE": "1"}):
            code_chk, data_chk = support.call("/api/update/check", owner=True)
            self.assertEqual(code_chk, 200)
            self.assertEqual(data_chk["state"], "cli_only")
            self.assertEqual(data_chk["desktop_version"], VERSION)
            code_dl, data_dl = support.call("/api/update/download", {}, owner=True)
            self.assertEqual(code_dl, 409)
            self.assertIn("CLI", data_dl["error"])
            code_ins, _ = support.call("/api/update/install", {}, owner=True)
            self.assertEqual(code_ins, 409)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for the update UI test")
    def test_desktop_update_ui_hides_entry_when_backend_is_cli_mode(self):
        code = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
function node(id){
 return elements[id]||=({innerHTML:'',disabled:false,hidden:true,classes:new Set(),
  classList:{toggle(k,v){if(v)this.s.add(k);else this.s.delete(k)},contains(k){return this.s.has(k)},s:null},
  insertAdjacentHTML(){}});
}
const updateNode=node('updateApp');updateNode.classList.s=updateNode.classes;
const ctx=vm.createContext({document:{getElementById:node},esc:String,showModal(){},hideModal(){},
 setTimeout:()=>1,clearTimeout(){},
 fetch:async()=>({ok:true,json:async()=>({state:'cli_only',current:'2.8.40'})}),post:async()=>[true,{}]});
vm.runInContext(fs.readFileSync('static/update.js','utf8'),ctx);
(async()=>{
 node('updateApp').onclick();
 await new Promise(r=>global.setTimeout(r,10));
 assert.equal(updateNode.hidden,true);
 assert.match(node('updateContent').innerHTML,/CLI 后台/);
 assert.match(node('updateContent').innerHTML,/\/update/);
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        r = subprocess.run(["node", "-e", code], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_make_cli_manifest_reads_cli_version(self):
        script = ROOT / "packaging" / "make_cli_manifest.py"
        spec = importlib.util.spec_from_file_location("any_cli_manifest_generator", script)
        self.assertIsNotNone(spec)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            (troot / "bridge").mkdir()
            (troot / "website").mkdir()
            (troot / "bridge" / "version.py").write_text('VERSION = "2.8.39"\nCLI_VERSION = "2.8.40"\n', encoding="utf-8")
            with patch.object(mod, "ROOT", troot), patch.object(sys, "argv", ["make_cli_manifest.py", "--notes", "测试 CLI 说明"]):
                mod.main()
            generated = json.loads((troot / "website" / "cli-release.json").read_text(encoding="utf-8"))
            self.assertEqual(generated["app"], "AnY-CLI")
            self.assertEqual(generated["version"], "2.8.40")
            self.assertEqual(generated["notes"], "测试 CLI 说明")


if __name__ == "__main__":
    unittest.main()
