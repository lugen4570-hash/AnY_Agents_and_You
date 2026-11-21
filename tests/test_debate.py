"""Debate endpoints, round bounds and termination through the room scheduler."""

import threading
import unittest
from unittest.mock import patch

import test_multiroom as support

from bridge import debate


class DebateTests(unittest.TestCase):
    def setUp(self):
        self.room = support.R.rooms.create("论道测试", "", support.WD, participants=["codex", "claude"])
        self.calls = []

    def start(self, **options):
        return support.call("POST", support.rp(self.room, "debate/start"), {"topic": "议题", **options})

    def state(self):
        return support.call("GET", support.rp(self.room, "state"))[1]["debate"]

    def reply(self, ai, prompt, sid, images, mode, room):
        self.calls.append((ai, prompt, mode))
        answer = "最终答复" if "【论道最终回答】" in prompt else f"{ai} 的观点 @用户 @codex\n{debate.READY}"
        return True, answer, sid or f"{ai}-debate-session", []

    def test_zero_rounds_only_calls_moderator(self):
        with patch.object(support.R, "ai_caller", self.reply):
            self.assertEqual(self.start(max_rounds=0, moderator="claude")[0], 200)
            self.assertTrue(support.idle(self.room))
        self.assertEqual([ai for ai, _, _ in self.calls], ["claude"])
        self.assertEqual(self.state()["completed_rounds"], 0)
        self.assertEqual(self.state()["status"], "completed")
        self.assertEqual(self.room.messages[-1]["origin"], "debate-summary")

    def test_agreement_waits_for_minimum_and_turns_are_read_only(self):
        self.room.set_mode("work")
        with patch.object(support.R, "ai_caller", self.reply):
            self.assertEqual(self.start(min_rounds=2, max_rounds=5)[0], 200)
            self.assertTrue(support.idle(self.room))
        self.assertEqual([ai for ai, _, _ in self.calls], ["codex", "claude", "codex", "claude", "codex"])
        self.assertTrue(all(mode == "discuss" for _, _, mode in self.calls))
        self.assertIn("codex 的观点", self.calls[1][1])
        self.assertEqual(self.state()["completed_rounds"], 2)
        self.assertTrue(all(debate.READY not in msg["text"] for msg in self.room.messages))

    def test_unlimited_debate_can_finish_after_minimum(self):
        running, release = threading.Event(), threading.Event()

        def disagree(ai, prompt, sid, images, mode, room):
            if not self.calls:
                running.set()
                release.wait(5)
            ok, answer, session, edits = self.reply(ai, prompt, sid, images, mode, room)
            return ok, answer.removesuffix(debate.READY), session, edits

        with patch.object(support.R, "ai_caller", disagree):
            self.assertEqual(self.start(min_rounds=1, max_rounds=None)[0], 200)
            try:
                self.assertTrue(running.wait(5))
                self.assertEqual(self.start(max_rounds=0)[0], 409)
                status, payload = support.call("POST", support.rp(self.room, "debate/finish"), {})
                self.assertEqual(status, 200)
                self.assertTrue(payload["debate"]["finish_requested"])
            finally:
                release.set()
            self.assertTrue(support.idle(self.room))
        self.assertEqual(self.state()["completed_rounds"], 1)
        self.assertEqual(self.state()["status"], "completed")

    def test_maximum_stops_debate_without_agreement(self):
        def disagree(ai, prompt, sid, images, mode, room):
            ok, answer, session, edits = self.reply(ai, prompt, sid, images, mode, room)
            return ok, answer.removesuffix(debate.READY), session, edits

        with patch.object(support.R, "ai_caller", disagree):
            self.assertEqual(self.start(min_rounds=2, max_rounds=1)[0], 409)
            self.assertEqual(self.start(max_rounds=1)[0], 200)
            self.assertTrue(support.idle(self.room))
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.state()["completed_rounds"], 1)
        self.assertEqual(self.state()["status"], "completed")


if __name__ == "__main__":
    unittest.main()
