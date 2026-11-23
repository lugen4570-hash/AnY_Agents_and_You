# -*- coding: utf-8 -*-
"""几场会议同时跑：各跑各的、互不挡；会议列表的状态；外部发言按会议号；HTTP 接口带会议号。"""
import json, os, sys, tempfile, threading, time, unittest, urllib.error, urllib.request
from unittest.mock import patch
from urllib.parse import quote

os.environ["ROUNDTABLE_LOG_DIR"] = tempfile.mkdtemp(prefix="rt_multi_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import room as R, web, common, access, registry

WD = tempfile.mkdtemp(prefix="rt_multi_wd_")
gate = {}      # 会议号 -> Event：放行它的 AI
started = {}   # (会议号, ai) -> 开跑时间


def fake(ai, prompt, sid, imgs, mode=None, room=None):
    started[(room.id, ai)] = time.time()
    ev = gate.get(room.id)
    if ev is not None:
        ev.wait(10)
    return True, "@用户 %s 回 %s" % (ai, room.title()), sid or ("sid-%s-%s" % (ai, room.id[-4:])), []


R.ai_caller = fake
srv = web.ExclusiveServer(("127.0.0.1", 0), web.Handler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def call(method, path, obj=None, auth=True, key=None):
    h = {"Content-Type": "application/json"}
    if auth:
        h["X-RT-Token"] = web.RT_TOKEN
    if key:
        h["Authorization"] = "Bearer " + key
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), method=method,
                                 data=json.dumps(obj).encode() if obj is not None else None, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def rp(r, act):
    return "/api/r/%s/%s" % (quote(r.id), act)


def idle(*rooms, t=10):
    end = time.time() + t
    while time.time() < end:
        if not any(r.busy_for() for r in rooms):
            return True
        time.sleep(0.05)
    return False


class MultiRoom(unittest.TestCase):
    def setUp(self):
        gate.clear()
        started.clear()

    def test_create_permissions_and_rename_through_owner_api(self):
        body = {"title": "改名前", "workdir": WD, "participants": ["codex"],
                "permissions": {"codex": {"work": True}}}
        status, payload = call("POST", "/api/rooms/new", body)
        self.assertEqual(status, 200, payload)
        room = R.rooms.get(payload["id"])
        self.assertTrue(access.permissions(room, "codex")["work"])
        self.assertEqual(call("POST", rp(room, "rename"), {"title": " 改名后 "})[0], 200)
        state = call("GET", rp(room, "state"))[1]
        self.assertEqual(state["title"], "改名后")
        self.assertEqual(room.id, payload["id"])
        self.assertEqual(common.read_json(os.path.join(room.dir, "meeting.json"))["title"], "改名后")
        self.assertEqual(call("POST", rp(room, "rename"), {"title": "\n"})[0], 409)
        self.assertEqual(call("POST", rp(room, "rename"), {"title": "越权"}, auth=False)[0], 403)
        self.assertEqual(call("POST", "/api/rooms/new", {**body, "permissions": {"codex": {"work": "true"}}})[0], 400)
        self.assertEqual(call("POST", rp(room, "mode"), {"mode": "work"})[0], 200)
        self.assertEqual(room.messages[-1]["text"], "切到干活模式")
        self.assertEqual(call("POST", rp(room, "members"), {"participants": ["codex"], "permissions": {"codex": {"work": False}}})[0], 200)
        self.assertEqual(room.messages[-1]["text"], "已关闭干活权限：codex")
        room.meta["codex_session"] = "old-codex-session"
        room.save_meta()
        self.assertEqual(call("POST", rp(room, "session/reset"), {"ai": "codex"})[0], 200)
        self.assertNotIn("codex_session", room.meta)
        self.assertEqual(room.meta["old_sessions"]["codex"], ["old-codex-session"])

    def test_purge_api_reports_sessions_that_need_manual_cleanup(self):
        room = R.rooms.create("需要手动清理", "", WD, participants=[])
        room.meta["antigravity_session"] = "agy-session-1234"
        room.save_meta()
        self.assertEqual(call("POST", "/api/rooms/delete", {"id": room.id})[0], 200)
        status, payload = call("POST", "/api/trash/purge", {"id": room.id})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["cleanup"], [{"room": "需要手动清理", "ai": "antigravity",
                                               "session": "agy-session-1234", "status": "manual",
                                               "message": "agy 端需要手动清理"}])

    def test_rooms_run_in_parallel(self):
        a = R.rooms.create("甲", "", WD)
        b = R.rooms.create("乙", "", WD)
        gate[a.id] = threading.Event()
        a.handle_message("你", "@claude 慢慢想")
        time.sleep(0.2)
        self.assertTrue(a.busy_for("claude"))
        # 甲还在跑，乙照样能叫、能跑完
        b.handle_message("你", "@claude 你好")
        self.assertTrue(idle(b, t=5), "乙不该被甲挡住")
        self.assertIn("claude 回 乙", b.messages[-1]["text"])
        self.assertTrue(a.busy_for("claude"))
        gate[a.id].set()
        self.assertTrue(idle(a))
        self.assertIn("claude 回 甲", a.messages[-1]["text"])
        # 两场会议的会话各是各的
        self.assertNotEqual(a.meta["claude_session"], b.meta["claude_session"])

    def test_new_room_while_other_busy(self):
        a = R.rooms.create("忙的", "", WD)
        gate[a.id] = threading.Event()
        a.handle_message("你", "@codex 干长活")
        time.sleep(0.2)
        s, j = call("POST", "/api/rooms/new", {"title": "新的", "workdir": WD})
        self.assertEqual(s, 200)
        self.assertTrue(j["id"])
        self.assertTrue(a.busy_for("codex"), "开新会议不影响正在跑的")
        # 忙的那场不能删，别的能删
        self.assertEqual(call("POST", "/api/rooms/delete", {"id": a.id})[0], 409)
        self.assertEqual(call("POST", "/api/rooms/delete", {"id": j["id"]})[0], 200)
        gate[a.id].set()
        idle(a)

    def test_listing_status(self):
        a = R.rooms.create("看状态", "", WD)
        gate[a.id] = threading.Event()
        a.handle_message("你", "@claude 想想")
        time.sleep(0.2)
        s, j = call("GET", "/api/rooms")
        self.assertEqual(s, 200)
        row = next(x for x in j["rooms"] if x["id"] == a.id)
        self.assertEqual(row["running"], ["claude"])
        gate[a.id].set()
        idle(a)
        row = next(x for x in call("GET", "/api/rooms")[1]["rooms"] if x["id"] == a.id)
        self.assertEqual(row["running"], [])
        self.assertEqual(row["count"], len(a.messages))
        self.assertEqual(row["last_to_user"], len(a.messages) - 1, "AI @用户 的那条")

    def test_room_api_routes(self):
        a = R.rooms.create("接口", "旧目标", WD)
        self.assertEqual(call("POST", rp(a, "send"), {"text": "@claude 嗨"})[0], 200)
        idle(a)
        s, j = call("GET", rp(a, "messages") + "?since=0")
        self.assertEqual(s, 200)
        self.assertEqual(j["meeting"], a.id)
        self.assertEqual([m["speaker"] for m in j["messages"]], ["你", "claude"])
        self.assertEqual(call("POST", rp(a, "announcement"), {"text": "新目标"})[0], 200)
        st = call("GET", rp(a, "state"))[1]
        self.assertEqual(st["announcement"], "新目标")
        # 用户的接口只认浏览器
        self.assertEqual(call("POST", rp(a, "send"), {"text": "x"}, auth=False)[0], 403)
        # 没有的会议
        s, j = call("GET", "/api/r/%s/state" % quote("不存在的会议"))
        self.assertEqual(s, 404)
        self.assertTrue(j.get("gone"))
        # 打开会议 = 记成"最近打开的"
        self.assertEqual(call("POST", rp(a, "open"), {})[0], 200)
        self.assertEqual(R.last_room(), a.id)

    def test_owner_recall_preserves_cursor_and_redacts_old_quotes_on_reload(self):
        room = R.rooms.create("撤回", "", WD, participants=[])
        path = rp(room, "recall")
        room.add_message("你", "请撤回", [{"path": "private.png"}])
        room.add_message("claude", "后续消息", reply_to=room.make_reply(0))
        self.assertEqual(call("POST", path, {"id": 0}, auth=False)[0], 403)
        self.assertEqual(call("POST", path, {"id": 1})[0], 403)
        self.assertEqual(call("POST", path, {"id": True})[0], 404)
        for _ in range(2):
            self.assertEqual(call("POST", path, {"id": 0})[0], 200)
        update = call("GET", rp(room, "messages") + "?since=2")[1]
        self.assertEqual((update["next"], update["messages"], update["recalled"]), (2, [], [0]))
        self.assertIsNone(room.make_reply(0, "原文"))
        with R.rooms.lock:
            R.rooms.loaded.pop(room.id)
        room.close()
        loaded = R.rooms.get(room.id)
        self.assertEqual(loaded.messages[0]["text"], "消息已撤回")
        self.assertNotIn("attachments", loaded.messages[0])
        self.assertEqual(loaded.messages[1]["reply_to"]["text"], "消息已撤回")

    def test_recall_restores_message_with_image_and_stops_active_agents(self):
        room = R.rooms.create("撤回停AI", "", WD, participants=["claude", "codex"])
        ai_msg = room.add_message("claude", "之前的回答")
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s?name=shot.png" % (PORT, rp(room, "upload")),
            method="POST",
            data=b"\x89PNG\r\n\x1a\nfake",
            headers={"X-RT-Token": web.RT_TOKEN},
        )
        with urllib.request.urlopen(req) as resp:
            uploaded = json.loads(resp.read().decode())
        gate[room.id] = threading.Event()
        self.addCleanup(gate[room.id].set)
        status, _ = call("POST", rp(room, "send"), {
            "text": "@claude 看下这张图",
            "attachments": [{"path": uploaded["path"], "kind": uploaded["kind"]}],
            "reply_to": ai_msg["id"],
        })
        self.assertEqual(status, 200)
        msg_id = room.messages[-1]["id"]
        deadline = time.time() + 5
        while time.time() < deadline and (room.id, "claude") not in started:
            time.sleep(0.02)
        self.assertIn((room.id, "claude"), started)
        room.handle_message("你", "@claude 另一条请求")
        queued_id = room.messages[-1]["id"]
        status, payload = call("POST", rp(room, "recall"), {"id": msg_id})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["draft"]["text"], "@claude 看下这张图")
        self.assertEqual(payload["draft"]["attachments"][0]["path"], uploaded["path"])
        self.assertEqual(payload["draft"]["attachments"][0]["kind"], "image")
        self.assertEqual(payload["draft"]["reply_to"]["id"], ai_msg["id"])
        self.assertIn("claude", payload["stopped"])
        self.assertTrue(any(job[2] == queued_id for job in room.pending))
        gate[room.id].set()
        self.assertTrue(idle(room, t=5))
        replies = [m for m in room.messages if m["speaker"] == "claude" and "claude 回" in m["text"]]
        self.assertEqual(len(replies), 1)
        self.assertEqual(len(room.clean_attachments([{"path": uploaded["path"]}])), 1)

    def test_recall_removes_queued_turn_and_leaves_another_message_queued(self):
        meeting = R.rooms.create("排队撤回", "", WD, participants=["claude"])
        with meeting.ai_lock("claude"):
            meeting.handle_message("你", "@claude 待撤回")
            meeting.handle_message("你", "@claude 保留")
            self.assertEqual(meeting.queued_count(), 2)
            status, result = call("POST", rp(meeting, "recall"), {"id": 0})
            self.assertEqual((status, result["stopped"]), (200, ["claude"]))
            self.assertEqual(meeting.queued_count(), 1)
        self.assertTrue(idle(meeting))
        self.assertEqual([m["speaker"] for m in meeting.messages].count("claude"), 1)

    def test_recall_cascades_through_agent_replies_and_rebuilds_native_context(self):
        meeting = R.rooms.create("回退 AI 会话", "", WD, participants=["claude", "codex"])
        calls = []

        def reply(ai, prompt, sid, images, mode, room):
            calls.append((ai, prompt, sid))
            if "START_CASCADE" in prompt and ai == "claude":
                text = "@codex CASCADE_FIRST"
            elif "CASCADE_FIRST" in prompt and ai == "codex":
                text = "CASCADE_SECOND"
            else:
                text = "KEEP_REPLY"
            return True, text, sid or f"session-{len(calls)}", []

        with patch.object(R, "ai_caller", reply):
            meeting.handle_message("你", "@claude KEEP_REQUEST")
            self.assertTrue(idle(meeting))
            old_sid = meeting.meta["claude_session"]
            meeting.handle_message("你", "@claude START_CASCADE")
            self.assertTrue(idle(meeting))
            self.assertEqual([m["text"] for m in meeting.messages[-2:]], ["@codex CASCADE_FIRST", "CASCADE_SECOND"])
            status, result = call("POST", rp(meeting, "recall"), {"id": 2})
            self.assertEqual((status, result["recalled"]), (200, [2, 3, 4]))
            R.rooms.unload(meeting.id)
            meeting = R.rooms.get(meeting.id)
            self.assertEqual([m["text"] for m in meeting.messages[:2]], ["@claude KEEP_REQUEST", "KEEP_REPLY"])
            self.assertTrue(all(m["recalled"] for m in meeting.messages[2:5]))
            self.assertIsNone(meeting.handoff_cmd("claude"))
            meeting.handle_message("你", "@claude NEXT_REQUEST")
            self.assertTrue(idle(meeting))
            _, prompt, sid = calls[-1]
            self.assertIsNone(sid)
            self.assertIn("KEEP_REQUEST", prompt)
            self.assertIn("KEEP_REPLY", prompt)
            self.assertIn("NEXT_REQUEST", prompt)
            self.assertNotIn("CASCADE", prompt)
            self.assertIn(old_sid, meeting.meta["old_sessions"]["claude"])

    def test_goal_in_prompt(self):
        a = R.rooms.create("目标", "把第三章写完", WD)
        seen = []
        R.ai_caller = lambda ai, prompt, sid, imgs, mode=None, room=None: (seen.append(prompt), (True, "@用户 好", sid or "s1", []))[1]
        try:
            a.handle_message("你", "@claude 开始")
            idle(a)
            self.assertIn("这场会议的目标：\n把第三章写完", seen[-1])
            a.write_announcement("改成写第四章")
            a.handle_message("你", "@claude 继续")
            idle(a)
            self.assertIn("会议目标改了，新的目标：\n改成写第四章", seen[-1])
            self.assertNotIn("这场会议的目标：", seen[-1])
            a.handle_message("你", "@claude 再来")
            idle(a)
            self.assertNotIn("目标", seen[-1].split("新消息：")[0], "目标没改就不重复递")
        finally:
            R.ai_caller = fake

    def test_external_post_room(self):
        registry.save_agent({"id":"external-codex","driver":"external","enabled":True})
        a = R.rooms.create("外部甲", "", WD)
        b = R.rooms.create("外部乙", "", WD)
        b.set_participants(list(b.ais)+['external-codex'])
        R.set_last(a.id)
        key = access.credential("external-codex")
        s, j = call("POST", "/api/post", {"speaker": "claude", "text": "不带会议号"}, auth=False)
        self.assertEqual(s, 401)
        s, j = call("POST", "/api/post", {"speaker": "external-codex", "text": "带会议号", "room": b.id}, auth=False, key=key)
        self.assertEqual((s, j["room"]), (200, b.id))
        self.assertEqual(b.messages[-1]["text"], "带会议号")
        self.assertEqual(b.messages[-1].get("origin"), "external")
        self.assertEqual(call("POST", "/api/post", {"speaker": "external-codex", "text": "x", "room": "没有"}, auth=False, key=key)[0], 404)
        self.assertEqual(call("POST", "/api/post", {"speaker": "你", "text": "冒充用户"}, auth=False, key=key)[0], 403)

    def test_stop_only_this_room(self):
        a = R.rooms.create("停甲", "", WD)
        b = R.rooms.create("停乙", "", WD)
        gate[a.id] = threading.Event()
        gate[b.id] = threading.Event()
        a.handle_message("你", "@claude 长活")
        b.handle_message("你", "@claude 长活")
        time.sleep(0.2)
        a.stop_ais(["claude"])
        self.assertTrue(b.busy_for("claude"), "停甲不该动乙")
        self.assertEqual(b.state["epoch"]["claude"], 0)
        gate[a.id].set()
        gate[b.id].set()
        idle(a, b)

    def test_reload_from_disk(self):
        a = R.rooms.create("重读", "目标X", WD)
        a.handle_message("你", "@claude 记住")
        idle(a)
        rid, n = a.id, len(a.messages)
        R.rooms.unload(rid)
        b = R.rooms.get(rid)
        self.assertIsNot(a, b)
        self.assertEqual(len(b.messages), n)
        self.assertEqual(b.goal(), "目标X")
        self.assertEqual(b.meta["claude_session"], a.meta["claude_session"])

    def test_legacy_page_endpoints(self):
        a = R.rooms.create("老页面", "", WD)
        R.set_last(a.id)
        s, j = call("GET", "/api/state")
        self.assertEqual((s, j["meeting"], j.get("reload")), (200, a.id, True))
        self.assertEqual(call("POST", "/api/send", {"text": "x"})[0], 409)

    def test_idle_rooms_lru_evicted_without_dropping_busy_room(self):
        old_cap = getattr(R.rooms, "max_loaded", None)
        R.rooms.max_loaded = 2
        self.addCleanup(lambda: setattr(R.rooms, "max_loaded", old_cap) if old_cap is not None else delattr(R.rooms, "max_loaded") if hasattr(R.rooms, "max_loaded") else None)
        r1 = R.rooms.create("忙房间", "", WD)
        gate[r1.id] = threading.Event()
        self.addCleanup(gate[r1.id].set)
        r1.handle_message("你", "@claude 别被赶走")
        time.sleep(0.15)
        time.sleep(0.03)
        r2 = R.rooms.create("闲置一", "", WD)
        time.sleep(0.03)
        r3 = R.rooms.create("闲置二", "", WD)
        # r1 忙不能逐出；最旧的闲置房间 r2 应该被从内存逐出并关停，保留 r1 与 r3
        self.assertLessEqual(len(R.rooms.loaded), 2)
        self.assertIn(r1.id, R.rooms.loaded)
        self.assertNotIn(r2.id, R.rooms.loaded)
        self.assertTrue(r2.closed)
        # 重新读取被逐出的闲置房间应从磁盘无缝复活，此时把闲置且更早的 r3 逐出
        reloaded = R.rooms.get(r2.id)
        self.assertIsNotNone(reloaded)
        self.assertIsNot(reloaded, r2)
        self.assertIn(r1.id, R.rooms.loaded)
        self.assertNotIn(r3.id, R.rooms.loaded)
        gate[r1.id].set()
        idle(r1)

    def test_scan_caches_unchanged_meeting_json(self):
        from unittest import mock
        r = R.rooms.create("缓存扫描", "")
        R.scan(R.MEET_DIR)
        real_read_json = R.read_json
        calls = []

        def tracked(p):
            if os.path.basename(p) == "meeting.json":
                calls.append(p)
            return real_read_json(p)

        with mock.patch.object(R, "read_json", side_effect=tracked):
            first = R.scan(R.MEET_DIR)
            self.assertEqual(calls, [], "未修改的 meeting.json 二次 scan 不应重复读盘解析")
            hit = [x for x in first if x["id"] == r.id][0]
            hit["title"] = "外部篡改不影响缓存"
            second = R.scan(R.MEET_DIR)
            self.assertEqual([x for x in second if x["id"] == r.id][0]["title"], "缓存扫描")
            r.meta["title"] = "改名后应失效"
            r.save_meta()
            meta_path = os.path.join(r.dir, "meeting.json")
            mt = os.path.getmtime(meta_path)
            os.utime(meta_path, (mt + 2, mt + 2))
            third = R.scan(R.MEET_DIR)
            self.assertEqual([x for x in third if x["id"] == r.id][0]["title"], "改名后应失效")
            self.assertTrue(any(r.id in p for p in calls))


if __name__ == "__main__":
    unittest.main()
