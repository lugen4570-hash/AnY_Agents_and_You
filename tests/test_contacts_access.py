"""Contacts, projects and authenticated external access. No real AI calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from urllib.parse import quote

DATA = tempfile.mkdtemp(prefix="bridge_contacts_")
os.environ["ROUNDTABLE_LOG_DIR"] = DATA
os.environ["ROUNDTABLE_NO_PRESETS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import access, agents, common, install, mcp, projects, registry, room as R, web

agents.prewarm = lambda *a: None
registry.load()
srv = web.ExclusiveServer(("127.0.0.1", 0), web.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%s" % srv.server_address[1]


def call(path, obj=None, key=None, owner=False, headers=None):
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = "Bearer " + key
    if owner:
        h["X-RT-Token"] = web.RT_TOKEN
    h.update(headers or {})
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode() if obj is not None else None, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class Contacts(unittest.TestCase):
    def setUp(self):
        registry.save_agent({"id": "alice", "label": "Alice", "kind": "user", "driver": "external", "enabled": True})
        registry.save_agent({"id": "bot", "driver": "external", "enabled": True})
        self.key = access.credential("alice")
        self.bot_key = access.credential("bot")
        self.r = R.rooms.create("受邀", "测试目标", DATA, participants=["alice", "bot"])
        self.other = R.rooms.create("私有会话", "", DATA, participants=[])
        self.r.set_members(["alice", "bot"], {"alice": {"trigger": False}, "bot": {"post": False}})

    def test_contacts_do_not_join_existing_rooms(self):
        self.assertEqual(self.other.ais, [])
        self.assertEqual(R.fix_meta(dict(self.other.meta))["participants"], [])

    def test_project_creation_and_members_at_creation(self):
        status, data = call("/api/projects/new", {"name": "示例项目", "workdir": DATA}, owner=True)
        self.assertEqual(status, 200)
        p = data["project"]
        status, data = call("/api/rooms/new", {"title": "第一条会话", "project": p["id"], "participants": ["alice"]}, owner=True)
        self.assertEqual(status, 200)
        r = R.rooms.get(data["id"])
        self.assertEqual((r.meta["project"], r.ais, r.workdir()), (p["id"], ["alice"], DATA))
        self.assertFalse(r.meta["permissions"]["alice"]["work"])
        self.assertEqual(call("/api/rooms/new", {"project": "invalid"}, owner=True)[0], 400)

    def test_macos_folder_picker_is_local_and_can_cancel(self):
        path = "/api/projects/choose-workdir"
        with patch.object(web.sys, "platform", "darwin"), \
             patch.object(projects, "choose_macos_workdir", side_effect=[DATA, None, OSError("unavailable")]) as choose:
            self.assertEqual(call(path, {})[0], 403)
            forwarded = {"X-Forwarded-For": "10.0.0.2"}
            self.assertEqual(call(path, {}, owner=True, headers=forwarded)[0], 403)
            choose.assert_not_called()
            self.assertEqual(call(path, {}, owner=True), (200, {"workdir": DATA}))
            self.assertEqual(call(path, {}, owner=True), (200, {"workdir": None}))
            self.assertEqual(call(path, {}, owner=True)[0], 503)
        with patch.object(web.sys, "platform", "win32"):
            self.assertEqual(call(path, {}, owner=True)[0], 404)

    def test_delete_empty_project_after_moving_live_and_archived_rooms(self):
        with tempfile.TemporaryDirectory(dir=DATA) as destination_dir:
            source = projects.create("源项目", DATA)
            destination = projects.create("目标项目", destination_dir)
            active = R.rooms.create("进行中", wd=DATA, project=source["id"], participants=[])
            archived = R.rooms.create("已归档", wd=DATA, project=source["id"], participants=[])
            active.add_message("用户", "迁移后仍可读取")
            R.set_archived(archived.id, True)
            R.rooms.unload(archived.id)
            delete = "/api/projects/delete"
            move = "/api/rooms/move"
            self.assertEqual(call(delete, {"id": source["id"]}, owner=True)[0], 409)
            self.assertEqual(call(move, {"id": active.id, "project": destination["id"]}, key=self.key)[0], 403)
            self.assertEqual(call(move, {"id": active.id, "project": "invalid"}, owner=True)[0], 404)
            for meeting in (active, archived):
                self.assertEqual(call(move, {"id": meeting.id, "project": destination["id"]}, owner=True)[0], 200)
                self.assertEqual(common.read_json(os.path.join(meeting.dir, "meeting.json"))["project"], destination["id"])
            self.assertEqual(call(delete, {"id": source["id"]}, owner=True)[0], 200)
            _, listing = call("/api/rooms", owner=True)
            self.assertNotIn(source["id"], {p["id"] for p in listing["projects"]})
            rows = {r["id"]: r for r in listing["rooms"]}
            self.assertEqual(rows[active.id]["project"], destination["id"])
            self.assertEqual(rows[active.id]["workdir"], DATA)
            self.assertTrue(rows[archived.id]["archived"])
            self.assertEqual(active.messages[-1]["text"], "迁移后仍可读取")
            self.assertTrue(Path(DATA).is_dir())

    def test_legacy_projects_are_stable(self):
        legacy = R.rooms.create("旧会话", "", DATA)
        rows = projects.listing([legacy.summary()])
        self.assertIn(projects.legacy_id(DATA), [p["id"] for p in rows])
        self.assertEqual(projects.legacy_id(DATA), projects.legacy_id(DATA))

    def test_only_invited_rooms_are_visible(self):
        status, data = call("/api/external/rooms", key=self.key)
        self.assertEqual(status, 200)
        self.assertIn(self.r.id, [r["id"] for r in data["rooms"]])
        self.assertNotIn(self.other.id, [r["id"] for r in data["rooms"]])
        self.assertEqual(call("/api/external/messages?room=" + quote(self.other.id), key=self.key)[0], 403)

    def test_identity_cannot_be_spoofed_or_self_join(self):
        path = "/api/post"
        self.assertEqual(call(path, {"room": self.r.id, "text": "x"})[0], 401)
        self.assertEqual(call(path, {"room": self.r.id, "text": "x", "speaker": "bot"}, self.key)[0], 403)
        self.assertEqual(call(path, {"room": self.other.id, "text": "x", "join": True}, self.key)[0], 403)
        self.assertEqual(self.other.ais, [])
        self.assertEqual(call(path, {"text": "x"}, self.key)[0], 409)

    def test_readonly_and_posting(self):
        self.assertEqual(call("/api/post", {"room": self.r.id, "text": "hello"}, self.bot_key)[0], 403)
        self.assertEqual(call("/api/post", {"room": self.r.id, "text": "hello"}, self.key)[0], 200)
        self.assertEqual(self.r.messages[-1]["speaker"], "alice")
        self.r.add_message("系统", "quiet secret", quiet=True)
        status, data = call("/api/external/messages?room=" + quote(self.r.id), key=self.key)
        self.assertEqual(status, 200)
        self.assertNotIn("quiet secret", json.dumps(data))

    def test_human_contact_can_recall_only_own_message(self):
        self.r.set_members(["alice", "bot"], {"alice": {"trigger": False}, "bot": {"post": True}})
        owner_id = self.r.add_message("你", "管理员的话")["id"]
        bot_id = self.r.add_message("bot", "AI 的话")["id"]
        self.assertEqual(call("/api/post", {"room": self.r.id, "text": "访客的话"}, self.key)[0], 200)
        guest_id = self.r.messages[-1]["id"]
        path = "/api/external/recall"
        self.assertEqual(call(path, {"room": self.r.id, "id": owner_id}, self.key)[0], 403)
        self.assertEqual(call(path, {"room": self.r.id, "id": bot_id}, self.bot_key)[0], 403)
        status, recalled = call(path, {"room": self.r.id, "id": guest_id}, self.key)
        self.assertEqual(status, 200)
        self.assertEqual(recalled.get("draft"), {"text": "访客的话"})
        status, data = call("/api/external/messages?room=" + quote(self.r.id), key=self.key)
        self.assertEqual(status, 200)
        self.assertEqual((data["self"], data["recalled"]), ("alice", [guest_id]))
        self.assertEqual(data["messages"][-1]["text"], "消息已撤回")

    def test_rotation_revocation_and_hash_storage(self):
        self.assertNotIn(self.key, Path(DATA, "contact_keys.json").read_text(encoding="utf-8"))
        new = access.credential("alice")
        self.assertEqual(call("/api/external/rooms", key=self.key)[0], 401)
        self.assertEqual(call("/api/external/rooms", key=new)[0], 200)
        access.credential("alice", revoke=True)
        self.assertEqual(call("/api/external/rooms", key=new)[0], 401)

    def test_membership_removal_and_reload(self):
        self.r.meta["alice_session"] = "existing-session"
        self.r.set_members(["bot"], {})
        self.assertNotIn("alice", R.fix_meta(dict(self.r.meta))["participants"])
        self.assertEqual(call("/api/external/messages?room=" + quote(self.r.id), key=self.key)[0], 403)

    def test_permission_scope_and_validation(self):
        self.assertTrue(self.r.set_members(["alice"], {"alice": {"post": False}})[0])
        self.other.set_members(["alice"], {})
        self.assertFalse(access.allowed(self.r, "alice", "post"))
        self.assertTrue(access.allowed(self.other, "alice", "post"))
        for bad in ({"alice": {"work": "yes"}}, {"alice": {"admin": True}}, {"unknown": {}}):
            self.assertFalse(self.r.set_members(["alice"], bad)[0])

    def test_owner_api_is_not_external_api(self):
        for path in ("/api/rooms", "/api/agents", "/api/r/" + quote(self.r.id) + "/state"):
            self.assertEqual(call(path, key=self.key)[0], 403)
        self.assertEqual(call("/api/projects/new", {"name": "x", "workdir": DATA}, headers={"Sec-Fetch-Site": "same-origin"})[0], 403)

    def test_internal_tools_enforce_permissions(self):
        self.assertRaises(mcp.ToolError, mcp.call_room_tool, self.r.id, "bot", "post", {"text": "x"})
        self.assertRaises(mcp.ToolError, mcp.call_room_tool, self.r.id, "alice", "board", {"op": "add", "text": "x"})
        self.assertRaises(mcp.ToolError, mcp.call_room_tool, self.r.id, "alice", "post", {"files": [__file__]})
        self.assertEqual(self.r.member_mode("alice", "work"), "discuss")

    def test_trigger_permission(self):
        called=[]
        old=self.r.enqueue
        self.r.enqueue=lambda ai, **kw: called.append(ai)
        try:
            self.r.handle_message("alice", "@bot hello", origin="external")
            self.assertEqual(called, [])
        finally:
            self.r.enqueue=old

    def test_mcp_auth_and_scope(self):
        msg={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "read_room", "arguments": {"room": self.other.id}}}
        self.assertEqual(call("/mcp", msg)[0], 401)
        status, data=call("/mcp", msg, self.key)
        self.assertEqual(status, 200)
        self.assertTrue(data["result"]["isError"])
        msg["params"]={"name": "post_to_room", "arguments": {"room": self.r.id, "text": "MCP hello"}}
        self.assertFalse(call("/mcp", msg, self.key)[1]["result"]["isError"])

    def test_installer_credentials_and_backups(self):
        path=os.path.join(DATA, "mcp.json")
        common.write_json(path, {"other": True, "mcpServers": {"keep": {"url": "http://example.test"}}})
        self.assertTrue(install.install_json({"path": path, "token": "test-key"})[0])
        data=common.read_json(path)
        self.assertTrue(data["other"])
        self.assertIn("keep", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["ai-bridge"]["headers"]["Authorization"], "Bearer test-key")
        path=os.path.join(DATA, "config.toml")
        Path(path).write_text('[mcp_servers.ai-bridge]\nurl="old"\nstartup_timeout_sec=45\n[other]\nkeep=true\n', encoding="utf-8")
        self.assertTrue(install.install_toml({"path": path, "token": "new-key"})[0])
        import tomllib
        data=tomllib.loads(Path(path).read_text(encoding="utf-8"))
        self.assertTrue(data["other"]["keep"])
        self.assertEqual(data["mcp_servers"]["ai-bridge"]["startup_timeout_sec"], 45)
        self.assertEqual(data["mcp_servers"]["ai-bridge"]["http_headers"]["Authorization"], "Bearer new-key")

    def test_install_writes_atomically_preserving_existing_config(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            jpath = os.path.join(tmp, "mcp.json")
            orig_json = '{"mcpServers": {"keep": {"url": "http://127.0.0.1:1"}}}\n'
            Path(jpath).write_text(orig_json, encoding="utf-8")
            with mock.patch("json.dump", side_effect=OSError("write failed mid-stream")):
                with self.assertRaises(OSError):
                    install.install_json({"path": jpath, "token": "k1"})
            self.assertEqual(Path(jpath).read_text(encoding="utf-8"), orig_json)

            vpath = os.path.join(tmp, "variant.json")
            Path(vpath).write_text(orig_json, encoding="utf-8")
            with mock.patch("json.dump", side_effect=OSError("write failed mid-stream")):
                with self.assertRaises(OSError):
                    install.install_json_servers({"path": vpath, "token": "k2"})
            self.assertEqual(Path(vpath).read_text(encoding="utf-8"), orig_json)

            tpath = os.path.join(tmp, "config.toml")
            orig_toml = '[mcp_servers.ai-bridge]\nurl = "http://127.0.0.1:8766/mcp"\n'
            Path(tpath).write_text(orig_toml, encoding="utf-8")
            with mock.patch("bridge.install.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    install.install_toml({"path": tpath, "token": "k3"})
            self.assertEqual(Path(tpath).read_text(encoding="utf-8"), orig_toml)

            tpath2 = os.path.join(tmp, "config_append.toml")
            orig_toml2 = '[other]\nkeep = true\n'
            Path(tpath2).write_text(orig_toml2, encoding="utf-8")
            with mock.patch("bridge.install.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    install.install_toml({"path": tpath2, "token": "k4"})
            self.assertEqual(Path(tpath2).read_text(encoding="utf-8"), orig_toml2)


if __name__ == "__main__":
    unittest.main()
