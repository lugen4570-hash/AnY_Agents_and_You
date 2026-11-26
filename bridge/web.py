# -*- coding: utf-8 -*-
"""HTTP 接口和启动。

会议相关的接口都带会议号：/api/r/<会议号>/<动作>，每个浏览器标签页可以开着不同的会议，互不影响。
管理员接口只认页面注入的 X-RT-Token；
外部程序用 /api/post 或 /mcp；钩子用 /api/guard/*（带钥匙）。"""
import hmac, io, json, mimetypes, os, re, secrets, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from subprocess import SubprocessError
from typing import Any, Mapping
from urllib.parse import parse_qs, quote, unquote, urlsplit

from . import access, acp, agent_settings, agents, common, conn_settings, connections, debate, devices, discovery, execution, extensions, install, invites, mcp, members, model_catalog, pal, projects, registry, room as R
from .common import (HERE, HOST, MAX_ANN, MAX_BODY, MAX_UPLOAD, MEET_DIR, PORT, PROJECT,
                     in_dir, kind_of)
from .guard import USER, guard
from .version import VERSION, API_REVISION

RT_TOKEN = secrets.token_urlsafe(24)   # 每次启动随机；页面加载时注入 HTML，前端每个请求带 X-RT-Token
logger = common.get_logger(__name__)
USER_ONLY_MSG = "这个接口只给网页上的用户用；外部程序请用 /api/post 或 /mcp 并写明自己的身份"
STATIC = os.path.join(HERE, "static")
INDEX = os.environ.get("ROUNDTABLE_INDEX") or os.path.join(HERE, "index.html")   # 页面；开发时可以指到别的文件
ROOM_PATH = re.compile(r"^/api/r/([^/]+)/([a-z/]+)$")


