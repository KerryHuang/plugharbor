#!/usr/bin/env bash
# self-rotate.sh 行為測試：stub herdr 模擬 /clear 換 session id、/clear 後第一個指令被吞掉
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/self-rotate.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/herdr" <<'STUB'
#!/usr/bin/env bash
S="$STUB_DIR"
case "$1 $2" in
  "agent wait") exit 0 ;;
  "agent get")  echo "{\"agent_session\":{\"value\":\"$(cat "$S/sid" 2>/dev/null || echo s0)\"}}" ;;
  "agent read") cat "$S/screen" 2>/dev/null || true ;;
  "agent prompt")
    echo "$4" >> "$S/sent"
    if [ "$4" = /clear ]; then echo s1 > "$S/sid"; : > "$S/screen"; touch "$S/swallow"; exit 0; fi
    if [ -e "$S/swallow" ]; then rm "$S/swallow"; exit 0; fi   # 重繪中，吞掉
    [ "$4" = /reload-plugins ] && echo "Reloaded: 5 plugins" >> "$S/screen"
    echo "❯ $4" >> "$S/screen" ;;
esac
STUB
chmod +x "$TMP/herdr"

fail=0
check() { if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

# 情境 1：上一輪的 /clear 還留在畫面上，仍要等 session id 換了才算清掉
echo "❯ /clear" > "$TMP/screen"
PATH="$TMP:$PATH" STUB_DIR="$TMP" HERDR_PANE_ID=wX:p1 ROTATE_DELAY=0 sh "$SCRIPT" 繼續自動駕駛 "$TMP/log"
check "最後一行是完成" "$([ "$(tail -1 "$TMP/log")" = 完成 ]; echo $?)"
check "被吞掉的 /reload-plugins 有重送" "$([ "$(grep -c '^/reload-plugins$' "$TMP/sent")" -eq 2 ]; echo $?)"
check "接回訊息送到" "$(grep -qF '❯ 繼續自動駕駛' "$TMP/screen"; echo $?)"

# 情境 1b：長接回句在畫面上折行，仍只送一次
rm -f "$TMP/sent" "$TMP/log"; LONG="讀 /a/很長的路徑/handoff.md，從「下一步」接著做；完工時照檔末刪掉它。"
cat > "$TMP/b3" <<'STUB'
#!/usr/bin/env bash
S="$STUB_DIR"
case "$1 $2" in
  "agent get") echo "{\"agent_session\":{\"value\":\"$(cat "$S/sid3" 2>/dev/null || echo s0)\"}}" ;;
  "agent read") cat "$S/screen3" 2>/dev/null || true ;;
  "agent prompt") echo "$4" >> "$S/sent"
    case "$4" in /clear) echo s9 > "$S/sid3" ;; /reload-plugins) echo Reloaded >> "$S/screen3" ;;
      *) printf '%s\n' "$4" | fold -b -w 30 >> "$S/screen3" ;; esac ;;
esac
STUB
mkdir -p "$TMP/b3d"; mv "$TMP/b3" "$TMP/b3d/herdr"; chmod +x "$TMP/b3d/herdr"
PATH="$TMP/b3d:$PATH" STUB_DIR="$TMP" HERDR_PANE_ID=wX:p1 ROTATE_DELAY=0 sh "$SCRIPT" "$LONG" "$TMP/log"
check "折行的長句只送一次" "$([ "$(grep -cF '讀 /a/' "$TMP/sent")" -eq 1 ] && [ "$(tail -1 "$TMP/log")" = 完成 ]; echo $?)"

# 情境 2：不在 herdr pane 內就不跑
if env -u HERDR_PANE_ID PATH="$TMP:$PATH" sh "$SCRIPT" 2>/dev/null; then r=1; else r=0; fi
check "沒有 HERDR_PANE_ID 就退出" "$r"

# 情境 3：/clear 一直沒生效 → 記失敗、不送後續
rm -f "$TMP/sent" "$TMP/log"; echo s0 > "$TMP/sid"
cat > "$TMP/herdr2" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  "agent get") echo '{"agent_session":{"value":"s0"}}' ;;
  "agent prompt") echo "$4" >> "$STUB_DIR/sent" ;;
esac
STUB
mkdir -p "$TMP/b2"; mv "$TMP/herdr2" "$TMP/b2/herdr"; chmod +x "$TMP/b2/herdr"
PATH="$TMP/b2:$PATH" STUB_DIR="$TMP" HERDR_PANE_ID=wX:p1 ROTATE_DELAY=0 sh "$SCRIPT" x "$TMP/log" || true
check "/clear 失敗就停" "$(! grep -q reload "$TMP/sent"; echo $?)"
check "log 記失敗" "$(grep -q '失敗：/clear' "$TMP/log"; echo $?)"

exit $fail
