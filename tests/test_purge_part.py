import os, sys, tempfile, time, unittest, json, threading
os.environ["ROUNDTABLE_LOG_DIR"] = tempfile.mkdtemp(prefix="rt_pp_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import room as R, agents, common, web, workspace as ws
ROOM = None   # 这个测试文件当前在用的会议


def new_room(title, ann="", wd=None):
    global ROOM
    ROOM = R.rooms.create(title, ann, wd)
    return ROOM.id

FAKE_HOME = tempfile.mkdtemp(prefix="rt_home_")
agents.CLAUDE_HOME = FAKE_HOME          # 绝不碰真的 ~/.claude
codex_deleted = []
agents.delete_codex_thread = lambda sid: (codex_deleted.append(sid) or (True, ""))   # 不碰真的 codex
calls = []


def fake(ai, prompt, sid, imgs, mode=None, room=None):
    calls.append((ai, prompt))
    return True, "@用户 好了", sid or ("sid-%s-%d" % (ai, time.time_ns())), []


R.ai_caller = fake


def wait_idle():
    for _ in range(200):
        if not ROOM.busy_for():
            return
        time.sleep(0.05)


def make_claude_files(sid):
    proj = os.path.join(FAKE_HOME, "projects", "D--Some-Proj")
    os.makedirs(os.path.join(proj, sid, "subagents"), exist_ok=True)
    open(os.path.join(proj, sid + ".jsonl"), "w").close()
    os.makedirs(os.path.join(FAKE_HOME, "file-history", sid), exist_ok=True)
    os.makedirs(os.path.join(FAKE_HOME, "todos"), exist_ok=True)
    open(os.path.join(FAKE_HOME, "todos", sid + "-agent-x.json"), "w").close()
    keep = os.path.join(proj, "other-session-1234.jsonl")
    open(keep, "w").close()
    return proj, keep


def wait_note(word):
    for _ in range(100):
        if any(word in m["text"] for m in ROOM.messages):
            return True
        time.sleep(0.05)
    return False


class T(unittest.TestCase):
    def test_purge_deletes_sessions(self):
        a = new_room("要删的")
        ROOM.handle_message("你", "两个都说话")
        wait_idle()
        csid, xsid = ROOM.meta["claude_session"], ROOM.meta["codex_session"]
        ROOM.meta["old_sessions"]["claude"].append("old-claude-0001")
        ROOM.save_meta()
        proj, keep = make_claude_files(csid)
        make_claude_files("old-claude-0001")
        new_room("留着的")
        ok, err = R.trash_meeting(a)
        self.assertTrue(ok, err)
        self.assertTrue(os.path.exists(os.path.join(proj, csid + ".jsonl")), "进回收站时不删")
        cleanup = []
        ok, err = R.purge_all(cleanup)
        self.assertTrue(ok, err)
        self.assertFalse(any("彻底删除" in m["text"] for m in ROOM.messages))
        self.assertTrue(any(item["ai"] == "claude" and item["status"] == "deleted" for item in cleanup))
        self.assertFalse(os.path.exists(os.path.join(proj, csid + ".jsonl")))
        self.assertFalse(os.path.exists(os.path.join(proj, csid)))
        self.assertFalse(os.path.exists(os.path.join(FAKE_HOME, "file-history", csid)))
        self.assertFalse(os.path.exists(os.path.join(FAKE_HOME, "todos", csid + "-agent-x.json")))
        self.assertFalse(os.path.exists(os.path.join(proj, "old-claude-0001.jsonl")))
        self.assertTrue(os.path.exists(keep), "别的会话不能动")
        self.assertIn(xsid, codex_deleted)

    def test_shared_session_kept(self):
        a = new_room("共用甲")
        ROOM.handle_message("你", "@claude 在吗")
        wait_idle()
        sid = ROOM.meta["claude_session"]
        proj, _ = make_claude_files(sid)
        b = new_room("共用乙")
        ROOM.meta["claude_session"] = sid    # 两场会议指向同一个会话（比如复制出来的）
        ROOM.save_meta()
        new_room("第三场")
        R.trash_meeting(a)
        R.purge_all()
        time.sleep(0.5)
        self.assertTrue(os.path.exists(os.path.join(proj, sid + ".jsonl")), "别的会议还在用，不删")

    def test_bad_sid_ignored(self):
        self.assertEqual(agents.delete_claude_session("../../x"), 0)
        self.assertEqual(agents.delete_claude_session("*"), 0)
        self.assertEqual(R.meeting_sessions({"claude_session": "..\\..", "codex_session": "abc-def-123"}),
                         {"claude": [], "codex": ["abc-def-123"]})

    def test_partial_quote(self):
        new_room("引用一段")
        ROOM.handle_message("你", "@claude 说点长的")
        wait_idle()
        cm = [m for m in ROOM.messages if m["speaker"] == "claude"][-1]
        calls.clear()
        ROOM.handle_message("你", "这个对吗", reply_to=ROOM.make_reply(cm["id"], "  好\n了  "))
        wait_idle()
        self.assertEqual([c[0] for c in calls], ["claude"])
        self.assertIn("（回复 [claude] 那条里的这段：“好 了”）这个对吗", calls[0][1])
        r = ROOM.make_reply(cm["id"], "x" * 300)
        self.assertTrue(r["part"])
        self.assertEqual(len(r["text"]), R.QUOTE_LEN + 1)

    def test_meeting_sessions_and_delete_sessions_handle_custom_agents(self):
        from unittest import mock
        meta = {
            "claude_session": "cccccccc-1111-2222-3333-444444444444",
            "acp-bot_session": "acp-session-1234",
            "opencode_session": "ses_1234abcd",
            "claude-alt_session": "aaaaaaaa-1111-2222-3333-444444444444",
            "old_sessions": {"claude": [], "codex": [], "acp-bot": ["acp-old-567890"]},
        }
        sids = R.meeting_sessions(meta)
        self.assertEqual(sids["acp-bot"], ["acp-session-1234", "acp-old-567890"])
        self.assertEqual(sids["opencode"], ["ses_1234abcd"])
        self.assertEqual(sids["claude-alt"], ["aaaaaaaa-1111-2222-3333-444444444444"])

        new_room("删第三方会话")
        deleted_claude = []

        def fake_agent(aid):
            if aid == "claude-alt":
                return {"id": "claude-alt", "driver": "claude"}
            if aid == "acp-bot":
                return {"id": "acp-bot", "driver": "acp"}
            return None

        with mock.patch.object(R.registry, "get", side_effect=fake_agent), \
             mock.patch.object(agents, "delete_claude_session", side_effect=lambda sid: (deleted_claude.append(sid), 2)[1]):
            results = R.delete_sessions("测试场", {"claude-alt": ["aaaaaaaa-1111-2222-3333-444444444444"],
                                                 "acp-bot": ["acp-session-1234"], "antigravity": ["agy-session-1234"]})
        self.assertEqual(deleted_claude, ["aaaaaaaa-1111-2222-3333-444444444444"])
        self.assertEqual([item["status"] for item in results], ["deleted", "manual", "manual"])
        self.assertEqual([item["ai"] for item in results], ["claude-alt", "acp-bot", "antigravity"])
        self.assertEqual(results[-1]["session"], "agy-session-1234")
        self.assertFalse(any("彻底删除" in m["text"] for m in ROOM.messages))


if __name__ == "__main__":
    unittest.main()