class Handler(BaseHTTPRequestHandler):
    server_version = "AIBridge"

    def log_message(self, *a):
        pass

    # ---------- 回应 ----------
    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj, extra=None):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", extra)

    def _length(self):
        try:
            return int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return -1

    def _read_chunked_body(self, max_bytes):
        chunks = []
        total = 0
        while True:
            line = self.rfile.readline(4096)
            if not line:
                raise ValueError("incomplete chunked body")
            size_hex = line.split(b";", 1)[0].strip()
            try:
                chunk_size = int(size_hex, 16)
            except ValueError as exc:
                raise ValueError("bad chunk size") from exc
            if chunk_size < 0:
                raise ValueError("bad chunk size")
            if chunk_size == 0:
                while True:
                    trailer = self.rfile.readline(4096)
                    if not trailer or trailer in (b"\r\n", b"\n"):
                        break
                break
            total += chunk_size
            if total > max_bytes:
                raise ValueError("too large (max 25MB)")
            data = self.rfile.read(chunk_size)
            if len(data) != chunk_size:
                raise ValueError("incomplete chunked body")
            eol = self.rfile.readline(4)
            if eol not in (b"\r\n", b"\n"):
                raise ValueError("malformed chunk terminator")
            chunks.append(data)
        return b"".join(chunks)

    def _read_json(self):
        n = self._length()
        if n < 0 or n > MAX_BODY:
            self._json(413, {"error": "too large"})
            return None
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            self._json(400, {"error": "bad json"})
            return None
        if not isinstance(data, dict):
            self._json(400, {"error": "bad json"})
            return None
        return data

    def _from_browser(self):
        """管理员能力：进程内令牌，或请求头里的未撤销设备凭证。cookie 不在这里放行。"""
        tok = self.headers.get("X-RT-Token") or ""
        if not tok:
            return False
        if hmac.compare_digest(tok.encode("utf-8"), RT_TOKEN.encode("utf-8")):
            self._device_id = ""
            return True
        device = devices.verify(tok)
        if not device:
            return False
        self._device_id = device["id"]
        return True

    def _cookies(self):
        out = {}
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, sep, value = part.strip().partition("=")
            if sep and name:
                out[name] = value
        return out

    def _owner_cookie(self):
        return self._cookies().get("rt_owner") == RT_TOKEN

    def _device_cookie(self):
        token = self._cookies().get("any_device") or self._cookies().get("cojam_device") or ""
        return token if token and devices.verify(token) else ""

    def _is_local_owner(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        forwarded = any(self.headers.get(h) for h in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host", "X-Real-IP"))
        return (not forwarded and self.client_address[0] in ("127.0.0.1", "::1")
                and host in ("localhost", "127.0.0.1"))

    def _is_host_owner(self):
        return self._is_local_owner() and not getattr(self, "_device_id", "")

    def _https(self):
        return (self.headers.get("X-Forwarded-Proto") or "").lower() == "https"

    def _device_cookie_header(self, token):
        parts = ["any_device=" + token, "HttpOnly", "SameSite=Lax", "Path=/", "Max-Age=31536000"]
        if self._https():
            parts.append("Secure")
        return "; ".join(parts)

    @staticmethod
    def _base_url(value):
        try:
            url = urlsplit(str(value or "").strip())
        except ValueError:
            return ""
        if url.scheme not in ("http", "https") or not url.netloc:
            return ""
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            return ""
        return "%s://%s" % (url.scheme, url.netloc)

    def _owner_page(self, token, extra=None):
        html = getattr(self.server, "ui_index", None)
        if html is None:
            with open(INDEX, "rb") as f:
                html = f.read()
        html = html.replace(b"__RT_TOKEN__", token.encode("ascii"))
        return self._send(200, html, "text/html; charset=utf-8", extra)

    def _bearer(self):
        a = self.headers.get("Authorization") or ""
        if a.lower().startswith("bearer "):
            return a[7:].strip()
        return (self.headers.get("X-Bridge-Key") or "").strip()

    # ---------- 静态 ----------
    def _static(self, name, ctype):
        if name == "member-connector.zip":
            if not self._from_browser() and not self._owner_cookie() and not self._device_cookie():
                return self._json(403, {"error": USER_ONLY_MSG})
            if not os.path.isfile(os.path.join(STATIC, name)) and not getattr(sys, "frozen", False):
                from .member_package import build
                build()
        p = os.path.join(STATIC, name)
        if not os.path.isfile(p):
            return self._send(404, b"not found", "text/plain")
        body = getattr(self.server, "ui_assets", {}).get(name)
        if body is None:
            with open(p, "rb") as f:
                body = f.read()
        self._send(200, body, ctype)

    def _serve_file(self, rel, private_share=False):
        rel = unquote(rel)
        if "\x00" in rel:
            return self._send(400, b"bad", "text/plain")
        base = os.path.realpath(MEET_DIR)
        full = os.path.realpath(os.path.join(base, rel.replace("/", os.sep)))
        if not in_dir(full, base):
            return self._send(403, b"forbidden", "text/plain")
        parts = os.path.relpath(full, base).split(os.sep)
        if len(parts) < 3 or parts[1] != "files":  # 只放行 <会议>/files/ 里的东西
            return self._send(403, b"forbidden", "text/plain")
        if not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        safe = kind_of(full) in ("image", "audio") or ctype == "application/pdf"
        if ctype == "image/svg+xml":
            safe = False
        total = os.path.getsize(full)
        start, end, code = 0, total - 1, 200
        mt = re.match(r"bytes=(\d*)-(\d*)$", (self.headers.get("Range", "")).strip())
        if mt and (mt.group(1) or mt.group(2)):
            if mt.group(1):
                start = int(mt.group(1))
                if mt.group(2):
                    end = min(end, int(mt.group(2)))
            else:
                start = max(0, total - int(mt.group(2)))
            if start > end or start >= total:
                return self._send(416, b"", "text/plain", {"Content-Range": "bytes */%d" % total})
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store" if private_share else "private, max-age=3600")
        if code == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, total))
        if not safe or private_share:
            self.send_header("Content-Disposition", "attachment")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(full, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(left, 1 << 20))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    # ---------- GET ----------
    def do_GET(self):
        path, _, qs = self.path.partition("?")
        q = parse_qs(qs)
        if path == "/api/server/info":
            return self._json(200, {"app": "AI Bridge", "version": VERSION, "api_revision": API_REVISION,
                                    "lan_url": getattr(self.server, "lan_url", None),
                                    "tailscale_url": getattr(self.server, "tailscale_url", None),
                                    "owner_devices_supported": True})
        if path == "/enroll":
            return self._static("enroll.html", "text/html; charset=utf-8")
        if path == "/join":
            return self._static("join.html", "text/html; charset=utf-8")
        if path in ("/", "/index.html"):
            device_token = self._device_cookie()
            if device_token:
                return self._owner_page(device_token)
            if self._is_local_owner():
                return self._owner_page(RT_TOKEN, {"Set-Cookie": "rt_owner=" + RT_TOKEN + "; HttpOnly; SameSite=Strict; Path=/"})
            return self._static("join.html", "text/html; charset=utf-8")
        if path.startswith("/static/") and re.match(r"^/static/[\w.\-]+$", path):
            name = path[len("/static/"):]
            return self._static(name, mimetypes.guess_type(name)[0] or "application/octet-stream")
        if path.startswith("/files/"):
            if not self._from_browser() and not self._owner_cookie() and not self._device_cookie():
                return self._json(403, {"error": USER_ONLY_MSG})
            return self._serve_file(path[len("/files/"):])
        if path == "/mcp":
            return self._json(405, {"error": "这个 MCP 服务只收 POST"}, {"Allow": "POST"})
        if path.startswith("/api/external/"):
            return self._external_get(path, q)
        if path.startswith("/api/") and not self._from_browser():
            return self._json(403, {"error": USER_ONLY_MSG})
        if path == "/api/update/check":
            from . import updater
            return self._json(200, updater.check())
        if path == "/api/update/status":
            from . import updater
            return self._json(200, updater.status())
        if path == "/api/server/runtime":
            from .common import LOG_DIR
            from .server_runtime import installation
            return self._json(200, {"install": installation(), "data": os.path.realpath(LOG_DIR)})
        if path == "/api/rooms":
            with R.rooms.lock:
                rows = R.rooms.listing()
                for row in rows:
                    if not row.get("project") and not row.get("standalone"):
                        row["project"] = projects.legacy_id(row["workdir"])
                groups = projects.listing(rows)
            return self._json(200, {"rooms": rows, "projects": groups, "last": R.last_room(), "default_workdir": PROJECT})
        if path == "/api/trash":
            rows = R.list_trash()
            for row in rows:
                if not row.get("project") and not row.get("standalone"):
                    row["project"] = projects.legacy_id(row["workdir"])
            return self._json(200, {"trash": rows})
        if path == "/api/devices":
            return self._json(200, {"account": devices.account(),
                                    "devices": devices.listing(getattr(self, "_device_id", ""))})
        if path == "/api/devices/code/status":
            status = devices.code_status((q.get("id") or [""])[0])
            return self._json(200, status) if status is not None else self._json(404, {"error": "接入码不存在"})
        if path == "/api/invites":
            return self._json(200, {"invites": invites.listing(), "guests": invites.guest_listing()})
        if path == "/api/claims":
            return self._json(200, {"claims": guard.listing()})
        if path == "/api/discovery":
            if (q.get("scan") or [""])[0] in ("1", "true", "yes"):
                return self._json(200, discovery.scan())
            discovery.ensure_scanned(async_scan=False)
            return self._json(200, discovery.status())
        if path == "/api/settings/connection":
            return self._json(200, conn_settings.snapshot())
        if path == "/api/extensions":
            pid = (q.get("project_id") or [""])[0]
            ref = (q.get("refresh") or [""])[0] in ("1", "true", "yes")
            return self._json(200, extensions.list_extensions(
                pid, refresh=ref, local_host=self._is_host_owner(), conversations=R.rooms.listing()))
        if path == "/api/agents/config":
            try:
                return self._json(200, agent_settings.view((q.get("id") or [""])[0]))
            except ValueError as error:
                return self._json(404, {"error": str(error)})
        if path == "/api/agents":
            reload_agents = (q.get("reload") or [""])[0] in ("1", "true", "yes")
            if reload_agents:
                registry.load()      # 用户刚改了 data/agents.d：重读一遍，不用重启服务器
            installation_details = {} if q.get("summary") == ["1"] and not reload_agents else {
                "discovered_presets": registry.discover_hidden_presets(), "hosts": install.hosts_status(),
            }
            # 待命通道不属于某一种 driver：Claude/Codex 的桌面端也能待命，界面要能看到
            member_rows = {}
            for s in registry.all_specs():
                if s.get("kind") == "user":
                    continue
                st = members.broker.status(s["id"])
                if st["automatic"] or s["driver"] == "external":
                    member_rows[s["id"]] = st
            return self._json(200, dict(registry.catalog(), default_dir=PROJECT,
                                        local_workspace=self._is_host_owner(),
                                        macos_workspace_picker=sys.platform == "darwin" and self._is_host_owner(),
                                        owner_devices=devices.listing(getattr(self, "_device_id", "")),
                                        connections=connections.catalog(), members=member_rows,
                                        discovery=discovery.status(), connection_settings=conn_settings.snapshot(),
                                        mcp_url="http://127.0.0.1:%d/mcp" % PORT, **installation_details))
        if path in ("/api/state", "/api/messages"):   # 老页面（服务器换了新版、页面还没刷新）：按最近打开的那场回
            rid = R.last_room()
            r = R.rooms.get(rid) if rid else None
            if r is None:
                return self._json(200, {"meeting": None, "messages": [], "next": 0, "running": [], "queued": 0, "reload": True})
            if path == "/api/state":
                return self._json(200, dict(r.api_state(), reload=True))
            return self._json(200, dict(r.messages_since(_int(q, "since")), reload=True))
        m = ROOM_PATH.match(path)
        if m:
            r = R.rooms.get(unquote(m.group(1)))
            if r is None:
                return self._json(404, {"error": "没有这场会议（可能删了）", "gone": True})
            act = m.group(2)
            if act == "messages":
                return self._json(200, r.messages_since(_int(q, "since")))
            if act == "state":
                return self._json(200, r.api_state())
            if act == "models/catalog":
                ai = (q.get("ai") or [""])[0]
                if ai not in r.ais:
                    return self._json(400, {"error": "请选择当前会话的 Agent"})
                return self._json(200, r.model_info(ai))
            if act == "tools":
                ai = (q.get("ai") or [""])[0]
                if ai not in r.ais:
                    return self._json(400, {"error": "ai 只能是这场会议里的：" + "、".join(r.ais)})
                return self._json(200, r.tools_info(ai))
        return self._send(404, b"not found", "text/plain")

    do_HEAD = do_GET

    # ---------- POST ----------
    def do_POST(self):
        path, _, qs = self.path.partition("?")
        if path == "/mcp":
            return self._mcp()
        if path.startswith("/api/guard/"):
            return self._guard(path[len("/api/guard/"):])
        if path == "/api/post":
            return self._external_post()
        if path == "/api/external/recall":
            return self._external_post(recall=True)
        if path.startswith("/api/external/member/"):
            data = self._read_json()
            if data is None:
                return
            key = self._bearer()
            pid = access.identify(key)
            if not pid:
                return self._json(401, {"error": "接入密钥无效"})
            try:
                result = members.handle(pid, key, path.rsplit("/", 1)[1], data)
                connections.seen(pid, key, "member", data.get("device"))
                return self._json(200, result)
            except members.MemberError as e:
                return self._json(e.code, {"error": str(e)})
        if path == "/api/external/hello":
            data = self._read_json()
            if data is None:
                return
            key = self._bearer()
            pid = access.identify(key)
            if not pid:
                return self._json(401, {"error": "接入密钥无效或已撤销"})
            connections.seen(pid, key, "web" if data.get("client") == "AI Bridge 网页" else "http", data.get("client"))
            return self._json(200, {"ok": True, "contact": registry.public(registry.get(pid))})
        if path == "/api/guest/redeem":
            data = self._read_json()
            if data is None:
                return
            try:
                result = invites.redeem(str(data.get("invite") or ""),
                                        str(data.get("token") or ""),
                                        str(data.get("device_key") or ""),
                                        str(data.get("name") or ""),
                                        str(data.get("device") or ""))
            except invites.InviteError as error:
                return self._json(error.code, {"error": str(error)})
            return self._json(200, {"ok": True, "token": result["token"],
                                    "contact": result["contact"], "room": result["room"],
                                    "rooms": result["rooms"], "created": result["created"]})
        if path == "/api/devices/enroll":
            data = self._read_json()
            if data is None:
                return
            try:
                result = devices.enroll(str(data.get("code") or ""), str(data.get("label") or ""),
                                        str(data.get("client_id") or ""))
            except devices.DeviceError as error:
                return self._json(error.code, {"error": str(error)})
            return self._json(200, {"ok": True, "token": result["token"], "device": result["device"]},
                              {"Set-Cookie": self._device_cookie_header(result["token"])})
        if path == "/api/devices/restore":
            data = self._read_json()
            if data is None:
                return
            token = str(data.get("token") or "")
            device = devices.verify(token)
            if not device:
                return self._json(401, {"error": "设备凭证无效或已撤销"})
            return self._json(200, {"ok": True}, {"Set-Cookie": self._device_cookie_header(token)})
        if path == "/api/invites/resolve-owner":
            if not self._from_browser():
                return self._json(403, {"error": USER_ONLY_MSG})
            data = self._read_json()
            if data is None:
                return
            try:
                invite = invites.find(str(data.get("invite") or ""))
            except invites.InviteError as error:
                return self._json(error.code, {"error": str(error)})
            return self._json(200, {"room": invite.get("room") or ""})
        if path == "/api/agents/add":         # 页面上"手动添加"，不让人碰 json
            data = self._read_json()
            if data is None:
                return
            if not self._from_browser():
                return self._json(403, {"error": USER_ONLY_MSG})
            spec = data.get("spec")
            if not self._is_host_owner():
                driver = str(spec.get("driver") or "").strip().lower() if isinstance(spec, dict) else ""
                if driver != "external":
                    return self._json(403, {"error": "远程设备只能添加外部接入（external）联系人；本地代理请在运行 AnY 的设备上添加。"})
                cur = registry.get(str(spec.get("id") or "").strip().lower())
                if cur is not None and cur.get("driver") != "external":
                    return self._json(403, {"error": "不能从其他设备修改或覆盖本地代理联系人。"})
            try:
                ok, msg = registry.save_agent(spec or {})
            except OSError:
                return self._json(500, {"error": "无法保存联系人，请检查应用数据目录的写入权限和剩余空间"})
            return self._json(200 if ok else 400, {"ok": ok, "error": msg, "agents": registry.catalog()["agents"]})
        if path == "/api/agents/remove":
            data = self._read_json()
            if data is None:
                return
            if not self._from_browser():
                return self._json(403, {"error": USER_ONLY_MSG})
            pid = str(data.get("id") or "")
            if not self._is_host_owner():
                cur = registry.get(pid)
                if cur is not None and cur.get("driver") != "external":
                    return self._json(403, {"error": "不能从其他设备删除本地代理联系人。"})
            try:
                ok, msg = R.remove_contact(pid)
            except OSError:
                return self._json(500, {"error": "无法删除联系人，请检查数据目录的写入权限。"})
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if path == "/api/agents/restore":
            data = self._read_json()
            if data is None:
                return
            if not self._from_browser():
                return self._json(403, {"error": USER_ONLY_MSG})
            if not self._is_host_owner():
                return self._json(403, {"error": "不能从其他设备恢复本机代理。"})
            if not registry.restore_preset(str(data.get("id") or "")):
                return self._json(404, {"error": "未找到已安装的程序，请重新检测"})
            return self._json(200, {"ok": True})
        if path == "/api/agents/install":     # 页面上的"一键接入"，不让人碰命令行
            data = self._read_json()
            if data is None:
                return
            if not self._from_browser():
                return self._json(403, {"error": USER_ONLY_MSG})
            if not self._is_host_owner():
                return self._json(403, {"error": "不能从其他设备写入本机宿主配置。"})
            token = str(data.get("token") or "")
            if not token or access.identify(token) != str(data.get("contact") or data.get("host") or ""):
                return self._json(400, {"error": "请先生成此联系人的接入密钥"})
            ok, msg = install.host_install(str(data.get("host") or ""), token)
            return self._json(200 if ok else 409, {"ok": ok, "msg": msg, "hosts": install.hosts_status()})
        if not self._from_browser():
            return self._json(403, {"error": USER_ONLY_MSG})
        m = ROOM_PATH.match(path)
        if m:
            r = R.rooms.get(unquote(m.group(1)))
            if r is None:
                return self._json(404, {"error": "没有这场会议（可能删了）", "gone": True})
            return self._room_post(r, m.group(2), qs)
        if path == "/api/upload" or path == "/api/send":
            return self._json(409, {"error": "页面是旧版的，刷新一下再发", "reload": True})
        data = self._read_json()
        if data is None:
            return
        if path in {"/api/agents/config", "/api/agents/config/mcp", "/api/server/exit", "/api/server/stop", "/api/rooms/delete",
                    "/api/devices/code", "/api/devices/link", "/api/devices/revoke"} and not self._is_host_owner():
            return self._json(403, {"error": "请在运行 AnY 的电脑上进行此操作"})
        if path == "/api/cloud/account":
            if not self._is_host_owner():
                return self._json(403, {"error": "请在运行 AnY 的电脑上管理云账号"})
            from . import cloud_account
            code, response = cloud_account.handle(data)
            return self._json(code, response)
        if path == "/api/agents/config":
            from contextlib import ExitStack
            pid = str(data.get("id") or "")
            try:
                with ExitStack() as stack:
                    for room in sorted(R.rooms.all(), key=lambda row: row.id):
                        stack.enter_context(room.lock)
                        if pid in room.meta.get("participants", []) and (room.busy_for(pid) or execution.binding(room, pid)["phase"] != "ready"):
                            return self._json(409, {"error": "此 Agent 正在回复或排队，请结束后再修改配置"})
                    result = agent_settings.save(pid, data.get("changes"), data.get("revision"))
                return self._json(200, {"ok": True, "config": result})
            except ValueError as error:
                return self._json(409 if "其他窗口" in str(error) else 400, {"error": str(error)})
            except OSError:
                return self._json(500, {"error": "无法保存 Agent 设置，请检查数据目录的写入权限和剩余空间"})
        if path == "/api/agents/config/mcp":
            try:
                result = agent_settings.install_mcp(str(data.get("id") or ""), data.get("replace_key") is True,
                                                    data.get("revision"))
                return self._json(200, {"ok": True, "message": result})
            except (ValueError, OSError) as error:
                return self._json(400, {"error": str(error)})
        if path == "/api/extensions/open-folder":
            try:
                return self._json(200, extensions.open_folder(
                    str(data.get("root_id") or ""),
                    local_host=self._is_host_owner(),
                    conversations=R.rooms.listing()))
            except extensions.ExtensionError as error:
                return self._json(error.code, {"error": error.message})
        if path == "/api/extensions/import-skill":
            try:
                return self._json(200, extensions.import_skill(
                    agent_id=str(data.get("agent_id") or ""),
                    scope=str(data.get("scope") or ""),
                    project_id=str(data.get("project_id") or ""),
                    source_path=str(data.get("source_path") or ""),
                    local_host=self._is_host_owner(),
                    conversations=R.rooms.listing()))
            except extensions.ExtensionError as error:
                body = {"error": error.message}
                if error.conflict_name:
                    body["conflict_name"] = error.conflict_name
                return self._json(error.code, body)
        if path == "/api/update/download":
            if not self._is_local_owner():
                return self._json(403, {"error": "请在运行 AnY 的电脑上下载更新"})
            from . import updater
            try:
                if data.get('auto_install') is True:
                    return self._json(200, updater.start_download(auto_install=True,
                        busy=lambda: any(row.get('running') or row.get('queued') for row in R.rooms.listing()),
                        stop_backend=lambda: stop_idle_for_update(self.server)))
                return self._json(200, updater.start_download())
            except ValueError as error:
                return self._json(409, {"error": str(error)})
        if path == "/api/update/install":
            if not self._is_local_owner() or bool(getattr(self, "_device_id", "")):
                return self._json(403, {"error": "请在运行 AnY 的电脑上安装更新"})
            if any(row.get("running") or row.get("queued") for row in R.rooms.listing()):
                return self._json(409, {"error": "还有任务正在运行或排队，请等待完成后再更新"})
            from . import updater
            try:
                return self._json(200, updater.start_install(lambda: stop_idle_for_update(self.server)))
            except ValueError as error:
                return self._json(409, {"error": str(error)})
        if path == "/api/invites":
            room_id = str(data.get("room") or "")
            r = R.rooms.get(room_id)
            if r is None or common.is_archived(r.meta.get("status")):
                return self._json(400, {"error": "会话不存在或已归档"})
            try:
                issued = invites.create(room_id, data.get("permissions"), str(data.get("label") or "游客邀请"),
                                        data.get("expires_days") or 7)
            except invites.InviteError as error:
                return self._json(error.code, {"error": str(error)})
            base = self._base_url(data.get("base")) or getattr(self.server, "lan_url", None) or ""
            url = (base.rstrip("/") + "/join#invite=" + quote(issued["token"])) if base else ""
            return self._json(200, {"ok": True, "token": issued["token"],
                                    "invite": invites.public(issued), "url": url,
                                    "expires": issued["expires"]})
        if path == "/api/invites/revoke":
            try:
                invites.revoke(str(data.get("id") or ""))
            except invites.InviteError as error:
                return self._json(error.code, {"error": str(error)})
            return self._json(200, {"ok": True})
        if path == "/api/guests/remove":
            try:
                return self._json(200, invites.remove_guest(str(data.get("id") or "")))
            except invites.InviteError as error:
                return self._json(error.code, {"error": str(error)})
        if path == "/api/ui/session":
            if getattr(self, "_device_id", ""):
                return self._json(200, {"ok": True, "tracked": False})
            lifecycle = getattr(self.server, "owner_lifecycle", None)
            if lifecycle is not None:
                try:
                    lifecycle.update(data.get("tab"), data.get("action"), data.get("instance"))
                except ValueError as error:
                    return self._json(400, {"error": str(error)})
            return self._json(200, {"ok": True})
        if path == "/api/server/exit":
            self._json(200, {"ok": True})
            threading.Thread(target=lambda: stop_application(self.server), daemon=True).start()
            return
        if path == "/api/server/stop":
            # The launcher uses this only after confirming the same installation/data.
            if any(row.get("running") or row.get("queued") for row in R.rooms.listing()):
                return self._json(409, {"error": "仍有任务运行或排队，请等待结束后再更新"})
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path == "/api/devices/code":
            base = self._base_url(data.get("base")) or getattr(self.server, "lan_url", None) or ""
            result = devices.create_code(str(data.get("label") or ""))
            return self._json(200, {"ok": True, "id": result["id"], "code": result["token"], "expires": result["expires"],
                                    "url": (base.rstrip("/") + "/enroll#code=" + quote(result["token"])) if base else ""})
        if path == "/api/devices/link":
            base = self._base_url(data.get("base")) or getattr(self.server, "lan_url", None) or ""
            if not base:
                return self._json(400, {"error": "请填写设备可以访问的地址"})
            result = devices.create_link(str(data.get("label") or ""))
            return self._json(200, {"ok": True, "id": result["device"]["id"],
                                    "url": base.rstrip("/") + "/enroll#device=" + quote(result["token"])})
        if path == "/api/devices/revoke":
            try:
                device_id = str(data.get("id") or "")
                devices.revoke(device_id)
            except devices.DeviceError as error:
                return self._json(error.code, {"error": str(error)})
            for room in R.rooms.all():
                room.revoke_dispatch_device(device_id)
            return self._json(200, {"ok": True})
        if path == "/api/discovery/scan":
            return self._json(200, discovery.scan())
        if path == "/api/discovery/connect":
            ok, res = discovery.connect(str(data.get("id") or ""), data.get("via"), data.get("replace_key") is True)
            return self._json(200 if ok else 409, res)
        if path == "/api/discovery/prepare":
            try:
                return self._json(200, dict(discovery.prepare(data.get("id"), data.get("via")), ok=True))
            except (ValueError, OSError) as error:
                return self._json(409, {"error": str(error)})
        if path == "/api/discovery/dismiss":
            return self._json(200, discovery.dismiss(str(data.get("id") or "all")))
        if path == "/api/settings/connection":
            snap = conn_settings.save(
                global_values=data.get("global") if isinstance(data.get("global"), dict) else None,
                pid=str(data.get("id") or "") or None,
                contact_values=data.get("contact") if isinstance(data.get("contact"), dict) else None,
                clear_contact=bool(data.get("clear_contact")),
            )
            return self._json(200, {"ok": True, "settings": snap})
        if path == "/api/members/standby/stop":
            pid = str(data.get("id") or "")
            if not pid:
                return self._json(400, {"error": "缺少成员 id"})
            return self._json(200, members.broker.stop_standby(pid))
        if path == "/api/contacts/key":
            try:
                token = access.credential(str(data.get("id") or ""), data.get("revoke") is True)
                return self._json(200, {"ok": True, "token": token})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
        if path == "/api/contacts/check":
            try:
                return self._json(200, {"ok": True, "connection": connections.check(str(data.get("id") or ""))})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
        if path == "/api/contacts/status":
            pid = str(data.get("id") or "")
            return self._json(200, {"connection": connections.status(pid), "member": members.broker.status(pid)})
        if path == "/api/projects/choose-workdir":
            if not self._is_host_owner():
                return self._json(403, {"error": "只能在运行 AnY 的 Mac 上选择项目文件夹。"})
            if sys.platform != "darwin":
                return self._json(404, {"error": "此系统不提供网页文件夹选择器。"})
            try:
                workdir = projects.choose_macos_workdir()
            except (OSError, SubprocessError, UnicodeError) as error:
                logger.warning("macOS folder picker failed: %s", error)
                return self._json(503, {"error": "无法打开 macOS 文件夹选择器，请重试或手动填写路径。"})
            return self._json(200, {"workdir": workdir})
        if path in ("/api/projects/new", "/api/projects/update", "/api/projects/workspaces"):
            if not self._is_host_owner():
                return self._json(403, {"error": "不能从其他设备指定这台电脑的文件夹；请在运行 AnY 的设备上管理项目。"})
            try:
                if path == "/api/projects/new":
                    p = projects.create(data.get("name"), data.get("workdir"), data.get("workdirs"))
                else:
                    pid = str(data.get("id") or "")
                    with R.rooms.lock:
                        rows = R.rooms.listing()
                        if path == "/api/projects/update":
                            p = projects.update(pid, data.get("name"), data.get("workdirs"), rows)
                        else:
                            p = next((p for p in projects.listing(rows) if p["id"] == pid), None)
                    if p is None:
                        return self._json(404, {"error": "项目不存在"})
                    if path == "/api/projects/workspaces":
                        return self._json(200, {"workspaces": projects.workspaces(p)})
                return self._json(200, {"ok": True, "project": p})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            except OSError:
                return self._json(500, {"error": "无法保存项目变更，请检查数据目录的写入权限和剩余空间"})
        if path in ("/api/projects/delete", "/api/rooms/move"):
            try:
                with R.rooms.lock:
                    rows = R.rooms.listing()
                    if path == "/api/projects/delete":
                        pid = str(data.get("id") or "")
                        project_rows = [row for row in rows if (row.get("project") or ("" if row.get("standalone") else projects.legacy_id(row["workdir"]))) == pid]
                        if any(row.get("running") or row.get("queued") or ((loaded := R.rooms.loaded.get(row["id"])) is not None and loaded.busy_for())
                               for row in project_rows):
                            return self._json(409, {"ok": False, "error": "项目下有正在运行或排队的会话，请先停止后再删除"})
                        trashed_rooms: list[str] = []
                        for row in project_rows:
                            ok, msg = R.trash_meeting(row["id"])
                            if not ok:
                                return self._json(409, {"ok": False, "error": msg, "trashed_rooms": trashed_rooms})
                            trashed_rooms.append(row["id"])
                        ok, msg = projects.delete(pid, rows)
                        return self._json(200 if ok else 409, {"ok": ok, "error": msg, "trashed_rooms": trashed_rooms})
                    else:
                        pid = str(data.get("project") or "")
                        if not any(p["id"] == pid for p in projects.listing(rows)):
                            return self._json(404, {"error": "目标项目不存在"})
                        ok, msg = R.rooms.move_project(str(data.get("id") or ""), pid)
            except OSError:
                return self._json(500, {"error": "无法保存项目变更，请检查数据目录的写入权限和剩余空间"})
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if path == "/api/rooms/new":
            if data.get("workdir") and (not self._is_local_owner() or getattr(self, "_device_id", "")):
                return self._json(403, {"error": "不能从其他设备指定这台电脑的文件夹。"})
            ann = str(data.get("announcement", ""))
            if len(ann.encode("utf-8")) > MAX_ANN:
                return self._json(413, {"error": "too large (max 16KB)"})
            pid = str(data.get("project") or "")
            workspace = data.get("workspace")
            if workspace is not None and (not isinstance(workspace, str) or not pid):
                return self._json(400, {"error": "请选择项目里的工作目录"})
            if workspace and not self._is_host_owner():
                return self._json(403, {"error": "请在运行 AnY 的设备上选择工作目录"})
            member_ids = data.get("participants")
            if member_ids is not None and (not isinstance(member_ids, list) or any(not isinstance(a, str) or a not in registry.enabled_ids() for a in member_ids)):
                return self._json(400, {"error": "请选择已有且启用的联系人"})
            try:
                if "permissions" in data and not isinstance(data["permissions"], dict):
                    raise ValueError("权限必须是对象")
                project = None
                if workspace:
                    project = next((p for p in projects.listing(R.rooms.listing()) if p["id"] == pid), None)
                    if project is None or workspace not in {w["path"] for w in projects.workspaces(project)}:
                        raise ValueError("工作目录不在项目中，或已不可用")
                with R.rooms.lock:
                    current = next((p for p in projects.listing(R.rooms.listing()) if p["id"] == pid), None)
                    if pid and current is None:
                        raise ValueError("项目不存在")
                    if workspace and current != project:
                        raise ValueError("项目工作目录已更新，请重新选择")
                    wd = workspace or (current["workdir"] if current else str(data.get("workdir") or "").strip().strip('"')) or PROJECT
                    wd = os.path.normpath(os.path.expandvars(os.path.expanduser(wd)))
                    if not os.path.isabs(wd) or not os.path.isdir(wd):
                        raise ValueError("工作文件夹不存在：" + wd)
                    r = R.rooms.create(str(data.get("title", "")), ann, wd, pid, member_ids, data.get("permissions"), standalone=not pid)
            except ValueError as error:
                return self._json(400, {"error": str(error)})
            return self._json(200, {"ok": True, "id": r.id})
        if path == "/api/rooms/archive":
            ok, msg = R.set_archived(str(data.get("id", "")), bool(data.get("on")))
        elif path == "/api/rooms/delete":
            ok, msg = R.trash_meeting(str(data.get("id", "")))
        elif path == "/api/trash/restore":
            ok, msg, _new = R.restore_meeting(str(data.get("id", "")))
        elif path == "/api/trash/purge":
            cleanup: list[dict[str, str]] = []
            if "id" in data:
                ok, msg = R.purge_meeting(str(data.get("id") or ""), cleanup)
            else:
                ok, msg = R.purge_all(cleanup)
            return self._json(200 if ok else 409, {"ok": ok, "error": msg, "cleanup": cleanup})
        elif path == "/api/claims/release":
            it = guard.force_release(str(data.get("key", "")))
            if it is None:
                return self._json(409, {"ok": False, "error": "已经放开了"})
            r = R.rooms.loaded.get(it["room"])
            if r is not None:
                r.add_message("系统", "你放开了 %s 占着的 %s" % (it["ai"], it["shown"]))
            return self._json(200, {"ok": True})
        elif path == "/api/claims/mine":   # 用户自己占：我在手动改这些，AI 别动
            paths = [os.path.normpath(os.path.expanduser(str(p).strip().strip('"'))) for p in data.get("paths") or [] if str(p).strip()]
            if not paths or not all(os.path.isabs(p) for p in paths):
                return self._json(400, {"error": "填完整路径"})
            res = guard.claim(("", USER), paths, data.get("minutes"), str(data.get("reason") or "用户自己在改"), "")
            return self._json(200, {"ok": True, "claimed": [p for p, ok_, _ in res if ok_],
                                    "blocked": [{"path": p, "by": hit["ai"]} for p, ok_, hit in res if not ok_]})
        else:
            return self._send(404, b"not found", "text/plain")
        return self._json(200 if ok else 409, {"ok": ok, "error": msg})

    def _room_post(self, r, act, qs):
        device = getattr(self, "_device_id", "")
        can_dispatch = not device or r.device_can_dispatch(device)
        if not can_dispatch and act in {"mode", "turn/retry", "turn/approval", "wrapup", "compact", "undo",
                                        "debate/start", "debate/continue", "debate/finish"}:
            return self._json(403, {"error": "这台设备尚未获准在本会话派活，请在运行 AnY 的电脑上授权"})
        if device and act in {"execution", "tools", "handoff", "session/reset"}:
            return self._json(403, {"error": "请在运行 AnY 的电脑上管理执行环境"})
        if device and act in {"members", "participants", "invite"}:
            return self._json(403, {"error": "请在运行 AnY 的电脑上管理本会话成员权限"})
        if act in ('send', 'turn/retry', 'compact', 'wrapup', 'debate/start', 'debate/continue'):
            from . import updater
            if updater.status().get('state') == 'installing':
                return self._json(409, {"error": "AnY 正在更新，请重新打开后再操作"})
        if act == "upload":
            name = (parse_qs(qs).get("name") or [""])[0]
            te = (self.headers.get("Transfer-Encoding") or "").lower()
            if "chunked" in te:
                try:
                    body = self._read_chunked_body(MAX_UPLOAD)
                except ValueError as e:
                    code = 413 if "too large" in str(e) else 400
                    return self._json(code, {"error": str(e)})
                if not body:
                    return self._json(400, {"error": "empty"})
                try:
                    full = r.save_upload(name, io.BytesIO(body).read, len(body))
                except Exception as e:
                    return self._json(500, {"error": str(e)})
                return self._json(200, R.make_attachment(full))
            n = self._length()
            if n <= 0:
                return self._json(400, {"error": "empty"})
            if n > MAX_UPLOAD:
                return self._json(413, {"error": "too large (max 25MB)"})
            try:
                full = r.save_upload(name, self.rfile.read, n)
            except Exception as e:
                return self._json(500, {"error": str(e)})
            return self._json(200, R.make_attachment(full))
        data = self._read_json()
        if data is None:
            return
        if act == "open":   # 页面打开了这场会议：记成"最近打开的"（外部程序不指定会议时发到这里）
            R.set_last(r.id)
            return self._json(200, {"ok": True})
        if act == "send":
            text = str(data.get("text", "")).strip()
            atts = r.clean_attachments(data.get("attachments"))
            if not text and not atts:
                return self._json(400, {"error": "empty"})
            reply = r.make_reply(data.get("reply_to"), data.get("reply_part")) if data.get("reply_to") is not None else None
            R.set_last(r.id)
            r.handle_message("你", text, atts, reply_to=reply, dispatch_device=device)
            return self._json(200, {"ok": True})
        if act == "recall":
            return self._recall(r, data.get("id"), "你")
        if act in ("rename", "session/reset"):
            try:
                if act == "rename":
                    ok, msg = r.rename(data.get("title"))
                else:
                    ok, msg = r.reset_session(str(data.get("ai") or ""))
            except OSError:
                return self._json(500, {"error": "无法保存会话，请检查数据目录权限或文件是否被占用后重试"})
            return self._json(200 if ok else 409, {"ok": ok, "error": msg, "title": r.title()})
        if act in ("debate/start", "debate/finish", "debate/continue"):
            try:
                if act == "debate/start":
                    state = debate.start(r, data)
                elif act == "debate/continue":
                    state = debate.continue_debate(r, data)
                else:
                    state = debate.finish(r)
            except ValueError as error:
                return self._json(409, {"ok": False, "error": str(error)})
            except OSError:
                return self._json(500, {"ok": False, "error": "无法保存论道状态"})
            return self._json(200, {"ok": True, "debate": state})
        if act == "announcement":
            text = str(data.get("text", ""))
            if len(text.encode("utf-8")) > MAX_ANN:
                return self._json(413, {"error": "too large (max 16KB)"})
            r.write_announcement(text)
            return self._json(200, {"ok": True})
        if act == "board":
            try:
                ids = [int(data.get("id"))] if data.get("id") is not None else []
            except (TypeError, ValueError):
                return self._json(400, {"error": "bad id"})
            res = r.board_op("你", str(data.get("op", "")), str(data.get("kind", "")), str(data.get("text", "")), ids)
            if not res:
                return self._json(400, {"error": "没改成"})
            r.board_note("你", [res])
            return self._json(200, {"ok": True})
        if act == "mode":
            ok, msg = r.set_mode(str(data.get("mode", "")))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act in ("turn/retry", "turn/retry/preview"):
            message_id = data.get("id")
            if type(message_id) is not int:
                return self._json(400, {"ok": False, "error": "bad id"})
            if act.endswith("/preview"):
                ok, msg, plan = r.retry_preview(message_id)
                return self._json(200 if ok else 409, {"ok": ok, "error": msg, "plan": plan})
            ok, msg = r.retry_turn(message_id, data.get("action"))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "turn/approval":
            approval_id, decision = data.get("id"), data.get("decision")
            if not isinstance(approval_id, str) or decision not in ("allow", "deny"):
                return self._json(400, {"ok": False, "error": "bad approval"})
            ok, msg = r.resolve_turn_approval(approval_id, decision)
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act in ("step/info", "step/diff"):
            seq, path = data.get("step"), data.get("path")
            if type(seq) is not int:
                return self._json(400, {"ok": False, "error": "bad step"})
            if act == "step/info":
                step = r.step_info(seq)
                return self._json(200 if step else 404, {"ok": bool(step), "step": step})
            if not isinstance(path, str):
                return self._json(400, {"ok": False, "error": "bad step or path"})
            ok, diff, reason = r.step_diff(seq, path)
            return self._json(200 if ok else 404, {"ok": ok, "diff": diff, "reason": reason})
        if act in ("undo", "undo/preview"):
            try:
                seq = int(data.get("step"))
            except (TypeError, ValueError):
                return self._json(400, {"ok": False, "error": "bad step"})
            if act == "undo/preview":
                ok, msg, plan = r.undo_preview(seq)
                return self._json(200 if ok else 409, {"ok": ok, "error": msg, "plan": plan})
            ok, msg = r.undo_step(seq)
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "models":
            ok, msg, changed = r.set_models(str(data.get("ai", "")), str(data.get("model") or ""), str(data.get("effort") or ""))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg, "model_changed": changed, "model": r.model_info(str(data.get("ai", ""))) if ok else None})
        if act == "models/refresh":
            ai = str(data.get("ai") or "")
            try:
                model_catalog.refresh(r, ai)
                return self._json(200, {"ok": True, "model": r.model_info(ai)})
            except ValueError as error:
                return self._json(409, {"error": str(error)})
        if act == "execution":
            pid = str(data.get("ai") or "")
            try:
                expected = data.get("version")
                if not isinstance(expected, int) or isinstance(expected, bool):
                    raise ValueError("请提供当前执行端版本")
                result = execution.cancel(r, pid, expected) if data.get("op") == "cancel" else execution.prepare(r, pid, str(data.get("endpoint") or ""), expected)
                return self._json(200, dict(result, ok=True))
            except (ValueError, OSError) as error:
                return self._json(409, {"error": str(error)})
        if act == "tools":
            ok, msg = r.set_tools(str(data.get("ai", "")), data.get("tools"))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "handoff":
            ok, msg = r.set_handoff(str(data.get("ai", "")), bool(data.get("on")))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "wrapup":
            ok, msg = r.request_wrapup()
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "stop":
            who = str(data.get("ai") or "")
            if who and who not in r.ais:
                return self._json(400, {"error": "ai 只能是这场会议里的：" + "、".join(r.ais) + "；不填 = 全停"})
            return self._json(200, {"ok": True, "msg": r.stop_ais([who] if who else None)})
        if act == "participants":
            ok, msg = r.set_participants(data.get("participants"))
            return self._json(200 if ok else 409, {"ok": ok, "error": msg, "participants": list(r.ais)})
        if act == "members":
            try:
                shared = data.get("guest_discussion")
                dispatch_devices = data.get("dispatch_devices")
                if shared is not None and shared != r.meta.get("guest_discussion", {}) and not self._is_host_owner():
                    return self._json(403, {"error": "请在运行 AnY 的电脑上更改 Agent 共享"})
                if dispatch_devices is not None:
                    if not self._is_host_owner():
                        return self._json(403, {"error": "请在运行 AnY 的电脑上管理设备派活权限"})
                    paired = {row["id"] for row in devices.listing()}
                    if not isinstance(dispatch_devices, list) or any(not isinstance(pid, str) or pid not in paired for pid in dispatch_devices):
                        return self._json(400, {"error": "请选择有效的配对设备"})
                    dispatch_devices = list(dict.fromkeys(dispatch_devices))
                ok, msg = r.set_members(data.get("participants"), data.get("permissions"), shared, dispatch_devices)
            except OSError:
                return self._json(500, {"error": "无法保存会话，请检查数据目录权限或文件是否被占用后重试"})
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})
        if act == "contact/policies":
            if not self._is_host_owner():
                return self._json(403, {"error": "请在运行 AnY 的电脑上管理联系人授权"})
            try:
                r.set_contact_policy(str(data.get("contact") or ""), data.get("policy"))
            except ValueError as error:
                return self._json(409, {"error": str(error)})
            except OSError:
                return self._json(500, {"error": "无法保存联系人授权"})
            return self._json(200, {"ok": True})
        if act == "contact/revoke":
            if not self._is_host_owner():
                return self._json(403, {"error": "请在运行 AnY 的电脑上撤销联系人授权"})
            try:
                pid = str(data.get("contact") or "")
                revoked = r.remove_external_human(pid) if access.human(pid) else r.revoke_agent(pid)
            except OSError:
                return self._json(500, {"error": "撤权操作遇到本机文件或进程错误，请查看状态"})
            return self._json(200 if revoked else 404, {"ok": revoked, "error": "" if revoked else "找不到本会话的联系人"})
        if act == "contact/share":
            if not self._is_host_owner():
                return self._json(403, {"error": "请在运行 AnY 的电脑上确认外发"})
            try:
                message = r.share_result(data.get("id"), data.get("recipients"), data.get("attachments", []),
                                         data.get("share_text", True) is True)
            except ValueError as error:
                return self._json(400, {"error": str(error)})
            except OSError:
                return self._json(500, {"error": "无法复制并发布所选附件"})
            return self._json(200, {"ok": True, "id": message["id"]})
        if act == "invite":
            pid = str(data.get("contact") or "")
            value = data.get("permissions")
            if not isinstance(value, dict):
                return self._json(400, {"error": "请选择此联系人的会话权限"})
            if "joined" in data and not isinstance(data["joined"], bool):
                return self._json(400, {"error": "加入状态必须是布尔值"})
            if not registry.get(pid):
                return self._json(409, {"error": "联系人不存在"})
            try:
                with r.lock:
                    member_ids: list[str] = list(dict.fromkeys([str(a) for a in r.meta.get("participants", [])] + [pid]))
                    if data.get("joined") is False:
                        member_ids = [a for a in member_ids if a != pid]
                    perms: dict[str, Any] = {a: access.permissions(r, a) for a in member_ids}
                    if pid in member_ids:
                        perms[pid] = value
                    ok, msg = r.set_members(member_ids, perms)
            except OSError:
                return self._json(500, {"error": "无法保存会话，请检查数据目录权限或文件是否被占用后重试"})
            return self._json(200 if ok else 409, {"ok": ok, "error": msg})

        if act == "compact":
            who = str(data.get("ai") or "")
            if who and who not in r.ais:
                return self._json(400, {"error": "ai 只能是这场会议里的：" + "、".join(r.ais) + "；不填 = 全压"})
            todo = r.request_compact([who] if who else None)
            if not todo:
                return self._json(409, {"error": "%s已经在压缩了" % (who or "两个都")})
            return self._json(200, {"ok": True, "ais": todo})
        return self._send(404, b"not found", "text/plain")

    def _recall(self, room, mid, speaker, external=False):
        try:
            code, result = room.recall_message(mid, speaker)
        except OSError:
            return self._json(500, {"error": "无法保存撤回，请检查数据目录的写入权限"})
        if external and code == 200:
            result = dict(result)
            for key in ("draft", "restored"):
                if isinstance(result.get(key), dict):
                    result[key] = {"text": result[key].get("text", "")}
        return self._json(code, result)

    def _external_post(self, recall=False):
        """给外部程序用：桌面应用里的 Claude、终端里的 Claude / Codex 等。room 不填 = 用户最近打开的那场。"""
        from . import updater
        if updater.status().get('state') == 'installing':
            return self._json(409, {"error": "AnY 正在更新，请重新打开后再操作"})
        data = self._read_json()
        if data is None:
            return
        speaker = access.identify(self._bearer())
        if not speaker:
            return self._json(401, {"error": "请使用联系人接入密钥"})
        if data.get("speaker") and data["speaker"] != speaker:
            return self._json(403, {"error": "密钥不能冒用其他联系人"})
        rid = str(data.get("room") or "").strip()
        r = R.rooms.get(rid) if rid else None
        if r is None:
            return self._json(409 if not rid else 404, {"error": "room 必填，请先列出受邀会话" if not rid else "没有这场会话：" + rid})
        if not access.allowed(r, speaker, "read") or not access.allowed(r, speaker, "post"):
            return self._json(403, {"error": "未加入此会话或没有发言权限"})
        if not access.external_allowed(r, speaker, str(data.get("worker") or self.headers.get("X-AnY-Worker") or self.headers.get("X-Cojam-Worker") or ""),
                                       str(data.get("binding_token") or self.headers.get("X-AnY-Execution") or self.headers.get("X-Cojam-Execution") or "")):
            return self._json(403, {"error": "此会话属于另一个执行端"})
        if recall:
            if (registry.get(speaker) or {}).get("kind") != "user":
                return self._json(403, {"error": "只有真人联系人能撤回自己的消息"})
            return self._recall(r, data.get("id"), speaker, external=True)
        text = str(data.get("text", "")).strip()
        if not text:
            return self._json(400, {"error": "empty"})
        dispatch_errors: list[dict[str, str]] = []
        r.handle_message(speaker, text, origin="external", dispatch_errors=dispatch_errors)
        connections.seen(speaker, self._bearer(), "http")
        return self._json(200, {"ok": True, "speaker": speaker, "origin": "external", "room": r.id,
                                "dispatch_errors": dispatch_errors})

    def _external_get(self, path, q):
        pid = access.identify(self._bearer())
        if not pid:
            return self._json(401, {"error": "接入密钥无效或已撤销"})
        if path == "/api/external/rooms":
            connections.seen(pid, self._bearer(), "http")
            worker = str(self.headers.get("X-AnY-Worker") or self.headers.get("X-Cojam-Worker") or "")
            execution = str(self.headers.get("X-AnY-Execution") or self.headers.get("X-Cojam-Execution") or "")
            return self._json(200, {"contact": registry.public(registry.get(pid)), "rooms": access.visible_rooms(pid, worker, execution)})
        rid = (q.get("room") or [""])[0]
        r = R.rooms.get(rid) if rid else None
        worker = str(self.headers.get("X-AnY-Worker") or self.headers.get("X-Cojam-Worker") or "")
        execution = str(self.headers.get("X-AnY-Execution") or self.headers.get("X-Cojam-Execution") or "")
        if r is None or not access.external_allowed(r, pid, worker, execution):
            return self._json(403, {"error": "没有此会话的读取权限"})
        if path == "/api/external/messages":
            connections.seen(pid, self._bearer(), "http")
            result = r.messages_since(_int(q, "since"), external_pid=pid)
            # External clients receive text and message metadata, never local file paths.
            is_guest = access.human(pid)
            public = []
            for message in result["messages"]:
                row = {k: message[k] for k in ("id", "time", "speaker", "text", "to_user", "recalled") if k in message}
                if is_guest:
                    speaker = message["speaker"]
                    if speaker == "系统":
                        row["role"] = "system"
                    else:
                        row["role"] = "human" if speaker == "你" or access.human(speaker) else "ai"
                if is_guest and message.get("origin") == "shared-result":
                    row["shared_attachments"] = [{"name": item["name"], "size": item["size"], "index": index}
                                                 for index, item in enumerate(message.get("attachments", []))]
                public.append(row)
            result["messages"] = public
            result["self"] = pid if (registry.get(pid) or {}).get("kind") == "user" else ""
            result["permissions"] = access.permissions(r, pid)
            if access.human(pid):
                result["history_from"] = access.history_start(r, pid)
            return self._json(200, result)
        if path == "/api/external/attachment" and access.human(pid):
            try:
                message, index = int(q["message"][0]), int(q["index"][0])
            except (KeyError, ValueError):
                return self._json(400, {"error": "缺少有效的附件编号"})
            attachment = r.shared_attachment(pid, message, index)
            if attachment and attachment["url"].startswith("/files/"):
                return self._serve_file(attachment["url"][len("/files/"):], private_share=True)
            return self._json(404, {"error": "附件不存在或未分享给你"})
        return self._json(404, {"error": "unknown endpoint"})

    def _mcp(self):
        origin = self.headers.get("Origin")
        if origin and not re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$", origin):
            return self._json(403, {"error": "origin not allowed"})   # 防网页借浏览器打本机端口（DNS rebinding）
        n = self._length()
        if n < 0 or n > MAX_BODY * 4:
            return self._json(413, {"error": "too large"})
        code, resp = mcp.handle_http(self.rfile.read(n), self._bearer())
        if resp is None:
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._json(code, resp)

    def _guard(self, kind):
        """编辑前的钩子来问：能不能改这个文件。钥匙 = 会议室起 AI 时给的。"""
        who = R.who_by_key(self._bearer())
        n = self._length()
        if n < 0 or n > MAX_BODY * 16:
            return self._json(413, {"error": "too large"})
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return self._json(400, {"error": "bad json"})
        if not isinstance(data, dict):
            return self._json(400, {"error": "bad json"})
        if who is None:   # 钥匙对不上（会议室重启过之类）：不挡，免得 AI 白白卡住
            return self._json(200, agents.guard_allow(kind))
        r = R.rooms.get(who[0])
        if r is not None and (execution.binding(r, who[1])["endpoint"] == "desktop" or execution.binding(r, who[1])["phase"] != "ready"
                              or not access.allowed(r, who[1], "work") or r.turn_revoked(who[1])
                              or (who[1] in r.turn_dispatch and r.active_member_mode(who[1]) != "work")):
            return self._json(200, {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "此成员没有干活权限"}})
        return self._json(200, agents.guard_decide(kind, r, who[1], data))


