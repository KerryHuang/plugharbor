#!/usr/bin/env bash
# self-rotate.sh 行為測試：herdr、hc 兩種後端各跑同一組情境。
# stub 模擬 /clear 換 session id、/clear 後第一個指令被吞掉；PATH 只含 stub 與系統目錄，不碰真的 hc／herdr。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/self-rotate.sh"
TMP="$(mktemp -d)"
trap 'kill "${CPID:-}" 2>/dev/null || true; rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/state/plugharbor/hc-sessions"
# 共用的「畫面／session」模擬：STUB_MODE = swallow（預設，/clear 後吞一個指令）｜fold（長句折行）｜wrapword（第一個空白就折行：不可斷的長路徑整段排到下一行）｜noclear（/clear 無效）
# ｜blank（/clear 沒換 id，但之後讀 session id 暫時回空）
cat > "$TMP/lib.sh" <<'LIB'
S="$STUB_DIR"; M="${STUB_MODE:-swallow}"
deliver() {
  echo "$1" >> "$S/sent"
  [ "$M" = noclear ] && return 0
  if [ "$M" = blank ]; then [ "$1" = /clear ] && { touch "$S/blank"; rm -f "$SIDFILE"; }; return 0; fi
  if [ "$1" = /clear ]; then
    echo s1 > "$SIDFILE"; : > "$S/screen"
    [ "$M" = swallow ] && touch "$S/swallow"
    return 0
  fi
  if [ -e "$S/swallow" ]; then rm "$S/swallow"; return 0; fi   # 重繪中，吞掉
  [ "$1" = /reload-plugins ] && echo "Reloaded: 5 plugins" >> "$S/screen"
  case "$M" in
    fold) printf '%s\n' "$1" | fold -b -w 30 >> "$S/screen" ;;
    wrapword) printf '❯ %s\n  %s\n' "${1%% *}" "${1#* }" >> "$S/screen" ;;
    *) echo "❯ $1" >> "$S/screen" ;;
  esac
}
LIB
cat > "$TMP/bin/herdr" <<'STUB'
#!/usr/bin/env bash
. "$STUB_DIR/lib.sh"
echo "herdr $*" >> "$S/calls"
case "$1 $2" in
  "agent wait") echo '{"agent_status":"idle"}' ;;
  "agent get")  if [ -e "$S/blank" ]; then echo '{}'; else echo "{\"agent_session\":{\"value\":\"$(cat "$SIDFILE" 2>/dev/null || echo s0)\"}}"; fi ;;
  "agent read") cat "$S/screen" 2>/dev/null || true ;;
  "agent prompt") deliver "$4" ;;
esac
STUB
cat > "$TMP/bin/hc" <<'STUB'
#!/usr/bin/env bash
. "$STUB_DIR/lib.sh"
echo "hc $*" >> "$S/calls"
case "$1" in
  get)  echo '{"address":"t3","status":"idle"}' ;;
  wait) echo '{"wait":{"ended":true,"status":"idle"}}' ;;
  read) cat "$S/screen" 2>/dev/null || true ;;
  send) echo "[${HC_TERMINAL_ID-}]" >> "$S/sendenv"; deliver "$5"; echo '{"ok":true}' ;;
esac
STUB
chmod +x "$TMP/bin/herdr" "$TMP/bin/hc"

# core 在跑：真的 listening socket（mux.py 以 connect 成功判斷）
python3 -c 'import socket,sys;s=socket.socket(socket.AF_UNIX);s.bind(sys.argv[1]);s.listen(8)
while True: s.accept()[0].close()' "$TMP/core.sock" &
CPID=$!; disown
for _ in 1 2 3 4 5 6 7 8 9 10; do [ -S "$TMP/core.sock" ] && break; sleep 0.2; done

