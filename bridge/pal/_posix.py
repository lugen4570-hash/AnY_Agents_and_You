"""POSIX (macOS / Linux) implementation for the Cojam Platform Abstraction Layer."""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ._shared import common_dot_dirs, find_command_with_dirs

logger = logging.getLogger(__name__)


def platform_command_dirs(home: str) -> list[str]:
    return common_dot_dirs(home)


def find_command_path(name: str, extra_paths: Sequence[str] | None = None) -> str | None:
    return find_command_with_dirs(name, platform_command_dirs, extra_paths)


def tailscale_command_path(
    which: Callable[[str], str | None] = shutil.which,
    isfile: Callable[[str], bool] = os.path.isfile,
    *,
    windows: bool | None = None,
) -> str | None:
    if windows:
        from ._win32 import tailscale_command_path as win_tailscale

        return win_tailscale(which=which, isfile=isfile, windows=True)
    return which("tailscale")


def subprocess_kwargs() -> dict[str, Any]:
    return {}


def installed_app_names(ttl: float = 30.0) -> frozenset[str]:
    del ttl
    return frozenset()


def resolve_command(
    name: str,
    find_fn: Callable[[str], str | None] | None = None,
) -> list[str] | None:
    finder = find_command_path if find_fn is None else find_fn
    path = finder(name)
    return [path] if path else None


def kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    try:
        proc.kill()
    except OSError as error:
        logger.debug("kill_process_tree: proc.kill failed for pid=%s: %s", getattr(proc, "pid", None), error)


def start_menu_dirs() -> list[str]:
    return []


def resolve_shortcut_target(path: str, modified_ns: int, size: int) -> str:
    del path, modified_ns, size
    return ""


def shell_join(argv: Sequence[str]) -> str:
    return shlex.join([str(v) for v in argv])


def cli_shell_command(executable: str, script: str) -> str:
    return shlex.join([executable, script])


def codex_platform_args() -> list[str]:
    return []


def socket_reuse_allowed() -> bool:
    return True


def apply_exclusive_socket(sock: socket.socket) -> None:
    del sock


def can_install_desktop_update(
    frozen: bool | None = None,
    executable: str | None = None,
    *,
    platform: str | None = None,
) -> bool:
    if platform == "win32":
        from ._win32 import can_install_desktop_update as win_can_install

        return win_can_install(frozen=frozen, executable=executable, platform=platform)
    del frozen, executable
    return False


def launch_hidden_powershell(
    encoded_command: str,
    env: Mapping[str, str],
    popen: Callable[..., Any] = subprocess.Popen,
) -> subprocess.Popen[Any]:
    del encoded_command, env, popen
    raise OSError("Windows PowerShell updater is unavailable on POSIX")


def prepend_member_gui_paths() -> None:
    if sys.platform != "darwin":
        return
    paths = [
        str(Path.home() / ".local/bin"),
        str(Path.home() / ".npm-global/bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    os.environ["PATH"] = os.pathsep.join([p for p in paths if os.path.isdir(p)] + [os.environ.get("PATH", "")])
