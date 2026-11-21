"""Terminal entry point and local Cojam HTTP client."""
import argparse
import http.client
import json
import os
import sys
from http.cookies import CookieError, SimpleCookie
from threading import Lock
from urllib.parse import quote

from .version import VERSION


class CliError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def room_path(room, action):
    return f"/api/r/{quote(room, safe='')}/{action}"


class LocalClient:
    """Use the same loopback owner session as the desktop/web launcher."""

    def __init__(self, port):
        self.port = port
        self._token = ""
        self._lock = Lock()

    def _request(self, path, data=None, token=""):
        # Connect directly to loopback without proxies or redirects.
        timeout = 25 if path.startswith("/api/discovery") else 5
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        headers = {"X-RT-Token": token} if token else {}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            conn.request("GET" if data is None else "POST", path, body, headers)
            response = conn.getresponse()
            return response.status, response.headers, response.read()
        except (OSError, http.client.HTTPException) as error:
            raise CliError(f"无法连接本机 Cojam（127.0.0.1:{self.port}）。请打开桌面端或运行 cojam serve。") from error
        finally:
            conn.close()

    def call(self, path, data=None):
        with self._lock:
            if not self._token:
                status, headers, _ = self._request("/")
                cookie = SimpleCookie()
                try:
                    cookie.load(headers.get("Set-Cookie", ""))
                except CookieError as error:
                    raise CliError("无法读取 Cojam 本机会话。") from error
                if status != 200 or "rt_owner" not in cookie:
                    raise CliError("这个端口没有可用的 Cojam 本机会话。")
                self._token = cookie["rt_owner"].value
            token = self._token
        status, _, body = self._request(path, data, token)
        if status in (401, 403):
            with self._lock:
                if self._token == token:
                    self._token = ""
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            payload = None
        if not 200 <= status < 300:
            detail = (payload.get("error") or payload.get("msg")) if isinstance(payload, dict) else None
            raise CliError(detail or f"Cojam 请求失败（HTTP {status}）。", status)
        if not isinstance(payload, dict):
            raise CliError("Cojam 返回了无法识别的响应。")
        return payload


def port_number(value):
    message = "端口应为 1 到 65535 之间的整数"
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(message) from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(message)
    return port


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cojam", description="合拍 Cojam 终端客户端")
    parser.add_argument("--version", action="version", version=f"Cojam {VERSION}")
    parser.add_argument("--port", type=port_number, default=os.environ.get("ROUNDTABLE_PORT", "8765"),
                        help="本机后台端口（默认 8765 或 ROUNDTABLE_PORT）")
    commands = parser.add_subparsers(dest="command")
    meeting = commands.add_parser("open", help="打开终端界面，可指定会话")
    meeting.add_argument("room", nargs="?", help="会话 ID")
    commands.add_parser("serve", help="从源码启动后台，不打开网页")
    commands.add_parser("rooms", help="以 JSON 列出项目和会话")
    send = commands.add_parser("send", help="向指定会话发言，输出 JSON")
    send.add_argument("room", help="会话 ID")
    send.add_argument("text", help="消息文本，使用 - 从标准输入读入")
    messages = commands.add_parser("messages", help="读取指定会话消息，输出 JSON")
    messages.add_argument("room", help="会话 ID")
    messages.add_argument("--since", type=int, default=0, help="上次响应的 next 游标")
    args = parser.parse_args(argv)

    if args.command == "serve":
        os.environ["ROUNDTABLE_PORT"] = str(args.port)
        os.environ["ROUNDTABLE_NO_BROWSER"] = "1"
        from .common import HERE
        if not os.path.isfile(os.path.join(HERE, "index.html")):
            print("请在 Cojam 源码目录运行 python -m bridge.cli serve，或使用桌面端启动后台。", file=sys.stderr)
            return 1
        from .web import main as serve
        serve(headless=True)
        return 0

    client = LocalClient(args.port)
    try:
        if args.command == "rooms":
            result = client.call("/api/rooms")
        elif args.command == "messages":
            if args.since < 0:
                parser.error("--since 不能为负数")
            result = client.call(room_path(args.room, f"messages?since={args.since}"))
        elif args.command == "send":
            message = sys.stdin.read() if args.text == "-" else args.text
            result = client.call(room_path(args.room, "send"), {"text": message})
        else:
            try:
                from .terminal import CojamTerminal
            except ModuleNotFoundError as error:
                if error.name not in ("textual", "rich"):
                    raise
                raise CliError('请先在源码目录运行 python -m pip install -e ".[cli]"。') from error
            CojamTerminal(client, getattr(args, "room", None)).run()
            return 0
        print(json.dumps(result))
        return 0
    except CliError as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    # Use the same module identity as bridge.terminal when launched with -m.
    from .cli import main as run

    raise SystemExit(run())
