import os, sys, tempfile, time, unittest, subprocess
os.environ["ROUNDTABLE_LOG_DIR"] = tempfile.mkdtemp(prefix="rt_wd_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import room as R, agents, common, web, workspace as ws
ROOM = None   # 这个测试文件当前在用的会议


def new_room(title, ann="", wd=None):
    global ROOM
    ROOM = R.rooms.create(title, ann, wd)
    return ROOM.id

calls = []


def fake(ai, prompt, sid, imgs, mode=None, room=None):
    calls.append((ai, mode, prompt, ROOM.workdir()))
    return True, "@用户 好了", sid or ("sid-" + ai), []


R.ai_caller = fake


def wait_idle():
    for _ in range(100):
        if not ROOM.busy_for():
            return
        time.sleep(0.05)


class T(unittest.TestCase):
    def setUp(self):
        calls.clear()

    def test_default_is_project(self):
        new_room("d%d" % time.time_ns())
        self.assertEqual(ROOM.workdir(), common.PROJECT)
        self.assertEqual(ROOM.api_state()["workdir"], common.PROJECT)

    def test_old_meeting_without_field(self):
        m = R.fix_meta({"title": "old"})
        self.assertEqual(m["workdir"], common.PROJECT)

    def test_other_folder_prompt_and_cmd(self):
        d = tempfile.mkdtemp(prefix="rt_other_")
        new_room("o%d" % time.time_ns(), "", d)
        self.assertEqual(ROOM.workdir(), d)
        ROOM.handle_message("你", "@claude 你好")
        wait_idle()
        self.assertEqual(calls[-1][3], d)
        cmd = agents.build_cmd("claude", "discuss", None, "claude", room=ROOM)
        # Native drivers receive room instructions separately from message deltas.
        self.assertIn("--append-system-prompt", cmd)
        self.assertIn("工作目录是 %s" % d, cmd[cmd.index("--append-system-prompt") + 1])
        self.assertIn("--add-dir", cmd)
        self.assertIn(common.LOG_DIR, cmd)
        self.assertIn(d, ROOM.handoff_cmd("claude"))
        self.assertEqual([m for m in R.rooms.listing() if m["id"] == ROOM.id][0]["workdir"], d)

    def test_non_git_work_mode_runs_and_warns_once(self):
        d = tempfile.mkdtemp(prefix="rt_nogit_")
        new_room("n%d" % time.time_ns(), "", d)
        self.assertFalse(ws.in_git(d))
        ROOM.set_mode("work")
        ROOM.handle_message("你", "@claude 干活")
        wait_idle()
        ROOM.handle_message("你", "@claude 再干")
        wait_idle()
        self.assertEqual([c[1] for c in calls], ["work", "work"])
        warns = [m for m in ROOM.messages if "不是 git 仓库" in m["text"]]
        self.assertEqual(len(warns), 1)

    def test_wrapup_generic_outside_project(self):
        d = tempfile.mkdtemp(prefix="rt_wrap_")
        new_room("w%d" % time.time_ns(), "", d)
        t = ROOM.wrapup_text()
        self.assertIn(d, t)
        self.assertNotIn("SKILL.md", t)
        d2 = tempfile.mkdtemp(prefix="rt_skill_")
        os.makedirs(os.path.join(d2, ".claude", "skills", "wrapup"))
        open(os.path.join(d2, ".claude", "skills", "wrapup", "SKILL.md"), "w").close()
        new_room("w2%d" % time.time_ns(), "", d2)
        self.assertIn("SKILL.md", ROOM.wrapup_text())

    def test_git_repo_elsewhere_snapshot(self):
        d = tempfile.mkdtemp(prefix="rt_repo_")
        subprocess.run(["git", "init", "-q", d], check=True)
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("x")
        new_room("g%d" % time.time_ns(), "", d)
        self.assertTrue(ws.in_git(d))
        tree = ws.snapshot_tree(d)
        self.assertTrue(tree)
        top, _ = ws.git_dirs(d)
        self.assertTrue(os.path.basename(ws.snapshot_index(top)).startswith("snapshot-"))
        self.assertNotEqual(ws.snapshot_index(top), ws.snapshot_index(tempfile.mkdtemp()))   # 每个仓库一份

    def test_undo_step_rolls_back_on_partial_failure(self):
        from unittest import mock
        d = tempfile.mkdtemp(prefix="rt_undo_")
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "-C", d, "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", d, "config", "user.name", "Test"], check=True)
        fa = os.path.join(d, "a.txt")
        fb = os.path.join(d, "b.txt")
        with open(fa, "w", encoding="utf-8") as f:
            f.write("a-v1")
        with open(fb, "w", encoding="utf-8") as f:
            f.write("b-v1")
        subprocess.run(["git", "-C", d, "add", "a.txt", "b.txt"], check=True)
        subprocess.run(["git", "-C", d, "commit", "-q", "-m", "init"], check=True)
        new_room("undo%d" % time.time_ns(), "", d)
        pre1 = ws.snapshot_tree(d)
        with open(fa, "w", encoding="utf-8") as f:
            f.write("a-v2")
        with open(fb, "w", encoding="utf-8") as f:
            f.write("b-v2")
        seq1 = ROOM.record_step("claude", pre1, [{"path": fa}, {"path": fb}], 10.0, 11.0)
        self.assertIsNotNone(seq1)
        real_replace = os.replace

        def fail_on_b(src, dst):
            if os.path.basename(dst) == "b.txt" and src.endswith(".rt_undo.tmp"):
                raise PermissionError("locked b.txt")
            return real_replace(src, dst)

        with mock.patch("bridge.room.os.replace", side_effect=fail_on_b):
            ok, err = ROOM.undo_step(seq1)
        self.assertFalse(ok)
        self.assertIn("locked b.txt", err)
        with open(fa, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "a-v2")
        with open(fb, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "b-v2")
        self.assertFalse(ROOM.meta["steps"][str(seq1)]["undone"])
        self.assertFalse(os.path.exists(fa + ".rt_undo.tmp"))
        self.assertFalse(os.path.exists(fb + ".rt_undo.tmp"))

        # 先删掉新建文件再覆盖已有文件时失败，应把已删的新建文件恢复
        fnew = os.path.join(d, "0_new.txt")
        pre2 = ws.snapshot_tree(d)
        with open(fnew, "w", encoding="utf-8") as f:
            f.write("created-once")
        with open(fa, "w", encoding="utf-8") as f:
            f.write("a-v3")
        seq2 = ROOM.record_step("claude", pre2, [{"path": fnew}, {"path": fa}], 12.0, 13.0)

        def fail_on_a(src, dst):
            if os.path.basename(dst) == "a.txt" and src.endswith(".rt_undo.tmp"):
                raise PermissionError("locked a.txt")
            return real_replace(src, dst)

        with mock.patch("bridge.room.os.replace", side_effect=fail_on_a):
            ok2, _ = ROOM.undo_step(seq2)
        self.assertFalse(ok2)
        with open(fnew, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "created-once")
        with open(fa, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "a-v3")


if __name__ == "__main__":
    unittest.main()
