"""Check and verify platform updates, with in-app installation on Windows."""
import hashlib
import base64
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
import urllib.request

from . import pal
from .common import get_logger
from .version import VERSION

logger = get_logger(__name__)

MANIFEST = 'https://lugen4570-hash.github.io/AnY_Agents_and_You/update.json'
DOWNLOAD_ROOT = 'https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/'
MACOS_MANIFEST = MANIFEST.replace('/update.json', '/macos-update.json')
MAX_INSTALLER = 100 * 1024 * 1024
CHUNK_SIZE = 128 * 1024
RANGE_THRESHOLD = 1024 * 1024
RANGE_WORKERS = 4
RANGE_RETRIES = 3
_CONTENT_RANGE_RE = re.compile(r'^bytes\s+(\d+)-(\d+)/(\d+)$')
LOCK = threading.RLock()
STATE: dict[str, Any] = {'state': 'idle', 'current': VERSION}
RELEASE: dict[str, Any] | None = None

# Run out of process: the backend executable must exit before Inno Setup can
# replace it. All variable values are passed through environment variables.
_INSTALL_HELPER = r'''
$ErrorActionPreference = 'Stop'
function ReportFailure($message) {
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show($message, 'AnY 更新') | Out-Null
}
try {
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class AnYUpdateWindows {
  delegate bool EnumWindowsProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc f, IntPtr p);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public static void Close(int id) {
    EnumWindows(delegate(IntPtr h, IntPtr p) {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == (uint)id) {
        StringBuilder title = new StringBuilder(256); GetWindowText(h, title, title.Capacity);
        if (title.ToString() == "AnY" || title.ToString() == "合拍 Cojam") PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
      }
      return true;
    }, IntPtr.Zero);
  }
}
'@
  $target = [int]$env:ANY_UPDATE_CORE_PID
  $deadline = (Get-Date).AddSeconds(45)
  $shellPath = Join-Path $env:ANY_UPDATE_DIRECTORY 'AnY.exe'
  while ($true) {
    $shells = @(Get-Process -Name 'AnY' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $shellPath })
    $cores = @(Get-Process -Name 'AnYCore' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $env:ANY_UPDATE_CORE_EXECUTABLE })
    $core = Get-Process -Id $target -ErrorAction SilentlyContinue
    if (-not $core -and $cores.Count -eq 0 -and $shells.Count -eq 0) { break }
    foreach ($shell in $shells) { [AnYUpdateWindows]::Close($shell.Id) }
    if ((Get-Date) -ge $deadline) { throw 'AnY 未能安全退出，请关闭 AnY 后手动运行已下载的安装程序。' }
    Start-Sleep -Milliseconds 250
  }
  $arguments = @('/SP-', '/SILENT', '/NORESTART', '/CLOSEAPPLICATIONS',
    '/NOFORCECLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS',
    ('/DIR="' + $env:ANY_UPDATE_DIRECTORY + '"'))
  $setup = Start-Process -FilePath $env:ANY_UPDATE_INSTALLER -ArgumentList $arguments -Wait -PassThru
  if ($setup.ExitCode -ne 0) { throw '更新安装未完成，请手动运行已下载的安装程序。' }
  Start-Process -FilePath $shellPath -WorkingDirectory $env:ANY_UPDATE_DIRECTORY | Out-Null
} catch { ReportFailure $_.Exception.Message; exit 1 }
'''


def version(value):
    text = str(value or '')
    if not re.fullmatch(r'(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})', text):
        raise ValueError('版本信息格式不正确')
    return tuple(map(int, text.split('.')))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def _open(url, headers=None):
    target: Any = urllib.request.Request(url, headers=headers) if headers else url
    return urllib.request.build_opener(NoRedirect).open(target, timeout=20)


def can_install():
    return pal.can_install_desktop_update(
        platform=sys.platform,
        frozen=getattr(sys, 'frozen', False),
        executable=sys.executable,
    )