def _int(q, name):
    try:
        return max(0, int((q.get(name) or ["0"])[0]))
    except ValueError:
        return 0


class ExclusiveServer(ThreadingHTTPServer):
    """端口独占：已经有会议室在跑时绑定失败，而不是两个进程悄悄共用一个端口。"""
    allow_reuse_address = pal.socket_reuse_allowed()   # Windows 的 SO_REUSEADDR 会允许重复绑定；别的系统上它只管 TIME_WAIT，留着
    daemon_threads = True
    lan_url: str | None = None
    tailscale_url: str | None = None
    owner_lifecycle: Any = None

    def __init__(self, *args, **kwargs):
        # Keep one UI/backend generation together until restart. Previously an
        # old process hot-served a new UI from disk and silently lost its APIs.
        with open(INDEX, "rb") as f:
            self.ui_index = f.read()
        self.ui_assets = {}
        for name in os.listdir(STATIC):
            if name.endswith((".js", ".css", ".html")):
                with open(os.path.join(STATIC, name), "rb") as f:
                    self.ui_assets[name] = f.read()
        super().__init__(*args, **kwargs)

    def server_bind(self):
        pal.apply_exclusive_socket(self.socket)
        # HTTPServer.server_bind performs reverse DNS, which can stall startup
        # before the desktop window can connect. The listener already has an IP.
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name, self.server_port = str(host), int(port)


