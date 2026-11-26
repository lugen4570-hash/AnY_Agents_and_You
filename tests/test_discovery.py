# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_BOOT_TMP = tempfile.mkdtemp(prefix="rt_disc_")
os.environ["ROUNDTABLE_LOG_DIR"] = _BOOT_TMP

from bridge import access, common, connections, discovery, install, registry


class TestDiscovery(unittest.TestCase):
    def test_discovery_only_commands_are_not_offered_as_automatic_drivers(self):
        entries = {entry["id"]: entry for entry in discovery.load_catalog()}
        for agent_id in ("devin", "cline", "kilo", "vibe"):
            with self.subTest(agent=agent_id), patch.object(discovery, "_find_cli", return_value="installed-agent"):
                item = discovery._inspect_entry(entries[agent_id], set(), {}, {}, {}, set())
                self.assertTrue(item["present"])
                self.assertEqual(item["level"], "unsupported")
                self.assertEqual(item["options"], [])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old_log = common.LOG_DIR
        common.LOG_DIR = discovery.LOG_DIR = connections.LOG_DIR = registry.LOG_DIR = access.LOG_DIR = self.tmp.name
        os.makedirs(os.path.join(self.tmp.name, "agents.d"), exist_ok=True)
        discovery._state.update(scanning=False, last_scan=0.0, items=[])

    def tearDown(self):
        common.LOG_DIR = discovery.LOG_DIR = connections.LOG_DIR = registry.LOG_DIR = access.LOG_DIR = self.old_log
        discovery._state.update(scanning=False, last_scan=0.0, items=[])
        self.tmp.cleanup()

    def test_scan_classifies_direct_and_mcp_agents(self):
        fake_bin = os.path.join(self.tmp.name, "claude.exe")
        Path(fake_bin).write_text("echo 1\n", encoding="utf-8")
        fake_desk = os.path.join(self.tmp.name, "Antigravity.exe")
        Path(fake_desk).write_text("desk\n", encoding="utf-8")

        fake_catalog = [
            {
                "id": "claude",
                "label": "Claude Code",
                "cli": {"driver": "claude", "bin": ["claude"], "paths": [fake_bin], "verified": True},
            },
            {
                "id": "antigravity",
                "label": "Google Antigravity",
                "desktop": {"detect": [fake_desk]},
                "mcp": {"id": "antigravity", "label": "Antigravity", "kind": "json", "path": os.path.join(self.tmp.name, "mcp.json")},
            },
            {
                "id": "missing-one",
                "label": "Missing Agent",
                "cli": {"driver": "cli", "bin": ["not-installed-xyz"]},
            },
        ]
        with patch.object(discovery, "load_catalog", return_value=fake_catalog), \
             patch.object(discovery, "_uninstall_names", return_value=set()), \
             patch.object(common, "find_executable", side_effect=lambda name, extra_paths=(): fake_bin if name == "claude" else None):
            st = discovery.scan()

        by_id = {x["id"]: x for x in st["items"]}
        self.assertTrue(by_id["claude"]["present"])
        self.assertEqual(by_id["claude"]["level"], "direct")
        self.assertTrue(by_id["antigravity"]["present"])
        self.assertEqual(by_id["antigravity"]["level"], "mcp")
        self.assertFalse(by_id["missing-one"]["present"])
        self.assertEqual(st["pending_count"], 2)

        discovery.dismiss("antigravity")
        st2 = discovery.status()
        self.assertEqual(st2["pending_count"], 1)

    def test_present_falls_back_to_uninstall_registry(self):
        """装在 D:\\cursor 这类非默认目录时，扫描和一键接入要得出同一个结论。"""
        host = {"id": "cursor", "label": "Cursor", "bin": [], "detect": [], "uninstall": ["cursor"]}
        with patch.object(install, "app_installed", return_value=True):
            self.assertTrue(install.present(host))
        with patch.object(install, "app_installed", return_value=False):
            self.assertFalse(install.present(host))

    def test_macos_detects_app_bundles_and_uses_native_mcp_config(self):
        bundle = Path(self.tmp.name, "Claude.app")
        (bundle / "Contents").mkdir(parents=True)
        (bundle / "Contents" / "Info.plist").touch()
        with patch.object(sys, "platform", "darwin"), patch.object(install, "HOSTS", []):
            install._load_catalog_hosts()
            hosts = {row["id"]: row for row in install.HOSTS}
            claude = hosts["claude-desktop"]
            self.assertIn("/Applications/Claude.app", claude["detect"])
            self.assertEqual(claude["path"], os.path.expanduser(
                "~/Library/Application Support/Claude/claude_desktop_config.json"))
            self.assertEqual(hosts["vscode"]["path"], os.path.expanduser(
                "~/Library/Application Support/Code/User/mcp.json"))
            self.assertTrue(registry._detected({"desktop": {"path": str(bundle)}}))
            with patch.object(install, "FROZEN", False):
                self.assertEqual(install._stdio_command(), (sys.executable, [str(ROOT / "roundtable.py"), "mcp-stdio"]))

    def test_user_saved_cli_is_not_connected_after_failed_verification(self):
        entry={'id':'failed-cli','cli':{'bin':['fake']}}
        spec={'enabled':True,'driver':'cli','user':True}
        with patch.object(discovery,'_find_cli',return_value='fake.exe'):
            item=discovery._inspect_entry(entry,set(),{'failed-cli':spec},{'failed-cli':{'state':'failed'}},{},set())
        self.assertFalse(item['connected'])

    def test_configured_desktop_does_not_repeatedly_prompt_as_new(self):
        discovery._state['items']=[{'id':'desktop','present':True,'level':'mcp','mcp_installed':True,'mcp_configured':True,'connected':False}]
        self.assertEqual(discovery.status()['pending_count'],0)

    def test_leftover_mcp_file_is_not_an_installed_desktop(self):
        entry={'id':'removed-desktop','mcp':{'id':'old-host'}}
        with patch.object(discovery,'_find_cli',return_value=None),patch.object(discovery,'_find_desktop',return_value=None):
            item=discovery._inspect_entry(entry,set(),{},{},{'old-host':{'installed':True}},set())
        self.assertFalse(item['present'])

    def test_failed_mcp_install_preserves_direct_driver_and_credentials(self):
        from bridge import agent_settings
        desktop=Path(self.tmp.name,'desktop.exe');desktop.write_text('fake desktop',encoding='utf-8')
        host={'id':'preserve-host','label':'Desktop','kind':'json-serverurl','path':str(Path(self.tmp.name,'mcp.json')),'detect':[str(desktop)]}
        entry={'id':'preserve-agent','label':'Preserve','cli':{'bin':[sys.executable]},'desktop':{'detect':[str(desktop)]},'mcp':host}
        registry.save_agent({'id':'preserve-agent','driver':'cli','bin':[sys.executable],'args':{'new':['custom','{prompt}']}})
        old=access.credential('preserve-agent')
        install.HOSTS.append(host)
        try:
            with patch.object(discovery,'load_catalog',return_value=[entry]),patch.object(discovery,'_uninstall_names',return_value=set()),patch.dict(install.INSTALLERS,{'json-serverurl':lambda host:(False,'failed host write')}):
                discovery.scan()
                ok,result=discovery.connect('preserve-agent','mcp',replace_key=True)
            self.assertFalse(ok,result)
            self.assertEqual(registry.get('preserve-agent')['driver'],'cli')
            self.assertEqual(registry.get('preserve-agent')['args']['new'],['custom','{prompt}'])
            self.assertEqual(access.identify(old),'preserve-agent')
        finally:
            install.HOSTS.remove(host)

    def test_connect_mcp_writes_config_and_returns_standby_prompt(self):
        mcp_path = os.path.join(self.tmp.name, "windsurf_mcp.json")
        fake_desk = os.path.join(self.tmp.name, "Windsurf.exe")
        Path(fake_desk).write_text("desk\n", encoding="utf-8")
        host = {"id": "windsurf-test", "label": "Windsurf", "kind": "json-serverurl",
                "path": mcp_path, "detect": [fake_desk], "restart": "重启 Windsurf"}
        fake_catalog = [{
            "id": "windsurf",
            "label": "Windsurf",
            "desktop": {"detect": [fake_desk]},
            "mcp": host,
        }]
        install.HOSTS.append(host)
        try:
            with patch.object(discovery, "load_catalog", return_value=fake_catalog), \
                 patch.object(discovery, "_uninstall_names", return_value=set()):
                discovery.scan()
                ok, res = discovery.connect("windsurf", via="mcp")
            self.assertTrue(ok, res)
            self.assertEqual(res["via"], "mcp")
            self.assertEqual(res["standby_prompt"], "/any_standby")
            written = json.loads(Path(mcp_path).read_text(encoding="utf-8"))
            self.assertIn("ai-bridge", written["mcpServers"])
            self.assertIn("serverUrl", written["mcpServers"]["ai-bridge"])
            self.assertIn("Authorization", written["mcpServers"]["ai-bridge"]["headers"])
        finally:
            install.HOSTS[:] = [h for h in install.HOSTS if h["id"] != "windsurf-test"]

    def test_finds_cursor_agent_wrapper_and_desktop_shortcut(self):
        fake_dir = Path(self.tmp.name) / "cursor"
        fake_dir.mkdir()
        agent_cmd = fake_dir / "agent.cmd"
        agent_cmd.write_text('powershell -File "%SCRIPT_DIR%\\cursor-agent.ps1"\n', encoding="utf-8")
        cursor_exe = fake_dir / "Cursor.exe"
        cursor_exe.write_bytes(b"")
        entry = {
            "id": "cursor",
            "label": "Cursor",
            "cli": {"driver": "cli", "bin": ["cursor-agent"], "preset": "cursor"},
            "desktop": {"detect": [], "shortcuts": ["Cursor"]},
        }
        with patch.object(discovery, "load_catalog", return_value=[entry]), \
             patch.object(discovery, "_uninstall_names", return_value=set()), \
             patch.object(common, "find_executable", side_effect=lambda n, extra_paths=(): str(agent_cmd) if n == "agent" else None), \
             patch.object(registry, "_shortcut_present_path", return_value=str(cursor_exe)):
            st = discovery.scan()
        item = st["items"][0]
        self.assertTrue(item["present"])
        self.assertEqual(item["exe"], str(agent_cmd))
        self.assertEqual(item["desktop_path"], str(cursor_exe))
        self.assertEqual(item["kind"], "both")

    def test_qoder_catalog_and_prepare_upgrade_from_external_preset(self):
        catalog = discovery.load_catalog()
        by_id = {row["id"]: row for row in catalog}
        self.assertIn("grok", by_id)
        self.assertIn("qoderclicn", by_id["qoder"]["cli"]["bin"])
        self.assertIn("qodercn", by_id["qoder"]["cli"]["bin"])

        fake_qoder = Path(self.tmp.name) / "qodercn.cmd"
        fake_qoder.write_text("@exit /b 0\n", encoding="utf-8")
        fake_desk = Path(self.tmp.name) / "Qoder CN Launcher.exe"
        fake_desk.write_bytes(b"")
        with patch.object(discovery, "load_catalog", return_value=[by_id["qoder"]]), \
             patch.object(discovery, "_uninstall_names", return_value=set()), \
             patch.object(common, "find_executable", side_effect=lambda n, extra_paths=(): str(fake_qoder) if n == "qodercn" else None), \
             patch.object(registry, "_shortcut_present_path", return_value=str(fake_desk)):
            st = discovery.scan()
            self.assertTrue(st["items"][0]["present"])
            self.assertEqual(st["items"][0]["level"], "direct")
            prep = discovery.prepare("qoder", "cli")
        self.assertEqual(prep["id"], "qoder")
        spec = registry.get("qoder")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["driver"], "cli")
        self.assertEqual(spec["id"], "qoder")


if __name__ == "__main__":
    unittest.main()
