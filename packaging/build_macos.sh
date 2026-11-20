#!/bin/bash
# Build on the target Mac architecture (PyInstaller cannot cross-compile).
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then echo '请在 macOS 上构建。' >&2; exit 1; fi
python3 -c 'import sys; assert sys.version_info >= (3, 11), "需要 Python 3.11+"'
python3 -m bridge.member_package
python3 -m PyInstaller --noconfirm --clean --onefile --name CojamCore \
  --add-data 'index.html:.' --add-data 'static:static' --add-data 'bridge/presets:bridge/presets' \
  --add-data 'bridge/catalog:bridge/catalog' \
  --hidden-import bridge.web --hidden-import bridge.acp --hidden-import bridge.discovery \
  --hidden-import bridge.conn_settings --hidden-import bridge.mcp_stdio roundtable.py
python3 -m PyInstaller --noconfirm --clean --windowed --onedir --name Cojam \
  --osx-bundle-identifier com.cojam.desktop --collect-all webview desktop_launcher.py
cp dist/CojamCore dist/Cojam.app/Contents/MacOS/CojamCore
codesign --force --deep --sign - dist/Cojam.app
version=$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
arch=$(uname -m)
ditto -c -k --sequesterRsrc --keepParent dist/Cojam.app "dist/Cojam-${version}-macOS-${arch}.zip"
echo "构建完成：dist/Cojam-${version}-macOS-${arch}.zip"