def _stop_runtime() -> None:
    """Close AnY-owned agent sessions and terminate AnY detached workers cleanly on exit."""
    from . import detached_jobs
    keep_detached = os.environ.get("ROUNDTABLE_KEEP_DETACHED_ON_EXIT") == "1"
    detached_jobs.begin_shutdown()
    snapshot = R.rooms.all()
    for room in snapshot:
        try:
            with room.lock:
                busy = bool(room.state["running"] or room.pending or not room.jobs.empty())
            if not keep_detached:
                if busy:
                    room.stop_ais()
                detached_jobs.cancel_jobs(room)
            elif busy and not detached_jobs.has_active_jobs(room):
                room.stop_ais()
        except Exception as error:
            logger.warning("退出时停止会话失败: %s", error, exc_info=True)
        try:
            agents.stop_codex(room)
            acp.stop(room)
        except Exception as error:
            logger.warning("退出时停止会话子进程失败: %s", error, exc_info=True)
    try:
        agents.stop_all_codex()
        acp.stop()
    except Exception as error:
        logger.warning("退出时停止后台 Agent 会话失败: %s", error, exc_info=True)


def stop_application(server: Any) -> None:
    _stop_runtime()
    server.shutdown()


def stop_idle_for_update(server: Any) -> bool:
    """Do not interrupt work if it started while an update was downloading."""
    if any(row.get('running') or row.get('queued') for row in R.rooms.listing()):
        return False
    def shutdown():
        # Unlike the normal exit action, never stop active work during update.
        snapshot = R.rooms.all()
        for room in snapshot:
            with room.lock:
                if room.state['running'] or room.pending or not room.jobs.empty():
                    return
        for room in snapshot:
            agents.stop_codex(room)
            acp.stop(room)
        agents.stop_all_codex()
        acp.stop()
        server.shutdown()
    threading.Thread(target=shutdown, daemon=True).start()
    return True


