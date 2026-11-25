"""Contacts, projects and authenticated external access. No real AI calls."""
import json
import os
from pathlib import Path
import shutil
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

    def test_project_update_persists_legacy_group_and_pins_existing_room(self):
        with tempfile.TemporaryDirectory(dir=DATA) as root:
            original = str(Path(root, "original"))
            replacement = str(Path(root, "replacement"))
            os.mkdir(original)
            os.mkdir(replacement)
            before = R.rooms.create("已有会议", wd=original, participants=[])
            pid = projects.legacy_id(original)
            settings = {"id": pid, "name": "新项目名", "workdirs": [replacement, original]}
            update = "/api/projects/update"
            self.assertEqual(call(update, settings, key=self.key)[0], 403)
            self.assertEqual(call(update, {**settings, "workdirs": [root + "-missing"]}, owner=True)[0], 400)
            self.assertEqual(call(update, settings, owner=True)[0], 200)
            _, listing = call("/api/rooms", owner=True)
            project = next(p for p in listing["projects"] if p["id"] == pid)
            self.assertEqual((project["name"], project["workdir"], project["workdirs"]), ("新项目名", replacement, [replacement, original]))
            self.assertEqual(before.workdir(), original)
            status, room = call("/api/rooms/new", {"project": pid, "participants": []}, owner=True)
            self.assertEqual(status, 200)
            self.assertEqual(R.rooms.get(room["id"]).workdir(), replacement)

    @unittest.skipUnless(shutil.which("git"), "Git is needed for linked worktree tests")
    def test_project_worktree_selection_uses_checked_out_branch(self):
        with tempfile.TemporaryDirectory(dir=DATA) as root:
            repo = str(Path(root, "repo"))
            linked = str(Path(root, "另一分支 worktree"))
            os.mkdir(repo)
            projects.git(["init", "-b", "main"], repo)
            projects.git(["commit", "--allow-empty", "-m", "initial"], repo)
            projects.git(["worktree", "add", "-b", "feature", linked], repo)
            project = projects.create("Repo", repo)
            status, result = call("/api/projects/workspaces", {"id": project["id"]}, owner=True)
            self.assertEqual(status, 200)
            self.assertEqual({w["path"]: w["branch"] for w in result["workspaces"]}, {repo: "main", linked: "feature"})
            payload = {"project": project["id"], "workspace": linked, "participants": []}
            self.assertEqual(call("/api/rooms/new", {**payload, "workspace": root}, owner=True)[0], 400)
            status, result = call("/api/rooms/new", payload, owner=True)
            self.assertEqual(status, 200)
            self.assertEqual(R.rooms.get(result["id"]).workdir(), linked)
            self.assertEqual(projects.git(["branch", "--show-current"], repo).strip(), b"main")

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

    def test_delete_project_directly_with_active_archived_and_trashed_rooms(self):
        with tempfile.TemporaryDirectory(dir=DATA) as workdir:
            project = projects.create("可直接删除", workdir)
            active = R.rooms.create("活跃", wd=workdir, project=project["id"], participants=[])
            archived = R.rooms.create("归档", wd=workdir, project=project["id"], participants=[])
            trashed = R.rooms.create("已进回收站", wd=workdir, project=project["id"], participants=[])
            R.set_archived(archived.id, True)
            R.trash_meeting(trashed.id)

            busy_project = projects.create("运行中项目", workdir)
            busy_room = R.rooms.create("运行中会话", wd=workdir, project=busy_project["id"], participants=[])
            with patch.object(R.Room, "busy_for", return_value=True):
                status, err = call("/api/projects/delete", {"id": busy_project["id"]}, owner=True)
                self.assertEqual(status, 409)
                self.assertIn("停止", err["error"])
            R.trash_meeting(busy_room.id)
            self.assertEqual(call("/api/projects/delete", {"id": busy_project["id"]}, owner=True)[0], 200)

            status, res = call("/api/projects/delete", {"id": project["id"]}, owner=True)
            self.assertEqual(status, 200)
            self.assertEqual(set(res["trashed_rooms"]), {active.id, archived.id})
            _, listing = call("/api/rooms", owner=True)
            self.assertNotIn(project["id"], {p["id"] for p in listing["projects"]})
            _, trash_data = call("/api/trash", owner=True)
            trash_ids = {item["id"] for item in trash_data["trash"]}
            self.assertTrue({active.id, archived.id, trashed.id}.issubset(trash_ids))
            self.assertTrue(Path(workdir).is_dir())

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

    def test_dispatch_ceiling_and_target_handoff_policy(self):
        registry.save_agent({"id": "sourcebot", "driver": "external", "enabled": True})
        try:
            room = self.other
            members = ["alice", "bot", "sourcebot"]
            self.assertTrue(room.set_members(members, {"alice": {"trigger": True}, "bot": {"work": True}})[0])
            self.assertTrue(room.set_mode("work")[0])
            room.set_contact_policies({"alice": {"call_agents": []}}, {"bot": {"accept_handoff": False}})
            owner = access.DispatchContext("你", "你", ceiling="discuss")
            self.assertEqual(access.can_dispatch(room, owner, "bot"), "")
            self.assertIn("未接受转派", access.can_dispatch(room, owner.handoff("sourcebot"), "bot"))
            guest = access.DispatchContext("alice", "alice", ceiling="work").handoff("sourcebot")
            self.assertIn("房间未允许", access.can_dispatch(room, guest, "bot"))
            self.assertEqual(access.effective_mode(room, owner, "bot", "work"), "discuss")
            self.assertEqual(access.effective_mode(room, guest, "bot", "work"), "discuss")
        finally:
            registry.remove_agent("sourcebot")

    def test_external_discussion_requires_both_grants_and_keeps_owner_context_private(self):
        ok, error = registry.save_agent({"id": "public-model", "driver": "http", "http_protocol": "openai_chat",
                                         "endpoint": "https://models.example.test/v1", "token": "test-key",
                                         "default": ["review-model", ""], "enabled": True})
        self.assertTrue(ok, error)
        try:
            room = self.other
            room.add_message("你", "入房之前的内容")
            self.assertTrue(room.set_mode("work")[0])
            self.assertTrue(room.set_members(["alice", "bot", "public-model"], {"alice": {"work": True}})[0])
            room.add_message("bot", "本机 Agent 的私有输出")
            room.meta["public-model_session"] = "private-session"
            endpoint = "/api/external/messages?room=" + quote(room.id)
            with patch.object(R.direct_model, "reply", return_value="公开讨论的回复") as model, \
                    patch.object(R, "ai_caller") as native:
                def ask(text):
                    status, result = call("/api/post", {"room": room.id, "text": text}, self.key)
                    self.assertEqual(status, 200)
                    return result.get("dispatch_errors")

                self.assertIn("房间未允许", ask("@public-model 第一条")[0]["reason"])
                self.assertTrue(room.set_members(list(room.ais), {"alice": {"trigger": True, "work": True}})[0])
                self.assertIn("尚未开放", ask("@public-model 第二条")[0]["reason"])
                self.assertFalse(room.set_members(list(room.ais), {}, {"bot": True})[0])
                self.assertTrue(room.set_members(list(room.ais), {"alice": {"trigger": True, "work": True}}, {"public-model": True})[0])
                self.assertEqual(ask("这是一条普通发言"), [])
                self.assertIn("尚未开放", ask("@bot 修改文件")[0]["reason"])
                model.assert_not_called()
                self.assertEqual(ask("@public-model 请讨论"), [])
                with room.ai_lock("public-model"):
                    pass
                for job in threading.enumerate():
                    if job.name.endswith("(run_job)"):
                        job.join(timeout=2)
                model.assert_called_once()
                self.assertIn("请讨论", model.call_args.args[1])
                self.assertNotIn("入房之前的内容", model.call_args.args[1])
                self.assertNotIn("本机 Agent 的私有输出", model.call_args.args[1])
                self.assertEqual(room.meta["public-model_session"], "private-session")
                native.assert_not_called()
            self.assertFalse(access.permissions(room, "alice")["work"])
            status, messages = call(endpoint, key=self.key)
            self.assertEqual(status, 200)
            visible = [entry["text"] for entry in messages["messages"]]
            self.assertIn("公开讨论的回复", visible)
            self.assertNotIn("入房之前的内容", visible)
            self.assertNotIn("本机 Agent 的私有输出", visible)
        finally:
            registry.remove_agent("public-model")

    def test_share_publishes_only_selected_parts_to_selected_user(self):
        registry.save_agent({"id": "ben", "kind": "user", "driver": "external", "enabled": True})
        try:
            ben_key = access.credential("ben")
            room = self.other
            self.assertTrue(room.set_members(["alice", "ben", "bot"], {})[0])
            room_id = quote(room.id)
            first = room.save_upload("review.txt", lambda n: b"hello"[:n], 5)
            private = room.add_message("bot", "私有正文", [R.make_attachment(first)])
            url = "/api/r/" + room_id + "/contact/share"
            payload = {"id": private["id"], "recipients": ["alice"], "attachments": [0], "share_text": False}
            self.assertEqual(call(url, payload, self.key)[0], 403)
            code, shared = call(url, payload, owner=True)
            self.assertEqual(code, 200, shared)
            listing = "/api/external/messages?room=" + room_id
            result = call(listing, key=self.key)[1]["messages"][-1]
            self.assertEqual(result["text"], "")
            self.assertEqual(result["shared_attachments"], [{"name": "review.txt", "size": 5, "index": 0}])
            self.assertFalse(any(m["id"] == shared["id"] for m in call(listing, key=ben_key)[1]["messages"]))
            self.assertFalse(any(m["id"] == shared["id"] for m in call(listing, key=self.bot_key)[1]["messages"]))
            download = "/api/external/attachment?room=%s&message=%d&index=0" % (room_id, shared["id"])
            Path(first).write_bytes(b"later")
            req = urllib.request.Request(BASE + download, headers={"Authorization": "Bearer " + self.key})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.read(), b"hello")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(call(download, key=ben_key)[0], 404)
            revoke = "/api/r/" + room_id + "/contact/revoke"
            self.assertEqual(call(revoke, {"contact": "alice"}, owner=True)[0], 200)
            self.assertEqual(call(download, key=self.key)[0], 403)
        finally:
            registry.remove_agent("ben")

    def test_unenforceable_workspace_policy_blocks_native_dispatch(self):
        room = self.other
        self.assertTrue(room.set_members(["bot"], {})[0])
        room_id = quote(room.id)
        url = "/api/r/" + room_id + "/contact/policies"
        policy = {"contact": "bot", "policy": {"workspace": {"read": True, "write": False, "exec": False}}}
        self.assertEqual(call(url, policy, owner=True)[0], 200)
        with patch.object(room, "enqueue") as enqueue:
            room.handle_message("你", "@bot 审阅项目")
            enqueue.assert_not_called()
        self.assertIn("无法强制执行", room.messages[-1]["text"])

    def test_native_edit_hook_honors_explicit_workspace(self):
        room = self.other
        self.assertTrue(room.set_members(["claude"], {"claude": {"work": True}})[0])
        room.set_contact_policies({}, {"claude": {"workspace": {"read": True, "write": True, "exec": True}}})
        result = agents.guard_decide("claude", room, "claude", {"tool_input": {"file_path": str(Path(DATA).parent / "other.txt")}})
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

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
