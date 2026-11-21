"""Launch the CLI installed by the website, with a local backend when needed."""
import argparse
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from . import cli


def data_directory():
    if override := os.environ.get("COJAM_CLI_INSTALL_DIR"):
        return Path(override).expanduser() / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cojam"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CojamCLI" / "data"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "cojam-cli" / "data"


def server_ready(port):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        conn.request("GET", "/api/server/info")
        response = conn.getresponse()
        info = json.loads(response.read(65536)) if response.status == 200 else {}
        return isinstance(info, dict) and info.get("app") == "AI Bridge"
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        conn.close()


def ensure_backend(port):
    if server_ready(port):
        return
    with socket.socket() as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise cli.CliError(f"无法使用端口 {port}。请稍后重试或设置 ROUNDTABLE_PORT。") from error

    directory = Path(os.environ.get("ROUNDTABLE_LOG_DIR", data_directory())).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "cli-server.log"
    env = dict(os.environ, ROUNDTABLE_LOG_DIR=str(directory), ROUNDTABLE_OWNER_LIFECYCLE="1")
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    with log.open("ab") as stream:
        child = subprocess.Popen([sys.executable, "-m", "bridge.cli", "--port", str(port), "serve"],
                                 stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, env=env, **options)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if server_ready(port):
            return
        if child.poll() is not None:
            break
        time.sleep(0.2)
    if child.poll() is None:
        child.terminate()
        child.wait(timeout=5)
    raise cli.CliError(f"无法启动 Cojam 后台。启动日志：{log}")


def main():
    args = sys.argv[1:]
    try:
        if not args or args[0] == "open":
            ensure_backend(cli.port_number(os.environ.get("ROUNDTABLE_PORT", "8765")))
        return cli.main(args)
    except (argparse.ArgumentTypeError, cli.CliError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
