"""Terminal entry point and local AnY HTTP client."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
import importlib.util
import json
import os
import sys
from http.cookies import CookieError, SimpleCookie
from threading import Lock
from urllib.parse import quote

from .version import CLI_VERSION, VERSION


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
            raise CliError(f"无法连接本机 AnY（127.0.0.1:{self.port}）。请运行 any 打开客户端，或运行 any serve 启动后台。") from error
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
                    raise CliError("无法读取 AnY 本机会话。") from error
                if status != 200 or "rt_owner" not in cookie:
                    raise CliError("这个端口没有可用的 AnY 本机会话。")
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
            raise CliError(detail or f"AnY 请求失败（HTTP {status}）。", status)
        if not isinstance(payload, dict):
            raise CliError("AnY 返回了无法识别的响应。")
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


def _run_cli_update(*, check_only: bool, as_json: bool) -> int:
    from . import cli_updater

    result = cli_updater.check()
    if not check_only and result.get("state") == "available" and result.get("release"):
        if not result.get("can_install"):
            if as_json:
                print(json.dumps({**result, "error": "当前为源码模式，请在源码目录运行 git pull 更新。"}, ensure_ascii=False))
            else:
                print(
                    f"发现 AnY CLI 新版本 v{result['latest']}（当前 v{result['current']}）。\n"
                    "当前不是通过官方终端安装脚本部署的环境，请在源码目录运行 git pull 更新。",
                    file=sys.stderr,
                )
            return 1
        try:
            installed = cli_updater.install_update(result["release"])
        except Exception as error:
            if as_json:
                print(json.dumps({**result, "state": "error", "error": str(error)}, ensure_ascii=False))
            else:
                print(f"AnY CLI 更新失败：{error}", file=sys.stderr)
            return 1
        if as_json:
            print(json.dumps(installed, ensure_ascii=False))
        else:
            print(f"AnY CLI 已更新至 v{installed['installed']}（commit {installed['commit'][:7]}），桌面端未受影响。")
            print("重新运行 any 即可使用新版 CLI。")
        return 0

    if as_json:
        out = {k: v for k, v in result.items() if k != "release"}
        print(json.dumps(out, ensure_ascii=False))
    elif result["state"] == "error":
        print(f"检查 AnY CLI 更新失败：{result['error']}", file=sys.stderr)
        return 1
    elif result["state"] == "available":
        print(f"发现 AnY CLI 新版本 v{result['latest']}（当前 v{result['current']}）。")
        if result["notes"]:
            print(result["notes"])
        print("运行 any update（或在终端内输入 /update install）即可独立更新 CLI。" if result["can_install"]
              else "当前为源码模式，请在源码目录运行 git pull 更新。")
    else:
        print(f"AnY CLI 当前已是最新版本（v{result['current']}，桌面端后台 v{VERSION}，两者独立更新）。")
    return 1 if result["state"] == "error" else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="any", description="AnY 终端客户端")
    parser.add_argument("--version", action="version", version=f"AnY CLI {CLI_VERSION}")
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
    upd = commands.add_parser("update", help="检查或更新 AnY CLI（与桌面端更新分离）")
    upd.add_argument("--check", action="store_true", help="只检查是否有 CLI 新版本")
    upd.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)

    if args.command == "update":
        return _run_cli_update(check_only=args.check, as_json=args.json)

    if args.command == "serve":
        os.environ["ROUNDTABLE_PORT"] = str(args.port)
        os.environ["ROUNDTABLE_NO_BROWSER"] = "1"
        from .common import HERE
        if not os.path.isfile(os.path.join(HERE, "index.html")):
            print("请在 AnY 源码目录运行 python -m bridge.cli serve，或使用桌面端启动后台。", file=sys.stderr)
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
            if not all(importlib.util.find_spec(name) for name in ("textual", "rich")):
                raise CliError('请先在源码目录运行 python -m pip install -e ".[cli]"。')
            from .cli_autostart import ensure_backend
            if sys.stderr.isatty():
                print("AnY 正在启动…", file=sys.stderr, flush=True)
            with ThreadPoolExecutor(max_workers=1) as executor:
                backend = executor.submit(ensure_backend, args.port)
                try:
                    from .terminal import AnYTerminal
                except ModuleNotFoundError as error:
                    if error.name not in ("textual", "rich"):
                        raise
                    raise CliError('请先在源码目录运行 python -m pip install -e ".[cli]"。') from error
                backend.result()
            AnYTerminal(client, getattr(args, "room", None)).run()
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