def parse_manifest(data, *, macos=False, macos_arch=None):
    if not isinstance(data, dict) or data.get('app') != 'AnY':
        raise ValueError('更新信息不完整')
    v = str(data.get('version') or '')
    version(v)
    url = str(data.get('url') or '')
    if macos_arch is not None:
        if not macos or macos_arch not in ('arm64', 'x86_64'):
            raise ValueError('不支持的 macOS 芯片类型')
        filename = f'AnY-macOS-{macos_arch}.dmg'
    else:
        filename = f'AnY-{v}-macOS-Python.zip' if macos else f'AnY-Setup-{v}.exe'
    if url != DOWNLOAD_ROOT + filename:
        raise ValueError('安装包地址无效')
    sha = str(data.get('sha256') or '').lower()
    size = data.get('size')
    if not re.fullmatch(r'[0-9a-f]{64}', sha) or type(size) is not int or not 0 < size <= MAX_INSTALLER:
        raise ValueError('安装包校验信息无效')
    return {'version': v, 'url': url, 'sha256': sha, 'size': size, 'macos': macos, 'macos_arch': macos_arch,
            'notes': str(data.get('notes') or '')[:1000]}


def check():
    global RELEASE
    macos = pal.is_macos(sys.platform)
    with LOCK:
        if STATE['state'] in ('downloading', 'installing'):
            return status()
    try:
        macos_arch = platform.machine() if macos and getattr(sys, 'frozen', False) else None
        manifest = MACOS_MANIFEST if macos else MANIFEST
        if macos_arch:
            if macos_arch not in ('arm64', 'x86_64'):
                raise ValueError('不支持的 macOS 芯片类型')
            manifest = MACOS_MANIFEST.replace('.json', f'-{macos_arch}.json')
        with _open(manifest) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('更新信息过大')
        release = parse_manifest(json.loads(raw), macos=macos, macos_arch=macos_arch)
        available = version(release['version']) > version(VERSION)
        with LOCK:
            RELEASE = release if available else None
            STATE.update(state='available' if available else 'current', current=VERSION,
                         latest=release['version'], notes=release['notes'], error='', path='', downloaded=0,
                         speed=0, size=release['size'], macos_dmg=bool(macos_arch))
            return status()
    except Exception:
        with LOCK:
            RELEASE = None
            STATE.update(state='error', current=VERSION, error='无法检查更新，请检查网络后重试', path='', speed=0)
            return dict(STATE)


def status():
    with LOCK:
        return dict(STATE, can_install=can_install(), macos=pal.is_macos(sys.platform))


def start_download(directory=None, auto_install=False, busy=None, stop_backend=None):
    with LOCK:
        if STATE['state'] in ('downloading', 'installing'):
            return status()
        if not RELEASE:
            raise ValueError('请先检查可用更新')
        if auto_install and not can_install():
            raise ValueError('应用内安装仅支持已安装的 Windows 桌面版。')
        release = dict(RELEASE)
        STATE.update(state='downloading', downloaded=0, speed=0, path='', error='')
    threading.Thread(target=_download, args=(release, directory, auto_install, busy, stop_backend), daemon=True).start()
    return status()


