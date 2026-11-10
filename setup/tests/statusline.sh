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

# subagent 列：模型簡稱／effort、截斷、模型未定顯示 ?
SSL="$REPO_DIR/setup/config/subagent-statusline.sh"
OUT="$(echo '{"columns":60,"tasks":[{"id":"a1","agentType":"general-purpose","model":"claude-sonnet-5-5","effort":"medium","label":"Scanning a very long description that must be truncated","tokenCount":42318},{"id":"a2","agentType":"Explore","label":"x","tokenCount":0}]}' | bash "$SSL")"
echo "$OUT" | grep -q '"id": "a1"' || fail "subagent 列應回傳 id：$OUT"
echo "$OUT" | grep -q 'sonnet/medium' || fail "subagent 列應顯示 sonnet/medium：$OUT"
echo "$OUT" | grep -q '42K' || fail "subagent 列應顯示 42K：$OUT"
echo "$OUT" | grep -q '…' || fail "過長的 label 應截斷：$OUT"
echo "$OUT" | grep -q '"id": "a2".*?' || fail "模型未定應顯示 ?：$OUT"

echo "PASS: statusline（4 項）"
