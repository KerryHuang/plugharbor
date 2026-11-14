#!/bin/sh
# 換新 session：等本 pane 閒置（呼叫它的回合結束）後送 /clear、/reload-plugins，再送接回訊息。
# 副本：workspace/skills/unattended/scripts/self-rotate.sh 與 toolkit/skills/handoff/scripts/self-rotate.sh 必須一致（兩個 plugin 各自能單獨安裝）。
# 用法（在 herdr pane 內由 session 背景啟動）：
#   nohup sh self-rotate.sh [接回訊息] [log] >/dev/null 2>&1 &
# /clear 後立刻送的指令會在畫面重繪時被吞掉，所以每步都確認生效、最多試 3 次。
set -u
P="${HERDR_PANE_ID:?不在 herdr pane 內}"
MSG="${1:-繼續自動駕駛}"; LOG="${2:-/dev/null}"; D="${ROTATE_DELAY:-3}"

sid() { herdr agent get "$P" 2>/dev/null | grep -o '"value":"[^"]*"' | head -1; }
fail() { echo "失敗：$1" >>"$LOG"; exit 1; }

# 送出 $1，直到 $2（檢查指令）成立
send() {
  for _ in 1 2 3; do
    sleep "$D"; herdr agent prompt "$P" "$1" >>"$LOG" 2>&1
    sleep "$D"; eval "$2" && return 0
  done
  fail "$1"
}

sleep "$D"
herdr agent wait "$P" --until idle --timeout 1800000 >>"$LOG" 2>&1 || fail "等不到閒置"
OLD="$(sid)"
# /clear 會換 session id；畫面上可能還留著上一輪的 /clear，不拿畫面判斷
send /clear '[ "$(sid)" != "$OLD" ]'
send /reload-plugins 'herdr agent read "$P" 2>/dev/null | grep -q Reloaded'
herdr agent wait "$P" --until idle --timeout 60000 >>"$LOG" 2>&1
# 長句在畫面上會折行，只比對前 10 個字（perl 按字元切，不切壞中文）
HEAD="$(perl -CSA -e 'print substr($ARGV[0], 0, 10)' "$MSG")"
send "$MSG" 'herdr agent read "$P" 2>/dev/null | grep -qF -- "$HEAD"'
echo 完成 >>"$LOG"
