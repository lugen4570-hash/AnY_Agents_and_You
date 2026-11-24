# -*- coding: utf-8 -*-
r"""stdio ↔ AnY HTTP MCP 转发桥：给只支持 stdio MCP 的桌面软件（如 Claude Desktop）用。

启动方式：
    python -m bridge.mcp_stdio
    python roundtable.py mcp-stdio
    AnY.exe mcp-stdio

环境变量：
    AI_BRIDGE_URL    默认 http://127.0.0.1:<PORT>/mcp
    AI_BRIDGE_TOKEN  联系人接入密钥（Bearer token）
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
from typing import Any, Sequence
import urllib.error
import urllib.request

from .common import PORT, get_logger

logger = get_logger(__name__)


def forward_one(line: str, url: str | None = None, token: str | None = None) -> str | None:
    raw = (line or "").strip()
    if not raw:
        return None
    try:
        msg = json.loads(raw)
    except Exception:
        return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
    target = url or os.environ.get("AI_BRIDGE_URL") or ("http://127.0.0.1:%d/mcp" % PORT)
    tok = token if token is not None else os.environ.get("AI_BRIDGE_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(target, data=raw.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=65) as resp:
            body = resp.read().decode("utf-8", "replace").strip()
            return body if body else None
    except urllib.error.HTTPError as e:
        if isinstance(msg, dict) and msg.get("id") is not None:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception as err:
                logger.debug("Failed reading HTTP error body: %s", err)
            return json.dumps({"jsonrpc": "2.0", "id": msg.get("id"),
                               "error": {"code": -32000, "message": "AnY HTTP %s: %s" % (e.code, detail)}},
                              ensure_ascii=False)
        return None
    except Exception as e:
        if isinstance(msg, dict) and msg.get("id") is not None:
            return json.dumps({"jsonrpc": "2.0", "id": msg.get("id"),
                               "error": {"code": -32000, "message": "连不上 AnY (%s): %s" % (target, e)}},
                              ensure_ascii=False)
        return None


MAX_WORKERS = 8
MAX_QUEUE = 64
_STOP = object()


def main(argv: Sequence[str] | None = None) -> int:
    # MCP 的 stdio 一律是 UTF-8；中文 Windows 默认 cp936，不重设会把中文和 emoji 弄乱。
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception as error:
                logger.debug("Stream reconfigure failed: %s", error)
    write_lock = threading.Lock()
    work_q: queue.Queue[Any] = queue.Queue(maxsize=MAX_QUEUE)
    cond = threading.Condition()
    eof = threading.Event()
    pending = 0
    workers: list[threading.Thread] = []

    def emit(resp: str | None) -> None:
        if not resp:
            return
        with write_lock:          # 多行响应不能交错
            sys.stdout.write(resp + "\n")
            sys.stdout.flush()

    def worker() -> None:
        nonlocal pending
        while True:
            try:
                raw = work_q.get(timeout=0.5)
            except queue.Empty:
                if eof.is_set():
                    return
                continue
            if raw is _STOP:
                work_q.task_done()
                return
            try:
                emit(forward_one(raw))
            except Exception as error:
                logger.exception("mcp_stdio worker failed handling message: %s", error)
            finally:
                with cond:
                    pending -= 1
                    if pending == 0:
                        cond.notify_all()
                work_q.task_done()

    # 一条 55 秒的待命调用不能把 ping / tools/list 堵在后面，所以用固定上限的后台工作池并发处理。
    for raw in sys.stdin:
        with cond:
            pending += 1
            if len(workers) < MAX_WORKERS:
                t = threading.Thread(target=worker, daemon=True)
                workers.append(t)
                t.start()
        work_q.put(raw)
    eof.set()
    with cond:
        cond.wait_for(lambda: pending == 0, timeout=0.5)
    for _ in workers:
        try:
            work_q.put_nowait(_STOP)
        except queue.Full:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
