"""Run a read-only, round-based debate using the room's existing Agent sessions."""

import threading

from . import access, execution, registry
from .common import MAX_ANN, is_archived

READY = "【可总结】"


def snapshot(room):
    value = room.meta.get("debate")
    if not value:
        return None
    value = dict(value)
    if not room.state.get("debate_active") and value["status"] in ("running", "summarizing"):
        value.update(status="interrupted", speaker=None)
    return value


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
        available = [ai for ai in room.ais if (registry.get(ai) or {}).get("kind") != "user"
                     and access.allowed(room, ai, "read") and access.allowed(room, ai, "post")
                     and not room.is_guest(ai) and not room.meta.get("handed_off", {}).get(ai)
                     and execution.binding(room, ai)["phase"] == "ready"]
        participants = data.get("participants", available)
        if (not isinstance(participants, list) or any(not isinstance(ai, str) or ai not in available for ai in participants)
                or len(set(participants)) != len(participants) or len(participants) < (1 if maximum == 0 else 2)):
            raise ValueError("请选择可在当前会话发言的 Agent，论道至少需要两位")
        moderator = data.get("moderator") or participants[0]
        if moderator not in participants:
            raise ValueError("主持人须为参辩 Agent")
        room.meta["debate"] = {"topic": topic.strip(), "participants": list(participants), "moderator": moderator,
                               "min_rounds": minimum, "max_rounds": maximum, "completed_rounds": 0,
                               "status": "running", "speaker": None, "finish_requested": False}
        room.save_meta()
        room.state["debate_active"] = True
        room.state["debate_cancelled"] = False
        room.system_note("开始论道：" + topic.strip())
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
            ready = True
            for ai in state["participants"]:
                with room.lock:
                    if room.state["debate_cancelled"]:
                        return
                    state["speaker"] = ai
                    tag = room.job_tag(ai)
                turn = ("【论道第 %d 轮】议题：%s\n请说明你的立场和依据，针对已出现的观点提出反驳或修正。"
                        "如果已经可以给出最终回答，在末尾另起一行写 %s。需要查证可使用只读工具。"
                        % (rounds + 1, state["topic"], READY))
                reply = room.process_job(ai, tag, debate_prompt=turn)
                if not reply:
                    return
                ready = ready and reply.rstrip().endswith(READY)
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
        if room.process_job(ai, tag, debate_prompt=prompt, debate_summary=True):
            status = "completed"
    except Exception as error:
        room.system_note("论道运行失败：%s" % error)
    finally:
        with room.lock:
            if room.state["debate_cancelled"]:
                status = "cancelled"
            state.update(status=status, speaker=None)
            room.state["debate_active"] = False
            room.save_meta()
            if status == "failed":
                room.system_note("论道未完成。已收到的发言仍在会话中，可检查 Agent 状态后重试。")
