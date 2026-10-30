#!/usr/bin/env bash
# statusline 的 context 顯示驗證。HOME 導到暫存目錄，不碰真的 ~/.claude。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

H="$TMP/home"; mkdir -p "$H/.claude"
echo '{"autoCompactWindow": 400000}' > "$H/.claude/settings.json"
SL="$REPO_DIR/setup/config/statusline.sh"

# autoCompactWindow 400K、210K → 進度條約半滿＋顯示 210K
OUT="$(cd "$TMP" && echo '{"model":{"display_name":"Opus"},"context_window":{"total_input_tokens":210000,"context_window_size":1000000,"used_percentage":21}}' | HOME="$H" bash "$SL")"
echo "$OUT" | grep -q '52% 210K' || fail "statusline 應顯示 52% 210K（對 400K compact 點）：$OUT"
echo "$OUT" | grep -q '███' || fail "statusline 應有進度條（210K／400K 約半滿）：$OUT"
OUT="$(cd "$TMP" && echo '{"model":{"display_name":"Opus"}}' | HOME="$H" bash "$SL")"
echo "$OUT" | grep -q '0K' || fail "缺 context_window 應顯示 0K：$OUT"

echo "PASS: statusline（3 項）"
