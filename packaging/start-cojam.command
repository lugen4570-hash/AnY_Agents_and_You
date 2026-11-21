#!/bin/sh
# macOS browser distribution: no third-party Python packages are required.
set -eu
cojam_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"

cojam_python=''
for cojam_candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    "$(command -v python3 || true)" /usr/bin/python3; do
    if [ -n "$cojam_candidate" ] && [ -x "$cojam_candidate" ] && \
        "$cojam_candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
        cojam_python=$cojam_candidate
        break
    fi
done

if [ -z "$cojam_python" ]; then
    echo '合拍需要 Python 3.11 或更新版本。请先安装 macOS 版 Python，再双击本文件。'
    echo '下载：https://www.python.org/downloads/macos/'
    printf '按回车退出…'
    read -r cojam_answer || true
    exit 1
fi

export ROUNDTABLE_LOG_DIR="${ROUNDTABLE_LOG_DIR:-$HOME/Library/Application Support/Cojam}"
export ROUNDTABLE_DEFAULT_DIR="${ROUNDTABLE_DEFAULT_DIR:-$HOME}"
export ROUNDTABLE_NO_BROWSER=0
export ROUNDTABLE_OWNER_LIFECYCLE=1
cd "$cojam_dir"
echo '正在启动合拍，浏览器将自动打开。此终端窗口运行期间请保持打开。'
echo "会议数据：$ROUNDTABLE_LOG_DIR"
exec "$cojam_python" "$cojam_dir/roundtable.py"
