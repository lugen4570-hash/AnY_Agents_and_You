import os, sys, tempfile, threading, time, unittest
os.environ["ROUNDTABLE_LOG_DIR"] = tempfile.mkdtemp(prefix="rt_sf_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import room as R, agents, common, web, workspace as ws
ROOM = None   # 这个测试文件当前在用的会议


def new_room(title, ann="", wd=None):
    global ROOM
    ROOM = R.rooms.create(title, ann, wd)
    return ROOM.id


replies = {}
calls = []


def fake(ai, prompt, sid, imgs, mode=None, room=None):
    calls.append((ai, prompt, list(imgs)))
    return True, replies.get(ai, "@用户 好了"), sid or ("sid-" + ai), []


def wait_idle():
    for _ in range(200):
        if not ROOM.busy_for():
            return
        time.sleep(0.05)


class T(unittest.TestCase):
    def setUp(self):
        R.ai_caller = fake
        replies.clear()
        calls.clear()
        self.wd = tempfile.mkdtemp(prefix="rt_sf_wd_")
        new_room("sf%d" % time.time_ns(), wd=self.wd)
        self.png = os.path.join(self.wd, "图.png")
        with open(self.png, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    def last(self, speaker):
        return [m for m in ROOM.messages if m["speaker"] == speaker][-1]

    def test_send_abs_and_relative(self):
        with open(os.path.join(self.wd, "说明.txt"), "w", encoding="utf-8") as f:
            f.write("hi")
        replies["claude"] = "@用户 截图和说明给你\n【发送】%s\n【发送】说明.txt" % self.png
        ROOM.handle_message("你", "@claude 发我")
        wait_idle()
        m = self.last("claude")
        self.assertEqual(m["text"], "@用户 截图和说明给你")
        self.assertEqual([a["name"] for a in m["attachments"]], ["图.png", "说明.txt"])
        self.assertEqual(m["attachments"][0]["kind"], "image")
        for a in m["attachments"]:
            full = R.abs_path(a)
            self.assertTrue(common.in_dir(full, ROOM.files_dir()) and os.path.isfile(full))
        self.assertTrue(m.get("to_user"))

    def test_only_file_no_text(self):
        replies["codex"] = "[发送] `%s`" % self.png
        ROOM.handle_message("你", "@codex 图")
        wait_idle()
        m = self.last("codex")
        self.assertEqual(m["text"], "")
        self.assertEqual(len(m["attachments"]), 1)

    def test_missing_file_reports_and_other_ai_sees(self):
        replies["claude"] = "给你\n【发送】不存在.png"
        ROOM.handle_message("你", "@claude 发我")
        wait_idle()
        self.assertNotIn("attachments", self.last("claude"))
        note = self.last("系统")
        self.assertIn("claude 的文件没发成", note["text"])
        self.assertIn("找不到文件", note["text"])
        self.assertFalse(note.get("quiet"), "失败要让 AI 下一轮看到")

    def test_in_code_block_ignored(self):
        replies["claude"] = "写法是：\n```\n【发送】%s\n```" % self.png
        ROOM.handle_message("你", "@claude 怎么发")
        wait_idle()
        m = self.last("claude")
        self.assertIn("【发送】", m["text"])
        self.assertNotIn("attachments", m)

    def test_other_ai_gets_image(self):
        replies["claude"] = "@codex 你看这张\n【发送】%s" % self.png
        ROOM.handle_message("你", "@claude 开始")
        wait_idle()
        codex_calls = [c for c in calls if c[0] == "codex"]
        self.assertTrue(codex_calls, "claude @ 了 codex")
        self.assertEqual(len(codex_calls[-1][2]), 1, "codex 应该收到那张图")
        self.assertIn("[附件 图片]", codex_calls[-1][1])

    def test_too_big(self):
        big = os.path.join(self.wd, "big.bin")
        with open(big, "wb") as f:
            f.truncate(common.MAX_UPLOAD + 1)
        replies["claude"] = "【发送】%s" % big
        ROOM.handle_message("你", "@claude 发")
        wait_idle()
        self.assertIn("太大", self.last("系统")["text"])

    def test_external_post_can_send(self):
        ROOM.handle_message("claude", "外面的我发一张\n【发送】%s" % self.png, origin="external")
        m = self.last("claude")
        self.assertEqual(len(m["attachments"]), 1)

    def test_rules_in_preamble(self):
        self.assertIn("【发送】", common.preamble("discuss", "D:/x"))
        self.assertIn("【发送】", common.preamble("work", "D:/x"))
        self.assertIn("不用先打开看", common.preamble("work", "D:/x"))

    def test_markdown_local_images_become_attachments(self):
        # codex 2026-10-14 实际这么写的：每张图前一行标题，图单独一行，本地绝对路径用正斜杠
        sub = os.path.join(self.wd, "概念 图")
        os.makedirs(sub)
        b = os.path.join(sub, "门(1).png")
        with open(b, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        fwd = lambda x: x.replace("\\", "/")
        replies["codex"] = ("@用户 这是两张图。\n\n中心枢纽  \n![中心枢纽](%s)\n\n收容门  \n![收容门](%s)\n\n网上那张 ![外链](https://e.com/x.png) 不动"
                            % (fwd(self.png), fwd(b)))
        ROOM.handle_message("你", "@codex 发图")
        wait_idle()
        m = self.last("codex")
        self.assertEqual([a["name"] for a in m["attachments"]], ["图.png", "门(1).png"])
        self.assertNotIn(fwd(self.png), m["text"])
        self.assertIn("中心枢纽", m["text"])
        self.assertIn("![外链](https://e.com/x.png)", m["text"])
        self.assertNotIn("\n\n\n", m["text"])

    def test_markdown_file_url_and_inline(self):
        from urllib.parse import quote
        url = "file:///" + quote(self.png.replace("\\", "/"))
        replies["claude"] = "看这张 ![x](%s) 就是它" % url
        ROOM.handle_message("你", "@claude 发")
        wait_idle()
        m = self.last("claude")
        self.assertEqual(len(m["attachments"]), 1)
        self.assertEqual(m["text"], "看这张  就是它")

    def test_markdown_missing_keeps_text(self):
        replies["claude"] = "![没有](D:/不存在/x.png)"
        ROOM.handle_message("你", "@claude 发")
        wait_idle()
        m = self.last("claude")
        self.assertNotIn("attachments", m)
        self.assertIn("![没有](D:/不存在/x.png)", m["text"], "没发成留着原文")
        self.assertIn("找不到文件", self.last("系统")["text"])

    def test_markdown_in_code_ignored(self):
        replies["claude"] = "写法：`![x](%s)`\n```\n![x](%s)\n```" % (self.png, self.png)
        ROOM.handle_message("你", "@claude 怎么写")
        wait_idle()
        self.assertNotIn("attachments", self.last("claude"))

    def test_blocks_host_file_outside_workdir(self):
        outside_dir = tempfile.mkdtemp(prefix="rt_sf_out_")
        self.addCleanup(lambda: __import__("shutil").rmtree(outside_dir, ignore_errors=True))
        secret = os.path.join(outside_dir, "secret.txt")
        with open(secret, "w", encoding="utf-8") as f:
            f.write("TOP-SECRET")
        ROOM.meta["mode"] = "discuss"
        with self.assertRaises(ValueError):
            ROOM.send_file(secret)
        ROOM.meta["mode"] = "work"
        with self.assertRaises(ValueError):
            ROOM.send_file(secret)
        replies["claude"] = "给你\n【发送】%s\n![图](%s)" % (secret, secret)
        ROOM.handle_message("你", "@claude 发")
        wait_idle()
        m = self.last("claude")
        self.assertNotIn("attachments", m)
        self.assertFalse(os.listdir(ROOM.files_dir()), "绝不能把工作目录外的文件拷进 files/")
        self.assertIn("claude 的文件没发成", self.last("系统")["text"])

    def test_allows_codex_gen_images_turn_allowlist_once(self):
        from unittest.mock import patch
        outside_dir = tempfile.mkdtemp(prefix="rt_sf_gen_")
        self.addCleanup(lambda: __import__("shutil").rmtree(outside_dir, ignore_errors=True))
        gen_img = os.path.join(outside_dir, "generated.png")
        with open(gen_img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"1" * 32)

        class FakeSrv:
            def err_tail(self):
                return []
            def run_turn(self, sid, prompt, imgs, mode, model, effort, edits, res, **kw):
                res["gen_images"] = [gen_img]
                return True, "@用户 画好了", "sid-codex-1"

        with patch.object(agents, "codex_for", return_value=FakeSrv()):
            ok, out, _ = agents.call_codex_appserver(ROOM, "画一张", None, (), "discuss", "", "", [], {})
        self.assertTrue(ok)
        self.assertIn("【发送】" + gen_img, out)
        rest, atts, errs = ROOM.apply_send_cmds(out)
        self.assertEqual(errs, [])
        self.assertEqual(len(atts), 1)
        self.assertEqual(atts[0]["name"], "generated.png")
        with self.assertRaises(ValueError):
            ROOM.send_file(gen_img)

    def test_make_attachment_handles_cross_drive_relpath_error(self):
        from unittest import mock
        in_room = os.path.join(ROOM.files_dir(), "1_shot.png")
        with open(in_room, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        ext_dir = tempfile.mkdtemp(prefix="rt_cross_drive_")
        ext_file = os.path.join(ext_dir, "2_ext.png")
        with open(ext_file, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        with mock.patch("bridge.room.os.path.relpath", side_effect=ValueError("path is on mount 'D:', start on mount 'C:'")):
            att_in = R.make_attachment(in_room)
            self.assertEqual(R.abs_path(att_in), os.path.normpath(in_room))
            self.assertTrue(att_in["url"].startswith("/files/"))
            with mock.patch("bridge.room.in_dir", return_value=False):
                att_ext = R.make_attachment(ext_file)
                self.assertEqual(R.abs_path(att_ext), os.path.normpath(ext_file))
                self.assertEqual(att_ext["url"], "")


if __name__ == "__main__":
    unittest.main()
