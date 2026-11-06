#!/bin/sh
# hooks.json 的 python 啟動殼：sh "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" <腳本檔名>
# 指令字串只留一層引號：Windows 的 Codex 經 powershell -Command 執行 hook，sh -c 內的雙引號會被吃掉。
# fail-open：腳本不在、或 python3／python 都跑不起來，一律 exit 0。
S="$(dirname "$0")/$1"
[ -f "$S" ] || exit 0
for PY in python3 python; do
  "$PY" -c "" 2>/dev/null && exec "$PY" "$S"
done
exit 0
