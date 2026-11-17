#!/bin/sh
# 換新 session：等本終端閒置（呼叫它的回合結束）後送 /clear、/reload-plugins，再送接回訊息。
# 後端（herdr TUI 或 Herdr.app）由 mux.py 判斷，這裡不分。
# 副本：workspace/skills/unattended/scripts/self-rotate.sh 與 toolkit/skills/handoff/scripts/self-rotate.sh 必須一致（兩個 plugin 各自能單獨安裝）。
# 用法（在 herdr 或 Herdr.app 的終端內由 session 背景啟動）：
#   nohup sh self-rotate.sh [接回訊息] [log] >/dev/null 2>&1 &
# /clear 後立刻送的指令會在畫面重繪時被吞掉，所以每步都確認生效、最多試 3 次。
set -u
MSG="${1:-繼續自動駕駛}"; LOG="${2:-/dev/null}"; D="${ROTATE_DELAY:-3}"

# mux.py：先找同目錄複本（workspace），再找 toolkit 的 agent-dispatch
MUX="$(dirname "$0")/mux.py"
[ -f "$MUX" ] || MUX="$(dirname "$0")/../../agent-dispatch/scripts/mux.py"
fail() { echo "失敗：$1" >>"$LOG"; exit 1; }
[ -f "$MUX" ] || fail "找不到 mux.py"

SELF="$(python3 "$MUX" env 2>/dev/null | grep -o '"self": *"[^"]*"' | head -1 | sed 's/.*: *"//; s/"$//')"
[ -n "$SELF" ] || { echo "不在 herdr 或 Herdr.app 的終端內" >&2; exit 1; }

sid() { python3 "$MUX" session "$SELF" 2>/dev/null | grep -o '"session": *"[^"]*"' | head -1; }
screen() { python3 "$MUX" read "$SELF" 2>/dev/null; }
# 等閒置 $1 秒；status 不是 idle／done（含逾時、core 沒跑）就算失敗
wait_idle() {
  _o="$(python3 "$MUX" wait "$SELF" --timeout "$1" 2>>"$LOG")"; echo "$_o" >>"$LOG"
  case "$_o" in '{"status": "idle"'*|'{"status": "done"'*) return 0 ;; esac
  return 1
}

# 送出 $1，直到 $2（檢查指令）成立
send() {
  for _ in 1 2 3; do
    sleep "$D"; python3 "$MUX" send "$SELF" --text "$1" >>"$LOG" 2>&1
    sleep "$D"; eval "$2" && return 0
  done
  fail "$1"
}

sleep "$D"
wait_idle 1800 || fail "等不到閒置"
OLD="$(sid)"
# /clear 會換 session id；畫面上可能還留著上一輪的 /clear，不拿畫面判斷
send /clear '[ "$(sid)" != "$OLD" ]'
send /reload-plugins 'screen | grep -q Reloaded'
wait_idle 60 || :
# 長句在畫面上會折行，只比對前 10 個字（perl 按字元切，不切壞中文）
HEAD="$(perl -CSA -e 'print substr($ARGV[0], 0, 10)' "$MSG")"
send "$MSG" 'screen | grep -qF -- "$HEAD"'
echo 完成 >>"$LOG"