def start_lan_listener(port: int | None = None) -> tuple[ExclusiveServer | None, str | None]:
    """在同一份 Handler 上再开一个只绑局域网地址的口子。没有局域网或端口被占就 (None, None)。
    管理员接口仍然只认本机页面注入的令牌，所以这个口子对外只到“加入会话”为止。"""
    ip = common.lan_ipv4()
    if not ip:
        return None, None
    port = int(os.environ.get("ROUNDTABLE_LAN_PORT", "8766")) if port is None else port
    try:
        srv = ExclusiveServer((ip, port), Handler)
    except OSError as error:
        logger.warning("局域网入口没开成（%s:%s）：%s", ip, port, error)
        return None, None
    srv.lan_url = "http://%s:%d" % (ip, srv.server_address[1])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.lan_url


def start_tailscale_listener(port: int | None = None) -> tuple[ExclusiveServer | None, str | None]:
    """在 Tailscale 地址上再开一个入口；没有 Tailscale 或端口被占就跳过，不影响其他入口。"""
    ip = common.tailscale_ipv4()
    if not ip:
        return None, None
    port = int(os.environ.get("ROUNDTABLE_TAILSCALE_PORT", "8767")) if port is None else port
    try:
        srv = ExclusiveServer((ip, port), Handler)
    except OSError as error:
        logger.warning("Tailscale 入口没开成（%s:%s）：%s", ip, port, error)
        return None, None
    srv.tailscale_url = "http://%s:%d" % (ip, srv.server_address[1])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.tailscale_url


