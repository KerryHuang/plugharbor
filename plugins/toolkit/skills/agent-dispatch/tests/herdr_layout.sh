#!/usr/bin/env bash
# herdr_layout.py 行為測試：PATH 前面放 stub herdr，檢查它收到的指令序列
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/herdr_layout.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/herdr" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$STUB_LOG"
case "$1 $2" in
  "pane get")    echo '{"result":{"pane":{"tab_id":"t1","label":""}}}' ;;
  "tab list")    echo '{"result":{"tabs":[{"tab_id":"t1","label":"demo"}]}}' ;;
  "pane rename") echo '{"result":{}}' ;;
  "pane move")   echo '{"result":{"move_result":{"changed":true,"pane":{"tab_id":"hold"}}}}' ;;
  "pane layout")
    panes='{"pane_id":"M","rect":{"width":10,"height":10,"x":0,"y":0}}'
    for i in $(seq 1 "$STUB_WORKERS"); do
      panes="$panes,{\"pane_id\":\"w$i\",\"rect\":{\"width\":10,\"height\":10,\"x\":$i,\"y\":0}}"
    done
    echo "{\"result\":{\"layout\":{\"focused_pane_id\":\"M\",\"panes\":[$panes]}}}" ;;
  *) echo '{"error":"unexpected"}' ;;
esac
STUB
chmod +x "$TMP/herdr"

fail=0
check() { # 說明 條件結果(0=成立)
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi
}
run() { # worker 數 -> 輸出到 $LOG，回傳腳本 exit code
  export STUB_LOG="$TMP/log.$1" STUB_WORKERS="$1"
  : > "$STUB_LOG"
  PATH="$TMP:$PATH" python3 "$SCRIPT" --main M --label demo > "$TMP/out.$1" 2>&1
}

# 1 worker：一次 split，主 pane 比例 0.5
run 1
n=$(grep -c -- '--split' "$TMP/log.1" || true)
[ "$n" -eq 1 ]; check "1 worker：只有一次 split" $?
grep -q -- '--split right --target-pane M --ratio 0.5' "$TMP/log.1"; check "1 worker：主 pane 比例 0.5" $?

# 主 pane label 以 ★ 開頭
grep -q 'pane rename M ★ demo' "$TMP/log.1"; check "主 pane label 以 ★ 開頭" $?

# 6 workers：主 pane 在左（只被切 right）、全高（從不被切 down）
run 6
grep -q -- '--split right --target-pane M --ratio 0.25' "$TMP/log.6"; check "6 workers：主 pane 留左側 0.25" $?
! grep -q -- '--split down --target-pane M' "$TMP/log.6"; check "6 workers：主 pane 不被切 down（全高）" $?

# 7 workers：腳本拒絕並提示開新 tab，且不動任何 pane
set +e; run 7; rc=$?; set -e
[ "$rc" -ne 0 ]; check "7 workers：退出碼非 0" $?
grep -q '請開新 tab' "$TMP/out.7"; check "7 workers：提示第 7 個起開新 tab" $?
! grep -q 'pane move' "$TMP/log.7"; check "7 workers：不搬動任何 pane" $?

exit $fail
