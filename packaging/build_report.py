"""Write final release hashes and a build report after signing and verification."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validation', type=Path, help='JSON describing the checks actually performed')
    args = parser.parse_args()
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    dist = ROOT / 'dist'
    names = [f'AnY-Setup-{version}.exe', f'AnY-Desktop-{version}-win64.zip',
             f'AnY-{version}-win64.zip', f'AnY-Member-{version}.zip', f'AnY-Portable-{version}.exe']
    artifacts = [{'file': name, 'bytes': (dist / name).stat().st_size,
                  'sha256': hashlib.sha256((dist / name).read_bytes()).hexdigest()} for name in names]
    signatures = {}
    if os.name == 'nt':
        paths = ['dist/AnYDesktop.exe', 'dist/AnYCore/AnYCore.exe', f'dist/AnY-Setup-{version}.exe']
        script = '$rows=@(); foreach ($p in @(' + ','.join("'" + p + "'" for p in paths) + ')) {'
        script += '$s=Get-AuthenticodeSignature -LiteralPath $p; $rows+=@{file=$p;status=[string]$s.Status;timestamped=[bool]$s.TimeStamperCertificate}};ConvertTo-Json -InputObject $rows -Compress'
        rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', script], cwd=ROOT, text=True))
        signatures = {row['file']: {'status': row['status'], 'timestamped': row['timestamped']} for row in rows}
        if (os.environ.get('ANY_REQUIRE_SIGNATURE') == '1' or os.environ.get('COJAM_REQUIRE_SIGNATURE') == '1') and any(
                row['status'] != 'Valid' or not row['timestamped'] for row in rows):
            raise RuntimeError('Required release signatures are missing or invalid')
    validation = json.loads(args.validation.read_text(encoding='utf-8')) if args.validation else {}
    rustc = shutil.which('rustc') or str(Path.home() / '.cargo' / 'bin' / ('rustc.exe' if os.name == 'nt' else 'rustc'))
    report = {
        'version': version,
        'built_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'environment': {'python': sys.version.split()[0], 'os': platform.platform(),
                        'rust': subprocess.check_output([rustc, '--version'], text=True).strip()},
        'signed': bool(signatures) and all(s['status'] == 'Valid' and s['timestamped'] for s in signatures.values()),
        'signatures': signatures,
        'validation': validation,
        'artifacts': artifacts,
    }
    (dist / f'SHA256SUMS-{version}.txt').write_text(
        ''.join(f'{a["sha256"]}  {a["file"]}\n' for a in artifacts), encoding='utf-8')
    report_path = dist / f'build-report-{version}.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(report_path)


if __name__ == '__main__':
    main()
