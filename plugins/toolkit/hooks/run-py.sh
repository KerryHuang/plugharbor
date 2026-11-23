#!/bin/sh
# hooks.json 的 python 啟動殼：sh "${CLAUDE_PLUGIN_ROOT}/hooks/run-py.sh" <腳本檔名>
# 指令字串只留一層引號：hooks.json 的 commandWindows 由 command 套樣板產生（tests/test_hooks_windows.py）。
# Windows 的 Codex 只跑 commandWindows（PowerShell），由它找 Git for Windows 的 sh.exe 再呼叫本檔；本檔必須是 LF（.gitattributes）。
# fail-open：腳本不在、或 python3／python 都跑不起來，一律 exit 0。
# Windows（Git Bash／MSYS）：不在 WindowsApps 的直接 exec，不先試跑，每支 hook 少一次 python 冷啟動（約 0.45 秒；
# Codex 並行跑 hook，累積起來會超過 timeout，plugharbor#74）。WindowsApps 下可能是 Store 的假執行檔，留到下面試跑。
# 其他平台照舊先試跑（啟動快，且要擋 PATH 上壞掉的 python3）。
S="$(dirname "$0")/$1"
[ -f "$S" ] || exit 0
case "${MSYSTEM:-}" in
  MINGW*|MSYS*|UCRT*|CLANG*)
    for PY in python3 python; do
      P="$(command -v "$PY" 2>/dev/null)" || continue
      case "$P" in *WindowsApps*) continue ;; esac
      exec "$P" "$S"
    done ;;
esac
for PY in python3 python; do
  "$PY" -c "" 2>/dev/null && exec "$PY" "$S"
done
exit 0
