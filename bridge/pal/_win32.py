"""Windows implementation for the Cojam Platform Abstraction Layer."""
from __future__ import annotations

import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict, cast

from ._shared import common_dot_dirs, find_command_with_dirs

logger = logging.getLogger(__name__)

CODEX_SANDBOX_OVERRIDE = 'windows.sandbox="unelevated"'
SHORTCUT_CACHE_MAX = 128


class _AppNamesCache(TypedDict):
    at: float
    names: frozenset[str]


_APP_NAMES: _AppNamesCache = {"at": 0.0, "names": frozenset()}
_APP_LOCK = threading.Lock()
_shortcut_targets: dict[tuple[str, int, int], str] = {}
_shortcut_targets_lock = threading.Lock()


def subprocess_kwargs() -> dict[str, Any]:
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}


def _read_npm_prefix_dirs(home: str) -> list[str]:
    """Discover custom npm global prefix directories (e.g. D:\\npm\\global) from env or .npmrc."""
    candidates: list[str] = []
    for env_key in ("NPM_CONFIG_PREFIX", "npm_config_prefix"):
        val = (os.environ.get(env_key) or "").strip().strip("\"'")
        if val:
            candidates.append(val)
    npmrc_files = [
        os.path.join(home, ".npmrc"),
        os.path.join(os.environ.get("APPDATA", ""), "npm", "etc", "npmrc"),
    ]
    for cfg in npmrc_files:
        if not cfg or not os.path.isfile(cfg):
            continue
        try:
            with open(cfg, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", ";")):
                        continue
                    match = re.match(r"^prefix\s*=\s*(.+)$", stripped, re.IGNORECASE)
                    if match:
                        val = match.group(1).strip().strip("\"'")
                        if val:
                            candidates.append(os.path.expandvars(os.path.expanduser(val)))
        except OSError:
            continue
    seen: set[str] = set()
    out: list[str] = []
    for path in candidates:
        norm = os.path.normcase(os.path.normpath(path))
        if norm not in seen and os.path.isdir(path):
            seen.add(norm)
            out.append(path)
    return out


def platform_command_dirs(home: str) -> list[str]:
    paths = common_dot_dirs(home)
    try:
        import winreg

        for root, key in (
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(root, key) as handle:
                    paths.append(os.path.expandvars(winreg.QueryValueEx(handle, "Path")[0]))
            except OSError:
                # Expected when user Environment or Path value does not exist.
                continue
    except ImportError:
        # Expected: winreg is unavailable on non-Windows Python.
        pass
    local_app = os.environ.get("LOCALAPPDATA", "")
    paths.extend([
        *_read_npm_prefix_dirs(home),
        os.path.join(home, ".grok", "bin"),
        os.path.join(home, "scoop", "shims"),
        os.path.join(home, ".qoder", "bin", "qodercli"),
        os.path.join(home, ".qoder-cn", "bin", "qoderclicn"),
        os.path.join(home, ".qoder-cn", "bin"),
        os.path.join(os.environ.get("APPDATA", ""), "npm"),
        os.path.join(local_app, "pnpm"),
        os.path.join(local_app, "Microsoft", "WinGet", "Links"),
        os.path.join(local_app, "cursor-agent"),
    ])
    return paths


def find_command_path(name: str, extra_paths: Sequence[str] | None = None) -> str | None:
    return find_command_with_dirs(name, platform_command_dirs, extra_paths)


def tailscale_command_path(
    which: Callable[[str], str | None] = shutil.which,
    isfile: Callable[[str], bool] = os.path.isfile,
    *,
    windows: bool | None = None,
) -> str | None:
    exe = which("tailscale")
    if exe:
        return exe
    if windows is False:
        return None
    candidate = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")
    return candidate if isfile(candidate) else None


def installed_app_names(ttl: float = 30.0) -> frozenset[str]:
    now = time.time()
    with _APP_LOCK:
        if _APP_NAMES["names"] and now - float(_APP_NAMES["at"]) < ttl:
            return _APP_NAMES["names"]
    names: set[str] = set()
    try:
        import winreg

        roots = (
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        )
        for root, sub in roots:
            try:
                with winreg.OpenKey(root, sub) as key:
                    for idx in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, idx)) as child:
                                val, _ = winreg.QueryValueEx(child, "DisplayName")
                                if isinstance(val, str) and val.strip():
                                    names.add(val.strip().lower())
                        except OSError:
                            # Expected when an uninstall key lacks DisplayName.
                            continue
            except OSError:
                # Expected when registry hive or WOW6432Node subkey is absent.
                continue
    except ImportError:
        # Expected: winreg is unavailable outside Windows.
        pass
    frozen = frozenset(names)
    with _APP_LOCK:
        _APP_NAMES["at"] = now
        _APP_NAMES["names"] = frozen
    return frozen


