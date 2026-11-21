"""Package the macOS browser launcher and local desktop builder from committed sources."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import runpy
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['bridge', 'static', 'index.html', 'roundtable.py', 'LICENSE', 'pyproject.toml',
          'desktop_launcher.py', 'desktop_shell', 'packaging/build-cojam.command', 'packaging/build_macos.sh',
          'packaging/start-cojam.command', 'packaging/macos-python-readme.txt',
          'packaging/member-readme.md', 'packaging/start-member.command', 'packaging/start-member.bat']


def build(source_ref='HEAD', output_dir=None):
    """Use committed Git objects so machine-local edits and data never enter the bundle."""
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', source_ref + '^{commit}'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', '--format=tar', commit, '--', *INPUTS], cwd=ROOT)
    output = Path(output_dir) if output_dir is not None else ROOT / 'dist' / 'macOS'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cojam-macos-build-') as scratch:
        clean = Path(scratch)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source:
                name = PurePosixPath(member.name)
                if member.isdir():
                    continue
                if not member.isfile() or name.is_absolute() or '..' in name.parts:
                    raise ValueError(f'Unexpected source entry: {member.name}')
                target = clean.joinpath(*name.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as stream:
                    target.write_bytes(stream.read())
        version = tomllib.loads((clean / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
        if version != runpy.run_path(str(clean / 'bridge/version.py'))['VERSION']:
            raise ValueError('pyproject.toml and bridge/version.py versions differ')
        for command in (clean / 'packaging').iterdir():
            if command.suffix in ('.command', '.sh'):
                command.write_bytes(command.read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n'))
        spec = importlib.util.spec_from_file_location('cojam_clean_member_bundle', clean / 'bridge/member_package.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.build(clean)
        files = {'启动合拍.command': (clean / 'packaging/start-cojam.command').read_bytes(),
                 '构建合拍桌面版.command': (clean / 'packaging/build-cojam.command').read_bytes(),
                 'README.txt': (clean / 'packaging/macos-python-readme.txt').read_bytes(),
                 **{name: (clean / name).read_bytes() for name in
                    ('index.html', 'roundtable.py', 'LICENSE', 'pyproject.toml', 'desktop_launcher.py',
                     'packaging/build_macos.sh', 'packaging/member-readme.md',
                     'packaging/start-member.command', 'packaging/start-member.bat')}}
        for folder in ('bridge', 'static', 'desktop_shell'):
            for path in sorted((clean / folder).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    files[path.relative_to(clean).as_posix()] = path.read_bytes()
        provenance = {'version': version, 'source_commit': commit, 'python_required': '>=3.11',
                      'python_runtime_bundled': False, 'interface': 'browser',
                      'desktop_builder': 'pywebview + PyInstaller on macOS', 'mac_hardware_tested': False}
        files['SOURCE.json'] = (json.dumps(provenance, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
        files['CHECKSUMS.json'] = (json.dumps(hashes, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        target = output / f'Cojam-{version}-macOS-Python.zip'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo('Cojam/' + name)
                info.create_system = 3
                info.external_attr = (0o100755 if name.endswith(('.command', '.sh')) else 0o100644) << 16
                bundle.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        (output / f'{target.name}.sha256').write_text(f'{digest}  {target.name}\n', encoding='utf-8')
        report = dict(provenance, artifact=target.name, bytes=target.stat().st_size, sha256=digest,
                      entries=len(files), source='committed Git archive; local edits excluded')
        (output / f'build-report-{version}-macOS-Python.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', default='HEAD')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    print(build(args.source_ref, args.output_dir))


if __name__ == '__main__':
    main()
