"""Independent update checker and installer for AnY CLI."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

from .version import CLI_VERSION

DEFAULT_BASE = "https://lugen4570-hash.github.io/AnY_Agents_and_You/"
MANIFEST_PATH = "cli/current.json"
MAX_MANIFEST = 65536
MAX_BUNDLE = 30 * 1024 * 1024
_SAFE_SUBDIR_RE = re.compile(r"release-[0-9a-f]{12}-")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any) -> None:
        return None


def base_url() -> str:
    """Return the trusted CLI distribution base URL (or localhost test server)."""
    override = os.environ.get("ANY_CLI_TEST_SOURCE", "")
    if re.fullmatch(r"http://127\.0\.0\.1:[0-9]+/", override):
        return override
    return DEFAULT_BASE


def parse_version(value: Any) -> tuple[int, int, int]:
    """Parse strict X.Y.Z semantic version tuples."""
    text = str(value or "").strip()
    if not re.fullmatch(r"(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})", text):
        raise ValueError("CLI 版本信息格式不正确")
    parts = text.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _open(url: str) -> Any:
    return urllib.request.build_opener(_NoRedirect).open(url, timeout=30)


def _download_bytes(url: str, limit: int) -> bytes:
    with _open(url) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("CLI 更新文件超出预期大小")
    return data


def detect_installation(package_file: str | Path | None = None) -> dict[str, Any]:
    """Inspect whether the active CLI is running from a managed AnYCLI generation or source."""
    bridge_dir = Path(package_file or __file__).resolve().parent
    source_dir = bridge_dir.parent
    generation = source_dir.parent
    complete = generation / ".complete"
    if source_dir.name == "AnY-CLI" and _SAFE_SUBDIR_RE.match(generation.name) and complete.is_file():
        root = generation.parent
        launcher = root / ("any.cmd" if sys.platform == "win32" else "any")
        digest = complete.read_text(encoding="utf-8", errors="replace").strip().lower()
        return {
            "mode": "managed",
            "can_install": True,
            "root": root,
            "generation": generation,
            "source_dir": source_dir,
            "launcher": launcher,
            "digest": digest,
        }
    return {
        "mode": "source",
        "can_install": False,
        "root": source_dir,
        "generation": None,
        "source_dir": source_dir,
        "launcher": None,
        "digest": "",
    }


def parse_manifest(data: Any, *, base: str | None = None) -> dict[str, Any]:
    """Validate cli/current.json payload against the trusted origin."""
    if not isinstance(data, dict):
        raise ValueError("CLI 更新清单格式无效")
    app = data.get("app")
    if app is not None and app != "AnY-CLI":
        raise ValueError("CLI 更新清单不属于 AnY-CLI")
    commit = str(data.get("commit") or "").lower()
    sha256 = str(data.get("sha256") or "").lower()
    size = data.get("size")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or not re.fullmatch(r"[0-9a-f]{64}", sha256)
        or type(size) is not int
        or not 0 < size <= MAX_BUNDLE
    ):
        raise ValueError("CLI 更新清单校验信息无效")

    raw_version = str(data.get("version") or "").strip()
    if raw_version:
        parse_version(raw_version)

    effective_base = base or base_url()
    expected_url = f"{effective_base}cli/any-cli-{commit}.tar.gz"
    raw_url = str(data.get("url") or "").strip()
    if raw_url and raw_url != expected_url:
        raise ValueError("CLI 更新包下载地址无效")

    notes = str(data.get("notes") or "").strip()[:1000]
    return {
        "version": raw_version,
        "commit": commit,
        "sha256": sha256,
        "size": size,
        "url": expected_url,
        "notes": notes,
    }


def check(package_file: str | Path | None = None) -> dict[str, Any]:
    """Fetch cli/current.json and determine whether a newer CLI release is available."""
    install_info = detect_installation(package_file)
    effective_base = base_url()
    try:
        raw = _download_bytes(effective_base + MANIFEST_PATH, MAX_MANIFEST)
        release = parse_manifest(json.loads(raw), base=effective_base)
        remote_ver = release["version"]
        if remote_ver:
            cur_t = parse_version(CLI_VERSION)
            rem_t = parse_version(remote_ver)
            if rem_t > cur_t:
                available = True
            elif rem_t == cur_t and install_info["mode"] == "managed":
                available = bool(install_info["digest"] and install_info["digest"] != release["sha256"])
            else:
                available = False
        else:
            available = install_info["mode"] == "managed" and install_info["digest"] != release["sha256"]

        return {
            "state": "available" if available else "current",
            "channel": "cli",
            "current": CLI_VERSION,
            "latest": remote_ver or CLI_VERSION,
            "commit": release["commit"],
            "sha256": release["sha256"],
            "size": release["size"],
            "url": release["url"],
            "notes": release["notes"],
            "mode": install_info["mode"],
            "can_install": install_info["can_install"],
            "root": str(install_info["root"]),
            "launcher": str(install_info["launcher"] or ""),
            "release": release if available else None,
            "error": "",
        }
    except Exception as error:
        return {
            "state": "error",
            "channel": "cli",
            "current": CLI_VERSION,
            "latest": "",
            "commit": "",
            "sha256": "",
            "size": 0,
            "url": "",
            "notes": "",
            "mode": install_info["mode"],
            "can_install": install_info["can_install"],
            "root": str(install_info["root"]),
            "launcher": str(install_info["launcher"] or ""),
            "release": None,
            "error": str(error) or "无法检查 CLI 更新，请检查网络后重试",
        }


def _python_in(generation: Path) -> Path:
    return generation / ("venv/Scripts/python.exe" if sys.platform == "win32" else "venv/bin/python")


def _atomic_text(path: Path, content: str, *, executable: bool = False) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(content)
    try:
        if executable:
            tmp.chmod(0o755)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _write_launcher(root: Path, interpreter: Path) -> Path:
    if sys.platform == "win32":
        launcher = root / "any.cmd"
        rel = str(interpreter.relative_to(root))
        _atomic_text(launcher, f'@echo off\n"%~dp0{rel}" -I -X utf8 -m bridge.cli %*\n')
    else:
        launcher = root / "any"
        _atomic_text(
            launcher,
            f'#!/bin/sh\nexec {shlex.quote(str(interpreter))} -I -X utf8 -m bridge.cli "$@"\n',
            executable=True,
        )
    return launcher


def _extract_source(bundle: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            if (
                not path.parts
                or path.parts[0] != "AnY-CLI"
                or ".." in path.parts
                or "\\" in entry.name
                or ":" in entry.name
                or not (entry.isdir() or entry.isfile())
            ):
                raise ValueError("CLI 更新包包含不安全的路径")
            target = destination.joinpath(*path.parts)
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(entry)
                if extracted is None:
                    raise ValueError("CLI 更新包文件读取失败")
                with extracted as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)


def _find_uv(root: Path) -> str | None:
    if found := shutil.which("uv"):
        return found
    if sys.platform == "win32":
        candidates = (root / "bootstrap" / "uv.exe", Path.home() / ".local" / "bin" / "uv.exe")
    else:
        xdg = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        candidates = (xdg / "any-cli" / "bootstrap" / "uv", Path.home() / ".local" / "bin" / "uv")
    return next((str(c) for c in candidates if c.is_file()), None)


def _base_python() -> str:
    candidate = getattr(sys, "_base_executable", "") or sys.executable
    return candidate if candidate and Path(candidate).is_file() else sys.executable


def _run_quiet(cmd: list[str], *, cwd: Path | None = None) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        detail = (res.stderr or res.stdout or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"命令执行失败（退出码 {res.returncode}）")


def _setup_venv(root: Path, generation: Path, interpreter: Path) -> None:
    venv_dir = generation / "venv"
    source_dir = generation / "AnY-CLI"
    base_py = _base_python()
    try:
        _run_quiet([base_py, "-m", "venv", str(venv_dir)])
        _run_quiet([str(interpreter), "-m", "pip", "--disable-pip-version-check", "install", "-e", ".[cli]"], cwd=source_dir)
    except Exception:
        uv_bin = _find_uv(root)
        if not uv_bin:
            raise
        shutil.rmtree(venv_dir, ignore_errors=True)
        _run_quiet([uv_bin, "venv", "--python", base_py, str(venv_dir)])
        _run_quiet([uv_bin, "pip", "install", "--python", str(interpreter), "-e", ".[cli]"], cwd=source_dir)


def install_update(release: dict[str, Any], package_file: str | Path | None = None) -> dict[str, Any]:
    """Download, verify, install a new CLI generation, and switch the CLI launcher."""
    install_info = detect_installation(package_file)
    if not install_info["can_install"]:
        raise ValueError("当前不是通过 AnY CLI 安装脚本部署的环境，请在源码目录执行 git pull 更新。")

    root: Path = install_info["root"]
    current_gen: Path | None = install_info["generation"]
    bundle = _download_bytes(release["url"], release["size"])
    if len(bundle) != release["size"] or hashlib.sha256(bundle).hexdigest() != release["sha256"]:
        raise ValueError("CLI 更新包校验未通过，已放弃安装")

    generation = Path(tempfile.mkdtemp(prefix=f"release-{release['commit'][:12]}-", dir=root))
    interpreter = _python_in(generation)
    try:
        _extract_source(bundle, generation)
        _setup_venv(root, generation, interpreter)
        _atomic_text(generation / ".complete", release["sha256"])
        launcher = _write_launcher(root, interpreter)
    except BaseException:
        shutil.rmtree(generation, ignore_errors=True)
        raise

    # Prune inactive older generations while keeping the currently running process's directory intact.
    for stale in root.glob("release-*"):
        if stale.is_dir() and stale != generation and stale != current_gen:
            shutil.rmtree(stale, ignore_errors=True)

    return {
        "state": "installed",
        "channel": "cli",
        "current": CLI_VERSION,
        "installed": release.get("version") or CLI_VERSION,
        "commit": release["commit"],
        "notes": release.get("notes") or "",
        "launcher": str(launcher),
        "generation": str(generation),
    }
