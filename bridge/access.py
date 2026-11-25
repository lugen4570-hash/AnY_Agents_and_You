"""Application contacts, revocable credentials and conversation permissions."""
from __future__ import annotations

import hashlib
import os
import secrets
import threading
from dataclasses import asdict, dataclass, replace
from typing import Any, cast

from . import registry
from .common import LOG_DIR, in_dir, read_json, write_json

LOCK = threading.RLock()
PERMISSIONS = {"read": True, "post": True, "trigger": True, "board": False, "files": False, "work": False}
HUMAN_PERMISSIONS = dict(PERMISSIONS, trigger=False)
WORKSPACE_ACTIONS = ("read", "write", "exec")
MAX_HANDOFFS = 12


@dataclass(frozen=True)
class DispatchContext:
    root: str
    caller: str
    device: str = ""
    ceiling: str = "discuss"
    trace: tuple[str, ...] = ()

    def handoff(self, caller: str) -> DispatchContext:
        return replace(self, caller=caller, trace=(*self.trace, caller))

    def limited(self, mode: str) -> DispatchContext:
        return replace(self, ceiling=mode)

    def stored(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def restore(cls, raw: dict[str, Any]) -> DispatchContext:
        return cls(raw["root"], raw["caller"], raw["device"], raw["ceiling"], tuple(raw["trace"]))


def human(pid: str) -> bool:
    return (registry.get(pid) or {}).get("kind") == "user"


def guest_model(pid: str) -> dict[str, Any] | None:
    spec = registry.get(pid)
    if spec and spec.get("driver") == "http" and spec.get("http_protocol"):
        return cast(dict[str, Any], spec)
    return None


def guest_call_error(room: Any, caller: str, target: str) -> str:
    if not allowed(room, caller, "read") or not allowed(room, caller, "post") or not allowed(room, caller, "trigger"):
        return "房间未允许此外部成员调用 Agent"
    if not allowed(room, target, "read") or not allowed(room, target, "post"):
        return "此 Agent 当前没有在本会话回答的权限"
    policy = room.meta.get("agent_policies", {}).get(target, {})
    accepted = policy.get("accept_users")
    if (accepted is not None and caller not in accepted) or (
            accepted is None and not room.meta.get("guest_discussion", {}).get(target)):
        return "此 Agent 尚未开放外部成员讨论"
    from . import execution
    bound = execution.binding(room, target)
    if guest_model(target) is None or bound["endpoint"] != "http" or bound["phase"] != "ready":
        return "此执行端暂不支持隔离的外部讨论"
    return ""


def can_dispatch(room: Any, context: DispatchContext, target: str) -> str:
    if context.device and not room.device_can_dispatch(context.device):
        return "发起设备尚未获准在本会话派活，或其授权已收回"
    if human(target) or not allowed(room, target, "read") or not allowed(room, target, "post"):
        return "目标 Agent 未加入会话或没有回复权限"
    if context.root != "你":
        if not human(context.root):
            return "找不到授权本次任务的发起人"
        targets = room.meta.get("user_policies", {}).get(context.root, {}).get("call_agents")
        if targets is not None and target not in targets:
            return "房间未允许你调用这个 Agent"
        if error := guest_call_error(room, context.root, target):
            return error
    if context.caller != context.root:
        if len(context.trace) > MAX_HANDOFFS:
            return "本次任务已达到 Agent 转派次数上限"
        if not allowed(room, context.caller, "trigger"):
            return "来源 Agent 无权转派任务"
        policies = room.meta.get("agent_policies", {})
        targets = policies.get(context.caller, {}).get("handoff_targets")
        if targets is not None and target not in targets:
            return "来源 Agent 的转派范围没有包含目标"
        destination = policies.get(target, {})
        accepted_agents = destination.get("accept_agents")
        if not destination.get("accept_handoff", context.root == "你") or (
                accepted_agents is not None and context.caller not in accepted_agents):
            return "目标 Agent 未接受转派"
    cap = workspace_cap(room, target)
    if cap is not None and guest_model(target) is None and not all(cap.values()):
        grant = room.meta["agent_policies"][target]["workspace"]
        if all(grant.get(action) for action in WORKSPACE_ACTIONS):
            return "授权的执行设备未连接或工作目录已变更"
        return "此执行端无法强制执行所选读、写和命令限制"
    return ""


def workspace_target(room: Any, target: str) -> dict[str, str]:
    from . import execution, members
    bound = execution.binding(room, target)
    if execution.remote(room, target):
        scope = room.id if bound["endpoint"] == "desktop" else None
        status = members.broker.status(target, scope)
        return {"path": status["workdir"], "worker": status["worker"]}
    return {"path": os.path.normcase(os.path.realpath(room.workdir())), "worker": ""}


def workspace_cap(room: Any, target: str) -> dict[str, bool] | None:
    grant = room.meta.get("agent_policies", {}).get(target, {}).get("workspace")
    if grant is None:
        return None
    today = workspace_target(room, target)
    if not today["path"] or grant.get("path") != today["path"] or grant.get("worker", "") != today["worker"]:
        return dict.fromkeys(WORKSPACE_ACTIONS, False)
    return {key: bool(grant.get(key)) for key in WORKSPACE_ACTIONS}


def workspace_path_allowed(room: Any, target: str, action: str, path: str) -> bool:
    cap = workspace_cap(room, target)
    return cap is None or (cap[action] and (in_dir(path, room.workdir()) or
                           (action == "read" and in_dir(path, room.files_dir()))))


def effective_mode(room: Any, context: DispatchContext, target: str, requested: str) -> str:
    if context.root != "你" or context.ceiling != "work" or requested != "work":
        return "discuss"
    return cast(str, room.member_mode(target, "work"))


def normalize_policies(room: Any, users: Any, agents: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    human_ids = {pid for pid in room.ais if human(pid)}
    agent_ids = set(room.ais) - human_ids

    def selected(values: Any, allowed_ids: set[str]) -> list[str]:
        if not isinstance(values, list) or any(not isinstance(pid, str) or pid not in allowed_ids for pid in values):
            raise ValueError("请选择本会话中有效的联系人")
        return list(dict.fromkeys(values))

    if not isinstance(users, dict) or not isinstance(agents, dict):
        raise ValueError("联系人权限格式无效")
    for pid, value in users.items():
        if pid not in human_ids or not isinstance(value, dict) or set(value) - {"history_scope", "call_agents"}:
            raise ValueError("用户权限必须属于本会话中的外部用户")
        if value.get("history_scope", "since_join") not in ("since_join", "all_room"):
            raise ValueError("历史消息范围无效")
        if "call_agents" in value:
            value["call_agents"] = selected(value["call_agents"], agent_ids)
    for pid, value in agents.items():
        if pid not in agent_ids or not isinstance(value, dict) or set(value) - {"accept_users", "accept_handoff", "accept_agents", "handoff_targets", "workspace"}:
            raise ValueError("Agent 共享必须属于本会话中的 Agent")
        if "accept_users" in value:
            value["accept_users"] = selected(value["accept_users"], human_ids)
            if value["accept_users"] and guest_model(pid) is None:
                raise ValueError("当前仅直连模型支持隔离的外部讨论")
        if "accept_handoff" in value and type(value["accept_handoff"]) is not bool:
            raise ValueError("接收转派必须是开关")
        for field in ("accept_agents", "handoff_targets"):
            if field in value:
                value[field] = selected(value[field], agent_ids - {pid})
        if "workspace" in value:
            grant = value["workspace"]
            if (not isinstance(grant, dict) or set(grant) - {"path", "worker", *WORKSPACE_ACTIONS}
                    or any(type(grant.get(key)) is not bool for key in WORKSPACE_ACTIONS)):
                raise ValueError("请分别设置工作区读取、写入和命令权限")
            previous = room.meta.get("agent_policies", {}).get(pid, {}).get("workspace", {})
            if "path" in grant:
                if any(grant.get(key, "") != previous.get(key, "") for key in ("path", "worker")):
                    raise ValueError("工作区授权必须绑定到实际执行端")
                workspace = {key: previous.get(key, "") for key in ("path", "worker")}
            else:
                workspace = workspace_target(room, pid)
                if all(grant[key] for key in WORKSPACE_ACTIONS) and not workspace["path"]:
                    raise ValueError("请先连接执行设备，再授权当前工作区")
            value["workspace"] = {**grant, **workspace}
    return users, agents


def history_start(room: Any, pid: str) -> int:
    if room.meta.get("user_policies", {}).get(pid, {}).get("history_scope") == "all_room":
        return 0
    return joined_at(room, pid)


def joined_at(room: Any, pid: str) -> int:
    start = room.meta.get("member_joined_at", {}).get(pid, 0)
    return start if type(start) is int and start >= 0 else 0


def visible_message(room: Any, pid: str, message: dict[str, Any]) -> bool:
    hidden = message.get("not_for")
    if message.get("quiet") or hidden == pid or (isinstance(hidden, list) and pid in hidden):
        return False
    if not human(pid):
        return message.get("origin") not in ("shared-result", "guest-discussion")
    # Only human posts and isolated discussions are published to outside humans.
    if message["id"] < history_start(room, pid):
        return False
    if message.get("origin") == "shared-result":
        return pid in message.get("shared_with", ()) and message["id"] >= joined_at(room, pid)
    speaker = message["speaker"]
    if speaker == "你" or human(speaker):
        return True
    source = message.get("source_message")
    return (message.get("origin") == "guest-discussion" and type(source) is int
            and history_start(room, pid) <= source < len(room.messages)
            and room.messages[source]["speaker"] == pid)


def permissions(room: Any, pid: str) -> dict[str, Any]:
    is_human = human(pid)
    defaults: dict[str, Any] = dict(HUMAN_PERMISSIONS if is_human else PERMISSIONS)
    if "permissions" not in room.meta:  # preserve existing local rooms
        defaults.update(board=True, files=True, work=True)
    effective = dict(defaults, **room.meta.get("permissions", {}).get(pid, {}))
    if is_human:
        effective.update(work=False, board=False, files=False)
    if (registry.get(pid) or {}).get("http_protocol"):
        effective.update(work=False, board=False, files=False, trigger=False)
    return effective


def allowed(room: Any, pid: str, action: str = "read") -> bool:
    spec = registry.get(pid)
    if not room or not spec or not spec["enabled"]:
        return False
    with room.lock:
        return bool(pid in room.ais and permissions(room, pid).get(action))


def require(room: Any, pid: str, action: str = "read") -> None:
    if not allowed(room, pid, action):
        raise PermissionError("未加入此会话或没有%s权限" % action)


def credential(pid: str, revoke: bool = False) -> str:
    spec = registry.get(pid)
    if not spec or not spec["enabled"]:
        raise ValueError("联系人不存在或未启用")
    path = os.path.join(LOG_DIR, "contact_keys.json")
    with LOCK:
        keys = read_json(path) or {}
        token = "" if revoke else secrets.token_urlsafe(32)
        keys.pop(pid, None)
        if token:
            keys[pid] = hashlib.sha256(token.encode()).hexdigest()
        os.makedirs(LOG_DIR, exist_ok=True)
        write_json(path, keys)
        from . import connections
        connections.forget(pid)
    return token


def identify(token: str) -> str | None:
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    with LOCK:
        keys = read_json(os.path.join(LOG_DIR, "contact_keys.json")) or {}
        for pid, saved in keys.items():
            if secrets.compare_digest(saved, digest):
                spec = registry.get(pid)
                return str(pid) if spec and spec["enabled"] else None
    return None


def external_allowed(room: Any, pid: str, worker: str = "", token: str = "") -> bool:
    if not allowed(room, pid):
        return False
    if (registry.get(pid) or {}).get("kind") == "user":
        return True
    from . import execution
    return bool(execution.authorize(room, pid, worker, token))


def visible_rooms(pid: str, worker: str = "", token: str = "") -> list[dict[str, Any]]:
    from .room import rooms
    visible = cast(
        list[dict[str, Any]],
        [x for x in rooms.listing() if pid in x.get("participants", []) and external_allowed(rooms.get(x["id"]), pid, worker, token)],
    )
    if human(pid):
        return [{**row, "workdir": "", "running": []} for row in visible]
    return visible
