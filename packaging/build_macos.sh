#!/bin/bash
# Build on the target Mac architecture (PyInstaller cannot cross-compile).
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then echo '请在 macOS 上构建。' >&2; exit 1; fi
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:${PATH:-/usr/bin:/bin}"
python=''
for candidate in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
  if [[ -x "$candidate" ]] && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    python=$candidate
    break
  fi
done
if [[ -z "$python" ]]; then
  echo '请先安装 macOS 版 Python 3.11 或更新版本：https://www.python.org/downloads/macos/' >&2
  exit 1
fi

echo '正在准备桌面构建环境，首次构建需要联网下载 Python 依赖…'
"$python" -m venv .venv-macos-build
python="$PWD/.venv-macos-build/bin/python"
"$python" -m pip install 'pywebview>=5.3' 'pyinstaller>=6'
"$python" -m bridge.member_package
"$python" -m PyInstaller --noconfirm --clean --onefile --name CojamCore \
  --add-data 'index.html:.' --add-data 'static:static' --add-data 'bridge/presets:bridge/presets' \
  --add-data 'bridge/catalog:bridge/catalog' \
  --hidden-import bridge.web --hidden-import bridge.acp --hidden-import bridge.discovery \
  --hidden-import bridge.conn_settings --hidden-import bridge.mcp_stdio roundtable.py
icon_args=()
if [[ -f roundtable.icns ]]; then
  icon_args=(--icon roundtable.icns)
fi
"$python" -m PyInstaller --noconfirm --clean --windowed --onedir --name Cojam \
  "${icon_args[@]}" \
  --osx-bundle-identifier com.cojam.desktop --collect-all webview desktop_launcher.py
cp dist/CojamCore dist/Cojam.app/Contents/MacOS/CojamCore
version=$("$python" -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
arch=$("$python" -c 'import platform; print(platform.machine())')
"$python" - "$version" <<'PY'
import plistlib
from pathlib import Path
import sys

path = Path("dist/Cojam.app/Contents/Info.plist")
info = plistlib.loads(path.read_bytes())
info.update(CFBundleShortVersionString=sys.argv[1], CFBundleVersion=sys.argv[1], CFBundleDisplayName="AnY")
path.write_bytes(plistlib.dumps(info))
PY
codesign --force --deep --sign - dist/Cojam.app
codesign --verify --deep --strict dist/Cojam.app
ditto -c -k --sequesterRsrc --keepParent dist/Cojam.app "dist/Cojam-${version}-macOS-${arch}.zip"
echo "构建完成：$PWD/dist/Cojam.app"
echo "应用压缩包：$PWD/dist/Cojam-${version}-macOS-${arch}.zip"
