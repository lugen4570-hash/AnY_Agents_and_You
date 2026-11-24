"""Start or reuse the local backend for the interactive CLI."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from threading import Thread
import time

from . import cli


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def data_directory():
    if override := (os.environ.get("ANY_CLI_INSTALL_DIR") or os.environ.get("COJAM_CLI_INSTALL_DIR")):
        return Path(override).expanduser() / "data"
    if sys.platform == "darwin":
        primary = Path.home() / "Library" / "Application Support" / "AnY"
        legacy = Path.home() / "Library" / "Application Support" / "Cojam"
        return primary if (_path_exists(primary) or not _path_exists(legacy)) else legacy
    if sys.platform == "win32":
        local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        primary = local_app / "AnYCLI" / "data"
        legacy = local_app / "CojamCLI" / "data"
        return primary if (_path_exists(primary) or not _path_exists(legacy)) else legacy
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    primary = xdg_data / "any-cli" / "data"
    legacy = xdg_data / "cojam-cli" / "data"
    return primary if (_path_exists(primary) or not _path_exists(legacy)) else legacy


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

    directory = Path(os.environ.get("ROUNDTABLE_LOG_DIR") or data_directory()).resolve()
    log = directory / "cli-server.log"
    env = dict(os.environ, ROUNDTABLE_LOG_DIR=str(directory), ROUNDTABLE_OWNER_LIFECYCLE="1")
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with log.open("ab") as stream:
            child = subprocess.Popen([sys.executable, "-m", "bridge.cli", "--port", str(port), "serve"],
                                     cwd=Path(__file__).resolve().parents[1], stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=stream, env=env, **options)
        ready = False
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                ready = server_ready(port)
                if ready:
                    Thread(target=child.wait, daemon=True).start()
                    return
                if child.poll() is not None:
                    break
                time.sleep(0.2)
        finally:
            if not ready and child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
    except (OSError, subprocess.SubprocessError) as error:
        raise cli.CliError(f"无法启动 AnY 后台（{error}）。启动日志：{log}") from error
    raise cli.CliError(f"无法启动 AnY 后台。启动日志：{log}")


if __name__ == "__main__":
    # Existing website installations still use this module as their entry point.
    raise SystemExit(cli.main())
