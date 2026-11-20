"""Platform Abstraction Layer (PAL) dispatching Windows and POSIX implementations."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

IS_WINDOWS: bool = os.name == "nt"
IS_MACOS: bool = sys.platform == "darwin"

if IS_WINDOWS:
    from . import _win32 as _impl
else:
    from . import _posix as _impl  # type: ignore[no-redef]


def is_macos(platform: str | None = None) -> bool:
    return (sys.platform if platform is None else platform) == "darwin"


def subprocess_kwargs() -> dict[str, Any]:
    return _impl.subprocess_kwargs()


def find_command_path(name: str, extra_paths: Sequence[str] | None = None) -> str | None:
    return _impl.find_command_path(name, extra_paths)


def tailscale_command_path(
    which: Callable[[str], str | None] = shutil.which,
    isfile: Callable[[str], bool] = os.path.isfile,
    *,
    windows: bool | None = None,
) -> str | None:
    return _impl.tailscale_command_path(which=which, isfile=isfile, windows=windows)


def installed_app_names(ttl: float = 30.0) -> frozenset[str]:
    return _impl.installed_app_names(ttl)


def resolve_command(
    name: str,
    find_fn: Callable[[str], str | None] | None = None,
) -> list[str] | None:
    return _impl.resolve_command(name, find_fn=find_fn)


def kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    _impl.kill_process_tree(proc)


def start_menu_dirs() -> list[str]:
    return _impl.start_menu_dirs()


def resolve_shortcut_target(path: str, modified_ns: int, size: int) -> str:
    return _impl.resolve_shortcut_target(path, modified_ns, size)


def shell_join(argv: Sequence[str]) -> str:
    return _impl.shell_join(argv)


def cli_shell_command(executable: str, script: str) -> str:
    return _impl.cli_shell_command(executable, script)


def codex_platform_args() -> list[str]:
    return _impl.codex_platform_args()


def socket_reuse_allowed() -> bool:
    return _impl.socket_reuse_allowed()


def apply_exclusive_socket(sock: socket.socket) -> None:
    _impl.apply_exclusive_socket(sock)


def can_install_desktop_update(
    frozen: bool | None = None,
    executable: str | None = None,
    *,
    platform: str | None = None,
) -> bool:
    return _impl.can_install_desktop_update(frozen=frozen, executable=executable, platform=platform)


def launch_hidden_powershell(
    encoded_command: str,
    env: Mapping[str, str],
    popen: Callable[..., Any] = subprocess.Popen,
) -> subprocess.Popen[Any]:
    return _impl.launch_hidden_powershell(encoded_command, env, popen=popen)


def prepend_member_gui_paths() -> None:
    _impl.prepend_member_gui_paths()


__all__ = [
    "IS_MACOS",
    "IS_WINDOWS",
    "apply_exclusive_socket",
    "can_install_desktop_update",
    "cli_shell_command",
    "codex_platform_args",
    "find_command_path",
    "installed_app_names",
    "is_macos",
    "kill_process_tree",
    "launch_hidden_powershell",
    "prepend_member_gui_paths",
    "resolve_command",
    "resolve_shortcut_target",
    "shell_join",
    "socket_reuse_allowed",
    "start_menu_dirs",
    "subprocess_kwargs",
    "tailscale_command_path",
]
