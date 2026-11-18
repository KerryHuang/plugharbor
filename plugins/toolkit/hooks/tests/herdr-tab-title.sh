#!/usr/bin/env bash
# herdr-tab-title hook 行為驗證：用假的 hc／herdr-app，HOME 導到暫存目錄，不碰真的 Herdr.app。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || fail "找不到可執行的 python"

HOOK="$PLUGIN_DIR/hooks/herdr-tab-title.py"
H="$TMP/home"; BIN="$TMP/bin"; mkdir -p "$H" "$BIN"
# 假 CLI：hc get 回 $TMP/get.json；herdr-app ls 回 $TMP/ls.json；do 把參數記到 $TMP/renamed
cat > "$BIN/hc" <<EOF
#!/bin/sh
cat "$TMP/get.json"
EOF
cat > "$BIN/herdr-app" <<EOF
#!/bin/sh
if [ "\$1" = ls ]; then cat "$TMP/ls.json"; exit 0; fi
shift; echo "\$*" > "$TMP/renamed"; echo '{"ok":true}'
EOF
chmod +x "$BIN/hc" "$BIN/herdr-app"

setup() {  # $1=terminal title $2=tab name $3=tab 的 terminal 清單（逗號分隔）
  "$PY" - "$TMP" "$1" "$2" "$3" <<'PYEOF'
import json, sys
tmp, title, name, terms = sys.argv[1:]
json.dump({"title": title, "labels": {"herdr.tab": "tb1"}}, open(f"{tmp}/get.json", "w", encoding="utf-8"), ensure_ascii=False)
tab = {"id": "tb1", "name": name, "terminals": [{"terminal": t} for t in terms.split(",")]}
json.dump({"spaces": [{"tabs": [tab]}]}, open(f"{tmp}/ls.json", "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
  rm -f "$TMP/renamed"
}
run() { echo '{}' | HOME="$H" USERPROFILE="$H" PATH="$BIN:$PATH" HC_TERMINAL_ID="${1:-t1}" "$PY" "$HOOK"; }
renamed() { cat "$TMP/renamed" 2>/dev/null || true; }

# 1) 預設名稱「Claude Code」→ 改成標題（去掉開頭的 ✳）
setup "✳ 登入頁修正" "Claude Code" "t1"
run; [ "$(renamed)" = "tab.rename --id tb1 --name 登入頁修正" ] || fail "預設名稱未改：$(renamed)"

# 2) 編號名稱 → 改
setup "登入頁修正" "2" "t1"
run; [ -n "$(renamed)" ] || fail "編號名稱未改"

# 3) 上次 hook 寫的名稱 → 標題變了跟著改
setup "結帳流程" "登入頁修正" "t1"
run; [ "$(renamed)" = "tab.rename --id tb1 --name 結帳流程" ] || fail "未跟著更新自己寫的名稱"

# 4) 使用者手動改過 → 不覆寫
setup "新標題" "我自己取的" "t1"
run; [ -z "$(renamed)" ] || fail "覆寫了手動命名"

# 5) 已同名 → 不重複改
setup "結帳流程" "結帳流程" "t1"
run; [ -z "$(renamed)" ] || fail "同名仍重複改"

# 6) 標題還是預設「Claude Code」→ 不改
setup "Claude Code" "2" "t1"
run; [ -z "$(renamed)" ] || fail "用預設標題改名"

# 7) 不是分頁的第一個 terminal（旁邊的 worker）→ 不改
setup "worker 任務" "Claude Code" "t0,t1"
run t1; [ -z "$(renamed)" ] || fail "worker 改了主分頁"

# 8) 不在 Herdr.app 內 → 安靜結束
setup "登入頁修正" "Claude Code" "t1"
echo '{}' | HOME="$H" PATH="$BIN:$PATH" env -u HC_TERMINAL_ID "$PY" "$HOOK"
[ -z "$(renamed)" ] || fail "沒有 HC_TERMINAL_ID 仍改名"

echo "herdr-tab-title: all passed"
