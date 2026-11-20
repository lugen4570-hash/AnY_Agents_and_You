"""Create explicit release artifacts; never include data or machine credentials."""
from pathlib import Path
import os
import shutil
import subprocess
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
DIST = ROOT/'dist'
DIST.mkdir(exist_ok=True)


def verify_signed(path: Path) -> None:
    """Ensure a Windows release binary has a trusted Authenticode signature with timestamp."""
    if os.environ.get('COJAM_REQUIRE_SIGNATURE') != '1':
        return
    if os.name != 'nt':
        raise RuntimeError('必须在 Windows 上验证正式发行包的签名')
    shell = shutil.which('pwsh') or 'powershell.exe'
    rel = path.relative_to(ROOT).as_posix()
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$s=Get-AuthenticodeSignature -LiteralPath '{rel}'; "
        "if ($s.Status -ne 'Valid' -or -not $s.TimeStamperCertificate) { exit 1 }"
    )
    result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', script], cwd=ROOT)
    if result.returncode:
        raise RuntimeError(f'正式发行包需要有效的受信任签名及时间戳：{rel}')


def write_tree(archive: zipfile.ZipFile, source_dir: Path, dest_prefix: str) -> None:
    """Recursively write a directory tree into a ZipFile under dest_prefix."""
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        for name in sorted(files):
            full = Path(root) / name
            rel = full.relative_to(source_dir).as_posix()
            archive.write(full, f'{dest_prefix}/{rel}')


verify_signed(DIST / 'Cojam.exe')
portable = DIST / f'Cojam-Portable-{VERSION}.exe'
shutil.copyfile(DIST / 'Cojam.exe', portable)
print(portable)
connector = DIST/('Cojam-Member-%s.zip' % VERSION)
shutil.copyfile(ROOT/'static'/'member-connector.zip', connector)
target = DIST/('Cojam-%s-win64.zip' % VERSION)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for source, name in [('dist/Cojam.exe','Cojam.exe'),('LICENSE','LICENSE'),('packaging/README.txt','README.txt'),
                         ('packaging/connect-member.bat','连接其他会议室.bat'),('docs/CONTACTS.md','CONTACTS.md'),
                         ('docs/MEMBERS.md','MEMBERS.md'),('docs/PROVIDERS.md','PROVIDERS.md'),
                         ('examples/contact_client.py','contact_client.py')]:
        archive.write(ROOT/source, name)
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
print(target)
print(connector)
desktop_exe = DIST/'CojamDesktop.exe'
if desktop_exe.is_file():
    core_dir = DIST/'CojamCore'
    core_exe = core_dir/'CojamCore.exe'
    internal_dir = core_dir/'_internal'
    if not core_exe.is_file() or not internal_dir.is_dir():
        raise RuntimeError('桌面版需要先构建目录核心 dist/CojamCore/（含 CojamCore.exe 与 _internal）')
    verify_signed(desktop_exe)
    verify_signed(core_exe)
    desktop = DIST/('Cojam-Desktop-%s-win64.zip' % VERSION)
    with zipfile.ZipFile(desktop, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(desktop_exe, 'Cojam.exe')
        archive.write(core_exe, 'CojamCore.exe')
        write_tree(archive, internal_dir, '_internal')
        archive.write(ROOT/'packaging'/'desktop-readme.txt', 'README.txt')
        archive.write(ROOT/'LICENSE', 'LICENSE')
        archive.write(ROOT/'packaging'/'connect-member.bat', '连接其他会议室.bat')
        for source, name in [('docs/CONTACTS.md','CONTACTS.md'), ('docs/MEMBERS.md','MEMBERS.md'),
                             ('docs/PROVIDERS.md','PROVIDERS.md'), ('examples/contact_client.py','contact_client.py')]:
            archive.write(ROOT/source, name)
    with zipfile.ZipFile(desktop) as archive:
        assert archive.testzip() is None
    print(desktop)
