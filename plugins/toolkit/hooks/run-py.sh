#!/bin/sh
# hooks.json 的 python 啟動殼：sh "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" <腳本檔名>
# 指令字串只留一層引號：hooks.json 的 commandWindows 由 command 套樣板產生（tests/test_hooks_windows.py）。
# Windows 的 Codex 只跑 commandWindows（PowerShell），由它找 Git for Windows 的 sh.exe 再呼叫本檔；本檔必須是 LF（.gitattributes）。
# fail-open：腳本不在、或 python3／python 都跑不起來，一律 exit 0。
S="$(dirname "$0")/$1"
[ -f "$S" ] || exit 0
for PY in python3 python; do
  "$PY" -c "" 2>/dev/null && exec "$PY" "$S"
done
exit 0
