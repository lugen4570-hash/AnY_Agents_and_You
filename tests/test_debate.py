"""Debate endpoints, blind first round, turn skipping, continuation and termination."""

import threading
import unittest
from unittest.mock import patch

import test_multiroom as support

from bridge import debate


class DebateTests(unittest.TestCase):
    def setUp(self):
        self.room = support.R.rooms.create("论道测试", "", support.WD, participants=["codex", "claude"])
        self.calls = []
        self.calls_lock = threading.Lock()

    def start(self, **options):
        return support.call("POST", support.rp(self.room, "debate/start"), {"topic": "议题", **options})

    def cont(self, **options):
        return support.call("POST", support.rp(self.room, "debate/continue"), options)

    def state(self):
        return support.call("GET", support.rp(self.room, "state"))[1]["debate"]

    def reply(self, ai, prompt, sid, images, mode, room):
        with self.calls_lock:
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
        self.assertEqual({ai for ai, _, _ in self.calls[:2]}, {"codex", "claude"})
        self.assertEqual([ai for ai, _, _ in self.calls[2:]], ["codex", "claude", "codex"])
        self.assertTrue(all(mode == "discuss" for _, _, mode in self.calls))
        self.assertNotIn("codex 的观点", self.calls[0][1])
        self.assertNotIn("claude 的观点", self.calls[0][1])
        self.assertNotIn("codex 的观点", self.calls[1][1])
        self.assertNotIn("claude 的观点", self.calls[1][1])
        self.assertIn("claude 的观点", self.calls[2][1])
        self.assertIn("codex 的观点", self.calls[3][1])
        self.assertEqual(self.state()["completed_rounds"], 2)
        self.assertTrue(all(debate.READY not in msg["text"] for msg in self.room.messages))
        self.assertTrue(all(debate.PASS not in msg["text"] for msg in self.room.messages))

    def test_first_round_is_blind_and_parallel(self):
        barrier = threading.Barrier(2, timeout=3)
        seen_in_r1 = {}

        def blind_caller(ai, prompt, sid, images, mode, room):
            with self.calls_lock:
                self.calls.append((ai, prompt, mode))
            if "（独立表态）" in prompt:
                barrier.wait()
                seen_in_r1[ai] = prompt
                answer = f"{ai} 首轮独立看法"
            elif "【论道最终回答】" in prompt:
                answer = "盲发总结"
            else:
                answer = f"{ai} 次轮回应\n{debate.READY}"
            return True, answer, sid or f"{ai}-debate-session", []

        with patch.object(support.R, "ai_caller", blind_caller):
            self.assertEqual(self.start(min_rounds=1, max_rounds=2)[0], 200)
            self.assertTrue(support.idle(self.room))
        self.assertEqual(set(seen_in_r1), {"codex", "claude"})
        self.assertNotIn("首轮独立看法", seen_in_r1["codex"])
        self.assertNotIn("首轮独立看法", seen_in_r1["claude"])
        debate_msgs = [m for m in self.room.messages if m.get("origin") == "debate"]
        self.assertEqual([(m["speaker"], m["text"]) for m in debate_msgs[:2]],
                         [("codex", "codex 首轮独立看法"), ("claude", "claude 首轮独立看法")])

    def test_opening_round_holds_live_progress_and_posts_until_all_agents_finish(self):
        progress_written, release_round = threading.Event(), threading.Event()
        second_round = []

        def caller(ai, prompt, sid, images, mode, room):
            if "（独立表态）" in prompt:
                if ai == "codex":
                    room.push_live(ai, {"live": "首轮实时观点"})
                    room.post_progress(ai, "首轮中途发帖", [])
                    room.handle_message(ai, "首轮外部发帖", origin="external")
                    progress_written.set()
                release_round.wait(8)
                return True, f"{ai} 的独立观点", sid or ai, []
            if "【论道第 2 轮】" in prompt:
                second_round.append(prompt)
            return True, f"{ai} 的后续答复\n{debate.READY}", sid or ai, []

        with patch.object(support.R, "ai_caller", caller):
            self.assertEqual(self.start(min_rounds=2, max_rounds=2)[0], 200)
            try:
                self.assertTrue(progress_written.wait(5))
                reply = support.call("GET", support.rp(self.room, "state"))[1]
                self.assertIn("codex", reply["running"])
                self.assertNotIn("codex", reply["live"])
                with self.room.lock:
                    self.assertFalse(any("首轮" in m["text"] or m.get("origin") == "debate" for m in self.room.messages))
            finally:
                release_round.set()
            self.assertTrue(support.idle(self.room))

        texts = [m["text"] for m in self.room.messages]
        self.assertIn("首轮中途发帖", texts)
        self.assertIn("首轮外部发帖", texts)
        first = next(m for m in self.room.messages if m["text"] == "codex 的独立观点")
        self.assertIn("首轮实时观点", first["progress"])
        self.assertTrue(any("codex 的独立观点" in prompt for prompt in second_round))

    def test_agent_can_skip_turn_until_new_objection_while_counting_rounds(self):
        counts = {"codex": 0, "claude": 0}

        def skip_caller(ai, prompt, sid, images, mode, room):
            if "【论道最终回答】" in prompt:
                return True, "最终总结", sid or f"{ai}-s", []
            counts[ai] += 1
            n = counts[ai]
            if ai == "codex":
                if n == 1:
                    return True, "codex 初稿", sid or "codex-s", []
                if n == 2:
                    return True, debate.PASS, sid or "codex-s", []
                return True, f"codex 看到新异议后补充\n{debate.READY}", sid or "codex-s", []
            if n == 1:
                return True, "claude 初稿", sid or "claude-s", []
            if n == 2:
                return True, "claude 提出新反驳", sid or "claude-s", []
            return True, debate.PASS, sid or "claude-s", []

        with patch.object(support.R, "ai_caller", skip_caller):
            self.assertEqual(self.start(min_rounds=1, max_rounds=3)[0], 200)
            self.assertTrue(support.idle(self.room))
        self.assertEqual(self.state()["completed_rounds"], 3)
        self.assertEqual(self.state()["status"], "completed")
        codex_msgs = [m["text"] for m in self.room.messages if m["speaker"] == "codex" and m.get("origin") == "debate"]
        self.assertEqual(codex_msgs, ["codex 初稿", "codex 看到新异议后补充"])
        skip_notes = [m["text"] for m in self.room.messages if m["speaker"] == "系统" and "跳过发言" in m["text"]]
        self.assertTrue(any("codex 第 2 轮无异议，跳过发言" in t for t in skip_notes))
        self.assertTrue(any("claude 第 3 轮无异议，跳过发言" in t for t in skip_notes))

    def test_continue_debate_with_user_feedback(self):
        self.assertEqual(self.cont(feedback="还没有历史论道")[0], 409)

        def caller(ai, prompt, sid, images, mode, room):
            with self.calls_lock:
                self.calls.append((ai, prompt, mode))
            if "【论道最终回答】" in prompt:
                return True, f"总结第 {len(self.calls)} 次", sid or f"{ai}-s", []
            return True, f"{ai} 表态\n{debate.READY}", sid or f"{ai}-s", []

        with patch.object(support.R, "ai_caller", caller):
            self.assertEqual(self.start(min_rounds=1, max_rounds=1)[0], 200)
            self.assertTrue(support.idle(self.room))
            self.assertEqual(self.state()["completed_rounds"], 1)
            self.assertEqual(self.cont(feedback="   ")[0], 409)
            status, payload = self.cont(feedback="我不满意方案A，请补充安全性分析", min_rounds=1, max_rounds=2)
            self.assertEqual(status, 200)
            self.assertEqual(payload["debate"]["status"], "running")
            self.assertTrue(support.idle(self.room))

        self.assertEqual(self.state()["completed_rounds"], 2)
        self.assertEqual(self.state()["status"], "completed")
        feedback_msgs = [m for m in self.room.messages if m.get("origin") == "debate-feedback"]
        self.assertEqual(len(feedback_msgs), 1)
        self.assertEqual(feedback_msgs[0]["speaker"], "你")
        self.assertIn("补充安全性分析", feedback_msgs[0]["text"])
        cont_prompts = [p for _, p, _ in self.calls if "基于用户反馈独立表态" in p]
        self.assertEqual(len(cont_prompts), 2)
        self.assertTrue(all("补充安全性分析" in p for p in cont_prompts))
        self.assertIn("请回应用户本次补充的意见", self.calls[-1][1])
        self.assertIn("补充安全性分析", self.calls[-1][1])

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
                self.assertEqual(self.cont(feedback="运行中不能继续")[0], 409)
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
