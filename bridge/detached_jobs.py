# -*- coding: utf-8 -*-
"""Detached CLI job runner & dialogue collector.

Cojam acts as a meeting room and conversation collector: closing or restarting
Cojam does NOT kill in-flight local CLI agent jobs. Each CLI turn runs in a
detached process group that writes live status and final parsed results to
`<room_dir>/jobs/<job_id>.json`. When Cojam reopens (or while it stays open),
it collects completed replies and reattaches to still-running jobs.
"""
from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from typing import Any

from . import agents, drivers, execution, registry
from .common import HERE, PROJECT, get_logger, mode_key, now_str, read_json, write_json

logger = get_logger(__name__)

DETACH_DRIVERS = frozenset({"cli", "codex", "claude"})
_shutting_down = threading.Event()
_collect_lock = threading.Lock()


def begin_shutdown() -> None:
    """Signal Cojam watchers to detach cleanly without killing running CLI workers."""
    _shutting_down.set()


def reset_shutdown() -> None:
    _shutting_down.clear()


def is_shutting_down() -> bool:
    return _shutting_down.is_set()


def should_detach(room: Any, ai: str, current_caller: Any) -> bool:
    if os.environ.get("ROUNDTABLE_DETACHED_CLI", "1") == "0":
        return False
    if current_caller is not drivers.call:
        return False
    if room is None or not getattr(room, "dir", ""):
        return False
    if execution.remote(room, ai):
        return False
    spec = registry.get(ai) or {}
    drv = spec.get("driver") or ""
    return drv in DETACH_DRIVERS


def jobs_dir(room_dir: str) -> str:
    return os.path.join(room_dir, "jobs")


def pid_alive(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return code.value == STILL_ACTIVE
                return False
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_pid_tree(pid: int) -> None:
    if not isinstance(pid, int) or pid <= 0:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=10,
            )
        except Exception:
            pass
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def _worker_cmd(job_path: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "detached-job", job_path]
    return [sys.executable, "-m", "bridge.detached_jobs", job_path]


def _detach_popen_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
        "cwd": HERE,
    }
    if sys.platform == "win32":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    return kwargs


def spawn_job(
    room: Any,
    ai: str,
    prompt: str,
    sid: str | None,
    images: list[str],
    mode: str,
    *,
    upto: int,
    ver: int,
    pre_tree: str | None,
    t0: float,
    model_revision: str = "",
    source: int | None = None,
) -> str:
    """Persist job spec to disk and launch a detached worker process. Returns job_path."""
    jdir = jobs_dir(room.dir)
    os.makedirs(jdir, exist_ok=True)
    job_id = "job_" + secrets.token_hex(8)
    job_path = os.path.join(jdir, job_id + ".json")
    mo_m, mo_e = room.effective_models(ai)
    payload: dict[str, Any] = {
        "id": job_id,
        "room_id": room.id,
        "room_dir": room.dir,
        "ai": ai,
        "mode": mode,
        "prompt": prompt,
        "sid": sid or "",
        "images": list(images or ()),
        "workdir": room.workdir(),
        "title": room.title(),
        "session_name": room.session_name(),
        "goal": room.goal(),
        "model": mo_m,
        "effort": mo_e,
        "instructions": room.system_instructions(ai, mode),
        "tools": (room.meta.get("tools") or {}).get(ai) or agents.default_tools(ai),
        "bridge_key": room.keys.get(ai, ""),
        "upto": upto,
        "ver": ver,
        "pre_tree": pre_tree,
        "t0": t0,
        "model_revision": model_revision,
        "source_message": source,
        "status": "starting",
        "pid": 0,
        "live": "",
        "live_time": "",
        "result": None,
        "created_at": time.time(),
    }
    write_json(job_path, payload)
    proc = subprocess.Popen(_worker_cmd(job_path), **_detach_popen_kwargs())
    payload["pid"] = proc.pid
    write_json(job_path, payload)
    return job_path