def owner_lifecycle_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get("ROUNDTABLE_NO_BROWSER") != "1" or env.get("ROUNDTABLE_OWNER_LIFECYCLE") == "1"


def main(*, headless: bool = False) -> None:
    common.setup_logging()
    url = "http://%s:%d/" % (HOST, PORT)
    try:
        srv = ExclusiveServer((HOST, PORT), Handler)
    except OSError:
        from .server_runtime import reuse_or_stop, show_startup_error
        action, message = reuse_or_stop(url)
        if action == "reuse":
            if os.environ.get("ROUNDTABLE_NO_BROWSER") != "1":
                webbrowser.open(url)
            return
        if action != "stopped":
            if headless:
                print(message, file=sys.stderr)
                raise SystemExit(1)
            show_startup_error(message)
            return
        try:
            srv = ExclusiveServer((HOST, PORT), Handler)
        except OSError:
            if headless:
                print("旧后台尚未退出，请稍后重新启动 AnY。", file=sys.stderr)
                raise SystemExit(1)
            show_startup_error("旧后台尚未退出，请稍后重新打开 AI Bridge。")
            return
    lan_srv, lan_url = start_lan_listener()
    ts_srv, tailscale_url = start_tailscale_listener()
    for extra in (srv, lan_srv, ts_srv):
        if extra is not None:
            extra.lan_url = lan_url
            extra.tailscale_url = tailscale_url
    if owner_lifecycle_enabled():
        from .owner_lifecycle import OwnerLifecycle
        srv.owner_lifecycle = OwnerLifecycle(lambda: stop_application(srv))
        if os.environ.get("ROUNDTABLE_OWNER_LIFECYCLE") == "1":
            lease = float(os.environ.get("ROUNDTABLE_STARTUP_LEASE", "90") or "90")
            srv.owner_lifecycle.arm(lease)
        for extra in (lan_srv, ts_srv):
            if extra is not None:
                extra.owner_lifecycle = srv.owner_lifecycle
    agents.start_reaper()
    discovery.ensure_scanned(async_scan=True)
    from . import detached_jobs
    detached_jobs.reset_shutdown()
    threading.Thread(target=detached_jobs.recover_all, args=(R.rooms,), daemon=True, name="detached-recover").start()
    print("会议室已启动：" + url)
    if lan_url:
        print("同一局域网（同一个 WiFi）可扫码或打开：" + lan_url)
    if tailscale_url:
        print("Tailscale 网络可打开：" + tailscale_url)
    if os.environ.get("ROUNDTABLE_NO_BROWSER") != "1":
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        if headless:
            _stop_runtime()
    finally:
        srv.server_close()
        for extra in (lan_srv, ts_srv):
            if extra is not None:
                extra.shutdown()
                extra.server_close()
