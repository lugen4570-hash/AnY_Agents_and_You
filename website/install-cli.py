"""Install AnY CLI into an isolated Python environment and open the client."""
from __future__ import annotations

import argparse
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
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

BASE = "https://lugen4570-hash.github.io/AnY_Agents_and_You/"


def install_root():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AnYCLI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AnYCLI"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "any-cli"


def download(path, limit):
    with urllib.request.urlopen(BASE + path, timeout=40) as response:
        if not response.geturl().startswith(BASE):
            raise ValueError("下载服务返回了意外的地址。")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("下载文件超出预期大小。")
    return content


def source_manifest():
    data = json.loads(download("cli/current.json", 16384))
    if not isinstance(data, dict):
        raise ValueError("无法识别 CLI 发布清单。")
    commit = data.get("commit")
    digest = data.get("sha256")
    size = data.get("size")
    if (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(size) is not int or not 0 < size <= 30 * 1024 * 1024):
        raise ValueError("无法识别 CLI 发布清单。")
    return commit, digest, size


def extract_source(data, destination):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            if (not path.parts or path.parts[0] != "AnY-CLI" or ".." in path.parts
                    or "\\" in entry.name or ":" in entry.name or not (entry.isdir() or entry.isfile())):
                raise ValueError("CLI 安装文件包含意外的路径。")
            target = destination.joinpath(*path.parts)
            if entry.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(entry) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def python_in(generation):
    return generation / ("venv/Scripts/python.exe" if sys.platform == "win32" else "venv/bin/python")


def atomic_text(path, content, executable=False):
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        if executable:
            temporary.chmod(0o755)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_launcher(root, interpreter):
    if sys.platform == "win32":
        launcher = root / "any.cmd"
        executable = str(interpreter.relative_to(root))
        command = f'@echo off\n"%~dp0{executable}" -I -m bridge.cli %*\n'
        atomic_text(launcher, command)
    else:
        launcher = root / "any"
        command = f'#!/bin/sh\nexec {shlex.quote(str(interpreter))} -I -m bridge.cli "$@"\n'
        atomic_text(launcher, command, executable=True)
    return launcher


def _find_uv():
    found = shutil.which("uv")
    if found:
        return found
    if sys.platform == "win32":
        candidates = (install_root() / "bootstrap" / "uv.exe", Path.home() / ".local" / "bin" / "uv.exe")
    else:
        data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        candidates = (data / "any-cli" / "bootstrap" / "uv", Path.home() / ".local" / "bin" / "uv")
    return next((str(candidate) for candidate in candidates if candidate.is_file()), None)


def _setup_venv(generation, interpreter):
    venv_dir = generation / "venv"
    source_dir = generation / "AnY-CLI"
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        subprocess.run([str(interpreter), "-m", "pip", "--disable-pip-version-check", "install", "-e", ".[cli]"],
                       cwd=source_dir, check=True, stdout=sys.stderr)
    except subprocess.CalledProcessError:
        uv_bin = _find_uv()
        if not uv_bin:
            raise
        shutil.rmtree(venv_dir, ignore_errors=True)
        subprocess.run([uv_bin, "venv", "--python", sys.executable, str(venv_dir)], check=True)
        subprocess.run([uv_bin, "pip", "install", "--python", str(interpreter), "-e", ".[cli]"],
                       cwd=source_dir, check=True, stdout=sys.stderr)


def install(root):
    root.mkdir(parents=True, exist_ok=True)
    commit, digest, size = source_manifest()
    for ready in sorted(root.glob(f"release-{commit[:12]}-*/.complete")):
        interpreter = python_in(ready.parent)
        if interpreter.is_file() and ready.read_text(encoding="utf-8") == digest:
            return interpreter, write_launcher(root, interpreter)

    print("正在下载并安装 AnY CLI…", file=sys.stderr, flush=True)
    bundle = download(f"cli/any-cli-{commit}.tar.gz", size)
    if len(bundle) != size or hashlib.sha256(bundle).hexdigest() != digest:
        raise ValueError("CLI 安装文件的校验未通过，请重试。")
    generation = Path(tempfile.mkdtemp(prefix=f"release-{commit[:12]}-", dir=root))
    interpreter = python_in(generation)
    try:
        extract_source(bundle, generation)
        _setup_venv(generation, interpreter)
        atomic_text(generation / ".complete", digest)
    except BaseException:
        shutil.rmtree(generation, ignore_errors=True)
        raise
    return interpreter, write_launcher(root, interpreter)


def main(argv=None):
    if sys.version_info < (3, 11):
        print("AnY CLI 需要 Python 3.11 或更新版本。", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-only", action="store_true", help="只安装，安装后不打开聊天界面")
    parser.add_argument("--print-launcher", action="store_true", help="安装并输出启动脚本路径")
    args = parser.parse_args(argv)
    try:
        root = Path(os.environ.get("ANY_CLI_INSTALL_DIR") or os.environ.get("COJAM_CLI_INSTALL_DIR") or install_root()).expanduser().resolve()
        interpreter, launcher = install(root)
        if args.print_launcher:
            print(launcher, flush=True)
            return 0
        print(f"AnY CLI 已就绪。下次也可运行：{launcher}", flush=True)
        if not args.install_only:
            return subprocess.call([str(interpreter), "-I", "-m", "bridge.cli"])
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"AnY CLI 安装失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
