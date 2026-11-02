#!/usr/bin/env bash
# herdr-tree 版型腳本解析：不再有內建 defaultLayout，預設指向 toolkit 的 herdr_layout.py；找不到回 null 只警告
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TS="$REPO/setup/herdr/pi/herdr-tree.ts"
LP="$REPO/setup/herdr/pi/layout-path.ts"
fail=0
ok() { echo "OK:   $1"; }
ng() { echo "FAIL: $1"; fail=1; }

[ "$(grep -c 'defaultLayout' "$TS")" = 0 ] && ok "herdr-tree.ts 無 defaultLayout" || ng "herdr-tree.ts 仍有 defaultLayout"

call() { node --experimental-strip-types --no-warnings -e "import('$LP').then(m => console.log(String(m.resolveLayout())))" 2>&1; }

got="$(env -u HERDR_TREE_LAYOUT bash -c "$(declare -f call); LP='$LP'; call")"
case "$got" in
  */plugins/toolkit/skills/agent-dispatch/scripts/herdr_layout.py) [ -f "$got" ] && ok "預設路徑存在：結尾正確" || ng "路徑不存在：$got" ;;
  *) ng "預設路徑不對：$got" ;;
esac

got="$(HERDR_TREE_LAYOUT=/nonexistent/x.py call)"
[ "$got" = null ] && ok "覆寫路徑不存在回 null" || ng "覆寫不存在應回 null：$got"

got="$(HERDR_TREE_LAYOUT="$0" call)"
[ "$got" = "$0" ] && ok "覆寫路徑存在就用它" || ng "覆寫存在應回原路徑：$got"

# 呼叫端：null 時 warn 後 return，不重排
grep -A3 'resolveLayout()' "$TS" | grep -q 'console.warn' && ok "呼叫端 null 時印警告" || ng "呼叫端缺警告"

grep -B1 -A3 'await runPy' "$TS" | grep -q 'try' && grep -A3 'await runPy' "$TS" | grep -q 'catch' && ok "腳本執行失敗有 try/catch 警告" || ng "runPy 缺 try/catch"

[ "$fail" = 0 ]
