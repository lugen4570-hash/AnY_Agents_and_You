"""Run a read-only, round-based debate using the room's existing Agent sessions."""

import threading

from . import access, execution, registry
from .common import MAX_ANN, is_archived

READY = "【可总结】"
PASS = "【跳过】"


def parse_turn(raw):
    text = (raw or "").strip()
    ready = text.endswith(READY)
    body = text.removesuffix(READY).rstrip() if ready else text
    skipped = body.strip() in ("", PASS)
    if skipped:
        body = ""
    return body, ready, skipped


def snapshot(room):
    value = room.meta.get("debate")
    if not value:
        return None
    value = dict(value)
    if not room.state.get("debate_active") and value["status"] in ("running", "summarizing"):
        value.update(status="interrupted", speaker=None)
    return value


def _available_agents(room):
    return [ai for ai in room.ais if (registry.get(ai) or {}).get("kind") != "user"
            and access.allowed(room, ai, "read") and access.allowed(room, ai, "post")
            and not room.is_guest(ai) and not room.meta.get("handed_off", {}).get(ai)
            and execution.binding(room, ai)["phase"] == "ready"]


def _validate_participants(available, participants, allow_single):
    if (not isinstance(participants, list) or any(not isinstance(ai, str) or ai not in available for ai in participants)
            or len(set(participants)) != len(participants) or len(participants) < (1 if allow_single else 2)):
        raise ValueError("请选择可在当前会话发言的 Agent，论道至少需要两位")


def start(room, data):
    topic = data.get("topic")
    minimum, maximum = data.get("min_rounds", 0), data.get("max_rounds")
    if not isinstance(topic, str) or not topic.strip() or len(topic.encode("utf-8")) > MAX_ANN:
        raise ValueError("请填写议题，长度不能超过 16 KB")
    if type(minimum) is not int or minimum < 0 or (maximum is not None and (type(maximum) is not int or maximum < minimum)):
        raise ValueError("轮次下限须为非负整数，上限须大于等于下限或留空")
    with room.lock:
        if room.closed or is_archived(room.meta.get("status")) or room.busy_for():
            raise ValueError("会话正在忙或已归档，暂时不能开始论道")
        available = _available_agents(room)
        participants = data.get("participants", available)
        _validate_participants(available, participants, maximum == 0)
        moderator = data.get("moderator") or participants[0]
        if moderator not in participants:
            raise ValueError("主持人须为参辩 Agent")
        room.meta["debate"] = {"topic": topic.strip(), "participants": list(participants), "moderator": moderator,
                               "min_rounds": minimum, "max_rounds": maximum, "completed_rounds": 0,
                               "phase_start_round": 0, "blind_first": bool(data.get("blind_first", True)),
                               "feedback": "", "status": "running", "speaker": None, "finish_requested": False}
        room.save_meta()
        room.state["debate_active"] = True
        room.state["debate_cancelled"] = False
        room.system_note("开始论道：" + topic.strip())
        state = snapshot(room)
        threading.Thread(target=run, args=(room,), daemon=True, name="debate-" + room.id).start()
        return state


def continue_debate(room, data):
    feedback = data.get("feedback")
    if not isinstance(feedback, str) or not feedback.strip() or len(feedback.encode("utf-8")) > MAX_ANN:
        raise ValueError("请填写你的反馈或补充意见，长度不能超过 16 KB")
    add_min, add_max = data.get("min_rounds", 1), data.get("max_rounds", 3)
    if type(add_min) is not int or add_min < 0 or (add_max is not None and (type(add_max) is not int or add_max < add_min)):
        raise ValueError("轮次下限须为非负整数，上限须大于等于下限或留空")
    with room.lock:
        if room.closed or is_archived(room.meta.get("status")) or room.busy_for():
            raise ValueError("会话正在忙或已归档，暂时不能继续论道")
        prev = snapshot(room)
        if not prev or room.state.get("debate_active") or prev.get("status") in ("running", "summarizing"):
            raise ValueError("当前会话还没有可继续的论道")
        available = _available_agents(room)
        participants = data.get("participants")
        if participants is None:
            participants = [ai for ai in prev.get("participants", []) if ai in available]
        _validate_participants(available, participants, add_max == 0)
        moderator = data.get("moderator") or (prev.get("moderator") if prev.get("moderator") in participants else participants[0])
        if moderator not in participants:
            raise ValueError("主持人须为参辩 Agent")
        base = int(prev.get("completed_rounds", 0))
        note = feedback.strip()
        room.add_message("你", note, origin="debate-feedback")
        room.meta["debate"] = {
            "topic": prev["topic"],
            "participants": list(participants),
            "moderator": moderator,
            "min_rounds": base + add_min,
            "max_rounds": None if add_max is None else base + add_max,
            "completed_rounds": base,
            "phase_start_round": base,
            "blind_first": bool(data.get("blind_first", True)),
            "feedback": note,
            "status": "running",
            "speaker": None,
            "finish_requested": False,
        }
        room.save_meta()
        room.state["debate_active"] = True
        room.state["debate_cancelled"] = False
        room.system_note("继续论道：" + prev["topic"])
        state = snapshot(room)
        threading.Thread(target=run, args=(room,), daemon=True, name="debate-" + room.id).start()
        return state


def finish(room):
    with room.lock:
        state = room.meta.get("debate") or {}
        if not room.state.get("debate_active") or state.get("status") not in ("running", "summarizing"):
            raise ValueError("没有正在进行的论道")
        state["finish_requested"] = True
        room.save_meta()
        return snapshot(room)