def wait_for_job(
    job_path: str,
    *,
    on_live: Any = None,
    is_cancelled: Any = None,
    poll_interval: float = 0.25,
) -> tuple[str, dict[str, Any] | None]:
    """Wait until job finishes, is cancelled, worker dies, or Cojam begins shutting down.

    Returns (state, job_data) where state is one of:
    'done' | 'detached' | 'cancelled' | 'dead'.
    """
    last_live = ""
    startup_deadline = time.time() + 15.0
    while True:
        if is_shutting_down():
            return "detached", read_json(job_path)
        if is_cancelled and is_cancelled():
            return "cancelled", read_json(job_path)
        data = read_json(job_path)
        if not isinstance(data, dict):
            return "dead", None
        status = data.get("status")
        live_text = data.get("live") or ""
        if live_text and live_text != last_live:
            last_live = live_text
            if on_live:
                on_live({"live": live_text})
        if status == "done":
            return "done", data
        if status in ("collected", "cancelled"):
            return status, data
        pid = int(data.get("pid") or 0)
        if pid and not pid_alive(pid):
            # Re-read once to avoid race with final write before process exit.
            data2 = read_json(job_path)
            if isinstance(data2, dict) and data2.get("status") == "done":
                return "done", data2
            if time.time() > startup_deadline or status == "running":
                return "dead", data2 if isinstance(data2, dict) else data
        time.sleep(poll_interval)


