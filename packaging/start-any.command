#!/bin/sh
# macOS browser distribution: no third-party Python packages are required.
set -eu
any_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"

any_python=''
for any_candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    "$(command -v python3 || true)" /usr/bin/python3; do
    if [ -n "$any_candidate" ] && [ -x "$any_candidate" ] && \
        "$any_candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
        any_python=$any_candidate
        break
    fi
done

if [ -z "$any_python" ]; then
    echo 'AnY 需要 Python 3.11 或更新版本。请先安装 macOS 版 Python，再双击本文件。'
    echo '下载：https://www.python.org/downloads/macos/'
    printf '按回车退出…'
    read -r any_answer || true
    exit 1
fi

any_support="$HOME/Library/Application Support/AnY"
if [ ! -e "$any_support" ] && [ -e "$HOME/Library/Application Support/Cojam" ]; then
    any_support="$HOME/Library/Application Support/Cojam"
fi
export ROUNDTABLE_LOG_DIR="${ROUNDTABLE_LOG_DIR:-$any_support}"
export ROUNDTABLE_DEFAULT_DIR="${ROUNDTABLE_DEFAULT_DIR:-$HOME}"
export ROUNDTABLE_NO_BROWSER=0
export ROUNDTABLE_OWNER_LIFECYCLE=1
cd "$any_dir"
echo '正在启动 AnY，浏览器将自动打开。此终端窗口运行期间请保持打开。'
echo "会议数据：$ROUNDTABLE_LOG_DIR"
exec "$any_python" "$any_dir/roundtable.py"