def _blind_turn_prompt(state, rounds):
    if state.get("feedback") and rounds > 0:
        return ("【论道第 %d 轮（基于用户反馈独立表态）】议题：%s\n用户最新反馈：%s\n"
                "请结合用户最新反馈，独立说明你的立场和依据（本轮其他成员的观点将在全员完成后一并公开）。"
                "如果没有新的补充或异议，可直接只回复 %s 跳过本轮发言。"
                "如果已经可以给出最终回答，在末尾另起一行写 %s。需要查证可使用只读工具。"
                % (rounds + 1, state["topic"], state["feedback"], PASS, READY))
    return ("【论道第 %d 轮（独立表态）】议题：%s\n"
            "请独立说明你的立场和依据（本轮其他成员的观点将在全员完成后一并公开）。"
            "如果没有新的补充或异议，可直接只回复 %s 跳过本轮发言。"
            "如果已经可以给出最终回答，在末尾另起一行写 %s。需要查证可使用只读工具。"
            % (rounds + 1, state["topic"], PASS, READY))


def run(room):
    state = room.meta["debate"]
    status = "failed"
    try:
        while True:
            with room.lock:
                rounds = state["completed_rounds"]
                if room.state["debate_cancelled"]:
                    return
                if rounds == state["max_rounds"] or (state["finish_requested"] and rounds >= state["min_rounds"]):
                    break
                is_blind = bool(state.get("blind_first", True)) and rounds == int(state.get("phase_start_round", 0))
            ready = True
            if is_blind:
                with room.lock:
                    if room.state["debate_cancelled"]:
                        return
                    participants = list(state["participants"])
                    tags = [(ai, room.job_tag(ai)) for ai in participants]
                    room.state["debate_blind_posts"] = {ai: [] for ai in participants}
                    state["speaker"] = "、".join(participants)
                    room.save_meta()
                turn = _blind_turn_prompt(state, rounds)
                results, errors = {}, []
                results_lock = threading.Lock()

                def _worker(ai, tag):
                    try:
                        res = room.process_job(ai, tag, debate_prompt=turn, debate_defer=True)
                    except Exception as exc:
                        with results_lock:
                            errors.append(exc)
                        return
                    with results_lock:
                        results[ai] = res

                threads = [threading.Thread(target=_worker, args=(ai, tag), daemon=True,
                                            name=f"debate-blind-{room.id}-{ai}") for ai, tag in tags]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                if errors:
                    raise errors[0]
                with room.lock:
                    posts = room.state.pop("debate_blind_posts")
                    if room.closed or room.state["debate_cancelled"] or any(results.get(ai) is None for ai in participants):
                        return
                    for ai in participants:
                        res = results[ai]
                        if res["skipped"]:
                            room.system_note("%s 第 %d 轮无异议，跳过发言" % (ai, rounds + 1))
                        else:
                            for text, attachments in posts[ai]:
                                room.post_progress(ai, text, attachments)
                            room.add_message(ai, res["text"], to_user=False, origin="debate", progress=res.get("progress"))
                        ready = ready and (res["ready"] or res["skipped"])
            else:
                for ai in state["participants"]:
                    with room.lock:
                        if room.state["debate_cancelled"]:
                            return
                        state["speaker"] = ai
                        tag = room.job_tag(ai)
                    turn = ("【论道第 %d 轮】议题：%s\n请针对已出现的观点提出反驳、补充或修正。"
                            "如果没有新的补充或异议，可直接只回复 %s 跳过本轮发言（后续若再有异议仍可发言）。"
                            "如果已经可以给出最终回答，在末尾另起一行写 %s。需要查证可使用只读工具。"
                            % (rounds + 1, state["topic"], PASS, READY))
                    reply = room.process_job(ai, tag, debate_prompt=turn)
                    if not reply:
                        return
                    _, is_ready, is_skipped = parse_turn(reply)
                    if is_skipped:
                        room.system_note("%s 第 %d 轮无异议，跳过发言" % (ai, rounds + 1))
                    ready = ready and (is_ready or is_skipped)
            with room.lock:
                state["completed_rounds"] += 1
                room.save_meta()
                if ready and state["completed_rounds"] >= state["min_rounds"]:
                    break
        ai = state["moderator"]
        with room.lock:
            if room.state["debate_cancelled"]:
                return
            state.update(status="summarizing", speaker=ai)
            room.save_meta()
            tag = room.job_tag(ai)
        prompt = ("【论道最终回答】议题：%s\n请综合本次论道，给出可以直接交给用户的最终答案，"
                  "说明采纳的观点和理由、仍存在的分歧。若没有进行辩论，直接作答。需要查证可使用只读工具。"
                  % state["topic"])
        if state.get("feedback"):
            prompt += "\n请回应用户本次补充的意见：\n" + state["feedback"]
        if room.process_job(ai, tag, debate_prompt=prompt, debate_summary=True):
            status = "completed"
    except Exception as error:
        room.system_note("论道运行失败：%s" % error)
    finally:
        with room.lock:
            room.state.pop("debate_blind_posts", None)
            if room.state["debate_cancelled"]:
                status = "cancelled"
            state.update(status=status, speaker=None)
            room.state["debate_active"] = False
            room.save_meta()
            if status == "failed":
                room.system_note("论道未完成。已收到的发言仍在会话中，可检查 Agent 状态后重试。")
