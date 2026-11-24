#!/usr/bin/env bash
set -euo pipefail

BASE="https://lugen4570-hash.github.io/AnY_Agents_and_You/"
if [[ ${ANY_CLI_TEST_SOURCE:-} =~ ^http://127\.0\.0\.1:[0-9]+/$ ]]; then
  BASE=$ANY_CLI_TEST_SOURCE
fi
original_path=${PATH:-}
uv_dir="${XDG_DATA_HOME:-$HOME/.local/share}/any-cli/bootstrap"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:${PATH:-/usr/bin:/bin}"

check_python() {
  local bin="${1:-}"
  [[ -n "$bin" && -x "$bin" ]] || return 1
  # Apple's placeholder can pop up the Xcode Command Line Tools installer.
  if [[ $(uname -s) == Darwin && "$bin" == /usr/bin/python3 ]]; then return 1; fi
  "$bin" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1
}

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    printf '%s\n' "$HOME/.local/bin/uv"
    return 0
  fi
  if [[ -x "$uv_dir/uv" ]]; then
    printf '%s\n' "$uv_dir/uv"
    return 0
  fi
  return 1
}

find_python() {
  local candidate uv_bin py
  for candidate in \
    "$(command -v python3 || true)" \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /usr/bin/python3; do
    if check_python "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  if uv_bin=$(find_uv); then
    for ver in 3.12 3.11 3.13; do
      py=$("$uv_bin" python find "$ver" 2>/dev/null || true)
      if check_python "$py"; then
        printf '%s\n' "$py"
        return 0
      fi
    done
  fi
  return 1
}

install_only=0
for arg in "$@"; do
  if [[ "$arg" == "--install-only" ]]; then
    install_only=1
  fi
done

if [[ ${ANY_CLI_MANAGED_PYTHON:-0} == 1 ]] || ! py=$(find_python); then
  echo "未检测到 Python 3.11+，正在自动配置独立 Python 运行环境…"
  if ! uv_bin=$(find_uv); then
    curl -LsSf https://astral.sh/uv/0.13.9/install.sh | UV_UNMANAGED_INSTALL="$uv_dir" sh
    uv_bin="$uv_dir/uv"
  fi
  "$uv_bin" python install --no-bin 3.12
  py=$("$uv_bin" python find --managed-python 3.12)
fi

tmp_py=$(mktemp "${TMPDIR:-/tmp}/any-install-cli-XXXXXX.py")
trap 'rm -f "$tmp_py"' EXIT
curl -fsSL "${BASE}install-cli.py" -o "$tmp_py"

launcher=$("$py" "$tmp_py" --print-launcher)
rm -f "$tmp_py"

mkdir -p "$HOME/.local/bin"
shortcut="$HOME/.local/bin/any"
if [[ ! -e "$shortcut" && ! -L "$shortcut" ]]; then
  ln -s "$launcher" "$shortcut"
fi

echo "AnY CLI 已安装：$launcher"
if [[ $(readlink "$shortcut" 2>/dev/null || true) == "$launcher" && ":$original_path:" != *":$HOME/.local/bin:"* ]]; then
  echo '如需在当前终端直接输入 any，请先执行：'
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

if [[ "$install_only" -eq 0 ]]; then
  if [[ -t 0 ]]; then
    exec "$launcher"
  elif [[ -t 1 && -r /dev/tty ]]; then
    exec "$launcher" < /dev/tty
  fi
fi
