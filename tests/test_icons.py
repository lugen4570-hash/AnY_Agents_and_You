"""Browser icons must reference the current Cojam artwork without PWA metadata."""
from pathlib import Path
import unittest
import urllib.error
import urllib.request

import test_contacts_access as support
from bridge.version import VERSION


class CojamIcons(unittest.TestCase):
    def test_versioned_icons_are_served_with_current_artwork(self):
        root = Path(__file__).resolve().parents[1]
        path = '/static/icon-192.png?v=cojam-' + VERSION.replace('.', '')
        url = support.BASE + path
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.headers.get_content_type(), 'image/png')
            self.assertEqual(response.read(), (root / 'static/icon-192.png').read_bytes())
        for name in ('index.html', 'static/join.html', 'static/enroll.html'):
            self.assertIn(path, (root / name).read_text(encoding='utf-8'))

    def test_pwa_manifest_and_service_worker_are_removed(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('manifest.webmanifest', html)
        self.assertNotIn('web-app-capable', html)
        core = (root / 'static/app-core.js').read_text(encoding='utf-8')
        self.assertNotIn('serviceWorker.register', core)
        self.assertIn('getRegistrations', core)
        for obsolete in ('manifest.webmanifest', 'sw.js', 'offline.html', 'icon-512.png', 'icon-maskable-512.png'):
            self.assertFalse((root / 'static' / obsolete).exists(), obsolete)
        for path in ('/manifest.webmanifest', '/sw.js'):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(support.BASE + path)
            self.assertEqual(ctx.exception.code, 404)
            ctx.exception.close()


if __name__ == '__main__':
    unittest.main()