def start_install(stop_backend=None):
    """Launch the verified installer for this installation, without force closing apps."""
    if not can_install():
        raise ValueError('应用内安装仅支持 Windows 桌面版，请手动运行安装程序。')
    if stop_backend is None:
        raise ValueError('无法安全退出当前后台，请手动运行安装程序。')
    core = Path(sys.executable).resolve()
    with LOCK:
        if STATE.get('state') != 'downloaded' or not RELEASE:
            raise ValueError('请先下载并校验更新。')
        release = dict(RELEASE)
        installer = Path(STATE.get('path') or '')
        try:
            if not installer.is_file() or installer.stat().st_size != release['size']:
                raise ValueError('安装包已丢失或被更改，请重新下载。')
            digest = hashlib.sha256()
            with installer.open('rb') as stream:
                for chunk in iter(lambda: stream.read(128 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != release['sha256']:
                raise ValueError('安装包校验失败，请重新下载。')
            environment = dict(os.environ, ANY_UPDATE_CORE_PID=str(os.getpid()), ANY_UPDATE_CORE_EXECUTABLE=str(core),
                               ANY_UPDATE_INSTALLER=str(installer), ANY_UPDATE_DIRECTORY=str(core.parent))
            encoded = base64.b64encode(_INSTALL_HELPER.encode('utf-16le')).decode('ascii')
            proc = pal.launch_hidden_powershell(encoded, environment, popen=subprocess.Popen)
        except OSError as error:
            raise ValueError('无法启动安装程序，请手动运行已下载的安装包。') from error
        STATE.update(state='installing', error='')
        try:
            stopped = stop_backend()
        except Exception:
            stopped = False
        if not stopped:
            try:
                proc.terminate()
            except OSError as error:
                logger.debug("Updater process terminate failed: %s", error)
            STATE.update(state='downloaded', error='后台无法安全退出，请确认任务已完成后再更新。')
            raise ValueError(STATE['error'])
        threading.Thread(target=_watch_install, args=(proc,), daemon=True).start()
        return dict(STATE)


def _watch_install(proc):
    """If this backend survives, surface installer failure or completion."""
    try:
        code = proc.wait()
    except OSError:
        code = -1
    with LOCK:
        if STATE.get('state') != 'installing':
            return
        if code:
            STATE.update(state='downloaded', error='安装未完成，请重试或手动运行已下载的安装包。')
        else:
            STATE.update(state='installed', error='')


class _ProgressTracker:
    """Thread-safe download progress and transfer speed tracker."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.total = 0
        self.started = time.monotonic()
        self.last_report = 0.0
        self.lock = threading.Lock()

    def add(self, count: int, force: bool = False) -> None:
        with self.lock:
            self.total += count
            if self.total > self.limit:
                raise ValueError('安装包大小不符')
            now = time.monotonic()
            if force or now - self.last_report >= 0.2:
                self.last_report = now
                speed = int(self.total / max(now - self.started, 0.1))
                total = self.total
            else:
                return
        with LOCK:
            STATE['downloaded'] = total
            STATE['speed'] = speed


def _parse_content_range(response: Any, expected_start: int, expected_end: int, expected_size: int) -> bool:
    if getattr(response, 'status', None) != 206:
        return False
    headers = getattr(response, 'headers', None)
    raw = headers.get('Content-Range', '') if headers else ''
    match = _CONTENT_RANGE_RE.fullmatch(str(raw).strip())
    if not match:
        return False
    start, end, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return start == expected_start and end == expected_end and total == expected_size


def _write_slice_response(
    response: Any,
    out: Any,
    file_lock: threading.Lock,
    pos: int,
    end: int,
    tracker: _ProgressTracker,
) -> int:
    expected = end - pos + 1
    written = 0
    while written < expected:
        chunk = response.read(min(CHUNK_SIZE, expected - written))
        if not chunk:
            break
        with file_lock:
            out.seek(pos + written)
            out.write(chunk)
        written += len(chunk)
        tracker.add(len(chunk))
    return pos + written


def _download_slice(
    url: str,
    start: int,
    end: int,
    total_size: int,
    out: Any,
    file_lock: threading.Lock,
    tracker: _ProgressTracker,
    initial_response: Any = None,
) -> None:
    pos = start
    response = initial_response
    for attempt in range(RANGE_RETRIES + 1):
        try:
            if response is None:
                response = _open(url, headers={'Range': f'bytes={pos}-{end}'})
                if not _parse_content_range(response, pos, end, total_size):
                    raise ValueError('分片响应无效')
            with response:
                pos = _write_slice_response(response, out, file_lock, pos, end, tracker)
            if pos > end:
                return
            raise ValueError('分片下载未完成')
        except Exception:
            if attempt >= RANGE_RETRIES:
                raise
            response = None
            time.sleep(0.3 * (attempt + 1))


def _stream_single(response: Any, out: Any, limit: int, tracker: _ProgressTracker) -> None:
    while True:
        chunk = response.read(CHUNK_SIZE)
        if not chunk:
            break
        tracker.add(len(chunk))
        out.write(chunk)
    tracker.add(0, force=True)


def _download_to_temp(url: str, size: int, fd: int) -> None:
    limit = min(size, MAX_INSTALLER)
    tracker = _ProgressTracker(limit)
    with os.fdopen(fd, 'wb+') as out:
        if size < RANGE_THRESHOLD:
            with _open(url) as response:
                _stream_single(response, out, limit, tracker)
            return

        workers = min(RANGE_WORKERS, max(1, size // (512 * 1024)))
        span = (size + workers - 1) // workers
        ranges = [(i * span, min(size - 1, (i + 1) * span - 1)) for i in range(workers) if i * span < size]
        start0, end0 = ranges[0]
        first = _open(url, headers={'Range': f'bytes={start0}-{end0}'})
        if len(ranges) == 1 or not _parse_content_range(first, start0, end0, size):
            with first:
                _stream_single(first, out, limit, tracker)
            return

        file_lock = threading.Lock()
        errors: list[BaseException] = []

        def run_slice(s: int, e: int, resp: Any = None) -> None:
            try:
                _download_slice(url, s, e, size, out, file_lock, tracker, initial_response=resp)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run_slice, args=(s, e), daemon=True) for s, e in ranges[1:]]
        for thread in threads:
            thread.start()
        run_slice(start0, end0, first)
        for thread in threads:
            thread.join()
        if errors:
            raise errors[0]
        tracker.add(0, force=True)


def _hash_file(path: str) -> tuple[int, str]:
    total = 0
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        while chunk := stream.read(CHUNK_SIZE):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def _download(release, directory=None, auto_install=False, busy=None, stop_backend=None):
    temp: str | None = None
    created = None
    try:
        folder = Path(directory) if directory else Path.home() / 'Downloads'
        folder.mkdir(parents=True, exist_ok=True)
        fd, temp_file = tempfile.mkstemp(prefix='.any-update-', suffix='.tmp', dir=folder)
        temp = temp_file
        _download_to_temp(release['url'], release['size'], fd)
        total, digest_hex = _hash_file(temp_file)
        if total != release['size'] or digest_hex != release['sha256']:
            raise ValueError('安装包校验失败')
        if arch := release.get('macos_arch'):
            name, extension = f"AnY-{release['version']}-macOS-{arch}", '.dmg'
        elif release.get('macos'):
            name, extension = f"AnY-{release['version']}-macOS-Python", '.zip'
        else:
            name, extension = 'AnY-Setup-' + release['version'], '.exe'
        for i in range(1000):
            path = folder / (name + (('-%d' % i) if i else '') + extension)
            try:
                # Reserve a fresh filename without overwriting existing files, then move atomically.
                with open(path, 'xb'):
                    created = path
                os.replace(temp_file, path)
                temp = None
                break
            except FileExistsError:
                continue
        else:
            raise ValueError('下载目录中已有太多同名文件')
        with LOCK:
            STATE.update(state='downloaded', path=str(path), speed=0, error='')
        if auto_install:
            try:
                if busy and busy():
                    raise ValueError('还有任务正在运行或排队，请等待完成后再更新。')
                start_install(stop_backend)
            except ValueError as error:
                with LOCK:
                    STATE.update(state='downloaded', error=str(error))
    except Exception as error:
        logger.debug("Update download/install failed: %s", error)
        if created:
            try:
                created.unlink(missing_ok=True)
            except OSError as cleanup_err:
                logger.debug("Cleanup temp installer %s failed: %s", created, cleanup_err)
        with LOCK:
            STATE.update(state='error', error='下载失败或文件校验未通过，请重试', path='', speed=0)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
