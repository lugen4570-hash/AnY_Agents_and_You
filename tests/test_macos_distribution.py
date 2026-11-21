"""Check the Mac Python bundle's actual payload, executable modes and source isolation."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('macos_bundle_builder', ROOT / 'packaging/build_macos_python.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MacDistribution(unittest.TestCase):
    def test_clean_payload_modes_member_bundle_and_determinism(self):
        with tempfile.TemporaryDirectory(prefix='cojam-mac-bundle-') as temp:
            fixture = Path(temp) / 'repo'
            fixture.mkdir()
            # Build a small clean repository fixture, never mutating the user's repo.
            paths = ['bridge', 'static', 'index.html', 'roundtable.py', 'LICENSE', 'pyproject.toml',
                     'desktop_launcher.py', 'desktop_shell',
                     'packaging/member-readme.md', 'packaging/start-member.command', 'packaging/start-member.bat']
            archive = subprocess.check_output(['git', 'archive', 'HEAD', '--', *paths], cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(archive)) as source:
                source.extractall(fixture, filter='data')
            for name in ('start-cojam.command', 'macos-python-readme.txt', 'build_macos.sh', 'build-cojam.command'):
                (fixture / 'packaging' / name).write_bytes((ROOT / 'packaging' / name).read_bytes())
            subprocess.run(['git', 'init', '-q'], cwd=fixture, check=True)
            subprocess.run(['git', 'add', '.'], cwd=fixture, check=True, capture_output=True)
            subprocess.run(['git', '-c', 'user.name=Package Test', '-c', 'user.email=test@example.invalid',
                            'commit', '-qm', 'Fixture'], cwd=fixture, check=True)
            # Local changes and files that must never enter a distribution.
            (fixture / 'static/app-core.js').write_text('LOCAL EDIT MUST NOT SHIP', encoding='utf-8')
            (fixture / 'bridge/private-token.txt').write_text('secret', encoding='utf-8')
            (fixture / 'data').mkdir()
            (fixture / 'data/devices.json').write_text('private', encoding='utf-8')
            with patch.object(builder, 'ROOT', fixture):
                output = builder.build(output_dir=Path(temp) / 'dist')
                first_digest = hashlib.sha256(output.read_bytes()).hexdigest()
                output2 = builder.build(output_dir=Path(temp) / 'dist2')
                self.assertEqual(output.read_bytes(), output2.read_bytes())
            with zipfile.ZipFile(output) as bundle:
                names = bundle.namelist()
                self.assertIsNone(bundle.testzip())
                self.assertTrue(any(n.startswith('Cojam/bridge/catalog/') for n in names))
                self.assertIn('Cojam/static/member-connector.zip', names)
                self.assertFalse(any(n.endswith('private-token.txt') or '/data/' in n or '__pycache__' in n for n in names))
                self.assertNotIn(b'LOCAL EDIT MUST NOT SHIP', bundle.read('Cojam/static/app-core.js'))
                launcher = bundle.getinfo('Cojam/启动合拍.command')
                self.assertEqual((launcher.external_attr >> 16) & 0o777, 0o755)
                self.assertNotIn(b'\r', bundle.read(launcher))
                self.assertIn(b'Library/Application Support/Cojam', bundle.read(launcher))
                packager = bundle.getinfo('Cojam/构建合拍桌面版.command')
                self.assertEqual((packager.external_attr >> 16) & 0o777, 0o755)
                self.assertNotIn(b'\r', bundle.read(packager))
                self.assertIn(b'packaging/build_macos.sh', bundle.read(packager))
                self.assertNotIn(b'\r', bundle.read('Cojam/packaging/build_macos.sh'))
                for resource in ('desktop_launcher.py', 'desktop_shell/main.py', 'desktop_shell/backend.py',
                                 'pyproject.toml', 'packaging/member-readme.md',
                                 'packaging/start-member.command', 'packaging/start-member.bat'):
                    self.assertIn('Cojam/' + resource, names)
                provenance = json.loads(bundle.read('Cojam/SOURCE.json'))
                self.assertFalse(provenance['python_runtime_bundled'])
                self.assertFalse(provenance['mac_hardware_tested'])
                checksums = json.loads(bundle.read('Cojam/CHECKSUMS.json'))
                for name, digest in checksums.items():
                    self.assertEqual(hashlib.sha256(bundle.read('Cojam/' + name)).hexdigest(), digest)
                with zipfile.ZipFile(io.BytesIO(bundle.read('Cojam/static/member-connector.zip'))) as member:
                    self.assertIsNone(member.testzip())
                    self.assertEqual((member.getinfo('start-member.command').external_attr >> 16) & 0o777, 0o755)
            sidecar = Path(str(output) + '.sha256').read_text()
            self.assertTrue(sidecar.startswith(first_digest + '  '))


if __name__ == '__main__':
    unittest.main()