_NODE_SCRIPT_EXTS = (".js", ".cjs", ".mjs")
_CURSOR_VERSION_RE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})(?:-(\d{2})-(\d{2})-(\d{2}))?-[a-f0-9]+$", re.IGNORECASE)
_SHIM_TARGET_RE = re.compile(r'"(?:%dp0%|%~dp0|%SCRIPT_DIR%)\\([^"]+)"', re.IGNORECASE)


def _find_node_binary(shim_dir: str) -> str | None:
    node = os.path.join(shim_dir, "node.exe")
    return node if os.path.isfile(node) else shutil.which("node")


def _is_node_script(path: str) -> bool:
    if path.lower().endswith(_NODE_SCRIPT_EXTS):
        return True
    try:
        with open(path, "rb") as handle:
            first_line = handle.readline(128).decode("utf-8", errors="replace").lower()
    except OSError:
        return False
    return first_line.startswith("#!") and "node" in first_line


def _has_staged_cursor_update(versions_dir: str) -> bool:
    pending_dir = os.path.join(versions_dir, "pending-launchers")
    try:
        if os.path.isdir(pending_dir) and any(n.endswith(".pending") for n in os.listdir(pending_dir)):
            return True
        return any(n.endswith(".new") for n in os.listdir(versions_dir))
    except OSError:
        return False


def _unwrap_ps1_node_launcher(ps1_path: str) -> list[str] | None:
    """Resolve PowerShell wrappers like Cursor's cursor-agent.ps1 directly to [node.exe, index.js]."""
    base_dir = os.path.dirname(ps1_path)
    versions_dir = os.path.join(base_dir, "versions")
    if os.path.isdir(versions_dir) and _has_staged_cursor_update(versions_dir):
        return None
    direct_node = os.path.join(base_dir, "node.exe")
    direct_js = os.path.join(base_dir, "index.js")
    if os.path.isfile(direct_node) and os.path.isfile(direct_js):
        return [direct_node, direct_js]
    if not os.path.isdir(versions_dir):
        return None
    try:
        entries = os.listdir(versions_dir)
    except OSError:
        return None
    best_key: tuple[int, ...] = ()
    best_cmd: list[str] | None = None
    for entry in entries:
        match = _CURSOR_VERSION_RE.match(entry)
        if not match:
            continue
        candidate_dir = os.path.join(versions_dir, entry)
        node_bin = os.path.join(candidate_dir, "node.exe")
        index_js = os.path.join(candidate_dir, "index.js")
        if not (os.path.isfile(node_bin) and os.path.isfile(index_js)):
            continue
        ver_key = tuple(int(part or 0) for part in match.groups())
        if ver_key > best_key:
            best_key = ver_key
            best_cmd = [node_bin, index_js]
    return best_cmd


def _unwrap_batch_shim(shim_path: str) -> list[str]:
    try:
        with open(shim_path, encoding="utf-8", errors="replace") as handle:
            txt = handle.read()
    except OSError as error:
        logger.debug("resolve_command failed reading batch shim %s: %s", shim_path, error)
        return [shim_path]
    shim_dir = os.path.dirname(shim_path)
    for match in _SHIM_TARGET_RE.finditer(txt):
        target = os.path.normpath(os.path.join(shim_dir, match.group(1)))
        if not os.path.isfile(target):
            continue
        lower = target.lower()
        if lower.endswith(".exe"):
            return [target]
        if lower.endswith(".ps1"):
            unwrapped = _unwrap_ps1_node_launcher(target)
            if unwrapped:
                return unwrapped
            continue
        if _is_node_script(target):
            node_bin = _find_node_binary(shim_dir)
            if node_bin:
                return [node_bin, target]
    return [shim_path]


