#!/bin/bash
set -eu
cd "$(dirname "$0")"

status=0
/bin/bash packaging/build_macos.sh || status=$?
if [[ "$status" -ne 0 && -t 0 ]]; then
  printf '构建失败。请查看上方错误，按回车关闭…'
  read -r answer || true
fi
exit "$status"