fail=0
check() { if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

# rot BACKEND MODE 訊息 → 以對應後端的環境執行 self-rotate.sh
rot() {
  local backend="$1" mode="$2"; shift 2
  rm -f "$TMP/sent" "$TMP/log" "$TMP/calls" "$TMP/sendenv" "$TMP/swallow" "$TMP/blank"
  echo "❯ /clear" > "$TMP/screen"
  if [ "$backend" = hc ]; then
    SIDFILE="$TMP/state/plugharbor/hc-sessions/t3"
    env -u HERDR_ENV -u HERDR_PANE_ID PATH="$TMP/bin:/usr/bin:/bin" STUB_DIR="$TMP" STUB_MODE="$mode" SIDFILE="$SIDFILE" \
      XDG_STATE_HOME="$TMP/state" HC_TERMINAL_ID=t3 MUX_CORE_SOCKET="${CORE:-$TMP/core.sock}" ROTATE_DELAY=0 sh "$SCRIPT" "$@"
  else
    SIDFILE="$TMP/sid"
    env -u HC_TERMINAL_ID PATH="$TMP/bin:/usr/bin:/bin" STUB_DIR="$TMP" STUB_MODE="$mode" SIDFILE="$SIDFILE" \
      HERDR_ENV=1 HERDR_PANE_ID=wX:p1 ROTATE_DELAY=0 sh "$SCRIPT" "$@"
  fi
}
reset_sid() { if [ "$1" = hc ]; then echo s0 > "$TMP/state/plugharbor/hc-sessions/t3"; else echo s0 > "$TMP/sid"; fi; }

for B in herdr hc; do
  echo "== 後端：$B =="
  # 情境 1：上一輪的 /clear 還留在畫面上，仍要等 session id 換了才算清掉
  reset_sid $B; rot $B swallow 繼續自動駕駛 "$TMP/log" || true
  check "$B 最後一行是完成" "$([ "$(tail -1 "$TMP/log")" = 完成 ]; echo $?)"
  check "$B 被吞掉的 /reload-plugins 有重送" "$([ "$(grep -c '^/reload-plugins$' "$TMP/sent")" -eq 2 ]; echo $?)"
  check "$B 接回訊息送到" "$(grep -qF '❯ 繼續自動駕駛' "$TMP/screen"; echo $?)"
  if [ $B = hc ]; then
    check "hc send 的環境沒有 HC_TERMINAL_ID" "$([ -s "$TMP/sendenv" ] && ! grep -qv '^\[\]$' "$TMP/sendenv"; echo $?)"
  fi

  # 情境 1b：長接回句在畫面上折行，仍只送一次
  LONG="讀 /a/很長的路徑/handoff.md，從「下一步」接著做；完工時照檔末刪掉它。"
  reset_sid $B; rot $B fold "$LONG" "$TMP/log" || true
  check "$B 折行的長句只送一次" "$([ "$(grep -cF '讀 /a/' "$TMP/sent")" -eq 1 ] && [ "$(tail -1 "$TMP/log")" = 完成 ]; echo $?)"

  # 情境 1c：第一個字後面就折行（路徑沒有空白、整段換到下一行），仍只送一次
  reset_sid $B; rot $B wrapword "$LONG" "$TMP/log" || true
  check "$B 首字後折行的長句只送一次" "$([ "$(grep -cF '讀 /a/' "$TMP/sent")" -eq 1 ] && [ "$(tail -1 "$TMP/log")" = 完成 ]; echo $?)"

  # 情境 2：不在 herdr／Herdr.app 內就不跑
  if env -u HERDR_ENV -u HERDR_PANE_ID -u HC_TERMINAL_ID PATH="$TMP/bin:/usr/bin:/bin" sh "$SCRIPT" 2>/dev/null; then r=1; else r=0; fi
  check "$B 沒有終端身分就退出" "$r"

  # 情境 3：/clear 一直沒生效 → 記失敗、不送後續
  reset_sid $B; rot $B noclear x "$TMP/log" || true
  check "$B /clear 失敗就停" "$(! grep -q reload "$TMP/sent"; echo $?)"
  check "$B log 記失敗" "$(grep -q '失敗：/clear' "$TMP/log"; echo $?)"

  # 情境 3b：session id 暫時讀不到（空字串）不算 /clear 成功
  reset_sid $B; rot $B blank x "$TMP/log" || true
  check "$B sid 讀空不算 /clear 成功" "$(! grep -q reload "$TMP/sent"; echo $?)"
  check "$B sid 讀空時 log 記失敗" "$(grep -q '失敗：/clear' "$TMP/log"; echo $?)"
done

# 情境 4：hc 的 core 沒跑 → 不得呼叫任何 hc
reset_sid hc; CORE="$TMP/nosock" rot hc swallow x "$TMP/log" || true
check "core 沒跑時不呼叫 hc" "$(! grep -q '^hc ' "$TMP/calls" 2>/dev/null; echo $?)"
check "core 沒跑時 log 記失敗" "$(grep -q '^失敗：' "$TMP/log"; echo $?)"

exit $fail
