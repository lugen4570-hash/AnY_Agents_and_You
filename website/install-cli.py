"""Install Cojam CLI into an isolated Python environment and open the client."""
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

BASE = "https://lugen4570-hash.github.io/Cojam/"


def install_root():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CojamCLI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CojamCLI"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "cojam-cli"


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
            if (not path.parts or path.parts[0] != "Cojam-CLI" or ".." in path.parts
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
        launcher = root / "cojam.cmd"
        executable = str(interpreter.relative_to(root))
        atomic_text(launcher, f'@echo off\n"%~dp0{executable}" -m bridge.cli_autostart %*\n')
    else:
        launcher = root / "cojam"
        atomic_text(launcher, f'#!/bin/sh\nexec {shlex.quote(str(interpreter))} -m bridge.cli_autostart "$@"\n', executable=True)
    return launcher


def install(root):
    root.mkdir(parents=True, exist_ok=True)
    commit, digest, size = source_manifest()
    for ready in sorted(root.glob(f"release-{commit[:12]}-*/.complete")):
        interpreter = python_in(ready.parent)
        if interpreter.is_file() and ready.read_text(encoding="utf-8") == digest:
            return interpreter, write_launcher(root, interpreter)

    print("正在下载并安装 Cojam CLI…", flush=True)
    bundle = download(f"cli/cojam-cli-{commit}.tar.gz", size)
    if len(bundle) != size or hashlib.sha256(bundle).hexdigest() != digest:
        raise ValueError("CLI 安装文件的校验未通过，请重试。")
    generation = Path(tempfile.mkdtemp(prefix=f"release-{commit[:12]}-", dir=root))
    extract_source(bundle, generation)
    interpreter = python_in(generation)
    subprocess.run([sys.executable, "-m", "venv", str(generation / "venv")], check=True)
    subprocess.run([str(interpreter), "-m", "pip", "--disable-pip-version-check", "install", "-e", ".[cli]"],
                   cwd=generation / "Cojam-CLI", check=True)
    atomic_text(generation / ".complete", digest)
    return interpreter, write_launcher(root, interpreter)


def main(argv=None):
    if sys.version_info < (3, 11):
        print("Cojam CLI 需要 Python 3.11 或更新版本。", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-only", action="store_true", help="只安装，安装后不打开聊天界面")
    args = parser.parse_args(argv)
    try:
        root = Path(os.environ.get("COJAM_CLI_INSTALL_DIR", install_root())).expanduser().resolve()
        interpreter, launcher = install(root)
        print(f"Cojam CLI 已就绪。下次也可运行：{launcher}", flush=True)
        if not args.install_only:
            return subprocess.call([str(interpreter), "-m", "bridge.cli_autostart"])
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"Cojam CLI 安装失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
