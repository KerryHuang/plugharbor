#!/usr/bin/env bash
# notification.sh：在 Herdr.app（HC_TERMINAL_ID）或 herdr TUI（HERDR_ENV＋HERDR_PANE_ID）內不發桌面通知；
# 不在內才呼叫通知指令。用 stub 取代 osascript／afplay／notify-send，不會真的通知。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail() { echo "FAIL: $1"; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
for c in osascript terminal-notifier afplay notify-send powershell.exe paplay aplay; do
  printf '#!/bin/sh\necho "$0" >> "%s/called"\n' "$TMP" > "$TMP/bin/$c"; chmod +x "$TMP/bin/$c"
done

# $@ = 額外環境變數；回傳 stub 是否被呼叫
run() {
  rm -f "$TMP/called"
  env -u HERDR_ENV -u HERDR_PANE_ID -u HC_TERMINAL_ID HOME="$TMP" PATH="$TMP/bin:$PATH" "$@" \
    bash "$PLUGIN_DIR/hooks/notification.sh" </dev/null || fail "exit 非 0：$*"
  sleep 0.3
  [ -f "$TMP/called" ]
}

run HC_TERMINAL_ID=t1 && fail "HC_TERMINAL_ID 下不該通知"
run HERDR_ENV=1 HERDR_PANE_ID=w:p1 && fail "herdr TUI 下不該通知"
# 沒有 pane id 的 HERDR_ENV 不算在 herdr 內
if [[ "$OSTYPE" == "darwin"* ]]; then
  run HERDR_ENV=1 || fail "HERDR_ENV 無 pane id 時應照常通知"
  run FOO=1 || fail "不在 herdr 內時應照常通知"
fi
echo "PASS: notification-herdr"
