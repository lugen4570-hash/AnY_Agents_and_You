"""Exercise the terminal client against the same HTTP server used by the desktop."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".test-tmp"
SCRATCH.mkdir(exist_ok=True)
DATA = tempfile.TemporaryDirectory(dir=SCRATCH, prefix="cli-", ignore_cleanup_errors=True)
os.environ["ROUNDTABLE_LOG_DIR"] = DATA.name
sys.path.insert(0, str(ROOT))

from bridge import room, web
from bridge.cli import LocalClient, main, room_path
from bridge.cli_autostart import server_ready


class CojamCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = web.ExclusiveServer(("127.0.0.1", 0), web.Handler)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.thread.join, 5)
        cls.addClassCleanup(cls.server.shutdown)
        cls.port = cls.server.server_address[1]

    def command(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-m", "bridge.cli", "--port", str(self.port), *args],
                              cwd=ROOT, input=stdin, capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=10)

    def test_json_commands_use_existing_room_and_cursor(self):
        meeting = room.rooms.create("CLI 脚本", wd=DATA.name, participants=[])
        listing = self.command("rooms")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn(meeting.id, [row["id"] for row in json.loads(listing.stdout)["rooms"]])
        sent = self.command("send", meeting.id, "-", stdin="你好\n第二行")
        self.assertEqual(sent.returncode, 0, sent.stderr)
        client = LocalClient(self.port)
        batch = client.call(room_path(meeting.id, "messages"))
        self.assertEqual(batch["messages"][-1]["text"], "你好\n第二行")
        result = self.command("messages", meeting.id, "--since", str(batch["next"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["messages"], [])

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_interactive_entrypoint_starts_backend_on_selected_port_and_reuses_it(self):
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
        with tempfile.TemporaryDirectory(dir=SCRATCH, ignore_cleanup_errors=True) as directory:
            environment = {
                "ROUNDTABLE_LOG_DIR": directory, "ROUNDTABLE_PORT": "1",
                "ROUNDTABLE_LAN_PORT": "0", "ROUNDTABLE_TAILSCALE_PORT": "0",
            }
            with (patch.dict(os.environ, environment),
                  patch("bridge.terminal.CojamTerminal") as terminal):
                self.assertFalse(server_ready(port))
                try:
                    terminal.return_value.run.side_effect = lambda: self.assertTrue(server_ready(port))
                    self.assertEqual(main(["--port", str(port), "open", "example-room"]), 0)
                    client, room_id = terminal.call_args.args
                    self.assertEqual((client.port, room_id), (port, "example-room"))
                    original = client.call("/api/rooms")
                    with patch("bridge.cli_autostart.subprocess.Popen") as start:
                        os.environ["ROUNDTABLE_PORT"] = str(port)
                        self.assertEqual(main([]), 0)
                        start.assert_not_called()
                    self.assertEqual(client.call("/api/rooms"), original)
                finally:
                    if server_ready(port):
                        LocalClient(port).call("/api/server/exit", {})

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_terminal_brand_motion_respects_settings(self):
        from bridge.terminal import CojamTerminal, ReplyActivity, WelcomeMark

        async def run(*, no_color, animation_level):
            app = CojamTerminal(LocalClient(self.port))
            app.no_color = no_color
            app.animation_level = animation_level
            async with app.run_test(size=(70, 20)) as pilot:
                mark = app.query_one(WelcomeMark)
                activity = app.query_one(ReplyActivity)
                activity.show(["Codex 正在回复"], color="#10a37f", leading=True)
                self.assertEqual(str(mark.render()), "∀ AnY")
                self.assertEqual(mark.size.height, 1)
                self.assertEqual(str(activity.render()), "● Codex 正在回复")
                await pilot.pause(.4)
                self.assertEqual(activity.beat, 0)

        asyncio.run(run(no_color=True, animation_level="full"))
        asyncio.run(run(no_color=False, animation_level="none"))

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_terminal_home_hides_archived_rooms_and_archived_only_projects(self):
        from textual.widgets import OptionList
        from bridge.terminal import CojamTerminal, SessionPicker

        async def run():
            app = CojamTerminal(LocalClient(self.port))
            groups = [{"id": "archive", "name": "旧项目"}, {"id": "mixed", "name": "混合项目"},
                      {"id": "empty", "name": "新项目"}]
            rows = [{"id": "archived", "project": "archive", "title": "旧会话", "archived": True},
                    {"id": "old", "project": "mixed", "title": "另一场旧会话", "archived": True},
                    {"id": "active", "project": "mixed", "title": "当前会话"}]
            async with app.run_test(size=(80, 22)):
                app.render_rooms({"rooms": rows, "projects": groups, "last": "archived"}, force=True)
                options = app.query_one("#rooms", OptionList)
                self.assertEqual([str(options.get_option_at_index(i).prompt) for i in range(options.option_count)],
                                 ["混合项目", "  ○ 当前会话  ·  空闲", "新项目 · 暂无会话"])
                self.assertEqual(options.highlighted_option.id, "active")
                self.assertEqual([row["id"] for row in SessionPicker(app.rooms, app.projects, app.room).rooms],
                                 ["archived", "old", "active"])

        asyncio.run(run())

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_transcript_distinguishes_speakers_without_color(self):
        from io import StringIO
        from rich.console import Console
        from bridge.terminal import transcript_entry

        output = StringIO()
        console = Console(file=output, color_system=None, width=46)
        agents = {"claude": {"label": "Claude"}, "codex": {"label": "Codex"},
                  "lee": {"label": "Lee", "kind": "user"}}
        for speaker in ("你", "claude", "codex", "lee", "系统"):
            console.print(transcript_entry({"speaker": speaker, "text": "**原文**", "time": "12:00"},
                                           agents, {}, {}))
        result = output.getvalue()
        for marker in ("◆ 你", "● Claude  Agent", "● Codex  Agent", "○ Lee  成员", "─ 系统"):
            self.assertIn(marker, result)
        self.assertEqual(result.count("**原文**"), 3)

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_terminal_create_send_and_receive(self):
        from textual.widgets import Footer, Input, OptionList, RichLog, Static
        from bridge.terminal import CojamTerminal, WelcomeMark

        async def wait_for(pilot, check):
            for _ in range(40):
                if check():
                    return
                await pilot.pause(0.15)
            self.fail("terminal did not receive the expected state")

        async def run():
            client = LocalClient(self.port)
            existing = room.rooms.create("启动页会话", wd=DATA.name, participants=[])
            room.set_last(existing.id)
            app = CojamTerminal(client)
            app.no_color = False
            app.animation_level = "full"
            async with app.run_test(size=(120, 36)) as pilot:
                await wait_for(pilot, lambda: app.connected and app.rooms)
                mark = app.query_one(WelcomeMark)
                await wait_for(pilot, lambda: mark.frame == len(mark.FRAMES) - 1)
                self.assertEqual(mark.frame, len(mark.FRAMES) - 1)
                self.assertEqual(str(mark.render()), "∀ AnY")
                self.assertEqual(mark.size.height, 1)
                self.assertIsNone(app.room)
                self.assertFalse(app.query_one("#chat").display)
                self.assertFalse(app.query(Footer))
                self.assertIn("新建项目", app.export_screenshot())
                self.assertEqual(app.query_one("#rooms", OptionList).highlighted_option.id, existing.id)
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.room == existing.id)
                await pilot.press("/")
                self.assertTrue(app.composer.menu.display)
                self.assertEqual(app.composer.suggestions[0].label, "/new")
                await pilot.press("r", "e", "s")
                self.assertEqual([candidate.label for candidate in app.composer.suggestions], ["/resume"])
                await pilot.press("escape")
                self.assertFalse(app.composer.menu.display)
                self.assertEqual(app.composer.prompt.text, "/res")
                app.composer.set_text("")
                await pilot.press("ctrl+n")
                await pilot.press("escape")
                app.composer.set_text("/project")
                await pilot.press("enter")
                await pilot.pause()
                app.screen.query_one("#new-title", Input).value = "终端项目"
                app.screen.query_one("#new-directory", Input).value = DATA.name
                await pilot.press("enter")
                await wait_for(pilot, lambda: bool(app.screen.query("#new-project")))
                app.screen.query_one("#new-title", Input).value = "终端开会"
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.state.get("title") == "终端开会")
                self.assertTrue(app.state["project"])
                await pilot.press("f2")
                self.assertTrue(app.query_one("#rooms", OptionList).has_focus)
                self.assertIsNone(app.room)
                await pilot.press("enter")
                self.assertFalse(app.query_one("#navigation").display)
                await wait_for(pilot, lambda: app.state.get("title") == "终端开会")
                app.composer.set_text("/mo")
                await pilot.press("down", "tab")
                self.assertEqual(app.composer.prompt.text, "/mode ")
                app.composer.set_text("/mode")
                self.assertEqual(app.composer.suggestions[0].label, "/mode")
                await pilot.press("tab")
                await pilot.press("down", "tab")
                self.assertEqual(app.composer.prompt.text, "/mode work")
                self.assertEqual(room.rooms.get(app.room).mode(), "discuss")
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.state.get("mode") == "work")
                app.composer.set_text("/mode discuss")
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.state.get("mode") == "discuss")
                app.composer.set_text("/todo 核对结果")
                await pilot.press("enter")
                await wait_for(pilot, lambda: "核对结果" in str(app.query_one("#details", Static).content))
                meeting = room.rooms.get(app.room)
                meeting.board_op("你", "add", "note", "今晚确认")
                meeting.board_op("你", "add", "todo", "先前任务")
                meeting.board_op("你", "done", "", "", [3])
                await wait_for(pilot, lambda: "[x] #3 先前任务" in str(app.query_one("#details", Static).content))
                details = str(app.query_one("#details", Static).content)
                self.assertIn("▌ 待办  1\n  [ ] #1 核对结果", details)
                self.assertIn("▌ 公告  1\n  › #2 今晚确认", details)
                self.assertIn("▌ 已完成  1\n  [x] #3 先前任务", details)
                room.rooms.get(app.room).set_participants([])
                app.composer.set_text("从终端发言")
                await pilot.press("shift+enter")
                app.composer.prompt.insert("第二行")
                self.assertEqual(app.composer.prompt.text, "从终端发言\n第二行")
                await pilot.press("enter")
                await wait_for(pilot, lambda: any("从终端发言" in line.text for line in app.query_one(RichLog).lines))
                await pilot.press("up")
                self.assertEqual(app.composer.prompt.text, "从终端发言\n第二行")
                await pilot.press("down")
                self.assertEqual(app.composer.prompt.text, "")
                await asyncio.to_thread(client.call, room_path(app.room, "send"), {"text": "从网页同步"})
                await wait_for(pilot, lambda: any("从网页同步" in line.text for line in app.query_one(RichLog).lines))
                meeting = room.rooms.get(app.room)
                await wait_for(pilot, lambda: app.state.get("participants") == [])
                detected = {"detected": [{"id": "codex", "label": "Codex", "options": ["codex", "mcp"]}]}
                with (patch.object(web.discovery, "scan", return_value=detected),
                      patch.object(web.discovery, "ensure_scanned"),
                      patch.object(web.discovery, "status", return_value=detected),
                      patch.object(web.discovery, "connect", return_value=(True, {"id": "codex", "msg": "测试接入成功"})) as connect):
                    app.composer.set_text("/scan")
                    await pilot.press("enter")
                    await wait_for(pilot, lambda: any("Codex  ·  cli" in line.text for line in app.query_one(RichLog).lines))
                    app.composer.set_text("/connect codex cli")
                    await pilot.press("enter")
                    await wait_for(pilot, lambda: any("测试接入成功" in line.text for line in app.query_one(RichLog).lines))
                    connect.assert_called_once_with("codex", "codex", False)
                    await wait_for(pilot, lambda: not app.sending)
                app.composer.set_text("/invite codex")
                await pilot.press("enter")
                await wait_for(pilot, lambda: "codex" in app.state.get("participants", []))
                app.composer.set_text("/model codex cojam-test-model")
                await pilot.press("enter")
                await wait_for(pilot, lambda: meeting.own_models("codex")[0] == "cojam-test-model")
                with patch.object(app, "submit") as submit:
                    app.state["running"] = ["codex"]
                    app.composer.set_text("/")
                    await pilot.press("escape")
                    submit.assert_not_called()
                    await pilot.press("escape")
                    submit.assert_called_once_with(room_path(app.room, "stop"), {})
                with patch.object(room, "ai_caller", return_value=(True, "**收到终端消息**", "test-session", [])):
                    app.composer.set_text("@co 后续")
                    app.composer.prompt.move_cursor((0, 3))
                    await pilot.press("tab")
                    self.assertEqual(app.composer.prompt.text, "@codex 后续")
                    self.assertEqual(app.composer.prompt.cursor_location, (0, 6))
                    app.composer.set_text("@co")
                    self.assertEqual(app.composer.suggestions[0].label, "@codex")
                    await pilot.press("tab")
                    self.assertEqual(app.composer.prompt.text, "@codex ")
                    app.composer.prompt.insert("你好")
                    await pilot.press("enter")
                    await wait_for(pilot, lambda: any("收到终端消息" in line.text
                                                      for line in app.query_one(RichLog).lines))
                app.composer.set_text("/handoff codex")
                await pilot.press("enter")
                await wait_for(pilot, lambda: any("codex resume test-session" in line.text
                                                  for line in app.query_one(RichLog).lines))
                app.composer.set_text("/return codex")
                await pilot.press("enter")
                await wait_for(pilot, lambda: not meeting.meta["handed_off"]["codex"])
                meeting.set_participants(["codex", "claude"])
                await wait_for(pilot, lambda: "claude" in app.state.get("participants", []))
                self.assertIn("你", str(app.query_one("#roster", Static).content))
                self.assertIn("F3", app.export_screenshot())
                release = threading.Event()

                def debate_reply(ai, prompt, sid, images, mode, meeting):
                    if "【论道最终回答】" in prompt:
                        return True, "终端论道总结", sid or ai, []
                    release.wait(8)
                    return True, "论道观点", sid or ai, []

                with patch.object(room, "ai_caller", debate_reply):
                    try:
                        app.composer.set_text("/debate 终端验证议题")
                        await pilot.press("enter")
                        await wait_for(pilot, lambda: bool(app.screen.query("#debate-topic")))
                        self.assertEqual(app.screen.query_one("#debate-topic", Input).value, "终端验证议题")
                        app.screen.query_one("#debate-max", Input).value = ""
                        await pilot.click("#debate-start")
                        await wait_for(pilot, lambda: "论道" in str(app.query_one("#activity", Static).content))
                        app.composer.set_text("/debate-finish")
                        await pilot.press("enter")
                        await wait_for(pilot, lambda: meeting.meta["debate"]["finish_requested"])
                    finally:
                        release.set()
                    await wait_for(pilot, lambda: meeting.meta.get("debate", {}).get("status") == "completed")
                await pilot.resize_terminal(80, 24)
                self.assertFalse(app.query_one("#details-pane").display)
                await pilot.press("f3")
                self.assertTrue(app.query_one("#details-pane").display)
                self.assertFalse(app.query_one("#chat").display)
                self.assertIn("claude", str(app.query_one("#details", Static).content))
                await pilot.click("#hide-members")
                self.assertTrue(app.query_one("#chat").display)
                await pilot.click("#show-members")
                self.assertTrue(app.query_one("#details-pane").display)
                await pilot.press("f3")
                self.assertTrue(app.query_one("#chat").display)
                second = room.rooms.create("另一个会话", wd=DATA.name, participants=[])
                await wait_for(pilot, lambda: any(row["id"] == second.id for row in app.rooms))
                app.composer.set_text("未发送的草稿")
                await pilot.press("ctrl+r")
                app.screen.query_one("#session-search", Input).value = "另一个"
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.room == second.id)
                await wait_for(pilot, lambda: room.last_room() == second.id)
                self.assertEqual(app.composer.prompt.text, "")
                await pilot.press("ctrl+r")
                app.screen.query_one("#session-search", Input).value = "终端开会"
                await pilot.press("enter")
                await wait_for(pilot, lambda: app.room == meeting.id)
                await wait_for(pilot, lambda: room.last_room() == meeting.id)
                self.assertEqual(app.composer.prompt.text, "未发送的草稿")

        with patch.object(self.server, "owner_lifecycle") as lifecycle:
            asyncio.run(run())
        actions = [call.args[1] for call in lifecycle.update.call_args_list]
        self.assertIn("open", actions)
        self.assertEqual(actions[-1], "close")

    @unittest.skipUnless(importlib.util.find_spec("textual"), "install the cli extra to test the terminal UI")
    def test_terminal_left_right_arrows_switch_between_home_and_chat(self):
        from textual.widgets import OptionList
        from bridge.terminal import CojamTerminal

        async def wait_for(pilot, check):
            for _ in range(40):
                if check():
                    return
                await pilot.pause(0.15)
            self.fail("terminal did not reach expected state")

        async def run():
            client = LocalClient(self.port)
            meeting = room.rooms.create("左右切换会话", wd=DATA.name, participants=[])
            room.set_last(meeting.id)
            app = CojamTerminal(client)
            async with app.run_test(size=(100, 28)) as pilot:
                await wait_for(pilot, lambda: app.connected and app.rooms)
                self.assertIsNone(app.room)
                self.assertEqual(app.query_one("#rooms", OptionList).highlighted_option.id, meeting.id)
                await pilot.press("right")
                await wait_for(pilot, lambda: app.room == meeting.id)
                self.assertTrue(app.composer.prompt.has_focus)
                await pilot.press("left")
                await wait_for(pilot, lambda: app.room is None)
                self.assertEqual(app.query_one("#rooms", OptionList).highlighted_option.id, meeting.id)
                await pilot.press("right")
                await wait_for(pilot, lambda: app.room == meeting.id)
                app.composer.set_text("hello")
                self.assertEqual(app.composer.prompt.cursor_location, (0, 5))
                await pilot.press("left")
                self.assertEqual(app.room, meeting.id)
                self.assertEqual(app.composer.prompt.cursor_location, (0, 4))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