def cancel_jobs(room: Any, targets: list[str] | None = None, *, source: int | None = None) -> int:
    """Explicitly cancel and terminate detached jobs for targets (user clicked Stop)."""
    jdir = jobs_dir(room.dir)
    if not os.path.isdir(jdir):
        return 0
    wanted = set(targets) if targets is not None else None
    killed = 0
    for name in sorted(os.listdir(jdir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(jdir, name)
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        if data.get("status") not in ("starting", "running"):
            continue
        if wanted is not None and data.get("ai") not in wanted:
            continue
        if source is not None and data.get("source_message") != source:
            continue
        pid = int(data.get("pid") or 0)
        data["status"] = "cancelled"
        write_json(path, data)
        if pid:
            kill_pid_tree(pid)
        killed += 1
    return killed


def has_active_jobs(room: Any) -> bool:
    jdir = jobs_dir(room.dir)
    if not os.path.isdir(jdir):
        return False
    for name in os.listdir(jdir):
        if not name.endswith(".json"):
            continue
        data = read_json(os.path.join(jdir, name))
        if isinstance(data, dict) and data.get("status") in ("starting", "running"):
            pid = int(data.get("pid") or 0)
            if pid and pid_alive(pid):
                return True
    return False


def apply_job_result(room: Any, job_path: str, data: dict[str, Any], *, was_stopped: bool = False) -> bool:
    """Atomically claim a finished job and apply its reply/state into `room`."""
    with _collect_lock:
        fresh = read_json(job_path)
        if not isinstance(fresh, dict) or fresh.get("status") != "done":
            return False
        fresh["status"] = "collected"
        fresh["collected_at"] = time.time()
        write_json(job_path, fresh)
        data = fresh

    ai = data.get("ai") or ""
    mode = data.get("mode") or room.mode()
    res = data.get("result") or {}
    ok = bool(res.get("ok"))
    out = str(res.get("text") or "")
    new_sid = res.get("sid") or data.get("sid") or None
    edits = res.get("edits") or []
    ctx = res.get("ctx")
    upto = int(data.get("upto", -1))
    ver = int(data.get("ver", 0))
    pre_tree = data.get("pre_tree")
    t0 = float(data.get("t0") or time.time())
    t1 = float(data.get("finished_at") or time.time())
    source = data.get("source_message")
    if source in room.recalled:
        if pre_tree is not None:
            room.record_step(ai, pre_tree, edits, t0, t1)
        return True

    from . import model_catalog
    model_catalog.result(room, ai, str(data.get("model_revision") or ""), ok, out, new_sid)

    if ok:
        with room.lock:
            room.meta[ai + "_session"] = new_sid
            room.meta["last_seen"][ai] = max(int(room.meta["last_seen"].get(ai, -1)), upto)
            room.meta["announcement_seen"][ai] = ver
            room.meta["mode_seen"][ai] = mode_key(mode)
            room.meta.setdefault("instruction_seen", {})[ai] = room.instruction_signature(ai, mode)
            room.meta["returned"][ai] = False
            if isinstance(ctx, dict) and ctx.get("used"):
                room.meta["ctx"][ai] = ctx
            room.save_meta()
            room.state["chain"] += 1
        if was_stopped:
            rest, ch = room.apply_board_cmds(ai, out)
            rest, sent, errs = room.apply_send_cmds(rest)
            if rest or sent or not (ch or errs):
                from .common import mentions
                room.add_message(ai, rest, sent, to_user="用户" in mentions(rest, exclude=ai))
            room.board_note(ai, ch, not_for=ai)
            room.send_note(ai, errs)
        else:
            room.handle_message(ai, out, source=source)
    else:
        if new_sid and new_sid != data.get("sid"):
            with room.lock:
                room.meta[ai + "_session"] = new_sid
                room.save_meta()
        room.add_message("系统", out or ("%s 后台任务失败" % ai))

    if pre_tree is not None:
        room.record_step(ai, pre_tree, edits, t0, t1)
    return True


def collect_for_room(room: Any) -> int:
    """Collect finished detached jobs for `room` and reattach watchers for running ones."""
    jdir = jobs_dir(room.dir)
    if not os.path.isdir(jdir):
        return 0
    collected = 0
    for name in sorted(os.listdir(jdir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(jdir, name)
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        status = data.get("status")
        if status == "done":
            if apply_job_result(room, path, data):
                collected += 1
        elif status in ("starting", "running"):
            source = data.get("source_message")
            if source in room.recalled:
                cancel_jobs(room, source=source)
                continue
            pid = int(data.get("pid") or 0)
            if pid and pid_alive(pid):
                _reattach_watcher(room, path, data)
            else:
                # Re-check in case worker just finished
                fresh = read_json(path)
                if isinstance(fresh, dict) and fresh.get("status") == "done":
                    if apply_job_result(room, path, fresh):
                        collected += 1
                elif isinstance(fresh, dict) and fresh.get("status") in ("starting", "running"):
                    fresh["status"] = "collected"
                    write_json(path, fresh)
                    room.add_message("系统", "%s 之前的后台任务已意外退出，未返回结果。" % (fresh.get("ai") or "AI"))
    return collected


_reattached: set[str] = set()
_reattach_lock = threading.Lock()


def _reattach_watcher(room: Any, job_path: str, data: dict[str, Any]) -> None:
    with _reattach_lock:
        if job_path in _reattached:
            return
        _reattached.add(job_path)
    ai = data.get("ai") or ""
    source = data.get("source_message")

    def watch() -> None:
        try:
            with room.ai_lock(ai):
                with room.turn_ready:
                    room.turn_ready.wait_for(lambda: ai not in room.interrupting)
                    if source in room.recalled:
                        return
                    if ai not in room.state["running"]:
                        room.state["running"].append(ai)
                    room.turn_sources[ai] = source
                    room.live[ai] = {"text": data.get("live") or "", "time": data.get("live_time") or "", "since": float(data.get("t0") or time.time())}
                try:
                    state, final_data = wait_for_job(
                        job_path,
                        on_live=lambda rr: room.push_live(ai, rr),
                        is_cancelled=lambda: ai in room.state["stopped"] or room.turn_recalled(ai),
                    )
                    if state == "done" and isinstance(final_data, dict):
                        with room.lock:
                            was_stopped = ai in room.state["stopped"]
                            room.state["stopped"].discard(ai)
                        apply_job_result(room, job_path, final_data, was_stopped=was_stopped)
                    elif state == "dead" and isinstance(final_data, dict):
                        final_data["status"] = "collected"
                        write_json(job_path, final_data)
                        room.add_message("系统", "%s 后台任务意外退出，未返回结果。" % ai)
                finally:
                    with room.lock:
                        if ai in room.state["running"]:
                            room.state["running"].remove(ai)
                        room.turn_sources.pop(ai, None)
                        room.state["stopped"].discard(ai)
                        room.live.pop(ai, None)
        finally:
            with _reattach_lock:
                _reattached.discard(job_path)

    threading.Thread(target=watch, daemon=True, name="reattach-" + (data.get("id") or ai)).start()


def recover_all(rooms_store: Any) -> int:
    """Scan all rooms on disk at Cojam startup and collect any pending detached jobs."""
    total = 0
    for row in rooms_store.listing():
        rid = row.get("id")
        if not rid:
            continue
        rdir = os.path.join(os.path.dirname(os.path.abspath(rooms_store.room_dir(rid))) if hasattr(rooms_store, "room_dir") else "", rid)
        # Check jobs dir directly via common.MEET_DIR to avoid loading idle rooms with no jobs.
        from .common import MEET_DIR
        jdir = jobs_dir(os.path.join(MEET_DIR, rid))
        if not os.path.isdir(jdir):
            continue
        has_pending = False
        for name in os.listdir(jdir):
            if not name.endswith(".json"):
                continue
            d = read_json(os.path.join(jdir, name))
            if isinstance(d, dict) and d.get("status") in ("starting", "running", "done"):
                has_pending = True
                break
        if has_pending:
            r = rooms_store.get(rid)
            if r is not None:
                total += collect_for_room(r)
    return total


# ===================== Detached Worker Runtime =====================

class _DetachedRoomProxy:
    """Minimal Room-compatible proxy used inside the detached worker process."""

    def __init__(self, job: dict[str, Any], job_path: str):
        self.id = job.get("room_id") or ""
        self._workdir = job.get("workdir") or PROJECT
        self._title = job.get("title") or self.id
        self._session_name = job.get("session_name") or ""
        self._goal = job.get("goal") or ""
        self._mode = job.get("mode") or "discuss"
        self._model = job.get("model") or ""
        self._effort = job.get("effort") or ""
        self._instructions = job.get("instructions") or ""
        ai = job.get("ai") or ""
        self.keys = {ai: job.get("bridge_key") or ""}
        self.meta = {"tools": {ai: job.get("tools") or agents.default_tools(ai)}}
        self.procs: dict[str, Any] = {}
        self.codex = None
        self.ctx: dict[str, Any] | None = None
        self._job_path = job_path
        self._last_live_write = 0.0
        self._live_lock = threading.Lock()

    def workdir(self) -> str:
        return self._workdir

    def title(self) -> str:
        return self._title

    def session_name(self) -> str:
        return self._session_name

    def goal(self) -> str:
        return self._goal

    def mode(self) -> str:
        return self._mode

    def effective_models(self, _ai: str) -> tuple[str, str]:
        return self._model, self._effort

    def system_instructions(self, _ai: str, _mode: str | None = None) -> str:
        return self._instructions

    def allow_send_paths(self, _paths: list[str]) -> None:
        return None

    def note_ctx(self, _ai: str, res: dict[str, Any]) -> None:
        used = res.get("ctx_used")
        if used:
            self.ctx = {"used": used, "window": res.get("ctx_win"), "time": now_str()}

    def push_live(self, _ai: str, res: dict[str, Any]) -> None:
        text = str((res or {}).get("live") or "").strip()
        if not text:
            return
        now = time.time()
        with self._live_lock:
            if now - self._last_live_write < 0.4:
                return
            self._last_live_write = now
            cur = read_json(self._job_path)
            if isinstance(cur, dict) and cur.get("status") == "running":
                cur["live"] = text[-400:]
                cur["live_time"] = now_str()
                write_json(self._job_path, cur)


def run_worker(job_path: str) -> int:
    """Entry point executed inside the detached worker process."""
    registry.ensure()
    job = read_json(job_path)
    if not isinstance(job, dict):
        return 2
    if job.get("status") == "cancelled":
        return 0
    job["pid"] = os.getpid()
    job["status"] = "running"
    job["started_at"] = time.time()
    write_json(job_path, job)

    ai = job.get("ai") or ""
    prompt = job.get("prompt") or ""
    sid = job.get("sid") or None
    images = list(job.get("images") or ())
    mode = job.get("mode") or "discuss"
    proxy = _DetachedRoomProxy(job, job_path)

    try:
        res = drivers.call(ai, prompt, sid, images, mode, proxy)
        ok, out, new_sid = bool(res[0]), str(res[1] or ""), res[2]
        edits = res[3] if len(res) > 3 else []
    except Exception as error:
        ok, out, new_sid, edits = False, f"{ai} 后台任务出错：{error}", sid, []
    finally:
        # Always cleanly stop any codex app-server spawned by this worker so no thread lock leaks.
        try:
            agents.stop_codex(proxy)
        except Exception:
            pass

    cur = read_json(job_path)
    if not isinstance(cur, dict):
        cur = job
    if cur.get("status") == "cancelled":
        return 0
    cur["status"] = "done"
    cur["finished_at"] = time.time()
    cur["result"] = {
        "ok": ok,
        "text": out,
        "sid": new_sid,
        "edits": edits,
        "ctx": proxy.ctx,
    }
    write_json(job_path, cur)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return 2
    return run_worker(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