def resolve_command(
    name: str,
    find_fn: Callable[[str], str | None] | None = None,
) -> list[str] | None:
    finder = find_command_path if find_fn is None else find_fn
    p = finder(name)
    if not p:
        return None
    lower = p.lower()
    if lower.endswith(".ps1"):
        return _unwrap_ps1_node_launcher(p) or [p]
    if lower.endswith((".cmd", ".bat")):
        return _unwrap_batch_shim(p)
    return [p]


def kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            timeout=30,
            check=False,
            **subprocess_kwargs(),
        )
        if result.returncode == 0:
            return
        logger.debug("taskkill returned %s for pid=%s, falling back to proc.kill()", result.returncode, proc.pid)
    except (OSError, subprocess.SubprocessError) as error:
        logger.debug("taskkill failed for pid=%s, falling back to proc.kill(): %s", getattr(proc, "pid", None), error)
    try:
        proc.kill()
    except OSError as kill_error:
        logger.debug("proc.kill fallback failed for pid=%s: %s", getattr(proc, "pid", None), kill_error)


def start_menu_dirs() -> list[str]:
    roots = [
        os.path.join(os.environ.get(key) or "", "Microsoft", "Windows", "Start Menu", "Programs")
        for key in ("APPDATA", "ProgramData")
    ]
    return [root for root in roots if root and os.path.isdir(root)]


def resolve_shortcut_target(path: str, modified_ns: int, size: int) -> str:
    key = (path, modified_ns, size)
    with _shortcut_targets_lock:
        if key in _shortcut_targets:
            return _shortcut_targets[key]
    quoted = path.replace("'", "''")
    script = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('" + quoted + "'); "
        "[Console]::Out.Write($s.TargetPath)"
    )
    exe = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    try:
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=4,
            check=False,
            **subprocess_kwargs(),
        )
        target = result.stdout.decode("utf-8", "replace").strip() if result.returncode == 0 else ""
        if target:
            with _shortcut_targets_lock:
                if len(_shortcut_targets) >= SHORTCUT_CACHE_MAX:
                    _shortcut_targets.clear()
                _shortcut_targets[key] = target
        return target
    except (OSError, subprocess.SubprocessError) as error:
        logger.debug("resolve_shortcut_target failed for %s: %s", path, error)
        return ""


def shell_join(argv: Sequence[str]) -> str:
    return "& " + " ".join("'" + str(value).replace("'", "''") + "'" for value in argv)


def cli_shell_command(executable: str, script: str) -> str:
    exe = executable.replace("\\", "/")
    scr = script.replace("\\", "/")
    return f'& "{exe}" "{scr}"'


def codex_platform_args() -> list[str]:
    return ["-c", CODEX_SANDBOX_OVERRIDE]


def socket_reuse_allowed() -> bool:
    return False


def apply_exclusive_socket(sock: socket.socket) -> None:
    option = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
    if option is not None:
        sock.setsockopt(socket.SOL_SOCKET, option, 1)


def can_install_desktop_update(
    frozen: bool | None = None,
    executable: str | None = None,
    *,
    platform: str | None = None,
) -> bool:
    plat = sys.platform if platform is None else platform
    is_frozen = getattr(sys, "frozen", False) if frozen is None else bool(frozen)
    if plat != "win32" or not is_frozen:
        return False
    core = Path(sys.executable if executable is None else executable).resolve()
    return core.name.lower() == "cojamcore.exe" and (core.parent / "Cojam.exe").is_file()


def launch_hidden_powershell(
    encoded_command: str,
    env: Mapping[str, str],
    popen: Callable[..., Any] = subprocess.Popen,
) -> subprocess.Popen[Any]:
    powershell = str(
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    return cast(
        subprocess.Popen[Any],
        popen(
            [powershell, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded_command],
            env=dict(env),
            close_fds=True,
            **subprocess_kwargs(),
        ),
    )


def prepend_member_gui_paths() -> None:
    return None
